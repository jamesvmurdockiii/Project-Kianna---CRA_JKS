#!/usr/bin/env python3
"""Tier 7.0b - Continuous-Regression Failure Analysis.

Tier 7.0 showed that CRA v2.1 online underperformed simple sequence baselines
on Mackey-Glass, Lorenz, and NARMA10. This tier does not tune CRA and does not
promote a new mechanism. It diagnoses where the gap lives.

The key probe is a leakage-safe causal readout over CRA internal state. The
state is captured inside the adapter evaluation callback after the current
input has driven the organism's prediction but before the current target is
used for learning. A ridge probe is then fit only on the chronological training
prefix and scored on held-out test rows.

Interpretation:
  - If the state probe closes the gap, CRA has useful state but the native
    online readout/credit interface is mismatched to continuous regression.
  - If the state probe also fails, the gap is deeper: state/history/reservoir
    dynamics or task interface.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
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

from coral_reef_spinnaker import Observation, Organism, ReefConfig  # noqa: E402
from coral_reef_spinnaker.signals import ConsequenceSignal  # noqa: E402
from tier2_learning import end_backend, load_backend, setup_backend  # noqa: E402
from tier4_scaling import mean, stdev  # noqa: E402
from tier7_0_standard_dynamical_benchmarks import (  # noqa: E402
    DEFAULT_MODELS as TIER7_MODELS,
    DEFAULT_TASKS,
    SequenceTask,
    build_task,
    geometric_mean,
    parse_csv,
    parse_seeds,
    ridge_fit,
    score_predictions,
)


TIER = "Tier 7.0b - Continuous-Regression Failure Analysis"
RUNNER_REVISION = "tier7_0b_continuous_regression_failure_analysis_20260505_0001"
DEFAULT_OUTPUT_DIR = OUTPUT_ROOT / "tier7_0b_20260505_continuous_regression_failure_analysis"


@dataclass
class Trace:
    task: str
    seed: int
    observed: np.ndarray
    target: np.ndarray
    train_end: int
    cra_prediction: np.ndarray
    features: np.ndarray
    feature_names: list[str]
    rows: list[dict[str, Any]]
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


def stable_corr(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if a.size < 3 or b.size < 3:
        return 0.0
    if float(np.std(a)) < 1e-12 or float(np.std(b)) < 1e-12:
        return 0.0
    return float(np.corrcoef(a, b)[0, 1])


def lag_matrix(values: np.ndarray, history: int) -> np.ndarray:
    rows = []
    for i in range(len(values)):
        row = [1.0]
        for lag in range(history):
            idx = i - lag
            row.append(float(values[idx]) if idx >= 0 else 0.0)
        rows.append(row)
    return np.asarray(rows, dtype=float)


def fit_predict_ridge(features: np.ndarray, target: np.ndarray, train_end: int, ridge: float) -> tuple[np.ndarray, float]:
    w = ridge_fit(features[:train_end], target[:train_end], ridge)
    return features @ w, float(np.linalg.norm(w))


class DiagnosticRegressionAdapter:
    task_name = "tier7_0b_regression"

    def __init__(self, organism: Organism, *, max_polyps: int):
        self.organism = organism
        self.max_polyps = max(1, int(max_polyps))
        self.feature_names = self._feature_names()
        self.rows: list[dict[str, Any]] = []
        self.features: list[list[float]] = []
        self.predictions: list[float] = []
        self.capture_steps = 0

    def _feature_names(self) -> list[str]:
        names = [
            "bias",
            "observed_current",
            "cra_colony_prediction",
            "context_memory_value",
            "predictive_context_value",
            "composition_module_uses",
            "composition_router_uses",
        ]
        for idx in range(self.max_polyps):
            prefix = f"polyp{idx}"
            names.extend(
                [
                    f"{prefix}_alive",
                    f"{prefix}_last_output",
                    f"{prefix}_current_prediction",
                    f"{prefix}_readout_weight",
                    f"{prefix}_readout_bias",
                    f"{prefix}_activity_rate",
                    f"{prefix}_dopamine_ema",
                    f"{prefix}_output_scale",
                    f"{prefix}_trophic_health",
                    f"{prefix}_last_feature",
                    f"{prefix}_matured_credit",
                ]
            )
        return names

    def encode(self, observation: Observation, n_channels: int) -> np.ndarray:
        out = np.zeros(max(1, int(n_channels)), dtype=float)
        values = np.asarray(observation.x, dtype=float).reshape(-1)
        out[0] = float(values[0]) if values.size else 0.0
        return out

    def _capture_features(self, prediction: float, observation: Observation) -> list[float]:
        states = []
        if self.organism.polyp_population is not None:
            states = list(self.organism.polyp_population.states)
        values = [
            1.0,
            float(np.asarray(observation.x, dtype=float).reshape(-1)[0]),
            float(prediction),
            float(getattr(self.organism, "_context_memory_value", 0.0)),
            float(getattr(self.organism, "_predictive_context_value", 0.0)),
            float(getattr(self.organism, "_composition_module_uses", 0.0)),
            float(getattr(self.organism, "_composition_router_uses", 0.0)),
        ]
        for idx in range(self.max_polyps):
            state = states[idx] if idx < len(states) else None
            if state is None:
                values.extend([0.0] * 11)
                continue
            values.extend(
                [
                    1.0 if bool(getattr(state, "is_alive", False)) else 0.0,
                    float(getattr(state, "last_output_signed_contribution", 0.0)),
                    float(getattr(state, "current_prediction", 0.0)),
                    float(getattr(state, "predictive_readout_weight", 0.0)),
                    float(getattr(state, "predictive_readout_bias", 0.0)),
                    float(getattr(state, "activity_rate", 0.0)),
                    float(getattr(state, "dopamine_ema", 0.0)),
                    float(getattr(state, "output_scale", 0.0)),
                    float(getattr(state, "trophic_health", 0.0)),
                    float(getattr(state, "last_prediction_feature", 0.0)),
                    float(getattr(state, "last_net_matured_consequence_credit", 0.0)),
                ]
            )
        return values

    def evaluate(self, prediction: float, observation: Observation, dt_seconds: float) -> ConsequenceSignal:
        del dt_seconds
        target = 0.0 if observation.target is None else float(observation.target)
        feature_values = self._capture_features(prediction, observation)
        self.features.append(feature_values)
        self.predictions.append(float(prediction))
        self.capture_steps += 1
        err = target - float(prediction)
        correct = (prediction >= 0.0) == (target >= 0.0)
        self.rows.append(
            {
                "step": int(observation.metadata.get("step", self.capture_steps - 1) if observation.metadata else self.capture_steps - 1),
                "observed": float(np.asarray(observation.x, dtype=float).reshape(-1)[0]),
                "target": target,
                "cra_prediction": float(prediction),
                "target_minus_prediction": err,
                "direction_correct": bool(correct),
                "capture_timing": "pre_current_target_learning",
            }
        )
        return ConsequenceSignal(
            immediate_signal=target,
            horizon_signal=target,
            actual_value=target,
            prediction=float(prediction),
            direction_correct=bool(correct),
            raw_dopamine=float(np.tanh(err)),
            task_metrics={"regression_error": err, "squared_error": err * err},
            metadata={"adapter": "tier7_0b_diagnostic", "stream_id": observation.stream_id},
        )


def collect_cra_trace(task: SequenceTask, *, seed: int, args: argparse.Namespace) -> Trace:
    random.seed(seed)
    np.random.seed(seed)
    sim, backend_name = load_backend(args.backend)
    setup_backend(sim, backend_name)
    cfg = ReefConfig.default()
    cfg.seed = int(seed)
    cfg.lifecycle.initial_population = int(args.cra_population_size)
    cfg.lifecycle.max_population_hard = int(args.cra_population_size)
    cfg.lifecycle.max_population_from_memory = False
    cfg.lifecycle.enable_reproduction = False
    cfg.lifecycle.enable_apoptosis = False
    cfg.measurement.stream_history_maxlen = max(len(task.observed) + 32, 256)
    cfg.learning.readout_learning_rate = float(args.cra_readout_lr)
    cfg.learning.delayed_readout_learning_rate = float(args.cra_delayed_lr)
    cfg.learning.evaluation_horizon_bars = int(max(1, task.horizon))
    cfg.spinnaker.sync_interval_steps = 0
    cfg.spinnaker.runtime_ms_per_step = 1000.0
    organism = Organism(cfg, sim, use_default_trading_bridge=False)
    adapter = DiagnosticRegressionAdapter(organism, max_polyps=args.cra_population_size)
    try:
        organism.initialize(stream_keys=[task.name])
        for step, (obs, target) in enumerate(zip(task.observed, task.target)):
            observation = Observation(
                stream_id=task.name,
                x=np.asarray([float(obs)], dtype=float),
                target=float(target),
                timestamp=float(step),
                metadata={"tier": "7.0b", "task": task.name, "step": int(step)},
            )
            organism.train_adapter_step(adapter, observation, dt_seconds=1.0)
        diagnostics = {
            "backend": backend_name,
            "capture_steps": adapter.capture_steps,
            "capture_timing": "inside adapter.evaluate before current target learning update",
            "backend_diagnostics": organism.backend_diagnostics(),
        }
    finally:
        organism.shutdown()
        end_backend(sim)
    return Trace(
        task=task.name,
        seed=int(seed),
        observed=np.asarray(task.observed, dtype=float),
        target=np.asarray(task.target, dtype=float),
        train_end=int(task.train_end),
        cra_prediction=np.asarray(adapter.predictions, dtype=float),
        features=np.asarray(adapter.features, dtype=float),
        feature_names=adapter.feature_names,
        rows=adapter.rows,
        diagnostics=diagnostics,
    )


def evaluate_probe(task: str, seed: int, train_end: int, target: np.ndarray, pred: np.ndarray, model: str, diagnostics: dict[str, Any] | None = None) -> dict[str, Any]:
    pseudo_task = SequenceTask(
        name=task,
        display_name=task,
        observed=np.zeros_like(target),
        target=np.asarray(target, dtype=float),
        train_end=int(train_end),
        horizon=1,
        metadata={},
    )
    scores = score_predictions(pseudo_task, np.asarray(pred, dtype=float))
    test = slice(train_end, len(target))
    return {
        "task": task,
        "seed": int(seed),
        "model": model,
        "status": "pass",
        "mse": scores["mse"],
        "nmse": scores["nmse"],
        "tail_mse": scores["tail_mse"],
        "train_mse": scores["train_mse"],
        "test_corr": stable_corr(np.asarray(pred, dtype=float)[test], target[test]),
        "diagnostics": diagnostics or {},
    }


def shuffled_target_probe(features: np.ndarray, target: np.ndarray, train_end: int, ridge: float, seed: int) -> tuple[np.ndarray, float]:
    rng = np.random.default_rng(seed + 7070)
    shuffled = np.asarray(target, dtype=float).copy()
    train_values = shuffled[:train_end].copy()
    rng.shuffle(train_values)
    shuffled[:train_end] = train_values
    w = ridge_fit(features[:train_end], shuffled[:train_end], ridge)
    return features @ w, float(np.linalg.norm(w))


def run_trace_probes(trace: Trace, *, args: argparse.Namespace) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    timeseries_rows: list[dict[str, Any]] = []
    target = trace.target
    train_end = trace.train_end
    observed_lags = lag_matrix(trace.observed, args.history)
    prediction_affine_features = np.column_stack([np.ones(len(target)), trace.cra_prediction])
    prediction_plus_observed_features = np.column_stack(
        [np.ones(len(target)), trace.cra_prediction, trace.observed]
    )

    probes: list[tuple[str, np.ndarray, dict[str, Any]]] = [
        ("cra_online_raw", trace.cra_prediction, {"probe": "raw CRA colony prediction"}),
    ]

    pred, norm = fit_predict_ridge(prediction_affine_features, target, train_end, args.ridge)
    probes.append(("cra_prediction_affine_probe", pred, {"probe": "ridge over raw CRA prediction only", "weight_norm": norm}))

    pred, norm = fit_predict_ridge(prediction_plus_observed_features, target, train_end, args.ridge)
    probes.append(
        (
            "cra_prediction_plus_observed_probe",
            pred,
            {"probe": "ridge over CRA prediction plus current observation", "weight_norm": norm},
        )
    )

    pred, norm = fit_predict_ridge(trace.features, target, train_end, args.ridge)
    probes.append(("cra_internal_state_ridge_probe", pred, {"probe": "ridge over pre-learning CRA internal state", "weight_norm": norm}))

    pred, norm = fit_predict_ridge(np.column_stack([trace.features, observed_lags]), target, train_end, args.ridge)
    probes.append(
        (
            "cra_state_plus_lag_probe",
            pred,
            {"probe": "ridge over CRA internal state plus same lag budget used by ridge_lag", "weight_norm": norm},
        )
    )

    pred, norm = shuffled_target_probe(trace.features, target, train_end, args.ridge, trace.seed)
    probes.append(
        (
            "cra_internal_state_shuffled_target_control",
            pred,
            {"probe": "same state features fit to shuffled train targets", "weight_norm": norm},
        )
    )

    for model, pred_values, diagnostics in probes:
        rows.append(evaluate_probe(trace.task, trace.seed, train_end, target, pred_values, model, diagnostics))
        for step, (obs, tgt, pred_value) in enumerate(zip(trace.observed, target, pred_values)):
            timeseries_rows.append(
                {
                    "task": trace.task,
                    "seed": int(trace.seed),
                    "model": model,
                    "step": int(step),
                    "split": "train" if step < train_end else "test",
                    "observed": float(obs),
                    "target": float(tgt),
                    "prediction": float(pred_value),
                    "squared_error": float((float(pred_value) - float(tgt)) ** 2),
                    "capture_timing": "pre_current_target_learning",
                }
            )
    return rows, timeseries_rows


def summarize_rows(rows: list[dict[str, Any]], tasks: list[str], models: list[str], seeds: list[int]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    summary: list[dict[str, Any]] = []
    aggregate: list[dict[str, Any]] = []
    for task in tasks:
        for model in models:
            subset = [r for r in rows if r["task"] == task and r["model"] == model and r["status"] == "pass"]
            summary.append(
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
                aggregate.append(
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
                aggregate.append(
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
        subset = [r for r in aggregate if r["model"] == model and r["status"] == "pass"]
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
    return summary, aggregate, aggregate_summary


def classify_failure(aggregate_summary: list[dict[str, Any]]) -> dict[str, Any]:
    by_model = {row["model"]: row for row in aggregate_summary if row["status"] == "pass"}
    raw = by_model.get("cra_online_raw")
    state = by_model.get("cra_internal_state_ridge_probe")
    lag_state = by_model.get("cra_state_plus_lag_probe")
    shuffled = by_model.get("cra_internal_state_shuffled_target_control")
    affine = by_model.get("cra_prediction_affine_probe")
    plus_obs = by_model.get("cra_prediction_plus_observed_probe")

    raw_mse = float(raw["geomean_mse_mean"]) if raw and raw.get("geomean_mse_mean") is not None else math.inf
    state_mse = float(state["geomean_mse_mean"]) if state and state.get("geomean_mse_mean") is not None else math.inf
    lag_state_mse = float(lag_state["geomean_mse_mean"]) if lag_state and lag_state.get("geomean_mse_mean") is not None else math.inf
    shuffled_mse = float(shuffled["geomean_mse_mean"]) if shuffled and shuffled.get("geomean_mse_mean") is not None else math.inf
    affine_mse = float(affine["geomean_mse_mean"]) if affine and affine.get("geomean_mse_mean") is not None else math.inf
    plus_obs_mse = float(plus_obs["geomean_mse_mean"]) if plus_obs and plus_obs.get("geomean_mse_mean") is not None else math.inf

    state_improvement = raw_mse / state_mse if math.isfinite(raw_mse) and state_mse > 0 and math.isfinite(state_mse) else None
    lag_state_improvement = raw_mse / lag_state_mse if math.isfinite(raw_mse) and lag_state_mse > 0 and math.isfinite(lag_state_mse) else None
    affine_improvement = raw_mse / affine_mse if math.isfinite(raw_mse) and affine_mse > 0 and math.isfinite(affine_mse) else None
    state_vs_shuffled = shuffled_mse / state_mse if math.isfinite(shuffled_mse) and state_mse > 0 and math.isfinite(state_mse) else None
    lag_state_vs_state = state_mse / lag_state_mse if math.isfinite(state_mse) and lag_state_mse > 0 and math.isfinite(lag_state_mse) else None

    if state_improvement is not None and state_improvement >= 2.0 and state_vs_shuffled is not None and state_vs_shuffled >= 1.25:
        failure_class = "recoverable_state_signal_default_readout_failure"
        recommendation = "Design a bounded continuous readout/interface repair before adding new organism mechanisms."
    elif lag_state_improvement is not None and lag_state_improvement >= 2.0 and lag_state_vs_state is not None and lag_state_vs_state >= 1.25:
        failure_class = "history_feature_gap"
        recommendation = "The current CRA state needs explicit causal history/reservoir support for these benchmarks."
    elif affine_improvement is not None and affine_improvement >= 1.5:
        failure_class = "output_calibration_partial_failure"
        recommendation = "The raw online prediction scale/sign interface is a major contributor; test calibration/readout repair."
    elif plus_obs_mse < raw_mse * 0.5:
        failure_class = "task_interface_or_observation_feature_gap"
        recommendation = "Current CRA prediction adds too little beyond the raw observation; inspect adapter/features before mechanism work."
    else:
        failure_class = "state_representation_gap"
        recommendation = "The benchmark exposes a deeper state/history dynamics gap; do not move this workload to hardware yet."

    return {
        "failure_class": failure_class,
        "raw_cra_geomean_mse": raw_mse,
        "state_probe_geomean_mse": state_mse,
        "state_plus_lag_geomean_mse": lag_state_mse,
        "prediction_affine_geomean_mse": affine_mse,
        "prediction_plus_observed_geomean_mse": plus_obs_mse,
        "shuffled_control_geomean_mse": shuffled_mse,
        "state_improvement_over_raw": state_improvement,
        "state_plus_lag_improvement_over_raw": lag_state_improvement,
        "affine_improvement_over_raw": affine_improvement,
        "state_vs_shuffled_control_advantage": state_vs_shuffled,
        "state_plus_lag_advantage_over_state": lag_state_vs_state,
        "recommendation": recommendation,
    }


def write_report(output_dir: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# Tier 7.0b Continuous-Regression Failure Analysis",
        "",
        f"- Generated: `{payload['generated_at_utc']}`",
        f"- Status: **{payload['status'].upper()}**",
        f"- Criteria: `{payload['criteria_passed']}/{payload['criteria_total']}`",
        f"- Failure class: `{payload['failure_classification']['failure_class']}`",
        "",
        "## Claim Boundary",
        "",
        payload["claim_boundary"],
        "",
        "## Aggregate Probe Summary",
        "",
        "| Model / Probe | Rank | Geomean MSE mean | Geomean NMSE mean |",
        "| --- | ---: | ---: | ---: |",
    ]
    for row in payload["aggregate_summary"]:
        lines.append(
            f"| {row['model']} | {row['rank_by_geomean_mse']} | {row['geomean_mse_mean']} | {row['geomean_nmse_mean']} |"
        )
    lines.extend(
        [
            "",
            "## Failure Classification",
            "",
            f"- Class: `{payload['failure_classification']['failure_class']}`",
            f"- Raw CRA geomean MSE: `{payload['failure_classification']['raw_cra_geomean_mse']}`",
            f"- State-probe geomean MSE: `{payload['failure_classification']['state_probe_geomean_mse']}`",
            f"- State+lag geomean MSE: `{payload['failure_classification']['state_plus_lag_geomean_mse']}`",
            f"- State improvement over raw: `{payload['failure_classification']['state_improvement_over_raw']}`",
            f"- State vs shuffled-control advantage: `{payload['failure_classification']['state_vs_shuffled_control_advantage']}`",
            f"- Recommendation: {payload['failure_classification']['recommendation']}",
            "",
            "## Interpretation Rule",
            "",
            "- This tier diagnoses the Tier 7.0 gap; it does not tune CRA.",
            "- Diagnostic ridge probes are not promoted mechanisms.",
            "- No benchmark migration to hardware is justified until a repair tier passes.",
            "",
        ]
    )
    (output_dir / "tier7_0b_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    tasks = parse_csv(args.tasks)
    seeds = parse_seeds(args)
    started = time.perf_counter()
    all_rows: list[dict[str, Any]] = []
    all_timeseries: list[dict[str, Any]] = []
    trace_diagnostics: list[dict[str, Any]] = []
    feature_rows: list[dict[str, Any]] = []

    for seed in seeds:
        for task_name in tasks:
            task = build_task(task_name, args.length, seed, args.horizon)
            trace = collect_cra_trace(task, seed=seed, args=args)
            trace_diagnostics.append({"task": task_name, "seed": seed, **trace.diagnostics})
            feature_rows.append(
                {
                    "task": task_name,
                    "seed": int(seed),
                    "feature_count": int(trace.features.shape[1]),
                    "feature_names": ",".join(trace.feature_names),
                    "capture_steps": int(trace.features.shape[0]),
                    "train_end": int(trace.train_end),
                }
            )
            rows, timeseries_rows = run_trace_probes(trace, args=args)
            all_rows.extend(rows)
            all_timeseries.extend(timeseries_rows)

    models = sorted({row["model"] for row in all_rows})
    summary_rows, aggregate_rows, aggregate_summary = summarize_rows(all_rows, tasks, models, seeds)
    failure_classification = classify_failure(aggregate_summary)
    criteria = [
        criterion("runner revision current", RUNNER_REVISION, "expected current source", RUNNER_REVISION.endswith("_0001")),
        criterion("all task names known", tasks, "subset of Tier 7.0 tasks", all(t in {"mackey_glass", "lorenz", "narma10"} for t in tasks)),
        criterion("all probes completed", f"{sum(r['status'] == 'pass' for r in all_rows)}/{len(all_rows)}", "all pass", all(r["status"] == "pass" for r in all_rows)),
        criterion("pre-learning capture documented", "pre_current_target_learning", "present", all("pre_current_target_learning" in row.get("capture_timing", "") for row in all_timeseries[: min(10, len(all_timeseries))]) if all_timeseries else True),
        criterion("feature rows complete", len(feature_rows), f"== {len(tasks) * len(seeds)}", len(feature_rows) == len(tasks) * len(seeds)),
        criterion("aggregate rows complete", len(aggregate_rows), f"== {len(models) * len(seeds)}", len(aggregate_rows) == len(models) * len(seeds)),
        criterion("failure class selected", failure_classification["failure_class"], "non-empty", bool(failure_classification["failure_class"])),
        criterion("shuffled control present", "cra_internal_state_shuffled_target_control" in models, "== true", "cra_internal_state_shuffled_target_control" in models),
        criterion("raw CRA probe present", "cra_online_raw" in models, "== true", "cra_online_raw" in models),
        criterion("state probe present", "cra_internal_state_ridge_probe" in models, "== true", "cra_internal_state_ridge_probe" in models),
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
        "train_fraction": float(args.train_fraction),
        "runtime_seconds": time.perf_counter() - started,
        "summary_rows": summary_rows,
        "aggregate_rows": aggregate_rows,
        "aggregate_summary": aggregate_summary,
        "failure_classification": failure_classification,
        "summary": failure_classification,
        "trace_diagnostics": trace_diagnostics,
        "feature_rows": feature_rows,
        "run_rows": all_rows,
        "fairness_contract": {
            "tier": TIER,
            "source_tier": "Tier 7.0",
            "same_tasks_and_split": True,
            "capture_timing": "adapter.evaluate callback before current target learning",
            "no_future_leakage": [
                "ridge probes fit only on train prefix",
                "features captured before current target updates CRA state",
                "same chronological stream generation as Tier 7.0",
            ],
            "nonclaims": [
                "not hardware evidence",
                "not a tuning run",
                "not a promoted mechanism",
                "not a new baseline freeze",
            ],
        },
        "claim_boundary": (
            "Tier 7.0b is software diagnostic evidence only. It localizes the "
            "Tier 7.0 continuous-regression benchmark gap using leakage-safe "
            "readout/state probes. It is not a tuning run, not a promoted "
            "mechanism, not hardware evidence, and not a new baseline freeze."
        ),
    }
    write_json(output_dir / "tier7_0b_results.json", payload)
    write_json(output_dir / "tier7_0b_fairness_contract.json", payload["fairness_contract"])
    write_csv(
        output_dir / "tier7_0b_summary.csv",
        summary_rows,
        [
            "task",
            "model",
            "status",
            "seed_count",
            "mse_mean",
            "mse_median",
            "mse_std",
            "mse_worst",
            "nmse_mean",
            "tail_mse_mean",
            "test_corr_mean",
        ],
    )
    write_csv(
        output_dir / "tier7_0b_aggregate.csv",
        aggregate_rows,
        ["task", "model", "seed", "status", "geomean_mse", "geomean_nmse"],
    )
    write_csv(
        output_dir / "tier7_0b_probe_timeseries.csv",
        all_timeseries,
        ["task", "seed", "model", "step", "split", "observed", "target", "prediction", "squared_error", "capture_timing"],
    )
    write_csv(
        output_dir / "tier7_0b_feature_inventory.csv",
        feature_rows,
        ["task", "seed", "feature_count", "feature_names", "capture_steps", "train_end"],
    )
    write_report(output_dir, payload)
    write_json(
        OUTPUT_ROOT / "tier7_0b_latest_manifest.json",
        {
            "tier": TIER,
            "runner_revision": RUNNER_REVISION,
            "generated_at_utc": payload["generated_at_utc"],
            "status": payload["status"],
            "manifest": str(output_dir / "tier7_0b_results.json"),
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
    parser.add_argument("--train-fraction", type=float, default=0.65)
    parser.add_argument("--history", type=int, default=12)
    parser.add_argument("--ridge", type=float, default=1e-3)
    parser.add_argument("--backend", default="mock")
    parser.add_argument("--cra-population-size", type=int, default=8)
    parser.add_argument("--cra-readout-lr", type=float, default=0.20)
    parser.add_argument("--cra-delayed-lr", type=float, default=0.20)
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
                "failure_class": payload["failure_classification"]["failure_class"],
                "output_dir": str(args.output_dir),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
