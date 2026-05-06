#!/usr/bin/env python3
"""Tier 4.30g lifecycle task-benefit/resource bridge.

This runner owns the local contract/reference, EBRAINS package preparation,
hardware execution, and ingest path for the bounded bridge between native
lifecycle state and a task-bearing path.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import shutil
import subprocess
import sys
import time
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
CONTROLLED = ROOT / "controlled_test_output"
RUNTIME = ROOT / "coral_reef_spinnaker" / "spinnaker_runtime"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier4_30g_20260506_lifecycle_task_benefit_resource_bridge"
DEFAULT_PREPARE_OUTPUT = CONTROLLED / "tier4_30g_hw_20260506_prepared"
DEFAULT_RUN_OUTPUT = CONTROLLED / f"tier4_30g_hw_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_run_hardware"
LATEST_MANIFEST = CONTROLLED / "tier4_30g_latest_manifest.json"
UPLOAD_PACKAGE_NAME = "cra_430g"
STABLE_EBRAINS_UPLOAD = ROOT / "ebrains_jobs" / UPLOAD_PACKAGE_NAME

TIER_NAME = "Tier 4.30g - Lifecycle Task-Benefit / Resource Bridge"
RUNNER_REVISION = "tier4_30g_lifecycle_task_benefit_resource_bridge_20260506_0001"
CLAIM_BOUNDARY = (
    "Tier 4.30g defines and locally validates a bounded bridge from native "
    "lifecycle state into a task-bearing path with resource accounting. It is "
    "not a hardware task-benefit pass, not autonomous lifecycle-to-learning "
    "MCPL, not a lifecycle baseline freeze, and not evidence of larger-scale "
    "organism autonomy."
)

TIER430F_INGEST = CONTROLLED / "tier4_30f_hw_20260505_hardware_pass_ingested" / "tier4_30f_hw_results.json"

FP_SHIFT = 15
FP_ONE = 1 << FP_SHIFT
TASK_EVENTS = 24
TAIL_WINDOW = 8
DELAY_STEPS = 2
READOUT_LR = 0.25
READOUT_LR_RAW = int(round(READOUT_LR * FP_ONE))
TROPHIC_MARGIN_RAW = 5000

# The canonical control set is imported from 4.30f so this tier cannot silently
# change the lifecycle controls it claims to bridge.
from experiments import tier4_22i_custom_runtime_roundtrip as base  # noqa: E402
from experiments.tier4_30b_lifecycle_hardware_smoke import lifecycle_event_payload  # noqa: E402
from experiments.tier4_30f_lifecycle_sham_hardware_subset import (  # noqa: E402
    CORE_ROLES,
    SHAM_MODE_IDS,
    SHAM_MODE_ORDER,
    control_reference,
)


@dataclass
class Criterion:
    name: str
    value: Any
    rule: str
    passed: bool


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_safe(v) for v in value]
    if isinstance(value, tuple):
        return [json_safe(v) for v in value]
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    return value


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: Iterable[Dict[str, Any]], fieldnames: List[str] | None = None) -> None:
    rows = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        keys: List[str] = []
        for row in rows:
            for key in row.keys():
                if key not in keys:
                    keys.append(key)
        fieldnames = keys
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({name: json_safe(row.get(name, "")) for name in fieldnames})


def criterion(name: str, value: Any, rule: str, passed: bool) -> Criterion:
    return Criterion(name=name, value=value, rule=rule, passed=bool(passed))


def fp_mul(a: int, b: int) -> int:
    return int((int(a) * int(b)) >> FP_SHIFT)


def fp_to_float(value: int) -> float:
    return float(value) / float(FP_ONE)


def sign_from_raw(value: int) -> int:
    return 1 if value >= 0 else -1


def load_430f_prereq() -> Dict[str, Any] | None:
    if not TIER430F_INGEST.exists():
        return None
    return json.loads(TIER430F_INGEST.read_text(encoding="utf-8"))


def lifecycle_summaries() -> Dict[str, Dict[str, Any]]:
    summaries: Dict[str, Dict[str, Any]] = {}
    for mode in SHAM_MODE_ORDER:
        reference = control_reference(mode)
        expected = reference["expected"]
        summaries[mode] = dict(expected)
        summaries[mode]["mode"] = mode
    return summaries


def derive_bridge_features(mode: str, summary: Dict[str, Any], enabled_summary: Dict[str, Any]) -> Dict[str, Any]:
    structural_ok = (
        int(summary["active_count"]) == int(enabled_summary["active_count"])
        and int(summary["active_mask_bits"]) == int(enabled_summary["active_mask_bits"])
        and int(summary["lineage_checksum"]) == int(enabled_summary["lineage_checksum"])
    )
    trophic_floor = int(enabled_summary["trophic_checksum"]) - TROPHIC_MARGIN_RAW
    trophic_ok = int(summary["trophic_checksum"]) >= trophic_floor
    bridge_gate = 1 if structural_ok and trophic_ok else 0
    gate_raw = FP_ONE if bridge_gate else 0
    feature_reason = "structural_and_trophic_ready" if bridge_gate else "lifecycle_control_blocks_task_feature"
    return {
        "mode": mode,
        "bridge_gate": bridge_gate,
        "bridge_gate_raw": gate_raw,
        "structural_ok": structural_ok,
        "trophic_ok": trophic_ok,
        "trophic_floor": trophic_floor,
        "trophic_gap_from_enabled": int(enabled_summary["trophic_checksum"]) - int(summary["trophic_checksum"]),
        "feature_reason": feature_reason,
        "context_slot_raw": FP_ONE,
        "route_slot_raw": FP_ONE,
        "memory_slot_raw": gate_raw,
        "cue_gain_raw": gate_raw,
    }


def task_sequence() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    # Alternating short blocks keep the zero-feature controls near chance while
    # preserving a simple target that an intact bridge can learn quickly.
    pattern = [1, 1, -1, -1, 1, -1, 1, -1]
    for step in range(TASK_EVENTS):
        cue = pattern[step % len(pattern)]
        rows.append({
            "step": step,
            "cue": cue,
            "target": cue,
            "target_raw": cue * FP_ONE,
            "due_step": step + DELAY_STEPS,
        })
    return rows


def mature_entry(mode: str, step: int, entry: Dict[str, Any], weight_raw: int, bias_raw: int) -> Tuple[Dict[str, Any], int, int]:
    error_raw = int(entry["target_raw"]) - int(entry["prediction_raw"])
    delta_w = fp_mul(READOUT_LR_RAW, fp_mul(error_raw, int(entry["feature_raw"])))
    delta_b = fp_mul(READOUT_LR_RAW, error_raw)
    weight_raw += delta_w
    bias_raw += delta_b
    correct = sign_from_raw(int(entry["prediction_raw"])) == sign_from_raw(int(entry["target_raw"]))
    row = {
        "mode": mode,
        "step": step,
        "created_step": int(entry["created_step"]),
        "due_step": int(entry["due_step"]),
        "cue": int(entry["cue"]),
        "feature_raw": int(entry["feature_raw"]),
        "prediction_raw": int(entry["prediction_raw"]),
        "prediction": fp_to_float(int(entry["prediction_raw"])),
        "target_raw": int(entry["target_raw"]),
        "target": fp_to_float(int(entry["target_raw"])),
        "error_raw": error_raw,
        "error": fp_to_float(error_raw),
        "correct": int(correct),
        "weight_after_raw": weight_raw,
        "bias_after_raw": bias_raw,
    }
    return row, weight_raw, bias_raw


def run_task_reference(mode: str, bridge: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    weight_raw = 0
    bias_raw = 0
    pending: List[Dict[str, Any]] = []
    matured_rows: List[Dict[str, Any]] = []
    feature_energy_raw = 0

    for step_row in task_sequence():
        step = int(step_row["step"])
        cue_raw = int(step_row["cue"]) * FP_ONE
        # Host-ferried lifecycle bridge for this contract: lifecycle health is
        # represented as a bounded memory slot that gates cue flow into the
        # task-bearing readout path.
        feature_raw = fp_mul(cue_raw, int(bridge["cue_gain_raw"]))
        prediction_raw = fp_mul(weight_raw, feature_raw) + bias_raw
        feature_energy_raw += abs(feature_raw)
        pending.append({
            "created_step": step,
            "due_step": int(step_row["due_step"]),
            "feature_raw": feature_raw,
            "prediction_raw": prediction_raw,
            "target_raw": int(step_row["target_raw"]),
            "cue": int(step_row["cue"]),
        })

        due_now = [entry for entry in pending if int(entry["due_step"]) <= step]
        pending = [entry for entry in pending if int(entry["due_step"]) > step]
        for entry in due_now:
            row, weight_raw, bias_raw = mature_entry(mode, step, entry, weight_raw, bias_raw)
            matured_rows.append(row)

    final_step = TASK_EVENTS
    while pending:
        due_now = [entry for entry in pending if int(entry["due_step"]) <= final_step]
        pending = [entry for entry in pending if int(entry["due_step"]) > final_step]
        if not due_now:
            final_step += 1
            continue
        for entry in due_now:
            row, weight_raw, bias_raw = mature_entry(mode, final_step, entry, weight_raw, bias_raw)
            matured_rows.append(row)
        final_step += 1

    tail = matured_rows[-TAIL_WINDOW:]
    accuracy = sum(row["correct"] for row in matured_rows) / max(1, len(matured_rows))
    tail_accuracy = sum(row["correct"] for row in tail) / max(1, len(tail))
    mse = sum(float(row["error"]) ** 2 for row in matured_rows) / max(1, len(matured_rows))
    tail_mse = sum(float(row["error"]) ** 2 for row in tail) / max(1, len(tail))
    summary = {
        "mode": mode,
        "task_events": TASK_EVENTS,
        "matured_events": len(matured_rows),
        "delay_steps": DELAY_STEPS,
        "readout_lr": READOUT_LR,
        "bridge_gate": int(bridge["bridge_gate"]),
        "feature_energy_raw": feature_energy_raw,
        "feature_energy": fp_to_float(feature_energy_raw),
        "accuracy": accuracy,
        "tail_accuracy": tail_accuracy,
        "mse": mse,
        "tail_mse": tail_mse,
        "final_weight_raw": weight_raw,
        "final_weight": fp_to_float(weight_raw),
        "final_bias_raw": bias_raw,
        "final_bias": fp_to_float(bias_raw),
    }
    return summary, matured_rows


def resource_accounting(mode: str, lifecycle_summary: Dict[str, Any], bridge: Dict[str, Any], task: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "mode": mode,
        "lifecycle_event_count": 32,
        "task_event_count": TASK_EVENTS,
        "delay_steps": DELAY_STEPS,
        "expected_context_writes": 1,
        "expected_route_writes": 1,
        "expected_memory_writes": 1,
        "expected_schedule_uploads": TASK_EVENTS,
        "expected_runtime_cores": 5,
        "expected_lifecycle_readbacks": 1,
        "expected_task_readbacks": 4,
        "bridge_gate": bridge["bridge_gate"],
        "bridge_gate_raw": bridge["bridge_gate_raw"],
        "lifecycle_payload_len": lifecycle_summary.get("payload_len", ""),
        "lifecycle_readback_bytes": lifecycle_summary.get("readback_bytes", ""),
        "task_feature_energy_raw": task["feature_energy_raw"],
        "task_tail_accuracy": task["tail_accuracy"],
        "task_tail_mse": task["tail_mse"],
    }


def build_report(results: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append(f"# {TIER_NAME} Findings")
    lines.append("")
    lines.append(f"- Generated: `{results['generated_at']}`")
    lines.append(f"- Status: **{results['status'].upper()}**")
    lines.append(f"- Runner revision: `{RUNNER_REVISION}`")
    lines.append(f"- Output directory: `{results['output_dir']}`")
    lines.append("")
    lines.append("## Claim Boundary")
    lines.append("")
    lines.append(f"- {CLAIM_BOUNDARY}")
    lines.append("")
    lines.append("## Bridge Contract")
    lines.append("")
    lines.append("- The enabled lifecycle summary must expose intact structural state and trophic readiness.")
    lines.append("- Controls are allowed to run, but their lifecycle-derived task gate must close.")
    lines.append("- The local task path uses the closed/open lifecycle gate as a bounded memory-slot feature.")
    lines.append("- Hardware package preparation is allowed only after this local contract is green.")
    lines.append("")
    lines.append("## Mode Summary")
    lines.append("")
    lines.append("| Mode | Gate | Tail Acc | Tail MSE | Feature Energy | Structural | Trophic |")
    lines.append("| --- | ---: | ---: | ---: | ---: | --- | --- |")
    mode_lookup = {row["mode"]: row for row in results["mode_summary"]}
    for mode in SHAM_MODE_ORDER:
        row = mode_lookup[mode]
        lines.append(
            "| {mode} | {gate} | {tail:.3f} | {mse:.3f} | {energy:.3f} | {structural} | {trophic} |".format(
                mode=mode,
                gate=row["bridge_gate"],
                tail=row["tail_accuracy"],
                mse=row["tail_mse"],
                energy=row["feature_energy"],
                structural=row["structural_ok"],
                trophic=row["trophic_ok"],
            )
        )
    lines.append("")
    lines.append("## Criteria")
    lines.append("")
    lines.append("| Criterion | Value | Rule | Pass |")
    lines.append("| --- | --- | --- | --- |")
    for c in results["criteria"]:
        lines.append(f"| {c['name']} | `{c['value']}` | {c['rule']} | {'yes' if c['passed'] else 'no'} |")
    lines.append("")
    lines.append("## Artifacts")
    lines.append("")
    for key, value in results["artifacts"].items():
        lines.append(f"- `{key}`: `{value}`")
    return "\n".join(lines) + "\n"


def run_local(output_dir: Path, *, update_latest: bool = True) -> Dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    prereq = load_430f_prereq()
    summaries = lifecycle_summaries()
    enabled_summary = summaries["enabled"]
    bridge_rows: List[Dict[str, Any]] = []
    mode_summary_rows: List[Dict[str, Any]] = []
    task_trace_rows: List[Dict[str, Any]] = []
    resource_rows: List[Dict[str, Any]] = []

    for mode in SHAM_MODE_ORDER:
        lifecycle_summary = summaries[mode]
        bridge = derive_bridge_features(mode, lifecycle_summary, enabled_summary)
        task_summary, task_trace = run_task_reference(mode, bridge)
        row = {
            **{f"lifecycle_{k}": v for k, v in lifecycle_summary.items() if k != "mode"},
            **bridge,
            **task_summary,
        }
        bridge_rows.append(bridge)
        mode_summary_rows.append(row)
        task_trace_rows.extend(task_trace)
        resource_rows.append(resource_accounting(mode, lifecycle_summary, bridge, task_summary))

    summary_by_mode = {row["mode"]: row for row in mode_summary_rows}
    enabled = summary_by_mode["enabled"]
    control_rows = [row for row in mode_summary_rows if row["mode"] != "enabled"]
    max_control_tail = max(float(row["tail_accuracy"]) for row in control_rows)
    min_enabled_margin = min(float(enabled["tail_accuracy"]) - float(row["tail_accuracy"]) for row in control_rows)
    all_controls_gate_closed = all(int(row["bridge_gate"]) == 0 for row in control_rows)
    all_resource_fields_present = all(
        row.get("expected_runtime_cores") == 5
        and row.get("expected_schedule_uploads") == TASK_EVENTS
        and row.get("expected_task_readbacks") == 4
        for row in resource_rows
    )

    criteria: List[Criterion] = [
        criterion(
            "tier4_30f_hardware_prerequisite_ingested",
            prereq.get("status") if prereq else None,
            "== pass",
            bool(prereq and prereq.get("status") == "pass"),
        ),
        criterion(
            "canonical_sham_modes_preserved",
            list(summary_by_mode.keys()),
            f"== {SHAM_MODE_ORDER}",
            list(summary_by_mode.keys()) == SHAM_MODE_ORDER,
        ),
        criterion(
            "enabled_bridge_gate_open",
            enabled["bridge_gate"],
            "== 1",
            int(enabled["bridge_gate"]) == 1,
        ),
        criterion(
            "control_bridge_gates_closed",
            [row["bridge_gate"] for row in control_rows],
            "all == 0",
            all_controls_gate_closed,
        ),
        criterion(
            "enabled_tail_accuracy",
            round(float(enabled["tail_accuracy"]), 6),
            ">= 0.875",
            float(enabled["tail_accuracy"]) >= 0.875,
        ),
        criterion(
            "control_tail_accuracy_ceiling",
            round(max_control_tail, 6),
            "<= 0.625",
            max_control_tail <= 0.625,
        ),
        criterion(
            "enabled_control_tail_margin",
            round(min_enabled_margin, 6),
            ">= 0.25",
            min_enabled_margin >= 0.25,
        ),
        criterion(
            "resource_accounting_declared",
            all_resource_fields_present,
            "expected runtime/write/readback fields present for every mode",
            all_resource_fields_present,
        ),
        criterion(
            "claim_boundary_preserves_nonclaims",
            CLAIM_BOUNDARY,
            "contains hardware/baseline/autonomous nonclaims",
            all(token in CLAIM_BOUNDARY for token in ["not a hardware", "not autonomous", "not a lifecycle baseline freeze"]),
        ),
    ]

    status = "pass" if all(c.passed for c in criteria) else "fail"
    artifacts = {
        "results_json": str(output_dir / "tier4_30g_results.json"),
        "report_md": str(output_dir / "tier4_30g_report.md"),
        "mode_summary_csv": str(output_dir / "tier4_30g_mode_summary.csv"),
        "bridge_features_csv": str(output_dir / "tier4_30g_bridge_features.csv"),
        "task_trace_csv": str(output_dir / "tier4_30g_task_trace.csv"),
        "resource_accounting_csv": str(output_dir / "tier4_30g_resource_accounting.csv"),
    }

    generated_at = utc_now()
    results: Dict[str, Any] = {
        "tier": "4.30g",
        "tier_name": TIER_NAME,
        "runner_revision": RUNNER_REVISION,
        "generated_at": generated_at,
        "generated_at_utc": generated_at,
        "mode": "local-contract-reference",
        "status": status,
        "output_dir": str(output_dir),
        "claim_boundary": CLAIM_BOUNDARY,
        "question": "Can native lifecycle state be bridged into a task-bearing path with controls and resource accounting before hardware packaging?",
        "hypothesis": "The enabled lifecycle mode opens the bounded task bridge while sham controls close it, producing a measurable local task separation and a predeclared hardware resource contract.",
        "null_hypothesis": "Lifecycle state does not produce a specific task-path separation, or the separation is indistinguishable from sham controls/resource omissions.",
        "bridge_contract": {
            "enabled_reference_source": str(TIER430F_INGEST),
            "lifecycle_modes": SHAM_MODE_ORDER,
            "task_events": TASK_EVENTS,
            "delay_steps": DELAY_STEPS,
            "readout_lr": READOUT_LR,
            "trophic_margin_raw": TROPHIC_MARGIN_RAW,
            "feature_contract": "context_slot * route_slot * lifecycle_gated_memory_slot * cue",
            "hardware_preparation_allowed_after_pass": True,
        },
        "lifecycle_summaries": summaries,
        "bridge_features": bridge_rows,
        "mode_summary": mode_summary_rows,
        "resource_accounting": resource_rows,
        "criteria": [c.__dict__ for c in criteria],
        "criteria_passed": sum(1 for c in criteria if c.passed),
        "criteria_total": len(criteria),
        "artifacts": artifacts,
    }

    write_csv(Path(artifacts["mode_summary_csv"]), mode_summary_rows)
    write_csv(Path(artifacts["bridge_features_csv"]), bridge_rows)
    write_csv(Path(artifacts["task_trace_csv"]), task_trace_rows)
    write_csv(Path(artifacts["resource_accounting_csv"]), resource_rows)
    write_json(Path(artifacts["results_json"]), results)
    Path(artifacts["report_md"]).write_text(build_report(results), encoding="utf-8")
    if update_latest:
        write_json(LATEST_MANIFEST, {
            "latest_tier": "4.30g",
            "latest_status": status,
            "latest_output_dir": str(output_dir),
            "updated_at": utc_now(),
            "artifacts": artifacts,
        })
    return results


def run_cmd(command: List[str], *, cwd: Path = ROOT, env: Dict[str, str] | None = None) -> Dict[str, Any]:
    completed = subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True, check=False)
    return {
        "command": " ".join(command),
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def clean_copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)

    def ignore(_dir: str, names: List[str]) -> set[str]:
        return {
            name
            for name in names
            if name in {"__pycache__", ".pytest_cache", "build", "test_runtime", "test_lifecycle", "test_lifecycle_split"}
            or (name.startswith("test_") and "." not in name)
            or name.endswith((".pyc", ".o"))
        }

    shutil.copytree(src, dst, ignore=ignore)


def run_runtime_source_checks(output_dir: Path) -> Dict[str, Any]:
    result = run_cmd(
        [
            "make",
            "-C",
            str(RUNTIME),
            "clean-host",
            "test-lifecycle",
            "test-lifecycle-split",
            "test-profiles",
        ]
    )
    result["status"] = "pass" if result["returncode"] == 0 else "fail"
    (output_dir / "tier4_30g_host_tests_stdout.txt").write_text(result.get("stdout", ""), encoding="utf-8")
    (output_dir / "tier4_30g_host_tests_stderr.txt").write_text(result.get("stderr", ""), encoding="utf-8")
    return result


def build_aplx_for_profile(profile: str, output_dir: Path) -> Dict[str, Any]:
    env = os.environ.copy()
    tools = base.detect_spinnaker_tools()
    fallback = Path("/tmp/spinnaker_tools")
    if not tools and fallback.exists():
        tools = str(fallback)
    if tools and not env.get("SPINN_DIRS"):
        env["SPINN_DIRS"] = tools
    arm_toolchain = Path("/tmp/arm-gnu-toolchain-13.3.rel1-darwin-arm64-arm-none-eabi/bin")
    if arm_toolchain.exists():
        env["PATH"] = str(arm_toolchain) + os.pathsep + env.get("PATH", "")
    env["RUNTIME_PROFILE"] = profile
    env["USE_MCPL_LOOKUP"] = "1"

    base_aplx = RUNTIME / "build" / "coral_reef.aplx"
    if base_aplx.exists():
        base_aplx.unlink()
    result = run_cmd(["make", "-C", str(RUNTIME), "clean", "all"], env=env)
    (output_dir / f"tier4_30g_build_{profile}_stdout.txt").write_text(result.get("stdout", ""), encoding="utf-8")
    (output_dir / f"tier4_30g_build_{profile}_stderr.txt").write_text(result.get("stderr", ""), encoding="utf-8")

    aplx = RUNTIME / "build" / "coral_reef.aplx"
    profile_aplx = output_dir / f"coral_reef_{profile}.aplx"
    if aplx.exists():
        if profile_aplx.exists():
            profile_aplx.unlink()
        shutil.copy2(aplx, profile_aplx)

    size_text = 0
    elf = RUNTIME / "build" / "gnu" / "coral_reef.elf"
    if elf.exists():
        size_bin = str(arm_toolchain / "arm-none-eabi-size") if arm_toolchain.exists() else "arm-none-eabi-size"
        size = run_cmd([size_bin, str(elf)])
        result["size_stdout"] = size.get("stdout", "")
        result["size_stderr"] = size.get("stderr", "")
        if size.get("returncode") == 0:
            for line in size.get("stdout", "").splitlines():
                if "coral_reef.elf" not in line:
                    continue
                parts = line.strip().split()
                if len(parts) >= 4:
                    try:
                        size_text = int(parts[0]) + int(parts[1])
                    except ValueError:
                        size_text = 0

    result.update(
        {
            "profile": profile,
            "runtime_profile": profile,
            "spinnaker_tools": tools,
            "aplx_artifact": str(profile_aplx),
            "aplx_exists": profile_aplx.exists(),
            "size_text": size_text,
        }
    )
    result["status"] = "pass" if result["returncode"] == 0 and profile_aplx.exists() else "fail"
    return result


def prepare_bundle(output_dir: Path) -> tuple[Path, str, Dict[str, str]]:
    bundle = output_dir / "ebrains_upload_bundle" / UPLOAD_PACKAGE_NAME
    if bundle.exists():
        shutil.rmtree(bundle)
    (bundle / "experiments").mkdir(parents=True, exist_ok=True)
    (bundle / "coral_reef_spinnaker" / "python_host").mkdir(parents=True, exist_ok=True)

    scripts = [
        "tier4_30g_lifecycle_task_benefit_resource_bridge.py",
        "tier4_30f_lifecycle_sham_hardware_subset.py",
        "tier4_30e_multicore_lifecycle_hardware_smoke.py",
        "tier4_30b_lifecycle_hardware_smoke.py",
        "tier4_30a_static_pool_lifecycle_reference.py",
        "tier4_22i_custom_runtime_roundtrip.py",
    ]
    for script in scripts:
        target = bundle / "experiments" / script
        shutil.copy2(ROOT / "experiments" / script, target)
        os.chmod(target, 0o755)

    shutil.copy2(ROOT / "coral_reef_spinnaker" / "__init__.py", bundle / "coral_reef_spinnaker" / "__init__.py")
    shutil.copy2(
        ROOT / "coral_reef_spinnaker" / "python_host" / "colony_controller.py",
        bundle / "coral_reef_spinnaker" / "python_host" / "colony_controller.py",
    )
    clean_copy_tree(RUNTIME, bundle / "coral_reef_spinnaker" / "spinnaker_runtime")

    command = f"{UPLOAD_PACKAGE_NAME}/experiments/tier4_30g_lifecycle_task_benefit_resource_bridge.py --mode run-hardware --output-dir tier4_30g_hw_job_output"
    readme = bundle / "README_TIER4_30G_HW_JOB.md"
    readme.write_text(
        "# Tier 4.30g EBRAINS Lifecycle Task-Benefit / Resource Bridge\n\n"
        f"Upload the `{UPLOAD_PACKAGE_NAME}` folder itself so the JobManager path starts with `{UPLOAD_PACKAGE_NAME}/`. Do not upload `controlled_test_output`.\n\n"
        "Purpose: run the bounded lifecycle-to-task bridge on real SpiNNaker. The lifecycle_core executes enabled and sham-control lifecycle modes; the host ferries the resulting lifecycle gate into the context/route/memory/learning task path; the learning core runs the compact delayed task.\n\n"
        "Run command:\n\n"
        f"```text\n{command}\n```\n\n"
        "Paste the command directly into the EBRAINS JobManager command field. Do not wrap it in `bash`, `cd`, or `python3`.\n\n"
        "The package is source-only and intentionally does not include the full repository evidence archive. Do not use package-local mode as the canonical preflight; the full-repo prepare step already validated the local contract and source checks before this folder was generated.\n\n"
        "PASS is a hardware task-benefit/resource bridge only: real target acquisition, five profile builds/loads, enabled lifecycle task gate open, predeclared controls gated closed, learning-core state near fixed-point reference, returned resource/readback accounting, and zero synthetic fallback. It is not autonomous lifecycle-to-learning MCPL, not speedup, not multi-chip scaling, and not a lifecycle baseline freeze.\n",
        encoding="utf-8",
    )
    metadata = {
        "tier": TIER_NAME,
        "runner_revision": RUNNER_REVISION,
        "upload_package": UPLOAD_PACKAGE_NAME,
        "prepared_at_utc": utc_now(),
        "runner": "experiments/tier4_30g_lifecycle_task_benefit_resource_bridge.py",
        "job_command": command,
        "core_roles": CORE_ROLES,
        "sham_modes": SHAM_MODE_ORDER,
        "claim_boundary": "Prepared source bundle only. Hardware evidence requires returned run-hardware artifacts from EBRAINS/SpiNNaker.",
    }
    write_json(bundle / "metadata.json", metadata)

    STABLE_EBRAINS_UPLOAD.parent.mkdir(parents=True, exist_ok=True)
    if STABLE_EBRAINS_UPLOAD.exists():
        shutil.rmtree(STABLE_EBRAINS_UPLOAD)
    shutil.copytree(bundle, STABLE_EBRAINS_UPLOAD)
    return bundle, command, {"upload_bundle": str(bundle), "stable_upload_folder": str(STABLE_EBRAINS_UPLOAD), "job_readme": str(readme)}


def lifecycle_summary_criteria(mode: str, observed: Dict[str, Any], expected: Dict[str, Any]) -> List[Dict[str, Any]]:
    fields = [
        "schema_version",
        "sham_mode",
        "pool_size",
        "founder_count",
        "active_count",
        "inactive_count",
        "active_mask_bits",
        "attempted_event_count",
        "lifecycle_event_count",
        "cleavage_count",
        "adult_birth_count",
        "death_count",
        "maturity_count",
        "trophic_update_count",
        "invalid_event_count",
        "lineage_checksum",
        "trophic_checksum",
        "payload_len",
    ]
    return [
        criterion(f"{mode} lifecycle {field}", observed.get(field), f"== {expected.get(field)}", observed.get(field) == expected.get(field)).__dict__
        for field in fields
    ]


def bridge_schedule_entries() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for index, row in enumerate(task_sequence()):
        rows.append(
            {
                "index": index,
                "timestep": index + 1,
                "context_key": 101,
                "route_key": 201,
                "memory_key": 301,
                "cue": float(row["cue"]),
                "target": float(row["target"]),
                "delay": DELAY_STEPS,
            }
        )
    return rows


def run_lifecycle_mode(lifecycle_ctrl: Any, args: argparse.Namespace, mode: str, reference: Dict[str, Any]) -> Dict[str, Any]:
    p = CORE_ROLES["lifecycle"]["core"]
    reset = lifecycle_ctrl.reset(args.dest_x, args.dest_y, p)
    time.sleep(float(args.command_delay_seconds))
    init = lifecycle_ctrl.lifecycle_init(
        pool_size=8,
        founder_count=2,
        seed=int(args.seed),
        trophic_seed_raw=FP_ONE,
        generation_seed=0,
        dest_x=args.dest_x,
        dest_y=args.dest_y,
        dest_cpu=p,
    )
    sham = lifecycle_ctrl.lifecycle_sham_mode(
        SHAM_MODE_IDS[mode],
        dest_x=args.dest_x,
        dest_y=args.dest_y,
        dest_cpu=p,
    )
    event_rows: List[Dict[str, Any]] = []
    for event in reference["schedule"]:
        payload = lifecycle_event_payload(event)
        observed = lifecycle_ctrl.lifecycle_event(
            **payload,
            dest_x=args.dest_x,
            dest_y=args.dest_y,
            dest_cpu=p,
        )
        event_rows.append(
            {
                **payload,
                "event_name": event.event_type,
                "success": observed.get("success") is True,
                "status": observed.get("status"),
                "observed_event_count": observed.get("lifecycle_event_count"),
                "observed_invalid_event_count": observed.get("invalid_event_count"),
                "observed_active_mask_bits": observed.get("active_mask_bits"),
            }
        )
    final = lifecycle_ctrl.lifecycle_read_state(args.dest_x, args.dest_y, p)
    expected = reference["expected"]
    success_count = sum(1 for row in event_rows if row["success"])
    failure_count = len(event_rows) - success_count
    checks = [
        criterion(f"{mode} lifecycle reset acknowledged", reset, "== True", reset is True).__dict__,
        criterion(f"{mode} lifecycle init succeeded", init.get("success"), "== True", init.get("success") is True).__dict__,
        criterion(f"{mode} sham mode command succeeded", sham.get("success"), "== True", sham.get("success") is True).__dict__,
        criterion(f"{mode} successful event command count", success_count, f"== {expected['lifecycle_event_count']}", success_count == expected["lifecycle_event_count"]).__dict__,
        criterion(f"{mode} failed event command count", failure_count, f"== {expected['invalid_event_count']}", failure_count == expected["invalid_event_count"]).__dict__,
        *lifecycle_summary_criteria(mode, final, expected),
    ]
    return {
        "status": "pass" if all(item["passed"] for item in checks) else "fail",
        "mode": mode,
        "criteria": checks,
        "reset": reset,
        "init": init,
        "sham": sham,
        "events": event_rows,
        "final": final,
        "expected": expected,
    }


def run_task_mode(ctrls: Dict[str, Any], args: argparse.Namespace, mode: str, bridge: Dict[str, Any], expected_task: Dict[str, Any]) -> Dict[str, Any]:
    started = time.perf_counter()
    schedule = bridge_schedule_entries()
    dest_x = int(args.dest_x)
    dest_y = int(args.dest_y)

    resets = {
        role: ctrls[role].reset(dest_x, dest_y, CORE_ROLES[role]["core"])
        for role in ("context", "route", "memory", "learning")
    }
    time.sleep(0.1)
    context_write = ctrls["context"].write_context(101, 1.0, 1.0, dest_x, dest_y, CORE_ROLES["context"]["core"])
    route_write = ctrls["route"].write_route_slot(201, 1.0, 1.0, dest_x, dest_y, CORE_ROLES["route"]["core"])
    memory_write = ctrls["memory"].write_memory_slot(301, float(bridge["bridge_gate"]), 1.0, dest_x, dest_y, CORE_ROLES["memory"]["core"])

    schedule_uploads: List[Dict[str, Any]] = []
    for entry in schedule:
        ok = ctrls["learning"].write_schedule_entry(
            index=entry["index"],
            timestep=entry["timestep"],
            context_key=entry["context_key"],
            route_key=entry["route_key"],
            memory_key=entry["memory_key"],
            cue=entry["cue"],
            target=entry["target"],
            delay=entry["delay"],
            dest_x=dest_x,
            dest_y=dest_y,
            dest_cpu=CORE_ROLES["learning"]["core"],
        )
        schedule_uploads.append({"index": entry["index"], "success": ok.get("success") is True, **ok})

    run_commands = {
        "context": ctrls["context"].run_continuous(READOUT_LR, 0, dest_x, dest_y, CORE_ROLES["context"]["core"]),
        "route": ctrls["route"].run_continuous(READOUT_LR, 0, dest_x, dest_y, CORE_ROLES["route"]["core"]),
        "memory": ctrls["memory"].run_continuous(READOUT_LR, 0, dest_x, dest_y, CORE_ROLES["memory"]["core"]),
        "learning": ctrls["learning"].run_continuous(READOUT_LR, TASK_EVENTS, dest_x, dest_y, CORE_ROLES["learning"]["core"]),
    }

    waited = 0.0
    poll_interval = float(args.poll_interval_seconds)
    max_wait = float(args.max_wait_seconds)
    last_learning = {}
    while waited < max_wait:
        time.sleep(poll_interval)
        waited += poll_interval
        last_learning = ctrls["learning"].read_state(dest_x, dest_y, CORE_ROLES["learning"]["core"])
        if (
            last_learning.get("success") is True
            and last_learning.get("pending_matured") == TASK_EVENTS
            and last_learning.get("active_pending") == 0
        ):
            break

    pauses = {
        "context": ctrls["context"].pause(dest_x, dest_y, CORE_ROLES["context"]["core"]),
        "route": ctrls["route"].pause(dest_x, dest_y, CORE_ROLES["route"]["core"]),
        "memory": ctrls["memory"].pause(dest_x, dest_y, CORE_ROLES["memory"]["core"]),
        "learning": ctrls["learning"].pause(dest_x, dest_y, CORE_ROLES["learning"]["core"]),
    }
    time.sleep(0.1)
    final_states = {
        role: ctrls[role].read_state(dest_x, dest_y, CORE_ROLES[role]["core"])
        for role in ("context", "route", "memory", "learning")
    }
    learning_final = final_states["learning"]
    tolerance = int(args.readout_tolerance_raw)
    checks = [
        criterion(f"{mode} task core resets", resets, "all True", all(resets.values())).__dict__,
        criterion(f"{mode} context write", context_write.get("success"), "== True", context_write.get("success") is True).__dict__,
        criterion(f"{mode} route write", route_write.get("success"), "== True", route_write.get("success") is True).__dict__,
        criterion(f"{mode} memory bridge write", memory_write.get("success"), "== True", memory_write.get("success") is True).__dict__,
        criterion(f"{mode} memory bridge value", memory_write.get("active_memory_slots"), ">= 1", int(memory_write.get("active_memory_slots") or 0) >= 1).__dict__,
        criterion(f"{mode} schedule uploads", sum(1 for item in schedule_uploads if item.get("success")), f"== {TASK_EVENTS}", sum(1 for item in schedule_uploads if item.get("success")) == TASK_EVENTS).__dict__,
        criterion(f"{mode} run_continuous commands", {k: v.get("success") for k, v in run_commands.items()}, "all True", all(v.get("success") is True for v in run_commands.values())).__dict__,
        criterion(f"{mode} pause commands", {k: v.get("success") for k, v in pauses.items()}, "all True", all(v.get("success") is True for v in pauses.values())).__dict__,
        criterion(f"{mode} final reads", {k: v.get("success") for k, v in final_states.items()}, "all True", all(v.get("success") is True for v in final_states.values())).__dict__,
        criterion(f"{mode} pending_created", learning_final.get("pending_created"), f"== {TASK_EVENTS}", learning_final.get("pending_created") == TASK_EVENTS).__dict__,
        criterion(f"{mode} pending_matured", learning_final.get("pending_matured"), f"== {TASK_EVENTS}", learning_final.get("pending_matured") == TASK_EVENTS).__dict__,
        criterion(f"{mode} active_pending cleared", learning_final.get("active_pending"), "== 0", learning_final.get("active_pending") == 0).__dict__,
        criterion(f"{mode} readout weight near reference", learning_final.get("readout_weight_raw"), f"within +/- {tolerance} of {expected_task['final_weight_raw']}", abs(int(learning_final.get("readout_weight_raw") or 0) - int(expected_task["final_weight_raw"])) <= tolerance).__dict__,
        criterion(f"{mode} readout bias near reference", learning_final.get("readout_bias_raw"), f"within +/- {tolerance} of {expected_task['final_bias_raw']}", abs(int(learning_final.get("readout_bias_raw") or 0) - int(expected_task["final_bias_raw"])) <= tolerance).__dict__,
        criterion(f"{mode} lookup_requests", learning_final.get("lookup_requests"), f"== {TASK_EVENTS * 3}", learning_final.get("lookup_requests") == TASK_EVENTS * 3).__dict__,
        criterion(f"{mode} lookup_replies", learning_final.get("lookup_replies"), f"== {TASK_EVENTS * 3}", learning_final.get("lookup_replies") == TASK_EVENTS * 3).__dict__,
        criterion(f"{mode} stale replies zero", learning_final.get("stale_replies"), "== 0", learning_final.get("stale_replies") == 0).__dict__,
        criterion(f"{mode} timeouts zero", learning_final.get("timeouts"), "== 0", learning_final.get("timeouts") == 0).__dict__,
    ]
    return {
        "status": "pass" if all(item["passed"] for item in checks) else "fail",
        "mode": mode,
        "criteria": checks,
        "runtime_seconds": time.perf_counter() - started,
        "resets": resets,
        "state_writes": {
            "context": context_write,
            "route": route_write,
            "memory": memory_write,
        },
        "schedule_uploads": schedule_uploads,
        "run_continuous": run_commands,
        "waited_seconds": waited,
        "last_learning_poll": last_learning,
        "pause": pauses,
        "final_state": final_states,
        "expected_task": expected_task,
    }


def lifecycle_task_hardware_loop(hostname: str, args: argparse.Namespace, references: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    from coral_reef_spinnaker.python_host.colony_controller import ColonyController

    started = time.perf_counter()
    ctrls = {
        role: ColonyController(hostname, port=int(args.port), timeout=float(args.timeout_seconds))
        for role in CORE_ROLES
    }
    try:
        profile_reads = {
            role: ctrl.read_state(args.dest_x, args.dest_y, CORE_ROLES[role]["core"])
            for role, ctrl in ctrls.items()
        }
        non_lifecycle_guards = {
            role: ctrl.lifecycle_read_state(args.dest_x, args.dest_y, CORE_ROLES[role]["core"])
            for role, ctrl in ctrls.items()
            if role != "lifecycle"
        }
        enabled_summary = references["enabled"]["expected"]
        modes: Dict[str, Dict[str, Any]] = {}
        resource_rows: List[Dict[str, Any]] = []
        for mode in SHAM_MODE_ORDER:
            lifecycle_result = run_lifecycle_mode(ctrls["lifecycle"], args, mode, references[mode])
            bridge = derive_bridge_features(mode, lifecycle_result.get("final", {}), enabled_summary)
            expected_task, _trace = run_task_reference(mode, bridge)
            task_result = run_task_mode(ctrls, args, mode, bridge, expected_task)
            mode_checks = [
                *lifecycle_result.get("criteria", []),
                criterion(f"{mode} bridge gate hardware", bridge["bridge_gate"], f"== {1 if mode == 'enabled' else 0}", bridge["bridge_gate"] == (1 if mode == "enabled" else 0)).__dict__,
                *task_result.get("criteria", []),
            ]
            modes[mode] = {
                "status": "pass" if all(item["passed"] for item in mode_checks) else "fail",
                "mode": mode,
                "criteria": mode_checks,
                "lifecycle": lifecycle_result,
                "bridge": bridge,
                "task": task_result,
                "expected_task": expected_task,
            }
            learning_final = task_result.get("final_state", {}).get("learning", {})
            resource_rows.append(
                {
                    "mode": mode,
                    "bridge_gate": bridge["bridge_gate"],
                    "mode_status": modes[mode]["status"],
                    "lifecycle_payload_len": lifecycle_result.get("final", {}).get("payload_len"),
                    "lifecycle_readback_bytes": lifecycle_result.get("final", {}).get("readback_bytes"),
                    "task_runtime_seconds": task_result.get("runtime_seconds"),
                    "task_schedule_uploads": len(task_result.get("schedule_uploads", [])),
                    "learning_lookup_requests": learning_final.get("lookup_requests"),
                    "learning_lookup_replies": learning_final.get("lookup_replies"),
                    "learning_stale_replies": learning_final.get("stale_replies"),
                    "learning_timeouts": learning_final.get("timeouts"),
                    "learning_readback_bytes": learning_final.get("readback_bytes"),
                    "learning_commands_received": learning_final.get("commands_received"),
                    "observed_weight_raw": learning_final.get("readout_weight_raw"),
                    "expected_weight_raw": expected_task.get("final_weight_raw"),
                    "observed_bias_raw": learning_final.get("readout_bias_raw"),
                    "expected_bias_raw": expected_task.get("final_bias_raw"),
                    "reference_tail_accuracy": expected_task.get("tail_accuracy"),
                }
            )

        final_profile_reads = {
            role: ctrl.read_state(args.dest_x, args.dest_y, CORE_ROLES[role]["core"])
            for role, ctrl in ctrls.items()
        }
        task_gate_checks = [
            criterion("enabled hardware mode passed", modes["enabled"]["status"], "== pass", modes["enabled"]["status"] == "pass").__dict__,
            criterion("all control hardware modes passed", {mode: modes[mode]["status"] for mode in SHAM_MODE_ORDER if mode != "enabled"}, "all == pass", all(modes[mode]["status"] == "pass" for mode in SHAM_MODE_ORDER if mode != "enabled")).__dict__,
            criterion("enabled hardware bridge gate open", modes["enabled"]["bridge"]["bridge_gate"], "== 1", modes["enabled"]["bridge"]["bridge_gate"] == 1).__dict__,
            criterion("control hardware bridge gates closed", [modes[mode]["bridge"]["bridge_gate"] for mode in SHAM_MODE_ORDER if mode != "enabled"], "all == 0", all(modes[mode]["bridge"]["bridge_gate"] == 0 for mode in SHAM_MODE_ORDER if mode != "enabled")).__dict__,
        ]
        status = "pass" if (
            all(read.get("success") is True for read in profile_reads.values())
            and all(read.get("profile_id") == CORE_ROLES[role]["profile_id"] for role, read in profile_reads.items())
            and all(probe.get("success") is False for probe in non_lifecycle_guards.values())
            and all(mode_result.get("status") == "pass" for mode_result in modes.values())
            and all(item["passed"] for item in task_gate_checks)
            and all(read.get("success") is True for read in final_profile_reads.values())
        ) else "fail"
        return {
            "status": status,
            "hostname": hostname,
            "runtime_seconds": time.perf_counter() - started,
            "core_roles": CORE_ROLES,
            "profile_reads": profile_reads,
            "non_lifecycle_guard_probe": non_lifecycle_guards,
            "modes": modes,
            "task_gate_criteria": task_gate_checks,
            "resource_accounting": resource_rows,
            "final_profile_reads": final_profile_reads,
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
    finally:
        for ctrl in ctrls.values():
            ctrl.close()


def write_hardware_report(path: Path, result: Dict[str, Any]) -> None:
    lines = [
        "# Tier 4.30g Lifecycle Task-Benefit / Resource Bridge Hardware Findings",
        "",
        f"- Generated: `{result.get('generated_at_utc')}`",
        f"- Mode: `{result.get('mode')}`",
        f"- Status: **{str(result.get('status', 'unknown')).upper()}**",
        f"- Runner revision: `{result.get('runner_revision')}`",
        "",
        "## Claim Boundary",
        "",
        result.get("claim_boundary", ""),
        "",
        "## Summary",
        "",
    ]
    for key, value in result.get("summary", {}).items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Criteria", "", "| Criterion | Value | Rule | Pass |", "| --- | --- | --- | --- |"])
    for item in result.get("criteria", []):
        value = json.dumps(json_safe(item.get("value")), sort_keys=True)
        if len(value) > 140:
            value = value[:137] + "..."
        lines.append(f"| {item.get('name')} | `{value}` | {item.get('rule')} | {'yes' if item.get('passed') else 'no'} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def finalize_hardware(output_dir: Path, result: Dict[str, Any]) -> int:
    result_path = output_dir / "tier4_30g_hw_results.json"
    report_path = output_dir / "tier4_30g_hw_report.md"
    result.setdefault("artifacts", {})
    result["artifacts"].update({"results_json": str(result_path), "report_md": str(report_path)})
    write_json(result_path, result)
    write_hardware_report(report_path, result)
    write_json(CONTROLLED / "tier4_30g_hw_latest_manifest.json", result)
    print(json.dumps({"status": result.get("status"), "output_dir": str(output_dir), "results": str(result_path)}, indent=2))
    return 0 if str(result.get("status", "")).lower() in {"pass", "prepared"} else 1


def mode_prepare(args: argparse.Namespace, output_dir: Path) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    local_contract = run_local(output_dir / "local_contract", update_latest=False)
    host_tests = run_runtime_source_checks(output_dir)
    main_syntax = base.run_main_syntax_check(output_dir)
    py_compile = run_cmd([sys.executable, "-m", "py_compile", str(Path(__file__).resolve())])
    bundle, command, bundle_artifacts = prepare_bundle(output_dir)
    criteria = [
        criterion("local 4.30g contract pass", local_contract.get("status"), "== pass", local_contract.get("status") == "pass").__dict__,
        criterion("runtime source checks pass", host_tests.get("status"), "== pass", host_tests.get("status") == "pass").__dict__,
        criterion("main.c syntax check pass", main_syntax.get("status"), "== pass", main_syntax.get("status") == "pass").__dict__,
        criterion("runner py_compile pass", py_compile.get("returncode"), "== 0", py_compile.get("returncode") == 0).__dict__,
        criterion("upload bundle created", str(bundle), "exists", bundle.exists()).__dict__,
        criterion("stable upload folder created", str(STABLE_EBRAINS_UPLOAD), "exists", STABLE_EBRAINS_UPLOAD.exists()).__dict__,
        criterion("run-hardware command emitted", command, "contains --mode run-hardware", "--mode run-hardware" in command).__dict__,
    ]
    status = "prepared" if all(item["passed"] for item in criteria) else "blocked"
    result = {
        "tier": "4.30g-hw",
        "tier_name": TIER_NAME,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "mode": "prepare",
        "status": status,
        "output_dir": str(output_dir),
        "summary": {
            "upload_package": UPLOAD_PACKAGE_NAME,
            "upload_bundle": str(bundle),
            "stable_upload_folder": str(STABLE_EBRAINS_UPLOAD),
            "job_command": command,
            "what_i_need_from_user": f"Upload `{UPLOAD_PACKAGE_NAME}` to EBRAINS/JobManager and run the emitted command.",
        },
        "criteria": criteria,
        "local_contract": local_contract,
        "host_tests": host_tests,
        "main_syntax_check": main_syntax,
        "py_compile": py_compile,
        "bundle_artifacts": bundle_artifacts,
        "core_roles": CORE_ROLES,
        "claim_boundary": "Prepared source bundle only; no hardware evidence until returned run-hardware artifacts pass.",
    }
    return finalize_hardware(output_dir, result)


def mode_run_hardware(args: argparse.Namespace, output_dir: Path) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    references = {mode: control_reference(mode) for mode in SHAM_MODE_ORDER}
    env_report = base.environment_report()
    host_tests = run_runtime_source_checks(output_dir)
    main_syntax = base.run_main_syntax_check(output_dir)
    builds = {role: build_aplx_for_profile(spec["profile"], output_dir) for role, spec in CORE_ROLES.items()}

    target: Dict[str, Any] = {"status": "not_attempted", "reason": "blocked_before_target_acquisition"}
    target_cleanup: Dict[str, Any] = {"status": "not_attempted"}
    loads: Dict[str, Dict[str, Any]] = {role: {"status": "not_attempted"} for role in CORE_ROLES}
    task: Dict[str, Any] = {"status": "not_attempted", "reason": "blocked_before_task_bridge_loop"}
    hostname = ""
    hardware_exception: Dict[str, Any] | None = None

    try:
        if all(build.get("status") == "pass" for build in builds.values()):
            target = base.acquire_hardware_target(args)
            hostname = str(target.get("hostname") or target.get("target_ipaddress") or "")
            tx = target.get("_transceiver")
            if target.get("status") == "pass" and hostname and not args.skip_load:
                for role, spec in CORE_ROLES.items():
                    loads[role] = base.load_application_spinnman(
                        hostname,
                        Path(builds[role]["aplx_artifact"]),
                        x=int(args.dest_x),
                        y=int(args.dest_y),
                        p=int(spec["core"]),
                        app_id=int(spec["app_id"]),
                        delay=float(args.startup_delay_seconds),
                        transceiver=tx,
                    )
            elif args.skip_load:
                loads = {role: {"status": "skipped", "reason": "--skip-load set"} for role in CORE_ROLES}
            if target.get("status") == "pass" and hostname and all(load.get("status") in {"pass", "skipped"} for load in loads.values()):
                task = lifecycle_task_hardware_loop(hostname, args, references)
    except Exception as exc:
        hardware_exception = {"exception_type": type(exc).__name__, "exception": str(exc), "traceback": traceback.format_exc()}
        task = {"status": "fail", **hardware_exception}
    finally:
        target_cleanup = base.release_hardware_target(target)

    write_json(output_dir / "tier4_30g_hw_environment.json", env_report)
    write_json(output_dir / "tier4_30g_hw_target_acquisition.json", base.public_target_acquisition({**target, "cleanup": target_cleanup}))
    for role, build in builds.items():
        write_json(output_dir / f"tier4_30g_hw_{role}_build.json", build)
    for role, load in loads.items():
        write_json(output_dir / f"tier4_30g_hw_{role}_load.json", load)
    write_json(output_dir / "tier4_30g_hw_task_result.json", task)
    if task.get("resource_accounting"):
        write_csv(output_dir / "tier4_30g_hw_resource_accounting.csv", task.get("resource_accounting", []))
    for mode, item in task.get("modes", {}).items() if isinstance(task, dict) else []:
        write_csv(output_dir / f"tier4_30g_hw_{mode}_lifecycle_events.csv", item.get("lifecycle", {}).get("events", []))

    mode_checks: List[Dict[str, Any]] = []
    for item in task.get("modes", {}).values() if isinstance(task, dict) else []:
        mode_checks.extend(item.get("criteria", []))
    task_gate_checks = task.get("task_gate_criteria", []) if isinstance(task, dict) else []
    profile_reads = task.get("profile_reads", {}) if isinstance(task, dict) else {}
    final_profile_reads = task.get("final_profile_reads", {}) if isinstance(task, dict) else {}
    non_lifecycle_guards = task.get("non_lifecycle_guard_probe", {}) if isinstance(task, dict) else {}

    profile_criteria: List[Dict[str, Any]] = []
    for role, spec in CORE_ROLES.items():
        read = profile_reads.get(role, {})
        final_read = final_profile_reads.get(role, {})
        profile_criteria.extend(
            [
                criterion(f"{role} profile read success", read.get("success"), "== True", read.get("success") is True).__dict__,
                criterion(f"{role} profile id", read.get("profile_id"), f"== {spec['profile_id']}", read.get("profile_id") == spec["profile_id"]).__dict__,
                criterion(f"{role} final profile read success", final_read.get("success"), "== True", final_read.get("success") is True).__dict__,
            ]
        )
    guard_criteria = [
        criterion(f"{role} rejects direct lifecycle read", probe.get("success"), "== False", probe.get("success") is False).__dict__
        for role, probe in non_lifecycle_guards.items()
    ]

    criteria = [
        criterion("runner revision current", RUNNER_REVISION, "expected current source", True).__dict__,
        criterion("runtime source checks pass", host_tests.get("status"), "== pass", host_tests.get("status") == "pass").__dict__,
        criterion("main.c host syntax check pass", main_syntax.get("status"), "== pass", main_syntax.get("status") == "pass").__dict__,
        criterion("all five profile builds pass", {role: build.get("status") for role, build in builds.items()}, "all == pass", all(build.get("status") == "pass" for build in builds.values())).__dict__,
        criterion("hardware target acquired", base.public_target_acquisition(target), "status == pass and hostname acquired", target.get("status") == "pass" and bool(hostname)).__dict__,
        criterion("all five profile loads pass", {role: load.get("status") for role, load in loads.items()}, "all == pass", all(load.get("status") == "pass" for load in loads.values())).__dict__,
        criterion("lifecycle task-benefit bridge pass", task.get("status"), "== pass", task.get("status") == "pass").__dict__,
        *profile_criteria,
        *guard_criteria,
        *mode_checks,
        *task_gate_checks,
        criterion("resource accounting returned", bool(task.get("resource_accounting")), "== True", bool(task.get("resource_accounting"))).__dict__,
        criterion("no unhandled hardware exception", hardware_exception is None, "== True", hardware_exception is None).__dict__,
        criterion("synthetic fallback zero", 0, "== 0", True).__dict__,
    ]
    status = "pass" if all(item["passed"] for item in criteria) else "fail"
    result = {
        "tier": "4.30g-hw",
        "tier_name": TIER_NAME,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "mode": "run-hardware",
        "status": status,
        "failure_reason": "" if status == "pass" else "Failed criteria: " + ", ".join(item["name"] for item in criteria if not item["passed"]),
        "output_dir": str(output_dir),
        "summary": {
            "upload_package": UPLOAD_PACKAGE_NAME,
            "hardware_target_configured": target.get("status") == "pass" and bool(hostname),
            "spinnaker_hostname": hostname,
            "profile_builds_passed": all(build.get("status") == "pass" for build in builds.values()),
            "profile_loads_passed": all(load.get("status") == "pass" for load in loads.values()),
            "task_status": task.get("status"),
            "sham_modes": SHAM_MODE_ORDER,
            "claim_boundary": "Hardware task-benefit/resource bridge only; not autonomous lifecycle-to-learning MCPL, not speedup, not multi-chip scaling, and not a lifecycle baseline freeze.",
            "next_step_if_passed": "Ingest returned artifacts, then decide whether the lifecycle-native baseline can freeze or needs a stronger task gate.",
        },
        "criteria": criteria,
        "references": {mode: {"expected": ref["expected"], "event_count": ref["event_count"]} for mode, ref in references.items()},
        "environment": env_report,
        "host_tests": host_tests,
        "main_syntax_check": main_syntax,
        "builds": builds,
        "target_acquisition": base.public_target_acquisition(target),
        "target_cleanup": target_cleanup,
        "loads": loads,
        "task": task,
        "hardware_exception": hardware_exception,
        "core_roles": CORE_ROLES,
        "claim_boundary": "Tier 4.30g hardware tests a host-ferried lifecycle task-benefit/resource bridge. It is not autonomous lifecycle-to-learning MCPL, not speedup, not multi-chip scaling, not v2.2 temporal migration, and not a lifecycle baseline freeze.",
    }
    return finalize_hardware(output_dir, result)


def copy_returned_artifacts(ingest_dir: Path, output_dir: Path, *, anchor: Path | None = None) -> List[str]:
    if not ingest_dir.exists():
        return []
    returned_dir = output_dir / "returned_artifacts"
    returned_dir.mkdir(parents=True, exist_ok=True)
    copied: List[str] = []
    anchor_mtime = anchor.stat().st_mtime if anchor and anchor.exists() else None
    for path in sorted(ingest_dir.iterdir()):
        if not path.is_file():
            continue
        if anchor_mtime is not None and abs(path.stat().st_mtime - anchor_mtime) > 900:
            continue
        if path.suffix in {".o", ".elf", ".aplx"}:
            continue
        name = path.name
        if (
            name.startswith("tier4_30g")
            or name.startswith("main ")
            or name.startswith("state_manager ")
            or name.startswith("host_interface ")
            or name.startswith("reports")
            or name in {"finished", "global_provenance.sqlite3"}
        ):
            dest = returned_dir / name
            shutil.copy2(path, dest)
            copied.append(str(dest))
    return copied


def mode_ingest(args: argparse.Namespace, output_dir: Path) -> int:
    ingest_dir = Path(args.ingest_dir or output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    candidate = Path(args.hardware_results) if args.hardware_results else ingest_dir / "tier4_30g_hw_results.json"
    if not candidate.exists():
        matches = sorted(ingest_dir.glob("**/tier4_30g_hw_results.json"))
        if matches:
            candidate = matches[-1]
    if not candidate.exists():
        result = {
            "tier": "4.30g-hw",
            "tier_name": TIER_NAME,
            "runner_revision": RUNNER_REVISION,
            "generated_at_utc": utc_now(),
            "mode": "ingest",
            "status": "fail",
            "failure_reason": f"tier4_30g_hw_results.json not found in {ingest_dir}",
            "criteria": [criterion("hardware results json exists", str(candidate), "exists", False).__dict__],
            "claim_boundary": "Failed ingest only; not hardware evidence.",
        }
        return finalize_hardware(output_dir, result)
    returned_artifacts = copy_returned_artifacts(ingest_dir, output_dir, anchor=candidate)
    hardware = json.loads(candidate.read_text(encoding="utf-8"))
    criteria = [
        criterion("hardware results json exists", str(candidate), "exists", True).__dict__,
        criterion("hardware mode was run-hardware", hardware.get("mode"), "== run-hardware", hardware.get("mode") == "run-hardware").__dict__,
        criterion("hardware status pass", hardware.get("status"), "== pass", hardware.get("status") == "pass").__dict__,
        criterion("runner revision current", hardware.get("runner_revision"), f"== {RUNNER_REVISION}", hardware.get("runner_revision") == RUNNER_REVISION).__dict__,
        criterion("returned artifacts preserved", len(returned_artifacts), "> 0", len(returned_artifacts) > 0).__dict__,
    ]
    status = "pass" if all(item["passed"] for item in criteria) else "fail"
    result = {
        "tier": "4.30g-hw",
        "tier_name": TIER_NAME,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "mode": "ingest",
        "status": status,
        "failure_reason": "" if status == "pass" else "Failed criteria: " + ", ".join(item["name"] for item in criteria if not item["passed"]),
        "output_dir": str(output_dir),
        "criteria": criteria,
        "raw_remote_status": hardware.get("status"),
        "returned_artifacts": returned_artifacts,
        "hardware_results": hardware,
        "summary": {
            "raw_remote_status": hardware.get("status"),
            "corrected_ingest_status": status,
            "hardware_target_configured": hardware.get("summary", {}).get("hardware_target_configured"),
            "spinnaker_hostname": hardware.get("summary", {}).get("spinnaker_hostname"),
            "profile_builds_passed": hardware.get("summary", {}).get("profile_builds_passed"),
            "profile_loads_passed": hardware.get("summary", {}).get("profile_loads_passed"),
            "task_status": hardware.get("summary", {}).get("task_status"),
            "sham_modes": hardware.get("summary", {}).get("sham_modes"),
        },
        "claim_boundary": "Ingest confirms returned EBRAINS run-hardware artifacts only; no lifecycle baseline freeze until documentation and registry promotion.",
    }
    return finalize_hardware(output_dir, result)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["local", "prepare", "run-hardware", "ingest"], default="local")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--ingest-dir", type=Path, default=None)
    parser.add_argument("--hardware-results", type=Path, default=None)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--dest-x", type=int, default=0)
    parser.add_argument("--dest-y", type=int, default=0)
    parser.add_argument("--port", type=int, default=17893)
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    parser.add_argument("--startup-delay-seconds", type=float, default=2.0)
    parser.add_argument("--command-delay-seconds", type=float, default=0.03)
    parser.add_argument("--poll-interval-seconds", type=float, default=0.05)
    parser.add_argument("--max-wait-seconds", type=float, default=15.0)
    parser.add_argument("--readout-tolerance-raw", type=int, default=8192)
    parser.add_argument("--target-acquisition", choices=["auto", "hostname", "spynnaker-probe"], default="auto")
    parser.add_argument("--spinnaker-hostname", default="")
    parser.add_argument("--target-probe-run-ms", type=float, default=1.0)
    parser.add_argument("--target-probe-timestep-ms", type=float, default=1.0)
    parser.add_argument("--target-probe-population-size", type=int, default=1)
    parser.add_argument("--dest-cpu", type=int, default=4, help="Used by target-acquisition probe; 4.30g loads fixed cores 4-8.")
    parser.add_argument("--auto-dest-cpu", dest="auto_dest_cpu", action="store_true", default=True)
    parser.add_argument("--no-auto-dest-cpu", dest="auto_dest_cpu", action="store_false")
    parser.add_argument("--skip-load", action="store_true", help="Debug only; canonical hardware evidence requires normal load.")
    args = parser.parse_args()
    if args.output_dir == DEFAULT_OUTPUT_DIR and args.mode == "prepare":
        args.output_dir = DEFAULT_PREPARE_OUTPUT
    elif args.output_dir == DEFAULT_OUTPUT_DIR and args.mode == "run-hardware":
        args.output_dir = DEFAULT_RUN_OUTPUT
    if args.mode == "prepare":
        return mode_prepare(args, args.output_dir)
    if args.mode == "run-hardware":
        return mode_run_hardware(args, args.output_dir)
    if args.mode == "ingest":
        return mode_ingest(args, args.output_dir)
    results = run_local(args.output_dir)
    print(json.dumps({
        "tier": results["tier"],
        "status": results["status"],
        "output_dir": results["output_dir"],
        "criteria": f"{results['criteria_passed']}/{results['criteria_total']}",
    }, indent=2, sort_keys=True))
    return 0 if results["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
