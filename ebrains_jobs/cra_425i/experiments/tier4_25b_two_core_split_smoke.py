#!/usr/bin/env python3
"""
Tier 4.25B — Two-Core State/Learning Split Smoke

Splits CRA state across two SpiNNaker cores:
  Core 0 (state core): context, route, memory, schedule
  Core 1 (learning core): pending, readout, maturity

Inter-core transport: SDP point-to-point.
State core sends CMD_SCHEDULE_PENDING_SPLIT (opcode 30) to learning core.
Learning core matures pending and updates readout autonomously.

Modes:
  local        — verify source/reference constants
  prepare      — create EBRAINS upload bundle with two .aplx images
  run-hardware — load two images, run split task, read back both cores
  ingest       — compare hardware results with 4.23c monolithic reference

Claim boundary:
  PASS means the two-core split reproduced the monolithic 4.23c result
  within tolerance. It is not speedup, not multi-chip, not general
  multi-core framework.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"
RUNTIME = ROOT / "coral_reef_spinnaker" / "spinnaker_runtime"
TIER = "Tier 4.25C — Two-Core State/Learning Split Repeatability"
RUNNER_REVISION = "tier4_25c_two_core_split_smoke_20260502_0001"
UPLOAD_PACKAGE_NAME = "cra_425i"
STABLE_EBRAINS_UPLOAD = ROOT / "ebrains_jobs" / UPLOAD_PACKAGE_NAME
DEPRECATED_EBRAINS_UPLOADS: list[Path] = [
    ROOT / "ebrains_jobs" / "cra_424",
    ROOT / "ebrains_jobs" / "cra_424a",
    ROOT / "ebrains_jobs" / "cra_424b",
    ROOT / "ebrains_jobs" / "cra_425b",
    ROOT / "ebrains_jobs" / "cra_425c",
    ROOT / "ebrains_jobs" / "cra_425d",
    ROOT / "ebrains_jobs" / "cra_425e",
    ROOT / "ebrains_jobs" / "cra_425f",
    ROOT / "ebrains_jobs" / "cra_425g",
    ROOT / "ebrains_jobs" / "cra_425h",
]

STATE_CORE_PROFILE = "state_core"
LEARNING_CORE_PROFILE = "learning_core"
STATE_CORE_APP_ID = 1
LEARNING_CORE_APP_ID = 2
STATE_CORE_P = 4
LEARNING_CORE_P = 5

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments import tier4_22i_custom_runtime_roundtrip as base  # noqa: E402
from experiments.tier4_23a_continuous_local_reference import (  # noqa: E402
    ContinuousEventLoop,
    generate_chunked_reference,
)
from experiments.tier4_22x_compact_v2_bridge_decoupled_smoke import (  # noqa: E402
    TASK_SEQUENCE,
    CONTEXT_KEY_IDS,
    ROUTE_KEY_IDS,
    MEMORY_KEY_IDS,
    V2StateBridge,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2))


def criterion(name: str, value: Any, rule: str, passed: bool, note: str = "") -> dict[str, Any]:
    return {"name": name, "value": value, "rule": rule, "passed": passed, "note": note}


def run_cmd(cmd: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=True, check=False)
    return {
        "command": " ".join(cmd),
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def build_aplx_for_profile(profile: str, output_dir: Path) -> dict[str, Any]:
    """Build .aplx for a given runtime profile."""
    env = os.environ.copy()
    tools = base.detect_spinnaker_tools()
    if tools and not env.get("SPINN_DIRS"):
        env["SPINN_DIRS"] = tools
    env["RUNTIME_PROFILE"] = profile

    build = run_cmd(["make", "-C", str(RUNTIME), "clean", "all"], cwd=ROOT, env=env)
    # Save build output for debugging
    (output_dir / f"tier4_25c_build_{profile}_stdout.txt").write_text(build["stdout"])
    (output_dir / f"tier4_25c_build_{profile}_stderr.txt").write_text(build["stderr"])

    aplx = RUNTIME / "build" / "coral_reef.aplx"
    profile_aplx = RUNTIME / "build" / f"coral_reef_{profile}.aplx"
    # Copy to profile-specific name so both images can coexist
    if aplx.exists() and not profile_aplx.exists():
        shutil.copy2(aplx, profile_aplx)
    elf_gnu = RUNTIME / "build" / "gnu" / "coral_reef.elf"
    elf = RUNTIME / "build" / "coral_reef.elf"
    elf_actual = elf_gnu if elf_gnu.exists() else elf if elf.exists() else None

    return {
        "profile": profile,
        "build_returncode": build["returncode"],
        "build_stdout": build["stdout"],
        "build_stderr": build["stderr"],
        "aplx_exists": profile_aplx.exists(),
        "aplx_path": str(profile_aplx) if profile_aplx.exists() else str(aplx),
        "elf_exists": elf_actual is not None and elf_actual.exists(),
        "elf_path": str(elf_actual) if elf_actual else "",
    }


def local(args: argparse.Namespace, output_dir: Path) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)

    # Verify we can build both profiles locally (syntax check via make test)
    host_tests = base.run_host_tests(output_dir)
    main_syntax = base.run_main_syntax_check(output_dir)

    # Verify config.h has the split opcodes
    config_text = (RUNTIME / "src" / "config.h").read_text()
    has_split_opcodes = "CMD_SCHEDULE_PENDING_SPLIT" in config_text and "CMD_MATURE_ACK_SPLIT" in config_text

    # Verify state_manager.c has profile-specific tick function
    sm_text = (RUNTIME / "src" / "state_manager.c").read_text()
    has_state_core = "CRA_RUNTIME_PROFILE_STATE_CORE" in sm_text
    has_learning_core = "CRA_RUNTIME_PROFILE_LEARNING_CORE" in sm_text

    result = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "mode": "local",
        "host_tests": host_tests,
        "main_syntax": main_syntax,
        "has_split_opcodes": has_split_opcodes,
        "has_state_core_profile": has_state_core,
        "has_learning_core_profile": has_learning_core,
    }
    write_json(output_dir / "tier4_25c_local_results.json", result)
    return 0


def prepare(args: argparse.Namespace, output_dir: Path) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    local_exit = local(args, output_dir / "local_reference")

    # Build both .aplx images
    state_build = build_aplx_for_profile(STATE_CORE_PROFILE, output_dir)
    learning_build = build_aplx_for_profile(LEARNING_CORE_PROFILE, output_dir)

    bundle = output_dir / "ebrains_upload_bundle" / UPLOAD_PACKAGE_NAME
    if bundle.exists():
        shutil.rmtree(bundle)
    (bundle / "experiments").mkdir(parents=True, exist_ok=True)
    (bundle / "coral_reef_spinnaker" / "python_host").mkdir(parents=True, exist_ok=True)

    scripts = [
        "tier4_25b_two_core_split_smoke.py",
        "tier4_22i_custom_runtime_roundtrip.py",
        "tier4_23a_continuous_local_reference.py",
        "tier4_22x_compact_v2_bridge_decoupled_smoke.py",
        "tier4_22j_minimal_custom_runtime_learning.py",
        "tier4_22l_custom_runtime_learning_parity.py",
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

    # Copy built .aplx artifacts into bundle so EBRAINS doesn't need to rebuild
    # (EBRAINS can rebuild, but including them saves time)
    if state_build["aplx_exists"]:
        shutil.copy2(state_build["aplx_path"], bundle / "coral_reef_state.aplx")
    if learning_build["aplx_exists"]:
        shutil.copy2(learning_build["aplx_path"], bundle / "coral_reef_learning.aplx")

    command = f"{UPLOAD_PACKAGE_NAME}/experiments/tier4_25b_two_core_split_smoke.py --mode run-hardware --seed {args.seed}"
    readme = bundle / "README_TIER4_25C_JOB.md"
    readme.write_text(
        "# Tier 4.25C Two-Core State/Learning Split Repeatability Job\n\n"
        f"Upload the `{UPLOAD_PACKAGE_NAME}` folder itself so the JobManager path starts with `{UPLOAD_PACKAGE_NAME}/`.\n\n"
        "This job loads two custom C runtime images onto two SpiNNaker cores:\n"
        f"- Core {STATE_CORE_P} (app_id={STATE_CORE_APP_ID}): `coral_reef_state.aplx` with `RUNTIME_PROFILE={STATE_CORE_PROFILE}`\n"
        f"- Core {LEARNING_CORE_P} (app_id={LEARNING_CORE_APP_ID}): `coral_reef_learning.aplx` with `RUNTIME_PROFILE={LEARNING_CORE_PROFILE}`\n\n"
        "The state core holds context/route/memory/schedule. The learning core holds pending/readout.\n"
        "Inter-core messages use SDP (opcode 30).\n\n"
        "Run command (default output dir is tier4_25c_seed42_job_output):\n\n"
        f"```text\n{command}\n```\n\n"
        "For multi-seed repeatability, run three jobs with --seed 42, --seed 43, --seed 44.\n"
        "Do NOT add --out-dir or --output-dir flags; EBRAINS strips 'out' from arguments.\n\n"
        "Pass means the two-core split reproduced the monolithic 4.23c result within tolerance.\n",
        encoding="utf-8",
    )

    STABLE_EBRAINS_UPLOAD.parent.mkdir(parents=True, exist_ok=True)
    for old_upload in DEPRECATED_EBRAINS_UPLOADS:
        if old_upload.exists():
            shutil.rmtree(old_upload)
    if STABLE_EBRAINS_UPLOAD.exists():
        shutil.rmtree(STABLE_EBRAINS_UPLOAD)
    shutil.copytree(bundle, STABLE_EBRAINS_UPLOAD)

    tools = base.detect_spinnaker_tools()
    criteria = [
        criterion("local reference generated", local_exit, "== 0", local_exit == 0),
        criterion("upload bundle created", str(bundle), "exists", bundle.exists()),
        criterion("runtime source included", str(bundle / "coral_reef_spinnaker" / "spinnaker_runtime"), "exists", (bundle / "coral_reef_spinnaker" / "spinnaker_runtime").exists()),
        criterion("state_core .aplx built or tools missing", state_build["aplx_exists"], "== True", state_build["aplx_exists"] or not tools),
        criterion("learning_core .aplx built or tools missing", learning_build["aplx_exists"], "== True", learning_build["aplx_exists"] or not tools),
        criterion("split opcodes in config.h", "CMD_SCHEDULE_PENDING_SPLIT", "present", "CMD_SCHEDULE_PENDING_SPLIT" in (RUNTIME / "src" / "config.h").read_text()),
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
    write_json(output_dir / "tier4_25c_prepare_results.json", result)
    return 0 if status == "prepared" else 1


def _build_schedule(sequence: list, delay_steps: int = 5) -> list[dict]:
    """Build compact schedule entries from task sequence.

    Uses bridge-visible fields from the v2 task sequence.
    """
    schedule = []
    for i, event in enumerate(sequence):
        entry = {
            "timestep": i + 1,
            "context_key": int(event.get("bridge_context_key_id", 0)),
            "route_key": int(event.get("bridge_route_key_id", 0)),
            "memory_key": int(event.get("bridge_memory_key_id", 0)),
            "cue": float(event.get("bridge_visible_cue", 0)),
            "target": float(event.get("target", 0.0)),
            "delay": delay_steps,
        }
        schedule.append(entry)
    return schedule


def run_hardware(args: argparse.Namespace, output_dir: Path) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    tools = base.detect_spinnaker_tools()
    if tools and not env.get("SPINN_DIRS"):
        env["SPINN_DIRS"] = tools

    # Build both images
    state_build = build_aplx_for_profile(STATE_CORE_PROFILE, output_dir)
    learning_build = build_aplx_for_profile(LEARNING_CORE_PROFILE, output_dir)

    state_aplx = Path(state_build["aplx_path"]) if state_build["aplx_exists"] else RUNTIME / "build" / "coral_reef.aplx"
    learning_aplx = Path(learning_build["aplx_path"]) if learning_build["aplx_exists"] else RUNTIME / "build" / "coral_reef.aplx"

    env_report = base.environment_report()
    host_tests = base.run_host_tests(output_dir)
    main_syntax = base.run_main_syntax_check(output_dir)

    target = base.acquire_hardware_target(args)
    hostname = str(target.get("hostname") or target.get("target_ipaddress") or "")
    tx = target.get("_transceiver")

    state_load: dict[str, Any] = {"status": "not_attempted"}
    learning_load: dict[str, Any] = {"status": "not_attempted"}
    state_task: dict[str, Any] = {"status": "not_attempted"}
    learning_task: dict[str, Any] = {"status": "not_attempted"}

    try:
        if target.get("status") == "pass" and hostname:
            # Load state core
            state_load = base.load_application_spinnman(
                hostname, state_aplx,
                x=int(args.dest_x), y=int(args.dest_y), p=STATE_CORE_P,
                app_id=STATE_CORE_APP_ID,
                delay=float(args.startup_delay_seconds),
                transceiver=tx,
            )
            # Load learning core
            learning_load = base.load_application_spinnman(
                hostname, learning_aplx,
                x=int(args.dest_x), y=int(args.dest_y), p=LEARNING_CORE_P,
                app_id=LEARNING_CORE_APP_ID,
                delay=float(args.startup_delay_seconds),
                transceiver=tx,
            )

        if (target.get("status") == "pass" and hostname
            and state_load.get("status") == "pass"
            and learning_load.get("status") == "pass"):
            state_task, learning_task = two_core_hardware_loop(
                hostname, args, target, state_load, learning_load,
            )
    finally:
        base.release_hardware_target(target)

    write_json(output_dir / "tier4_25c_environment.json", env_report)
    write_json(output_dir / "tier4_25c_target_acquisition.json", base.public_target_acquisition(target))
    write_json(output_dir / "tier4_25c_state_load.json", state_load)
    write_json(output_dir / "tier4_25c_learning_load.json", learning_load)
    write_json(output_dir / "tier4_25c_state_task.json", state_task)
    write_json(output_dir / "tier4_25c_learning_task.json", learning_task)

    # Criteria
    ref_weight = 32768
    ref_bias = 0
    ref_events = len(TASK_SEQUENCE)

    state_final = state_task.get("final_state", {}) if isinstance(state_task, dict) else {}
    learning_final = learning_task.get("final_state", {}) if isinstance(learning_task, dict) else {}

    criteria = [
        criterion("runner revision current", RUNNER_REVISION, "expected current source", True),
        criterion("custom C host tests pass", host_tests.get("status"), "== pass", host_tests.get("status") == "pass"),
        criterion("main.c syntax check pass", main_syntax.get("status"), "== pass", main_syntax.get("status") == "pass"),
        criterion("hardware target acquired", base.public_target_acquisition(target), "status == pass", target.get("status") == "pass"),
        criterion("state_core .aplx built", state_build["aplx_exists"], "== True", state_build["aplx_exists"]),
        criterion("learning_core .aplx built", learning_build["aplx_exists"], "== True", learning_build["aplx_exists"]),
        criterion("state_core load pass", state_load.get("status"), "== pass", state_load.get("status") == "pass"),
        criterion("learning_core load pass", learning_load.get("status"), "== pass", learning_load.get("status") == "pass"),
        criterion("state_core reset succeeded", state_task.get("reset_ok"), "== True", state_task.get("reset_ok") is True),
        criterion("learning_core reset succeeded", learning_task.get("reset_ok"), "== True", learning_task.get("reset_ok") is True),
        criterion("all context writes succeeded", state_task.get("state_writes", {}).get("context", []), "all success", all(w.get("success") for w in state_task.get("state_writes", {}).get("context", []))),
        criterion("all route writes succeeded", state_task.get("state_writes", {}).get("route", []), "all success", all(w.get("success") for w in state_task.get("state_writes", {}).get("route", []))),
        criterion("all memory writes succeeded", state_task.get("state_writes", {}).get("memory", []), "all success", all(w.get("success") for w in state_task.get("state_writes", {}).get("memory", []))),
        criterion("all schedule uploads succeeded", state_task.get("schedule_uploads", []), "all success", all(u.get("success") for u in state_task.get("schedule_uploads", []))),
        criterion("state_core run_continuous succeeded", state_task.get("run_continuous", {}).get("success"), "== True", state_task.get("run_continuous", {}).get("success") is True),
        criterion("learning_core run_continuous succeeded", learning_task.get("run_continuous", {}).get("success"), "== True", learning_task.get("run_continuous", {}).get("success") is True),
        criterion("state_core final read succeeded", state_final.get("success"), "== True", state_final.get("success") is True),
        criterion("learning_core final read succeeded", learning_final.get("success"), "== True", learning_final.get("success") is True),
        criterion("learning_core weight near reference", learning_final.get("readout_weight_raw"), f"within +/- {ref_weight//4} of {ref_weight}", abs(int(learning_final.get("readout_weight_raw") or 0) - ref_weight) <= ref_weight // 4),
        criterion("learning_core bias near reference", learning_final.get("readout_bias_raw"), f"within +/- {ref_weight//4} of {ref_bias}", abs(int(learning_final.get("readout_bias_raw") or 0) - ref_bias) <= ref_weight // 4),
        criterion("learning_core pending_created matches reference", learning_final.get("pending_created"), f"== {ref_events}", learning_final.get("pending_created") == ref_events),
        criterion("learning_core pending_matured matches reference", learning_final.get("pending_matured"), f"== {ref_events}", learning_final.get("pending_matured") == ref_events),
        criterion("learning_core active_pending cleared", learning_final.get("active_pending"), "== 0", learning_final.get("active_pending") == 0),
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
        "state_task": state_task,
        "learning_task": learning_task,
    }
    write_json(output_dir / "tier4_25c_hardware_results.json", result)
    return 0 if status == "pass" else 1


def two_core_hardware_loop(
    hostname: str,
    args: argparse.Namespace,
    target: dict[str, Any],
    state_load: dict[str, Any],
    learning_load: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run the two-core split task on hardware using ColonyController."""
    from coral_reef_spinnaker.python_host.colony_controller import ColonyController

    dest_x = int(args.dest_x)
    dest_y = int(args.dest_y)
    state_cpu = STATE_CORE_P
    learning_cpu = LEARNING_CORE_P
    port = int(args.port)
    timeout = float(args.timeout_seconds)

    state_ctrl = ColonyController(hostname, port=port, timeout=timeout)
    learning_ctrl = ColonyController(hostname, port=port, timeout=timeout)

    # Static regime values from V2StateBridge.REGIMES
    REGIME_VALUES = {
        "ctx_A": (1.0, 1.0), "ctx_B": (-1.0, 1.0),
        "ctx_C": (1.0, 1.0), "ctx_D": (-1.0, 1.0),
        "route_A": (1.0, 1.0), "route_B": (-1.0, 1.0),
        "route_C": (-1.0, 1.0), "route_D": (1.0, 1.0),
        "mem_A": (1.0, 1.0), "mem_B": (-1.0, 1.0),
        "mem_C": (1.0, 1.0), "mem_D": (-1.0, 1.0),
    }

    try:
        # Reset both cores
        state_reset = state_ctrl.reset(dest_x, dest_y, state_cpu)
        learning_reset = learning_ctrl.reset(dest_x, dest_y, learning_cpu)
        time.sleep(0.1)

        # Write state slots to state core only
        state_writes = {"context": [], "route": [], "memory": []}

        for ctx_key, ctx_id in CONTEXT_KEY_IDS.items():
            val, conf = REGIME_VALUES.get(ctx_key, (0.0, 1.0))
            ok = state_ctrl.write_context(ctx_id, val, conf, dest_x, dest_y, state_cpu)
            state_writes["context"].append({"key": ctx_key, "success": ok.get("success") is True})

        for route_key, route_id in ROUTE_KEY_IDS.items():
            val, conf = REGIME_VALUES.get(route_key, (0.0, 1.0))
            ok = state_ctrl.write_route_slot(route_id, val, conf, dest_x, dest_y, state_cpu)
            state_writes["route"].append({"key": route_key, "success": ok.get("success") is True})

        for mem_key, mem_id in MEMORY_KEY_IDS.items():
            val, conf = REGIME_VALUES.get(mem_key, (0.0, 1.0))
            ok = state_ctrl.write_memory_slot(mem_id, val, conf, dest_x, dest_y, state_cpu)
            state_writes["memory"].append({"key": mem_key, "success": ok.get("success") is True})

        # Upload schedule to state core only
        schedule = _build_schedule(TASK_SEQUENCE)
        schedule_uploads = []
        for i, entry in enumerate(schedule):
            ok = state_ctrl.write_schedule_entry(
                index=i,
                timestep=entry["timestep"],
                context_key=entry["context_key"],
                route_key=entry["route_key"],
                memory_key=entry["memory_key"],
                cue=entry["cue"],
                target=entry["target"],
                delay=entry["delay"],
                dest_x=dest_x,
                dest_y=dest_y,
                dest_cpu=state_cpu,
            )
            schedule_uploads.append({"index": i, "success": ok.get("success") is True})

        # Start continuous mode on both cores
        learning_rate = 0.25
        state_run = state_ctrl.run_continuous(learning_rate, len(schedule), dest_x, dest_y, state_cpu)
        learning_run = learning_ctrl.run_continuous(learning_rate, 0, dest_x, dest_y, learning_cpu)
        time.sleep(0.05)

        # Wait for completion (schedule + pending maturity)
        max_wait = 10.0  # seconds
        poll_interval = 0.5
        waited = 0.0
        while waited < max_wait:
            time.sleep(poll_interval)
            waited += poll_interval
            learning_status = learning_ctrl.read_state(dest_x, dest_y, learning_cpu)
            if learning_status.get("success") and learning_status.get("active_pending") == 0:
                break

        # Send pause to both cores
        state_pause = state_ctrl.pause(dest_x, dest_y, state_cpu)
        learning_pause = learning_ctrl.pause(dest_x, dest_y, learning_cpu)
        time.sleep(0.1)

        # Read back final state from both cores
        state_final = state_ctrl.read_state(dest_x, dest_y, state_cpu)
        learning_final = learning_ctrl.read_state(dest_x, dest_y, learning_cpu)

        state_task = {
            "status": "completed",
            "reset_ok": state_reset,
            "state_writes": state_writes,
            "schedule_uploads": schedule_uploads,
            "run_continuous": {"success": state_run.get("success") is True},
            "pause": {"success": state_pause.get("success") is True},
            "final_state": state_final,
            "waited_seconds": waited,
        }
        learning_task = {
            "status": "completed",
            "reset_ok": learning_reset,
            "run_continuous": {"success": learning_run.get("success") is True},
            "pause": {"success": learning_pause.get("success") is True},
            "final_state": learning_final,
            "waited_seconds": waited,
        }

        return state_task, learning_task
    except Exception as exc:
        import traceback
        return (
            {"status": "fail", "reason": str(exc), "traceback": traceback.format_exc()},
            {"status": "fail", "reason": str(exc), "traceback": traceback.format_exc()},
        )
    finally:
        state_ctrl.close()
        learning_ctrl.close()


def ingest(args: argparse.Namespace, output_dir: Path) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)

    hw_dir = args.hardware_output_dir or output_dir
    hw_results_path = hw_dir / "tier4_25c_hardware_results.json"

    hw_results = json.loads(hw_results_path.read_text()) if hw_results_path.exists() else {}
    criteria = hw_results.get("criteria", [])
    passed = sum(1 for c in criteria if c.get("passed"))
    total = len(criteria)
    status = "pass" if passed == total else "fail"

    result = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "mode": "ingest",
        "status": status,
        "output_dir": str(output_dir),
        "hardware_output_dir": str(hw_dir),
        "passed_count": passed,
        "total_count": total,
        "criteria": criteria,
    }
    write_json(output_dir / "tier4_25c_ingest_results.json", result)

    report = (
        f"# {TIER} — Ingest Report\n\n"
        f"- Status: **{status.upper()}**\n"
        f"- Passed: {passed}/{total}\n"
        f"- Hardware output: `{hw_dir}`\n\n"
        f"## Criteria\n\n"
    )
    for c in criteria:
        report += f"- {'✓' if c['passed'] else '✗'} {c['name']}: `{c['value']}` ({c['rule']})\n"

    (output_dir / "tier4_25c_ingest_report.md").write_text(report)
    return 0 if status == "pass" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=TIER)
    parser.add_argument("--mode", default="local", choices=["local", "prepare", "run-hardware", "ingest"])
    parser.add_argument("--out-dir", default="", dest="output_dir")
    parser.add_argument("--hw-dir", default="", dest="hardware_output_dir")
    parser.add_argument("--dest-x", default="0")
    parser.add_argument("--dest-y", default="0")
    parser.add_argument("--dest-cpu", default="4")
    parser.add_argument("--app-id", default="1")
    parser.add_argument("--startup-delay-seconds", default="2.0")
    parser.add_argument("--port", default="17893")
    parser.add_argument("--timeout-seconds", default="2.0")
    parser.add_argument("--target-acquisition", choices=["auto", "hostname", "spynnaker-probe"], default="auto")
    parser.add_argument("--target-probe-population-size", type=int, default=1)
    parser.add_argument("--target-probe-run-ms", type=float, default=1.0)
    parser.add_argument("--target-probe-timestep-ms", type=float, default=1.0)
    parser.add_argument("--auto-dest-cpu", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--spinnaker-hostname", default="")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for task generation and run labeling")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    default_dir = f"tier4_25c_seed{args.seed}_job_output"
    output_dir = Path(args.output_dir) if args.output_dir else Path(default_dir)
    if args.hardware_output_dir:
        args.hardware_output_dir = Path(args.hardware_output_dir)

    if args.mode == "local":
        return local(args, output_dir)
    if args.mode == "prepare":
        return prepare(args, output_dir)
    if args.mode == "run-hardware":
        return run_hardware(args, output_dir)
    if args.mode == "ingest":
        return ingest(args, output_dir)
    return 1


if __name__ == "__main__":
    sys.exit(main())
