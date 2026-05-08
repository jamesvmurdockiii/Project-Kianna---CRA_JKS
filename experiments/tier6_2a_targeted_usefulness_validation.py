#!/usr/bin/env python3
"""Tier 6.2a - Targeted hard-task validation over frozen v2.3.

Tier 7.0j froze v2.3 as a narrow generic bounded recurrent-state software
baseline on the locked Mackey-Glass/Lorenz/NARMA10 public scoreboard. This
runner asks the next, more diagnostic question:

Where does v2.3 help or fail on harder controlled regimes that resemble the
next real-ish adapter targets?

This is not a private usefulness proof. It is a software-only diagnostic gate
used to select the next mechanism, real-ish adapter, or claim narrowing step.
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
    write_json,
)
from tier5_19b_temporal_substrate_gate import temporal_features_variant  # noqa: E402
from tier7_0_standard_dynamical_benchmarks import (  # noqa: E402
    SequenceTask,
    chronological_split,
    geometric_mean,
    parse_csv,
    parse_seeds,
    zscore_from_train,
)
from tier7_0b_continuous_regression_failure_analysis import lag_matrix  # noqa: E402
from tier7_0c_continuous_readout_repair import shuffled_rows, shuffled_target  # noqa: E402


TIER = "Tier 6.2a - Targeted Hard-Task Validation Over v2.3"
RUNNER_REVISION = "tier6_2a_targeted_usefulness_validation_20260508_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier6_2a_20260508_targeted_usefulness_validation"
DEFAULT_TASKS = (
    "variable_delay_multi_cue,"
    "hidden_context_reentry,"
    "concept_drift_stream,"
    "anomaly_detection_stream,"
    "delayed_control_proxy"
)

V23 = "v2_3_generic_bounded_recurrent_state"
V22 = "v2_2_fading_memory_reference"
LAG = "lag_only_online_lms_control"
RESERVOIR = "fixed_random_reservoir_online_control"
ESN = "fixed_esn_train_prefix_ridge_baseline"
RESET = "v2_3_state_reset_ablation"
SHUFFLED = "v2_3_shuffled_state_sham"
SHUFFLED_TARGET = "v2_3_shuffled_target_control"
NO_UPDATE = "v2_3_no_update_ablation"
REQUIRED_MODELS = [V23, V22, LAG, RESERVOIR, ESN, RESET, SHUFFLED, SHUFFLED_TARGET, NO_UPDATE]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_csv_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def finite_or_inf(value: Any) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return math.inf
    return out if math.isfinite(out) else math.inf


def ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None:
        return None
    if not math.isfinite(float(numerator)) or not math.isfinite(float(denominator)):
        return None
    if abs(float(denominator)) < 1e-12:
        return None
    return float(numerator) / float(denominator)


def _smooth_noise(rng: np.random.Generator, total: int, *, scale: float = 0.2, decay: float = 0.82) -> np.ndarray:
    raw = rng.normal(0.0, scale, size=total)
    out = np.zeros(total, dtype=float)
    for idx in range(1, total):
        out[idx] = decay * out[idx - 1] + raw[idx]
    return out


def variable_delay_multi_cue(length: int, seed: int, *, horizon: int) -> SequenceTask:
    """Delayed cue stream with alternating delay bands and distractors.

    The current observation is not enough by itself: the target is a delayed
    cue whose relevant delay switches between short and long bands. This is a
    diagnostic for temporal retention and readout adaptation, not a public
    benchmark.
    """
    del horizon
    rng = np.random.default_rng(seed + 62011)
    warmup = 96
    max_delay = 36
    total = length + warmup + max_delay + 8
    cue = rng.choice([-1.0, 1.0], size=total)
    hold = rng.integers(5, 17, size=total)
    for idx in range(1, total):
        if idx % int(hold[idx]) != 0:
            cue[idx] = cue[idx - 1]
    distractor = _smooth_noise(rng, total, scale=0.35, decay=0.76)
    delay_schedule = np.where(((np.arange(total) // 240) % 2) == 0, 8, 28)
    delayed = np.zeros(total, dtype=float)
    for idx in range(max_delay, total):
        delayed[idx] = cue[idx - int(delay_schedule[idx])]
    observed_raw = np.tanh(0.72 * cue + 0.28 * distractor + 0.10 * np.roll(cue, 3))
    target_raw = delayed
    observed_raw = observed_raw[warmup : warmup + length]
    target_raw = target_raw[warmup : warmup + length]
    train_end = chronological_split(length, 0.65)
    observed, obs_mu, obs_sd = zscore_from_train(observed_raw, train_end)
    target, tgt_mu, tgt_sd = zscore_from_train(target_raw, train_end)
    return SequenceTask(
        name="variable_delay_multi_cue",
        display_name="Variable-delay multi-cue diagnostic",
        observed=observed,
        target=target,
        train_end=train_end,
        horizon=1,
        metadata={
            "obs_mu": obs_mu,
            "obs_sd": obs_sd,
            "target_mu": tgt_mu,
            "target_sd": tgt_sd,
            "delay_bands": [8, 28],
            "diagnostic_role": "temporal retention and variable delayed-credit pressure",
        },
    )


def hidden_context_reentry(length: int, seed: int, *, horizon: int) -> SequenceTask:
    """A-B-A context reentry where the same signal has different meanings."""
    del horizon
    rng = np.random.default_rng(seed + 62021)
    warmup = 64
    total = length + warmup + 8
    signal = rng.choice([-1.0, 1.0], size=total)
    for idx in range(1, total):
        if rng.random() < 0.86:
            signal[idx] = signal[idx - 1]
    phase = np.arange(total) // max(64, total // 6)
    context = np.where(np.isin(phase % 6, [0, 1, 4, 5]), 1.0, -1.0)
    cue_pulse = np.zeros(total, dtype=float)
    for idx in range(0, total, max(64, total // 6)):
        cue_pulse[idx : min(total, idx + 6)] = context[idx]
    distractor = _smooth_noise(rng, total, scale=0.18, decay=0.64)
    observed_raw = np.tanh(0.78 * signal + 0.18 * cue_pulse + 0.10 * distractor)
    target_raw = signal * context
    observed_raw = observed_raw[warmup : warmup + length]
    target_raw = target_raw[warmup : warmup + length]
    train_end = chronological_split(length, 0.65)
    observed, obs_mu, obs_sd = zscore_from_train(observed_raw, train_end)
    target, tgt_mu, tgt_sd = zscore_from_train(target_raw, train_end)
    return SequenceTask(
        name="hidden_context_reentry",
        display_name="Hidden-context A-B-A reentry diagnostic",
        observed=observed,
        target=target,
        train_end=train_end,
        horizon=1,
        metadata={
            "obs_mu": obs_mu,
            "obs_sd": obs_sd,
            "target_mu": tgt_mu,
            "target_sd": tgt_sd,
            "diagnostic_role": "same signal, different action depending on remembered/reentered context",
        },
    )


def concept_drift_stream(length: int, seed: int, *, horizon: int) -> SequenceTask:
    """Streaming regression with nonstationary rule switches and smooth drift."""
    del horizon
    rng = np.random.default_rng(seed + 62031)
    warmup = 80
    total = length + warmup + 8
    x = _smooth_noise(rng, total, scale=0.42, decay=0.55)
    x = np.tanh(x + 0.25 * np.sin(np.arange(total) / 17.0))
    rule = np.where(((np.arange(total) // 360) % 2) == 0, 1.0, -1.0)
    drift = np.sin(np.arange(total) / 220.0)
    target_raw = np.tanh(rule * (0.85 * x + 0.25 * np.roll(x, 5)) + 0.35 * drift)
    observed_raw = np.tanh(x + 0.08 * rng.normal(size=total))
    observed_raw = observed_raw[warmup : warmup + length]
    target_raw = target_raw[warmup : warmup + length]
    train_end = chronological_split(length, 0.65)
    observed, obs_mu, obs_sd = zscore_from_train(observed_raw, train_end)
    target, tgt_mu, tgt_sd = zscore_from_train(target_raw, train_end)
    return SequenceTask(
        name="concept_drift_stream",
        display_name="Online concept-drift stream diagnostic",
        observed=observed,
        target=target,
        train_end=train_end,
        horizon=1,
        metadata={
            "obs_mu": obs_mu,
            "obs_sd": obs_sd,
            "target_mu": tgt_mu,
            "target_sd": tgt_sd,
            "switch_period": 360,
            "diagnostic_role": "online adaptation under changing mapping",
        },
    )


def anomaly_detection_stream(length: int, seed: int, *, horizon: int) -> SequenceTask:
    """Rare event stream where target marks near-future anomaly pressure."""
    rng = np.random.default_rng(seed + 62041)
    warmup = 100
    total = length + warmup + horizon + 16
    base = _smooth_noise(rng, total, scale=0.18, decay=0.91)
    anomaly = np.zeros(total, dtype=float)
    cursor = 120 + int(seed % 17)
    while cursor < total - 24:
        width = int(rng.integers(3, 9))
        sign = float(rng.choice([-1.0, 1.0]))
        anomaly[cursor : cursor + width] = sign
        cursor += int(rng.integers(70, 150))
    precursor = np.zeros(total, dtype=float)
    for idx in np.flatnonzero(anomaly):
        start = max(0, idx - int(max(2, horizon)))
        precursor[start:idx] += 0.25 * float(np.sign(anomaly[idx]))
    observed_raw = np.tanh(base + precursor + 0.75 * anomaly + 0.03 * rng.normal(size=total))
    future_pressure = np.zeros(total, dtype=float)
    lookahead = int(max(2, horizon))
    for idx in range(total - lookahead):
        future_pressure[idx] = np.max(np.abs(anomaly[idx + 1 : idx + 1 + lookahead]))
    target_raw = 2.0 * future_pressure - 1.0
    observed_raw = observed_raw[warmup : warmup + length]
    target_raw = target_raw[warmup : warmup + length]
    train_end = chronological_split(length, 0.65)
    observed, obs_mu, obs_sd = zscore_from_train(observed_raw, train_end)
    target, tgt_mu, tgt_sd = zscore_from_train(target_raw, train_end)
    return SequenceTask(
        name="anomaly_detection_stream",
        display_name="Near-future anomaly stream diagnostic",
        observed=observed,
        target=target,
        train_end=train_end,
        horizon=int(max(2, horizon)),
        metadata={
            "obs_mu": obs_mu,
            "obs_sd": obs_sd,
            "target_mu": tgt_mu,
            "target_sd": tgt_sd,
            "diagnostic_role": "rare-event anticipation and tail stability",
        },
    )


def delayed_control_proxy(length: int, seed: int, *, horizon: int) -> SequenceTask:
    """One-dimensional delayed-control proxy with inertia and delayed reward."""
    rng = np.random.default_rng(seed + 62051)
    warmup = 90
    total = length + warmup + horizon + 16
    setpoint = np.sin(np.arange(total) / 45.0) + 0.4 * np.sign(np.sin(np.arange(total) / 190.0))
    disturbance = _smooth_noise(rng, total, scale=0.24, decay=0.88)
    state = np.zeros(total, dtype=float)
    for idx in range(1, total):
        state[idx] = 0.91 * state[idx - 1] + 0.08 * setpoint[idx - 1] + 0.14 * disturbance[idx]
    error = setpoint - state
    momentum = np.zeros(total, dtype=float)
    for idx in range(1, total):
        momentum[idx] = 0.86 * momentum[idx - 1] + 0.14 * error[idx]
    observed_raw = np.tanh(error + 0.16 * disturbance)
    target_raw = np.tanh(0.72 * np.roll(error, int(max(1, horizon))) + 0.44 * momentum)
    observed_raw = observed_raw[warmup : warmup + length]
    target_raw = target_raw[warmup : warmup + length]
    train_end = chronological_split(length, 0.65)
    observed, obs_mu, obs_sd = zscore_from_train(observed_raw, train_end)
    target, tgt_mu, tgt_sd = zscore_from_train(target_raw, train_end)
    return SequenceTask(
        name="delayed_control_proxy",
        display_name="Delayed-control proxy diagnostic",
        observed=observed,
        target=target,
        train_end=train_end,
        horizon=int(max(1, horizon)),
        metadata={
            "obs_mu": obs_mu,
            "obs_sd": obs_sd,
            "target_mu": tgt_mu,
            "target_sd": tgt_sd,
            "diagnostic_role": "state -> action-like target under delayed consequence pressure",
        },
    )


TASK_BUILDERS = {
    "variable_delay_multi_cue": variable_delay_multi_cue,
    "hidden_context_reentry": hidden_context_reentry,
    "concept_drift_stream": concept_drift_stream,
    "anomaly_detection_stream": anomaly_detection_stream,
    "delayed_control_proxy": delayed_control_proxy,
}


def build_task(name: str, length: int, seed: int, horizon: int) -> SequenceTask:
    if name not in TASK_BUILDERS:
        raise ValueError(f"unknown Tier 6.2a task {name!r}")
    return TASK_BUILDERS[name](length, seed, horizon=horizon)


def run_task_models(task: SequenceTask, *, seed: int, args: argparse.Namespace, capture_timeseries: bool) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    timeseries: list[dict[str, Any]] = []
    timescales = parse_timescales(args.temporal_timescales)
    base_kwargs = {
        "seed": seed,
        "train_end": task.train_end,
        "timescales": timescales,
        "hidden_units": args.temporal_hidden_units,
        "recurrent_scale": args.temporal_recurrent_scale,
        "input_scale": args.temporal_input_scale,
        "hidden_decay": args.temporal_hidden_decay,
    }
    full = temporal_features_variant(task.observed, mode="full", **base_kwargs)
    fading = temporal_features_variant(task.observed, mode="fading_only", **base_kwargs)
    reset = temporal_features_variant(task.observed, mode="full", reset_interval=args.state_reset_interval, **base_kwargs)
    lag = lag_matrix(task.observed, args.history)
    reservoir = random_reservoir_features(
        task.observed,
        seed=seed,
        units=args.reservoir_units,
        spectral_radius=args.reservoir_spectral_radius,
        input_scale=args.reservoir_input_scale,
    )
    wrong_target = shuffled_target(task.target, task.train_end, seed)
    specs: list[tuple[str, np.ndarray, np.ndarray | None, bool, dict[str, Any]]] = [
        (LAG, lag, None, True, {"role": "same causal lag-budget online LMS control", "history": int(args.history)}),
        (RESERVOIR, reservoir.features, None, True, reservoir.diagnostics),
        (V22, fading.features, None, True, {**fading.diagnostics, "role": "frozen v2.2 fading-memory reference"}),
        (V23, full.features, None, True, {**full.diagnostics, "role": "frozen v2.3 generic bounded recurrent-state baseline"}),
        (RESET, reset.features, None, True, {**reset.diagnostics, "ablation": "v2.3 state reset periodically"}),
        (SHUFFLED, shuffled_rows(full.features, task.train_end, seed), None, True, {**full.diagnostics, "sham": "v2.3 rows shuffled within train/test splits"}),
        (SHUFFLED_TARGET, full.features, wrong_target, True, {**full.diagnostics, "control": "v2.3 readout updates against shuffled target"}),
        (NO_UPDATE, full.features, None, False, {**full.diagnostics, "ablation": "v2.3 readout updates disabled"}),
    ]
    for model, features, update_target, update_enabled, diagnostics in specs:
        row, pred = run_online_model(
            task=task,
            seed=seed,
            model=model,
            features=features,
            args=args,
            update_target=update_target,
            update_enabled=update_enabled,
            diagnostics={**diagnostics, "tier6_2a_task_role": task.metadata.get("diagnostic_role")},
        )
        rows.append(row)
        if capture_timeseries:
            append_timeseries(timeseries, task=task, seed=seed, model=model, prediction=pred)
    esn_row, esn_pred = run_train_prefix_esn(task, seed=seed, args=args)
    rows.append(esn_row)
    if capture_timeseries:
        append_timeseries(timeseries, task=task, seed=seed, model=ESN, prediction=esn_pred)
    diagnostics = {
        "task": task.name,
        "seed": int(seed),
        "v2_3_feature_count": int(full.features.shape[1]),
        "v2_2_feature_count": int(fading.features.shape[1]),
        "lag_feature_count": int(lag.shape[1]),
        "reservoir_feature_count": int(reservoir.features.shape[1]),
        "diagnostic_role": task.metadata.get("diagnostic_role"),
    }
    return rows, timeseries, diagnostics


def summarize(rows: list[dict[str, Any]], tasks: list[str], models: list[str], seeds: list[int]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    summary_rows: list[dict[str, Any]] = []
    for task in tasks:
        for model in models:
            subset = [r for r in rows if r["task"] == task and r["model"] == model and r["status"] == "pass"]
            values = [finite_or_inf(r.get("mse")) for r in subset]
            corr_values = [finite_or_inf(r.get("test_corr")) for r in subset if r.get("test_corr") is not None]
            summary_rows.append(
                {
                    "task": task,
                    "model": model,
                    "status": "pass" if len(subset) == len(seeds) and all(math.isfinite(v) for v in values) else "fail",
                    "seed_count": len(subset),
                    "mse_mean": mean(values),
                    "mse_median": float(np.median(values)) if values else None,
                    "mse_std": stdev(values),
                    "mse_worst": max(values) if values else None,
                    "nmse_mean": mean([finite_or_inf(r.get("nmse")) for r in subset]),
                    "tail_mse_mean": mean([finite_or_inf(r.get("tail_mse")) for r in subset]),
                    "test_corr_mean": mean(corr_values),
                }
            )
    aggregate_rows: list[dict[str, Any]] = []
    for model in models:
        for seed in seeds:
            subset = [r for r in rows if r["model"] == model and r["seed"] == seed and r["status"] == "pass"]
            by_task = {r["task"]: r for r in subset}
            if all(task in by_task for task in tasks):
                aggregate_rows.append(
                    {
                        "task": "all_targeted_diagnostics_geomean",
                        "model": model,
                        "seed": int(seed),
                        "status": "pass",
                        "geomean_mse": geometric_mean([by_task[task]["mse"] for task in tasks]),
                        "geomean_nmse": geometric_mean([by_task[task]["nmse"] for task in tasks]),
                    }
                )
    aggregate_summary: list[dict[str, Any]] = []
    for model in models:
        subset = [r for r in aggregate_rows if r["model"] == model and r["status"] == "pass"]
        mse_values = [finite_or_inf(r.get("geomean_mse")) for r in subset]
        nmse_values = [finite_or_inf(r.get("geomean_nmse")) for r in subset]
        aggregate_summary.append(
            {
                "task": "all_targeted_diagnostics_geomean",
                "model": model,
                "status": "pass" if len(mse_values) == len(seeds) and all(math.isfinite(v) for v in mse_values) else "fail",
                "seed_count": len(mse_values),
                "geomean_mse_mean": mean(mse_values),
                "geomean_mse_median": float(np.median(mse_values)) if mse_values else None,
                "geomean_mse_worst": max(mse_values) if mse_values else None,
                "geomean_nmse_mean": mean(nmse_values),
            }
        )
    ranked = sorted(
        [row for row in aggregate_summary if row["status"] == "pass" and math.isfinite(float(row["geomean_mse_mean"]))],
        key=lambda row: float(row["geomean_mse_mean"]),
    )
    rank = {row["model"]: idx + 1 for idx, row in enumerate(ranked)}
    for row in aggregate_summary:
        row["rank_by_geomean_mse"] = rank.get(row["model"])
    aggregate_summary.sort(key=lambda row: (row.get("rank_by_geomean_mse") or 10_000, row["model"]))
    return summary_rows, aggregate_rows, aggregate_summary


def metric(rows: list[dict[str, Any]], task: str, model: str, key: str = "mse_mean") -> float:
    row = next((item for item in rows if item.get("task") == task and item.get("model") == model), None)
    return finite_or_inf(row.get(key)) if row else math.inf


def aggregate_metric(rows: list[dict[str, Any]], model: str, key: str = "geomean_mse_mean") -> float:
    row = next((item for item in rows if item.get("model") == model), None)
    return finite_or_inf(row.get(key)) if row else math.inf


def classify(summary_rows: list[dict[str, Any]], aggregate_summary: list[dict[str, Any]], tasks: list[str]) -> dict[str, Any]:
    task_profiles: list[dict[str, Any]] = []
    v23_best_tasks: list[str] = []
    v23_beats_v22_tasks: list[str] = []
    v23_beats_simple_online_tasks: list[str] = []
    v23_sham_separated_tasks: list[str] = []
    esn_dominated_tasks: list[str] = []
    for task in tasks:
        task_model_rows = [row for row in summary_rows if row["task"] == task and row["status"] == "pass"]
        ranked = sorted(task_model_rows, key=lambda row: finite_or_inf(row.get("mse_mean")))
        best_model = ranked[0]["model"] if ranked else None
        v23 = metric(summary_rows, task, V23)
        v22 = metric(summary_rows, task, V22)
        lag = metric(summary_rows, task, LAG)
        reservoir = metric(summary_rows, task, RESERVOIR)
        esn = metric(summary_rows, task, ESN)
        reset = metric(summary_rows, task, RESET)
        shuffled = metric(summary_rows, task, SHUFFLED)
        shuffled_target = metric(summary_rows, task, SHUFFLED_TARGET)
        no_update = metric(summary_rows, task, NO_UPDATE)
        beats_v22 = v23 < v22
        beats_simple = v23 < min(lag, reservoir)
        sham_separated = min(reset, shuffled, shuffled_target, no_update) > v23
        if best_model == V23:
            v23_best_tasks.append(task)
        if beats_v22:
            v23_beats_v22_tasks.append(task)
        if beats_simple:
            v23_beats_simple_online_tasks.append(task)
        if sham_separated:
            v23_sham_separated_tasks.append(task)
        if best_model == ESN and esn < v23:
            esn_dominated_tasks.append(task)
        task_profiles.append(
            {
                "task": task,
                "best_model": best_model,
                "v2_3_rank": next((idx + 1 for idx, row in enumerate(ranked) if row["model"] == V23), None),
                "v2_3_mse": v23,
                "v2_2_mse": v22,
                "lag_mse": lag,
                "reservoir_mse": reservoir,
                "esn_mse": esn,
                "v2_2_over_v2_3_margin": ratio(v22, v23),
                "lag_over_v2_3_margin": ratio(lag, v23),
                "reservoir_over_v2_3_margin": ratio(reservoir, v23),
                "esn_over_v2_3_margin": ratio(esn, v23),
                "sham_min_over_v2_3_margin": ratio(min(reset, shuffled, shuffled_target, no_update), v23),
                "beats_v2_2": beats_v22,
                "beats_simple_online_controls": beats_simple,
                "sham_separated": sham_separated,
            }
        )
    aggregate_v23 = aggregate_metric(aggregate_summary, V23)
    aggregate_v22 = aggregate_metric(aggregate_summary, V22)
    aggregate_lag = aggregate_metric(aggregate_summary, LAG)
    aggregate_reservoir = aggregate_metric(aggregate_summary, RESERVOIR)
    aggregate_esn = aggregate_metric(aggregate_summary, ESN)
    aggregate_rank = next((row.get("rank_by_geomean_mse") for row in aggregate_summary if row.get("model") == V23), None)
    public_like_support = (
        len(v23_beats_v22_tasks) >= max(1, math.ceil(0.6 * len(tasks)))
        and len(v23_beats_simple_online_tasks) >= 1
        and len(v23_sham_separated_tasks) >= 1
    )
    if public_like_support and aggregate_v23 < aggregate_v22 and aggregate_v23 < min(aggregate_lag, aggregate_reservoir):
        outcome = "v2_3_has_targeted_usefulness_signal_but_needs_public_adapter_validation"
        recommendation = (
            "Proceed to Tier 7.1 real-ish/public adapter contract for the winning regimes; "
            "do not freeze a new baseline and do not move to native hardware yet."
        )
    elif len(v23_beats_v22_tasks) >= 1:
        outcome = "v2_3_partial_regime_signal_next_needs_failure_specific_mechanism_or_7_1_probe"
        recommendation = (
            "Use the per-task failures to choose one next general mechanism or a narrow Tier 7.1 adapter; "
            "keep v2.3 as the frozen baseline."
        )
    else:
        outcome = "v2_3_targeted_diagnostics_do_not_show_usefulness_signal"
        recommendation = (
            "Do not move to hardware or real-ish adapters as a usefulness claim. Select the next planned "
            "general mechanism from the measured failure pattern, then rerun the public scoreboard."
        )
    return {
        "outcome": outcome,
        "recommendation": recommendation,
        "v2_3_best_task_count": len(v23_best_tasks),
        "v2_3_best_tasks": v23_best_tasks,
        "v2_3_beats_v2_2_task_count": len(v23_beats_v22_tasks),
        "v2_3_beats_v2_2_tasks": v23_beats_v22_tasks,
        "v2_3_beats_simple_online_task_count": len(v23_beats_simple_online_tasks),
        "v2_3_beats_simple_online_tasks": v23_beats_simple_online_tasks,
        "v2_3_sham_separated_task_count": len(v23_sham_separated_tasks),
        "v2_3_sham_separated_tasks": v23_sham_separated_tasks,
        "esn_dominated_task_count": len(esn_dominated_tasks),
        "esn_dominated_tasks": esn_dominated_tasks,
        "aggregate_v2_3_geomean_mse": aggregate_v23,
        "aggregate_v2_2_geomean_mse": aggregate_v22,
        "aggregate_lag_geomean_mse": aggregate_lag,
        "aggregate_reservoir_geomean_mse": aggregate_reservoir,
        "aggregate_esn_geomean_mse": aggregate_esn,
        "aggregate_v2_3_rank": aggregate_rank,
        "aggregate_v2_2_over_v2_3_margin": ratio(aggregate_v22, aggregate_v23),
        "aggregate_lag_over_v2_3_margin": ratio(aggregate_lag, aggregate_v23),
        "aggregate_reservoir_over_v2_3_margin": ratio(aggregate_reservoir, aggregate_v23),
        "aggregate_esn_over_v2_3_margin": ratio(aggregate_esn, aggregate_v23),
        "task_profiles": task_profiles,
        "baseline_freeze_authorized": False,
        "hardware_transfer_authorized": False,
    }


def write_report(output_dir: Path, payload: dict[str, Any]) -> None:
    c = payload["classification"]
    lines = [
        "# Tier 6.2a Targeted Hard-Task Validation Over v2.3",
        "",
        f"- Generated: `{payload['generated_at_utc']}`",
        f"- Runner revision: `{payload['runner_revision']}`",
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
        f"- v2.3 best task count: `{c['v2_3_best_task_count']}`",
        f"- v2.3 beats v2.2 task count: `{c['v2_3_beats_v2_2_task_count']}`",
        f"- v2.3 beats simple online controls task count: `{c['v2_3_beats_simple_online_task_count']}`",
        f"- v2.3 sham-separated task count: `{c['v2_3_sham_separated_task_count']}`",
        f"- ESN-dominated task count: `{c['esn_dominated_task_count']}`",
        f"- Aggregate v2.3 geomean MSE: `{c['aggregate_v2_3_geomean_mse']}`",
        f"- Aggregate v2.2 geomean MSE: `{c['aggregate_v2_2_geomean_mse']}`",
        f"- Aggregate ESN geomean MSE: `{c['aggregate_esn_geomean_mse']}`",
        f"- Recommendation: {c['recommendation']}",
        "",
        "## Per-Task Profile",
        "",
        "| Task | Best model | v2.3 rank | v2.3 MSE | v2.2/v2.3 | lag/v2.3 | reservoir/v2.3 | ESN/v2.3 | sham-min/v2.3 |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in c["task_profiles"]:
        lines.append(
            "| "
            f"{row['task']} | {row['best_model']} | {row['v2_3_rank']} | {row['v2_3_mse']} | "
            f"{row['v2_2_over_v2_3_margin']} | {row['lag_over_v2_3_margin']} | "
            f"{row['reservoir_over_v2_3_margin']} | {row['esn_over_v2_3_margin']} | "
            f"{row['sham_min_over_v2_3_margin']} |"
        )
    lines.extend(
        [
            "",
            "## Aggregate Summary",
            "",
            "| Model | Rank | Geomean MSE mean | Geomean NMSE mean | Worst seed geomean MSE |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in payload["aggregate_summary"]:
        lines.append(
            f"| {row['model']} | {row.get('rank_by_geomean_mse')} | {row['geomean_mse_mean']} | "
            f"{row['geomean_nmse_mean']} | {row['geomean_mse_worst']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation Rule",
            "",
            "- This tier cannot make a paper usefulness claim by itself.",
            "- It cannot freeze a new baseline and cannot authorize hardware transfer.",
            "- If v2.3 shows a regime-specific signal, validate that regime in Tier 7.1.",
            "- If v2.3 loses broadly, select the next planned general mechanism from the measured failure class.",
            "",
        ]
    )
    (output_dir / "tier6_2a_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=TIER)
    parser.add_argument("--tasks", default=DEFAULT_TASKS)
    parser.add_argument("--seeds", default="42,43,44")
    parser.add_argument("--seed-count", type=int, default=None)
    parser.add_argument("--base-seed", type=int, default=42)
    parser.add_argument("--length", type=int, default=2400)
    parser.add_argument("--horizon", type=int, default=8)
    parser.add_argument("--history", type=int, default=16)
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
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--timeseries-max-length", type=int, default=720)
    return parser


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if args.smoke:
        args.tasks = "hidden_context_reentry"
        args.seeds = "42"
        args.length = min(int(args.length), 480)
    tasks = parse_csv(args.tasks)
    seeds = parse_seeds(args)
    started = time.perf_counter()
    all_rows: list[dict[str, Any]] = []
    all_timeseries: list[dict[str, Any]] = []
    task_diagnostics: list[dict[str, Any]] = []
    invalid_tasks: list[dict[str, Any]] = []
    capture_timeseries = int(args.length) <= int(args.timeseries_max_length)
    for seed in seeds:
        for task_name in tasks:
            task = build_task(task_name, int(args.length), seed, int(args.horizon))
            descriptor = {
                "task": task.name,
                "display_name": task.display_name,
                "seed": int(seed),
                "length": int(len(task.target)),
                "train_end": int(task.train_end),
                "horizon": int(task.horizon),
                "metadata": task.metadata,
                "observed_finite": bool(np.isfinite(task.observed).all()),
                "target_finite": bool(np.isfinite(task.target).all()),
            }
            write_json(output_dir / f"{task.name}_seed{seed}_task.json", descriptor)
            if not (descriptor["observed_finite"] and descriptor["target_finite"]):
                invalid_tasks.append(descriptor)
                continue
            rows, timeseries, diagnostics = run_task_models(task, seed=seed, args=args, capture_timeseries=capture_timeseries)
            all_rows.extend(rows)
            all_timeseries.extend(timeseries)
            task_diagnostics.append(diagnostics)
    models = sorted({str(row["model"]) for row in all_rows})
    summary_rows, aggregate_rows, aggregate_summary = summarize(all_rows, tasks, models, seeds)
    classification = classify(summary_rows, aggregate_summary, tasks)
    expected_run_count = len(tasks) * len(seeds) * len(REQUIRED_MODELS)
    pass_run_count = sum(1 for row in all_rows if row.get("status") == "pass")
    criteria = [
        criterion("runner revision current", RUNNER_REVISION, "expected current source", RUNNER_REVISION.endswith("_0001")),
        criterion("contract linked", "docs/TIER6_2_USEFULNESS_BATTERY_CONTRACT.md", "present", (ROOT / "docs/TIER6_2_USEFULNESS_BATTERY_CONTRACT.md").exists()),
        criterion("tasks are predeclared 6.2a diagnostics", tasks, "subset of task builders", all(task in TASK_BUILDERS for task in tasks)),
        criterion("all generated streams finite", len(invalid_tasks), "0 invalid streams", len(invalid_tasks) == 0),
        criterion("all required model/task/seed runs completed", f"{pass_run_count}/{expected_run_count}", "all pass", pass_run_count == expected_run_count),
        criterion("v2.3 frozen baseline present", V23 in models, "== true", V23 in models),
        criterion("v2.2 reference present", V22 in models, "== true", V22 in models),
        criterion("fair baselines present", [LAG, RESERVOIR, ESN], "all present", all(model in models for model in [LAG, RESERVOIR, ESN])),
        criterion("v2.3 shams and ablations present", [RESET, SHUFFLED, SHUFFLED_TARGET, NO_UPDATE], "all present", all(model in models for model in [RESET, SHUFFLED, SHUFFLED_TARGET, NO_UPDATE])),
        criterion("classification produced", classification["outcome"], "non-empty", bool(classification["outcome"])),
        criterion("no new baseline freeze authorized", classification["baseline_freeze_authorized"], "== false", classification["baseline_freeze_authorized"] is False),
        criterion("no hardware transfer authorized", classification["hardware_transfer_authorized"], "== false", classification["hardware_transfer_authorized"] is False),
    ]
    criteria_passed = sum(1 for item in criteria if item["passed"])
    payload = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "status": "pass" if criteria_passed == len(criteria) else "fail",
        "criteria": criteria,
        "criteria_passed": criteria_passed,
        "criteria_total": len(criteria),
        "failed_criteria": [item for item in criteria if not item["passed"]],
        "output_dir": str(output_dir),
        "tasks": tasks,
        "seeds": seeds,
        "length": int(args.length),
        "horizon": int(args.horizon),
        "classification": classification,
        "summary_rows": summary_rows,
        "aggregate_rows": aggregate_rows,
        "aggregate_summary": aggregate_summary,
        "task_diagnostics": task_diagnostics,
        "invalid_tasks": invalid_tasks,
        "runtime_seconds": time.perf_counter() - started,
        "claim_boundary": (
            "Tier 6.2a is a software-only targeted diagnostic over frozen v2.3. It tests harder controlled regimes "
            "to select the next mechanism or real-ish adapter direction. It is not public usefulness proof, not a "
            "baseline freeze, not hardware/native transfer, not topology-specific recurrence, and not AGI/ASI evidence."
        ),
        "fairness_contract": {
            "baseline_under_test": "CRA_EVIDENCE_BASELINE_v2.3",
            "reference_baseline": "CRA_EVIDENCE_BASELINE_v2.2",
            "prediction_policy": "online normalized LMS predictions are emitted before update for v2.3/v2.2/controls; ESN uses train-prefix ridge readout",
            "normalization_policy": "task streams are z-scored from train prefix only",
            "seed_policy": seeds,
            "custom_task_policy": "diagnostic-only; cannot replace public benchmarks or justify paper usefulness alone",
            "hardware_policy": "blocked until software usefulness or mechanism evidence earns a separate transfer contract",
            "excluded_baselines": {
                "GRU/LSTM": "deferred to Tier 7.1 public/real-ish adapter suite or explicit public benchmark rerun; this tier is a compact diagnostic gate",
                "task-specific RL": "deferred until Tier 7.4 policy/action selection tasks",
            },
        },
    }
    write_json(output_dir / "tier6_2a_results.json", payload)
    write_json(output_dir / "tier6_2a_fairness_contract.json", payload["fairness_contract"])
    write_csv_rows(output_dir / "tier6_2a_summary.csv", summary_rows)
    write_csv_rows(output_dir / "tier6_2a_aggregate.csv", aggregate_rows)
    write_csv_rows(output_dir / "tier6_2a_aggregate_summary.csv", aggregate_summary)
    write_csv_rows(output_dir / "tier6_2a_task_profiles.csv", classification["task_profiles"])
    if capture_timeseries:
        write_csv_rows(output_dir / "tier6_2a_timeseries.csv", all_timeseries)
    write_report(output_dir, payload)
    manifest = {
        "tier": TIER,
        "status": payload["status"],
        "generated_at_utc": payload["generated_at_utc"],
        "output_dir": str(output_dir),
        "results_json": str(output_dir / "tier6_2a_results.json"),
        "report_md": str(output_dir / "tier6_2a_report.md"),
        "summary_csv": str(output_dir / "tier6_2a_summary.csv"),
        "aggregate_summary_csv": str(output_dir / "tier6_2a_aggregate_summary.csv"),
    }
    write_json(output_dir / "tier6_2a_latest_manifest.json", manifest)
    write_json(CONTROLLED / "tier6_2a_latest_manifest.json", manifest)
    return payload


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    payload = run(args)
    print(
        json.dumps(
            json_safe(
                {
                    "status": payload["status"],
                    "criteria": f"{payload['criteria_passed']}/{payload['criteria_total']}",
                    "classification": payload["classification"]["outcome"],
                    "recommendation": payload["classification"]["recommendation"],
                }
            ),
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
