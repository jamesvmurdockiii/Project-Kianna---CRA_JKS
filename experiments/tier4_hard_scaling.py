#!/usr/bin/env python3
"""Run Tier 4.10b hard population-scaling tests for the CRA organism.

This test follows the baseline population-scaling test, but makes the task
hard enough that scaling has something to prove:

- noisy delayed cue/reward trials
- rule switches every 30-50 steps
- fixed population sizes N=4,8,16,32,64
- ecology/energy remains active, while births/deaths are disabled to control N
- seeded founder diversity creates a portfolio of fast/slow local learners

Pass criteria are deliberately broad: larger N can show value via accuracy,
correlation, recovery, or lower seed variance. Huge accuracy gains are not
required.
"""

from __future__ import annotations

import argparse
import math
import random
import sys
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

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

from coral_reef_spinnaker import Organism, ReefConfig
from tier2_learning import (
    DEFAULT_AMPLITUDE,
    DEFAULT_DT_SECONDS,
    criterion,
    load_backend,
    markdown_value,
    pass_fail,
    setup_backend,
    strict_sign,
    summarize_rows,
    write_csv,
    write_json,
    utc_now,
    end_backend,
)
from tier4_scaling import (
    TestResult,
    aggregate_rows_by_step,
    alive_readout_weights,
    alive_trophic_health,
    max_value,
    mean,
    min_value,
    parse_population_sizes,
    rolling_mean,
    seeds_from_args,
    stdev,
)


def hard_delayed_switch_task(
    *,
    steps: int,
    amplitude: float,
    seed: int,
    noise_prob: float,
    min_delay: int,
    max_delay: int,
    min_switch_interval: int,
    max_switch_interval: int,
    trial_period: int,
    sensory_noise_fraction: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[int], dict[str, Any]]:
    """Create a noisy delayed-reward switch task.

    A cue appears every ``trial_period`` steps. Its reward arrives 3-5 steps
    later by default. The cue/outcome rule flips at irregular intervals, and
    ``noise_prob`` flips a subset of outcomes.
    """
    if trial_period <= max_delay:
        raise ValueError("trial_period must exceed max_delay to avoid reward/cue overlap")

    rng = np.random.default_rng(seed)
    sensory = np.zeros(steps, dtype=float)
    target = np.zeros(steps, dtype=float)
    evaluation_target = np.zeros(steps, dtype=float)
    evaluation_mask = np.zeros(steps, dtype=bool)

    switch_steps = [0]
    cursor = 0
    while cursor < steps:
        cursor += int(rng.integers(min_switch_interval, max_switch_interval + 1))
        if cursor < steps:
            switch_steps.append(cursor)

    initial_rule = 1.0 if rng.random() < 0.5 else -1.0

    def rule_at(step: int) -> float:
        idx = int(np.searchsorted(switch_steps, step, side="right") - 1)
        return initial_rule * (1.0 if idx % 2 == 0 else -1.0)

    trials = 0
    noisy_trials = 0
    delays: list[int] = []
    for start in range(0, steps - max_delay, trial_period):
        cue_sign = 1.0 if rng.random() < 0.5 else -1.0
        delay = int(rng.integers(min_delay, max_delay + 1))
        outcome_sign = rule_at(start) * cue_sign
        if rng.random() < noise_prob:
            outcome_sign *= -1.0
            noisy_trials += 1

        sensory_noise = rng.normal(0.0, sensory_noise_fraction * amplitude)
        sensory[start] = amplitude * cue_sign + sensory_noise
        target[start + delay] = amplitude * outcome_sign
        evaluation_target[start] = amplitude * outcome_sign
        evaluation_mask[start] = True
        trials += 1
        delays.append(delay)

    metadata = {
        "trials": trials,
        "noisy_trials": noisy_trials,
        "noise_rate_actual": 0.0 if trials == 0 else noisy_trials / trials,
        "mean_delay": float(np.mean(delays)) if delays else None,
        "min_delay": min_delay,
        "max_delay": max_delay,
        "trial_period": trial_period,
        "switch_steps": switch_steps,
    }
    return sensory, target, evaluation_target, evaluation_mask, switch_steps, metadata


def make_config(
    *,
    seed: int,
    steps: int,
    population_size: int,
    horizon: int,
    args: argparse.Namespace,
) -> ReefConfig:
    cfg = ReefConfig.default()
    cfg.seed = int(seed)
    cfg.lifecycle.initial_population = int(population_size)
    cfg.lifecycle.max_population_from_memory = False
    cfg.lifecycle.max_population_hard = int(population_size)
    cfg.lifecycle.enable_reproduction = False
    cfg.lifecycle.enable_apoptosis = False
    cfg.lifecycle.enable_structural_plasticity = True
    cfg.measurement.stream_history_maxlen = max(steps + 16, 128)
    cfg.spinnaker.sync_interval_steps = 0
    cfg.spinnaker.runtime_ms_per_step = 1000.0
    cfg.learning.evaluation_horizon_bars = int(horizon)
    cfg.learning.readout_learning_rate = float(args.readout_lr)
    cfg.learning.delayed_readout_learning_rate = float(args.delayed_readout_lr)
    return cfg


def apply_founder_diversity(
    organism: Organism,
    *,
    seed: int,
    weight_span: float,
    lr_min: float,
    lr_max: float,
    bias_std: float,
) -> None:
    """Seed a deterministic portfolio of specialists for fixed-N scaling."""
    if organism.polyp_population is None:
        return
    states = [p for p in organism.polyp_population.states if getattr(p, "is_alive", False)]
    if not states:
        return
    rng = np.random.default_rng(seed + 17_029)
    weights = np.linspace(-weight_span, weight_span, len(states), dtype=float)
    rng.shuffle(weights)
    lr_scales = np.geomspace(lr_min, lr_max, len(states), dtype=float)
    rng.shuffle(lr_scales)
    for polyp, weight, lr_scale in zip(states, weights, lr_scales):
        polyp.predictive_readout_weight = float(weight)
        polyp.predictive_readout_bias = float(rng.normal(0.0, bias_std))
        polyp.predictive_readout_lr_scale = float(lr_scale)
        polyp.directional_accuracy_ema = float(np.clip(rng.normal(0.5, 0.03), 0.35, 0.65))


def recovery_steps_for_switches(
    rows: list[dict[str, Any]],
    switch_steps: list[int],
    *,
    window_trials: int,
    threshold: float,
    steps: int,
) -> list[int]:
    cue_rows = [
        r
        for r in rows
        if bool(r.get("target_signal_nonzero", False))
        and int(r.get("target_signal_sign", 0)) != 0
    ]
    recoveries: list[int] = []
    for switch_step in switch_steps[1:]:
        after = [r for r in cue_rows if int(r["step"]) >= switch_step]
        recovered: int | None = None
        for idx in range(0, max(0, len(after) - window_trials + 1)):
            window = after[idx : idx + window_trials]
            acc = float(np.mean([bool(r["strict_direction_correct"]) for r in window]))
            if acc >= threshold:
                recovered = int(window[0]["step"]) - int(switch_step)
                break
        if recovered is None:
            recovered = int(steps - switch_step)
        recoveries.append(max(0, recovered))
    return recoveries


def run_hard_case(
    *,
    population_size: int,
    seed: int,
    args: argparse.Namespace,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    random.seed(seed)
    np.random.seed(seed)
    task = hard_delayed_switch_task(
        steps=args.steps,
        amplitude=args.amplitude,
        seed=args.task_seed + seed,
        noise_prob=args.noise_prob,
        min_delay=args.min_delay,
        max_delay=args.max_delay,
        min_switch_interval=args.min_switch_interval,
        max_switch_interval=args.max_switch_interval,
        trial_period=args.trial_period,
        sensory_noise_fraction=args.sensory_noise_fraction,
    )
    sensory, target, evaluation_target, evaluation_mask, switch_steps, task_metadata = task

    sim, backend_name = load_backend(args.backend)
    setup_backend(sim, backend_name)
    cfg = make_config(
        seed=seed,
        steps=args.steps,
        population_size=population_size,
        horizon=args.max_delay,
        args=args,
    )
    organism = Organism(cfg, sim)
    rows: list[dict[str, Any]] = []
    task_window: deque[float] = deque(maxlen=args.max_delay)
    started = time.perf_counter()

    try:
        organism.initialize(stream_keys=["controlled"])
        apply_founder_diversity(
            organism,
            seed=seed,
            weight_span=args.initial_weight_span,
            lr_min=args.lr_scale_min,
            lr_max=args.lr_scale_max,
            bias_std=args.initial_bias_std,
        )
        for step, (sensory_value, target_value, eval_value, eval_enabled) in enumerate(
            zip(sensory, target, evaluation_target, evaluation_mask)
        ):
            task_window.append(float(target_value))
            task_signal = float(np.sum(list(task_window)))
            metrics = organism.train_step(
                market_return_1m=float(target_value),
                dt_seconds=args.dt_seconds,
                sensory_return_1m=float(sensory_value),
            )

            prediction = float(metrics.colony_prediction)
            eval_sign = strict_sign(float(eval_value))
            pred_sign = strict_sign(prediction)
            weights = alive_readout_weights(organism)
            trophic = alive_trophic_health(organism)
            learning_status = (
                organism.learning_manager.get_summary()
                if organism.learning_manager is not None
                else {}
            )
            row = metrics.to_dict()
            row.update(
                {
                    "test_name": "hard_population_scaling",
                    "population_size": int(population_size),
                    "backend": backend_name,
                    "seed": int(seed),
                    "step": int(step),
                    "sensory_return_1m": float(sensory_value),
                    "target_return_1m": float(target_value),
                    "task_signal_horizon": task_signal,
                    "target_signal_horizon": float(eval_value),
                    "target_signal_sign": eval_sign,
                    "target_signal_nonzero": bool(eval_enabled and eval_sign != 0),
                    "prediction_sign": pred_sign,
                    "strict_direction_correct": bool(
                        eval_enabled and pred_sign != 0 and pred_sign == eval_sign
                    ),
                    "mean_readout_weight": float(np.mean(weights)) if weights else 0.0,
                    "min_readout_weight": float(np.min(weights)) if weights else 0.0,
                    "max_readout_weight": float(np.max(weights)) if weights else 0.0,
                    "mean_abs_readout_weight": float(np.mean(np.abs(weights)))
                    if weights
                    else 0.0,
                    "mean_trophic_health": float(np.mean(trophic)) if trophic else 0.0,
                    "min_trophic_health": float(np.min(trophic)) if trophic else 0.0,
                    "max_trophic_health": float(np.max(trophic)) if trophic else 0.0,
                    "pending_horizons": int(learning_status.get("pending_horizons", 0)),
                    "matured_horizons": int(learning_status.get("matured_horizons", 0)),
                }
            )
            rows.append(row)
    finally:
        organism.shutdown()
        end_backend(sim)

    summary = summarize_rows(rows)
    recoveries = recovery_steps_for_switches(
        rows,
        switch_steps,
        window_trials=args.recovery_window_trials,
        threshold=args.recovery_accuracy_threshold,
        steps=args.steps,
    )
    summary.update(
        {
            "backend": backend_name,
            "seed": int(seed),
            "steps": int(args.steps),
            "population_size": int(population_size),
            "runtime_seconds": time.perf_counter() - started,
            "mean_recovery_steps": mean(recoveries),
            "max_recovery_steps": max(recoveries) if recoveries else 0,
            "recovery_steps_by_switch": recoveries,
            "switch_steps": switch_steps,
            "task_metadata": task_metadata,
            "config": cfg.to_dict(),
        }
    )
    return rows, summary


def aggregate_population(population_size: int, summaries: list[dict[str, Any]]) -> dict[str, Any]:
    keys = [
        "tail_accuracy",
        "all_accuracy",
        "early_accuracy",
        "accuracy_improvement",
        "prediction_target_corr",
        "tail_prediction_target_corr",
        "max_abs_dopamine",
        "mean_abs_dopamine",
        "final_accuracy_ema",
        "tail_accuracy_ema",
        "final_n_alive",
        "max_n_alive",
        "total_births",
        "total_deaths",
        "final_mean_readout_weight",
        "final_mean_abs_readout_weight",
        "runtime_seconds",
        "mean_recovery_steps",
        "max_recovery_steps",
    ]
    agg: dict[str, Any] = {
        "population_size": int(population_size),
        "runs": len(summaries),
        "seeds": [s["seed"] for s in summaries],
    }
    for key in keys:
        values = [s.get(key) for s in summaries]
        agg[f"{key}_mean"] = mean(values)
        agg[f"{key}_std"] = stdev(values)
        agg[f"{key}_min"] = min_value(values)
        agg[f"{key}_max"] = max_value(values)
    agg["total_births_sum"] = int(sum(int(s.get("total_births", 0)) for s in summaries))
    agg["total_deaths_sum"] = int(sum(int(s.get("total_deaths", 0)) for s in summaries))
    return agg


def plot_hard_scaling_summary(aggregates: list[dict[str, Any]], output_path: Path) -> None:
    if plt is None:
        return
    sizes = np.asarray([int(a["population_size"]) for a in aggregates], dtype=float)
    all_acc = np.asarray([float(a["all_accuracy_mean"]) for a in aggregates], dtype=float)
    tail_acc = np.asarray([float(a["tail_accuracy_mean"]) for a in aggregates], dtype=float)
    corr = np.asarray([float(a["prediction_target_corr_mean"]) for a in aggregates], dtype=float)
    recovery = np.asarray([float(a["mean_recovery_steps_mean"]) for a in aggregates], dtype=float)
    variance = np.asarray([float(a["all_accuracy_std"]) for a in aggregates], dtype=float)
    runtime = np.asarray([float(a["runtime_seconds_mean"]) for a in aggregates], dtype=float)

    fig, axes = plt.subplots(2, 3, figsize=(15, 8))
    fig.suptitle("Tier 4.10b Hard Population Scaling", fontsize=14, fontweight="bold")
    panels = [
        (axes[0, 0], all_acc, "overall accuracy", "#1f6feb"),
        (axes[0, 1], tail_acc, "tail accuracy", "#2f855a"),
        (axes[0, 2], corr, "prediction/target corr", "#8250df"),
        (axes[1, 0], recovery, "mean recovery steps", "#d1242f"),
        (axes[1, 1], variance, "accuracy std across seeds", "#9a6700"),
        (axes[1, 2], runtime, "runtime seconds", "#57606a"),
    ]
    for ax, values, ylabel, color in panels:
        ax.plot(sizes, values, marker="o", color=color)
        ax.set_xscale("log", base=2)
        ax.set_xticks(sizes)
        ax.set_xticklabels([str(int(s)) for s in sizes])
        ax.set_xlabel("population size")
        ax.set_ylabel(ylabel)
        ax.grid(alpha=0.25)
    axes[0, 0].set_ylim(-0.05, 1.05)
    axes[0, 1].set_ylim(-0.05, 1.05)
    axes[0, 2].set_ylim(-1.05, 1.05)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def plot_hard_scaling_timeseries(
    grouped_rows: dict[int, list[dict[str, Any]]],
    output_path: Path,
    switch_steps: list[int],
) -> None:
    if plt is None:
        return
    colors = plt.cm.plasma(np.linspace(0.1, 0.9, max(1, len(grouped_rows))))
    fig, axes = plt.subplots(4, 1, figsize=(12, 11), sharex=True)
    fig.suptitle("Tier 4.10b Hard Scaling Time Series", fontsize=14, fontweight="bold")
    target_plotted = False
    for (size, rows), color in zip(sorted(grouped_rows.items()), colors):
        agg = aggregate_rows_by_step(rows)
        if not agg:
            continue
        steps = agg["step"]
        correct = np.nan_to_num(agg["correct"], nan=0.0)
        axes[0].plot(steps, rolling_mean(correct, 9), label=f"N={size}", color=color, lw=1.2)
        axes[1].plot(steps, agg["colony_prediction"], label=f"N={size}", color=color, lw=1.0)
        if not target_plotted:
            axes[1].plot(steps, agg["target_signal_horizon"], label="eval target", color="#57606a", lw=1.0, alpha=0.75)
            target_plotted = True
        axes[2].plot(steps, agg["mean_readout_weight"], label=f"N={size}", color=color, lw=1.0)
        axes[3].plot(steps, agg["n_alive"], label=f"N={size}", color=color, lw=1.0)
    for ax in axes:
        for switch_step in switch_steps[1:]:
            ax.axvline(switch_step, color="#d29922", lw=0.7, linestyle="--", alpha=0.45)
        ax.axhline(0.0, color="black", lw=0.7, alpha=0.35)
        ax.grid(alpha=0.25)
        ax.legend(loc="upper right", ncol=2)
    axes[0].set_ylabel("rolling cue accuracy")
    axes[0].set_ylim(-0.05, 1.05)
    axes[1].set_ylabel("prediction")
    axes[2].set_ylabel("readout weight")
    axes[3].set_ylabel("alive polyps")
    axes[3].set_xlabel("step")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def run_hard_population_scaling(args: argparse.Namespace, output_dir: Path) -> TestResult:
    grouped_rows: dict[int, list[dict[str, Any]]] = {}
    size_results: list[dict[str, Any]] = []
    first_switch_steps: list[int] = []
    for size in args.population_sizes:
        rows_all: list[dict[str, Any]] = []
        summaries: list[dict[str, Any]] = []
        artifacts: dict[str, str] = {}
        for seed in seeds_from_args(args):
            print(f"[tier4.10b] hard_population_scaling/N={size}: seed {seed}...", flush=True)
            rows, summary = run_hard_case(population_size=size, seed=seed, args=args)
            csv_path = output_dir / f"hard_population_scaling_N{size}_seed{seed}_timeseries.csv"
            write_csv(csv_path, rows)
            artifacts[f"seed_{seed}_timeseries_csv"] = str(csv_path)
            rows_all.extend(rows)
            summaries.append(summary)
            if not first_switch_steps:
                first_switch_steps = list(summary["switch_steps"])
        grouped_rows[size] = rows_all
        size_results.append(
            {
                "population_size": int(size),
                "summaries": summaries,
                "aggregate": aggregate_population(size, summaries),
                "artifacts": artifacts,
            }
        )

    aggregates = [entry["aggregate"] for entry in size_results]
    smallest = aggregates[0]
    largest = aggregates[-1]
    larger = aggregates[1:] if len(aggregates) > 1 else aggregates

    best_accuracy = max(float(a["all_accuracy_mean"]) for a in larger)
    best_corr = max(float(a["prediction_target_corr_mean"]) for a in larger)
    best_recovery = min(float(a["mean_recovery_steps_mean"]) for a in larger)
    best_variance = min(float(a["all_accuracy_std"]) for a in larger)

    accuracy_delta = best_accuracy - float(smallest["all_accuracy_mean"])
    corr_delta = best_corr - float(smallest["prediction_target_corr_mean"])
    recovery_delta = float(smallest["mean_recovery_steps_mean"]) - best_recovery
    variance_delta = float(smallest["all_accuracy_std"]) - best_variance
    large_vs_small_accuracy = float(largest["all_accuracy_mean"]) - float(smallest["all_accuracy_mean"])

    scaling_value_passed = (
        accuracy_delta >= args.scaling_accuracy_delta
        or corr_delta >= args.scaling_corr_delta
        or recovery_delta >= args.scaling_recovery_delta
        or variance_delta >= args.scaling_variance_delta
    )

    summary_plot = output_dir / "hard_population_scaling_summary.png"
    timeseries_plot = output_dir / "hard_population_scaling_timeseries.png"
    plot_hard_scaling_summary(aggregates, summary_plot)
    plot_hard_scaling_timeseries(grouped_rows, timeseries_plot, first_switch_steps)

    final_alive_matches = all(
        int(round(float(a["final_n_alive_mean"]))) == int(a["population_size"])
        for a in aggregates
    )
    no_births_or_deaths = all(
        int(a["total_births_sum"]) == 0 and int(a["total_deaths_sum"]) == 0
        for a in aggregates
    )
    min_all_accuracy = min(float(a["all_accuracy_mean"]) for a in aggregates)

    criteria = [
        criterion("no extinction/collapse", final_alive_matches, "==", True, final_alive_matches),
        criterion("fixed population has no births/deaths", no_births_or_deaths, "==", True, no_births_or_deaths),
        criterion(
            "all sizes above random overall accuracy",
            min_all_accuracy,
            ">=",
            args.min_all_accuracy,
            min_all_accuracy >= args.min_all_accuracy,
        ),
        criterion(
            "larger N does not degrade sharply",
            large_vs_small_accuracy,
            ">=",
            -args.large_population_degradation_tolerance,
            large_vs_small_accuracy >= -args.large_population_degradation_tolerance,
        ),
        criterion(
            "larger N shows some scaling value",
            {
                "accuracy_delta": accuracy_delta,
                "corr_delta": corr_delta,
                "recovery_delta": recovery_delta,
                "variance_delta": variance_delta,
            },
            "any >=",
            {
                "accuracy": args.scaling_accuracy_delta,
                "corr": args.scaling_corr_delta,
                "recovery": args.scaling_recovery_delta,
                "variance": args.scaling_variance_delta,
            },
            scaling_value_passed,
            "Scaling value may appear as accuracy, correlation, recovery, or lower seed variance.",
        ),
    ]
    status, failure_reason = pass_fail(criteria)
    return TestResult(
        name="hard_population_scaling",
        status=status,
        summary={
            "population_sizes": [int(s) for s in args.population_sizes],
            "seeds": seeds_from_args(args),
            "aggregates": aggregates,
            "scaling_value": {
                "accuracy_delta": accuracy_delta,
                "corr_delta": corr_delta,
                "recovery_delta": recovery_delta,
                "variance_delta": variance_delta,
                "large_vs_small_accuracy": large_vs_small_accuracy,
            },
            "task": {
                "noise_prob": args.noise_prob,
                "delay_range": [args.min_delay, args.max_delay],
                "switch_interval_range": [args.min_switch_interval, args.max_switch_interval],
                "trial_period": args.trial_period,
                "sensory_noise_fraction": args.sensory_noise_fraction,
            },
        },
        criteria=criteria,
        artifacts={
            "summary_plot_png": str(summary_plot) if summary_plot.exists() else "",
            "timeseries_plot_png": str(timeseries_plot) if timeseries_plot.exists() else "",
        },
        failure_reason=failure_reason,
    )


def summary_rows(result: TestResult) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for agg in result.summary["aggregates"]:
        rows.append(
            {
                "test_name": result.name,
                "status": result.status,
                "population_size": agg["population_size"],
                "runs": agg["runs"],
                "all_accuracy_mean": agg["all_accuracy_mean"],
                "all_accuracy_std": agg["all_accuracy_std"],
                "tail_accuracy_mean": agg["tail_accuracy_mean"],
                "prediction_target_corr_mean": agg["prediction_target_corr_mean"],
                "tail_prediction_target_corr_mean": agg["tail_prediction_target_corr_mean"],
                "mean_recovery_steps_mean": agg["mean_recovery_steps_mean"],
                "max_recovery_steps_mean": agg["max_recovery_steps_mean"],
                "final_n_alive_mean": agg["final_n_alive_mean"],
                "total_births_sum": agg["total_births_sum"],
                "total_deaths_sum": agg["total_deaths_sum"],
                "runtime_seconds_mean": agg["runtime_seconds_mean"],
                "runtime_seconds_max": agg["runtime_seconds_max"],
            }
        )
    return rows


def write_report(
    *,
    path: Path,
    result: TestResult,
    manifest_path: Path,
    summary_csv_path: Path,
    output_dir: Path,
    args: argparse.Namespace,
) -> None:
    overall = "PASS" if result.passed else "FAIL"
    lines = [
        "# Tier 4.10b Hard Population Scaling Findings",
        "",
        f"- Generated: `{utc_now()}`",
        f"- Backend: `{args.backend}`",
        f"- Overall status: **{overall}**",
        f"- Population sizes: `{', '.join(str(s) for s in args.population_sizes)}`",
        f"- Seeds: `{', '.join(str(s) for s in seeds_from_args(args))}`",
        f"- Steps per run: `{args.steps}`",
        f"- Noise probability: `{args.noise_prob}`",
        f"- Delay range: `{args.min_delay}-{args.max_delay}`",
        f"- Switch interval range: `{args.min_switch_interval}-{args.max_switch_interval}`",
        f"- Output directory: `{output_dir}`",
        "",
        "Tier 4.10b asks whether larger fixed populations add value when the task is harder: delayed rewards, irregular switches, and noisy outcomes. Births/deaths are disabled to control N, but trophic/energy dynamics still run.",
        "",
        "## Evidence Trail Position",
        "",
        "The original validation plan has 12 numbered core tests. Tier 4.10b is an added addendum after core test 10, bringing the expanded tracked evidence suite to 13 entries: tests 1-10, 10b, 11, and 12.",
        "",
        "## Artifact Index",
        "",
        f"- JSON manifest: `{manifest_path.name}`",
        f"- Summary CSV: `{summary_csv_path.name}`",
    ]
    if MATPLOTLIB_ERROR:
        lines.append(f"- Plotting unavailable: `{MATPLOTLIB_ERROR}`")
    for label, artifact in result.artifacts.items():
        if artifact:
            lines.append(f"- `{label}`: `{Path(artifact).name}`")

    lines.extend(
        [
            "",
            "## Summary",
            "",
            "| N | Overall acc | Acc std | Tail acc | Corr | Recovery steps | Runtime s |",
            "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for agg in result.summary["aggregates"]:
        lines.append(
            "| "
            f"{agg['population_size']} | "
            f"{markdown_value(agg['all_accuracy_mean'])} | "
            f"{markdown_value(agg['all_accuracy_std'])} | "
            f"{markdown_value(agg['tail_accuracy_mean'])} | "
            f"{markdown_value(agg['prediction_target_corr_mean'])} | "
            f"{markdown_value(agg['mean_recovery_steps_mean'])} | "
            f"{markdown_value(agg['runtime_seconds_mean'])} |"
        )

    sv = result.summary["scaling_value"]
    lines.extend(
        [
            "",
            "## Scaling Value",
            "",
            f"- Best larger-N accuracy delta vs N=4: `{markdown_value(sv['accuracy_delta'])}`",
            f"- Best larger-N correlation delta vs N=4: `{markdown_value(sv['corr_delta'])}`",
            f"- Best larger-N recovery improvement vs N=4: `{markdown_value(sv['recovery_delta'])}` steps",
            f"- Best larger-N variance reduction vs N=4: `{markdown_value(sv['variance_delta'])}`",
            f"- N=64 overall accuracy delta vs N=4: `{markdown_value(sv['large_vs_small_accuracy'])}`",
            "",
            "Interpretation: a hard-scaling pass does not require a large raw-accuracy jump. Scaling value can appear as better prediction/target correlation, faster recovery after switches, or lower seed-to-seed variance.",
            "",
            "## Criteria",
            "",
            "| Criterion | Value | Rule | Pass |",
            "| --- | --- | --- | --- |",
        ]
    )
    for item in result.criteria:
        lines.append(
            "| "
            f"{item['name']} | "
            f"{markdown_value(item['value'])} | "
            f"{item['operator']} {markdown_value(item['threshold'])} | "
            f"{'yes' if item['passed'] else 'no'} |"
        )

    lines.extend(["", "## Plots", ""])
    for label, artifact in result.artifacts.items():
        if artifact:
            lines.append(f"![{label}]({Path(artifact).name})")
            lines.append("")
    if result.failure_reason:
        lines.extend(["", "## Failure", "", result.failure_reason, ""])
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run Tier 4.10b hard CRA population-scaling tests.",
    )
    parser.add_argument("--backend", choices=["nest", "brian2", "mock"], default="nest")
    parser.add_argument("--population-sizes", nargs="+", default=["4,8,16,32,64"])
    parser.add_argument("--steps", type=int, default=280)
    parser.add_argument("--base-seed", type=int, default=42)
    parser.add_argument("--seed-count", type=int, default=3)
    parser.add_argument("--task-seed", type=int, default=9001)
    parser.add_argument("--amplitude", type=float, default=DEFAULT_AMPLITUDE)
    parser.add_argument("--dt-seconds", type=float, default=DEFAULT_DT_SECONDS)
    parser.add_argument("--readout-lr", type=float, default=0.10)
    parser.add_argument("--delayed-readout-lr", type=float, default=0.05)
    parser.add_argument("--noise-prob", type=float, default=0.15)
    parser.add_argument("--sensory-noise-fraction", type=float, default=0.20)
    parser.add_argument("--min-delay", type=int, default=3)
    parser.add_argument("--max-delay", type=int, default=5)
    parser.add_argument("--min-switch-interval", type=int, default=40)
    parser.add_argument("--max-switch-interval", type=int, default=50)
    parser.add_argument("--trial-period", type=int, default=7)
    parser.add_argument("--initial-weight-span", type=float, default=0.8)
    parser.add_argument("--initial-bias-std", type=float, default=0.005)
    parser.add_argument("--lr-scale-min", type=float, default=0.25)
    parser.add_argument("--lr-scale-max", type=float, default=2.5)
    parser.add_argument("--recovery-window-trials", type=int, default=4)
    parser.add_argument("--recovery-accuracy-threshold", type=float, default=0.60)
    parser.add_argument("--output-dir", type=Path, default=None)

    parser.add_argument("--min-all-accuracy", type=float, default=0.51)
    parser.add_argument("--large-population-degradation-tolerance", type=float, default=0.08)
    parser.add_argument("--scaling-accuracy-delta", type=float, default=0.015)
    parser.add_argument("--scaling-corr-delta", type=float, default=0.03)
    parser.add_argument("--scaling-recovery-delta", type=float, default=1.0)
    parser.add_argument("--scaling-variance-delta", type=float, default=0.002)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.steps <= 0:
        parser.error("--steps must be positive")
    if args.seed_count <= 0:
        parser.error("--seed-count must be positive")
    if args.min_delay < 1 or args.max_delay < args.min_delay:
        parser.error("--min-delay/--max-delay must define a positive range")
    if args.trial_period <= args.max_delay:
        parser.error("--trial-period must exceed --max-delay")
    if not 0.0 <= args.noise_prob <= 1.0:
        parser.error("--noise-prob must be in [0, 1]")
    try:
        args.population_sizes = parse_population_sizes(args.population_sizes)
    except ValueError as exc:
        parser.error(str(exc))

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = args.output_dir or (ROOT / "controlled_test_output" / f"tier4_10b_{timestamp}")
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[tier4.10b] running hard_population_scaling on {args.backend}...", flush=True)
    result = run_hard_population_scaling(args, output_dir)
    print(
        f"[tier4.10b] hard_population_scaling: {result.status.upper()}",
        result.failure_reason,
        flush=True,
    )

    summary_csv_path = output_dir / "tier4_10b_summary.csv"
    manifest_path = output_dir / "tier4_10b_results.json"
    report_path = output_dir / "tier4_10b_report.md"
    write_csv(summary_csv_path, summary_rows(result))
    write_json(
        manifest_path,
        {
            "generated_at_utc": utc_now(),
            "tier": "Tier 4.10b - hard population scaling",
            "backend": args.backend,
            "command": " ".join(sys.argv),
            "output_dir": str(output_dir),
            "result": result.to_dict(),
        },
    )
    write_report(
        path=report_path,
        result=result,
        manifest_path=manifest_path,
        summary_csv_path=summary_csv_path,
        output_dir=output_dir,
        args=args,
    )
    write_json(
        ROOT / "controlled_test_output" / "tier4_10b_latest_manifest.json",
        {
            "generated_at_utc": utc_now(),
            "manifest": str(manifest_path),
            "report": str(report_path),
            "summary_csv": str(summary_csv_path),
            "status": result.status,
        },
    )
    print(f"[tier4.10b] wrote report: {report_path}", flush=True)
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
