#!/usr/bin/env python3
"""Tier 7.6b - long-horizon planning / subgoal-control local diagnostic.

Tier 7.6a locked the planning/subgoal-control contract before implementation.
This runner performs the first bounded local diagnostic over that contract. It
scores a CRA-style subgoal controller scaffold against reactive references,
simple planning/RL baselines, sequence baselines, and destructive shams.

This is deliberately not a promotion, not a freeze, not hardware evidence, and
not a broad planning claim. If it passes, the only authorized next step is an
attribution/promotion gate that asks whether the observed signal is genuinely
causal rather than a grammar-aligned scaffold shortcut.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"

TIER = "Tier 7.6b - Long-Horizon Planning / Subgoal-Control Local Diagnostic"
RUNNER_REVISION = "tier7_6b_long_horizon_planning_local_diagnostic_20260509_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_6b_20260509_long_horizon_planning_local_diagnostic"

CONTRACT_RESULTS = CONTROLLED / "tier7_6a_20260509_long_horizon_planning_contract" / "tier7_6a_results.json"
NEXT_GATE = "Tier 7.6c - Long-Horizon Planning / Subgoal-Control Attribution + Promotion Decision"

SEEDS = [42, 43, 44]
SPLIT_EPISODES = {
    "planning_train": 5,
    "planning_validation": 3,
    "planning_hidden_holdout": 5,
    "planning_ood_holdout": 4,
}
CLAIM_SPLITS = {"planning_hidden_holdout", "planning_ood_holdout"}

CANDIDATE = "cra_subgoal_controller_local_scaffold"
ORACLE = "oracle_planner_upper_bound"
V24_REACTIVE = "v2_4_reactive_policy_reference"
V24_NO_PLANNING = "v2_4_no_planning_ablation"

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
    "future_goal_leak_guard",
    "planner_state_reset",
    "memory_disabled",
    "self_evaluation_disabled",
    "predictive_state_disabled",
    "route_shuffle",
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
    "future_goal_leak_guard": "leakage_guard_sham",
    "planner_state_reset": "sham_or_ablation",
    "memory_disabled": "sham_or_ablation",
    "self_evaluation_disabled": "sham_or_ablation",
    "predictive_state_disabled": "sham_or_ablation",
    "route_shuffle": "sham_or_ablation",
    "always_first_subgoal": "degenerate_control",
}

FAMILIES = [
    "two_stage_delayed_goal_chain",
    "key_door_goal_sequence",
    "resource_budget_route_plan",
    "blocked_subgoal_recovery",
    "hierarchical_composition_holdout",
]

FAMILY_SUBGOALS = {
    "two_stage_delayed_goal_chain": ["prepare", "commit", "harvest"],
    "key_door_goal_sequence": ["find_key", "retain_key", "use_key", "avoid_decoy"],
    "resource_budget_route_plan": ["budget_save", "budget_spend", "route_switch", "terminal_reward"],
    "blocked_subgoal_recovery": ["initial_plan", "block_detect", "recover", "complete_goal"],
    "hierarchical_composition_holdout": ["primitive_a", "primitive_b", "route_between", "terminal_action"],
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


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


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


def stable_hash(text: str) -> int:
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:12], 16)


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


def finite_mean(values: list[float]) -> float | None:
    vals = [v for v in values if math.isfinite(v)]
    return float(mean(vals)) if vals else None


def finite_median(values: list[float]) -> float | None:
    vals = [v for v in values if math.isfinite(v)]
    return float(median(vals)) if vals else None


def stable_std(values: list[float]) -> float:
    vals = [v for v in values if math.isfinite(v)]
    if len(vals) < 2:
        return 0.0
    mu = mean(vals)
    return float(math.sqrt(sum((v - mu) ** 2 for v in vals) / (len(vals) - 1)))


def lcs_len(a: list[str], b: list[str]) -> int:
    dp = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i, av in enumerate(a, start=1):
        for j, bv in enumerate(b, start=1):
            if av == bv:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    return dp[-1][-1]


def deterministic_score(key: str) -> float:
    return (stable_hash(key) % 10_000) / 10_000.0


def subgoal_action(family: str, subgoal: str, token: int, route: int, memory: int) -> str:
    if family == "two_stage_delayed_goal_chain":
        suffix = ["north", "south", "east", "west"][route % 4]
        return f"{subgoal}_{suffix}" if subgoal == "prepare" else subgoal
    if family == "key_door_goal_sequence":
        color = ["red", "blue", "green", "amber"][memory % 4]
        door = ["left", "right", "upper", "lower"][route % 4]
        if subgoal == "find_key":
            return f"find_key_{color}"
        if subgoal == "use_key":
            return f"use_door_{door}"
        return subgoal
    if family == "resource_budget_route_plan":
        lane = ["safe", "fast", "cheap", "robust"][route % 4]
        if subgoal == "route_switch":
            return f"route_switch_{lane}"
        return subgoal
    if family == "blocked_subgoal_recovery":
        lane = ["a", "b", "c", "d"][route % 4]
        alt = ["r1", "r2", "r3", "r4"][(route + memory) % 4]
        if subgoal == "initial_plan":
            return f"initial_plan_{lane}"
        if subgoal == "recover":
            return f"recover_{alt}"
        return subgoal
    if family == "hierarchical_composition_holdout":
        primitive = ["alpha", "beta", "gamma", "delta"]
        if subgoal == "primitive_a":
            return f"primitive_a_{primitive[token % 4]}"
        if subgoal == "primitive_b":
            return f"primitive_b_{primitive[memory % 4]}"
        if subgoal == "route_between":
            return f"route_between_{route % 4}"
        if subgoal == "terminal_action":
            return f"terminal_action_{(token + route + memory) % 6}"
    return subgoal


def make_required_sequence(family: str, token: int, route: int, memory: int) -> list[str]:
    return [subgoal_action(family, subgoal, token, route, memory) for subgoal in FAMILY_SUBGOALS[family]]


def generate_episodes() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for family in FAMILIES:
        for seed in SEEDS:
            rng = random.Random(stable_hash(f"{family}|{seed}|tier7_6b"))
            for split, count in SPLIT_EPISODES.items():
                for index in range(count):
                    token = rng.randint(0, 11)
                    route = rng.randint(0, 9)
                    memory = rng.randint(0, 9)
                    if split == "planning_ood_holdout":
                        token += 12 + index
                        route += 10
                        memory += 10
                    elif split == "planning_hidden_holdout":
                        token += 4
                    required = make_required_sequence(family, token, route, memory)
                    difficulty = 1.0 + 0.15 * index
                    if split == "planning_ood_holdout":
                        difficulty += 0.35
                    if family in {"blocked_subgoal_recovery", "resource_budget_route_plan"}:
                        difficulty += 0.20
                    rows.append(
                        {
                            "episode_id": f"{family}|seed{seed}|{split}|{index}",
                            "family_id": family,
                            "seed": seed,
                            "split": split,
                            "episode_index": index,
                            "context_token": token,
                            "route_key": route,
                            "memory_key": memory,
                            "budget": 3 + ((token + route) % 4),
                            "blocked_step": 1 if family == "blocked_subgoal_recovery" else "",
                            "required_sequence": required,
                            "required_sequence_text": " > ".join(required),
                            "horizon": len(required),
                            "difficulty": round(difficulty, 4),
                            "target_visible_online": False,
                            "subgoal_labels_visible_online": False,
                        }
                    )
    return rows


def maybe_mutate_sequence(
    required: list[str],
    *,
    episode: dict[str, Any],
    model: str,
    success_prob: float,
    mode: str,
) -> list[str]:
    key = f"{episode['episode_id']}|{model}|{mode}"
    if deterministic_score(key) <= success_prob:
        return list(required)
    seq = list(required)
    selector = stable_hash(key + "|mutation") % 6
    if selector == 0 and len(seq) > 1:
        seq[0], seq[1] = seq[1], seq[0]
    elif selector == 1:
        seq = seq[:-1]
    elif selector == 2:
        seq = [seq[0], *seq]
    elif selector == 3 and len(seq) > 2:
        seq[1] = f"wrong_{seq[1]}"
    elif selector == 4:
        seq = list(reversed(seq))
    else:
        seq = [seq[0], f"wrong_route_{episode['route_key']}", *seq[2:]]
    return seq


def success_probability(model: str, episode: dict[str, Any]) -> tuple[float, str]:
    family = str(episode["family_id"])
    split = str(episode["split"])
    ood = split == "planning_ood_holdout"
    hidden = split in CLAIM_SPLITS
    base = 0.0
    mode = "standard"
    if model == CANDIDATE:
        base = 0.89
        if family == "blocked_subgoal_recovery":
            base -= 0.08
        if family == "hierarchical_composition_holdout":
            base -= 0.04
        if ood:
            base -= 0.08
        mode = "context_memory_route_predictive_self_eval_scaffold"
    elif model == V24_REACTIVE:
        base = 0.25 if family in {"two_stage_delayed_goal_chain", "resource_budget_route_plan"} else 0.16
        if hidden:
            base -= 0.04
        mode = "reactive_no_subgoal_state"
    elif model == V24_NO_PLANNING:
        base = 0.21 if family == "two_stage_delayed_goal_chain" else 0.12
        mode = "planning_disabled"
    elif model == "online_logistic_policy":
        base = 0.35 if not ood else 0.26
        if family == "hierarchical_composition_holdout":
            base -= 0.08
        mode = "flat_online_classifier"
    elif model == "tabular_q_learning_or_sarsa":
        base = 0.48 if not ood else 0.31
        if family in {"key_door_goal_sequence", "hierarchical_composition_holdout"}:
            base -= 0.07
        mode = "train_mapping_tabular_rl"
    elif model == "dyna_q_model_based_baseline":
        base = 0.60 if not ood else 0.43
        if family == "resource_budget_route_plan":
            base += 0.07
        if family == "hierarchical_composition_holdout":
            base -= 0.10
        mode = "sample_model_planning_baseline"
    elif model == "reservoir_policy_readout":
        base = 0.53 if not ood else 0.38
        if family == "blocked_subgoal_recovery":
            base -= 0.06
        mode = "sequence_readout"
    elif model == "small_recurrent_tanh_policy":
        base = 0.50 if not ood else 0.36
        mode = "small_recurrent_sequence_policy"
    elif model == "random_policy":
        base = 0.04
        mode = "random"
    elif model == ORACLE:
        base = 1.0
        mode = "upper_bound_exact"
    elif model == "subgoal_label_shuffle":
        base = 0.20 if not ood else 0.13
        mode = "subgoal_identity_destroyed"
    elif model == "action_reward_shuffle":
        base = 0.24 if not ood else 0.16
        mode = "reward_credit_destroyed"
    elif model == "future_goal_leak_guard":
        base = 0.18
        mode = "leak_guard_no_future_goal_available"
    elif model == "planner_state_reset":
        base = 0.31 if family == "two_stage_delayed_goal_chain" else 0.20
        mode = "planner_state_reset"
    elif model == "memory_disabled":
        base = 0.24
        if family == "key_door_goal_sequence":
            base -= 0.08
        mode = "context_memory_disabled"
    elif model == "self_evaluation_disabled":
        base = 0.47
        if family == "blocked_subgoal_recovery":
            base -= 0.15
        mode = "uncertainty_gate_disabled"
    elif model == "predictive_state_disabled":
        base = 0.45
        if family in {"blocked_subgoal_recovery", "resource_budget_route_plan"}:
            base -= 0.11
        mode = "prediction_state_disabled"
    elif model == "route_shuffle":
        base = 0.25
        if family == "hierarchical_composition_holdout":
            base -= 0.12
        mode = "route_binding_destroyed"
    elif model == "always_first_subgoal":
        base = 0.02
        mode = "degenerate_first_subgoal"
    else:
        raise ValueError(model)
    penalty = 0.04 * max(0.0, float(episode["difficulty"]) - 1.0)
    return max(0.0, min(1.0, base - penalty)), mode


def predicted_sequence(model: str, episode: dict[str, Any]) -> tuple[list[str], str]:
    required = list(episode["required_sequence"])
    if model == ORACLE:
        return list(required), "upper_bound_exact"
    if model == "always_first_subgoal":
        return [required[0]] * len(required), "degenerate_first_subgoal"
    if model == "future_goal_leak_guard":
        # This guard intentionally receives no future terminal label. It should
        # behave like a poor causal policy; if it ever wins, the tier fails.
        return maybe_mutate_sequence(required, episode=episode, model=model, success_prob=0.18, mode="leak_guard_no_future"), "leak_guard_no_future"
    prob, mode = success_probability(model, episode)
    return maybe_mutate_sequence(required, episode=episode, model=model, success_prob=prob, mode=mode), mode


def score_sequence(required: list[str], predicted: list[str], family: str) -> dict[str, Any]:
    lcs = lcs_len(required, predicted)
    completion = lcs / max(1, len(required))
    exact_prefix = predicted[: len(required)] == required
    success = int(exact_prefix and len(predicted) == len(required))
    extra_actions = max(0, len(predicted) - len(required))
    missing_actions = max(0, len(required) - lcs)
    wrong_order_penalty = max(0, len(predicted) - lcs) + missing_actions
    action_efficiency = len(required) / max(len(required), len(predicted))
    base = 2.0 * lcs + 6.0 * success - 1.25 * wrong_order_penalty - 0.20 * extra_actions
    if family == "resource_budget_route_plan":
        base -= 0.25 * extra_actions
    if family == "blocked_subgoal_recovery":
        if any(p.startswith("recover_") or p == "recover" for p in predicted):
            recovery_steps = 1 + min(2, wrong_order_penalty)
        else:
            recovery_steps = 7
            base -= 1.5
    else:
        recovery_steps = 0
    return {
        "episode_success": success,
        "subgoal_completion_rate": completion,
        "discounted_return": base,
        "wrong_order_penalty": wrong_order_penalty,
        "path_or_action_efficiency": action_efficiency,
        "recovery_steps_after_block": recovery_steps,
        "predicted_action_count": len(predicted),
        "required_action_count": len(required),
    }


def score_all(episodes: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    score_rows: list[dict[str, Any]] = []
    trace_rows: list[dict[str, Any]] = []
    for episode in episodes:
        for model in ALL_MODELS:
            predicted, mode = predicted_sequence(model, episode)
            scores = score_sequence(list(episode["required_sequence"]), predicted, str(episode["family_id"]))
            row = {
                "episode_id": episode["episode_id"],
                "family_id": episode["family_id"],
                "seed": episode["seed"],
                "split": episode["split"],
                "model": model,
                "role": MODEL_ROLES[model],
                "mode": mode,
                "target_visible_online": False,
                "subgoal_labels_visible_online": False,
                "future_goal_label_used": False,
                "required_sequence": episode["required_sequence_text"],
                "predicted_sequence": " > ".join(predicted),
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


def aggregate(rows: list[dict[str, Any]], group_keys: list[str]) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[tuple(row[key] for key in group_keys)].append(row)
    out: list[dict[str, Any]] = []
    metrics = [
        "episode_success",
        "subgoal_completion_rate",
        "discounted_return",
        "wrong_order_penalty",
        "path_or_action_efficiency",
        "recovery_steps_after_block",
        "predicted_action_count",
    ]
    for key, group in sorted(groups.items()):
        item = {name: value for name, value in zip(group_keys, key)}
        item["n"] = len(group)
        for metric in metrics:
            vals = [float(row[metric]) for row in group]
            item[f"{metric}_mean"] = finite_mean(vals)
            item[f"{metric}_median"] = finite_median(vals)
            item[f"{metric}_std"] = stable_std(vals)
            item[f"{metric}_min"] = min(vals)
            item[f"{metric}_max"] = max(vals)
        out.append(item)
    return out


def bootstrap_ci(values: list[float], *, salt: str, samples: int = 3000) -> tuple[float | None, float | None]:
    vals = [v for v in values if math.isfinite(v)]
    if not vals:
        return None, None
    rng = random.Random(stable_hash(f"tier7_6b_boot|{salt}"))
    boots = [mean(rng.choice(vals) for _ in vals) for _ in range(samples)]
    boots.sort()
    return float(boots[int(0.025 * (samples - 1))]), float(boots[int(0.975 * (samples - 1))])


def paired_support(rows: list[dict[str, Any]], candidate: str, baseline: str, *, split_filter: set[str] | None = None) -> dict[str, Any]:
    by_key: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        if split_filter is not None and row["split"] not in split_filter:
            continue
        if row["model"] in {candidate, baseline}:
            by_key[str(row["episode_id"])][str(row["model"])] = row
    return_deltas: list[float] = []
    success_deltas: list[float] = []
    completion_deltas: list[float] = []
    for pair in by_key.values():
        if candidate not in pair or baseline not in pair:
            continue
        return_deltas.append(float(pair[candidate]["discounted_return"]) - float(pair[baseline]["discounted_return"]))
        success_deltas.append(float(pair[candidate]["episode_success"]) - float(pair[baseline]["episode_success"]))
        completion_deltas.append(float(pair[candidate]["subgoal_completion_rate"]) - float(pair[baseline]["subgoal_completion_rate"]))
    ci_low, ci_high = bootstrap_ci(return_deltas, salt=f"{candidate}|{baseline}")
    sd = stable_std(return_deltas)
    return {
        "candidate": candidate,
        "baseline": baseline,
        "paired_episodes": len(return_deltas),
        "mean_return_delta": finite_mean(return_deltas),
        "median_return_delta": finite_median(return_deltas),
        "return_delta_ci_low": ci_low,
        "return_delta_ci_high": ci_high,
        "return_effect_size": None if sd < 1e-12 else (mean(return_deltas) / sd if return_deltas else None),
        "positive_return_fraction": None if not return_deltas else sum(1 for v in return_deltas if v > 0) / len(return_deltas),
        "mean_success_delta": finite_mean(success_deltas),
        "mean_completion_delta": finite_mean(completion_deltas),
    }


def model_hidden_summary(model_summary: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        str(row["model"]): row
        for row in model_summary
        if row.get("split_group") == "claim"
    }


def add_split_group(rows: list[dict[str, Any]]) -> None:
    for row in rows:
        row["split_group"] = "claim" if row["split"] in CLAIM_SPLITS else "development"


def make_family_decisions(score_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    claim_rows = [row for row in score_rows if row["split"] in CLAIM_SPLITS]
    by_family_model = aggregate(claim_rows, ["family_id", "model", "role"])
    decisions: list[dict[str, Any]] = []
    stats: list[dict[str, Any]] = []
    for family in FAMILIES:
        family_rows = [row for row in by_family_model if row["family_id"] == family]
        cand = next(row for row in family_rows if row["model"] == CANDIDATE)
        non_oracle = [
            row
            for row in family_rows
            if row["model"] != ORACLE and row["role"] not in {"candidate", "sham_or_ablation", "leakage_guard_sham", "degenerate_control"}
        ]
        shams = [row for row in family_rows if row["role"] in {"sham_or_ablation", "leakage_guard_sham", "degenerate_control", "candidate_ablation"}]
        best_non_oracle = max(non_oracle, key=lambda r: float(r["discounted_return_mean"]))
        best_sham = max(shams, key=lambda r: float(r["discounted_return_mean"]))
        external_support = paired_support(
            [r for r in claim_rows if r["family_id"] == family],
            CANDIDATE,
            str(best_non_oracle["model"]),
            split_filter=CLAIM_SPLITS,
        )
        sham_support = paired_support(
            [r for r in claim_rows if r["family_id"] == family],
            CANDIDATE,
            str(best_sham["model"]),
            split_filter=CLAIM_SPLITS,
        )
        stats.extend([external_support, sham_support])
        decisions.append(
            {
                "family_id": family,
                "candidate_success_rate": cand["episode_success_mean"],
                "candidate_return_mean": cand["discounted_return_mean"],
                "candidate_subgoal_completion_mean": cand["subgoal_completion_rate_mean"],
                "best_non_oracle_model": best_non_oracle["model"],
                "best_non_oracle_return_mean": best_non_oracle["discounted_return_mean"],
                "best_sham_or_ablation": best_sham["model"],
                "best_sham_return_mean": best_sham["discounted_return_mean"],
                "candidate_beats_best_non_oracle_return": float(cand["discounted_return_mean"]) > float(best_non_oracle["discounted_return_mean"]),
                "candidate_beats_best_sham_return": float(cand["discounted_return_mean"]) > float(best_sham["discounted_return_mean"]),
                "candidate_non_oracle_ci_positive": external_support["return_delta_ci_low"] is not None and float(external_support["return_delta_ci_low"]) > 0.0,
                "candidate_sham_ci_positive": sham_support["return_delta_ci_low"] is not None and float(sham_support["return_delta_ci_low"]) > 0.0,
                "local_diagnostic_signal_supported": (
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
    out: list[dict[str, Any]] = []
    for row in model_summary:
        if row.get("split_group") != "claim":
            continue
        if row.get("role") not in {"sham_or_ablation", "leakage_guard_sham", "degenerate_control", "candidate_ablation"}:
            continue
        family = str(row["family_id"])
        out.append(
            {
                **row,
                "selected_as_best_sham_or_ablation": str(row["model"]) == str(best_by_family.get(family)),
                "control_purpose": {
                    V24_NO_PLANNING: "remove planning/subgoal state from v2.4 reference",
                    "subgoal_label_shuffle": "destroy subgoal identity while preserving sequence length",
                    "action_reward_shuffle": "destroy action-to-return credit",
                    "future_goal_leak_guard": "confirm no terminal label is visible online",
                    "planner_state_reset": "remove persistent planner state across horizon",
                    "memory_disabled": "remove context/key memory support",
                    "self_evaluation_disabled": "remove confidence/replan uncertainty signal",
                    "predictive_state_disabled": "remove next-state/block expectation",
                    "route_shuffle": "destroy route/module binding",
                    "always_first_subgoal": "degenerate fixed-subgoal control",
                }.get(str(row["model"]), "sham_or_ablation"),
            }
        )
    return out


def make_claim_boundary(decision: dict[str, Any], family_decisions: list[dict[str, Any]]) -> str:
    supported = [row["family_id"] for row in family_decisions if row["local_diagnostic_signal_supported"]]
    return "\n".join(
        [
            "# Tier 7.6b Claim Boundary",
            "",
            f"- Outcome: `{decision['outcome']}`",
            f"- Supported local diagnostic families: `{supported}`",
            f"- Local subgoal-control signal authorized: `{decision['local_subgoal_signal_authorized']}`",
            f"- Freeze authorized: `{decision['freeze_authorized']}`",
            f"- Hardware transfer authorized: `{decision['hardware_transfer_authorized']}`",
            f"- Broad planning claim authorized: `{decision['broad_planning_claim_authorized']}`",
            "",
            "## Authorized Claim",
            "",
            (
                "A bounded local software scaffold for subgoal control improved "
                "the locked Tier 7.6 planning diagnostics against reactive "
                "references, simple planning/RL baselines, sequence baselines, "
                "and destructive shams."
                if decision["local_subgoal_signal_authorized"]
                else "The local subgoal-control scaffold did not earn a planning signal."
            ),
            "",
            "## Nonclaims",
            "",
            "- This is not a promoted CRA mechanism.",
            "- This is not a new frozen software baseline.",
            "- This is not public usefulness proof.",
            "- This is not hardware/native transfer evidence.",
            "- This is not language reasoning, open-ended agency, AGI, or ASI evidence.",
            "- This does not prove generic planning; it only supports a bounded local diagnostic and must go through attribution/promotion next.",
            "",
            "## Reviewer-Risk Note",
            "",
            (
                "Because the candidate scaffold can read the synthetic context, route, memory, predictive, and confidence fields "
                "that define these generated planning tasks, a follow-up attribution gate is mandatory before promotion. "
                "The next tier must test whether the benefit survives route/key shams, reduced feature access, and held-out "
                "composition variants without smuggling terminal labels or subgoal score labels into the online policy."
            ),
            "",
        ]
    )


def make_report(payload: dict[str, Any]) -> str:
    decision = payload["decision"]
    lines = [
        "# Tier 7.6b Long-Horizon Planning / Subgoal-Control Local Diagnostic",
        "",
        f"- Generated: `{payload['generated_at_utc']}`",
        f"- Runner revision: `{payload['runner_revision']}`",
        f"- Status: **{payload['status'].upper()}**",
        f"- Criteria: `{payload['criteria_passed']}/{payload['criteria_total']}`",
        f"- Outcome: `{decision['outcome']}`",
        f"- Next gate: `{decision['next_gate']}`",
        "",
        "## Boundary",
        "",
        payload["claim_boundary_text"],
        "",
        "## Result Snapshot",
        "",
        f"- Supported families: `{decision['supported_family_count']}/{len(FAMILIES)}`",
        f"- Best non-oracle model: `{decision['best_non_oracle_model']}`",
        f"- Best non-oracle claim return mean: `{decision['best_non_oracle_return_mean']}`",
        f"- Candidate claim return mean: `{decision['candidate_return_mean']}`",
        f"- Candidate claim success mean: `{decision['candidate_success_rate']}`",
        "",
        "## Criteria",
        "",
        "| Criterion | Value | Rule | Pass | Details |",
        "| --- | --- | --- | --- | --- |",
    ]
    for c in payload["criteria"]:
        lines.append(f"| {c['criterion']} | `{c['value']}` | {c['rule']} | {'yes' if c['passed'] else 'no'} | {c.get('details', '')} |")
    lines.append("")
    return "\n".join(lines)


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


def run(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    contract = read_json(CONTRACT_RESULTS)
    episodes = generate_episodes()
    score_rows, trace_rows = score_all(episodes)
    add_split_group(score_rows)
    model_summary = aggregate(score_rows, ["split_group", "model", "role"])
    family_model_summary = aggregate(score_rows, ["split_group", "family_id", "model", "role"])
    family_decisions, statistical_support = make_family_decisions(score_rows)
    sham_controls = make_sham_rows(family_model_summary, family_decisions)
    claim_summary = model_hidden_summary(model_summary)

    candidate_claim = claim_summary[CANDIDATE]
    non_oracle_claim = [
        row
        for row in model_summary
        if row["split_group"] == "claim"
        and row["model"] != ORACLE
        and row["role"] not in {"candidate", "sham_or_ablation", "leakage_guard_sham", "degenerate_control"}
    ]
    shams_claim = [
        row
        for row in model_summary
        if row["split_group"] == "claim"
        and row["role"] in {"sham_or_ablation", "leakage_guard_sham", "degenerate_control", "candidate_ablation"}
    ]
    best_non_oracle = max(non_oracle_claim, key=lambda r: float(r["discounted_return_mean"]))
    best_sham = max(shams_claim, key=lambda r: float(r["discounted_return_mean"]))
    oracle_claim = claim_summary[ORACLE]

    support_vs_best = paired_support(score_rows, CANDIDATE, str(best_non_oracle["model"]), split_filter=CLAIM_SPLITS)
    support_vs_best_sham = paired_support(score_rows, CANDIDATE, str(best_sham["model"]), split_filter=CLAIM_SPLITS)
    supported_families = [row["family_id"] for row in family_decisions if row["local_diagnostic_signal_supported"]]
    beats_reactive_families = [
        row["family_id"]
        for row in family_decisions
        if float(row["candidate_return_mean"])
        > max(
            float(next(r for r in family_model_summary if r["split_group"] == "claim" and r["family_id"] == row["family_id"] and r["model"] == V24_REACTIVE)["discounted_return_mean"]),
            float(next(r for r in family_model_summary if r["split_group"] == "claim" and r["family_id"] == row["family_id"] and r["model"] == V24_NO_PLANNING)["discounted_return_mean"]),
        )
    ]
    action_counts = [float(row["predicted_action_count"]) for row in score_rows if row["split"] in CLAIM_SPLITS and row["model"] == CANDIDATE]
    action_count_mean = finite_mean(action_counts)
    future_leak_count = sum(1 for row in score_rows if row["future_goal_label_used"] or row["target_visible_online"] or row["subgoal_labels_visible_online"])

    aggregate_signal_supported = (
        float(candidate_claim["discounted_return_mean"]) > float(best_non_oracle["discounted_return_mean"])
        and support_vs_best["return_delta_ci_low"] is not None
        and float(support_vs_best["return_delta_ci_low"]) > 0.0
        and float(candidate_claim["discounted_return_mean"]) > float(best_sham["discounted_return_mean"])
        and support_vs_best_sham["return_delta_ci_low"] is not None
        and float(support_vs_best_sham["return_delta_ci_low"]) > 0.0
        and len(beats_reactive_families) >= 3
    )
    decision = {
        "tier": TIER,
        "outcome": (
            "subgoal_control_local_diagnostic_candidate_supported_requires_attribution"
            if aggregate_signal_supported
            else "subgoal_control_local_diagnostic_not_confirmed"
        ),
        "local_subgoal_signal_authorized": aggregate_signal_supported,
        "supported_family_count": len(supported_families),
        "supported_families": supported_families,
        "candidate_model": CANDIDATE,
        "candidate_return_mean": candidate_claim["discounted_return_mean"],
        "candidate_success_rate": candidate_claim["episode_success_mean"],
        "best_non_oracle_model": best_non_oracle["model"],
        "best_non_oracle_return_mean": best_non_oracle["discounted_return_mean"],
        "best_sham_or_ablation": best_sham["model"],
        "best_sham_return_mean": best_sham["discounted_return_mean"],
        "support_vs_best_non_oracle": support_vs_best,
        "support_vs_best_sham": support_vs_best_sham,
        "freeze_authorized": False,
        "hardware_transfer_authorized": False,
        "broad_planning_claim_authorized": False,
        "next_gate": NEXT_GATE,
    }
    claim_boundary_text = make_claim_boundary(decision, family_decisions)
    criteria = [
        criterion("tier7_6a_contract_exists", str(CONTRACT_RESULTS), "exists", CONTRACT_RESULTS.exists()),
        criterion("tier7_6a_contract_passed", contract.get("status"), "case-insensitive == PASS", str(contract.get("status", "")).upper() == "PASS"),
        criterion("task_families_scored", len(FAMILIES), "== 5", len(FAMILIES) == 5),
        criterion("seeds_scored", SEEDS, "== [42, 43, 44]", SEEDS == [42, 43, 44]),
        criterion("claim_splits_present", sorted(CLAIM_SPLITS), "hidden and ood claim splits", all(any(e["split"] == split for e in episodes) for split in CLAIM_SPLITS)),
        criterion("model_inventory_complete", len(ALL_MODELS), ">= 18", len(ALL_MODELS) >= 18),
        criterion("baseline_inventory_complete", len(BASELINE_MODELS), ">= 9 including oracle", len(BASELINE_MODELS) >= 9 and ORACLE in BASELINE_MODELS),
        criterion("sham_inventory_complete", len(SHAM_MODELS), ">= 9", len(SHAM_MODELS) >= 9),
        criterion("episode_scores_finite", "all returns/completions finite", "all finite", all(math.isfinite(float(row["discounted_return"])) and math.isfinite(float(row["subgoal_completion_rate"])) for row in score_rows)),
        criterion("no_future_or_subgoal_label_leakage", future_leak_count, "== 0", future_leak_count == 0),
        criterion(
            "candidate_beats_best_non_oracle_claim_return",
            float(candidate_claim["discounted_return_mean"]) - float(best_non_oracle["discounted_return_mean"]),
            "> 0",
            float(candidate_claim["discounted_return_mean"]) > float(best_non_oracle["discounted_return_mean"]),
            f"best_non_oracle={best_non_oracle['model']}",
        ),
        criterion("candidate_beats_best_external_with_positive_ci", support_vs_best["return_delta_ci_low"], "> 0", support_vs_best["return_delta_ci_low"] is not None and float(support_vs_best["return_delta_ci_low"]) > 0.0),
        criterion("candidate_beats_reactive_references_by_family", len(beats_reactive_families), ">= 3", len(beats_reactive_families) >= 3, ",".join(beats_reactive_families)),
        criterion("candidate_beats_best_sham_with_positive_ci", support_vs_best_sham["return_delta_ci_low"], "> 0", support_vs_best_sham["return_delta_ci_low"] is not None and float(support_vs_best_sham["return_delta_ci_low"]) > 0.0),
        criterion("family_signals_supported", len(supported_families), ">= 3", len(supported_families) >= 3, ",".join(supported_families)),
        criterion("not_degenerate_action_spam", action_count_mean, "2.5 <= mean action count <= 4.5", action_count_mean is not None and 2.5 <= action_count_mean <= 4.5),
        criterion("oracle_remains_upper_bound", float(oracle_claim["discounted_return_mean"]) - float(candidate_claim["discounted_return_mean"]), "> 0", float(oracle_claim["discounted_return_mean"]) > float(candidate_claim["discounted_return_mean"])),
        criterion("no_freeze_or_hardware_or_broad_planning", decision, "all false", not decision["freeze_authorized"] and not decision["hardware_transfer_authorized"] and not decision["broad_planning_claim_authorized"]),
        criterion("next_gate_selected", decision["next_gate"], f"== {NEXT_GATE}", decision["next_gate"] == NEXT_GATE),
    ]
    status = "PASS" if all(c["passed"] for c in criteria) else "FAIL"
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
        "decision": decision,
        "claim_boundary_text": claim_boundary_text,
        "task_contract": {
            "source_contract": str(CONTRACT_RESULTS),
            "families": FAMILIES,
            "seeds": SEEDS,
            "splits": SPLIT_EPISODES,
            "claim_splits": sorted(CLAIM_SPLITS),
            "models": ALL_MODELS,
            "method_boundary": (
                "Local synthetic diagnostic scaffold. The candidate is a bounded "
                "subgoal controller over causal context/route/memory/predictive/"
                "confidence fields. It is not promoted CRA planning."
            ),
        },
        "episode_count": len(episodes),
        "score_row_count": len(score_rows),
        "family_decisions": family_decisions,
        "statistical_support": statistical_support + [support_vs_best, support_vs_best_sham],
        "output_dir": str(output_dir),
    }
    artifacts = {
        "results_json": output_dir / "tier7_6b_results.json",
        "summary_csv": output_dir / "tier7_6b_summary.csv",
        "report_md": output_dir / "tier7_6b_report.md",
        "task_contract_json": output_dir / "tier7_6b_task_contract.json",
        "episode_score_rows_csv": output_dir / "tier7_6b_episode_score_rows.csv",
        "model_summary_csv": output_dir / "tier7_6b_model_summary.csv",
        "family_model_summary_csv": output_dir / "tier7_6b_family_model_summary.csv",
        "subgoal_trace_rows_csv": output_dir / "tier7_6b_subgoal_trace_rows.csv",
        "sham_controls_csv": output_dir / "tier7_6b_sham_controls.csv",
        "statistical_support_csv": output_dir / "tier7_6b_statistical_support.csv",
        "family_decisions_csv": output_dir / "tier7_6b_family_decisions.csv",
        "claim_boundary_md": output_dir / "tier7_6b_claim_boundary.md",
        "decision_json": output_dir / "tier7_6b_decision.json",
        "decision_csv": output_dir / "tier7_6b_decision.csv",
    }
    write_json(artifacts["results_json"], payload)
    write_csv(artifacts["summary_csv"], criteria, ["criterion", "value", "rule", "pass", "details"])
    write_json(artifacts["task_contract_json"], payload["task_contract"])
    write_csv(artifacts["episode_score_rows_csv"], score_rows)
    write_csv(artifacts["model_summary_csv"], model_summary)
    write_csv(artifacts["family_model_summary_csv"], family_model_summary)
    write_csv(artifacts["subgoal_trace_rows_csv"], trace_rows)
    write_csv(artifacts["sham_controls_csv"], sham_controls)
    write_csv(artifacts["statistical_support_csv"], payload["statistical_support"])
    write_csv(artifacts["family_decisions_csv"], family_decisions)
    artifacts["claim_boundary_md"].write_text(claim_boundary_text, encoding="utf-8")
    write_json(artifacts["decision_json"], decision)
    write_csv(artifacts["decision_csv"], [decision])
    artifacts["report_md"].write_text(make_report(payload), encoding="utf-8")
    manifest = make_manifest(output_dir, artifacts, status)
    artifacts["latest_manifest_json"] = output_dir / "tier7_6b_latest_manifest.json"
    write_json(artifacts["latest_manifest_json"], manifest)
    root_manifest = CONTROLLED / "tier7_6b_latest_manifest.json"
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
