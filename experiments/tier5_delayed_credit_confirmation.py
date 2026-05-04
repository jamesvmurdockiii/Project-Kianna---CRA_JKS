#!/usr/bin/env python3
"""Tier 5.4 delayed-credit confirmation.

Tier 5.3 identified stronger delayed-credit learning (`delayed_lr_0_20`) as the
leading candidate fix for CRA's longer-run weakness. Tier 5.4 confirms whether
that candidate survives a tighter comparison against current CRA and the same
external baselines at 960 and 1500 steps.
"""

from __future__ import annotations

import argparse
import copy
import csv
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
except Exception as exc:  # pragma: no cover
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
    TaskStream,
    TestResult,
    aggregate_summaries,
    build_parser as build_tier5_1_parser,
    build_tasks,
    parse_models,
    recovery_steps,
    run_baseline_case,
)
from tier5_cra_failure_analysis import (  # noqa: E402
    VariantSpec,
    run_cra_variant,
)


TIER = "Tier 5.4 - Delayed-Credit Confirmation"
DEFAULT_RUN_LENGTHS = "960,1500"
DEFAULT_TASKS = "delayed_cue,hard_noisy_switching"
DEFAULT_MODELS = "random_sign,sign_persistence,online_perceptron,online_logistic_regression,echo_state_network,small_gru,stdp_only_snn,evolutionary_population"
CURRENT_VARIANT = VariantSpec(
    "cra_current",
    "cra_control",
    "Current v0.3 CRA configuration used as the no-retune reference.",
    {},
)
CANDIDATE_VARIANT = VariantSpec(
    "cra_delayed_lr_0_20",
    "delayed_credit_candidate",
    "Tier 5.3 candidate fix: stronger matured delayed-credit readout learning.",
    {"learning.delayed_readout_learning_rate": 0.20},
)
CRA_VARIANTS = (CURRENT_VARIANT, CANDIDATE_VARIANT)


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
        return ["delayed_cue", "hard_noisy_switching"]
    return names


def max_value(values: list[Any]) -> float | None:
    vals = [float(v) for v in values if v is not None and v != ""]
    return max(vals) if vals else None


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
    if model.startswith("cra_"):
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
            "configured_dopamine_tau",
            "configured_initial_population",
            "configured_max_population",
        ]
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
        for key in keys:
            vals = [s.get(key) for s in summaries]
            aggregate[f"{key}_mean"] = mean(vals)
            aggregate[f"{key}_std"] = stdev(vals)
            aggregate[f"{key}_min"] = min_value(vals)
            aggregate[f"{key}_max"] = max_value(vals)
    else:
        aggregate = aggregate_summaries(representative_task, model, summaries, rows_by_seed, args)
        aggregate["run_length_steps"] = int(run_length)
        aggregate["task"] = task_name
        aggregate["display_name"] = representative_task.display_name
        aggregate["domain"] = representative_task.domain
        aggregate["model_family"] = model_family
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


def summary_csv_rows(aggregates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fields = [
        "run_length_steps",
        "task",
        "model",
        "model_family",
        "runs",
        "all_accuracy_mean",
        "all_accuracy_std",
        "tail_accuracy_mean",
        "tail_accuracy_std",
        "tail_accuracy_min",
        "prediction_target_corr_mean",
        "tail_prediction_target_corr_mean",
        "mean_recovery_steps",
        "max_recovery_steps",
        "runtime_seconds_mean",
        "runtime_seconds_std",
        "evaluation_count_mean",
        "final_n_alive_mean",
        "total_births_mean",
        "total_deaths_mean",
        "max_abs_dopamine_mean",
        "configured_delayed_readout_lr_mean",
    ]
    return [{field: row.get(field) for field in fields} for row in aggregates]


def build_confirmations(aggregates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    keys = sorted({(int(a["run_length_steps"]), a["task"]) for a in aggregates})
    for run_length, task in keys:
        task_aggs = [a for a in aggregates if int(a["run_length_steps"]) == run_length and a["task"] == task]
        current = next((a for a in task_aggs if a["model"] == CURRENT_VARIANT.name), None)
        candidate = next((a for a in task_aggs if a["model"] == CANDIDATE_VARIANT.name), None)
        externals = [a for a in task_aggs if not str(a["model"]).startswith("cra_")]
        if not current or not candidate or not externals:
            continue
        best_tail = max(externals, key=lambda a: -1.0 if a.get("tail_accuracy_mean") is None else float(a["tail_accuracy_mean"]))
        best_corr = max(externals, key=lambda a: abs(float(a.get("prediction_target_corr_mean") or 0.0)))
        tail_values = [float(a.get("tail_accuracy_mean") or 0.0) for a in externals]
        corr_values = [abs(float(a.get("prediction_target_corr_mean") or 0.0)) for a in externals]
        runtime_values = [float(a.get("runtime_seconds_mean") or 0.0) for a in externals]
        external_median_tail = float(np.median(tail_values)) if tail_values else None
        external_median_abs_corr = float(np.median(corr_values)) if corr_values else None
        external_median_runtime = float(np.median(runtime_values)) if runtime_values else None
        candidate_tail = float(candidate.get("tail_accuracy_mean") or 0.0)
        current_tail = float(current.get("tail_accuracy_mean") or 0.0)
        candidate_corr_abs = abs(float(candidate.get("prediction_target_corr_mean") or 0.0))
        current_corr_abs = abs(float(current.get("prediction_target_corr_mean") or 0.0))
        row = {
            "run_length_steps": int(run_length),
            "task": task,
            "current_cra_tail_accuracy_mean": current.get("tail_accuracy_mean"),
            "candidate_cra_tail_accuracy_mean": candidate.get("tail_accuracy_mean"),
            "candidate_tail_accuracy_std": candidate.get("tail_accuracy_std"),
            "candidate_tail_accuracy_min": candidate.get("tail_accuracy_min"),
            "candidate_tail_delta_vs_current": candidate_tail - current_tail,
            "current_cra_abs_corr_mean": current_corr_abs,
            "candidate_cra_abs_corr_mean": candidate_corr_abs,
            "candidate_abs_corr_delta_vs_current": candidate_corr_abs - current_corr_abs,
            "external_median_tail_accuracy": external_median_tail,
            "best_external_tail_accuracy_mean": best_tail.get("tail_accuracy_mean"),
            "best_external_tail_model": best_tail.get("model"),
            "external_median_abs_corr": external_median_abs_corr,
            "best_external_abs_corr_mean": abs(float(best_corr.get("prediction_target_corr_mean") or 0.0)),
            "best_external_corr_model": best_corr.get("model"),
            "candidate_tail_delta_vs_external_median": None if external_median_tail is None else candidate_tail - external_median_tail,
            "candidate_tail_delta_vs_best_external": candidate_tail - float(best_tail.get("tail_accuracy_mean") or 0.0),
            "candidate_abs_corr_delta_vs_external_median": None if external_median_abs_corr is None else candidate_corr_abs - external_median_abs_corr,
            "candidate_abs_corr_delta_vs_best_external": candidate_corr_abs - abs(float(best_corr.get("prediction_target_corr_mean") or 0.0)),
            "current_mean_recovery_steps": current.get("mean_recovery_steps"),
            "candidate_mean_recovery_steps": candidate.get("mean_recovery_steps"),
            "candidate_runtime_seconds_mean": candidate.get("runtime_seconds_mean"),
            "external_median_runtime_seconds": external_median_runtime,
        }
        recovery_candidates = [a for a in externals if a.get("mean_recovery_steps") is not None]
        if recovery_candidates:
            best_recovery = min(recovery_candidates, key=lambda a: float(a["mean_recovery_steps"]))
            recovery_values = [float(a["mean_recovery_steps"]) for a in recovery_candidates]
            row.update(
                {
                    "external_median_recovery_steps": float(np.median(recovery_values)),
                    "best_external_recovery_model": best_recovery.get("model"),
                    "best_external_mean_recovery_steps": best_recovery.get("mean_recovery_steps"),
                    "candidate_recovery_delta_vs_current": (
                        None
                        if current.get("mean_recovery_steps") is None or candidate.get("mean_recovery_steps") is None
                        else float(current["mean_recovery_steps"]) - float(candidate["mean_recovery_steps"])
                    ),
                    "candidate_recovery_delta_vs_external_median": float(np.median(recovery_values)) - float(candidate.get("mean_recovery_steps") or 0.0),
                    "candidate_recovery_delta_vs_best_external": float(best_recovery.get("mean_recovery_steps") or 0.0) - float(candidate.get("mean_recovery_steps") or 0.0),
                }
            )
        rows.append(row)
    return rows


def build_task_findings(confirmations: list[dict[str, Any]], args: argparse.Namespace) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for task in sorted({row["task"] for row in confirmations}):
        rows = sorted([row for row in confirmations if row["task"] == task], key=lambda r: int(r["run_length_steps"]))
        if not rows:
            continue
        candidate_tails = [float(row.get("candidate_cra_tail_accuracy_mean") or 0.0) for row in rows]
        tail_deltas_current = [float(row.get("candidate_tail_delta_vs_current") or 0.0) for row in rows]
        tail_deltas_median = [float(row.get("candidate_tail_delta_vs_external_median") or 0.0) for row in rows]
        tail_deltas_best = [float(row.get("candidate_tail_delta_vs_best_external") or 0.0) for row in rows]
        final = rows[-1]
        beats_median_all = all(delta >= -args.median_tolerance for delta in tail_deltas_median)
        beats_best_all = all(delta >= -args.best_tolerance for delta in tail_deltas_best)
        no_regression = all(delta >= -args.regression_tolerance for delta in tail_deltas_current)
        near_one = all(tail >= args.delayed_cue_tail_threshold for tail in candidate_tails) if task == "delayed_cue" else None
        variance_ok = all(float(row.get("candidate_tail_accuracy_std") or 0.0) <= args.max_tail_accuracy_std for row in rows)
        if task == "delayed_cue":
            classification = "confirmed" if near_one and no_regression and variance_ok else "not_confirmed"
        elif task == "hard_noisy_switching":
            classification = "confirmed_vs_median" if beats_median_all and no_regression and variance_ok else "not_confirmed"
            if beats_best_all and classification == "confirmed_vs_median":
                classification = "confirmed_vs_best_external"
        else:
            classification = "diagnostic_only"
        findings.append(
            {
                "task": task,
                "classification": classification,
                "run_lengths": ",".join(str(row["run_length_steps"]) for row in rows),
                "candidate_tail_min_across_lengths": min(candidate_tails) if candidate_tails else None,
                "candidate_tail_final": final.get("candidate_cra_tail_accuracy_mean"),
                "candidate_tail_delta_vs_current_min": min(tail_deltas_current) if tail_deltas_current else None,
                "candidate_tail_delta_vs_external_median_min": min(tail_deltas_median) if tail_deltas_median else None,
                "candidate_tail_delta_vs_best_external_min": min(tail_deltas_best) if tail_deltas_best else None,
                "candidate_tail_std_max": max([float(row.get("candidate_tail_accuracy_std") or 0.0) for row in rows], default=None),
                "near_one_tail_all_lengths": near_one,
                "beats_external_median_all_lengths": beats_median_all,
                "beats_best_external_all_lengths": beats_best_all,
                "no_regression_vs_current_all_lengths": no_regression,
                "variance_acceptable": variance_ok,
                "final_best_external_tail_model": final.get("best_external_tail_model"),
                "final_best_external_tail_accuracy": final.get("best_external_tail_accuracy_mean"),
                "final_candidate_recovery_steps": final.get("candidate_mean_recovery_steps"),
                "final_external_median_recovery_steps": final.get("external_median_recovery_steps"),
            }
        )
    return findings


def evaluate_tier(
    *,
    aggregates: list[dict[str, Any]],
    confirmations: list[dict[str, Any]],
    findings: list[dict[str, Any]],
    observed_runs: int,
    run_lengths: list[int],
    args: argparse.Namespace,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    tasks = selected_task_names(args.tasks)
    external_models = parse_models(args.models)
    seeds = seeds_from_args(args)
    expected_runs = len(run_lengths) * len(tasks) * len(seeds) * (len(CRA_VARIANTS) + len(external_models))
    expected_cells = len(run_lengths) * len(tasks) * (len(CRA_VARIANTS) + len(external_models))
    expected_confirmations = len(run_lengths) * len(tasks)
    observed_cells = len(aggregates)
    observed_lengths = sorted({int(a["run_length_steps"]) for a in aggregates})
    by_task = {row["task"]: row for row in findings}
    delayed = by_task.get("delayed_cue", {})
    hard = by_task.get("hard_noisy_switching", {})
    delayed_pass = bool(delayed.get("near_one_tail_all_lengths")) and bool(delayed.get("no_regression_vs_current_all_lengths"))
    hard_pass = bool(hard.get("beats_external_median_all_lengths")) and bool(hard.get("no_regression_vs_current_all_lengths"))
    variance_pass = all(bool(row.get("variance_acceptable")) for row in findings)
    summary = {
        "expected_runs": expected_runs,
        "observed_runs": observed_runs,
        "expected_cells": expected_cells,
        "observed_cells": observed_cells,
        "expected_confirmation_rows": expected_confirmations,
        "observed_confirmation_rows": len(confirmations),
        "tasks": tasks,
        "seeds": seeds,
        "run_lengths": run_lengths,
        "cra_variants": [variant.name for variant in CRA_VARIANTS],
        "external_models": external_models,
        "candidate_variant": CANDIDATE_VARIANT.name,
        "delayed_cue_confirmed": delayed_pass,
        "hard_noisy_switching_confirmed_vs_external_median": hard_pass,
        "hard_noisy_switching_confirmed_vs_best_external": bool(hard.get("beats_best_external_all_lengths")),
        "variance_acceptable_all_tasks": variance_pass,
        "claim_boundary": "Controlled software confirmation only; Tier 4.16 should proceed only if candidate confirmation holds and superiority is claimed only if best-external comparisons are nonnegative.",
        "findings": findings,
    }
    criteria = [
        criterion("full delayed-credit confirmation matrix completed", observed_runs, "==", expected_runs, observed_runs == expected_runs),
        criterion("all aggregate cells produced", observed_cells, "==", expected_cells, observed_cells == expected_cells),
        criterion("all requested run lengths represented", observed_lengths, "==", run_lengths, observed_lengths == run_lengths),
        criterion("confirmation rows generated", len(confirmations), "==", expected_confirmations, len(confirmations) == expected_confirmations),
        criterion("delayed_cue stays near 1.0 tail accuracy", delayed.get("candidate_tail_min_across_lengths"), ">=", args.delayed_cue_tail_threshold, delayed_pass),
        criterion("hard_noisy_switching beats external median", hard.get("candidate_tail_delta_vs_external_median_min"), ">=", -args.median_tolerance, hard_pass),
        criterion("candidate does not regress versus current CRA", min([float(row.get("candidate_tail_delta_vs_current_min") or 0.0) for row in findings], default=0.0), ">=", -args.regression_tolerance, all(bool(row.get("no_regression_vs_current_all_lengths")) for row in findings)),
        criterion("variance across seeds acceptable", max([float(row.get("candidate_tail_std_max") or 0.0) for row in findings], default=0.0), "<=", args.max_tail_accuracy_std, variance_pass),
    ]
    return criteria, summary


def plot_confirmation(confirmations: list[dict[str, Any]], path: Path) -> None:
    if plt is None or not confirmations:
        return
    tasks = sorted({row["task"] for row in confirmations})
    fig, axes = plt.subplots(len(tasks), 2, figsize=(14, max(4, 4 * len(tasks))), squeeze=False)
    fig.suptitle("Tier 5.4 Delayed-Credit Confirmation", fontsize=15, fontweight="bold")
    for i, task in enumerate(tasks):
        rows = sorted([row for row in confirmations if row["task"] == task], key=lambda r: int(r["run_length_steps"]))
        x = [int(row["run_length_steps"]) for row in rows]
        ax = axes[i][0]
        ax.plot(x, [float(row.get("current_cra_tail_accuracy_mean") or 0.0) for row in rows], marker="o", label="current CRA", color="#6b7280")
        ax.plot(x, [float(row.get("candidate_cra_tail_accuracy_mean") or 0.0) for row in rows], marker="o", label="delayed_lr_0_20", color="#1f6feb")
        ax.plot(x, [float(row.get("external_median_tail_accuracy") or 0.0) for row in rows], marker="o", label="external median", color="#8250df")
        ax.plot(x, [float(row.get("best_external_tail_accuracy_mean") or 0.0) for row in rows], marker="o", label="best external", color="#2f855a")
        ax.set_title(f"{task.replace('_', ' ')} tail accuracy")
        ax.set_xlabel("steps")
        ax.set_ylabel("tail accuracy")
        ax.set_ylim(0, 1.05)
        ax.grid(alpha=0.25)
        ax.legend(fontsize=8)
        ax = axes[i][1]
        ax.axhline(0.0, color="black", linewidth=0.8)
        ax.plot(x, [float(row.get("candidate_tail_delta_vs_current") or 0.0) for row in rows], marker="o", label="vs current CRA", color="#1f6feb")
        ax.plot(x, [float(row.get("candidate_tail_delta_vs_external_median") or 0.0) for row in rows], marker="o", label="vs external median", color="#8250df")
        ax.plot(x, [float(row.get("candidate_tail_delta_vs_best_external") or 0.0) for row in rows], marker="o", label="vs best external", color="#2f855a")
        ax.set_title(f"{task.replace('_', ' ')} candidate tail deltas")
        ax.set_xlabel("steps")
        ax.set_ylabel("positive means candidate better")
        ax.grid(alpha=0.25)
        ax.legend(fontsize=8)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_seed_variance(aggregates: list[dict[str, Any]], path: Path) -> None:
    if plt is None or not aggregates:
        return
    rows = [row for row in aggregates if row["model"] in {CURRENT_VARIANT.name, CANDIDATE_VARIANT.name}]
    labels = [f"{r['task']}\n{r['run_length_steps']}\n{r['model'].replace('cra_', '')}" for r in rows]
    means = [float(r.get("tail_accuracy_mean") or 0.0) for r in rows]
    stds = [float(r.get("tail_accuracy_std") or 0.0) for r in rows]
    fig, ax = plt.subplots(figsize=(max(12, len(rows) * 0.65), 5))
    ax.bar(range(len(rows)), means, yerr=stds, color=["#6b7280" if r["model"] == CURRENT_VARIANT.name else "#1f6feb" for r in rows], capsize=3)
    ax.set_title("Tier 5.4 CRA Tail Accuracy Mean +/- Seed Std")
    ax.set_ylabel("tail accuracy")
    ax.set_ylim(0, 1.05)
    ax.set_xticks(range(len(rows)))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def write_report(path: Path, result: TestResult, confirmations: list[dict[str, Any]], findings: list[dict[str, Any]], args: argparse.Namespace, run_lengths: list[int], output_dir: Path) -> None:
    overall = "PASS" if result.passed else "FAIL"
    lines = [
        "# Tier 5.4 Delayed-Credit Confirmation Findings",
        "",
        f"- Generated: `{utc_now()}`",
        f"- Status: **{overall}**",
        f"- CRA backend: `{args.backend}`",
        f"- Seeds: `{', '.join(str(s) for s in seeds_from_args(args))}`",
        f"- Run lengths: `{', '.join(str(s) for s in run_lengths)}`",
        f"- Tasks: `{args.tasks}`",
        f"- Candidate: `{CANDIDATE_VARIANT.name}`",
        f"- Output directory: `{output_dir}`",
        "",
        "Tier 5.4 confirms whether the Tier 5.3 delayed-credit candidate survives a direct comparison against current CRA and the external baselines at 960 and 1500 steps.",
        "",
        "## Claim Boundary",
        "",
        "- This is controlled software evidence, not hardware evidence.",
        "- Passing confirms the delayed-credit candidate under these tasks/run lengths; it does not automatically authorize a superiority claim.",
        "- Superiority over external baselines may be claimed only where the candidate also beats the best external baseline, not merely the median.",
        "- If this passes, the next hardware step is Tier 4.16 using the confirmed delayed-credit setting.",
        "",
        "## Task Findings",
        "",
        "| Task | Classification | Min candidate tail | Final candidate tail | Min delta vs current | Min delta vs median | Min delta vs best | Max seed std |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in findings:
        lines.append(
            "| "
            f"{row['task']} | `{row['classification']}` | "
            f"{markdown_value(row.get('candidate_tail_min_across_lengths'))} | "
            f"{markdown_value(row.get('candidate_tail_final'))} | "
            f"{markdown_value(row.get('candidate_tail_delta_vs_current_min'))} | "
            f"{markdown_value(row.get('candidate_tail_delta_vs_external_median_min'))} | "
            f"{markdown_value(row.get('candidate_tail_delta_vs_best_external_min'))} | "
            f"{markdown_value(row.get('candidate_tail_std_max'))} |"
        )
    lines.extend(
        [
            "",
            "## Confirmation Rows",
            "",
            "| Steps | Task | Current CRA tail | Candidate tail | External median | Best external | Best model | Delta vs current | Delta vs median | Delta vs best |",
            "| ---: | --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |",
        ]
    )
    for row in sorted(confirmations, key=lambda r: (r["task"], int(r["run_length_steps"]))):
        lines.append(
            "| "
            f"{row['run_length_steps']} | {row['task']} | "
            f"{markdown_value(row.get('current_cra_tail_accuracy_mean'))} | "
            f"{markdown_value(row.get('candidate_cra_tail_accuracy_mean'))} | "
            f"{markdown_value(row.get('external_median_tail_accuracy'))} | "
            f"{markdown_value(row.get('best_external_tail_accuracy_mean'))} | "
            f"`{row.get('best_external_tail_model')}` | "
            f"{markdown_value(row.get('candidate_tail_delta_vs_current'))} | "
            f"{markdown_value(row.get('candidate_tail_delta_vs_external_median'))} | "
            f"{markdown_value(row.get('candidate_tail_delta_vs_best_external'))} |"
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
            "- `tier5_4_results.json`: machine-readable manifest.",
            "- `tier5_4_summary.csv`: aggregate task/model/run-length metrics.",
            "- `tier5_4_confirmation.csv`: current CRA, candidate, median external, and best external comparison rows.",
            "- `tier5_4_findings.csv`: task-level confirmation findings.",
            "- `tier5_4_confirmation.png`: confirmation curves and deltas.",
            "- `tier5_4_seed_variance.png`: CRA seed variance summary.",
            "- `*_timeseries.csv`: per-run-length/per-task/per-model/per-seed online traces.",
            "",
            "## Plots",
            "",
            "![confirmation](tier5_4_confirmation.png)",
            "",
            "![seed_variance](tier5_4_seed_variance.png)",
            "",
        ]
    )
    if MATPLOTLIB_ERROR:
        lines.append(f"Plotting unavailable: `{MATPLOTLIB_ERROR}`")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def run_tier(args: argparse.Namespace, output_dir: Path, run_lengths: list[int]) -> TestResult:
    external_models = parse_models(args.models)
    summaries_by_cell: dict[tuple[int, str, str], list[dict[str, Any]]] = {}
    rows_by_cell_seed: dict[tuple[int, str, str, int], list[dict[str, Any]]] = {}
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
                for variant in CRA_VARIANTS:
                    print(f"[tier5.4] steps={run_length} task={task.name} model={variant.name} seed={seed}", flush=True)
                    rows, summary = run_cra_variant(task, seed=seed, variant=variant, args=length_args)
                    for row in rows:
                        row["run_length_steps"] = int(run_length)
                        row["model"] = variant.name
                        row["model_family"] = "CRA"
                    summary["run_length_steps"] = int(run_length)
                    summary["model"] = variant.name
                    summary["model_family"] = "CRA"
                    csv_path = output_dir / f"steps{run_length}_{task.name}_{variant.name}_seed{seed}_timeseries.csv"
                    write_csv(csv_path, rows)
                    artifacts[f"steps{run_length}_{task.name}_{variant.name}_seed{seed}_timeseries_csv"] = str(csv_path)
                    summaries_by_cell.setdefault((run_length, task.name, variant.name), []).append(summary)
                    rows_by_cell_seed[(run_length, task.name, variant.name, seed)] = rows
                    observed_runs += 1
                for model in external_models:
                    print(f"[tier5.4] steps={run_length} task={task.name} model={model} seed={seed}", flush=True)
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
        model_family = "CRA" if model.startswith("cra_") else LEARNER_FACTORIES[model].family
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

    confirmations = build_confirmations(aggregates)
    findings = build_task_findings(confirmations, args)
    criteria, tier_summary = evaluate_tier(
        aggregates=aggregates,
        confirmations=confirmations,
        findings=findings,
        observed_runs=observed_runs,
        run_lengths=run_lengths,
        args=args,
    )
    status, failure_reason = pass_fail(criteria)

    summary_csv = output_dir / "tier5_4_summary.csv"
    confirmation_csv = output_dir / "tier5_4_confirmation.csv"
    findings_csv = output_dir / "tier5_4_findings.csv"
    confirmation_plot = output_dir / "tier5_4_confirmation.png"
    variance_plot = output_dir / "tier5_4_seed_variance.png"
    write_csv(summary_csv, summary_csv_rows(aggregates))
    write_csv(confirmation_csv, confirmations)
    write_csv(findings_csv, findings)
    plot_confirmation(confirmations, confirmation_plot)
    plot_seed_variance(aggregates, variance_plot)

    result_artifacts = {
        "summary_csv": str(summary_csv),
        "confirmation_csv": str(confirmation_csv),
        "findings_csv": str(findings_csv),
        "confirmation_png": str(confirmation_plot) if confirmation_plot.exists() else "",
        "seed_variance_png": str(variance_plot) if variance_plot.exists() else "",
    }
    result_artifacts.update(artifacts)
    return TestResult(
        name="delayed_credit_confirmation",
        status=status,
        summary={
            "tier_summary": tier_summary,
            "aggregates": aggregates,
            "confirmations": confirmations,
            "findings": findings,
            "models": [variant.name for variant in CRA_VARIANTS] + external_models,
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
    latest_path = ROOT / "controlled_test_output" / "tier5_4_latest_manifest.json"
    payload = {
        "generated_at_utc": utc_now(),
        "tier": TIER,
        "status": status,
        "output_dir": str(output_dir),
        "manifest": str(manifest_path),
        "report": str(report_path),
        "summary_csv": str(summary_csv),
        "canonical": False,
        "claim": "Latest Tier 5.4 delayed-credit confirmation; promote only after review.",
    }
    write_json(latest_path, payload)


def build_parser() -> argparse.ArgumentParser:
    parser = build_tier5_1_parser()
    parser.description = "Run Tier 5.4 delayed-credit confirmation."
    parser.set_defaults(
        backend="nest",
        tasks=DEFAULT_TASKS,
        models=DEFAULT_MODELS,
        seed_count=3,
        cra_population_size=8,
    )
    parser.add_argument("--run-lengths", default=DEFAULT_RUN_LENGTHS, help="Comma-separated confirmation run lengths")
    parser.add_argument("--delayed-cue-tail-threshold", type=float, default=0.95)
    parser.add_argument("--median-tolerance", type=float, default=0.0)
    parser.add_argument("--best-tolerance", type=float, default=0.0)
    parser.add_argument("--regression-tolerance", type=float, default=0.02)
    parser.add_argument("--max-tail-accuracy-std", type=float, default=0.18)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    run_lengths = parse_run_lengths(args.run_lengths)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = args.output_dir or (ROOT / "controlled_test_output" / f"tier5_4_{timestamp}")
    output_dir.mkdir(parents=True, exist_ok=True)

    result = run_tier(args, output_dir, run_lengths)
    manifest_path = output_dir / "tier5_4_results.json"
    report_path = output_dir / "tier5_4_report.md"
    summary_csv = output_dir / "tier5_4_summary.csv"
    confirmation_csv = output_dir / "tier5_4_confirmation.csv"
    findings_csv = output_dir / "tier5_4_findings.csv"
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
            "findings": result.summary["findings"],
            "runtime_seconds": result.summary["runtime_seconds"],
        },
        "artifacts": {
            "summary_csv": str(summary_csv),
            "confirmation_csv": str(confirmation_csv),
            "findings_csv": str(findings_csv),
            "report_md": str(report_path),
            "confirmation_png": str(output_dir / "tier5_4_confirmation.png"),
            "seed_variance_png": str(output_dir / "tier5_4_seed_variance.png"),
        },
    }
    write_json(manifest_path, json_safe(manifest))
    write_report(report_path, result, result.summary["confirmations"], result.summary["findings"], args, run_lengths, output_dir)
    write_latest(output_dir, report_path, manifest_path, summary_csv, result.status)
    print(
        json.dumps(
            {
                "status": result.status,
                "output_dir": str(output_dir),
                "manifest": str(manifest_path),
                "report": str(report_path),
                "summary_csv": str(summary_csv),
                "confirmation_csv": str(confirmation_csv),
                "findings_csv": str(findings_csv),
                "failure_reason": result.failure_reason,
            },
            indent=2,
        )
    )
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
