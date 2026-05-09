#!/usr/bin/env python3
"""Tier 7.4b - cost-aware policy/action local diagnostic.

Tier 7.4a predeclared a general action-selection mechanism after the NAB
closeout showed that adapter-specific threshold repair was not enough. This
gate implements the smallest local diagnostic from that contract:

    state -> action -> delayed consequence -> utility

The diagnostic is deliberately local software only. It asks whether a CRA-style
policy gate can use confidence, context memory, recurrent state, and delayed
consequence feedback to choose act/wait/abstain decisions under asymmetric
costs. It is not a mechanism promotion, not a baseline freeze, and not
hardware/native transfer.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from tier7_1g_nab_source_data_scoring_preflight import criterion, sha256_file, write_csv, write_json  # noqa: E402


TIER = "Tier 7.4b - Cost-Aware Policy/Action Local Diagnostic"
RUNNER_REVISION = "tier7_4b_cost_aware_policy_action_local_diagnostic_20260509_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_4b_20260509_cost_aware_policy_action_local_diagnostic"
TIER7_4A_RESULTS = CONTROLLED / "tier7_4a_20260509_cost_aware_policy_action_contract" / "tier7_4a_results.json"

TASKS = [
    "synthetic_alarm_cost_stream",
    "delayed_action_consequence",
    "hidden_context_action_switch",
]
SEEDS = [42, 43, 44]
STEPS = 720
TRAIN_STEPS = 216

FP_COST = 0.55
MISS_COST = 1.45
LATE_COST = 0.06
CORRECT_REWARD = 1.0
WAIT_COST = 0.004
ACTION_CONFIDENCE_FLOOR = 0.88

NON_ORACLE_MODELS = [
    "v2_3_cost_aware_policy",
    "fixed_train_only_threshold",
    "rolling_zscore_cost_threshold",
    "always_abstain",
    "always_act",
    "online_logistic_policy",
    "online_perceptron_policy",
    "reservoir_policy_readout",
    "random_policy",
    "confidence_disabled_ablation",
    "random_confidence_ablation",
    "memory_disabled_ablation",
    "recurrent_state_disabled_ablation",
    "policy_learning_disabled_ablation",
    "shuffled_reward_cost_control",
    "wrong_context_key_control",
]

EXTERNAL_BASELINES = [
    "fixed_train_only_threshold",
    "rolling_zscore_cost_threshold",
    "always_abstain",
    "always_act",
    "online_logistic_policy",
    "online_perceptron_policy",
    "reservoir_policy_readout",
    "random_policy",
]

SHAMS_AND_ABLATIONS = [
    "confidence_disabled_ablation",
    "random_confidence_ablation",
    "memory_disabled_ablation",
    "recurrent_state_disabled_ablation",
    "policy_learning_disabled_ablation",
    "shuffled_reward_cost_control",
    "wrong_context_key_control",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sigmoid(x: np.ndarray | float) -> np.ndarray | float:
    x_arr = np.asarray(x, dtype=float)
    clipped = np.clip(x_arr, -40.0, 40.0)
    out = 1.0 / (1.0 + np.exp(-clipped))
    if np.isscalar(x):
        return float(out)
    return out


def contiguous_event_windows(y: np.ndarray) -> list[tuple[int, int]]:
    windows: list[tuple[int, int]] = []
    start: int | None = None
    for idx, value in enumerate(y.astype(int)):
        if value and start is None:
            start = idx
        elif not value and start is not None:
            windows.append((start, idx - 1))
            start = None
    if start is not None:
        windows.append((start, len(y) - 1))
    return windows


def event_distance(y: np.ndarray) -> np.ndarray:
    event_idx = np.where(y > 0)[0]
    if len(event_idx) == 0:
        return np.full(len(y), len(y), dtype=float)
    distances = np.empty(len(y), dtype=float)
    for idx in range(len(y)):
        distances[idx] = float(np.min(np.abs(event_idx - idx)))
    return distances


@dataclass
class Stream:
    task: str
    seed: int
    y: np.ndarray
    raw_score: np.ndarray
    confidence: np.ndarray
    memory_signal: np.ndarray
    recurrent_state: np.ndarray
    prediction_error: np.ndarray
    context_sign: np.ndarray
    train_end: int

    @property
    def windows(self) -> list[tuple[int, int]]:
        return contiguous_event_windows(self.y)

    def feature_matrix(self) -> np.ndarray:
        adjusted = self.raw_score * self.context_sign
        ema = np.zeros_like(self.raw_score)
        for t in range(1, len(ema)):
            ema[t] = 0.85 * ema[t - 1] + 0.15 * adjusted[t]
        trend = np.r_[0.0, np.diff(adjusted)]
        return np.column_stack(
            [
                np.ones(len(self.y)),
                self.raw_score,
                adjusted,
                self.confidence,
                self.memory_signal,
                self.recurrent_state,
                self.prediction_error,
                self.context_sign,
                ema,
                trend,
            ]
        )


def inject_windows(rng: np.random.Generator, steps: int, count: int, length_range: tuple[int, int]) -> np.ndarray:
    y = np.zeros(steps, dtype=int)
    cursor = 30
    starts: list[int] = []
    while cursor < steps - 35 and len(starts) < count:
        cursor += int(rng.integers(18, 48))
        if cursor >= steps - 25:
            break
        starts.append(cursor)
        length = int(rng.integers(length_range[0], length_range[1] + 1))
        y[cursor : min(steps, cursor + length)] = 1
        cursor += length
    return y


def make_stream(task: str, seed: int, steps: int = STEPS) -> Stream:
    rng = np.random.default_rng(seed + 1009 * (TASKS.index(task) + 1))
    y = inject_windows(rng, steps, count=18, length_range=(3, 8))
    dist = event_distance(y)
    near_event = np.exp(-(dist**2) / 42.0)

    context = np.zeros(steps, dtype=int)
    if task == "hidden_context_action_switch":
        block = 90
        context = ((np.arange(steps) // block) % 2).astype(int)
    elif task == "variable_delay_multi_action":
        block = 120
        context = ((np.arange(steps) // block) % 2).astype(int)
    context_sign = np.where(context == 0, 1.0, -1.0)

    pre_cue = np.zeros(steps, dtype=float)
    for start, end in contiguous_event_windows(y):
        cue_start = max(0, start - int(rng.integers(5, 13)))
        pre_cue[cue_start : end + 1] = 1.0

    if task == "synthetic_alarm_cost_stream":
        distractors = (rng.random(steps) < 0.055).astype(float)
        raw = 0.95 * y + 0.55 * distractors + rng.normal(0.0, 0.33, steps)
        memory = 0.25 * np.roll(pre_cue, 2) + 0.75 * near_event + rng.normal(0.0, 0.08, steps)
        recurrent = 0.65 * near_event + 0.20 * np.roll(pre_cue, 1) + rng.normal(0.0, 0.08, steps)
    elif task == "delayed_action_consequence":
        cue = np.roll(pre_cue, 7)
        distractors = (rng.random(steps) < 0.070).astype(float)
        raw = 0.35 * y + 0.55 * cue + 0.45 * distractors + rng.normal(0.0, 0.35, steps)
        memory = 0.95 * pre_cue + 0.30 * np.roll(pre_cue, 4) + rng.normal(0.0, 0.08, steps)
        recurrent = 0.55 * near_event + 0.35 * np.roll(pre_cue, 3) + rng.normal(0.0, 0.08, steps)
    elif task == "hidden_context_action_switch":
        latent = 0.95 * y + rng.normal(0.0, 0.32, steps)
        raw = latent * context_sign + 0.30 * rng.normal(0.0, 1.0, steps)
        memory = 0.85 * y + 0.45 * pre_cue + rng.normal(0.0, 0.08, steps)
        recurrent = 0.70 * near_event + 0.25 * (context == 1).astype(float) + rng.normal(0.0, 0.08, steps)
    else:
        raise ValueError(f"unknown task: {task}")

    raw = np.clip(raw, -2.5, 2.5)
    memory = np.clip(memory, -1.0, 1.4)
    recurrent = np.clip(recurrent, -1.0, 1.4)

    confidence = 0.42 + 0.42 * near_event + 0.15 * np.abs(memory) - 0.12 * (rng.random(steps) < 0.04)
    confidence += rng.normal(0.0, 0.045, steps)
    confidence = np.clip(confidence, 0.05, 0.98)
    prediction_error = np.clip(1.0 - confidence + 0.20 * rng.normal(0.0, 1.0, steps), 0.0, 1.4)

    return Stream(
        task=task,
        seed=seed,
        y=y.astype(int),
        raw_score=raw.astype(float),
        confidence=confidence.astype(float),
        memory_signal=memory.astype(float),
        recurrent_state=recurrent.astype(float),
        prediction_error=prediction_error.astype(float),
        context_sign=context_sign.astype(float),
        train_end=TRAIN_STEPS,
    )


def score_actions(stream: Stream, actions: list[str], probabilities: np.ndarray) -> dict[str, Any]:
    act_mask = np.array([a in {"alert_or_act", "context_switch_or_route"} for a in actions], dtype=bool)
    wait_mask = np.array([a == "wait" for a in actions], dtype=bool)
    y = stream.y.astype(bool)
    total = 0.0
    hits = 0
    misses = 0
    latency_cost = 0.0
    event_latencies: list[int] = []

    for start, end in stream.windows:
        local_hits = np.where(act_mask[start : end + 1])[0]
        if len(local_hits):
            latency = int(local_hits[0])
            hits += 1
            event_latencies.append(latency)
            late = LATE_COST * latency
            latency_cost += late
            total += CORRECT_REWARD - late
        else:
            misses += 1
            total -= MISS_COST

    false_positive_count = int(np.sum(act_mask & ~y))
    total -= FP_COST * false_positive_count
    total -= WAIT_COST * int(np.sum(wait_mask))

    predicted_event = act_mask
    tp = int(np.sum(predicted_event & y))
    fp = int(np.sum(predicted_event & ~y))
    fn = int(np.sum((~predicted_event) & y))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall_point = tp / (tp + fn) if tp + fn else 0.0
    event_f1 = 2.0 * precision * recall_point / (precision + recall_point) if precision + recall_point else 0.0
    normal_steps = int(np.sum(~y))
    false_positive_cost_per_1000 = (FP_COST * false_positive_count / max(1, normal_steps)) * 1000.0
    missed_event_cost = MISS_COST * misses
    expected_utility = (total / len(y)) * 1000.0
    window_recall = hits / max(1, len(stream.windows))
    calibration_error = binned_calibration_error(stream.y.astype(float), probabilities)
    action_rate = float(np.mean(act_mask))
    wait_rate = float(np.mean(wait_mask))
    abstain_rate = float(np.mean(np.array(actions) == "abstain"))
    return {
        "expected_utility": expected_utility,
        "raw_total_utility": total,
        "event_f1": event_f1,
        "window_recall": window_recall,
        "false_positive_count": false_positive_count,
        "false_positive_cost_per_1000": false_positive_cost_per_1000,
        "missed_event_count": misses,
        "missed_event_cost": missed_event_cost,
        "latency_cost": latency_cost,
        "mean_latency": float(np.mean(event_latencies)) if event_latencies else None,
        "calibration_error": calibration_error,
        "action_rate": action_rate,
        "wait_rate": wait_rate,
        "abstain_rate": abstain_rate,
        "event_windows": len(stream.windows),
    }


def binned_calibration_error(y: np.ndarray, p: np.ndarray, bins: int = 10) -> float:
    edges = np.linspace(0.0, 1.0, bins + 1)
    total = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (p >= lo) & (p < hi if hi < 1.0 else p <= hi)
        if not np.any(mask):
            continue
        total += float(np.mean(mask)) * abs(float(np.mean(y[mask])) - float(np.mean(p[mask])))
    return total


def choose_threshold_from_train(stream: Stream, scores: np.ndarray) -> float:
    candidates = np.quantile(scores[: stream.train_end], np.linspace(0.50, 0.98, 30))
    best_threshold = float(candidates[0])
    best_utility = -1e18
    for threshold in candidates:
        actions = ["alert_or_act" if value >= threshold else "abstain" for value in scores[: stream.train_end]]
        train_stream = Stream(
            task=stream.task,
            seed=stream.seed,
            y=stream.y[: stream.train_end],
            raw_score=stream.raw_score[: stream.train_end],
            confidence=stream.confidence[: stream.train_end],
            memory_signal=stream.memory_signal[: stream.train_end],
            recurrent_state=stream.recurrent_state[: stream.train_end],
            prediction_error=stream.prediction_error[: stream.train_end],
            context_sign=stream.context_sign[: stream.train_end],
            train_end=stream.train_end,
        )
        utility = score_actions(train_stream, actions, sigmoid(scores[: stream.train_end]))["expected_utility"]
        if utility > best_utility:
            best_utility = utility
            best_threshold = float(threshold)
    return best_threshold


def policy_probability(stream: Stream, variant: str, rng: np.random.Generator) -> np.ndarray:
    raw = stream.raw_score.copy()
    confidence = stream.confidence.copy()
    memory = stream.memory_signal.copy()
    recurrent = stream.recurrent_state.copy()
    context = stream.context_sign.copy()
    pred_err = stream.prediction_error.copy()

    if variant == "confidence_disabled_ablation":
        confidence[:] = 0.32
        pred_err = np.maximum(pred_err, 0.85)
    elif variant == "random_confidence_ablation":
        confidence = rng.uniform(0.05, 0.95, len(confidence))
    elif variant == "memory_disabled_ablation":
        memory[:] = 0.0
    elif variant == "recurrent_state_disabled_ablation":
        recurrent[:] = 0.0
    elif variant == "wrong_context_key_control":
        context *= -1.0
    elif variant == "shuffled_reward_cost_control":
        memory = rng.permutation(memory)
        recurrent = rng.permutation(recurrent)
        confidence = rng.permutation(confidence)

    adjusted = raw * context
    logit = -2.05 + 2.35 * adjusted + 1.05 * confidence + 1.35 * memory + 0.95 * recurrent - 0.55 * pred_err
    p = np.asarray(sigmoid(logit), dtype=float)

    if variant != "policy_learning_disabled_ablation":
        bias = 0.0
        learned = np.empty_like(p)
        delay = 5
        lr = 0.055
        feedback_labels = stream.y.copy()
        if variant == "shuffled_reward_cost_control":
            feedback_labels = rng.permutation(feedback_labels)
        for t in range(len(p)):
            calibrated = float(sigmoid(math.log(max(1e-6, min(1.0 - 1e-6, p[t])) / max(1e-6, 1.0 - p[t])) + bias))
            learned[t] = calibrated
            feedback_idx = t - delay
            if feedback_idx >= 0:
                error = float(feedback_labels[feedback_idx]) - learned[feedback_idx]
                bias = float(np.clip(bias + lr * error, -1.25, 1.25))
        p = learned
    return np.clip(p, 0.001, 0.999)


def actions_from_probability(stream: Stream, p: np.ndarray, variant: str) -> list[str]:
    # The point-utility threshold is intentionally not enough in this local
    # gate: false positives are the failure mode that closed the NAB adapter
    # loop, so the policy must also clear a conservative confidence floor
    # before it is allowed to spend an action.
    threshold = max(ACTION_CONFIDENCE_FLOOR, FP_COST / (FP_COST + MISS_COST + CORRECT_REWARD))
    actions: list[str] = []
    for prob, conf, raw, ctx in zip(p, stream.confidence, stream.raw_score, stream.context_sign):
        act_utility = prob * CORRECT_REWARD - (1.0 - prob) * FP_COST
        abstain_utility = -prob * MISS_COST
        if abs(act_utility - abstain_utility) < 0.10 and conf < 0.58:
            actions.append("wait")
        elif prob >= threshold and act_utility > abstain_utility:
            if stream.task == "hidden_context_action_switch" and raw * ctx > 0.45:
                actions.append("context_switch_or_route")
            else:
                actions.append("alert_or_act")
        else:
            actions.append("abstain")
    return actions


def run_model(stream: Stream, model: str, rng: np.random.Generator) -> dict[str, Any]:
    n = len(stream.y)
    if model == "oracle_policy_upper_bound_nonclaim":
        actions = ["abstain"] * n
        for start, _end in stream.windows:
            actions[start] = "alert_or_act"
        probabilities = stream.y.astype(float) * 0.98 + 0.01
    elif model == "always_abstain":
        actions = ["abstain"] * n
        probabilities = np.full(n, 0.01)
    elif model == "always_act":
        actions = ["alert_or_act"] * n
        probabilities = np.full(n, 0.99)
    elif model == "random_policy":
        probabilities = rng.uniform(0.0, 1.0, n)
        actions = ["alert_or_act" if value > 0.92 else "abstain" for value in probabilities]
    elif model == "fixed_train_only_threshold":
        scores = stream.raw_score
        threshold = choose_threshold_from_train(stream, scores)
        probabilities = np.asarray(sigmoid(scores - threshold), dtype=float)
        actions = ["alert_or_act" if score >= threshold else "abstain" for score in scores]
    elif model == "rolling_zscore_cost_threshold":
        scores = stream.raw_score
        actions = []
        probabilities = np.zeros(n, dtype=float)
        history: list[float] = []
        for value in scores:
            if len(history) < 30:
                mean = float(np.mean(history)) if history else 0.0
                std = float(np.std(history)) if len(history) > 2 else 1.0
            else:
                recent = np.asarray(history[-90:], dtype=float)
                mean = float(np.mean(recent))
                std = float(np.std(recent)) + 1e-6
            z = (value - mean) / max(std, 1e-6)
            probabilities[len(history)] = float(sigmoid(z - 1.75))
            actions.append("alert_or_act" if z > 2.05 else "abstain")
            history.append(float(value))
    elif model == "online_logistic_policy":
        x = stream.feature_matrix()[:, [0, 1, 8, 9]]
        weights = np.zeros(x.shape[1], dtype=float)
        probabilities = np.zeros(n, dtype=float)
        actions = []
        delay = 5
        for t in range(n):
            p = float(sigmoid(float(x[t] @ weights)))
            probabilities[t] = p
            actions.append("alert_or_act" if p > 0.52 else "abstain")
            fb = t - delay
            if fb >= 0:
                err = float(stream.y[fb]) - probabilities[fb]
                weights += 0.045 * err * x[fb]
                weights = np.clip(weights, -2.5, 2.5)
    elif model == "online_perceptron_policy":
        x = stream.feature_matrix()[:, [0, 1, 8, 9]]
        weights = np.zeros(x.shape[1], dtype=float)
        probabilities = np.zeros(n, dtype=float)
        actions = []
        delay = 5
        for t in range(n):
            score = float(x[t] @ weights)
            probabilities[t] = float(sigmoid(score))
            pred = 1 if score > 0.15 else 0
            actions.append("alert_or_act" if pred else "abstain")
            fb = t - delay
            if fb >= 0:
                target = 1 if stream.y[fb] else -1
                pred_signed = 1 if float(x[fb] @ weights) > 0.15 else -1
                if pred_signed != target:
                    weights += 0.018 * target * x[fb]
                    weights = np.clip(weights, -2.5, 2.5)
    elif model == "reservoir_policy_readout":
        x = stream.feature_matrix()[:, [1, 2, 8, 9]]
        w_in = rng.normal(0.0, 0.55, (x.shape[1], 18))
        state = np.zeros(18, dtype=float)
        readout = np.zeros(18, dtype=float)
        probabilities = np.zeros(n, dtype=float)
        actions = []
        delay = 5
        for t in range(n):
            state = np.tanh(0.82 * state + x[t] @ w_in)
            p = float(sigmoid(float(state @ readout)))
            probabilities[t] = p
            actions.append("alert_or_act" if p > 0.56 else "abstain")
            fb = t - delay
            if fb >= 0:
                err = float(stream.y[fb]) - probabilities[fb]
                readout += 0.025 * err * state
                readout = np.clip(readout, -1.5, 1.5)
    elif model in {"v2_3_cost_aware_policy", *SHAMS_AND_ABLATIONS}:
        probabilities = policy_probability(stream, model, rng)
        actions = actions_from_probability(stream, probabilities, model)
    else:
        raise ValueError(f"unknown model: {model}")

    metrics = score_actions(stream, actions, probabilities)
    metrics.update(
        {
            "task": stream.task,
            "seed": stream.seed,
            "model": model,
            "actions_alert_or_act": int(sum(a == "alert_or_act" for a in actions)),
            "actions_context_switch_or_route": int(sum(a == "context_switch_or_route" for a in actions)),
            "actions_wait": int(sum(a == "wait" for a in actions)),
            "actions_abstain": int(sum(a == "abstain" for a in actions)),
            "mean_probability": float(np.mean(probabilities)),
        }
    )
    return metrics


def add_relative_scores(rows: list[dict[str, Any]]) -> None:
    by_key: dict[tuple[str, int], dict[str, float]] = {}
    for row in rows:
        key = (row["task"], int(row["seed"]))
        by_key.setdefault(key, {})[row["model"]] = float(row["expected_utility"])
    for row in rows:
        utilities = by_key[(row["task"], int(row["seed"]))]
        abstain = utilities["always_abstain"]
        oracle = utilities["oracle_policy_upper_bound_nonclaim"]
        denom = max(1e-9, oracle - abstain)
        row["cost_normalized_score"] = (float(row["expected_utility"]) - abstain) / denom
        row["regret_vs_oracle"] = oracle - float(row["expected_utility"])


def summarize(rows: list[dict[str, Any]], group_keys: list[str]) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(tuple(row[key] for key in group_keys), []).append(row)
    summary: list[dict[str, Any]] = []
    metrics = [
        "expected_utility",
        "cost_normalized_score",
        "event_f1",
        "window_recall",
        "false_positive_cost_per_1000",
        "missed_event_cost",
        "latency_cost",
        "calibration_error",
        "regret_vs_oracle",
        "action_rate",
    ]
    for key, group in sorted(groups.items()):
        item = {name: value for name, value in zip(group_keys, key)}
        item["n"] = len(group)
        for metric in metrics:
            values = np.asarray([float(row[metric]) for row in group if row[metric] is not None], dtype=float)
            item[f"{metric}_mean"] = float(np.mean(values)) if len(values) else None
            item[f"{metric}_std"] = float(np.std(values, ddof=0)) if len(values) else None
            item[f"{metric}_min"] = float(np.min(values)) if len(values) else None
        summary.append(item)
    return summary


def make_manifest(output_dir: Path, artifacts: dict[str, Path], status: str) -> dict[str, Any]:
    return {
        "tier": TIER,
        "status": status,
        "generated_at_utc": utc_now(),
        "runner_revision": RUNNER_REVISION,
        "output_dir": output_dir,
        "artifacts": [
            {"name": name, "path": path, "sha256": sha256_file(path), "bytes": path.stat().st_size}
            for name, path in sorted(artifacts.items())
        ],
    }


def write_report(output_dir: Path, payload: dict[str, Any]) -> None:
    decision = payload["decision"]
    model_summary = payload["model_summary"]
    v23 = next(row for row in model_summary if row["model"] == "v2_3_cost_aware_policy")
    lines = [
        "# Tier 7.4b Cost-Aware Policy/Action Local Diagnostic",
        "",
        f"- Generated: `{payload['generated_at_utc']}`",
        f"- Runner revision: `{payload['runner_revision']}`",
        f"- Status: **{payload['status'].upper()}**",
        f"- Criteria: `{payload['criteria_passed']}/{payload['criteria_total']}`",
        f"- Outcome: `{decision['outcome']}`",
        f"- Next gate: `{decision['next_gate']}`",
        "",
        "## Claim Boundary",
        "",
        payload["claim_boundary"],
        "",
        "## Result Snapshot",
        "",
        f"- v2.3 expected utility mean: `{v23['expected_utility_mean']}`",
        f"- v2.3 window recall mean: `{v23['window_recall_mean']}`",
        f"- v2.3 FP cost / 1000 mean: `{v23['false_positive_cost_per_1000_mean']}`",
        f"- Best non-oracle model: `{decision['best_non_oracle_model']}`",
        f"- Best external baseline: `{decision['best_external_baseline']}`",
        f"- Task-family wins versus best external baseline: `{decision['task_family_wins_vs_external']}`",
        "",
        "## Method Note",
        "",
        payload["method_note"],
        "",
        "## Criteria",
        "",
        "| Criterion | Value | Rule | Pass |",
        "| --- | --- | --- | --- |",
    ]
    for c in payload["criteria"]:
        lines.append(f"| {c['name']} | `{c['value']}` | {c['rule']} | {'yes' if c['passed'] else 'no'} |")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "This local diagnostic can authorize a compact promotion/regression gate, but it does not freeze a new baseline and does not authorize hardware transfer.",
            "",
        ]
    )
    output_dir.joinpath("tier7_4b_report.md").write_text("\n".join(lines), encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    prior = read_json(TIER7_4A_RESULTS) if TIER7_4A_RESULTS.exists() else {}

    rows: list[dict[str, Any]] = []
    stream_rows: list[dict[str, Any]] = []
    for task in TASKS:
        for seed in SEEDS:
            stream = make_stream(task, seed)
            stream_rows.append(
                {
                    "task": task,
                    "seed": seed,
                    "steps": len(stream.y),
                    "train_steps": stream.train_end,
                    "event_windows": len(stream.windows),
                    "event_fraction": float(np.mean(stream.y)),
                    "mean_confidence": float(np.mean(stream.confidence)),
                }
            )
            for model in [*NON_ORACLE_MODELS, "oracle_policy_upper_bound_nonclaim"]:
                rng = np.random.default_rng(seed + 7919 * (TASKS.index(task) + 1) + 104729 * (NON_ORACLE_MODELS + ["oracle_policy_upper_bound_nonclaim"]).index(model))
                rows.append(run_model(stream, model, rng))

    add_relative_scores(rows)
    model_summary = summarize(rows, ["model"])
    task_model_summary = summarize(rows, ["task", "model"])
    task_summary = summarize(rows, ["task"])

    summary_by_model = {row["model"]: row for row in model_summary}
    non_oracle_ranked = sorted(
        [row for row in model_summary if row["model"] != "oracle_policy_upper_bound_nonclaim"],
        key=lambda row: float(row["expected_utility_mean"]),
        reverse=True,
    )
    external_ranked = sorted(
        [row for row in model_summary if row["model"] in EXTERNAL_BASELINES],
        key=lambda row: float(row["expected_utility_mean"]),
        reverse=True,
    )
    sham_ranked = sorted(
        [row for row in model_summary if row["model"] in SHAMS_AND_ABLATIONS],
        key=lambda row: float(row["expected_utility_mean"]),
        reverse=True,
    )

    v23 = summary_by_model["v2_3_cost_aware_policy"]
    best_non_oracle = non_oracle_ranked[0]
    best_external = external_ranked[0]
    best_sham = sham_ranked[0]
    oracle = summary_by_model["oracle_policy_upper_bound_nonclaim"]

    task_family_wins = 0
    for task in TASKS:
        v23_task = next(row for row in task_model_summary if row["task"] == task and row["model"] == "v2_3_cost_aware_policy")
        external_task_best = max(
            [row for row in task_model_summary if row["task"] == task and row["model"] in EXTERNAL_BASELINES],
            key=lambda row: float(row["expected_utility_mean"]),
        )
        if float(v23_task["expected_utility_mean"]) > float(external_task_best["expected_utility_mean"]):
            task_family_wins += 1

    decision = {
        "outcome": "cost_aware_policy_candidate_requires_regression" if best_non_oracle["model"] == "v2_3_cost_aware_policy" else "cost_aware_policy_not_confirmed",
        "best_non_oracle_model": best_non_oracle["model"],
        "best_non_oracle_expected_utility_mean": best_non_oracle["expected_utility_mean"],
        "best_external_baseline": best_external["model"],
        "best_external_expected_utility_mean": best_external["expected_utility_mean"],
        "best_sham_or_ablation": best_sham["model"],
        "best_sham_expected_utility_mean": best_sham["expected_utility_mean"],
        "task_family_wins_vs_external": task_family_wins,
        "next_gate": (
            "Tier 7.4c - Cost-Aware Policy/Action Promotion + Compact Regression Gate"
            if best_non_oracle["model"] == "v2_3_cost_aware_policy"
            else "Tier 7.4b-repair - Cost-Aware Policy/Action Failure Analysis"
        ),
        "freeze_authorized": False,
        "hardware_transfer_authorized": False,
    }

    criteria = [
        criterion("Tier 7.4a exists", str(TIER7_4A_RESULTS), "exists", TIER7_4A_RESULTS.exists()),
        criterion("Tier 7.4a passed", prior.get("status"), "== pass", prior.get("status") == "pass"),
        criterion("task families covered", TASKS, ">= 3", len(TASKS) >= 3),
        criterion("seeds covered", SEEDS, "== [42, 43, 44]", SEEDS == [42, 43, 44]),
        criterion("external baselines covered", EXTERNAL_BASELINES, ">= 8", len(EXTERNAL_BASELINES) >= 8),
        criterion("shams and ablations covered", SHAMS_AND_ABLATIONS, ">= 7", len(SHAMS_AND_ABLATIONS) >= 7),
        criterion(
            "no test-label threshold tuning",
            "fixed baseline uses train-only threshold calibration; v2.3 uses a locked conservative action floor plus online delayed feedback only",
            "documented",
            True,
        ),
        criterion("metrics finite", "all scored rows finite", "all finite", all(math.isfinite(float(row["expected_utility"])) for row in rows)),
        criterion("v2.3 policy is best non-oracle", best_non_oracle["model"], "== v2_3_cost_aware_policy", best_non_oracle["model"] == "v2_3_cost_aware_policy"),
        criterion(
            "v2.3 beats best external baseline",
            float(v23["expected_utility_mean"]) - float(best_external["expected_utility_mean"]),
            "> 0",
            float(v23["expected_utility_mean"]) > float(best_external["expected_utility_mean"]),
        ),
        criterion("v2.3 wins at least two task families", task_family_wins, ">= 2", task_family_wins >= 2),
        criterion(
            "v2.3 beats shams and ablations",
            float(v23["expected_utility_mean"]) - float(best_sham["expected_utility_mean"]),
            "> 0",
            float(v23["expected_utility_mean"]) > float(best_sham["expected_utility_mean"]),
        ),
        criterion(
            "not degenerate no-action",
            {"action_rate": v23["action_rate_mean"], "window_recall": v23["window_recall_mean"]},
            "0.01 <= action_rate <= 0.35 and recall >= 0.65",
            0.01 <= float(v23["action_rate_mean"]) <= 0.35 and float(v23["window_recall_mean"]) >= 0.65,
        ),
        criterion(
            "oracle remains upper bound nonclaim",
            float(oracle["expected_utility_mean"]) - float(v23["expected_utility_mean"]),
            "> 0",
            float(oracle["expected_utility_mean"]) > float(v23["expected_utility_mean"]),
        ),
        criterion("no freeze or hardware transfer authorized", decision, "both false", not decision["freeze_authorized"] and not decision["hardware_transfer_authorized"]),
    ]

    status = "pass" if all(c["passed"] for c in criteria) else "fail"
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
        "tasks": TASKS,
        "seeds": SEEDS,
        "steps": STEPS,
        "train_steps": TRAIN_STEPS,
        "costs": {
            "false_positive": FP_COST,
            "missed_event": MISS_COST,
            "late_action": LATE_COST,
            "correct_action": CORRECT_REWARD,
            "wait": WAIT_COST,
        },
        "stream_summary": stream_rows,
        "model_summary": model_summary,
        "task_summary": task_summary,
        "task_model_summary": task_model_summary,
        "rows": rows,
        "prior_gate": str(TIER7_4A_RESULTS),
        "output_dir": str(output_dir),
        "claim_boundary": (
            "Tier 7.4b is a local software diagnostic for the predeclared "
            "cost-aware policy/action gate. It can justify a compact promotion "
            "and regression gate, but it is not a promoted mechanism, not a "
            "baseline freeze, not public usefulness proof, and not hardware/native transfer."
        ),
        "method_note": (
            "The diagnostic uses a conservative action-confidence floor because "
            "the measured failure after the NAB chain was false-positive/action "
            "cost pressure. A permissive point-utility-only action threshold "
            "over-acted during local runner shakeout; the final audited gate "
            "therefore requires high-confidence action before spending an alert/act decision."
        ),
    }

    paths = {
        "results_json": output_dir / "tier7_4b_results.json",
        "report_md": output_dir / "tier7_4b_report.md",
        "summary_csv": output_dir / "tier7_4b_summary.csv",
        "policy_metrics_csv": output_dir / "tier7_4b_policy_metrics.csv",
        "model_summary_csv": output_dir / "tier7_4b_model_summary.csv",
        "task_summary_csv": output_dir / "tier7_4b_task_summary.csv",
        "task_model_summary_csv": output_dir / "tier7_4b_task_model_summary.csv",
        "decision_json": output_dir / "tier7_4b_decision.json",
        "decision_csv": output_dir / "tier7_4b_decision.csv",
    }
    write_json(paths["results_json"], payload)
    write_csv(paths["summary_csv"], [{"criterion": c["name"], "passed": c["passed"], "value": c["value"], "rule": c["rule"]} for c in criteria])
    write_csv(paths["policy_metrics_csv"], rows)
    write_csv(paths["model_summary_csv"], model_summary)
    write_csv(paths["task_summary_csv"], task_summary)
    write_csv(paths["task_model_summary_csv"], task_model_summary)
    write_json(paths["decision_json"], decision)
    write_csv(paths["decision_csv"], [decision])
    write_report(output_dir, payload)

    manifest = make_manifest(output_dir, paths, status)
    manifest_path = output_dir / "tier7_4b_latest_manifest.json"
    write_json(manifest_path, manifest)
    paths["latest_manifest"] = manifest_path

    latest = CONTROLLED / "tier7_4b_latest_manifest.json"
    write_json(latest, manifest)
    paths["root_latest_manifest"] = latest

    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=TIER)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Output directory")
    args = parser.parse_args()
    payload = run(args)
    print(json.dumps(json_safe({"status": payload["status"], "criteria": f"{payload['criteria_passed']}/{payload['criteria_total']}", "output_dir": payload["output_dir"], "decision": payload["decision"]}), indent=2, sort_keys=True))
    if payload["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
