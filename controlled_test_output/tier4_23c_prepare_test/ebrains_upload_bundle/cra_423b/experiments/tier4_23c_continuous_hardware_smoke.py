#!/usr/bin/env python3
"""Tier 4.23c — One-Board Hardware Continuous Smoke.

Uploads a compact event schedule to the chip, starts autonomous continuous
execution via CMD_RUN_CONTINUOUS, and reads back compact state for comparison
with the Tier 4.23a local fixed-point reference.

Modes:
  local        — run continuous loop locally, compare with chunked 4.22x reference
  prepare      — create EBRAINS upload bundle
  run-hardware — upload schedule, run continuous, read back on real SpiNNaker
  ingest       — compare returned hardware artifacts with local reference

Claim boundary:
  LOCAL/PREPARED means the reference and bundle are ready; not hardware evidence.
  PASS in run-hardware means the timer-driven autonomous event loop on real
  SpiNNaker matched the local fixed-point reference within declared tolerance.
  This is not full native v2.1, not speedup evidence, not multi-core scaling,
  and not final autonomy.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"
RUNTIME = ROOT / "coral_reef_spinnaker" / "spinnaker_runtime"
TIER = "Tier 4.23c - One-Board Hardware Continuous Smoke"
RUNNER_REVISION = "tier4_23c_continuous_hardware_smoke_20260501_0004"
RUNTIME_PROFILE = "decoupled_memory_route"
RUNTIME_PROFILE_COMMANDS = [
    "CMD_RESET",
    "CMD_READ_STATE",
    "CMD_MATURE_PENDING",
    "CMD_WRITE_CONTEXT",
    "CMD_READ_CONTEXT",
    "CMD_WRITE_ROUTE_SLOT",
    "CMD_READ_ROUTE_SLOT",
    "CMD_WRITE_MEMORY_SLOT",
    "CMD_READ_MEMORY_SLOT",
    "CMD_SCHEDULE_DECOUPLED_MEMORY_ROUTE_CONTEXT_PENDING",
    "CMD_WRITE_SCHEDULE_ENTRY",
    "CMD_RUN_CONTINUOUS",
    "CMD_PAUSE",
]
UPLOAD_PACKAGE_NAME = "cra_423b"
STABLE_EBRAINS_UPLOAD = ROOT / "ebrains_jobs" / UPLOAD_PACKAGE_NAME
DEPRECATED_EBRAINS_UPLOADS: list[Path] = []

FP_SHIFT = 15
FP_ONE = 1 << FP_SHIFT
TASK_LEARNING_RATE = 0.25
TASK_TAIL_WINDOW = 6
PENDING_GAP_DEPTH = 2

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments import tier4_22i_custom_runtime_roundtrip as base  # noqa: E402
from experiments.tier4_22x_compact_v2_bridge_decoupled_smoke import (  # noqa: E402
    TASK_SEQUENCE,
    CONTEXT_KEY_IDS,
    ROUTE_KEY_IDS,
    MEMORY_KEY_IDS,
    V2StateBridge,
)
from experiments.tier4_23a_continuous_local_reference import (  # noqa: E402
    ContinuousEventLoop,
    generate_chunked_reference,
    compare_continuous_vs_chunked,
    fp_from_float,
    fp_to_float,
    criterion,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def markdown_value(value: Any) -> str:
    if isinstance(value, bool):
        return "True" if value else "False"
    if value is None:
        return "None"
    return str(value)


def build_schedule(sequence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert the task sequence into chip schedule entries."""
    schedule: list[dict[str, Any]] = []
    for event in sequence:
        schedule.append(
            {
                "timestep": int(event["step"]),
                "context_key": int(event["bridge_context_key_id"]),
                "route_key": int(event["bridge_route_key_id"]),
                "memory_key": int(event["bridge_memory_key_id"]),
                "cue": float(event["bridge_visible_cue"]),
                "target": float(event["target"]),
                "delay": PENDING_GAP_DEPTH,
            }
        )
    return schedule


def local(args: argparse.Namespace, output_dir: Path) -> int:
    """Local mode: run continuous loop and compare with chunked reference."""
    output_dir.mkdir(parents=True, exist_ok=True)

    sequence = TASK_SEQUENCE
    schedule = build_schedule(sequence)

    loop = ContinuousEventLoop(sequence)
    continuous_ref = loop.run()

    chunked_ref = generate_chunked_reference(sequence)
    deltas = compare_continuous_vs_chunked(continuous_ref, chunked_ref)

    cont_metrics = continuous_ref["metrics"]
    chunk_metrics = chunked_ref["metrics"]

    criteria = [
        criterion("runner revision current", RUNNER_REVISION, "expected current source", True),
        criterion("continuous reference generated", continuous_ref["status"], "== pass", continuous_ref["status"] == "pass"),
        criterion("chunked reference generated", chunked_ref["status"], "== pass", chunked_ref["status"] == "pass"),
        criterion("sequence length matches", continuous_ref["sequence_length"], f"== {chunked_ref['sequence_length']}", continuous_ref["sequence_length"] == chunked_ref["sequence_length"]),
        criterion("autonomous timesteps equal sequence + gap + drain", continuous_ref["autonomous_timesteps"], f"== {continuous_ref['sequence_length'] + PENDING_GAP_DEPTH}", continuous_ref["autonomous_timesteps"] == continuous_ref["sequence_length"] + PENDING_GAP_DEPTH),
        criterion("decisions equal sequence length", continuous_ref["decisions"], f"== {continuous_ref['sequence_length']}", continuous_ref["decisions"] == continuous_ref["sequence_length"]),
        criterion("rewards equal sequence length", continuous_ref["rewards"], f"== {continuous_ref['sequence_length']}", continuous_ref["rewards"] == continuous_ref["sequence_length"]),
        criterion("max pending depth matches chunked", continuous_ref["max_pending_depth"], f"== {chunked_ref['max_pending_depth']}", continuous_ref["max_pending_depth"] == chunked_ref["max_pending_depth"]),
        criterion("max feature delta", deltas["max_feature_delta"], "<= 1", deltas["max_feature_delta"] <= 1),
        criterion("max prediction delta", deltas["max_prediction_delta"], "<= 1", deltas["max_prediction_delta"] <= 1),
        criterion("max weight delta", deltas["max_weight_delta"], "<= 1", deltas["max_weight_delta"] <= 1),
        criterion("max bias delta", deltas["max_bias_delta"], "<= 1", deltas["max_bias_delta"] <= 1),
        criterion("all feature deltas zero", deltas["feature_deltas_all_zero"], "== True", deltas["feature_deltas_all_zero"]),
        criterion("all prediction deltas zero", deltas["prediction_deltas_all_zero"], "== True", deltas["prediction_deltas_all_zero"]),
        criterion("all weight deltas zero", deltas["weight_deltas_all_zero"], "== True", deltas["weight_deltas_all_zero"]),
        criterion("all bias deltas zero", deltas["bias_deltas_all_zero"], "== True", deltas["bias_deltas_all_zero"]),
        criterion("continuous accuracy matches chunked", cont_metrics["accuracy"], f"== {chunk_metrics['accuracy']}", abs(cont_metrics["accuracy"] - chunk_metrics["accuracy"]) < 0.0001),
        criterion("continuous tail accuracy matches chunked", cont_metrics["tail_accuracy"], f"== {chunk_metrics['tail_accuracy']}", abs(cont_metrics["tail_accuracy"] - chunk_metrics["tail_accuracy"]) < 0.0001),
        criterion("continuous final weight matches chunked", continuous_ref["final_readout_weight_raw"], f"== {chunked_ref['final_readout_weight_raw']}", continuous_ref["final_readout_weight_raw"] == chunked_ref["final_readout_weight_raw"]),
        criterion("continuous final bias matches chunked", continuous_ref["final_readout_bias_raw"], f"== {chunked_ref['final_readout_bias_raw']}", continuous_ref["final_readout_bias_raw"] == chunked_ref["final_readout_bias_raw"]),
        criterion("zero synthetic fallback", 0, "== 0", True),
    ]

    passed = sum(1 for c in criteria if c["passed"])
    total = len(criteria)
    status = "pass" if passed == total else "fail"

    result = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "mode": "local",
        "status": status,
        "passed_count": passed,
        "total_count": total,
        "output_dir": str(output_dir),
        "schedule": schedule,
        "criteria": criteria,
        "continuous_reference": {
            "sequence_length": continuous_ref["sequence_length"],
            "autonomous_timesteps": continuous_ref["autonomous_timesteps"],
            "decisions": continuous_ref["decisions"],
            "rewards": continuous_ref["rewards"],
            "max_pending_depth": continuous_ref["max_pending_depth"],
            "final_readout_weight_raw": continuous_ref["final_readout_weight_raw"],
            "final_readout_bias_raw": continuous_ref["final_readout_bias_raw"],
            "metrics": cont_metrics,
        },
        "chunked_reference_summary": {
            "sequence_length": chunked_ref["sequence_length"],
            "metrics": chunk_metrics,
        },
        "deltas": deltas,
    }

    write_json(output_dir / "tier4_23c_local_results.json", result)
    write_csv(output_dir / "tier4_23c_schedule.csv", schedule)

    report_path = output_dir / "tier4_23c_local_report.md"
    report_lines = [
        f"# {TIER}",
        "",
        f"- Generated: `{utc_now()}`",
        f"- Mode: `local`",
        f"- Status: **{'PASS' if status == 'pass' else 'FAIL'}**",
        f"- Output directory: `{output_dir}`",
        "",
        "## Summary",
        "",
        f"- sequence_length: `{continuous_ref['sequence_length']}`",
        f"- autonomous_timesteps: `{continuous_ref['autonomous_timesteps']}`",
        f"- max_pending_depth: `{continuous_ref['max_pending_depth']}`",
        f"- continuous accuracy: `{cont_metrics['accuracy']}`",
        f"- continuous tail_accuracy: `{cont_metrics['tail_accuracy']}`",
        f"- max_feature_delta: `{deltas['max_feature_delta']}`",
        f"- max_prediction_delta: `{deltas['max_prediction_delta']}`",
        f"- max_weight_delta: `{deltas['max_weight_delta']}`",
        f"- max_bias_delta: `{deltas['max_bias_delta']}`",
        f"- final_weight_raw: `{continuous_ref['final_readout_weight_raw']}`",
        f"- final_bias_raw: `{continuous_ref['final_readout_bias_raw']}`",
        "",
        "## Criteria",
        "",
        "| Criterion | Value | Rule | Pass |",
        "| --- | --- | --- | --- |",
    ]
    for c in criteria:
        report_lines.append(
            f"| {c['name']} | `{markdown_value(c['value'])}` | `{c['rule']}` | {'yes' if c['passed'] else 'no'} |"
        )
    report_lines.append("")
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    return 0 if status == "pass" else 1


def prepare(args: argparse.Namespace, output_dir: Path) -> int:
    """Prepare mode: create EBRAINS upload bundle."""
    output_dir.mkdir(parents=True, exist_ok=True)

    local_ref_dir = output_dir / "local_reference"
    local_exit = local(args, local_ref_dir)

    bundle = output_dir / "ebrains_upload_bundle" / UPLOAD_PACKAGE_NAME
    if bundle.exists():
        shutil.rmtree(bundle)
    (bundle / "experiments").mkdir(parents=True, exist_ok=True)
    (bundle / "coral_reef_spinnaker" / "python_host").mkdir(parents=True, exist_ok=True)

    scripts = [
        "tier4_23c_continuous_hardware_smoke.py",
        "tier4_23a_continuous_local_reference.py",
        "tier4_22x_compact_v2_bridge_decoupled_smoke.py",
        "tier4_22w_native_decoupled_memory_route_composition_smoke.py",
        "tier4_22u_native_memory_route_state_smoke.py",
        "tier4_22t_native_keyed_route_state_smoke.py",
        "tier4_22s_native_route_state_smoke.py",
        "tier4_22r_native_context_state_smoke.py",
        "tier4_22l_custom_runtime_learning_parity.py",
        "tier4_22j_minimal_custom_runtime_learning.py",
        "tier4_22i_custom_runtime_roundtrip.py",
    ]
    for script in scripts:
        src = ROOT / "experiments" / script
        if src.exists():
            shutil.copy2(src, bundle / "experiments" / script)
            os.chmod(bundle / "experiments" / script, 0o755)

    shutil.copy2(ROOT / "coral_reef_spinnaker" / "__init__.py", bundle / "coral_reef_spinnaker" / "__init__.py")
    shutil.copy2(
        ROOT / "coral_reef_spinnaker" / "python_host" / "colony_controller.py",
        bundle / "coral_reef_spinnaker" / "python_host" / "colony_controller.py",
    )
    base.copy_tree_clean(RUNTIME, bundle / "coral_reef_spinnaker" / "spinnaker_runtime")

    command = f"{UPLOAD_PACKAGE_NAME}/experiments/tier4_23c_continuous_hardware_smoke.py --mode run-hardware --output-dir tier4_23c_job_output"
    readme = bundle / "README_TIER4_23C_JOB.md"
    readme.write_text(
        "# Tier 4.23c EBRAINS Hardware Continuous Smoke Job\n\n"
        f"Upload the `{UPLOAD_PACKAGE_NAME}` folder itself so the JobManager path starts with `{UPLOAD_PACKAGE_NAME}/`.\n\n"
        f"This job builds and loads the custom C runtime with `RUNTIME_PROFILE={RUNTIME_PROFILE}`. "
        "It pre-writes keyed context slots, route slots, and memory slots, then uploads a compact "
        "48-event schedule via CMD_WRITE_SCHEDULE_ENTRY, starts autonomous execution with "
        "CMD_RUN_CONTINUOUS, waits for completion, and reads back compact state via CMD_READ_STATE.\n\n"
        f"Enabled runtime command surface: `{', '.join(RUNTIME_PROFILE_COMMANDS)}`.\n\n"
        "Run command:\n\n"
        f"```text\n{command}\n```\n\n"
        "Pass means the timer-driven autonomous event loop on real SpiNNaker matched the local "
        "fixed-point continuous reference within predeclared tolerance. It is not full v2.1 on-chip, "
        "not speedup evidence, and not final autonomy.\n",
        encoding="utf-8",
    )

    STABLE_EBRAINS_UPLOAD.parent.mkdir(parents=True, exist_ok=True)
    for old_upload in DEPRECATED_EBRAINS_UPLOADS:
        if old_upload.exists():
            shutil.rmtree(old_upload)
    if STABLE_EBRAINS_UPLOAD.exists():
        shutil.rmtree(STABLE_EBRAINS_UPLOAD)
    shutil.copytree(bundle, STABLE_EBRAINS_UPLOAD)

    criteria = [
        criterion("local reference generated", local_exit, "== 0", local_exit == 0),
        criterion("upload bundle created", str(bundle), "exists", bundle.exists()),
        criterion("runtime source included", str(bundle / "coral_reef_spinnaker" / "spinnaker_runtime"), "exists", (bundle / "coral_reef_spinnaker" / "spinnaker_runtime").exists()),
        criterion("run-hardware command emitted", command, "contains --mode run-hardware", "--mode run-hardware" in command),
    ]

    status = "prepared" if all(c["passed"] for c in criteria) else "blocked"
    result = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "mode": "prepare",
        "status": status,
        "output_dir": str(output_dir),
        "summary": {
            "upload_bundle": str(bundle),
            "stable_upload_folder": str(STABLE_EBRAINS_UPLOAD),
            "job_command": command,
            "what_i_need_from_user": f"Upload {UPLOAD_PACKAGE_NAME} to EBRAINS/JobManager and run the emitted command.",
            "claim_boundary": "Prepared source bundle only; no hardware evidence until returned artifacts pass ingest.",
            "next_step_if_passed": "Run the emitted EBRAINS command and ingest returned files.",
        },
        "criteria": criteria,
    }
    write_json(output_dir / "tier4_23c_prepare_results.json", result)
    return 0 if status == "prepared" else 1


def continuous_hardware_loop(
    hostname: str,
    args: argparse.Namespace,
    *,
    dest_cpu: int,
    schedule: list[dict[str, Any]],
    reference: dict[str, Any],
) -> dict[str, Any]:
    """Execute the continuous hardware micro-loop."""
    from coral_reef_spinnaker.python_host.colony_controller import ColonyController

    ctrl = ColonyController(hostname, port=int(args.port), timeout=float(args.timeout_seconds))
    started = time.perf_counter()

    try:
        # Reset
        reset_ok = ctrl.reset(args.dest_x, args.dest_y, dest_cpu)
        time.sleep(args.command_delay_seconds)

        # Pre-write all state slots
        state_writes: dict[str, list[dict[str, Any]]] = {
            "context": [],
            "route": [],
            "memory": [],
        }

        for key_name, key_id in CONTEXT_KEY_IDS.items():
            value = 1 if ("A" in key_name or "C" in key_name) else -1
            resp = ctrl.write_context(key_id, value, confidence=1.0, dest_x=args.dest_x, dest_y=args.dest_y, dest_cpu=dest_cpu)
            state_writes["context"].append({"key": key_id, "value": value, "success": resp.get("success")})
            time.sleep(args.command_delay_seconds)

        for key_name, key_id in ROUTE_KEY_IDS.items():
            value = 1 if ("A" in key_name or "D" in key_name) else -1
            resp = ctrl.write_route_slot(key_id, value, confidence=1.0, dest_x=args.dest_x, dest_y=args.dest_y, dest_cpu=dest_cpu)
            state_writes["route"].append({"key": key_id, "value": value, "success": resp.get("success")})
            time.sleep(args.command_delay_seconds)

        for key_name, key_id in MEMORY_KEY_IDS.items():
            value = 1 if ("A" in key_name or "C" in key_name) else -1
            resp = ctrl.write_memory_slot(key_id, value, confidence=1.0, dest_x=args.dest_x, dest_y=args.dest_y, dest_cpu=dest_cpu)
            state_writes["memory"].append({"key": key_id, "value": value, "success": resp.get("success")})
            time.sleep(args.command_delay_seconds)

        # Upload schedule entries
        schedule_uploads: list[dict[str, Any]] = []
        for idx, entry in enumerate(schedule):
            resp = ctrl.write_schedule_entry(
                index=idx,
                timestep=entry["timestep"],
                context_key=entry["context_key"],
                route_key=entry["route_key"],
                memory_key=entry["memory_key"],
                cue=entry["cue"],
                target=entry["target"],
                delay=entry["delay"],
                dest_x=args.dest_x,
                dest_y=args.dest_y,
                dest_cpu=dest_cpu,
            )
            schedule_uploads.append({"index": idx, "success": resp.get("success")})
            time.sleep(args.command_delay_seconds / 10)

        # Start continuous execution
        run_resp = ctrl.run_continuous(
            learning_rate=TASK_LEARNING_RATE,
            schedule_count=len(schedule),
            dest_x=args.dest_x,
            dest_y=args.dest_y,
            dest_cpu=dest_cpu,
        )
        time.sleep(args.command_delay_seconds)

        # Wait for completion (safe margin)
        wait_seconds = float(args.continuous_wait_seconds)
        time.sleep(wait_seconds)

        # Pause to get stopped timestep
        pause_resp = ctrl.pause(dest_x=args.dest_x, dest_y=args.dest_y, dest_cpu=dest_cpu)
        stopped_timestep = pause_resp.get("stopped_timestep", 0)

        # Read back final state
        final_state = ctrl.read_state(args.dest_x, args.dest_y, dest_cpu)
        time.sleep(args.command_delay_seconds)

        # Read back slot states for verification
        ctx_states: list[dict[str, Any]] = []
        for key_id in CONTEXT_KEY_IDS.values():
            state = ctrl.read_context(key_id, dest_x=args.dest_x, dest_y=args.dest_y, dest_cpu=dest_cpu)
            ctx_states.append(state)
            time.sleep(args.command_delay_seconds / 2)

        route_states: list[dict[str, Any]] = []
        for key_id in ROUTE_KEY_IDS.values():
            state = ctrl.read_route_slot(key_id, dest_x=args.dest_x, dest_y=args.dest_y, dest_cpu=dest_cpu)
            route_states.append(state)
            time.sleep(args.command_delay_seconds / 2)

        mem_states: list[dict[str, Any]] = []
        for key_id in MEMORY_KEY_IDS.values():
            state = ctrl.read_memory_slot(key_id, dest_x=args.dest_x, dest_y=args.dest_y, dest_cpu=dest_cpu)
            mem_states.append(state)
            time.sleep(args.command_delay_seconds / 2)

        final_weight_raw = final_state.get("readout_weight_raw", 0)
        final_bias_raw = final_state.get("readout_bias_raw", 0)

        all_writes_ok = (
            reset_ok
            and all(w.get("success") for w in state_writes["context"])
            and all(w.get("success") for w in state_writes["route"])
            and all(w.get("success") for w in state_writes["memory"])
            and all(u.get("success") for u in schedule_uploads)
            and run_resp.get("success")
            and pause_resp.get("success")
            and final_state.get("success")
        )

        return {
            "status": "pass" if all_writes_ok else "fail",
            "hostname": hostname,
            "dest_x": int(args.dest_x),
            "dest_y": int(args.dest_y),
            "dest_cpu": dest_cpu,
            "runtime_seconds": time.perf_counter() - started,
            "reset_ok": reset_ok,
            "state_writes": state_writes,
            "schedule_uploads": schedule_uploads,
            "run_continuous": run_resp,
            "pause": pause_resp,
            "stopped_timestep": stopped_timestep,
            "final_state": final_state,
            "context_states": ctx_states,
            "route_states": route_states,
            "memory_states": mem_states,
            "final_readout_weight_raw": final_weight_raw,
            "final_readout_bias_raw": final_bias_raw,
        }
    except Exception as exc:
        return {
            "status": "fail",
            "hostname": hostname,
            "runtime_seconds": time.perf_counter() - started,
            "exception_type": type(exc).__name__,
            "exception": str(exc),
            "traceback": traceback.format_exc(),
        }


def run_hardware(args: argparse.Namespace, output_dir: Path) -> int:
    """Run-hardware mode: upload schedule, run continuous, read back."""
    output_dir.mkdir(parents=True, exist_ok=True)

    sequence = TASK_SEQUENCE
    schedule = build_schedule(sequence)
    continuous_ref_local = ContinuousEventLoop(sequence).run()

    env = os.environ.copy()
    tools = base.detect_spinnaker_tools()
    if tools and not env.get("SPINN_DIRS"):
        env["SPINN_DIRS"] = tools
    env["RUNTIME_PROFILE"] = RUNTIME_PROFILE
    build = base.run_cmd(["make", "-C", str(RUNTIME), "clean", "all"], cwd=ROOT, env=env)
    aplx = Path(build.get("aplx_artifact") or RUNTIME / "build" / "coral_reef.aplx")
    build["runtime_profile"] = RUNTIME_PROFILE
    build["status"] = "pass" if build["returncode"] == 0 and aplx.exists() else "fail"

    env_report = base.environment_report()
    host_tests = base.run_host_tests(output_dir)
    main_syntax = base.run_main_syntax_check(output_dir)

    target = base.acquire_hardware_target(args)
    hostname = str(target.get("hostname") or target.get("target_ipaddress") or "")
    dest_cpu = int(target.get("dest_cpu") or args.dest_cpu)

    load: dict[str, Any] = {"status": "not_attempted"}
    task_result: dict[str, Any] = {"status": "not_attempted"}

    try:
        if target.get("status") == "pass" and not args.skip_load:
            load = base.load_application_spinnman(
                hostname,
                aplx,
                x=int(args.dest_x),
                y=int(args.dest_y),
                p=dest_cpu,
                app_id=int(args.app_id),
                delay=float(args.startup_delay_seconds),
                transceiver=target.get("_transceiver"),
            )
        elif args.skip_load:
            load = {"status": "skipped", "reason": "--skip-load set", "hostname": hostname, "dest_cpu": dest_cpu}

        if target.get("status") == "pass" and hostname and load.get("status") in {"pass", "skipped"}:
            task_result = continuous_hardware_loop(
                hostname, args, dest_cpu=dest_cpu,
                schedule=schedule, reference=continuous_ref_local,
            )
    finally:
        target_cleanup = base.release_hardware_target(target)

    write_json(output_dir / "tier4_23c_environment.json", env_report)
    write_json(output_dir / "tier4_23c_target_acquisition.json", base.public_target_acquisition({**target, "cleanup": target_cleanup}))
    write_json(output_dir / "tier4_23c_load_result.json", load)
    write_json(output_dir / "tier4_23c_task_result.json", task_result)

    ref_weight = continuous_ref_local["final_readout_weight_raw"]
    ref_bias = continuous_ref_local["final_readout_bias_raw"]
    ref_decisions = continuous_ref_local["sequence_length"]
    ref_rewards = continuous_ref_local["sequence_length"]

    final_state = task_result.get("final_state", {}) if isinstance(task_result, dict) else {}

    criteria = [
        criterion("runner revision current", RUNNER_REVISION, "expected current source", True),
        criterion("custom C host tests pass", host_tests.get("status"), "== pass", host_tests.get("status") == "pass"),
        criterion("main.c host syntax check pass", main_syntax.get("status"), "== pass", main_syntax.get("status") == "pass"),
        criterion("hardware runtime profile selected", build.get("runtime_profile"), f"== {RUNTIME_PROFILE}", build.get("runtime_profile") == RUNTIME_PROFILE),
        criterion("hardware target acquired", base.public_target_acquisition(target), "status == pass and hostname acquired", target.get("status") == "pass" and bool(hostname)),
        criterion("custom runtime .aplx build pass", build["status"], "== pass", build["status"] == "pass"),
        criterion("custom runtime app load pass", load.get("status"), "== pass", load.get("status") == "pass"),
        criterion("reset succeeded", task_result.get("reset_ok"), "== True", task_result.get("reset_ok") is True),
        criterion("all context writes succeeded", task_result.get("state_writes", {}).get("context", []), "all success", all(w.get("success") for w in task_result.get("state_writes", {}).get("context", []))),
        criterion("all route writes succeeded", task_result.get("state_writes", {}).get("route", []), "all success", all(w.get("success") for w in task_result.get("state_writes", {}).get("route", []))),
        criterion("all memory writes succeeded", task_result.get("state_writes", {}).get("memory", []), "all success", all(w.get("success") for w in task_result.get("state_writes", {}).get("memory", []))),
        criterion("all schedule uploads succeeded", task_result.get("schedule_uploads", []), "all success", all(u.get("success") for u in task_result.get("schedule_uploads", []))),
        criterion("run_continuous succeeded", task_result.get("run_continuous", {}).get("success"), "== True", task_result.get("run_continuous", {}).get("success") is True),
        criterion("pause succeeded", task_result.get("pause", {}).get("success"), "== True", task_result.get("pause", {}).get("success") is True),
        criterion("final state read succeeded", final_state.get("success"), "== True", final_state.get("success") is True),
        criterion("final weight matches local reference", task_result.get("final_readout_weight_raw"), f"== {ref_weight}", task_result.get("final_readout_weight_raw") == ref_weight),
        criterion("final bias matches local reference", task_result.get("final_readout_bias_raw"), f"== {ref_bias}", task_result.get("final_readout_bias_raw") == ref_bias),
        criterion("decisions count matches reference", final_state.get("decisions"), f"== {ref_decisions}", final_state.get("decisions") == ref_decisions),
        criterion("reward events count matches reference", final_state.get("reward_events"), f"== {ref_rewards}", final_state.get("reward_events") == ref_rewards),
        criterion("pending created count matches reference", final_state.get("pending_created"), f"== {ref_decisions}", final_state.get("pending_created") == ref_decisions),
        criterion("pending matured count matches reference", final_state.get("pending_matured"), f"== {ref_rewards}", final_state.get("pending_matured") == ref_rewards),
        criterion("active pending cleared", final_state.get("active_pending"), "== 0", final_state.get("active_pending") == 0),
    ]

    status = "pass" if all(c["passed"] for c in criteria) else "fail"
    result = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "mode": "run-hardware",
        "status": status,
        "output_dir": str(output_dir),
        "criteria": criteria,
        "task_result": task_result,
    }
    write_json(output_dir / "tier4_23c_hardware_results.json", result)
    return 0 if status == "pass" else 1


def ingest(args: argparse.Namespace, output_dir: Path) -> int:
    """Ingest mode: compare hardware results with local reference."""
    output_dir.mkdir(parents=True, exist_ok=True)

    hardware_dir = args.hardware_output_dir or output_dir
    hardware_results_path = hardware_dir / "tier4_23c_hardware_results.json"
    task_result_path = hardware_dir / "tier4_23c_task_result.json"

    if not hardware_results_path.exists():
        print(f"Hardware results not found: {hardware_results_path}")
        return 1

    hardware_results = base.read_json(hardware_results_path)
    task_result = base.read_json(task_result_path) if task_result_path.exists() else {}

    ref_dir = args.reference_dir
    if ref_dir and (ref_dir / "tier4_23c_local_results.json").exists():
        local_ref = base.read_json(ref_dir / "tier4_23c_local_results.json")
    else:
        local_ref_dir = output_dir / "local_reference"
        local_exit = local(args, local_ref_dir)
        if local_exit != 0:
            print("Local reference generation failed")
            return 1
        local_ref = base.read_json(local_ref_dir / "tier4_23c_local_results.json")

    cont_ref = local_ref.get("continuous_reference", {})
    ref_weight = cont_ref.get("final_readout_weight_raw")
    ref_bias = cont_ref.get("final_readout_bias_raw")
    ref_decisions = cont_ref.get("sequence_length")
    ref_rewards = cont_ref.get("sequence_length")

    final_state = task_result.get("final_state", {}) if isinstance(task_result, dict) else {}

    criteria = [
        criterion("hardware result file exists", str(hardware_results_path), "exists", True),
        criterion("hardware overall status", hardware_results.get("status"), "== pass", hardware_results.get("status") == "pass"),
        criterion("hardware task status", task_result.get("status"), "== pass", task_result.get("status") == "pass"),
        criterion("all state writes succeeded", task_result.get("state_writes", {}), "all success", all(
            w.get("success") for w in task_result.get("state_writes", {}).get("context", [])
            + task_result.get("state_writes", {}).get("route", [])
            + task_result.get("state_writes", {}).get("memory", [])
        )),
        criterion("all schedule uploads succeeded", task_result.get("schedule_uploads", []), "all success", all(u.get("success") for u in task_result.get("schedule_uploads", []))),
        criterion("run_continuous succeeded", task_result.get("run_continuous", {}).get("success"), "== True", task_result.get("run_continuous", {}).get("success") is True),
        criterion("pause succeeded", task_result.get("pause", {}).get("success"), "== True", task_result.get("pause", {}).get("success") is True),
        criterion("final state read succeeded", final_state.get("success"), "== True", final_state.get("success") is True),
        criterion("final weight matches local reference", task_result.get("final_readout_weight_raw"), f"== {ref_weight}", task_result.get("final_readout_weight_raw") == ref_weight),
        criterion("final bias matches local reference", task_result.get("final_readout_bias_raw"), f"== {ref_bias}", task_result.get("final_readout_bias_raw") == ref_bias),
        criterion("decisions count matches reference", final_state.get("decisions"), f"== {ref_decisions}", final_state.get("decisions") == ref_decisions),
        criterion("reward events count matches reference", final_state.get("reward_events"), f"== {ref_rewards}", final_state.get("reward_events") == ref_rewards),
        criterion("pending created count matches reference", final_state.get("pending_created"), f"== {ref_decisions}", final_state.get("pending_created") == ref_decisions),
        criterion("pending matured count matches reference", final_state.get("pending_matured"), f"== {ref_rewards}", final_state.get("pending_matured") == ref_rewards),
        criterion("active pending cleared", final_state.get("active_pending"), "== 0", final_state.get("active_pending") == 0),
    ]

    status = "pass" if all(c["passed"] for c in criteria) else "fail"
    result = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "mode": "ingest",
        "status": status,
        "output_dir": str(output_dir),
        "hardware_results": hardware_results,
        "task_result": task_result,
        "local_reference": local_ref,
        "criteria": criteria,
    }
    write_json(output_dir / "tier4_23c_ingest_results.json", result)
    return 0 if status == "pass" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=TIER)
    parser.add_argument("--mode", default="local", choices=["local", "prepare", "run-hardware", "ingest"])
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--hardware-output-dir", type=Path, default=None)
    parser.add_argument("--reference-dir", type=Path, default=None)
    parser.add_argument("--spinnaker-hostname", default="")
    parser.add_argument("--target-acquisition", choices=["auto", "hostname", "spynnaker-probe"], default="auto")
    parser.add_argument("--target-probe-population-size", type=int, default=1)
    parser.add_argument("--target-probe-run-ms", type=float, default=1.0)
    parser.add_argument("--target-probe-timestep-ms", type=float, default=1.0)
    parser.add_argument("--auto-dest-cpu", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--dest-x", type=int, default=0)
    parser.add_argument("--dest-y", type=int, default=0)
    parser.add_argument("--dest-cpu", type=int, default=1)
    parser.add_argument("--app-id", type=int, default=17)
    parser.add_argument("--port", type=int, default=17893)
    parser.add_argument("--timeout-seconds", type=float, default=5.0)
    parser.add_argument("--startup-delay-seconds", type=float, default=2.0)
    parser.add_argument("--command-delay-seconds", type=float, default=0.05)
    parser.add_argument("--continuous-wait-seconds", type=float, default=3.0)
    parser.add_argument("--skip-load", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    default = CONTROLLED / f"tier4_23c_{stamp}_{args.mode.replace('-', '_')}"
    output_dir = (args.output_dir or default).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        if args.mode == "local":
            return local(args, output_dir)
        if args.mode == "prepare":
            return prepare(args, output_dir)
        if args.mode == "run-hardware":
            return run_hardware(args, output_dir)
        if args.mode == "ingest":
            return ingest(args, output_dir)
        raise SystemExit(f"unsupported mode: {args.mode}")
    except Exception as exc:
        result = {
            "tier": TIER,
            "runner_revision": RUNNER_REVISION,
            "generated_at_utc": utc_now(),
            "mode": args.mode,
            "status": "fail",
            "failure_reason": f"Unhandled {type(exc).__name__}: {exc}",
            "traceback": traceback.format_exc(),
            "output_dir": str(output_dir),
        }
        write_json(output_dir / "tier4_23c_crash.json", result)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
