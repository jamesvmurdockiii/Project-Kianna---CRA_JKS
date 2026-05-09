#!/usr/bin/env python3
"""Tier 7.7o - generic temporal-interface reframing contract.

Tier 7.7n showed that the partitioned-driver task gain is explained by generic
same-feature random projection / nonlinear-lag interface controls. This contract
locks how that finding is handled before any tuning, promotion, or mechanism
implementation.
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

TIER = "Tier 7.7o - Generic Temporal-Interface Reframing Contract"
RUNNER_REVISION = "tier7_7o_generic_temporal_interface_reframing_contract_20260509_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_7o_20260509_generic_temporal_interface_reframing_contract"
PREREQ_77N = CONTROLLED / "tier7_7n_20260509_partitioned_driver_attribution_scoring_gate" / "tier7_7n_results.json"
NEXT_GATE = "Tier 7.7p - CRA-Native Temporal Interface Internalization Contract"


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


def finding_rows() -> list[dict[str, Any]]:
    return [
        {
            "finding": "partitioned_driver_not_promoted",
            "status": "locked",
            "reason": "Tier 7.7n classified the signal as generic_projection_explains_gain.",
            "action": "Do not freeze, promote, or transfer the partitioned-driver repair.",
        },
        {
            "finding": "random_projection_is_strong_control",
            "status": "locked",
            "reason": "Same-feature random projection beat the full partitioned driver on Lorenz at 128 units.",
            "action": "Treat as a stricter generic-basis control/baseline and as a design target for a separately contracted CRA-native temporal expansion mechanism.",
        },
        {
            "finding": "nonlinear_lag_interface_is_strong_control",
            "status": "locked",
            "reason": "Unpartitioned nonlinear/lag same-budget control beat the full partitioned driver on Lorenz at 128 units.",
            "action": "Treat as a feature-interface control and design target; do not call it a CRA mechanism until internalized, ablated, and regression-tested.",
        },
        {
            "finding": "driver_group_ablations_were_informative",
            "status": "locked",
            "reason": "Removing fast-trace and nonlinear driver groups hurt the full candidate, but this did not overcome the generic-interface explanation.",
            "action": "Carry driver-group ablation style forward for future mechanism gates.",
        },
    ]


def route_rows() -> list[dict[str, Any]]:
    return [
        {
            "route": "external_baseline_or_control",
            "decision": "required",
            "description": "Random projection and nonlinear/lag interface controls must be included as stronger baselines in future standardized temporal gates.",
            "promotion_allowed": False,
        },
        {
            "route": "cra_native_temporal_interface_internalization",
            "decision": "next_contract",
            "description": "Internalize the useful causal temporal-basis capability as organism-native dynamics, such as sparse temporal expansion microcircuits, polyp-local delay/trace branches, or recurrent sensory-basis units.",
            "promotion_allowed": "only after separate scoring, sham separation, compact regression, and benchmark rerun",
        },
        {
            "route": "optional_benchmark_adapter",
            "decision": "noncanonical_unless_explicit",
            "description": "A host-side causal temporal-interface adapter may be tested for diagnosis, but it cannot be promoted as CRA unless converted into organism-native dynamics.",
            "promotion_allowed": False,
        },
        {
            "route": "cra_internal_mechanism_candidate",
            "decision": "covered_by_next_contract",
            "description": "Any internalized version must be expressed as CRA dynamics, ablated, compared to random projection/nonlinear-lag controls, and pass compact regression before promotion.",
            "promotion_allowed": "only after separate scoring and compact regression",
        },
        {
            "route": "partitioned_driver_repair",
            "decision": "parked",
            "description": "The 7.7l/7.7n partitioned-driver repair is not promoted because its gain is generic-interface explainable.",
            "promotion_allowed": False,
        },
    ]


def fairness_rows() -> list[dict[str, Any]]:
    return [
        {"rule": "causal_inputs_only", "requirement": "No future targets, future observations beyond the forecast horizon, test labels, or post-hoc task hints."},
        {"rule": "same_train_test_splits", "requirement": "Use the locked chronological splits and seeds from the standardized scoreboard unless a new contract says otherwise."},
        {"rule": "budget_accounting", "requirement": "Report feature count, hidden/state count, readout parameters, and training update budget for every candidate and control."},
        {"rule": "baseline_fairness", "requirement": "Compare against ESN, online linear/perceptron/logistic where applicable, random projection, nonlinear-lag, and current CRA baseline."},
        {"rule": "no_adapter_rescue", "requirement": "An adapter cannot rescue a failed CRA mechanism claim unless it is separately internalized and ablated."},
        {"rule": "compact_regression_before_freeze", "requirement": "Any promoted interface/internal mechanism must pass compact regression before a baseline freeze."},
    ]


def outcome_rows() -> list[dict[str, Any]]:
    return [
        {
            "outcome": "generic_interface_reframed_as_baseline",
            "rule": "Random projection/nonlinear-lag remain external controls or baselines; no CRA promotion.",
            "allowed_claim": "The current Lorenz gain identified a stronger temporal-interface baseline/control, not a promoted CRA mechanism.",
        },
        {
            "outcome": "cra_native_internalization_authorized",
            "rule": "A new contract may internalize the useful causal temporal-interface capability as CRA-native dynamics while preserving random-projection and nonlinear-lag as controls.",
            "allowed_claim": "The generic-interface result justifies a new internalization candidate, not a promotion of the existing external control.",
        },
        {
            "outcome": "adapter_candidate_authorized",
            "rule": "A future contract explicitly tests a causal adapter against all controls and baselines.",
            "allowed_claim": "Adapter evidence only; no CRA-internal mechanism claim unless internalized later.",
        },
        {
            "outcome": "internal_mechanism_candidate_authorized",
            "rule": "A future contract expresses the interface as CRA-native dynamics with shams, ablations, and compact regression.",
            "allowed_claim": "Possible internal mechanism candidate, not yet promoted.",
        },
        {
            "outcome": "partitioned_driver_remains_parked",
            "rule": "7.7n generic-interface explanation remains the current result.",
            "allowed_claim": "Partitioned driver is parked as diagnostic evidence.",
        },
    ]


def expected_artifacts() -> list[dict[str, Any]]:
    names = [
        "tier7_7o_results.json",
        "tier7_7o_contract.json",
        "tier7_7o_summary.csv",
        "tier7_7o_findings.csv",
        "tier7_7o_routes.csv",
        "tier7_7o_fairness_rules.csv",
        "tier7_7o_outcome_classes.csv",
        "tier7_7o_claim_boundary.md",
        "tier7_7o_report.md",
    ]
    return [{"artifact": name, "required_for_contract": True} for name in names]


def build_contract(prereq: dict[str, Any]) -> dict[str, Any]:
    classification = prereq.get("classification") or {}
    diagnostics = classification.get("diagnostics") or {}
    return {
        "question": "How should CRA handle the Tier 7.7n finding that random projection and nonlinear/lag controls explain or exceed the partitioned-driver gain?",
        "hypothesis": "The safe interpretation is to treat random projection and nonlinear/lag interfaces as stronger controls/baselines while authorizing a separate contract to internalize the useful causal temporal-basis capability as CRA-native dynamics.",
        "null_hypothesis": "The generic-interface result can be promoted directly as a CRA mechanism without further controls, internalization, or regression.",
        "decision": "park_partitioned_driver_and_authorize_cra_native_temporal_interface_internalization",
        "prior_diagnostic": {
            "tier": "7.7n",
            "status": prereq.get("status"),
            "outcome": classification.get("outcome"),
            "full_lorenz_128_geomean_mse": diagnostics.get("full_lorenz_128_geomean_mse"),
            "random_projection_lorenz_128_geomean_mse": diagnostics.get("random_projection_lorenz_128_geomean_mse"),
            "nonlinear_lag_lorenz_128_geomean_mse": diagnostics.get("nonlinear_lag_lorenz_128_geomean_mse"),
        },
        "decision_boundary": "This contract closes the partitioned-driver repair path as non-promoted, makes random-projection/nonlinear-lag signals mandatory controls, and authorizes a new CRA-native temporal-interface internalization contract. It does not implement a new mechanism, score a model, freeze a baseline, claim external-baseline superiority, or transfer anything to hardware/native runtime.",
    }


def run(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    prereq = read_json(PREREQ_77N)
    contract = build_contract(prereq)
    findings = finding_rows()
    routes = route_rows()
    fairness = fairness_rows()
    outcomes = outcome_rows()
    artifacts = expected_artifacts()
    claim_boundary = contract["decision_boundary"]
    criteria = [
        criterion("Tier 7.7n prerequisite exists", str(PREREQ_77N), "exists", PREREQ_77N.exists()),
        criterion("Tier 7.7n prerequisite passed", prereq.get("status"), "== pass", prereq.get("status") == "pass"),
        criterion("Tier 7.7n generic-interface outcome", contract["prior_diagnostic"]["outcome"], "== generic_projection_explains_gain", contract["prior_diagnostic"]["outcome"] == "generic_projection_explains_gain"),
        criterion("question locked", contract["question"], "non-empty", bool(contract["question"])),
        criterion("decision locked", contract["decision"], "park and authorize internalization", contract["decision"] == "park_partitioned_driver_and_authorize_cra_native_temporal_interface_internalization"),
        criterion("partitioned driver parked", [row["finding"] for row in findings], "includes partitioned_driver_not_promoted", any(row["finding"] == "partitioned_driver_not_promoted" for row in findings)),
        criterion("random projection route locked", [row["route"] for row in routes], "includes external baseline/control", any(row["route"] == "external_baseline_or_control" for row in routes)),
        criterion("CRA-native internalization authorized", [row["route"] for row in routes], "next contract", any(row["route"] == "cra_native_temporal_interface_internalization" and row["decision"] == "next_contract" for row in routes)),
        criterion("fairness rules locked", [row["rule"] for row in fairness], "includes budget and baseline fairness", {"budget_accounting", "baseline_fairness"}.issubset({row["rule"] for row in fairness})),
        criterion("outcome classes locked", [row["outcome"] for row in outcomes], ">= 4 classes", len(outcomes) >= 4),
        criterion("expected artifacts locked", [row["artifact"] for row in artifacts], ">= 8 artifacts", len(artifacts) >= 8),
        criterion("no baseline freeze authorized", False, "false", True),
        criterion("no mechanism promotion authorized", False, "false", True),
        criterion("no hardware/native transfer authorized", False, "false", True),
    ]
    passed = sum(1 for item in criteria if item["passed"])
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
        "routes": routes,
        "fairness_rules": fairness,
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
        "prerequisite": {"path": str(PREREQ_77N), "sha256": sha256_file(PREREQ_77N), "status": prereq.get("status")},
        "next_gate": NEXT_GATE,
    }
    write_json(output_dir / "tier7_7o_results.json", payload)
    write_json(output_dir / "tier7_7o_contract.json", contract)
    write_csv(output_dir / "tier7_7o_summary.csv", criteria)
    write_csv(output_dir / "tier7_7o_findings.csv", findings)
    write_csv(output_dir / "tier7_7o_routes.csv", routes)
    write_csv(output_dir / "tier7_7o_fairness_rules.csv", fairness)
    write_csv(output_dir / "tier7_7o_outcome_classes.csv", outcomes)
    write_csv(output_dir / "tier7_7o_expected_artifacts.csv", artifacts)
    (output_dir / "tier7_7o_claim_boundary.md").write_text(claim_boundary + "\n", encoding="utf-8")
    report = [
        "# Tier 7.7o Generic Temporal-Interface Reframing Contract",
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
    (output_dir / "tier7_7o_report.md").write_text("\n".join(report), encoding="utf-8")
    manifest = {"tier": TIER, "status": status, "generated_at_utc": payload["generated_at_utc"], "output_dir": str(output_dir), "results_json": str(output_dir / "tier7_7o_results.json"), "report_md": str(output_dir / "tier7_7o_report.md"), "summary_csv": str(output_dir / "tier7_7o_summary.csv")}
    write_json(output_dir / "tier7_7o_latest_manifest.json", manifest)
    write_json(CONTROLLED / "tier7_7o_latest_manifest.json", manifest)
    return payload


def main() -> int:
    payload = run()
    print(json.dumps(json_safe({"status": payload["status"], "criteria": f"{payload['criteria_passed']}/{payload['criteria_total']}", "output_dir": payload["output_dir"], "next_gate": payload["next_gate"]}), indent=2, sort_keys=True))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
