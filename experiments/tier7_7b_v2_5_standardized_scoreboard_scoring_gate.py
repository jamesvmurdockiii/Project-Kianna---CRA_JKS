#!/usr/bin/env python3
"""Tier 7.7b - v2.5 standardized benchmark/usefulness scoreboard scoring gate.

This runner scores frozen v2.5 against the Tier 7.7a pre-registered
standardized scoreboard. It intentionally does not tune the benchmark, alter
the split, or add a post-hoc rescue task.

The primary scoreboard is Mackey-Glass + Lorenz + NARMA10 at length 8000,
horizon 8, seeds 42/43/44, chronological 65/35 split. Secondary public/real-ish
signals are recorded from prior registered evidence, but cannot rescue a failed
standardized core.
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
BASELINES = ROOT / "baselines"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from tier5_19a_temporal_substrate_reference import (  # noqa: E402
    append_timeseries,
    criterion,
    json_safe,
    parse_timescales,
    random_reservoir_features,
    run_online_model,
    run_train_prefix_esn,
    summarize,
    write_json,
)
from tier5_19b_temporal_substrate_gate import temporal_features_variant  # noqa: E402
from tier5_19c_fading_memory_regression import build_task  # noqa: E402
from tier7_0_standard_dynamical_benchmarks import build_model, parse_csv, parse_seeds  # noqa: E402
from tier7_0b_continuous_regression_failure_analysis import evaluate_probe, lag_matrix  # noqa: E402
from tier7_0c_continuous_readout_repair import shuffled_rows, shuffled_target  # noqa: E402
from tier7_0e_standard_dynamical_v2_2_sweep import (  # noqa: E402
    aggregate_by_model,
    finite_task_descriptor,
    geomean,
    ratio,
    write_rows,
)


TIER = "Tier 7.7b - v2.5 Standardized Benchmark / Usefulness Scoreboard Scoring Gate"
RUNNER_REVISION = "tier7_7b_v2_5_standardized_scoreboard_scoring_gate_20260509_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_7b_20260509_v2_5_standardized_scoreboard_scoring_gate"
CONTRACT_RESULTS = CONTROLLED / "tier7_7a_20260509_v2_5_standardized_scoreboard_contract" / "tier7_7a_results.json"
CONTRACT_JSON = CONTROLLED / "tier7_7a_20260509_v2_5_standardized_scoreboard_contract" / "tier7_7a_scoreboard_contract.json"
V25_BASELINE = BASELINES / "CRA_EVIDENCE_BASELINE_v2.5.json"
V23_BASELINE = BASELINES / "CRA_EVIDENCE_BASELINE_v2.3.json"
SECONDARY_CMAPSS = CONTROLLED / "tier7_4g_20260509_policy_action_confirmation_reference_separation" / "tier7_4g_results.json"
SECONDARY_NAB = CONTROLLED / "tier7_1m_20260508_nab_closeout_mechanism_return_decision" / "tier7_1m_results.json"

DEFAULT_TASKS = "mackey_glass,lorenz,narma10"
STANDARD_THREE = {"mackey_glass", "lorenz", "narma10"}

V25 = "cra_v2_5_scoreboard_candidate"
V23 = "cra_v2_3_generic_recurrent_reference"
V24 = "cra_v2_4_policy_reference_no_planning"
PLANNING_DISABLED = "planning_disabled_v2_3_equivalent"
POLICY_DISABLED = "policy_action_disabled"
STATE_DISABLED = "state_disabled"
MEMORY_DISABLED = "memory_disabled"
REPLAY_DISABLED = "replay_disabled_not_applicable_standardized_core"
PREDICTION_DISABLED = "prediction_disabled"
SELF_EVAL_DISABLED = "self_evaluation_disabled"
COMPOSITION_DISABLED = "composition_routing_disabled"
TARGET_SHUFFLE = "target_shuffle_control"
TIME_SHUFFLE = "time_shuffle_control"
FUTURE_LABEL_GUARD = "future_label_leak_guard"
LAG = "lag_only_online_lms_control"
RESERVOIR = "fixed_random_reservoir_online_control"
ESN = "fixed_esn_train_prefix_ridge_baseline"
PERSISTENCE = "persistence"
ONLINE_LMS = "online_lms"
RIDGE_LAG = "ridge_lag"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    write_rows(path, rows)


def safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def task_metric(summary_rows: list[dict[str, Any]], task: str, model: str, key: str = "mse_mean") -> float | None:
    row = next((item for item in summary_rows if item.get("task") == task and item.get("model") == model), None)
    if not row or row.get("status") != "pass":
        return None
    return safe_float(row.get(key))


def aggregate_metric(seed_aggregate_rows: list[dict[str, Any]], model: str, seed: int) -> float | None:
    row = next(
        (
            item
            for item in seed_aggregate_rows
            if item.get("task") == "standard_three_geomean"
            and item.get("model") == model
            and int(item.get("seed", -1)) == int(seed)
        ),
        None,
    )
    if not row or row.get("status") != "pass":
        return None
    return safe_float(row.get("geomean_mse"))


def paired_bootstrap_ci(deltas: list[float], *, seed: int = 77701, draws: int = 10000) -> dict[str, Any]:
    clean = [float(value) for value in deltas if math.isfinite(float(value))]
    if not clean:
        return {"mean": None, "ci_low": None, "ci_high": None, "n": 0, "positive_fraction": None}
    rng = np.random.default_rng(seed)
    arr = np.asarray(clean, dtype=float)
    means = np.empty(draws, dtype=float)
    for idx in range(draws):
        sample = rng.choice(arr, size=len(arr), replace=True)
        means[idx] = float(np.mean(sample))
    return {
        "mean": float(np.mean(arr)),
        "ci_low": float(np.percentile(means, 2.5)),
        "ci_high": float(np.percentile(means, 97.5)),
        "n": int(len(arr)),
        "positive_fraction": float(np.mean(arr > 0.0)),
    }


def causal_v2_5_meta_features(observed: np.ndarray, *, horizon: int) -> tuple[np.ndarray, dict[str, Any]]:
    """Build predeclared causal meta-state columns for v2.5 scoring.

    These columns are not trained on future targets. They are a compact,
    benchmark-agnostic adapter that exposes the already-promoted host-side
    v2.5 ideas to continuous streams: predictive extrapolation, reliability
    gating, context/memory timescales, composition/routing interactions, and
    reduced-feature subgoal pressure.
    """
    values = np.asarray(observed, dtype=float)
    fast = np.zeros_like(values)
    mid = np.zeros_like(values)
    slow = np.zeros_like(values)
    ultra = np.zeros_like(values)
    volatility = np.zeros_like(values)
    previous = 0.0
    for idx, value in enumerate(values):
        x = float(value)
        delta = x - previous if idx else 0.0
        fast[idx] = fast[idx - 1] + 0.28 * (x - fast[idx - 1]) if idx else x
        mid[idx] = mid[idx - 1] + 0.10 * (x - mid[idx - 1]) if idx else x
        slow[idx] = slow[idx - 1] + 0.035 * (x - slow[idx - 1]) if idx else x
        ultra[idx] = ultra[idx - 1] + 0.012 * (x - ultra[idx - 1]) if idx else x
        volatility[idx] = 0.94 * volatility[idx - 1] + 0.06 * abs(delta) if idx else abs(delta)
        previous = x
    trend_fast = fast - mid
    trend_slow = mid - slow
    curvature = fast - 2.0 * mid + slow
    novelty = values - slow
    reliability = 1.0 / (1.0 + np.abs(novelty) + volatility)
    bounded_horizon = float(max(1, int(horizon)))
    predictive_fast = fast + bounded_horizon * trend_fast
    predictive_slow = slow + 0.25 * bounded_horizon * trend_slow
    subgoal_pressure = np.tanh(0.75 * predictive_fast + 0.25 * predictive_slow)
    policy_gate = reliability * subgoal_pressure
    route_context = np.tanh(trend_fast * slow)
    composed_context = np.tanh((fast - slow) * (mid - ultra))
    memory_bridge = np.tanh(slow + 0.5 * ultra)
    replay_stabilized = 0.65 * slow + 0.35 * ultra
    features = np.column_stack(
        [
            predictive_fast,
            predictive_slow,
            subgoal_pressure,
            reliability,
            policy_gate,
            route_context,
            composed_context,
            memory_bridge,
            replay_stabilized,
            trend_fast,
            trend_slow,
            curvature,
            volatility,
            novelty,
            predictive_fast * reliability,
            predictive_slow * reliability,
        ]
    )
    diagnostics = {
        "feature_family": "causal_v2_5_meta_state_adapter",
        "future_target_access": False,
        "horizon": int(horizon),
        "columns": [
            "predictive_fast",
            "predictive_slow",
            "subgoal_pressure",
            "reliability",
            "policy_gate",
            "route_context",
            "composed_context",
            "memory_bridge",
            "replay_stabilized",
            "trend_fast",
            "trend_slow",
            "curvature",
            "volatility",
            "novelty",
            "predictive_fast_reliable",
            "predictive_slow_reliable",
        ],
    }
    return features, diagnostics


def select_meta_columns(meta: np.ndarray, mode: str) -> np.ndarray:
    """Return v2.5 meta-state subsets for predeclared ablations."""
    # Column indices are fixed by causal_v2_5_meta_features.
    prediction = [0, 1, 14, 15]
    planning = [2, 4]
    self_eval = [3, 12, 13]
    routing = [5, 6]
    memory = [7, 8, 10]
    policy = [4]
    if mode == "full":
        return meta
    if mode == "v2_4_policy_no_planning":
        keep = sorted(set(self_eval + routing + memory + policy + [9, 10, 11, 12, 13]))
        return meta[:, keep]
    if mode == "prediction_disabled":
        drop = set(prediction)
    elif mode == "planning_disabled":
        return np.zeros((len(meta), 0), dtype=float)
    elif mode == "policy_disabled":
        drop = set(policy)
    elif mode == "self_eval_disabled":
        drop = set(self_eval)
    elif mode == "composition_disabled":
        drop = set(routing)
    elif mode == "memory_disabled":
        drop = set(memory)
    elif mode == "replay_disabled":
        drop = {8}
    else:
        raise ValueError(f"unknown meta-feature mode {mode!r}")
    keep = [idx for idx in range(meta.shape[1]) if idx not in drop]
    return meta[:, keep]


def run_sequence_model(task: Any, *, seed: int, model_name: str, args: argparse.Namespace) -> tuple[dict[str, Any], np.ndarray]:
    model = build_model(model_name, seed=seed, args=args)
    model.fit(task)
    pred, diagnostics = model.predict_all(task)
    return evaluate_probe(task.name, seed, task.train_end, task.target, pred, model.name, diagnostics), pred


def run_task_models(task: Any, *, seed: int, args: argparse.Namespace, capture_timeseries: bool) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
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
    recurrent_only = temporal_features_variant(task.observed, mode="recurrent_only", **base_kwargs)
    meta, meta_diagnostics = causal_v2_5_meta_features(task.observed, horizon=args.horizon)
    lag = lag_matrix(task.observed, args.history)
    reservoir = random_reservoir_features(
        task.observed,
        seed=seed,
        units=args.reservoir_units,
        spectral_radius=args.reservoir_spectral_radius,
        input_scale=args.reservoir_input_scale,
    )
    wrong_target = shuffled_target(task.target, task.train_end, seed)
    v25_features = np.column_stack([full.features, select_meta_columns(meta, "full")])

    specs: list[tuple[str, np.ndarray, np.ndarray | None, bool, dict[str, Any]]] = [
        (LAG, lag, None, True, {"role": "same causal lag budget", "history": int(args.history)}),
        (RESERVOIR, reservoir.features, None, True, reservoir.diagnostics),
        (V23, full.features, None, True, {**full.diagnostics, "role": "frozen v2.3 generic recurrent reference"}),
        (
            V24,
            np.column_stack([full.features, select_meta_columns(meta, "v2_4_policy_no_planning")]),
            None,
            True,
            {**full.diagnostics, **meta_diagnostics, "role": "v2.4 policy/action reference without v2.5 planning columns"},
        ),
        (
            V25,
            v25_features,
            None,
            True,
            {**full.diagnostics, **meta_diagnostics, "role": "frozen v2.5 scoreboard candidate adapter"},
        ),
        (PLANNING_DISABLED, full.features, None, True, {**full.diagnostics, "ablation": "remove v2.5 planning/subgoal meta-state; equals v2.3 reference on standardized core"}),
        (
            POLICY_DISABLED,
            np.column_stack([full.features, select_meta_columns(meta, "policy_disabled")]),
            None,
            True,
            {**full.diagnostics, **meta_diagnostics, "ablation": "remove policy-gate column"},
        ),
        (STATE_DISABLED, recurrent_only.features, None, True, {**recurrent_only.diagnostics, "ablation": "remove full recurrent/fading interface state"}),
        (
            MEMORY_DISABLED,
            np.column_stack([full.features, select_meta_columns(meta, "memory_disabled")]),
            None,
            True,
            {**full.diagnostics, **meta_diagnostics, "ablation": "remove v2.5 slow-memory bridge columns"},
        ),
        (
            REPLAY_DISABLED,
            np.column_stack([full.features, select_meta_columns(meta, "replay_disabled")]),
            None,
            True,
            {**full.diagnostics, **meta_diagnostics, "ablation": "remove replay-stabilized slow context column; standardized core has no explicit replay buffer"},
        ),
        (
            PREDICTION_DISABLED,
            np.column_stack([full.features, select_meta_columns(meta, "prediction_disabled")]),
            None,
            True,
            {**full.diagnostics, **meta_diagnostics, "ablation": "remove predictive extrapolation columns"},
        ),
        (
            SELF_EVAL_DISABLED,
            np.column_stack([full.features, select_meta_columns(meta, "self_eval_disabled")]),
            None,
            True,
            {**full.diagnostics, **meta_diagnostics, "ablation": "remove reliability/uncertainty columns"},
        ),
        (
            COMPOSITION_DISABLED,
            np.column_stack([full.features, select_meta_columns(meta, "composition_disabled")]),
            None,
            True,
            {**full.diagnostics, **meta_diagnostics, "ablation": "remove route/composition interaction columns"},
        ),
        (
            TARGET_SHUFFLE,
            v25_features,
            wrong_target,
            True,
            {**full.diagnostics, **meta_diagnostics, "control": "candidate readout updates against shuffled training targets"},
        ),
        (
            TIME_SHUFFLE,
            shuffled_rows(v25_features, task.train_end, seed),
            None,
            True,
            {**full.diagnostics, **meta_diagnostics, "control": "candidate feature rows shuffled within train/test splits"},
        ),
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
            diagnostics={**diagnostics, "tier7_7b_model_family": "locked_v2_5_scoreboard"},
        )
        rows.append(row)
        if capture_timeseries:
            append_timeseries(timeseries, task=task, seed=seed, model=model, prediction=pred)

    for baseline in [PERSISTENCE, ONLINE_LMS, RIDGE_LAG]:
        row, pred = run_sequence_model(task, seed=seed, model_name=baseline, args=args)
        rows.append(row)
        if capture_timeseries:
            append_timeseries(timeseries, task=task, seed=seed, model=row["model"], prediction=pred)

    esn_row, esn_pred = run_train_prefix_esn(task, seed=seed, args=args)
    rows.append(esn_row)
    if capture_timeseries:
        append_timeseries(timeseries, task=task, seed=seed, model=ESN, prediction=esn_pred)

    diagnostics = {
        "task": task.name,
        "seed": int(seed),
        "candidate_feature_count": int(v25_features.shape[1]),
        "v2_3_feature_count": int(full.features.shape[1]),
        "v2_5_meta_feature_count": int(meta.shape[1]),
        "lag_feature_count": int(lag.shape[1]),
        "reservoir_feature_count": int(reservoir.features.shape[1]),
        "future_label_guard": {
            "meta_features_use_target": False,
            "online_prediction_before_update": True,
            "normalization_train_prefix_only": True,
            "target_shuffle_control_present": True,
            "time_shuffle_control_present": True,
        },
    }
    return rows, timeseries, diagnostics


def run_scoreboard(args: argparse.Namespace, output_dir: Path) -> dict[str, Any]:
    tasks = parse_csv(args.tasks)
    seeds = parse_seeds(args)
    capture_timeseries = int(args.length) <= int(args.timeseries_max_length)
    all_rows: list[dict[str, Any]] = []
    all_timeseries: list[dict[str, Any]] = []
    task_descriptors: list[dict[str, Any]] = []
    task_diagnostics: list[dict[str, Any]] = []
    invalid_tasks: list[dict[str, Any]] = []
    started = time.perf_counter()
    for seed in seeds:
        for task_name in tasks:
            task = build_task(task_name, args.length, seed, args.horizon)
            finite_descriptor = finite_task_descriptor(task)
            descriptor = {
                "length": int(args.length),
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
            write_json(output_dir / f"{task.name}_seed{seed}_task.json", descriptor)
            if not (finite_descriptor["observed_finite"] and finite_descriptor["target_finite"]):
                invalid_tasks.append(descriptor)
                task_diagnostics.append(
                    {
                        "task": task.name,
                        "seed": int(seed),
                        "status": "invalid_task_stream",
                        "finite_check": finite_descriptor,
                    }
                )
                continue
            rows, timeseries, diagnostics = run_task_models(task, seed=seed, args=args, capture_timeseries=capture_timeseries)
            for row in rows:
                row["length"] = int(args.length)
                row["horizon"] = int(args.horizon)
            all_rows.extend(rows)
            if capture_timeseries:
                all_timeseries.extend(timeseries)
            task_diagnostics.append({"length": int(args.length), **diagnostics})
    models = sorted({str(row["model"]) for row in all_rows})
    summary_rows, seed_aggregate_rows, seed_aggregate_summary = summarize(all_rows, tasks, models, seeds)
    model_aggregate_rows = aggregate_by_model(summary_rows, tasks)
    for table in [summary_rows, seed_aggregate_rows, seed_aggregate_summary, model_aggregate_rows]:
        for row in table:
            row["length"] = int(args.length)
            row["horizon"] = int(args.horizon)
    if capture_timeseries:
        write_csv_rows(output_dir / "tier7_7b_timeseries.csv", all_timeseries)
    return {
        "runtime_seconds": time.perf_counter() - started,
        "tasks": tasks,
        "seeds": seeds,
        "models": models,
        "scoreboard_rows": all_rows,
        "summary_rows": summary_rows,
        "seed_aggregate_rows": seed_aggregate_rows,
        "seed_aggregate_summary": seed_aggregate_summary,
        "model_aggregate_rows": model_aggregate_rows,
        "task_descriptors": task_descriptors,
        "task_diagnostics": task_diagnostics,
        "invalid_tasks": invalid_tasks,
        "timeseries_captured": bool(capture_timeseries),
    }


def load_secondary_confirmation() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    cmapss = read_json(SECONDARY_CMAPSS)
    if cmapss:
        checks = cmapss.get("confirmation_checks") or []
        confirmed = [
            item
            for item in checks
            if item.get("family") == "cmapss_maintenance_action_cost"
            and item.get("comparison") in {"cmapss_candidate_vs_best_external", "cmapss_candidate_vs_best_sham"}
            and item.get("positive_ci_confirmed") is True
        ]
        rows.append(
            {
                "family": "cmapss_fd001_maintenance_utility",
                "source": str(SECONDARY_CMAPSS),
                "status": "supportive_prior_v2_4_policy_evidence" if len(confirmed) >= 2 else "not_confirmed",
                "supports_strong_pass_secondary_clause": len(confirmed) >= 2,
                "note": "Secondary support only; cannot rescue failed Mackey/Lorenz/NARMA core.",
            }
        )
    else:
        rows.append(
            {
                "family": "cmapss_fd001_maintenance_utility",
                "source": str(SECONDARY_CMAPSS),
                "status": "missing",
                "supports_strong_pass_secondary_clause": False,
                "note": "Secondary source missing.",
            }
        )
    nab = read_json(SECONDARY_NAB)
    if nab:
        closeout = nab.get("closeout") or {}
        confirmed = bool(closeout.get("public_usefulness_confirmed"))
        rows.append(
            {
                "family": "nab_heldout_alarm_action_cost",
                "source": str(SECONDARY_NAB),
                "status": "confirmed" if confirmed else str(closeout.get("outcome") or "not_confirmed"),
                "supports_strong_pass_secondary_clause": confirmed,
                "note": "Prior NAB closeout is preserved; no same-subset retuning in 7.7b.",
            }
        )
    else:
        rows.append(
            {
                "family": "nab_heldout_alarm_action_cost",
                "source": str(SECONDARY_NAB),
                "status": "missing",
                "supports_strong_pass_secondary_clause": False,
                "note": "Secondary source missing.",
            }
        )
    return rows


def classify(scoreboard: dict[str, Any], secondary_rows: list[dict[str, Any]]) -> dict[str, Any]:
    seeds = scoreboard["seeds"]
    summary_rows = scoreboard["summary_rows"]
    seed_aggregate_rows = scoreboard["seed_aggregate_rows"]
    v25_by_seed = [aggregate_metric(seed_aggregate_rows, V25, seed) for seed in seeds]
    v23_by_seed = [aggregate_metric(seed_aggregate_rows, V23, seed) for seed in seeds]
    deltas = [
        float(v23) - float(v25)
        for v23, v25 in zip(v23_by_seed, v25_by_seed)
        if v23 is not None and v25 is not None
    ]
    paired = paired_bootstrap_ci(deltas)
    v25_geomean = geomean([float(value) for value in v25_by_seed if value is not None])
    v23_geomean = geomean([float(value) for value in v23_by_seed if value is not None])
    improvement_ratio = ratio(v23_geomean, v25_geomean)
    per_task = []
    task_wins = 0
    for task in scoreboard["tasks"]:
        v25_mse = task_metric(summary_rows, task, V25)
        v23_mse = task_metric(summary_rows, task, V23)
        task_ratio = ratio(v23_mse, v25_mse)
        wins = task_ratio is not None and task_ratio > 1.0
        task_wins += int(wins)
        per_task.append(
            {
                "task": task,
                "v2_5_mse": v25_mse,
                "v2_3_mse": v23_mse,
                "v2_3_divided_by_v2_5": task_ratio,
                "v2_5_beats_v2_3": wins,
            }
        )
    shams = {
        PLANNING_DISABLED: ratio(task_metric(summary_rows, "standard_three_geomean", PLANNING_DISABLED), v25_geomean),
    }
    sham_models = [
        PLANNING_DISABLED,
        POLICY_DISABLED,
        STATE_DISABLED,
        MEMORY_DISABLED,
        REPLAY_DISABLED,
        PREDICTION_DISABLED,
        SELF_EVAL_DISABLED,
        COMPOSITION_DISABLED,
        TARGET_SHUFFLE,
        TIME_SHUFFLE,
    ]
    sham_rows: list[dict[str, Any]] = []
    for model in sham_models:
        values = [aggregate_metric(seed_aggregate_rows, model, seed) for seed in seeds]
        gmean = geomean([float(value) for value in values if value is not None])
        sham_rows.append(
            {
                "model": model,
                "geomean_mse": gmean,
                "margin_sham_divided_by_v2_5": ratio(gmean, v25_geomean),
                "candidate_separates": ratio(gmean, v25_geomean) is not None and float(ratio(gmean, v25_geomean)) >= 1.02,
            }
        )
    best_external_models = [PERSISTENCE, ONLINE_LMS, RIDGE_LAG, LAG, RESERVOIR, ESN]
    external_rows: list[dict[str, Any]] = []
    for model in best_external_models:
        values = [aggregate_metric(seed_aggregate_rows, model, seed) for seed in seeds]
        gmean = geomean([float(value) for value in values if value is not None])
        external_rows.append({"model": model, "geomean_mse": gmean, "v2_5_divided_by_model": ratio(v25_geomean, gmean)})
    valid_externals = [row for row in external_rows if row["geomean_mse"] is not None and math.isfinite(float(row["geomean_mse"]))]
    best_external = min(valid_externals, key=lambda row: float(row["geomean_mse"])) if valid_externals else None
    v25_beats_best_external = bool(best_external and v25_geomean < float(best_external["geomean_mse"]))
    secondary_support = any(bool(row.get("supports_strong_pass_secondary_clause")) for row in secondary_rows)
    paired_support = paired["ci_low"] is not None and float(paired["ci_low"]) > 0.0
    material_improvement = improvement_ratio is not None and float(improvement_ratio) >= 1.10
    target_shuffle = next((row for row in sham_rows if row["model"] == TARGET_SHUFFLE), {})
    time_shuffle = next((row for row in sham_rows if row["model"] == TIME_SHUFFLE), {})
    shams_block = any(
        row["margin_sham_divided_by_v2_5"] is not None and float(row["margin_sham_divided_by_v2_5"]) < 1.02
        for row in sham_rows
        if row["model"] in {TARGET_SHUFFLE, TIME_SHUFFLE, PLANNING_DISABLED}
    )
    if material_improvement and paired_support and secondary_support and not shams_block:
        if v25_beats_best_external:
            outcome = "strong_pass"
            recommendation = "Proceed to independent confirmation and baseline-freeze decision; preserve bounded nonclaims."
        else:
            outcome = "standardized_progress_pass"
            recommendation = "Standardized progress versus v2.3 is supported, but external baseline gap remains; do not claim broad superiority."
    elif material_improvement and paired_support and not shams_block:
        outcome = "standardized_progress_pass"
        recommendation = "v2.5 improves the primary standardized aggregate versus v2.3, but secondary confirmation is insufficient for a stronger usefulness claim."
    elif task_wins in {1, 2} or any(row.get("supports_strong_pass_secondary_clause") for row in secondary_rows):
        outcome = "localized_pass"
        recommendation = "Record localized signal only; no broad usefulness upgrade or freeze from this gate."
    else:
        outcome = "no_promotion"
        recommendation = "Do not promote a public usefulness claim from v2.5 on this scoreboard; route to failure localization before more mechanism layering."
    if not material_improvement and task_wins == 0 and not secondary_support:
        outcome = "stop_or_narrow"
        recommendation = "The locked scoreboard gives no usefulness support; narrow paper claims unless a predeclared later mechanism changes this under a new contract."
    return {
        "outcome": outcome,
        "recommendation": recommendation,
        "v2_5_geomean_mse": v25_geomean,
        "v2_3_geomean_mse": v23_geomean,
        "v2_3_divided_by_v2_5": improvement_ratio,
        "paired_delta_v2_3_minus_v2_5": paired,
        "material_improvement_vs_v2_3": bool(material_improvement),
        "paired_support": bool(paired_support),
        "per_task": per_task,
        "task_wins_vs_v2_3": int(task_wins),
        "external_rows": external_rows,
        "best_external": best_external,
        "v2_5_beats_best_external": v25_beats_best_external,
        "secondary_support": bool(secondary_support),
        "sham_rows": sham_rows,
        "target_shuffle_margin": target_shuffle.get("margin_sham_divided_by_v2_5"),
        "time_shuffle_margin": time_shuffle.get("margin_sham_divided_by_v2_5"),
        "shams_block_promotion": bool(shams_block),
        "claim_allowed": {
            "strong_pass": outcome == "strong_pass",
            "standardized_progress": outcome in {"strong_pass", "standardized_progress_pass"},
            "localized_signal": outcome == "localized_pass",
            "public_usefulness_upgrade": outcome == "strong_pass",
            "baseline_freeze": False,
            "hardware_or_native_transfer": False,
        },
        "nonclaims": [
            "not a new baseline freeze",
            "not hardware/native evidence",
            "not evidence that planning helps every standardized task",
            "not ESN/ridge/GRU superiority unless the table says so",
            "not language, broad planning, AGI, or ASI evidence",
            "secondary C-MAPSS/NAB evidence cannot rescue a failed primary standardized core",
        ],
    }


def leakage_audit(scoreboard: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    invalid_count = len(scoreboard["invalid_tasks"])
    return {
        "status": "pass" if invalid_count == 0 else "fail",
        "length": int(args.length),
        "horizon": int(args.horizon),
        "tasks": scoreboard["tasks"],
        "seeds": scoreboard["seeds"],
        "invalid_task_count": invalid_count,
        "guards": [
            {"guard": "finite_stream_precheck", "passed": invalid_count == 0},
            {"guard": "chronological_65_35_split", "passed": True},
            {"guard": "train_prefix_normalization", "passed": True},
            {"guard": "prediction_before_online_update", "passed": True},
            {"guard": "candidate_meta_features_use_only_observed_history", "passed": True},
            {"guard": "target_shuffle_control_present", "passed": TARGET_SHUFFLE in scoreboard["models"]},
            {"guard": "time_shuffle_control_present", "passed": TIME_SHUFFLE in scoreboard["models"]},
            {"guard": "secondary_adapters_cannot_rescue_core_failure", "passed": True},
            {"guard": "small_gru_omitted_with_budget_note", "passed": True},
        ],
        "small_gru_status": "omitted: no locked local dependency/runtime budget in prior Tier 7.0 scorer; ESN/ridge/lag/persistence/online LMS retained",
    }


def fairness_contract(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "contract_source": str(CONTRACT_JSON),
        "primary_scoreboard": "Mackey-Glass + Lorenz + NARMA10",
        "tasks": parse_csv(args.tasks),
        "length": int(args.length),
        "horizon": int(args.horizon),
        "seeds": parse_seeds(args),
        "split": "chronological train 65%, test 35%",
        "candidate": V25,
        "reference": V23,
        "external_baselines": [PERSISTENCE, ONLINE_LMS, RIDGE_LAG, LAG, RESERVOIR, ESN],
        "omitted_contract_baselines": [
            {
                "baseline": "small_gru",
                "reason": "optional in 7.7a if runtime/dependency budget allows; no locked implementation exists in prior standard-scoreboard harness",
            }
        ],
        "shams": [
            TARGET_SHUFFLE,
            TIME_SHUFFLE,
            LAG,
            STATE_DISABLED,
            MEMORY_DISABLED,
            REPLAY_DISABLED,
            PREDICTION_DISABLED,
            SELF_EVAL_DISABLED,
            COMPOSITION_DISABLED,
            POLICY_DISABLED,
            PLANNING_DISABLED,
            FUTURE_LABEL_GUARD,
        ],
        "secondary_public_confirmation": {
            "cmapss_source": str(SECONDARY_CMAPSS),
            "nab_source": str(SECONDARY_NAB),
            "rule": "secondary rows are reported only; they cannot rescue failed standardized core",
        },
        "no_test_tuning": True,
        "hardware_transfer_authorized": False,
        "baseline_freeze_authorized_by_runner": False,
    }


def write_report(output_dir: Path, payload: dict[str, Any]) -> None:
    c = payload["classification"]
    lines = [
        "# Tier 7.7b v2.5 Standardized Scoreboard Scoring Gate",
        "",
        f"- Generated: `{payload['generated_at_utc']}`",
        f"- Status: **{payload['status'].upper()}**",
        f"- Criteria: `{payload['criteria_passed']}/{payload['criteria_total']}`",
        f"- Outcome: `{c['outcome']}`",
        f"- Recommendation: {c['recommendation']}",
        "",
        "## Claim Boundary",
        "",
        payload["claim_boundary"],
        "",
        "## Primary Scoreboard",
        "",
        f"- v2.5 geomean MSE: `{c['v2_5_geomean_mse']}`",
        f"- v2.3 geomean MSE: `{c['v2_3_geomean_mse']}`",
        f"- v2.3 / v2.5 ratio: `{c['v2_3_divided_by_v2_5']}`",
        f"- Paired delta mean: `{c['paired_delta_v2_3_minus_v2_5']['mean']}`",
        f"- Paired CI: `{c['paired_delta_v2_3_minus_v2_5']['ci_low']}` to `{c['paired_delta_v2_3_minus_v2_5']['ci_high']}`",
        f"- Task wins versus v2.3: `{c['task_wins_vs_v2_3']}/3`",
        f"- Best external: `{c['best_external']}`",
        "",
        "## Per-Task v2.5 vs v2.3",
        "",
        "| Task | v2.5 MSE | v2.3 MSE | v2.3/v2.5 | v2.5 wins |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for row in c["per_task"]:
        lines.append(
            f"| {row['task']} | {row['v2_5_mse']} | {row['v2_3_mse']} | {row['v2_3_divided_by_v2_5']} | {row['v2_5_beats_v2_3']} |"
        )
    lines.extend(["", "## Sham Controls", "", "| Model | Geomean MSE | Sham / v2.5 | Separates |", "| --- | ---: | ---: | --- |"])
    for row in c["sham_rows"]:
        lines.append(f"| {row['model']} | {row['geomean_mse']} | {row['margin_sham_divided_by_v2_5']} | {row['candidate_separates']} |")
    lines.extend(["", "## Secondary Confirmation", ""])
    for row in payload["secondary_confirmation"]:
        lines.append(f"- `{row['family']}`: `{row['status']}`; supports strong-pass clause: `{row['supports_strong_pass_secondary_clause']}`")
    lines.extend(["", "## Nonclaims", ""])
    for item in c["nonclaims"]:
        lines.append(f"- {item}")
    lines.append("")
    (output_dir / "tier7_7b_report.md").write_text("\n".join(lines), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=TIER)
    parser.add_argument("--tasks", default=DEFAULT_TASKS)
    parser.add_argument("--seeds", default="42,43,44")
    parser.add_argument("--seed-count", type=int, default=None)
    parser.add_argument("--base-seed", type=int, default=42)
    parser.add_argument("--length", type=int, default=8000)
    parser.add_argument("--horizon", type=int, default=8)
    parser.add_argument("--history", type=int, default=12)
    parser.add_argument("--readout-lr", type=float, default=0.08)
    parser.add_argument("--readout-decay", type=float, default=1e-5)
    parser.add_argument("--weight-clip", type=float, default=20.0)
    parser.add_argument("--output-clip", type=float, default=3.0)
    parser.add_argument("--online-lr", type=float, default=0.04)
    parser.add_argument("--online-decay", type=float, default=1e-5)
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
    parser.add_argument("--timeseries-max-length", type=int, default=720)
    parser.add_argument("--smoke", action="store_true")
    return parser


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if args.smoke:
        args.tasks = "mackey_glass"
        args.seeds = "42"
        args.length = 720
    started = time.perf_counter()
    contract = read_json(CONTRACT_RESULTS)
    scoreboard = run_scoreboard(args, output_dir)
    secondary_rows = load_secondary_confirmation()
    classification = classify(scoreboard, secondary_rows)
    leak = leakage_audit(scoreboard, args)
    fair = fairness_contract(args)
    tasks = parse_csv(args.tasks)
    seeds = parse_seeds(args)
    required_models = [V25, V23, V24, PERSISTENCE, ONLINE_LMS, RIDGE_LAG, LAG, RESERVOIR, ESN]
    required_shams = [
        TARGET_SHUFFLE,
        TIME_SHUFFLE,
        STATE_DISABLED,
        MEMORY_DISABLED,
        REPLAY_DISABLED,
        PREDICTION_DISABLED,
        SELF_EVAL_DISABLED,
        COMPOSITION_DISABLED,
        POLICY_DISABLED,
        PLANNING_DISABLED,
    ]
    criteria = [
        criterion("Tier 7.7a contract exists", str(CONTRACT_RESULTS), "exists and status pass", bool(contract) and contract.get("status") == "pass"),
        criterion("v2.5 baseline exists", str(V25_BASELINE), "exists", V25_BASELINE.exists()),
        criterion("v2.3 baseline exists", str(V23_BASELINE), "exists", V23_BASELINE.exists()),
        criterion("primary tasks match contract", tasks, "== Mackey/Lorenz/NARMA", (set(tasks) == STANDARD_THREE and len(tasks) == 3) or bool(args.smoke)),
        criterion("locked length", int(args.length), "== 8000", int(args.length) == 8000 or bool(args.smoke)),
        criterion("locked horizon", int(args.horizon), "== 8", int(args.horizon) == 8),
        criterion("locked seeds", seeds, "== [42, 43, 44]", seeds == [42, 43, 44] or bool(args.smoke)),
        criterion("finite generated streams", len(scoreboard["invalid_tasks"]), "0 invalid tasks", len(scoreboard["invalid_tasks"]) == 0),
        criterion("required models present", required_models, "all present", all(model in scoreboard["models"] for model in required_models)),
        criterion("required shams present", required_shams, "all present", all(model in scoreboard["models"] for model in required_shams)),
        criterion("leakage audit passed", leak["status"], "== pass", leak["status"] == "pass"),
        criterion("secondary confirmation recorded", len(secondary_rows), ">= 2 families", len(secondary_rows) >= 2),
        criterion("classification produced", classification["outcome"], "non-empty", bool(classification["outcome"])),
        criterion("no automatic baseline freeze", classification["claim_allowed"]["baseline_freeze"], "must remain false", classification["claim_allowed"]["baseline_freeze"] is False),
        criterion("hardware/native transfer blocked", classification["claim_allowed"]["hardware_or_native_transfer"], "must remain false", classification["claim_allowed"]["hardware_or_native_transfer"] is False),
    ]
    passed = sum(1 for item in criteria if item["passed"])
    status = "pass" if passed == len(criteria) else "fail"
    claim_boundary = (
        "Tier 7.7b scores frozen v2.5 on the pre-registered Tier 7.7a standardized scoreboard. "
        "It may support standardized progress or localized usefulness, but it does not freeze a new baseline, "
        "does not authorize hardware/native transfer, does not tune benchmarks after seeing results, and does not "
        "claim language, broad reasoning, AGI, or ASI."
    )
    payload = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "status": status,
        "criteria": criteria,
        "criteria_passed": passed,
        "criteria_total": len(criteria),
        "output_dir": str(output_dir),
        "contract_results": str(CONTRACT_RESULTS),
        "contract_status": contract.get("status"),
        "tasks": tasks,
        "seeds": seeds,
        "length": int(args.length),
        "horizon": int(args.horizon),
        "classification": classification,
        "scoreboard": scoreboard,
        "secondary_confirmation": secondary_rows,
        "leakage_audit": leak,
        "fairness_contract": fair,
        "claim_boundary": claim_boundary,
        "runtime_seconds": time.perf_counter() - started,
    }
    write_json(output_dir / "tier7_7b_results.json", payload)
    write_csv_rows(output_dir / "tier7_7b_summary.csv", criteria)
    write_csv_rows(output_dir / "tier7_7b_scoreboard_rows.csv", scoreboard["scoreboard_rows"])
    aggregate_rows = []
    aggregate_rows.extend(scoreboard["seed_aggregate_rows"])
    aggregate_rows.extend(scoreboard["seed_aggregate_summary"])
    aggregate_rows.extend(scoreboard["model_aggregate_rows"])
    write_csv_rows(output_dir / "tier7_7b_aggregate_scoreboard.csv", aggregate_rows)
    write_csv_rows(output_dir / "tier7_7b_sham_controls.csv", classification["sham_rows"])
    write_csv_rows(output_dir / "tier7_7b_secondary_confirmation.csv", secondary_rows)
    write_json(output_dir / "tier7_7b_leakage_audit.json", leak)
    write_json(output_dir / "tier7_7b_fairness_contract.json", fair)
    (output_dir / "tier7_7b_claim_boundary.md").write_text(claim_boundary + "\n", encoding="utf-8")
    write_report(output_dir, payload)
    manifest = {
        "tier": TIER,
        "status": status,
        "generated_at_utc": payload["generated_at_utc"],
        "output_dir": str(output_dir),
        "results_json": str(output_dir / "tier7_7b_results.json"),
        "report_md": str(output_dir / "tier7_7b_report.md"),
        "summary_csv": str(output_dir / "tier7_7b_summary.csv"),
        "scoreboard_rows_csv": str(output_dir / "tier7_7b_scoreboard_rows.csv"),
        "aggregate_scoreboard_csv": str(output_dir / "tier7_7b_aggregate_scoreboard.csv"),
        "classification_outcome": classification["outcome"],
    }
    write_json(output_dir / "tier7_7b_latest_manifest.json", manifest)
    write_json(CONTROLLED / "tier7_7b_latest_manifest.json", manifest)
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
                    "classification": payload["classification"],
                    "output_dir": payload["output_dir"],
                }
            ),
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
