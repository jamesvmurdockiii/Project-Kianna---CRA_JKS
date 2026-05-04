#!/usr/bin/env python3
"""Run Tier 4.11 domain-transfer tests for the CRA organism.

Tier 4.11 asks whether CRA learning is substrate-level rather than trading-
specific. It compares the existing controlled finance/signed-return path with a
non-finance ``sensor_control`` TaskAdapter using the same backend, seeds, fixed
population settings, and delayed signed consequence structure.

Cases:
- finance_signed_return: controlled finance-style signed-return task
- sensor_control: non-finance TaskAdapter task, no TradingBridge constructed
- finance_zero_signal / sensor_zero_signal: negative controls
- finance_shuffled_label / sensor_shuffled_label: leakage/random-label controls
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

from coral_reef_spinnaker import (  # noqa: E402
    Observation,
    Organism,
    ReefConfig,
    SensorControlAdapter,
)
from tier2_learning import (  # noqa: E402
    DEFAULT_AMPLITUDE,
    DEFAULT_DT_SECONDS,
    criterion,
    load_backend,
    markdown_value,
    pass_fail,
    plot_case,
    setup_backend,
    strict_sign,
    summarize_rows,
    write_csv,
    write_json,
    utc_now,
    end_backend,
)
from tier4_scaling import (  # noqa: E402
    TestResult,
    alive_readout_weights,
    alive_trophic_health,
    mean,
    seeds_from_args,
    stdev,
)


@dataclass(frozen=True)
class CaseSpec:
    name: str
    domain: str
    adapter: str
    task_kind: str
    uses_trading_bridge: bool
    should_learn: bool
    control_kind: str = "none"


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


def delayed_signed_task(
    *,
    steps: int,
    amplitude: float,
    delay: int,
    period: int,
    seed: int,
    kind: str,
    sensory_noise_fraction: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, dict[str, Any]]:
    """Build delayed cue/consequence arrays for learning and controls."""
    rng = np.random.default_rng(seed)
    sensory = np.zeros(steps, dtype=float)
    target = np.zeros(steps, dtype=float)
    evaluation_target = np.zeros(steps, dtype=float)
    evaluation_mask = np.zeros(steps, dtype=bool)

    if kind == "zero":
        return sensory, target, evaluation_target, evaluation_mask, {
            "kind": kind,
            "trials": 0,
            "delay": delay,
            "period": period,
        }

    trial_starts = list(range(0, steps - delay, period))
    cue_signs = np.asarray(
        [1.0 if i % 2 == 0 else -1.0 for i in range(len(trial_starts))],
        dtype=float,
    )
    rng.shuffle(cue_signs)

    if kind == "learn":
        outcome_signs = -cue_signs
    elif kind == "shuffled":
        base = -cue_signs.copy()
        outcome_signs = base.copy()
        best_signs = outcome_signs.copy()
        best_abs_corr = float("inf")
        for _ in range(256):
            rng.shuffle(outcome_signs)
            corr = 0.0
            if (
                len(cue_signs) >= 3
                and np.std(cue_signs) > 0
                and np.std(outcome_signs) > 0
            ):
                corr = float(np.corrcoef(cue_signs, outcome_signs)[0, 1])
            if abs(corr) < best_abs_corr:
                best_abs_corr = abs(corr)
                best_signs = outcome_signs.copy()
            if abs(corr) <= 0.05:
                break
        outcome_signs = best_signs
    else:
        raise ValueError(f"Unsupported task kind: {kind}")

    for start, cue_sign, outcome_sign in zip(trial_starts, cue_signs, outcome_signs):
        sensory_noise = rng.normal(0.0, sensory_noise_fraction * amplitude)
        sensory[start] = amplitude * cue_sign + sensory_noise
        target[start + delay] = amplitude * outcome_sign
        evaluation_target[start] = amplitude * outcome_sign
        evaluation_mask[start] = True

    if kind == "shuffled":
        corr = None
        if len(cue_signs) >= 3 and np.std(cue_signs) > 0 and np.std(outcome_signs) > 0:
            corr = float(np.corrcoef(cue_signs, outcome_signs)[0, 1])
    else:
        corr = -1.0

    return sensory, target, evaluation_target, evaluation_mask, {
        "kind": kind,
        "trials": len(trial_starts),
        "delay": delay,
        "period": period,
        "cue_outcome_corr": corr,
    }


def run_case_seed(
    *,
    spec: CaseSpec,
    seed: int,
    args: argparse.Namespace,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    random.seed(seed)
    np.random.seed(seed)
    sensory, target, evaluation_target, evaluation_mask, task_metadata = delayed_signed_task(
        steps=args.steps,
        amplitude=args.amplitude,
        delay=args.delay,
        period=args.period,
        seed=args.task_seed + seed,
        kind=spec.task_kind,
        sensory_noise_fraction=args.sensory_noise_fraction,
    )

    sim, backend_name = load_backend(args.backend)
    setup_backend(sim, backend_name)
    cfg = make_config(
        seed=seed,
        steps=args.steps,
        population_size=args.population_size,
        horizon=args.delay,
        args=args,
    )
    organism = Organism(
        cfg,
        sim,
        use_default_trading_bridge=spec.uses_trading_bridge,
    )
    adapter = SensorControlAdapter()
    rows: list[dict[str, Any]] = []
    task_window: deque[float] = deque(maxlen=args.delay)
    started = time.perf_counter()

    try:
        organism.initialize(stream_keys=[spec.domain])
        bridge_present_after_init = organism.trading_bridge is not None
        for step, (sensory_value, target_value, eval_value, eval_enabled) in enumerate(
            zip(sensory, target, evaluation_target, evaluation_mask)
        ):
            task_window.append(float(target_value))
            task_signal = float(np.sum(list(task_window)))

            if spec.uses_trading_bridge:
                metrics = organism.train_step(
                    market_return_1m=float(target_value),
                    dt_seconds=args.dt_seconds,
                    sensory_return_1m=float(sensory_value),
                )
            else:
                observation = Observation(
                    stream_id=spec.domain,
                    x=np.asarray([float(sensory_value)], dtype=float),
                    target=float(target_value),
                    metadata={
                        "case": spec.name,
                        "step": step,
                        "adapter": spec.adapter,
                    },
                )
                metrics = organism.train_adapter_step(
                    adapter,
                    observation,
                    dt_seconds=args.dt_seconds,
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
                    "test_name": spec.name,
                    "domain": spec.domain,
                    "adapter": spec.adapter,
                    "control_kind": spec.control_kind,
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
                    "uses_trading_bridge": bool(spec.uses_trading_bridge),
                    "trading_bridge_present_after_init": bool(bridge_present_after_init),
                    "trading_bridge_present_after_step": bool(organism.trading_bridge is not None),
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
            "steps": int(args.steps),
            "population_size": int(args.population_size),
            "domain": spec.domain,
            "adapter": spec.adapter,
            "control_kind": spec.control_kind,
            "uses_trading_bridge": bool(spec.uses_trading_bridge),
            "trading_bridge_present_after_init": bool(
                rows[0]["trading_bridge_present_after_init"] if rows else False
            ),
            "trading_bridge_present_any_step": bool(
                any(bool(r["trading_bridge_present_after_step"]) for r in rows)
            ),
            "runtime_seconds": time.perf_counter() - started,
            "task_metadata": task_metadata,
            "config": cfg.to_dict(),
        }
    )
    return rows, summary


def aggregate_case(spec: CaseSpec, summaries: list[dict[str, Any]]) -> dict[str, Any]:
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
        "final_matured_horizons",
        "max_matured_horizons",
        "runtime_seconds",
    ]
    agg: dict[str, Any] = {
        "case": spec.name,
        "domain": spec.domain,
        "adapter": spec.adapter,
        "control_kind": spec.control_kind,
        "uses_trading_bridge": bool(spec.uses_trading_bridge),
        "should_learn": bool(spec.should_learn),
        "runs": len(summaries),
        "seeds": [s["seed"] for s in summaries],
    }
    for key in keys:
        values = [s.get(key) for s in summaries]
        agg[f"{key}_mean"] = mean(values)
        agg[f"{key}_std"] = stdev(values)
    agg["total_births_sum"] = int(sum(int(s.get("total_births", 0)) for s in summaries))
    agg["total_deaths_sum"] = int(sum(int(s.get("total_deaths", 0)) for s in summaries))
    agg["trading_bridge_present_any_run"] = bool(
        any(bool(s.get("trading_bridge_present_any_step", False)) for s in summaries)
    )
    agg["trading_bridge_present_after_init_any_run"] = bool(
        any(bool(s.get("trading_bridge_present_after_init", False)) for s in summaries)
    )
    return agg


def case_criteria(spec: CaseSpec, agg: dict[str, Any], args: argparse.Namespace) -> list[dict[str, Any]]:
    criteria: list[dict[str, Any]] = [
        criterion(
            "no extinction/collapse",
            agg["final_n_alive_mean"],
            "==",
            args.population_size,
            agg["final_n_alive_mean"] == args.population_size,
        ),
        criterion(
            "fixed population has no births/deaths",
            {"births": agg["total_births_sum"], "deaths": agg["total_deaths_sum"]},
            "==",
            {"births": 0, "deaths": 0},
            agg["total_births_sum"] == 0 and agg["total_deaths_sum"] == 0,
        ),
    ]
    if not spec.uses_trading_bridge:
        criteria.append(
            criterion(
                "adapter path does not construct TradingBridge",
                agg["trading_bridge_present_any_run"],
                "==",
                False,
                not agg["trading_bridge_present_any_run"],
            )
        )

    if spec.should_learn:
        corr = agg["prediction_target_corr_mean"]
        tail_corr = agg["tail_prediction_target_corr_mean"]
        corr_value = max(
            abs(float(corr)) if corr is not None else 0.0,
            abs(float(tail_corr)) if tail_corr is not None else 0.0,
        )
        criteria.extend(
            [
                criterion(
                    "learns above baseline overall accuracy",
                    agg["all_accuracy_mean"],
                    ">=",
                    args.learn_all_accuracy_threshold,
                    agg["all_accuracy_mean"] is not None
                    and agg["all_accuracy_mean"] >= args.learn_all_accuracy_threshold,
                ),
                criterion(
                    "learns above baseline tail accuracy",
                    agg["tail_accuracy_mean"],
                    ">=",
                    args.learn_tail_accuracy_threshold,
                    agg["tail_accuracy_mean"] is not None
                    and agg["tail_accuracy_mean"] >= args.learn_tail_accuracy_threshold,
                ),
                criterion(
                    "prediction/target relationship emerges",
                    corr_value,
                    ">= abs",
                    args.learn_abs_corr_threshold,
                    corr_value >= args.learn_abs_corr_threshold,
                    "The mapping may be inverted, so absolute correlation is used.",
                ),
                criterion(
                    "delayed horizons mature",
                    agg["max_matured_horizons_mean"],
                    ">",
                    0,
                    agg["max_matured_horizons_mean"] is not None
                    and agg["max_matured_horizons_mean"] > 0,
                ),
            ]
        )
    elif spec.control_kind == "zero":
        criteria.extend(
            [
                criterion(
                    "zero control has no evaluation labels",
                    agg["all_accuracy_mean"],
                    "is",
                    None,
                    agg["all_accuracy_mean"] is None,
                ),
                criterion(
                    "zero control has no dopamine",
                    agg["max_abs_dopamine_mean"],
                    "<=",
                    args.zero_max_abs_dopamine,
                    agg["max_abs_dopamine_mean"] is not None
                    and agg["max_abs_dopamine_mean"] <= args.zero_max_abs_dopamine,
                ),
            ]
        )
    else:
        corr = agg["prediction_target_corr_mean"]
        corr_abs = abs(float(corr)) if corr is not None else 0.0
        criteria.extend(
            [
                criterion(
                    "shuffled control stays near chance",
                    agg["all_accuracy_mean"],
                    "<=",
                    args.shuffled_max_accuracy,
                    agg["all_accuracy_mean"] is not None
                    and agg["all_accuracy_mean"] <= args.shuffled_max_accuracy,
                ),
                criterion(
                    "shuffled control has low abs correlation",
                    corr_abs,
                    "<=",
                    args.shuffled_max_abs_corr,
                    corr_abs <= args.shuffled_max_abs_corr,
                ),
            ]
        )
    return criteria


def summary_rows(results: list[TestResult]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for result in results:
        agg = result.summary["aggregate"]
        rows.append(
            {
                "case": agg["case"],
                "status": result.status,
                "domain": agg["domain"],
                "adapter": agg["adapter"],
                "control_kind": agg["control_kind"],
                "uses_trading_bridge": agg["uses_trading_bridge"],
                "runs": agg["runs"],
                "all_accuracy_mean": agg["all_accuracy_mean"],
                "all_accuracy_std": agg["all_accuracy_std"],
                "tail_accuracy_mean": agg["tail_accuracy_mean"],
                "prediction_target_corr_mean": agg["prediction_target_corr_mean"],
                "max_abs_dopamine_mean": agg["max_abs_dopamine_mean"],
                "final_n_alive_mean": agg["final_n_alive_mean"],
                "total_births_sum": agg["total_births_sum"],
                "total_deaths_sum": agg["total_deaths_sum"],
                "trading_bridge_present_any_run": agg["trading_bridge_present_any_run"],
                "runtime_seconds_mean": agg["runtime_seconds_mean"],
            }
        )
    return rows


def plot_summary(results: list[TestResult], path: Path) -> None:
    if plt is None or not results:
        return
    labels = [r.summary["aggregate"]["case"].replace("_", "\n") for r in results]
    all_acc = [r.summary["aggregate"].get("all_accuracy_mean") for r in results]
    tail_acc = [r.summary["aggregate"].get("tail_accuracy_mean") for r in results]
    corr = [r.summary["aggregate"].get("prediction_target_corr_mean") for r in results]
    dopamine = [r.summary["aggregate"].get("max_abs_dopamine_mean") for r in results]
    x = np.arange(len(labels))

    def clean(values: list[Any]) -> np.ndarray:
        return np.asarray([0.0 if v is None else float(v) for v in values], dtype=float)

    fig, axes = plt.subplots(2, 2, figsize=(14, 8))
    fig.suptitle("Tier 4.11 Domain Transfer", fontsize=14, fontweight="bold")
    panels = [
        (axes[0, 0], clean(all_acc), "overall accuracy", (0.0, 1.0)),
        (axes[0, 1], clean(tail_acc), "tail accuracy", (0.0, 1.0)),
        (axes[1, 0], clean(corr), "prediction/target corr", (-1.0, 1.0)),
        (axes[1, 1], clean(dopamine), "max |dopamine|", None),
    ]
    colors = ["#1f6feb", "#2f855a", "#8250df", "#9a6700"]
    for (ax, values, ylabel, ylim), color in zip(panels, colors):
        ax.bar(x, values, color=color, alpha=0.82)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=0, fontsize=8)
        ax.set_ylabel(ylabel)
        if ylim is not None:
            ax.set_ylim(*ylim)
        ax.grid(axis="y", alpha=0.25)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(path, dpi=160)
    plt.close(fig)


def write_report(
    *,
    path: Path,
    results: list[TestResult],
    manifest_path: Path,
    summary_csv_path: Path,
    output_dir: Path,
    args: argparse.Namespace,
) -> None:
    overall = "PASS" if results and all(r.passed for r in results) else "FAIL"
    lines = [
        "# Tier 4.11 Domain Transfer Findings",
        "",
        f"- Generated: `{utc_now()}`",
        f"- Backend: `{args.backend}`",
        f"- Overall status: **{overall}**",
        f"- Population size: `{args.population_size}` fixed polyps",
        f"- Seeds: `{', '.join(str(s) for s in seeds_from_args(args))}`",
        f"- Steps per run: `{args.steps}`",
        f"- Delay: `{args.delay}` steps",
        f"- Output directory: `{output_dir}`",
        "",
        "Tier 4.11 tests whether the same CRA core and learning manager transfer from the controlled finance/signed-return path to a non-finance `sensor_control` TaskAdapter under the same NEST backend and fixed population settings.",
        "",
        "## Artifact Index",
        "",
        f"- JSON manifest: `{manifest_path.name}`",
        f"- Summary CSV: `{summary_csv_path.name}`",
    ]
    if MATPLOTLIB_ERROR:
        lines.append(f"- Plotting unavailable: `{MATPLOTLIB_ERROR}`")
    lines.append("- Summary plot: `domain_transfer_summary.png`")

    lines.extend(
        [
            "",
            "## Summary",
            "",
            "| Case | Status | Domain | Adapter | Bridge? | Overall acc | Tail acc | Corr | Max |DA| |",
            "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for result in results:
        agg = result.summary["aggregate"]
        lines.append(
            "| "
            f"{agg['case']} | "
            f"{result.status} | "
            f"{agg['domain']} | "
            f"{agg['adapter']} | "
            f"{agg['uses_trading_bridge']} | "
            f"{markdown_value(agg['all_accuracy_mean'])} | "
            f"{markdown_value(agg['tail_accuracy_mean'])} | "
            f"{markdown_value(agg['prediction_target_corr_mean'])} | "
            f"{markdown_value(agg['max_abs_dopamine_mean'])} |"
        )

    lines.extend(["", "## Criteria", ""])
    for result in results:
        lines.extend([f"### {result.name}", ""])
        lines.extend(["| Criterion | Value | Rule | Pass |", "| --- | --- | --- | --- |"])
        for item in result.criteria:
            lines.append(
                "| "
                f"{item['name']} | "
                f"{markdown_value(item['value'])} | "
                f"{item['operator']} {markdown_value(item['threshold'])} | "
                f"{'yes' if item['passed'] else 'no'} |"
            )
        if result.failure_reason:
            lines.extend(["", f"Failure: {result.failure_reason}"])
        lines.append("")

    lines.extend(
        [
            "## Interpretation",
            "",
            "- Finance and sensor_control use the same CRA organism core, learning manager, backend, seeds, and fixed population settings.",
            "- The sensor_control cases run through `train_adapter_step(...)` with `use_default_trading_bridge=False`, so no TradingBridge is constructed for the non-finance adapter path.",
            "- A pass means the non-finance adapter learns while zero and shuffled controls do not show fake learning.",
            "- In sparse delayed-control cases, useful learning can appear through matured delayed-consequence credit rather than same-step raw dopamine telemetry; read `max_matured_horizons` alongside `raw_dopamine`.",
            "",
            "## Plots",
            "",
            "![domain_transfer_summary](domain_transfer_summary.png)",
            "",
        ]
    )
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def case_specs() -> list[CaseSpec]:
    return [
        CaseSpec(
            name="finance_signed_return",
            domain="finance",
            adapter="TradingBridge",
            task_kind="learn",
            uses_trading_bridge=True,
            should_learn=True,
        ),
        CaseSpec(
            name="sensor_control",
            domain="sensor_control",
            adapter="SensorControlAdapter",
            task_kind="learn",
            uses_trading_bridge=False,
            should_learn=True,
        ),
        CaseSpec(
            name="finance_zero_signal",
            domain="finance",
            adapter="TradingBridge",
            task_kind="zero",
            uses_trading_bridge=True,
            should_learn=False,
            control_kind="zero",
        ),
        CaseSpec(
            name="sensor_zero_signal",
            domain="sensor_control",
            adapter="SensorControlAdapter",
            task_kind="zero",
            uses_trading_bridge=False,
            should_learn=False,
            control_kind="zero",
        ),
        CaseSpec(
            name="finance_shuffled_label",
            domain="finance",
            adapter="TradingBridge",
            task_kind="shuffled",
            uses_trading_bridge=True,
            should_learn=False,
            control_kind="shuffled",
        ),
        CaseSpec(
            name="sensor_shuffled_label",
            domain="sensor_control",
            adapter="SensorControlAdapter",
            task_kind="shuffled",
            uses_trading_bridge=False,
            should_learn=False,
            control_kind="shuffled",
        ),
    ]


def run_domain_transfer(args: argparse.Namespace, output_dir: Path) -> list[TestResult]:
    results: list[TestResult] = []
    for spec in case_specs():
        print(f"[tier4.11] {spec.name}: running {len(seeds_from_args(args))} seeds...", flush=True)
        rows_all: list[dict[str, Any]] = []
        summaries: list[dict[str, Any]] = []
        artifacts: dict[str, str] = {}
        for seed in seeds_from_args(args):
            rows, summary = run_case_seed(spec=spec, seed=seed, args=args)
            csv_path = output_dir / f"{spec.name}_seed{seed}_timeseries.csv"
            png_path = output_dir / f"{spec.name}_seed{seed}_timeseries.png"
            write_csv(csv_path, rows)
            plot_case(rows, png_path, f"Tier 4.11 {spec.name} seed {seed}")
            artifacts[f"seed_{seed}_timeseries_csv"] = str(csv_path)
            if png_path.exists():
                artifacts[f"seed_{seed}_timeseries_png"] = str(png_path)
            rows_all.extend(rows)
            summaries.append(summary)

        aggregate = aggregate_case(spec, summaries)
        criteria = case_criteria(spec, aggregate, args)
        status, failure_reason = pass_fail(criteria)
        result = TestResult(
            name=spec.name,
            status=status,
            summary={
                "aggregate": aggregate,
                "seed_summaries": summaries,
            },
            criteria=criteria,
            artifacts=artifacts,
            failure_reason=failure_reason,
        )
        results.append(result)
        print(f"[tier4.11] {spec.name}: {status.upper()} {failure_reason}", flush=True)
        if args.stop_on_fail and not result.passed:
            break
    summary_plot = output_dir / "domain_transfer_summary.png"
    plot_summary(results, summary_plot)
    return results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Tier 4.11 CRA domain-transfer tests.")
    parser.add_argument("--backend", choices=["nest", "brian2", "mock"], default="nest")
    parser.add_argument("--steps", type=int, default=220)
    parser.add_argument("--base-seed", type=int, default=42)
    parser.add_argument("--seed-count", type=int, default=3)
    parser.add_argument("--task-seed", type=int, default=11_411)
    parser.add_argument("--population-size", type=int, default=8)
    parser.add_argument("--amplitude", type=float, default=DEFAULT_AMPLITUDE)
    parser.add_argument("--dt-seconds", type=float, default=DEFAULT_DT_SECONDS)
    parser.add_argument("--delay", type=int, default=3)
    parser.add_argument("--period", type=int, default=5)
    parser.add_argument("--readout-lr", type=float, default=0.10)
    parser.add_argument("--delayed-readout-lr", type=float, default=0.05)
    parser.add_argument("--sensory-noise-fraction", type=float, default=0.10)
    parser.add_argument("--stop-on-fail", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=None)

    parser.add_argument("--learn-all-accuracy-threshold", type=float, default=0.58)
    parser.add_argument("--learn-tail-accuracy-threshold", type=float, default=0.62)
    parser.add_argument("--learn-abs-corr-threshold", type=float, default=0.05)
    parser.add_argument("--zero-max-abs-dopamine", type=float, default=1e-12)
    parser.add_argument("--shuffled-max-accuracy", type=float, default=0.62)
    parser.add_argument("--shuffled-max-abs-corr", type=float, default=0.25)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.steps <= 0:
        parser.error("--steps must be positive")
    if args.seed_count <= 0:
        parser.error("--seed-count must be positive")
    if args.population_size <= 0:
        parser.error("--population-size must be positive")
    if args.delay <= 0 or args.period <= args.delay:
        parser.error("--period must exceed --delay")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = args.output_dir or (ROOT / "controlled_test_output" / f"tier4_11_{timestamp}")
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    results = run_domain_transfer(args, output_dir)
    overall_passed = bool(results) and all(r.passed for r in results) and len(results) == len(case_specs())

    summary_csv_path = output_dir / "tier4_11_summary.csv"
    manifest_path = output_dir / "tier4_11_results.json"
    report_path = output_dir / "tier4_11_report.md"
    write_csv(summary_csv_path, summary_rows(results))
    write_json(
        manifest_path,
        {
            "generated_at_utc": utc_now(),
            "tier": "Tier 4.11 - domain transfer",
            "backend": args.backend,
            "command": " ".join(sys.argv),
            "output_dir": str(output_dir),
            "status": "pass" if overall_passed else "fail",
            "results": [r.to_dict() for r in results],
        },
    )
    write_report(
        path=report_path,
        results=results,
        manifest_path=manifest_path,
        summary_csv_path=summary_csv_path,
        output_dir=output_dir,
        args=args,
    )
    write_json(
        ROOT / "controlled_test_output" / "tier4_11_latest_manifest.json",
        {
            "generated_at_utc": utc_now(),
            "manifest": str(manifest_path),
            "report": str(report_path),
            "summary_csv": str(summary_csv_path),
            "status": "pass" if overall_passed else "fail",
        },
    )
    print(f"[tier4.11] wrote report: {report_path}", flush=True)
    return 0 if overall_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
