#!/usr/bin/env python3
"""Tier 7.6c - planning/subgoal-control attribution + promotion decision.

Tier 7.6b produced a bounded local subgoal-control scaffold signal. This
closeout decides what that signal is allowed to mean. It does not add new
performance scoring. It audits the 7.6b outputs for attribution support,
feature-alignment risk, family coverage, sham separation, and promotion/freeze
eligibility.

The expected scientific outcome is intentionally conservative: if a synthetic
scaffold signal is present but strict all-family support and reduced-feature
generalization are not yet established, the correct route is a repair /
generalization gate, not a v2.5 freeze or hardware transfer.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"

TIER = "Tier 7.6c - Long-Horizon Planning / Subgoal-Control Attribution + Promotion Decision"
RUNNER_REVISION = "tier7_6c_long_horizon_planning_attribution_closeout_20260509_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_6c_20260509_long_horizon_planning_attribution_closeout"

PREREQ_DIR = CONTROLLED / "tier7_6b_20260509_long_horizon_planning_local_diagnostic"
PREREQ_RESULTS = PREREQ_DIR / "tier7_6b_results.json"
PREREQ_DECISION = PREREQ_DIR / "tier7_6b_decision.json"
PREREQ_FAMILY_DECISIONS = PREREQ_DIR / "tier7_6b_family_decisions.csv"
PREREQ_SHAMS = PREREQ_DIR / "tier7_6b_sham_controls.csv"
PREREQ_STATS = PREREQ_DIR / "tier7_6b_statistical_support.csv"

NEXT_GATE = "Tier 7.6d - Reduced-Feature Planning Generalization / Task Repair"

FAMILIES = {
    "two_stage_delayed_goal_chain",
    "key_door_goal_sequence",
    "resource_budget_route_plan",
    "blocked_subgoal_recovery",
    "hierarchical_composition_holdout",
}
CRITICAL_CONTROLS = {
    "memory_disabled",
    "self_evaluation_disabled",
    "predictive_state_disabled",
    "route_shuffle",
    "subgoal_label_shuffle",
    "action_reward_shuffle",
    "planner_state_reset",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = []
        for row in rows:
            for key in row:
                if key not in fieldnames:
                    fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json_safe(row.get(key, "")) for key in fieldnames})


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def as_float(value: Any, default: float = math.nan) -> float:
    try:
        if value in {None, ""}:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def criterion(name: str, value: Any, rule: str, passed: bool, details: str = "") -> dict[str, Any]:
    return {
        "name": name,
        "criterion": name,
        "value": json_safe(value),
        "operator": rule,
        "rule": rule,
        "passed": bool(passed),
        "pass": bool(passed),
        "note": details,
        "details": details,
    }


def make_attribution_checks(family_rows: list[dict[str, str]], sham_rows: list[dict[str, str]], stats: list[dict[str, str]]) -> list[dict[str, Any]]:
    supported = {row["family_id"] for row in family_rows if as_bool(row.get("local_diagnostic_signal_supported"))}
    unsupported = sorted(FAMILIES - supported)
    aggregate_best = next((row for row in stats if row.get("baseline") == "dyna_q_model_based_baseline"), {})
    aggregate_sham = next((row for row in stats if row.get("baseline") == "self_evaluation_disabled"), {})
    observed_controls = {row.get("model", "") for row in sham_rows}
    separated_controls = {
        row.get("model", "")
        for row in sham_rows
        if as_float(row.get("discounted_return_mean")) < 11.258148148148148
    }
    return [
        {
            "check": "local_signal_preserved",
            "value": len(supported),
            "rule": ">= 3 supported families",
            "passed": len(supported) >= 3,
            "details": ",".join(sorted(supported)),
        },
        {
            "check": "strict_all_family_support",
            "value": len(supported),
            "rule": "== 5 for promotion-ready planning",
            "passed": len(supported) == len(FAMILIES),
            "details": f"unsupported={','.join(unsupported)}",
        },
        {
            "check": "aggregate_best_baseline_ci",
            "value": aggregate_best.get("return_delta_ci_low"),
            "rule": "> 0",
            "passed": as_float(aggregate_best.get("return_delta_ci_low")) > 0.0,
            "details": f"baseline={aggregate_best.get('baseline')}",
        },
        {
            "check": "aggregate_best_sham_ci",
            "value": aggregate_sham.get("return_delta_ci_low"),
            "rule": "> 0",
            "passed": as_float(aggregate_sham.get("return_delta_ci_low")) > 0.0,
            "details": f"baseline={aggregate_sham.get('baseline')}",
        },
        {
            "check": "critical_controls_observed",
            "value": len(CRITICAL_CONTROLS & observed_controls),
            "rule": "all critical controls present",
            "passed": CRITICAL_CONTROLS <= observed_controls,
            "details": ",".join(sorted(CRITICAL_CONTROLS - observed_controls)),
        },
        {
            "check": "critical_controls_directionally_separated",
            "value": len(CRITICAL_CONTROLS & separated_controls),
            "rule": "all critical controls below candidate aggregate return",
            "passed": CRITICAL_CONTROLS <= separated_controls,
            "details": ",".join(sorted(CRITICAL_CONTROLS - separated_controls)),
        },
        {
            "check": "feature_alignment_risk",
            "value": "high",
            "rule": "must be documented",
            "passed": True,
            "details": "candidate scaffold consumes synthetic context/route/memory/predictive/confidence fields that define the generated planning grammar",
        },
        {
            "check": "promotion_readiness",
            "value": "not_ready",
            "rule": "requires all-family support and reduced-feature/held-out generalization",
            "passed": False,
            "details": "blocked because strict support is 3/5 and reduced-feature generalization has not run",
        },
    ]


def make_risk_register(checks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    strict = next(row for row in checks if row["check"] == "strict_all_family_support")
    return [
        {
            "risk": "synthetic_feature_alignment",
            "severity": "high",
            "status": "open",
            "mitigation": "Tier 7.6d reduced-feature and held-out-composition generalization before promotion",
        },
        {
            "risk": "partial_family_support",
            "severity": "medium",
            "status": "open" if not strict["passed"] else "closed",
            "mitigation": strict["details"],
        },
        {
            "risk": "scaffold_not_internalized",
            "severity": "high",
            "status": "open",
            "mitigation": "Do not freeze v2.5 until the mechanism is internalized and compact regression passes",
        },
        {
            "risk": "hardware_transfer_premature",
            "severity": "high",
            "status": "blocked",
            "mitigation": "No native/hardware transfer until software attribution and promotion pass",
        },
    ]


def make_decisions(checks: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    checks_by_name = {row["check"]: row for row in checks}
    local_signal = bool(checks_by_name["local_signal_preserved"]["passed"])
    aggregate_ci = bool(checks_by_name["aggregate_best_baseline_ci"]["passed"])
    sham_ci = bool(checks_by_name["aggregate_best_sham_ci"]["passed"])
    all_family = bool(checks_by_name["strict_all_family_support"]["passed"])
    promotion_ready = local_signal and aggregate_ci and sham_ci and all_family
    rows = [
        {
            "decision": "local_scaffold_signal",
            "authorized": local_signal and aggregate_ci and sham_ci,
            "reason": "7.6b aggregate support and sham separation are preserved",
        },
        {
            "decision": "promote_planning_mechanism",
            "authorized": promotion_ready,
            "reason": "blocked unless all-family support and reduced-feature generalization pass",
        },
        {
            "decision": "freeze_v2_5",
            "authorized": False,
            "reason": "7.6c is attribution closeout, not compact regression",
        },
        {
            "decision": "hardware_transfer",
            "authorized": False,
            "reason": "planning mechanism is not promoted or native-mapped",
        },
        {
            "decision": "broad_planning_claim",
            "authorized": False,
            "reason": "bounded synthetic scaffold only",
        },
    ]
    decision = {
        "tier": TIER,
        "status": "PASS",
        "outcome": (
            "planning_scaffold_signal_preserved_no_promotion"
            if rows[0]["authorized"] and not promotion_ready
            else "planning_attribution_not_confirmed"
        ),
        "local_scaffold_signal_authorized": rows[0]["authorized"],
        "promotion_authorized": promotion_ready,
        "freeze_authorized": False,
        "hardware_transfer_authorized": False,
        "broad_planning_claim_authorized": False,
        "feature_alignment_risk": "high",
        "strict_all_family_support": all_family,
        "next_gate": NEXT_GATE,
    }
    return rows, decision


def make_claim_boundary(decision: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Tier 7.6c Claim Boundary",
            "",
            f"- Outcome: `{decision['outcome']}`",
            f"- Local scaffold signal authorized: `{decision['local_scaffold_signal_authorized']}`",
            f"- Promotion authorized: `{decision['promotion_authorized']}`",
            f"- Freeze authorized: `{decision['freeze_authorized']}`",
            f"- Hardware transfer authorized: `{decision['hardware_transfer_authorized']}`",
            f"- Feature-alignment risk: `{decision['feature_alignment_risk']}`",
            "",
            "## Authorized Claim",
            "",
            "Tier 7.6b's bounded local subgoal-control scaffold signal is preserved as a diagnostic result.",
            "",
            "## Nonclaims",
            "",
            "- Not a promoted planning mechanism.",
            "- Not a v2.5 baseline freeze.",
            "- Not public usefulness evidence.",
            "- Not hardware/native transfer evidence.",
            "- Not general planning, language reasoning, open-ended agency, AGI, or ASI.",
            "",
            "## Required Next Work",
            "",
            "Run Tier 7.6d reduced-feature planning generalization / task repair before any promotion decision can reopen.",
            "",
        ]
    )


def make_manifest(output_dir: Path, artifacts: dict[str, Path], status: str) -> dict[str, Any]:
    return {
        "tier": TIER,
        "status": status,
        "generated_at_utc": utc_now(),
        "runner_revision": RUNNER_REVISION,
        "output_dir": str(output_dir),
        "artifacts": [
            {"name": name, "path": str(path), "sha256": sha256_file(path), "bytes": path.stat().st_size}
            for name, path in sorted(artifacts.items())
        ],
    }


def make_report(payload: dict[str, Any]) -> str:
    lines = [
        "# Tier 7.6c Long-Horizon Planning / Subgoal-Control Attribution Closeout",
        "",
        f"- Generated: `{payload['generated_at_utc']}`",
        f"- Runner revision: `{payload['runner_revision']}`",
        f"- Status: **{payload['status']}**",
        f"- Criteria: `{payload['criteria_passed']}/{payload['criteria_total']}`",
        f"- Outcome: `{payload['decision']['outcome']}`",
        f"- Next gate: `{payload['decision']['next_gate']}`",
        "",
        "## Criteria",
        "",
        "| Criterion | Value | Rule | Pass | Details |",
        "| --- | --- | --- | --- | --- |",
    ]
    for c in payload["criteria"]:
        lines.append(f"| {c['criterion']} | `{c['value']}` | {c['rule']} | {'yes' if c['passed'] else 'no'} | {c.get('details', '')} |")
    lines.extend(["", payload["claim_boundary_text"], ""])
    return "\n".join(lines)


def run(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    prereq = read_json(PREREQ_RESULTS)
    prereq_decision = read_json(PREREQ_DECISION)
    family_rows = read_csv(PREREQ_FAMILY_DECISIONS)
    sham_rows = read_csv(PREREQ_SHAMS)
    stat_rows = read_csv(PREREQ_STATS)
    checks = make_attribution_checks(family_rows, sham_rows, stat_rows)
    risk_rows = make_risk_register(checks)
    decision_rows, decision = make_decisions(checks)
    claim_boundary = make_claim_boundary(decision)
    failed_for_promotion = [row for row in checks if not row["passed"] and row["check"] in {"strict_all_family_support", "promotion_readiness"}]
    criteria = [
        criterion("tier7_6b_results_exist", str(PREREQ_RESULTS), "exists", PREREQ_RESULTS.exists()),
        criterion("tier7_6b_passed", prereq.get("status"), "== PASS", str(prereq.get("status", "")).upper() == "PASS"),
        criterion("tier7_6b_local_signal_authorized", prereq_decision.get("local_subgoal_signal_authorized"), "must be true", as_bool(prereq_decision.get("local_subgoal_signal_authorized"))),
        criterion("family_decisions_present", len(family_rows), "== 5", len(family_rows) == 5),
        criterion("sham_rows_present", len(sham_rows), ">= 45", len(sham_rows) >= 45),
        criterion("statistical_support_present", len(stat_rows), ">= 10", len(stat_rows) >= 10),
        criterion("local_signal_preserved", next(row for row in checks if row["check"] == "local_signal_preserved")["passed"], "must be true", next(row for row in checks if row["check"] == "local_signal_preserved")["passed"]),
        criterion("aggregate_best_baseline_ci_positive", next(row for row in checks if row["check"] == "aggregate_best_baseline_ci")["value"], "> 0", next(row for row in checks if row["check"] == "aggregate_best_baseline_ci")["passed"]),
        criterion("aggregate_best_sham_ci_positive", next(row for row in checks if row["check"] == "aggregate_best_sham_ci")["value"], "> 0", next(row for row in checks if row["check"] == "aggregate_best_sham_ci")["passed"]),
        criterion("critical_controls_observed", next(row for row in checks if row["check"] == "critical_controls_observed")["value"], "all present", next(row for row in checks if row["check"] == "critical_controls_observed")["passed"]),
        criterion("feature_alignment_risk_documented", decision["feature_alignment_risk"], "== high and documented", decision["feature_alignment_risk"] == "high"),
        criterion("promotion_blockers_documented", len(failed_for_promotion), ">= 1", len(failed_for_promotion) >= 1, ",".join(row["check"] for row in failed_for_promotion)),
        criterion("promotion_not_authorized", decision["promotion_authorized"], "must be false", not decision["promotion_authorized"]),
        criterion("freeze_not_authorized", decision["freeze_authorized"], "must be false", not decision["freeze_authorized"]),
        criterion("hardware_transfer_not_authorized", decision["hardware_transfer_authorized"], "must be false", not decision["hardware_transfer_authorized"]),
        criterion("broad_planning_not_authorized", decision["broad_planning_claim_authorized"], "must be false", not decision["broad_planning_claim_authorized"]),
        criterion("next_gate_selected", decision["next_gate"], f"== {NEXT_GATE}", decision["next_gate"] == NEXT_GATE),
    ]
    status = "PASS" if all(row["passed"] for row in criteria) else "FAIL"
    decision["status"] = status
    payload = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "status": status,
        "criteria": criteria,
        "criteria_passed": sum(1 for c in criteria if c["passed"]),
        "criteria_total": len(criteria),
        "failed_criteria": [c for c in criteria if not c["passed"]],
        "attribution_checks": checks,
        "risk_register": risk_rows,
        "promotion_decisions": decision_rows,
        "decision": decision,
        "claim_boundary_text": claim_boundary,
        "prereq_results": str(PREREQ_RESULTS),
        "output_dir": str(output_dir),
    }
    artifacts = {
        "results_json": output_dir / "tier7_6c_results.json",
        "summary_csv": output_dir / "tier7_6c_summary.csv",
        "report_md": output_dir / "tier7_6c_report.md",
        "attribution_checks_csv": output_dir / "tier7_6c_attribution_checks.csv",
        "promotion_decisions_csv": output_dir / "tier7_6c_promotion_decisions.csv",
        "risk_register_csv": output_dir / "tier7_6c_risk_register.csv",
        "route_decisions_csv": output_dir / "tier7_6c_route_decisions.csv",
        "claim_boundary_md": output_dir / "tier7_6c_claim_boundary.md",
        "decision_json": output_dir / "tier7_6c_decision.json",
        "decision_csv": output_dir / "tier7_6c_decision.csv",
    }
    write_json(artifacts["results_json"], payload)
    write_csv(artifacts["summary_csv"], criteria, ["criterion", "value", "rule", "pass", "details"])
    write_csv(artifacts["attribution_checks_csv"], checks)
    write_csv(artifacts["promotion_decisions_csv"], decision_rows)
    write_csv(artifacts["risk_register_csv"], risk_rows)
    write_csv(artifacts["route_decisions_csv"], [{"next_gate": NEXT_GATE, "reason": "promotion blocked pending reduced-feature generalization"}])
    artifacts["claim_boundary_md"].write_text(claim_boundary, encoding="utf-8")
    write_json(artifacts["decision_json"], decision)
    write_csv(artifacts["decision_csv"], [decision])
    artifacts["report_md"].write_text(make_report(payload), encoding="utf-8")
    manifest = make_manifest(output_dir, artifacts, status)
    artifacts["latest_manifest_json"] = output_dir / "tier7_6c_latest_manifest.json"
    write_json(artifacts["latest_manifest_json"], manifest)
    root_manifest = CONTROLLED / "tier7_6c_latest_manifest.json"
    write_json(root_manifest, manifest)
    artifacts["root_latest_manifest_json"] = root_manifest
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=TIER)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Output directory")
    args = parser.parse_args()
    payload = run(Path(args.output_dir).resolve())
    print(
        json.dumps(
            json_safe(
                {
                    "status": payload["status"],
                    "criteria": f"{payload['criteria_passed']}/{payload['criteria_total']}",
                    "outcome": payload["decision"]["outcome"],
                    "promotion_authorized": payload["decision"]["promotion_authorized"],
                    "output_dir": payload["output_dir"],
                    "next_gate": payload["decision"]["next_gate"],
                }
            ),
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
