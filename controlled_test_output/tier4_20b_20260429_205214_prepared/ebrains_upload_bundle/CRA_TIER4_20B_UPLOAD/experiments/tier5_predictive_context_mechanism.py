#!/usr/bin/env python3
"""Tier 5.12b internal predictive-context mechanism diagnostic.

Tier 5.12a validated task pressure: reflex shortcuts fail, while a causal
predictive signal can solve the streams. Tier 5.12b tests the next bounded
mechanism step: can CRA store a visible causal precursor before feedback arrives
and inject that retained predictive context at the later decision point?

This is software mechanism evidence only. It is not full world modeling, not
language grounding, not planning, not hidden-state inference, and not hardware
prediction.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
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

from coral_reef_spinnaker import Organism, ReefConfig  # noqa: E402
from tier2_learning import (  # noqa: E402
    criterion,
    end_backend,
    load_backend,
    markdown_value,
    pass_fail,
    setup_backend,
    strict_sign,
    write_csv,
    write_json,
)
from tier4_scaling import mean, min_value, seeds_from_args, stdev  # noqa: E402
from tier5_external_baselines import build_parser as build_tier5_1_parser, parse_models, summarize_rows  # noqa: E402
from tier5_macro_eligibility import computed_horizon, set_nested_attr  # noqa: E402
from tier5_predictive_task_pressure import (  # noqa: E402
    CONTROL_MODELS,
    DEFAULT_MODELS,
    PredictiveTask,
    build_tasks as build_predictive_tasks,
    run_control_model,
    run_external_model,
    task_pressure_summary,
)


TIER = "Tier 5.12b - Internal Predictive Context Mechanism Diagnostic"
DEFAULT_TASKS = "masked_input_prediction,event_stream_prediction,sensor_anomaly_prediction"
DEFAULT_VARIANTS = "v1_7_reactive,external_predictive_scaffold,internal_predictive_context,wrong_predictive_context,shuffled_predictive_context,no_write_predictive_context"
EPS = 1e-12


@dataclass(frozen=True)
class PredictiveVariant:
    name: str
    group: str
    runner: str
    feature_mode: str
    hypothesis: str
    overrides: dict[str, Any]


VARIANTS: tuple[PredictiveVariant, ...] = (
    PredictiveVariant(
        name="v1_7_reactive",
        group="frozen_baseline",
        runner="internal",
        feature_mode="raw",
        hypothesis="v1.7 CRA receives the raw predictive-pressure stream without predictive-context injection.",
        overrides={
            "learning.delayed_readout_learning_rate": 0.20,
            "learning.macro_eligibility_enabled": False,
            "learning.context_memory_enabled": True,
            "learning.context_memory_mode": "keyed",
            "learning.context_memory_slot_count": 4,
            "learning.predictive_context_enabled": False,
        },
    ),
    PredictiveVariant(
        name="external_predictive_scaffold",
        group="external_scaffold",
        runner="external",
        feature_mode="predictive_scaffold",
        hypothesis="External scaffold injects the causal predictive signal at decision rows before CRA sees the observation.",
        overrides={
            "learning.delayed_readout_learning_rate": 0.20,
            "learning.macro_eligibility_enabled": False,
            "learning.context_memory_enabled": True,
            "learning.context_memory_mode": "keyed",
            "learning.context_memory_slot_count": 4,
            "learning.predictive_context_enabled": False,
        },
    ),
    PredictiveVariant(
        name="internal_predictive_context",
        group="candidate",
        runner="internal",
        feature_mode="keyed",
        hypothesis="Internal CRA predictive context stores visible precursor sign and injects it at the later decision row.",
        overrides={
            "learning.delayed_readout_learning_rate": 0.20,
            "learning.macro_eligibility_enabled": False,
            "learning.context_memory_enabled": True,
            "learning.context_memory_mode": "keyed",
            "learning.context_memory_slot_count": 4,
            "learning.predictive_context_enabled": True,
            "learning.predictive_context_mode": "keyed",
            "learning.predictive_context_slot_count": 8,
            "learning.predictive_context_input_gain": 1.0,
        },
    ),
    PredictiveVariant(
        name="wrong_predictive_context",
        group="predictive_ablation",
        runner="internal",
        feature_mode="wrong",
        hypothesis="Control: predictive context is systematically inverted at decision rows.",
        overrides={
            "learning.delayed_readout_learning_rate": 0.20,
            "learning.macro_eligibility_enabled": False,
            "learning.context_memory_enabled": True,
            "learning.context_memory_mode": "keyed",
            "learning.context_memory_slot_count": 4,
            "learning.predictive_context_enabled": True,
            "learning.predictive_context_mode": "wrong",
            "learning.predictive_context_slot_count": 8,
        },
    ),
    PredictiveVariant(
        name="shuffled_predictive_context",
        group="predictive_ablation",
        runner="internal",
        feature_mode="shuffled",
        hypothesis="Control: predictive context reads a different retained slot when possible.",
        overrides={
            "learning.delayed_readout_learning_rate": 0.20,
            "learning.macro_eligibility_enabled": False,
            "learning.context_memory_enabled": True,
            "learning.context_memory_mode": "keyed",
            "learning.context_memory_slot_count": 4,
            "learning.predictive_context_enabled": True,
            "learning.predictive_context_mode": "shuffled",
            "learning.predictive_context_slot_count": 8,
        },
    ),
    PredictiveVariant(
        name="no_write_predictive_context",
        group="predictive_ablation",
        runner="internal",
        feature_mode="no_write",
        hypothesis="Control: predictive context reads at decision rows but never writes precursor state.",
        overrides={
            "learning.delayed_readout_learning_rate": 0.20,
            "learning.macro_eligibility_enabled": False,
            "learning.context_memory_enabled": True,
            "learning.context_memory_mode": "keyed",
            "learning.context_memory_slot_count": 4,
            "learning.predictive_context_enabled": True,
            "learning.predictive_context_mode": "no_write",
            "learning.predictive_context_slot_count": 8,
        },
    ),
)


VISIBLE_UPDATE_EVENTS = {
    "masked_input_prediction": {"visible_cue_b"},
    "event_stream_prediction": {"event_b"},
    "sensor_anomaly_prediction": {"precursor_b"},
}


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


def parse_variants(raw: str) -> list[PredictiveVariant]:
    names = [item.strip() for item in raw.split(",") if item.strip()]
    if not names or names == ["all"]:
        return list(VARIANTS)
    by_name = {variant.name: variant for variant in VARIANTS}
    missing = [name for name in names if name not in by_name]
    if missing:
        raise argparse.ArgumentTypeError(f"unknown Tier 5.12b variants: {', '.join(missing)}")
    selected = [by_name[name] for name in names]
    required = {"v1_7_reactive", "external_predictive_scaffold", "internal_predictive_context"}
    present = {variant.name for variant in selected}
    if not required.issubset(present):
        raise argparse.ArgumentTypeError(
            "Tier 5.12b requires v1_7_reactive, external_predictive_scaffold, and internal_predictive_context"
        )
    return selected


def make_config(*, seed: int, task: PredictiveTask, variant: PredictiveVariant, args: argparse.Namespace) -> ReefConfig:
    cfg = ReefConfig.default()
    cfg.seed = int(seed)
    cfg.lifecycle.initial_population = int(args.cra_population_size)
    cfg.lifecycle.max_population_from_memory = False
    cfg.lifecycle.max_population_hard = int(args.cra_population_size)
    cfg.lifecycle.enable_reproduction = False
    cfg.lifecycle.enable_apoptosis = False
    cfg.lifecycle.enable_structural_plasticity = True
    cfg.measurement.stream_history_maxlen = max(task.stream.steps + 32, 128)
    cfg.spinnaker.sync_interval_steps = 0
    cfg.spinnaker.runtime_ms_per_step = 1000.0
    cfg.learning.evaluation_horizon_bars = computed_horizon(task.stream)
    cfg.learning.readout_learning_rate = float(args.cra_readout_lr)
    cfg.learning.delayed_readout_learning_rate = float(args.cra_delayed_readout_lr)
    if hasattr(cfg.network, "message_passing_steps"):
        cfg.network.message_passing_steps = int(args.message_passing_steps)
        cfg.network.message_context_gain = float(args.message_context_gain)
        cfg.network.message_prediction_mix = float(args.message_prediction_mix)
    for key, value in variant.overrides.items():
        set_nested_attr(cfg, key, value)
    if cfg.lifecycle.max_population_hard < cfg.lifecycle.initial_population:
        cfg.lifecycle.max_population_hard = cfg.lifecycle.initial_population
    return cfg


def trial_label_map(task: PredictiveTask) -> dict[int, int]:
    mapping: dict[int, int] = {}
    for step in range(task.stream.steps):
        if not bool(task.stream.evaluation_mask[step]):
            continue
        trial = int(task.trial_id[step])
        sign = strict_sign(float(task.stream.evaluation_target[step]))
        if trial >= 0 and sign != 0:
            mapping[trial] = sign
    return mapping


def predictive_metadata_for_step(task: PredictiveTask, step: int, label_by_trial: dict[int, int]) -> dict[str, Any]:
    event = str(task.event_type[step])
    trial = int(task.trial_id[step])
    label = int(label_by_trial.get(trial, 0))
    metadata: dict[str, Any] = {
        "tier": "5.12b",
        "event_type": event,
        "phase": task.phase[step],
        "trial_id": trial,
        "predictive_context_key": f"trial:{trial}",
    }
    update_events = VISIBLE_UPDATE_EVENTS.get(task.stream.name, set())
    if event in update_events and label != 0:
        metadata["predictive_context_update"] = True
        metadata["predictive_context_sign"] = int(label)
    if bool(task.stream.evaluation_mask[step]):
        metadata["predictive_context_decision"] = True
    return metadata


def transformed_external_observation(task: PredictiveTask, step: int, variant: PredictiveVariant) -> tuple[float, dict[str, Any]]:
    raw = float(task.stream.sensory[step])
    if variant.feature_mode == "predictive_scaffold" and bool(task.stream.evaluation_mask[step]):
        signal = strict_sign(float(task.predictive_signal[step]))
        if signal != 0:
            return float(signal), {"feature_source": "external_predictive_scaffold", "feature_active": True}
    return raw, {"feature_source": "raw", "feature_active": False}


def run_cra_predictive_variant(
    task: PredictiveTask,
    *,
    seed: int,
    variant: PredictiveVariant,
    args: argparse.Namespace,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    random.seed(seed)
    np.random.seed(seed)
    sim, backend_name = load_backend(args.backend)
    setup_backend(sim, backend_name)
    cfg = make_config(seed=seed, task=task, variant=variant, args=args)
    organism = Organism(cfg, sim, use_default_trading_bridge=False)
    label_by_trial = trial_label_map(task)
    rows: list[dict[str, Any]] = []
    started = time.perf_counter()
    try:
        organism.initialize(stream_keys=[task.stream.domain])
        for step in range(task.stream.steps):
            raw_observation = float(task.stream.sensory[step])
            metadata = predictive_metadata_for_step(task, step, label_by_trial)
            if variant.runner == "external":
                observation, feature = transformed_external_observation(task, step, variant)
            else:
                observation = raw_observation
                feature = {"feature_source": "pending_internal", "feature_active": False}
            consequence = float(task.stream.current_target[step])
            metrics = organism.train_task_step(
                observation_value=observation,
                consequence_value=consequence,
                horizon_signal=consequence,
                dt_seconds=float(args.dt_seconds),
                task_name=task.stream.name,
                metadata=metadata,
            )
            if variant.runner == "internal":
                feature = {
                    "feature_source": str(metrics.predictive_context_feature_source),
                    "feature_active": bool(metrics.predictive_context_feature_active),
                    "predictive_context_value": int(metrics.predictive_context_value),
                    "predictive_context_updates": int(metrics.predictive_context_updates),
                    "predictive_context_key": str(metrics.predictive_context_key),
                    "predictive_context_slot_count": int(metrics.predictive_context_slot_count),
                    "predictive_context_visible_signal": int(metrics.predictive_context_visible_signal),
                }
            prediction = float(metrics.colony_prediction)
            eval_sign = strict_sign(float(task.stream.evaluation_target[step]))
            pred_sign = strict_sign(prediction)
            injected_observation = (
                float(metrics.predictive_context_bound_observation)
                if variant.runner == "internal"
                else float(observation)
            )
            row = metrics.to_dict()
            row.update(
                {
                    "task": task.stream.name,
                    "model": variant.name,
                    "model_family": "CRA",
                    "variant": variant.name,
                    "variant_group": variant.group,
                    "backend": backend_name,
                    "seed": int(seed),
                    "step": int(step),
                    "event_type": task.event_type[step],
                    "phase": task.phase[step],
                    "trial_id": int(task.trial_id[step]),
                    "context_sign": int(task.context_sign[step]),
                    "cue_a_sign": int(task.cue_a_sign[step]),
                    "cue_b_sign": int(task.cue_b_sign[step]),
                    "predictive_runner": variant.runner,
                    "raw_sensory_return_1m": raw_observation,
                    "sensory_return_1m": injected_observation,
                    "target_return_1m": consequence,
                    "target_signal_horizon": float(task.stream.evaluation_target[step]),
                    "target_signal_sign": eval_sign,
                    "target_signal_nonzero": bool(task.stream.evaluation_mask[step] and eval_sign != 0),
                    "prediction_sign": pred_sign,
                    "strict_direction_correct": bool(task.stream.evaluation_mask[step] and pred_sign != 0 and pred_sign == eval_sign),
                    "feedback_due_step": int(task.stream.feedback_due_step[step]),
                    "predictive_signal": float(task.predictive_signal[step]),
                    "predictive_signal_sign": strict_sign(float(task.predictive_signal[step])),
                    "metadata_update": bool(metadata.get("predictive_context_update", False)),
                    "metadata_decision": bool(metadata.get("predictive_context_decision", False)),
                    "configured_horizon_bars": int(cfg.learning.evaluation_horizon_bars),
                    "configured_readout_lr": float(cfg.learning.readout_learning_rate),
                    "configured_delayed_readout_lr": float(cfg.learning.delayed_readout_learning_rate),
                    "configured_initial_population": int(cfg.lifecycle.initial_population),
                    "configured_max_population": int(cfg.lifecycle.max_population_hard),
                    **feature,
                }
            )
            rows.append(row)
    finally:
        organism.shutdown()
        end_backend(sim)
    summary = summarize_rows(rows)
    active_steps = sum(1 for row in rows if bool(row.get("feature_active", False)))
    updates = max([int(row.get("predictive_context_updates", 0) or 0) for row in rows], default=0)
    metadata_updates = sum(1 for row in rows if bool(row.get("metadata_update", False)))
    summary.update(
        {
            "task": task.stream.name,
            "model": variant.name,
            "model_family": "CRA",
            "variant": variant.name,
            "variant_group": variant.group,
            "feature_mode": variant.feature_mode,
            "predictive_runner": variant.runner,
            "hypothesis": variant.hypothesis,
            "backend": backend_name,
            "seed": int(seed),
            "steps": task.stream.steps,
            "runtime_seconds": time.perf_counter() - started,
            "feature_active_steps": int(active_steps),
            "predictive_context_updates": int(updates),
            "metadata_update_steps": int(metadata_updates),
            "task_metadata": task.stream.metadata,
            "task_pressure": task_pressure_summary(task),
            "config_overrides": variant.overrides,
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
        "final_n_alive",
        "total_births",
        "total_deaths",
        "max_abs_dopamine",
        "mean_abs_dopamine",
        "feature_active_steps",
        "predictive_context_updates",
        "metadata_update_steps",
    ]
    aggregate: dict[str, Any] = {
        "task": task.stream.name,
        "display_name": task.stream.display_name,
        "domain": task.stream.domain,
        "model": model,
        "model_family": summaries[0].get("model_family") if summaries else None,
        "variant_group": summaries[0].get("variant_group") if summaries else None,
        "feature_mode": summaries[0].get("feature_mode") if summaries else None,
        "predictive_runner": summaries[0].get("predictive_runner") if summaries else None,
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
        aggregate[f"{key}_sum"] = float(sum(valid)) if valid else None
    return aggregate


def composite_score(row: dict[str, Any]) -> float:
    acc = float(row.get("all_accuracy_mean") or 0.0)
    tail = float(row.get("tail_accuracy_mean") or 0.0)
    corr = abs(float(row.get("prediction_target_corr_mean") or 0.0))
    return acc + 0.30 * tail + 0.15 * corr


def build_comparisons(aggregates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    by_task_model = {(row["task"], row["model"]): row for row in aggregates}
    for task in sorted({row["task"] for row in aggregates}):
        baseline = by_task_model.get((task, "v1_7_reactive"), {})
        scaffold = by_task_model.get((task, "external_predictive_scaffold"), {})
        candidate = by_task_model.get((task, "internal_predictive_context"), {})
        ablations = [
            row
            for row in aggregates
            if row["task"] == task and row.get("variant_group") == "predictive_ablation"
        ]
        controls = [
            row
            for row in aggregates
            if row["task"] == task and row["model"] in CONTROL_MODELS and row["model"] != "predictive_memory"
        ]
        standards = [
            row
            for row in aggregates
            if row["task"] == task
            and row.get("model_family") != "CRA"
            and row["model"] not in CONTROL_MODELS
        ]
        best_ablation = max(ablations, key=composite_score, default={})
        best_control = max(controls, key=lambda row: float(row.get("all_accuracy_mean") or 0.0), default={})
        best_standard = max(standards, key=lambda row: float(row.get("all_accuracy_mean") or 0.0), default={})
        pressure = candidate.get("task_pressure") or baseline.get("task_pressure") or {}
        rows.append(
            {
                "task": task,
                "baseline_all_accuracy": baseline.get("all_accuracy_mean"),
                "baseline_tail_accuracy": baseline.get("tail_accuracy_mean"),
                "candidate_all_accuracy": candidate.get("all_accuracy_mean"),
                "candidate_tail_accuracy": candidate.get("tail_accuracy_mean"),
                "candidate_all_delta_vs_v1_7": float(candidate.get("all_accuracy_mean") or 0.0) - float(baseline.get("all_accuracy_mean") or 0.0),
                "candidate_tail_delta_vs_v1_7": float(candidate.get("tail_accuracy_mean") or 0.0) - float(baseline.get("tail_accuracy_mean") or 0.0),
                "scaffold_all_accuracy": scaffold.get("all_accuracy_mean"),
                "scaffold_tail_accuracy": scaffold.get("tail_accuracy_mean"),
                "candidate_all_delta_vs_external_scaffold": float(candidate.get("all_accuracy_mean") or 0.0) - float(scaffold.get("all_accuracy_mean") or 0.0),
                "candidate_tail_delta_vs_external_scaffold": float(candidate.get("tail_accuracy_mean") or 0.0) - float(scaffold.get("tail_accuracy_mean") or 0.0),
                "best_ablation_model": best_ablation.get("model"),
                "best_ablation_all_accuracy": best_ablation.get("all_accuracy_mean"),
                "candidate_all_delta_vs_best_ablation": float(candidate.get("all_accuracy_mean") or 0.0) - float(best_ablation.get("all_accuracy_mean") or 0.0),
                "candidate_composite_delta_vs_best_ablation": composite_score(candidate) - composite_score(best_ablation) if best_ablation else None,
                "best_control_model": best_control.get("model"),
                "best_control_all_accuracy": best_control.get("all_accuracy_mean"),
                "candidate_all_delta_vs_best_control": float(candidate.get("all_accuracy_mean") or 0.0) - float(best_control.get("all_accuracy_mean") or 0.0),
                "best_standard_model": best_standard.get("model"),
                "best_standard_all_accuracy": best_standard.get("all_accuracy_mean"),
                "candidate_all_delta_vs_best_standard": float(candidate.get("all_accuracy_mean") or 0.0) - float(best_standard.get("all_accuracy_mean") or 0.0),
                "candidate_feature_active_steps": candidate.get("feature_active_steps_sum"),
                "candidate_predictive_context_updates": candidate.get("predictive_context_updates_sum"),
                "candidate_metadata_update_steps": candidate.get("metadata_update_steps_sum"),
                "same_current_input_opposite_labels": bool(pressure.get("same_current_input_opposite_labels", False)),
                "same_last_sign_opposite_labels": bool(pressure.get("same_last_sign_opposite_labels", False)),
                "decision_count": pressure.get("decision_count"),
            }
        )
    return rows


def evaluate_tier(
    *,
    aggregates: list[dict[str, Any]],
    comparisons: list[dict[str, Any]],
    leakage: dict[str, Any],
    variants: list[PredictiveVariant],
    models: list[str],
    args: argparse.Namespace,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    tasks = [item.strip() for item in args.tasks.split(",") if item.strip()]
    if not tasks or tasks == ["all"]:
        tasks = [item.strip() for item in DEFAULT_TASKS.split(",") if item.strip()]
    seeds = seeds_from_args(args)
    expected_runs = len(tasks) * len(seeds) * (len(variants) + len(models) + len(CONTROL_MODELS))
    observed_runs = sum(int(row.get("runs", 0)) for row in aggregates)
    candidate_accs = [float(row.get("candidate_all_accuracy") or 0.0) for row in comparisons]
    candidate_tail = [float(row.get("candidate_tail_accuracy") or 0.0) for row in comparisons]
    baseline_edges = [float(row.get("candidate_all_delta_vs_v1_7") or 0.0) for row in comparisons]
    scaffold_edges = [float(row.get("candidate_all_delta_vs_external_scaffold") or 0.0) for row in comparisons]
    ablation_edges = [float(row.get("candidate_all_delta_vs_best_ablation") or 0.0) for row in comparisons]
    control_edges = [float(row.get("candidate_all_delta_vs_best_control") or 0.0) for row in comparisons]
    standard_edges = [float(row.get("candidate_all_delta_vs_best_standard") or 0.0) for row in comparisons]
    active_steps = sum(float(row.get("candidate_feature_active_steps") or 0.0) for row in comparisons)
    context_updates = sum(float(row.get("candidate_predictive_context_updates") or 0.0) for row in comparisons)
    metadata_updates = sum(float(row.get("candidate_metadata_update_steps") or 0.0) for row in comparisons)
    ambiguity_ok = all(
        bool(row.get("same_current_input_opposite_labels")) and bool(row.get("same_last_sign_opposite_labels"))
        for row in comparisons
    )
    base_criteria = [
        criterion("full variant/baseline/control/task/seed matrix completed", observed_runs, "==", expected_runs, observed_runs == expected_runs),
        criterion("feedback timing has no leakage violations", leakage.get("feedback_due_violations"), "==", 0, int(leakage.get("feedback_due_violations", 0)) == 0),
        criterion("task remains shortcut-ambiguous", ambiguity_ok, "==", True, ambiguity_ok),
        criterion("candidate predictive context feature is active", active_steps, ">", 0, active_steps > 0),
        criterion("candidate receives predictive-context writes", context_updates, ">", 0, context_updates > 0),
        criterion("metadata exposes precursor writes before decisions", metadata_updates, ">", 0, metadata_updates > 0),
    ]
    science_criteria = [
        criterion(
            "candidate reaches minimum predictive-task accuracy",
            min(candidate_accs) if candidate_accs else None,
            ">=",
            args.min_candidate_accuracy,
            bool(candidate_accs) and min(candidate_accs) >= args.min_candidate_accuracy,
        ),
        criterion(
            "candidate reaches minimum tail accuracy",
            min(candidate_tail) if candidate_tail else None,
            ">=",
            args.min_candidate_tail_accuracy,
            bool(candidate_tail) and min(candidate_tail) >= args.min_candidate_tail_accuracy,
        ),
        criterion(
            "candidate improves over v1.7 reactive CRA",
            min(baseline_edges) if baseline_edges else None,
            ">=",
            args.min_candidate_edge_vs_v1_7,
            bool(baseline_edges) and min(baseline_edges) >= args.min_candidate_edge_vs_v1_7,
        ),
        criterion(
            "internal candidate approaches external predictive scaffold",
            min(scaffold_edges) if scaffold_edges else None,
            ">=",
            -abs(float(args.max_candidate_gap_vs_external_scaffold)),
            bool(scaffold_edges) and min(scaffold_edges) >= -abs(float(args.max_candidate_gap_vs_external_scaffold)),
            "Internal predictive context can trail the external scaffold slightly but cannot collapse relative to it.",
        ),
        criterion(
            "predictive ablations are worse than candidate",
            min(ablation_edges) if ablation_edges else None,
            ">=",
            args.min_candidate_edge_vs_ablation,
            bool(ablation_edges) and min(ablation_edges) >= args.min_candidate_edge_vs_ablation,
        ),
        criterion(
            "candidate beats best shortcut control",
            min(control_edges) if control_edges else None,
            ">=",
            args.min_candidate_edge_vs_control,
            bool(control_edges) and min(control_edges) >= args.min_candidate_edge_vs_control,
        ),
        criterion(
            "candidate beats best selected external baseline",
            min(standard_edges) if standard_edges else None,
            ">=",
            args.min_candidate_edge_vs_standard,
            bool(standard_edges) and min(standard_edges) >= args.min_candidate_edge_vs_standard,
        ),
    ]
    criteria = base_criteria if args.smoke else base_criteria + science_criteria
    summary = {
        "expected_runs": expected_runs,
        "observed_runs": observed_runs,
        "tasks": tasks,
        "seeds": seeds,
        "models": models,
        "variants": [variant.name for variant in variants],
        "controls": list(CONTROL_MODELS),
        "steps": args.steps,
        "smoke": bool(args.smoke),
        "leakage": leakage,
        "claim_boundary": "Software mechanism evidence only; visible predictive-context binding, not full world modeling/language/planning/hardware prediction.",
        "excluded_default_task": "hidden_regime_switching is excluded from default 5.12b because this mechanism requires visible precursor writes; latent regime inference is future work.",
    }
    return criteria, summary


def aggregate_csv_rows(aggregates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fields = [
        "task",
        "model",
        "model_family",
        "variant_group",
        "runs",
        "steps",
        "tail_accuracy_mean",
        "all_accuracy_mean",
        "prediction_target_corr_mean",
        "runtime_seconds_mean",
        "evaluation_count_mean",
        "feature_active_steps_sum",
        "predictive_context_updates_sum",
        "metadata_update_steps_sum",
    ]
    return [{field: row.get(field) for field in fields} for row in aggregates]


def plot_predictive_context(comparisons: list[dict[str, Any]], path: Path) -> None:
    if plt is None or not comparisons:
        return
    tasks = [row["task"].replace("_", "\n") for row in comparisons]
    baseline = [float(row.get("baseline_all_accuracy") or 0.0) for row in comparisons]
    scaffold = [float(row.get("scaffold_all_accuracy") or 0.0) for row in comparisons]
    candidate = [float(row.get("candidate_all_accuracy") or 0.0) for row in comparisons]
    ablation = [float(row.get("best_ablation_all_accuracy") or 0.0) for row in comparisons]
    x = np.arange(len(tasks))
    width = 0.2
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.bar(x - 1.5 * width, baseline, width, label="v1.7 reactive", color="#9f1239")
    ax.bar(x - 0.5 * width, scaffold, width, label="external scaffold", color="#166534")
    ax.bar(x + 0.5 * width, candidate, width, label="internal predictive context", color="#1d4ed8")
    ax.bar(x + 1.5 * width, ablation, width, label="best ablation", color="#737373")
    ax.set_title("Tier 5.12b Internal Predictive Context Diagnostic")
    ax.set_xticks(x)
    ax.set_xticklabels(tasks)
    ax.set_ylim(0.0, 1.05)
    ax.set_ylabel("decision accuracy")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fairness_contract(args: argparse.Namespace, variants: list[PredictiveVariant], models: list[str]) -> dict[str, Any]:
    return {
        "tier": TIER,
        "purpose": "test bounded internal CRA predictive-context binding after Tier 5.12a task-pressure validation",
        "selected_external_baselines": models,
        "variants": [variant.name for variant in variants],
        "predictive_controls": list(CONTROL_MODELS),
        "fairness_rules": [
            "same sensory stream, target stream, evaluation mask, and feedback_due_step arrays per seed",
            "standard baselines see only the sensory stream and configured feature history",
            "candidate internal predictive context can write only at visible precursor metadata rows",
            "candidate internal predictive context can read only at marked decision/evaluation rows",
            "wrong/shuffled/no-write predictive-context controls must not match the candidate",
            "feedback_due_step must be greater than or equal to prediction step",
            "passing Tier 5.12b does not freeze v1.8 without compact regression",
        ],
        "tasks": args.tasks,
        "steps": args.steps,
        "seeds": seeds_from_args(args),
        "feature_history": args.feature_history,
        "excluded_default_task": "hidden_regime_switching is reserved for later latent-predictive inference, not this visible-precursor binding bridge.",
    }


def run_tier(args: argparse.Namespace, output_dir: Path) -> dict[str, Any]:
    variants = parse_variants(args.variants)
    models = [model for model in parse_models(args.models) if model != "cra"]
    summaries_by_cell: dict[tuple[str, str], list[dict[str, Any]]] = {}
    rows_by_cell_seed: dict[tuple[str, str, int], list[dict[str, Any]]] = {}
    task_by_name: dict[str, PredictiveTask] = {}
    artifacts: dict[str, str] = {}
    started = time.perf_counter()
    for seed in seeds_from_args(args):
        for task in build_predictive_tasks(args, seed=args.task_seed + seed):
            task_by_name[task.stream.name] = task
            for variant in variants:
                print(f"[tier5.12b] task={task.stream.name} variant={variant.name} seed={seed}", flush=True)
                rows, summary = run_cra_predictive_variant(task, seed=seed, variant=variant, args=args)
                csv_path = output_dir / f"{task.stream.name}_{variant.name}_seed{seed}_timeseries.csv"
                write_csv(csv_path, rows)
                artifacts[f"{task.stream.name}_{variant.name}_seed{seed}_timeseries_csv"] = str(csv_path)
                summaries_by_cell.setdefault((task.stream.name, variant.name), []).append(summary)
                rows_by_cell_seed[(task.stream.name, variant.name, seed)] = rows
            for model in [*models, *CONTROL_MODELS]:
                print(f"[tier5.12b] task={task.stream.name} model={model} seed={seed}", flush=True)
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
        variants=variants,
        models=models,
        args=args,
    )
    status, failure_reason = pass_fail(criteria)
    summary_csv = output_dir / "tier5_12b_summary.csv"
    comparisons_csv = output_dir / "tier5_12b_comparisons.csv"
    fairness_json = output_dir / "tier5_12b_fairness_contract.json"
    plot_path = output_dir / "tier5_12b_predictive_context.png"
    write_csv(summary_csv, aggregate_csv_rows(aggregates))
    write_csv(comparisons_csv, comparisons)
    write_json(fairness_json, fairness_contract(args, variants, models))
    plot_predictive_context(comparisons, plot_path)
    result = {
        "name": TIER,
        "status": status,
        "summary": {
            "tier_summary": tier_summary,
            "aggregates": aggregates,
            "comparisons": comparisons,
            "runtime_seconds": time.perf_counter() - started,
        },
        "criteria": criteria,
        "artifacts": {
            **artifacts,
            "summary_csv": str(summary_csv),
            "comparisons_csv": str(comparisons_csv),
            "fairness_contract_json": str(fairness_json),
            "predictive_context_png": str(plot_path),
        },
        "failure_reason": failure_reason,
    }
    return result


def write_report(path: Path, result: dict[str, Any], args: argparse.Namespace, output_dir: Path) -> None:
    overall = "PASS" if result["status"] == "pass" else "FAIL"
    comparisons = result["summary"]["comparisons"]
    aggregates = result["summary"]["aggregates"]
    lines = [
        "# Tier 5.12b Internal Predictive Context Mechanism Findings",
        "",
        f"- Generated: `{utc_now()}`",
        f"- Status: **{overall}**",
        f"- Steps: `{args.steps}`",
        f"- Seeds: `{', '.join(str(seed) for seed in seeds_from_args(args))}`",
        f"- Tasks: `{args.tasks}`",
        f"- Variants: `{args.variants}`",
        f"- Selected standard baselines: `{args.models}`",
        f"- Backend: `{args.backend}`",
        f"- Smoke mode: `{args.smoke}`",
        f"- Output directory: `{output_dir}`",
        "",
        "Tier 5.12b tests whether CRA can store a visible causal predictive precursor before feedback arrives and use it later at a decision point.",
        "",
        "## Claim Boundary",
        "",
        "- This is software mechanism evidence, not hardware evidence.",
        "- This is visible predictive-context binding, not full world modeling or hidden-state inference.",
        "- This does not prove language grounding, planning, or AGI capability.",
        "- A pass authorizes compact regression/promotion review; it does not automatically freeze v1.8.",
        "- `hidden_regime_switching` is intentionally excluded from the default mechanism run because that needs latent-regime inference, not visible precursor storage.",
        "",
        "## Comparisons",
        "",
        "| Task | v1.7 acc | Scaffold acc | Internal predictive acc | Best ablation | Ablation acc | Best control | Control acc | Best baseline | Baseline acc | Edge vs v1.7 | Edge vs ablation | Edge vs baseline | Updates | Active steps |",
        "| --- | ---: | ---: | ---: | --- | ---: | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in comparisons:
        lines.append(
            "| "
            f"{row['task']} | "
            f"{markdown_value(row.get('baseline_all_accuracy'))} | "
            f"{markdown_value(row.get('scaffold_all_accuracy'))} | "
            f"{markdown_value(row.get('candidate_all_accuracy'))} | "
            f"`{row.get('best_ablation_model')}` | "
            f"{markdown_value(row.get('best_ablation_all_accuracy'))} | "
            f"`{row.get('best_control_model')}` | "
            f"{markdown_value(row.get('best_control_all_accuracy'))} | "
            f"`{row.get('best_standard_model')}` | "
            f"{markdown_value(row.get('best_standard_all_accuracy'))} | "
            f"{markdown_value(row.get('candidate_all_delta_vs_v1_7'))} | "
            f"{markdown_value(row.get('candidate_all_delta_vs_best_ablation'))} | "
            f"{markdown_value(row.get('candidate_all_delta_vs_best_standard'))} | "
            f"{markdown_value(row.get('candidate_predictive_context_updates'))} | "
            f"{markdown_value(row.get('candidate_feature_active_steps'))} |"
        )
    lines.extend(
        [
            "",
            "## Aggregate Matrix",
            "",
            "| Task | Model | Family | Group | Tail acc | All acc | Corr | Runtime s |",
            "| --- | --- | --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in sorted(aggregates, key=lambda item: (item["task"], item["model"])):
        lines.append(
            "| "
            f"{row['task']} | `{row['model']}` | {row.get('model_family')} | {row.get('variant_group')} | "
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
            "- `tier5_12b_results.json`: machine-readable manifest.",
            "- `tier5_12b_report.md`: human findings and claim boundary.",
            "- `tier5_12b_summary.csv`: aggregate task/model metrics.",
            "- `tier5_12b_comparisons.csv`: predictive-context comparison table.",
            "- `tier5_12b_fairness_contract.json`: predeclared comparison/leakage rules.",
            "- `tier5_12b_predictive_context.png`: comparison plot.",
            "- `*_timeseries.csv`: per-task/per-model/per-seed traces.",
            "",
            "![predictive_context](tier5_12b_predictive_context.png)",
            "",
        ]
    )
    if MATPLOTLIB_ERROR:
        lines.append(f"Plotting unavailable: `{MATPLOTLIB_ERROR}`")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_latest(output_dir: Path, report_path: Path, manifest_path: Path, summary_csv: Path, status: str) -> None:
    latest_path = ROOT / "controlled_test_output" / "tier5_12b_latest_manifest.json"
    payload = {
        "generated_at_utc": utc_now(),
        "tier": TIER,
        "status": status,
        "output_dir": str(output_dir),
        "manifest": str(manifest_path),
        "report": str(report_path),
        "summary_csv": str(summary_csv),
        "canonical": False,
        "claim": "Latest Tier 5.12b internal predictive-context mechanism diagnostic; passing authorizes compact regression/promotion review only.",
    }
    write_json(latest_path, payload)


def build_parser() -> argparse.ArgumentParser:
    parser = build_tier5_1_parser()
    parser.description = "Run Tier 5.12b internal predictive-context mechanism diagnostic."
    parser.set_defaults(
        backend="nest",
        tasks=DEFAULT_TASKS,
        steps=720,
        seed_count=3,
        models=DEFAULT_MODELS,
        feature_history=6,
    )
    parser.add_argument("--variants", default=DEFAULT_VARIANTS)
    parser.add_argument("--predictive-horizon", type=int, default=8)
    parser.add_argument("--predictive-period", type=int, default=8)
    parser.add_argument("--predictive-regime-block", type=int, default=96)
    parser.add_argument("--masked-period", type=int, default=12)
    parser.add_argument("--masked-gap", type=int, default=6)
    parser.add_argument("--event-period", type=int, default=10)
    parser.add_argument("--anomaly-period", type=int, default=12)
    parser.add_argument("--rolling-window", type=int, default=5)
    parser.add_argument("--message-passing-steps", type=int, default=1)
    parser.add_argument("--message-context-gain", type=float, default=0.15)
    parser.add_argument("--message-prediction-mix", type=float, default=0.35)
    parser.add_argument("--min-candidate-accuracy", type=float, default=0.90)
    parser.add_argument("--min-candidate-tail-accuracy", type=float, default=0.90)
    parser.add_argument("--min-candidate-edge-vs-v1-7", type=float, default=0.20)
    parser.add_argument("--max-candidate-gap-vs-external-scaffold", type=float, default=0.10)
    parser.add_argument("--min-candidate-edge-vs-ablation", type=float, default=0.20)
    parser.add_argument("--min-candidate-edge-vs-control", type=float, default=0.20)
    parser.add_argument("--min-candidate-edge-vs-standard", type=float, default=0.20)
    parser.add_argument("--smoke", action="store_true", help="Run harness integrity gates only; scientific mechanism gates are skipped.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = args.output_dir or (ROOT / "controlled_test_output" / f"tier5_12b_{timestamp}")
    output_dir.mkdir(parents=True, exist_ok=True)
    result = run_tier(args, output_dir)
    manifest_path = output_dir / "tier5_12b_results.json"
    report_path = output_dir / "tier5_12b_report.md"
    summary_csv = output_dir / "tier5_12b_summary.csv"
    write_json(manifest_path, result)
    write_report(report_path, result, args, output_dir)
    write_latest(output_dir, report_path, manifest_path, summary_csv, result["status"])
    print(f"Tier 5.12b status: {result['status']}")
    print(f"Report: {report_path}")
    if result["failure_reason"]:
        print(f"Failure: {result['failure_reason']}")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
