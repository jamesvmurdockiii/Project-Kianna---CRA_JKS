#!/usr/bin/env python3
"""Tier 5.12a predictive task-pressure validation.

Tier 5.12 should not start by adding a predictive/world-model mechanism and
hoping the benchmark is meaningful. This harness first validates predictive
pressure: the current sensory value and sign-persistence shortcuts must fail,
while a correct causal predictive signal can solve the task without feedback
leakage.

This is task-validation evidence only. It is not CRA predictive coding, not a
world model, not language grounding, and not a new frozen baseline.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except Exception as exc:  # pragma: no cover - optional plotting dependency
    plt = None
    MATPLOTLIB_ERROR = str(exc)
else:
    MATPLOTLIB_ERROR = None

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from tier2_learning import criterion, markdown_value, pass_fail, safe_corr, strict_sign, write_csv, write_json  # noqa: E402
from tier4_scaling import mean, min_value, seeds_from_args, stdev  # noqa: E402
from tier5_external_baselines import (  # noqa: E402
    FeatureBuilder,
    LEARNER_FACTORIES,
    TaskStream,
    TestResult,
    build_parser as build_tier5_1_parser,
    parse_models,
    summarize_rows,
)


TIER = "Tier 5.12a - Predictive Task-Pressure Validation"
DEFAULT_TASKS = "hidden_regime_switching,masked_input_prediction,event_stream_prediction,sensor_anomaly_prediction"
DEFAULT_MODELS = "sign_persistence,online_perceptron,online_logistic_regression,echo_state_network,small_gru,stdp_only_snn"
CONTROL_MODELS = (
    "current_reflex",
    "sign_persistence_control",
    "rolling_majority",
    "predictive_memory",
    "wrong_horizon_control",
    "shuffled_target_control",
)
EPS = 1e-12


@dataclass(frozen=True)
class PredictiveTask:
    stream: TaskStream
    event_type: list[str]
    phase: list[str]
    trial_id: np.ndarray
    context_sign: np.ndarray
    cue_a_sign: np.ndarray
    cue_b_sign: np.ndarray
    predictive_signal: np.ndarray
    wrong_horizon_signal: np.ndarray
    shuffled_target_signal: np.ndarray


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.ndarray):
        return [json_safe(v) for v in value.tolist()]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        f = float(value)
        return None if math.isnan(f) or math.isinf(f) else f
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def init_arrays(steps: int) -> dict[str, Any]:
    return {
        "sensory": np.zeros(steps, dtype=float),
        "current_target": np.zeros(steps, dtype=float),
        "evaluation_target": np.zeros(steps, dtype=float),
        "evaluation_mask": np.zeros(steps, dtype=bool),
        "feedback_due": np.full(steps, -1, dtype=int),
        "event_type": ["none" for _ in range(steps)],
        "phase": ["none" for _ in range(steps)],
        "trial_id": np.full(steps, -1, dtype=int),
        "context_sign": np.zeros(steps, dtype=int),
        "cue_a_sign": np.zeros(steps, dtype=int),
        "cue_b_sign": np.zeros(steps, dtype=int),
        "predictive_signal": np.zeros(steps, dtype=float),
    }


def balanced_pair(index: int) -> tuple[int, int]:
    cycle = ((1, 1), (1, -1), (-1, 1), (-1, -1))
    return cycle[index % len(cycle)]


def finalize_task(
    *,
    name: str,
    display_name: str,
    steps: int,
    arrays: dict[str, Any],
    amplitude: float,
    seed: int,
    rng: np.random.Generator,
    metadata: dict[str, Any],
    switch_steps: list[int] | None = None,
) -> PredictiveTask:
    evaluation_mask = arrays["evaluation_mask"]
    evaluation_target = arrays["evaluation_target"]
    predictive_signal = arrays["predictive_signal"].copy()
    eval_steps = np.flatnonzero(evaluation_mask & (np.asarray([strict_sign(v) for v in evaluation_target]) != 0))
    eval_targets = np.asarray([strict_sign(float(evaluation_target[step])) for step in eval_steps], dtype=float)
    wrong_horizon_signal = np.zeros(steps, dtype=float)
    shuffled_target_signal = np.zeros(steps, dtype=float)
    if len(eval_steps) > 0:
        shifted = np.roll(eval_targets, 2 if len(eval_targets) > 2 else 1)
        shuffled = eval_targets.copy()
        rng.shuffle(shuffled)
        wrong_horizon_signal[eval_steps] = shifted
        shuffled_target_signal[eval_steps] = shuffled
    stream = TaskStream(
        name=name,
        display_name=display_name,
        domain=name,
        steps=steps,
        sensory=arrays["sensory"],
        current_target=arrays["current_target"],
        evaluation_target=evaluation_target,
        evaluation_mask=evaluation_mask,
        feedback_due_step=arrays["feedback_due"],
        switch_steps=switch_steps or [],
        metadata={
            **metadata,
            "task_kind": name,
            "decision_events": int(len(eval_steps)),
            "feedback": "delayed",
            "feedback_due_after_prediction": True,
            "amplitude": amplitude,
            "task_seed": int(seed),
        },
    )
    return PredictiveTask(
        stream=stream,
        event_type=arrays["event_type"],
        phase=arrays["phase"],
        trial_id=arrays["trial_id"],
        context_sign=arrays["context_sign"],
        cue_a_sign=arrays["cue_a_sign"],
        cue_b_sign=arrays["cue_b_sign"],
        predictive_signal=predictive_signal,
        wrong_horizon_signal=wrong_horizon_signal,
        shuffled_target_signal=shuffled_target_signal,
    )


def hidden_regime_switching_task(*, steps: int, amplitude: float, seed: int, args: argparse.Namespace) -> PredictiveTask:
    rng = np.random.default_rng(seed + 1201)
    arrays = init_arrays(steps)
    period = int(args.predictive_period)
    horizon = int(args.predictive_horizon)
    block = int(args.predictive_regime_block)
    trial_id = 0
    switch_steps: list[int] = []
    for start in range(2, steps - horizon, period):
        block_index = start // max(1, block)
        regime = 1 if block_index % 2 == 0 else -1
        if start % block < period:
            switch_steps.append(start)
            arrays["event_type"][start] = "regime_marker"
        cue = 1 if (trial_id + int(rng.integers(0, 2))) % 2 == 0 else -1
        label = regime * cue
        arrays["sensory"][start] = amplitude * cue
        arrays["current_target"][min(start + horizon, steps - 1)] = amplitude * label
        arrays["evaluation_target"][start] = amplitude * label
        arrays["evaluation_mask"][start] = True
        arrays["feedback_due"][start] = start + horizon
        arrays["trial_id"][start] = trial_id
        arrays["context_sign"][start] = regime
        arrays["cue_a_sign"][start] = cue
        arrays["predictive_signal"][start] = float(label)
        arrays["phase"][start] = f"regime_{block_index}"
        trial_id += 1
    return finalize_task(
        name="hidden_regime_switching",
        display_name="Hidden Regime Switching",
        steps=steps,
        arrays=arrays,
        amplitude=amplitude,
        seed=seed,
        rng=rng,
        metadata={"period": period, "horizon": horizon, "regime_block": block, "trials": trial_id},
        switch_steps=sorted(set(switch_steps)),
    )


def masked_input_prediction_task(*, steps: int, amplitude: float, seed: int, args: argparse.Namespace) -> PredictiveTask:
    rng = np.random.default_rng(seed + 1301)
    arrays = init_arrays(steps)
    period = int(args.masked_period)
    gap = int(args.masked_gap)
    horizon = int(args.predictive_horizon)
    trial_id = 0
    for start in range(0, steps - max(gap, horizon) - 3, period):
        cue_a, cue_b = balanced_pair(trial_id + int(rng.integers(0, 4)))
        decision = start + gap
        label = cue_a * cue_b
        arrays["sensory"][start] = 0.8 * amplitude * cue_a
        arrays["sensory"][start + 1] = 0.8 * amplitude * cue_b
        arrays["event_type"][start] = "visible_cue_a"
        arrays["event_type"][start + 1] = "visible_cue_b"
        arrays["phase"][start] = "visible"
        arrays["phase"][start + 1] = "visible"
        arrays["event_type"][decision] = "masked_decision"
        arrays["phase"][decision] = "masked"
        arrays["current_target"][min(decision + horizon, steps - 1)] = amplitude * label
        arrays["evaluation_target"][decision] = amplitude * label
        arrays["evaluation_mask"][decision] = True
        arrays["feedback_due"][decision] = decision + horizon
        for step in (start, start + 1, decision):
            arrays["trial_id"][step] = trial_id
            arrays["cue_a_sign"][step] = cue_a
            arrays["cue_b_sign"][step] = cue_b
        arrays["predictive_signal"][decision] = float(label)
        trial_id += 1
    return finalize_task(
        name="masked_input_prediction",
        display_name="Masked Input Prediction",
        steps=steps,
        arrays=arrays,
        amplitude=amplitude,
        seed=seed,
        rng=rng,
        metadata={"period": period, "gap": gap, "horizon": horizon, "trials": trial_id},
    )


def event_stream_prediction_task(*, steps: int, amplitude: float, seed: int, args: argparse.Namespace) -> PredictiveTask:
    rng = np.random.default_rng(seed + 1401)
    arrays = init_arrays(steps)
    period = int(args.event_period)
    horizon = int(args.predictive_horizon)
    trial_id = 0
    for start in range(0, steps - horizon - 3, period):
        cue_a, cue_b = balanced_pair(trial_id + int(rng.integers(0, 4)))
        decision = start + 2
        label = cue_a * cue_b
        arrays["sensory"][start] = amplitude * cue_a
        arrays["sensory"][start + 1] = amplitude * cue_b
        arrays["sensory"][decision] = 0.0
        arrays["event_type"][start] = "event_a"
        arrays["event_type"][start + 1] = "event_b"
        arrays["event_type"][decision] = "predict_next_event"
        arrays["phase"][start] = "event_stream"
        arrays["phase"][start + 1] = "event_stream"
        arrays["phase"][decision] = "prediction"
        arrays["current_target"][min(decision + horizon, steps - 1)] = amplitude * label
        arrays["evaluation_target"][decision] = amplitude * label
        arrays["evaluation_mask"][decision] = True
        arrays["feedback_due"][decision] = decision + horizon
        for step in (start, start + 1, decision):
            arrays["trial_id"][step] = trial_id
            arrays["cue_a_sign"][step] = cue_a
            arrays["cue_b_sign"][step] = cue_b
        arrays["predictive_signal"][decision] = float(label)
        trial_id += 1
    return finalize_task(
        name="event_stream_prediction",
        display_name="Event Stream Prediction",
        steps=steps,
        arrays=arrays,
        amplitude=amplitude,
        seed=seed,
        rng=rng,
        metadata={"period": period, "horizon": horizon, "trials": trial_id},
    )


def sensor_anomaly_prediction_task(*, steps: int, amplitude: float, seed: int, args: argparse.Namespace) -> PredictiveTask:
    rng = np.random.default_rng(seed + 1501)
    arrays = init_arrays(steps)
    period = int(args.anomaly_period)
    horizon = int(args.predictive_horizon)
    trial_id = 0
    for start in range(1, steps - horizon - 4, period):
        cue_a, cue_b = balanced_pair(trial_id + int(rng.integers(0, 4)))
        decision = start + 3
        label = cue_a * cue_b
        arrays["sensory"][start] = 0.6 * amplitude * cue_a
        arrays["sensory"][start + 1] = 0.25 * amplitude * int(rng.choice([-1, 1]))
        arrays["sensory"][start + 2] = 0.6 * amplitude * cue_b
        arrays["sensory"][decision] = 0.0
        arrays["event_type"][start] = "precursor_a"
        arrays["event_type"][start + 1] = "distractor"
        arrays["event_type"][start + 2] = "precursor_b"
        arrays["event_type"][decision] = "anomaly_forecast"
        arrays["phase"][start] = "precursor"
        arrays["phase"][start + 1] = "distractor"
        arrays["phase"][start + 2] = "precursor"
        arrays["phase"][decision] = "forecast"
        arrays["current_target"][min(decision + horizon, steps - 1)] = amplitude * label
        arrays["evaluation_target"][decision] = amplitude * label
        arrays["evaluation_mask"][decision] = True
        arrays["feedback_due"][decision] = decision + horizon
        for step in (start, start + 1, start + 2, decision):
            arrays["trial_id"][step] = trial_id
            arrays["cue_a_sign"][step] = cue_a
            arrays["cue_b_sign"][step] = cue_b
        arrays["predictive_signal"][decision] = float(label)
        trial_id += 1
    return finalize_task(
        name="sensor_anomaly_prediction",
        display_name="Sensor Anomaly Prediction",
        steps=steps,
        arrays=arrays,
        amplitude=amplitude,
        seed=seed,
        rng=rng,
        metadata={"period": period, "horizon": horizon, "trials": trial_id},
    )


def build_tasks(args: argparse.Namespace, seed: int) -> list[PredictiveTask]:
    factories = {
        "hidden_regime_switching": hidden_regime_switching_task,
        "masked_input_prediction": masked_input_prediction_task,
        "event_stream_prediction": event_stream_prediction_task,
        "sensor_anomaly_prediction": sensor_anomaly_prediction_task,
    }
    names = [item.strip() for item in args.tasks.split(",") if item.strip()]
    if not names or names == ["all"]:
        names = [item.strip() for item in DEFAULT_TASKS.split(",")]
    missing = [name for name in names if name not in factories]
    if missing:
        raise argparse.ArgumentTypeError(f"unknown Tier 5.12a tasks: {', '.join(missing)}")
    return [factories[name](steps=args.steps, amplitude=args.amplitude, seed=seed, args=args) for name in names]


def task_pressure_summary(task: PredictiveTask) -> dict[str, Any]:
    by_current: dict[int, set[int]] = {}
    by_last: dict[int, set[int]] = {}
    last_nonzero = 0
    for step in range(task.stream.steps):
        s = strict_sign(float(task.stream.sensory[step]))
        if s != 0:
            last_nonzero = s
        if not bool(task.stream.evaluation_mask[step]):
            continue
        label = strict_sign(float(task.stream.evaluation_target[step]))
        if label == 0:
            continue
        by_current.setdefault(s, set()).add(label)
        by_last.setdefault(last_nonzero, set()).add(label)
    return {
        "same_current_input_opposite_labels": any(len(values) > 1 for values in by_current.values()),
        "same_last_sign_opposite_labels": any(len(values) > 1 for values in by_last.values()),
        "ambiguous_current_bins": sum(1 for values in by_current.values() if len(values) > 1),
        "ambiguous_last_sign_bins": sum(1 for values in by_last.values() if len(values) > 1),
        "decision_count": int(np.sum(task.stream.evaluation_mask)),
    }


def control_prediction(model: str, task: PredictiveTask, step: int, memory: dict[str, Any], window: int) -> float:
    sensory = float(task.stream.sensory[step])
    sensory_sign = strict_sign(sensory)
    if sensory_sign != 0:
        memory["last_nonzero"] = sensory_sign
        history = memory.setdefault("history", [])
        history.append(sensory_sign)
        if len(history) > window:
            del history[:-window]
    if model == "current_reflex":
        return float(sensory_sign)
    if model == "sign_persistence_control":
        return float(memory.get("last_nonzero", 1))
    if model == "rolling_majority":
        history = memory.get("history", [])
        if not history:
            return 1.0
        total = sum(int(v) for v in history[-window:])
        return float(strict_sign(total) or history[-1])
    if model == "predictive_memory":
        return float(task.predictive_signal[step])
    if model == "wrong_horizon_control":
        return float(task.wrong_horizon_signal[step])
    if model == "shuffled_target_control":
        return float(task.shuffled_target_signal[step])
    raise ValueError(f"unknown control model: {model}")


def run_control_model(task: PredictiveTask, model: str, *, seed: int, args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    memory: dict[str, Any] = {"last_nonzero": 1, "history": []}
    rows: list[dict[str, Any]] = []
    started = time.perf_counter()
    for step in range(task.stream.steps):
        prediction = control_prediction(model, task, step, memory, int(args.rolling_window))
        eval_sign = strict_sign(float(task.stream.evaluation_target[step]))
        pred_sign = strict_sign(float(prediction))
        rows.append(
            {
                "task": task.stream.name,
                "model": model,
                "model_family": "predictive_control",
                "backend": "numpy_rule",
                "seed": int(seed),
                "step": int(step),
                "event_type": task.event_type[step],
                "phase": task.phase[step],
                "trial_id": int(task.trial_id[step]),
                "context_sign": int(task.context_sign[step]),
                "cue_a_sign": int(task.cue_a_sign[step]),
                "cue_b_sign": int(task.cue_b_sign[step]),
                "sensory_return_1m": float(task.stream.sensory[step]),
                "target_return_1m": float(task.stream.current_target[step]),
                "target_signal_horizon": float(task.stream.evaluation_target[step]),
                "target_signal_sign": eval_sign,
                "target_signal_nonzero": bool(task.stream.evaluation_mask[step] and eval_sign != 0),
                "colony_prediction": float(prediction),
                "prediction_sign": pred_sign,
                "strict_direction_correct": bool(task.stream.evaluation_mask[step] and pred_sign != 0 and pred_sign == eval_sign),
                "feedback_due_step": int(task.stream.feedback_due_step[step]),
                "predictive_signal": float(task.predictive_signal[step]),
                "wrong_horizon_signal": float(task.wrong_horizon_signal[step]),
                "shuffled_target_signal": float(task.shuffled_target_signal[step]),
            }
        )
    summary = summarize_rows(rows)
    summary.update(
        {
            "task": task.stream.name,
            "model": model,
            "model_family": "predictive_control",
            "seed": int(seed),
            "steps": task.stream.steps,
            "runtime_seconds": time.perf_counter() - started,
            "task_metadata": task.stream.metadata,
            "task_pressure": task_pressure_summary(task),
        }
    )
    return rows, summary


def run_external_model(task: PredictiveTask, model: str, *, seed: int, args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    feature_builder = FeatureBuilder(history=args.feature_history, amplitude=args.amplitude)
    learner_cls = LEARNER_FACTORIES[model]
    learner = learner_cls(seed=seed, feature_size=feature_builder.size, args=args)
    pending: dict[int, list[tuple[Any, int]]] = {}
    rows: list[dict[str, Any]] = []
    started = time.perf_counter()
    for step in range(task.stream.steps):
        x = feature_builder.step(float(task.stream.sensory[step]))
        prediction, update_state = learner.step(x)
        eval_sign = strict_sign(float(task.stream.evaluation_target[step]))
        pred_sign = strict_sign(float(prediction))
        if bool(task.stream.evaluation_mask[step]) and eval_sign != 0:
            due = int(task.stream.feedback_due_step[step])
            if due >= step and due < task.stream.steps:
                pending.setdefault(due, []).append((update_state, eval_sign))
        rows.append(
            {
                "task": task.stream.name,
                "model": model,
                "model_family": learner.family,
                "backend": "numpy_online",
                "seed": int(seed),
                "step": int(step),
                "event_type": task.event_type[step],
                "phase": task.phase[step],
                "trial_id": int(task.trial_id[step]),
                "context_sign": int(task.context_sign[step]),
                "cue_a_sign": int(task.cue_a_sign[step]),
                "cue_b_sign": int(task.cue_b_sign[step]),
                "sensory_return_1m": float(task.stream.sensory[step]),
                "target_return_1m": float(task.stream.current_target[step]),
                "target_signal_horizon": float(task.stream.evaluation_target[step]),
                "target_signal_sign": eval_sign,
                "target_signal_nonzero": bool(task.stream.evaluation_mask[step] and eval_sign != 0),
                "colony_prediction": float(prediction),
                "prediction_sign": pred_sign,
                "strict_direction_correct": bool(task.stream.evaluation_mask[step] and pred_sign != 0 and pred_sign == eval_sign),
                "feedback_due_step": int(task.stream.feedback_due_step[step]),
                "predictive_signal": float(task.predictive_signal[step]),
            }
        )
        for state, label in pending.pop(step, []):
            learner.update(state, label)
    summary = summarize_rows(rows)
    summary.update(
        {
            "task": task.stream.name,
            "model": model,
            "model_family": learner.family,
            "seed": int(seed),
            "steps": task.stream.steps,
            "runtime_seconds": time.perf_counter() - started,
            "task_metadata": task.stream.metadata,
            "task_pressure": task_pressure_summary(task),
            "diagnostics": learner.diagnostics(),
        }
    )
    return rows, summary


def leakage_summary(rows_by_cell_seed: dict[tuple[str, str, int], list[dict[str, Any]]]) -> dict[str, Any]:
    violations: list[dict[str, Any]] = []
    checked = 0
    for (task, model, seed), rows in rows_by_cell_seed.items():
        for row in rows:
            if not bool(row.get("target_signal_nonzero", False)):
                continue
            checked += 1
            step = int(row.get("step", 0))
            due = int(row.get("feedback_due_step", -1))
            if due < step or due < 0:
                violations.append({"task": task, "model": model, "seed": seed, "step": step, "due": due})
    return {"checked_feedback_rows": checked, "feedback_due_violations": len(violations), "example_violations": violations[:10]}


def aggregate_runs(task: PredictiveTask, model: str, summaries: list[dict[str, Any]]) -> dict[str, Any]:
    keys = [
        "all_accuracy",
        "tail_accuracy",
        "early_accuracy",
        "accuracy_improvement",
        "prediction_target_corr",
        "tail_prediction_target_corr",
        "runtime_seconds",
        "evaluation_count",
        "mean_abs_prediction",
        "max_abs_prediction",
    ]
    aggregate = {
        "task": task.stream.name,
        "display_name": task.stream.display_name,
        "model": model,
        "model_family": summaries[0].get("model_family") if summaries else None,
        "runs": len(summaries),
        "seeds": [s.get("seed") for s in summaries],
        "steps": task.stream.steps,
        "task_pressure": task_pressure_summary(task),
        "task_metadata": task.stream.metadata,
    }
    for key in keys:
        vals = [s.get(key) for s in summaries]
        aggregate[f"{key}_mean"] = mean(vals)
        aggregate[f"{key}_std"] = stdev(vals)
        aggregate[f"{key}_min"] = min_value(vals)
        valid = [float(v) for v in vals if v is not None]
        aggregate[f"{key}_max"] = max(valid) if valid else None
    return aggregate


def build_comparisons(aggregates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    by_task_model = {(row["task"], row["model"]): row for row in aggregates}
    for task in sorted({row["task"] for row in aggregates}):
        current = by_task_model.get((task, "current_reflex"), {})
        sign = by_task_model.get((task, "sign_persistence_control"), {})
        majority = by_task_model.get((task, "rolling_majority"), {})
        predictive = by_task_model.get((task, "predictive_memory"), {})
        wrong = by_task_model.get((task, "wrong_horizon_control"), {})
        shuffled = by_task_model.get((task, "shuffled_target_control"), {})
        standard = [row for row in aggregates if row["task"] == task and row["model"] not in CONTROL_MODELS]
        best_standard = max(standard, key=lambda row: float(row.get("tail_accuracy_mean") or 0.0), default={})
        best_reflex = max(
            [current, sign, majority],
            key=lambda row: float(row.get("all_accuracy_mean") or 0.0),
            default={},
        )
        worst_sham = max(
            [wrong, shuffled],
            key=lambda row: float(row.get("all_accuracy_mean") or 0.0),
            default={},
        )
        pressure = predictive.get("task_pressure") or {}
        rows.append(
            {
                "task": task,
                "current_reflex_accuracy": current.get("all_accuracy_mean"),
                "sign_persistence_accuracy": sign.get("all_accuracy_mean"),
                "rolling_majority_accuracy": majority.get("all_accuracy_mean"),
                "predictive_memory_accuracy": predictive.get("all_accuracy_mean"),
                "wrong_horizon_accuracy": wrong.get("all_accuracy_mean"),
                "shuffled_target_accuracy": shuffled.get("all_accuracy_mean"),
                "best_standard_model": best_standard.get("model"),
                "best_standard_accuracy": best_standard.get("all_accuracy_mean"),
                "best_reflex_model": best_reflex.get("model"),
                "best_reflex_accuracy": best_reflex.get("all_accuracy_mean"),
                "best_sham_model": worst_sham.get("model"),
                "best_sham_accuracy": worst_sham.get("all_accuracy_mean"),
                "predictive_edge_vs_current": float(predictive.get("all_accuracy_mean") or 0.0) - float(current.get("all_accuracy_mean") or 0.0),
                "predictive_edge_vs_sign": float(predictive.get("all_accuracy_mean") or 0.0) - float(sign.get("all_accuracy_mean") or 0.0),
                "predictive_edge_vs_best_reflex": float(predictive.get("all_accuracy_mean") or 0.0) - float(best_reflex.get("all_accuracy_mean") or 0.0),
                "predictive_edge_vs_best_sham": float(predictive.get("all_accuracy_mean") or 0.0) - float(worst_sham.get("all_accuracy_mean") or 0.0),
                "same_current_input_opposite_labels": bool(pressure.get("same_current_input_opposite_labels", False)),
                "same_last_sign_opposite_labels": bool(pressure.get("same_last_sign_opposite_labels", False)),
                "ambiguous_current_bins": pressure.get("ambiguous_current_bins"),
                "ambiguous_last_sign_bins": pressure.get("ambiguous_last_sign_bins"),
                "decision_count": pressure.get("decision_count"),
            }
        )
    return rows


def evaluate_tier(
    *,
    aggregates: list[dict[str, Any]],
    comparisons: list[dict[str, Any]],
    leakage: dict[str, Any],
    models: list[str],
    args: argparse.Namespace,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    tasks = [item.strip() for item in args.tasks.split(",") if item.strip()]
    if not tasks or tasks == ["all"]:
        tasks = [item.strip() for item in DEFAULT_TASKS.split(",")]
    seeds = seeds_from_args(args)
    expected_runs = len(tasks) * len(seeds) * (len(models) + len(CONTROL_MODELS))
    observed_runs = sum(int(row.get("runs", 0)) for row in aggregates)
    predictive_accs = [float(row.get("predictive_memory_accuracy") or 0.0) for row in comparisons]
    predictive_edges_current = [float(row.get("predictive_edge_vs_current") or 0.0) for row in comparisons]
    predictive_edges_sign = [float(row.get("predictive_edge_vs_sign") or 0.0) for row in comparisons]
    predictive_edges_reflex = [float(row.get("predictive_edge_vs_best_reflex") or 0.0) for row in comparisons]
    predictive_edges_sham = [float(row.get("predictive_edge_vs_best_sham") or 0.0) for row in comparisons]
    wrong_accs = [float(row.get("wrong_horizon_accuracy") or 0.0) for row in comparisons]
    shuffled_accs = [float(row.get("shuffled_target_accuracy") or 0.0) for row in comparisons]
    current_accs = [float(row.get("current_reflex_accuracy") or 0.0) for row in comparisons]
    sign_accs = [float(row.get("sign_persistence_accuracy") or 0.0) for row in comparisons]
    ambiguity_ok = all(
        bool(row.get("same_current_input_opposite_labels")) and bool(row.get("same_last_sign_opposite_labels"))
        for row in comparisons
    )
    base_criteria = [
        criterion("full task/model/seed matrix completed", observed_runs, "==", expected_runs, observed_runs == expected_runs),
        criterion("feedback timing has no leakage violations", leakage.get("feedback_due_violations"), "==", 0, int(leakage.get("feedback_due_violations", 0)) == 0),
        criterion("current and last-sign shortcuts are ambiguous", ambiguity_ok, "==", True, ambiguity_ok),
    ]
    science_criteria = [
        criterion(
            "current reflex does not solve predictive tasks",
            max(current_accs) if current_accs else None,
            "<=",
            args.max_reflex_accuracy,
            bool(current_accs) and max(current_accs) <= args.max_reflex_accuracy,
            "A predictive task cannot be solvable from the current sensory value alone.",
        ),
        criterion(
            "sign persistence does not solve predictive tasks",
            max(sign_accs) if sign_accs else None,
            "<=",
            args.max_sign_persistence_accuracy,
            bool(sign_accs) and max(sign_accs) <= args.max_sign_persistence_accuracy,
            "A predictive task cannot collapse to last nonzero sign memory.",
        ),
        criterion(
            "causal predictive memory solves tasks",
            min(predictive_accs) if predictive_accs else None,
            ">=",
            args.min_predictive_memory_accuracy,
            bool(predictive_accs) and min(predictive_accs) >= args.min_predictive_memory_accuracy,
            "Proves the streams are solvable when the necessary predictive state is available.",
        ),
        criterion(
            "predictive memory beats current reflex",
            min(predictive_edges_current) if predictive_edges_current else None,
            ">=",
            args.min_predictive_edge,
            bool(predictive_edges_current) and min(predictive_edges_current) >= args.min_predictive_edge,
        ),
        criterion(
            "predictive memory beats sign persistence",
            min(predictive_edges_sign) if predictive_edges_sign else None,
            ">=",
            args.min_predictive_edge,
            bool(predictive_edges_sign) and min(predictive_edges_sign) >= args.min_predictive_edge,
        ),
        criterion(
            "predictive memory beats best reflex shortcut",
            min(predictive_edges_reflex) if predictive_edges_reflex else None,
            ">=",
            args.min_predictive_edge,
            bool(predictive_edges_reflex) and min(predictive_edges_reflex) >= args.min_predictive_edge,
        ),
        criterion(
            "wrong/shuffled target controls fail",
            max(max(wrong_accs) if wrong_accs else 0.0, max(shuffled_accs) if shuffled_accs else 0.0),
            "<=",
            args.max_wrong_or_shuffled_accuracy,
            bool(wrong_accs and shuffled_accs)
            and max(max(wrong_accs), max(shuffled_accs)) <= args.max_wrong_or_shuffled_accuracy,
            "Prediction must depend on the correct binding/horizon rather than target leakage or generic rehearsal.",
        ),
        criterion(
            "predictive memory beats best wrong/shuffled sham",
            min(predictive_edges_sham) if predictive_edges_sham else None,
            ">=",
            args.min_predictive_edge_vs_sham,
            bool(predictive_edges_sham) and min(predictive_edges_sham) >= args.min_predictive_edge_vs_sham,
        ),
    ]
    criteria = base_criteria if args.smoke else base_criteria + science_criteria
    summary = {
        "expected_runs": expected_runs,
        "observed_runs": observed_runs,
        "tasks": tasks,
        "seeds": seeds,
        "models": models,
        "controls": list(CONTROL_MODELS),
        "steps": args.steps,
        "smoke": bool(args.smoke),
        "leakage": leakage,
        "claim_boundary": "Task-validation evidence only; it proves predictive pressure, not CRA predictive coding or world modeling.",
    }
    return criteria, summary


def aggregate_csv_rows(aggregates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fields = [
        "task",
        "model",
        "model_family",
        "runs",
        "steps",
        "tail_accuracy_mean",
        "tail_accuracy_std",
        "all_accuracy_mean",
        "prediction_target_corr_mean",
        "tail_prediction_target_corr_mean",
        "runtime_seconds_mean",
        "evaluation_count_mean",
    ]
    return [{field: row.get(field) for field in fields} for row in aggregates]


def plot_task_pressure(comparisons: list[dict[str, Any]], path: Path) -> None:
    if plt is None or not comparisons:
        return
    tasks = [row["task"].replace("_", "\n") for row in comparisons]
    current = [float(row.get("current_reflex_accuracy") or 0.0) for row in comparisons]
    sign = [float(row.get("sign_persistence_accuracy") or 0.0) for row in comparisons]
    predictive = [float(row.get("predictive_memory_accuracy") or 0.0) for row in comparisons]
    wrong = [float(row.get("wrong_horizon_accuracy") or 0.0) for row in comparisons]
    x = np.arange(len(tasks))
    width = 0.2
    fig, ax = plt.subplots(figsize=(13, 5))
    ax.bar(x - 1.5 * width, current, width, label="current reflex", color="#a61e4d")
    ax.bar(x - 0.5 * width, sign, width, label="sign persistence", color="#b7791f")
    ax.bar(x + 0.5 * width, predictive, width, label="predictive memory", color="#2f855a")
    ax.bar(x + 1.5 * width, wrong, width, label="wrong horizon", color="#718096")
    ax.set_title("Tier 5.12a Predictive Task-Pressure Validation")
    ax.set_xticks(x)
    ax.set_xticklabels(tasks)
    ax.set_ylim(0.0, 1.05)
    ax.set_ylabel("decision accuracy")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fairness_contract(args: argparse.Namespace, models: list[str]) -> dict[str, Any]:
    return {
        "tier": TIER,
        "purpose": "validate predictive task pressure before testing any CRA predictive/world-model mechanism",
        "selected_external_baselines": models,
        "predictive_controls": list(CONTROL_MODELS),
        "fairness_rules": [
            "same sensory stream, target stream, evaluation mask, and feedback_due_step arrays per seed",
            "standard baselines see only the sensory stream and configured feature history",
            "predictive_memory is a task-validation control, not a CRA mechanism or competitor",
            "wrong_horizon_control and shuffled_target_control must fail before the task is accepted",
            "feedback_due_step must be greater than or equal to prediction step",
            "passing Tier 5.12a authorizes Tier 5.12b predictive mechanism testing only",
        ],
        "tasks": args.tasks,
        "steps": args.steps,
        "seeds": seeds_from_args(args),
        "feature_history": args.feature_history,
        "predictive_horizon": args.predictive_horizon,
    }


def run_tier(args: argparse.Namespace, output_dir: Path) -> dict[str, Any]:
    models = [model for model in parse_models(args.models) if model != "cra"]
    summaries_by_cell: dict[tuple[str, str], list[dict[str, Any]]] = {}
    rows_by_cell_seed: dict[tuple[str, str, int], list[dict[str, Any]]] = {}
    task_by_name: dict[str, PredictiveTask] = {}
    artifacts: dict[str, str] = {}
    started = time.perf_counter()
    for seed in seeds_from_args(args):
        for task in build_tasks(args, seed=args.task_seed + seed):
            task_by_name[task.stream.name] = task
            for model in [*models, *CONTROL_MODELS]:
                print(f"[tier5.12a] task={task.stream.name} model={model} seed={seed}", flush=True)
                if model in CONTROL_MODELS:
                    rows, summary = run_control_model(task, model, seed=seed, args=args)
                else:
                    rows, summary = run_external_model(task, model, seed=seed, args=args)
                csv_path = output_dir / f"{task.stream.name}_{model}_seed{seed}_timeseries.csv"
                write_csv(csv_path, rows)
                artifacts[f"{task.stream.name}_{model}_seed{seed}_timeseries_csv"] = str(csv_path)
                summaries_by_cell.setdefault((task.stream.name, model), []).append(summary)
                rows_by_cell_seed[(task.stream.name, model, seed)] = rows
    aggregates = [
        aggregate_runs(task_by_name[task_name], model, summaries)
        for (task_name, model), summaries in sorted(summaries_by_cell.items())
    ]
    comparisons = build_comparisons(aggregates)
    leakage = leakage_summary(rows_by_cell_seed)
    criteria, tier_summary = evaluate_tier(
        aggregates=aggregates,
        comparisons=comparisons,
        leakage=leakage,
        models=models,
        args=args,
    )
    status, failure_reason = pass_fail(criteria)
    summary_csv = output_dir / "tier5_12a_summary.csv"
    comparisons_csv = output_dir / "tier5_12a_comparisons.csv"
    fairness_json = output_dir / "tier5_12a_fairness_contract.json"
    plot_path = output_dir / "tier5_12a_task_pressure.png"
    write_csv(summary_csv, aggregate_csv_rows(aggregates))
    write_csv(comparisons_csv, comparisons)
    write_json(fairness_json, fairness_contract(args, models))
    plot_task_pressure(comparisons, plot_path)
    result = TestResult(
        name=TIER,
        status=status,
        summary={
            "tier_summary": tier_summary,
            "aggregates": aggregates,
            "comparisons": comparisons,
            "runtime_seconds": time.perf_counter() - started,
        },
        criteria=criteria,
        artifacts={
            **artifacts,
            "summary_csv": str(summary_csv),
            "comparisons_csv": str(comparisons_csv),
            "fairness_contract_json": str(fairness_json),
            "task_pressure_png": str(plot_path),
        },
        failure_reason=failure_reason,
    )
    return result.to_dict()


def write_report(path: Path, result: dict[str, Any], args: argparse.Namespace, output_dir: Path) -> None:
    overall = "PASS" if result["status"] == "pass" else "FAIL"
    comparisons = result["summary"]["comparisons"]
    aggregates = result["summary"]["aggregates"]
    lines = [
        "# Tier 5.12a Predictive Task-Pressure Validation Findings",
        "",
        f"- Generated: `{utc_now()}`",
        f"- Status: **{overall}**",
        f"- Steps: `{args.steps}`",
        f"- Seeds: `{', '.join(str(seed) for seed in seeds_from_args(args))}`",
        f"- Tasks: `{args.tasks}`",
        f"- Selected standard baselines: `{args.models}`",
        f"- Smoke mode: `{args.smoke}`",
        f"- Output directory: `{output_dir}`",
        "",
        "Tier 5.12a validates predictive-pressure tasks before CRA predictive-coding/world-model mechanisms are tested.",
        "",
        "## Claim Boundary",
        "",
        "- This is task-validation evidence, not CRA predictive-coding evidence.",
        "- `predictive_memory` is an oracle-like control showing the task is solvable with the missing predictive state.",
        "- A pass authorizes Tier 5.12b predictive mechanism testing; it does not prove world modeling, language, planning, or hardware prediction.",
        "",
        "## Predictive Pressure Comparisons",
        "",
        "| Task | Current reflex acc | Sign persistence acc | Rolling majority acc | Predictive memory acc | Wrong horizon acc | Shuffled target acc | Best standard model | Best standard acc | Predictive edge vs best reflex | Predictive edge vs sham | Ambiguous current | Ambiguous last | Decisions |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- | --- | ---: |",
    ]
    for row in comparisons:
        lines.append(
            "| "
            f"{row['task']} | "
            f"{markdown_value(row.get('current_reflex_accuracy'))} | "
            f"{markdown_value(row.get('sign_persistence_accuracy'))} | "
            f"{markdown_value(row.get('rolling_majority_accuracy'))} | "
            f"{markdown_value(row.get('predictive_memory_accuracy'))} | "
            f"{markdown_value(row.get('wrong_horizon_accuracy'))} | "
            f"{markdown_value(row.get('shuffled_target_accuracy'))} | "
            f"`{row.get('best_standard_model')}` | "
            f"{markdown_value(row.get('best_standard_accuracy'))} | "
            f"{markdown_value(row.get('predictive_edge_vs_best_reflex'))} | "
            f"{markdown_value(row.get('predictive_edge_vs_best_sham'))} | "
            f"{row.get('same_current_input_opposite_labels')} | "
            f"{row.get('same_last_sign_opposite_labels')} | "
            f"{markdown_value(row.get('decision_count'))} |"
        )
    lines.extend(
        [
            "",
            "## Aggregate Matrix",
            "",
            "| Task | Model | Family | Tail acc | All acc | Corr | Runtime s |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in sorted(aggregates, key=lambda item: (item["task"], item["model"])):
        lines.append(
            "| "
            f"{row['task']} | `{row['model']}` | {row.get('model_family')} | "
            f"{markdown_value(row.get('tail_accuracy_mean'))} | "
            f"{markdown_value(row.get('all_accuracy_mean'))} | "
            f"{markdown_value(row.get('prediction_target_corr_mean'))} | "
            f"{markdown_value(row.get('runtime_seconds_mean'))} |"
        )
    lines.extend(["", "## Criteria", "", "| Criterion | Value | Rule | Pass | Note |", "| --- | --- | --- | --- | --- |"])
    for item in result["criteria"]:
        lines.append(
            "| "
            f"{item['name']} | "
            f"{markdown_value(item['value'])} | "
            f"{item['operator']} {markdown_value(item['threshold'])} | "
            f"{'yes' if item['passed'] else 'no'} | "
            f"{item.get('note', '')} |"
        )
    if result["failure_reason"]:
        lines.extend(["", f"Failure: {result['failure_reason']}"])
    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            "- `tier5_12a_results.json`: machine-readable manifest.",
            "- `tier5_12a_report.md`: human findings and claim boundary.",
            "- `tier5_12a_summary.csv`: aggregate task/model metrics.",
            "- `tier5_12a_comparisons.csv`: predictive-pressure comparison table.",
            "- `tier5_12a_fairness_contract.json`: predeclared comparison/leakage rules.",
            "- `tier5_12a_task_pressure.png`: predictive-pressure plot.",
            "- `*_timeseries.csv`: per-task/per-model/per-seed traces.",
            "",
            "![task_pressure](tier5_12a_task_pressure.png)",
            "",
        ]
    )
    if MATPLOTLIB_ERROR:
        lines.append(f"Plotting unavailable: `{MATPLOTLIB_ERROR}`")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_latest(output_dir: Path, report_path: Path, manifest_path: Path, summary_csv: Path, status: str) -> None:
    latest_path = ROOT / "controlled_test_output" / "tier5_12a_latest_manifest.json"
    payload = {
        "generated_at_utc": utc_now(),
        "tier": TIER,
        "status": status,
        "output_dir": str(output_dir),
        "manifest": str(manifest_path),
        "report": str(report_path),
        "summary_csv": str(summary_csv),
        "canonical": False,
        "claim": "Latest Tier 5.12a predictive task-pressure validation; passing authorizes mechanism testing only.",
    }
    write_json(latest_path, payload)


def build_parser() -> argparse.ArgumentParser:
    parser = build_tier5_1_parser()
    parser.description = "Run Tier 5.12a predictive task-pressure validation."
    parser.set_defaults(
        backend="mock",
        tasks=DEFAULT_TASKS,
        steps=720,
        seed_count=3,
        models=DEFAULT_MODELS,
        feature_history=6,
    )
    parser.add_argument("--predictive-horizon", type=int, default=8)
    parser.add_argument("--predictive-period", type=int, default=8)
    parser.add_argument("--predictive-regime-block", type=int, default=96)
    parser.add_argument("--masked-period", type=int, default=12)
    parser.add_argument("--masked-gap", type=int, default=6)
    parser.add_argument("--event-period", type=int, default=10)
    parser.add_argument("--anomaly-period", type=int, default=12)
    parser.add_argument("--rolling-window", type=int, default=5)
    parser.add_argument("--max-reflex-accuracy", type=float, default=0.70)
    parser.add_argument("--max-sign-persistence-accuracy", type=float, default=0.75)
    parser.add_argument("--min-predictive-memory-accuracy", type=float, default=0.95)
    parser.add_argument("--min-predictive-edge", type=float, default=0.20)
    parser.add_argument("--min-predictive-edge-vs-sham", type=float, default=0.20)
    parser.add_argument("--max-wrong-or-shuffled-accuracy", type=float, default=0.75)
    parser.add_argument("--smoke", action="store_true", help="Run harness integrity gates only; scientific predictive-pressure gates are skipped.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = args.output_dir or (ROOT / "controlled_test_output" / f"tier5_12a_{timestamp}")
    output_dir.mkdir(parents=True, exist_ok=True)
    result = run_tier(args, output_dir)
    manifest_path = output_dir / "tier5_12a_results.json"
    report_path = output_dir / "tier5_12a_report.md"
    summary_csv = output_dir / "tier5_12a_summary.csv"
    comparisons_csv = output_dir / "tier5_12a_comparisons.csv"
    fairness_json = output_dir / "tier5_12a_fairness_contract.json"
    manifest = {
        "tier": TIER,
        "generated_at_utc": utc_now(),
        "output_dir": str(output_dir),
        "command": " ".join(sys.argv),
        "status": result["status"],
        "result": result,
        "summary": {
            **result["summary"]["tier_summary"],
            "runtime_seconds": result["summary"]["runtime_seconds"],
            "comparisons": result["summary"]["comparisons"],
        },
        "artifacts": {
            "summary_csv": str(summary_csv),
            "comparisons_csv": str(comparisons_csv),
            "fairness_contract_json": str(fairness_json),
            "report_md": str(report_path),
            "task_pressure_png": str(output_dir / "tier5_12a_task_pressure.png"),
        },
    }
    write_json(manifest_path, json_safe(manifest))
    write_report(report_path, result, args, output_dir)
    write_latest(output_dir, report_path, manifest_path, summary_csv, result["status"])
    print(
        json.dumps(
            {
                "status": result["status"],
                "output_dir": str(output_dir),
                "manifest": str(manifest_path),
                "report": str(report_path),
                "summary_csv": str(summary_csv),
                "comparisons_csv": str(comparisons_csv),
                "fairness_contract_json": str(fairness_json),
                "failure_reason": result["failure_reason"],
            },
            indent=2,
        )
    )
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
