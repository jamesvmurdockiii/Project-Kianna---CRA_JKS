#!/usr/bin/env python3
"""Tier 5.45a — Healthy-NEST Rebaseline Scoring Gate.

Scores the locked Tier 5.45 contract on the real NEST organism path and keeps
the decision bounded: a pass means the scoring gate completed, not that a new
mechanism or baseline is automatically promoted.
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
from collections import defaultdict
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

from coral_reef_spinnaker import Observation, Organism, ReefConfig  # noqa: E402
from coral_reef_spinnaker.signals import ConsequenceSignal  # noqa: E402
from tier2_learning import end_backend, load_backend, setup_backend  # noqa: E402
from tier7_0_standard_dynamical_benchmarks import (  # noqa: E402
    EchoStateNetworkModel,
    OnlineLMSModel,
    PersistenceModel,
    RidgeLagModel,
    SequenceTask,
    chronological_split,
    parse_csv,
    parse_seeds,
    zscore_from_train,
)
from tier7_7z_r1_standardized_benchmark import compute_features, ridge  # noqa: E402


TIER = "Tier 5.45a — Healthy-NEST Rebaseline Scoring Gate"
RUNNER_REVISION = "tier5_45a_healthy_nest_rebaseline_scoring_20260515_0002"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier5_45a_20260515_healthy_nest_rebaseline_scoring"
CONTRACT_545 = CONTROLLED / "tier5_45_20260514_healthy_nest_rebaseline_contract" / "tier5_45_results.json"

EXPERIMENTAL_FLAGS = [
    "enable_neural_heritability",
    "enable_stream_specialization",
    "enable_variable_allocation",
    "enable_task_fitness_selection",
    "enable_operator_diversity",
    "enable_synaptic_heritability",
    "enable_niche_pressure",
    "enable_signal_transport",
    "enable_energy_economy",
    "enable_maturation",
    "enable_vector_readout",
    "enable_alignment_pressure",
    "enable_task_coupled_selection",
    "enable_causal_credit_selection",
    "enable_cross_polyp_coupling",
]

DEFAULT_TASKS = "sine,mackey_glass,lorenz,narma10"
DEFAULT_SEEDS = "42,43,44"
DEFAULT_CONDITIONS = "all"
DEFAULT_STEPS = 2000
DEFAULT_HORIZON = 8
DEFAULT_RUNTIME_MS_PER_STEP = 100.0


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
        out = float(value)
        return None if not math.isfinite(out) else out
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_rows(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = []
        for row in rows:
            for key in row:
                if key not in fieldnames:
                    fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json_safe(row.get(key, "")) for key in fieldnames})


def criterion(name: str, value: Any, rule: str, passed: bool, note: str = "") -> dict[str, Any]:
    return {
        "name": name,
        "criterion": name,
        "value": json_safe(value),
        "rule": rule,
        "passed": bool(passed),
        "note": note,
    }


def finite_geomean(values: list[float | None]) -> float | None:
    clean = [float(v) for v in values if v is not None and math.isfinite(float(v)) and float(v) > 0.0]
    if not clean:
        return None
    return float(math.exp(sum(math.log(v) for v in clean) / len(clean)))


def summarize(values: list[float | None]) -> dict[str, Any]:
    clean = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    if not clean:
        return {"n": 0, "mean": None, "median": None, "std": None, "min": None, "max": None}
    return {
        "n": len(clean),
        "mean": float(np.mean(clean)),
        "median": float(np.median(clean)),
        "std": float(np.std(clean, ddof=1)) if len(clean) > 1 else 0.0,
        "min": float(np.min(clean)),
        "max": float(np.max(clean)),
    }


def build_sine_task(length: int, seed: int, horizon: int) -> SequenceTask:
    rng = np.random.default_rng(seed + 54501)
    warmup = 64
    total = length + horizon + warmup + 2
    x = np.linspace(0.0, 24.0 * math.pi, total)
    raw = np.sin(x) + 0.25 * np.sin(0.13 * x + 0.7) + rng.normal(0.0, 0.01, size=total)
    series = raw[warmup : warmup + length + horizon]
    observed_raw = series[:length]
    target_raw = series[horizon : horizon + length]
    train_end = chronological_split(length, 0.65)
    observed, obs_mu, obs_sd = zscore_from_train(observed_raw, train_end)
    target, tgt_mu, tgt_sd = zscore_from_train(target_raw, train_end)
    return SequenceTask(
        name="sine",
        display_name="Sine future prediction",
        observed=observed,
        target=target,
        train_end=train_end,
        horizon=horizon,
        metadata={"obs_mu": obs_mu, "obs_sd": obs_sd, "target_mu": tgt_mu, "target_sd": tgt_sd},
    )


def build_task(name: str, length: int, seed: int, horizon: int) -> SequenceTask:
    if name == "sine":
        return build_sine_task(length, seed, horizon)
    from tier7_0_standard_dynamical_benchmarks import build_task as build_standard_task

    return build_standard_task(name, length, seed, horizon)


def score_predictions(task: SequenceTask, pred: np.ndarray) -> dict[str, float]:
    target = np.asarray(task.target, dtype=float)
    pred = np.asarray(pred, dtype=float)
    train_slice = slice(0, task.train_end)
    test_slice = slice(task.train_end, len(target))
    tail_start = task.train_end + max(1, int(0.75 * (len(target) - task.train_end)))
    train_err = pred[train_slice] - target[train_slice]
    test_err = pred[test_slice] - target[test_slice]
    tail_err = pred[tail_start:] - target[tail_start:]
    denom = float(np.var(target[test_slice]))
    if denom < 1e-12:
        denom = 1.0
    corr = 0.0
    if len(pred[test_slice]) > 2 and float(np.std(pred[test_slice])) > 1e-12 and float(np.std(target[test_slice])) > 1e-12:
        corr = float(np.corrcoef(pred[test_slice], target[test_slice])[0, 1])
    return {
        "train_mse": float(np.mean(train_err**2)),
        "mse": float(np.mean(test_err**2)),
        "nmse": float(np.mean(test_err**2) / denom),
        "tail_mse": float(np.mean(tail_err**2)),
        "test_correlation": corr,
    }


def participation_ratio(vectors: list[list[float]], train_end: int) -> dict[str, Any]:
    if len(vectors) < max(8, train_end + 4):
        return {"participation_ratio": None, "active_channels": 0, "rank95": None}
    width = max(len(v) for v in vectors)
    arr = np.asarray([list(v) + [0.0] * (width - len(v)) for v in vectors], dtype=float)
    seg = arr[train_end:]
    if seg.shape[0] < 4 or seg.shape[1] < 2:
        return {"participation_ratio": None, "active_channels": 0, "rank95": None}
    active = np.sum(np.abs(seg), axis=0) > 1e-12
    centered = seg[:, active] - np.mean(seg[:, active], axis=0, keepdims=True)
    if centered.shape[1] < 2:
        return {"participation_ratio": 1.0 if centered.shape[1] == 1 else None, "active_channels": int(centered.shape[1]), "rank95": 1}
    cov = centered.T @ centered / max(1, centered.shape[0] - 1)
    eig = np.sort(np.maximum(np.linalg.eigvalsh(cov), 0.0))[::-1]
    total = float(np.sum(eig))
    total_sq = float(np.sum(eig * eig))
    pr = float((total * total) / total_sq) if total_sq > 1e-18 else None
    rank95 = None
    if total > 1e-18:
        rank95 = int(np.searchsorted(np.cumsum(eig) / total, 0.95) + 1)
    return {"participation_ratio": pr, "active_channels": int(centered.shape[1]), "rank95": rank95}


class RegressionAdapter:
    task_name = "tier5_45a_regression"

    def encode(self, observation: Observation, n_channels: int) -> np.ndarray:
        out = np.zeros(max(1, int(n_channels)), dtype=float)
        x = float(np.asarray(observation.x, dtype=float).reshape(-1)[0])
        features = [
            x,
            abs(x),
            x * x,
            math.sin(x),
            math.cos(x),
            1.0 if x >= 0.0 else -1.0,
            float(observation.metadata.get("lag1", 0.0)),
            float(observation.metadata.get("lag2", 0.0)),
        ]
        for i, value in enumerate(features[: out.size]):
            out[i] = float(value)
        return out

    def evaluate(self, prediction: float, observation: Observation, dt_seconds: float) -> ConsequenceSignal:
        del dt_seconds
        target = 0.0 if observation.target is None else float(observation.target)
        err = target - float(prediction)
        return ConsequenceSignal(
            immediate_signal=target,
            horizon_signal=target,
            actual_value=target,
            prediction=float(prediction),
            direction_correct=bool((prediction >= 0.0) == (target >= 0.0)),
            raw_dopamine=float(np.tanh(err)),
            task_metrics={"regression_error": err, "squared_error": err * err},
            metadata={"adapter": "tier5_45a_regression", "stream_id": observation.stream_id},
        )


def condition_overrides(condition: str) -> dict[str, bool]:
    if condition == "organism_defaults_experimental_off":
        return {flag: False for flag in EXPERIMENTAL_FLAGS}
    if condition == "full_opt_in_stack":
        return {flag: True for flag in EXPERIMENTAL_FLAGS}
    if condition in EXPERIMENTAL_FLAGS:
        return {flag: flag == condition for flag in EXPERIMENTAL_FLAGS}
    raise ValueError(f"unknown organism condition {condition!r}")


def organism_condition_names(raw: str) -> list[str]:
    if raw == "all":
        return ["organism_defaults_experimental_off", *EXPERIMENTAL_FLAGS, "full_opt_in_stack"]
    aliases = {
        "defaults": "organism_defaults_experimental_off",
        "full": "full_opt_in_stack",
    }
    names = []
    for item in parse_csv(raw):
        name = aliases.get(item, item)
        if name.startswith("single:"):
            name = name.split(":", 1)[1]
        names.append(name)
    return names


def apply_condition_config(cfg: ReefConfig, condition: str, args: argparse.Namespace) -> dict[str, bool]:
    overrides = condition_overrides(condition)
    cfg.lifecycle.initial_population = int(args.initial_population)
    cfg.lifecycle.max_population_hard = int(args.max_population)
    cfg.lifecycle.max_population_from_memory = False
    cfg.lifecycle.enable_reproduction = bool(args.enable_lifecycle)
    cfg.lifecycle.enable_apoptosis = bool(args.enable_lifecycle)
    cfg.measurement.stream_history_maxlen = max(int(args.steps) + 32, 512)
    cfg.learning.readout_learning_rate = float(args.readout_lr)
    cfg.learning.delayed_readout_learning_rate = float(args.delayed_readout_lr)
    cfg.learning.evaluation_horizon_bars = int(args.horizon)
    cfg.spinnaker.sync_interval_steps = int(args.sync_interval_steps)
    cfg.spinnaker.runtime_ms_per_step = float(args.runtime_ms_per_step)
    cfg.spinnaker.n_input_per_polyp = 8
    cfg.spinnaker.per_polyp_input_diversity = True
    for flag, enabled in overrides.items():
        setattr(cfg.lifecycle, flag, bool(enabled))
    return overrides


def score_organism_condition(task: SequenceTask, condition: str, seed: int, args: argparse.Namespace) -> dict[str, Any]:
    random.seed(seed)
    np.random.seed(seed)
    sim, backend_name = load_backend(args.backend)
    setup_backend(sim, backend_name)
    cfg = ReefConfig.default()
    cfg.seed = int(seed)
    overrides = apply_condition_config(cfg, condition, args)
    organism = Organism(cfg, sim, use_default_trading_bridge=False)
    adapter = RegressionAdapter()
    predictions: list[float] = []
    per_neuron: list[list[int]] = []
    population_history: list[int] = []
    metric_rows: list[dict[str, Any]] = []
    births_total = 0
    deaths_total = 0
    start = time.perf_counter()
    status = "pass"
    failure_reason = ""
    diagnostics: dict[str, Any] = {}
    try:
        organism.initialize(stream_keys=[task.name])
        observed = np.asarray(task.observed, dtype=float)
        runtime_dt_seconds = float(args.runtime_ms_per_step) / 1000.0
        for step, (obs, target) in enumerate(zip(task.observed, task.target)):
            observation = Observation(
                stream_id=task.name,
                x=np.asarray([float(obs)], dtype=float),
                target=float(target),
                timestamp=float(step),
                metadata={
                    "tier": "5.45a",
                    "task": task.name,
                    "condition": condition,
                    "step": int(step),
                    "lag1": float(observed[step - 1]) if step >= 1 else 0.0,
                    "lag2": float(observed[step - 2]) if step >= 2 else 0.0,
                },
            )
            metrics = organism.train_adapter_step(adapter, observation, dt_seconds=runtime_dt_seconds)
            predictions.append(float(metrics.colony_prediction))
            per_neuron.append(organism.get_per_neuron_spike_vector())
            population_history.append(int(metrics.n_alive))
            births_total += int(metrics.births_this_step or 0)
            deaths_total += int(metrics.deaths_this_step or 0)
            if step in {0, task.train_end, len(task.target) - 1}:
                metric_rows.append(metrics.to_dict())
        diagnostics = organism.backend_diagnostics()
    except Exception as exc:
        status = "fail"
        failure_reason = repr(exc)
        try:
            diagnostics = organism.backend_diagnostics()
        except Exception:
            diagnostics = {"backend": backend_name}
    finally:
        try:
            organism.shutdown()
        finally:
            end_backend(sim)

    if status == "pass":
        pred = np.asarray(predictions, dtype=float)
        scores = score_predictions(task, pred)
        pr = participation_ratio(per_neuron, task.train_end)
    else:
        scores = {"train_mse": None, "mse": None, "nmse": None, "tail_mse": None, "test_correlation": None}
        pr = {"participation_ratio": None, "active_channels": 0, "rank95": None}
    return {
        "model": condition,
        "model_family": "nest_organism",
        "task": task.name,
        "seed": int(seed),
        "status": status,
        **scores,
        "runtime_seconds": time.perf_counter() - start,
        "per_neuron_participation_ratio": pr["participation_ratio"],
        "rank95_or_effective_rank": pr["rank95"],
        "active_channels": pr["active_channels"],
        "population_min": min(population_history) if population_history else None,
        "population_max": max(population_history) if population_history else None,
        "population_final": population_history[-1] if population_history else None,
        "birth_death_counts": {
            "births": int(births_total),
            "deaths": int(deaths_total),
        },
        "condition_overrides": overrides,
        "diagnostics": diagnostics,
        "synthetic_fallbacks": int(diagnostics.get("synthetic_fallbacks", 0) or 0),
        "sim_run_failures": int(diagnostics.get("sim_run_failures", 0) or 0),
        "summary_read_failures": int(diagnostics.get("summary_read_failures", 0) or 0),
        "failure_reason": failure_reason,
    }


def score_v26_reference(task: SequenceTask, seed: int, hidden: int) -> dict[str, Any]:
    features, _values = compute_features(task.observed, seed, hidden, 0.0, 1.0, 0.3)
    weights = ridge(features[: task.train_end], task.target[: task.train_end], alpha=1.0)
    pred = features @ weights
    scores = score_predictions(task, pred)
    hidden_cols = list(range(features.shape[1] - hidden, features.shape[1]))
    pr = participation_ratio(features[:, hidden_cols].tolist(), task.train_end)
    return {
        "model": "v2_6_predictive_reference",
        "model_family": "software_reference",
        "task": task.name,
        "seed": int(seed),
        "status": "pass",
        **scores,
        "runtime_seconds": 0.0,
        "per_neuron_participation_ratio": pr["participation_ratio"],
        "rank95_or_effective_rank": pr["rank95"],
        "active_channels": pr["active_channels"],
        "synthetic_fallbacks": 0,
        "sim_run_failures": 0,
        "summary_read_failures": 0,
        "failure_reason": "",
    }


def score_sequence_baseline(task: SequenceTask, model_name: str, seed: int, args: argparse.Namespace) -> dict[str, Any]:
    start = time.perf_counter()
    if model_name == "persistence_baseline":
        model = PersistenceModel()
    elif model_name == "online_linear_or_lag_ridge":
        model = RidgeLagModel(history=args.history, ridge=args.ridge)
    elif model_name == "esn_or_random_reservoir":
        model = EchoStateNetworkModel(
            seed=seed,
            units=args.esn_units,
            spectral_radius=args.esn_spectral_radius,
            input_scale=args.esn_input_scale,
            ridge=args.ridge,
        )
    elif model_name == "online_lms":
        model = OnlineLMSModel(history=args.history, lr=args.online_lr, ridge=args.online_decay)
    else:
        raise ValueError(f"unknown sequence baseline {model_name}")
    model.fit(task)
    pred, diag = model.predict_all(task)
    scores = score_predictions(task, pred)
    return {
        "model": model_name,
        "model_family": "external_baseline",
        "task": task.name,
        "seed": int(seed),
        "status": "pass",
        **scores,
        "runtime_seconds": time.perf_counter() - start,
        "per_neuron_participation_ratio": None,
        "rank95_or_effective_rank": None,
        "active_channels": None,
        "diagnostics": diag,
        "synthetic_fallbacks": 0,
        "sim_run_failures": 0,
        "summary_read_failures": 0,
        "failure_reason": "",
    }


def model_task_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    by_key: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_key[(str(row["model"]), str(row["task"]))].append(row)
    for (model, task), group in sorted(by_key.items()):
        passed = [r for r in group if r.get("status") == "pass"]
        out.append({
            "model": model,
            "task": task,
            "status": "pass" if len(passed) == len(group) and group else "fail",
            "seed_count": len(passed),
            "mse_mean": summarize([r.get("mse") for r in passed])["mean"],
            "mse_median": summarize([r.get("mse") for r in passed])["median"],
            "mse_std": summarize([r.get("mse") for r in passed])["std"],
            "mse_worst": summarize([r.get("mse") for r in passed])["max"],
            "nmse_mean": summarize([r.get("nmse") for r in passed])["mean"],
            "tail_mse_mean": summarize([r.get("tail_mse") for r in passed])["mean"],
            "test_correlation_mean": summarize([r.get("test_correlation") for r in passed])["mean"],
            "pr_mean": summarize([r.get("per_neuron_participation_ratio") for r in passed])["mean"],
            "rank95_mean": summarize([r.get("rank95_or_effective_rank") for r in passed])["mean"],
            "synthetic_fallbacks_sum": int(sum(int(r.get("synthetic_fallbacks", 0) or 0) for r in group)),
            "sim_run_failures_sum": int(sum(int(r.get("sim_run_failures", 0) or 0) for r in group)),
            "summary_read_failures_sum": int(sum(int(r.get("summary_read_failures", 0) or 0) for r in group)),
            "runtime_seconds_mean": summarize([r.get("runtime_seconds") for r in passed])["mean"],
        })
    return out


def aggregate_by_model(rows: list[dict[str, Any]], tasks: list[str], seeds: list[int]) -> list[dict[str, Any]]:
    models = sorted({str(r["model"]) for r in rows})
    out: list[dict[str, Any]] = []
    for model in models:
        model_rows = [r for r in rows if r["model"] == model and r.get("status") == "pass"]
        by_seed: list[dict[str, Any]] = []
        for seed in seeds:
            seed_rows = [r for r in model_rows if int(r["seed"]) == int(seed)]
            by_task = {str(r["task"]): r for r in seed_rows}
            values = [by_task[t]["mse"] for t in tasks if t in by_task and by_task[t].get("mse") is not None]
            by_seed.append({
                "model": model,
                "seed": int(seed),
                "status": "pass" if len(values) == len(tasks) else "fail",
                "geomean_mse": finite_geomean(values),
                "task_count": len(values),
            })
        passed = [r for r in by_seed if r["status"] == "pass" and r["geomean_mse"] is not None]
        out.append({
            "model": model,
            "status": "pass" if passed else "fail",
            "seed_count": len(passed),
            "geomean_mse_mean": summarize([r["geomean_mse"] for r in passed])["mean"],
            "geomean_mse_median": summarize([r["geomean_mse"] for r in passed])["median"],
            "geomean_mse_worst": summarize([r["geomean_mse"] for r in passed])["max"],
            "per_seed": by_seed,
        })
    pass_rows = [r for r in out if r["status"] == "pass" and r["geomean_mse_mean"] is not None]
    pass_rows.sort(key=lambda r: float(r["geomean_mse_mean"]))
    ranks = {r["model"]: idx + 1 for idx, r in enumerate(pass_rows)}
    for row in out:
        row["rank_by_geomean_mse"] = ranks.get(row["model"])
    return sorted(out, key=lambda r: (r["rank_by_geomean_mse"] or 10_000, r["model"]))


def task_regression_ok(candidate: str, reference: str, task_summary: list[dict[str, Any]], max_regression: float) -> bool:
    for row in task_summary:
        if row["model"] != candidate or row.get("mse_mean") is None:
            continue
        ref = next((r for r in task_summary if r["model"] == reference and r["task"] == row["task"]), None)
        if not ref or ref.get("mse_mean") is None:
            return False
        if float(row["mse_mean"]) > float(ref["mse_mean"]) * (1.0 + max_regression):
            return False
    return True


def decide_mechanisms(
    aggregate: list[dict[str, Any]],
    task_summary: list[dict[str, Any]],
    args: argparse.Namespace,
) -> tuple[str, list[dict[str, Any]]]:
    by_model = {r["model"]: r for r in aggregate}
    v26 = by_model.get("v2_6_predictive_reference", {})
    default = by_model.get("organism_defaults_experimental_off", {})
    v26_mse = v26.get("geomean_mse_mean")
    default_mse = default.get("geomean_mse_mean")
    decisions: list[dict[str, Any]] = []
    predictive_candidates: list[str] = []
    organism_candidates: list[str] = []
    substrate_candidates: list[str] = []
    pr_by_model = {
        model: summarize([r.get("pr_mean") for r in task_summary if r["model"] == model])["mean"]
        for model in {str(r["model"]) for r in task_summary}
    }
    for row in aggregate:
        model = str(row["model"])
        if model in {"v2_6_predictive_reference", "persistence_baseline", "online_linear_or_lag_ridge", "esn_or_random_reservoir", "online_lms"}:
            continue
        mse = row.get("geomean_mse_mean")
        task_ok_v26 = bool(v26_mse and task_regression_ok(model, "v2_6_predictive_reference", task_summary, args.max_task_regression))
        task_ok_default = bool(default_mse and task_regression_ok(model, "organism_defaults_experimental_off", task_summary, args.max_task_regression))
        delta_vs_v26 = None if mse is None or v26_mse in (None, 0) else (float(v26_mse) - float(mse)) / float(v26_mse)
        delta_vs_default = None if mse is None or default_mse in (None, 0) else (float(default_mse) - float(mse)) / float(default_mse)
        pr_mean = pr_by_model.get(model)
        default_pr = pr_by_model.get("organism_defaults_experimental_off")
        pr_lift = None if pr_mean is None or not default_pr else (float(pr_mean) - float(default_pr)) / max(1e-9, float(default_pr))
        predictive = bool(delta_vs_v26 is not None and delta_vs_v26 >= args.min_predictive_improvement and task_ok_v26)
        organism = bool(delta_vs_default is not None and delta_vs_default >= args.min_predictive_improvement and task_ok_default)
        substrate = bool(not predictive and not organism and pr_lift is not None and pr_lift >= args.min_pr_lift)
        if predictive:
            predictive_candidates.append(model)
        elif organism:
            organism_candidates.append(model)
        elif substrate:
            substrate_candidates.append(model)
        decisions.append({
            "model": model,
            "geomean_mse_mean": mse,
            "delta_mse_vs_v2_6": delta_vs_v26,
            "delta_mse_vs_default": delta_vs_default,
            "task_regression_ok_vs_v2_6": task_ok_v26,
            "task_regression_ok_vs_default": task_ok_default,
            "pr_lift_vs_default_first_task": pr_lift,
            "decision": "predictive_baseline_candidate" if predictive else "organism_predictive_candidate" if organism else "substrate_only_candidate" if substrate else "no_promotion",
        })
    if predictive_candidates:
        outcome = "predictive_baseline_candidate"
    elif organism_candidates:
        outcome = "organism_predictive_candidate"
    elif substrate_candidates:
        outcome = "substrate_only_candidate"
    elif by_model.get("full_opt_in_stack", {}).get("rank_by_geomean_mse") == 1:
        outcome = "full_stack_interaction_only"
    else:
        outcome = "no_promotion_confirmed"
    return outcome, decisions


def write_report(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        f"# {TIER}",
        "",
        f"- Generated: `{payload['generated_at_utc']}`",
        f"- Status: **{payload['status'].upper()}**",
        f"- Outcome: `{payload['outcome']}`",
        f"- Criteria: `{payload['criteria_passed']}/{payload['criteria_total']}`",
        f"- Runner revision: `{RUNNER_REVISION}`",
        "",
        "## Claim Boundary",
        "",
        payload["claim_boundary"],
        "",
        "## Aggregate Model Ranking",
        "",
        "| Rank | Model | Status | Seed count | Geomean MSE mean |",
        "| ---: | --- | --- | ---: | ---: |",
    ]
    for row in payload["aggregate_summary"]:
        lines.append(f"| {row.get('rank_by_geomean_mse')} | {row['model']} | {row['status']} | {row['seed_count']} | {row.get('geomean_mse_mean')} |")
    lines.extend(["", "## Mechanism Decisions", "", "| Model | Decision | Δ vs v2.6 | Δ vs default |", "| --- | --- | ---: | ---: |"])
    for row in payload["mechanism_decisions"]:
        lines.append(f"| {row['model']} | `{row['decision']}` | {row.get('delta_mse_vs_v2_6')} | {row.get('delta_mse_vs_default')} |")
    lines.extend(["", "## Criteria", "", "| Criterion | Value | Rule | Pass |", "| --- | --- | --- | --- |"])
    for c in payload["criteria"]:
        lines.append(f"| {c['name']} | `{c['value']}` | `{c['rule']}` | {'yes' if c['passed'] else 'no'} |")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def reference_model_names() -> list[str]:
    return [
        "v2_6_predictive_reference",
        "persistence_baseline",
        "online_linear_or_lag_ridge",
        "esn_or_random_reservoir",
    ]


def parse_csv_value(value: str) -> Any:
    if value == "":
        return None
    for caster in (int, float):
        try:
            return caster(value)
        except (TypeError, ValueError):
            pass
    return value


def read_seed_run_rows(path_or_dir: Path) -> list[dict[str, Any]]:
    path = path_or_dir
    if path.is_dir():
        path = path / "tier5_45a_seed_runs.csv"
    rows: list[dict[str, Any]] = []
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for raw in reader:
            row = {key: parse_csv_value(value) for key, value in raw.items()}
            rows.append(row)
    return rows


def write_scoring_bundle(
    *,
    output_dir: Path,
    rows: list[dict[str, Any]],
    tasks: list[str],
    seeds: list[int],
    conditions: list[str],
    args: argparse.Namespace,
    started: float,
    mode: str,
) -> dict[str, Any]:
    reference_models = reference_model_names()
    task_summary = model_task_summary(rows)
    aggregate_summary = aggregate_by_model(rows, tasks, seeds)
    outcome, decisions = decide_mechanisms(aggregate_summary, task_summary, args)
    organism_rows = [r for r in rows if r.get("model_family") == "nest_organism"]
    fallback_sum = int(sum(int(r.get("synthetic_fallbacks", 0) or 0) for r in organism_rows))
    sim_fail_sum = int(sum(int(r.get("sim_run_failures", 0) or 0) for r in organism_rows))
    read_fail_sum = int(sum(int(r.get("summary_read_failures", 0) or 0) for r in organism_rows))
    required_models = set(reference_models + conditions)
    scored_models = {str(r["model"]) for r in rows if r.get("status") == "pass"}
    expected_cells = len(tasks) * len(seeds) * len(required_models)
    unique_cells = {
        (str(r.get("model")), str(r.get("task")), int(r.get("seed")))
        for r in rows
        if r.get("model") in required_models and r.get("task") in tasks and r.get("seed") in seeds
    }
    criteria = [
        criterion("Tier 5.45 contract exists", CONTRACT_545.exists(), "true", CONTRACT_545.exists()),
        criterion("all requested tasks known", tasks, "subset of sine/MG/Lorenz/NARMA10", all(t in {"sine", "mackey_glass", "lorenz", "narma10"} for t in tasks)),
        criterion("all required models scored", sorted(required_models - scored_models), "[]", not (required_models - scored_models)),
        criterion("expected unique model/task/seed cells", len(unique_cells), f"== {expected_cells}", len(unique_cells) == expected_cells),
        criterion("organism synthetic fallbacks zero", fallback_sum, "== 0", fallback_sum == 0),
        criterion("organism sim.run failures zero", sim_fail_sum, "== 0", sim_fail_sum == 0),
        criterion("organism summary read failures zero", read_fail_sum, "== 0", read_fail_sum == 0),
        criterion("outcome classified", outcome, "non-empty", bool(outcome)),
        criterion("no automatic baseline freeze", False, "false", True),
        criterion("no hardware/native claim", False, "false", True),
    ]
    status = "pass" if all(c["passed"] for c in criteria) else "fail"
    payload = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "status": status,
        "outcome": "blocked_by_fallback_or_backend_instability" if status == "fail" and (fallback_sum or sim_fail_sum or read_fail_sum) else outcome,
        "criteria": criteria,
        "criteria_passed": sum(1 for c in criteria if c["passed"]),
        "criteria_total": len(criteria),
        "output_dir": str(output_dir),
        "mode": mode,
        "tasks": tasks,
        "seeds": seeds,
        "conditions": conditions,
        "reference_models": reference_models,
        "steps": int(args.steps),
        "runtime_seconds": time.perf_counter() - started,
        "aggregate_summary": aggregate_summary,
        "task_summary": task_summary,
        "mechanism_decisions": decisions,
        "backend_diagnostics": {
            "synthetic_fallbacks_sum": fallback_sum,
            "sim_run_failures_sum": sim_fail_sum,
            "summary_read_failures_sum": read_fail_sum,
        },
        "claim_boundary": (
            "Software/NEST scoring gate only. A pass means the post-cleanup "
            "healthy-NEST rebaseline was measured under the locked contract. "
            "It is not a hardware/native transfer, not an automatic mechanism "
            "promotion, not a baseline freeze, and not public superiority evidence."
        ),
        "next_gate": "Document promote/park decision; run a promotion/regression gate only if a candidate earns it.",
    }
    write_json(output_dir / "tier5_45a_results.json", payload)
    write_rows(output_dir / "tier5_45a_seed_runs.csv", rows)
    write_rows(output_dir / "tier5_45a_model_task_metrics.csv", task_summary)
    write_rows(output_dir / "tier5_45a_summary.csv", criteria)
    write_rows(output_dir / "tier5_45a_mechanism_decisions.csv", decisions)
    write_json(output_dir / "tier5_45a_backend_diagnostics.json", payload["backend_diagnostics"])
    write_report(output_dir / "tier5_45a_report.md", payload)
    write_json(
        output_dir / "tier5_45a_latest_manifest.json",
        {
            "tier": TIER,
            "runner_revision": RUNNER_REVISION,
            "generated_at_utc": payload["generated_at_utc"],
            "status": status,
            "outcome": payload["outcome"],
            "output_dir": str(output_dir),
            "artifacts": {
                "results_json": str(output_dir / "tier5_45a_results.json"),
                "report_md": str(output_dir / "tier5_45a_report.md"),
                "summary_csv": str(output_dir / "tier5_45a_summary.csv"),
                "seed_runs_csv": str(output_dir / "tier5_45a_seed_runs.csv"),
                "model_task_metrics_csv": str(output_dir / "tier5_45a_model_task_metrics.csv"),
                "mechanism_decisions_csv": str(output_dir / "tier5_45a_mechanism_decisions.csv"),
                "backend_diagnostics_json": str(output_dir / "tier5_45a_backend_diagnostics.json"),
            },
        },
    )
    return payload


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    tasks = [t.strip() for t in parse_csv(args.tasks) if t.strip()]
    seeds = sorted(set(parse_seeds(args)))
    conditions = organism_condition_names(args.conditions)
    started = time.perf_counter()
    rows: list[dict[str, Any]] = []

    for seed in seeds:
        for task_name in tasks:
            task = build_task(task_name, int(args.steps), seed, int(args.horizon))
            rows.append(score_v26_reference(task, seed, int(args.hidden)))
            rows.append(score_sequence_baseline(task, "persistence_baseline", seed, args))
            rows.append(score_sequence_baseline(task, "online_linear_or_lag_ridge", seed, args))
            rows.append(score_sequence_baseline(task, "esn_or_random_reservoir", seed, args))
            for condition in conditions:
                rows.append(score_organism_condition(task, condition, seed, args))

    return write_scoring_bundle(
        output_dir=output_dir,
        rows=rows,
        tasks=tasks,
        seeds=seeds,
        conditions=conditions,
        args=args,
        started=started,
        mode="direct",
    )


def run_merge(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    tasks = [t.strip() for t in parse_csv(args.tasks) if t.strip()]
    seeds = sorted(set(parse_seeds(args)))
    conditions = organism_condition_names(args.conditions)
    started = time.perf_counter()
    rows_by_cell: dict[tuple[str, str, int], dict[str, Any]] = {}
    for item in parse_csv(args.merge_input_dirs):
        for row in read_seed_run_rows(Path(item).expanduser().resolve()):
            try:
                key = (str(row["model"]), str(row["task"]), int(row["seed"]))
            except Exception:
                continue
            rows_by_cell.setdefault(key, row)
    return write_scoring_bundle(
        output_dir=output_dir,
        rows=list(rows_by_cell.values()),
        tasks=tasks,
        seeds=seeds,
        conditions=conditions,
        args=args,
        started=started,
        mode="merge",
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=TIER)
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    p.add_argument("--merge-input-dirs", default="")
    p.add_argument("--tasks", default=DEFAULT_TASKS)
    p.add_argument("--seeds", default=DEFAULT_SEEDS)
    p.add_argument("--conditions", default=DEFAULT_CONDITIONS)
    p.add_argument("--steps", type=int, default=DEFAULT_STEPS)
    p.add_argument("--horizon", type=int, default=DEFAULT_HORIZON)
    p.add_argument("--backend", default="nest")
    p.add_argument("--initial-population", type=int, default=8)
    p.add_argument("--max-population", type=int, default=32)
    p.add_argument("--enable-lifecycle", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--sync-interval-steps", type=int, default=0)
    p.add_argument("--runtime-ms-per-step", type=float, default=DEFAULT_RUNTIME_MS_PER_STEP)
    p.add_argument("--readout-lr", type=float, default=0.20)
    p.add_argument("--delayed-readout-lr", type=float, default=0.20)
    p.add_argument("--hidden", type=int, default=128)
    p.add_argument("--history", type=int, default=12)
    p.add_argument("--ridge", type=float, default=1e-3)
    p.add_argument("--online-lr", type=float, default=0.02)
    p.add_argument("--online-decay", type=float, default=1e-5)
    p.add_argument("--esn-units", type=int, default=64)
    p.add_argument("--esn-spectral-radius", type=float, default=0.9)
    p.add_argument("--esn-input-scale", type=float, default=0.5)
    p.add_argument("--min-predictive-improvement", type=float, default=0.05)
    p.add_argument("--max-task-regression", type=float, default=0.10)
    p.add_argument("--min-pr-lift", type=float, default=0.20)
    p.add_argument("--smoke", action="store_true", default=False)
    return p


def main() -> int:
    args = build_parser().parse_args()
    if args.smoke:
        args.output_dir = Path("/tmp/cra_tier5_45a_smoke")
        args.tasks = "sine"
        args.seeds = "42"
        args.conditions = "defaults,enable_vector_readout,full"
        args.steps = min(int(args.steps), 96)
        args.initial_population = min(int(args.initial_population), 4)
        args.max_population = min(int(args.max_population), 8)
        args.runtime_ms_per_step = 100.0
    payload = run_merge(args) if args.merge_input_dirs else run(args)
    print(json.dumps(json_safe({
        "status": payload["status"],
        "outcome": payload["outcome"],
        "criteria": f"{payload['criteria_passed']}/{payload['criteria_total']}",
        "output_dir": payload["output_dir"],
        "runtime_seconds": round(float(payload["runtime_seconds"]), 3),
    }), indent=2, sort_keys=True))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
