#!/usr/bin/env python3
"""Tier 7.7p - CRA-native temporal-interface internalization contract.

Tier 7.7o authorized a new contract to internalize the useful temporal-basis
capability exposed by generic random projection and nonlinear/lag controls. This
contract defines the native mechanism, controls, pass/fail criteria, and freeze
boundary before any implementation or scoring.
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

TIER = "Tier 7.7p - CRA-Native Temporal-Interface Internalization Contract"
RUNNER_REVISION = "tier7_7p_cra_native_temporal_interface_internalization_contract_20260509_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_7p_20260509_cra_native_temporal_interface_internalization_contract"
PREREQ_77O = CONTROLLED / "tier7_7o_20260509_generic_temporal_interface_reframing_contract" / "tier7_7o_results.json"
NEXT_GATE = "Tier 7.7q - CRA-Native Temporal-Interface Internalization Scoring Gate"


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


def mechanism_rows() -> list[dict[str, Any]]:
    return [
        {
            "mechanism": "cra_native_sparse_temporal_expansion",
            "role": "primary candidate",
            "description": "A CRA-native sensory/temporal expansion stage implemented as causal polyp-local or reef-local temporal basis units: sparse fixed/slow-plastic sensory projections, multiple delay/trace constants, thresholded nonlinear branch units, and recurrent sensory-basis units feeding the existing CRA learning/readout path.",
            "native_requirement": "Must be represented as organism state/features that could map to PyNN/SpiNNaker LIF subcircuits or native runtime state; not a host-only preprocessing adapter.",
            "promotable": True,
        },
        {
            "mechanism": "temporal_expansion_no_nonlinearity",
            "role": "nonlinearity ablation",
            "description": "Same temporal expansion budget with nonlinear/threshold branch transforms disabled.",
            "promotable": False,
        },
        {
            "mechanism": "temporal_expansion_no_delays",
            "role": "delay/trace ablation",
            "description": "Same expansion budget without explicit causal delay/trace branches.",
            "promotable": False,
        },
        {
            "mechanism": "temporal_expansion_frozen_random",
            "role": "generic-basis sham",
            "description": "Same feature count with frozen random causal projection; carried forward from the 7.7n winning control.",
            "promotable": False,
        },
        {
            "mechanism": "nonlinear_lag_external_control",
            "role": "strong external/control baseline",
            "description": "The 7.7n nonlinear/lag unpartitioned same-budget control; must remain a control, not a CRA claim.",
            "promotable": False,
        },
        {
            "mechanism": "current_cra_baseline",
            "role": "baseline reference",
            "description": "Current frozen CRA software baseline before temporal-interface internalization.",
            "promotable": False,
        },
    ]


def implementation_constraint_rows() -> list[dict[str, Any]]:
    return [
        {"constraint": "causal_only", "requirement": "No future observations, labels, targets, or test outcomes may enter the temporal interface."},
        {"constraint": "organism_native", "requirement": "The mechanism must be represented as CRA internal state or PyNN/SpiNNaker-compatible microcircuit/state variables, not as an unclaimed host-side adapter."},
        {"constraint": "budget_matched", "requirement": "Report and match feature count, hidden/state count, readout parameters, and update budget against all strong controls."},
        {"constraint": "one_mechanism", "requirement": "Do not combine morphology variability, lifecycle changes, replay changes, or hardware/native changes into this gate."},
        {"constraint": "hardware_path_awareness", "requirement": "The design must be compatible with later PyNN/SpiNNaker or custom-runtime mapping, but this tier remains software evidence only."},
        {"constraint": "no_freeze_without_regression", "requirement": "Even a scoring pass must route to promotion/compact regression before baseline freeze."},
    ]


def task_rows() -> list[dict[str, Any]]:
    return [
        {"task": "lorenz", "role": "primary target", "why": "7.7n showed the strongest generic-interface gain here.", "lengths": "8000,16000,32000", "seeds": "42,43,44", "required": True},
        {"task": "mackey_glass", "role": "positive-control regression guard", "why": "CRA already has a localized Mackey signal; internalization must not break it.", "lengths": "8000,16000,32000", "seeds": "42,43,44", "required": True},
        {"task": "narma10_repaired_u02", "role": "nonlinear-memory regression guard", "why": "The finite repaired NARMA stream remains the locked memory benchmark.", "lengths": "8000,16000,32000", "seeds": "42,43,44", "required": True},
    ]


def control_rows() -> list[dict[str, Any]]:
    return [
        {"control": "same_feature_random_projection", "purpose": "The 7.7n strongest generic control; candidate must beat or match it with CRA-native attribution.", "pass_requirement": "Candidate must beat this control by at least 5% on Lorenz or show equal performance with stronger CRA-specific ablation separation."},
        {"control": "nonlinear_lag_unpartitioned", "purpose": "The 7.7n strong causal feature-interface control.", "pass_requirement": "Candidate must beat or match while preserving internal-mechanism ablation losses."},
        {"control": "current_cra_baseline", "purpose": "Show internalization improves current CRA rather than merely matching it.", "pass_requirement": "Candidate improves Lorenz and does not materially regress Mackey/NARMA."},
        {"control": "no_nonlinearity", "purpose": "Test nonlinear branch causality.", "pass_requirement": "If nonlinear branches are claimed, disabling them should hurt."},
        {"control": "no_delay_trace", "purpose": "Test temporal trace/delay causality.", "pass_requirement": "If temporal traces are claimed, removing them should hurt."},
        {"control": "target_shuffle", "purpose": "Leakage guard.", "pass_requirement": "Target shuffle must fail strongly."},
        {"control": "time_shuffle", "purpose": "Temporal-order guard.", "pass_requirement": "Time shuffle must fail strongly."},
    ]


def metric_rows() -> list[dict[str, Any]]:
    return [
        {"metric": "geomean_mse", "role": "primary standardized score", "required": True},
        {"metric": "tail_mse", "role": "tail stability", "required": True},
        {"metric": "test_corr", "role": "prediction shape", "required": True},
        {"metric": "candidate_vs_random_projection_ratio", "role": "strong-control separation", "required": True},
        {"metric": "candidate_vs_nonlinear_lag_ratio", "role": "strong-control separation", "required": True},
        {"metric": "ablation_delta", "role": "mechanism causality", "required": True},
        {"metric": "feature_count", "role": "budget accounting", "required": True},
        {"metric": "readout_parameter_count", "role": "budget accounting", "required": True},
        {"metric": "state_participation_ratio", "role": "state geometry audit", "required": True},
        {"metric": "compact_regression_status", "role": "promotion/freeze guard", "required": True},
    ]


def outcome_rows() -> list[dict[str, Any]]:
    return [
        {"outcome": "native_temporal_interface_promotable_candidate", "rule": "Candidate beats or cleanly matches random-projection/nonlinear-lag controls, ablations hurt as predicted, shuffles fail, regressions are bounded, and compact regression passes in a later promotion gate.", "allowed_claim": "CRA has a software-supported native temporal-interface candidate eligible for promotion/regression, not yet frozen."},
        {"outcome": "external_controls_still_win", "rule": "Random projection or nonlinear-lag controls still beat the native candidate.", "allowed_claim": "Internalization failed to beat the stronger controls; do not promote."},
        {"outcome": "adapter_only_signal", "rule": "A host/adapter form works but the CRA-native representation does not separate from controls.", "allowed_claim": "Adapter diagnostic only; no CRA mechanism claim."},
        {"outcome": "ablation_not_causal", "rule": "Candidate scores well but no internal ablation hurts.", "allowed_claim": "Performance is not causally attributed to the proposed mechanism."},
        {"outcome": "regression_or_leakage_blocked", "rule": "Mackey/NARMA regress, target/time shuffles pass, or compact regression fails.", "allowed_claim": "No promotion; blocked by controls."},
        {"outcome": "inconclusive", "rule": "Margins conflict or confidence is insufficient.", "allowed_claim": "Diagnostic only."},
    ]


def expected_artifacts() -> list[dict[str, Any]]:
    names = [
        "tier7_7q_results.json",
        "tier7_7q_summary.csv",
        "tier7_7q_scoreboard.csv",
        "tier7_7q_score_summary.csv",
        "tier7_7q_mechanism_ablations.csv",
        "tier7_7q_budget_audit.csv",
        "tier7_7q_state_geometry.csv",
        "tier7_7q_strong_controls.csv",
        "tier7_7q_regression_summary.json",
        "tier7_7q_claim_boundary.md",
        "tier7_7q_report.md",
    ]
    return [{"artifact": name, "required_for_scoring_gate": True} for name in names]


def build_contract(prereq: dict[str, Any]) -> dict[str, Any]:
    return {
        "question": "Can CRA internalize the temporal-basis capability exposed by random-projection/nonlinear-lag controls as organism-native dynamics rather than a host-side adapter?",
        "hypothesis": "A CRA-native sparse temporal expansion mechanism with causal delay/trace branches and thresholded nonlinear branch units can recover the useful temporal-interface signal while separating from random projection, nonlinear-lag controls, and internal ablations.",
        "null_hypothesis": "The useful signal remains an external feature/interface effect; native CRA internalization does not beat or causally separate from random projection/nonlinear-lag controls.",
        "mechanism_under_test": "cra_native_sparse_temporal_expansion",
        "prior_diagnostic": {"tier": "7.7o", "status": prereq.get("status"), "decision": (prereq.get("contract") or {}).get("decision")},
        "decision_boundary": "This contract authorizes only the Tier 7.7q software scoring gate. It does not implement the mechanism, promote it, freeze a baseline, claim external-baseline superiority, or transfer anything to hardware/native runtime.",
    }


def run(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    prereq = read_json(PREREQ_77O)
    contract = build_contract(prereq)
    mechanisms = mechanism_rows()
    constraints = implementation_constraint_rows()
    tasks = task_rows()
    controls = control_rows()
    metrics = metric_rows()
    outcomes = outcome_rows()
    artifacts = expected_artifacts()
    claim_boundary = contract["decision_boundary"]
    criteria = [
        criterion("Tier 7.7o prerequisite exists", str(PREREQ_77O), "exists", PREREQ_77O.exists()),
        criterion("Tier 7.7o prerequisite passed", prereq.get("status"), "== pass", prereq.get("status") == "pass"),
        criterion("Tier 7.7o authorized internalization", contract["prior_diagnostic"]["decision"], "authorizes internalization", contract["prior_diagnostic"]["decision"] == "park_partitioned_driver_and_authorize_cra_native_temporal_interface_internalization"),
        criterion("question locked", contract["question"], "non-empty", bool(contract["question"])),
        criterion("hypothesis locked", contract["hypothesis"], "non-empty", bool(contract["hypothesis"])),
        criterion("null hypothesis locked", contract["null_hypothesis"], "non-empty", bool(contract["null_hypothesis"])),
        criterion("primary mechanism named", contract["mechanism_under_test"], "== cra_native_sparse_temporal_expansion", contract["mechanism_under_test"] == "cra_native_sparse_temporal_expansion"),
        criterion("native mechanism present", [row["mechanism"] for row in mechanisms], "includes primary candidate", any(row["mechanism"] == "cra_native_sparse_temporal_expansion" for row in mechanisms)),
        criterion("strong controls retained", [row["control"] for row in controls], "random projection and nonlinear lag", {"same_feature_random_projection", "nonlinear_lag_unpartitioned"}.issubset({row["control"] for row in controls})),
        criterion("ablation controls locked", [row["control"] for row in controls], "no nonlinearity and no delay", {"no_nonlinearity", "no_delay_trace"}.issubset({row["control"] for row in controls})),
        criterion("tasks locked", [row["task"] for row in tasks], "Lorenz/Mackey/repaired NARMA", {row["task"] for row in tasks} == {"lorenz", "mackey_glass", "narma10_repaired_u02"}),
        criterion("budget constraints locked", [row["constraint"] for row in constraints], "budget matched and organism native", {"budget_matched", "organism_native"}.issubset({row["constraint"] for row in constraints})),
        criterion("metrics include strong-control ratios", [row["metric"] for row in metrics], "includes control ratios", {"candidate_vs_random_projection_ratio", "candidate_vs_nonlinear_lag_ratio"}.issubset({row["metric"] for row in metrics})),
        criterion("outcome classes locked", [row["outcome"] for row in outcomes], ">= 6 classes", len(outcomes) >= 6),
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
        "mechanisms": mechanisms,
        "implementation_constraints": constraints,
        "tasks": tasks,
        "controls": controls,
        "metrics": metrics,
        "outcome_classes": outcomes,
        "expected_artifacts": artifacts,
        "claim_boundary": claim_boundary,
        "nonclaims": [
            "not a mechanism implementation",
            "not a model score",
            "not a mechanism promotion",
            "not a baseline freeze",
            "not external-baseline superiority",
            "not hardware/native transfer",
            "not language, AGI, or ASI evidence",
        ],
        "prerequisite": {"path": str(PREREQ_77O), "sha256": sha256_file(PREREQ_77O), "status": prereq.get("status")},
        "next_gate": NEXT_GATE,
    }
    write_json(output_dir / "tier7_7p_results.json", payload)
    write_json(output_dir / "tier7_7p_contract.json", contract)
    write_csv(output_dir / "tier7_7p_summary.csv", criteria)
    write_csv(output_dir / "tier7_7p_mechanisms.csv", mechanisms)
    write_csv(output_dir / "tier7_7p_implementation_constraints.csv", constraints)
    write_csv(output_dir / "tier7_7p_tasks.csv", tasks)
    write_csv(output_dir / "tier7_7p_controls.csv", controls)
    write_csv(output_dir / "tier7_7p_metrics.csv", metrics)
    write_csv(output_dir / "tier7_7p_outcome_classes.csv", outcomes)
    write_csv(output_dir / "tier7_7p_expected_artifacts.csv", artifacts)
    (output_dir / "tier7_7p_claim_boundary.md").write_text(claim_boundary + "\n", encoding="utf-8")
    report = [
        "# Tier 7.7p CRA-Native Temporal-Interface Internalization Contract",
        "",
        f"- Generated: `{payload['generated_at_utc']}`",
        f"- Status: **{status.upper()}**",
        f"- Criteria: `{passed}/{len(criteria)}`",
        f"- Next gate: `{NEXT_GATE}`",
        "",
        "## Question",
        "",
        contract["question"],
        "",
        "## Boundary",
        "",
        claim_boundary,
        "",
        "## Nonclaims",
        "",
    ]
    report.extend(f"- {item}" for item in payload["nonclaims"])
    report.append("")
    (output_dir / "tier7_7p_report.md").write_text("\n".join(report), encoding="utf-8")
    manifest = {"tier": TIER, "status": status, "generated_at_utc": payload["generated_at_utc"], "output_dir": str(output_dir), "results_json": str(output_dir / "tier7_7p_results.json"), "report_md": str(output_dir / "tier7_7p_report.md"), "summary_csv": str(output_dir / "tier7_7p_summary.csv")}
    write_json(output_dir / "tier7_7p_latest_manifest.json", manifest)
    write_json(CONTROLLED / "tier7_7p_latest_manifest.json", manifest)
    return payload


def main() -> int:
    payload = run()
    print(json.dumps(json_safe({"status": payload["status"], "criteria": f"{payload['criteria_passed']}/{payload['criteria_total']}", "output_dir": payload["output_dir"], "next_gate": payload["next_gate"]}), indent=2, sort_keys=True))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
