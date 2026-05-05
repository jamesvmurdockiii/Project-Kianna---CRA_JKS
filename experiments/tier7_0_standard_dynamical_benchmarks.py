#!/usr/bin/env python3
"""Tier 7.0 - Standard Dynamical Benchmark Suite.

This benchmark is a diagnostic gate, not an automatic promotion gate. It puts
CRA beside simple, traceable temporal baselines on three standard sequence
benchmarks:

* Mackey-Glass future prediction
* Lorenz future prediction
* NARMA10 nonlinear memory / system-identification

The suite is intentionally leakage-conservative:
  - train/test splits are chronological
  - normalization is fit on the training prefix only
  - prediction targets are future values
  - all rows record whether they are train or test
  - CRA is evaluated in online prequential mode and scored only on test rows

If CRA underperforms, the result is still useful: it tells us which next
mechanism should be tested, rather than encouraging blind tuning.
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
from typing import Any, Protocol

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


TIER = "Tier 7.0 - Standard Dynamical Benchmark Suite"
RUNNER_REVISION = "tier7_0_standard_dynamical_benchmarks_20260505_0001"
DEFAULT_OUTPUT_DIR = ROOT / "controlled_test_output" / "tier7_0_20260505_standard_dynamical_benchmarks"
DEFAULT_TASKS = "mackey_glass,lorenz,narma10"
DEFAULT_MODELS = "persistence,online_lms,ridge_lag,echo_state_network,cra_v2_1_online"


@dataclass(frozen=True)
class SequenceTask:
    name: str
    display_name: str
    observed: np.ndarray
    target: np.ndarray
    train_end: int
    horizon: int
    metadata: dict[str, Any]


@dataclass
class ModelResult:
    task: str
    model: str
    seed: int
    status: str
    mse: float | None
    nmse: float | None
    tail_mse: float | None
    train_mse: float | None
    runtime_seconds: float
    predictions: list[float]
    rows: list[dict[str, Any]]
    diagnostics: dict[str, Any]
    failure_reason: str = ""


class SequenceModel(Protocol):
    name: str

    def fit(self, task: SequenceTask) -> None:
        ...

    def predict_all(self, task: SequenceTask) -> tuple[np.ndarray, dict[str, Any]]:
        ...


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


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
        return None if not math.isfinite(f) else f
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def criterion(name: str, value: Any, rule: str, passed: bool, note: str = "") -> dict[str, Any]:
    return {"name": name, "value": json_safe(value), "rule": rule, "passed": bool(passed), "note": note}


def parse_csv(raw: str) -> list[str]:
    return [item.strip() for item in raw.replace(";", ",").split(",") if item.strip()]


def parse_seeds(args: argparse.Namespace) -> list[int]:
    if getattr(args, "seed_count", None) is not None:
        return [int(args.base_seed) + i for i in range(int(args.seed_count))]
    seeds = [int(item) for item in parse_csv(str(args.seeds))]
    if not seeds:
        return [42, 43, 44]
    return seeds


def chronological_split(length: int, train_fraction: float) -> int:
    if not 0.2 <= train_fraction <= 0.9:
        raise ValueError("train_fraction must be between 0.2 and 0.9")
    train_end = int(round(length * train_fraction))
    return max(32, min(length - 32, train_end))


def zscore_from_train(values: np.ndarray, train_end: int) -> tuple[np.ndarray, float, float]:
    train = np.asarray(values[:train_end], dtype=float)
    mu = float(np.mean(train))
    sd = float(np.std(train))
    if sd < 1e-9:
        sd = 1.0
    return (np.asarray(values, dtype=float) - mu) / sd, mu, sd


def mackey_glass_series(length: int, seed: int, *, horizon: int) -> SequenceTask:
    rng = np.random.default_rng(seed + 1001)
    tau = 17
    beta = 0.2
    gamma = 0.1
    n = 10
    dt = 1.0
    warmup = 300
    total = length + horizon + warmup + tau + 2
    x = np.ones(total, dtype=float) * 1.2
    x[: tau + 1] += rng.normal(0.0, 0.01, size=tau + 1)
    for t in range(tau, total - 1):
        delayed = x[t - tau]
        dx = beta * delayed / (1.0 + delayed**n) - gamma * x[t]
        x[t + 1] = x[t] + dt * dx + rng.normal(0.0, 0.0005)
    series = x[warmup : warmup + length + horizon]
    observed_raw = series[:length]
    target_raw = series[horizon : horizon + length]
    train_end = chronological_split(length, 0.65)
    observed, obs_mu, obs_sd = zscore_from_train(observed_raw, train_end)
    target, tgt_mu, tgt_sd = zscore_from_train(target_raw, train_end)
    return SequenceTask(
        name="mackey_glass",
        display_name="Mackey-Glass",
        observed=observed,
        target=target,
        train_end=train_end,
        horizon=horizon,
        metadata={"obs_mu": obs_mu, "obs_sd": obs_sd, "target_mu": tgt_mu, "target_sd": tgt_sd, "tau": tau},
    )


def lorenz_series(length: int, seed: int, *, horizon: int) -> SequenceTask:
    rng = np.random.default_rng(seed + 2002)
    dt = 0.01
    warmup = 1000
    total = length + horizon + warmup + 4
    sigma = 10.0
    rho = 28.0
    beta = 8.0 / 3.0
    state = np.zeros((total, 3), dtype=float)
    state[0] = np.asarray([1.0, 1.0, 1.0], dtype=float) + rng.normal(0.0, 0.01, size=3)

    def f(v: np.ndarray) -> np.ndarray:
        return np.asarray(
            [
                sigma * (v[1] - v[0]),
                v[0] * (rho - v[2]) - v[1],
                v[0] * v[1] - beta * v[2],
            ],
            dtype=float,
        )

    for t in range(total - 1):
        v = state[t]
        k1 = f(v)
        k2 = f(v + 0.5 * dt * k1)
        k3 = f(v + 0.5 * dt * k2)
        k4 = f(v + dt * k3)
        state[t + 1] = v + (dt / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)
    series = state[warmup : warmup + length + horizon, 0]
    observed_raw = series[:length]
    target_raw = series[horizon : horizon + length]
    train_end = chronological_split(length, 0.65)
    observed, obs_mu, obs_sd = zscore_from_train(observed_raw, train_end)
    target, tgt_mu, tgt_sd = zscore_from_train(target_raw, train_end)
    return SequenceTask(
        name="lorenz",
        display_name="Lorenz x(t)",
        observed=observed,
        target=target,
        train_end=train_end,
        horizon=horizon,
        metadata={"obs_mu": obs_mu, "obs_sd": obs_sd, "target_mu": tgt_mu, "target_sd": tgt_sd, "dt": dt},
    )


def narma10_series(length: int, seed: int, *, horizon: int) -> SequenceTask:
    del horizon  # NARMA10 standard target is the generated output at the next step.
    rng = np.random.default_rng(seed + 3003)
    warmup = 200
    total = length + warmup + 20
    u = rng.uniform(0.0, 0.5, size=total)
    y = np.zeros(total, dtype=float)
    for t in range(10, total - 1):
        y[t + 1] = (
            0.3 * y[t]
            + 0.05 * y[t] * np.sum(y[t - 9 : t + 1])
            + 1.5 * u[t - 9] * u[t]
            + 0.1
        )
    observed_raw = u[warmup : warmup + length]
    target_raw = y[warmup + 1 : warmup + 1 + length]
    train_end = chronological_split(length, 0.65)
    observed, obs_mu, obs_sd = zscore_from_train(observed_raw, train_end)
    target, tgt_mu, tgt_sd = zscore_from_train(target_raw, train_end)
    return SequenceTask(
        name="narma10",
        display_name="NARMA10",
        observed=observed,
        target=target,
        train_end=train_end,
        horizon=1,
        metadata={"obs_mu": obs_mu, "obs_sd": obs_sd, "target_mu": tgt_mu, "target_sd": tgt_sd},
    )


def build_task(name: str, length: int, seed: int, horizon: int) -> SequenceTask:
    if name == "mackey_glass":
        return mackey_glass_series(length, seed, horizon=horizon)
    if name == "lorenz":
        return lorenz_series(length, seed, horizon=horizon)
    if name == "narma10":
        return narma10_series(length, seed, horizon=horizon)
    raise ValueError(f"unknown task {name!r}")


def lag_features(observed: np.ndarray, index: int, history: int) -> np.ndarray:
    values = [1.0]
    for lag in range(history):
        idx = index - lag
        values.append(float(observed[idx]) if idx >= 0 else 0.0)
    current = float(observed[index])
    values.extend([abs(current), math.sin(current), math.cos(current)])
    return np.asarray(values, dtype=float)


def design_matrix(task: SequenceTask, history: int) -> np.ndarray:
    return np.vstack([lag_features(task.observed, i, history) for i in range(len(task.observed))])


def ridge_fit(x: np.ndarray, y: np.ndarray, ridge: float) -> np.ndarray:
    xtx = x.T @ x
    reg = float(ridge) * np.eye(xtx.shape[0])
    return np.linalg.solve(xtx + reg, x.T @ y)


class PersistenceModel:
    name = "persistence"

    def fit(self, task: SequenceTask) -> None:
        return None

    def predict_all(self, task: SequenceTask) -> tuple[np.ndarray, dict[str, Any]]:
        pred = np.zeros_like(task.target)
        pred[0] = float(task.observed[0])
        pred[1:] = task.observed[:-1]
        return pred, {"rule": "previous observed value"}


class OnlineLMSModel:
    name = "online_lms"

    def __init__(self, *, history: int, lr: float, ridge: float):
        self.history = history
        self.lr = lr
        self.ridge = ridge

    def fit(self, task: SequenceTask) -> None:
        return None

    def predict_all(self, task: SequenceTask) -> tuple[np.ndarray, dict[str, Any]]:
        features = design_matrix(task, self.history)
        w = np.zeros(features.shape[1], dtype=float)
        pred = np.zeros(len(task.target), dtype=float)
        for i, x in enumerate(features):
            pred[i] = float(np.dot(w, x))
            err = float(task.target[i] - pred[i])
            w *= 1.0 - self.ridge
            w += self.lr * err * x
            norm = float(np.linalg.norm(w))
            if norm > 100.0:
                w *= 100.0 / norm
        return pred, {"history": self.history, "lr": self.lr, "final_weight_norm": float(np.linalg.norm(w))}


class RidgeLagModel:
    name = "ridge_lag"

    def __init__(self, *, history: int, ridge: float):
        self.history = history
        self.ridge = ridge
        self.w: np.ndarray | None = None

    def fit(self, task: SequenceTask) -> None:
        x = design_matrix(task, self.history)
        self.w = ridge_fit(x[: task.train_end], task.target[: task.train_end], self.ridge)

    def predict_all(self, task: SequenceTask) -> tuple[np.ndarray, dict[str, Any]]:
        if self.w is None:
            raise RuntimeError("model not fit")
        x = design_matrix(task, self.history)
        return x @ self.w, {"history": self.history, "ridge": self.ridge, "weight_norm": float(np.linalg.norm(self.w))}


class EchoStateNetworkModel:
    name = "echo_state_network"

    def __init__(self, *, seed: int, units: int, spectral_radius: float, input_scale: float, ridge: float):
        self.seed = seed
        self.units = units
        self.spectral_radius = spectral_radius
        self.input_scale = input_scale
        self.ridge = ridge
        self.w_in: np.ndarray | None = None
        self.w_res: np.ndarray | None = None
        self.w_out: np.ndarray | None = None

    def _states(self, task: SequenceTask) -> np.ndarray:
        if self.w_in is None or self.w_res is None:
            rng = np.random.default_rng(self.seed + 4040)
            self.w_in = rng.normal(0.0, self.input_scale, size=(self.units, 2))
            raw = rng.normal(0.0, 1.0, size=(self.units, self.units))
            eig = max(abs(np.linalg.eigvals(raw)))
            self.w_res = raw * (self.spectral_radius / float(eig))
        state = np.zeros(self.units, dtype=float)
        states = np.zeros((len(task.observed), self.units + 2), dtype=float)
        for i, value in enumerate(task.observed):
            u = np.asarray([1.0, float(value)], dtype=float)
            state = np.tanh(self.w_res @ state + self.w_in @ u)
            states[i] = np.concatenate([[1.0, float(value)], state])
        return states

    def fit(self, task: SequenceTask) -> None:
        states = self._states(task)
        self.w_out = ridge_fit(states[: task.train_end], task.target[: task.train_end], self.ridge)

    def predict_all(self, task: SequenceTask) -> tuple[np.ndarray, dict[str, Any]]:
        if self.w_out is None:
            raise RuntimeError("model not fit")
        states = self._states(task)
        pred = states @ self.w_out
        return pred, {
            "units": self.units,
            "spectral_radius": self.spectral_radius,
            "input_scale": self.input_scale,
            "ridge": self.ridge,
            "readout_norm": float(np.linalg.norm(self.w_out)),
        }


class RegressionAdapter:
    task_name = "tier7_0_regression"

    def encode(self, observation: Observation, n_channels: int) -> np.ndarray:
        out = np.zeros(max(1, int(n_channels)), dtype=float)
        values = np.asarray(observation.x, dtype=float).reshape(-1)
        out[0] = float(values[0]) if values.size else 0.0
        return out

    def evaluate(self, prediction: float, observation: Observation, dt_seconds: float) -> ConsequenceSignal:
        del dt_seconds
        target = 0.0 if observation.target is None else float(observation.target)
        err = target - float(prediction)
        correct = (prediction >= 0.0) == (target >= 0.0)
        return ConsequenceSignal(
            immediate_signal=target,
            horizon_signal=target,
            actual_value=target,
            prediction=float(prediction),
            direction_correct=bool(correct),
            raw_dopamine=float(np.tanh(err)),
            task_metrics={"regression_error": err, "squared_error": err * err},
            metadata={"adapter": "tier7_0_regression", "stream_id": observation.stream_id},
        )


class CRAOnlineModel:
    name = "cra_v2_1_online"

    def __init__(self, *, seed: int, population_size: int, backend: str, readout_lr: float, delayed_lr: float):
        self.seed = seed
        self.population_size = population_size
        self.backend = backend
        self.readout_lr = readout_lr
        self.delayed_lr = delayed_lr

    def fit(self, task: SequenceTask) -> None:
        return None

    def predict_all(self, task: SequenceTask) -> tuple[np.ndarray, dict[str, Any]]:
        random.seed(self.seed)
        np.random.seed(self.seed)
        sim, backend_name = load_backend(self.backend)
        setup_backend(sim, backend_name)
        cfg = ReefConfig.default()
        cfg.seed = int(self.seed)
        cfg.lifecycle.initial_population = int(self.population_size)
        cfg.lifecycle.max_population_hard = int(self.population_size)
        cfg.lifecycle.max_population_from_memory = False
        cfg.lifecycle.enable_reproduction = False
        cfg.lifecycle.enable_apoptosis = False
        cfg.measurement.stream_history_maxlen = max(len(task.observed) + 32, 256)
        cfg.learning.readout_learning_rate = float(self.readout_lr)
        cfg.learning.delayed_readout_learning_rate = float(self.delayed_lr)
        cfg.learning.evaluation_horizon_bars = int(max(1, task.horizon))
        cfg.spinnaker.sync_interval_steps = 0
        cfg.spinnaker.runtime_ms_per_step = 1000.0
        organism = Organism(cfg, sim, use_default_trading_bridge=False)
        adapter = RegressionAdapter()
        predictions: list[float] = []
        try:
            organism.initialize(stream_keys=[task.name])
            for step, (obs, target) in enumerate(zip(task.observed, task.target)):
                observation = Observation(
                    stream_id=task.name,
                    x=np.asarray([float(obs)], dtype=float),
                    target=float(target),
                    timestamp=float(step),
                    metadata={"tier": "7.0", "task": task.name, "step": int(step)},
                )
                metrics = organism.train_adapter_step(adapter, observation, dt_seconds=1.0)
                predictions.append(float(metrics.colony_prediction))
        finally:
            organism.shutdown()
            end_backend(sim)
        return np.asarray(predictions, dtype=float), {
            "backend": backend_name,
            "population_size": self.population_size,
            "readout_lr": self.readout_lr,
            "delayed_lr": self.delayed_lr,
            "evaluation_horizon_bars": int(max(1, task.horizon)),
        }


def build_model(name: str, *, seed: int, args: argparse.Namespace) -> SequenceModel:
    if name == "persistence":
        return PersistenceModel()
    if name == "online_lms":
        return OnlineLMSModel(history=args.history, lr=args.online_lr, ridge=args.online_decay)
    if name == "ridge_lag":
        return RidgeLagModel(history=args.history, ridge=args.ridge)
    if name == "echo_state_network":
        return EchoStateNetworkModel(
            seed=seed,
            units=args.esn_units,
            spectral_radius=args.esn_spectral_radius,
            input_scale=args.esn_input_scale,
            ridge=args.ridge,
        )
    if name == "cra_v2_1_online":
        return CRAOnlineModel(
            seed=seed,
            population_size=args.cra_population_size,
            backend=args.backend,
            readout_lr=args.cra_readout_lr,
            delayed_lr=args.cra_delayed_lr,
        )
    raise ValueError(f"unknown model {name!r}")


def score_predictions(task: SequenceTask, pred: np.ndarray) -> dict[str, float]:
    y = task.target
    train_slice = slice(0, task.train_end)
    test_slice = slice(task.train_end, len(y))
    tail_start = task.train_end + max(1, int(0.75 * (len(y) - task.train_end)))
    train_err = pred[train_slice] - y[train_slice]
    test_err = pred[test_slice] - y[test_slice]
    tail_err = pred[tail_start:] - y[tail_start:]
    denom = float(np.var(y[test_slice]))
    if denom < 1e-12:
        denom = 1.0
    return {
        "train_mse": float(np.mean(train_err**2)),
        "mse": float(np.mean(test_err**2)),
        "nmse": float(np.mean(test_err**2) / denom),
        "tail_mse": float(np.mean(tail_err**2)),
        "target_variance_test": denom,
    }


def run_model(task: SequenceTask, model_name: str, *, seed: int, args: argparse.Namespace) -> ModelResult:
    started = time.perf_counter()
    try:
        model = build_model(model_name, seed=seed, args=args)
        model.fit(task)
        predictions, diagnostics = model.predict_all(task)
        if predictions.shape[0] != task.target.shape[0]:
            raise RuntimeError(f"prediction length {predictions.shape[0]} != target length {task.target.shape[0]}")
        scores = score_predictions(task, predictions)
        rows = []
        for step, (obs, target, pred) in enumerate(zip(task.observed, task.target, predictions)):
            split = "train" if step < task.train_end else "test"
            rows.append(
                {
                    "task": task.name,
                    "model": model_name,
                    "seed": int(seed),
                    "step": int(step),
                    "split": split,
                    "observed": float(obs),
                    "target": float(target),
                    "prediction": float(pred),
                    "squared_error": float((pred - target) ** 2),
                }
            )
        return ModelResult(
            task=task.name,
            model=model_name,
            seed=seed,
            status="pass",
            mse=scores["mse"],
            nmse=scores["nmse"],
            tail_mse=scores["tail_mse"],
            train_mse=scores["train_mse"],
            runtime_seconds=time.perf_counter() - started,
            predictions=[float(x) for x in predictions],
            rows=rows,
            diagnostics={**diagnostics, **scores},
        )
    except Exception as exc:
        return ModelResult(
            task=task.name,
            model=model_name,
            seed=seed,
            status="fail",
            mse=None,
            nmse=None,
            tail_mse=None,
            train_mse=None,
            runtime_seconds=time.perf_counter() - started,
            predictions=[],
            rows=[],
            diagnostics={},
            failure_reason=repr(exc),
        )


def geometric_mean(values: list[float]) -> float | None:
    clean = [float(v) for v in values if v is not None and math.isfinite(float(v)) and float(v) > 0]
    if not clean:
        return None
    return float(math.exp(sum(math.log(v) for v in clean) / len(clean)))


def summarize(results: list[ModelResult], tasks: list[str], models: list[str], seeds: list[int]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    aggregate_rows: list[dict[str, Any]] = []
    for task in tasks:
        for model in models:
            subset = [r for r in results if r.task == task and r.model == model and r.status == "pass"]
            rows.append(
                {
                    "task": task,
                    "model": model,
                    "status": "pass" if len(subset) == len(seeds) else "fail",
                    "seed_count": len(subset),
                    "mse_mean": mean([r.mse for r in subset]),
                    "mse_median": float(np.median([r.mse for r in subset])) if subset else None,
                    "mse_std": stdev([r.mse for r in subset]),
                    "mse_worst": max([r.mse for r in subset]) if subset else None,
                    "nmse_mean": mean([r.nmse for r in subset]),
                    "tail_mse_mean": mean([r.tail_mse for r in subset]),
                    "runtime_seconds_mean": mean([r.runtime_seconds for r in subset]),
                }
            )
    for model in models:
        for seed in seeds:
            subset = [r for r in results if r.model == model and r.seed == seed and r.status == "pass"]
            by_task = {r.task: r for r in subset}
            if all(task in by_task for task in tasks):
                aggregate_rows.append(
                    {
                        "task": "all_three_geomean",
                        "model": model,
                        "seed": int(seed),
                        "status": "pass",
                        "geomean_mse": geometric_mean([by_task[task].mse for task in tasks]),
                        "geomean_nmse": geometric_mean([by_task[task].nmse for task in tasks]),
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
    return rows, aggregate_rows


def summarize_aggregate(aggregate_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    models = sorted({str(row["model"]) for row in aggregate_rows})
    rows: list[dict[str, Any]] = []
    for model in models:
        subset = [
            row
            for row in aggregate_rows
            if row["model"] == model and row["status"] == "pass" and row.get("geomean_mse") is not None
        ]
        values = [float(row["geomean_mse"]) for row in subset]
        nmse_values = [float(row["geomean_nmse"]) for row in subset]
        rows.append(
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
    pass_rows = [row for row in rows if row["status"] == "pass" and row["geomean_mse_mean"] is not None]
    pass_rows.sort(key=lambda row: float(row["geomean_mse_mean"]))
    rank = {row["model"]: i + 1 for i, row in enumerate(pass_rows)}
    for row in rows:
        row["rank_by_geomean_mse"] = rank.get(row["model"])
    return sorted(rows, key=lambda row: (row["rank_by_geomean_mse"] or 10_000, row["model"]))


def classify_outcome(aggregate_summary: list[dict[str, Any]]) -> dict[str, Any]:
    pass_rows = [row for row in aggregate_summary if row["status"] == "pass" and row["geomean_mse_mean"] is not None]
    best = min(pass_rows, key=lambda row: float(row["geomean_mse_mean"])) if pass_rows else None
    cra = next((row for row in pass_rows if row["model"] == "cra_v2_1_online"), None)
    best_non_cra = min(
        [row for row in pass_rows if row["model"] != "cra_v2_1_online"],
        key=lambda row: float(row["geomean_mse_mean"]),
        default=None,
    )
    ratio = None
    if cra and best_non_cra and float(best_non_cra["geomean_mse_mean"]) > 0:
        ratio = float(cra["geomean_mse_mean"]) / float(best_non_cra["geomean_mse_mean"])
    if cra is None:
        outcome = "cra_run_failed"
        recommendation = "Repair CRA benchmark execution before interpreting capability."
    elif best and best["model"] == "cra_v2_1_online":
        outcome = "cra_best_on_standard_dynamical_suite"
        recommendation = "Run a promotion/regression gate before any claim upgrade."
    elif ratio is not None and ratio <= 1.25:
        outcome = "cra_competitive_but_not_best"
        recommendation = "Inspect task-wise failures before deciding whether mechanism work is justified."
    else:
        outcome = "cra_underperforms_standard_sequence_baselines"
        recommendation = (
            "Run Tier 7.0b failure analysis before tuning or hardware migration; classify whether the gap is "
            "continuous-valued regression readout, long-memory state, reservoir dynamics, normalization, or "
            "policy/credit mismatch."
        )
    return {
        "outcome": outcome,
        "best_model": None if best is None else best["model"],
        "cra_rank": None if cra is None else cra.get("rank_by_geomean_mse"),
        "cra_geomean_mse_mean": None if cra is None else cra.get("geomean_mse_mean"),
        "best_non_cra_model": None if best_non_cra is None else best_non_cra["model"],
        "best_non_cra_geomean_mse_mean": None if best_non_cra is None else best_non_cra.get("geomean_mse_mean"),
        "cra_vs_best_non_cra_mse_ratio": ratio,
        "recommendation": recommendation,
    }


def fairness_contract(args: argparse.Namespace, tasks: list[str], models: list[str], seeds: list[int]) -> dict[str, Any]:
    return {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "tasks": tasks,
        "models": models,
        "seeds": seeds,
        "split": "chronological",
        "train_fraction": args.train_fraction,
        "normalization": "z-score fit on train prefix only per task/seed",
        "prediction": "predict before update; CRA scored prequentially on test rows only",
        "no_future_leakage_rules": [
            "target horizon is shifted before split",
            "normalization uses train prefix only",
            "ridge/ESN readouts fit only on train rows",
            "online models update after producing each prediction",
        ],
        "nonclaims": [
            "not hardware evidence",
            "not a superiority claim",
            "not a tuning run",
            "not a new software baseline freeze",
        ],
    }


def write_report(output_dir: Path, results: dict[str, Any]) -> None:
    lines = [
        "# Tier 7.0 Standard Dynamical Benchmark Suite",
        "",
        f"- Generated: `{results['generated_at_utc']}`",
        f"- Status: **{results['status'].upper()}**",
        f"- Runner revision: `{results['runner_revision']}`",
        f"- Criteria: `{results['criteria_passed']}/{results['criteria_total']}`",
        f"- Tasks: `{', '.join(results['tasks'])}`",
        f"- Models: `{', '.join(results['models'])}`",
        "",
        "## Claim Boundary",
        "",
        results["claim_boundary"],
        "",
        "## Task Summary",
        "",
        "| Task | Model | Status | MSE mean | NMSE mean | Tail MSE mean |",
        "| --- | --- | --- | ---: | ---: | ---: |",
    ]
    for row in results["summary_rows"]:
        lines.append(
            "| "
            f"{row['task']} | {row['model']} | {row['status']} | "
            f"{row['mse_mean']} | {row['nmse_mean']} | {row['tail_mse_mean']} |"
        )
    lines.extend(["", "## Aggregate Geometric Mean", "", "| Model | Seed | Status | Geomean MSE | Geomean NMSE |", "| --- | ---: | --- | ---: | ---: |"])
    for row in results["aggregate_rows"]:
        lines.append(
            f"| {row['model']} | {row['seed']} | {row['status']} | {row['geomean_mse']} | {row['geomean_nmse']} |"
        )
    lines.extend(
        [
            "",
            "## Outcome Classification",
            "",
            f"- Outcome: `{results['outcome_classification']['outcome']}`",
            f"- Best model: `{results['outcome_classification']['best_model']}`",
            f"- CRA rank: `{results['outcome_classification']['cra_rank']}`",
            f"- CRA / best non-CRA MSE ratio: `{results['outcome_classification']['cra_vs_best_non_cra_mse_ratio']}`",
            f"- Recommendation: {results['outcome_classification']['recommendation']}",
            "",
            "| Model | Rank | Geomean MSE mean | Geomean NMSE mean |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for row in results["aggregate_summary"]:
        lines.append(
            f"| {row['model']} | {row['rank_by_geomean_mse']} | {row['geomean_mse_mean']} | {row['geomean_nmse_mean']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation Rule",
            "",
            "- This tier diagnoses capability; it does not freeze a new baseline by itself.",
            "- If CRA underperforms, classify the failure mode before adding mechanisms or tuning.",
            "- Do not move this suite to hardware until the software harness is stable and reviewer-safe.",
            "",
        ]
    )
    (output_dir / "tier7_0_report.md").write_text("\n".join(lines), encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    tasks = parse_csv(args.tasks)
    models = parse_csv(args.models)
    seeds = parse_seeds(args)
    results: list[ModelResult] = []
    detailed_rows: list[dict[str, Any]] = []
    started = time.perf_counter()

    for seed in seeds:
        built_tasks = {name: build_task(name, args.length, seed, args.horizon) for name in tasks}
        for task_name in tasks:
            task = built_tasks[task_name]
            task_meta_path = output_dir / f"{task.name}_seed{seed}_task.json"
            write_json(
                task_meta_path,
                {
                    "name": task.name,
                    "display_name": task.display_name,
                    "seed": int(seed),
                    "length": int(len(task.target)),
                    "train_end": int(task.train_end),
                    "horizon": int(task.horizon),
                    "metadata": task.metadata,
                },
            )
            for model_name in models:
                result = run_model(task, model_name, seed=seed, args=args)
                results.append(result)
                if result.rows:
                    timeseries_path = output_dir / f"{task.name}_{model_name}_seed{seed}_timeseries.csv"
                    write_csv(
                        timeseries_path,
                        result.rows,
                        ["task", "model", "seed", "step", "split", "observed", "target", "prediction", "squared_error"],
                    )
                    detailed_rows.extend(result.rows)

    summary_rows, aggregate_rows = summarize(results, tasks, models, seeds)
    aggregate_summary = summarize_aggregate(aggregate_rows)
    outcome_classification = classify_outcome(aggregate_summary)
    criteria = [
        criterion("runner revision current", RUNNER_REVISION, "expected current source", RUNNER_REVISION.endswith("_0001")),
        criterion("all task names known", tasks, "subset of supported tasks", all(t in {"mackey_glass", "lorenz", "narma10"} for t in tasks)),
        criterion("all requested models known", models, "subset of supported models", all(m in set(parse_csv(DEFAULT_MODELS)) for m in models)),
        criterion("all model/task/seed runs passed", f"{sum(r.status == 'pass' for r in results)}/{len(results)}", "all pass", all(r.status == "pass" for r in results)),
        criterion("aggregate geomean rows complete", len(aggregate_rows), f"== {len(models) * len(seeds)}", len(aggregate_rows) == len(models) * len(seeds)),
        criterion("aggregate geomean rows pass", [r["status"] for r in aggregate_rows], "all == pass", all(r["status"] == "pass" for r in aggregate_rows)),
        criterion("leakage guardrail documented", "train-normalized chronological split", "present", True),
        criterion("CRA model included", "cra_v2_1_online" in models, "== true", "cra_v2_1_online" in models),
        criterion("at least three non-CRA baselines included", len([m for m in models if not m.startswith("cra_")]), ">= 3", len([m for m in models if not m.startswith("cra_")]) >= 3),
        criterion("benchmark outcome classified", outcome_classification["outcome"], "non-empty", bool(outcome_classification["outcome"])),
    ]
    failed = [c for c in criteria if not c["passed"]]
    status = "pass" if not failed else "fail"
    result_payload = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "status": status,
        "output_dir": str(output_dir),
        "tasks": tasks,
        "models": models,
        "seeds": seeds,
        "length": int(args.length),
        "train_fraction": float(args.train_fraction),
        "runtime_seconds": time.perf_counter() - started,
        "criteria": criteria,
        "criteria_passed": len(criteria) - len(failed),
        "criteria_total": len(criteria),
        "failed_criteria": failed,
        "summary_rows": summary_rows,
        "aggregate_rows": aggregate_rows,
        "aggregate_summary": aggregate_summary,
        "outcome_classification": outcome_classification,
        "summary": {
            "outcome": outcome_classification["outcome"],
            "best_model": outcome_classification["best_model"],
            "cra_rank": outcome_classification["cra_rank"],
            "cra_geomean_mse_mean": outcome_classification["cra_geomean_mse_mean"],
            "best_non_cra_model": outcome_classification["best_non_cra_model"],
            "best_non_cra_geomean_mse_mean": outcome_classification["best_non_cra_geomean_mse_mean"],
            "cra_vs_best_non_cra_mse_ratio": outcome_classification["cra_vs_best_non_cra_mse_ratio"],
        },
        "run_rows": [
            {
                "task": r.task,
                "model": r.model,
                "seed": r.seed,
                "status": r.status,
                "mse": r.mse,
                "nmse": r.nmse,
                "tail_mse": r.tail_mse,
                "train_mse": r.train_mse,
                "runtime_seconds": r.runtime_seconds,
                "diagnostics": r.diagnostics,
                "failure_reason": r.failure_reason,
            }
            for r in results
        ],
        "fairness_contract": fairness_contract(args, tasks, models, seeds),
        "claim_boundary": (
            "Tier 7.0 is software benchmark/diagnostic evidence only. It compares "
            "CRA v2.1 online behavior against causal sequence baselines on "
            "Mackey-Glass, Lorenz, NARMA10, and aggregate geometric-mean MSE. "
            "It is not hardware evidence, not a new baseline freeze, not a "
            "superiority claim, and not a tuning run."
        ),
    }

    write_json(output_dir / "tier7_0_results.json", result_payload)
    write_json(output_dir / "tier7_0_fairness_contract.json", result_payload["fairness_contract"])
    write_csv(
        output_dir / "tier7_0_summary.csv",
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
            "runtime_seconds_mean",
        ],
    )
    write_csv(
        output_dir / "tier7_0_aggregate.csv",
        aggregate_rows,
        ["task", "model", "seed", "status", "geomean_mse", "geomean_nmse"],
    )
    write_report(output_dir, result_payload)
    write_json(
        OUTPUT_ROOT / "tier7_0_latest_manifest.json",
        {
            "tier": TIER,
            "runner_revision": RUNNER_REVISION,
            "generated_at_utc": result_payload["generated_at_utc"],
            "status": status,
            "manifest": str(output_dir / "tier7_0_results.json"),
            "output_dir": str(output_dir),
        },
    )
    return result_payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=TIER)
    parser.add_argument("--tasks", default=DEFAULT_TASKS)
    parser.add_argument("--models", default=DEFAULT_MODELS)
    parser.add_argument("--seeds", default="42,43,44")
    parser.add_argument("--seed-count", type=int, default=None)
    parser.add_argument("--base-seed", type=int, default=42)
    parser.add_argument("--length", type=int, default=720)
    parser.add_argument("--horizon", type=int, default=8)
    parser.add_argument("--train-fraction", type=float, default=0.65)
    parser.add_argument("--history", type=int, default=12)
    parser.add_argument("--ridge", type=float, default=1e-3)
    parser.add_argument("--online-lr", type=float, default=0.02)
    parser.add_argument("--online-decay", type=float, default=1e-5)
    parser.add_argument("--esn-units", type=int, default=64)
    parser.add_argument("--esn-spectral-radius", type=float, default=0.9)
    parser.add_argument("--esn-input-scale", type=float, default=0.5)
    parser.add_argument("--backend", default="mock")
    parser.add_argument("--cra-population-size", type=int, default=8)
    parser.add_argument("--cra-readout-lr", type=float, default=0.20)
    parser.add_argument("--cra-delayed-lr", type=float, default=0.20)
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
                "output_dir": result["output_dir"],
            },
            indent=2,
        )
    )
    if result["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
