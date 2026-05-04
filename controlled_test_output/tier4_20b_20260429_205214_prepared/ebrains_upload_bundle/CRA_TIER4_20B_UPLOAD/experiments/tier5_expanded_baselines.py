#!/usr/bin/env python3
"""Tier 5.5 expanded baseline suite with fairness/statistical reporting.

Tier 5.5 is the first paper-grade baseline gate after the v0.8 hardware-capable
CRA baseline. It is intentionally stricter than Tier 5.1/Tier 5.2:

* identical causal task streams for CRA and every baseline
* delayed feedback only when the consequence matures
* multiple run lengths and seeds
* paired CRA-vs-baseline deltas by seed
* confidence intervals, effect sizes, recovery, and sample-efficiency metrics

A pass does not mean CRA wins everything. A pass means the matrix completed and
CRA has at least one robust, defensible regime against fair external baselines.
If this tier fails, that is a scientific finding and should narrow the paper
claim or trigger targeted mechanism work.
"""

from __future__ import annotations

import argparse
import copy
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
except Exception as exc:  # pragma: no cover - plotting dependency is optional
    plt = None
    MATPLOTLIB_ERROR = str(exc)
else:
    MATPLOTLIB_ERROR = None

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from tier2_learning import criterion, markdown_value, pass_fail, write_csv, write_json  # noqa: E402
from tier4_scaling import mean, min_value, seeds_from_args, stdev  # noqa: E402
from tier5_cra_failure_analysis import VariantSpec, run_cra_variant  # noqa: E402
from tier5_external_baselines import (  # noqa: E402
    LEARNER_FACTORIES,
    TaskStream,
    TestResult,
    build_parser as build_tier5_1_parser,
    build_tasks,
    parse_models,
    recovery_steps,
    run_baseline_case,
)


TIER = "Tier 5.5 - Expanded Baseline Suite"
DEFAULT_RUN_LENGTHS = "120,240,480,960,1500"
DEFAULT_TASKS = "fixed_pattern,delayed_cue,hard_noisy_switching,sensor_control"
DEFAULT_EXTERNAL_MODELS = (
    "random_sign,sign_persistence,online_perceptron,online_logistic_regression,"
    "echo_state_network,small_gru,stdp_only_snn,evolutionary_population"
)

CRA_VARIANT_LIBRARY: dict[str, VariantSpec] = {
    "v0_8": VariantSpec(
        "cra_v0_8_delayed_lr_0_20",
        "CRA",
        "Frozen v0.8 hardware-capable CRA setting: fixed N=8, delayed_lr_0_20, host-side delayed credit.",
        {"learning.delayed_readout_learning_rate": 0.20},
    ),
    "delayed_lr_0_20": VariantSpec(
        "cra_v0_8_delayed_lr_0_20",
        "CRA",
        "Alias for the frozen v0.8 delayed-credit setting.",
        {"learning.delayed_readout_learning_rate": 0.20},
    ),
    "reference_lr_0_05": VariantSpec(
        "cra_reference_lr_0_05",
        "CRA_reference",
        "Pre-confirmation delayed-credit reference used only as a regression/control comparator.",
        {"learning.delayed_readout_learning_rate": 0.05},
    ),
}

METRIC_KEYS = [
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
    "steps_to_threshold",
    "reward_events_to_threshold",
    "area_under_learning_curve",
    "tail_evaluation_count",
]


@dataclass(frozen=True)
class RunKey:
    run_length: int
    task: str
    model: str
    seed: int


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


def parse_run_lengths(raw: str) -> list[int]:
    values: list[int] = []
    for chunk in raw.replace(";", ",").split(","):
        item = chunk.strip()
        if not item:
            continue
        value = int(item)
        if value <= 0:
            raise argparse.ArgumentTypeError("run lengths must be positive integers")
        values.append(value)
    values = sorted(set(values))
    if not values:
        raise argparse.ArgumentTypeError("at least one run length is required")
    return values


def selected_task_names(raw: str) -> list[str]:
    names = [item.strip() for item in raw.split(",") if item.strip()]
    if not names or names == ["all"]:
        return ["fixed_pattern", "delayed_cue", "sensor_control", "hard_noisy_switching"]
    return names


def parse_external_models(raw: str) -> list[str]:
    models = parse_models(raw)
    return [model for model in models if model != "cra"]


def parse_cra_variants(raw: str) -> list[VariantSpec]:
    names = [item.strip() for item in raw.split(",") if item.strip()]
    if not names:
        names = ["v0_8"]
    variants: list[VariantSpec] = []
    for name in names:
        if name not in CRA_VARIANT_LIBRARY:
            known = ", ".join(sorted(CRA_VARIANT_LIBRARY))
            raise argparse.ArgumentTypeError(f"unknown CRA variant {name!r}; known variants: {known}")
        variant = CRA_VARIANT_LIBRARY[name]
        if variant.name not in {v.name for v in variants}:
            variants.append(variant)
    return variants


def finite_values(values: list[Any]) -> list[float]:
    clean: list[float] = []
    for value in values:
        if value is None or value == "":
            continue
        try:
            f = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(f):
            clean.append(f)
    return clean


def median_value(values: list[Any]) -> float | None:
    clean = finite_values(values)
    return None if not clean else float(np.median(clean))


def max_value(values: list[Any]) -> float | None:
    clean = finite_values(values)
    return None if not clean else float(np.max(clean))


def bootstrap_ci(values: list[Any], *, reps: int, ci_level: float, seed: int) -> tuple[float | None, float | None]:
    clean = finite_values(values)
    if not clean:
        return None, None
    if len(clean) == 1 or reps <= 0:
        return clean[0], clean[0]
    rng = np.random.default_rng(seed)
    arr = np.asarray(clean, dtype=float)
    draws = rng.choice(arr, size=(int(reps), arr.size), replace=True)
    means = np.mean(draws, axis=1)
    alpha = max(0.0, min(1.0, 1.0 - float(ci_level)))
    lo = float(np.quantile(means, alpha / 2.0))
    hi = float(np.quantile(means, 1.0 - alpha / 2.0))
    return lo, hi


def cohen_d(values: list[Any]) -> float | None:
    clean = finite_values(values)
    if not clean:
        return None
    if len(clean) < 2:
        return 0.0
    sd = float(np.std(clean, ddof=1))
    if sd <= 1e-12:
        return 0.0
    return float(np.mean(clean) / sd)


def sample_efficiency(rows: list[dict[str, Any]], *, threshold: float, window_trials: int) -> dict[str, Any]:
    eval_rows = [r for r in rows if bool(r.get("target_signal_nonzero", False))]
    if not eval_rows:
        return {
            "steps_to_threshold": None,
            "reward_events_to_threshold": None,
            "area_under_learning_curve": None,
            "tail_evaluation_count": 0,
        }
    correct = np.asarray([1.0 if bool(r.get("strict_direction_correct", False)) else 0.0 for r in eval_rows], dtype=float)
    cumulative = np.cumsum(correct) / np.arange(1, len(correct) + 1, dtype=float)
    area = float(np.mean(cumulative))
    window = max(1, int(window_trials))
    steps_to_threshold: int | None = None
    reward_events_to_threshold: int | None = None
    if len(correct) >= window:
        for idx in range(0, len(correct) - window + 1):
            acc = float(np.mean(correct[idx : idx + window]))
            if acc >= float(threshold):
                steps_to_threshold = int(eval_rows[idx + window - 1]["step"])
                reward_events_to_threshold = int(idx + window)
                break
    tail_start = int((rows[-1].get("step", len(rows) - 1) + 1) * 0.75) if rows else 0
    tail_eval_count = sum(1 for r in eval_rows if int(r.get("step", 0)) >= tail_start)
    return {
        "steps_to_threshold": steps_to_threshold,
        "reward_events_to_threshold": reward_events_to_threshold,
        "area_under_learning_curve": area,
        "tail_evaluation_count": int(tail_eval_count),
    }


def enrich_summary(summary: dict[str, Any], rows: list[dict[str, Any]], args: argparse.Namespace) -> dict[str, Any]:
    enriched = dict(summary)
    enriched.update(
        sample_efficiency(
            rows,
            threshold=float(args.sample_efficiency_threshold),
            window_trials=int(args.sample_efficiency_window_trials),
        )
    )
    return enriched


def aggregate_cell(
    *,
    run_length: int,
    task_name: str,
    model: str,
    model_family: str,
    summaries: list[dict[str, Any]],
    rows_by_seed: dict[int, list[dict[str, Any]]],
    task_by_seed: dict[int, TaskStream],
    args: argparse.Namespace,
) -> dict[str, Any]:
    representative_task = next(iter(task_by_seed.values()))
    aggregate: dict[str, Any] = {
        "run_length_steps": int(run_length),
        "task": task_name,
        "display_name": representative_task.display_name,
        "domain": representative_task.domain,
        "model": model,
        "model_family": model_family,
        "runs": len(summaries),
        "seeds": [int(s.get("seed")) for s in summaries],
    }
    for key in METRIC_KEYS:
        values = [s.get(key) for s in summaries]
        lo, hi = bootstrap_ci(
            values,
            reps=int(args.bootstrap_reps),
            ci_level=float(args.ci_level),
            seed=9300 + int(run_length) + len(task_name) + len(model),
        )
        aggregate[f"{key}_mean"] = mean(values)
        aggregate[f"{key}_median"] = median_value(values)
        aggregate[f"{key}_std"] = stdev(values)
        aggregate[f"{key}_min"] = min_value(values)
        aggregate[f"{key}_max"] = max_value(values)
        aggregate[f"{key}_ci_low"] = lo
        aggregate[f"{key}_ci_high"] = hi

    per_seed_recovery: list[int] = []
    for seed, rows in rows_by_seed.items():
        task = task_by_seed.get(seed)
        if task and task.switch_steps:
            per_seed_recovery.extend(
                recovery_steps(
                    rows,
                    task.switch_steps,
                    window_trials=args.recovery_window_trials,
                    threshold=args.recovery_accuracy_threshold,
                    steps=task.steps,
                )
            )
    aggregate["mean_recovery_steps"] = mean(per_seed_recovery)
    aggregate["median_recovery_steps"] = median_value(per_seed_recovery)
    aggregate["max_recovery_steps"] = max(per_seed_recovery) if per_seed_recovery else None
    return aggregate


def per_seed_summary_rows(summaries_by_cell: dict[tuple[int, str, str], list[dict[str, Any]]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for (run_length, task_name, model), summaries in sorted(summaries_by_cell.items()):
        for summary in sorted(summaries, key=lambda s: int(s.get("seed", -1))):
            rows.append(
                {
                    "run_length_steps": run_length,
                    "task": task_name,
                    "model": model,
                    "model_family": summary.get("model_family"),
                    "seed": int(summary.get("seed")),
                    "all_accuracy": summary.get("all_accuracy"),
                    "tail_accuracy": summary.get("tail_accuracy"),
                    "prediction_target_corr": summary.get("prediction_target_corr"),
                    "tail_prediction_target_corr": summary.get("tail_prediction_target_corr"),
                    "runtime_seconds": summary.get("runtime_seconds"),
                    "evaluation_count": summary.get("evaluation_count"),
                    "steps_to_threshold": summary.get("steps_to_threshold"),
                    "reward_events_to_threshold": summary.get("reward_events_to_threshold"),
                    "area_under_learning_curve": summary.get("area_under_learning_curve"),
                    "tail_evaluation_count": summary.get("tail_evaluation_count"),
                    "final_n_alive": summary.get("final_n_alive"),
                    "total_births": summary.get("total_births"),
                    "total_deaths": summary.get("total_deaths"),
                    "max_abs_dopamine": summary.get("max_abs_dopamine"),
                }
            )
    return rows


def aggregate_csv_rows(aggregates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fields = [
        "run_length_steps",
        "task",
        "model",
        "model_family",
        "runs",
        "all_accuracy_mean",
        "all_accuracy_std",
        "all_accuracy_ci_low",
        "all_accuracy_ci_high",
        "tail_accuracy_mean",
        "tail_accuracy_std",
        "tail_accuracy_min",
        "tail_accuracy_ci_low",
        "tail_accuracy_ci_high",
        "prediction_target_corr_mean",
        "tail_prediction_target_corr_mean",
        "runtime_seconds_mean",
        "evaluation_count_mean",
        "mean_recovery_steps",
        "max_recovery_steps",
        "steps_to_threshold_mean",
        "reward_events_to_threshold_mean",
        "area_under_learning_curve_mean",
        "tail_evaluation_count_mean",
        "final_n_alive_mean",
        "total_births_mean",
        "total_deaths_mean",
        "max_abs_dopamine_mean",
    ]
    return [{field: row.get(field) for field in fields} for row in aggregates]


def values_by_seed(summaries: list[dict[str, Any]], key: str) -> dict[int, float]:
    by_seed: dict[int, float] = {}
    for summary in summaries:
        value = summary.get(key)
        clean = finite_values([value])
        if clean:
            by_seed[int(summary["seed"])] = clean[0]
    return by_seed


def paired_delta(cra_summaries: list[dict[str, Any]], baseline_summaries: list[dict[str, Any]], key: str) -> list[float]:
    left = values_by_seed(cra_summaries, key)
    right = values_by_seed(baseline_summaries, key)
    seeds = sorted(set(left) & set(right))
    return [left[seed] - right[seed] for seed in seeds]


def paired_delta_to_external_median(
    cra_summaries: list[dict[str, Any]],
    external_summaries_by_model: dict[str, list[dict[str, Any]]],
    key: str,
) -> list[float]:
    cra_by_seed = values_by_seed(cra_summaries, key)
    external_by_model_seed = {model: values_by_seed(summaries, key) for model, summaries in external_summaries_by_model.items()}
    deltas: list[float] = []
    for seed, cra_value in sorted(cra_by_seed.items()):
        external_values = [by_seed[seed] for by_seed in external_by_model_seed.values() if seed in by_seed]
        if external_values:
            deltas.append(cra_value - float(np.median(external_values)))
    return deltas


def delta_stats(prefix: str, deltas: list[float], args: argparse.Namespace) -> dict[str, Any]:
    lo, hi = bootstrap_ci(deltas, reps=int(args.bootstrap_reps), ci_level=float(args.ci_level), seed=12881 + len(prefix))
    clean = finite_values(deltas)
    return {
        f"{prefix}_mean": mean(clean),
        f"{prefix}_median": median_value(clean),
        f"{prefix}_std": stdev(clean),
        f"{prefix}_min": min_value(clean),
        f"{prefix}_ci_low": lo,
        f"{prefix}_ci_high": hi,
        f"{prefix}_cohen_d": cohen_d(clean),
        f"{prefix}_fraction_positive": None if not clean else float(np.mean([v > 0.0 for v in clean])),
        f"{prefix}_n": len(clean),
    }


def build_comparisons(
    aggregates: list[dict[str, Any]],
    summaries_by_cell: dict[tuple[int, str, str], list[dict[str, Any]]],
    cra_models: list[str],
    external_models: list[str],
    args: argparse.Namespace,
) -> list[dict[str, Any]]:
    comparisons: list[dict[str, Any]] = []
    keys = sorted({(int(a["run_length_steps"]), a["task"]) for a in aggregates})
    for run_length, task in keys:
        cell_aggs = [a for a in aggregates if int(a["run_length_steps"]) == run_length and a["task"] == task]
        external_aggs = [a for a in cell_aggs if a["model"] in external_models]
        if not external_aggs:
            continue
        best_tail = max(external_aggs, key=lambda a: -1.0 if a.get("tail_accuracy_mean") is None else float(a["tail_accuracy_mean"]))
        best_corr = max(external_aggs, key=lambda a: abs(float(a.get("prediction_target_corr_mean") or 0.0)))
        recovery_candidates = [a for a in external_aggs if a.get("mean_recovery_steps") is not None]
        best_recovery = min(recovery_candidates, key=lambda a: float(a["mean_recovery_steps"])) if recovery_candidates else None
        external_tail_values = [float(a.get("tail_accuracy_mean") or 0.0) for a in external_aggs]
        external_corr_values = [abs(float(a.get("prediction_target_corr_mean") or 0.0)) for a in external_aggs]
        external_runtime_values = [float(a.get("runtime_seconds_mean") or 0.0) for a in external_aggs]
        external_auc_values = [float(a.get("area_under_learning_curve_mean") or 0.0) for a in external_aggs]
        external_eff_values = finite_values([a.get("reward_events_to_threshold_mean") for a in external_aggs])
        external_summaries_by_model = {
            model: summaries_by_cell.get((run_length, task, model), []) for model in external_models
        }
        for cra_model in cra_models:
            cra = next((a for a in cell_aggs if a["model"] == cra_model), None)
            if not cra:
                continue
            cra_summaries = summaries_by_cell.get((run_length, task, cra_model), [])
            best_tail_summaries = summaries_by_cell.get((run_length, task, best_tail["model"]), [])
            tail_vs_best = paired_delta(cra_summaries, best_tail_summaries, "tail_accuracy")
            tail_vs_median = paired_delta_to_external_median(cra_summaries, external_summaries_by_model, "tail_accuracy")
            corr_vs_best = paired_delta(cra_summaries, summaries_by_cell.get((run_length, task, best_corr["model"]), []), "prediction_target_corr")
            auc_vs_median = paired_delta_to_external_median(cra_summaries, external_summaries_by_model, "area_under_learning_curve")
            cra_tail = float(cra.get("tail_accuracy_mean") or 0.0)
            cra_corr_abs = abs(float(cra.get("prediction_target_corr_mean") or 0.0))
            cra_auc = float(cra.get("area_under_learning_curve_mean") or 0.0)
            row: dict[str, Any] = {
                "run_length_steps": int(run_length),
                "task": task,
                "cra_model": cra_model,
                "cra_tail_accuracy_mean": cra.get("tail_accuracy_mean"),
                "cra_tail_accuracy_ci_low": cra.get("tail_accuracy_ci_low"),
                "cra_tail_accuracy_ci_high": cra.get("tail_accuracy_ci_high"),
                "cra_all_accuracy_mean": cra.get("all_accuracy_mean"),
                "cra_abs_corr_mean": cra_corr_abs,
                "cra_runtime_seconds_mean": cra.get("runtime_seconds_mean"),
                "cra_area_under_learning_curve_mean": cra.get("area_under_learning_curve_mean"),
                "cra_reward_events_to_threshold_mean": cra.get("reward_events_to_threshold_mean"),
                "best_external_tail_model": best_tail["model"],
                "best_external_tail_accuracy_mean": best_tail.get("tail_accuracy_mean"),
                "best_external_corr_model": best_corr["model"],
                "best_external_abs_corr_mean": abs(float(best_corr.get("prediction_target_corr_mean") or 0.0)),
                "external_median_tail_accuracy": float(np.median(external_tail_values)) if external_tail_values else None,
                "external_median_abs_corr": float(np.median(external_corr_values)) if external_corr_values else None,
                "external_median_runtime_seconds": float(np.median(external_runtime_values)) if external_runtime_values else None,
                "external_median_area_under_learning_curve": float(np.median(external_auc_values)) if external_auc_values else None,
                "external_median_reward_events_to_threshold": float(np.median(external_eff_values)) if external_eff_values else None,
                "cra_tail_minus_best_external": cra_tail - float(best_tail.get("tail_accuracy_mean") or 0.0),
                "cra_tail_minus_external_median": cra_tail - float(np.median(external_tail_values)) if external_tail_values else None,
                "cra_abs_corr_minus_best_external": cra_corr_abs - abs(float(best_corr.get("prediction_target_corr_mean") or 0.0)),
                "cra_abs_corr_minus_external_median": cra_corr_abs - float(np.median(external_corr_values)) if external_corr_values else None,
                "cra_auc_minus_external_median": cra_auc - float(np.median(external_auc_values)) if external_auc_values else None,
            }
            row.update(delta_stats("paired_tail_delta_vs_best", tail_vs_best, args))
            row.update(delta_stats("paired_tail_delta_vs_external_median", tail_vs_median, args))
            row.update(delta_stats("paired_corr_delta_vs_best", corr_vs_best, args))
            row.update(delta_stats("paired_auc_delta_vs_external_median", auc_vs_median, args))
            if best_recovery is not None and cra.get("mean_recovery_steps") is not None:
                row.update(
                    {
                        "cra_mean_recovery_steps": cra.get("mean_recovery_steps"),
                        "best_external_recovery_model": best_recovery.get("model"),
                        "best_external_mean_recovery_steps": best_recovery.get("mean_recovery_steps"),
                        "external_median_recovery_steps": float(np.median([float(a["mean_recovery_steps"]) for a in recovery_candidates])),
                        "median_recovery_minus_cra": float(np.median([float(a["mean_recovery_steps"]) for a in recovery_candidates])) - float(cra["mean_recovery_steps"]),
                        "best_external_recovery_minus_cra": float(best_recovery["mean_recovery_steps"]) - float(cra["mean_recovery_steps"]),
                    }
                )
            row["robust_advantage_regime"] = bool(
                (float(row.get("paired_tail_delta_vs_external_median_mean") or 0.0) >= args.min_tail_edge)
                or (float(row.get("cra_abs_corr_minus_external_median") or 0.0) >= args.min_corr_edge)
                or (float(row.get("median_recovery_minus_cra") or 0.0) >= args.min_recovery_edge)
                or (float(row.get("cra_auc_minus_external_median") or 0.0) >= args.min_auc_edge)
            )
            row["not_dominated_by_best_external"] = bool(
                float(row.get("paired_tail_delta_vs_best_mean") or 0.0) >= -args.best_tail_tolerance
                or float(row.get("cra_abs_corr_minus_best_external") or 0.0) >= -args.best_corr_tolerance
                or float(row.get("best_external_recovery_minus_cra") or 0.0) >= -args.best_recovery_tolerance
            )
            comparisons.append(row)
    return comparisons


def comparison_csv_rows(comparisons: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fields = [
        "run_length_steps",
        "task",
        "cra_model",
        "cra_tail_accuracy_mean",
        "cra_tail_accuracy_ci_low",
        "cra_tail_accuracy_ci_high",
        "external_median_tail_accuracy",
        "best_external_tail_accuracy_mean",
        "best_external_tail_model",
        "cra_tail_minus_external_median",
        "cra_tail_minus_best_external",
        "paired_tail_delta_vs_external_median_mean",
        "paired_tail_delta_vs_external_median_ci_low",
        "paired_tail_delta_vs_external_median_ci_high",
        "paired_tail_delta_vs_external_median_cohen_d",
        "paired_tail_delta_vs_best_mean",
        "paired_tail_delta_vs_best_ci_low",
        "paired_tail_delta_vs_best_ci_high",
        "paired_tail_delta_vs_best_cohen_d",
        "cra_abs_corr_mean",
        "external_median_abs_corr",
        "best_external_abs_corr_mean",
        "best_external_corr_model",
        "cra_abs_corr_minus_external_median",
        "cra_abs_corr_minus_best_external",
        "cra_area_under_learning_curve_mean",
        "external_median_area_under_learning_curve",
        "cra_auc_minus_external_median",
        "cra_reward_events_to_threshold_mean",
        "external_median_reward_events_to_threshold",
        "cra_mean_recovery_steps",
        "external_median_recovery_steps",
        "median_recovery_minus_cra",
        "best_external_recovery_minus_cra",
        "cra_runtime_seconds_mean",
        "external_median_runtime_seconds",
        "robust_advantage_regime",
        "not_dominated_by_best_external",
    ]
    return [{field: row.get(field) for field in fields} for row in comparisons]


def plot_edge_summary(comparisons: list[dict[str, Any]], path: Path) -> None:
    if plt is None or not comparisons:
        return
    tasks = sorted({row["task"] for row in comparisons})
    run_lengths = sorted({int(row["run_length_steps"]) for row in comparisons})
    fig, axes = plt.subplots(len(tasks), 1, figsize=(12, max(4, 3.5 * len(tasks))), squeeze=False)
    fig.suptitle("Tier 5.5 CRA v0.8 Edge Versus External Median", fontsize=15, fontweight="bold")
    for i, task in enumerate(tasks):
        ax = axes[i][0]
        rows = sorted([row for row in comparisons if row["task"] == task], key=lambda r: int(r["run_length_steps"]))
        x = [int(row["run_length_steps"]) for row in rows]
        ax.axhline(0.0, color="black", linewidth=0.8)
        ax.plot(x, [float(row.get("cra_tail_minus_external_median") or 0.0) for row in rows], marker="o", label="tail accuracy edge", color="#1f6feb")
        ax.plot(x, [float(row.get("cra_abs_corr_minus_external_median") or 0.0) for row in rows], marker="o", label="abs corr edge", color="#8250df")
        ax.plot(x, [float(row.get("cra_auc_minus_external_median") or 0.0) for row in rows], marker="o", label="AULC edge", color="#2f855a")
        ax.set_title(task.replace("_", " "))
        ax.set_xticks(run_lengths)
        ax.set_xlabel("run length (steps)")
        ax.set_ylabel("positive means CRA better")
        ax.grid(alpha=0.25)
        ax.legend(fontsize=8)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(path, dpi=160)
    plt.close(fig)


def build_fairness_contract(args: argparse.Namespace, run_lengths: list[int], cra_variants: list[VariantSpec], external_models: list[str]) -> dict[str, Any]:
    return {
        "claim_boundary": "Controlled software baseline comparison only; not hardware evidence and not proof of universal superiority.",
        "baseline_version": "CRA evidence baseline v0.8",
        "causal_rules": [
            "all models receive the same task stream for the same task seed and seed",
            "models predict before seeing the current evaluation label",
            "delayed tasks update only when the feedback_due_step matures",
            "no baseline receives future labels, switch locations, or reward signs early",
            "CRA and baselines share train/evaluation windows and task masks",
        ],
        "matrix": {
            "run_lengths": run_lengths,
            "tasks": selected_task_names(args.tasks),
            "seeds": seeds_from_args(args),
            "cra_variants": [variant.name for variant in cra_variants],
            "external_models": external_models,
        },
        "fixed_hyperparameters": {
            "cra_population_size": args.cra_population_size,
            "cra_readout_lr": args.cra_readout_lr,
            "cra_delayed_readout_lr_arg_default": args.cra_delayed_readout_lr,
            "feature_history": args.feature_history,
            "perceptron_lr": args.perceptron_lr,
            "logistic_lr": args.logistic_lr,
            "reservoir_hidden": args.reservoir_hidden,
            "reservoir_lr": args.reservoir_lr,
            "reservoir_leak": args.reservoir_leak,
            "reservoir_radius": args.reservoir_radius,
            "gru_hidden": args.gru_hidden,
            "gru_lr": args.gru_lr,
            "stdp_hidden": args.stdp_hidden,
            "stdp_lr": args.stdp_lr,
            "evo_population": args.evo_population,
            "evo_mutation": args.evo_mutation,
        },
        "deferred_reviewer_defense_baselines": [
            "surrogate_gradient_snn",
            "ann_trained_readout",
            "ann_to_snn_converted_when_task_compatible",
            "liquid_state_machine_variant",
            "contextual_bandit_or_actor_critic_for_action_tasks",
        ],
        "notes": [
            "Tier 5.6 must audit hyperparameter budgets before final paper claims.",
            "If Tier 5.5 fails to find a robust advantage regime, narrow the claim or run targeted mechanism diagnostics before adding architecture features.",
        ],
    }


def evaluate_tier(
    *,
    aggregates: list[dict[str, Any]],
    comparisons: list[dict[str, Any]],
    observed_runs: int,
    run_lengths: list[int],
    cra_variants: list[VariantSpec],
    external_models: list[str],
    args: argparse.Namespace,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    tasks = selected_task_names(args.tasks)
    seeds = seeds_from_args(args)
    expected_runs = len(run_lengths) * len(tasks) * len(seeds) * (len(cra_variants) + len(external_models))
    expected_cells = len(run_lengths) * len(tasks) * (len(cra_variants) + len(external_models))
    expected_comparison_rows = len(run_lengths) * len(tasks) * len(cra_variants)
    observed_lengths = sorted({int(a["run_length_steps"]) for a in aggregates})
    fixed_external = [a for a in aggregates if a["task"] == "fixed_pattern" and a["model"] in external_models]
    best_fixed = max([float(a.get("tail_accuracy_mean") or 0.0) for a in fixed_external], default=None)
    advantage_rows = [row for row in comparisons if bool(row.get("robust_advantage_regime"))]
    hard_rows = [row for row in comparisons if row["task"] in {"delayed_cue", "hard_noisy_switching", "sensor_control"}]
    not_dominated = [row for row in hard_rows if bool(row.get("not_dominated_by_best_external"))]
    ci_rows = [row for row in comparisons if row.get("paired_tail_delta_vs_external_median_ci_low") is not None]
    summary = {
        "expected_runs": expected_runs,
        "observed_runs": observed_runs,
        "expected_cells": expected_cells,
        "observed_cells": len(aggregates),
        "expected_comparison_rows": expected_comparison_rows,
        "observed_comparison_rows": len(comparisons),
        "run_lengths": run_lengths,
        "observed_run_lengths": observed_lengths,
        "tasks": tasks,
        "seeds": seeds,
        "cra_variants": [variant.name for variant in cra_variants],
        "external_models": external_models,
        "robust_advantage_regime_count": len(advantage_rows),
        "robust_advantage_regimes": [
            {"run_length_steps": row["run_length_steps"], "task": row["task"], "cra_model": row["cra_model"]}
            for row in advantage_rows
        ],
        "not_dominated_hard_regime_count": len(not_dominated),
        "best_fixed_external_tail_accuracy": best_fixed,
        "claim_boundary": "Controlled software expanded-baseline comparison; not hardware evidence, not full hyperparameter fairness audit, and not proof of universal superiority.",
    }
    fixed_requested = "fixed_pattern" in tasks
    fixed_pass = (not fixed_requested) or (best_fixed is not None and best_fixed >= args.fixed_external_tail_threshold)
    criteria = [
        criterion("full expanded baseline run matrix completed", observed_runs, "==", expected_runs, observed_runs == expected_runs),
        criterion("all aggregate cells produced", len(aggregates), "==", expected_cells, len(aggregates) == expected_cells),
        criterion("all requested run lengths represented", observed_lengths, "==", run_lengths, observed_lengths == run_lengths),
        criterion("all comparison rows produced", len(comparisons), "==", expected_comparison_rows, len(comparisons) == expected_comparison_rows),
        criterion(
            "simple external baseline learns fixed-pattern sanity task",
            best_fixed,
            ">=",
            args.fixed_external_tail_threshold,
            fixed_pass,
            "Skipped if fixed_pattern is not part of this run.",
        ),
        criterion(
            "paired confidence intervals produced for comparisons",
            len(ci_rows),
            "==",
            expected_comparison_rows,
            len(ci_rows) == expected_comparison_rows,
        ),
        criterion(
            "CRA has at least one robust advantage regime",
            len(advantage_rows),
            ">=",
            args.min_advantage_regimes,
            len(advantage_rows) >= args.min_advantage_regimes,
            "Set --min-advantage-regimes 0 for smoke runs only.",
        ),
        criterion(
            "CRA is not dominated on most hard/adaptive regimes",
            len(not_dominated),
            ">=",
            max(0, len(hard_rows) - args.allowed_dominated_hard_regimes),
            len(not_dominated) >= max(0, len(hard_rows) - args.allowed_dominated_hard_regimes),
        ),
    ]
    return criteria, summary


def write_report(
    path: Path,
    result: TestResult,
    aggregates: list[dict[str, Any]],
    comparisons: list[dict[str, Any]],
    fairness_contract: dict[str, Any],
    args: argparse.Namespace,
    run_lengths: list[int],
    output_dir: Path,
) -> None:
    overall = "PASS" if result.passed else "FAIL"
    lines = [
        "# Tier 5.5 Expanded Baseline Suite Findings",
        "",
        f"- Generated: `{utc_now()}`",
        f"- Status: **{overall}**",
        f"- CRA backend: `{args.backend}`",
        f"- Seeds: `{', '.join(str(s) for s in seeds_from_args(args))}`",
        f"- Run lengths: `{', '.join(str(v) for v in run_lengths)}`",
        f"- Tasks: `{args.tasks}`",
        f"- Output directory: `{output_dir}`",
        "",
        "Tier 5.5 compares the locked CRA v0.8 delayed-credit configuration against fair external baselines across run lengths and seeds. It exports paired seed deltas, confidence intervals, effect sizes, recovery, runtime, and sample-efficiency metrics.",
        "",
        "## Claim Boundary",
        "",
        "- This is controlled software evidence, not hardware evidence.",
        "- Passing does not mean CRA wins every task or every metric.",
        "- A strong paper claim requires Tier 5.6 hyperparameter fairness audit after this suite.",
        "- Reviewer-defense baselines that are not implemented here are listed as deferred, not silently claimed.",
        "",
        "## Fairness Contract",
        "",
    ]
    for rule in fairness_contract["causal_rules"]:
        lines.append(f"- {rule}")
    lines.extend(
        [
            "",
            "## CRA Versus External Baselines",
            "",
            "| Steps | Task | CRA | CRA tail | Median external tail | Best external tail | Best model | Paired delta vs median | CI low | CI high | d | Robust edge | Not dominated |",
            "| ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- | --- |",
        ]
    )
    for row in sorted(comparisons, key=lambda r: (r["task"], int(r["run_length_steps"]), r["cra_model"])):
        lines.append(
            "| "
            f"{row['run_length_steps']} | {row['task']} | `{row['cra_model']}` | "
            f"{markdown_value(row.get('cra_tail_accuracy_mean'))} | "
            f"{markdown_value(row.get('external_median_tail_accuracy'))} | "
            f"{markdown_value(row.get('best_external_tail_accuracy_mean'))} | "
            f"`{row.get('best_external_tail_model')}` | "
            f"{markdown_value(row.get('paired_tail_delta_vs_external_median_mean'))} | "
            f"{markdown_value(row.get('paired_tail_delta_vs_external_median_ci_low'))} | "
            f"{markdown_value(row.get('paired_tail_delta_vs_external_median_ci_high'))} | "
            f"{markdown_value(row.get('paired_tail_delta_vs_external_median_cohen_d'))} | "
            f"{'yes' if row.get('robust_advantage_regime') else 'no'} | "
            f"{'yes' if row.get('not_dominated_by_best_external') else 'no'} |"
        )
    lines.extend(
        [
            "",
            "## Aggregate Cells",
            "",
            "| Steps | Task | Model | Family | Runs | Tail acc | Tail CI | Corr | AULC | Reward events to threshold | Runtime s |",
            "| ---: | --- | --- | --- | ---: | ---: | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in sorted(aggregates, key=lambda r: (r["task"], int(r["run_length_steps"]), r["model"])):
        lines.append(
            "| "
            f"{row['run_length_steps']} | {row['task']} | `{row['model']}` | {row.get('model_family')} | {row.get('runs')} | "
            f"{markdown_value(row.get('tail_accuracy_mean'))} | "
            f"[{markdown_value(row.get('tail_accuracy_ci_low'))}, {markdown_value(row.get('tail_accuracy_ci_high'))}] | "
            f"{markdown_value(row.get('prediction_target_corr_mean'))} | "
            f"{markdown_value(row.get('area_under_learning_curve_mean'))} | "
            f"{markdown_value(row.get('reward_events_to_threshold_mean'))} | "
            f"{markdown_value(row.get('runtime_seconds_mean'))} |"
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
            "- `tier5_5_results.json`: machine-readable manifest.",
            "- `tier5_5_summary.csv`: aggregate task/model/run-length statistics.",
            "- `tier5_5_comparisons.csv`: CRA-vs-external paired comparison rows.",
            "- `tier5_5_per_seed.csv`: per-seed audit table.",
            "- `tier5_5_fairness_contract.json`: causal/fairness contract for the run.",
            "- `tier5_5_edge_summary.png`: CRA edge versus external median by task/run length.",
            "- `*_timeseries.csv`: per-run traces for reproducibility.",
            "",
            "## Plots",
            "",
            "![edge_summary](tier5_5_edge_summary.png)",
            "",
        ]
    )
    if MATPLOTLIB_ERROR:
        lines.append(f"Plotting unavailable: `{MATPLOTLIB_ERROR}`")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def run_tier(args: argparse.Namespace, output_dir: Path, run_lengths: list[int], cra_variants: list[VariantSpec]) -> TestResult:
    external_models = parse_external_models(args.models)
    cra_model_names = [variant.name for variant in cra_variants]
    summaries_by_cell: dict[tuple[int, str, str], list[dict[str, Any]]] = {}
    rows_by_cell_seed: dict[RunKey, list[dict[str, Any]]] = {}
    task_by_length_name_seed: dict[tuple[int, str, int], TaskStream] = {}
    artifacts: dict[str, str] = {}
    observed_runs = 0
    started = time.perf_counter()

    for run_length in run_lengths:
        length_args = copy.copy(args)
        length_args.steps = int(run_length)
        for seed in seeds_from_args(args):
            tasks = build_tasks(length_args, seed=length_args.task_seed + seed)
            for task in tasks:
                task_by_length_name_seed[(run_length, task.name, seed)] = task
                for variant in cra_variants:
                    print(f"[tier5.5] steps={run_length} task={task.name} model={variant.name} seed={seed}", flush=True)
                    rows, summary = run_cra_variant(task, seed=seed, variant=variant, args=length_args)
                    for row in rows:
                        row["run_length_steps"] = int(run_length)
                        row["model"] = variant.name
                        row["model_family"] = variant.group
                    summary = enrich_summary(summary, rows, args)
                    summary["run_length_steps"] = int(run_length)
                    summary["model"] = variant.name
                    summary["model_family"] = variant.group
                    csv_path = output_dir / f"steps{run_length}_{task.name}_{variant.name}_seed{seed}_timeseries.csv"
                    write_csv(csv_path, rows)
                    artifacts[f"steps{run_length}_{task.name}_{variant.name}_seed{seed}_timeseries_csv"] = str(csv_path)
                    summaries_by_cell.setdefault((run_length, task.name, variant.name), []).append(summary)
                    rows_by_cell_seed[RunKey(run_length, task.name, variant.name, seed)] = rows
                    observed_runs += 1
                for model in external_models:
                    print(f"[tier5.5] steps={run_length} task={task.name} model={model} seed={seed}", flush=True)
                    rows, summary = run_baseline_case(task, model, seed=seed, args=length_args)
                    for row in rows:
                        row["run_length_steps"] = int(run_length)
                    summary = enrich_summary(summary, rows, args)
                    summary["run_length_steps"] = int(run_length)
                    csv_path = output_dir / f"steps{run_length}_{task.name}_{model}_seed{seed}_timeseries.csv"
                    write_csv(csv_path, rows)
                    artifacts[f"steps{run_length}_{task.name}_{model}_seed{seed}_timeseries_csv"] = str(csv_path)
                    summaries_by_cell.setdefault((run_length, task.name, model), []).append(summary)
                    rows_by_cell_seed[RunKey(run_length, task.name, model, seed)] = rows
                    observed_runs += 1

    aggregates: list[dict[str, Any]] = []
    for (run_length, task_name, model), summaries in sorted(summaries_by_cell.items()):
        seed_rows = {
            int(summary["seed"]): rows_by_cell_seed[RunKey(run_length, task_name, model, int(summary["seed"]))]
            for summary in summaries
        }
        seed_tasks = {
            int(summary["seed"]): task_by_length_name_seed[(run_length, task_name, int(summary["seed"]))]
            for summary in summaries
        }
        model_family = next((variant.group for variant in cra_variants if variant.name == model), None)
        if model_family is None:
            model_family = LEARNER_FACTORIES[model].family
        aggregates.append(
            aggregate_cell(
                run_length=run_length,
                task_name=task_name,
                model=model,
                model_family=model_family,
                summaries=summaries,
                rows_by_seed=seed_rows,
                task_by_seed=seed_tasks,
                args=args,
            )
        )

    comparisons = build_comparisons(aggregates, summaries_by_cell, cra_model_names, external_models, args)
    fairness_contract = build_fairness_contract(args, run_lengths, cra_variants, external_models)
    criteria, tier_summary = evaluate_tier(
        aggregates=aggregates,
        comparisons=comparisons,
        observed_runs=observed_runs,
        run_lengths=run_lengths,
        cra_variants=cra_variants,
        external_models=external_models,
        args=args,
    )
    status, failure_reason = pass_fail(criteria)

    summary_csv = output_dir / "tier5_5_summary.csv"
    comparison_csv = output_dir / "tier5_5_comparisons.csv"
    per_seed_csv = output_dir / "tier5_5_per_seed.csv"
    fairness_json = output_dir / "tier5_5_fairness_contract.json"
    edge_plot = output_dir / "tier5_5_edge_summary.png"
    write_csv(summary_csv, aggregate_csv_rows(aggregates))
    write_csv(comparison_csv, comparison_csv_rows(comparisons))
    write_csv(per_seed_csv, per_seed_summary_rows(summaries_by_cell))
    write_json(fairness_json, json_safe(fairness_contract))
    plot_edge_summary(comparisons, edge_plot)

    result_artifacts = {
        "summary_csv": str(summary_csv),
        "comparisons_csv": str(comparison_csv),
        "per_seed_csv": str(per_seed_csv),
        "fairness_contract_json": str(fairness_json),
        "edge_summary_png": str(edge_plot) if edge_plot.exists() else "",
    }
    result_artifacts.update(artifacts)
    return TestResult(
        name="expanded_baseline_suite",
        status=status,
        summary={
            "tier_summary": tier_summary,
            "aggregates": aggregates,
            "comparisons": comparisons,
            "fairness_contract": fairness_contract,
            "models": cra_model_names + external_models,
            "cra_variants": cra_model_names,
            "external_models": external_models,
            "seeds": seeds_from_args(args),
            "tasks": selected_task_names(args.tasks),
            "run_lengths": run_lengths,
            "backend": args.backend,
            "runtime_seconds": time.perf_counter() - started,
            "claim_boundary": tier_summary["claim_boundary"],
        },
        criteria=criteria,
        artifacts=result_artifacts,
        failure_reason=failure_reason,
    )


def write_latest(output_dir: Path, report_path: Path, manifest_path: Path, summary_csv: Path, status: str) -> None:
    latest_path = ROOT / "controlled_test_output" / "tier5_5_latest_manifest.json"
    payload = {
        "generated_at_utc": utc_now(),
        "tier": TIER,
        "status": status,
        "output_dir": str(output_dir),
        "manifest": str(manifest_path),
        "report": str(report_path),
        "summary_csv": str(summary_csv),
        "canonical": False,
        "claim": "Latest Tier 5.5 expanded-baseline suite; promote only after review and Tier 5.6 fairness audit.",
    }
    write_json(latest_path, payload)


def build_parser() -> argparse.ArgumentParser:
    parser = build_tier5_1_parser()
    parser.description = "Run Tier 5.5 expanded CRA baseline/fairness comparison."
    parser.set_defaults(
        backend="nest",
        tasks=DEFAULT_TASKS,
        models=DEFAULT_EXTERNAL_MODELS,
        seed_count=10,
        cra_population_size=8,
        cra_delayed_readout_lr=0.20,
    )
    parser.add_argument("--run-lengths", default=DEFAULT_RUN_LENGTHS, help="Comma-separated online run lengths")
    parser.add_argument("--cra-variants", default="v0_8", help="Comma-separated CRA variants: v0_8, reference_lr_0_05")
    parser.add_argument("--bootstrap-reps", type=int, default=1000)
    parser.add_argument("--ci-level", type=float, default=0.95)
    parser.add_argument("--sample-efficiency-threshold", type=float, default=0.75)
    parser.add_argument("--sample-efficiency-window-trials", type=int, default=8)
    parser.add_argument("--min-tail-edge", type=float, default=0.02)
    parser.add_argument("--min-corr-edge", type=float, default=0.02)
    parser.add_argument("--min-recovery-edge", type=float, default=2.0)
    parser.add_argument("--min-auc-edge", type=float, default=0.02)
    parser.add_argument("--best-tail-tolerance", type=float, default=0.20)
    parser.add_argument("--best-corr-tolerance", type=float, default=0.05)
    parser.add_argument("--best-recovery-tolerance", type=float, default=-12.0)
    parser.add_argument("--min-advantage-regimes", type=int, default=1)
    parser.add_argument("--allowed-dominated-hard-regimes", type=int, default=2)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    run_lengths = parse_run_lengths(args.run_lengths)
    cra_variants = parse_cra_variants(args.cra_variants)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = args.output_dir or (ROOT / "controlled_test_output" / f"tier5_5_{timestamp}")
    output_dir.mkdir(parents=True, exist_ok=True)

    result = run_tier(args, output_dir, run_lengths, cra_variants)
    manifest_path = output_dir / "tier5_5_results.json"
    report_path = output_dir / "tier5_5_report.md"
    summary_csv = output_dir / "tier5_5_summary.csv"
    comparison_csv = output_dir / "tier5_5_comparisons.csv"
    per_seed_csv = output_dir / "tier5_5_per_seed.csv"
    fairness_json = output_dir / "tier5_5_fairness_contract.json"
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
            "backend": args.backend,
            "models": result.summary["models"],
            "cra_variants": result.summary["cra_variants"],
            "external_models": result.summary["external_models"],
            "tasks": result.summary["tasks"],
            "seeds": result.summary["seeds"],
            "run_lengths": run_lengths,
            "runtime_seconds": result.summary["runtime_seconds"],
        },
        "artifacts": {
            "summary_csv": str(summary_csv),
            "comparisons_csv": str(comparison_csv),
            "per_seed_csv": str(per_seed_csv),
            "fairness_contract_json": str(fairness_json),
            "report_md": str(report_path),
            "edge_summary_png": str(output_dir / "tier5_5_edge_summary.png"),
        },
    }
    write_json(manifest_path, json_safe(manifest))
    write_report(
        report_path,
        result,
        result.summary["aggregates"],
        result.summary["comparisons"],
        result.summary["fairness_contract"],
        args,
        run_lengths,
        output_dir,
    )
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
                "per_seed_csv": str(per_seed_csv),
                "fairness_contract_json": str(fairness_json),
                "failure_reason": result.failure_reason,
            },
            indent=2,
        )
    )
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
