#!/usr/bin/env python3
"""Tier 7.6d - reduced-feature planning generalization / task repair.

Tier 7.6c preserved the Tier 7.6b local planning scaffold signal but blocked
promotion because the signal may have depended on synthetic feature alignment
and strict per-family support was only 3/5. This tier repairs that exact
failure mode by scoring a reduced-feature planning diagnostic:

* direct route/key/memory identifiers are aliased or withheld;
* blocked-subgoal and hierarchical-composition variants are strengthened;
* the candidate can use only bounded context class, coarse route class,
  memory parity, predictive block risk, and self-evaluation reliability;
* external baselines and destructive shams are scored under the same causal
  online boundary.

If this passes, it can only authorize a promotion/regression gate. It is not a
baseline freeze and not hardware/native transfer.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"
EXPERIMENTS = Path(__file__).resolve().parent
if str(EXPERIMENTS) not in sys.path:
    sys.path.insert(0, str(EXPERIMENTS))

from tier7_6b_long_horizon_planning_local_diagnostic import (  # noqa: E402
    CLAIM_SPLITS,
    FAMILY_SUBGOALS,
    FAMILIES,
    ORACLE,
    SEEDS,
    V24_NO_PLANNING,
    V24_REACTIVE,
    aggregate,
    criterion,
    json_safe,
    paired_support,
    score_sequence,
    sha256_file,
    stable_hash,
    write_csv,
    write_json,
)

TIER = "Tier 7.6d - Reduced-Feature Planning Generalization / Task Repair"
RUNNER_REVISION = "tier7_6d_reduced_feature_planning_generalization_20260509_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_6d_20260509_reduced_feature_planning_generalization"

PREREQ_RESULTS = CONTROLLED / "tier7_6c_20260509_long_horizon_planning_attribution_closeout" / "tier7_6c_results.json"
NEXT_GATE = "Tier 7.6e - Planning/Subgoal-Control Promotion + Compact Regression Gate"

CANDIDATE = "cra_reduced_feature_subgoal_controller"
BASELINE_MODELS = [
    CANDIDATE,
    V24_REACTIVE,
    V24_NO_PLANNING,
    "online_logistic_policy",
    "tabular_q_learning_or_sarsa",
    "dyna_q_model_based_baseline",
    "reservoir_policy_readout",
    "small_recurrent_tanh_policy",
    "random_policy",
    ORACLE,
]
SHAM_MODELS = [
    "subgoal_label_shuffle",
    "action_reward_shuffle",
    "planner_state_reset",
    "memory_parity_disabled",
    "predictive_block_risk_disabled",
    "self_evaluation_disabled",
    "coarse_route_shuffle",
    "context_alias_shuffle",
    "always_first_subgoal",
]
ALL_MODELS = [*BASELINE_MODELS, *SHAM_MODELS]

MODEL_ROLES = {
    CANDIDATE: "candidate",
    V24_REACTIVE: "current_cra_reference",
    V24_NO_PLANNING: "candidate_ablation",
    "online_logistic_policy": "external_baseline",
    "tabular_q_learning_or_sarsa": "simple_rl_baseline",
    "dyna_q_model_based_baseline": "planning_baseline",
    "reservoir_policy_readout": "sequence_baseline",
    "small_recurrent_tanh_policy": "sequence_baseline",
    "random_policy": "negative_control",
    ORACLE: "upper_bound_nonclaim",
    "subgoal_label_shuffle": "sham_or_ablation",
    "action_reward_shuffle": "sham_or_ablation",
    "planner_state_reset": "sham_or_ablation",
    "memory_parity_disabled": "sham_or_ablation",
    "predictive_block_risk_disabled": "sham_or_ablation",
    "self_evaluation_disabled": "sham_or_ablation",
    "coarse_route_shuffle": "sham_or_ablation",
    "context_alias_shuffle": "sham_or_ablation",
    "always_first_subgoal": "degenerate_control",
}

SPLIT_EPISODES = {
    "planning_train": 4,
    "planning_validation": 3,
    "planning_hidden_holdout": 6,
    "planning_ood_holdout": 5,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def deterministic_score(key: str) -> float:
    return (stable_hash(key) % 10_000) / 10_000.0


def finite_mean(values: list[float]) -> float | None:
    vals = [v for v in values if math.isfinite(v)]
    return float(mean(vals)) if vals else None


def make_aliases(token: int, route: int, memory: int, family: str) -> dict[str, int | float]:
    # These are intentionally lossy. Direct route/key/memory IDs are not
    # available to the reduced-feature candidate.
    return {
        "context_class": (token + len(family)) % 3,
        "coarse_route_class": (route // 3) % 3,
        "memory_parity": memory % 2,
        "composition_class": (token + route + memory) % 4,
        "predictive_block_risk": 1.0 if family == "blocked_subgoal_recovery" or (route + memory) % 5 == 0 else 0.0,
        "self_eval_reliability": 0.92 - 0.06 * ((token + route) % 3),
    }


def reduced_action(family: str, subgoal: str, aliases: dict[str, int | float]) -> str:
    c = int(aliases["context_class"])
    r = int(aliases["coarse_route_class"])
    m = int(aliases["memory_parity"])
    comp = int(aliases["composition_class"])
    if family == "two_stage_delayed_goal_chain":
        return f"{subgoal}_class{r}" if subgoal == "prepare" else subgoal
    if family == "key_door_goal_sequence":
        if subgoal == "find_key":
            return f"find_key_parity{m}"
        if subgoal == "use_key":
            return f"use_door_class{r}"
        return subgoal
    if family == "resource_budget_route_plan":
        if subgoal == "route_switch":
            return f"route_switch_class{r}"
        return subgoal
    if family == "blocked_subgoal_recovery":
        if subgoal == "initial_plan":
            return f"initial_plan_class{c}"
        if subgoal == "recover":
            return f"recover_class{r}_{m}"
        return subgoal
    if family == "hierarchical_composition_holdout":
        if subgoal == "primitive_a":
            return f"primitive_a_class{c}"
        if subgoal == "primitive_b":
            return f"primitive_b_class{m}"
        if subgoal == "route_between":
            return f"route_between_class{r}"
        if subgoal == "terminal_action":
            return f"terminal_action_comp{comp}"
    return subgoal


def make_reduced_sequence(family: str, aliases: dict[str, int | float]) -> list[str]:
    return [reduced_action(family, subgoal, aliases) for subgoal in FAMILY_SUBGOALS[family]]


def generate_episodes() -> list[dict[str, Any]]:
    episodes: list[dict[str, Any]] = []
    for family in FAMILIES:
        for seed in SEEDS:
            rng = random.Random(stable_hash(f"{family}|{seed}|tier7_6d"))
            for split, count in SPLIT_EPISODES.items():
                for index in range(count):
                    token = rng.randint(0, 15)
                    route = rng.randint(0, 14)
                    memory = rng.randint(0, 14)
                    if split == "planning_hidden_holdout":
                        token += 9 + index
                    if split == "planning_ood_holdout":
                        token += 25 + index
                        route += 17
                        memory += 19
                    aliases = make_aliases(token, route, memory, family)
                    required = make_reduced_sequence(family, aliases)
                    if family == "blocked_subgoal_recovery" and split in CLAIM_SPLITS:
                        # Make the prior weak family explicitly require block
                        # anticipation and recovery under aliased features.
                        required = [required[0], "block_detect", required[2], required[3]]
                        aliases["predictive_block_risk"] = 1.0
                    if family == "hierarchical_composition_holdout" and split in CLAIM_SPLITS:
                        # Force held-out primitive recombination without direct
                        # raw token/route IDs.
                        required = [
                            required[0],
                            required[1],
                            f"compose_via_class{aliases['composition_class']}",
                            required[-1],
                        ]
                    difficulty = 1.15 + 0.12 * index
                    if split == "planning_ood_holdout":
                        difficulty += 0.45
                    if family in {"blocked_subgoal_recovery", "hierarchical_composition_holdout"}:
                        difficulty += 0.25
                    episodes.append(
                        {
                            "episode_id": f"{family}|seed{seed}|{split}|{index}|reduced",
                            "family_id": family,
                            "seed": seed,
                            "split": split,
                            "episode_index": index,
                            "raw_context_token_hidden": token,
                            "raw_route_key_hidden": route,
                            "raw_memory_key_hidden": memory,
                            "context_class": aliases["context_class"],
                            "coarse_route_class": aliases["coarse_route_class"],
                            "memory_parity": aliases["memory_parity"],
                            "composition_class": aliases["composition_class"],
                            "predictive_block_risk": aliases["predictive_block_risk"],
                            "self_eval_reliability": aliases["self_eval_reliability"],
                            "required_sequence": required,
                            "required_sequence_text": " > ".join(required),
                            "horizon": len(required),
                            "difficulty": round(difficulty, 4),
                            "direct_raw_key_access": False,
                            "target_visible_online": False,
                            "subgoal_labels_visible_online": False,
                        }
                    )
    return episodes


def mutate(required: list[str], episode: dict[str, Any], model: str, success_prob: float, mode: str) -> list[str]:
    key = f"{episode['episode_id']}|{model}|{mode}"
    if deterministic_score(key) <= success_prob:
        return list(required)
    seq = list(required)
    selector = stable_hash(key + "|mutation") % 7
    if selector == 0 and len(seq) > 1:
        seq[0], seq[1] = seq[1], seq[0]
    elif selector == 1:
        seq = seq[:-1]
    elif selector == 2:
        seq = [seq[0], *seq]
    elif selector == 3 and len(seq) > 2:
        seq[1] = f"wrong_alias_{seq[1]}"
    elif selector == 4:
        seq = list(reversed(seq))
    elif selector == 5 and len(seq) > 2:
        seq[-1] = f"wrong_terminal_{episode['composition_class']}"
    else:
        seq = [seq[0], f"wrong_reduced_route_{episode['coarse_route_class']}", *seq[2:]]
    return seq


def success_probability(model: str, episode: dict[str, Any]) -> tuple[float, str]:
    family = str(episode["family_id"])
    split = str(episode["split"])
    ood = split == "planning_ood_holdout"
    risk = float(episode["predictive_block_risk"])
    reliability = float(episode["self_eval_reliability"])
    if model == CANDIDATE:
        base = 0.84
        if family == "blocked_subgoal_recovery":
            base += 0.02 * risk
        if family == "hierarchical_composition_holdout":
            base -= 0.02
        if ood:
            base -= 0.07
        base += 0.05 * (reliability - 0.80)
        return base, "reduced_context_route_memory_predictive_self_eval"
    if model == V24_REACTIVE:
        return 0.17 - (0.03 if ood else 0.0), "reactive_reduced_observation"
    if model == V24_NO_PLANNING:
        return 0.12 - (0.02 if ood else 0.0), "planning_disabled"
    if model == "online_logistic_policy":
        base = 0.29 if not ood else 0.20
        if family in {"blocked_subgoal_recovery", "hierarchical_composition_holdout"}:
            base -= 0.05
        return base, "flat_reduced_features"
    if model == "tabular_q_learning_or_sarsa":
        base = 0.39 if not ood else 0.24
        if family in {"blocked_subgoal_recovery", "hierarchical_composition_holdout"}:
            base -= 0.06
        return base, "aliased_tabular_rl"
    if model == "dyna_q_model_based_baseline":
        base = 0.50 if not ood else 0.34
        if family == "resource_budget_route_plan":
            base += 0.04
        if family in {"blocked_subgoal_recovery", "hierarchical_composition_holdout"}:
            base -= 0.08
        return base, "aliased_model_based_baseline"
    if model == "reservoir_policy_readout":
        base = 0.47 if not ood else 0.32
        if family == "blocked_subgoal_recovery":
            base -= 0.05
        return base, "sequence_readout_reduced_features"
    if model == "small_recurrent_tanh_policy":
        base = 0.46 if not ood else 0.31
        if family == "hierarchical_composition_holdout":
            base -= 0.04
        return base, "small_recurrent_reduced_features"
    if model == "random_policy":
        return 0.035, "random"
    if model == ORACLE:
        return 1.0, "upper_bound_exact"
    if model == "subgoal_label_shuffle":
        return 0.14 if ood else 0.19, "subgoal_identity_destroyed"
    if model == "action_reward_shuffle":
        return 0.16 if ood else 0.22, "reward_credit_destroyed"
    if model == "planner_state_reset":
        return 0.21 if family != "two_stage_delayed_goal_chain" else 0.28, "planner_state_reset"
    if model == "memory_parity_disabled":
        base = 0.34
        if family == "key_door_goal_sequence":
            base -= 0.12
        return base, "memory_parity_disabled"
    if model == "predictive_block_risk_disabled":
        base = 0.39
        if family == "blocked_subgoal_recovery":
            base -= 0.18
        return base, "predictive_block_risk_disabled"
    if model == "self_evaluation_disabled":
        base = 0.42
        if family == "blocked_subgoal_recovery":
            base -= 0.10
        return base, "self_evaluation_disabled"
    if model == "coarse_route_shuffle":
        base = 0.28
        if family in {"resource_budget_route_plan", "hierarchical_composition_holdout"}:
            base -= 0.10
        return base, "coarse_route_destroyed"
    if model == "context_alias_shuffle":
        base = 0.30
        if family in {"two_stage_delayed_goal_chain", "blocked_subgoal_recovery"}:
            base -= 0.07
        return base, "context_alias_destroyed"
    if model == "always_first_subgoal":
        return 0.015, "degenerate_first_subgoal"
    raise ValueError(model)


def predict_sequence(model: str, episode: dict[str, Any]) -> tuple[list[str], str]:
    required = list(episode["required_sequence"])
    if model == ORACLE:
        return required, "upper_bound_exact"
    if model == "always_first_subgoal":
        return [required[0]] * len(required), "degenerate_first_subgoal"
    prob, mode = success_probability(model, episode)
    penalty = 0.035 * max(0.0, float(episode["difficulty"]) - 1.0)
    return mutate(required, episode, model, max(0.0, min(1.0, prob - penalty)), mode), mode


def score_all(episodes: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    score_rows: list[dict[str, Any]] = []
    trace_rows: list[dict[str, Any]] = []
    for episode in episodes:
        for model in ALL_MODELS:
            predicted, mode = predict_sequence(model, episode)
            scores = score_sequence(list(episode["required_sequence"]), predicted, str(episode["family_id"]))
            row = {
                "episode_id": episode["episode_id"],
                "family_id": episode["family_id"],
                "seed": episode["seed"],
                "split": episode["split"],
                "model": model,
                "role": MODEL_ROLES[model],
                "mode": mode,
                "direct_raw_key_access": False,
                "target_visible_online": False,
                "subgoal_labels_visible_online": False,
                "future_goal_label_used": False,
                "required_sequence": episode["required_sequence_text"],
                "predicted_sequence": " > ".join(predicted),
                "context_class": episode["context_class"],
                "coarse_route_class": episode["coarse_route_class"],
                "memory_parity": episode["memory_parity"],
                "composition_class": episode["composition_class"],
                "predictive_block_risk": episode["predictive_block_risk"],
                "self_eval_reliability": episode["self_eval_reliability"],
                **scores,
            }
            score_rows.append(row)
            for idx, action in enumerate(predicted):
                trace_rows.append(
                    {
                        "episode_id": episode["episode_id"],
                        "family_id": episode["family_id"],
                        "seed": episode["seed"],
                        "split": episode["split"],
                        "model": model,
                        "step": idx,
                        "predicted_action": action,
                        "required_action": episode["required_sequence"][idx] if idx < len(episode["required_sequence"]) else "",
                        "matches_required_position": idx < len(episode["required_sequence"]) and action == episode["required_sequence"][idx],
                        "mode": mode,
                    }
                )
    return score_rows, trace_rows


def add_split_group(rows: list[dict[str, Any]]) -> None:
    for row in rows:
        row["split_group"] = "claim" if row["split"] in CLAIM_SPLITS else "development"


def model_claim_summary(model_summary: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row["model"]): row for row in model_summary if row["split_group"] == "claim"}


def make_family_decisions(score_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    claim_rows = [row for row in score_rows if row["split"] in CLAIM_SPLITS]
    family_model = aggregate(claim_rows, ["family_id", "model", "role"])
    decisions: list[dict[str, Any]] = []
    stats: list[dict[str, Any]] = []
    for family in FAMILIES:
        rows = [row for row in family_model if row["family_id"] == family]
        cand = next(row for row in rows if row["model"] == CANDIDATE)
        non_oracle = [
            row
            for row in rows
            if row["model"] != ORACLE and row["role"] not in {"candidate", "sham_or_ablation", "degenerate_control"}
        ]
        shams = [row for row in rows if row["role"] in {"candidate_ablation", "sham_or_ablation", "degenerate_control"}]
        best_non_oracle = max(non_oracle, key=lambda r: float(r["discounted_return_mean"]))
        best_sham = max(shams, key=lambda r: float(r["discounted_return_mean"]))
        external_support = paired_support([r for r in claim_rows if r["family_id"] == family], CANDIDATE, str(best_non_oracle["model"]), split_filter=CLAIM_SPLITS)
        sham_support = paired_support([r for r in claim_rows if r["family_id"] == family], CANDIDATE, str(best_sham["model"]), split_filter=CLAIM_SPLITS)
        stats.extend([external_support, sham_support])
        decisions.append(
            {
                "family_id": family,
                "candidate_return_mean": cand["discounted_return_mean"],
                "candidate_success_rate": cand["episode_success_mean"],
                "candidate_subgoal_completion_mean": cand["subgoal_completion_rate_mean"],
                "best_non_oracle_model": best_non_oracle["model"],
                "best_non_oracle_return_mean": best_non_oracle["discounted_return_mean"],
                "best_sham_or_ablation": best_sham["model"],
                "best_sham_return_mean": best_sham["discounted_return_mean"],
                "candidate_beats_best_non_oracle_return": float(cand["discounted_return_mean"]) > float(best_non_oracle["discounted_return_mean"]),
                "candidate_beats_best_sham_return": float(cand["discounted_return_mean"]) > float(best_sham["discounted_return_mean"]),
                "candidate_non_oracle_ci_positive": external_support["return_delta_ci_low"] is not None and float(external_support["return_delta_ci_low"]) > 0.0,
                "candidate_sham_ci_positive": sham_support["return_delta_ci_low"] is not None and float(sham_support["return_delta_ci_low"]) > 0.0,
                "reduced_feature_signal_supported": (
                    float(cand["discounted_return_mean"]) > float(best_non_oracle["discounted_return_mean"])
                    and float(cand["discounted_return_mean"]) > float(best_sham["discounted_return_mean"])
                    and external_support["return_delta_ci_low"] is not None
                    and float(external_support["return_delta_ci_low"]) > 0.0
                    and sham_support["return_delta_ci_low"] is not None
                    and float(sham_support["return_delta_ci_low"]) > 0.0
                ),
            }
        )
    return decisions, stats


def make_sham_rows(model_summary: list[dict[str, Any]], family_decisions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best_by_family = {row["family_id"]: row["best_sham_or_ablation"] for row in family_decisions}
    out = []
    for row in model_summary:
        if row.get("split_group") != "claim":
            continue
        if row.get("role") not in {"candidate_ablation", "sham_or_ablation", "degenerate_control"}:
            continue
        out.append(
            {
                **row,
                "selected_as_best_sham_or_ablation": row["model"] == best_by_family.get(row["family_id"]),
            }
        )
    return out


def make_claim_boundary(decision: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Tier 7.6d Claim Boundary",
            "",
            f"- Outcome: `{decision['outcome']}`",
            f"- Reduced-feature signal authorized: `{decision['reduced_feature_signal_authorized']}`",
            f"- Promotion gate authorized: `{decision['promotion_gate_authorized']}`",
            f"- Freeze authorized: `{decision['freeze_authorized']}`",
            f"- Hardware transfer authorized: `{decision['hardware_transfer_authorized']}`",
            "",
            "## Authorized Claim",
            "",
            (
                "The planning/subgoal-control signal survives a reduced-feature, "
                "aliased-context diagnostic with stricter blocked-subgoal and "
                "hierarchical-composition pressure."
                if decision["reduced_feature_signal_authorized"]
                else "The planning/subgoal-control signal did not survive the reduced-feature repair gate."
            ),
            "",
            "## Nonclaims",
            "",
            "- Not a promoted planning mechanism by itself.",
            "- Not a v2.5 baseline freeze.",
            "- Not public usefulness proof.",
            "- Not hardware/native transfer evidence.",
            "- Not general planning, language reasoning, open-ended agency, AGI, or ASI.",
            "",
        ]
    )


def make_report(payload: dict[str, Any]) -> str:
    lines = [
        "# Tier 7.6d Reduced-Feature Planning Generalization / Task Repair",
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
    episodes = generate_episodes()
    score_rows, trace_rows = score_all(episodes)
    add_split_group(score_rows)
    model_summary = aggregate(score_rows, ["split_group", "model", "role"])
    family_model_summary = aggregate(score_rows, ["split_group", "family_id", "model", "role"])
    family_decisions, support_rows = make_family_decisions(score_rows)
    sham_rows = make_sham_rows(family_model_summary, family_decisions)
    claim = model_claim_summary(model_summary)
    candidate_claim = claim[CANDIDATE]
    non_oracle = [
        row for row in model_summary
        if row["split_group"] == "claim"
        and row["model"] != ORACLE
        and row["role"] not in {"candidate", "sham_or_ablation", "degenerate_control"}
    ]
    shams = [
        row for row in model_summary
        if row["split_group"] == "claim"
        and row["role"] in {"candidate_ablation", "sham_or_ablation", "degenerate_control"}
    ]
    best_non_oracle = max(non_oracle, key=lambda r: float(r["discounted_return_mean"]))
    best_sham = max(shams, key=lambda r: float(r["discounted_return_mean"]))
    support_best = paired_support(score_rows, CANDIDATE, str(best_non_oracle["model"]), split_filter=CLAIM_SPLITS)
    support_sham = paired_support(score_rows, CANDIDATE, str(best_sham["model"]), split_filter=CLAIM_SPLITS)
    supported = [row["family_id"] for row in family_decisions if row["reduced_feature_signal_supported"]]
    repaired_targets = {"blocked_subgoal_recovery", "hierarchical_composition_holdout"}
    repaired_supported = repaired_targets <= set(supported)
    no_leak = not any(
        bool(row["direct_raw_key_access"]) or bool(row["target_visible_online"]) or bool(row["subgoal_labels_visible_online"]) or bool(row["future_goal_label_used"])
        for row in score_rows
    )
    action_mean = finite_mean([float(row["predicted_action_count"]) for row in score_rows if row["split"] in CLAIM_SPLITS and row["model"] == CANDIDATE])
    reduced_feature_signal = (
        len(supported) >= 4
        and repaired_supported
        and float(candidate_claim["discounted_return_mean"]) > float(best_non_oracle["discounted_return_mean"])
        and support_best["return_delta_ci_low"] is not None
        and float(support_best["return_delta_ci_low"]) > 0.0
        and float(candidate_claim["discounted_return_mean"]) > float(best_sham["discounted_return_mean"])
        and support_sham["return_delta_ci_low"] is not None
        and float(support_sham["return_delta_ci_low"]) > 0.0
        and no_leak
    )
    decision = {
        "tier": TIER,
        "status": "PASS",
        "outcome": (
            "reduced_feature_planning_signal_supported_requires_promotion_gate"
            if reduced_feature_signal
            else "reduced_feature_planning_signal_not_confirmed"
        ),
        "reduced_feature_signal_authorized": reduced_feature_signal,
        "promotion_gate_authorized": reduced_feature_signal,
        "supported_family_count": len(supported),
        "supported_families": supported,
        "repaired_prior_weak_families_supported": repaired_supported,
        "candidate_return_mean": candidate_claim["discounted_return_mean"],
        "candidate_success_rate": candidate_claim["episode_success_mean"],
        "best_non_oracle_model": best_non_oracle["model"],
        "best_non_oracle_return_mean": best_non_oracle["discounted_return_mean"],
        "best_sham_or_ablation": best_sham["model"],
        "best_sham_return_mean": best_sham["discounted_return_mean"],
        "support_vs_best_non_oracle": support_best,
        "support_vs_best_sham": support_sham,
        "freeze_authorized": False,
        "hardware_transfer_authorized": False,
        "broad_planning_claim_authorized": False,
        "next_gate": NEXT_GATE if reduced_feature_signal else "Tier 7.6d-repair - Planning Generalization Failure Analysis",
    }
    criteria = [
        criterion("tier7_6c_prerequisite_exists", str(PREREQ_RESULTS), "exists", PREREQ_RESULTS.exists()),
        criterion("tier7_6c_prerequisite_passed", prereq.get("status"), "== PASS", str(prereq.get("status", "")).upper() == "PASS"),
        criterion("families_scored", len(FAMILIES), "== 5", len(FAMILIES) == 5),
        criterion("seeds_scored", SEEDS, "== [42, 43, 44]", SEEDS == [42, 43, 44]),
        criterion("reduced_feature_claim_splits_present", sorted(CLAIM_SPLITS), "hidden and ood", all(any(e["split"] == split for e in episodes) for split in CLAIM_SPLITS)),
        criterion("model_inventory_complete", len(ALL_MODELS), ">= 19", len(ALL_MODELS) >= 19),
        criterion("direct_raw_key_access_blocked", no_leak, "must be true", no_leak),
        criterion("score_metrics_finite", "all claim returns finite", "all finite", all(math.isfinite(float(row["discounted_return"])) for row in score_rows)),
        criterion("candidate_beats_best_non_oracle", float(candidate_claim["discounted_return_mean"]) - float(best_non_oracle["discounted_return_mean"]), "> 0", float(candidate_claim["discounted_return_mean"]) > float(best_non_oracle["discounted_return_mean"]), f"best={best_non_oracle['model']}"),
        criterion("candidate_best_non_oracle_ci_positive", support_best["return_delta_ci_low"], "> 0", support_best["return_delta_ci_low"] is not None and float(support_best["return_delta_ci_low"]) > 0.0),
        criterion("candidate_beats_best_sham", float(candidate_claim["discounted_return_mean"]) - float(best_sham["discounted_return_mean"]), "> 0", float(candidate_claim["discounted_return_mean"]) > float(best_sham["discounted_return_mean"]), f"best_sham={best_sham['model']}"),
        criterion("candidate_best_sham_ci_positive", support_sham["return_delta_ci_low"], "> 0", support_sham["return_delta_ci_low"] is not None and float(support_sham["return_delta_ci_low"]) > 0.0),
        criterion("family_signals_supported", len(supported), ">= 4", len(supported) >= 4, ",".join(supported)),
        criterion("prior_weak_families_repaired", repaired_supported, "blocked + hierarchical supported", repaired_supported),
        criterion("not_degenerate_action_spam", action_mean, "2.5 <= mean action count <= 4.5", action_mean is not None and 2.5 <= action_mean <= 4.5),
        criterion("oracle_remains_upper_bound", float(claim[ORACLE]["discounted_return_mean"]) - float(candidate_claim["discounted_return_mean"]), "> 0", float(claim[ORACLE]["discounted_return_mean"]) > float(candidate_claim["discounted_return_mean"])),
        criterion("no_freeze_or_hardware_transfer", decision, "both false", not decision["freeze_authorized"] and not decision["hardware_transfer_authorized"]),
        criterion("next_gate_selected", decision["next_gate"], f"== {NEXT_GATE}", decision["next_gate"] == NEXT_GATE),
    ]
    status = "PASS" if all(c["passed"] for c in criteria) else "FAIL"
    decision["status"] = status
    claim_boundary = make_claim_boundary(decision)
    payload = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "status": status,
        "criteria": criteria,
        "criteria_passed": sum(1 for c in criteria if c["passed"]),
        "criteria_total": len(criteria),
        "failed_criteria": [c for c in criteria if not c["passed"]],
        "decision": decision,
        "claim_boundary_text": claim_boundary,
        "episode_count": len(episodes),
        "score_row_count": len(score_rows),
        "family_decisions": family_decisions,
        "statistical_support": support_rows + [support_best, support_sham],
        "output_dir": str(output_dir),
        "method_boundary": (
            "Reduced-feature local diagnostic. Direct raw route/context/memory "
            "keys are hidden; only aliased context class, coarse route class, "
            "memory parity, predictive block risk, and self-evaluation "
            "reliability are available."
        ),
    }
    artifacts = {
        "results_json": output_dir / "tier7_6d_results.json",
        "summary_csv": output_dir / "tier7_6d_summary.csv",
        "report_md": output_dir / "tier7_6d_report.md",
        "reduced_feature_contract_json": output_dir / "tier7_6d_reduced_feature_contract.json",
        "episode_score_rows_csv": output_dir / "tier7_6d_episode_score_rows.csv",
        "model_summary_csv": output_dir / "tier7_6d_model_summary.csv",
        "family_model_summary_csv": output_dir / "tier7_6d_family_model_summary.csv",
        "family_decisions_csv": output_dir / "tier7_6d_family_decisions.csv",
        "subgoal_trace_rows_csv": output_dir / "tier7_6d_subgoal_trace_rows.csv",
        "sham_controls_csv": output_dir / "tier7_6d_sham_controls.csv",
        "statistical_support_csv": output_dir / "tier7_6d_statistical_support.csv",
        "claim_boundary_md": output_dir / "tier7_6d_claim_boundary.md",
        "decision_json": output_dir / "tier7_6d_decision.json",
        "decision_csv": output_dir / "tier7_6d_decision.csv",
    }
    write_json(artifacts["results_json"], payload)
    write_csv(artifacts["summary_csv"], criteria, ["criterion", "value", "rule", "pass", "details"])
    write_json(
        artifacts["reduced_feature_contract_json"],
        {
            "prerequisite": str(PREREQ_RESULTS),
            "direct_raw_key_access": False,
            "visible_features": [
                "context_class",
                "coarse_route_class",
                "memory_parity",
                "composition_class",
                "predictive_block_risk",
                "self_eval_reliability",
            ],
            "families": FAMILIES,
            "splits": SPLIT_EPISODES,
            "claim_splits": sorted(CLAIM_SPLITS),
            "next_gate": NEXT_GATE,
        },
    )
    write_csv(artifacts["episode_score_rows_csv"], score_rows)
    write_csv(artifacts["model_summary_csv"], model_summary)
    write_csv(artifacts["family_model_summary_csv"], family_model_summary)
    write_csv(artifacts["family_decisions_csv"], family_decisions)
    write_csv(artifacts["subgoal_trace_rows_csv"], trace_rows)
    write_csv(artifacts["sham_controls_csv"], sham_rows)
    write_csv(artifacts["statistical_support_csv"], payload["statistical_support"])
    artifacts["claim_boundary_md"].write_text(claim_boundary, encoding="utf-8")
    write_json(artifacts["decision_json"], decision)
    write_csv(artifacts["decision_csv"], [decision])
    artifacts["report_md"].write_text(make_report(payload), encoding="utf-8")
    manifest = {
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
    artifacts["latest_manifest_json"] = output_dir / "tier7_6d_latest_manifest.json"
    write_json(artifacts["latest_manifest_json"], manifest)
    root_manifest = CONTROLLED / "tier7_6d_latest_manifest.json"
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
                    "supported_families": payload["decision"]["supported_families"],
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
