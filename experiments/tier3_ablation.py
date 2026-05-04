#!/usr/bin/env python3
"""Run Tier 3 controlled architecture ablation tests for the CRA organism.

Tier 3 asks whether the architecture's named mechanisms matter:

7. Ablation: no dopamine.
8. Ablation: no plasticity.
9. Ablation: no trophic selection.

Each test compares an intact run against a targeted ablation, exports
per-step CSV evidence, writes a JSON manifest and Markdown report, and creates
comparison plots. Use ``--stop-on-fail`` to halt at the first broken
architectural claim.
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
    DEFAULT_MAX_POLYPS,
    criterion,
    delayed_reward_task,
    fixed_pattern_task,
    json_safe,
    load_backend,
    markdown_value,
    nonstationary_switch_task,
    pass_fail,
    setup_backend,
    strict_sign,
    summarize_rows,
    window_accuracy,
    write_csv,
    write_json,
    utc_now,
    end_backend,
)


INITIAL_READOUT_WEIGHT = 0.25


@dataclass
class TestResult:
    name: str
    status: str
    summary: dict[str, Any]
    criteria: list[dict[str, Any]]
    artifacts: dict[str, str]
    cases: list[dict[str, Any]]
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
            "cases": self.cases,
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


def make_config(
    *,
    seed: int,
    steps: int,
    max_polyps: int,
    horizon: int,
    fixed_population: bool,
    ablation: str,
    args: argparse.Namespace,
) -> ReefConfig:
    cfg = ReefConfig.default()
    cfg.seed = int(seed)
    cfg.lifecycle.max_population_from_memory = False
    cfg.lifecycle.max_population_hard = int(max_polyps)
    cfg.lifecycle.enable_reproduction = not fixed_population
    cfg.lifecycle.enable_apoptosis = not fixed_population
    cfg.lifecycle.enable_structural_plasticity = not fixed_population
    cfg.measurement.stream_history_maxlen = max(steps + 16, 128)
    cfg.spinnaker.sync_interval_steps = 0
    cfg.spinnaker.runtime_ms_per_step = 1000.0
    cfg.learning.evaluation_horizon_bars = int(horizon)
    cfg.learning.readout_learning_rate = float(args.readout_lr)
    cfg.learning.delayed_readout_learning_rate = float(args.delayed_readout_lr)

    if ablation == "no_dopamine":
        cfg.learning.dopamine_gain = 0.0
        cfg.learning.dopamine_scale = 0.0
        cfg.learning.dopamine_reward_scale = 0.0
        cfg.learning.da_gain_default = 0.0
    elif ablation == "no_plasticity":
        cfg.learning.enable_readout_plasticity = False
        cfg.learning.readout_learning_rate = 0.0
        cfg.learning.delayed_readout_learning_rate = 0.0
        cfg.learning.stdp_a_plus = 0.0
        cfg.learning.stdp_a_minus = 0.0
        cfg.learning.reinforcement_lr = 0.0
        cfg.lifecycle.enable_structural_plasticity = False
    elif ablation == "no_trophic_selection":
        cfg.lifecycle.enable_reproduction = False
        cfg.lifecycle.enable_apoptosis = False
        cfg.lifecycle.enable_structural_plasticity = False
    elif ablation != "intact":
        raise ValueError(f"Unsupported ablation: {ablation}")

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


def run_case(
    *,
    test_name: str,
    case_label: str,
    ablation: str,
    seed: int,
    sensory: np.ndarray,
    target: np.ndarray,
    evaluation_target: np.ndarray,
    evaluation_mask: np.ndarray,
    horizon: int,
    fixed_population: bool,
    max_polyps: int,
    args: argparse.Namespace,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not (
        sensory.shape == target.shape == evaluation_target.shape == evaluation_mask.shape
    ):
        raise ValueError("sensory, target, evaluation_target, and mask shapes must match")

    random.seed(seed)
    np.random.seed(seed)
    sim, backend_name = load_backend(args.backend)
    setup_backend(sim, backend_name)

    cfg = make_config(
        seed=seed,
        steps=int(target.size),
        max_polyps=max_polyps,
        horizon=horizon,
        fixed_population=fixed_population,
        ablation=ablation,
        args=args,
    )
    organism = Organism(cfg, sim)
    rows: list[dict[str, Any]] = []
    task_window: deque[float] = deque(maxlen=horizon)
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
                    "test_name": test_name,
                    "case_label": case_label,
                    "ablation": ablation,
                    "backend": backend_name,
                    "seed": seed,
                    "step": step,
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
            "seed": seed,
            "steps": int(target.size),
            "runtime_seconds": time.perf_counter() - started,
            "horizon": horizon,
            "case_label": case_label,
            "ablation": ablation,
            "fixed_population": fixed_population,
            "final_weight_change_from_initial": (
                None
                if "final_mean_readout_weight" not in summary
                else float(summary["final_mean_readout_weight"] - INITIAL_READOUT_WEIGHT)
            ),
            "final_abs_weight_change_from_initial": (
                None
                if "final_mean_readout_weight" not in summary
                else float(abs(summary["final_mean_readout_weight"] - INITIAL_READOUT_WEIGHT))
            ),
            "config": cfg.to_dict(),
        }
    )
    return rows, summary


def aggregate_case(label: str, summaries: list[dict[str, Any]]) -> dict[str, Any]:
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
        "final_abs_weight_change_from_initial",
        "final_weight_change_from_initial",
    ]
    aggregate: dict[str, Any] = {
        "case_label": label,
        "runs": len(summaries),
        "seeds": [s["seed"] for s in summaries],
    }
    for key in keys:
        values = [s.get(key) for s in summaries]
        aggregate[f"{key}_mean"] = mean(values)
        aggregate[f"{key}_std"] = stdev(values)
        aggregate[f"{key}_min"] = min_value(values)
    aggregate["total_births_sum"] = int(sum(int(s.get("total_births", 0)) for s in summaries))
    aggregate["total_deaths_sum"] = int(sum(int(s.get("total_deaths", 0)) for s in summaries))
    return aggregate


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
        values: list[float] = []
        for step in steps:
            step_rows = by_step[step]
            values.append(float(np.mean([float(r.get(key, 0.0)) for r in step_rows])))
        return np.asarray(values, dtype=float)

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
        "mean_trophic_health": avg("mean_trophic_health"),
    }


def plot_comparison(
    *,
    grouped_rows: dict[str, list[dict[str, Any]]],
    path: Path,
    title: str,
    switch_step: int | None = None,
) -> None:
    if plt is None:
        return
    colors = {
        "intact": "#1f6feb",
        "no_dopamine": "#d1242f",
        "no_plasticity": "#8250df",
        "no_trophic_selection": "#9a6700",
    }
    fig, axes = plt.subplots(5, 1, figsize=(12, 13), sharex=True)
    fig.suptitle(title, fontsize=14, fontweight="bold")

    plotted_target = False
    for label, rows in grouped_rows.items():
        agg = aggregate_rows_by_step(rows)
        if not agg:
            continue
        steps = agg["step"]
        color = colors.get(label, None)
        correct = agg["correct"]
        axes[0].plot(
            steps,
            rolling_mean(np.nan_to_num(correct, nan=0.0), 9),
            label=label,
            color=color,
            lw=1.4,
        )
        axes[1].plot(
            steps,
            agg["colony_prediction"],
            label=f"{label} prediction",
            color=color,
            lw=1.1,
        )
        if not plotted_target:
            axes[1].plot(
                steps,
                agg["target_signal_horizon"],
                label="target",
                color="#57606a",
                lw=1.0,
                alpha=0.8,
            )
            plotted_target = True
        axes[2].plot(steps, agg["raw_dopamine"], label=label, color=color, lw=1.0)
        axes[3].plot(steps, agg["mean_readout_weight"], label=label, color=color, lw=1.2)
        axes[4].plot(steps, agg["n_alive"], label=f"{label} alive", color=color, lw=1.1)

    axes[0].set_ylabel("rolling accuracy")
    axes[0].set_ylim(-0.05, 1.05)
    axes[1].set_ylabel("prediction")
    axes[2].set_ylabel("dopamine")
    axes[3].set_ylabel("readout weight")
    axes[4].set_ylabel("alive polyps")
    axes[4].set_xlabel("step")

    for ax in axes:
        ax.axhline(0.0, color="black", lw=0.7, alpha=0.35)
        ax.grid(alpha=0.2)
        ax.legend(loc="upper right")
        if switch_step is not None:
            ax.axvline(switch_step, color="#d29922", lw=1.0, linestyle="--", alpha=0.9)

    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(path, dpi=160)
    plt.close(fig)


def run_replicates(
    *,
    test_name: str,
    cases: list[dict[str, Any]],
    task: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray],
    horizon: int,
    output_dir: Path,
    args: argparse.Namespace,
    max_polyps: int,
) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    sensory, target, evaluation_target, evaluation_mask = task
    case_results: list[dict[str, Any]] = []
    grouped_rows: dict[str, list[dict[str, Any]]] = {}

    for case in cases:
        label = case["label"]
        ablation = case["ablation"]
        fixed_population = bool(case["fixed_population"])
        rows_all: list[dict[str, Any]] = []
        summaries: list[dict[str, Any]] = []
        artifacts: dict[str, str] = {}
        for seed in seeds_from_args(args):
            print(f"[tier3] {test_name}/{label}: seed {seed}...", flush=True)
            rows, summary = run_case(
                test_name=test_name,
                case_label=label,
                ablation=ablation,
                seed=seed,
                sensory=sensory,
                target=target,
                evaluation_target=evaluation_target,
                evaluation_mask=evaluation_mask,
                horizon=horizon,
                fixed_population=fixed_population,
                max_polyps=max_polyps,
                args=args,
            )
            csv_path = output_dir / f"{test_name}_{label}_seed{seed}_timeseries.csv"
            write_csv(csv_path, rows)
            artifacts[f"seed_{seed}_timeseries_csv"] = str(csv_path)
            rows_all.extend(rows)
            summaries.append(summary)

        grouped_rows[label] = rows_all
        aggregate = aggregate_case(label, summaries)
        case_results.append(
            {
                "label": label,
                "ablation": ablation,
                "fixed_population": fixed_population,
                "summaries": summaries,
                "aggregate": aggregate,
                "artifacts": artifacts,
            }
        )

    return case_results, grouped_rows


def run_no_dopamine(args: argparse.Namespace, output_dir: Path) -> TestResult:
    task = fixed_pattern_task(args.steps, args.amplitude)
    case_results, grouped_rows = run_replicates(
        test_name="no_dopamine_ablation",
        cases=[
            {"label": "intact", "ablation": "intact", "fixed_population": True},
            {"label": "no_dopamine", "ablation": "no_dopamine", "fixed_population": True},
        ],
        task=task,
        horizon=1,
        output_dir=output_dir,
        args=args,
        max_polyps=args.max_polyps,
    )
    by_label = {case["label"]: case["aggregate"] for case in case_results}
    intact = by_label["intact"]
    ablated = by_label["no_dopamine"]
    delta = (
        None
        if intact["tail_accuracy_mean"] is None or ablated["tail_accuracy_mean"] is None
        else intact["tail_accuracy_mean"] - ablated["tail_accuracy_mean"]
    )
    plot_path = output_dir / "no_dopamine_ablation_comparison.png"
    plot_comparison(
        grouped_rows=grouped_rows,
        path=plot_path,
        title="Tier 3.7 Dopamine Ablation: Intact vs No Dopamine",
    )

    criteria = [
        criterion(
            "intact learns fixed pattern",
            intact["tail_accuracy_mean"],
            ">=",
            args.intact_tail_threshold,
            intact["tail_accuracy_mean"] is not None
            and intact["tail_accuracy_mean"] >= args.intact_tail_threshold,
        ),
        criterion(
            "no-dopamine fails fixed pattern",
            ablated["tail_accuracy_mean"],
            "<=",
            args.ablation_tail_ceiling,
            ablated["tail_accuracy_mean"] is not None
            and ablated["tail_accuracy_mean"] <= args.ablation_tail_ceiling,
        ),
        criterion(
            "dopamine ablation performance drop",
            delta,
            ">=",
            args.ablation_delta_threshold,
            delta is not None and delta >= args.ablation_delta_threshold,
        ),
        criterion(
            "ablated dopamine is zero",
            ablated["max_abs_dopamine_mean"],
            "<=",
            args.dopamine_zero_threshold,
            ablated["max_abs_dopamine_mean"] is not None
            and ablated["max_abs_dopamine_mean"] <= args.dopamine_zero_threshold,
        ),
        criterion(
            "ablated readout remains frozen",
            ablated["final_abs_weight_change_from_initial_mean"],
            "<=",
            args.weight_freeze_tolerance,
            ablated["final_abs_weight_change_from_initial_mean"] is not None
            and ablated["final_abs_weight_change_from_initial_mean"]
            <= args.weight_freeze_tolerance,
        ),
    ]
    status, failure_reason = pass_fail(criteria)
    return TestResult(
        name="no_dopamine_ablation",
        status=status,
        summary={"delta_tail_accuracy_mean": delta, "intact": intact, "no_dopamine": ablated},
        criteria=criteria,
        artifacts={"comparison_plot_png": str(plot_path) if plot_path.exists() else ""},
        cases=case_results,
        failure_reason=failure_reason,
    )


def run_no_plasticity(args: argparse.Namespace, output_dir: Path) -> TestResult:
    task = fixed_pattern_task(args.steps, args.amplitude)
    case_results, grouped_rows = run_replicates(
        test_name="no_plasticity_ablation",
        cases=[
            {"label": "intact", "ablation": "intact", "fixed_population": True},
            {
                "label": "no_plasticity",
                "ablation": "no_plasticity",
                "fixed_population": True,
            },
        ],
        task=task,
        horizon=1,
        output_dir=output_dir,
        args=args,
        max_polyps=args.max_polyps,
    )
    by_label = {case["label"]: case["aggregate"] for case in case_results}
    intact = by_label["intact"]
    ablated = by_label["no_plasticity"]
    delta = (
        None
        if intact["tail_accuracy_mean"] is None or ablated["tail_accuracy_mean"] is None
        else intact["tail_accuracy_mean"] - ablated["tail_accuracy_mean"]
    )
    plot_path = output_dir / "no_plasticity_ablation_comparison.png"
    plot_comparison(
        grouped_rows=grouped_rows,
        path=plot_path,
        title="Tier 3.8 Plasticity Ablation: Intact vs Frozen Readout/STDP",
    )

    criteria = [
        criterion(
            "intact learns fixed pattern",
            intact["tail_accuracy_mean"],
            ">=",
            args.intact_tail_threshold,
            intact["tail_accuracy_mean"] is not None
            and intact["tail_accuracy_mean"] >= args.intact_tail_threshold,
        ),
        criterion(
            "no-plasticity fails fixed pattern",
            ablated["tail_accuracy_mean"],
            "<=",
            args.ablation_tail_ceiling,
            ablated["tail_accuracy_mean"] is not None
            and ablated["tail_accuracy_mean"] <= args.ablation_tail_ceiling,
        ),
        criterion(
            "plasticity ablation performance drop",
            delta,
            ">=",
            args.ablation_delta_threshold,
            delta is not None and delta >= args.ablation_delta_threshold,
        ),
        criterion(
            "dopamine still present under plasticity ablation",
            ablated["max_abs_dopamine_mean"],
            ">=",
            args.dopamine_present_threshold,
            ablated["max_abs_dopamine_mean"] is not None
            and ablated["max_abs_dopamine_mean"] >= args.dopamine_present_threshold,
            "Separates frozen plasticity from dopamine-off.",
        ),
        criterion(
            "ablated readout remains frozen",
            ablated["final_abs_weight_change_from_initial_mean"],
            "<=",
            args.weight_freeze_tolerance,
            ablated["final_abs_weight_change_from_initial_mean"] is not None
            and ablated["final_abs_weight_change_from_initial_mean"]
            <= args.weight_freeze_tolerance,
        ),
    ]
    status, failure_reason = pass_fail(criteria)
    return TestResult(
        name="no_plasticity_ablation",
        status=status,
        summary={"delta_tail_accuracy_mean": delta, "intact": intact, "no_plasticity": ablated},
        criteria=criteria,
        artifacts={"comparison_plot_png": str(plot_path) if plot_path.exists() else ""},
        cases=case_results,
        failure_reason=failure_reason,
    )


def run_no_trophic_selection(args: argparse.Namespace, output_dir: Path) -> TestResult:
    sensory, target, evaluation_target, evaluation_mask, switch_step = nonstationary_switch_task(
        args.ecology_steps,
        args.amplitude,
    )
    case_results, grouped_rows = run_replicates(
        test_name="no_trophic_selection_ablation",
        cases=[
            {"label": "intact", "ablation": "intact", "fixed_population": False},
            {
                "label": "no_trophic_selection",
                "ablation": "no_trophic_selection",
                "fixed_population": True,
            },
        ],
        task=(sensory, target, evaluation_target, evaluation_mask),
        horizon=1,
        output_dir=output_dir,
        args=args,
        max_polyps=args.ecology_max_polyps,
    )
    by_label = {case["label"]: case["aggregate"] for case in case_results}
    intact = by_label["intact"]
    ablated = by_label["no_trophic_selection"]

    # Add switch-specific summaries because ecology should improve adaptation,
    # not only final tail statistics.
    for case in case_results:
        for summary in case["summaries"]:
            csv_path = Path(case["artifacts"][f"seed_{summary['seed']}_timeseries_csv"])
            # Re-read only the already-generated summary inputs would be clumsy;
            # the aggregate tail metric remains the primary behavioral criterion.
            summary["switch_step"] = switch_step

    tail_delta = (
        None
        if intact["tail_accuracy_mean"] is None or ablated["tail_accuracy_mean"] is None
        else intact["tail_accuracy_mean"] - ablated["tail_accuracy_mean"]
    )
    all_accuracy_delta = (
        None
        if intact["all_accuracy_mean"] is None or ablated["all_accuracy_mean"] is None
        else intact["all_accuracy_mean"] - ablated["all_accuracy_mean"]
    )
    corr_delta = (
        None
        if (
            intact["prediction_target_corr_mean"] is None
            or ablated["prediction_target_corr_mean"] is None
        )
        else intact["prediction_target_corr_mean"]
        - ablated["prediction_target_corr_mean"]
    )
    alive_delta = (
        None
        if intact["final_n_alive_mean"] is None or ablated["final_n_alive_mean"] is None
        else intact["final_n_alive_mean"] - ablated["final_n_alive_mean"]
    )
    plot_path = output_dir / "no_trophic_selection_ablation_comparison.png"
    plot_comparison(
        grouped_rows=grouped_rows,
        path=plot_path,
        title="Tier 3.9 Trophic Selection Ablation: Ecology On vs Off",
        switch_step=switch_step,
    )

    criteria = [
        criterion(
            "intact trophic selection produces births",
            intact["total_births_sum"],
            ">=",
            args.trophic_births_min,
            intact["total_births_sum"] >= args.trophic_births_min,
        ),
        criterion(
            "ablated selection has no births",
            ablated["total_births_sum"],
            "==",
            0,
            ablated["total_births_sum"] == 0,
        ),
        criterion(
            "ablated selection has no deaths",
            ablated["total_deaths_sum"],
            "==",
            0,
            ablated["total_deaths_sum"] == 0,
        ),
        criterion(
            "trophic selection expands population",
            alive_delta,
            ">=",
            args.trophic_alive_delta_threshold,
            alive_delta is not None and alive_delta >= args.trophic_alive_delta_threshold,
        ),
        criterion(
            "trophic selection improves overall accuracy",
            all_accuracy_delta,
            ">=",
            args.trophic_all_accuracy_delta_threshold,
            all_accuracy_delta is not None
            and all_accuracy_delta >= args.trophic_all_accuracy_delta_threshold,
            "Tail accuracy can saturate in both cases; this measures adaptation over the full switch stressor.",
        ),
        criterion(
            "trophic selection improves prediction correlation",
            corr_delta,
            ">=",
            args.trophic_corr_delta_threshold,
            corr_delta is not None and corr_delta >= args.trophic_corr_delta_threshold,
        ),
    ]
    status, failure_reason = pass_fail(criteria)
    return TestResult(
        name="no_trophic_selection_ablation",
        status=status,
        summary={
            "switch_step": switch_step,
            "tail_accuracy_delta_mean": tail_delta,
            "all_accuracy_delta_mean": all_accuracy_delta,
            "prediction_corr_delta_mean": corr_delta,
            "final_alive_delta_mean": alive_delta,
            "intact": intact,
            "no_trophic_selection": ablated,
        },
        criteria=criteria,
        artifacts={"comparison_plot_png": str(plot_path) if plot_path.exists() else ""},
        cases=case_results,
        failure_reason=failure_reason,
    )


def summary_rows(results: list[TestResult]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for result in results:
        row = {
            "test_name": result.name,
            "status": result.status,
            "failure_reason": result.failure_reason,
        }
        if result.name == "no_dopamine_ablation":
            row.update(
                {
                    "intact_tail_accuracy_mean": result.summary["intact"]["tail_accuracy_mean"],
                    "ablated_tail_accuracy_mean": result.summary["no_dopamine"]["tail_accuracy_mean"],
                    "delta_tail_accuracy_mean": result.summary["delta_tail_accuracy_mean"],
                    "ablated_max_abs_dopamine_mean": result.summary["no_dopamine"]["max_abs_dopamine_mean"],
                }
            )
        elif result.name == "no_plasticity_ablation":
            row.update(
                {
                    "intact_tail_accuracy_mean": result.summary["intact"]["tail_accuracy_mean"],
                    "ablated_tail_accuracy_mean": result.summary["no_plasticity"]["tail_accuracy_mean"],
                    "delta_tail_accuracy_mean": result.summary["delta_tail_accuracy_mean"],
                    "ablated_max_abs_dopamine_mean": result.summary["no_plasticity"]["max_abs_dopamine_mean"],
                }
            )
        elif result.name == "no_trophic_selection_ablation":
            row.update(
                {
                    "intact_tail_accuracy_mean": result.summary["intact"]["tail_accuracy_mean"],
                    "ablated_tail_accuracy_mean": result.summary["no_trophic_selection"]["tail_accuracy_mean"],
                    "tail_accuracy_delta_mean": result.summary["tail_accuracy_delta_mean"],
                    "all_accuracy_delta_mean": result.summary["all_accuracy_delta_mean"],
                    "prediction_corr_delta_mean": result.summary["prediction_corr_delta_mean"],
                    "intact_births_sum": result.summary["intact"]["total_births_sum"],
                    "ablated_births_sum": result.summary["no_trophic_selection"]["total_births_sum"],
                    "final_alive_delta_mean": result.summary["final_alive_delta_mean"],
                }
            )
        rows.append(row)
    return rows


def write_report(
    *,
    path: Path,
    results: list[TestResult],
    manifest_path: Path,
    summary_csv_path: Path,
    output_dir: Path,
    stopped_after: str | None,
    args: argparse.Namespace,
) -> None:
    overall = "PASS" if results and all(r.passed for r in results) else "FAIL"
    if stopped_after:
        overall = "STOPPED"

    lines = [
        "# Tier 3 Controlled Architecture Ablation Findings",
        "",
        f"- Generated: `{utc_now()}`",
        f"- Backend: `{args.backend}`",
        f"- Overall status: **{overall}**",
        f"- Seeds: `{', '.join(str(s) for s in seeds_from_args(args))}`",
        f"- Fixed-pattern steps: `{args.steps}`",
        f"- Ecology steps: `{args.ecology_steps}`",
        f"- Output directory: `{output_dir}`",
        "",
        "Tier 3 asks whether named architecture mechanisms are actually doing work. Each result compares an intact organism against a targeted ablation under the same controlled task.",
        "",
        "## Artifact Index",
        "",
        f"- JSON manifest: `{manifest_path.name}`",
        f"- Summary CSV: `{summary_csv_path.name}`",
    ]
    if MATPLOTLIB_ERROR:
        lines.append(f"- Plotting unavailable: `{MATPLOTLIB_ERROR}`")

    lines.extend(
        [
            "",
            "## Summary",
            "",
            "| Test | Status | Key result | Interpretation |",
            "| --- | --- | --- | --- |",
        ]
    )

    for result in results:
        if result.name == "no_dopamine_ablation":
            key = (
                f"intact_tail={markdown_value(result.summary['intact']['tail_accuracy_mean'])}, "
                f"no_da_tail={markdown_value(result.summary['no_dopamine']['tail_accuracy_mean'])}, "
                f"delta={markdown_value(result.summary['delta_tail_accuracy_mean'])}"
            )
            note = "Dopamine-gated learning matters." if result.passed else result.failure_reason
        elif result.name == "no_plasticity_ablation":
            key = (
                f"intact_tail={markdown_value(result.summary['intact']['tail_accuracy_mean'])}, "
                f"frozen_tail={markdown_value(result.summary['no_plasticity']['tail_accuracy_mean'])}, "
                f"delta={markdown_value(result.summary['delta_tail_accuracy_mean'])}"
            )
            note = "Plasticity is required, not just inference." if result.passed else result.failure_reason
        elif result.name == "no_trophic_selection_ablation":
            key = (
                f"births={markdown_value(result.summary['intact']['total_births_sum'])}, "
                f"all_acc_delta={markdown_value(result.summary['all_accuracy_delta_mean'])}, "
                f"corr_delta={markdown_value(result.summary['prediction_corr_delta_mean'])}, "
                f"alive_delta={markdown_value(result.summary['final_alive_delta_mean'])}"
            )
            note = "Ecology improves adaptation over the switch stressor." if result.passed else result.failure_reason
        else:
            key = ""
            note = result.failure_reason or "criteria satisfied"
        lines.append(
            f"| `{result.name}` | **{result.status.upper()}** | {key} | {note or 'criteria satisfied'} |"
        )

    for result in results:
        lines.extend(
            [
                "",
                f"## {result.name}",
                "",
                f"Status: **{result.status.upper()}**",
                "",
                "Criteria:",
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
        lines.extend(["", "Case aggregates:", ""])
        for case in result.cases:
            agg = case["aggregate"]
            lines.append(
                f"- `{case['label']}`: tail_acc_mean={markdown_value(agg.get('tail_accuracy_mean'))}, "
                f"max_da_mean={markdown_value(agg.get('max_abs_dopamine_mean'))}, "
                f"births_sum={markdown_value(agg.get('total_births_sum'))}, "
                f"final_alive_mean={markdown_value(agg.get('final_n_alive_mean'))}, "
                f"final_weight_mean={markdown_value(agg.get('final_mean_readout_weight_mean'))}"
            )
        lines.extend(["", "Artifacts:", ""])
        for label, artifact in result.artifacts.items():
            if artifact:
                artifact_path = Path(artifact)
                lines.append(f"- `{label}`: `{artifact_path.name}`")
                if artifact_path.suffix.lower() == ".png":
                    lines.extend(["", f"![{result.name} comparison]({artifact_path.name})", ""])
        lines.append("")

    if stopped_after:
        lines.extend(
            [
                "## Stop Condition",
                "",
                f"Execution stopped after `{stopped_after}` because `--stop-on-fail` was enabled.",
                "",
            ]
        )

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def resolve_tests(selected: list[str]) -> list[str]:
    order = [
        "no_dopamine_ablation",
        "no_plasticity_ablation",
        "no_trophic_selection_ablation",
    ]
    aliases = {
        "all": "all",
        "dopamine": "no_dopamine_ablation",
        "no_dopamine": "no_dopamine_ablation",
        "no_dopamine_ablation": "no_dopamine_ablation",
        "plasticity": "no_plasticity_ablation",
        "no_plasticity": "no_plasticity_ablation",
        "no_plasticity_ablation": "no_plasticity_ablation",
        "trophic": "no_trophic_selection_ablation",
        "no_trophic": "no_trophic_selection_ablation",
        "no_trophic_selection": "no_trophic_selection_ablation",
        "no_trophic_selection_ablation": "no_trophic_selection_ablation",
    }
    normalized = [aliases[item] for item in selected]
    if "all" in normalized:
        return order
    wanted = set(normalized)
    return [name for name in order if name in wanted]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run Tier 3 CRA architecture ablations and export findings.",
    )
    parser.add_argument(
        "--tests",
        nargs="+",
        default=["all"],
        choices=[
            "all",
            "dopamine",
            "no_dopamine",
            "no_dopamine_ablation",
            "plasticity",
            "no_plasticity",
            "no_plasticity_ablation",
            "trophic",
            "no_trophic",
            "no_trophic_selection",
            "no_trophic_selection_ablation",
        ],
    )
    parser.add_argument("--backend", choices=["nest", "brian2", "mock"], default="nest")
    parser.add_argument("--steps", type=int, default=180)
    parser.add_argument("--ecology-steps", type=int, default=220)
    parser.add_argument("--base-seed", type=int, default=42)
    parser.add_argument("--seed-count", type=int, default=3)
    parser.add_argument("--amplitude", type=float, default=DEFAULT_AMPLITUDE)
    parser.add_argument("--max-polyps", type=int, default=DEFAULT_MAX_POLYPS)
    parser.add_argument("--ecology-max-polyps", type=int, default=16)
    parser.add_argument("--dt-seconds", type=float, default=DEFAULT_DT_SECONDS)
    parser.add_argument("--readout-lr", type=float, default=0.10)
    parser.add_argument("--delayed-readout-lr", type=float, default=0.05)
    parser.add_argument("--stop-on-fail", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=None)

    parser.add_argument("--intact-tail-threshold", type=float, default=0.75)
    parser.add_argument("--ablation-tail-ceiling", type=float, default=0.55)
    parser.add_argument("--ablation-delta-threshold", type=float, default=0.20)
    parser.add_argument("--dopamine-zero-threshold", type=float, default=1e-9)
    parser.add_argument("--dopamine-present-threshold", type=float, default=0.50)
    parser.add_argument("--weight-freeze-tolerance", type=float, default=0.01)
    parser.add_argument("--trophic-births-min", type=int, default=1)
    parser.add_argument("--trophic-alive-delta-threshold", type=float, default=1.0)
    parser.add_argument("--trophic-all-accuracy-delta-threshold", type=float, default=0.05)
    parser.add_argument("--trophic-corr-delta-threshold", type=float, default=0.10)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.steps <= 0:
        parser.error("--steps must be positive")
    if args.ecology_steps <= 0:
        parser.error("--ecology-steps must be positive")
    if args.seed_count <= 0:
        parser.error("--seed-count must be positive")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = args.output_dir or (ROOT / "controlled_test_output" / f"tier3_{timestamp}")
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    selected_tests = resolve_tests(args.tests)
    runners = {
        "no_dopamine_ablation": run_no_dopamine,
        "no_plasticity_ablation": run_no_plasticity,
        "no_trophic_selection_ablation": run_no_trophic_selection,
    }
    results: list[TestResult] = []
    stopped_after: str | None = None

    for test_name in selected_tests:
        print(f"[tier3] running {test_name} on {args.backend}...", flush=True)
        result = runners[test_name](args, output_dir)
        results.append(result)
        print(
            f"[tier3] {test_name}: {result.status.upper()}",
            result.failure_reason,
            flush=True,
        )
        if args.stop_on_fail and not result.passed:
            stopped_after = test_name
            break

    summary_csv_path = output_dir / "tier3_summary.csv"
    manifest_path = output_dir / "tier3_results.json"
    report_path = output_dir / "tier3_report.md"
    write_csv(summary_csv_path, summary_rows(results))

    manifest = {
        "generated_at_utc": utc_now(),
        "tier": "Tier 3 - architecture ablation tests",
        "backend": args.backend,
        "command": " ".join(sys.argv),
        "output_dir": str(output_dir),
        "selected_tests": selected_tests,
        "stopped_after": stopped_after,
        "seeds": seeds_from_args(args),
        "thresholds": {
            "intact_tail_threshold": args.intact_tail_threshold,
            "ablation_tail_ceiling": args.ablation_tail_ceiling,
            "ablation_delta_threshold": args.ablation_delta_threshold,
            "dopamine_zero_threshold": args.dopamine_zero_threshold,
            "dopamine_present_threshold": args.dopamine_present_threshold,
            "weight_freeze_tolerance": args.weight_freeze_tolerance,
            "trophic_births_min": args.trophic_births_min,
            "trophic_alive_delta_threshold": args.trophic_alive_delta_threshold,
            "trophic_all_accuracy_delta_threshold": args.trophic_all_accuracy_delta_threshold,
            "trophic_corr_delta_threshold": args.trophic_corr_delta_threshold,
        },
        "results": [r.to_dict() for r in results],
    }
    write_json(manifest_path, manifest)
    write_report(
        path=report_path,
        results=results,
        manifest_path=manifest_path,
        summary_csv_path=summary_csv_path,
        output_dir=output_dir,
        stopped_after=stopped_after,
        args=args,
    )

    latest_path = ROOT / "controlled_test_output" / "tier3_latest_manifest.json"
    write_json(
        latest_path,
        {
            "latest_manifest": str(manifest_path),
            "latest_report": str(report_path),
            "latest_summary_csv": str(summary_csv_path),
            "generated_at_utc": utc_now(),
        },
    )

    print(f"[tier3] wrote report: {report_path}", flush=True)
    return 0 if results and all(r.passed for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
