#!/usr/bin/env python3
"""Tier 4.20a v2.1 hardware-transfer readiness audit.

This audit does not run SpiNNaker. It maps the frozen v2.1 software mechanisms
to the runtime contracts already proven in the repo: step host loop, chunked
host replay, and future hybrid/on-chip/custom-C execution.

The purpose is to avoid two bad paths: porting speculative mechanisms too early,
or building a huge software-only stack before checking hardware transfer risk.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"
TIER = "Tier 4.20a - v2.1 Hardware Transfer Readiness Audit"
V21_BASELINE = ROOT / "baselines" / "CRA_EVIDENCE_BASELINE_v2.1.json"
V08_BASELINE = ROOT / "baselines" / "CRA_EVIDENCE_BASELINE_v0.8.json"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from coral_reef_spinnaker.runtime_modes import make_runtime_plan  # noqa: E402


@dataclass(frozen=True)
class MechanismTransferRow:
    mechanism: str
    source_tier: str
    current_claim: str
    current_location: str
    chunked_host_status: str
    continuous_status: str
    on_chip_status: str
    hardware_probe_priority: str
    risk: str
    required_bridge_work: str
    claim_boundary: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    return value


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    import csv

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


def mechanism_rows() -> list[MechanismTransferRow]:
    return [
        MechanismTransferRow(
            mechanism="PendingHorizon delayed credit / delayed_lr_0_20",
            source_tier="Tier 5.4, Tier 4.16a/b",
            current_claim="confirmed delayed-credit setting and hardware-surviving hard-task bridge in earlier chunked host capsules",
            current_location="host-side learning manager",
            chunked_host_status="ready_for_probe",
            continuous_status="future_custom_runtime",
            on_chip_status="not_implemented",
            hardware_probe_priority="high",
            risk="medium",
            required_bridge_work="reuse scheduled input and per-step binned readback; verify matured feedback replay under v2.1 tasks",
            claim_boundary="not native on-chip eligibility; host computes delayed credit at chunk boundaries",
        ),
        MechanismTransferRow(
            mechanism="keyed context memory",
            source_tier="Tier 5.10g, Tier 5.10e/f",
            current_claim="bounded host-side keyed/multi-slot context memory repairs interference and preserves regression",
            current_location="host metadata/state in learning manager",
            chunked_host_status="needs_bridge_adapter",
            continuous_status="future_custom_runtime",
            on_chip_status="not_implemented",
            hardware_probe_priority="high",
            risk="medium",
            required_bridge_work="carry visible context/decision metadata through chunk scheduler; replay per-step context writes and decisions after binned readback",
            claim_boundary="not native memory and not hardware memory until a returned SpiNNaker probe passes",
        ),
        MechanismTransferRow(
            mechanism="replay / consolidation",
            source_tier="Tier 5.11d",
            current_claim="correct-binding replay repairs silent reentry and separates wrong-memory controls",
            current_location="host offline/consolidation loop",
            chunked_host_status="needs_probe_design",
            continuous_status="future_custom_runtime",
            on_chip_status="not_implemented",
            hardware_probe_priority="medium",
            risk="high",
            required_bridge_work="define replay epochs around hardware chunks; prevent replay from fabricating spike readback; log replay events separately from real hardware events",
            claim_boundary="hardware replay is unproven; priority weighting is not the promoted claim",
        ),
        MechanismTransferRow(
            mechanism="visible predictive context / predictive binding",
            source_tier="Tier 5.12d, Tier 5.17e",
            current_claim="bounded host-side predictive-context and predictive-binding evidence through v2.0 guardrails",
            current_location="host metadata/state and diagnostic input injection",
            chunked_host_status="needs_bridge_adapter",
            continuous_status="future_custom_runtime",
            on_chip_status="not_implemented",
            hardware_probe_priority="high",
            risk="medium_high",
            required_bridge_work="schedule precursor/decision metadata inside chunks; preserve no-label/no-reward preexposure contract; compare against shuffled/wrong-domain controls in hardware probe",
            claim_boundary="not full world model and not on-chip predictive coding",
        ),
        MechanismTransferRow(
            mechanism="composition and module routing",
            source_tier="Tier 5.13c, Tier 5.14",
            current_claim="internal host-side composition/routing and working-memory/context binding survive guardrails",
            current_location="host module tables, router scores, and metadata-driven feature injection",
            chunked_host_status="needs_bridge_adapter",
            continuous_status="future_custom_runtime",
            on_chip_status="not_implemented",
            hardware_probe_priority="medium",
            risk="high",
            required_bridge_work="map skill/context events to chunk scheduler; replay module/router updates after feedback; prove pre-feedback route selection with hardware readback",
            claim_boundary="not hardware/on-chip routing, language, planning, or general compositional reasoning",
        ),
        MechanismTransferRow(
            mechanism="self-evaluation / reliability monitoring",
            source_tier="Tier 5.18, Tier 5.18c",
            current_claim="v2.1 bounded host-side reliability monitor predicts primary-path error/hazard risk and improves confidence-gated behavior",
            current_location="host diagnostic monitor and confidence-gated fallback",
            chunked_host_status="needs_bridge_adapter",
            continuous_status="future_custom_runtime",
            on_chip_status="not_implemented",
            hardware_probe_priority="medium",
            risk="medium_high",
            required_bridge_work="compute monitor features only from pre-feedback/binned state; log confidence before outcome; verify sham monitors in hardware-compatible capsule",
            claim_boundary="not consciousness, self-awareness, introspection, on-chip self-monitoring, language, planning, or AGI",
        ),
        MechanismTransferRow(
            mechanism="macro eligibility residual trace",
            source_tier="Tier 5.9a/b/c",
            current_claim="failed v2.1-era recheck; remains parked as non-promoted delayed-credit diagnostic evidence",
            current_location="host learning manager diagnostic path",
            chunked_host_status="not_promoted",
            continuous_status="future_custom_runtime_if_promoted",
            on_chip_status="not_implemented",
            hardware_probe_priority="low_until_promoted",
            risk="high",
            required_bridge_work="do not port; revive only if a future measured blocker specifically requires macro eligibility and the trace beats shuffled/zero controls",
            claim_boundary="not native eligibility and not part of the v2.1 claim unless future gates pass",
        ),
        MechanismTransferRow(
            mechanism="spike temporal-code diagnostics",
            source_tier="Tier 5.15",
            current_claim="software temporal CRA uses latency/burst/interval structure under diagnostics",
            current_location="software diagnostic encoding/readout path",
            chunked_host_status="needs_dedicated_temporal_probe",
            continuous_status="future_custom_runtime",
            on_chip_status="not_implemented",
            hardware_probe_priority="medium",
            risk="medium_high",
            required_bridge_work="ensure temporal codes are delivered inside chunks and read back with bin resolution fine enough to preserve timing controls",
            claim_boundary="not hardware temporal coding until a temporal hardware probe passes",
        ),
    ]


def write_report(path: Path, result: dict[str, Any], rows: list[MechanismTransferRow]) -> None:
    lines = [
        "# Tier 4.20a v2.1 Hardware Transfer Readiness Audit",
        "",
        f"- Generated: `{result['generated_at_utc']}`",
        f"- Status: **{result['status'].upper()}**",
        f"- Output directory: `{result['output_dir']}`",
        "",
        "Tier 4.20a is an engineering audit, not a hardware run. It maps v2.1 mechanisms onto the proven runtime vocabulary so we know what can be tested through chunked host SpiNNaker and what must wait for hybrid/custom-C/on-chip work.",
        "",
        "## Claim Boundary",
        "",
        "- `PASS` means the transfer plan is explicit and auditable.",
        "- It is not a SpiNNaker hardware pass, not custom-C evidence, and not on-chip autonomy.",
        "- Any hardware claim still requires returned pyNN.spiNNaker artifacts with real spike readback, zero fallback, and zero read/run failures.",
        "",
        "## Runtime Contracts",
        "",
        f"- Step host plan: `{result['summary']['step_plan']['implementation_stage']}`, sim.run calls `{result['summary']['step_plan']['sim_run_calls']}`",
        f"- Chunked host plan: `{result['summary']['chunked_plan']['implementation_stage']}`, chunk size `{result['summary']['chunked_plan']['chunk_size_steps']}`, sim.run calls `{result['summary']['chunked_plan']['sim_run_calls']}`",
        f"- Continuous/on-chip plan implemented: `{result['summary']['continuous_on_chip_plan']['implemented']}`; blockers `{', '.join(result['summary']['continuous_on_chip_plan']['blockers'])}`",
        "",
        "## Mechanism Transfer Matrix",
        "",
        "| Mechanism | Chunked host | Continuous | On-chip | Priority | Risk | Required bridge work |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row.mechanism} | `{row.chunked_host_status}` | `{row.continuous_status}` | `{row.on_chip_status}` | `{row.hardware_probe_priority}` | `{row.risk}` | {row.required_bridge_work} |"
        )
    lines.extend(["", "## Criteria", "", "| Criterion | Value | Rule | Pass |", "| --- | --- | --- | --- |"])
    for item in result["criteria"]:
        lines.append(f"| {item['name']} | `{item['value']}` | `{item['rule']}` | {'yes' if item['passed'] else 'no'} |")
    lines.extend(["", "## Recommended Hardware Sequence", "", *[f"{i}. {step}" for i, step in enumerate(result['summary']['recommended_sequence'], start=1)], ""])
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def criterion(name: str, passed: bool, value: Any, rule: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "value": value, "rule": rule}


def plan_record(plan: Any) -> dict[str, Any]:
    record = asdict(plan)
    record.update(
        {
            "sim_run_calls": plan.sim_run_calls,
            "simulated_ms_per_chunk": plan.simulated_ms_per_chunk,
            "call_reduction_factor": plan.call_reduction_factor,
            "learning_update_interval_steps": plan.learning_update_interval_steps,
        }
    )
    return record


def run_audit(args: argparse.Namespace, output_dir: Path) -> dict[str, Any]:
    rows = mechanism_rows()
    step = make_runtime_plan(runtime_mode="step", learning_location="host", chunk_size_steps=1, total_steps=args.total_steps, dt_seconds=args.dt_seconds)
    chunked = make_runtime_plan(runtime_mode="chunked", learning_location="host", chunk_size_steps=args.chunk_size_steps, total_steps=args.total_steps, dt_seconds=args.dt_seconds)
    continuous = make_runtime_plan(runtime_mode="continuous", learning_location="on_chip", chunk_size_steps=args.chunk_size_steps, total_steps=args.total_steps, dt_seconds=args.dt_seconds)

    row_dicts = [asdict(row) for row in rows]
    promoted = [row for row in rows if row.chunked_host_status in {"ready_for_probe", "needs_bridge_adapter", "needs_probe_design", "needs_dedicated_temporal_probe"}]
    incorrect_on_chip = [row.mechanism for row in rows if row.on_chip_status not in {"not_implemented"}]
    sequence = [
        "Keep macro eligibility parked after the failed Tier 5.9c v2.1-era recheck; do not include it in hardware probes.",
        "Run Tier 4.20b one-seed v2.1 chunked hardware probe using delayed/context/predictive/self-evaluation-compatible mechanisms only.",
        "If 4.20b passes, run Tier 4.20c three-seed repeat on the smallest v2.1 capsule.",
        "Only after returned hardware evidence is clean, design Tier 4.21 hybrid/native eligibility or on-chip memory prototypes for the mechanisms that actually mattered.",
    ]
    criteria = [
        criterion("frozen v2.1 baseline artifact exists", V21_BASELINE.exists(), str(V21_BASELINE), "exists"),
        criterion("post-chunked-runtime v0.8 baseline artifact exists", V08_BASELINE.exists(), str(V08_BASELINE), "exists"),
        criterion("chunked host runtime contract is implemented", chunked.implemented, chunked.implementation_stage, "implemented == true"),
        criterion("continuous/on-chip runtime is explicitly not overclaimed", not continuous.implemented, continuous.implementation_stage, "implemented == false"),
        criterion("all promoted v2.1 mechanisms classified", len(promoted) >= 6, len(promoted), ">= 6 classified transferable/probe rows"),
        criterion("no mechanism is incorrectly marked on-chip proven", not incorrect_on_chip, ", ".join(incorrect_on_chip) if incorrect_on_chip else "none", "none"),
    ]
    status = "pass" if all(item["passed"] for item in criteria) else "fail"
    return {
        "tier": TIER,
        "generated_at_utc": utc_now(),
        "output_dir": str(output_dir),
        "status": status,
        "failure_reason": "" if status == "pass" else "Failed criteria: " + ", ".join(item["name"] for item in criteria if not item["passed"]),
        "criteria": criteria,
        "mechanism_rows": row_dicts,
        "summary": {
            "step_plan": plan_record(step),
            "chunked_plan": plan_record(chunked),
            "continuous_on_chip_plan": plan_record(continuous),
            "mechanisms_classified": len(rows),
            "chunked_probe_candidates": [row.mechanism for row in promoted],
            "recommended_sequence": sequence,
        },
        "artifacts": {
            "summary_csv": str(output_dir / "tier4_20a_summary.csv"),
            "matrix_csv": str(output_dir / "tier4_20a_transfer_matrix.csv"),
            "report_md": str(output_dir / "tier4_20a_report.md"),
        },
    }


def write_latest(output_dir: Path, manifest_path: Path, report_path: Path, summary_csv: Path, status: str) -> None:
    write_json(
        CONTROLLED / "tier4_20a_latest_manifest.json",
        {
            "generated_at_utc": utc_now(),
            "tier": TIER,
            "status": status,
            "output_dir": str(output_dir),
            "manifest": str(manifest_path),
            "report": str(report_path),
            "summary_csv": str(summary_csv),
            "canonical": False,
            "claim": "Latest Tier 4.20a v2.1 hardware-transfer readiness audit; engineering plan only, not hardware evidence.",
        },
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Tier 4.20a v2.1 hardware-transfer readiness audit.")
    parser.add_argument("--total-steps", type=int, default=1200)
    parser.add_argument("--chunk-size-steps", type=int, default=50)
    parser.add_argument("--dt-seconds", type=float, default=0.05)
    parser.add_argument("--output-dir", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = args.output_dir or (CONTROLLED / f"tier4_20a_{timestamp}")
    output_dir.mkdir(parents=True, exist_ok=True)

    started = time.perf_counter()
    result = run_audit(args, output_dir)
    result["summary"]["runtime_seconds"] = time.perf_counter() - started
    rows = [MechanismTransferRow(**row) for row in result["mechanism_rows"]]

    manifest_path = output_dir / "tier4_20a_results.json"
    report_path = output_dir / "tier4_20a_report.md"
    summary_csv = output_dir / "tier4_20a_summary.csv"
    matrix_csv = output_dir / "tier4_20a_transfer_matrix.csv"
    write_json(manifest_path, result)
    write_csv(summary_csv, [{"status": result["status"], **{item["name"]: item["passed"] for item in result["criteria"]}}])
    write_csv(matrix_csv, result["mechanism_rows"])
    write_report(report_path, result, rows)
    write_latest(output_dir, manifest_path, report_path, summary_csv, result["status"])
    print(json.dumps({"status": result["status"], "output_dir": str(output_dir), "manifest": str(manifest_path), "report": str(report_path), "failure_reason": result["failure_reason"]}, indent=2))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
