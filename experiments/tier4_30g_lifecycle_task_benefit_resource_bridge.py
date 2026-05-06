#!/usr/bin/env python3
"""Tier 4.30g lifecycle task-benefit/resource bridge.

This tier is intentionally a local contract/reference gate. It defines the
bounded bridge between native lifecycle state and a task-bearing path before a
new EBRAINS hardware package is prepared.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
CONTROLLED = ROOT / "controlled_test_output"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier4_30g_20260506_lifecycle_task_benefit_resource_bridge"
LATEST_MANIFEST = CONTROLLED / "tier4_30g_latest_manifest.json"

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
from experiments.tier4_30f_lifecycle_sham_hardware_subset import (  # noqa: E402
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
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
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
    lines.append("- Hardware preparation is intentionally deferred until this contract is green.")
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
    lines.append("")
    return "\n".join(lines) + "\n"


def run_local(output_dir: Path) -> Dict[str, Any]:
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
    write_json(LATEST_MANIFEST, {
        "latest_tier": "4.30g",
        "latest_status": status,
        "latest_output_dir": str(output_dir),
        "updated_at": utc_now(),
        "artifacts": artifacts,
    })
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["local"], default="local")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
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
