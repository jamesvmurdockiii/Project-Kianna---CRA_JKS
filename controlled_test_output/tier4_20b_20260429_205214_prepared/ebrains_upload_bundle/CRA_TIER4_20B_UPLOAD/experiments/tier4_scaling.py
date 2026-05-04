#!/usr/bin/env python3
"""Run Tier 4 population-scaling tests for the CRA organism.

Tier 4.10 asks whether the organism breaks, degrades, or improves as the
starting colony size increases. This harness runs the same fixed-population
nonstationary switch task at exact population sizes, exports per-run evidence,
and writes a report/manifest/plot bundle.
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
    json_safe,
    load_backend,
    markdown_value,
    nonstationary_switch_task,
    pass_fail,
    setup_backend,
    strict_sign,
    summarize_rows,
    write_csv,
    write_json,
    utc_now,
    end_backend,
)


@dataclass
class TestResult:
    name: str
    status: str
    summary: dict[str, Any]
    criteria: list[dict[str, Any]]
    artifacts: dict[str, str]
    failure_reason: str = ""

    @property
    def passed(self) -> bool:
        return self.status == "pass"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "summary": self.summary,
            "criteria": self.criteria,
            "artifacts": self.artifacts,
            "failure_reason": self.failure_reason,
        }


def seeds_from_args(args: argparse.Namespace) -> list[int]:
    return [args.base_seed + i for i in range(args.seed_count)]


def mean(values: list[float | None]) -> float | None:
    clean = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    if not clean:
        return None
    return float(np.mean(clean))


def stdev(values: list[float | None]) -> float | None:
    clean = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    if len(clean) < 2:
        return 0.0 if clean else None
    return float(np.std(clean, ddof=1))


def min_value(values: list[float | None]) -> float | None:
    clean = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    return None if not clean else float(np.min(clean))


def max_value(values: list[float | None]) -> float | None:
    clean = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    return None if not clean else float(np.max(clean))


def make_config(
    *,
    seed: int,
    steps: int,
    population_size: int,
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
    cfg.learning.evaluation_horizon_bars = 1
    cfg.learning.readout_learning_rate = float(args.readout_lr)
    cfg.learning.delayed_readout_learning_rate = float(args.delayed_readout_lr)
    return cfg


def alive_readout_weights(organism: Organism) -> list[float]:
    if organism.polyp_population is None:
        return []
    return [
        float(getattr(p, "predictive_readout_weight", 0.0))
        for p in organism.polyp_population.states
        if getattr(p, "is_alive", False)
    ]


def alive_trophic_health(organism: Organism) -> list[float]:
    if organism.polyp_population is None:
        return []
    return [
        float(getattr(p, "trophic_health", 0.0))
        for p in organism.polyp_population.states
        if getattr(p, "is_alive", False)
    ]


def run_scaling_case(
    *,
    population_size: int,
    seed: int,
    sensory: np.ndarray,
    target: np.ndarray,
    evaluation_target: np.ndarray,
    evaluation_mask: np.ndarray,
    args: argparse.Namespace,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    random.seed(seed)
    np.random.seed(seed)
    sim, backend_name = load_backend(args.backend)
    setup_backend(sim, backend_name)

    cfg = make_config(
        seed=seed,
        steps=int(target.size),
        population_size=population_size,
        args=args,
    )
    organism = Organism(cfg, sim)
    rows: list[dict[str, Any]] = []
    task_window: deque[float] = deque(maxlen=1)
    started = time.perf_counter()

    try:
        organism.initialize(stream_keys=["controlled"])
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
                    "test_name": "population_scaling",
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
    summary.update(
        {
            "backend": backend_name,
            "seed": int(seed),
            "steps": int(target.size),
            "population_size": int(population_size),
            "runtime_seconds": time.perf_counter() - started,
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


def rolling_mean(values: np.ndarray, window: int) -> np.ndarray:
    if values.size == 0:
        return values
    window = max(1, min(window, values.size))
    kernel = np.ones(window, dtype=float) / float(window)
    return np.convolve(values, kernel, mode="same")


def aggregate_rows_by_step(rows: list[dict[str, Any]]) -> dict[str, np.ndarray]:
    if not rows:
        return {}
    steps = sorted({int(r["step"]) for r in rows})
    by_step = {step: [r for r in rows if int(r["step"]) == step] for step in steps}

    def avg(key: str) -> np.ndarray:
        return np.asarray(
            [
                float(np.mean([float(r.get(key, 0.0)) for r in by_step[step]]))
                for step in steps
            ],
            dtype=float,
        )

    def correctness() -> np.ndarray:
        values: list[float] = []
        for step in steps:
            step_rows = [
                r for r in by_step[step] if bool(r.get("target_signal_nonzero", False))
            ]
            if not step_rows:
                values.append(np.nan)
            else:
                values.append(float(np.mean([bool(r["strict_direction_correct"]) for r in step_rows])))
        return np.asarray(values, dtype=float)

    return {
        "step": np.asarray(steps, dtype=int),
        "correct": correctness(),
        "target_signal_horizon": avg("target_signal_horizon"),
        "colony_prediction": avg("colony_prediction"),
        "raw_dopamine": avg("raw_dopamine"),
        "mean_readout_weight": avg("mean_readout_weight"),
        "n_alive": avg("n_alive"),
    }


def plot_scaling_summary(
    *,
    aggregates: list[dict[str, Any]],
    output_path: Path,
) -> None:
    if plt is None:
        return
    sizes = np.asarray([int(a["population_size"]) for a in aggregates], dtype=float)
    all_acc = np.asarray([float(a["all_accuracy_mean"]) for a in aggregates], dtype=float)
    tail_acc = np.asarray([float(a["tail_accuracy_mean"]) for a in aggregates], dtype=float)
    corr = np.asarray([float(a["prediction_target_corr_mean"]) for a in aggregates], dtype=float)
    alive = np.asarray([float(a["final_n_alive_mean"]) for a in aggregates], dtype=float)
    runtime = np.asarray([float(a["runtime_seconds_mean"]) for a in aggregates], dtype=float)

    fig, axes = plt.subplots(2, 2, figsize=(12, 9))
    fig.suptitle("Tier 4.10 Population Scaling", fontsize=14, fontweight="bold")

    axes[0, 0].plot(sizes, all_acc, marker="o", label="all accuracy")
    axes[0, 0].plot(sizes, tail_acc, marker="o", label="tail accuracy")
    axes[0, 0].set_ylabel("accuracy")
    axes[0, 0].set_ylim(-0.05, 1.05)
    axes[0, 0].legend()

    axes[0, 1].plot(sizes, corr, marker="o", color="#2f855a")
    axes[0, 1].set_ylabel("prediction/target corr")
    axes[0, 1].set_ylim(-1.05, 1.05)

    axes[1, 0].plot(sizes, alive, marker="o", color="#8250df")
    axes[1, 0].plot(sizes, sizes, linestyle="--", color="#57606a", alpha=0.7, label="target size")
    axes[1, 0].set_ylabel("final alive polyps")
    axes[1, 0].legend()

    axes[1, 1].plot(sizes, runtime, marker="o", color="#9a6700")
    axes[1, 1].set_ylabel("mean runtime seconds")

    for ax in axes.ravel():
        ax.set_xscale("log", base=2)
        ax.set_xticks(sizes)
        ax.set_xticklabels([str(int(s)) for s in sizes])
        ax.set_xlabel("population size")
        ax.grid(alpha=0.25)

    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def plot_scaling_timeseries(
    *,
    grouped_rows: dict[int, list[dict[str, Any]]],
    output_path: Path,
    switch_step: int,
) -> None:
    if plt is None:
        return
    colors = plt.cm.viridis(np.linspace(0.1, 0.9, max(1, len(grouped_rows))))
    fig, axes = plt.subplots(4, 1, figsize=(12, 11), sharex=True)
    fig.suptitle("Tier 4.10 Population Scaling Time Series", fontsize=14, fontweight="bold")

    target_plotted = False
    for (size, rows), color in zip(sorted(grouped_rows.items()), colors):
        agg = aggregate_rows_by_step(rows)
        if not agg:
            continue
        steps = agg["step"]
        correct = np.nan_to_num(agg["correct"], nan=0.0)
        axes[0].plot(steps, rolling_mean(correct, 9), label=f"N={size}", color=color, lw=1.3)
        axes[1].plot(steps, agg["colony_prediction"], label=f"N={size}", color=color, lw=1.0)
        if not target_plotted:
            axes[1].plot(
                steps,
                agg["target_signal_horizon"],
                label="target",
                color="#57606a",
                lw=1.0,
                alpha=0.75,
            )
            target_plotted = True
        axes[2].plot(steps, agg["mean_readout_weight"], label=f"N={size}", color=color, lw=1.0)
        axes[3].plot(steps, agg["n_alive"], label=f"N={size}", color=color, lw=1.0)

    axes[0].set_ylabel("rolling accuracy")
    axes[0].set_ylim(-0.05, 1.05)
    axes[1].set_ylabel("prediction")
    axes[2].set_ylabel("readout weight")
    axes[3].set_ylabel("alive polyps")
    axes[3].set_xlabel("step")

    for ax in axes:
        ax.axvline(switch_step, color="#d29922", lw=1.0, linestyle="--", alpha=0.85)
        ax.axhline(0.0, color="black", lw=0.7, alpha=0.35)
        ax.grid(alpha=0.25)
        ax.legend(loc="upper right", ncol=2)

    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def run_population_scaling(args: argparse.Namespace, output_dir: Path) -> TestResult:
    sensory, target, evaluation_target, evaluation_mask, switch_step = nonstationary_switch_task(
        args.steps,
        args.amplitude,
    )

    grouped_rows: dict[int, list[dict[str, Any]]] = {}
    size_results: list[dict[str, Any]] = []
    for size in args.population_sizes:
        summaries: list[dict[str, Any]] = []
        rows_all: list[dict[str, Any]] = []
        artifacts: dict[str, str] = {}
        for seed in seeds_from_args(args):
            print(f"[tier4] population_scaling/N={size}: seed {seed}...", flush=True)
            rows, summary = run_scaling_case(
                population_size=size,
                seed=seed,
                sensory=sensory,
                target=target,
                evaluation_target=evaluation_target,
                evaluation_mask=evaluation_mask,
                args=args,
            )
            csv_path = output_dir / f"population_scaling_N{size}_seed{seed}_timeseries.csv"
            write_csv(csv_path, rows)
            artifacts[f"seed_{seed}_timeseries_csv"] = str(csv_path)
            rows_all.extend(rows)
            summaries.append(summary)
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
    best_all_accuracy = max(
        float(a["all_accuracy_mean"])
        for a in aggregates
        if a["all_accuracy_mean"] is not None
    )
    large_vs_small_all = (
        None
        if largest["all_accuracy_mean"] is None or smallest["all_accuracy_mean"] is None
        else largest["all_accuracy_mean"] - smallest["all_accuracy_mean"]
    )
    best_vs_small_all = (
        None
        if smallest["all_accuracy_mean"] is None
        else best_all_accuracy - smallest["all_accuracy_mean"]
    )

    summary_plot = output_dir / "population_scaling_summary.png"
    timeseries_plot = output_dir / "population_scaling_timeseries.png"
    plot_scaling_summary(aggregates=aggregates, output_path=summary_plot)
    plot_scaling_timeseries(
        grouped_rows=grouped_rows,
        output_path=timeseries_plot,
        switch_step=switch_step,
    )

    final_alive_matches = all(
        int(round(float(a["final_n_alive_mean"]))) == int(a["population_size"])
        for a in aggregates
    )
    no_births_or_deaths = all(
        int(a["total_births_sum"]) == 0 and int(a["total_deaths_sum"]) == 0
        for a in aggregates
    )
    min_tail_accuracy = min(float(a["tail_accuracy_min"]) for a in aggregates)
    min_all_accuracy = min(float(a["all_accuracy_mean"]) for a in aggregates)
    min_corr = min(float(a["prediction_target_corr_mean"]) for a in aggregates)

    criteria = [
        criterion(
            "all sizes preserve exact population",
            final_alive_matches,
            "==",
            True,
            final_alive_matches,
        ),
        criterion(
            "no lifecycle churn in fixed scaling mode",
            no_births_or_deaths,
            "==",
            True,
            no_births_or_deaths,
        ),
        criterion(
            "minimum tail accuracy across sizes",
            min_tail_accuracy,
            ">=",
            args.min_tail_accuracy,
            min_tail_accuracy >= args.min_tail_accuracy,
        ),
        criterion(
            "minimum overall accuracy across sizes",
            min_all_accuracy,
            ">=",
            args.min_all_accuracy,
            min_all_accuracy >= args.min_all_accuracy,
        ),
        criterion(
            "minimum prediction/target correlation",
            min_corr,
            ">=",
            args.min_prediction_corr,
            min_corr >= args.min_prediction_corr,
        ),
        criterion(
            "largest population does not collapse versus smallest",
            large_vs_small_all,
            ">=",
            -args.large_population_degradation_tolerance,
            large_vs_small_all is not None
            and large_vs_small_all >= -args.large_population_degradation_tolerance,
        ),
        criterion(
            "some larger population improves or matches smallest",
            best_vs_small_all,
            ">=",
            -args.best_population_tolerance,
            best_vs_small_all is not None
            and best_vs_small_all >= -args.best_population_tolerance,
            "A near-zero value means scaling saturated rather than improved.",
        ),
    ]
    status, failure_reason = pass_fail(criteria)
    return TestResult(
        name="population_scaling",
        status=status,
        summary={
            "switch_step": switch_step,
            "population_sizes": [int(s) for s in args.population_sizes],
            "seeds": seeds_from_args(args),
            "aggregates": aggregates,
            "large_vs_small_all_accuracy_delta": large_vs_small_all,
            "best_vs_small_all_accuracy_delta": best_vs_small_all,
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
                "tail_accuracy_mean": agg["tail_accuracy_mean"],
                "tail_accuracy_min": agg["tail_accuracy_min"],
                "all_accuracy_mean": agg["all_accuracy_mean"],
                "prediction_target_corr_mean": agg["prediction_target_corr_mean"],
                "tail_prediction_target_corr_mean": agg["tail_prediction_target_corr_mean"],
                "final_n_alive_mean": agg["final_n_alive_mean"],
                "max_n_alive_mean": agg["max_n_alive_mean"],
                "total_births_sum": agg["total_births_sum"],
                "total_deaths_sum": agg["total_deaths_sum"],
                "final_mean_readout_weight_mean": agg["final_mean_readout_weight_mean"],
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
        "# Tier 4 Population Scaling Findings",
        "",
        f"- Generated: `{utc_now()}`",
        f"- Backend: `{args.backend}`",
        f"- Overall status: **{overall}**",
        f"- Population sizes: `{', '.join(str(s) for s in args.population_sizes)}`",
        f"- Seeds: `{', '.join(str(s) for s in seeds_from_args(args))}`",
        f"- Steps per run: `{args.steps}`",
        f"- Output directory: `{output_dir}`",
        "",
        "Tier 4.10 runs the same nonstationary switch task at exact fixed colony sizes. Reproduction and apoptosis are disabled so the population-size axis is controlled.",
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
            artifact_path = Path(artifact)
            lines.append(f"- `{label}`: `{artifact_path.name}`")
    lines.extend(
        [
            "",
            "## Summary",
            "",
            "| Population | Tail acc | Overall acc | Pred/target corr | Final alive | Mean runtime s |",
            "| ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for agg in result.summary["aggregates"]:
        lines.append(
            "| "
            f"{agg['population_size']} | "
            f"{markdown_value(agg['tail_accuracy_mean'])} | "
            f"{markdown_value(agg['all_accuracy_mean'])} | "
            f"{markdown_value(agg['prediction_target_corr_mean'])} | "
            f"{markdown_value(agg['final_n_alive_mean'])} | "
            f"{markdown_value(agg['runtime_seconds_mean'])} |"
        )

    lines.extend(
        [
            "",
            "## Criteria",
            "",
            "| Criterion | Value | Rule | Pass |",
            "| --- | ---: | --- | --- |",
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
            artifact_path = Path(artifact)
            lines.append(f"![{label}]({artifact_path.name})")
            lines.append("")

    if result.failure_reason:
        lines.extend(["", "## Failure", "", result.failure_reason, ""])

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def parse_population_sizes(values: list[str]) -> list[int]:
    sizes: list[int] = []
    for item in values:
        for part in item.split(","):
            part = part.strip()
            if not part:
                continue
            size = int(part)
            if size < 1:
                raise ValueError("population sizes must be >= 1")
            sizes.append(size)
    deduped = sorted(set(sizes))
    return deduped


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run Tier 4 CRA population-scaling tests and export findings.",
    )
    parser.add_argument("--backend", choices=["nest", "brian2", "mock"], default="nest")
    parser.add_argument("--population-sizes", nargs="+", default=["4,8,16,32,64"])
    parser.add_argument("--steps", type=int, default=220)
    parser.add_argument("--base-seed", type=int, default=42)
    parser.add_argument("--seed-count", type=int, default=3)
    parser.add_argument("--amplitude", type=float, default=DEFAULT_AMPLITUDE)
    parser.add_argument("--dt-seconds", type=float, default=DEFAULT_DT_SECONDS)
    parser.add_argument("--readout-lr", type=float, default=0.10)
    parser.add_argument("--delayed-readout-lr", type=float, default=0.05)
    parser.add_argument("--stop-on-fail", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=None)

    parser.add_argument("--min-tail-accuracy", type=float, default=0.80)
    parser.add_argument("--min-all-accuracy", type=float, default=0.70)
    parser.add_argument("--min-prediction-corr", type=float, default=0.30)
    parser.add_argument("--large-population-degradation-tolerance", type=float, default=0.08)
    parser.add_argument("--best-population-tolerance", type=float, default=0.02)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.steps <= 0:
        parser.error("--steps must be positive")
    if args.seed_count <= 0:
        parser.error("--seed-count must be positive")
    try:
        args.population_sizes = parse_population_sizes(args.population_sizes)
    except ValueError as exc:
        parser.error(str(exc))

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = args.output_dir or (ROOT / "controlled_test_output" / f"tier4_{timestamp}")
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[tier4] running population_scaling on {args.backend}...", flush=True)
    result = run_population_scaling(args, output_dir)
    print(
        f"[tier4] population_scaling: {result.status.upper()}",
        result.failure_reason,
        flush=True,
    )

    summary_csv_path = output_dir / "tier4_summary.csv"
    manifest_path = output_dir / "tier4_results.json"
    report_path = output_dir / "tier4_report.md"
    write_csv(summary_csv_path, summary_rows(result))
    manifest = {
        "generated_at_utc": utc_now(),
        "tier": "Tier 4 - population scaling tests",
        "backend": args.backend,
        "command": " ".join(sys.argv),
        "output_dir": str(output_dir),
        "result": result.to_dict(),
        "thresholds": {
            "min_tail_accuracy": args.min_tail_accuracy,
            "min_all_accuracy": args.min_all_accuracy,
            "min_prediction_corr": args.min_prediction_corr,
            "large_population_degradation_tolerance": args.large_population_degradation_tolerance,
            "best_population_tolerance": args.best_population_tolerance,
        },
    }
    write_json(manifest_path, manifest)
    write_report(
        path=report_path,
        result=result,
        manifest_path=manifest_path,
        summary_csv_path=summary_csv_path,
        output_dir=output_dir,
        args=args,
    )
    latest_path = ROOT / "controlled_test_output" / "tier4_latest_manifest.json"
    write_json(
        latest_path,
        {
            "generated_at_utc": utc_now(),
            "manifest": str(manifest_path),
            "report": str(report_path),
            "summary_csv": str(summary_csv_path),
            "status": result.status,
        },
    )
    print(f"[tier4] wrote report: {report_path}", flush=True)
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
