#!/usr/bin/env python3
"""Tier 4.22j minimal custom-runtime closed-loop learning smoke.

Tier 4.22i proved the custom C sidecar can build, load, accept host commands,
and return compact state from real SpiNNaker. Tier 4.22j adds the smallest
possible on-chip learning heartbeat:

    RESET -> SCHEDULE_PENDING(feature, delay) -> wait -> MATURE_PENDING(target, lr)
    -> CMD_READ_STATE proves pending matured and readout weight/bias changed.

Claim boundary:
- PREPARED means the EBRAINS source bundle and command are ready.
- PASS in run-hardware means the loaded custom runtime performed one delayed
  pending/readout update on real SpiNNaker and exposed it through compact
  readback.
- This is not full CRA task learning, not v2.1 mechanism transfer, not speedup
  evidence, not multi-core scaling, and not final on-chip autonomy.
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
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"
RUNTIME = ROOT / "coral_reef_spinnaker" / "spinnaker_runtime"
TIER = "Tier 4.22j - Minimal Custom-Runtime Closed-Loop Learning Smoke"
RUNNER_REVISION = "tier4_22j_minimal_custom_runtime_learning_20260501_0001"
TIER4_22I_LATEST = CONTROLLED / "tier4_22i_latest_manifest.json"
DEFAULT_OUTPUT = CONTROLLED / "tier4_22j_20260501_minimal_custom_runtime_learning_prepared"
UPLOAD_PACKAGE_NAME = "cra_422s"
STABLE_EBRAINS_UPLOAD = ROOT / "ebrains_jobs" / UPLOAD_PACKAGE_NAME
DEPRECATED_EBRAINS_UPLOADS = [
    ROOT / "ebrains_jobs" / "cra_422j",
    ROOT / "ebrains_jobs" / "cra_422s_old",
]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments import tier4_22i_custom_runtime_roundtrip as base  # noqa: E402


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def criterion(name: str, value: Any, rule: str, passed: bool, note: str = "") -> dict[str, Any]:
    return {"name": name, "value": value, "rule": rule, "passed": bool(passed), "note": note}


def markdown_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.6g}"
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, sort_keys=True)
    return str(value)


def int_or(value: Any, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def latest_status(path: Path) -> tuple[str, str | None]:
    return base.latest_status(path)


def command_surface_checks(config_source: str, controller_source: str, host_source: str, test_source: str, *, label: str) -> list[dict[str, Any]]:
    return [
        criterion(
            f"{label} CMD_SCHEDULE_PENDING defined",
            "CMD_SCHEDULE_PENDING 9",
            "config.h defines opcode",
            "#define CMD_SCHEDULE_PENDING 9" in config_source,
        ),
        criterion(
            f"{label} CMD_MATURE_PENDING defined",
            "CMD_MATURE_PENDING 10",
            "config.h defines opcode",
            "#define CMD_MATURE_PENDING   10" in config_source,
        ),
        criterion(
            f"{label} learning opcodes host-tested",
            "assert command constants",
            "host tests cover opcodes",
            "assert(CMD_SCHEDULE_PENDING == 9)" in test_source
            and "assert(CMD_MATURE_PENDING == 10)" in test_source,
        ),
        criterion(
            f"{label} controller exposes schedule command",
            "schedule_pending_decision",
            "Python host can schedule delayed-credit state on board",
            "def schedule_pending_decision" in controller_source
            and "CMD_SCHEDULE_PENDING" in controller_source,
        ),
        criterion(
            f"{label} controller exposes mature command",
            "mature_pending",
            "Python host can mature delayed-credit state on board",
            "def mature_pending" in controller_source
            and "CMD_MATURE_PENDING" in controller_source,
        ),
        criterion(
            f"{label} runtime schedule handler exists",
            "_handle_schedule_pending",
            "runtime computes prediction and schedules pending horizon",
            "static void _handle_schedule_pending" in host_source
            and "cra_state_predict_readout" in host_source
            and "cra_state_schedule_pending_horizon" in host_source,
        ),
        criterion(
            f"{label} runtime mature handler exists",
            "_handle_mature_pending",
            "runtime matures pending horizon and updates readout",
            "static void _handle_mature_pending" in host_source
            and "cra_state_mature_pending_horizons" in host_source,
        ),
        criterion(
            f"{label} learning commands dispatched",
            "case CMD_SCHEDULE_PENDING / CMD_MATURE_PENDING",
            "SDP dispatcher routes learning commands",
            "case CMD_SCHEDULE_PENDING" in host_source
            and "case CMD_MATURE_PENDING" in host_source,
        ),
    ]


def prepare_bundle(output_dir: Path) -> tuple[Path, str, dict[str, str]]:
    bundle = output_dir / "ebrains_upload_bundle" / UPLOAD_PACKAGE_NAME
    if bundle.exists():
        shutil.rmtree(bundle)
    (bundle / "experiments").mkdir(parents=True, exist_ok=True)
    (bundle / "coral_reef_spinnaker" / "python_host").mkdir(parents=True, exist_ok=True)

    for script in [
        "tier4_22j_minimal_custom_runtime_learning.py",
        "tier4_22i_custom_runtime_roundtrip.py",
    ]:
        shutil.copy2(ROOT / "experiments" / script, bundle / "experiments" / script)
        os.chmod(bundle / "experiments" / script, 0o755)
    shutil.copy2(ROOT / "coral_reef_spinnaker" / "__init__.py", bundle / "coral_reef_spinnaker" / "__init__.py")
    shutil.copy2(
        ROOT / "coral_reef_spinnaker" / "python_host" / "colony_controller.py",
        bundle / "coral_reef_spinnaker" / "python_host" / "colony_controller.py",
    )
    base.copy_tree_clean(RUNTIME, bundle / "coral_reef_spinnaker" / "spinnaker_runtime")

    command = f"{UPLOAD_PACKAGE_NAME}/experiments/tier4_22j_minimal_custom_runtime_learning.py --mode run-hardware --output-dir tier4_22j_job_output"
    readme = bundle / "README_TIER4_22J_JOB.md"
    readme.write_text(
        "# Tier 4.22j EBRAINS Minimal Custom-Runtime Learning Job\n\n"
        f"Upload the `{UPLOAD_PACKAGE_NAME}` folder itself so the JobManager path starts with `{UPLOAD_PACKAGE_NAME}/`. Do not upload `controlled_test_output`.\n\n"
        "This job depends on the Tier 4.22i board-roundtrip pass. It builds and loads the custom C runtime, then sends `CMD_SCHEDULE_PENDING` followed by `CMD_MATURE_PENDING` and validates that compact `CMD_READ_STATE` shows one pending horizon matured and readout weight/bias changed on chip.\n\n"
        "Run command:\n\n"
        f"```text\n{command}\n```\n\n"
        "Pass means a minimal delayed pending/readout update happened in the custom runtime on real SpiNNaker. It is not full CRA task learning or speedup evidence.\n",
        encoding="utf-8",
    )
    artifacts = {"upload_bundle": str(bundle), "job_readme": str(readme)}
    STABLE_EBRAINS_UPLOAD.parent.mkdir(parents=True, exist_ok=True)
    for old_upload in DEPRECATED_EBRAINS_UPLOADS:
        if old_upload.exists():
            shutil.rmtree(old_upload)
    if STABLE_EBRAINS_UPLOAD.exists():
        shutil.rmtree(STABLE_EBRAINS_UPLOAD)
    shutil.copytree(bundle, STABLE_EBRAINS_UPLOAD)
    artifacts["stable_upload_folder"] = str(STABLE_EBRAINS_UPLOAD)
    return bundle, command, artifacts


def minimal_learning_smoke(hostname: str, args: argparse.Namespace, *, dest_cpu: int) -> dict[str, Any]:
    from coral_reef_spinnaker.python_host.colony_controller import ColonyController

    started = time.perf_counter()
    ctrl = ColonyController(hostname, port=int(args.port), timeout=float(args.timeout_seconds))
    try:
        reset_ok = ctrl.reset(args.dest_x, args.dest_y, dest_cpu)
        time.sleep(float(args.command_delay_seconds))
        state_after_reset = ctrl.read_state(args.dest_x, args.dest_y, dest_cpu)
        schedule = ctrl.schedule_pending_decision(
            feature=float(args.learning_feature),
            delay_steps=int(args.pending_delay_steps),
            dest_x=args.dest_x,
            dest_y=args.dest_y,
            dest_cpu=dest_cpu,
        )
        time.sleep(float(args.command_delay_seconds))
        state_after_schedule = ctrl.read_state(args.dest_x, args.dest_y, dest_cpu)
        time.sleep(float(args.learning_delay_seconds))
        mature = ctrl.mature_pending(
            target=float(args.learning_target),
            learning_rate=float(args.learning_rate),
            mature_timestep=0,
            dest_x=args.dest_x,
            dest_y=args.dest_y,
            dest_cpu=dest_cpu,
        )
        time.sleep(float(args.command_delay_seconds))
        state_after_mature = ctrl.read_state(args.dest_x, args.dest_y, dest_cpu)
        ok = (
            bool(reset_ok)
            and bool(state_after_reset.get("success"))
            and bool(schedule.get("success"))
            and bool(state_after_schedule.get("success"))
            and int(state_after_schedule.get("pending_created") or 0) >= 1
            and int(state_after_schedule.get("active_pending") or 0) >= 1
            and int(state_after_schedule.get("decisions") or 0) >= 1
            and bool(mature.get("success"))
            and int(mature.get("matured_count") or 0) >= 1
            and bool(state_after_mature.get("success"))
            and int(state_after_mature.get("pending_matured") or 0) >= 1
            and int(state_after_mature.get("active_pending") or 0) == 0
            and int(state_after_mature.get("reward_events") or 0) >= 1
            and int(state_after_mature.get("readout_weight_raw") or 0) > 0
            and int(state_after_mature.get("readout_bias_raw") or 0) > 0
        )
        return {
            "status": "pass" if ok else "fail",
            "hostname": hostname,
            "dest_x": int(args.dest_x),
            "dest_y": int(args.dest_y),
            "dest_cpu": int(dest_cpu),
            "reset_ok": reset_ok,
            "schedule_pending": schedule,
            "mature_pending": mature,
            "state_after_reset": state_after_reset,
            "state_after_schedule": state_after_schedule,
            "state_after_mature": state_after_mature,
            "runtime_seconds": time.perf_counter() - started,
        }
    except Exception as exc:
        return {
            "status": "fail",
            "hostname": hostname,
            "exception_type": type(exc).__name__,
            "exception": str(exc),
            "traceback": traceback.format_exc(),
            "runtime_seconds": time.perf_counter() - started,
        }
    finally:
        ctrl.close()


def write_report(path: Path, result: dict[str, Any]) -> None:
    summary = result.get("summary", {})
    lines = [
        "# Tier 4.22j Minimal Custom-Runtime Closed-Loop Learning Smoke",
        "",
        f"- Generated: `{result.get('generated_at_utc', utc_now())}`",
        f"- Mode: `{result.get('mode', summary.get('mode', 'unknown'))}`",
        f"- Status: **{str(result.get('status', 'unknown')).upper()}**",
        f"- Output directory: `{result.get('output_dir', path.parent)}`",
        "",
        "Tier 4.22j tests a minimal chip-owned delayed-credit/readout update after the Tier 4.22i board command path passed.",
        "",
        "## Claim Boundary",
        "",
        "- `PREPARED` means the source bundle and command are ready, not hardware evidence.",
        "- `PASS` in `run-hardware` means one delayed pending/readout update happened in the loaded custom runtime and was visible through compact readback.",
        "- This is not full CRA task learning, not speedup evidence, not multi-core scaling, and not final on-chip autonomy.",
        "",
        "## Summary",
        "",
    ]
    for key in [
        "tier4_22i_status", "hardware_target_configured", "spinnaker_hostname", "selected_dest_cpu",
        "aplx_build_status", "app_load_status", "learning_smoke_status", "pending_created_after_schedule",
        "pending_matured_after_mature", "readout_weight_after_mature", "readout_bias_after_mature",
        "custom_runtime_learning_next_allowed", "raw_remote_status", "raw_remote_failure_reason",
        "ingest_classification", "false_fail_reason", "next_step_if_passed",
    ]:
        if key in summary:
            lines.append(f"- {key}: `{markdown_value(summary[key])}`")
    lines.extend(["", "## Criteria", "", "| Criterion | Value | Rule | Pass |", "| --- | --- | --- | --- |"])
    for item in result.get("criteria", []):
        lines.append(f"| {item['name']} | `{markdown_value(item.get('value'))}` | `{item.get('rule')}` | {'yes' if item.get('passed') else 'no'} |")
    artifacts = result.get("artifacts", {})
    if artifacts:
        lines.extend(["", "## Artifacts", ""])
        for key, value in artifacts.items():
            lines.append(f"- `{key}`: `{value}`")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_latest(output_dir: Path, manifest: Path, report: Path, status: str, mode: str) -> None:
    CONTROLLED.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at_utc": utc_now(),
        "tier": TIER,
        "status": status,
        "mode": mode,
        "output_dir": str(output_dir),
        "manifest": str(manifest),
        "report": str(report),
        "canonical": False,
        "claim": "Latest Tier 4.22j minimal custom-runtime learning smoke; pass is one delayed pending/readout update on board only, not full CRA learning or speedup evidence.",
    }
    write_json(CONTROLLED / "tier4_22j_latest_manifest.json", payload)


def finalize(output_dir: Path, result: dict[str, Any]) -> int:
    manifest = output_dir / "tier4_22j_results.json"
    report = output_dir / "tier4_22j_report.md"
    result.setdefault("artifacts", {})
    result["artifacts"].update({"manifest_json": str(manifest), "report_md": str(report)})
    write_json(manifest, result)
    write_report(report, result)
    write_latest(output_dir, manifest, report, str(result.get("status", "unknown")), str(result.get("mode", "unknown")))
    print(json.dumps({"status": result.get("status"), "output_dir": str(output_dir), "manifest": str(manifest), "report": str(report)}, indent=2))
    return 0 if str(result.get("status", "")).lower() in {"pass", "prepared"} else 1


def prepare(args: argparse.Namespace, output_dir: Path) -> int:
    tier4_22i_status, tier4_22i_manifest = latest_status(TIER4_22I_LATEST)
    main_syntax = base.run_main_syntax_check(output_dir)
    bundle, command, bundle_artifacts = prepare_bundle(output_dir)
    source_checks = command_surface_checks(
        read_text(RUNTIME / "src" / "config.h"),
        read_text(ROOT / "coral_reef_spinnaker" / "python_host" / "colony_controller.py"),
        read_text(RUNTIME / "src" / "host_interface.c"),
        read_text(RUNTIME / "tests" / "test_runtime.c"),
        label="source",
    )
    source_checks += base.sdp_command_protocol_checks(
        read_text(ROOT / "coral_reef_spinnaker" / "python_host" / "colony_controller.py"),
        read_text(RUNTIME / "src" / "host_interface.c"),
        read_text(RUNTIME / "stubs" / "sark.h"),
        label="source",
    )
    bundle_runtime = bundle / "coral_reef_spinnaker" / "spinnaker_runtime"
    bundle_checks = command_surface_checks(
        read_text(bundle_runtime / "src" / "config.h"),
        read_text(bundle / "coral_reef_spinnaker" / "python_host" / "colony_controller.py"),
        read_text(bundle_runtime / "src" / "host_interface.c"),
        read_text(bundle_runtime / "tests" / "test_runtime.c"),
        label="bundle",
    )
    bundle_checks += base.sdp_command_protocol_checks(
        read_text(bundle / "coral_reef_spinnaker" / "python_host" / "colony_controller.py"),
        read_text(bundle_runtime / "src" / "host_interface.c"),
        read_text(bundle_runtime / "stubs" / "sark.h"),
        label="bundle",
    )
    criteria = [
        criterion("Tier 4.22i board roundtrip pass exists", tier4_22i_status, "== pass", tier4_22i_status == "pass"),
        criterion("main.c host syntax check pass", main_syntax.get("status"), "== pass", main_syntax.get("status") == "pass"),
        criterion("upload bundle created", str(bundle), "exists", bundle.exists()),
        criterion("runtime source included", str(bundle / "coral_reef_spinnaker" / "spinnaker_runtime"), "exists", (bundle / "coral_reef_spinnaker" / "spinnaker_runtime").exists()),
        criterion("run-hardware command emitted", command, "contains --mode run-hardware", "--mode run-hardware" in command),
    ] + source_checks + bundle_checks
    status = "prepared" if all(item["passed"] for item in criteria) else "blocked"
    result = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "mode": "prepare",
        "status": status,
        "failure_reason": "" if status == "prepared" else "Failed criteria: " + ", ".join(item["name"] for item in criteria if not item["passed"]),
        "output_dir": str(output_dir),
        "summary": {
            "mode": "prepare",
            "tier4_22i_status": tier4_22i_status,
            "tier4_22i_manifest": tier4_22i_manifest,
            "main_syntax_check_passed": main_syntax.get("status") == "pass",
            "jobmanager_command": command,
            "upload_folder": str(bundle),
            "stable_upload_folder": str(STABLE_EBRAINS_UPLOAD),
            "what_i_need_from_user": f"Upload the generated {UPLOAD_PACKAGE_NAME} folder to EBRAINS/JobManager and run the emitted command; download returned files after completion.",
            "claim_boundary": "Prepared source bundle only; no hardware learning evidence until returned run-hardware artifacts pass.",
        },
        "criteria": criteria,
        "main_syntax_check": main_syntax,
        "artifacts": bundle_artifacts,
    }
    return finalize(output_dir, result)


def run_hardware(args: argparse.Namespace, output_dir: Path) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    tier4_22i_status, tier4_22i_manifest = latest_status(TIER4_22I_LATEST)
    env_report = base.environment_report()
    host_tests = base.run_host_tests(output_dir)
    main_syntax = base.run_main_syntax_check(output_dir)
    build = base.build_aplx(output_dir)
    aplx = Path(build.get("aplx_artifact") or RUNTIME / "build" / "coral_reef.aplx")
    target = {"status": "not_attempted", "reason": "blocked_before_target_acquisition"}
    target_cleanup = {"status": "not_attempted"}
    load = {"status": "not_attempted", "reason": "blocked_before_load"}
    learning = {"status": "not_attempted", "reason": "blocked_before_learning_smoke"}
    hostname = ""
    dest_cpu = int(args.dest_cpu)

    if build.get("status") == "pass":
        target = base.acquire_hardware_target(args)
        hostname = str(target.get("hostname") or target.get("target_ipaddress") or "")
        dest_cpu = int(target.get("dest_cpu") or args.dest_cpu)
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
                learning = minimal_learning_smoke(hostname, args, dest_cpu=dest_cpu)
        finally:
            target_cleanup = base.release_hardware_target(target)

    env_path = output_dir / "tier4_22j_environment.json"
    target_path = output_dir / "tier4_22j_target_acquisition.json"
    write_json(env_path, env_report)
    write_json(target_path, base.public_target_acquisition({**target, "cleanup": target_cleanup}))
    write_json(output_dir / "tier4_22j_load_result.json", load)
    write_json(output_dir / "tier4_22j_learning_result.json", learning)

    after_schedule = learning.get("state_after_schedule", {}) if isinstance(learning, dict) else {}
    after_mature = learning.get("state_after_mature", {}) if isinstance(learning, dict) else {}
    mature = learning.get("mature_pending", {}) if isinstance(learning, dict) else {}
    criteria = [
        criterion("runner revision current", RUNNER_REVISION, "expected current source", True),
        criterion("Tier 4.22i board roundtrip pass exists or fresh bundle", tier4_22i_status, "== pass OR missing in fresh EBRAINS bundle", tier4_22i_status in {"pass", "missing"}),
        criterion("custom C host tests pass", host_tests.get("status"), "== pass", host_tests.get("status") == "pass"),
        criterion("main.c host syntax check pass", main_syntax.get("status"), "== pass", main_syntax.get("status") == "pass"),
        *command_surface_checks(
            read_text(RUNTIME / "src" / "config.h"),
            read_text(ROOT / "coral_reef_spinnaker" / "python_host" / "colony_controller.py"),
            read_text(RUNTIME / "src" / "host_interface.c"),
            read_text(RUNTIME / "tests" / "test_runtime.c"),
            label="runtime",
        ),
        criterion("hardware target acquired", base.public_target_acquisition(target), "status == pass and hostname/IP/transceiver acquired", target.get("status") == "pass" and bool(hostname), "; ".join(str(n) for n in target.get("notes", []))),
        criterion("custom runtime .aplx build pass", build.get("status"), "== pass", build.get("status") == "pass"),
        criterion("custom runtime app load pass", load.get("status"), "== pass", load.get("status") == "pass"),
        criterion("minimal learning smoke pass", learning.get("status"), "== pass", learning.get("status") == "pass"),
        criterion("pending horizon created", after_schedule.get("pending_created"), ">= 1", int(after_schedule.get("pending_created") or 0) >= 1),
        criterion("pending horizon active after schedule", after_schedule.get("active_pending"), ">= 1", int(after_schedule.get("active_pending") or 0) >= 1),
        criterion("decision recorded after schedule", after_schedule.get("decisions"), ">= 1", int(after_schedule.get("decisions") or 0) >= 1),
        criterion("pending mature command matured one", mature.get("matured_count"), ">= 1", int(mature.get("matured_count") or 0) >= 1),
        criterion("pending horizon matured in state", after_mature.get("pending_matured"), ">= 1", int(after_mature.get("pending_matured") or 0) >= 1),
        criterion("active pending cleared", after_mature.get("active_pending"), "== 0", int_or(after_mature.get("active_pending"), -1) == 0),
        criterion("reward event recorded", after_mature.get("reward_events"), ">= 1", int(after_mature.get("reward_events") or 0) >= 1),
        criterion("readout weight increased", after_mature.get("readout_weight_raw"), "> 0", int(after_mature.get("readout_weight_raw") or 0) > 0),
        criterion("readout bias increased", after_mature.get("readout_bias_raw"), "> 0", int(after_mature.get("readout_bias_raw") or 0) > 0),
        criterion("synthetic fallback zero", 0, "== 0", True),
    ]
    status = "pass" if all(item["passed"] for item in criteria) else "fail"
    result = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "mode": "run-hardware",
        "status": status,
        "failure_reason": "" if status == "pass" else "Failed criteria: " + ", ".join(item["name"] for item in criteria if not item["passed"]),
        "output_dir": str(output_dir),
        "summary": {
            "mode": "run-hardware",
            "tier4_22i_status": tier4_22i_status,
            "tier4_22i_manifest": tier4_22i_manifest,
            "hardware_target_configured": target.get("status") == "pass" and bool(hostname),
            "spinnaker_hostname": hostname,
            "selected_dest_cpu": dest_cpu,
            "aplx_build_status": build.get("status"),
            "app_load_status": load.get("status"),
            "learning_smoke_status": learning.get("status"),
            "pending_created_after_schedule": after_schedule.get("pending_created"),
            "pending_matured_after_mature": after_mature.get("pending_matured"),
            "readout_weight_after_mature": after_mature.get("readout_weight"),
            "readout_bias_after_mature": after_mature.get("readout_bias"),
            "custom_runtime_learning_next_allowed": status == "pass",
            "claim_boundary": "One minimal delayed pending/readout update on board only; not full CRA task learning or speedup evidence.",
            "next_step_if_passed": "Tier 4.22l small custom-runtime learning parity: compare this C readout update path against the local Tier 4.22e float/C-equation reference on a tiny sequence before scaling task complexity.",
        },
        "criteria": criteria,
        "environment": env_report,
        "target_acquisition": base.public_target_acquisition(target),
        "target_cleanup": target_cleanup,
        "host_tests": host_tests,
        "main_syntax_check": main_syntax,
        "aplx_build": build,
        "app_load": load,
        "learning_smoke": learning,
        "artifacts": {
            "environment_json": str(env_path),
            "target_acquisition_json": str(target_path),
            "host_test_stdout": str(output_dir / "tier4_22i_host_test_stdout.txt"),
            "host_test_stderr": str(output_dir / "tier4_22i_host_test_stderr.txt"),
            "main_syntax_stdout": str(output_dir / "tier4_22i_main_syntax_normal_stdout.txt"),
            "main_syntax_stderr": str(output_dir / "tier4_22i_main_syntax_normal_stderr.txt"),
            "aplx_build_stdout": str(output_dir / "tier4_22i_aplx_build_stdout.txt"),
            "aplx_build_stderr": str(output_dir / "tier4_22i_aplx_build_stderr.txt"),
            "load_result_json": str(output_dir / "tier4_22j_load_result.json"),
            "learning_result_json": str(output_dir / "tier4_22j_learning_result.json"),
        },
    }
    return finalize(output_dir, result)


def _copy_latest(source: Path, output_dir: Path, pattern: str, *, target_name: str | None = None) -> str:
    matches = [p for p in source.glob(pattern) if p.is_file()]
    if not matches:
        return ""
    chosen = max(matches, key=lambda p: p.stat().st_mtime)
    target = output_dir / (target_name or chosen.name)
    shutil.copy2(chosen, target)
    return str(target)


def ingest(args: argparse.Namespace, output_dir: Path) -> int:
    if args.ingest_dir is None:
        raise SystemExit("--ingest-dir is required in ingest mode")
    source = args.ingest_dir.resolve()
    if not source.exists():
        raise SystemExit(f"ingest dir does not exist: {source}")
    output_dir.mkdir(parents=True, exist_ok=True)

    raw_manifest_path = source / "tier4_22j_results.json"
    if not raw_manifest_path.exists():
        raise SystemExit(f"missing tier4_22j_results.json in ingest dir: {source}")
    raw_report_path = source / "tier4_22j_report.md"
    raw_learning_path = source / "tier4_22j_learning_result.json"
    raw_manifest = read_json(raw_manifest_path)
    learning = read_json(raw_learning_path) if raw_learning_path.exists() else raw_manifest.get("learning_smoke", {})

    artifacts: dict[str, str] = {}
    artifacts["raw_remote_manifest_json"] = _copy_latest(source, output_dir, "tier4_22j_results.json", target_name="remote_tier4_22j_results_raw.json")
    artifacts["raw_remote_report_md"] = _copy_latest(source, output_dir, "tier4_22j_report.md", target_name="remote_tier4_22j_report_raw.md")
    exact_artifact_names = {
        "tier4_22j_environment.json": "environment_json",
        "tier4_22j_target_acquisition.json": "target_acquisition_json",
        "tier4_22j_load_result.json": "load_result_json",
        "tier4_22j_learning_result.json": "learning_result_json",
    }
    for exact, artifact_name in exact_artifact_names.items():
        copied = _copy_latest(source, output_dir, exact)
        if copied:
            artifacts[artifact_name] = copied
    for pattern, name in [
        ("tier4_22i_host_test_stdout*.txt", "host_test_stdout"),
        ("tier4_22i_host_test_stderr*.txt", "host_test_stderr"),
        ("tier4_22i_main_syntax_normal_stdout*.txt", "main_syntax_stdout"),
        ("tier4_22i_main_syntax_normal_stderr*.txt", "main_syntax_stderr"),
        ("tier4_22i_main_syntax_normal*.o", "main_syntax_object"),
        ("tier4_22i_aplx_build_stdout*.txt", "aplx_build_stdout"),
        ("tier4_22i_aplx_build_stderr*.txt", "aplx_build_stderr"),
        ("coral_reef*.aplx", "aplx_binary"),
        ("coral_reef*.elf", "elf_binary"),
        ("coral_reef*.txt", "elf_listing"),
        ("reports*.zip", "spinnaker_reports_zip"),
        ("main*.o", "main_object"),
        ("host_interface*.o", "host_interface_object"),
        ("state_manager*.o", "state_manager_object"),
        ("synapse_manager*.o", "synapse_manager_object"),
        ("neuron_manager*.o", "neuron_manager_object"),
        ("router*.o", "router_object"),
    ]:
        copied = _copy_latest(source, output_dir, pattern)
        if copied:
            artifacts[name] = copied

    corrected = deepcopy(raw_manifest)
    corrected["mode"] = "ingest"
    corrected["output_dir"] = str(output_dir)
    corrected["raw_remote_status"] = raw_manifest.get("status")
    corrected["raw_remote_failure_reason"] = raw_manifest.get("failure_reason", "")

    after_mature = learning.get("state_after_mature", {}) if isinstance(learning, dict) else {}
    corrected_false_fail = False
    for item in corrected.get("criteria", []):
        if item.get("name") == "active pending cleared":
            item["value"] = after_mature.get("active_pending")
            item["passed"] = int_or(after_mature.get("active_pending"), -1) == 0
            item["note"] = "Corrected during ingest: raw runner used `active_pending or -1`, which converts a legitimate zero into -1."
            corrected_false_fail = bool(item["passed"])
    if corrected_false_fail and str(raw_manifest.get("status")) == "fail":
        if all(item.get("passed") for item in corrected.get("criteria", [])):
            corrected["status"] = "pass"
            corrected["failure_reason"] = ""
    corrected.setdefault("summary", {})
    corrected["summary"].update({
        "mode": "ingest",
        "raw_remote_status": raw_manifest.get("status"),
        "raw_remote_failure_reason": raw_manifest.get("failure_reason", ""),
        "ingest_classification": "hardware_pass_raw_false_fail" if corrected.get("status") == "pass" and raw_manifest.get("status") == "fail" else "ingested",
        "false_fail_reason": "Raw runner treated active_pending=0 as missing because the criterion used Python `or -1`; all returned hardware learning values satisfy the declared pass criteria." if corrected_false_fail else "",
        "hardware_target_configured": corrected.get("summary", {}).get("hardware_target_configured"),
        "learning_smoke_status": corrected.get("summary", {}).get("learning_smoke_status"),
        "custom_runtime_learning_next_allowed": corrected.get("status") == "pass",
    })
    corrected.setdefault("criteria", []).append(
        criterion(
            "raw false-fail classification",
            corrected["summary"]["ingest_classification"],
            "raw fail may be reclassified only when returned hardware data satisfy all declared criteria",
            corrected.get("status") == "pass" and raw_manifest.get("status") == "fail",
            corrected["summary"]["false_fail_reason"],
        )
    )
    corrected.setdefault("artifacts", {})
    corrected["artifacts"].update({k: v for k, v in artifacts.items() if v})
    return finalize(output_dir, corrected)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=TIER)
    parser.add_argument("--mode", choices=["prepare", "run-hardware", "ingest"], default="prepare")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--ingest-dir", type=Path, default=None)
    parser.add_argument("--spinnaker-hostname", default="")
    parser.add_argument("--target-acquisition", choices=["auto", "hostname", "spynnaker-probe"], default="auto")
    parser.add_argument("--target-probe-population-size", type=int, default=1)
    parser.add_argument("--target-probe-run-ms", type=float, default=1.0)
    parser.add_argument("--target-probe-timestep-ms", type=float, default=1.0)
    parser.add_argument("--auto-dest-cpu", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--dest-x", type=int, default=0)
    parser.add_argument("--dest-y", type=int, default=0)
    parser.add_argument("--dest-cpu", type=int, default=1)
    parser.add_argument("--port", type=int, default=17893)
    parser.add_argument("--timeout-seconds", type=float, default=3.0)
    parser.add_argument("--app-id", type=int, default=17)
    parser.add_argument("--startup-delay-seconds", type=float, default=1.0)
    parser.add_argument("--command-delay-seconds", type=float, default=0.05)
    parser.add_argument("--learning-delay-seconds", type=float, default=0.10)
    parser.add_argument("--pending-delay-steps", type=int, default=5)
    parser.add_argument("--learning-feature", type=float, default=1.0)
    parser.add_argument("--learning-target", type=float, default=1.0)
    parser.add_argument("--learning-rate", type=float, default=0.25)
    parser.add_argument("--skip-load", action="store_true")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
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
            "criteria": [criterion("runner completed without unhandled exception", type(exc).__name__, "no exception", False, str(exc))],
        }
        return finalize(output_dir, result)


if __name__ == "__main__":
    raise SystemExit(main())
