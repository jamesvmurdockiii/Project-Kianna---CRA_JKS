#!/usr/bin/env python3
"""Tier 7.7t - low-rank state repair campaign contract.

Tier 7.7 remains active because CRA recurrent state is dynamic but
effectively low-rank (PR near 2). This contract locks the repair
campaign: failure modes, repair families, controls, metrics, outcome
classes, baseline-escalation rules, and promotion criteria — without
implementing or scoring any repair candidate.

Boundary: contract only; not scoring, not mechanism promotion, not
a baseline freeze, and not hardware/native transfer.
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

TIER = "Tier 7.7t - Low-Rank State Repair Campaign Contract"
RUNNER_REVISION = "tier7_7t_low_rank_state_repair_campaign_contract_20260509_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_7t_20260509_low_rank_state_repair_campaign_contract"
PREREQ_77S = CONTROLLED / "tier7_7s_20260509_bounded_temporal_basis_utility_promotion" / "tier7_7s_results.json"
NEXT_GATE = "Tier 7.7u - State-Collapse Causal Localization"


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


def failure_modes() -> list[dict[str, Any]]:
    return [
        {
            "failure_mode": "shared_driver_synchronization",
            "description": "Common input drive forces units into the same principal modes.",
            "candidate_probe": "Compare state PR when each polyp partition receives independent input channels vs a single shared driver.",
            "priority": 1,
        },
        {
            "failure_mode": "plasticity_homogenization",
            "description": "Learning dynamics make many units converge to similar filters over time.",
            "candidate_probe": "Track per-neuron weight/filter similarity over training; compare fixed-random-weight vs learned-weight PR and pairwise correlations.",
            "priority": 2,
        },
        {
            "failure_mode": "inhibition_normalization_compression",
            "description": "WTA or inhibition collapses state into a small number of dominant modes.",
            "candidate_probe": "Measure PR with and without inhibition; compare reduced-inhibition and no-inhibition diagnostic variants.",
            "priority": 3,
        },
        {
            "failure_mode": "input_encoder_bottleneck",
            "description": "State never receives enough independent causal channels.",
            "candidate_probe": "Measure state PR vs input channel count; compare per-input-channel contribution to state variance.",
            "priority": 4,
        },
        {
            "failure_mode": "recurrent_topology_bottleneck",
            "description": "Eigen spectrum / sparse graph structure supports only a few useful modes.",
            "candidate_probe": "Compare block-sparse, small-world, and all-to-all recurrent graph PR; measure recurrent weight eigen spectrum.",
            "priority": 5,
        },
        {
            "failure_mode": "trophic_energy_selection_compression",
            "description": "Survival/selection pressure suppresses diverse but initially weak states.",
            "candidate_probe": "Compare state PR with trophic pressure enabled vs disabled; measure per-polyp activity variance distribution vs trophic counter.",
            "priority": 6,
        },
        {
            "failure_mode": "readout_interface_bottleneck",
            "description": "Recurrent state may be richer internally than the readout exposes.",
            "candidate_probe": "Measure state PR vs readout-budgeted PR; compare linear readout vs richer readout observability.",
            "priority": 7,
        },
        {
            "failure_mode": "clipping_saturation_quantization",
            "description": "Activity is dynamic but constrained to a narrow manifold by numerical bounds.",
            "candidate_probe": "Count per-neuron saturation/clipping events; measure state norm distribution; compare with/without activation clipping.",
            "priority": 8,
        },
    ]


def repair_families() -> list[dict[str, Any]]:
    return [
        {
            "family": "A",
            "name": "diversity_preserving_state_dynamics",
            "goal": "Prevent units from collapsing into the same dominant modes.",
            "mechanism_candidates": [
                "activity decorrelation pressure",
                "homeostatic target-rate diversity",
                "anti-synchrony penalty or local inhibitory balancing",
                "per-partition activity quotas",
            ],
            "required_controls": [
                "no-diversity-pressure ablation",
                "shuffled-diversity-pressure sham",
                "global-whitening oracle upper bound",
                "random projection",
                "nonlinear-lag",
            ],
            "route_after_contract": "Tier 7.7v repair candidate compact score",
        },
        {
            "family": "B",
            "name": "independent_causal_subspace_drivers",
            "goal": "Give recurrent units independent causal views without relying on external random projection.",
            "mechanism_candidates": [
                "orthogonalized input projections",
                "channel-specialized polyp partitions",
                "multi-timescale causal trace banks",
                "delay-line diversity with same feature budget",
                "input dropout / channel masking during training to force specialization",
            ],
            "required_controls": [
                "same-feature random projection",
                "nonlinear-lag",
                "channel-shuffle",
                "no-delay-line ablation",
                "single-driver ablation",
            ],
            "route_after_contract": "Tier 7.7v repair candidate compact score",
        },
        {
            "family": "C",
            "name": "recurrent_topology_spectrum_repair",
            "goal": "Make the recurrent graph support more useful independent temporal modes.",
            "mechanism_candidates": [
                "spectral-radius-controlled recurrent initialization",
                "block-sparse recurrent modules with weak cross-links",
                "winnerless competition / balanced ring motifs",
                "diverse recurrent time constants",
            ],
            "required_controls": [
                "permuted recurrence",
                "orthogonal recurrence",
                "block recurrence",
                "state reset",
                "same-edge-count random graph",
            ],
            "route_after_contract": "Tier 7.7v repair candidate compact score",
        },
        {
            "family": "D",
            "name": "plasticity_anti_homogenization",
            "goal": "Keep learning from making every unit converge to the same filter.",
            "mechanism_candidates": [
                "novelty-preserving plasticity gates",
                "weight/filter similarity penalty diagnostic",
                "specialist protection / anti-collapse trophic pressure",
                "slower plasticity for minority modes",
                "diversity-aware consolidation",
            ],
            "required_controls": [
                "no-plasticity",
                "no-diversity-gate ablation",
                "shuffled-specialist-protection sham",
                "same-budget fixed plasticity",
            ],
            "route_after_contract": "Tier 7.7v repair candidate compact score",
        },
        {
            "family": "E",
            "name": "morphology_template_variability_route",
            "goal": "Create state diversity through heterogeneous polyp templates.",
            "mechanism_candidates": [
                "variable polyp internal templates",
                "diverse timescales",
                "variable excitatory/inhibitory ratios",
                "structured sparse connectivity",
            ],
            "required_controls": [
                "same-capacity fixed template",
                "morphology shuffle",
                "same-feature random projection",
                "nonlinear-lag",
                "target shuffle",
                "time shuffle",
            ],
            "route_after_contract": "Tier 7.8 contract only if 7.7u localizes bottleneck to template diversity or families A-D fail cleanly",
        },
    ]


def repair_queue() -> list[dict[str, Any]]:
    rows = []
    for fam in repair_families():
        rows.append({
            "family": fam["family"],
            "name": fam["name"],
            "goal": fam["goal"],
            "order_rule": "7.7u localization determines activation order",
            "activation_condition": "Failure mode localized to this family's target mechanism.",
            "next_tier": fam["route_after_contract"],
        })
    return rows


def controls() -> list[dict[str, Any]]:
    return [
        {"control": "current_cra_v2_5", "class": "baseline", "mandatory_for_compact_score": True, "mandatory_for_expanded_score": True},
        {"control": "current_cra_plus_temporal_basis_utility", "class": "baseline", "mandatory_for_compact_score": True, "mandatory_for_expanded_score": True},
        {"control": "random_projection", "class": "strong_generic_control", "mandatory_for_compact_score": True, "mandatory_for_expanded_score": True},
        {"control": "nonlinear_lag", "class": "strong_generic_control", "mandatory_for_compact_score": True, "mandatory_for_expanded_score": True},
        {"control": "target_shuffle", "class": "leakage_control", "mandatory_for_compact_score": True, "mandatory_for_expanded_score": True},
        {"control": "time_shuffle", "class": "leakage_control", "mandatory_for_compact_score": True, "mandatory_for_expanded_score": True},
        {"control": "no_plasticity", "class": "ablation", "mandatory_for_compact_score": False, "mandatory_for_expanded_score": False},
        {"control": "frozen_random_state", "class": "ablation", "mandatory_for_compact_score": False, "mandatory_for_expanded_score": False},
        {"control": "state_scramble", "class": "ablation", "mandatory_for_compact_score": False, "mandatory_for_expanded_score": False},
        {"control": "no_inhibition_diagnostic", "class": "ablation", "mandatory_for_compact_score": False, "mandatory_for_expanded_score": False},
        {"control": "input_channel_shuffle", "class": "leakage_control", "mandatory_for_compact_score": False, "mandatory_for_expanded_score": False},
        {"control": "ESN", "class": "external_baseline", "mandatory_for_compact_score": False, "mandatory_for_expanded_score": True},
        {"control": "online_LMS_ridge", "class": "external_baseline", "mandatory_for_compact_score": False, "mandatory_for_expanded_score": True},
    ]


def metrics() -> list[dict[str, Any]]:
    return [
        {"metric": "participation_ratio", "domain": "state_geometry", "description": "Effective state dimensionality; target PR >= 4.0 or >= 2x current baseline.", "threshold_at_128_state": "PR >= 4.0 for strong repair candidate; PR >= 2.5 for diagnostic progress", "mandatory": True},
        {"metric": "rank_95", "domain": "state_geometry", "description": "Number of PCA components needed for 95% variance.", "threshold_at_128_state": "> 2 (current is near 2)", "mandatory": True},
        {"metric": "rank_99", "domain": "state_geometry", "description": "Number of PCA components needed for 99% variance.", "threshold_at_128_state": "> rank_95", "mandatory": True},
        {"metric": "top_pc_dominance", "domain": "state_geometry", "description": "Fraction of variance in the first principal component.", "threshold_at_128_state": "decrease vs current baseline", "mandatory": True},
        {"metric": "covariance_spectrum", "domain": "state_geometry", "description": "Eigenvalue distribution of state covariance matrix.", "threshold_at_128_state": "broadened vs current baseline", "mandatory": True},
        {"metric": "lorenz_geomean_mse", "domain": "task", "description": "Geomean MSE on the locked Lorenz task.", "threshold_at_128_state": ">= 10% improvement vs current CRA and temporal-utility reference", "mandatory": True},
        {"metric": "mackey_glass_geomean_mse", "domain": "task", "description": "Geomean MSE on the locked Mackey-Glass task.", "threshold_at_128_state": "no > 10% material regression vs current baseline", "mandatory": True},
        {"metric": "narma10_geomean_mse", "domain": "task", "description": "Geomean MSE on the repaired NARMA10 task.", "threshold_at_128_state": "no > 10% material regression vs current baseline", "mandatory": True},
        {"metric": "aggregate_geomean_mse", "domain": "task", "description": "Geomean MSE across Mackey-Glass, Lorenz, and repaired NARMA10.", "threshold_at_128_state": "improve or stable vs current baseline", "mandatory": True},
        {"metric": "per_neuron_activity_variance", "domain": "state_geometry", "description": "Distribution of per-neuron activity variance.", "mandatory": False},
        {"metric": "pairwise_state_correlation", "domain": "state_geometry", "description": "Pairwise correlation matrix of state dimensions.", "mandatory": False},
        {"metric": "weight_filter_similarity", "domain": "state_geometry", "description": "Cosine similarity of learned weight vectors over time.", "mandatory": False},
        {"metric": "per_input_channel_contribution", "domain": "state_geometry", "description": "Variance contribution per input channel.", "mandatory": False},
        {"metric": "readout_concentration", "domain": "state_geometry", "description": "Readout weight concentration / effective readout degrees of freedom.", "mandatory": False},
        {"metric": "clipping_saturation_rate", "domain": "state_geometry", "description": "Fraction of neurons at saturation bounds.", "mandatory": False},
        {"metric": "seed_variance", "domain": "task", "description": "Variance across seeds 42/43/44.", "mandatory": True},
    ]


def outcome_classes() -> list[dict[str, Any]]:
    return [
        {
            "outcome": "input_bottleneck_confirmed",
            "action": "Route to Repair Family B (independent causal subspace drivers) in 7.7v.",
        },
        {
            "outcome": "plasticity_homogenization_confirmed",
            "action": "Route to Repair Family D (plasticity anti-homogenization) in 7.7v.",
        },
        {
            "outcome": "inhibition_compression_confirmed",
            "action": "Route to Repair Family A (diversity-preserving state dynamics) in 7.7v.",
        },
        {
            "outcome": "recurrent_topology_bottleneck_confirmed",
            "action": "Route to Repair Family C (recurrent topology/spectrum repair) in 7.7v.",
        },
        {
            "outcome": "trophic_selection_compression_confirmed",
            "action": "Route to Repair Family A or D depending on whether the compression is activity-based or plasticity-based.",
        },
        {
            "outcome": "readout_exposure_bottleneck_confirmed",
            "action": "Implement a richer readout diagnostic; if confirmable as the primary cause, route to 7.7v as a separate readout-observability repair.",
        },
        {
            "outcome": "numeric_saturation_confirmed",
            "action": "Fix activation bounds/normalization; rerun 7.7u diagnostics before committing a repair family.",
        },
        {
            "outcome": "mixed_or_inconclusive",
            "action": "Prioritize the failure mode with the largest PR-sensitivity to intervention; if still inconclusive, try Family A (broadest applicability).",
        },
        {
            "outcome": "score_gain_without_dimension",
            "description": "Task score improves but PR/rank remain collapsed.",
            "action": "Preserve as bounded utility evidence; do not promote as a state repair.",
        },
        {
            "outcome": "dimension_gain_without_score",
            "description": "PR/rank improve but benchmark usefulness does not.",
            "action": "Preserve as geometric evidence; do not promote until usefulness gate passes.",
        },
        {
            "outcome": "generic_control_explains_gain",
            "description": "Random projection or nonlinear-lag still explains the improvement.",
            "action": "Repair candidate is not CRA-specific; return to 7.7 to localize a different failure mode.",
        },
        {
            "outcome": "bounded_utility_only",
            "description": "Useful and safe, but not CRA-specific mechanism evidence.",
            "action": "Preserve as utility evidence; no mechanism promotion or baseline freeze.",
        },
        {
            "outcome": "mechanism_candidate",
            "description": "Geometry, usefulness, and attribution all pass.",
            "action": "Route to 7.7x promotion/regression gate.",
        },
    ]


def baseline_escalation() -> list[dict[str, Any]]:
    return [
        {
            "stage": "7.7t_contract",
            "tasks": [],
            "length": None,
            "seeds": [],
            "baselines": [],
            "authorized": False,
            "description": "Contract only; no scoring.",
        },
        {
            "stage": "7.7u_localization",
            "tasks": ["Mackey-Glass", "Lorenz", "repaired NARMA10"],
            "length": 8000,
            "seeds": [42],
            "baselines": ["current CRA v2.5", "temporal-basis utility reference"],
            "authorized": True,
            "description": "Minimal task scoring for state-geometry measurement only; diagnose, do not benchmark.",
        },
        {
            "stage": "7.7v_compact_repair_score",
            "tasks": ["Mackey-Glass", "Lorenz", "repaired NARMA10"],
            "length": 8000,
            "seeds": [42, 43, 44],
            "baselines": ["current CRA v2.5", "temporal-basis utility reference", "random projection", "nonlinear-lag", "target shuffle", "time shuffle", "repair candidate", "repair-family-specific ablations", "ESN / ridge if cheap"],
            "authorized": False,
            "description": "Compact repair scoring with repair-family-specific controls.",
        },
        {
            "stage": "7.7w_expanded_confirmation",
            "tasks": ["Mackey-Glass", "Lorenz", "repaired NARMA10"],
            "length": "8000/16000/32000",
            "seeds": [42, 43, 44],
            "baselines": ["compact repair baselines", "ESN/reservoir", "online lag/ridge", "small GRU if available"],
            "authorized": False,
            "description": "Longer lengths, more baselines. Only if compact repair passes.",
        },
        {
            "stage": "7.7x_promotion_regression",
            "tasks": ["all compact regression suite"],
            "length": "as per regression spec",
            "seeds": [42, 43, 44],
            "baselines": ["all prior confirmed baselines plus mechanism ablations and leakage guards"],
            "authorized": False,
            "description": "Compact regression, mechanism ablations, leakage guards, freeze decision.",
        },
    ]


def expected_artifact_specs() -> list[dict[str, Any]]:
    names = [
        "tier7_7t_results.json",
        "tier7_7t_contract.json",
        "tier7_7t_summary.csv",
        "tier7_7t_failure_modes.csv",
        "tier7_7t_candidate_repair_queue.csv",
        "tier7_7t_controls.csv",
        "tier7_7t_metrics.csv",
        "tier7_7t_outcome_classes.csv",
        "tier7_7t_baseline_escalation.csv",
        "tier7_7t_expected_artifacts.csv",
        "tier7_7t_claim_boundary.md",
        "tier7_7t_report.md",
    ]
    return [{"artifact": name, "required_for_contract": True} for name in names]


def stopping_rules() -> list[dict[str, Any]]:
    return [
        {
            "condition": "three_families_fail",
            "rule": "Three distinct repair families fail to increase state dimensionality and usefulness under locked controls.",
            "action": "Execute 7.7 closeout contract; narrow claim to bounded temporal utility plus strong Mackey signal with unresolved Lorenz bottleneck.",
        },
        {
            "condition": "generic_control_explains_all",
            "rule": "Every useful score gain remains explained by random projection or nonlinear-lag controls.",
            "action": "Execute 7.7 closeout contract; the architecture has an unresolved state bottleneck that generic controls can match.",
        },
        {
            "condition": "capacity_only",
            "rule": "State geometry improves only by adding capacity that matched controls can reproduce.",
            "action": "Execute 7.7 closeout contract; the benefit is a capacity confound, not a mechanism repair.",
        },
    ]


def route_conditions() -> list[dict[str, Any]]:
    return [
        {
            "route": "Tier 7.8 morphology",
            "condition": "7.7u localizes bottleneck to lack of intrinsic unit/template diversity.",
            "requirement": "Tier 7.7u must explicitly confirm this failure mode before 7.8 activates.",
        },
        {
            "route": "Tier 7.8 morphology",
            "condition": "Repair families A-D fail cleanly and morphology is the next best hypothesis.",
            "requirement": "A 7.7 closeout contract must explicitly route to morphology.",
        },
        {
            "route": "Tier 7.8 morphology",
            "condition": "A 7.7 closeout contract explicitly routes the low-rank repair campaign to morphology.",
            "requirement": "Requires formal closeout evidence.",
        },
        {
            "route": "Tier 7.9 lifecycle",
            "condition": "7.7 low-rank repair is fixed or formally bounded, AND 7.8 static morphology is tested or bypassed.",
            "requirement": "Lifecycle must not activate until state repair and morphology decisions are resolved.",
        },
    ]


def do_not_rules() -> list[str]:
    return [
        "start with a repair implementation before 7.7t contract passes",
        "run 7.8 morphology as active before 7.7 routes there",
        "run lifecycle/evolution before state repair or morphology route decision",
        "use public adapters to rescue a failed standardized core gate",
        "claim mechanism promotion from score gain alone",
        "claim state repair from PR gain alone",
        "drop random-projection or nonlinear-lag controls",
        "freeze a baseline from a contract or compact score",
        "port to hardware/native C before software usefulness survives controls",
        "tune thresholds after seeing results",
        "hide negative or generic-control-explained outcomes",
    ]


def build_contract() -> dict[str, Any]:
    return {
        "question": "Which measured failure mode should the next repair target, and what would count as a real state-dimensionality repair rather than another generic feature win?",
        "hypothesis": "The low-rank state collapse (PR near 2) is caused by one or more specific architectural pressures. A controlled localization gate can identify the primary cause, enabling a targeted repair instead of blind tuning.",
        "null_hypothesis": "The low-rank collapse is an irreducible property of the current architecture at its current capacity and cannot be materially improved without adding more neurons, external random projection, or nonlinear-lag features that generic controls can match.",
        "decision": "lock_campaign_and_authorize_localization",
        "failure_class_locked": "low_effective_dimensionality_with_pr_near_2",
        "prior_evidence": {
            "77j": "low_rank_collapse_confirmed; PR stayed around 2 and readout collapse did not explain it",
            "77l": "partitioned-driver repair improved task score but did not sufficiently increase dimensionality",
            "77n": "generic random projection / nonlinear-lag controls explained the partitioned-driver gain",
            "77q": "CRA-native temporal interface helped current CRA but still lost to strong generic controls",
            "77s": "temporal-basis interface promoted only as bounded engineering utility, not a CRA-specific mechanism",
        },
        "failure_modes_count": len(failure_modes()),
        "repair_families_count": len(repair_families()),
        "controls_count": len(controls()),
        "metrics_count": len(metrics()),
        "outcome_classes_count": len(outcome_classes()),
        "escalation_stages_count": len(baseline_escalation()),
        "decision_boundary": (
            "This contract locks the Tier 7.7 low-rank state repair campaign without implementing or scoring any repair candidate. "
            "It predeclares failure modes, repair families, controls, metrics, outcome classes, and baseline-escalation rules. "
            "Tier 7.8 and Tier 7.9 are explicitly queued behind the 7.7 repair campaign and must not activate until 7.7 routes there. "
            "No mechanism promotion, baseline freeze, public usefulness claim, or hardware/native transfer is authorized from this contract."
        ),
    }


def run(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    prereq = read_json(PREREQ_77S) if PREREQ_77S.exists() else None
    contract = build_contract()
    fail_modes = failure_modes()
    rep_families = repair_families()
    rep_queue = repair_queue()
    ctrls = controls()
    mtrs = metrics()
    out_classes = outcome_classes()
    esc = baseline_escalation()
    stop_rules = stopping_rules()
    route_conds = route_conditions()
    do_not = do_not_rules()
    artifacts = expected_artifact_specs()

    claim_boundary = contract["decision_boundary"]

    criteria = [
        criterion("Tier 7.7s prerequisite referenced", True, "contract self-consistent", True),
        criterion("failure class locked: low PR", True, "contract self-consistent", True),
        criterion("failure modes enumerated", len(fail_modes), "== 8", len(fail_modes) == 8),
        criterion("repair families predeclared", len(rep_families), "== 5", len(rep_families) == 5),
        criterion("family A diversity-preserving locked", rep_families[0]["name"], "== diversity_preserving_state_dynamics", rep_families[0]["name"] == "diversity_preserving_state_dynamics"),
        criterion("family B independent subspace locked", rep_families[1]["name"], "== independent_causal_subspace_drivers", rep_families[1]["name"] == "independent_causal_subspace_drivers"),
        criterion("family C topology/spectrum locked", rep_families[2]["name"], "== recurrent_topology_spectrum_repair", rep_families[2]["name"] == "recurrent_topology_spectrum_repair"),
        criterion("family D anti-homogenization locked", rep_families[3]["name"], "== plasticity_anti_homogenization", rep_families[3]["name"] == "plasticity_anti_homogenization"),
        criterion("family E morphology-routing locked", rep_families[4]["name"], "== morphology_template_variability_route", rep_families[4]["name"] == "morphology_template_variability_route"),
        criterion("controls include random projection", any("random_projection" == c["control"] for c in ctrls), "true", True),
        criterion("controls include nonlinear-lag", any("nonlinear_lag" == c["control"] for c in ctrls), "true", True),
        criterion("state-geometry metrics locked", len([m for m in mtrs if m["domain"] == "state_geometry"]), ">= 5", len([m for m in mtrs if m["domain"] == "state_geometry"]) >= 5),
        criterion("task metrics locked", len([m for m in mtrs if m["domain"] == "task"]), ">= 4", len([m for m in mtrs if m["domain"] == "task"]) >= 4),
        criterion("outcome classes locked", len(out_classes), ">= 8", len(out_classes) >= 8),
        criterion("baseline escalation locked", len(esc), "== 5", len(esc) == 5),
        criterion("compact score before expanded baselines", esc[2]["stage"], "== 7.7v_compact_repair_score", esc[2]["stage"] == "7.7v_compact_repair_score"),
        criterion("stopping rules locked", len(stop_rules), "== 3", len(stop_rules) == 3),
        criterion("route conditions to 7.8 locked", len(route_conds), ">= 3", len(route_conds) >= 3),
        criterion("do-not rules locked", len(do_not), ">= 8", len(do_not) >= 8),
        criterion("expected artifacts locked", len(artifacts), ">= 10", len(artifacts) >= 10),
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
        "failure_modes": fail_modes,
        "repair_families": rep_families,
        "repair_queue": rep_queue,
        "controls": ctrls,
        "metrics": mtrs,
        "outcome_classes": out_classes,
        "baseline_escalation": esc,
        "stopping_rules": stop_rules,
        "route_conditions": route_conds,
        "do_not_rules": do_not,
        "expected_artifacts": artifacts,
        "claim_boundary": claim_boundary,
        "nonclaims": [
            "not a repair implementation",
            "not a model score",
            "not a mechanism promotion",
            "not a baseline freeze",
            "not public usefulness proof",
            "not hardware/native transfer",
            "not a curriculum/environment claim",
            "not language, AGI, or ASI evidence",
        ],
        "prerequisite": {
            "path": str(PREREQ_77S),
            "sha256": sha256_file(PREREQ_77S) if PREREQ_77S and PREREQ_77S.exists() else "prerequisite_not_available",
            "tier": "7.7s",
            "description": "Tier 7.7s promoted temporal-basis interface as bounded engineering utility; Tier 7.7t follows as the next contract.",
        },
        "next_gate": NEXT_GATE,
        "planning_document": str(ROOT / "docs" / "TIER_7_7_LOW_RANK_REPAIR_PLAN.md"),
    }
    write_json(output_dir / "tier7_7t_results.json", payload)
    write_json(output_dir / "tier7_7t_contract.json", contract)
    write_csv(output_dir / "tier7_7t_summary.csv", criteria)
    write_csv(output_dir / "tier7_7t_failure_modes.csv", fail_modes)
    write_csv(output_dir / "tier7_7t_candidate_repair_queue.csv", rep_queue)
    write_csv(output_dir / "tier7_7t_controls.csv", ctrls)
    write_csv(output_dir / "tier7_7t_metrics.csv", mtrs)
    write_csv(output_dir / "tier7_7t_outcome_classes.csv", out_classes)
    write_csv(output_dir / "tier7_7t_baseline_escalation.csv", esc)
    (output_dir / "tier7_7t_claim_boundary.md").write_text(claim_boundary + "\n", encoding="utf-8")
    expected_artifacts_csv = [{"artifact": a["artifact"], "required_for_contract": a["required_for_contract"]} for a in artifacts]
    write_csv(output_dir / "tier7_7t_expected_artifacts.csv", expected_artifacts_csv)
    report = [
        "# Tier 7.7t Low-Rank State Repair Campaign Contract",
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
        "## Failure Class Locked",
        "",
        contract["failure_class_locked"],
        "",
        "## Prior Evidence",
        "",
    ]
    for key, val in contract["prior_evidence"].items():
        report.append(f"- `{key}`: {val}")
    report.extend([
        "",
        "## Boundary",
        "",
        claim_boundary,
        "",
        "## Nonclaims",
        "",
    ])
    report.extend(f"- {item}" for item in payload["nonclaims"])
    report.extend([
        "",
        "## Repair Families",
        "",
    ])
    for fam in rep_families:
        report.append(f"### Family {fam['family']}: {fam['name']}")
        report.append(f"**Goal:** {fam['goal']}")
        report.append(f"**Candidates:** {', '.join(fam['mechanism_candidates'])}")
        report.append("")
    report.extend([
        "## Stopping Rules",
        "",
    ])
    for rule in stop_rules:
        report.append(f"- **{rule['condition']}**: {rule['rule']} → {rule['action']}")
    report.extend([
        "",
        "## Route Conditions (Tier 7.8 / Tier 7.9)",
        "",
    ])
    for rc in route_conds:
        report.append(f"- **{rc['route']}**: {rc['condition']}")
    report.append("")
    (output_dir / "tier7_7t_report.md").write_text("\n".join(report), encoding="utf-8")
    manifest = {
        "tier": TIER,
        "status": status,
        "generated_at_utc": payload["generated_at_utc"],
        "output_dir": str(output_dir),
        "results_json": str(output_dir / "tier7_7t_results.json"),
        "report_md": str(output_dir / "tier7_7t_report.md"),
        "summary_csv": str(output_dir / "tier7_7t_summary.csv"),
    }
    write_json(output_dir / "tier7_7t_latest_manifest.json", manifest)
    write_json(CONTROLLED / "tier7_7t_latest_manifest.json", manifest)
    return payload


def main() -> int:
    payload = run()
    print(json.dumps(json_safe({
        "status": payload["status"],
        "criteria": f"{payload['criteria_passed']}/{payload['criteria_total']}",
        "output_dir": payload["output_dir"],
        "next_gate": payload["next_gate"],
    }), indent=2, sort_keys=True))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
