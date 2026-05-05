#!/usr/bin/env python3
"""Tier 5.19b - Temporal Substrate Benchmark / Sham / Regression Gate.

This tier follows the 5.19a local reference. It sharpens the unresolved question:
did the candidate need bounded nonlinear recurrence, or did fading memory alone
explain the useful part?

The gate remains software-only and does not freeze a baseline. If it recommends
promotion, a separate compact regression/freeze step is still required.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
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

from tier5_19a_temporal_substrate_reference import (  # noqa: E402
    STANDARD_TASKS,
    FeatureBundle,
    append_timeseries,
    build_task as build_5_19a_task,
    criterion,
    freeze_temporal_columns,
    json_safe,
    parse_timescales,
    random_reservoir_features,
    run_online_model,
    run_train_prefix_esn,
    summarize,
    utc_now,
    write_csv,
    write_json,
)
from tier7_0_standard_dynamical_benchmarks import (  # noqa: E402
    SequenceTask,
    chronological_split,
    parse_csv,
    parse_seeds,
    zscore_from_train,
)
from tier7_0b_continuous_regression_failure_analysis import (  # noqa: E402
    collect_cra_trace,
    lag_matrix,
)
from tier7_0c_continuous_readout_repair import (  # noqa: E402
    shuffled_rows,
    shuffled_target,
)


TIER = "Tier 5.19b - Temporal Substrate Benchmark / Sham / Regression Gate"
RUNNER_REVISION = "tier5_19b_temporal_substrate_gate_20260505_0002"
DEFAULT_OUTPUT_DIR = OUTPUT_ROOT / "tier5_19b_20260505_temporal_substrate_gate"
DEFAULT_TASKS = "mackey_glass,lorenz,narma10,heldout_long_memory,recurrence_pressure"


def recurrence_pressure_task(length: int, seed: int, *, horizon: int) -> SequenceTask:
    """Held-out diagnostic where nonlinear recurrent state should matter."""
    rng = np.random.default_rng(seed + 51902)
    warmup = 300
    total = length + horizon + warmup + 8
    drive = rng.choice([-1.0, 1.0], size=total) * rng.uniform(0.25, 1.0, size=total)
    drive = np.tanh(0.65 * drive + 0.35 * np.roll(drive, 3))
    a = np.zeros(total, dtype=float)
    b = np.zeros(total, dtype=float)
    c = np.zeros(total, dtype=float)
    for t in range(1, total):
        a[t] = np.tanh(0.84 * a[t - 1] - 0.52 * b[t - 1] + 0.38 * drive[t])
        b[t] = np.tanh(0.43 * a[t - 1] + 0.88 * b[t - 1] + 0.16 * drive[t - 1])
        c[t] = np.tanh(0.74 * c[t - 1] + 0.55 * a[t] * b[t])
    observed_raw = drive[warmup : warmup + length]
    target_raw = (0.6 * c + 0.4 * a)[warmup + horizon : warmup + horizon + length]
    train_end = chronological_split(length, 0.65)
    observed, obs_mu, obs_sd = zscore_from_train(observed_raw, train_end)
    target, tgt_mu, tgt_sd = zscore_from_train(target_raw, train_end)
    return SequenceTask(
        name="recurrence_pressure",
        display_name="Held-out nonlinear recurrence-pressure diagnostic",
        observed=observed,
        target=target,
        train_end=train_end,
        horizon=horizon,
        metadata={
            "obs_mu": obs_mu,
            "obs_sd": obs_sd,
            "target_mu": tgt_mu,
            "target_sd": tgt_sd,
            "hidden_dynamics": "two coupled tanh state variables plus nonlinear product accumulator",
            "purpose": "separate bounded recurrence from fading-memory-only traces",
        },
    )


def build_task(name: str, length: int, seed: int, horizon: int) -> SequenceTask:
    if name == "recurrence_pressure":
        return recurrence_pressure_task(length, seed, horizon=horizon)
    return build_5_19a_task(name, length, seed, horizon)


def temporal_features_variant(
    observed: np.ndarray,
    *,
    seed: int,
    train_end: int,
    timescales: list[float],
    hidden_units: int,
    recurrent_scale: float,
    input_scale: float,
    hidden_decay: float,
    mode: str,
    reset_interval: int = 0,
    recurrent_seed_offset: int = 0,
) -> FeatureBundle:
    values = np.asarray(observed, dtype=float)
    traces = np.zeros(len(timescales), dtype=float)
    hidden_size = 0 if mode == "fading_only" else max(1, int(hidden_units))
    hidden = np.zeros(hidden_size, dtype=float)
    rng = np.random.default_rng(seed + 51919)
    sham_rng = np.random.default_rng(seed + 51919 + int(recurrent_seed_offset))

    def driver_for(x: float, previous_traces: np.ndarray) -> np.ndarray:
        if mode == "recurrent_only":
            return np.asarray([x, x * x, math.sin(x), math.cos(x)], dtype=float)
        trace_deltas = np.diff(traces) if traces.size > 1 else np.asarray([], dtype=float)
        novelty = x - float(previous_traces[-1] if previous_traces.size else 0.0)
        return np.concatenate([[x], traces, trace_deltas, [novelty]])

    sample_driver = driver_for(0.0, traces.copy())
    w_in = rng.normal(0.0, float(input_scale), size=(hidden_size, len(sample_driver))) if hidden_size else np.zeros((0, len(sample_driver)))
    raw_rec = rng.normal(0.0, 1.0, size=(hidden_size, hidden_size)) if hidden_size else np.zeros((0, 0))
    if hidden_size:
        eig = max(1e-9, float(max(abs(np.linalg.eigvals(raw_rec)))))
        w_rec = raw_rec * (float(recurrent_scale) / eig)
        if mode == "permuted_recurrence":
            # Keep input weights identical to the full candidate and perturb only
            # recurrent wiring. Otherwise this sham would conflate recurrence
            # specificity with a different input projection.
            perm = np.arange(hidden_size)
            sham_rng.shuffle(perm)
            signs = sham_rng.choice([-1.0, 1.0], size=hidden_size)
            w_rec = w_rec[:, perm] * signs.reshape(1, -1)
    else:
        w_rec = raw_rec

    rows: list[np.ndarray] = []
    for step, value in enumerate(values):
        x = float(value)
        previous_traces = traces.copy()
        for idx, tau in enumerate(timescales):
            alpha = 1.0 - math.exp(-1.0 / max(1e-6, float(tau)))
            traces[idx] = traces[idx] + alpha * (x - traces[idx])
        driver = driver_for(x, previous_traces)
        if hidden_size:
            if reset_interval > 0 and step > 0 and step % int(reset_interval) == 0:
                hidden[:] = 0.0
            hidden = np.tanh(float(hidden_decay) * hidden + w_rec @ hidden + w_in @ driver)
        trace_deltas = np.diff(traces) if traces.size > 1 else np.asarray([], dtype=float)
        novelty = x - float(previous_traces[-1] if previous_traces.size else 0.0)
        if mode == "recurrent_only":
            row = np.concatenate([[1.0, x], hidden])
            names = ["bias", "observed_current"] + [f"hidden_{idx}" for idx in range(hidden_size)]
        elif mode == "fading_only":
            row = np.concatenate([[1.0, x], traces, trace_deltas, [novelty]])
            names = (
                ["bias", "observed_current"]
                + [f"ema_tau_{tau:g}" for tau in timescales]
                + [f"ema_delta_{i}_{i+1}" for i in range(max(0, len(timescales) - 1))]
                + ["novelty_vs_slowest_ema"]
            )
        else:
            row = np.concatenate([[1.0, x], traces, trace_deltas, [novelty], hidden])
            names = (
                ["bias", "observed_current"]
                + [f"ema_tau_{tau:g}" for tau in timescales]
                + [f"ema_delta_{i}_{i+1}" for i in range(max(0, len(timescales) - 1))]
                + ["novelty_vs_slowest_ema"]
                + [f"hidden_{idx}" for idx in range(hidden_size)]
            )
        rows.append(row)
    features = np.vstack(rows)
    return FeatureBundle(
        features=features,
        temporal_start=2,
        names=names,
        diagnostics={
            "state_location": "readout/interface temporal substrate reference",
            "mode": mode,
            "timescales": timescales,
            "hidden_units": int(hidden_size),
            "recurrent_scale": float(recurrent_scale),
            "input_scale": float(input_scale),
            "hidden_decay": float(hidden_decay),
            "reset_interval": int(reset_interval),
            "recurrent_permutation_seed_offset": int(recurrent_seed_offset),
            "permutation_scope": "recurrent weights only" if mode == "permuted_recurrence" else "none",
            "feature_count": int(features.shape[1]),
            "train_prefix_state_norm_mean": float(np.mean(np.linalg.norm(features[:train_end, 2:], axis=1))),
            "test_state_norm_mean": float(np.mean(np.linalg.norm(features[train_end:, 2:], axis=1))),
        },
    )


def run_task(task: SequenceTask, *, seed: int, args: argparse.Namespace) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    timeseries: list[dict[str, Any]] = []
    trace = collect_cra_trace(task, seed=seed, args=args)
    lag = lag_matrix(task.observed, args.history)
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
    bundles = {
        "full": temporal_features_variant(task.observed, mode="full", **base_kwargs),
        "fading_only": temporal_features_variant(task.observed, mode="fading_only", **base_kwargs),
        "recurrent_only": temporal_features_variant(task.observed, mode="recurrent_only", **base_kwargs),
        "state_reset": temporal_features_variant(
            task.observed,
            mode="full",
            reset_interval=args.state_reset_interval,
            **base_kwargs,
        ),
        "permuted_recurrence": temporal_features_variant(
            task.observed,
            mode="permuted_recurrence",
            recurrent_seed_offset=71,
            **base_kwargs,
        ),
    }
    reservoir = random_reservoir_features(
        task.observed,
        seed=seed,
        units=args.reservoir_units,
        spectral_radius=args.reservoir_spectral_radius,
        input_scale=args.reservoir_input_scale,
    )
    wrong_target = shuffled_target(task.target, task.train_end, seed)
    specs: list[tuple[str, np.ndarray, np.ndarray | None, bool, dict[str, Any]]] = [
        (
            "raw_cra_v2_1_online",
            np.column_stack([np.ones(len(task.target)), trace.cra_prediction]),
            None,
            False,
            {"role": "raw CRA v2.1 prediction", "backend": trace.diagnostics.get("backend")},
        ),
        ("lag_only_online_lms_control", lag, None, True, {"role": "same causal lag budget", "history": int(args.history)}),
        ("fixed_random_reservoir_online_control", reservoir.features, None, True, reservoir.diagnostics),
        ("temporal_full_candidate", bundles["full"].features, None, True, bundles["full"].diagnostics),
        ("temporal_plus_lag_reference", np.column_stack([bundles["full"].features, lag[:, 1:]]), None, True, {**bundles["full"].diagnostics, "includes_lag_budget": int(args.history)}),
        ("fading_memory_only_ablation", bundles["fading_only"].features, None, True, bundles["fading_only"].diagnostics),
        ("recurrent_hidden_only_ablation", bundles["recurrent_only"].features, None, True, bundles["recurrent_only"].diagnostics),
        ("state_reset_ablation", bundles["state_reset"].features, None, True, bundles["state_reset"].diagnostics),
        ("permuted_recurrence_sham", bundles["permuted_recurrence"].features, None, True, bundles["permuted_recurrence"].diagnostics),
        ("frozen_temporal_state_ablation", freeze_temporal_columns(bundles["full"].features, task.train_end, bundles["full"].temporal_start), None, True, {**bundles["full"].diagnostics, "ablation": "temporal columns frozen after train prefix"}),
        ("shuffled_temporal_state_sham", shuffled_rows(bundles["full"].features, task.train_end, seed), None, True, {**bundles["full"].diagnostics, "sham": "feature rows shuffled within train/test splits"}),
        ("temporal_shuffled_target_control", bundles["full"].features, wrong_target, True, {**bundles["full"].diagnostics, "control": "online readout updates against shuffled targets"}),
        ("temporal_no_plasticity_ablation", bundles["full"].features, None, False, {**bundles["full"].diagnostics, "ablation": "readout updates disabled"}),
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
        "full_feature_count": int(bundles["full"].features.shape[1]),
        "fading_only_feature_count": int(bundles["fading_only"].features.shape[1]),
        "recurrent_only_feature_count": int(bundles["recurrent_only"].features.shape[1]),
        "lag_feature_count": int(lag.shape[1]),
    }
    return rows, timeseries, diagnostics


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


def ratio(control: float, candidate: float) -> float | None:
    if not math.isfinite(control) or not math.isfinite(candidate) or candidate <= 0.0:
        return None
    return control / candidate


def classify(summary_rows: list[dict[str, Any]], aggregate_summary: list[dict[str, Any]]) -> dict[str, Any]:
    cand = "temporal_full_candidate"
    lag = "lag_only_online_lms_control"
    fading = "fading_memory_only_ablation"
    recurrent_only = "recurrent_hidden_only_ablation"
    reset = "state_reset_ablation"
    permuted = "permuted_recurrence_sham"
    shuffled = "shuffled_temporal_state_sham"
    frozen = "frozen_temporal_state_ablation"
    no_plasticity = "temporal_no_plasticity_ablation"
    recurrence_candidate = metric(summary_rows, "recurrence_pressure", cand)
    recurrence_lag = metric(summary_rows, "recurrence_pressure", lag)
    recurrence_fading = metric(summary_rows, "recurrence_pressure", fading)
    recurrence_reset = metric(summary_rows, "recurrence_pressure", reset)
    recurrence_permuted = metric(summary_rows, "recurrence_pressure", permuted)
    recurrence_recurrent_only = metric(summary_rows, "recurrence_pressure", recurrent_only)
    recurrence_shuffled = metric(summary_rows, "recurrence_pressure", shuffled)
    recurrence_frozen = metric(summary_rows, "recurrence_pressure", frozen)
    recurrence_no_plasticity = metric(summary_rows, "recurrence_pressure", no_plasticity)
    heldout_candidate = metric(summary_rows, "heldout_long_memory", cand)
    heldout_lag = metric(summary_rows, "heldout_long_memory", lag)
    standard_candidate = aggregate_metric(aggregate_summary, "standard_three_geomean", cand)
    standard_lag = aggregate_metric(aggregate_summary, "standard_three_geomean", lag)
    recurrence_margins = {
        "vs_lag": ratio(recurrence_lag, recurrence_candidate),
        "vs_fading_only": ratio(recurrence_fading, recurrence_candidate),
        "vs_state_reset": ratio(recurrence_reset, recurrence_candidate),
        "vs_permuted_recurrence": ratio(recurrence_permuted, recurrence_candidate),
        "vs_recurrent_only": ratio(recurrence_recurrent_only, recurrence_candidate),
        "vs_shuffled_state": ratio(recurrence_shuffled, recurrence_candidate),
        "vs_frozen_state": ratio(recurrence_frozen, recurrence_candidate),
        "vs_no_plasticity": ratio(recurrence_no_plasticity, recurrence_candidate),
    }
    heldout_vs_lag = ratio(heldout_lag, heldout_candidate)
    standard_vs_lag = ratio(standard_lag, standard_candidate)
    recurrence_specific = all(
        value is not None and value >= threshold
        for value, threshold in [
            (recurrence_margins["vs_lag"], 1.10),
            (recurrence_margins["vs_fading_only"], 1.05),
            (recurrence_margins["vs_state_reset"], 1.05),
            (recurrence_margins["vs_shuffled_state"], 1.10),
            (recurrence_margins["vs_no_plasticity"], 1.10),
        ]
    )
    fading_promising = heldout_vs_lag is not None and heldout_vs_lag >= 1.10
    if recurrence_specific and fading_promising:
        outcome = "temporal_substrate_ready_for_compact_regression"
        recommendation = "Run Tier 5.19c compact regression/freeze decision before any hardware work."
    elif fading_promising:
        outcome = "fading_memory_supported_recurrence_unproven"
        recommendation = "Consider a narrowed fading-memory candidate or repair recurrence; do not promote or claim recurrence-specific value from this tier."
    else:
        outcome = "temporal_substrate_not_promotable"
        recommendation = "Park or repair; keep Tier 7 limitation explicit."
    return {
        "outcome": outcome,
        "recommendation": recommendation,
        "recurrence_candidate_mse": recurrence_candidate,
        "recurrence_lag_mse": recurrence_lag,
        "recurrence_fading_only_mse": recurrence_fading,
        "recurrence_state_reset_mse": recurrence_reset,
        "recurrence_permuted_mse": recurrence_permuted,
        "recurrence_recurrent_only_mse": recurrence_recurrent_only,
        "recurrence_shuffled_mse": recurrence_shuffled,
        "recurrence_frozen_mse": recurrence_frozen,
        "recurrence_no_plasticity_mse": recurrence_no_plasticity,
        "recurrence_margins": recurrence_margins,
        "heldout_candidate_mse": heldout_candidate,
        "heldout_lag_mse": heldout_lag,
        "heldout_vs_lag_margin": heldout_vs_lag,
        "standard_candidate_geomean_mse": standard_candidate,
        "standard_lag_geomean_mse": standard_lag,
        "standard_vs_lag_margin": standard_vs_lag,
        "recurrence_specific_pass": bool(recurrence_specific),
        "fading_memory_pass": bool(fading_promising),
    }


def write_report(output_dir: Path, payload: dict[str, Any]) -> None:
    c = payload["classification"]
    lines = [
        "# Tier 5.19b Temporal Substrate Benchmark / Sham / Regression Gate",
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
        f"- Recurrence-pressure candidate MSE: `{c['recurrence_candidate_mse']}`",
        f"- Recurrence-pressure lag-only MSE: `{c['recurrence_lag_mse']}`",
        f"- Recurrence margin vs fading-only: `{c['recurrence_margins']['vs_fading_only']}`",
        f"- Recurrence margin vs reset: `{c['recurrence_margins']['vs_state_reset']}`",
        f"- Recurrence margin vs shuffled state: `{c['recurrence_margins']['vs_shuffled_state']}`",
        f"- Held-out long-memory margin vs lag: `{c['heldout_vs_lag_margin']}`",
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
            "- This tier may recommend promotion, narrowing, or repair; it does not freeze a baseline by itself.",
            "- If recurrence-specific controls do not separate, do not claim bounded nonlinear recurrence.",
            "- No hardware migration is allowed from this tier alone.",
            "",
        ]
    )
    (output_dir / "tier5_19b_report.md").write_text("\n".join(lines), encoding="utf-8")


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
        criterion("runner revision current", RUNNER_REVISION, "expected current source", RUNNER_REVISION.endswith("_0002")),
        criterion("Tier 5.19a source present", "experiments/tier5_19a_temporal_substrate_reference.py", "present", (ROOT / "experiments/tier5_19a_temporal_substrate_reference.py").exists()),
        criterion("all tasks known", tasks, "standard plus heldout_long_memory plus recurrence_pressure", all(t in STANDARD_TASKS or t in {"heldout_long_memory", "recurrence_pressure"} for t in tasks)),
        criterion("recurrence-pressure diagnostic included", "recurrence_pressure" in tasks, "== true", "recurrence_pressure" in tasks),
        criterion("all runs completed", f"{sum(r['status'] == 'pass' for r in all_rows)}/{len(all_rows)}", "all pass", all(r["status"] == "pass" for r in all_rows)),
        criterion("lag-only control present", "lag_only_online_lms_control" in models, "== true", "lag_only_online_lms_control" in models),
        criterion("fading-only ablation present", "fading_memory_only_ablation" in models, "== true", "fading_memory_only_ablation" in models),
        criterion("recurrent-only ablation present", "recurrent_hidden_only_ablation" in models, "== true", "recurrent_hidden_only_ablation" in models),
        criterion("state-reset and recurrence sham present", "state_reset_ablation/permuted_recurrence_sham", "all present", all(m in models for m in ["state_reset_ablation", "permuted_recurrence_sham"])),
        criterion("destructive shams present", "frozen/shuffled/no plasticity/shuffled target", "all present", all(m in models for m in ["frozen_temporal_state_ablation", "shuffled_temporal_state_sham", "temporal_no_plasticity_ablation", "temporal_shuffled_target_control"])),
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
            "source": "Tier 5.19a local temporal substrate reference",
            "split": "chronological",
            "normalization": "train-prefix z-score for tasks; train-prefix feature normalization for online readouts",
            "prediction": "online readouts predict before update",
            "hardware_policy": "software-only; hardware blocked until promotion and compact regression",
            "recurrence_specific_controls": [
                "fading-memory-only",
                "recurrent-hidden-only",
                "state-reset",
                "permuted-recurrence",
                "shuffled-state",
                "frozen-state",
            ],
            "nonclaims": [
                "not hardware evidence",
                "not a software baseline freeze",
                "not native/on-chip temporal dynamics",
                "not recurrence-specific proof unless classification says so",
            ],
        },
        "claim_boundary": (
            "Tier 5.19b is software benchmark/sham gate evidence only. It may "
            "recommend promotion, narrowing, or repair, but does not freeze a "
            "baseline by itself and does not authorize hardware migration."
        ),
    }
    write_json(output_dir / "tier5_19b_results.json", payload)
    write_json(output_dir / "tier5_19b_fairness_contract.json", payload["fairness_contract"])
    write_csv(
        output_dir / "tier5_19b_summary.csv",
        summary_rows,
        ["task", "model", "status", "seed_count", "mse_mean", "mse_median", "mse_std", "mse_worst", "nmse_mean", "tail_mse_mean", "test_corr_mean"],
    )
    write_csv(
        output_dir / "tier5_19b_aggregate.csv",
        aggregate_rows,
        ["task", "model", "seed", "status", "geomean_mse", "geomean_nmse"],
    )
    write_csv(
        output_dir / "tier5_19b_timeseries.csv",
        all_timeseries,
        ["task", "seed", "model", "step", "split", "observed", "target", "prediction", "squared_error"],
    )
    write_report(output_dir, payload)
    write_json(
        OUTPUT_ROOT / "tier5_19b_latest_manifest.json",
        {
            "tier": TIER,
            "runner_revision": RUNNER_REVISION,
            "generated_at_utc": payload["generated_at_utc"],
            "status": payload["status"],
            "manifest": str(output_dir / "tier5_19b_results.json"),
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
    parser.add_argument("--state-reset-interval", type=int, default=24)
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
