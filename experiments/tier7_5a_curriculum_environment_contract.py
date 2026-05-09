#!/usr/bin/env python3
"""Tier 7.5a - curriculum/environment generator contract.

Contract-only gate for generated task families. This does not implement or
score curriculum learning. It locks the generator requirements, train/held-out
splits, difficulty schedule, baselines, metrics, leakage controls, and artifacts
before any generated-task results can be interpreted.
"""

from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"

TIER = "Tier 7.5a - Curriculum / Environment Generator Contract"
RUNNER_REVISION = "tier7_5a_curriculum_environment_contract_20260509_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_5a_20260509_curriculum_environment_contract"

PREREQ = CONTROLLED / "tier7_4h_20260509_policy_action_attribution_closeout" / "tier7_4h_results.json"
NEXT_GATE = "Tier 7.5b - Curriculum / Environment Generator Implementation Preflight"


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


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    if fieldnames is None:
        keys: list[str] = []
        for row in rows:
            for key in row:
                if key not in keys:
                    keys.append(key)
        fieldnames = keys
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json_safe(row.get(key, "")) for key in fieldnames})


def sha256_file(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def criterion(name: str, value: Any, rule: str, passed: bool, details: str = "") -> dict[str, Any]:
    return {
        "name": name,
        "criterion": name,
        "value": value,
        "operator": rule,
        "rule": rule,
        "passed": bool(passed),
        "pass": bool(passed),
        "note": details,
        "details": details,
    }


def task_family_rows() -> list[dict[str, Any]]:
    return [
        {
            "family_id": "generated_delayed_credit",
            "capability_pressure": "delayed credit and causal reward timing",
            "generator_knobs": "delay_steps, reward_sparsity, distractor_rate, cue_noise",
            "primary_metrics": "tail_accuracy,recovery_steps,credit_assignment_error",
            "baseline_classes": "lag_ridge,online_logistic,reservoir,small_gru,stpd_only,current_cra",
            "heldout_rule": "withhold delay/noise combinations and seeds before scoring",
        },
        {
            "family_id": "generated_hidden_context_reentry",
            "capability_pressure": "working memory, keyed context, reentry",
            "generator_knobs": "context_count,key_overlap,distractor_gap,reentry_gap,slot_pressure",
            "primary_metrics": "reentry_accuracy,forgetting_delta,reacquisition_steps",
            "baseline_classes": "explicit_lag_memory,reservoir,small_gru,current_cra,memory_ablation",
            "heldout_rule": "withhold context-key mappings and recurrence schedules",
        },
        {
            "family_id": "generated_nonstationary_switching",
            "capability_pressure": "adaptation, recovery, uncertainty, lifecycle hooks",
            "generator_knobs": "switch_interval,regime_count,noise,drift_rate,return_probability",
            "primary_metrics": "post_switch_recovery,tail_accuracy,variance,collapse_rate",
            "baseline_classes": "ewma,online_logistic,reservoir,small_gru,current_cra,sham_controls",
            "heldout_rule": "withhold switch schedules and regime-return patterns",
        },
        {
            "family_id": "generated_compositional_reuse",
            "capability_pressure": "module routing, composition, skill reuse",
            "generator_knobs": "primitive_count,composition_depth,route_ambiguity,heldout_combinations",
            "primary_metrics": "heldout_composition_success,module_reuse_score,route_error",
            "baseline_classes": "monolithic_cra,route_shuffle,small_gru,reservoir,oracle_router",
            "heldout_rule": "withhold compositions while exposing primitives",
        },
        {
            "family_id": "generated_policy_action_cost",
            "capability_pressure": "action choice, asymmetric cost, delayed consequence",
            "generator_knobs": "action_count,cost_asymmetry,event_rate,latency_penalty,confidence_noise",
            "primary_metrics": "expected_utility,regret,action_rate,false_positive_cost,missed_event_cost",
            "baseline_classes": "bandit,threshold_policy,online_logistic,reservoir,small_gru,current_cra",
            "heldout_rule": "withhold cost/action regimes and event schedules",
        },
        {
            "family_id": "generated_predictive_binding",
            "capability_pressure": "pre-reward representation, predictive binding, anomaly anticipation",
            "generator_knobs": "masked_channels,cross_modal_lag,anomaly_rate,latent_factor_count",
            "primary_metrics": "masked_recovery,next_state_mse,downstream_sample_efficiency",
            "baseline_classes": "auto_regressive_ridge,reservoir,small_gru,random_projection,current_cra",
            "heldout_rule": "withhold latent-factor combinations and anomaly timing",
        },
    ]


def difficulty_rows() -> list[dict[str, Any]]:
    return [
        {
            "level": 0,
            "name": "sanity_easy",
            "purpose": "verify generator and scoring are wired",
            "knob_policy": "short delays, low noise, single context/regime, no heldout claim",
            "promotion_use": "debug only",
        },
        {
            "level": 1,
            "name": "baseline_competitive",
            "purpose": "simple baselines should remain viable",
            "knob_policy": "moderate noise/delay and low ambiguity",
            "promotion_use": "required fairness check",
        },
        {
            "level": 2,
            "name": "memory_or_adaptation_pressure",
            "purpose": "force use of context, recurrence, or adaptation",
            "knob_policy": "longer gaps, recurring regimes, distractors, slot pressure",
            "promotion_use": "primary generated-task scoring starts here",
        },
        {
            "level": 3,
            "name": "composition_or_policy_pressure",
            "purpose": "test reuse, routing, and cost-aware action",
            "knob_policy": "heldout compositions, asymmetric costs, delayed consequences",
            "promotion_use": "mechanism comparison tier",
        },
        {
            "level": 4,
            "name": "ood_generalization",
            "purpose": "anti-overfitting and held-out family test",
            "knob_policy": "withheld generator modes and unseen combinations",
            "promotion_use": "claim-boundary gate",
        },
    ]


def split_rows() -> list[dict[str, Any]]:
    return [
        {
            "split": "generator_train",
            "visible_to_development": True,
            "purpose": "implementation debugging and predeclared candidate development",
            "seed_policy": "fixed development seeds only",
            "claim_allowed": False,
        },
        {
            "split": "generator_validation",
            "visible_to_development": True,
            "purpose": "choose from predeclared mechanism variants only",
            "seed_policy": "fixed validation seeds, no hidden-family access",
            "claim_allowed": False,
        },
        {
            "split": "generated_holdout",
            "visible_to_development": False,
            "purpose": "final family-level pass/fail and effect-size estimate",
            "seed_policy": "precommitted hidden seeds/families materialized only at scoring",
            "claim_allowed": True,
        },
        {
            "split": "generator_ood_holdout",
            "visible_to_development": False,
            "purpose": "test withheld task families and generator modes",
            "seed_policy": "separate hidden family IDs and held-out knob ranges",
            "claim_allowed": True,
        },
    ]


def baseline_rows() -> list[dict[str, Any]]:
    return [
        {"baseline": "current_cra_v2_4", "role": "candidate_reference", "fairness_rule": "locked current frozen software baseline"},
        {"baseline": "v2_2_reference", "role": "prior_cra_reference", "fairness_rule": "same streams and scoring"},
        {"baseline": "lag_ridge_or_ar", "role": "strong_simple_public_baseline", "fairness_rule": "causal train-prefix fitting only"},
        {"baseline": "online_logistic_or_perceptron", "role": "online_linear_baseline", "fairness_rule": "same causal feature stream"},
        {"baseline": "reservoir_esn", "role": "recurrent_baseline", "fairness_rule": "predeclared reservoir size/tuning budget"},
        {"baseline": "small_gru", "role": "neural_sequence_baseline", "fairness_rule": "bounded parameter budget and train-prefix only"},
        {"baseline": "bandit_or_simple_rl", "role": "policy_action_baseline", "fairness_rule": "only for action-cost families"},
        {"baseline": "stpd_only_snn", "role": "snn_reviewer_defense", "fairness_rule": "same encoding where practical"},
        {"baseline": "oracle_upper_bound", "role": "upper_bound", "fairness_rule": "reported but never used as candidate baseline"},
    ]


def leakage_rows() -> list[dict[str, Any]]:
    return [
        {"guard": "future_target_block", "rule": "no future reward/label/target visible before action or prediction"},
        {"guard": "heldout_family_block", "rule": "held-out family IDs and knob ranges cannot be used during implementation/tuning"},
        {"guard": "same_stream_fairness", "rule": "CRA and baselines receive identical causal streams"},
        {"guard": "shuffle_controls", "rule": "target-shuffle, state-shuffle, route-shuffle, and wrong-key controls where applicable"},
        {"guard": "oracle_separation", "rule": "oracle baselines are upper bounds only and cannot leak into candidate state"},
        {"guard": "difficulty_no_peeking", "rule": "difficulty schedule is fixed before scoring and cannot be adjusted after seeing holdout"},
    ]


def metric_rows() -> list[dict[str, Any]]:
    return [
        {"metric": "primary_task_score", "use": "family-specific main score such as MSE, accuracy, utility, or regret", "required": True},
        {"metric": "tail_or_holdout_score", "use": "late-window or held-out-family score", "required": True},
        {"metric": "sample_efficiency", "use": "steps/events to threshold", "required": True},
        {"metric": "recovery_after_switch", "use": "adaptation after nonstationary changes", "required": True},
        {"metric": "forgetting_or_reacquisition", "use": "old-regime retention and reentry speed", "required": True},
        {"metric": "variance_worst_seed", "use": "seed robustness and collapse risk", "required": True},
        {"metric": "effect_size_and_ci", "use": "paired effect sizes and bootstrap/confidence intervals", "required": True},
        {"metric": "runtime_and_resource", "use": "wall time, memory/state size, and hardware-transfer relevance", "required": True},
    ]


def pass_fail_rows() -> list[dict[str, Any]]:
    return [
        {
            "gate": "contract_pass",
            "pass_rule": "all contract artifacts exist and no scoring/tuning is performed",
            "fail_rule": "missing family/split/baseline/leakage/metric definitions",
        },
        {
            "gate": "future_implementation_pass",
            "pass_rule": "generator materializes deterministic train/validation/holdout streams and dry-run baselines without leakage",
            "fail_rule": "non-determinism, hidden split exposure, or incompatible baseline inputs",
        },
        {
            "gate": "future_scoring_pass",
            "pass_rule": "candidate improves over current CRA and strongest fair baselines on at least one held-out generated family with shams separated",
            "fail_rule": "wins vanish on heldout/OOD families or are explained by leakage/shams",
        },
        {
            "gate": "claim_boundary",
            "pass_rule": "claim is restricted to families and metrics that pass",
            "fail_rule": "single-family success inflated into broad usefulness, planning, language, AGI, or ASI",
        },
    ]


def expected_artifact_rows() -> list[dict[str, Any]]:
    return [
        {"artifact": "tier7_5b_generator_manifest.json", "producer": "future Tier 7.5b", "purpose": "materialized generator source/split manifest"},
        {"artifact": "tier7_5b_task_family_streams.csv", "producer": "future Tier 7.5b", "purpose": "dry-run stream inventory without labels visible online"},
        {"artifact": "tier7_5c_score_rows.csv", "producer": "future scoring gate", "purpose": "per-family/model/seed scoring rows"},
        {"artifact": "tier7_5c_baseline_summary.csv", "producer": "future scoring gate", "purpose": "baseline comparison table"},
        {"artifact": "tier7_5c_sham_controls.csv", "producer": "future scoring gate", "purpose": "shuffle/oracle/leakage controls"},
        {"artifact": "tier7_5c_claim_boundary.md", "producer": "future scoring gate", "purpose": "earned claims and nonclaims"},
    ]


def make_report(output_dir: Path, status: str, criteria: list[dict[str, Any]], decision: dict[str, Any]) -> str:
    passed = sum(1 for c in criteria if c["passed"])
    return "\n".join(
        [
            "# Tier 7.5a Curriculum / Environment Generator Contract",
            "",
            f"- Generated: `{utc_now()}`",
            f"- Status: **{status}**",
            f"- Output directory: `{output_dir}`",
            f"- Runner revision: `{RUNNER_REVISION}`",
            "",
            "## Boundary",
            "",
            "This is a contract-only gate. It does not implement curriculum generation, score CRA, tune mechanisms, freeze a baseline, or authorize hardware/native transfer.",
            "",
            "## Summary",
            "",
            f"- criteria_passed: `{passed}/{len(criteria)}`",
            f"- outcome: `{decision['outcome']}`",
            f"- next_gate: `{decision['next_gate']}`",
            "",
            "## Criteria",
            "",
            "| Criterion | Value | Rule | Pass | Details |",
            "| --- | --- | --- | --- | --- |",
            *[
                f"| {c['criterion']} | `{c['value']}` | {c['rule']} | {'yes' if c['passed'] else 'no'} | {c.get('details', '')} |"
                for c in criteria
            ],
            "",
            "## Interpretation",
            "",
            "Tier 7.5a locks the curriculum/environment-generator evidence contract before implementation. The next gate may build the generator only against these predeclared families, splits, baselines, metrics, leakage controls, and artifacts.",
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


def main() -> int:
    output_dir = DEFAULT_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    prereq = read_json(PREREQ)
    families = task_family_rows()
    difficulty = difficulty_rows()
    splits = split_rows()
    baselines = baseline_rows()
    leakage = leakage_rows()
    metrics = metric_rows()
    pass_fail = pass_fail_rows()
    expected = expected_artifact_rows()

    decision = {
        "tier": TIER,
        "status": "PASS",
        "outcome": "curriculum_environment_contract_locked_no_scoring",
        "next_gate": NEXT_GATE,
        "contract_only": True,
        "scoring_performed": False,
        "freeze_authorized": False,
        "hardware_transfer_authorized": False,
        "broad_public_usefulness_authorized": False,
        "claim_boundary": "Contract only; no curriculum capability claim until implementation and held-out scoring pass.",
    }
    criteria = [
        criterion("tier7_4h_prerequisite_exists", PREREQ.exists(), "must exist", PREREQ.exists(), str(PREREQ)),
        criterion("tier7_4h_prerequisite_passed", prereq.get("status"), "case-insensitive == PASS", str(prereq.get("status", "")).upper() == "PASS"),
        criterion("task_family_count", len(families), ">= 5", len(families) >= 5),
        criterion("difficulty_levels_defined", len(difficulty), ">= 4", len(difficulty) >= 4),
        criterion("split_contract_defined", len(splits), ">= 4", len(splits) >= 4),
        criterion("heldout_split_hidden", any(r["split"] == "generated_holdout" and not r["visible_to_development"] for r in splits), "must be true", True),
        criterion("baseline_inventory_defined", len(baselines), ">= 8", len(baselines) >= 8),
        criterion("leakage_guards_defined", len(leakage), ">= 5", len(leakage) >= 5),
        criterion("metrics_defined", len(metrics), ">= 8", len(metrics) >= 8),
        criterion("pass_fail_gates_defined", len(pass_fail), ">= 4", len(pass_fail) >= 4),
        criterion("expected_artifacts_defined", len(expected), ">= 5", len(expected) >= 5),
        criterion("contract_only_no_scoring", decision["scoring_performed"], "must be False", not decision["scoring_performed"]),
        criterion("freeze_blocked", decision["freeze_authorized"], "must be False", not decision["freeze_authorized"]),
        criterion("hardware_transfer_blocked", decision["hardware_transfer_authorized"], "must be False", not decision["hardware_transfer_authorized"]),
        criterion("broad_claim_blocked", decision["broad_public_usefulness_authorized"], "must be False", not decision["broad_public_usefulness_authorized"]),
        criterion("next_gate_selected", decision["next_gate"], "non-empty", bool(decision["next_gate"])),
    ]
    status = "PASS" if all(c["passed"] for c in criteria) else "FAIL"
    decision["status"] = status
    results = {
        "tier": TIER,
        "status": status,
        "generated_at_utc": utc_now(),
        "runner_revision": RUNNER_REVISION,
        "criteria": criteria,
        "decision": decision,
        "task_families": families,
        "difficulty_schedule": difficulty,
        "split_contract": splits,
        "baseline_inventory": baselines,
        "leakage_guards": leakage,
        "metrics": metrics,
        "pass_fail_gates": pass_fail,
        "expected_artifacts": expected,
    }

    artifacts = {
        "results_json": output_dir / "tier7_5a_results.json",
        "summary_csv": output_dir / "tier7_5a_summary.csv",
        "report_md": output_dir / "tier7_5a_report.md",
        "task_families_csv": output_dir / "tier7_5a_task_families.csv",
        "difficulty_schedule_csv": output_dir / "tier7_5a_difficulty_schedule.csv",
        "split_contract_csv": output_dir / "tier7_5a_split_contract.csv",
        "baseline_inventory_csv": output_dir / "tier7_5a_baseline_inventory.csv",
        "leakage_guards_csv": output_dir / "tier7_5a_leakage_guards.csv",
        "metrics_csv": output_dir / "tier7_5a_metrics.csv",
        "pass_fail_gates_csv": output_dir / "tier7_5a_pass_fail_gates.csv",
        "expected_artifacts_csv": output_dir / "tier7_5a_expected_artifacts.csv",
        "decision_json": output_dir / "tier7_5a_decision.json",
        "decision_csv": output_dir / "tier7_5a_decision.csv",
    }
    write_json(artifacts["results_json"], results)
    write_csv(artifacts["summary_csv"], criteria, ["criterion", "value", "rule", "pass", "details"])
    write_csv(artifacts["task_families_csv"], families)
    write_csv(artifacts["difficulty_schedule_csv"], difficulty)
    write_csv(artifacts["split_contract_csv"], splits)
    write_csv(artifacts["baseline_inventory_csv"], baselines)
    write_csv(artifacts["leakage_guards_csv"], leakage)
    write_csv(artifacts["metrics_csv"], metrics)
    write_csv(artifacts["pass_fail_gates_csv"], pass_fail)
    write_csv(artifacts["expected_artifacts_csv"], expected)
    write_json(artifacts["decision_json"], decision)
    write_csv(artifacts["decision_csv"], [decision])
    artifacts["report_md"].write_text(make_report(output_dir, status, criteria, decision), encoding="utf-8")
    manifest = make_manifest(output_dir, artifacts, status)
    artifacts["latest_manifest_json"] = output_dir / "tier7_5a_latest_manifest.json"
    write_json(artifacts["latest_manifest_json"], manifest)

    print(json.dumps(json_safe({"status": status, "outcome": decision["outcome"], "output_dir": output_dir, "next_gate": NEXT_GATE}), indent=2))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
