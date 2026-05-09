#!/usr/bin/env python3
"""Tier 7.6a - long-horizon planning / subgoal-control contract.

Contract-only gate for bounded planning and subgoal control. This tier does not
implement or score a planner. It locks the exact question, task families,
baselines, shams, leakage guards, metrics, pass/fail criteria, expected
artifacts, and nonclaims before any Tier 7.6 scoring can be interpreted.
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

TIER = "Tier 7.6a - Long-Horizon Planning / Subgoal Control Contract"
RUNNER_REVISION = "tier7_6a_long_horizon_planning_contract_20260509_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_6a_20260509_long_horizon_planning_contract"

PREREQ = CONTROLLED / "tier7_5d_20260509_curriculum_environment_attribution_closeout" / "tier7_5d_results.json"
NEXT_GATE = "Tier 7.6b - Long-Horizon Planning / Subgoal-Control Local Diagnostic"


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
            "family_id": "two_stage_delayed_goal_chain",
            "planning_pressure": "prepare action must happen before a delayed sparse goal action can succeed",
            "subgoals": "prepare, commit, harvest",
            "hidden_holdout_rule": "withhold action-delay schedules and cue aliases",
            "primary_metrics": "episode_success,subgoal_completion,delayed_return,wrong_order_penalty",
        },
        {
            "family_id": "key_door_goal_sequence",
            "planning_pressure": "agent must acquire/remember a key-like context before choosing door/goal action",
            "subgoals": "find_key,retain_key,use_key,avoid_decoy",
            "hidden_holdout_rule": "withhold key-door mappings and distractor layouts",
            "primary_metrics": "final_success,key_retention,decoy_error_rate,path_efficiency",
        },
        {
            "family_id": "resource_budget_route_plan",
            "planning_pressure": "agent must trade immediate utility against a limited resource budget over a sequence",
            "subgoals": "budget_save,budget_spend,route_switch,terminal_reward",
            "hidden_holdout_rule": "withhold resource-cost schedules and terminal reward placements",
            "primary_metrics": "net_return,regret_vs_oracle,budget_violation_rate,plan_length",
        },
        {
            "family_id": "blocked_subgoal_recovery",
            "planning_pressure": "agent must detect a blocked subgoal and replan without future-label access",
            "subgoals": "initial_plan,block_detect,recover,complete_goal",
            "hidden_holdout_rule": "withhold block timing, recovery path, and context-key combinations",
            "primary_metrics": "recovery_steps,goal_success_after_block,collapse_rate",
        },
        {
            "family_id": "hierarchical_composition_holdout",
            "planning_pressure": "agent must compose learned primitives into held-out multi-step skills",
            "subgoals": "primitive_a,primitive_b,route_between,terminal_action",
            "hidden_holdout_rule": "withhold compositions while exposing primitives",
            "primary_metrics": "heldout_composition_success,module_reuse_score,route_error,regret",
        },
    ]


def split_rows() -> list[dict[str, Any]]:
    return [
        {
            "split": "planning_train",
            "visible_to_development": True,
            "claim_allowed": False,
            "purpose": "debug implementation and train candidates under causal online boundaries",
        },
        {
            "split": "planning_validation",
            "visible_to_development": True,
            "claim_allowed": False,
            "purpose": "choose only among predeclared candidates and hyperparameters",
        },
        {
            "split": "planning_hidden_holdout",
            "visible_to_development": False,
            "claim_allowed": True,
            "purpose": "final hidden pass/fail for task families and effect-size support",
        },
        {
            "split": "planning_ood_holdout",
            "visible_to_development": False,
            "claim_allowed": True,
            "purpose": "withheld compositions, resource schedules, and blocked-subgoal regimes",
        },
    ]


def baseline_rows() -> list[dict[str, Any]]:
    return [
        {"baseline": "v2_4_reactive_policy_reference", "role": "current_cra_reference", "fairness_rule": "same causal observations/actions; no subgoal state"},
        {"baseline": "v2_4_no_planning_ablation", "role": "candidate_ablation", "fairness_rule": "same CRA mechanisms with planner/subgoal state disabled"},
        {"baseline": "online_logistic_policy", "role": "external_baseline", "fairness_rule": "train-prefix only, same causal features"},
        {"baseline": "tabular_q_learning_or_sarsa", "role": "simple_rl_baseline", "fairness_rule": "same action space, same episode budget"},
        {"baseline": "dyna_q_model_based_baseline", "role": "planning_baseline", "fairness_rule": "same transition/reward samples, bounded planning updates"},
        {"baseline": "reservoir_policy_readout", "role": "sequence_baseline", "fairness_rule": "predeclared size/tuning budget"},
        {"baseline": "small_recurrent_tanh_policy", "role": "sequence_baseline", "fairness_rule": "bounded recurrent hidden size, no future labels"},
        {"baseline": "random_policy", "role": "negative_control", "fairness_rule": "same action set and episode count"},
        {"baseline": "oracle_planner_upper_bound", "role": "upper_bound_nonclaim", "fairness_rule": "reported only; never used as a candidate baseline"},
    ]


def sham_rows() -> list[dict[str, Any]]:
    return [
        {"sham": "subgoal_label_shuffle", "purpose": "break subgoal identity while preserving event/action counts"},
        {"sham": "action_reward_shuffle", "purpose": "break action-to-outcome credit while preserving marginal reward"},
        {"sham": "future_goal_leak_guard", "purpose": "detect any use of terminal labels before causal availability"},
        {"sham": "planner_state_reset", "purpose": "remove long-horizon state at episode boundaries or distractor gaps"},
        {"sham": "memory_disabled", "purpose": "test whether context memory is required for planning benefit"},
        {"sham": "self_evaluation_disabled", "purpose": "test whether reliability/uncertainty contributes to replanning"},
        {"sham": "predictive_state_disabled", "purpose": "test whether predictive/context modeling contributes to planning"},
        {"sham": "route_shuffle", "purpose": "break module-routing support for hierarchical composition"},
        {"sham": "always_first_subgoal", "purpose": "detect degenerate fixed-subgoal policy"},
    ]


def metric_rows() -> list[dict[str, Any]]:
    return [
        {"metric": "episode_success_rate", "purpose": "final goal completion"},
        {"metric": "subgoal_completion_rate", "purpose": "intermediate milestone completion"},
        {"metric": "discounted_return", "purpose": "reward/cost performance over horizon"},
        {"metric": "regret_vs_oracle", "purpose": "distance from upper-bound planner without using it as baseline"},
        {"metric": "path_or_action_efficiency", "purpose": "avoid brute-force action spam"},
        {"metric": "recovery_steps_after_block", "purpose": "measure replanning rather than collapse"},
        {"metric": "wrong_order_penalty", "purpose": "detect reflexive actions in invalid sequence order"},
        {"metric": "seed_variance_and_worst_case", "purpose": "prevent mean-only claims"},
        {"metric": "paired_effect_size_and_ci", "purpose": "require statistical support versus best baseline and shams"},
    ]


def leakage_rows() -> list[dict[str, Any]]:
    return [
        {"guard": "no_future_terminal_reward", "rule": "terminal success/reward cannot be visible before the decision that earns it"},
        {"guard": "causal_observation_order", "rule": "observations/actions/rewards must be logged in prediction-before-update order"},
        {"guard": "hidden_mapping_block", "rule": "hidden key-door, route, and composition mappings cannot be used during development"},
        {"guard": "same_episode_budget", "rule": "CRA and baselines receive the same episode counts, action budgets, and train/eval windows"},
        {"guard": "oracle_is_upper_bound_only", "rule": "oracle planner cannot be used for tuning or candidate comparison claims"},
        {"guard": "subgoal_label_audit", "rule": "subgoal labels used for scoring cannot be visible to online policy unless declared as observations"},
    ]


def pass_fail_rows() -> list[dict[str, Any]]:
    return [
        {
            "kind": "pass",
            "rule": "candidate beats strongest non-oracle baseline on hidden success/return with positive paired support",
        },
        {
            "kind": "pass",
            "rule": "candidate beats v2.4 reactive/no-planning references on at least three planning families",
        },
        {
            "kind": "pass",
            "rule": "subgoal shams and planner-state ablations lose on the families they target",
        },
        {
            "kind": "pass",
            "rule": "benefit is not explained by action spam, always-first-subgoal, or future-goal leakage",
        },
        {
            "kind": "pass",
            "rule": "compact regression stays green before any promotion or baseline freeze",
        },
        {
            "kind": "fail",
            "rule": "simple tabular/model-based baseline wins all hidden planning families",
        },
        {
            "kind": "fail",
            "rule": "candidate wins only by seeing terminal/subgoal labels early",
        },
        {
            "kind": "fail",
            "rule": "shuffled subgoal or no-planning ablations match the intact candidate",
        },
        {
            "kind": "fail",
            "rule": "performance collapses into a degenerate always-act or always-first-subgoal policy",
        },
    ]


def nonclaim_rows() -> list[dict[str, Any]]:
    return [
        {"nonclaim": "general planning", "reason": "Tier 7.6 is bounded subgoal-control evidence only"},
        {"nonclaim": "language reasoning", "reason": "no language input/output or semantic grounding is tested"},
        {"nonclaim": "open-ended agency", "reason": "tasks, action sets, and horizons are fixed and audited"},
        {"nonclaim": "AGI/ASI", "reason": "bounded planning diagnostics are not general intelligence evidence"},
        {"nonclaim": "hardware/native transfer", "reason": "software contract/scoring must pass before any native migration is considered"},
        {"nonclaim": "new baseline freeze from contract", "reason": "contract-only gates cannot freeze baselines"},
    ]


def expected_artifact_rows() -> list[dict[str, Any]]:
    return [
        {"artifact": "tier7_6b_task_contract.json", "required_for": "local diagnostic"},
        {"artifact": "tier7_6b_episode_score_rows.csv", "required_for": "scoring"},
        {"artifact": "tier7_6b_model_summary.csv", "required_for": "scoring"},
        {"artifact": "tier7_6b_subgoal_trace_rows.csv", "required_for": "mechanism attribution"},
        {"artifact": "tier7_6b_sham_controls.csv", "required_for": "reviewer defense"},
        {"artifact": "tier7_6b_statistical_support.csv", "required_for": "effect size / CI"},
        {"artifact": "tier7_6b_claim_boundary.md", "required_for": "paper discipline"},
        {"artifact": "tier7_6b_decision.json", "required_for": "route/freeze decision"},
    ]


def make_contract() -> dict[str, Any]:
    return {
        "question": (
            "Can CRA use bounded internal state to select and maintain subgoals "
            "over multi-step horizons, improving delayed sparse-return tasks "
            "beyond reactive policy/action selection and fair planning/RL baselines?"
        ),
        "hypothesis": (
            "A bounded subgoal-control layer that uses context memory, routing, "
            "predictive state, and self-evaluation can improve multi-step goal "
            "completion, recovery after blocked subgoals, and regret versus "
            "reactive CRA references under causal observations."
        ),
        "null_hypothesis": (
            "CRA's proposed subgoal-control path does not outperform reactive "
            "v2.4, no-planning ablations, or simple planning/RL baselines under "
            "identical action budgets and hidden holdout schedules."
        ),
        "next_gate_if_accepted": NEXT_GATE,
        "claim_boundary": (
            "Contract only. No planning score, no public usefulness claim, no "
            "new baseline freeze, no hardware/native transfer, and no language, "
            "AGI, or ASI claim."
        ),
    }


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


def make_report(output_dir: Path, status: str, criteria: list[dict[str, Any]], contract: dict[str, Any]) -> str:
    passed = sum(1 for c in criteria if c["passed"])
    return "\n".join(
        [
            "# Tier 7.6a Long-Horizon Planning / Subgoal-Control Contract",
            "",
            f"- Generated: `{utc_now()}`",
            f"- Status: **{status}**",
            f"- Output directory: `{output_dir}`",
            f"- Runner revision: `{RUNNER_REVISION}`",
            f"- Criteria: `{passed}/{len(criteria)}`",
            f"- Next gate: `{contract['next_gate_if_accepted']}`",
            "",
            "## Question",
            "",
            contract["question"],
            "",
            "## Hypothesis",
            "",
            contract["hypothesis"],
            "",
            "## Null Hypothesis",
            "",
            contract["null_hypothesis"],
            "",
            "## Boundary",
            "",
            contract["claim_boundary"],
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
        ]
    )


def main() -> int:
    output_dir = DEFAULT_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    prereq = read_json(PREREQ)
    contract = make_contract()
    tasks = task_family_rows()
    splits = split_rows()
    baselines = baseline_rows()
    shams = sham_rows()
    metrics = metric_rows()
    leakage = leakage_rows()
    pass_fail = pass_fail_rows()
    nonclaims = nonclaim_rows()
    expected_artifacts = expected_artifact_rows()
    decision = {
        "tier": TIER,
        "status": "PASS",
        "outcome": "long_horizon_planning_contract_locked_no_scoring",
        "scoring_performed": False,
        "implementation_performed": False,
        "freeze_authorized": False,
        "hardware_transfer_authorized": False,
        "broad_planning_claim_authorized": False,
        "next_gate": NEXT_GATE,
    }
    criteria = [
        criterion("tier7_5d_prerequisite_exists", PREREQ.exists(), "must exist", PREREQ.exists(), str(PREREQ)),
        criterion("tier7_5d_prerequisite_passed", prereq.get("status"), "case-insensitive == PASS", str(prereq.get("status", "")).upper() == "PASS"),
        criterion("contract_question_defined", bool(contract["question"]), "non-empty", bool(contract["question"])),
        criterion("hypothesis_defined", bool(contract["hypothesis"]), "non-empty", bool(contract["hypothesis"])),
        criterion("null_hypothesis_defined", bool(contract["null_hypothesis"]), "non-empty", bool(contract["null_hypothesis"])),
        criterion("task_families_declared", len(tasks), ">= 5", len(tasks) >= 5),
        criterion("splits_declared", len(splits), ">= 4", len(splits) >= 4),
        criterion("baselines_declared", len(baselines), ">= 8", len(baselines) >= 8),
        criterion("planning_rl_baselines_included", any("q_learning" in row["baseline"] or "dyna_q" in row["baseline"] for row in baselines), "must include simple planning/RL baselines", any("q_learning" in row["baseline"] or "dyna_q" in row["baseline"] for row in baselines)),
        criterion("shams_declared", len(shams), ">= 8", len(shams) >= 8),
        criterion("metrics_declared", len(metrics), ">= 8", len(metrics) >= 8),
        criterion("leakage_guards_declared", len(leakage), ">= 6", len(leakage) >= 6),
        criterion("pass_fail_rules_declared", len(pass_fail), ">= 8", len(pass_fail) >= 8),
        criterion("nonclaims_declared", len(nonclaims), ">= 6", len(nonclaims) >= 6),
        criterion("expected_artifacts_declared", len(expected_artifacts), ">= 8", len(expected_artifacts) >= 8),
        criterion("contract_no_scoring", decision["scoring_performed"], "must be False", not decision["scoring_performed"]),
        criterion("contract_no_freeze", decision["freeze_authorized"], "must be False", not decision["freeze_authorized"]),
        criterion("contract_no_hardware_transfer", decision["hardware_transfer_authorized"], "must be False", not decision["hardware_transfer_authorized"]),
        criterion("next_gate_selected", decision["next_gate"], f"== {NEXT_GATE}", decision["next_gate"] == NEXT_GATE),
    ]
    status = "PASS" if all(c["passed"] for c in criteria) else "FAIL"
    decision["status"] = status
    results = {
        "tier": TIER,
        "status": status,
        "generated_at_utc": utc_now(),
        "runner_revision": RUNNER_REVISION,
        "criteria": criteria,
        "contract": contract,
        "decision": decision,
    }
    artifacts = {
        "results_json": output_dir / "tier7_6a_results.json",
        "summary_csv": output_dir / "tier7_6a_summary.csv",
        "report_md": output_dir / "tier7_6a_report.md",
        "task_families_csv": output_dir / "tier7_6a_task_families.csv",
        "splits_csv": output_dir / "tier7_6a_split_contract.csv",
        "baselines_csv": output_dir / "tier7_6a_baseline_inventory.csv",
        "shams_csv": output_dir / "tier7_6a_sham_controls.csv",
        "metrics_csv": output_dir / "tier7_6a_metrics.csv",
        "leakage_guards_csv": output_dir / "tier7_6a_leakage_guards.csv",
        "pass_fail_csv": output_dir / "tier7_6a_pass_fail_gates.csv",
        "nonclaims_csv": output_dir / "tier7_6a_nonclaims.csv",
        "expected_artifacts_csv": output_dir / "tier7_6a_expected_artifacts.csv",
        "decision_json": output_dir / "tier7_6a_decision.json",
        "decision_csv": output_dir / "tier7_6a_decision.csv",
    }
    write_json(artifacts["results_json"], results)
    write_csv(artifacts["summary_csv"], criteria, ["criterion", "value", "rule", "pass", "details"])
    write_csv(artifacts["task_families_csv"], tasks)
    write_csv(artifacts["splits_csv"], splits)
    write_csv(artifacts["baselines_csv"], baselines)
    write_csv(artifacts["shams_csv"], shams)
    write_csv(artifacts["metrics_csv"], metrics)
    write_csv(artifacts["leakage_guards_csv"], leakage)
    write_csv(artifacts["pass_fail_csv"], pass_fail)
    write_csv(artifacts["nonclaims_csv"], nonclaims)
    write_csv(artifacts["expected_artifacts_csv"], expected_artifacts)
    write_json(artifacts["decision_json"], decision)
    write_csv(artifacts["decision_csv"], [decision])
    artifacts["report_md"].write_text(make_report(output_dir, status, criteria, contract), encoding="utf-8")
    latest = make_manifest(output_dir, artifacts, status)
    artifacts["latest_manifest_json"] = output_dir / "tier7_6a_latest_manifest.json"
    write_json(artifacts["latest_manifest_json"], latest)
    print(
        json.dumps(
            json_safe(
                {
                    "status": status,
                    "outcome": decision["outcome"],
                    "task_families": len(tasks),
                    "baselines": len(baselines),
                    "shams": len(shams),
                    "output_dir": output_dir,
                    "next_gate": NEXT_GATE,
                }
            ),
            indent=2,
        )
    )
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
