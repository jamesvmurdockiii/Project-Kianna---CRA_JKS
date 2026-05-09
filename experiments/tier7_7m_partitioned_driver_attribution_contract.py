#!/usr/bin/env python3
"""Tier 7.7m - partitioned-driver attribution contract.

Tier 7.7l found a useful task-performance gain from the partitioned-driver
candidate, but the predeclared state-dimensionality and diversity-pressure
attribution gates did not pass. This contract locks the next attribution probe
before any implementation, tuning, promotion, or architecture change.
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

TIER = "Tier 7.7m - Partitioned-Driver Attribution Contract"
RUNNER_REVISION = "tier7_7m_partitioned_driver_attribution_contract_20260509_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_7m_20260509_partitioned_driver_attribution_contract"
PREREQ_77L = CONTROLLED / "tier7_7l_20260509_effective_state_dimensionality_repair_scoring_gate" / "tier7_7l_results.json"
NEXT_GATE = "Tier 7.7n - Partitioned-Driver Attribution Scoring Gate"


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


def attribution_hypothesis_rows() -> list[dict[str, Any]]:
    return [
        {
            "hypothesis": "driver_partitioning_causes_gain",
            "status": "candidate_primary",
            "rationale": "Tier 7.7l partitioned causal drivers improved Lorenz, Mackey-Glass, and repaired NARMA versus the matched single-pool reference.",
            "required_probe": "partition labels shuffled or merged should lose while full partitioned driver retains the gain.",
        },
        {
            "hypothesis": "nonlinear_lag_feature_enrichment_causes_gain",
            "status": "candidate_primary",
            "rationale": "The 7.7l candidate changed the causal driver basis; gains may come from lag/nonlinear features rather than partitioned recurrence.",
            "required_probe": "unpartitioned nonlinear/lag same-feature-budget control must be compared to the full candidate.",
        },
        {
            "hypothesis": "readout_or_feature_budget_causes_gain",
            "status": "confound_to_rule_out",
            "rationale": "A larger or more useful interface can improve forecasting even if CRA-specific recurrence is not causal.",
            "required_probe": "same-feature-count random projection and readout-budget-matched controls must be included.",
        },
        {
            "hypothesis": "diversity_pressure_causes_gain",
            "status": "weakened_by_7_7l",
            "rationale": "Tier 7.7l diversity-disabled was only 1.0165x worse than the full candidate, so diversity pressure is not yet a clean explanation.",
            "required_probe": "repeat diversity-disabled and include stronger no-partition/no-diversity controls before attributing to diversity.",
        },
        {
            "hypothesis": "generic_basis_or_basis_luck_causes_gain",
            "status": "confound_to_rule_out",
            "rationale": "Prior Lorenz gates showed generic/permuted bases can be competitive; attribution requires separating candidate-specific structure from generic projections.",
            "required_probe": "permuted recurrence, orthogonal basis, block basis, and same-feature random projection controls must remain locked.",
        },
        {
            "hypothesis": "leakage_or_temporal_artifact_causes_gain",
            "status": "guard",
            "rationale": "Tier 7.7l target/time shuffles separated strongly, but all scoring gates must preserve these guards.",
            "required_probe": "target-shuffle and time-shuffle controls must fail strongly or the gate is blocked.",
        },
    ]


def variant_rows() -> list[dict[str, Any]]:
    return [
        {
            "variant": "partitioned_driver_full",
            "role": "candidate under attribution",
            "description": "The Tier 7.7l repair candidate: partitioned causal drivers with lag/nonlinear channels and deterministic diversity pressure.",
            "promotable": True,
        },
        {
            "variant": "partition_labels_shuffled",
            "role": "partition-causality sham",
            "description": "Keep feature budget and nonlinear/lag drivers but shuffle partition assignment so driver-to-state grouping should no longer be coherent.",
            "promotable": False,
        },
        {
            "variant": "partition_merged_unpartitioned",
            "role": "partition-ablation control",
            "description": "Use the same causal drivers without fixed partitions to test whether partitioning itself matters.",
            "promotable": False,
        },
        {
            "variant": "nonlinear_lag_unpartitioned_same_budget",
            "role": "feature-enrichment control",
            "description": "Retain lag/nonlinear driver features at the same budget, but remove partition-specific recurrence/state grouping.",
            "promotable": False,
        },
        {
            "variant": "linear_lag_partitioned",
            "role": "nonlinear-feature ablation",
            "description": "Keep partitions and lagged drivers but remove nonlinear transforms to test whether nonlinear enrichment is necessary.",
            "promotable": False,
        },
        {
            "variant": "diversity_pressure_disabled_repeat",
            "role": "diversity attribution repeat",
            "description": "Repeat the 7.7l diversity-disabled ablation under the attribution matrix.",
            "promotable": False,
        },
        {
            "variant": "same_feature_count_random_projection",
            "role": "interface-budget sham",
            "description": "Match feature count/readout budget with causal random projections but no CRA-specific partitioned driver structure.",
            "promotable": False,
        },
        {
            "variant": "readout_budget_matched_single_pool",
            "role": "baseline reference",
            "description": "Locked single-pool same-capacity reference with matched readout and training budget.",
            "promotable": False,
        },
        {
            "variant": "permuted_recurrence_ensemble",
            "role": "generic-basis sham",
            "description": "Preserve the prior generic recurrence sham family to test basis luck.",
            "promotable": False,
        },
        {
            "variant": "target_shuffle",
            "role": "leakage guard",
            "description": "Wrong target alignment guard.",
            "promotable": False,
        },
        {
            "variant": "time_shuffle",
            "role": "temporal-order guard",
            "description": "Wrong temporal order guard.",
            "promotable": False,
        },
    ]


def driver_group_ablation_rows() -> list[dict[str, Any]]:
    return [
        {
            "ablation": "remove_fast_trace_drivers",
            "purpose": "Measure whether short-timescale causal drivers carry the 7.7l gain.",
            "expected_if_causal": "Loss on Lorenz and/or NARMA relative to full candidate.",
        },
        {
            "ablation": "remove_slow_trace_drivers",
            "purpose": "Measure whether slow-timescale memory drivers carry the gain.",
            "expected_if_causal": "Loss on Mackey/NARMA or long-run Lorenz stability.",
        },
        {
            "ablation": "remove_lag_drivers",
            "purpose": "Measure whether explicit causal lag channels explain the improvement.",
            "expected_if_causal": "Loss on Mackey and NARMA plus possible Lorenz degradation.",
        },
        {
            "ablation": "remove_nonlinear_drivers",
            "purpose": "Measure whether nonlinear basis enrichment explains the improvement.",
            "expected_if_causal": "Loss on Lorenz and NARMA relative to linear partitioned control.",
        },
        {
            "ablation": "drop_one_partition_family",
            "purpose": "Check whether one partition family dominates the result rather than a distributed mechanism.",
            "expected_if_causal": "Specific, interpretable degradation without total collapse.",
        },
    ]


def task_rows() -> list[dict[str, Any]]:
    return [
        {
            "task": "lorenz",
            "role": "primary attribution target",
            "why": "7.7l produced the clearest repair signal here but did not prove the causal source.",
            "lengths": "8000,16000,32000",
            "seeds": "42,43,44",
            "required": True,
        },
        {
            "task": "mackey_glass",
            "role": "positive-control regression and attribution guard",
            "why": "7.7l improved Mackey versus single-pool; attribution should not destroy the established Mackey signal.",
            "lengths": "8000,16000,32000",
            "seeds": "42,43,44",
            "required": True,
        },
        {
            "task": "narma10_repaired_u02",
            "role": "nonlinear-memory regression and attribution guard",
            "why": "7.7l improved repaired NARMA versus single-pool; attribution must track whether lag/nonlinear drivers explain it.",
            "lengths": "8000,16000,32000",
            "seeds": "42,43,44",
            "required": True,
        },
    ]


def metric_rows() -> list[dict[str, Any]]:
    return [
        {"metric": "geomean_mse", "role": "primary standardized task score", "required": True},
        {"metric": "tail_mse", "role": "tail stability", "required": True},
        {"metric": "test_corr", "role": "prediction shape", "required": True},
        {"metric": "candidate_vs_control_mse_ratio", "role": "attribution margin", "required": True},
        {"metric": "driver_group_ablation_delta", "role": "causal driver attribution", "required": True},
        {"metric": "participation_ratio", "role": "state-geometry audit", "required": True},
        {"metric": "rank95_variance_count", "role": "state-rank audit", "required": True},
        {"metric": "top_pc_fraction", "role": "low-rank collapse audit", "required": True},
        {"metric": "state_kernel_alignment", "role": "candidate/control state similarity", "required": True},
        {"metric": "readout_weight_pr", "role": "readout concentration guard", "required": True},
        {"metric": "feature_count", "role": "interface-budget audit", "required": True},
        {"metric": "readout_parameter_count", "role": "fairness audit", "required": True},
        {"metric": "target_shuffle_guard", "role": "leakage guard", "required": True},
        {"metric": "time_shuffle_guard", "role": "temporal guard", "required": True},
        {"metric": "compact_regression_status", "role": "promotion guard if attribution passes", "required": True},
    ]


def pass_fail_rows() -> list[dict[str, Any]]:
    return [
        {
            "outcome": "driver_partition_attribution_confirmed",
            "rule": "Full partitioned driver beats partition-shuffled, merged/unpartitioned, same-feature random projection, and best generic sham by at least 5% on Lorenz; at least one coherent driver-group ablation hurts as predicted; Mackey/NARMA regressions stay within 10%; shuffle guards and compact regression pass.",
            "allowed_claim": "The 7.7l performance gain is attributable to causal driver partitioning under controlled software benchmark conditions.",
        },
        {
            "outcome": "nonlinear_lag_features_explain_gain",
            "rule": "Unpartitioned nonlinear/lag same-budget control matches full candidate, while removing lag/nonlinear drivers hurts.",
            "allowed_claim": "The gain is useful but explained by causal lag/nonlinear feature enrichment, not partitioned CRA recurrence; no mechanism promotion until reframed.",
        },
        {
            "outcome": "readout_or_feature_budget_explains_gain",
            "rule": "Same-feature-count random projection or widened-interface control matches or beats the full candidate.",
            "allowed_claim": "The gain is an interface/readout-budget effect, not a CRA-specific mechanism; do not promote.",
        },
        {
            "outcome": "diversity_pressure_attribution_confirmed",
            "rule": "Full candidate materially beats diversity-disabled repeat and the difference is not explained by partition/feature/readout controls.",
            "allowed_claim": "Diversity pressure contributes causally to the observed performance improvement, subject to compact regression.",
        },
        {
            "outcome": "generic_projection_explains_gain",
            "rule": "Permuted, orthogonal, block, or random projection shams match or beat the candidate.",
            "allowed_claim": "The observed improvement remains generic-basis explainable; no promotion.",
        },
        {
            "outcome": "task_gain_but_attribution_inconclusive",
            "rule": "Full candidate remains useful versus single-pool, but attribution controls disagree or margins are too small.",
            "allowed_claim": "Keep as a diagnostic candidate; no promotion, freeze, hardware transfer, or broad usefulness claim.",
        },
        {
            "outcome": "regression_or_leakage_blocked",
            "rule": "Mackey/NARMA regress materially, target/time shuffles do not fail, or compact regression fails.",
            "allowed_claim": "No attribution claim and no mechanism promotion.",
        },
        {
            "outcome": "negative_result",
            "rule": "Full candidate no longer improves over single-pool/reference under the attribution matrix.",
            "allowed_claim": "The 7.7l gain did not reproduce under attribution pressure; park the repair.",
        },
    ]


def expected_artifacts() -> list[dict[str, Any]]:
    names = [
        "tier7_7n_results.json",
        "tier7_7n_summary.csv",
        "tier7_7n_scoreboard.csv",
        "tier7_7n_score_summary.csv",
        "tier7_7n_attribution_margins.csv",
        "tier7_7n_driver_group_ablations.csv",
        "tier7_7n_state_geometry.csv",
        "tier7_7n_state_geometry_summary.csv",
        "tier7_7n_state_kernel_alignment.csv",
        "tier7_7n_readout_budget_audit.csv",
        "tier7_7n_sham_controls.csv",
        "tier7_7n_regression_summary.json",
        "tier7_7n_claim_boundary.md",
        "tier7_7n_report.md",
    ]
    return [{"artifact": name, "required_for_scoring_gate": True} for name in names]


def build_contract(prereq: dict[str, Any]) -> dict[str, Any]:
    classification = prereq.get("classification") or {}
    diagnostics = classification.get("diagnostics") or {}
    return {
        "question": "What caused the Tier 7.7l partitioned-driver performance gain: causal driver partitioning, lag/nonlinear feature enrichment, readout/interface budget, diversity pressure, or a generic basis confound?",
        "hypothesis": "If causal driver partitioning is responsible, the full candidate should beat partition-shuffled, merged/unpartitioned, same-feature random projection, and generic-basis controls while coherent driver-group ablations produce interpretable losses.",
        "null_hypothesis": "The 7.7l gain is explained by lag/nonlinear features alone, readout/interface budget, generic random basis effects, leakage, or non-reproducible scoring noise rather than CRA-specific partitioned drivers.",
        "mechanism_under_test": "partitioned_driver_full_attribution",
        "primary_reference": "Tier 7.7l partitioned_driver_diverse_recurrent_state versus single_pool_same_capacity",
        "prior_diagnostic": {
            "tier": "7.7l",
            "status": prereq.get("status"),
            "outcome": classification.get("outcome"),
            "lorenz_repair_128_geomean_mse": diagnostics.get("lorenz_repair_128_geomean_mse"),
            "lorenz_single_pool_128_geomean_mse": diagnostics.get("lorenz_single_pool_128_geomean_mse"),
            "repair_pr_128": diagnostics.get("repair_pr_128"),
            "diversity_disabled_divided_by_repair": diagnostics.get("diversity_disabled_divided_by_repair"),
        },
        "decision_boundary": "This contract authorizes only the Tier 7.7n attribution scoring gate. It does not authorize mechanism promotion, baseline freeze, hardware/native transfer, external-baseline superiority, broad public usefulness, language, AGI, or ASI claims.",
    }


def run(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    prereq = read_json(PREREQ_77L)
    contract = build_contract(prereq)
    hypotheses = attribution_hypothesis_rows()
    variants = variant_rows()
    ablations = driver_group_ablation_rows()
    tasks = task_rows()
    metrics = metric_rows()
    outcomes = pass_fail_rows()
    artifacts = expected_artifacts()
    claim_boundary = (
        "Tier 7.7m is a pre-registration contract for attributing the Tier 7.7l partitioned-driver task gain. It does not implement the attribution gate, score a new model, promote a mechanism, freeze a baseline, claim public usefulness, or transfer anything to hardware/native runtime."
    )
    criteria = [
        criterion("Tier 7.7l prerequisite exists", str(PREREQ_77L), "exists", PREREQ_77L.exists()),
        criterion("Tier 7.7l prerequisite passed", prereq.get("status"), "== pass", prereq.get("status") == "pass"),
        criterion("Tier 7.7l outcome requires attribution", contract["prior_diagnostic"]["outcome"], "== task_gain_without_dimension", contract["prior_diagnostic"]["outcome"] == "task_gain_without_dimension"),
        criterion("question locked", contract["question"], "non-empty", bool(contract["question"])),
        criterion("hypothesis locked", contract["hypothesis"], "non-empty", bool(contract["hypothesis"])),
        criterion("null hypothesis locked", contract["null_hypothesis"], "non-empty", bool(contract["null_hypothesis"])),
        criterion("primary mechanism named", contract["mechanism_under_test"], "== partitioned_driver_full_attribution", contract["mechanism_under_test"] == "partitioned_driver_full_attribution"),
        criterion("attribution hypotheses locked", [row["hypothesis"] for row in hypotheses], "includes primary and confounds", {"driver_partitioning_causes_gain", "nonlinear_lag_feature_enrichment_causes_gain", "readout_or_feature_budget_causes_gain", "generic_basis_or_basis_luck_causes_gain"}.issubset({row["hypothesis"] for row in hypotheses})),
        criterion("variants include partition controls", [row["variant"] for row in variants], "partition shuffled and merged", {"partition_labels_shuffled", "partition_merged_unpartitioned"}.issubset({row["variant"] for row in variants})),
        criterion("variants include feature controls", [row["variant"] for row in variants], "nonlinear/lag and linear controls", {"nonlinear_lag_unpartitioned_same_budget", "linear_lag_partitioned"}.issubset({row["variant"] for row in variants})),
        criterion("variants include interface controls", [row["variant"] for row in variants], "random projection and budget matched", {"same_feature_count_random_projection", "readout_budget_matched_single_pool"}.issubset({row["variant"] for row in variants})),
        criterion("driver-group ablations locked", [row["ablation"] for row in ablations], ">= 4 ablations", len(ablations) >= 4),
        criterion("tasks locked", [row["task"] for row in tasks], "Lorenz/Mackey/repaired NARMA", {row["task"] for row in tasks} == {"lorenz", "mackey_glass", "narma10_repaired_u02"}),
        criterion("metrics include attribution margin", [row["metric"] for row in metrics], "includes candidate_vs_control_mse_ratio", any(row["metric"] == "candidate_vs_control_mse_ratio" for row in metrics)),
        criterion("metrics include driver ablation delta", [row["metric"] for row in metrics], "includes driver_group_ablation_delta", any(row["metric"] == "driver_group_ablation_delta" for row in metrics)),
        criterion("metrics include budget audit", [row["metric"] for row in metrics], "feature/readout budget", {"feature_count", "readout_parameter_count"}.issubset({row["metric"] for row in metrics})),
        criterion("leakage guards locked", [row["variant"] for row in variants], "target/time shuffles", {"target_shuffle", "time_shuffle"}.issubset({row["variant"] for row in variants})),
        criterion("decision classes locked", [row["outcome"] for row in outcomes], ">= 7 classes", len(outcomes) >= 7),
        criterion("expected artifacts locked", [row["artifact"] for row in artifacts], ">= 12 artifacts", len(artifacts) >= 12),
        criterion("polyp morphology excluded", "separate future contract", "not part of Tier 7.7m", True),
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
        "attribution_hypotheses": hypotheses,
        "variants": variants,
        "driver_group_ablations": ablations,
        "tasks": tasks,
        "metrics": metrics,
        "outcome_classes": outcomes,
        "expected_artifacts": artifacts,
        "claim_boundary": claim_boundary,
        "nonclaims": [
            "not an attribution implementation",
            "not a model score",
            "not a mechanism promotion",
            "not a baseline freeze",
            "not a public usefulness claim",
            "not external-baseline superiority",
            "not hardware/native transfer",
            "not language, AGI, or ASI evidence",
        ],
        "prerequisite": {
            "path": str(PREREQ_77L),
            "sha256": sha256_file(PREREQ_77L),
            "status": prereq.get("status"),
        },
        "next_gate": NEXT_GATE,
    }
    write_json(output_dir / "tier7_7m_results.json", payload)
    write_json(output_dir / "tier7_7m_contract.json", contract)
    write_csv(output_dir / "tier7_7m_summary.csv", criteria)
    write_csv(output_dir / "tier7_7m_attribution_hypotheses.csv", hypotheses)
    write_csv(output_dir / "tier7_7m_variants.csv", variants)
    write_csv(output_dir / "tier7_7m_driver_group_ablations.csv", ablations)
    write_csv(output_dir / "tier7_7m_tasks.csv", tasks)
    write_csv(output_dir / "tier7_7m_metrics.csv", metrics)
    write_csv(output_dir / "tier7_7m_outcome_classes.csv", outcomes)
    write_csv(output_dir / "tier7_7m_expected_artifacts.csv", artifacts)
    (output_dir / "tier7_7m_claim_boundary.md").write_text(claim_boundary + "\n", encoding="utf-8")
    report = [
        "# Tier 7.7m Partitioned-Driver Attribution Contract",
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
    (output_dir / "tier7_7m_report.md").write_text("\n".join(report), encoding="utf-8")
    manifest = {
        "tier": TIER,
        "status": status,
        "generated_at_utc": payload["generated_at_utc"],
        "output_dir": str(output_dir),
        "results_json": str(output_dir / "tier7_7m_results.json"),
        "report_md": str(output_dir / "tier7_7m_report.md"),
        "summary_csv": str(output_dir / "tier7_7m_summary.csv"),
    }
    write_json(output_dir / "tier7_7m_latest_manifest.json", manifest)
    write_json(CONTROLLED / "tier7_7m_latest_manifest.json", manifest)
    return payload


def main() -> int:
    payload = run()
    print(json.dumps(json_safe({"status": payload["status"], "criteria": f"{payload['criteria_passed']}/{payload['criteria_total']}", "output_dir": payload["output_dir"], "next_gate": payload["next_gate"]}), indent=2, sort_keys=True))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
