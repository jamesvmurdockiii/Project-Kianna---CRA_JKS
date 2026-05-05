#!/usr/bin/env python3
"""Tier 7.0d - State-Specific Continuous Interface / Claim-Narrowing.

Tier 7.0c showed that a bounded continuous readout improves raw CRA output, but
the lag-only online control still explains most of the benchmark gain. This tier
asks the sharper question:

    Does CRA state add value beyond the same causal lag budget?

The runner keeps the same Mackey-Glass, Lorenz, and NARMA10 streams as Tier 7.0.
It tests online state-specific candidates plus train-prefix ridge upper-bound
probes. It does not move the benchmark to hardware, does not freeze a baseline,
and does not tune against held-out rows.
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
OUTPUT_ROOT = ROOT / "controlled_test_output"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from tier4_scaling import mean, stdev  # noqa: E402
from tier7_0_standard_dynamical_benchmarks import (  # noqa: E402
    DEFAULT_TASKS,
    SequenceTask,
    build_task,
    geometric_mean,
    parse_csv,
    parse_seeds,
)
from tier7_0b_continuous_regression_failure_analysis import (  # noqa: E402
    collect_cra_trace,
    evaluate_probe,
    fit_predict_ridge,
    lag_matrix,
)
from tier7_0c_continuous_readout_repair import (  # noqa: E402
    normalize_features,
    online_normalized_lms,
    shuffled_rows,
    shuffled_target,
)


TIER = "Tier 7.0d - State-Specific Continuous Interface / Claim-Narrowing"
RUNNER_REVISION = "tier7_0d_state_specific_continuous_interface_20260505_0001"
DEFAULT_OUTPUT_DIR = OUTPUT_ROOT / "tier7_0d_20260505_state_specific_continuous_interface"


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
        value = float(value)
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def criterion(name: str, value: Any, rule: str, passed: bool, note: str = "") -> dict[str, Any]:
    return {"name": name, "value": json_safe(value), "rule": rule, "passed": bool(passed), "note": note}


def ridge_weights(features: np.ndarray, target: np.ndarray, ridge: float) -> np.ndarray:
    x = np.asarray(features, dtype=float)
    y = np.asarray(target, dtype=float)
    xtx = x.T @ x
    reg = float(ridge) * np.eye(x.shape[1], dtype=float)
    return np.linalg.solve(xtx + reg, x.T @ y)


def residualize_state_against_lag(
    state_features: np.ndarray,
    lag_features: np.ndarray,
    train_end: int,
    ridge: float,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Remove train-prefix lag-explainable state components.

    The first column is preserved as a bias. Non-bias state columns are predicted
    from the lag matrix using only the chronological train prefix, then residuals
    are used as state-specific features for all rows.
    """
    state = np.asarray(state_features, dtype=float)
    lag = np.asarray(lag_features, dtype=float)
    state_nonbias = state[:, 1:]
    if state_nonbias.shape[1] == 0:
        return np.ones((state.shape[0], 1), dtype=float), {"projected_columns": 0, "projection_norm": 0.0}
    projection = ridge_weights(lag[:train_end], state_nonbias[:train_end], ridge)
    predicted_state = lag @ projection
    residual = state_nonbias - predicted_state
    return np.column_stack([np.ones(len(state)), residual]), {
        "projected_columns": int(state_nonbias.shape[1]),
        "projection_norm": float(np.linalg.norm(projection)),
        "orthogonalization": "state_nonbias_residualized_against_lag_using_train_prefix",
    }


def online_two_stage_residual_lms(
    lag_features: np.ndarray,
    residual_state_features: np.ndarray,
    target: np.ndarray,
    *,
    lr: float,
    decay: float,
    weight_clip: float,
    output_clip: float,
    update_target: np.ndarray | None = None,
    update_enabled: bool = True,
) -> tuple[np.ndarray, dict[str, Any]]:
    lag = np.asarray(lag_features, dtype=float)
    residual = np.asarray(residual_state_features, dtype=float)
    y = np.asarray(target, dtype=float)
    update_y = y if update_target is None else np.asarray(update_target, dtype=float)
    w_lag = np.zeros(lag.shape[1], dtype=float)
    w_res = np.zeros(residual.shape[1], dtype=float)
    predictions = np.zeros(len(y), dtype=float)
    max_lag_norm = 0.0
    max_res_norm = 0.0
    for step in range(len(y)):
        lag_pred = float(np.dot(w_lag, lag[step]))
        residual_pred = float(np.dot(w_res, residual[step]))
        pred = lag_pred + residual_pred
        if output_clip > 0.0:
            pred = float(np.clip(pred, -output_clip, output_clip))
        predictions[step] = pred
        if not update_enabled:
            continue
        lag_err = float(update_y[step] - lag_pred)
        lag_denom = 1.0 + float(np.dot(lag[step], lag[step]))
        w_lag = (1.0 - float(decay)) * w_lag + (float(lr) * lag_err / lag_denom) * lag[step]
        residual_target = float(update_y[step] - lag_pred)
        residual_err = residual_target - residual_pred
        residual_denom = 1.0 + float(np.dot(residual[step], residual[step]))
        w_res = (1.0 - float(decay)) * w_res + (float(lr) * residual_err / residual_denom) * residual[step]
        for weights in (w_lag, w_res):
            norm = float(np.linalg.norm(weights))
            if weight_clip > 0.0 and norm > weight_clip:
                weights *= weight_clip / norm
        max_lag_norm = max(max_lag_norm, float(np.linalg.norm(w_lag)))
        max_res_norm = max(max_res_norm, float(np.linalg.norm(w_res)))
    return predictions, {
        "lr": float(lr),
        "decay": float(decay),
        "weight_clip": float(weight_clip),
        "output_clip": float(output_clip),
        "update_enabled": bool(update_enabled),
        "final_lag_weight_norm": float(np.linalg.norm(w_lag)),
        "final_residual_weight_norm": float(np.linalg.norm(w_res)),
        "max_lag_weight_norm": max_lag_norm,
        "max_residual_weight_norm": max_res_norm,
        "contract": "prediction_before_update_two_stage_lag_then_state_residual",
    }


def append_timeseries(
    rows: list[dict[str, Any]],
    *,
    task: str,
    seed: int,
    model: str,
    observed: np.ndarray,
    target: np.ndarray,
    prediction: np.ndarray,
    train_end: int,
) -> None:
    for step, (obs, tgt, pred) in enumerate(zip(observed, target, prediction)):
        rows.append(
            {
                "task": task,
                "seed": int(seed),
                "model": model,
                "step": int(step),
                "split": "train" if step < train_end else "test",
                "observed": float(obs),
                "target": float(tgt),
                "prediction": float(pred),
                "squared_error": float((float(pred) - float(tgt)) ** 2),
            }
        )


def run_state_specific_models(
    task: SequenceTask,
    trace: Any,
    *,
    seed: int,
    args: argparse.Namespace,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    target = np.asarray(trace.target, dtype=float)
    train_end = int(trace.train_end)
    lag_features = lag_matrix(trace.observed, args.history)
    state_features, state_norm = normalize_features(trace.features, train_end)
    lag_norm, lag_meta = normalize_features(lag_features, train_end)
    residual_state, residual_meta = residualize_state_against_lag(
        state_features,
        lag_norm,
        train_end,
        args.residual_ridge,
    )
    lag_plus_state = np.column_stack([lag_norm, state_features[:, 1:]])
    lag_plus_residual = np.column_stack([lag_norm, residual_state[:, 1:]])
    shuffled_residual = shuffled_rows(residual_state, train_end, seed)
    lag_plus_shuffled_residual = np.column_stack([lag_norm, shuffled_residual[:, 1:]])
    wrong_target = shuffled_target(target, train_end, seed)

    model_predictions: list[tuple[str, np.ndarray, dict[str, Any]]] = [
        ("raw_cra_v2_1_online", np.asarray(trace.cra_prediction, dtype=float), {"role": "raw CRA prediction"}),
    ]

    online_specs: list[tuple[str, np.ndarray, np.ndarray | None, bool, dict[str, Any]]] = [
        ("lag_only_online_lms_control", lag_norm, None, True, {"role": "online lag-only control", "lag_budget": int(args.history)}),
        ("state_only_online_lms_control", state_features, None, True, {"role": "online state-only control"}),
        ("state_plus_lag_online_lms_reference", lag_plus_state, None, True, {"role": "online lag plus raw state reference"}),
        ("orthogonal_state_only_online_control", residual_state, None, True, {"role": "online state residualized against lag"}),
        (
            "lag_plus_orthogonal_state_online_repair",
            lag_plus_residual,
            None,
            True,
            {"role": "online lag plus lag-orthogonal CRA state candidate"},
        ),
        (
            "lag_plus_shuffled_orthogonal_state_control",
            lag_plus_shuffled_residual,
            None,
            True,
            {"role": "online lag plus shuffled lag-orthogonal state control"},
        ),
        (
            "lag_plus_orthogonal_state_shuffled_target_control",
            lag_plus_residual,
            wrong_target,
            True,
            {"role": "online lag plus lag-orthogonal state updated with shuffled targets"},
        ),
        ("frozen_lag_plus_state_control", lag_plus_state, None, False, {"role": "online lag plus state with updates disabled"}),
    ]
    for model, features, update_target, update_enabled, diagnostics in online_specs:
        pred, diag = online_normalized_lms(
            features,
            target,
            train_end=train_end,
            lr=args.readout_lr,
            decay=args.readout_decay,
            weight_clip=args.weight_clip,
            output_clip=args.output_clip,
            update_target=update_target,
            update_enabled=update_enabled,
        )
        model_predictions.append(
            (
                model,
                pred,
                {
                    **diagnostics,
                    **diag,
                    "feature_normalization": "train_prefix",
                    "state_normalization_columns": len(state_norm["feature_mu"]),
                    "lag_meta": lag_meta,
                    "residual_meta": residual_meta,
                },
            )
        )

    pred, diag = online_two_stage_residual_lms(
        lag_norm,
        residual_state,
        target,
        lr=args.readout_lr,
        decay=args.readout_decay,
        weight_clip=args.weight_clip,
        output_clip=args.output_clip,
    )
    model_predictions.append(
        (
            "two_stage_lag_residual_state_online_repair",
            pred,
            {**diag, "role": "two-stage online lag model plus residual state model", "residual_meta": residual_meta},
        )
    )
    pred, diag = online_two_stage_residual_lms(
        lag_norm,
        shuffled_residual,
        target,
        lr=args.readout_lr,
        decay=args.readout_decay,
        weight_clip=args.weight_clip,
        output_clip=args.output_clip,
    )
    model_predictions.append(
        (
            "two_stage_shuffled_residual_control",
            pred,
            {**diag, "role": "two-stage online lag model plus shuffled residual state control"},
        )
    )

    ridge_specs: list[tuple[str, np.ndarray, dict[str, Any]]] = [
        ("train_prefix_ridge_lag_upper_bound", lag_norm, {"role": "train-prefix ridge lag-only upper-bound probe"}),
        (
            "train_prefix_ridge_lag_plus_state_upper_bound",
            lag_plus_state,
            {"role": "train-prefix ridge lag plus raw state upper-bound probe"},
        ),
        (
            "train_prefix_ridge_lag_plus_orthogonal_state_upper_bound",
            lag_plus_residual,
            {"role": "train-prefix ridge lag plus lag-orthogonal state upper-bound probe"},
        ),
        (
            "train_prefix_ridge_orthogonal_state_only_probe",
            residual_state,
            {"role": "train-prefix ridge lag-orthogonal state-only probe"},
        ),
    ]
    for model, features, diagnostics in ridge_specs:
        pred, norm = fit_predict_ridge(features, target, train_end, args.ridge)
        model_predictions.append((model, pred, {**diagnostics, "weight_norm": norm, "ridge": float(args.ridge)}))

    rows: list[dict[str, Any]] = []
    timeseries: list[dict[str, Any]] = []
    for model, pred, diagnostics in model_predictions:
        rows.append(evaluate_probe(task.name, seed, train_end, target, pred, model, diagnostics))
        append_timeseries(
            timeseries,
            task=task.name,
            seed=seed,
            model=model,
            observed=trace.observed,
            target=target,
            prediction=pred,
            train_end=train_end,
        )
    diagnostics = {
        "lag_feature_count": int(lag_norm.shape[1]),
        "state_feature_count": int(state_features.shape[1]),
        "orthogonal_state_feature_count": int(residual_state.shape[1]),
        "residual_meta": residual_meta,
    }
    return rows, timeseries, diagnostics


def summarize(rows: list[dict[str, Any]], tasks: list[str], models: list[str], seeds: list[int]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    summary_rows: list[dict[str, Any]] = []
    aggregate_rows: list[dict[str, Any]] = []
    for task in tasks:
        for model in models:
            subset = [r for r in rows if r["task"] == task and r["model"] == model and r["status"] == "pass"]
            summary_rows.append(
                {
                    "task": task,
                    "model": model,
                    "status": "pass" if len(subset) == len(seeds) else "fail",
                    "seed_count": len(subset),
                    "mse_mean": mean([r["mse"] for r in subset]),
                    "mse_median": float(np.median([r["mse"] for r in subset])) if subset else None,
                    "mse_std": stdev([r["mse"] for r in subset]),
                    "mse_worst": max([r["mse"] for r in subset]) if subset else None,
                    "nmse_mean": mean([r["nmse"] for r in subset]),
                    "tail_mse_mean": mean([r["tail_mse"] for r in subset]),
                    "test_corr_mean": mean([r["test_corr"] for r in subset]),
                }
            )
    for model in models:
        for seed in seeds:
            subset = [r for r in rows if r["model"] == model and r["seed"] == seed and r["status"] == "pass"]
            by_task = {r["task"]: r for r in subset}
            if all(task in by_task for task in tasks):
                aggregate_rows.append(
                    {
                        "task": "all_three_geomean",
                        "model": model,
                        "seed": int(seed),
                        "status": "pass",
                        "geomean_mse": geometric_mean([by_task[task]["mse"] for task in tasks]),
                        "geomean_nmse": geometric_mean([by_task[task]["nmse"] for task in tasks]),
                    }
                )
            else:
                aggregate_rows.append(
                    {
                        "task": "all_three_geomean",
                        "model": model,
                        "seed": int(seed),
                        "status": "fail",
                        "geomean_mse": None,
                        "geomean_nmse": None,
                    }
                )
    aggregate_summary = []
    for model in models:
        subset = [r for r in aggregate_rows if r["model"] == model and r["status"] == "pass"]
        values = [float(r["geomean_mse"]) for r in subset if r["geomean_mse"] is not None]
        nmse_values = [float(r["geomean_nmse"]) for r in subset if r["geomean_nmse"] is not None]
        aggregate_summary.append(
            {
                "model": model,
                "status": "pass" if values else "fail",
                "seed_count": len(values),
                "geomean_mse_mean": mean(values),
                "geomean_mse_median": float(np.median(values)) if values else None,
                "geomean_mse_worst": max(values) if values else None,
                "geomean_nmse_mean": mean(nmse_values),
            }
        )
    pass_rows = [r for r in aggregate_summary if r["status"] == "pass" and r["geomean_mse_mean"] is not None]
    pass_rows.sort(key=lambda r: float(r["geomean_mse_mean"]))
    rank = {row["model"]: i + 1 for i, row in enumerate(pass_rows)}
    for row in aggregate_summary:
        row["rank_by_geomean_mse"] = rank.get(row["model"])
    aggregate_summary.sort(key=lambda row: (row["rank_by_geomean_mse"] or 10_000, row["model"]))
    return summary_rows, aggregate_rows, aggregate_summary


def classify_state_specific_result(aggregate_summary: list[dict[str, Any]]) -> dict[str, Any]:
    by_model = {row["model"]: row for row in aggregate_summary if row["status"] == "pass"}

    def mse(name: str) -> float:
        row = by_model.get(name)
        if not row or row.get("geomean_mse_mean") is None:
            return math.inf
        return float(row["geomean_mse_mean"])

    raw = mse("raw_cra_v2_1_online")
    lag = mse("lag_only_online_lms_control")
    lag_plus_state = mse("state_plus_lag_online_lms_reference")
    lag_plus_orth = mse("lag_plus_orthogonal_state_online_repair")
    two_stage = mse("two_stage_lag_residual_state_online_repair")
    lag_plus_shuffled = mse("lag_plus_shuffled_orthogonal_state_control")
    two_stage_shuffled = mse("two_stage_shuffled_residual_control")
    shuffled_target_control = mse("lag_plus_orthogonal_state_shuffled_target_control")
    ridge_lag = mse("train_prefix_ridge_lag_upper_bound")
    ridge_lag_state = mse("train_prefix_ridge_lag_plus_state_upper_bound")
    ridge_lag_orth = mse("train_prefix_ridge_lag_plus_orthogonal_state_upper_bound")

    online_candidates = {
        "lag_plus_orthogonal_state_online_repair": lag_plus_orth,
        "two_stage_lag_residual_state_online_repair": two_stage,
    }
    best_online_name, best_online = min(online_candidates.items(), key=lambda item: item[1])
    best_sham = min(lag_plus_shuffled, two_stage_shuffled, shuffled_target_control)
    best_ridge_state = min(ridge_lag_state, ridge_lag_orth)

    raw_improvement = raw / best_online if best_online > 0 and math.isfinite(raw) and math.isfinite(best_online) else None
    online_vs_lag = lag / best_online if best_online > 0 and math.isfinite(lag) and math.isfinite(best_online) else None
    online_vs_sham = best_sham / best_online if best_online > 0 and math.isfinite(best_sham) and math.isfinite(best_online) else None
    ridge_state_vs_lag = ridge_lag / best_ridge_state if best_ridge_state > 0 and math.isfinite(ridge_lag) and math.isfinite(best_ridge_state) else None
    raw_state_lag_vs_lag = lag / lag_plus_state if lag_plus_state > 0 and math.isfinite(lag_plus_state) and math.isfinite(lag) else None

    if online_vs_lag is not None and online_vs_lag >= 1.10 and online_vs_sham is not None and online_vs_sham >= 1.10:
        outcome = "state_specific_online_value_found"
        recommendation = "Run a compact regression/promotion gate before any baseline freeze or hardware migration."
    elif ridge_state_vs_lag is not None and ridge_state_vs_lag >= 1.10:
        outcome = "state_value_exists_but_online_interface_still_fails"
        recommendation = "Do not promote 7.0d; design a better online interface if this benchmark remains a priority."
    else:
        outcome = "lag_regression_explains_benchmark"
        recommendation = "Narrow the Tier 7 continuous-regression claim; do not move this benchmark path to hardware yet."

    return {
        "outcome": outcome,
        "raw_cra_geomean_mse": raw,
        "lag_only_online_geomean_mse": lag,
        "state_plus_lag_online_geomean_mse": lag_plus_state,
        "lag_plus_orthogonal_state_online_geomean_mse": lag_plus_orth,
        "two_stage_lag_residual_state_online_geomean_mse": two_stage,
        "lag_plus_shuffled_orthogonal_state_geomean_mse": lag_plus_shuffled,
        "two_stage_shuffled_residual_geomean_mse": two_stage_shuffled,
        "shuffled_target_control_geomean_mse": shuffled_target_control,
        "train_prefix_ridge_lag_geomean_mse": ridge_lag,
        "train_prefix_ridge_lag_plus_state_geomean_mse": ridge_lag_state,
        "train_prefix_ridge_lag_plus_orthogonal_state_geomean_mse": ridge_lag_orth,
        "best_state_specific_online_model": best_online_name,
        "best_state_specific_online_geomean_mse": best_online,
        "best_state_specific_online_improvement_over_raw": raw_improvement,
        "best_state_specific_online_margin_vs_lag_only": online_vs_lag,
        "best_state_specific_online_margin_vs_best_sham": online_vs_sham,
        "train_prefix_ridge_state_margin_vs_lag": ridge_state_vs_lag,
        "raw_state_plus_lag_online_margin_vs_lag": raw_state_lag_vs_lag,
        "recommendation": recommendation,
    }


def write_report(output_dir: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# Tier 7.0d State-Specific Continuous Interface / Claim-Narrowing",
        "",
        f"- Generated: `{payload['generated_at_utc']}`",
        f"- Status: **{payload['status'].upper()}**",
        f"- Criteria: `{payload['criteria_passed']}/{payload['criteria_total']}`",
        f"- Outcome: `{payload['state_specific_classification']['outcome']}`",
        "",
        "## Claim Boundary",
        "",
        payload["claim_boundary"],
        "",
        "## Aggregate Summary",
        "",
        "| Model | Rank | Geomean MSE mean | Geomean NMSE mean |",
        "| --- | ---: | ---: | ---: |",
    ]
    for row in payload["aggregate_summary"]:
        lines.append(
            f"| {row['model']} | {row['rank_by_geomean_mse']} | {row['geomean_mse_mean']} | {row['geomean_nmse_mean']} |"
        )
    c = payload["state_specific_classification"]
    lines.extend(
        [
            "",
            "## Classification",
            "",
            f"- Outcome: `{c['outcome']}`",
            f"- Raw CRA geomean MSE: `{c['raw_cra_geomean_mse']}`",
            f"- Lag-only online geomean MSE: `{c['lag_only_online_geomean_mse']}`",
            f"- Best state-specific online model: `{c['best_state_specific_online_model']}`",
            f"- Best state-specific online geomean MSE: `{c['best_state_specific_online_geomean_mse']}`",
            f"- Margin versus lag-only: `{c['best_state_specific_online_margin_vs_lag_only']}`",
            f"- Margin versus best sham: `{c['best_state_specific_online_margin_vs_best_sham']}`",
            f"- Train-prefix ridge state margin versus lag: `{c['train_prefix_ridge_state_margin_vs_lag']}`",
            f"- Recommendation: {c['recommendation']}",
            "",
            "## Interpretation Rule",
            "",
            "- If state-specific online candidates do not beat lag-only, do not promote a continuous readout mechanism.",
            "- If train-prefix upper bounds show state value but online candidates fail, this is still an online-interface problem.",
            "- If lag-only remains the best explanation, narrow the benchmark claim instead of tuning blindly.",
            "",
        ]
    )
    (output_dir / "tier7_0d_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    tasks = parse_csv(args.tasks)
    seeds = parse_seeds(args)
    started = time.perf_counter()
    all_rows: list[dict[str, Any]] = []
    all_timeseries: list[dict[str, Any]] = []
    trace_diagnostics: list[dict[str, Any]] = []
    state_specific_diagnostics: list[dict[str, Any]] = []

    for seed in seeds:
        for task_name in tasks:
            task = build_task(task_name, args.length, seed, args.horizon)
            trace = collect_cra_trace(task, seed=seed, args=args)
            rows, timeseries, diagnostics = run_state_specific_models(task, trace, seed=seed, args=args)
            all_rows.extend(rows)
            all_timeseries.extend(timeseries)
            trace_diagnostics.append({"task": task_name, "seed": int(seed), **trace.diagnostics})
            state_specific_diagnostics.append({"task": task_name, "seed": int(seed), **diagnostics})

    models = sorted({row["model"] for row in all_rows})
    summary_rows, aggregate_rows, aggregate_summary = summarize(all_rows, tasks, models, seeds)
    classification = classify_state_specific_result(aggregate_summary)
    criteria = [
        criterion("runner revision current", RUNNER_REVISION, "expected current source", RUNNER_REVISION.endswith("_0001")),
        criterion("all task names known", tasks, "subset of Tier 7.0 tasks", all(t in {"mackey_glass", "lorenz", "narma10"} for t in tasks)),
        criterion("all runs completed", f"{sum(r['status'] == 'pass' for r in all_rows)}/{len(all_rows)}", "all pass", all(r["status"] == "pass" for r in all_rows)),
        criterion("classification produced", classification["outcome"], "non-empty", bool(classification["outcome"])),
        criterion("raw CRA present", "raw_cra_v2_1_online" in models, "== true", "raw_cra_v2_1_online" in models),
        criterion("lag-only control present", "lag_only_online_lms_control" in models, "== true", "lag_only_online_lms_control" in models),
        criterion("orthogonal state candidate present", "lag_plus_orthogonal_state_online_repair" in models, "== true", "lag_plus_orthogonal_state_online_repair" in models),
        criterion("two-stage residual candidate present", "two_stage_lag_residual_state_online_repair" in models, "== true", "two_stage_lag_residual_state_online_repair" in models),
        criterion("state-specific shams present", "shuffled residual and shuffled target", "all present", all(m in models for m in ["lag_plus_shuffled_orthogonal_state_control", "two_stage_shuffled_residual_control", "lag_plus_orthogonal_state_shuffled_target_control"])),
        criterion("train-prefix upper bounds present", "ridge lag and lag+state probes", "all present", all(m in models for m in ["train_prefix_ridge_lag_upper_bound", "train_prefix_ridge_lag_plus_state_upper_bound", "train_prefix_ridge_lag_plus_orthogonal_state_upper_bound"])),
    ]
    failed = [c for c in criteria if not c["passed"]]
    payload = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "status": "pass" if not failed else "fail",
        "criteria": criteria,
        "criteria_passed": len(criteria) - len(failed),
        "criteria_total": len(criteria),
        "failed_criteria": failed,
        "tasks": tasks,
        "seeds": seeds,
        "backend": str(args.backend),
        "length": int(args.length),
        "horizon": int(args.horizon),
        "history": int(args.history),
        "runtime_seconds": time.perf_counter() - started,
        "summary_rows": summary_rows,
        "aggregate_rows": aggregate_rows,
        "aggregate_summary": aggregate_summary,
        "classification": classification["outcome"],
        "key_metrics": classification,
        "state_specific_classification": classification,
        "summary": classification,
        "run_rows": all_rows,
        "trace_diagnostics": trace_diagnostics,
        "state_specific_diagnostics": state_specific_diagnostics,
        "fairness_contract": {
            "tier": TIER,
            "source_tiers": ["Tier 7.0", "Tier 7.0b", "Tier 7.0c"],
            "same_tasks_and_split": True,
            "feature_normalization": "train prefix only",
            "state_orthogonalization": "state residualized against lag features using train prefix only",
            "readout_update": "prediction before update; online normalized LMS; no batch test fit for online candidates",
            "upper_bound_probes": "train-prefix ridge only; diagnostic, not promoted mechanism",
            "no_future_leakage": [
                "all online candidates consume only current/past features",
                "normalization and state residualization use train prefix only",
                "online updates occur after each prediction",
                "ridge probes fit only chronological train prefix",
            ],
            "nonclaims": [
                "not hardware evidence",
                "not a baseline freeze",
                "not a promoted continuous readout mechanism unless a later promotion/regression gate passes",
            ],
        },
        "claim_boundary": (
            "Tier 7.0d is software diagnostic evidence only. It tests whether "
            "CRA state adds value beyond causal lag regression on the Tier 7 "
            "standard dynamical benchmark suite. It is not hardware evidence, "
            "not a baseline freeze, not a tuning loop, and not proof of "
            "superiority over external baselines."
        ),
    }
    write_json(output_dir / "tier7_0d_results.json", payload)
    write_json(output_dir / "tier7_0d_fairness_contract.json", payload["fairness_contract"])
    write_csv(
        output_dir / "tier7_0d_summary.csv",
        summary_rows,
        ["task", "model", "status", "seed_count", "mse_mean", "mse_median", "mse_std", "mse_worst", "nmse_mean", "tail_mse_mean", "test_corr_mean"],
    )
    write_csv(
        output_dir / "tier7_0d_aggregate.csv",
        aggregate_rows,
        ["task", "model", "seed", "status", "geomean_mse", "geomean_nmse"],
    )
    write_csv(
        output_dir / "tier7_0d_timeseries.csv",
        all_timeseries,
        ["task", "seed", "model", "step", "split", "observed", "target", "prediction", "squared_error"],
    )
    write_report(output_dir, payload)
    write_json(
        OUTPUT_ROOT / "tier7_0d_latest_manifest.json",
        {
            "tier": TIER,
            "runner_revision": RUNNER_REVISION,
            "generated_at_utc": payload["generated_at_utc"],
            "status": payload["status"],
            "manifest": str(output_dir / "tier7_0d_results.json"),
            "output_dir": str(output_dir),
        },
    )
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=TIER)
    parser.add_argument("--tasks", default=DEFAULT_TASKS)
    parser.add_argument("--seeds", default="42,43,44")
    parser.add_argument("--seed-count", type=int, default=None)
    parser.add_argument("--base-seed", type=int, default=42)
    parser.add_argument("--length", type=int, default=720)
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
    parser.add_argument("--residual-ridge", type=float, default=1e-3)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    payload = run(args)
    print(
        json.dumps(
            {
                "tier": payload["tier"],
                "status": payload["status"],
                "criteria": f"{payload['criteria_passed']}/{payload['criteria_total']}",
                "outcome": payload["state_specific_classification"]["outcome"],
                "output_dir": str(args.output_dir),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
