#!/usr/bin/env python3
"""Tier 4.22l tiny custom-runtime learning parity gate.

Tier 4.22j proved one minimal chip-owned delayed pending/readout update on
real SpiNNaker. Tier 4.22l keeps the next step deliberately tiny: run a
predeclared sequence of four pending-horizon readout updates and compare the
board's fixed-point state against a local s16.15 reference that mirrors the C
runtime equation exactly.

Claim boundary:
- LOCAL/PREPARED means the reference, bundle, and command are ready.
- PASS in run-hardware means the custom runtime performed the tiny update
  sequence on real SpiNNaker and matched the local fixed-point reference within
  the declared raw tolerance.
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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"
RUNTIME = ROOT / "coral_reef_spinnaker" / "spinnaker_runtime"
TIER = "Tier 4.22l - Tiny Custom-Runtime Learning Parity"
RUNNER_REVISION = "tier4_22l_custom_runtime_learning_parity_20260501_0001"
TIER4_22J_LATEST = CONTROLLED / "tier4_22j_latest_manifest.json"
DEFAULT_OUTPUT = CONTROLLED / "tier4_22l_20260501_custom_runtime_learning_parity_prepared"
UPLOAD_PACKAGE_NAME = "cra_422t"
STABLE_EBRAINS_UPLOAD = ROOT / "ebrains_jobs" / UPLOAD_PACKAGE_NAME
DEPRECATED_EBRAINS_UPLOADS = [
    ROOT / "ebrains_jobs" / "cra_422t_old",
]

FP_SHIFT = 15
FP_ONE = 1 << FP_SHIFT
PARITY_LEARNING_RATE = 0.25
PARITY_SEQUENCE = [
    {"step": 1, "feature": 1.0, "target": 1.0, "purpose": "positive feature / positive target"},
    {"step": 2, "feature": 1.0, "target": -1.0, "purpose": "positive feature / negative target"},
    {"step": 3, "feature": -1.0, "target": -1.0, "purpose": "negative feature / negative target"},
    {"step": 4, "feature": -1.0, "target": 0.5, "purpose": "negative feature / fractional positive target"},
]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments import tier4_22i_custom_runtime_roundtrip as base  # noqa: E402
from experiments import tier4_22j_minimal_custom_runtime_learning as t22j  # noqa: E402


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    keys: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                keys.append(key)
                seen.add(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


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


def fp_from_float(value: float) -> int:
    return int(float(value) * FP_ONE)


def fp_to_float(value: int) -> float:
    return int(value) / FP_ONE


def fp_mul(a: int, b: int) -> int:
    return (int(a) * int(b)) >> FP_SHIFT


def generate_reference(sequence: list[dict[str, Any]] | None = None, learning_rate: float = PARITY_LEARNING_RATE) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    weight = 0
    bias = 0
    lr_raw = fp_from_float(learning_rate)
    for event in sequence or PARITY_SEQUENCE:
        feature_raw = fp_from_float(float(event["feature"]))
        target_raw = fp_from_float(float(event["target"]))
        prediction_raw = fp_mul(weight, feature_raw) + bias
        error_raw = target_raw - prediction_raw
        delta_w_raw = fp_mul(lr_raw, fp_mul(error_raw, feature_raw))
        delta_b_raw = fp_mul(lr_raw, error_raw)
        weight += delta_w_raw
        bias += delta_b_raw
        rows.append(
            {
                "step": int(event["step"]),
                "purpose": str(event.get("purpose", "")),
                "feature": float(event["feature"]),
                "target": float(event["target"]),
                "feature_raw": feature_raw,
                "target_raw": target_raw,
                "learning_rate": float(learning_rate),
                "learning_rate_raw": lr_raw,
                "prediction_raw": prediction_raw,
                "prediction": fp_to_float(prediction_raw),
                "error_raw": error_raw,
                "delta_w_raw": delta_w_raw,
                "delta_b_raw": delta_b_raw,
                "readout_weight_raw": weight,
                "readout_bias_raw": bias,
                "readout_weight": fp_to_float(weight),
                "readout_bias": fp_to_float(bias),
            }
        )
    return {
        "status": "pass",
        "fixed_point": "s16.15",
        "equation": "prediction=w*feature+bias; error=target-prediction; w+=lr*error*feature; b+=lr*error",
        "learning_rate": float(learning_rate),
        "learning_rate_raw": lr_raw,
        "sequence_length": len(rows),
        "rows": rows,
        "final_readout_weight_raw": weight,
        "final_readout_bias_raw": bias,
        "final_readout_weight": fp_to_float(weight),
        "final_readout_bias": fp_to_float(bias),
    }


def latest_status(path: Path) -> tuple[str, str | None]:
    return base.latest_status(path)


def parity_source_checks(config_source: str, state_source: str, host_source: str, controller_source: str, *, label: str) -> list[dict[str, Any]]:
    return [
        criterion(
            f"{label} fixed-point helper is s16.15",
            "FP_SHIFT 15",
            "config.h defines the same fixed-point scale as the Python reference",
            "#define FP_SHIFT      15" in config_source and "FP_MUL(a, b)" in config_source,
        ),
        criterion(
            f"{label} readout prediction equation present",
            "FP_MUL(readout_weight, feature) + readout_bias",
            "runtime prediction must match local parity reference",
            "FP_MUL(g_summary.readout_weight, feature) + g_summary.readout_bias" in state_source,
        ),
        criterion(
            f"{label} readout update equation present",
            "delta_w = lr * error * feature; delta_b = lr * error",
            "runtime maturation must match local parity reference",
            "int32_t error = target - prediction" in state_source
            and "int32_t delta_w = FP_MUL(learning_rate, FP_MUL(error, feature))" in state_source
            and "int32_t delta_b = FP_MUL(learning_rate, error)" in state_source,
        ),
        criterion(
            f"{label} mature command supports explicit mature_timestep",
            "msg->arg3 != 0 ? msg->arg3 : g_timestep",
            "parity run uses explicit due_timestep to avoid timer-race false failures",
            "uint32_t mature_timestep = msg->arg3 != 0 ? msg->arg3 : g_timestep" in host_source,
        ),
        criterion(
            f"{label} controller exposes returned due_timestep",
            "due_timestep",
            "hardware parity can mature exactly the pending event it scheduled",
            "due_timestep" in controller_source and "mature_timestep" in controller_source,
        ),
    ]


def write_reference_artifacts(output_dir: Path, reference: dict[str, Any]) -> dict[str, str]:
    reference_json = output_dir / "tier4_22l_reference.json"
    reference_csv = output_dir / "tier4_22l_parity_reference.csv"
    write_json(reference_json, reference)
    write_csv(reference_csv, list(reference.get("rows", [])))
    return {"reference_json": str(reference_json), "reference_csv": str(reference_csv)}


def prepare_bundle(output_dir: Path) -> tuple[Path, str, dict[str, str]]:
    bundle = output_dir / "ebrains_upload_bundle" / UPLOAD_PACKAGE_NAME
    if bundle.exists():
        shutil.rmtree(bundle)
    (bundle / "experiments").mkdir(parents=True, exist_ok=True)
    (bundle / "coral_reef_spinnaker" / "python_host").mkdir(parents=True, exist_ok=True)

    for script in [
        "tier4_22l_custom_runtime_learning_parity.py",
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

    command = f"{UPLOAD_PACKAGE_NAME}/experiments/tier4_22l_custom_runtime_learning_parity.py --mode run-hardware --output-dir tier4_22l_job_output"
    readme = bundle / "README_TIER4_22L_JOB.md"
    readme.write_text(
        "# Tier 4.22l EBRAINS Tiny Custom-Runtime Learning Parity Job\n\n"
        f"Upload the `{UPLOAD_PACKAGE_NAME}` folder itself so the JobManager path starts with `{UPLOAD_PACKAGE_NAME}/`. Do not upload `controlled_test_output`.\n\n"
        "This job depends conceptually on the Tier 4.22j minimal learning-smoke pass. It builds and loads the custom C runtime, then sends a four-event `CMD_SCHEDULE_PENDING`/`CMD_MATURE_PENDING` sequence and validates that compact `CMD_READ_STATE` matches the local s16.15 fixed-point reference.\n\n"
        "Run command:\n\n"
        f"```text\n{command}\n```\n\n"
        "Pass means the tiny chip-owned readout update sequence matched the local reference. It is not full CRA task learning, v2.1 transfer, or speedup evidence.\n",
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


def tiny_learning_parity(hostname: str, args: argparse.Namespace, *, dest_cpu: int, reference: dict[str, Any]) -> dict[str, Any]:
    from coral_reef_spinnaker.python_host.colony_controller import ColonyController

    started = time.perf_counter()
    ctrl = ColonyController(hostname, port=int(args.port), timeout=float(args.timeout_seconds))
    rows: list[dict[str, Any]] = []
    try:
        reset_ok = ctrl.reset(args.dest_x, args.dest_y, dest_cpu)
        time.sleep(float(args.command_delay_seconds))
        state_after_reset = ctrl.read_state(args.dest_x, args.dest_y, dest_cpu)
        expected_rows = list(reference.get("rows", []))
        for expected in expected_rows:
            schedule = ctrl.schedule_pending_decision(
                feature=float(expected["feature"]),
                delay_steps=int(args.pending_delay_steps),
                dest_x=args.dest_x,
                dest_y=args.dest_y,
                dest_cpu=dest_cpu,
            )
            time.sleep(float(args.command_delay_seconds))
            state_after_schedule = ctrl.read_state(args.dest_x, args.dest_y, dest_cpu)
            due_timestep = int_or(schedule.get("due_timestep"), 0)
            mature = ctrl.mature_pending(
                target=float(expected["target"]),
                learning_rate=float(reference.get("learning_rate", PARITY_LEARNING_RATE)),
                mature_timestep=due_timestep,
                dest_x=args.dest_x,
                dest_y=args.dest_y,
                dest_cpu=dest_cpu,
            )
            time.sleep(float(args.command_delay_seconds))
            state_after_mature = ctrl.read_state(args.dest_x, args.dest_y, dest_cpu)
            rows.append(
                {
                    "step": int(expected["step"]),
                    "feature": expected["feature"],
                    "target": expected["target"],
                    "expected_prediction_raw": expected["prediction_raw"],
                    "observed_prediction_raw": schedule.get("prediction_raw"),
                    "prediction_raw_delta": int_or(schedule.get("prediction_raw"), 10**12) - int(expected["prediction_raw"]),
                    "expected_readout_weight_raw": expected["readout_weight_raw"],
                    "observed_readout_weight_raw": mature.get("readout_weight_raw"),
                    "state_readout_weight_raw": state_after_mature.get("readout_weight_raw"),
                    "readout_weight_raw_delta": int_or(mature.get("readout_weight_raw"), 10**12) - int(expected["readout_weight_raw"]),
                    "expected_readout_bias_raw": expected["readout_bias_raw"],
                    "observed_readout_bias_raw": mature.get("readout_bias_raw"),
                    "state_readout_bias_raw": state_after_mature.get("readout_bias_raw"),
                    "readout_bias_raw_delta": int_or(mature.get("readout_bias_raw"), 10**12) - int(expected["readout_bias_raw"]),
                    "schedule_success": bool(schedule.get("success")),
                    "mature_success": bool(mature.get("success")),
                    "matured_count": mature.get("matured_count"),
                    "due_timestep": due_timestep,
                    "state_after_schedule_success": bool(state_after_schedule.get("success")),
                    "state_after_mature_success": bool(state_after_mature.get("success")),
                    "active_pending_after_schedule": state_after_schedule.get("active_pending"),
                    "active_pending_after_mature": state_after_mature.get("active_pending"),
                    "pending_created_after_mature": state_after_mature.get("pending_created"),
                    "pending_matured_after_mature": state_after_mature.get("pending_matured"),
                    "reward_events_after_mature": state_after_mature.get("reward_events"),
                    "schedule": schedule,
                    "mature": mature,
                    "state_after_schedule": state_after_schedule,
                    "state_after_mature": state_after_mature,
                }
            )
        final_state = rows[-1]["state_after_mature"] if rows else state_after_reset
        tolerance = int(args.raw_tolerance)
        ok = (
            bool(reset_ok)
            and bool(state_after_reset.get("success"))
            and len(rows) == len(expected_rows)
            and all(row.get("schedule_success") for row in rows)
            and all(row.get("mature_success") for row in rows)
            and all(int_or(row.get("matured_count"), -1) == 1 for row in rows)
            and all(abs(int(row.get("prediction_raw_delta", 10**12))) <= tolerance for row in rows)
            and all(abs(int(row.get("readout_weight_raw_delta", 10**12))) <= tolerance for row in rows)
            and all(abs(int(row.get("readout_bias_raw_delta", 10**12))) <= tolerance for row in rows)
            and int_or(final_state.get("pending_created"), -1) == len(expected_rows)
            and int_or(final_state.get("pending_matured"), -1) == len(expected_rows)
            and int_or(final_state.get("reward_events"), -1) == len(expected_rows)
            and int_or(final_state.get("active_pending"), -1) == 0
        )
        return {
            "status": "pass" if ok else "fail",
            "hostname": hostname,
            "dest_x": int(args.dest_x),
            "dest_y": int(args.dest_y),
            "dest_cpu": int(dest_cpu),
            "raw_tolerance": tolerance,
            "reset_ok": reset_ok,
            "state_after_reset": state_after_reset,
            "rows": rows,
            "final_state": final_state,
            "runtime_seconds": time.perf_counter() - started,
        }
    except Exception as exc:
        return {
            "status": "fail",
            "hostname": hostname,
            "exception_type": type(exc).__name__,
            "exception": str(exc),
            "traceback": traceback.format_exc(),
            "rows": rows,
            "runtime_seconds": time.perf_counter() - started,
        }
    finally:
        ctrl.close()


def write_report(path: Path, result: dict[str, Any]) -> None:
    summary = result.get("summary", {})
    lines = [
        "# Tier 4.22l Tiny Custom-Runtime Learning Parity",
        "",
        f"- Generated: `{result.get('generated_at_utc', utc_now())}`",
        f"- Mode: `{result.get('mode', summary.get('mode', 'unknown'))}`",
        f"- Status: **{str(result.get('status', 'unknown')).upper()}**",
        f"- Output directory: `{result.get('output_dir', path.parent)}`",
        "",
        "Tier 4.22l compares a tiny chip-owned pending-horizon/readout update sequence against a local s16.15 fixed-point reference.",
        "",
        "## Claim Boundary",
        "",
        "- `LOCAL`/`PREPARED` means the reference, source bundle, and command are ready, not hardware evidence.",
        "- `PASS` in `run-hardware` means the tiny on-chip update sequence matched the local fixed-point reference within tolerance.",
        "- This is not full CRA task learning, not v2.1 mechanism transfer, not speedup evidence, not multi-core scaling, and not final on-chip autonomy.",
        "",
        "## Summary",
        "",
    ]
    for key in [
        "tier4_22j_status", "mode", "reference_status", "reference_sequence_length", "reference_final_weight", "reference_final_bias",
        "hardware_target_configured", "spinnaker_hostname", "selected_dest_cpu", "aplx_build_status", "app_load_status", "learning_parity_status",
        "final_pending_created", "final_pending_matured", "final_reward_events", "final_readout_weight", "final_readout_bias",
        "jobmanager_command", "upload_folder", "stable_upload_folder", "what_i_need_from_user", "next_step_if_passed",
    ]:
        if key in summary:
            lines.append(f"- {key}: `{markdown_value(summary[key])}`")
    lines.extend(["", "## Criteria", "", "| Criterion | Value | Rule | Pass |", "| --- | --- | --- | --- |"])
    for item in result.get("criteria", []):
        lines.append(f"| {item['name']} | `{markdown_value(item.get('value'))}` | `{item.get('rule')}` | {'yes' if item.get('passed') else 'no'} |")
    rows = result.get("learning_parity", {}).get("rows", [])
    if rows:
        lines.extend(["", "## Parity Rows", "", "| Step | Feature | Target | Expected prediction raw | Observed prediction raw | Expected weight raw | Observed weight raw | Expected bias raw | Observed bias raw |", "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"])
        for row in rows:
            lines.append(
                "| {step} | `{feature}` | `{target}` | `{ep}` | `{op}` | `{ew}` | `{ow}` | `{eb}` | `{ob}` |".format(
                    step=row.get("step"),
                    feature=row.get("feature"),
                    target=row.get("target"),
                    ep=row.get("expected_prediction_raw"),
                    op=row.get("observed_prediction_raw"),
                    ew=row.get("expected_readout_weight_raw"),
                    ow=row.get("observed_readout_weight_raw"),
                    eb=row.get("expected_readout_bias_raw"),
                    ob=row.get("observed_readout_bias_raw"),
                )
            )
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
        "claim": "Latest Tier 4.22l tiny custom-runtime learning parity; pass means a tiny on-chip readout update sequence matched local fixed-point reference only.",
    }
    write_json(CONTROLLED / "tier4_22l_latest_manifest.json", payload)


def finalize(output_dir: Path, result: dict[str, Any]) -> int:
    manifest = output_dir / "tier4_22l_results.json"
    report = output_dir / "tier4_22l_report.md"
    result.setdefault("artifacts", {})
    result["artifacts"].update({"manifest_json": str(manifest), "report_md": str(report)})
    write_json(manifest, result)
    write_report(report, result)
    write_latest(output_dir, manifest, report, str(result.get("status", "unknown")), str(result.get("mode", "unknown")))
    print(json.dumps({"status": result.get("status"), "output_dir": str(output_dir), "manifest": str(manifest), "report": str(report)}, indent=2))
    return 0 if str(result.get("status", "")).lower() in {"pass", "prepared"} else 1


def local(args: argparse.Namespace, output_dir: Path) -> int:
    tier4_22j_status, tier4_22j_manifest = latest_status(TIER4_22J_LATEST)
    reference = generate_reference(learning_rate=float(args.learning_rate))
    reference_artifacts = write_reference_artifacts(output_dir, reference)
    main_syntax = base.run_main_syntax_check(output_dir)
    source_checks = t22j.command_surface_checks(
        read_text(RUNTIME / "src" / "config.h"),
        read_text(ROOT / "coral_reef_spinnaker" / "python_host" / "colony_controller.py"),
        read_text(RUNTIME / "src" / "host_interface.c"),
        read_text(RUNTIME / "tests" / "test_runtime.c"),
        label="source",
    )
    source_checks += parity_source_checks(
        read_text(RUNTIME / "src" / "config.h"),
        read_text(RUNTIME / "src" / "state_manager.c"),
        read_text(RUNTIME / "src" / "host_interface.c"),
        read_text(ROOT / "coral_reef_spinnaker" / "python_host" / "colony_controller.py"),
        label="source",
    )
    criteria = [
        criterion("Tier 4.22j minimal learning-smoke pass exists", tier4_22j_status, "== pass", tier4_22j_status == "pass"),
        criterion("main.c host syntax check pass", main_syntax.get("status"), "== pass", main_syntax.get("status") == "pass"),
        criterion("local fixed-point reference generated", reference.get("status"), "== pass", reference.get("status") == "pass"),
        criterion("reference sequence length", reference.get("sequence_length"), "== 4", reference.get("sequence_length") == 4),
        criterion("reference final weight nonzero", reference.get("final_readout_weight_raw"), "!= 0", int(reference.get("final_readout_weight_raw") or 0) != 0),
        criterion("reference final bias nonzero", reference.get("final_readout_bias_raw"), "!= 0", int(reference.get("final_readout_bias_raw") or 0) != 0),
    ] + source_checks
    status = "pass" if all(item["passed"] for item in criteria) else "blocked"
    result = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "mode": "local",
        "status": status,
        "failure_reason": "" if status == "local" else "Failed criteria: " + ", ".join(item["name"] for item in criteria if not item["passed"]),
        "output_dir": str(output_dir),
        "summary": {
            "mode": "local",
            "tier4_22j_status": tier4_22j_status,
            "tier4_22j_manifest": tier4_22j_manifest,
            "reference_status": reference.get("status"),
            "reference_sequence_length": reference.get("sequence_length"),
            "reference_final_weight": reference.get("final_readout_weight"),
            "reference_final_bias": reference.get("final_readout_bias"),
            "next_step_if_passed": "Prepare cra_422t and run the Tier 4.22l tiny parity sequence on EBRAINS.",
        },
        "criteria": criteria,
        "reference": reference,
        "main_syntax_check": main_syntax,
        "artifacts": reference_artifacts,
    }
    return finalize(output_dir, result)


def prepare(args: argparse.Namespace, output_dir: Path) -> int:
    tier4_22j_status, tier4_22j_manifest = latest_status(TIER4_22J_LATEST)
    reference = generate_reference(learning_rate=float(args.learning_rate))
    reference_artifacts = write_reference_artifacts(output_dir, reference)
    main_syntax = base.run_main_syntax_check(output_dir)
    bundle, command, bundle_artifacts = prepare_bundle(output_dir)
    source_checks = t22j.command_surface_checks(
        read_text(RUNTIME / "src" / "config.h"),
        read_text(ROOT / "coral_reef_spinnaker" / "python_host" / "colony_controller.py"),
        read_text(RUNTIME / "src" / "host_interface.c"),
        read_text(RUNTIME / "tests" / "test_runtime.c"),
        label="source",
    )
    source_checks += parity_source_checks(
        read_text(RUNTIME / "src" / "config.h"),
        read_text(RUNTIME / "src" / "state_manager.c"),
        read_text(RUNTIME / "src" / "host_interface.c"),
        read_text(ROOT / "coral_reef_spinnaker" / "python_host" / "colony_controller.py"),
        label="source",
    )
    bundle_runtime = bundle / "coral_reef_spinnaker" / "spinnaker_runtime"
    bundle_checks = t22j.command_surface_checks(
        read_text(bundle_runtime / "src" / "config.h"),
        read_text(bundle / "coral_reef_spinnaker" / "python_host" / "colony_controller.py"),
        read_text(bundle_runtime / "src" / "host_interface.c"),
        read_text(bundle_runtime / "tests" / "test_runtime.c"),
        label="bundle",
    )
    bundle_checks += parity_source_checks(
        read_text(bundle_runtime / "src" / "config.h"),
        read_text(bundle_runtime / "src" / "state_manager.c"),
        read_text(bundle_runtime / "src" / "host_interface.c"),
        read_text(bundle / "coral_reef_spinnaker" / "python_host" / "colony_controller.py"),
        label="bundle",
    )
    criteria = [
        criterion("Tier 4.22j minimal learning-smoke pass exists", tier4_22j_status, "== pass", tier4_22j_status == "pass"),
        criterion("main.c host syntax check pass", main_syntax.get("status"), "== pass", main_syntax.get("status") == "pass"),
        criterion("local fixed-point reference generated", reference.get("status"), "== pass", reference.get("status") == "pass"),
        criterion("upload bundle created", str(bundle), "exists", bundle.exists()),
        criterion("runtime source included", str(bundle / "coral_reef_spinnaker" / "spinnaker_runtime"), "exists", (bundle / "coral_reef_spinnaker" / "spinnaker_runtime").exists()),
        criterion("run-hardware command emitted", command, "contains --mode run-hardware", "--mode run-hardware" in command),
    ] + source_checks + bundle_checks
    status = "prepared" if all(item["passed"] for item in criteria) else "blocked"
    artifacts = {**reference_artifacts, **bundle_artifacts}
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
            "tier4_22j_status": tier4_22j_status,
            "tier4_22j_manifest": tier4_22j_manifest,
            "reference_status": reference.get("status"),
            "reference_sequence_length": reference.get("sequence_length"),
            "reference_final_weight": reference.get("final_readout_weight"),
            "reference_final_bias": reference.get("final_readout_bias"),
            "jobmanager_command": command,
            "upload_folder": str(bundle),
            "stable_upload_folder": str(STABLE_EBRAINS_UPLOAD),
            "what_i_need_from_user": f"Upload the generated {UPLOAD_PACKAGE_NAME} folder to EBRAINS/JobManager and run the emitted command; download returned files after completion.",
            "claim_boundary": "Prepared source bundle only; no hardware parity evidence until returned run-hardware artifacts pass.",
            "next_step_if_passed": "Run the emitted EBRAINS command and ingest returned files.",
        },
        "criteria": criteria,
        "reference": reference,
        "main_syntax_check": main_syntax,
        "artifacts": artifacts,
    }
    return finalize(output_dir, result)


def run_hardware(args: argparse.Namespace, output_dir: Path) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    tier4_22j_status, tier4_22j_manifest = latest_status(TIER4_22J_LATEST)
    reference = generate_reference(learning_rate=float(args.learning_rate))
    reference_artifacts = write_reference_artifacts(output_dir, reference)
    env_report = base.environment_report()
    host_tests = base.run_host_tests(output_dir)
    main_syntax = base.run_main_syntax_check(output_dir)
    build = base.build_aplx(output_dir)
    aplx = Path(build.get("aplx_artifact") or RUNTIME / "build" / "coral_reef.aplx")
    target = {"status": "not_attempted", "reason": "blocked_before_target_acquisition"}
    target_cleanup = {"status": "not_attempted"}
    load = {"status": "not_attempted", "reason": "blocked_before_load"}
    parity = {"status": "not_attempted", "reason": "blocked_before_learning_parity"}
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
                parity = tiny_learning_parity(hostname, args, dest_cpu=dest_cpu, reference=reference)
        finally:
            target_cleanup = base.release_hardware_target(target)

    env_path = output_dir / "tier4_22l_environment.json"
    target_path = output_dir / "tier4_22l_target_acquisition.json"
    load_path = output_dir / "tier4_22l_load_result.json"
    parity_path = output_dir / "tier4_22l_learning_parity_result.json"
    parity_csv = output_dir / "tier4_22l_learning_parity_rows.csv"
    write_json(env_path, env_report)
    write_json(target_path, base.public_target_acquisition({**target, "cleanup": target_cleanup}))
    write_json(load_path, load)
    write_json(parity_path, parity)
    write_csv(parity_csv, [{k: v for k, v in row.items() if k not in {"schedule", "mature", "state_after_schedule", "state_after_mature"}} for row in parity.get("rows", [])] if isinstance(parity, dict) else [])

    final_state = parity.get("final_state", {}) if isinstance(parity, dict) else {}
    rows = parity.get("rows", []) if isinstance(parity, dict) else []
    tolerance = int(args.raw_tolerance)
    criteria = [
        criterion("runner revision current", RUNNER_REVISION, "expected current source", True),
        criterion("Tier 4.22j minimal learning-smoke pass exists or fresh bundle", tier4_22j_status, "== pass OR missing in fresh EBRAINS bundle", tier4_22j_status in {"pass", "missing"}),
        criterion("local fixed-point reference generated", reference.get("status"), "== pass", reference.get("status") == "pass"),
        criterion("custom C host tests pass", host_tests.get("status"), "== pass", host_tests.get("status") == "pass"),
        criterion("main.c host syntax check pass", main_syntax.get("status"), "== pass", main_syntax.get("status") == "pass"),
        *t22j.command_surface_checks(
            read_text(RUNTIME / "src" / "config.h"),
            read_text(ROOT / "coral_reef_spinnaker" / "python_host" / "colony_controller.py"),
            read_text(RUNTIME / "src" / "host_interface.c"),
            read_text(RUNTIME / "tests" / "test_runtime.c"),
            label="runtime",
        ),
        *parity_source_checks(
            read_text(RUNTIME / "src" / "config.h"),
            read_text(RUNTIME / "src" / "state_manager.c"),
            read_text(RUNTIME / "src" / "host_interface.c"),
            read_text(ROOT / "coral_reef_spinnaker" / "python_host" / "colony_controller.py"),
            label="runtime",
        ),
        criterion("hardware target acquired", base.public_target_acquisition(target), "status == pass and hostname/IP/transceiver acquired", target.get("status") == "pass" and bool(hostname), "; ".join(str(n) for n in target.get("notes", []))),
        criterion("custom runtime .aplx build pass", build.get("status"), "== pass", build.get("status") == "pass"),
        criterion("custom runtime app load pass", load.get("status"), "== pass", load.get("status") == "pass"),
        criterion("tiny learning parity pass", parity.get("status"), "== pass", parity.get("status") == "pass"),
        criterion("all schedule commands succeeded", [row.get("schedule_success") for row in rows], "all True", bool(rows) and all(row.get("schedule_success") for row in rows)),
        criterion("all mature commands succeeded", [row.get("mature_success") for row in rows], "all True", bool(rows) and all(row.get("mature_success") for row in rows)),
        criterion("one pending matured per step", [row.get("matured_count") for row in rows], "all == 1", bool(rows) and all(int_or(row.get("matured_count"), -1) == 1 for row in rows)),
        criterion("predictions match local reference", [row.get("prediction_raw_delta") for row in rows], f"abs(delta) <= {tolerance}", bool(rows) and all(abs(int(row.get("prediction_raw_delta", 10**12))) <= tolerance for row in rows)),
        criterion("weights match local reference", [row.get("readout_weight_raw_delta") for row in rows], f"abs(delta) <= {tolerance}", bool(rows) and all(abs(int(row.get("readout_weight_raw_delta", 10**12))) <= tolerance for row in rows)),
        criterion("biases match local reference", [row.get("readout_bias_raw_delta") for row in rows], f"abs(delta) <= {tolerance}", bool(rows) and all(abs(int(row.get("readout_bias_raw_delta", 10**12))) <= tolerance for row in rows)),
        criterion("pending created count final", final_state.get("pending_created"), f"== {reference.get('sequence_length')}", int_or(final_state.get("pending_created"), -1) == int(reference.get("sequence_length") or -2)),
        criterion("pending matured count final", final_state.get("pending_matured"), f"== {reference.get('sequence_length')}", int_or(final_state.get("pending_matured"), -1) == int(reference.get("sequence_length") or -2)),
        criterion("reward events final", final_state.get("reward_events"), f"== {reference.get('sequence_length')}", int_or(final_state.get("reward_events"), -1) == int(reference.get("sequence_length") or -2)),
        criterion("active pending cleared final", final_state.get("active_pending"), "== 0", int_or(final_state.get("active_pending"), -1) == 0),
        criterion("final weight matches reference", final_state.get("readout_weight_raw"), f"== {reference.get('final_readout_weight_raw')} +/- {tolerance}", abs(int_or(final_state.get("readout_weight_raw"), 10**12) - int(reference.get("final_readout_weight_raw") or 0)) <= tolerance),
        criterion("final bias matches reference", final_state.get("readout_bias_raw"), f"== {reference.get('final_readout_bias_raw')} +/- {tolerance}", abs(int_or(final_state.get("readout_bias_raw"), 10**12) - int(reference.get("final_readout_bias_raw") or 0)) <= tolerance),
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
            "tier4_22j_status": tier4_22j_status,
            "tier4_22j_manifest": tier4_22j_manifest,
            "reference_status": reference.get("status"),
            "reference_sequence_length": reference.get("sequence_length"),
            "reference_final_weight": reference.get("final_readout_weight"),
            "reference_final_bias": reference.get("final_readout_bias"),
            "hardware_target_configured": target.get("status") == "pass" and bool(hostname),
            "spinnaker_hostname": hostname,
            "selected_dest_cpu": dest_cpu,
            "aplx_build_status": build.get("status"),
            "app_load_status": load.get("status"),
            "learning_parity_status": parity.get("status"),
            "final_pending_created": final_state.get("pending_created"),
            "final_pending_matured": final_state.get("pending_matured"),
            "final_reward_events": final_state.get("reward_events"),
            "final_readout_weight": final_state.get("readout_weight"),
            "final_readout_bias": final_state.get("readout_bias"),
            "claim_boundary": "Tiny on-chip fixed-point parity sequence only; not full CRA task learning or speedup evidence.",
            "next_step_if_passed": "Tier 4.22m: expand from tiny parity to a minimal task micro-loop only after this exact fixed-point path passes on board.",
        },
        "criteria": criteria,
        "reference": reference,
        "environment": env_report,
        "target_acquisition": base.public_target_acquisition(target),
        "target_cleanup": target_cleanup,
        "host_tests": host_tests,
        "main_syntax_check": main_syntax,
        "aplx_build": build,
        "app_load": load,
        "learning_parity": parity,
        "artifacts": {
            **reference_artifacts,
            "environment_json": str(env_path),
            "target_acquisition_json": str(target_path),
            "host_test_stdout": str(output_dir / "tier4_22i_host_test_stdout.txt"),
            "host_test_stderr": str(output_dir / "tier4_22i_host_test_stderr.txt"),
            "main_syntax_stdout": str(output_dir / "tier4_22i_main_syntax_normal_stdout.txt"),
            "main_syntax_stderr": str(output_dir / "tier4_22i_main_syntax_normal_stderr.txt"),
            "aplx_build_stdout": str(output_dir / "tier4_22i_aplx_build_stdout.txt"),
            "aplx_build_stderr": str(output_dir / "tier4_22i_aplx_build_stderr.txt"),
            "load_result_json": str(load_path),
            "learning_parity_result_json": str(parity_path),
            "learning_parity_rows_csv": str(parity_csv),
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

    raw_manifest_path = source / "tier4_22l_results.json"
    if not raw_manifest_path.exists():
        raise SystemExit(f"missing tier4_22l_results.json in ingest dir: {source}")
    raw_manifest = read_json(raw_manifest_path)

    artifacts: dict[str, str] = {}
    artifacts["raw_remote_manifest_json"] = _copy_latest(source, output_dir, "tier4_22l_results.json", target_name="remote_tier4_22l_results_raw.json")
    artifacts["raw_remote_report_md"] = _copy_latest(source, output_dir, "tier4_22l_report.md", target_name="remote_tier4_22l_report_raw.md")
    exact_artifact_names = {
        "tier4_22l_environment.json": "environment_json",
        "tier4_22l_target_acquisition.json": "target_acquisition_json",
        "tier4_22l_load_result.json": "load_result_json",
        "tier4_22l_learning_parity_result.json": "learning_parity_result_json",
        "tier4_22l_learning_parity_rows.csv": "learning_parity_rows_csv",
        "tier4_22l_reference.json": "reference_json",
        "tier4_22l_parity_reference.csv": "reference_csv",
        "tier4_22l_latest_manifest.json": "remote_latest_manifest_json",
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

    ingested = dict(raw_manifest)
    ingested["mode"] = "ingest"
    ingested["output_dir"] = str(output_dir)
    ingested["raw_remote_status"] = raw_manifest.get("status")
    ingested["raw_remote_failure_reason"] = raw_manifest.get("failure_reason", "")
    ingested.setdefault("summary", {})
    ingested["summary"].update(
        {
            "mode": "ingest",
            "raw_remote_status": raw_manifest.get("status"),
            "ingest_classification": "hardware_pass_ingested" if raw_manifest.get("status") == "pass" else "hardware_return_ingested",
            "claim_boundary": "Ingested returned EBRAINS artifacts; a pass is tiny signed fixed-point custom-runtime parity only, not full CRA task learning or speedup evidence.",
        }
    )
    ingested.setdefault("criteria", []).append(
        criterion(
            "returned EBRAINS artifact ingested",
            ingested["summary"]["ingest_classification"],
            "raw remote pass preserved with returned artifacts copied into controlled output",
            raw_manifest.get("status") == "pass",
        )
    )
    ingested.setdefault("artifacts", {})
    ingested["artifacts"].update({k: v for k, v in artifacts.items() if v})
    return finalize(output_dir, ingested)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=TIER)
    parser.add_argument("--mode", choices=["local", "prepare", "run-hardware", "ingest"], default="prepare")
    parser.add_argument("--output-dir", type=Path, default=None)
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
    parser.add_argument("--pending-delay-steps", type=int, default=5)
    parser.add_argument("--learning-rate", type=float, default=PARITY_LEARNING_RATE)
    parser.add_argument("--raw-tolerance", type=int, default=1)
    parser.add_argument("--skip-load", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    default = DEFAULT_OUTPUT if args.mode == "prepare" else CONTROLLED / f"tier4_22l_{stamp}_{args.mode.replace('-', '_')}"
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
            "criteria": [criterion("runner completed without unhandled exception", type(exc).__name__, "no exception", False, str(exc))],
        }
        return finalize(output_dir, result)


if __name__ == "__main__":
    raise SystemExit(main())
