#!/usr/bin/env python3
"""Tier 5.10b memory-pressure task validation.

Tier 5.10 failed partly because the recurrence tasks were still solvable by a
simple sign-persistence reflex. Tier 5.10b does not test a new CRA mechanism.
It validates repaired task streams: the same current cue must require different
actions depending on remembered context, context-aware controls must solve the
tasks, and reflex/shuffled/reset controls must fail.
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


TIER = "Tier 5.10b - Memory-Pressure Task Validation"
DEFAULT_TASKS = "delayed_context_cue,distractor_gap_context,hidden_context_recurrence"
DEFAULT_MODELS = "sign_persistence,online_perceptron,online_logistic_regression,echo_state_network,small_gru,stdp_only_snn"
CONTROL_MODELS = (
    "oracle_context",
    "stream_context_memory",
    "shuffled_context",
    "memory_reset",
    "wrong_context",
)
EPS = 1e-12


@dataclass(frozen=True)
class TrialRecord:
    trial_id: int
    context_step: int
    decision_step: int
    context_sign: int
    decision_cue_sign: int
    label_sign: int
    phase: str


@dataclass(frozen=True)
class MemoryTask:
    stream: TaskStream
    context_sign: np.ndarray
    decision_cue_sign: np.ndarray
    trial_id: np.ndarray
    event_type: list[str]
    phase: list[str]
    trials: list[TrialRecord]


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


def make_empty_task_arrays(steps: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[str], list[str]]:
    sensory = np.zeros(steps, dtype=float)
    current_target = np.zeros(steps, dtype=float)
    evaluation_target = np.zeros(steps, dtype=float)
    evaluation_mask = np.zeros(steps, dtype=bool)
    feedback_due = np.full(steps, -1, dtype=int)
    context_sign = np.zeros(steps, dtype=int)
    decision_cue_sign = np.zeros(steps, dtype=int)
    trial_id = np.full(steps, -1, dtype=int)
    event_type = ["none" for _ in range(steps)]
    phase = ["none" for _ in range(steps)]
    return (
        sensory,
        current_target,
        evaluation_target,
        evaluation_mask,
        feedback_due,
        context_sign,
        decision_cue_sign,
        trial_id,
        event_type,
        phase,
    )


def fill_trial(
    *,
    sensory: np.ndarray,
    current_target: np.ndarray,
    evaluation_target: np.ndarray,
    evaluation_mask: np.ndarray,
    feedback_due: np.ndarray,
    context_by_step: np.ndarray,
    cue_by_step: np.ndarray,
    trial_by_step: np.ndarray,
    event_type: list[str],
    phase_by_step: list[str],
    trial_id: int,
    context_step: int,
    decision_step: int,
    context_sign: int,
    decision_cue_sign: int,
    amplitude: float,
    rng: np.random.Generator,
    phase: str,
    distractor_steps: list[int],
    distractor_scale: float,
) -> TrialRecord:
    label_sign = int(context_sign * decision_cue_sign)
    sensory[context_step] = 0.55 * amplitude * context_sign
    event_type[context_step] = "context"
    phase_by_step[context_step] = phase
    trial_by_step[context_step] = trial_id
    context_by_step[context_step] = context_sign
    for step in distractor_steps:
        if 0 <= step < decision_step and event_type[step] == "none":
            sensory[step] = distractor_scale * amplitude * int(rng.choice([-1, 1]))
            event_type[step] = "distractor"
            phase_by_step[step] = phase
            trial_by_step[step] = trial_id
            context_by_step[step] = context_sign
    sensory[decision_step] = amplitude * decision_cue_sign
    current_target[decision_step] = amplitude * label_sign
    evaluation_target[decision_step] = amplitude * label_sign
    evaluation_mask[decision_step] = True
    feedback_due[decision_step] = decision_step
    context_by_step[decision_step] = context_sign
    cue_by_step[decision_step] = decision_cue_sign
    trial_by_step[decision_step] = trial_id
    event_type[decision_step] = "decision"
    phase_by_step[decision_step] = phase
    return TrialRecord(
        trial_id=trial_id,
        context_step=context_step,
        decision_step=decision_step,
        context_sign=int(context_sign),
        decision_cue_sign=int(decision_cue_sign),
        label_sign=int(label_sign),
        phase=phase,
    )


def balanced_context_cue_pair(index: int) -> tuple[int, int]:
    cycle = ((1, 1), (1, -1), (-1, 1), (-1, -1))
    return cycle[index % len(cycle)]


def task_from_arrays(
    *,
    name: str,
    display_name: str,
    steps: int,
    sensory: np.ndarray,
    current_target: np.ndarray,
    evaluation_target: np.ndarray,
    evaluation_mask: np.ndarray,
    feedback_due: np.ndarray,
    context_sign: np.ndarray,
    decision_cue_sign: np.ndarray,
    trial_id: np.ndarray,
    event_type: list[str],
    phase: list[str],
    trials: list[TrialRecord],
    metadata: dict[str, Any],
) -> MemoryTask:
    switch_steps = sorted({record.context_step for record in trials if record.phase.endswith("_start")})
    stream = TaskStream(
        name=name,
        display_name=display_name,
        domain=name,
        steps=steps,
        sensory=sensory,
        current_target=current_target,
        evaluation_target=evaluation_target,
        evaluation_mask=evaluation_mask,
        feedback_due_step=feedback_due,
        switch_steps=switch_steps,
        metadata={
            **metadata,
            "task_kind": name,
            "trials": len(trials),
            "decision_events": int(np.sum(evaluation_mask)),
            "context_events": int(sum(1 for event in event_type if event == "context")),
            "trial_records": [record.__dict__ for record in trials],
        },
    )
    return MemoryTask(
        stream=stream,
        context_sign=context_sign,
        decision_cue_sign=decision_cue_sign,
        trial_id=trial_id,
        event_type=event_type,
        phase=phase,
        trials=trials,
    )


def delayed_context_cue_task(*, steps: int, amplitude: float, seed: int, args: argparse.Namespace) -> MemoryTask:
    rng = np.random.default_rng(seed + 51021)
    (
        sensory,
        current_target,
        evaluation_target,
        evaluation_mask,
        feedback_due,
        context_by_step,
        cue_by_step,
        trial_by_step,
        event_type,
        phase_by_step,
    ) = make_empty_task_arrays(steps)
    gap = int(args.context_gap)
    period = int(args.context_period)
    trials: list[TrialRecord] = []
    trial_id = 0
    for context_step in range(0, steps - gap - 1, period):
        decision_step = context_step + gap
        context_sign, cue_sign = balanced_context_cue_pair(trial_id)
        distractors = list(range(context_step + 1, decision_step))
        trials.append(
            fill_trial(
                sensory=sensory,
                current_target=current_target,
                evaluation_target=evaluation_target,
                evaluation_mask=evaluation_mask,
                feedback_due=feedback_due,
                context_by_step=context_by_step,
                cue_by_step=cue_by_step,
                trial_by_step=trial_by_step,
                event_type=event_type,
                phase_by_step=phase_by_step,
                trial_id=trial_id,
                context_step=context_step,
                decision_step=decision_step,
                context_sign=context_sign,
                decision_cue_sign=cue_sign,
                amplitude=amplitude,
                rng=rng,
                phase="independent_context",
                distractor_steps=distractors,
                distractor_scale=float(args.distractor_scale),
            )
        )
        trial_id += 1
    return task_from_arrays(
        name="delayed_context_cue",
        display_name="Delayed Context Cue",
        steps=steps,
        sensory=sensory,
        current_target=current_target,
        evaluation_target=evaluation_target,
        evaluation_mask=evaluation_mask,
        feedback_due=feedback_due,
        context_sign=context_by_step,
        decision_cue_sign=cue_by_step,
        trial_id=trial_by_step,
        event_type=event_type,
        phase=phase_by_step,
        trials=trials,
        metadata={"context_gap": gap, "context_period": period},
    )


def distractor_gap_context_task(*, steps: int, amplitude: float, seed: int, args: argparse.Namespace) -> MemoryTask:
    rng = np.random.default_rng(seed + 51022)
    (
        sensory,
        current_target,
        evaluation_target,
        evaluation_mask,
        feedback_due,
        context_by_step,
        cue_by_step,
        trial_by_step,
        event_type,
        phase_by_step,
    ) = make_empty_task_arrays(steps)
    gap = int(args.long_context_gap)
    period = int(args.long_context_period)
    trials: list[TrialRecord] = []
    trial_id = 0
    for context_step in range(0, steps - gap - 1, period):
        decision_step = context_step + gap
        context_sign, cue_sign = balanced_context_cue_pair(trial_id)
        distractors = [step for step in range(context_step + 1, decision_step) if rng.random() < args.distractor_density]
        trials.append(
            fill_trial(
                sensory=sensory,
                current_target=current_target,
                evaluation_target=evaluation_target,
                evaluation_mask=evaluation_mask,
                feedback_due=feedback_due,
                context_by_step=context_by_step,
                cue_by_step=cue_by_step,
                trial_by_step=trial_by_step,
                event_type=event_type,
                phase_by_step=phase_by_step,
                trial_id=trial_id,
                context_step=context_step,
                decision_step=decision_step,
                context_sign=context_sign,
                decision_cue_sign=cue_sign,
                amplitude=amplitude,
                rng=rng,
                phase="long_distractor_gap",
                distractor_steps=distractors,
                distractor_scale=float(args.distractor_scale),
            )
        )
        trial_id += 1
    return task_from_arrays(
        name="distractor_gap_context",
        display_name="Distractor Gap Context",
        steps=steps,
        sensory=sensory,
        current_target=current_target,
        evaluation_target=evaluation_target,
        evaluation_mask=evaluation_mask,
        feedback_due=feedback_due,
        context_sign=context_by_step,
        decision_cue_sign=cue_by_step,
        trial_id=trial_by_step,
        event_type=event_type,
        phase=phase_by_step,
        trials=trials,
        metadata={"context_gap": gap, "context_period": period, "distractor_density": args.distractor_density},
    )


def hidden_context_recurrence_task(*, steps: int, amplitude: float, seed: int, args: argparse.Namespace) -> MemoryTask:
    rng = np.random.default_rng(seed + 51023)
    (
        sensory,
        current_target,
        evaluation_target,
        evaluation_mask,
        feedback_due,
        context_by_step,
        cue_by_step,
        trial_by_step,
        event_type,
        phase_by_step,
    ) = make_empty_task_arrays(steps)
    phases = [
        ("A0_start", 1),
        ("B_start", -1),
        ("A_return_start", 1),
        ("B_return_start", -1),
    ]
    min_phase_len = int(args.recurrence_decision_gap) + 2 * int(args.recurrence_trial_gap) + 1
    phase_len = max(min_phase_len, min(int(args.recurrence_phase_len), max(1, steps // len(phases))))
    trial_gap = int(args.recurrence_trial_gap)
    decision_gap = int(args.recurrence_decision_gap)
    trials: list[TrialRecord] = []
    trial_id = 0
    for idx, (phase_name, context_sign) in enumerate(phases):
        phase_start = min(idx * phase_len, steps - 1)
        phase_end = steps if idx == len(phases) - 1 else min((idx + 1) * phase_len, steps)
        if phase_start + decision_gap >= steps:
            break
        # A single context marker starts each phase; decisions then continue
        # without explicit context labels.
        first_decision = phase_start + decision_gap
        for decision_step in range(first_decision, max(first_decision, phase_end - 1), trial_gap):
            if decision_step >= steps:
                break
            context_step = phase_start if decision_step == first_decision else max(phase_start, decision_step - decision_gap)
            cue_sign = 1 if trial_id % 2 == 0 else -1
            # Only the first trial of a phase receives an actual context marker;
            # later decisions must retain the phase context through distractors.
            actual_context_step = phase_start if decision_step == first_decision else decision_step - decision_gap
            if decision_step != first_decision:
                # Use a weak distractor marker instead of a real context cue.
                actual_context_step = max(phase_start, decision_step - decision_gap)
                event_type[actual_context_step] = "distractor"
                sensory[actual_context_step] = float(args.distractor_scale) * amplitude * int(rng.choice([-1, 1]))
            distractors = [step for step in range(actual_context_step + 1, decision_step) if rng.random() < args.distractor_density]
            record = fill_trial(
                sensory=sensory,
                current_target=current_target,
                evaluation_target=evaluation_target,
                evaluation_mask=evaluation_mask,
                feedback_due=feedback_due,
                context_by_step=context_by_step,
                cue_by_step=cue_by_step,
                trial_by_step=trial_by_step,
                event_type=event_type,
                phase_by_step=phase_by_step,
                trial_id=trial_id,
                context_step=phase_start if decision_step == first_decision else actual_context_step,
                decision_step=decision_step,
                context_sign=context_sign,
                decision_cue_sign=cue_sign,
                amplitude=amplitude,
                rng=rng,
                phase=phase_name,
                distractor_steps=distractors,
                distractor_scale=float(args.distractor_scale),
            )
            if decision_step != first_decision:
                # Remove the artificial repeated context cue created by
                # fill_trial. The ground-truth context remains in the row
                # arrays, but the sensory stream no longer tells baselines.
                sensory[record.context_step] = float(args.distractor_scale) * amplitude * int(rng.choice([-1, 1]))
                event_type[record.context_step] = "distractor"
            trials.append(record)
            trial_id += 1
    return task_from_arrays(
        name="hidden_context_recurrence",
        display_name="Hidden Context Recurrence",
        steps=steps,
        sensory=sensory,
        current_target=current_target,
        evaluation_target=evaluation_target,
        evaluation_mask=evaluation_mask,
        feedback_due=feedback_due,
        context_sign=context_by_step,
        decision_cue_sign=cue_by_step,
        trial_id=trial_by_step,
        event_type=event_type,
        phase=phase_by_step,
        trials=trials,
        metadata={
            "phases": [{"name": name, "context_sign": sign} for name, sign in phases],
            "phase_len": phase_len,
            "trial_gap": trial_gap,
            "decision_gap": decision_gap,
        },
    )


def build_tasks(args: argparse.Namespace, seed: int) -> list[MemoryTask]:
    factories = {
        "delayed_context_cue": delayed_context_cue_task,
        "distractor_gap_context": distractor_gap_context_task,
        "hidden_context_recurrence": hidden_context_recurrence_task,
    }
    names = [item.strip() for item in args.tasks.split(",") if item.strip()]
    if not names or names == ["all"]:
        names = list(factories)
    missing = [name for name in names if name not in factories]
    if missing:
        raise argparse.ArgumentTypeError(f"unknown Tier 5.10b tasks: {', '.join(missing)}")
    return [factories[name](steps=args.steps, amplitude=args.amplitude, seed=seed, args=args) for name in names]


def task_ambiguity_summary(task: MemoryTask) -> dict[str, Any]:
    decisions = [record for record in task.trials]
    by_cue: dict[int, set[int]] = {-1: set(), 1: set()}
    for record in decisions:
        by_cue[int(record.decision_cue_sign)].add(int(record.label_sign))
    ambiguous_cues = [cue for cue, labels in by_cue.items() if len(labels) > 1]
    contexts = [record.context_sign for record in decisions]
    labels = [record.label_sign for record in decisions]
    return {
        "decision_count": len(decisions),
        "ambiguous_current_cue_count": len(ambiguous_cues),
        "context_balance": None if not contexts else float(np.mean([1 if value > 0 else 0 for value in contexts])),
        "label_balance": None if not labels else float(np.mean([1 if value > 0 else 0 for value in labels])),
        "same_current_input_opposite_labels": len(ambiguous_cues) >= 2,
    }


def prediction_for_control(model: str, task: MemoryTask, step: int, memory: dict[str, Any], shuffled_context_by_trial: dict[int, int]) -> float:
    event = task.event_type[step]
    sensory_sign = strict_sign(float(task.stream.sensory[step]))
    if event == "context":
        memory["context"] = int(task.context_sign[step]) or sensory_sign or 1
        return 0.0
    if event == "decision":
        cue = int(task.decision_cue_sign[step]) or sensory_sign or 1
        context = int(task.context_sign[step]) or int(memory.get("context", 1))
        trial_id = int(task.trial_id[step])
        if model == "oracle_context":
            return float(context * cue)
        if model == "stream_context_memory":
            return float(int(memory.get("context", context)) * cue)
        if model == "shuffled_context":
            return float(int(shuffled_context_by_trial.get(trial_id, 1)) * cue)
        if model == "memory_reset":
            return float(cue)
        if model == "wrong_context":
            return float(-context * cue)
    return 0.0


def run_control_model(task: MemoryTask, model: str, *, seed: int, args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rng = np.random.default_rng(seed + 8100)
    trial_contexts = [record.context_sign for record in task.trials]
    shuffled = list(trial_contexts)
    rng.shuffle(shuffled)
    shuffled_context_by_trial = {record.trial_id: int(shuffled[idx]) for idx, record in enumerate(task.trials)}
    memory: dict[str, Any] = {"context": 1}
    rows: list[dict[str, Any]] = []
    started = time.perf_counter()
    for step in range(task.stream.steps):
        prediction = prediction_for_control(model, task, step, memory, shuffled_context_by_trial)
        eval_sign = strict_sign(float(task.stream.evaluation_target[step]))
        pred_sign = strict_sign(prediction)
        rows.append(
            {
                "task": task.stream.name,
                "model": model,
                "model_family": "context_control",
                "backend": "numpy_rule",
                "seed": int(seed),
                "step": int(step),
                "event_type": task.event_type[step],
                "phase": task.phase[step],
                "trial_id": int(task.trial_id[step]),
                "context_sign": int(task.context_sign[step]),
                "decision_cue_sign": int(task.decision_cue_sign[step]),
                "sensory_return_1m": float(task.stream.sensory[step]),
                "target_return_1m": float(task.stream.current_target[step]),
                "target_signal_horizon": float(task.stream.evaluation_target[step]),
                "target_signal_sign": eval_sign,
                "target_signal_nonzero": bool(task.stream.evaluation_mask[step] and eval_sign != 0),
                "colony_prediction": float(prediction),
                "prediction_sign": pred_sign,
                "strict_direction_correct": bool(task.stream.evaluation_mask[step] and pred_sign != 0 and pred_sign == eval_sign),
                "feedback_due_step": int(task.stream.feedback_due_step[step]),
            }
        )
        if task.event_type[step] == "decision" and model == "memory_reset":
            memory["context"] = 1
    summary = summarize_rows(rows)
    summary.update(
        {
            "task": task.stream.name,
            "model": model,
            "model_family": "context_control",
            "seed": int(seed),
            "steps": task.stream.steps,
            "runtime_seconds": time.perf_counter() - started,
            "task_metadata": task.stream.metadata,
            "ambiguity": task_ambiguity_summary(task),
        }
    )
    return rows, summary


def run_external_model(task: MemoryTask, model: str, *, seed: int, args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
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
                "decision_cue_sign": int(task.decision_cue_sign[step]),
                "sensory_return_1m": float(task.stream.sensory[step]),
                "target_return_1m": float(task.stream.current_target[step]),
                "target_signal_horizon": float(task.stream.evaluation_target[step]),
                "target_signal_sign": eval_sign,
                "target_signal_nonzero": bool(task.stream.evaluation_mask[step] and eval_sign != 0),
                "colony_prediction": float(prediction),
                "prediction_sign": pred_sign,
                "strict_direction_correct": bool(task.stream.evaluation_mask[step] and pred_sign != 0 and pred_sign == eval_sign),
                "feedback_due_step": int(task.stream.feedback_due_step[step]),
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
            "ambiguity": task_ambiguity_summary(task),
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


def aggregate_runs(task: MemoryTask, model: str, summaries: list[dict[str, Any]]) -> dict[str, Any]:
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
        "ambiguity": task_ambiguity_summary(task),
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
        sign = by_task_model.get((task, "sign_persistence"), {})
        oracle = by_task_model.get((task, "oracle_context"), {})
        memory = by_task_model.get((task, "stream_context_memory"), {})
        shuffled = by_task_model.get((task, "shuffled_context"), {})
        reset = by_task_model.get((task, "memory_reset"), {})
        wrong = by_task_model.get((task, "wrong_context"), {})
        standard = [
            row
            for row in aggregates
            if row["task"] == task
            and row["model"] not in CONTROL_MODELS
        ]
        best_standard = max(standard, key=lambda row: float(row.get("tail_accuracy_mean") or 0.0), default={})
        control_fail_best = max(
            [shuffled, reset, wrong],
            key=lambda row: float(row.get("tail_accuracy_mean") or 0.0),
            default={},
        )
        rows.append(
            {
                "task": task,
                "sign_persistence_accuracy": sign.get("all_accuracy_mean"),
                "oracle_context_accuracy": oracle.get("all_accuracy_mean"),
                "stream_context_memory_accuracy": memory.get("all_accuracy_mean"),
                "shuffled_context_accuracy": shuffled.get("all_accuracy_mean"),
                "memory_reset_accuracy": reset.get("all_accuracy_mean"),
                "wrong_context_accuracy": wrong.get("all_accuracy_mean"),
                "best_standard_model": best_standard.get("model"),
                "best_standard_accuracy": best_standard.get("all_accuracy_mean"),
                "best_failure_control_accuracy": control_fail_best.get("all_accuracy_mean"),
                "oracle_edge_vs_sign": float(oracle.get("all_accuracy_mean") or 0.0) - float(sign.get("all_accuracy_mean") or 0.0),
                "memory_edge_vs_sign": float(memory.get("all_accuracy_mean") or 0.0) - float(sign.get("all_accuracy_mean") or 0.0),
                "memory_edge_vs_best_failure_control": float(memory.get("all_accuracy_mean") or 0.0) - float(control_fail_best.get("all_accuracy_mean") or 0.0),
                "best_standard_edge_vs_sign": float(best_standard.get("all_accuracy_mean") or 0.0) - float(sign.get("all_accuracy_mean") or 0.0),
                "same_current_input_opposite_labels": bool((oracle.get("ambiguity") or {}).get("same_current_input_opposite_labels", False)),
                "ambiguous_current_cue_count": (oracle.get("ambiguity") or {}).get("ambiguous_current_cue_count"),
                "decision_count": (oracle.get("ambiguity") or {}).get("decision_count"),
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
    sign_accs = [float(row.get("sign_persistence_accuracy") or 0.0) for row in comparisons]
    oracle_accs = [float(row.get("oracle_context_accuracy") or 0.0) for row in comparisons]
    memory_accs = [float(row.get("stream_context_memory_accuracy") or 0.0) for row in comparisons]
    memory_edges = [float(row.get("memory_edge_vs_sign") or 0.0) for row in comparisons]
    failure_edges = [float(row.get("memory_edge_vs_best_failure_control") or 0.0) for row in comparisons]
    best_standard_accs = [float(row.get("best_standard_accuracy") or 0.0) for row in comparisons]
    ambiguity_ok = all(bool(row.get("same_current_input_opposite_labels")) for row in comparisons)
    base_criteria = [
        criterion("full task/model/seed matrix completed", observed_runs, "==", expected_runs, observed_runs == expected_runs),
        criterion("feedback timing has no leakage violations", leakage.get("feedback_due_violations"), "==", 0, int(leakage.get("feedback_due_violations", 0)) == 0),
        criterion("same current input supports opposite labels", ambiguity_ok, "==", True, ambiguity_ok),
    ]
    science_criteria = [
        criterion(
            "sign_persistence no longer dominates",
            max(sign_accs) if sign_accs else None,
            "<=",
            args.max_sign_persistence_tail,
            bool(sign_accs) and max(sign_accs) <= args.max_sign_persistence_tail,
            "A memory-pressure task cannot be solved by the reflex baseline.",
        ),
        criterion(
            "oracle context solves the task",
            min(oracle_accs) if oracle_accs else None,
            ">=",
            args.min_oracle_tail,
            bool(oracle_accs) and min(oracle_accs) >= args.min_oracle_tail,
            "Proves the task is solvable with the missing context state.",
        ),
        criterion(
            "stream context memory solves the task",
            min(memory_accs) if memory_accs else None,
            ">=",
            args.min_context_memory_tail,
            bool(memory_accs) and min(memory_accs) >= args.min_context_memory_tail,
            "Proves a simple memory of prior context is sufficient.",
        ),
        criterion(
            "context memory beats sign persistence",
            min(memory_edges) if memory_edges else None,
            ">=",
            args.min_memory_edge_vs_sign,
            bool(memory_edges) and min(memory_edges) >= args.min_memory_edge_vs_sign,
            "The task must reward remembered context over current-signal reflexes.",
        ),
        criterion(
            "shuffled/reset/wrong memory controls fail",
            min(failure_edges) if failure_edges else None,
            ">=",
            args.min_memory_edge_vs_failure_control,
            bool(failure_edges) and min(failure_edges) >= args.min_memory_edge_vs_failure_control,
            "The benefit must depend on correct memory, not generic capacity.",
        ),
        criterion(
            "standard baselines do not solve every repaired task",
            max(best_standard_accs) if best_standard_accs else None,
            "<=",
            args.max_best_standard_accuracy,
            bool(best_standard_accs) and max(best_standard_accs) <= args.max_best_standard_accuracy,
            "The task may remain learnable by stronger baselines, but not trivially solved before CRA testing.",
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
        "claim_boundary": "Task-validation evidence only; it proves memory pressure, not CRA memory performance.",
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
    sign = [float(row.get("sign_persistence_accuracy") or 0.0) for row in comparisons]
    oracle = [float(row.get("oracle_context_accuracy") or 0.0) for row in comparisons]
    memory = [float(row.get("stream_context_memory_accuracy") or 0.0) for row in comparisons]
    x = np.arange(len(tasks))
    width = 0.25
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.bar(x - width, sign, width, label="sign persistence", color="#b7791f")
    ax.bar(x, memory, width, label="stream context memory", color="#2f855a")
    ax.bar(x + width, oracle, width, label="oracle context", color="#1f6feb")
    ax.set_title("Tier 5.10b Memory-Pressure Task Validation")
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
        "purpose": "validate memory-pressure tasks before testing CRA memory mechanisms",
        "selected_external_baselines": models,
        "context_controls": list(CONTROL_MODELS),
        "fairness_rules": [
            "same sensory stream, target stream, evaluation mask, and feedback_due_step arrays per seed",
            "standard baselines see only the sensory stream and their configured feature history",
            "oracle_context and stream_context_memory are task-validation controls, not CRA competitors",
            "shuffled_context, memory_reset, and wrong_context must lose before the task is accepted",
            "feedback_due_step must be greater than or equal to prediction step",
            "passing Tier 5.10b authorizes Tier 5.10c mechanism testing only, not a CRA memory claim",
        ],
        "tasks": args.tasks,
        "steps": args.steps,
        "seeds": seeds_from_args(args),
        "context_gap": args.context_gap,
        "long_context_gap": args.long_context_gap,
        "feature_history": args.feature_history,
    }


def run_tier(args: argparse.Namespace, output_dir: Path) -> dict[str, Any]:
    models = parse_models(args.models)
    models = [model for model in models if model != "cra"]
    summaries_by_cell: dict[tuple[str, str], list[dict[str, Any]]] = {}
    rows_by_cell_seed: dict[tuple[str, str, int], list[dict[str, Any]]] = {}
    task_by_name: dict[str, MemoryTask] = {}
    artifacts: dict[str, str] = {}
    started = time.perf_counter()
    for seed in seeds_from_args(args):
        tasks = build_tasks(args, seed=args.task_seed + seed)
        for task in tasks:
            task_by_name[task.stream.name] = task
            for model in [*models, *CONTROL_MODELS]:
                print(f"[tier5.10b] task={task.stream.name} model={model} seed={seed}", flush=True)
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
    summary_csv = output_dir / "tier5_10b_summary.csv"
    comparisons_csv = output_dir / "tier5_10b_comparisons.csv"
    fairness_json = output_dir / "tier5_10b_fairness_contract.json"
    plot_path = output_dir / "tier5_10b_task_pressure.png"
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
        "# Tier 5.10b Memory-Pressure Task Validation Findings",
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
        "Tier 5.10b validates whether repaired recurrence/context tasks actually require remembered context before CRA memory mechanisms are tested.",
        "",
        "## Claim Boundary",
        "",
        "- This is task-validation evidence, not CRA capability evidence.",
        "- Oracle/context-memory controls are included to prove the task is solvable if the missing memory exists.",
        "- A pass authorizes Tier 5.10c mechanism testing; it does not promote sleep/replay or any CRA memory mechanism.",
        "",
        "## Task Pressure Comparisons",
        "",
        "| Task | Sign persistence acc | Context memory acc | Oracle acc | Shuffled acc | Reset acc | Wrong-context acc | Best standard model | Best standard acc | Memory edge vs sign | Memory edge vs failure control | Ambiguous cues | Decisions |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in comparisons:
        lines.append(
            "| "
            f"{row['task']} | "
            f"{markdown_value(row.get('sign_persistence_accuracy'))} | "
            f"{markdown_value(row.get('stream_context_memory_accuracy'))} | "
            f"{markdown_value(row.get('oracle_context_accuracy'))} | "
            f"{markdown_value(row.get('shuffled_context_accuracy'))} | "
            f"{markdown_value(row.get('memory_reset_accuracy'))} | "
            f"{markdown_value(row.get('wrong_context_accuracy'))} | "
            f"`{row.get('best_standard_model')}` | "
            f"{markdown_value(row.get('best_standard_accuracy'))} | "
            f"{markdown_value(row.get('memory_edge_vs_sign'))} | "
            f"{markdown_value(row.get('memory_edge_vs_best_failure_control'))} | "
            f"{markdown_value(row.get('ambiguous_current_cue_count'))} | "
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
            "- `tier5_10b_results.json`: machine-readable manifest.",
            "- `tier5_10b_report.md`: human findings and claim boundary.",
            "- `tier5_10b_summary.csv`: aggregate task/model metrics.",
            "- `tier5_10b_comparisons.csv`: task-pressure comparison table.",
            "- `tier5_10b_fairness_contract.json`: predeclared comparison/leakage rules.",
            "- `tier5_10b_task_pressure.png`: task-pressure plot.",
            "- `*_timeseries.csv`: per-task/per-model/per-seed traces.",
            "",
            "![task_pressure](tier5_10b_task_pressure.png)",
            "",
        ]
    )
    if MATPLOTLIB_ERROR:
        lines.append(f"Plotting unavailable: `{MATPLOTLIB_ERROR}`")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_latest(output_dir: Path, report_path: Path, manifest_path: Path, summary_csv: Path, status: str) -> None:
    latest_path = ROOT / "controlled_test_output" / "tier5_10b_latest_manifest.json"
    payload = {
        "generated_at_utc": utc_now(),
        "tier": TIER,
        "status": status,
        "output_dir": str(output_dir),
        "manifest": str(manifest_path),
        "report": str(report_path),
        "summary_csv": str(summary_csv),
        "canonical": False,
        "claim": "Latest Tier 5.10b task-pressure validation; passing authorizes memory-mechanism retest only.",
    }
    write_json(latest_path, payload)


def build_parser() -> argparse.ArgumentParser:
    parser = build_tier5_1_parser()
    parser.description = "Run Tier 5.10b memory-pressure task validation."
    parser.set_defaults(
        backend="mock",
        tasks=DEFAULT_TASKS,
        steps=720,
        seed_count=3,
        models=DEFAULT_MODELS,
        feature_history=5,
    )
    parser.add_argument("--context-gap", type=int, default=12)
    parser.add_argument("--context-period", type=int, default=24)
    parser.add_argument("--long-context-gap", type=int, default=32)
    parser.add_argument("--long-context-period", type=int, default=48)
    parser.add_argument("--distractor-density", type=float, default=0.65)
    parser.add_argument("--distractor-scale", type=float, default=0.30)
    parser.add_argument("--recurrence-phase-len", type=int, default=240)
    parser.add_argument("--recurrence-trial-gap", type=int, default=12)
    parser.add_argument("--recurrence-decision-gap", type=int, default=16)
    parser.add_argument("--max-sign-persistence-tail", type=float, default=0.65)
    parser.add_argument("--min-oracle-tail", type=float, default=0.95)
    parser.add_argument("--min-context-memory-tail", type=float, default=0.90)
    parser.add_argument("--min-memory-edge-vs-sign", type=float, default=0.25)
    parser.add_argument("--min-memory-edge-vs-failure-control", type=float, default=0.25)
    parser.add_argument("--max-best-standard-accuracy", type=float, default=0.85)
    parser.add_argument("--smoke", action="store_true", help="Run harness integrity gates only; scientific task-pressure gates are skipped.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = args.output_dir or (ROOT / "controlled_test_output" / f"tier5_10b_{timestamp}")
    output_dir.mkdir(parents=True, exist_ok=True)
    result = run_tier(args, output_dir)
    manifest_path = output_dir / "tier5_10b_results.json"
    report_path = output_dir / "tier5_10b_report.md"
    summary_csv = output_dir / "tier5_10b_summary.csv"
    comparisons_csv = output_dir / "tier5_10b_comparisons.csv"
    fairness_json = output_dir / "tier5_10b_fairness_contract.json"
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
            "task_pressure_png": str(output_dir / "tier5_10b_task_pressure.png"),
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
