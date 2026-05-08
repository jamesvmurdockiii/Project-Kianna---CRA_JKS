#!/usr/bin/env python3
"""Tier 7.0e - Standard dynamical benchmark rerun with v2.2 length sweep.

This runner keeps Mackey-Glass, Lorenz, and NARMA10 as the public scoreboard and
tests the strongest immediate concern from Tier 7.0: whether the prior negative
result was partly a short-training-budget artifact.

It reuses the promoted v2.2 fading-memory temporal-state path from Tier 5.19c
and evaluates it across predeclared stream lengths. Custom synthetic tasks are
not part of this runner; those remain diagnostics only.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from tier4_scaling import mean, stdev  # noqa: E402
from tier5_19a_temporal_substrate_reference import (  # noqa: E402
    append_timeseries,
    criterion,
    json_safe,
    parse_timescales,
    random_reservoir_features,
    run_online_model,
    run_train_prefix_esn,
    summarize,
    write_csv,
    write_json,
)
from tier5_19b_temporal_substrate_gate import temporal_features_variant  # noqa: E402
from tier5_19c_fading_memory_regression import build_task, run_task as run_full_diagnostic_task  # noqa: E402
from tier7_0b_continuous_regression_failure_analysis import lag_matrix  # noqa: E402
from tier7_0_standard_dynamical_benchmarks import parse_csv, parse_seeds  # noqa: E402


TIER = "Tier 7.0e - Standard Dynamical Benchmark Rerun With v2.2 And Run-Length Sweep"
RUNNER_REVISION = "tier7_0e_standard_dynamical_v2_2_sweep_20260508_0002"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_0e_20260508_standard_dynamical_v2_2_sweep"
DEFAULT_TASKS = "mackey_glass,lorenz,narma10"
DEFAULT_LENGTHS = "720,2000,10000,50000"
STANDARD_THREE = {"mackey_glass", "lorenz", "narma10"}
V22_CANDIDATE = "fading_memory_only_ablation"
RAW_V21 = "raw_cra_v2_1_online"
PUBLIC_BASELINES = {
    "lag_only_online_lms_control",
    "fixed_random_reservoir_online_control",
    "fixed_esn_train_prefix_ridge_baseline",
}
DIAGNOSTIC_REFERENCES = {
    "temporal_full_candidate",
    "temporal_plus_lag_reference",
    "recurrent_hidden_only_ablation",
    "state_reset_ablation",
    "permuted_recurrence_sham",
    "frozen_temporal_state_ablation",
    "shuffled_temporal_state_sham",
    "temporal_shuffled_target_control",
    "temporal_no_plasticity_ablation",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def parse_lengths(raw: str) -> list[int]:
    lengths = [int(item) for item in parse_csv(raw)]
    if not lengths:
        raise ValueError("at least one length is required")
    if any(length < 128 for length in lengths):
        raise ValueError("all lengths must be >= 128 for a stable chronological split")
    return sorted(dict.fromkeys(lengths))


def geomean(values: list[float]) -> float:
    if not values:
        return math.inf
    valid = [float(value) for value in values if value is not None and math.isfinite(float(value)) and float(value) > 0.0]
    if len(valid) != len(values):
        return math.inf
    return float(math.exp(sum(math.log(value) for value in valid) / len(valid)))


def ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None:
        return None
    if not math.isfinite(float(numerator)) or not math.isfinite(float(denominator)):
        return None
    if abs(float(denominator)) < 1e-12:
        return None
    return float(numerator) / float(denominator)


def write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        write_csv(path, [], [])
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def metric(summary_rows: list[dict[str, Any]], task: str, model: str, key: str = "mse_mean") -> float:
    row = next((item for item in summary_rows if item.get("task") == task and item.get("model") == model), None)
    if not row or row.get("status") != "pass" or row.get(key) is None:
        return math.inf
    value = float(row[key])
    return value if math.isfinite(value) else math.inf


def aggregate_by_model(summary_rows: list[dict[str, Any]], tasks: list[str]) -> list[dict[str, Any]]:
    models = sorted({str(row["model"]) for row in summary_rows})
    rows: list[dict[str, Any]] = []
    for model in models:
        mse_values = [metric(summary_rows, task, model, "mse_mean") for task in tasks]
        nmse_values = [metric(summary_rows, task, model, "nmse_mean") for task in tasks]
        rows.append(
            {
                "model": model,
                "geomean_mse": geomean(mse_values),
                "geomean_nmse": geomean(nmse_values),
                "task_count": len(tasks),
                "role": (
                    "v2_2_candidate"
                    if model == V22_CANDIDATE
                    else "raw_v2_1"
                    if model == RAW_V21
                    else "public_baseline"
                    if model in PUBLIC_BASELINES
                    else "diagnostic_reference"
                    if model in DIAGNOSTIC_REFERENCES
                    else "other"
                ),
            }
        )
    public = [row for row in rows if row["role"] in {"public_baseline", "raw_v2_1", "v2_2_candidate"}]
    ranked = sorted(
        [row for row in public if math.isfinite(float(row["geomean_mse"]))],
        key=lambda row: float(row["geomean_mse"]),
    )
    rank_by_model = {row["model"]: idx + 1 for idx, row in enumerate(ranked)}
    for row in rows:
        row["public_rank"] = rank_by_model.get(row["model"])
    return sorted(rows, key=lambda row: (row["public_rank"] or 10_000, row["model"]))


def run_scoreboard_task(
    task: Any,
    *,
    seed: int,
    args: argparse.Namespace,
    capture_timeseries: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Run only the public-scoreboard models needed for long exposure sweeps.

    The full Tier 5.19c diagnostic matrix includes raw CRA trace collection and
    many destructive shams. That is the right tool for mechanism causality, but
    it is intentionally too heavy for 10k/50k public benchmark sweeps. This lean
    lane keeps the same leakage-safe chronological protocol while limiting the
    comparison to the v2.2 candidate and public baseline families.
    """
    rows: list[dict[str, Any]] = []
    timeseries: list[dict[str, Any]] = []
    timescales = parse_timescales(args.temporal_timescales)
    fading = temporal_features_variant(
        task.observed,
        seed=seed,
        train_end=task.train_end,
        timescales=timescales,
        hidden_units=args.temporal_hidden_units,
        recurrent_scale=args.temporal_recurrent_scale,
        input_scale=args.temporal_input_scale,
        hidden_decay=args.temporal_hidden_decay,
        mode="fading_only",
    )
    lag = lag_matrix(task.observed, args.history)
    reservoir = random_reservoir_features(
        task.observed,
        seed=seed,
        units=args.reservoir_units,
        spectral_radius=args.reservoir_spectral_radius,
        input_scale=args.reservoir_input_scale,
    )
    specs: list[tuple[str, np.ndarray, dict[str, Any]]] = [
        ("lag_only_online_lms_control", lag, {"role": "same causal lag budget", "history": int(args.history)}),
        ("fixed_random_reservoir_online_control", reservoir.features, reservoir.diagnostics),
        (V22_CANDIDATE, fading.features, fading.diagnostics),
    ]
    for model, features, diagnostics in specs:
        row, pred = run_online_model(
            task=task,
            seed=seed,
            model=model,
            features=features,
            args=args,
            update_enabled=True,
            diagnostics={**diagnostics, "matrix_mode": "scoreboard"},
        )
        rows.append(row)
        if capture_timeseries:
            append_timeseries(timeseries, task=task, seed=seed, model=model, prediction=pred)
    esn_row, esn_pred = run_train_prefix_esn(task, seed=seed, args=args)
    rows.append(esn_row)
    if capture_timeseries:
        append_timeseries(timeseries, task=task, seed=seed, model="fixed_esn_train_prefix_ridge_baseline", prediction=esn_pred)
    diagnostics = {
        "task": task.name,
        "seed": int(seed),
        "matrix_mode": "scoreboard",
        "raw_cra_v2_1_policy": "omitted from long-run scoreboard mode; use full_diagnostic mode for raw trace/sham matrix",
        "fading_only_feature_count": int(fading.features.shape[1]),
        "lag_feature_count": int(lag.shape[1]),
        "reservoir_feature_count": int(reservoir.features.shape[1]),
    }
    return rows, timeseries, diagnostics


def finite_task_descriptor(task: Any) -> dict[str, Any]:
    observed = np.asarray(task.observed, dtype=float)
    target = np.asarray(task.target, dtype=float)
    return {
        "observed_finite": bool(np.isfinite(observed).all()),
        "target_finite": bool(np.isfinite(target).all()),
        "observed_nonfinite_count": int(np.size(observed) - np.count_nonzero(np.isfinite(observed))),
        "target_nonfinite_count": int(np.size(target) - np.count_nonzero(np.isfinite(target))),
        "target_min": None if not np.isfinite(target).any() else float(np.nanmin(target[np.isfinite(target)])),
        "target_max": None if not np.isfinite(target).any() else float(np.nanmax(target[np.isfinite(target)])),
    }


def run_one_length(length: int, args: argparse.Namespace, output_dir: Path) -> dict[str, Any]:
    tasks = parse_csv(args.tasks)
    seeds = parse_seeds(args)
    length_dir = output_dir / f"length_{length}"
    length_dir.mkdir(parents=True, exist_ok=True)
    all_rows: list[dict[str, Any]] = []
    all_timeseries: list[dict[str, Any]] = []
    capture_timeseries = int(length) <= int(args.timeseries_max_length)
    task_diagnostics: list[dict[str, Any]] = []
    task_descriptors: list[dict[str, Any]] = []
    invalid_tasks: list[dict[str, Any]] = []
    started = time.perf_counter()
    for seed in seeds:
        for task_name in tasks:
            task = build_task(task_name, length, seed, args.horizon)
            finite_descriptor = finite_task_descriptor(task)
            descriptor = {
                "length": int(length),
                "task": task.name,
                "display_name": task.display_name,
                "seed": int(seed),
                "sample_count": int(len(task.target)),
                "train_end": int(task.train_end),
                "test_count": int(len(task.target) - task.train_end),
                "horizon": int(task.horizon),
                "metadata": task.metadata,
                "finite_check": finite_descriptor,
            }
            task_descriptors.append(descriptor)
            write_json(length_dir / f"{task.name}_seed{seed}_task.json", descriptor)
            if not (finite_descriptor["observed_finite"] and finite_descriptor["target_finite"]):
                invalid_tasks.append(descriptor)
                task_diagnostics.append(
                    {
                        "length": int(length),
                        "task": task.name,
                        "seed": int(seed),
                        "status": "invalid_task_stream",
                        "finite_check": finite_descriptor,
                        "reason": "generated observed/target stream contains non-finite values; model scoring skipped",
                    }
                )
                continue
            if args.matrix_mode == "full_diagnostic":
                rows, timeseries, diagnostics = run_full_diagnostic_task(task, seed=seed, args=args)
            else:
                rows, timeseries, diagnostics = run_scoreboard_task(
                    task,
                    seed=seed,
                    args=args,
                    capture_timeseries=capture_timeseries,
                )
            for row in rows:
                row["length"] = int(length)
                row["matrix_mode"] = str(args.matrix_mode)
            for row in timeseries:
                row["length"] = int(length)
                row["matrix_mode"] = str(args.matrix_mode)
            all_rows.extend(rows)
            if capture_timeseries:
                all_timeseries.extend(timeseries)
            task_diagnostics.append({"length": int(length), **diagnostics})
    models = sorted({str(row["model"]) for row in all_rows})
    summary_rows, seed_aggregate_rows, seed_aggregate_summary = summarize(all_rows, tasks, models, seeds)
    for row in summary_rows:
        row["length"] = int(length)
    for row in seed_aggregate_rows:
        row["length"] = int(length)
    for row in seed_aggregate_summary:
        row["length"] = int(length)
    model_aggregate_rows = aggregate_by_model(summary_rows, tasks)
    for row in model_aggregate_rows:
        row["length"] = int(length)
    runtime_seconds = time.perf_counter() - started
    write_rows(length_dir / "tier7_0e_summary.csv", summary_rows)
    write_rows(length_dir / "tier7_0e_seed_aggregate.csv", seed_aggregate_rows)
    write_rows(length_dir / "tier7_0e_model_aggregate.csv", model_aggregate_rows)
    if capture_timeseries:
        write_rows(length_dir / "tier7_0e_timeseries.csv", all_timeseries)
    write_json(
        length_dir / "tier7_0e_length_results.json",
        {
            "tier": TIER,
            "runner_revision": RUNNER_REVISION,
            "length": int(length),
            "tasks": tasks,
            "seeds": seeds,
            "models": models,
            "summary_rows": summary_rows,
            "seed_aggregate_rows": seed_aggregate_rows,
            "seed_aggregate_summary": seed_aggregate_summary,
            "model_aggregate_rows": model_aggregate_rows,
            "task_descriptors": task_descriptors,
            "invalid_tasks": invalid_tasks,
            "task_diagnostics": task_diagnostics,
            "timeseries_policy": {
                "captured": bool(capture_timeseries),
                "timeseries_max_length": int(args.timeseries_max_length),
                "reason": "captured for short audit trace" if capture_timeseries else "omitted to avoid large long-run artifacts",
            },
            "runtime_seconds": runtime_seconds,
        },
    )
    return {
        "length": int(length),
        "runtime_seconds": runtime_seconds,
        "timeseries_captured": bool(capture_timeseries),
        "tasks": tasks,
        "seeds": seeds,
        "models": models,
        "summary_rows": summary_rows,
        "seed_aggregate_rows": seed_aggregate_rows,
        "seed_aggregate_summary": seed_aggregate_summary,
        "model_aggregate_rows": model_aggregate_rows,
        "invalid_tasks": invalid_tasks,
    }


def classify(length_results: list[dict[str, Any]], requested_lengths: list[int]) -> dict[str, Any]:
    by_length: dict[int, dict[str, Any]] = {}
    for result in length_results:
        length = int(result["length"])
        aggregate = {row["model"]: row for row in result["model_aggregate_rows"]}
        candidate = aggregate.get(V22_CANDIDATE, {})
        raw = aggregate.get(RAW_V21, {})
        baselines = [aggregate[model] for model in PUBLIC_BASELINES if model in aggregate]
        best_baseline = min(baselines, key=lambda row: float(row["geomean_mse"]), default=None)
        candidate_mse = candidate.get("geomean_mse")
        raw_mse = raw.get("geomean_mse")
        best_baseline_mse = None if best_baseline is None else best_baseline.get("geomean_mse")
        by_length[length] = {
            "candidate_mse": candidate_mse,
            "raw_v2_1_mse": raw_mse,
            "best_baseline_model": None if best_baseline is None else best_baseline["model"],
            "best_baseline_mse": best_baseline_mse,
            "margin_vs_raw_v2_1": ratio(raw_mse, candidate_mse),
            "margin_vs_best_baseline": ratio(best_baseline_mse, candidate_mse),
            "competitive_with_best_baseline": (
                candidate_mse is not None
                and best_baseline_mse is not None
                and math.isfinite(float(candidate_mse))
                and math.isfinite(float(best_baseline_mse))
                and float(candidate_mse) <= float(best_baseline_mse) * 1.25
            ),
        }
    candidate_curve = [
        (length, values["candidate_mse"])
        for length, values in sorted(by_length.items())
        if values["candidate_mse"] is not None and math.isfinite(float(values["candidate_mse"]))
    ]
    baseline_curve = [
        (length, values["best_baseline_mse"])
        for length, values in sorted(by_length.items())
        if values["best_baseline_mse"] is not None and math.isfinite(float(values["best_baseline_mse"]))
    ]
    candidate_improvement = None
    if len(candidate_curve) >= 2 and float(candidate_curve[-1][1]) > 0:
        candidate_improvement = float(candidate_curve[0][1]) / float(candidate_curve[-1][1])
    baseline_improvement = None
    if len(baseline_curve) >= 2 and float(baseline_curve[-1][1]) > 0:
        baseline_improvement = float(baseline_curve[0][1]) / float(baseline_curve[-1][1])
    longest_length = max(by_length) if by_length else None
    longest = {} if longest_length is None else by_length[longest_length]
    any_competitive = any(bool(values["competitive_with_best_baseline"]) for values in by_length.values())
    any_improves_vs_raw = any(
        values["margin_vs_raw_v2_1"] is not None and float(values["margin_vs_raw_v2_1"]) >= 1.25
        for values in by_length.values()
    )
    all_requested_completed = sorted(by_length) == sorted(requested_lengths)
    if any_competitive:
        outcome = "v2_2_competitive_on_standard_scoreboard"
        recommendation = "Run ablations and compact regression before any claim upgrade."
    elif any_improves_vs_raw and candidate_improvement is not None and candidate_improvement >= 1.25:
        outcome = "v2_2_improves_with_length_but_baselines_still_lead"
        recommendation = "Run Tier 7.0f failure localization before adding the next general mechanism."
    elif any_improves_vs_raw:
        outcome = "v2_2_improves_vs_v2_1_but_not_length_competitive"
        recommendation = "Do not blame short length alone; diagnose readout/recurrent/interface gap."
    else:
        outcome = "v2_2_does_not_move_standard_scoreboard"
        recommendation = "Stop blaming training duration; run failure localization or narrow claim."
    return {
        "outcome": outcome,
        "recommendation": recommendation,
        "requested_lengths": requested_lengths,
        "completed_lengths": sorted(by_length),
        "all_requested_lengths_completed": bool(all_requested_completed),
        "by_length": by_length,
        "candidate_improvement_first_to_last": candidate_improvement,
        "best_baseline_improvement_first_to_last": baseline_improvement,
        "longest_length": longest_length,
        "longest_length_candidate_mse": longest.get("candidate_mse"),
        "longest_length_best_baseline_model": longest.get("best_baseline_model"),
        "longest_length_best_baseline_mse": longest.get("best_baseline_mse"),
        "longest_length_margin_vs_best_baseline": longest.get("margin_vs_best_baseline"),
        "any_competitive_with_best_baseline": bool(any_competitive),
        "any_improves_vs_raw_v2_1": bool(any_improves_vs_raw),
        "claim": (
            "standardized benchmark improvement"
            if any_competitive or any_improves_vs_raw
            else "no public benchmark improvement from this tier"
        ),
        "nonclaims": [
            "not hardware evidence",
            "not custom synthetic usefulness proof",
            "not universal benchmark superiority",
            "not a new baseline freeze",
            "not language, planning, AGI, or ASI",
        ],
    }


def write_report(output_dir: Path, payload: dict[str, Any]) -> None:
    c = payload["classification"]
    lines = [
        "# Tier 7.0e Standard Dynamical Benchmark Rerun",
        "",
        f"- Generated: `{payload['generated_at_utc']}`",
        f"- Status: **{payload['status'].upper()}**",
        f"- Matrix mode: `{payload['matrix_mode']}`",
        f"- Criteria: `{payload['criteria_passed']}/{payload['criteria_total']}`",
        f"- Outcome: `{c['outcome']}`",
        f"- Recommendation: {c['recommendation']}",
        "",
        "## Claim Boundary",
        "",
        payload["claim_boundary"],
        "",
        "## Length Sweep",
        "",
        "| Length | v2.2 candidate MSE | Raw v2.1 MSE | Best baseline | Best baseline MSE | Candidate / best baseline | Margin vs raw v2.1 |",
        "| ---: | ---: | ---: | --- | ---: | ---: | ---: |",
    ]
    for length, values in sorted(c["by_length"].items()):
        candidate = values["candidate_mse"]
        raw = values["raw_v2_1_mse"]
        baseline = values["best_baseline_mse"]
        margin_best = ratio(candidate, baseline)
        lines.append(
            "| "
            f"{length} | "
            f"{candidate} | "
            f"{raw} | "
            f"{values['best_baseline_model']} | "
            f"{baseline} | "
            f"{margin_best} | "
            f"{values['margin_vs_raw_v2_1']} |"
        )
    invalid_tasks = [
        item
        for result in payload.get("length_results", [])
        for item in result.get("invalid_tasks", [])
    ]
    lines.extend(
        [
            "",
            "## Benchmark Stream Validity",
            "",
            f"- Invalid generated task streams: `{len(invalid_tasks)}`",
        ]
    )
    for item in invalid_tasks:
        finite_check = item.get("finite_check", {})
        lines.append(
            f"- `{item.get('task')}` seed `{item.get('seed')}` length `{item.get('length')}` "
            f"target_nonfinite_count=`{finite_check.get('target_nonfinite_count')}`"
        )
    if invalid_tasks:
        lines.append("")
    else:
        lines.append("")
    lines.extend(
        [
            "## Interpretation",
            "",
            f"- Candidate improvement first-to-last: `{c['candidate_improvement_first_to_last']}`",
            f"- Best-baseline improvement first-to-last: `{c['best_baseline_improvement_first_to_last']}`",
            f"- Any competitive length: `{c['any_competitive_with_best_baseline']}`",
            f"- Any improvement versus raw v2.1: `{c['any_improves_vs_raw_v2_1']}`",
            "",
            "## Nonclaims",
            "",
        ]
    )
    for item in c["nonclaims"]:
        lines.append(f"- {item}")
    lines.append("")
    (output_dir / "tier7_0e_report.md").write_text("\n".join(lines), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=TIER)
    parser.add_argument("--tasks", default=DEFAULT_TASKS)
    parser.add_argument("--seeds", default="42,43,44")
    parser.add_argument("--seed-count", type=int, default=None)
    parser.add_argument("--base-seed", type=int, default=42)
    parser.add_argument("--lengths", default=DEFAULT_LENGTHS)
    parser.add_argument(
        "--matrix-mode",
        choices=["scoreboard", "full_diagnostic"],
        default="scoreboard",
        help=(
            "scoreboard runs only the v2.2 candidate plus public baselines for long exposure; "
            "full_diagnostic preserves the raw CRA/sham matrix for shorter mechanism audits."
        ),
    )
    parser.add_argument("--horizon", type=int, default=8)
    parser.add_argument("--history", type=int, default=12)
    parser.add_argument("--backend", default="mock")
    parser.add_argument("--cra-population-size", type=int, default=8)
    parser.add_argument("--cra-readout-lr", type=float, default=0.20)
    parser.add_argument("--cra-delayed-lr", type=float, default=0.20)
    parser.add_argument("--readout-lr", type=float, default=0.08)
    parser.add_argument("--readout-decay", type=float, default=1e-5)
    parser.add_argument("--weight-clip", type=float, default=20.0)
    parser.add_argument("--output-clip", type=float, default=3.0)
    parser.add_argument("--ridge", type=float, default=1e-3)
    parser.add_argument("--temporal-timescales", default="2,4,8,16,32,64,128")
    parser.add_argument("--temporal-hidden-units", type=int, default=16)
    parser.add_argument("--temporal-recurrent-scale", type=float, default=0.65)
    parser.add_argument("--temporal-input-scale", type=float, default=0.45)
    parser.add_argument("--temporal-hidden-decay", type=float, default=0.72)
    parser.add_argument("--state-reset-interval", type=int, default=24)
    parser.add_argument("--reservoir-units", type=int, default=32)
    parser.add_argument("--reservoir-spectral-radius", type=float, default=0.9)
    parser.add_argument("--reservoir-input-scale", type=float, default=0.5)
    parser.add_argument("--esn-units", type=int, default=64)
    parser.add_argument("--esn-spectral-radius", type=float, default=0.9)
    parser.add_argument("--esn-input-scale", type=float, default=0.5)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--smoke", action="store_true", help="Run one small length/task/seed for local validation only.")
    parser.add_argument(
        "--timeseries-max-length",
        type=int,
        default=2000,
        help="Write per-step timeseries only for lengths at or below this value; long runs keep summary/aggregate artifacts.",
    )
    return parser


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if args.smoke:
        args.tasks = "mackey_glass"
        args.seeds = "42"
        args.lengths = "720"
    tasks = parse_csv(args.tasks)
    lengths = parse_lengths(args.lengths)
    started = time.perf_counter()
    length_results = [run_one_length(length, args, output_dir) for length in lengths]
    classification = classify(length_results, lengths)
    criteria = [
        criterion("standard task subset only", sorted(tasks), "subset of standard three", set(tasks).issubset(STANDARD_THREE)),
        criterion("matrix mode declared", args.matrix_mode, "scoreboard or full_diagnostic", args.matrix_mode in {"scoreboard", "full_diagnostic"}),
        criterion(
            "generated benchmark streams finite",
            sum(len(result["invalid_tasks"]) for result in length_results),
            "0 invalid task streams",
            all(not result["invalid_tasks"] for result in length_results),
        ),
        criterion("v2.2 candidate present", V22_CANDIDATE, "present for every length", all(any(row["model"] == V22_CANDIDATE for row in result["model_aggregate_rows"]) for result in length_results)),
        criterion(
            "raw v2.1 reference policy",
            args.matrix_mode,
            "required in full_diagnostic; historical-only in scoreboard",
            args.matrix_mode == "scoreboard"
            or all(any(row["model"] == RAW_V21 for row in result["model_aggregate_rows"]) for result in length_results),
        ),
        criterion("public baselines present", sorted(PUBLIC_BASELINES), "at least two per length", all(sum(1 for row in result["model_aggregate_rows"] if row["model"] in PUBLIC_BASELINES) >= 2 for result in length_results)),
        criterion("length sweep completed", classification["completed_lengths"], "== requested lengths", bool(classification["all_requested_lengths_completed"])),
        criterion("classification produced", classification["outcome"], "non-empty", bool(classification["outcome"])),
    ]
    status = "pass" if all(item["passed"] for item in criteria) else "fail"
    all_summary_rows: list[dict[str, Any]] = []
    all_model_aggregate_rows: list[dict[str, Any]] = []
    for result in length_results:
        all_summary_rows.extend(result["summary_rows"])
        all_model_aggregate_rows.extend(result["model_aggregate_rows"])
    payload = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "status": status,
        "matrix_mode": args.matrix_mode,
        "criteria": criteria,
        "criteria_passed": sum(1 for item in criteria if item["passed"]),
        "criteria_total": len(criteria),
        "output_dir": str(output_dir),
        "tasks": tasks,
        "lengths": lengths,
        "seeds": parse_seeds(args),
        "classification": classification,
        "summary_rows": all_summary_rows,
        "model_aggregate_rows": all_model_aggregate_rows,
        "length_results": [
            {
                "length": result["length"],
                "runtime_seconds": result["runtime_seconds"],
                "models": result["models"],
                "invalid_tasks": result["invalid_tasks"],
            }
            for result in length_results
        ],
        "runtime_seconds": time.perf_counter() - started,
        "fairness_contract": {
            "tier": TIER,
            "scoreboard": "Mackey-Glass / Lorenz / NARMA10 standard dynamical suite",
            "split": "chronological",
            "normalization": "train-prefix only inside imported task builders and online readouts",
            "lengths": lengths,
            "prediction": "online readouts predict before update; train-prefix baselines fit only train rows",
            "custom_task_policy": "no custom synthetic tasks in this runner",
            "matrix_mode": args.matrix_mode,
            "long_run_policy": (
                "scoreboard mode omits raw CRA trace collection and destructive shams so 10k/50k "
                "public benchmark sweeps remain practical; use full_diagnostic mode for shorter "
                "mechanism-causality audits."
            ),
            "hardware_policy": "software-only; hardware transfer blocked until benchmark/mechanism earns it",
        },
        "claim_boundary": (
            "Tier 7.0e is software benchmark evidence only. It reruns the public "
            "standard dynamical scoreboard with v2.2 and a length sweep. It is "
            "not hardware evidence, not a custom synthetic usefulness claim, not "
            "a new baseline freeze, and not AGI/ASI evidence."
        ),
    }
    write_json(output_dir / "tier7_0e_results.json", payload)
    write_json(output_dir / "tier7_0e_fairness_contract.json", payload["fairness_contract"])
    write_rows(output_dir / "tier7_0e_summary.csv", all_summary_rows)
    write_rows(output_dir / "tier7_0e_model_aggregate.csv", all_model_aggregate_rows)
    write_report(output_dir, payload)
    write_json(
        CONTROLLED / "tier7_0e_latest_manifest.json",
        {
            "tier": TIER,
            "runner_revision": RUNNER_REVISION,
            "generated_at_utc": payload["generated_at_utc"],
            "status": status,
            "manifest": str(output_dir / "tier7_0e_results.json"),
            "output_dir": str(output_dir),
        },
    )
    return payload


def main() -> None:
    result = run(build_parser().parse_args())
    print(
        json.dumps(
            {
                "tier": TIER,
                "status": result["status"],
                "matrix_mode": result["matrix_mode"],
                "criteria": f"{result['criteria_passed']}/{result['criteria_total']}",
                "outcome": result["classification"]["outcome"],
                "output_dir": result["output_dir"],
            },
            indent=2,
        )
    )
    if result["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
