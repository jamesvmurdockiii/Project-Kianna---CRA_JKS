#!/usr/bin/env python3
"""Tier 5.19a - Local Continuous Temporal Substrate Reference.

This is the first executable step after the Tier 5.19 / 7.0e contract. It is a
software-only reference gate. It does not freeze a baseline and does not move the
Tier 7 benchmark path to hardware.

The runner tests a bounded temporal substrate candidate against lag-only,
reservoir, frozen/shuffled-state, no-recurrence, no-plasticity, and shuffled-
target controls on the standard Tier 7.0 tasks plus one held-out long-memory
diagnostic.
"""

from __future__ import annotations

import argparse
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

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "controlled_test_output"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from tier4_scaling import mean, stdev  # noqa: E402
from tier7_0_standard_dynamical_benchmarks import (  # noqa: E402
    EchoStateNetworkModel,
    SequenceTask,
    build_task as build_standard_task,
    chronological_split,
    geometric_mean,
    parse_csv,
    parse_seeds,
    score_predictions,
    zscore_from_train,
)
from tier7_0b_continuous_regression_failure_analysis import (  # noqa: E402
    collect_cra_trace,
    evaluate_probe,
    lag_matrix,
)
from tier7_0c_continuous_readout_repair import (  # noqa: E402
    normalize_features,
    online_normalized_lms,
    shuffled_rows,
    shuffled_target,
)


TIER = "Tier 5.19a - Local Continuous Temporal Substrate Reference"
RUNNER_REVISION = "tier5_19a_temporal_substrate_reference_20260505_0001"
DEFAULT_OUTPUT_DIR = OUTPUT_ROOT / "tier5_19a_20260505_temporal_substrate_reference"
DEFAULT_TASKS = "mackey_glass,lorenz,narma10,heldout_long_memory"
STANDARD_TASKS = {"mackey_glass", "lorenz", "narma10"}


@dataclass(frozen=True)
class FeatureBundle:
    features: np.ndarray
    temporal_start: int
    names: list[str]
    diagnostics: dict[str, Any]


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


def heldout_long_memory_task(length: int, seed: int, *, horizon: int) -> SequenceTask:
    """Long-memory nonlinear diagnostic not used by Tier 7.0.

    The current observation plus a short lag window is intentionally incomplete:
    the target depends on a slow hidden accumulator and a nonlinear interaction
    between fast and slow traces.
    """
    rng = np.random.default_rng(seed + 51901)
    warmup = 250
    total = length + horizon + warmup + 8
    drive = rng.normal(0.0, 0.55, size=total)
    drive = np.tanh(drive + 0.25 * np.roll(drive, 1))
    fast = np.zeros(total, dtype=float)
    slow = np.zeros(total, dtype=float)
    gated = np.zeros(total, dtype=float)
    for t in range(1, total):
        fast[t] = 0.78 * fast[t - 1] + 0.22 * drive[t]
        slow[t] = 0.985 * slow[t - 1] + 0.015 * np.tanh(fast[t] + 0.35 * drive[t - 1])
        gated[t] = 0.94 * gated[t - 1] + 0.06 * np.tanh(2.0 * fast[t] * slow[t])
    observed_raw = drive[warmup : warmup + length]
    target_raw = (0.65 * slow + 0.35 * gated)[warmup + horizon : warmup + horizon + length]
    train_end = chronological_split(length, 0.65)
    observed, obs_mu, obs_sd = zscore_from_train(observed_raw, train_end)
    target, tgt_mu, tgt_sd = zscore_from_train(target_raw, train_end)
    return SequenceTask(
        name="heldout_long_memory",
        display_name="Held-out nonlinear long-memory diagnostic",
        observed=observed,
        target=target,
        train_end=train_end,
        horizon=horizon,
        metadata={
            "obs_mu": obs_mu,
            "obs_sd": obs_sd,
            "target_mu": tgt_mu,
            "target_sd": tgt_sd,
            "hidden_timescale": "slow accumulator decay 0.985 plus nonlinear gate decay 0.94",
            "not_in_tier7_standard_suite": True,
        },
    )


def build_task(name: str, length: int, seed: int, horizon: int) -> SequenceTask:
    if name == "heldout_long_memory":
        return heldout_long_memory_task(length, seed, horizon=horizon)
    return build_standard_task(name, length, seed, horizon)


def parse_timescales(raw: str) -> list[float]:
    out = [float(item) for item in parse_csv(raw)]
    if not out:
        raise ValueError("at least one temporal timescale is required")
    return out


def temporal_substrate_features(
    observed: np.ndarray,
    *,
    seed: int,
    train_end: int,
    timescales: list[float],
    hidden_units: int,
    recurrent_scale: float,
    input_scale: float,
    hidden_decay: float,
    include_recurrence: bool,
) -> FeatureBundle:
    values = np.asarray(observed, dtype=float)
    traces = np.zeros(len(timescales), dtype=float)
    hidden = np.zeros(max(0, int(hidden_units)), dtype=float)
    rng = np.random.default_rng(seed + 51919)
    input_dim = 1 + len(timescales) + max(0, len(timescales) - 1) + 1
    w_in = rng.normal(0.0, float(input_scale), size=(hidden.size, input_dim)) if hidden.size else np.zeros((0, input_dim))
    raw_rec = rng.normal(0.0, 1.0, size=(hidden.size, hidden.size)) if hidden.size else np.zeros((0, 0))
    if hidden.size:
        eig = max(1e-9, float(max(abs(np.linalg.eigvals(raw_rec)))))
        w_rec = raw_rec * (float(recurrent_scale) / eig)
    else:
        w_rec = raw_rec
    rows: list[np.ndarray] = []
    for value in values:
        x = float(value)
        previous_traces = traces.copy()
        for idx, tau in enumerate(timescales):
            alpha = 1.0 - math.exp(-1.0 / max(1e-6, float(tau)))
            traces[idx] = traces[idx] + alpha * (x - traces[idx])
        trace_deltas = np.diff(traces) if traces.size > 1 else np.asarray([], dtype=float)
        novelty = x - float(previous_traces[-1] if previous_traces.size else 0.0)
        driver = np.concatenate([[x], traces, trace_deltas, [novelty]])
        if hidden.size:
            recurrent_term = w_rec @ hidden if include_recurrence else 0.0
            hidden = np.tanh(float(hidden_decay) * hidden + recurrent_term + w_in @ driver)
        rows.append(np.concatenate([[1.0, x], traces, trace_deltas, [novelty], hidden]))
    names = ["bias", "observed_current"]
    names.extend([f"ema_tau_{tau:g}" for tau in timescales])
    names.extend([f"ema_delta_{i}_{i+1}" for i in range(max(0, len(timescales) - 1))])
    names.append("novelty_vs_slowest_ema")
    names.extend([f"hidden_{idx}" for idx in range(hidden.size)])
    features = np.vstack(rows)
    return FeatureBundle(
        features=features,
        temporal_start=2,
        names=names,
        diagnostics={
            "state_location": "readout/interface temporal substrate reference",
            "timescales": timescales,
            "hidden_units": int(hidden.size),
            "include_recurrence": bool(include_recurrence),
            "recurrent_scale": float(recurrent_scale),
            "input_scale": float(input_scale),
            "hidden_decay": float(hidden_decay),
            "feature_count": int(features.shape[1]),
            "train_prefix_state_norm_mean": float(np.mean(np.linalg.norm(features[:train_end, 2:], axis=1))),
            "test_state_norm_mean": float(np.mean(np.linalg.norm(features[train_end:, 2:], axis=1))),
            "bounded_state": "tanh hidden units plus bounded EMA traces over z-scored input",
        },
    )


def random_reservoir_features(
    observed: np.ndarray,
    *,
    seed: int,
    units: int,
    spectral_radius: float,
    input_scale: float,
) -> FeatureBundle:
    values = np.asarray(observed, dtype=float)
    rng = np.random.default_rng(seed + 61231)
    w_in = rng.normal(0.0, float(input_scale), size=(units, 2))
    raw = rng.normal(0.0, 1.0, size=(units, units))
    eig = max(1e-9, float(max(abs(np.linalg.eigvals(raw)))))
    w_res = raw * (float(spectral_radius) / eig)
    state = np.zeros(units, dtype=float)
    rows = []
    for value in values:
        u = np.asarray([1.0, float(value)], dtype=float)
        state = np.tanh(w_res @ state + w_in @ u)
        rows.append(np.concatenate([[1.0, float(value)], state]))
    return FeatureBundle(
        features=np.vstack(rows),
        temporal_start=2,
        names=["bias", "observed_current"] + [f"reservoir_{idx}" for idx in range(units)],
        diagnostics={
            "state_location": "random reservoir control",
            "units": int(units),
            "spectral_radius": float(spectral_radius),
            "input_scale": float(input_scale),
        },
    )


def freeze_temporal_columns(features: np.ndarray, train_end: int, temporal_start: int) -> np.ndarray:
    out = np.asarray(features, dtype=float).copy()
    if len(out) > train_end and train_end > 0:
        out[train_end:, temporal_start:] = out[train_end - 1, temporal_start:]
    return out


def append_timeseries(
    rows: list[dict[str, Any]],
    *,
    task: SequenceTask,
    seed: int,
    model: str,
    prediction: np.ndarray,
) -> None:
    for step, (obs, target, pred) in enumerate(zip(task.observed, task.target, prediction)):
        rows.append(
            {
                "task": task.name,
                "seed": int(seed),
                "model": model,
                "step": int(step),
                "split": "train" if step < task.train_end else "test",
                "observed": float(obs),
                "target": float(target),
                "prediction": float(pred),
                "squared_error": float((float(pred) - float(target)) ** 2),
            }
        )


def run_online_model(
    *,
    task: SequenceTask,
    seed: int,
    model: str,
    features: np.ndarray,
    args: argparse.Namespace,
    update_target: np.ndarray | None = None,
    update_enabled: bool = True,
    diagnostics: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], np.ndarray]:
    norm_features, norm_meta = normalize_features(features, task.train_end)
    pred, online_meta = online_normalized_lms(
        norm_features,
        task.target,
        train_end=task.train_end,
        lr=args.readout_lr,
        decay=args.readout_decay,
        weight_clip=args.weight_clip,
        output_clip=args.output_clip,
        update_target=update_target,
        update_enabled=update_enabled,
    )
    row = evaluate_probe(
        task.name,
        seed,
        task.train_end,
        task.target,
        pred,
        model,
        {
            **(diagnostics or {}),
            "readout": "online_normalized_lms_prediction_before_update",
            "feature_norm": "train_prefix_only",
            "online_meta": online_meta,
            "feature_count": int(features.shape[1]),
            "norm_columns": int(len(norm_meta["feature_mu"])),
        },
    )
    return row, pred


def run_train_prefix_esn(task: SequenceTask, *, seed: int, args: argparse.Namespace) -> tuple[dict[str, Any], np.ndarray]:
    model = EchoStateNetworkModel(
        seed=seed,
        units=args.esn_units,
        spectral_radius=args.esn_spectral_radius,
        input_scale=args.esn_input_scale,
        ridge=args.ridge,
    )
    model.fit(task)
    pred, diagnostics = model.predict_all(task)
    return (
        evaluate_probe(task.name, seed, task.train_end, task.target, pred, "fixed_esn_train_prefix_ridge_baseline", diagnostics),
        pred,
    )


def run_task(task: SequenceTask, *, seed: int, args: argparse.Namespace) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    timeseries: list[dict[str, Any]] = []
    trace = collect_cra_trace(task, seed=seed, args=args)
    lag = lag_matrix(task.observed, args.history)
    temporal = temporal_substrate_features(
        task.observed,
        seed=seed,
        train_end=task.train_end,
        timescales=parse_timescales(args.temporal_timescales),
        hidden_units=args.temporal_hidden_units,
        recurrent_scale=args.temporal_recurrent_scale,
        input_scale=args.temporal_input_scale,
        hidden_decay=args.temporal_hidden_decay,
        include_recurrence=True,
    )
    no_recurrence = temporal_substrate_features(
        task.observed,
        seed=seed,
        train_end=task.train_end,
        timescales=parse_timescales(args.temporal_timescales),
        hidden_units=args.temporal_hidden_units,
        recurrent_scale=0.0,
        input_scale=args.temporal_input_scale,
        hidden_decay=args.temporal_hidden_decay,
        include_recurrence=False,
    )
    reservoir = random_reservoir_features(
        task.observed,
        seed=seed,
        units=args.reservoir_units,
        spectral_radius=args.reservoir_spectral_radius,
        input_scale=args.reservoir_input_scale,
    )
    wrong_target = shuffled_target(task.target, task.train_end, seed)

    model_specs: list[tuple[str, np.ndarray, np.ndarray | None, bool, dict[str, Any]]] = [
        (
            "raw_cra_v2_1_online",
            np.column_stack([np.ones(len(task.target)), trace.cra_prediction]),
            None,
            False,
            {"role": "raw CRA v2.1 prediction", "backend": trace.diagnostics.get("backend")},
        ),
        ("lag_only_online_lms_control", lag, None, True, {"role": "same causal lag budget", "history": int(args.history)}),
        (
            "random_reservoir_online_lms_control",
            reservoir.features,
            None,
            True,
            reservoir.diagnostics,
        ),
        (
            "temporal_substrate_online_candidate",
            temporal.features,
            None,
            True,
            temporal.diagnostics,
        ),
        (
            "temporal_substrate_plus_lag_online_reference",
            np.column_stack([temporal.features, lag[:, 1:]]),
            None,
            True,
            {**temporal.diagnostics, "includes_lag_budget": int(args.history)},
        ),
        (
            "no_recurrence_temporal_ablation",
            no_recurrence.features,
            None,
            True,
            no_recurrence.diagnostics,
        ),
        (
            "frozen_temporal_state_ablation",
            freeze_temporal_columns(temporal.features, task.train_end, temporal.temporal_start),
            None,
            True,
            {**temporal.diagnostics, "ablation": "temporal columns frozen after train prefix"},
        ),
        (
            "shuffled_temporal_state_sham",
            shuffled_rows(temporal.features, task.train_end, seed),
            None,
            True,
            {**temporal.diagnostics, "sham": "feature rows shuffled within train/test splits"},
        ),
        (
            "temporal_substrate_shuffled_target_control",
            temporal.features,
            wrong_target,
            True,
            {**temporal.diagnostics, "control": "online readout updates against shuffled targets"},
        ),
        (
            "temporal_substrate_no_plasticity_ablation",
            temporal.features,
            None,
            False,
            {**temporal.diagnostics, "ablation": "readout updates disabled"},
        ),
    ]
    for model, features, update_target, update_enabled, diagnostics in model_specs:
        row, pred = run_online_model(
            task=task,
            seed=seed,
            model=model,
            features=features,
            args=args,
            update_target=update_target,
            update_enabled=update_enabled,
            diagnostics=diagnostics,
        )
        rows.append(row)
        append_timeseries(timeseries, task=task, seed=seed, model=model, prediction=pred)

    esn_row, esn_pred = run_train_prefix_esn(task, seed=seed, args=args)
    rows.append(esn_row)
    append_timeseries(timeseries, task=task, seed=seed, model="fixed_esn_train_prefix_ridge_baseline", prediction=esn_pred)

    diagnostics = {
        "task": task.name,
        "seed": int(seed),
        "trace_backend": trace.diagnostics.get("backend"),
        "temporal_feature_count": int(temporal.features.shape[1]),
        "lag_feature_count": int(lag.shape[1]),
        "temporal_feature_names": temporal.names,
        "heldout_task": task.name == "heldout_long_memory",
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
    aggregate_scopes = {
        "standard_three_geomean": [task for task in tasks if task in STANDARD_TASKS],
        "all_tasks_geomean": tasks,
    }
    for scope, scope_tasks in aggregate_scopes.items():
        if not scope_tasks:
            continue
        for model in models:
            for seed in seeds:
                subset = [r for r in rows if r["model"] == model and r["seed"] == seed and r["status"] == "pass"]
                by_task = {r["task"]: r for r in subset}
                if all(task in by_task for task in scope_tasks):
                    aggregate_rows.append(
                        {
                            "task": scope,
                            "model": model,
                            "seed": int(seed),
                            "status": "pass",
                            "geomean_mse": geometric_mean([by_task[task]["mse"] for task in scope_tasks]),
                            "geomean_nmse": geometric_mean([by_task[task]["nmse"] for task in scope_tasks]),
                        }
                    )
    aggregate_summary: list[dict[str, Any]] = []
    for scope in sorted({row["task"] for row in aggregate_rows}):
        for model in models:
            subset = [r for r in aggregate_rows if r["task"] == scope and r["model"] == model and r["status"] == "pass"]
            values = [float(r["geomean_mse"]) for r in subset if r["geomean_mse"] is not None]
            nmse_values = [float(r["geomean_nmse"]) for r in subset if r["geomean_nmse"] is not None]
            aggregate_summary.append(
                {
                    "task": scope,
                    "model": model,
                    "status": "pass" if values else "fail",
                    "seed_count": len(values),
                    "geomean_mse_mean": mean(values),
                    "geomean_mse_median": float(np.median(values)) if values else None,
                    "geomean_mse_worst": max(values) if values else None,
                    "geomean_nmse_mean": mean(nmse_values),
                }
            )
    for scope in sorted({row["task"] for row in aggregate_summary}):
        pass_rows = [r for r in aggregate_summary if r["task"] == scope and r["status"] == "pass" and r["geomean_mse_mean"] is not None]
        pass_rows.sort(key=lambda row: float(row["geomean_mse_mean"]))
        rank = {row["model"]: idx + 1 for idx, row in enumerate(pass_rows)}
        for row in aggregate_summary:
            if row["task"] == scope:
                row["rank_by_geomean_mse"] = rank.get(row["model"])
    aggregate_summary.sort(key=lambda row: (row["task"], row.get("rank_by_geomean_mse") or 10_000, row["model"]))
    return summary_rows, aggregate_rows, aggregate_summary


def metric(summary_rows: list[dict[str, Any]], task: str, model: str, key: str = "mse_mean") -> float:
    row = next((r for r in summary_rows if r["task"] == task and r["model"] == model), None)
    if not row or row.get(key) is None:
        return math.inf
    return float(row[key])


def aggregate_metric(aggregate_summary: list[dict[str, Any]], scope: str, model: str) -> float:
    row = next((r for r in aggregate_summary if r["task"] == scope and r["model"] == model), None)
    if not row or row.get("geomean_mse_mean") is None:
        return math.inf
    return float(row["geomean_mse_mean"])


def classify(summary_rows: list[dict[str, Any]], aggregate_summary: list[dict[str, Any]]) -> dict[str, Any]:
    candidate = "temporal_substrate_online_candidate"
    lag = "lag_only_online_lms_control"
    shuffled = "shuffled_temporal_state_sham"
    frozen = "frozen_temporal_state_ablation"
    no_recur = "no_recurrence_temporal_ablation"
    no_plasticity = "temporal_substrate_no_plasticity_ablation"
    heldout_candidate = metric(summary_rows, "heldout_long_memory", candidate)
    heldout_lag = metric(summary_rows, "heldout_long_memory", lag)
    heldout_shuffled = metric(summary_rows, "heldout_long_memory", shuffled)
    heldout_frozen = metric(summary_rows, "heldout_long_memory", frozen)
    heldout_no_recur = metric(summary_rows, "heldout_long_memory", no_recur)
    heldout_no_plasticity = metric(summary_rows, "heldout_long_memory", no_plasticity)
    standard_candidate = aggregate_metric(aggregate_summary, "standard_three_geomean", candidate)
    standard_lag = aggregate_metric(aggregate_summary, "standard_three_geomean", lag)
    all_candidate = aggregate_metric(aggregate_summary, "all_tasks_geomean", candidate)
    all_lag = aggregate_metric(aggregate_summary, "all_tasks_geomean", lag)

    def ratio(control: float, cand: float) -> float | None:
        if not math.isfinite(control) or not math.isfinite(cand) or cand <= 0:
            return None
        return control / cand

    heldout_vs_lag = ratio(heldout_lag, heldout_candidate)
    heldout_vs_shuffled = ratio(heldout_shuffled, heldout_candidate)
    heldout_vs_frozen = ratio(heldout_frozen, heldout_candidate)
    heldout_vs_no_recur = ratio(heldout_no_recur, heldout_candidate)
    heldout_vs_no_plasticity = ratio(heldout_no_plasticity, heldout_candidate)
    standard_vs_lag = ratio(standard_lag, standard_candidate)
    all_vs_lag = ratio(all_lag, all_candidate)

    if (
        heldout_vs_lag is not None
        and heldout_vs_lag >= 1.10
        and heldout_vs_shuffled is not None
        and heldout_vs_shuffled >= 1.10
        and heldout_vs_frozen is not None
        and heldout_vs_frozen >= 1.10
        and heldout_vs_no_plasticity is not None
        and heldout_vs_no_plasticity >= 1.10
    ):
        if heldout_vs_no_recur is not None and heldout_vs_no_recur >= 1.05:
            outcome = "temporal_reference_ready_for_5_19b"
            recommendation = "Proceed to Tier 5.19b benchmark/sham/regression gate; recurrence appears causally useful on the held-out diagnostic."
        else:
            outcome = "fading_memory_ready_but_recurrence_not_yet_specific"
            recommendation = "Proceed carefully: fading memory helps, but recurrence-specific value needs a sharper ablation in 5.19b."
    elif heldout_vs_lag is not None and heldout_vs_lag >= 1.10:
        outcome = "temporal_reference_promising_but_sham_separation_incomplete"
        recommendation = "Repair sham separation before promotion; do not freeze or migrate to hardware."
    else:
        outcome = "temporal_reference_not_ready"
        recommendation = "Do not promote; inspect whether lag-only, reservoir controls, or task design explains the result."

    return {
        "outcome": outcome,
        "recommendation": recommendation,
        "heldout_candidate_mse": heldout_candidate,
        "heldout_lag_mse": heldout_lag,
        "heldout_shuffled_mse": heldout_shuffled,
        "heldout_frozen_mse": heldout_frozen,
        "heldout_no_recurrence_mse": heldout_no_recur,
        "heldout_no_plasticity_mse": heldout_no_plasticity,
        "heldout_vs_lag_margin": heldout_vs_lag,
        "heldout_vs_shuffled_margin": heldout_vs_shuffled,
        "heldout_vs_frozen_margin": heldout_vs_frozen,
        "heldout_vs_no_recurrence_margin": heldout_vs_no_recur,
        "heldout_vs_no_plasticity_margin": heldout_vs_no_plasticity,
        "standard_candidate_geomean_mse": standard_candidate,
        "standard_lag_geomean_mse": standard_lag,
        "standard_vs_lag_margin": standard_vs_lag,
        "all_tasks_candidate_geomean_mse": all_candidate,
        "all_tasks_lag_geomean_mse": all_lag,
        "all_tasks_vs_lag_margin": all_vs_lag,
    }


def write_report(output_dir: Path, payload: dict[str, Any]) -> None:
    c = payload["classification"]
    lines = [
        "# Tier 5.19a Local Continuous Temporal Substrate Reference",
        "",
        f"- Generated: `{payload['generated_at_utc']}`",
        f"- Status: **{payload['status'].upper()}**",
        f"- Criteria: `{payload['criteria_passed']}/{payload['criteria_total']}`",
        f"- Outcome: `{c['outcome']}`",
        "",
        "## Claim Boundary",
        "",
        payload["claim_boundary"],
        "",
        "## Classification",
        "",
        f"- Held-out candidate MSE: `{c['heldout_candidate_mse']}`",
        f"- Held-out lag-only MSE: `{c['heldout_lag_mse']}`",
        f"- Held-out margin vs lag-only: `{c['heldout_vs_lag_margin']}`",
        f"- Held-out margin vs shuffled state: `{c['heldout_vs_shuffled_margin']}`",
        f"- Held-out margin vs frozen state: `{c['heldout_vs_frozen_margin']}`",
        f"- Held-out margin vs no recurrence: `{c['heldout_vs_no_recurrence_margin']}`",
        f"- Standard-suite candidate geomean MSE: `{c['standard_candidate_geomean_mse']}`",
        f"- Standard-suite lag-only geomean MSE: `{c['standard_lag_geomean_mse']}`",
        f"- Recommendation: {c['recommendation']}",
        "",
        "## Aggregate Summary",
        "",
        "| Scope | Model | Rank | Geomean MSE mean | Geomean NMSE mean |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for row in payload["aggregate_summary"]:
        lines.append(
            f"| {row['task']} | {row['model']} | {row.get('rank_by_geomean_mse')} | {row['geomean_mse_mean']} | {row['geomean_nmse_mean']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation Rule",
            "",
            "- This is a local software reference gate, not a baseline freeze.",
            "- If shams or lag-only explain the result, park or repair before 5.19b.",
            "- Do not move any Tier 7 benchmark workload to hardware from this tier alone.",
            "",
        ]
    )
    (output_dir / "tier5_19a_report.md").write_text("\n".join(lines), encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    tasks = parse_csv(args.tasks)
    seeds = parse_seeds(args)
    started = time.perf_counter()
    all_rows: list[dict[str, Any]] = []
    all_timeseries: list[dict[str, Any]] = []
    task_diagnostics: list[dict[str, Any]] = []
    for seed in seeds:
        for task_name in tasks:
            task = build_task(task_name, args.length, seed, args.horizon)
            rows, timeseries, diagnostics = run_task(task, seed=seed, args=args)
            all_rows.extend(rows)
            all_timeseries.extend(timeseries)
            task_diagnostics.append(diagnostics)
            write_json(
                output_dir / f"{task.name}_seed{seed}_task.json",
                {
                    "task": task.name,
                    "display_name": task.display_name,
                    "seed": int(seed),
                    "length": int(len(task.target)),
                    "train_end": int(task.train_end),
                    "horizon": int(task.horizon),
                    "metadata": task.metadata,
                },
            )
    models = sorted({row["model"] for row in all_rows})
    summary_rows, aggregate_rows, aggregate_summary = summarize(all_rows, tasks, models, seeds)
    classification = classify(summary_rows, aggregate_summary)
    criteria = [
        criterion("runner revision current", RUNNER_REVISION, "expected current source", RUNNER_REVISION.endswith("_0001")),
        criterion("contract linked", "docs/TIER5_19_CONTINUOUS_TEMPORAL_DYNAMICS_CONTRACT.md", "present", (ROOT / "docs/TIER5_19_CONTINUOUS_TEMPORAL_DYNAMICS_CONTRACT.md").exists()),
        criterion("all tasks known", tasks, "standard tasks plus heldout_long_memory", all(t in STANDARD_TASKS or t == "heldout_long_memory" for t in tasks)),
        criterion("heldout diagnostic included", "heldout_long_memory" in tasks, "== true", "heldout_long_memory" in tasks),
        criterion("all runs completed", f"{sum(r['status'] == 'pass' for r in all_rows)}/{len(all_rows)}", "all pass", all(r["status"] == "pass" for r in all_rows)),
        criterion("raw CRA v2.1 control present", "raw_cra_v2_1_online" in models, "== true", "raw_cra_v2_1_online" in models),
        criterion("lag-only control present", "lag_only_online_lms_control" in models, "== true", "lag_only_online_lms_control" in models),
        criterion("reservoir controls present", "fixed and random reservoir", "all present", all(m in models for m in ["fixed_esn_train_prefix_ridge_baseline", "random_reservoir_online_lms_control"])),
        criterion("temporal substrate candidate present", "temporal_substrate_online_candidate" in models, "== true", "temporal_substrate_online_candidate" in models),
        criterion("required shams present", "frozen/shuffled/no recurrence/no plasticity/shuffled target", "all present", all(m in models for m in ["frozen_temporal_state_ablation", "shuffled_temporal_state_sham", "no_recurrence_temporal_ablation", "temporal_substrate_no_plasticity_ablation", "temporal_substrate_shuffled_target_control"])),
        criterion("classification produced", classification["outcome"], "non-empty", bool(classification["outcome"])),
        criterion("software only", "no SpiNNaker or EBRAINS calls", "true", True),
    ]
    failed = [c for c in criteria if not c["passed"]]
    payload = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "status": "pass" if not failed else "fail",
        "output_dir": str(output_dir),
        "criteria": criteria,
        "criteria_passed": len(criteria) - len(failed),
        "criteria_total": len(criteria),
        "failed_criteria": failed,
        "tasks": tasks,
        "seeds": seeds,
        "backend": args.backend,
        "length": int(args.length),
        "horizon": int(args.horizon),
        "history": int(args.history),
        "runtime_seconds": time.perf_counter() - started,
        "summary_rows": summary_rows,
        "aggregate_rows": aggregate_rows,
        "aggregate_summary": aggregate_summary,
        "classification": classification,
        "summary": classification,
        "run_rows": all_rows,
        "task_diagnostics": task_diagnostics,
        "fairness_contract": {
            "tier": TIER,
            "contract": "docs/TIER5_19_CONTINUOUS_TEMPORAL_DYNAMICS_CONTRACT.md",
            "split": "chronological",
            "normalization": "train-prefix z-score for tasks; train-prefix feature normalization for online readouts",
            "prediction": "online readouts predict before update",
            "hardware_policy": "software-only local reference; hardware blocked until promotion",
            "no_future_leakage": [
                "task normalization uses chronological train prefix only",
                "feature normalization uses train prefix only",
                "online readouts update after prediction",
                "shuffled controls shuffle within train/test splits",
                "ESN readout fits train prefix only",
            ],
            "nonclaims": [
                "not hardware evidence",
                "not a software baseline freeze",
                "not a promoted temporal-substrate mechanism",
                "not universal benchmark superiority",
            ],
        },
        "claim_boundary": (
            "Tier 5.19a is local software reference evidence only. It defines and "
            "tests a bounded temporal-substrate candidate against lag, reservoir, "
            "frozen/shuffled-state, no-recurrence, no-plasticity, and shuffled-"
            "target controls. It is not hardware evidence, not a baseline freeze, "
            "and not a promoted CRA mechanism by itself."
        ),
    }
    write_json(output_dir / "tier5_19a_results.json", payload)
    write_json(output_dir / "tier5_19a_fairness_contract.json", payload["fairness_contract"])
    write_csv(
        output_dir / "tier5_19a_summary.csv",
        summary_rows,
        ["task", "model", "status", "seed_count", "mse_mean", "mse_median", "mse_std", "mse_worst", "nmse_mean", "tail_mse_mean", "test_corr_mean"],
    )
    write_csv(
        output_dir / "tier5_19a_aggregate.csv",
        aggregate_rows,
        ["task", "model", "seed", "status", "geomean_mse", "geomean_nmse"],
    )
    write_csv(
        output_dir / "tier5_19a_timeseries.csv",
        all_timeseries,
        ["task", "seed", "model", "step", "split", "observed", "target", "prediction", "squared_error"],
    )
    write_report(output_dir, payload)
    write_json(
        OUTPUT_ROOT / "tier5_19a_latest_manifest.json",
        {
            "tier": TIER,
            "runner_revision": RUNNER_REVISION,
            "generated_at_utc": payload["generated_at_utc"],
            "status": payload["status"],
            "manifest": str(output_dir / "tier5_19a_results.json"),
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
    parser.add_argument("--temporal-timescales", default="2,4,8,16,32,64,128")
    parser.add_argument("--temporal-hidden-units", type=int, default=16)
    parser.add_argument("--temporal-recurrent-scale", type=float, default=0.65)
    parser.add_argument("--temporal-input-scale", type=float, default=0.45)
    parser.add_argument("--temporal-hidden-decay", type=float, default=0.72)
    parser.add_argument("--reservoir-units", type=int, default=32)
    parser.add_argument("--reservoir-spectral-radius", type=float, default=0.9)
    parser.add_argument("--reservoir-input-scale", type=float, default=0.5)
    parser.add_argument("--esn-units", type=int, default=64)
    parser.add_argument("--esn-spectral-radius", type=float, default=0.9)
    parser.add_argument("--esn-input-scale", type=float, default=0.5)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    result = run(args)
    print(
        json.dumps(
            {
                "tier": TIER,
                "status": result["status"],
                "criteria": f"{result['criteria_passed']}/{result['criteria_total']}",
                "classification": result["classification"]["outcome"],
                "output_dir": result["output_dir"],
            },
            indent=2,
        )
    )
    if result["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
