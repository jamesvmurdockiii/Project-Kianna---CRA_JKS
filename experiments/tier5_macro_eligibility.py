#!/usr/bin/env python3
"""Tier 5.9a macro-eligibility trace diagnostic for CRA.

This tier is the first post-v1.4 mechanism-upgrade gate. It compares the
frozen v1.4 delayed-credit path against a host-side macro eligibility trace,
trace ablations, and selected external baselines on delayed/nonstationary tasks.

A pass means the candidate mechanism earned further promotion work. A failure
means the result is still useful diagnostic evidence, not a regression of the
v1.4 evidence baseline.
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

from coral_reef_spinnaker import Observation, Organism, ReefConfig, SensorControlAdapter  # noqa: E402
from tier2_learning import (  # noqa: E402
    DEFAULT_AMPLITUDE,
    DEFAULT_DT_SECONDS,
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
from tier5_external_baselines import (  # noqa: E402
    LEARNER_FACTORIES,
    TaskStream,
    TestResult,
    build_parser as build_tier5_1_parser,
    delayed_cue_task,
    hard_noisy_switching_task,
    parse_models,
    recovery_steps,
    run_baseline_case,
    summarize_rows,
)


TIER = "Tier 5.9a - Macro Eligibility Trace Diagnostic"
DEFAULT_TASKS = "delayed_cue,hard_noisy_switching,variable_delay_cue,aba_recurrence"
DEFAULT_MODELS = "sign_persistence,online_perceptron,online_logistic_regression,echo_state_network,stdp_only_snn"
DEFAULT_VARIANTS = "v1_4_pending_horizon,macro_eligibility,macro_eligibility_shuffled,macro_eligibility_zero"
EPS = 1e-12


@dataclass(frozen=True)
class VariantSpec:
    name: str
    group: str
    hypothesis: str
    overrides: dict[str, Any]


VARIANTS: tuple[VariantSpec, ...] = (
    VariantSpec(
        name="v1_4_pending_horizon",
        group="frozen_baseline",
        hypothesis="Frozen v1.4 delayed-credit path: PendingHorizon with delayed_lr_0_20 and no macro trace.",
        overrides={
            "learning.delayed_readout_learning_rate": 0.20,
            "learning.macro_eligibility_enabled": False,
        },
    ),
    VariantSpec(
        name="macro_eligibility",
        group="candidate",
        hypothesis="A decaying per-polyp eligibility trace should improve delayed/nonstationary credit assignment.",
        overrides={
            "learning.delayed_readout_learning_rate": 0.20,
            "learning.macro_eligibility_enabled": True,
            "learning.macro_eligibility_trace_mode": "normal",
            "learning.macro_eligibility_decay": 0.92,
            "learning.macro_eligibility_learning_rate_scale": 1.0,
        },
    ),
    VariantSpec(
        name="macro_eligibility_shuffled",
        group="trace_ablation",
        hypothesis="Control: eligibility trace is present but deterministically assigned to the wrong polyp.",
        overrides={
            "learning.delayed_readout_learning_rate": 0.20,
            "learning.macro_eligibility_enabled": True,
            "learning.macro_eligibility_trace_mode": "shuffled",
            "learning.macro_eligibility_decay": 0.92,
            "learning.macro_eligibility_learning_rate_scale": 1.0,
        },
    ),
    VariantSpec(
        name="macro_eligibility_zero",
        group="trace_ablation",
        hypothesis="Control: eligibility pathway is enabled but the trace contribution is zeroed.",
        overrides={
            "learning.delayed_readout_learning_rate": 0.20,
            "learning.macro_eligibility_enabled": True,
            "learning.macro_eligibility_trace_mode": "zero",
            "learning.macro_eligibility_decay": 0.92,
            "learning.macro_eligibility_learning_rate_scale": 1.0,
        },
    ),
)


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


def set_nested_attr(obj: Any, dotted: str, value: Any) -> None:
    target = obj
    parts = dotted.split(".")
    for part in parts[:-1]:
        target = getattr(target, part)
    setattr(target, parts[-1], value)


def parse_variants(raw: str) -> list[VariantSpec]:
    names = [item.strip() for item in raw.split(",") if item.strip()]
    if not names or names == ["all"]:
        return list(VARIANTS)
    by_name = {variant.name: variant for variant in VARIANTS}
    missing = [name for name in names if name not in by_name]
    if missing:
        raise argparse.ArgumentTypeError(f"unknown Tier 5.9a variants: {', '.join(missing)}")
    ordered: list[VariantSpec] = []
    for name in names:
        variant = by_name[name]
        if variant not in ordered:
            ordered.append(variant)
    if "v1_4_pending_horizon" not in {v.name for v in ordered}:
        raise argparse.ArgumentTypeError("Tier 5.9a variants must include v1_4_pending_horizon as the frozen comparator")
    if "macro_eligibility" not in {v.name for v in ordered}:
        raise argparse.ArgumentTypeError("Tier 5.9a variants must include macro_eligibility as the candidate")
    return ordered


def computed_horizon(task: TaskStream) -> int:
    due = task.feedback_due_step - np.arange(task.steps)
    if np.any(task.feedback_due_step >= 0):
        return int(max(1, np.max(due[task.feedback_due_step >= 0])))
    return 1


def variable_delay_cue_task(*, steps: int, amplitude: float, seed: int, args: argparse.Namespace) -> TaskStream:
    rng = np.random.default_rng(seed + 5901)
    min_delay = int(args.variable_min_delay)
    max_delay = int(args.variable_max_delay)
    period = int(args.variable_period)
    sensory = np.zeros(steps, dtype=float)
    current_target = np.zeros(steps, dtype=float)
    evaluation_target = np.zeros(steps, dtype=float)
    evaluation_mask = np.zeros(steps, dtype=bool)
    feedback_due = np.full(steps, -1, dtype=int)
    starts = list(range(0, steps - max_delay, period))
    delays: list[int] = []
    signs = np.asarray([1.0 if i % 2 == 0 else -1.0 for i in range(len(starts))], dtype=float)
    rng.shuffle(signs)
    for start, cue_sign in zip(starts, signs):
        delay = int(rng.integers(min_delay, max_delay + 1))
        label = -cue_sign
        sensory[start] = amplitude * cue_sign
        current_target[start + delay] = amplitude * label
        evaluation_target[start] = amplitude * label
        evaluation_mask[start] = True
        feedback_due[start] = start + delay
        delays.append(delay)
    return TaskStream(
        name="variable_delay_cue",
        display_name="Variable Delay Cue",
        domain="signed_variable_delay",
        steps=steps,
        sensory=sensory,
        current_target=current_target,
        evaluation_target=evaluation_target,
        evaluation_mask=evaluation_mask,
        feedback_due_step=feedback_due,
        switch_steps=[],
        metadata={
            "task_kind": "variable_delay_cue",
            "delay_range": [min_delay, max_delay],
            "period": period,
            "trials": len(starts),
            "mean_delay": mean(delays),
        },
    )


def aba_recurrence_task(*, steps: int, amplitude: float, seed: int, args: argparse.Namespace) -> TaskStream:
    rng = np.random.default_rng(seed + 5902)
    delay = int(args.aba_delay)
    period = int(args.aba_period)
    sensory = np.zeros(steps, dtype=float)
    current_target = np.zeros(steps, dtype=float)
    evaluation_target = np.zeros(steps, dtype=float)
    evaluation_mask = np.zeros(steps, dtype=bool)
    feedback_due = np.full(steps, -1, dtype=int)
    first_switch = max(period, steps // 3)
    second_switch = max(first_switch + period, (2 * steps) // 3)
    switch_steps = [0, first_switch, second_switch]

    def rule_at(step: int) -> float:
        if step < first_switch:
            return 1.0
        if step < second_switch:
            return -1.0
        return 1.0

    trials = 0
    for start in range(0, steps - delay, period):
        cue_sign = 1.0 if rng.random() < 0.5 else -1.0
        label = rule_at(start) * cue_sign
        sensory[start] = amplitude * cue_sign
        current_target[start + delay] = amplitude * label
        evaluation_target[start] = amplitude * label
        evaluation_mask[start] = True
        feedback_due[start] = start + delay
        trials += 1
    return TaskStream(
        name="aba_recurrence",
        display_name="A-B-A Recurrence",
        domain="aba_recurrence",
        steps=steps,
        sensory=sensory,
        current_target=current_target,
        evaluation_target=evaluation_target,
        evaluation_mask=evaluation_mask,
        feedback_due_step=feedback_due,
        switch_steps=switch_steps,
        metadata={
            "task_kind": "aba_recurrence",
            "delay": delay,
            "period": period,
            "trials": trials,
            "switch_steps": switch_steps,
            "rules": ["A: cue -> label", "B: cue -> -label", "A: recurrence"],
        },
    )


def build_tasks(args: argparse.Namespace, seed: int) -> list[TaskStream]:
    factories = {
        "delayed_cue": delayed_cue_task,
        "hard_noisy_switching": hard_noisy_switching_task,
        "variable_delay_cue": variable_delay_cue_task,
        "aba_recurrence": aba_recurrence_task,
    }
    task_names = [item.strip() for item in args.tasks.split(",") if item.strip()]
    if not task_names or task_names == ["all"]:
        task_names = list(factories)
    missing = [name for name in task_names if name not in factories]
    if missing:
        raise argparse.ArgumentTypeError(f"unknown Tier 5.9a tasks: {', '.join(missing)}")
    return [factories[name](steps=args.steps, amplitude=args.amplitude, seed=seed, args=args) for name in task_names]


def make_config(*, seed: int, task: TaskStream, variant: VariantSpec, args: argparse.Namespace) -> ReefConfig:
    cfg = ReefConfig.default()
    cfg.seed = int(seed)
    cfg.lifecycle.initial_population = int(args.cra_population_size)
    cfg.lifecycle.max_population_from_memory = False
    cfg.lifecycle.max_population_hard = int(args.cra_population_size)
    cfg.lifecycle.enable_reproduction = False
    cfg.lifecycle.enable_apoptosis = False
    cfg.lifecycle.enable_structural_plasticity = True
    cfg.measurement.stream_history_maxlen = max(task.steps + 32, 128)
    cfg.spinnaker.sync_interval_steps = 0
    cfg.spinnaker.runtime_ms_per_step = 1000.0
    cfg.learning.evaluation_horizon_bars = computed_horizon(task)
    cfg.learning.readout_learning_rate = float(args.cra_readout_lr)
    cfg.learning.delayed_readout_learning_rate = float(args.cra_delayed_readout_lr)
    if hasattr(cfg.network, "message_passing_steps"):
        cfg.network.message_passing_steps = int(args.message_passing_steps)
        cfg.network.message_context_gain = float(args.message_context_gain)
        cfg.network.message_prediction_mix = float(args.message_prediction_mix)
    for key, value in variant.overrides.items():
        set_nested_attr(cfg, key, value)
    cfg.lifecycle.max_population_from_memory = False
    if cfg.lifecycle.max_population_hard < cfg.lifecycle.initial_population:
        cfg.lifecycle.max_population_hard = cfg.lifecycle.initial_population
    return cfg


def macro_summary_from_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    def arr(key: str) -> list[float]:
        values = []
        for row in rows:
            try:
                values.append(float(row.get(key, 0.0) or 0.0))
            except (TypeError, ValueError):
                values.append(0.0)
        return values

    trace_abs = arr("macro_eligibility_trace_abs_sum")
    trace_counts = arr("macro_eligibility_trace_nonzero_count")
    matured = arr("macro_eligibility_matured_updates")
    active_steps = sum(1 for value in trace_abs if value > EPS)
    return {
        "macro_trace_abs_sum_mean": mean(trace_abs),
        "macro_trace_abs_sum_max": max(trace_abs) if trace_abs else 0.0,
        "macro_trace_nonzero_count_mean": mean(trace_counts),
        "macro_matured_updates_sum": int(round(sum(matured))),
        "macro_trace_active_steps": int(active_steps),
    }


def run_cra_variant(task: TaskStream, *, seed: int, variant: VariantSpec, args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    random.seed(seed)
    np.random.seed(seed)
    sim, backend_name = load_backend(args.backend)
    setup_backend(sim, backend_name)
    cfg = make_config(seed=seed, task=task, variant=variant, args=args)
    organism = Organism(cfg, sim, use_default_trading_bridge=(task.domain != "sensor_control"))
    adapter = SensorControlAdapter()
    rows: list[dict[str, Any]] = []
    started = time.perf_counter()
    try:
        organism.initialize(stream_keys=[task.domain])
        bridge_present_after_init = bool(organism.trading_bridge is not None)
        for step in range(task.steps):
            sensory_value = float(task.sensory[step])
            target_value = float(task.current_target[step])
            if task.domain == "sensor_control":
                observation = Observation(
                    stream_id=task.domain,
                    x=np.asarray([sensory_value], dtype=float),
                    target=target_value,
                    metadata={"task": task.name, "step": step, "tier": "5.9a"},
                )
                metrics = organism.train_adapter_step(adapter, observation, dt_seconds=args.dt_seconds)
            else:
                metrics = organism.train_step(
                    market_return_1m=target_value,
                    sensory_return_1m=sensory_value,
                    dt_seconds=args.dt_seconds,
                )
            prediction = float(metrics.colony_prediction)
            eval_sign = strict_sign(float(task.evaluation_target[step]))
            pred_sign = strict_sign(prediction)
            row = metrics.to_dict()
            row.update(
                {
                    "task": task.name,
                    "model": variant.name,
                    "model_family": "CRA",
                    "variant": variant.name,
                    "variant_group": variant.group,
                    "backend": backend_name,
                    "seed": int(seed),
                    "step": int(step),
                    "sensory_return_1m": sensory_value,
                    "target_return_1m": target_value,
                    "target_signal_horizon": float(task.evaluation_target[step]),
                    "target_signal_sign": eval_sign,
                    "target_signal_nonzero": bool(task.evaluation_mask[step] and eval_sign != 0),
                    "prediction_sign": pred_sign,
                    "strict_direction_correct": bool(task.evaluation_mask[step] and pred_sign != 0 and pred_sign == eval_sign),
                    "feedback_due_step": int(task.feedback_due_step[step]),
                    "configured_horizon_bars": int(cfg.learning.evaluation_horizon_bars),
                    "configured_readout_lr": float(cfg.learning.readout_learning_rate),
                    "configured_delayed_readout_lr": float(cfg.learning.delayed_readout_learning_rate),
                    "configured_macro_eligibility_enabled": bool(cfg.learning.macro_eligibility_enabled),
                    "configured_macro_eligibility_decay": float(cfg.learning.macro_eligibility_decay),
                    "configured_macro_eligibility_trace_mode": str(cfg.learning.macro_eligibility_trace_mode),
                    "configured_macro_eligibility_credit_mode": str(cfg.learning.macro_eligibility_credit_mode),
                    "configured_macro_eligibility_residual_scale": float(cfg.learning.macro_eligibility_residual_scale),
                    "configured_macro_eligibility_trace_clip": float(cfg.learning.macro_eligibility_trace_clip),
                    "configured_macro_eligibility_learning_rate_scale": float(cfg.learning.macro_eligibility_learning_rate_scale),
                    "configured_initial_population": int(cfg.lifecycle.initial_population),
                    "configured_max_population": int(cfg.lifecycle.max_population_hard),
                    "trading_bridge_present_after_init": bridge_present_after_init,
                    "trading_bridge_present_after_step": bool(organism.trading_bridge is not None),
                }
            )
            rows.append(row)
    finally:
        organism.shutdown()
        end_backend(sim)
    summary = summarize_rows(rows)
    summary.update(macro_summary_from_rows(rows))
    summary.update(
        {
            "task": task.name,
            "model": variant.name,
            "model_family": "CRA",
            "variant": variant.name,
            "variant_group": variant.group,
            "hypothesis": variant.hypothesis,
            "backend": backend_name,
            "seed": int(seed),
            "steps": task.steps,
            "runtime_seconds": time.perf_counter() - started,
            "configured_horizon_bars": int(cfg.learning.evaluation_horizon_bars),
            "configured_readout_lr": float(cfg.learning.readout_learning_rate),
            "configured_delayed_readout_lr": float(cfg.learning.delayed_readout_learning_rate),
            "configured_macro_eligibility_enabled": bool(cfg.learning.macro_eligibility_enabled),
            "configured_macro_eligibility_decay": float(cfg.learning.macro_eligibility_decay),
            "configured_macro_eligibility_trace_mode": str(cfg.learning.macro_eligibility_trace_mode),
            "configured_macro_eligibility_credit_mode": str(cfg.learning.macro_eligibility_credit_mode),
            "configured_macro_eligibility_residual_scale": float(cfg.learning.macro_eligibility_residual_scale),
            "configured_macro_eligibility_trace_clip": float(cfg.learning.macro_eligibility_trace_clip),
            "configured_macro_eligibility_learning_rate_scale": float(cfg.learning.macro_eligibility_learning_rate_scale),
            "configured_initial_population": int(cfg.lifecycle.initial_population),
            "configured_max_population": int(cfg.lifecycle.max_population_hard),
            "uses_trading_bridge": task.domain != "sensor_control",
            "trading_bridge_present_after_init": bool(rows[0]["trading_bridge_present_after_init"]) if rows else None,
            "trading_bridge_present_any_step": bool(any(bool(r["trading_bridge_present_after_step"]) for r in rows)),
            "task_metadata": task.metadata,
            "config_overrides": variant.overrides,
        }
    )
    return rows, summary


def aggregate_runs(
    *,
    task: TaskStream,
    model: str,
    family: str,
    summaries: list[dict[str, Any]],
    rows_by_seed: dict[int, list[dict[str, Any]]],
    tasks_by_seed: dict[int, TaskStream],
    args: argparse.Namespace,
) -> dict[str, Any]:
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
        "configured_horizon_bars",
        "configured_readout_lr",
        "configured_delayed_readout_lr",
        "configured_macro_eligibility_decay",
        "configured_macro_eligibility_residual_scale",
        "configured_macro_eligibility_trace_clip",
        "macro_trace_abs_sum_mean",
        "macro_trace_abs_sum_max",
        "macro_trace_nonzero_count_mean",
        "macro_matured_updates_sum",
        "macro_trace_active_steps",
    ]
    aggregate: dict[str, Any] = {
        "task": task.name,
        "display_name": task.display_name,
        "domain": task.domain,
        "model": model,
        "model_family": family,
        "variant_group": summaries[0].get("variant_group") if summaries else None,
        "runs": len(summaries),
        "seeds": [s.get("seed") for s in summaries],
        "steps": task.steps,
        "task_metadata": task.metadata,
    }
    for key in keys:
        vals = [s.get(key) for s in summaries]
        aggregate[f"{key}_mean"] = mean(vals)
        aggregate[f"{key}_std"] = stdev(vals)
        aggregate[f"{key}_min"] = min_value(vals)
        valid = [float(v) for v in vals if v is not None]
        aggregate[f"{key}_max"] = max(valid) if valid else None
        aggregate[f"{key}_sum"] = float(sum(valid)) if valid else None
    if any(seed_task.switch_steps for seed_task in tasks_by_seed.values()):
        per_seed_recovery = []
        for seed, rows in rows_by_seed.items():
            seed_task = tasks_by_seed.get(seed, task)
            if not seed_task.switch_steps:
                continue
            per_seed_recovery.extend(
                recovery_steps(
                    rows,
                    seed_task.switch_steps,
                    window_trials=args.recovery_window_trials,
                    threshold=args.recovery_accuracy_threshold,
                    steps=seed_task.steps,
                )
            )
        aggregate["mean_recovery_steps"] = mean(per_seed_recovery)
        aggregate["max_recovery_steps"] = max(per_seed_recovery) if per_seed_recovery else None
    else:
        aggregate["mean_recovery_steps"] = None
        aggregate["max_recovery_steps"] = None
    return aggregate


def composite_score(row: dict[str, Any]) -> float:
    tail = float(row.get("tail_accuracy_mean") or 0.0)
    corr = abs(float(row.get("prediction_target_corr_mean") or 0.0))
    recovery = row.get("mean_recovery_steps")
    recovery_bonus = 0.0 if recovery is None else -0.002 * float(recovery)
    return tail + 0.25 * corr + recovery_bonus


def build_comparisons(aggregates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    by_task_model = {(a["task"], a["model"]): a for a in aggregates}
    tasks = sorted({a["task"] for a in aggregates})
    for task in tasks:
        baseline = by_task_model.get((task, "v1_4_pending_horizon"), {})
        macro = by_task_model.get((task, "macro_eligibility"), {})
        ablations = [
            a
            for a in aggregates
            if a["task"] == task and a.get("variant_group") == "trace_ablation"
        ]
        externals = [
            a
            for a in aggregates
            if a["task"] == task and a.get("model_family") != "CRA"
        ]
        external_tail_values = [float(a.get("tail_accuracy_mean") or 0.0) for a in externals]
        external_corr_values = [abs(float(a.get("prediction_target_corr_mean") or 0.0)) for a in externals]
        best_external_tail = max(externals, key=lambda a: float(a.get("tail_accuracy_mean") or 0.0), default={})
        best_external_corr = max(externals, key=lambda a: abs(float(a.get("prediction_target_corr_mean") or 0.0)), default={})
        best_ablation = max(ablations, key=composite_score, default={})
        row = {
            "task": task,
            "baseline_tail_accuracy_mean": baseline.get("tail_accuracy_mean"),
            "macro_tail_accuracy_mean": macro.get("tail_accuracy_mean"),
            "macro_tail_delta_vs_v1_4": float(macro.get("tail_accuracy_mean") or 0.0) - float(baseline.get("tail_accuracy_mean") or 0.0),
            "baseline_abs_corr_mean": abs(float(baseline.get("prediction_target_corr_mean") or 0.0)),
            "macro_abs_corr_mean": abs(float(macro.get("prediction_target_corr_mean") or 0.0)),
            "macro_abs_corr_delta_vs_v1_4": abs(float(macro.get("prediction_target_corr_mean") or 0.0)) - abs(float(baseline.get("prediction_target_corr_mean") or 0.0)),
            "baseline_mean_recovery_steps": baseline.get("mean_recovery_steps"),
            "macro_mean_recovery_steps": macro.get("mean_recovery_steps"),
            "macro_recovery_delta_vs_v1_4": (
                None
                if baseline.get("mean_recovery_steps") is None or macro.get("mean_recovery_steps") is None
                else float(baseline["mean_recovery_steps"]) - float(macro["mean_recovery_steps"])
            ),
            "baseline_tail_accuracy_std": baseline.get("tail_accuracy_std"),
            "macro_tail_accuracy_std": macro.get("tail_accuracy_std"),
            "macro_tail_variance_reduction_vs_v1_4": float(baseline.get("tail_accuracy_std") or 0.0) - float(macro.get("tail_accuracy_std") or 0.0),
            "macro_composite_score": composite_score(macro),
            "best_ablation_model": best_ablation.get("model"),
            "best_ablation_composite_score": composite_score(best_ablation) if best_ablation else None,
            "macro_composite_delta_vs_best_ablation": None if not best_ablation else composite_score(macro) - composite_score(best_ablation),
            "external_median_tail_accuracy": float(np.median(external_tail_values)) if external_tail_values else None,
            "external_median_abs_corr": float(np.median(external_corr_values)) if external_corr_values else None,
            "best_external_tail_model": best_external_tail.get("model"),
            "best_external_tail_accuracy_mean": best_external_tail.get("tail_accuracy_mean"),
            "best_external_corr_model": best_external_corr.get("model"),
            "best_external_abs_corr_mean": abs(float(best_external_corr.get("prediction_target_corr_mean") or 0.0)) if best_external_corr else None,
            "macro_tail_delta_vs_external_median": None if not external_tail_values else float(macro.get("tail_accuracy_mean") or 0.0) - float(np.median(external_tail_values)),
            "macro_abs_corr_delta_vs_external_median": None if not external_corr_values else abs(float(macro.get("prediction_target_corr_mean") or 0.0)) - float(np.median(external_corr_values)),
            "macro_trace_active_steps_sum": macro.get("macro_trace_active_steps_sum"),
            "macro_matured_updates_sum": macro.get("macro_matured_updates_sum_sum"),
            "macro_trace_abs_sum_mean": macro.get("macro_trace_abs_sum_mean_mean"),
        }
        rows.append(row)
    return rows


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
    return {
        "checked_feedback_rows": checked,
        "feedback_due_violations": len(violations),
        "example_violations": violations[:10],
    }


def evaluate_tier(
    *,
    aggregates: list[dict[str, Any]],
    comparisons: list[dict[str, Any]],
    leakage: dict[str, Any],
    variants: list[VariantSpec],
    models: list[str],
    args: argparse.Namespace,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    tasks = [item.strip() for item in args.tasks.split(",") if item.strip()]
    if not tasks or tasks == ["all"]:
        tasks = ["delayed_cue", "hard_noisy_switching", "variable_delay_cue", "aba_recurrence"]
    seeds = seeds_from_args(args)
    expected_runs = len(tasks) * len(seeds) * (len(variants) + len(models))
    observed_runs = sum(int(a.get("runs", 0)) for a in aggregates)
    by_task = {row["task"]: row for row in comparisons}
    delayed = by_task.get("delayed_cue", {})
    hard = by_task.get("hard_noisy_switching", {})
    variable = by_task.get("variable_delay_cue", {})
    macro_trace_active = sum(float(row.get("macro_trace_active_steps_sum") or 0.0) for row in comparisons)
    macro_matured_updates = sum(float(row.get("macro_matured_updates_sum") or 0.0) for row in comparisons)
    ablation_edges = [float(row.get("macro_composite_delta_vs_best_ablation") or 0.0) for row in comparisons if row.get("best_ablation_model")]
    hard_improved = (
        float(hard.get("macro_tail_delta_vs_v1_4") or 0.0) >= args.min_hard_tail_delta
        or float(hard.get("macro_recovery_delta_vs_v1_4") or 0.0) >= args.min_hard_recovery_delta
        or float(hard.get("macro_tail_variance_reduction_vs_v1_4") or 0.0) >= args.min_hard_variance_reduction
    )
    variable_helped = (
        float(variable.get("macro_tail_delta_vs_v1_4") or 0.0) >= args.min_variable_delay_tail_delta
        or float(variable.get("macro_abs_corr_delta_vs_v1_4") or 0.0) >= args.min_variable_delay_corr_delta
        or float(variable.get("macro_composite_delta_vs_best_ablation") or 0.0) >= args.min_ablation_composite_delta
    )
    trace_ablation_hurts = bool(ablation_edges) and min(ablation_edges) >= args.min_ablation_composite_delta
    delayed_nonregression = float(delayed.get("macro_tail_delta_vs_v1_4") or 0.0) >= -abs(float(args.max_delayed_tail_regression))

    science_criteria = [
        criterion(
            "delayed_cue nonregression versus v1.4",
            delayed.get("macro_tail_delta_vs_v1_4"),
            ">=",
            -abs(float(args.max_delayed_tail_regression)),
            delayed_nonregression,
            "Macro eligibility must not damage the known delayed-cue behavior.",
        ),
        criterion(
            "hard_noisy_switching improves or reduces variance",
            {
                "tail_delta": hard.get("macro_tail_delta_vs_v1_4"),
                "recovery_delta": hard.get("macro_recovery_delta_vs_v1_4"),
                "variance_reduction": hard.get("macro_tail_variance_reduction_vs_v1_4"),
            },
            "any >=",
            {
                "tail": args.min_hard_tail_delta,
                "recovery": args.min_hard_recovery_delta,
                "variance": args.min_hard_variance_reduction,
            },
            hard_improved,
            "This is the main nonstationary/adaptive credit-assignment gate.",
        ),
        criterion(
            "variable_delay_cue shows delay-robust benefit",
            {
                "tail_delta": variable.get("macro_tail_delta_vs_v1_4"),
                "corr_delta": variable.get("macro_abs_corr_delta_vs_v1_4"),
                "ablation_delta": variable.get("macro_composite_delta_vs_best_ablation"),
            },
            "any >=",
            {
                "tail": args.min_variable_delay_tail_delta,
                "corr": args.min_variable_delay_corr_delta,
                "ablation": args.min_ablation_composite_delta,
            },
            variable_helped,
            "Macro eligibility should help as delay varies, not just match a fixed horizon.",
        ),
        criterion(
            "trace ablations are worse than normal trace",
            min(ablation_edges) if ablation_edges else None,
            ">=",
            args.min_ablation_composite_delta,
            trace_ablation_hurts,
            "Shuffled/zero controls must not explain the candidate improvement.",
        ),
    ]
    base_criteria = [
        criterion("full variant/baseline/task/seed matrix completed", observed_runs, "==", expected_runs, observed_runs == expected_runs),
        criterion("feedback timing has no leakage violations", leakage.get("feedback_due_violations"), "==", 0, int(leakage.get("feedback_due_violations", 0)) == 0),
        criterion("macro trace is active", macro_trace_active, ">", 0, macro_trace_active > 0),
        criterion("macro trace contributes to matured updates", macro_matured_updates, ">", 0, macro_matured_updates > 0),
    ]
    criteria = base_criteria if args.smoke else base_criteria + science_criteria
    summary = {
        "expected_runs": expected_runs,
        "observed_runs": observed_runs,
        "tasks": tasks,
        "seeds": seeds,
        "variants": [variant.name for variant in variants],
        "selected_baselines": models,
        "backend": args.backend,
        "steps": args.steps,
        "smoke": bool(args.smoke),
        "macro_trace_active_steps_sum": macro_trace_active,
        "macro_matured_updates_sum": macro_matured_updates,
        "leakage": leakage,
        "claim_boundary": "Diagnostic software mechanism test only; v1.4 remains the frozen architecture baseline until a candidate passes, ablates cleanly, and survives compact regression.",
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
        "tail_accuracy_std",
        "all_accuracy_mean",
        "prediction_target_corr_mean",
        "tail_prediction_target_corr_mean",
        "mean_recovery_steps",
        "runtime_seconds_mean",
        "evaluation_count_mean",
        "macro_trace_active_steps_sum",
        "macro_matured_updates_sum_sum",
        "macro_trace_abs_sum_mean_mean",
        "configured_horizon_bars_mean",
        "configured_delayed_readout_lr_mean",
        "configured_macro_eligibility_decay_mean",
        "configured_macro_eligibility_residual_scale_mean",
        "configured_macro_eligibility_trace_clip_mean",
    ]
    return [{field: row.get(field) for field in fields} for row in aggregates]


def plot_macro_comparisons(comparisons: list[dict[str, Any]], path: Path) -> None:
    if plt is None or not comparisons:
        return
    tasks = [row["task"].replace("_", "\n") for row in comparisons]
    tail = [float(row.get("macro_tail_delta_vs_v1_4") or 0.0) for row in comparisons]
    corr = [float(row.get("macro_abs_corr_delta_vs_v1_4") or 0.0) for row in comparisons]
    ablation = [float(row.get("macro_composite_delta_vs_best_ablation") or 0.0) for row in comparisons]
    x = np.arange(len(tasks))
    width = 0.25
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.axhline(0.0, color="black", lw=0.8)
    ax.bar(x - width, tail, width, label="tail delta vs v1.4", color="#1f6feb")
    ax.bar(x, corr, width, label="abs corr delta vs v1.4", color="#2f855a")
    ax.bar(x + width, ablation, width, label="composite delta vs best ablation", color="#b7791f")
    ax.set_title("Tier 5.9a Macro Eligibility Diagnostic")
    ax.set_xticks(x)
    ax.set_xticklabels(tasks)
    ax.set_ylabel("positive favors macro eligibility")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def write_report(path: Path, result: TestResult, aggregates: list[dict[str, Any]], comparisons: list[dict[str, Any]], args: argparse.Namespace, output_dir: Path) -> None:
    overall = "PASS" if result.passed else "FAIL"
    lines = [
        "# Tier 5.9a Macro Eligibility Trace Diagnostic Findings",
        "",
        f"- Generated: `{utc_now()}`",
        f"- Status: **{overall}**",
        f"- Backend: `{args.backend}`",
        f"- Steps: `{args.steps}`",
        f"- Seeds: `{', '.join(str(s) for s in seeds_from_args(args))}`",
        f"- Tasks: `{args.tasks}`",
        f"- Variants: `{args.variants}`",
        f"- Selected baselines: `{args.models}`",
        f"- Smoke mode: `{args.smoke}`",
        f"- Output directory: `{output_dir}`",
        "",
        "Tier 5.9a tests whether a host-side macro eligibility trace earns promotion beyond the frozen v1.4 PendingHorizon delayed-credit path.",
        "",
        "## Claim Boundary",
        "",
        "- This is software diagnostic evidence, not hardware evidence.",
        "- v1.4 remains the frozen architecture baseline unless macro eligibility passes this gate and then survives compact regression.",
        "- A failed run is still useful: it means the mechanism is not yet earned, not that existing CRA evidence regressed.",
        "",
        "## Task Comparisons",
        "",
        "| Task | v1.4 tail | Macro tail | Tail delta | Corr delta | Recovery delta | Best ablation | Macro-ablation delta | External median tail edge | Trace active steps | Matured updates |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in comparisons:
        lines.append(
            "| "
            f"{row['task']} | "
            f"{markdown_value(row.get('baseline_tail_accuracy_mean'))} | "
            f"{markdown_value(row.get('macro_tail_accuracy_mean'))} | "
            f"{markdown_value(row.get('macro_tail_delta_vs_v1_4'))} | "
            f"{markdown_value(row.get('macro_abs_corr_delta_vs_v1_4'))} | "
            f"{markdown_value(row.get('macro_recovery_delta_vs_v1_4'))} | "
            f"`{row.get('best_ablation_model')}` | "
            f"{markdown_value(row.get('macro_composite_delta_vs_best_ablation'))} | "
            f"{markdown_value(row.get('macro_tail_delta_vs_external_median'))} | "
            f"{markdown_value(row.get('macro_trace_active_steps_sum'))} | "
            f"{markdown_value(row.get('macro_matured_updates_sum'))} |"
        )
    lines.extend(
        [
            "",
            "## Aggregate Matrix",
            "",
            "| Task | Model | Family | Group | Tail acc | Tail std | Corr | Recovery | Runtime s | Trace active | Matured updates |",
            "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in sorted(aggregates, key=lambda r: (r["task"], r.get("model_family") != "CRA", r["model"])):
        lines.append(
            "| "
            f"{row['task']} | `{row['model']}` | {row.get('model_family')} | {row.get('variant_group') or ''} | "
            f"{markdown_value(row.get('tail_accuracy_mean'))} | "
            f"{markdown_value(row.get('tail_accuracy_std'))} | "
            f"{markdown_value(row.get('prediction_target_corr_mean'))} | "
            f"{markdown_value(row.get('mean_recovery_steps'))} | "
            f"{markdown_value(row.get('runtime_seconds_mean'))} | "
            f"{markdown_value(row.get('macro_trace_active_steps_sum'))} | "
            f"{markdown_value(row.get('macro_matured_updates_sum_sum'))} |"
        )
    lines.extend(["", "## Criteria", "", "| Criterion | Value | Rule | Pass | Note |", "| --- | --- | --- | --- | --- |"])
    for item in result.criteria:
        lines.append(
            "| "
            f"{item['name']} | "
            f"{markdown_value(item['value'])} | "
            f"{item['operator']} {markdown_value(item['threshold'])} | "
            f"{'yes' if item['passed'] else 'no'} | "
            f"{item.get('note', '')} |"
        )
    if result.failure_reason:
        lines.extend(["", f"Failure: {result.failure_reason}"])
    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            "- `tier5_9a_results.json`: machine-readable manifest.",
            "- `tier5_9a_summary.csv`: aggregate task/model metrics.",
            "- `tier5_9a_comparisons.csv`: macro-vs-v1.4/ablation/baseline comparison table.",
            "- `tier5_9a_fairness_contract.json`: predeclared comparison and leakage constraints.",
            "- `tier5_9a_macro_edges.png`: macro eligibility edge plot.",
            "- `*_timeseries.csv`: per-task/per-model/per-seed traces.",
            "",
            "## Plot",
            "",
            "![macro_edges](tier5_9a_macro_edges.png)",
            "",
        ]
    )
    if MATPLOTLIB_ERROR:
        lines.append(f"Plotting unavailable: `{MATPLOTLIB_ERROR}`")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def fairness_contract(args: argparse.Namespace, variants: list[VariantSpec], models: list[str]) -> dict[str, Any]:
    return {
        "tier": TIER,
        "frozen_comparator": "v1_4_pending_horizon",
        "candidate": "macro_eligibility",
        "ablation_controls": [v.name for v in variants if v.group == "trace_ablation"],
        "selected_external_baselines": models,
        "fairness_rules": [
            "same task stream per seed for CRA variants and selected baselines",
            "same evaluation_target, evaluation_mask, and feedback_due_step arrays",
            "models predict before consequence feedback matures",
            "feedback_due_step must be greater than or equal to the prediction step",
            "normal macro trace must beat shuffled/zero trace before promotion",
            "v1.4 remains frozen unless candidate passes and then survives compact regression",
        ],
        "tasks": args.tasks,
        "steps": args.steps,
        "seeds": seeds_from_args(args),
        "backend": args.backend,
    }


def run_tier(args: argparse.Namespace, output_dir: Path, variants: list[VariantSpec]) -> TestResult:
    models = parse_models(args.models)
    summaries_by_cell: dict[tuple[str, str], list[dict[str, Any]]] = {}
    rows_by_cell_seed: dict[tuple[str, str, int], list[dict[str, Any]]] = {}
    task_by_name: dict[str, TaskStream] = {}
    task_by_name_seed: dict[tuple[str, int], TaskStream] = {}
    artifacts: dict[str, str] = {}
    started = time.perf_counter()

    for seed in seeds_from_args(args):
        tasks = build_tasks(args, seed=args.task_seed + seed)
        for task in tasks:
            task_by_name[task.name] = task
            task_by_name_seed[(task.name, seed)] = task
            for variant in variants:
                print(f"[tier5.9a] task={task.name} variant={variant.name} seed={seed}", flush=True)
                rows, summary = run_cra_variant(task, seed=seed, variant=variant, args=args)
                csv_path = output_dir / f"{task.name}_{variant.name}_seed{seed}_timeseries.csv"
                write_csv(csv_path, rows)
                artifacts[f"{task.name}_{variant.name}_seed{seed}_timeseries_csv"] = str(csv_path)
                summaries_by_cell.setdefault((task.name, variant.name), []).append(summary)
                rows_by_cell_seed[(task.name, variant.name, seed)] = rows
            for model in models:
                print(f"[tier5.9a] task={task.name} baseline={model} seed={seed}", flush=True)
                rows, summary = run_baseline_case(task, model, seed=seed, args=args)
                csv_path = output_dir / f"{task.name}_{model}_seed{seed}_timeseries.csv"
                write_csv(csv_path, rows)
                artifacts[f"{task.name}_{model}_seed{seed}_timeseries_csv"] = str(csv_path)
                summaries_by_cell.setdefault((task.name, model), []).append(summary)
                rows_by_cell_seed[(task.name, model, seed)] = rows

    variant_by_name = {variant.name: variant for variant in variants}
    aggregates: list[dict[str, Any]] = []
    for (task_name, model), summaries in sorted(summaries_by_cell.items()):
        task = task_by_name[task_name]
        seed_rows = {
            int(summary["seed"]): rows_by_cell_seed[(task_name, model, int(summary["seed"]))]
            for summary in summaries
        }
        seed_tasks = {
            int(summary["seed"]): task_by_name_seed[(task_name, int(summary["seed"]))]
            for summary in summaries
        }
        if model in variant_by_name:
            family = "CRA"
        else:
            family = LEARNER_FACTORIES[model].family
        aggregates.append(
            aggregate_runs(
                task=task,
                model=model,
                family=family,
                summaries=summaries,
                rows_by_seed=seed_rows,
                tasks_by_seed=seed_tasks,
                args=args,
            )
        )

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

    summary_csv = output_dir / "tier5_9a_summary.csv"
    comparison_csv = output_dir / "tier5_9a_comparisons.csv"
    fairness_json = output_dir / "tier5_9a_fairness_contract.json"
    plot_path = output_dir / "tier5_9a_macro_edges.png"
    write_csv(summary_csv, aggregate_csv_rows(aggregates))
    write_csv(comparison_csv, comparisons)
    write_json(fairness_json, fairness_contract(args, variants, models))
    plot_macro_comparisons(comparisons, plot_path)

    result_artifacts = {
        "summary_csv": str(summary_csv),
        "comparisons_csv": str(comparison_csv),
        "fairness_contract_json": str(fairness_json),
        "macro_edges_png": str(plot_path) if plot_path.exists() else "",
    }
    result_artifacts.update(artifacts)
    return TestResult(
        name="macro_eligibility_trace_diagnostic",
        status=status,
        summary={
            "tier_summary": tier_summary,
            "aggregates": aggregates,
            "comparisons": comparisons,
            "fairness_contract": fairness_contract(args, variants, models),
            "runtime_seconds": time.perf_counter() - started,
        },
        criteria=criteria,
        artifacts=result_artifacts,
        failure_reason=failure_reason,
    )


def write_latest(output_dir: Path, report_path: Path, manifest_path: Path, summary_csv: Path, status: str) -> None:
    latest_path = ROOT / "controlled_test_output" / "tier5_9a_latest_manifest.json"
    payload = {
        "generated_at_utc": utc_now(),
        "tier": TIER,
        "status": status,
        "output_dir": str(output_dir),
        "manifest": str(manifest_path),
        "report": str(report_path),
        "summary_csv": str(summary_csv),
        "canonical": False,
        "claim": "Latest Tier 5.9a macro-eligibility diagnostic; promote only if the mechanism passes, ablates, and survives compact regression.",
    }
    write_json(latest_path, payload)


def build_parser() -> argparse.ArgumentParser:
    parser = build_tier5_1_parser()
    parser.description = "Run Tier 5.9a macro-eligibility trace diagnostics."
    parser.set_defaults(
        backend="nest",
        tasks=DEFAULT_TASKS,
        steps=960,
        seed_count=3,
        models=DEFAULT_MODELS,
        cra_population_size=8,
        cra_readout_lr=0.10,
        cra_delayed_readout_lr=0.20,
    )
    parser.add_argument("--variants", default=DEFAULT_VARIANTS, help="all or comma-separated Tier 5.9a CRA variant names")
    parser.add_argument("--variable-min-delay", type=int, default=2)
    parser.add_argument("--variable-max-delay", type=int, default=10)
    parser.add_argument("--variable-period", type=int, default=8)
    parser.add_argument("--aba-delay", type=int, default=5)
    parser.add_argument("--aba-period", type=int, default=8)
    parser.add_argument("--message-passing-steps", type=int, default=1)
    parser.add_argument("--message-context-gain", type=float, default=0.015)
    parser.add_argument("--message-prediction-mix", type=float, default=0.25)
    parser.add_argument("--max-delayed-tail-regression", type=float, default=0.02)
    parser.add_argument("--min-hard-tail-delta", type=float, default=0.01)
    parser.add_argument("--min-hard-recovery-delta", type=float, default=1.0)
    parser.add_argument("--min-hard-variance-reduction", type=float, default=0.01)
    parser.add_argument("--min-variable-delay-tail-delta", type=float, default=0.01)
    parser.add_argument("--min-variable-delay-corr-delta", type=float, default=0.01)
    parser.add_argument("--min-ablation-composite-delta", type=float, default=0.01)
    parser.add_argument("--smoke", action="store_true", help="Run harness integrity gates only; scientific promotion gates are skipped.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    variants = parse_variants(args.variants)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = args.output_dir or (ROOT / "controlled_test_output" / f"tier5_9a_{timestamp}")
    output_dir.mkdir(parents=True, exist_ok=True)

    result = run_tier(args, output_dir, variants)
    manifest_path = output_dir / "tier5_9a_results.json"
    report_path = output_dir / "tier5_9a_report.md"
    summary_csv = output_dir / "tier5_9a_summary.csv"
    comparison_csv = output_dir / "tier5_9a_comparisons.csv"
    fairness_json = output_dir / "tier5_9a_fairness_contract.json"
    manifest = {
        "tier": TIER,
        "generated_at_utc": utc_now(),
        "output_dir": str(output_dir),
        "command": " ".join(sys.argv),
        "backend": args.backend,
        "status": result.status,
        "result": result.to_dict(),
        "summary": {
            **result.summary["tier_summary"],
            "runtime_seconds": result.summary["runtime_seconds"],
            "comparisons": result.summary["comparisons"],
        },
        "artifacts": {
            "summary_csv": str(summary_csv),
            "comparisons_csv": str(comparison_csv),
            "fairness_contract_json": str(fairness_json),
            "report_md": str(report_path),
            "macro_edges_png": str(output_dir / "tier5_9a_macro_edges.png"),
        },
    }
    write_json(manifest_path, json_safe(manifest))
    write_report(report_path, result, result.summary["aggregates"], result.summary["comparisons"], args, output_dir)
    write_latest(output_dir, report_path, manifest_path, summary_csv, result.status)
    print(
        json.dumps(
            {
                "status": result.status,
                "output_dir": str(output_dir),
                "manifest": str(manifest_path),
                "report": str(report_path),
                "summary_csv": str(summary_csv),
                "comparisons_csv": str(comparison_csv),
                "fairness_contract_json": str(fairness_json),
                "failure_reason": result.failure_reason,
            },
            indent=2,
        )
    )
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
