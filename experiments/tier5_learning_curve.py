#!/usr/bin/env python3
"""Tier 5.2 learning-curve / run-length sweep for CRA.

Tier 5.1 compared CRA to simpler learners at one fixed horizon. Tier 5.2 asks
whether those findings change as the online stream gets longer. The pass/fail
criteria here are methodological: full matrix completion, complete curve cells,
and documented interpretation. CRA is allowed to lose a task; that is a finding,
not a harness failure.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

# Keep the local NEST/scientific stack usable on macOS when duplicate OpenMP
# runtimes are present. This matches Tier 5.1 and is not used as a tuning knob.
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
from tier5_external_baselines import (  # noqa: E402
    LEARNER_FACTORIES,
    TestResult,
    aggregate_summaries,
    build_parser as build_tier5_1_parser,
    build_tasks,
    parse_models,
    recovery_steps,
    run_baseline_case,
    run_cra_case,
)


TIER = "Tier 5.2 - Learning Curve / Run-Length Sweep"
DEFAULT_RUN_LENGTHS = "120,240,480,960,1500"
DEFAULT_TASKS = "sensor_control,hard_noisy_switching,delayed_cue"


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


def max_value(values: list[Any]) -> float | None:
    vals = [float(v) for v in values if v is not None]
    return max(vals) if vals else None


def aggregate_by_length(
    *,
    run_length: int,
    task_name: str,
    model: str,
    summaries: list[dict[str, Any]],
    rows_by_seed: dict[int, list[dict[str, Any]]],
    task_by_seed: dict[int, Any],
    args: argparse.Namespace,
) -> dict[str, Any]:
    # Reuse Tier 5.1 aggregation for scalar metrics, then repair recovery so it
    # uses each seed's own switch schedule rather than a single representative task.
    representative_task = next(iter(task_by_seed.values()))
    aggregate = aggregate_summaries(representative_task, model, summaries, rows_by_seed, args)
    aggregate["run_length_steps"] = int(run_length)
    aggregate["task"] = task_name
    aggregate["display_name"] = representative_task.display_name
    aggregate["domain"] = representative_task.domain
    aggregate["seeds"] = [int(s.get("seed")) for s in summaries]

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
    if per_seed_recovery:
        aggregate["mean_recovery_steps"] = mean(per_seed_recovery)
        aggregate["max_recovery_steps"] = max(per_seed_recovery)
    else:
        aggregate["mean_recovery_steps"] = None
        aggregate["max_recovery_steps"] = None
    return aggregate


def build_curve_comparisons(aggregates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    comparisons: list[dict[str, Any]] = []
    keys = sorted({(int(a["run_length_steps"]), a["task"]) for a in aggregates})
    for run_length, task in keys:
        task_aggs = [a for a in aggregates if int(a["run_length_steps"]) == run_length and a["task"] == task]
        cra = next((a for a in task_aggs if a["model"] == "cra"), None)
        externals = [a for a in task_aggs if a["model"] != "cra"]
        if not cra or not externals:
            continue
        best_tail = max(externals, key=lambda a: -1.0 if a.get("tail_accuracy_mean") is None else float(a["tail_accuracy_mean"]))
        best_corr = max(externals, key=lambda a: abs(float(a.get("prediction_target_corr_mean") or 0.0)))
        tail_values = [float(a.get("tail_accuracy_mean") or 0.0) for a in externals]
        corr_values = [abs(float(a.get("prediction_target_corr_mean") or 0.0)) for a in externals]
        runtime_values = [float(a.get("runtime_seconds_mean") or 0.0) for a in externals]
        external_median_tail = float(np.median(tail_values)) if tail_values else None
        external_median_abs_corr = float(np.median(corr_values)) if corr_values else None
        external_median_runtime = float(np.median(runtime_values)) if runtime_values else None
        cra_tail = float(cra.get("tail_accuracy_mean") or 0.0)
        cra_corr_abs = abs(float(cra.get("prediction_target_corr_mean") or 0.0))
        row = {
            "run_length_steps": int(run_length),
            "task": task,
            "cra_tail_accuracy_mean": cra.get("tail_accuracy_mean"),
            "cra_all_accuracy_mean": cra.get("all_accuracy_mean"),
            "cra_abs_corr_mean": cra_corr_abs,
            "cra_runtime_seconds_mean": cra.get("runtime_seconds_mean"),
            "best_external_tail_model": best_tail["model"],
            "best_external_tail_accuracy_mean": best_tail.get("tail_accuracy_mean"),
            "best_external_corr_model": best_corr["model"],
            "best_external_abs_corr_mean": abs(float(best_corr.get("prediction_target_corr_mean") or 0.0)),
            "external_median_tail_accuracy": external_median_tail,
            "external_median_abs_corr": external_median_abs_corr,
            "external_median_runtime_seconds": external_median_runtime,
            "cra_tail_minus_best_external": cra_tail - float(best_tail.get("tail_accuracy_mean") or 0.0),
            "cra_tail_minus_external_median": None if external_median_tail is None else cra_tail - external_median_tail,
            "cra_abs_corr_minus_best_external": cra_corr_abs - abs(float(best_corr.get("prediction_target_corr_mean") or 0.0)),
            "cra_abs_corr_minus_external_median": None if external_median_abs_corr is None else cra_corr_abs - external_median_abs_corr,
            "cra_runtime_minus_external_median_seconds": None if external_median_runtime is None else float(cra.get("runtime_seconds_mean") or 0.0) - external_median_runtime,
        }
        if cra.get("mean_recovery_steps") is not None:
            recovery_candidates = [a for a in externals if a.get("mean_recovery_steps") is not None]
            if recovery_candidates:
                best_recovery = min(recovery_candidates, key=lambda a: float(a["mean_recovery_steps"]))
                external_recovery_values = [float(a["mean_recovery_steps"]) for a in recovery_candidates]
                row.update(
                    {
                        "cra_mean_recovery_steps": cra.get("mean_recovery_steps"),
                        "best_external_recovery_model": best_recovery["model"],
                        "best_external_mean_recovery_steps": best_recovery.get("mean_recovery_steps"),
                        "external_median_recovery_steps": float(np.median(external_recovery_values)),
                        "median_recovery_minus_cra": float(np.median(external_recovery_values)) - float(cra["mean_recovery_steps"]),
                        "best_external_recovery_minus_cra": float(best_recovery["mean_recovery_steps"]) - float(cra["mean_recovery_steps"]),
                    }
                )
        comparisons.append(row)
    return comparisons


def slope(xs: list[int], ys: list[float]) -> float | None:
    if len(xs) < 2 or len(ys) < 2:
        return None
    if len(set(xs)) < 2:
        return None
    x = np.asarray(xs, dtype=float)
    y = np.asarray(ys, dtype=float)
    x = x / max(1.0, float(np.max(x)))
    return float(np.polyfit(x, y, 1)[0])


def classify_task_curve(rows: list[dict[str, Any]], *, acc_edge: float, corr_edge: float, recovery_edge: float) -> dict[str, Any]:
    ordered = sorted(rows, key=lambda r: int(r["run_length_steps"]))
    lengths = [int(r["run_length_steps"]) for r in ordered]
    tail_edges = [float(r.get("cra_tail_minus_external_median") or 0.0) for r in ordered]
    corr_edges = [float(r.get("cra_abs_corr_minus_external_median") or 0.0) for r in ordered]
    recovery_edges = [float(r.get("median_recovery_minus_cra") or 0.0) for r in ordered]
    final = ordered[-1]
    final_tail_edge = tail_edges[-1]
    final_corr_edge = corr_edges[-1]
    final_recovery_edge = recovery_edges[-1]
    initial_tail_edge = tail_edges[0]
    final_has_edge = (
        final_tail_edge >= acc_edge
        or final_corr_edge >= corr_edge
        or final_recovery_edge >= recovery_edge
    )
    if final_has_edge and (slope(lengths, tail_edges) or 0.0) > 0.0:
        classification = "cra_edge_emerges_or_grows"
    elif final_has_edge:
        classification = "cra_edge_persists"
    elif initial_tail_edge >= acc_edge and final_tail_edge < 0.0:
        classification = "cra_edge_disappears"
    elif final_tail_edge <= -0.10 and final_corr_edge <= -0.02 and final_recovery_edge < recovery_edge:
        classification = "external_baselines_dominate_final"
    else:
        classification = "mixed_or_neutral"
    return {
        "task": final["task"],
        "min_run_length_steps": lengths[0],
        "max_run_length_steps": lengths[-1],
        "initial_cra_tail_minus_external_median": initial_tail_edge,
        "final_cra_tail_minus_external_median": final_tail_edge,
        "final_cra_abs_corr_minus_external_median": final_corr_edge,
        "final_median_recovery_minus_cra": final_recovery_edge,
        "tail_edge_slope_normalized": slope(lengths, tail_edges),
        "abs_corr_edge_slope_normalized": slope(lengths, corr_edges),
        "recovery_edge_slope_normalized": slope(lengths, recovery_edges),
        "cra_tail_at_final_length": final.get("cra_tail_accuracy_mean"),
        "best_external_tail_at_final_length": final.get("best_external_tail_accuracy_mean"),
        "best_external_tail_model_at_final_length": final.get("best_external_tail_model"),
        "classification": classification,
    }


def analyze_curves(comparisons: list[dict[str, Any]], args: argparse.Namespace) -> list[dict[str, Any]]:
    analysis: list[dict[str, Any]] = []
    for task in sorted({row["task"] for row in comparisons}):
        rows = [row for row in comparisons if row["task"] == task]
        if rows:
            analysis.append(
                classify_task_curve(
                    rows,
                    acc_edge=args.cra_median_accuracy_edge,
                    corr_edge=args.cra_median_corr_edge,
                    recovery_edge=args.cra_median_recovery_edge,
                )
            )
    return analysis


def summary_csv_rows(aggregates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for a in aggregates:
        rows.append(
            {
                "run_length_steps": a["run_length_steps"],
                "task": a["task"],
                "model": a["model"],
                "model_family": a.get("model_family"),
                "runs": a["runs"],
                "all_accuracy_mean": a.get("all_accuracy_mean"),
                "all_accuracy_std": a.get("all_accuracy_std"),
                "tail_accuracy_mean": a.get("tail_accuracy_mean"),
                "tail_accuracy_std": a.get("tail_accuracy_std"),
                "prediction_target_corr_mean": a.get("prediction_target_corr_mean"),
                "tail_prediction_target_corr_mean": a.get("tail_prediction_target_corr_mean"),
                "mean_recovery_steps": a.get("mean_recovery_steps"),
                "max_recovery_steps": a.get("max_recovery_steps"),
                "runtime_seconds_mean": a.get("runtime_seconds_mean"),
                "runtime_seconds_std": a.get("runtime_seconds_std"),
                "evaluation_count_mean": a.get("evaluation_count_mean"),
                "final_n_alive_mean": a.get("final_n_alive_mean"),
                "total_births_mean": a.get("total_births_mean"),
                "total_deaths_mean": a.get("total_deaths_mean"),
                "max_abs_dopamine_mean": a.get("max_abs_dopamine_mean"),
            }
        )
    return rows


def plot_learning_curves(comparisons: list[dict[str, Any]], path: Path) -> None:
    if plt is None or not comparisons:
        return
    tasks = sorted({row["task"] for row in comparisons})
    fig, axes = plt.subplots(len(tasks), 3, figsize=(17, max(4, 4 * len(tasks))), squeeze=False)
    fig.suptitle("Tier 5.2 Learning Curves", fontsize=15, fontweight="bold")
    for i, task in enumerate(tasks):
        rows = sorted([row for row in comparisons if row["task"] == task], key=lambda r: int(r["run_length_steps"]))
        x = [int(r["run_length_steps"]) for r in rows]
        panels = [
            (
                axes[i][0],
                "tail accuracy",
                [float(r.get("cra_tail_accuracy_mean") or 0.0) for r in rows],
                [float(r.get("external_median_tail_accuracy") or 0.0) for r in rows],
                [float(r.get("best_external_tail_accuracy_mean") or 0.0) for r in rows],
                "accuracy",
            ),
            (
                axes[i][1],
                "abs corr",
                [float(r.get("cra_abs_corr_mean") or 0.0) for r in rows],
                [float(r.get("external_median_abs_corr") or 0.0) for r in rows],
                [float(r.get("best_external_abs_corr_mean") or 0.0) for r in rows],
                "abs corr",
            ),
            (
                axes[i][2],
                "recovery steps",
                [float(r.get("cra_mean_recovery_steps") or 0.0) for r in rows],
                [float(r.get("external_median_recovery_steps") or 0.0) for r in rows],
                [float(r.get("best_external_mean_recovery_steps") or 0.0) for r in rows],
                "steps (lower is better)",
            ),
        ]
        for ax, title, cra, median, best, ylabel in panels:
            ax.plot(x, cra, marker="o", label="CRA", color="#1f6feb", linewidth=2.0)
            ax.plot(x, median, marker="o", label="external median", color="#8250df", alpha=0.9)
            ax.plot(x, best, marker="o", label="best external", color="#2f855a", alpha=0.9)
            ax.set_title(f"{task.replace('_', ' ')}: {title}")
            ax.set_xlabel("run length (steps)")
            ax.set_ylabel(ylabel)
            ax.grid(alpha=0.25)
            ax.legend(fontsize=8)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_edges(comparisons: list[dict[str, Any]], path: Path) -> None:
    if plt is None or not comparisons:
        return
    tasks = sorted({row["task"] for row in comparisons})
    fig, axes = plt.subplots(len(tasks), 1, figsize=(12, max(4, 3.5 * len(tasks))), squeeze=False)
    fig.suptitle("Tier 5.2 CRA Edge Versus External Median", fontsize=15, fontweight="bold")
    for i, task in enumerate(tasks):
        ax = axes[i][0]
        rows = sorted([row for row in comparisons if row["task"] == task], key=lambda r: int(r["run_length_steps"]))
        x = [int(r["run_length_steps"]) for r in rows]
        ax.axhline(0.0, color="black", linewidth=0.8)
        ax.plot(x, [float(r.get("cra_tail_minus_external_median") or 0.0) for r in rows], marker="o", label="tail acc edge", color="#1f6feb")
        ax.plot(x, [float(r.get("cra_abs_corr_minus_external_median") or 0.0) for r in rows], marker="o", label="abs corr edge", color="#8250df")
        ax.plot(x, [float(r.get("median_recovery_minus_cra") or 0.0) for r in rows], marker="o", label="recovery edge", color="#2f855a")
        ax.set_title(task.replace("_", " "))
        ax.set_xlabel("run length (steps)")
        ax.set_ylabel("positive means CRA better")
        ax.grid(alpha=0.25)
        ax.legend(fontsize=8)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_runtime(aggregates: list[dict[str, Any]], path: Path) -> None:
    if plt is None or not aggregates:
        return
    tasks = sorted({row["task"] for row in aggregates})
    fig, ax = plt.subplots(figsize=(12, 6))
    for task in tasks:
        rows = sorted([row for row in aggregates if row["task"] == task and row["model"] == "cra"], key=lambda r: int(r["run_length_steps"]))
        if rows:
            ax.plot(
                [int(r["run_length_steps"]) for r in rows],
                [float(r.get("runtime_seconds_mean") or 0.0) for r in rows],
                marker="o",
                label=f"CRA {task}",
            )
    ax.set_title("Tier 5.2 CRA Runtime By Run Length")
    ax.set_xlabel("run length (steps)")
    ax.set_ylabel("mean runtime seconds")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def evaluate_tier(
    *,
    aggregates: list[dict[str, Any]],
    comparisons: list[dict[str, Any]],
    analysis: list[dict[str, Any]],
    observed_runs: int,
    args: argparse.Namespace,
    run_lengths: list[int],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    models = parse_models(args.models)
    tasks = selected_task_names(args.tasks)
    seeds = seeds_from_args(args)
    expected_runs = len(run_lengths) * len(tasks) * len(models) * len(seeds)
    expected_cells = len(run_lengths) * len(tasks) * len(models)
    observed_cells = len(aggregates)
    observed_lengths = sorted({int(a["run_length_steps"]) for a in aggregates})
    runtime_values = [a.get("runtime_seconds_mean") for a in aggregates]
    final_length = max(run_lengths)
    final_comparisons = [row for row in comparisons if int(row["run_length_steps"]) == final_length]
    final_advantage_tasks = [
        row["task"]
        for row in final_comparisons
        if float(row.get("cra_tail_minus_external_median") or 0.0) >= args.cra_median_accuracy_edge
        or float(row.get("cra_abs_corr_minus_external_median") or 0.0) >= args.cra_median_corr_edge
        or float(row.get("median_recovery_minus_cra") or 0.0) >= args.cra_median_recovery_edge
    ]
    classifications = {row["task"]: row["classification"] for row in analysis}
    summary = {
        "expected_runs": expected_runs,
        "observed_runs": observed_runs,
        "expected_curve_cells": expected_cells,
        "observed_curve_cells": observed_cells,
        "run_lengths": run_lengths,
        "observed_run_lengths": observed_lengths,
        "models": models,
        "tasks": tasks,
        "seeds": seeds,
        "final_run_length_steps": final_length,
        "final_advantage_tasks": final_advantage_tasks,
        "final_advantage_task_count": len(final_advantage_tasks),
        "task_classifications": classifications,
        "claim_boundary": "Controlled software learning-curve characterization only; not hardware evidence and not a claim that CRA wins every task.",
    }
    criteria = [
        criterion("full run-length/task/model/seed matrix completed", observed_runs, "==", expected_runs, observed_runs == expected_runs),
        criterion("all requested run lengths represented", observed_lengths, "==", run_lengths, observed_lengths == run_lengths),
        criterion("all aggregate curve cells produced", observed_cells, "==", expected_cells, observed_cells == expected_cells),
        criterion("task-level learning-curve interpretations produced", len(analysis), "==", len(tasks), len(analysis) == len(tasks)),
        criterion(
            "runtime recorded for every aggregate cell",
            sum(1 for value in runtime_values if value is not None),
            "==",
            expected_cells,
            sum(1 for value in runtime_values if value is not None) == expected_cells,
        ),
    ]
    return criteria, summary


def write_report(
    path: Path,
    result: TestResult,
    aggregates: list[dict[str, Any]],
    comparisons: list[dict[str, Any]],
    analysis: list[dict[str, Any]],
    args: argparse.Namespace,
    run_lengths: list[int],
    output_dir: Path,
) -> None:
    overall = "PASS" if result.passed else "FAIL"
    final_length = max(run_lengths)
    final_comparisons = [row for row in comparisons if int(row["run_length_steps"]) == final_length]
    lines = [
        "# Tier 5.2 Learning Curve / Run-Length Sweep Findings",
        "",
        f"- Generated: `{utc_now()}`",
        f"- Status: **{overall}**",
        f"- CRA backend: `{args.backend}`",
        f"- Seeds: `{', '.join(str(s) for s in seeds_from_args(args))}`",
        f"- Run lengths: `{', '.join(str(s) for s in run_lengths)}`",
        f"- Tasks: `{args.tasks}`",
        f"- Models: `{args.models}`",
        f"- Output directory: `{output_dir}`",
        "",
        "Tier 5.2 extends Tier 5.1 by repeating the same CRA and external-baseline comparison across multiple online run lengths. It answers whether CRA's hard-task edge grows, disappears, or remains mixed as the stream gets longer.",
        "",
        "## Claim Boundary",
        "",
        "- This is controlled software evidence, not hardware evidence.",
        "- Passing this tier means the learning curves are complete and interpretable; it does not require CRA to win every task.",
        "- A simple learner beating CRA is recorded as a scientific finding, not hidden as a harness failure.",
        "- Tier 4.16 hardware should use the strongest task identified here, not a task chosen by vibes.",
        "",
        "## Task-Level Interpretation",
        "",
        "| Task | Classification | Final CRA tail | Final best external tail | Best model | Final tail edge vs median | Final corr edge vs median | Final recovery edge |",
        "| --- | --- | ---: | ---: | --- | ---: | ---: | ---: |",
    ]
    final_by_task = {row["task"]: row for row in final_comparisons}
    for row in analysis:
        final = final_by_task.get(row["task"], {})
        lines.append(
            "| "
            f"{row['task']} | `{row['classification']}` | "
            f"{markdown_value(row.get('cra_tail_at_final_length'))} | "
            f"{markdown_value(row.get('best_external_tail_at_final_length'))} | "
            f"`{row.get('best_external_tail_model_at_final_length')}` | "
            f"{markdown_value(row.get('final_cra_tail_minus_external_median'))} | "
            f"{markdown_value(row.get('final_cra_abs_corr_minus_external_median'))} | "
            f"{markdown_value(row.get('final_median_recovery_minus_cra'))} |"
        )
    lines.extend(
        [
            "",
            "## Final-Length Comparison",
            "",
            f"Final length: `{final_length}` steps.",
            "",
            "| Task | CRA tail | External median tail | Best external tail | Best external model | CRA runtime s | External median runtime s |",
            "| --- | ---: | ---: | ---: | --- | ---: | ---: |",
        ]
    )
    for row in sorted(final_comparisons, key=lambda r: r["task"]):
        lines.append(
            "| "
            f"{row['task']} | "
            f"{markdown_value(row.get('cra_tail_accuracy_mean'))} | "
            f"{markdown_value(row.get('external_median_tail_accuracy'))} | "
            f"{markdown_value(row.get('best_external_tail_accuracy_mean'))} | "
            f"`{row.get('best_external_tail_model')}` | "
            f"{markdown_value(row.get('cra_runtime_seconds_mean'))} | "
            f"{markdown_value(row.get('external_median_runtime_seconds'))} |"
        )
    lines.extend(
        [
            "",
            "## All Curve Points",
            "",
            "| Steps | Task | CRA tail | External median tail | Tail edge | CRA abs corr | External median abs corr | Corr edge | Recovery edge |",
            "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in sorted(comparisons, key=lambda r: (r["task"], int(r["run_length_steps"]))):
        lines.append(
            "| "
            f"{row['run_length_steps']} | {row['task']} | "
            f"{markdown_value(row.get('cra_tail_accuracy_mean'))} | "
            f"{markdown_value(row.get('external_median_tail_accuracy'))} | "
            f"{markdown_value(row.get('cra_tail_minus_external_median'))} | "
            f"{markdown_value(row.get('cra_abs_corr_mean'))} | "
            f"{markdown_value(row.get('external_median_abs_corr'))} | "
            f"{markdown_value(row.get('cra_abs_corr_minus_external_median'))} | "
            f"{markdown_value(row.get('median_recovery_minus_cra'))} |"
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
            "- `tier5_2_results.json`: machine-readable manifest.",
            "- `tier5_2_summary.csv`: aggregate task/model/run-length metrics.",
            "- `tier5_2_comparisons.csv`: CRA-vs-external comparison for every task and run length.",
            "- `tier5_2_curve_analysis.csv`: task-level interpretation of whether CRA's edge grows, persists, fades, or remains mixed.",
            "- `tier5_2_learning_curves.png`: CRA vs external median/best curves.",
            "- `tier5_2_cra_edges_by_length.png`: CRA edge versus external median by run length.",
            "- `tier5_2_runtime_by_length.png`: CRA runtime by run length.",
            "- `*_timeseries.csv`: per-task/per-model/per-seed/per-length online traces.",
            "",
            "## Plots",
            "",
            "![learning_curves](tier5_2_learning_curves.png)",
            "",
            "![cra_edges](tier5_2_cra_edges_by_length.png)",
            "",
            "![runtime](tier5_2_runtime_by_length.png)",
            "",
        ]
    )
    if MATPLOTLIB_ERROR:
        lines.append(f"Plotting unavailable: `{MATPLOTLIB_ERROR}`")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def run_tier(args: argparse.Namespace, output_dir: Path, run_lengths: list[int]) -> TestResult:
    models = parse_models(args.models)
    summaries_by_cell: dict[tuple[int, str, str], list[dict[str, Any]]] = {}
    rows_by_cell_seed: dict[tuple[int, str, str, int], list[dict[str, Any]]] = {}
    task_by_length_name_seed: dict[tuple[int, str, int], Any] = {}
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
                for model in models:
                    print(f"[tier5.2] steps={run_length} task={task.name} model={model} seed={seed}", flush=True)
                    if model == "cra":
                        rows, summary = run_cra_case(task, seed=seed, args=length_args)
                    else:
                        rows, summary = run_baseline_case(task, model, seed=seed, args=length_args)
                    for row in rows:
                        row["run_length_steps"] = int(run_length)
                    summary["run_length_steps"] = int(run_length)
                    csv_path = output_dir / f"steps{run_length}_{task.name}_{model}_seed{seed}_timeseries.csv"
                    write_csv(csv_path, rows)
                    artifacts[f"steps{run_length}_{task.name}_{model}_seed{seed}_timeseries_csv"] = str(csv_path)
                    summaries_by_cell.setdefault((run_length, task.name, model), []).append(summary)
                    rows_by_cell_seed[(run_length, task.name, model, seed)] = rows
                    observed_runs += 1

    aggregates: list[dict[str, Any]] = []
    for (run_length, task_name, model), summaries in sorted(summaries_by_cell.items()):
        seed_rows = {
            int(summary["seed"]): rows_by_cell_seed[(run_length, task_name, model, int(summary["seed"]))]
            for summary in summaries
        }
        seed_tasks = {
            int(summary["seed"]): task_by_length_name_seed[(run_length, task_name, int(summary["seed"]))]
            for summary in summaries
        }
        aggregates.append(
            aggregate_by_length(
                run_length=run_length,
                task_name=task_name,
                model=model,
                summaries=summaries,
                rows_by_seed=seed_rows,
                task_by_seed=seed_tasks,
                args=args,
            )
        )

    comparisons = build_curve_comparisons(aggregates)
    analysis = analyze_curves(comparisons, args)
    criteria, tier_summary = evaluate_tier(
        aggregates=aggregates,
        comparisons=comparisons,
        analysis=analysis,
        observed_runs=observed_runs,
        args=args,
        run_lengths=run_lengths,
    )
    status, failure_reason = pass_fail(criteria)

    summary_csv = output_dir / "tier5_2_summary.csv"
    comparison_csv = output_dir / "tier5_2_comparisons.csv"
    analysis_csv = output_dir / "tier5_2_curve_analysis.csv"
    learning_plot = output_dir / "tier5_2_learning_curves.png"
    edge_plot = output_dir / "tier5_2_cra_edges_by_length.png"
    runtime_plot = output_dir / "tier5_2_runtime_by_length.png"
    write_csv(summary_csv, summary_csv_rows(aggregates))
    write_csv(comparison_csv, comparisons)
    write_csv(analysis_csv, analysis)
    plot_learning_curves(comparisons, learning_plot)
    plot_edges(comparisons, edge_plot)
    plot_runtime(aggregates, runtime_plot)

    result_artifacts = {
        "summary_csv": str(summary_csv),
        "comparisons_csv": str(comparison_csv),
        "curve_analysis_csv": str(analysis_csv),
        "learning_curves_png": str(learning_plot) if learning_plot.exists() else "",
        "cra_edges_png": str(edge_plot) if edge_plot.exists() else "",
        "runtime_png": str(runtime_plot) if runtime_plot.exists() else "",
    }
    result_artifacts.update(artifacts)
    return TestResult(
        name="learning_curve_run_length_sweep",
        status=status,
        summary={
            "tier_summary": tier_summary,
            "aggregates": aggregates,
            "comparisons": comparisons,
            "curve_analysis": analysis,
            "models": models,
            "seeds": seeds_from_args(args),
            "tasks": selected_task_names(args.tasks),
            "run_lengths": run_lengths,
            "backend": args.backend,
            "runtime_seconds": time.perf_counter() - started,
            "claim_boundary": "Controlled software learning-curve characterization only; not hardware evidence and not proof that CRA wins every task.",
        },
        criteria=criteria,
        artifacts=result_artifacts,
        failure_reason=failure_reason,
    )


def write_latest(output_dir: Path, report_path: Path, manifest_path: Path, summary_csv: Path, status: str) -> None:
    latest_path = ROOT / "controlled_test_output" / "tier5_2_latest_manifest.json"
    payload = {
        "generated_at_utc": utc_now(),
        "tier": TIER,
        "status": status,
        "output_dir": str(output_dir),
        "manifest": str(manifest_path),
        "report": str(report_path),
        "summary_csv": str(summary_csv),
        "canonical": False,
        "claim": "Latest Tier 5.2 learning-curve sweep; promote only after review.",
    }
    write_json(latest_path, payload)


def build_parser() -> argparse.ArgumentParser:
    parser = build_tier5_1_parser()
    parser.description = "Run Tier 5.2 CRA/baseline learning-curve sweeps."
    parser.set_defaults(tasks=DEFAULT_TASKS, models="all", seed_count=3, backend="nest")
    parser.add_argument("--run-lengths", default=DEFAULT_RUN_LENGTHS, help="Comma-separated online run lengths, e.g. 120,240,480,960,1500")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    run_lengths = parse_run_lengths(args.run_lengths)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = args.output_dir or (ROOT / "controlled_test_output" / f"tier5_2_{timestamp}")
    output_dir.mkdir(parents=True, exist_ok=True)

    result = run_tier(args, output_dir, run_lengths)
    manifest_path = output_dir / "tier5_2_results.json"
    report_path = output_dir / "tier5_2_report.md"
    summary_csv = output_dir / "tier5_2_summary.csv"
    comparison_csv = output_dir / "tier5_2_comparisons.csv"
    analysis_csv = output_dir / "tier5_2_curve_analysis.csv"
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
            "tasks": result.summary["tasks"],
            "seeds": result.summary["seeds"],
            "run_lengths": run_lengths,
            "curve_analysis": result.summary["curve_analysis"],
            "runtime_seconds": result.summary["runtime_seconds"],
        },
        "artifacts": {
            "summary_csv": str(summary_csv),
            "comparisons_csv": str(comparison_csv),
            "curve_analysis_csv": str(analysis_csv),
            "report_md": str(report_path),
            "learning_curves_png": str(output_dir / "tier5_2_learning_curves.png"),
            "cra_edges_png": str(output_dir / "tier5_2_cra_edges_by_length.png"),
            "runtime_png": str(output_dir / "tier5_2_runtime_by_length.png"),
        },
    }
    write_json(manifest_path, json_safe(manifest))
    write_report(
        report_path,
        result,
        result.summary["aggregates"],
        result.summary["comparisons"],
        result.summary["curve_analysis"],
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
                "curve_analysis_csv": str(analysis_csv),
                "failure_reason": result.failure_reason,
            },
            indent=2,
        )
    )
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
