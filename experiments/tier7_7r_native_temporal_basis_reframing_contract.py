#!/usr/bin/env python3
"""Tier 7.7r - native temporal-basis repair/reframing contract.

Tier 7.7q produced a useful-but-not-mechanism-proven result: the CRA-native
sparse temporal expansion improved over current CRA, but same-feature random
projection and nonlinear-lag controls still beat the key Lorenz score. This
contract preserves that signal without overclaiming it by splitting two
possible paths:

1. bounded engineering/interface utility promotion
2. stricter CRA-specific mechanism promotion

No new score, mechanism promotion, freeze, or hardware transfer is authorized
by this contract alone.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"

TIER = "Tier 7.7r - Native Temporal-Basis Repair/Reframing Contract"
RUNNER_REVISION = "tier7_7r_native_temporal_basis_reframing_contract_20260509_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_7r_20260509_native_temporal_basis_reframing_contract"
PREREQ_77Q = CONTROLLED / "tier7_7q_20260509_cra_native_temporal_interface_internalization_scoring_gate" / "tier7_7q_results.json"
NEXT_GATE = "Tier 7.7s - Bounded Temporal-Basis Utility Promotion/Regression Gate"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


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
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json_safe(row.get(key, "")) for key in fieldnames})


def sha256_file(path: Path) -> str | None:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def criterion(name: str, value: Any, rule: str, passed: bool, details: str = "") -> dict[str, Any]:
    return {
        "name": name,
        "criterion": name,
        "value": json_safe(value),
        "operator": rule,
        "rule": rule,
        "passed": bool(passed),
        "pass": bool(passed),
        "details": details,
        "note": details,
    }


def finding_rows(prereq: dict[str, Any]) -> list[dict[str, Any]]:
    diagnostics = ((prereq.get("classification") or {}).get("diagnostics") or {})
    return [
        {
            "finding": "native_candidate_is_useful_vs_current",
            "status": "locked",
            "evidence": f"current/native Lorenz ratio = {diagnostics.get('current_divided_by_native')}",
            "action": "Preserve as positive utility evidence; do not discard merely because strong controls beat it.",
        },
        {
            "finding": "native_candidate_not_mechanism_promoted",
            "status": "locked",
            "evidence": "random_projection and nonlinear_lag controls beat the key Lorenz score",
            "action": "Do not claim CRA-specific mechanism promotion from Tier 7.7q.",
        },
        {
            "finding": "ablation_signal_exists",
            "status": "locked",
            "evidence": f"ablations_hurt = {diagnostics.get('ablations_hurt')}",
            "action": "Carry ablation evidence forward as supporting, not sufficient, mechanism evidence.",
        },
        {
            "finding": "shuffle_guards_clean",
            "status": "locked",
            "evidence": f"target/native = {diagnostics.get('target_shuffle_divided_by_native')}; time/native = {diagnostics.get('time_shuffle_divided_by_native')}",
            "action": "Leakage and temporal-order guards support continued testing.",
        },
    ]


def decision_path_rows() -> list[dict[str, Any]]:
    return [
        {
            "path": "bounded_engineering_interface_utility",
            "decision": "authorized_for_next_gate",
            "question": "Does the temporal-basis interface reliably improve CRA without material regressions?",
            "promotion_name_if_passes": "CRA_TEMPORAL_INTERFACE_UTILITY_v0.1",
            "claim_if_passes": "A bounded causal temporal-basis interface improves the current CRA benchmark path under tested conditions.",
            "nonclaim": "Not a CRA-specific mechanism proof; not evidence that random projection/nonlinear-lag are biologically meaningful.",
        },
        {
            "path": "cra_specific_mechanism_promotion",
            "decision": "not_authorized_from_7_7q",
            "question": "Does a native CRA mechanism beat or causally separate from random-projection and nonlinear-lag controls?",
            "promotion_name_if_passes": "future only",
            "claim_if_passes": "CRA-specific temporal-interface dynamics add value beyond generic temporal bases.",
            "nonclaim": "7.7q did not satisfy this path.",
        },
        {
            "path": "park_temporal_interface_path",
            "decision": "fallback_if_utility_or_repair_fails",
            "question": "Should temporal-interface repair stop and the mechanism loop move to polyp morphology/template variability?",
            "promotion_name_if_passes": "none",
            "claim_if_passes": "Temporal-interface repair is not currently worth promoting.",
            "nonclaim": "Does not invalidate prior CRA mechanisms or hardware evidence.",
        },
    ]


def promotion_rule_rows() -> list[dict[str, Any]]:
    return [
        {
            "promotion_type": "bounded_engineering_interface_utility",
            "required_rule": "native or selected temporal-basis utility beats current CRA by >=10% on aggregate or on the locked target task, with no material regression >10% on Mackey/NARMA and clean shuffle guards",
            "requires_beating_random_projection": False,
            "requires_compact_regression": True,
            "allows_baseline_freeze": "only after separate promotion/regression gate",
        },
        {
            "promotion_type": "cra_specific_mechanism",
            "required_rule": "candidate beats or cleanly separates from random-projection and nonlinear-lag controls, internal ablations hurt, shuffle guards fail, and compact regression passes",
            "requires_beating_random_projection": True,
            "requires_compact_regression": True,
            "allows_baseline_freeze": "only after separate promotion/regression gate",
        },
        {
            "promotion_type": "none",
            "required_rule": "if utility fails, regressions appear, or controls show leakage, do not promote; park or redesign through a new contract",
            "requires_beating_random_projection": False,
            "requires_compact_regression": False,
            "allows_baseline_freeze": "never",
        },
    ]


def control_rows() -> list[dict[str, Any]]:
    return [
        {"control": "current_cra_baseline", "role": "utility baseline", "required": True},
        {"control": "same_feature_random_projection", "role": "strong generic-basis control", "required": True},
        {"control": "nonlinear_lag_unpartitioned", "role": "strong causal feature-interface control", "required": True},
        {"control": "no_delay_trace", "role": "temporal ablation", "required": True},
        {"control": "no_nonlinearity", "role": "branch nonlinearity ablation", "required": True},
        {"control": "target_shuffle", "role": "leakage guard", "required": True},
        {"control": "time_shuffle", "role": "temporal-order guard", "required": True},
    ]


def metric_rows() -> list[dict[str, Any]]:
    return [
        {"metric": "geomean_mse", "role": "primary score", "required": True},
        {"metric": "utility_vs_current_ratio", "role": "bounded utility decision", "required": True},
        {"metric": "strong_control_ratio", "role": "mechanism attribution decision", "required": True},
        {"metric": "task_regression_ratio", "role": "no-harm guard", "required": True},
        {"metric": "ablation_delta", "role": "causal support", "required": True},
        {"metric": "target_shuffle_ratio", "role": "leakage guard", "required": True},
        {"metric": "time_shuffle_ratio", "role": "temporal-order guard", "required": True},
        {"metric": "compact_regression_status", "role": "freeze guard", "required": True},
    ]


def outcome_rows() -> list[dict[str, Any]]:
    return [
        {
            "outcome": "utility_promotion_candidate_only",
            "rule": "Temporal basis reliably helps versus current CRA without regressions, but strong controls still win.",
            "allowed_claim": "Bounded engineering/interface utility candidate; not a CRA-specific mechanism.",
        },
        {
            "outcome": "mechanism_promotion_candidate",
            "rule": "Candidate beats strong controls, ablations hurt, no regressions, shuffles fail, compact regression passes later.",
            "allowed_claim": "CRA-specific mechanism candidate eligible for separate freeze decision.",
        },
        {
            "outcome": "park_temporal_interface",
            "rule": "Utility is weak, regressions appear, or leakage/controls fail.",
            "allowed_claim": "Temporal-interface repair is parked.",
        },
        {
            "outcome": "inconclusive",
            "rule": "Margins conflict or artifacts are insufficient.",
            "allowed_claim": "Diagnostic only.",
        },
    ]


def expected_artifacts() -> list[dict[str, Any]]:
    names = [
        "tier7_7r_results.json",
        "tier7_7r_contract.json",
        "tier7_7r_summary.csv",
        "tier7_7r_findings.csv",
        "tier7_7r_decision_paths.csv",
        "tier7_7r_promotion_rules.csv",
        "tier7_7r_controls.csv",
        "tier7_7r_metrics.csv",
        "tier7_7r_outcome_classes.csv",
        "tier7_7r_expected_artifacts.csv",
        "tier7_7r_claim_boundary.md",
        "tier7_7r_report.md",
    ]
    return [{"artifact": name, "required_for_contract": True} for name in names]


def build_contract(prereq: dict[str, Any]) -> dict[str, Any]:
    classification = prereq.get("classification") or {}
    diagnostics = classification.get("diagnostics") or {}
    utility_signal = bool(diagnostics.get("useful_vs_current") and diagnostics.get("guards_ok") and diagnostics.get("regressions_ok"))
    mechanism_blocked = not bool(diagnostics.get("beats_random_projection") and diagnostics.get("beats_nonlinear_lag"))
    return {
        "question": "How should CRA handle a temporal-basis candidate that helps current CRA but does not beat strong generic temporal controls?",
        "hypothesis": "The result should be preserved as a possible bounded engineering/interface utility while withholding CRA-specific mechanism promotion unless a later candidate beats or separates from random-projection and nonlinear-lag controls.",
        "null_hypothesis": "Any improvement over current CRA is sufficient for full mechanism promotion even if generic controls do better.",
        "decision": "split_utility_promotion_from_mechanism_promotion",
        "next_gate": NEXT_GATE,
        "prior_diagnostic": {
            "tier": "7.7q",
            "status": prereq.get("status"),
            "outcome": classification.get("outcome"),
            "native_lorenz_128_geomean_mse": diagnostics.get("native_lorenz_128_geomean_mse"),
            "current_divided_by_native": diagnostics.get("current_divided_by_native"),
            "random_projection_divided_by_native": diagnostics.get("random_projection_divided_by_native"),
            "nonlinear_lag_divided_by_native": diagnostics.get("nonlinear_lag_divided_by_native"),
            "utility_signal": utility_signal,
            "mechanism_blocked": mechanism_blocked,
        },
        "decision_boundary": "Tier 7.7r is a contract only. It preserves the Tier 7.7q positive utility signal, splits utility promotion from CRA-specific mechanism promotion, and authorizes a bounded utility promotion/regression gate. It does not promote a mechanism, freeze a baseline, claim external-baseline superiority, or transfer anything to hardware/native runtime.",
    }


def run(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    prereq = read_json(PREREQ_77Q)
    contract = build_contract(prereq)
    findings = finding_rows(prereq)
    paths = decision_path_rows()
    rules = promotion_rule_rows()
    controls = control_rows()
    metrics = metric_rows()
    outcomes = outcome_rows()
    artifacts = expected_artifacts()
    criteria = [
        criterion("Tier 7.7q prerequisite exists", str(PREREQ_77Q), "exists", PREREQ_77Q.exists()),
        criterion("Tier 7.7q prerequisite passed", prereq.get("status"), "== pass", prereq.get("status") == "pass"),
        criterion("Tier 7.7q outcome locked", contract["prior_diagnostic"]["outcome"], "== external_controls_still_win", contract["prior_diagnostic"]["outcome"] == "external_controls_still_win"),
        criterion("utility signal preserved", contract["prior_diagnostic"]["utility_signal"], "true", contract["prior_diagnostic"]["utility_signal"] is True),
        criterion("mechanism promotion blocked", contract["prior_diagnostic"]["mechanism_blocked"], "true", contract["prior_diagnostic"]["mechanism_blocked"] is True),
        criterion("decision splits utility from mechanism", contract["decision"], "split paths", contract["decision"] == "split_utility_promotion_from_mechanism_promotion"),
        criterion("bounded utility path locked", [row["path"] for row in paths], "includes utility path", "bounded_engineering_interface_utility" in {row["path"] for row in paths}),
        criterion("CRA-specific mechanism path locked", [row["path"] for row in paths], "includes mechanism path", "cra_specific_mechanism_promotion" in {row["path"] for row in paths}),
        criterion("promotion rules locked", [row["promotion_type"] for row in rules], "utility/mechanism/none", {"bounded_engineering_interface_utility", "cra_specific_mechanism", "none"}.issubset({row["promotion_type"] for row in rules})),
        criterion("strong controls retained", [row["control"] for row in controls], "random projection and nonlinear lag", {"same_feature_random_projection", "nonlinear_lag_unpartitioned"}.issubset({row["control"] for row in controls})),
        criterion("metrics locked", [row["metric"] for row in metrics], "utility and control ratios", {"utility_vs_current_ratio", "strong_control_ratio"}.issubset({row["metric"] for row in metrics})),
        criterion("outcome classes locked", [row["outcome"] for row in outcomes], ">= 4 classes", len(outcomes) >= 4),
        criterion("expected artifacts locked", [row["artifact"] for row in artifacts], ">= 10 artifacts", len(artifacts) >= 10),
        criterion("no baseline freeze authorized", False, "false", True),
        criterion("no hardware/native transfer authorized", False, "false", True),
    ]
    passed = sum(1 for row in criteria if row["passed"])
    status = "pass" if passed == len(criteria) else "fail"
    payload = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "status": status,
        "criteria": criteria,
        "criteria_passed": passed,
        "criteria_total": len(criteria),
        "output_dir": str(output_dir),
        "contract": contract,
        "findings": findings,
        "decision_paths": paths,
        "promotion_rules": rules,
        "controls": controls,
        "metrics": metrics,
        "outcome_classes": outcomes,
        "expected_artifacts": artifacts,
        "claim_boundary": contract["decision_boundary"],
        "nonclaims": [
            "not a mechanism promotion",
            "not a baseline freeze",
            "not hardware/native transfer",
            "not external-baseline superiority",
            "not broad public usefulness",
            "not language, AGI, or ASI evidence",
        ],
        "input_hashes": {"tier7_7q_results_sha256": sha256_file(PREREQ_77Q)},
    }
    prefix = "tier7_7r"
    write_json(output_dir / f"{prefix}_results.json", payload)
    write_json(output_dir / f"{prefix}_contract.json", contract)
    write_csv(output_dir / f"{prefix}_summary.csv", criteria)
    write_csv(output_dir / f"{prefix}_findings.csv", findings)
    write_csv(output_dir / f"{prefix}_decision_paths.csv", paths)
    write_csv(output_dir / f"{prefix}_promotion_rules.csv", rules)
    write_csv(output_dir / f"{prefix}_controls.csv", controls)
    write_csv(output_dir / f"{prefix}_metrics.csv", metrics)
    write_csv(output_dir / f"{prefix}_outcome_classes.csv", outcomes)
    write_csv(output_dir / f"{prefix}_expected_artifacts.csv", artifacts)
    (output_dir / f"{prefix}_claim_boundary.md").write_text(payload["claim_boundary"] + "\n", encoding="utf-8")
    report = [
        "# Tier 7.7r Native Temporal-Basis Repair/Reframing Contract",
        "",
        f"- Generated: `{payload['generated_at_utc']}`",
        f"- Status: **{status.upper()}**",
        f"- Criteria: `{passed}/{len(criteria)}`",
        f"- Next gate: `{NEXT_GATE}`",
        "",
        "## Decision",
        "",
        contract["decision_boundary"],
        "",
        "## Prior Diagnostic",
        "",
    ]
    for key, value in contract["prior_diagnostic"].items():
        report.append(f"- {key}: `{value}`")
    report.extend(["", "## Paths", ""])
    for row in paths:
        report.append(f"- `{row['path']}`: {row['decision']} - {row['claim_if_passes']}")
    report.extend(["", "## Nonclaims", ""])
    report.extend(f"- {item}" for item in payload["nonclaims"])
    report.append("")
    (output_dir / f"{prefix}_report.md").write_text("\n".join(report), encoding="utf-8")
    manifest = {
        "tier": TIER,
        "status": status,
        "generated_at_utc": payload["generated_at_utc"],
        "output_dir": str(output_dir),
        "results_json": str(output_dir / f"{prefix}_results.json"),
        "report_md": str(output_dir / f"{prefix}_report.md"),
        "summary_csv": str(output_dir / f"{prefix}_summary.csv"),
    }
    write_json(output_dir / f"{prefix}_latest_manifest.json", manifest)
    write_json(CONTROLLED / f"{prefix}_latest_manifest.json", manifest)
    return payload


def main() -> int:
    payload = run()
    print(json.dumps({"status": payload["status"], "criteria": f"{payload['criteria_passed']}/{payload['criteria_total']}", "next_gate": NEXT_GATE, "output_dir": payload["output_dir"]}, indent=2, sort_keys=True))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
