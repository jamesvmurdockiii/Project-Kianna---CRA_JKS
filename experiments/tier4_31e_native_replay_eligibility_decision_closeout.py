#!/usr/bin/env python3
"""Tier 4.31e native replay/eligibility decision closeout.

This is a decision gate, not a new mechanism implementation and not hardware
evidence. Tier 4.31d proved a narrow native temporal-state hardware smoke. This
gate asks whether the measured evidence now requires immediate native replay
buffers, sleep-like replay, or native eligibility traces before moving into the
Tier 4.32 mapping/resource model.

The scientific rule is deliberately conservative: do not implement mechanisms
by momentum. A native replay/eligibility implementation is authorized only if a
current promoted mechanism exposes a measured blocker that the existing bounded
host-scheduled/native-bridge path cannot answer.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"

TIER = "Tier 4.31e - Native Replay/Eligibility Decision Closeout"
RUNNER_REVISION = "tier4_31e_native_replay_eligibility_decision_20260506_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier4_31e_20260506_native_replay_eligibility_decision_closeout"

TIER4_29E_COMBINED = CONTROLLED / "tier4_29e_20260505_pass_ingested" / "tier4_29e_combined_results.json"
TIER4_31D_INGEST = CONTROLLED / "tier4_31d_hw_20260506_hardware_pass_ingested" / "tier4_31d_hw_results.json"
TIER4_31D_REMOTE = (
    CONTROLLED
    / "tier4_31d_hw_20260506_hardware_pass_ingested"
    / "returned_artifacts"
    / "tier4_31d_hw_results.json"
)
TIER5_9C = CONTROLLED / "tier5_9c_20260429_190503" / "tier5_9c_results.json"
TIER4_22G = CONTROLLED / "tier4_22g_20260430_event_indexed_trace_runtime" / "tier4_22g_results.json"
BASELINE_V22 = ROOT / "baselines" / "CRA_EVIDENCE_BASELINE_v2.2.json"
BASELINE_NATIVE_V04 = ROOT / "baselines" / "CRA_LIFECYCLE_NATIVE_BASELINE_v0.4.json"


@dataclass(frozen=True)
class Criterion:
    name: str
    value: Any
    rule: str
    passed: bool
    note: str = ""


@dataclass(frozen=True)
class EvidenceInput:
    source_id: str
    path: str
    status: str
    role: str
    extracted_signal: str


@dataclass(frozen=True)
class DecisionRow:
    candidate: str
    decision: str
    measured_blocker: str
    evidence_basis: str
    next_action: str
    claim_boundary: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "__dataclass_fields__"):
        return json_safe(asdict(value))
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    return value


def read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def criterion(name: str, value: Any, rule: str, passed: bool, note: str = "") -> Criterion:
    return Criterion(name=name, value=value, rule=rule, passed=bool(passed), note=note)


def status_of(payload: dict[str, Any]) -> str:
    if payload.get("frozen_at") and payload.get("baseline_id"):
        return "frozen"
    return str(payload.get("status") or payload.get("baseline_status") or payload.get("registry_status") or "unknown").lower()


def count_passed(criteria: list[dict[str, Any]]) -> tuple[int, int]:
    return sum(1 for item in criteria if bool(item.get("passed"))), len(criteria)


def evidence_inputs(
    tier4_29e: dict[str, Any],
    tier4_31d_ingest: dict[str, Any],
    tier4_31d_remote: dict[str, Any],
    tier5_9c: dict[str, Any],
    tier4_22g: dict[str, Any],
    v22: dict[str, Any],
    native_v04: dict[str, Any],
) -> list[EvidenceInput]:
    remote_passed, remote_total = count_passed(tier4_31d_remote.get("criteria", []))
    ingest_passed, ingest_total = count_passed(tier4_31d_ingest.get("criteria", []))
    tier4_22g_summary = tier4_22g.get("summary", {})
    return [
        EvidenceInput(
            "tier4_31d_hardware_smoke",
            str(TIER4_31D_REMOTE.relative_to(ROOT)),
            status_of(tier4_31d_remote),
            "latest native temporal hardware evidence",
            (
                f"{remote_passed}/{remote_total} criteria; board "
                f"{tier4_31d_remote.get('summary', {}).get('hostname')}; payload "
                f"{tier4_31d_remote.get('summary', {}).get('temporal_payload_len')}; "
                "enabled/zero/frozen/reset all passed"
            ),
        ),
        EvidenceInput(
            "tier4_31d_ingest",
            str(TIER4_31D_INGEST.relative_to(ROOT)),
            status_of(tier4_31d_ingest),
            "canonical ingest wrapper",
            (
                f"returned artifacts {tier4_31d_ingest.get('summary', {}).get('returned_artifact_count')}; "
                f"ingest criteria {ingest_passed}/{ingest_total}"
            ),
        ),
        EvidenceInput(
            "tier4_29e_native_replay_bridge",
            str(TIER4_29E_COMBINED.relative_to(ROOT)),
            status_of(tier4_29e),
            "current bounded replay/consolidation hardware evidence",
            (
                "host-scheduled replay/consolidation works through native four-core state "
                f"primitives; criteria {tier4_29e.get('passed_criteria')}/"
                f"{tier4_29e.get('total_criteria')}"
            ),
        ),
        EvidenceInput(
            "tier5_9c_macro_eligibility_recheck",
            str(TIER5_9C.relative_to(ROOT)),
            status_of(tier5_9c),
            "eligibility promotion guardrail",
            "macro eligibility failed promotion/trace-ablation specificity and remains parked",
        ),
        EvidenceInput(
            "tier4_22g_event_indexed_trace_runtime",
            str(TIER4_22G.relative_to(ROOT)),
            status_of(tier4_22g),
            "historical native eligibility substrate optimization",
            (
                f"repaired blockers {tier4_22g_summary.get('repaired_scale_blockers')}; "
                f"open blockers {tier4_22g_summary.get('open_scale_blockers')}"
            ),
        ),
        EvidenceInput(
            "cra_evidence_baseline_v2_2",
            str(BASELINE_V22.relative_to(ROOT)),
            status_of(v22),
            "current promoted software mechanism baseline",
            "bounded host-side fading-memory temporal state; not yet full native v2.2 transfer",
        ),
        EvidenceInput(
            "cra_lifecycle_native_baseline_v0_4",
            str(BASELINE_NATIVE_V04.relative_to(ROOT)),
            status_of(native_v04),
            "current promoted native lifecycle baseline",
            "lifecycle-native baseline already frozen separately; 4.31e does not supersede it",
        ),
    ]


def decision_matrix() -> list[DecisionRow]:
    return [
        DecisionRow(
            candidate="native replay buffers",
            decision="defer",
            measured_blocker="none in current promoted path",
            evidence_basis=(
                "Tier 4.29e already passed bounded host-scheduled replay through native "
                "four-core state primitives. Tier 4.31d did not test replay and did not "
                "expose a replay-specific failure."
            ),
            next_action=(
                "Do not implement chip-owned replay buffers now. Revisit after Tier 4.32 "
                "resource modeling or a later native memory/replay task exposes a schedule, "
                "DTCM, latency, or autonomy blocker."
            ),
            claim_boundary="This defers implementation; it does not claim native replay buffers are unnecessary forever.",
        ),
        DecisionRow(
            candidate="native sleep-like replay",
            decision="defer",
            measured_blocker="none in current promoted path",
            evidence_basis=(
                "Current evidence supports bounded replay/consolidation as a host-scheduled "
                "bridge, not biological sleep. No current hardware tier shows memory decay "
                "or recurrence failure that requires a sleep-like on-chip phase before scaling."
            ),
            next_action=(
                "Keep sleep-like replay as a future mechanism. Require a measured retention, "
                "interference, or autonomy blocker before allocating C/DTCM design work."
            ),
            claim_boundary="No sleep/REM/biological consolidation claim is made.",
        ),
        DecisionRow(
            candidate="native macro eligibility traces",
            decision="defer",
            measured_blocker="none; prior macro eligibility promotion failed",
            evidence_basis=(
                "Tier 5.9c failed the macro-eligibility promotion gate. Tier 4.22g repaired "
                "event-indexed/active trace scale blockers locally, but no current promoted "
                "mechanism requires reviving macro eligibility now."
            ),
            next_action=(
                "Do not run Tier 4.31f now. Reopen only if a later promoted mechanism exposes "
                "a credit-assignment/timing blocker that PendingHorizon, replay bridge, and "
                "temporal state cannot solve."
            ),
            claim_boundary="This does not reject eligibility traces as a long-term substrate; it rejects an immediate promotion.",
        ),
        DecisionRow(
            candidate="Tier 4.31f implementation gate",
            decision="defer / skip for now",
            measured_blocker="no triggering blocker",
            evidence_basis="4.31e decision rows all defer immediate replay/eligibility implementation.",
            next_action="Mark 4.31f deferred and proceed to Tier 4.32.",
            claim_boundary="No baseline freeze is authorized by this closeout.",
        ),
        DecisionRow(
            candidate="Tier 4.32 mapping/resource model",
            decision="authorize next",
            measured_blocker="resource and scaling envelope still need characterization",
            evidence_basis=(
                "4.27-4.31 have accumulated measured hardware data, but the repo still needs "
                "a consolidated mapping/resource model before single-chip multi-core stress "
                "or multi-chip communication claims."
            ),
            next_action=(
                "Build the 4.32 model over ITCM/DTCM, schedule length, message/readback bytes, "
                "state slots, lifecycle masks, temporal footprint, MCPL traffic, and failure classes."
            ),
            claim_boundary="4.32 is engineering/resource evidence, not benchmark superiority.",
        ),
    ]


def build_results() -> dict[str, Any]:
    tier4_29e = read_json(TIER4_29E_COMBINED)
    tier4_31d_ingest = read_json(TIER4_31D_INGEST)
    tier4_31d_remote = read_json(TIER4_31D_REMOTE)
    tier5_9c = read_json(TIER5_9C)
    tier4_22g = read_json(TIER4_22G)
    v22 = read_json(BASELINE_V22)
    native_v04 = read_json(BASELINE_NATIVE_V04)

    remote_criteria_passed, remote_criteria_total = count_passed(tier4_31d_remote.get("criteria", []))
    scenario_statuses = tier4_31d_remote.get("summary", {}).get("scenario_statuses", {})
    tier4_22g_summary = tier4_22g.get("summary", {})
    rows = decision_matrix()
    evidence = evidence_inputs(tier4_29e, tier4_31d_ingest, tier4_31d_remote, tier5_9c, tier4_22g, v22, native_v04)
    immediate_impls = [row for row in rows if row.decision.lower().startswith("implement")]
    authorize_432 = any(row.candidate == "Tier 4.32 mapping/resource model" and row.decision == "authorize next" for row in rows)

    criteria = [
        criterion("Tier 4.31d remote hardware smoke passed", status_of(tier4_31d_remote), "== pass", status_of(tier4_31d_remote) == "pass"),
        criterion("Tier 4.31d remote criteria complete", f"{remote_criteria_passed}/{remote_criteria_total}", "== 59/59", remote_criteria_passed == remote_criteria_total == 59),
        criterion("Tier 4.31d canonical ingest passed", status_of(tier4_31d_ingest), "== pass", status_of(tier4_31d_ingest) == "pass"),
        criterion("Tier 4.31d temporal controls passed", scenario_statuses, "enabled/zero/frozen/reset == pass", set(scenario_statuses) == {"enabled", "zero_state", "frozen_state", "reset_each_update"} and all(value == "pass" for value in scenario_statuses.values())),
        criterion("Tier 4.31d synthetic fallback absent", tier4_31d_remote.get("summary", {}).get("synthetic_fallback_used"), "is false", tier4_31d_remote.get("summary", {}).get("synthetic_fallback_used") is False),
        criterion("Tier 4.29e replay bridge passed", status_of(tier4_29e), "== pass", status_of(tier4_29e) == "pass"),
        criterion("Tier 4.29e criteria complete", f"{tier4_29e.get('passed_criteria')}/{tier4_29e.get('total_criteria')}", "== 114/114", tier4_29e.get("passed_criteria") == tier4_29e.get("total_criteria") == 114),
        criterion("Tier 5.9c macro eligibility remains non-promoted", status_of(tier5_9c), "== fail with promotion failure", status_of(tier5_9c) == "fail" and "promotion" in str(tier5_9c.get("failure_reason", "")).lower()),
        criterion("Tier 4.22g active-trace optimization history visible", tier4_22g_summary.get("repaired_scale_blockers"), "contains SCALE-001..003", set(tier4_22g_summary.get("repaired_scale_blockers", [])) == {"SCALE-001", "SCALE-002", "SCALE-003"}),
        criterion("software v2.2 baseline is frozen", status_of(v22), "== frozen", status_of(v22) == "frozen"),
        criterion("native lifecycle baseline exists", BASELINE_NATIVE_V04.exists(), "file exists", BASELINE_NATIVE_V04.exists()),
        criterion("decision matrix covers replay/sleep/eligibility/4.31f/4.32", [row.candidate for row in rows], "all required candidates present", {row.candidate for row in rows} == {"native replay buffers", "native sleep-like replay", "native macro eligibility traces", "Tier 4.31f implementation gate", "Tier 4.32 mapping/resource model"}),
        criterion("no immediate replay/eligibility implementation authorized", [row.candidate for row in immediate_impls], "empty", not immediate_impls),
        criterion("Tier 4.32 is authorized next", authorize_432, "is true", authorize_432),
        criterion("no baseline freeze authorized", "no_freeze", "decision gate only", True),
    ]
    failed = [item for item in criteria if not item.passed]
    final_decision = {
        "tier4_31f": "deferred",
        "tier4_32": "authorized_next",
        "native_replay_buffers": "defer_until_measured_resource_or_autonomy_blocker",
        "native_sleep_like_replay": "defer_until_measured_retention_or_interference_blocker",
        "native_macro_eligibility": "defer_until_specific_credit_assignment_blocker",
        "baseline_freeze": "not_authorized",
    }

    return {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "status": "pass" if not failed else "fail",
        "criteria_passed": len(criteria) - len(failed),
        "criteria_total": len(criteria),
        "criteria": criteria,
        "failed_criteria": failed,
        "evidence_inputs": evidence,
        "decision_matrix": rows,
        "final_decision": final_decision,
        "recommended_next_step": (
            "Tier 4.32 mapping/resource model over measured 4.27-4.31 hardware data."
            if not failed
            else "Repair failed criteria before leaving Tier 4.31e."
        ),
        "claim_boundary": (
            "Tier 4.31e is a local documentation/decision gate. It does not implement "
            "native replay buffers, sleep-like replay, or macro eligibility traces; it "
            "does not run hardware; it does not prove speedup, multi-chip scaling, "
            "benchmark superiority, or full v2.2 hardware transfer; and it does not "
            "freeze a new baseline."
        ),
    }


def write_report(path: Path, results: dict[str, Any]) -> None:
    lines = [
        "# Tier 4.31e Native Replay/Eligibility Decision Closeout",
        "",
        f"- Generated: `{results['generated_at_utc']}`",
        f"- Runner revision: `{results['runner_revision']}`",
        f"- Status: **{results['status'].upper()}**",
        f"- Criteria: `{results['criteria_passed']}/{results['criteria_total']}`",
        f"- Recommended next step: {results['recommended_next_step']}",
        "",
        "## Claim Boundary",
        "",
        results["claim_boundary"],
        "",
        "## Final Decision",
        "",
    ]
    for key, value in results["final_decision"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Evidence Inputs", "", "| Source | Status | Role | Extracted Signal | Path |", "| --- | --- | --- | --- | --- |"])
    for item in results["evidence_inputs"]:
        lines.append(
            f"| `{item['source_id']}` | `{item['status']}` | {item['role']} | {item['extracted_signal']} | `{item['path']}` |"
        )
    lines.extend(["", "## Decision Matrix", "", "| Candidate | Decision | Measured Blocker | Evidence Basis | Next Action | Boundary |", "| --- | --- | --- | --- | --- | --- |"])
    for row in results["decision_matrix"]:
        lines.append(
            f"| `{row['candidate']}` | `{row['decision']}` | {row['measured_blocker']} | {row['evidence_basis']} | {row['next_action']} | {row['claim_boundary']} |"
        )
    lines.extend(["", "## Criteria", "", "| Criterion | Value | Rule | Pass | Note |", "| --- | --- | --- | --- | --- |"])
    for item in results["criteria"]:
        lines.append(
            f"| {item['name']} | `{item['value']}` | `{item['rule']}` | {'yes' if item['passed'] else 'no'} | {item.get('note', '')} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    results = build_results()
    results["output_dir"] = str(output_dir)

    safe_results = json_safe(results)
    write_json(output_dir / "tier4_31e_results.json", safe_results)
    write_report(output_dir / "tier4_31e_report.md", safe_results)
    write_csv(output_dir / "tier4_31e_summary.csv", [asdict(row) for row in decision_matrix()])
    write_csv(output_dir / "tier4_31e_evidence_inputs.csv", [asdict(row) for row in results["evidence_inputs"]])
    write_json(
        CONTROLLED / "tier4_31e_latest_manifest.json",
        {
            "tier": TIER,
            "runner_revision": RUNNER_REVISION,
            "generated_at_utc": results["generated_at_utc"],
            "status": results["status"],
            "manifest": str(output_dir / "tier4_31e_results.json"),
            "output_dir": str(output_dir),
        },
    )
    return results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=TIER)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    results = run(args)
    print(
        json.dumps(
            {
                "tier": TIER,
                "status": results["status"],
                "criteria": f"{results['criteria_passed']}/{results['criteria_total']}",
                "output_dir": results["output_dir"],
                "final_decision": results["final_decision"],
                "next": results["recommended_next_step"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if results["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
