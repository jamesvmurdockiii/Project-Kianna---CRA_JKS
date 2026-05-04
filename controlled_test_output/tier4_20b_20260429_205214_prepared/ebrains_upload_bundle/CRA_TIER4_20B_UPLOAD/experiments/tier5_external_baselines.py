#!/usr/bin/env python3
"""Tier 5.1 external baselines for CRA.

Tier 5.1 asks a stricter question than the Tier 1-4 evidence ladder:

    Does CRA do anything useful compared with simpler learners?

The harness runs CRA and non-CRA learners on identical online task streams. Each
model predicts before seeing the label, and delayed tasks update only when the
consequence matures. This prevents label leakage in the baseline comparison.
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

# NEST/torch/scientific Python stacks on macOS can load more than one OpenMP
# runtime. We do not use this as a performance setting; it keeps local NEST
# import/setup available for controlled experiment execution.
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except Exception as exc:  # pragma: no cover - optional plotting dependency
    plt = None
    MATPLOTLIB_ERROR = str(exc)
else:
    MATPLOTLIB_ERROR = None

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from coral_reef_spinnaker import Observation, Organism, ReefConfig, SensorControlAdapter  # noqa: E402
from tier2_learning import (  # noqa: E402
    DEFAULT_AMPLITUDE,
    DEFAULT_DT_SECONDS,
    criterion,
    end_backend,
    load_backend,
    markdown_value,
    pass_fail,
    safe_corr,
    setup_backend,
    strict_sign,
    write_csv,
    write_json,
)
from tier4_scaling import mean, min_value, seeds_from_args, stdev  # noqa: E402


EPS = 1e-12
TIER = "Tier 5.1 - External Baselines"
DEFAULT_STEPS = 240
DEFAULT_POPULATION_SIZE = 8


@dataclass(frozen=True)
class TaskStream:
    name: str
    display_name: str
    domain: str
    steps: int
    sensory: np.ndarray
    current_target: np.ndarray
    evaluation_target: np.ndarray
    evaluation_mask: np.ndarray
    feedback_due_step: np.ndarray
    switch_steps: list[int]
    metadata: dict[str, Any]


@dataclass
class TestResult:
    name: str
    status: str
    summary: dict[str, Any]
    criteria: list[dict[str, Any]]
    artifacts: dict[str, str]
    failure_reason: str = ""

    @property
    def passed(self) -> bool:
        return self.status == "pass"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "summary": self.summary,
            "criteria": self.criteria,
            "artifacts": self.artifacts,
            "failure_reason": self.failure_reason,
        }


class OnlineLearner(Protocol):
    name: str
    family: str

    def step(self, x: np.ndarray) -> tuple[float, Any]:
        ...

    def update(self, state: Any, label: int) -> None:
        ...

    def diagnostics(self) -> dict[str, Any]:
        ...


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


def parse_models(raw: str) -> list[str]:
    values = [item.strip() for chunk in raw.split(",") for item in chunk.split() if item.strip()]
    if not values or values == ["all"]:
        return [
            "cra",
            "random_sign",
            "sign_persistence",
            "online_perceptron",
            "online_logistic_regression",
            "echo_state_network",
            "small_gru",
            "stdp_only_snn",
            "evolutionary_population",
        ]
    return values


def bounded_sigmoid_margin(score: float, label: int) -> float:
    margin = float(label) * float(score)
    if margin >= 40.0:
        return 0.0
    if margin <= -40.0:
        return float(label)
    return float(label) / (1.0 + math.exp(margin))


class FeatureBuilder:
    def __init__(self, *, history: int, amplitude: float):
        self.history = int(history)
        self.amplitude = float(amplitude) if abs(amplitude) > EPS else 1.0
        self.values = [0.0 for _ in range(self.history)]

    @property
    def size(self) -> int:
        # bias + current/history + abs(current) + sign(current)
        return 1 + self.history + 2

    def step(self, sensory_value: float) -> np.ndarray:
        scaled = float(sensory_value) / self.amplitude
        self.values = [scaled] + self.values[: self.history - 1]
        current = self.values[0]
        return np.asarray(
            [1.0, *self.values, abs(current), float(strict_sign(current))],
            dtype=float,
        )


class RandomSignBaseline:
    name = "random_sign"
    family = "chance"

    def __init__(self, *, seed: int, feature_size: int, args: argparse.Namespace):
        self.rng = np.random.default_rng(seed + 101)

    def step(self, x: np.ndarray) -> tuple[float, Any]:
        return float(self.rng.choice([-1.0, 1.0])), None

    def update(self, state: Any, label: int) -> None:
        return None

    def diagnostics(self) -> dict[str, Any]:
        return {}


class SignPersistenceBaseline:
    name = "sign_persistence"
    family = "rule"

    def __init__(self, *, seed: int, feature_size: int, args: argparse.Namespace):
        self.last_nonzero = 1.0

    def step(self, x: np.ndarray) -> tuple[float, Any]:
        current = float(x[1])
        sign = strict_sign(current)
        if sign != 0:
            self.last_nonzero = float(sign)
        return self.last_nonzero, None

    def update(self, state: Any, label: int) -> None:
        return None

    def diagnostics(self) -> dict[str, Any]:
        return {"last_nonzero": self.last_nonzero}


class OnlinePerceptronBaseline:
    name = "online_perceptron"
    family = "linear"

    def __init__(self, *, seed: int, feature_size: int, args: argparse.Namespace):
        self.lr = float(args.perceptron_lr)
        self.margin = float(args.perceptron_margin)
        self.w = np.zeros(feature_size, dtype=float)

    def step(self, x: np.ndarray) -> tuple[float, Any]:
        return float(np.dot(self.w, x)), x.copy()

    def update(self, state: np.ndarray, label: int) -> None:
        score = float(np.dot(self.w, state))
        if label * score <= self.margin:
            self.w += self.lr * float(label) * state
            norm = float(np.linalg.norm(self.w))
            if norm > 50.0:
                self.w *= 50.0 / norm

    def diagnostics(self) -> dict[str, Any]:
        return {"weight_norm": float(np.linalg.norm(self.w))}


class OnlineLogisticRegressionBaseline:
    name = "online_logistic_regression"
    family = "linear"

    def __init__(self, *, seed: int, feature_size: int, args: argparse.Namespace):
        self.lr = float(args.logistic_lr)
        self.l2 = float(args.logistic_l2)
        self.w = np.zeros(feature_size, dtype=float)

    def step(self, x: np.ndarray) -> tuple[float, Any]:
        return float(np.tanh(np.dot(self.w, x))), x.copy()

    def update(self, state: np.ndarray, label: int) -> None:
        grad = bounded_sigmoid_margin(float(np.dot(self.w, state)), label) * state
        self.w += self.lr * (grad - self.l2 * self.w)
        norm = float(np.linalg.norm(self.w))
        if norm > 50.0:
            self.w *= 50.0 / norm

    def diagnostics(self) -> dict[str, Any]:
        return {"weight_norm": float(np.linalg.norm(self.w))}


class EchoStateNetworkBaseline:
    name = "echo_state_network"
    family = "reservoir"

    def __init__(self, *, seed: int, feature_size: int, args: argparse.Namespace):
        self.rng = np.random.default_rng(seed + 202)
        self.hidden = int(args.reservoir_hidden)
        self.lr = float(args.reservoir_lr)
        self.leak = float(args.reservoir_leak)
        self.Win = self.rng.normal(0.0, 0.6, size=(self.hidden, feature_size))
        W = self.rng.normal(0.0, 1.0, size=(self.hidden, self.hidden))
        radius = max(abs(np.linalg.eigvals(W))) if self.hidden else 1.0
        self.W = W * (float(args.reservoir_radius) / (float(radius) + EPS))
        self.h = np.zeros(self.hidden, dtype=float)
        self.readout = np.zeros(self.hidden + 1, dtype=float)

    def step(self, x: np.ndarray) -> tuple[float, Any]:
        proposal = np.tanh(self.Win @ x + self.W @ self.h)
        self.h = (1.0 - self.leak) * self.h + self.leak * proposal
        state = np.concatenate([[1.0], self.h.copy()])
        return float(np.tanh(np.dot(self.readout, state))), state

    def update(self, state: np.ndarray, label: int) -> None:
        score = float(np.tanh(np.dot(self.readout, state)))
        self.readout += self.lr * (float(label) - score) * state
        norm = float(np.linalg.norm(self.readout))
        if norm > 100.0:
            self.readout *= 100.0 / norm

    def diagnostics(self) -> dict[str, Any]:
        return {
            "hidden_norm": float(np.linalg.norm(self.h)),
            "readout_norm": float(np.linalg.norm(self.readout)),
        }


class SmallGRUBaseline:
    name = "small_gru"
    family = "recurrent"

    def __init__(self, *, seed: int, feature_size: int, args: argparse.Namespace):
        self.rng = np.random.default_rng(seed + 303)
        self.hidden = int(args.gru_hidden)
        self.lr = float(args.gru_lr)
        scale = 0.5 / math.sqrt(max(1, feature_size))
        recurrent_scale = 0.5 / math.sqrt(max(1, self.hidden))
        self.Wz = self.rng.normal(0.0, scale, size=(self.hidden, feature_size))
        self.Wr = self.rng.normal(0.0, scale, size=(self.hidden, feature_size))
        self.Wh = self.rng.normal(0.0, scale, size=(self.hidden, feature_size))
        self.Uz = self.rng.normal(0.0, recurrent_scale, size=(self.hidden, self.hidden))
        self.Ur = self.rng.normal(0.0, recurrent_scale, size=(self.hidden, self.hidden))
        self.Uh = self.rng.normal(0.0, recurrent_scale, size=(self.hidden, self.hidden))
        self.h = np.zeros(self.hidden, dtype=float)
        self.readout = np.zeros(self.hidden + 1, dtype=float)

    @staticmethod
    def _sigmoid(x: np.ndarray) -> np.ndarray:
        return 1.0 / (1.0 + np.exp(-np.clip(x, -40.0, 40.0)))

    def step(self, x: np.ndarray) -> tuple[float, Any]:
        z = self._sigmoid(self.Wz @ x + self.Uz @ self.h)
        r = self._sigmoid(self.Wr @ x + self.Ur @ self.h)
        h_tilde = np.tanh(self.Wh @ x + self.Uh @ (r * self.h))
        self.h = (1.0 - z) * self.h + z * h_tilde
        state = np.concatenate([[1.0], self.h.copy()])
        return float(np.tanh(np.dot(self.readout, state))), state

    def update(self, state: np.ndarray, label: int) -> None:
        score = float(np.tanh(np.dot(self.readout, state)))
        self.readout += self.lr * (float(label) - score) * state
        norm = float(np.linalg.norm(self.readout))
        if norm > 100.0:
            self.readout *= 100.0 / norm

    def diagnostics(self) -> dict[str, Any]:
        return {
            "hidden_norm": float(np.linalg.norm(self.h)),
            "readout_norm": float(np.linalg.norm(self.readout)),
        }


class STDPOnlySNNBaseline:
    name = "stdp_only_snn"
    family = "snn_ablation"

    def __init__(self, *, seed: int, feature_size: int, args: argparse.Namespace):
        self.rng = np.random.default_rng(seed + 404)
        self.hidden = int(args.stdp_hidden)
        self.threshold = float(args.stdp_threshold)
        self.lr = float(args.stdp_lr)
        self.trace_decay = float(args.stdp_trace_decay)
        self.Win = self.rng.normal(0.0, 0.8, size=(self.hidden, feature_size))
        self.readout = self.rng.normal(0.0, 0.02, size=self.hidden)
        self.trace = np.zeros(self.hidden, dtype=float)

    def step(self, x: np.ndarray) -> tuple[float, Any]:
        drive = self.Win @ x
        spikes = (drive > self.threshold).astype(float)
        self.trace = self.trace_decay * self.trace + spikes
        score = float(np.dot(self.readout, self.trace))
        post = strict_sign(score) or strict_sign(float(np.sum(spikes))) or 1
        # Unsupervised STDP-like update: no task label or reward is used.
        self.readout += self.lr * float(post) * self.trace
        self.readout *= 0.999
        return score, None

    def update(self, state: Any, label: int) -> None:
        return None

    def diagnostics(self) -> dict[str, Any]:
        return {
            "trace_norm": float(np.linalg.norm(self.trace)),
            "readout_norm": float(np.linalg.norm(self.readout)),
        }


class EvolutionaryPopulationBaseline:
    name = "evolutionary_population"
    family = "population"

    def __init__(self, *, seed: int, feature_size: int, args: argparse.Namespace):
        self.rng = np.random.default_rng(seed + 505)
        self.population = int(args.evo_population)
        self.mutation = float(args.evo_mutation)
        self.decay = float(args.evo_fitness_decay)
        self.W = self.rng.normal(0.0, 0.5, size=(self.population, feature_size))
        self.fitness = np.zeros(self.population, dtype=float)
        self.update_count = 0

    def step(self, x: np.ndarray) -> tuple[float, Any]:
        scores = self.W @ x
        weights = np.exp(self.fitness - np.max(self.fitness))
        weights /= np.sum(weights) + EPS
        return float(np.dot(weights, np.tanh(scores))), x.copy()

    def update(self, state: np.ndarray, label: int) -> None:
        scores = self.W @ state
        correct = np.asarray([1.0 if strict_sign(s) == label else -1.0 for s in scores], dtype=float)
        self.fitness = self.decay * self.fitness + (1.0 - self.decay) * correct
        self.update_count += 1
        order = np.argsort(self.fitness)
        survivors = order[self.population // 2 :]
        replace = order[: self.population // 2]
        for idx in replace:
            parent = int(self.rng.choice(survivors))
            self.W[idx] = self.W[parent] + self.rng.normal(0.0, self.mutation, size=state.shape[0])
            self.fitness[idx] = self.fitness[parent] * 0.95

    def diagnostics(self) -> dict[str, Any]:
        return {
            "fitness_mean": float(np.mean(self.fitness)),
            "fitness_max": float(np.max(self.fitness)),
        }


LEARNER_FACTORIES = {
    "random_sign": RandomSignBaseline,
    "sign_persistence": SignPersistenceBaseline,
    "online_perceptron": OnlinePerceptronBaseline,
    "online_logistic_regression": OnlineLogisticRegressionBaseline,
    "echo_state_network": EchoStateNetworkBaseline,
    "small_gru": SmallGRUBaseline,
    "stdp_only_snn": STDPOnlySNNBaseline,
    "evolutionary_population": EvolutionaryPopulationBaseline,
}


def alternating_signs(steps: int) -> np.ndarray:
    return np.asarray([1.0 if i % 2 == 0 else -1.0 for i in range(steps)], dtype=float)


def fixed_pattern_task(*, steps: int, amplitude: float, seed: int, args: argparse.Namespace) -> TaskStream:
    signs = alternating_signs(steps)
    current_target = amplitude * signs
    sensory = np.concatenate([[0.0], current_target[:-1]])
    evaluation_target = current_target.copy()
    evaluation_mask = np.ones(steps, dtype=bool)
    evaluation_mask[0] = False
    feedback_due = np.arange(steps, dtype=int)
    feedback_due[~evaluation_mask] = -1
    return TaskStream(
        name="fixed_pattern",
        display_name="Fixed Pattern",
        domain="signed_pattern",
        steps=steps,
        sensory=sensory,
        current_target=current_target,
        evaluation_target=evaluation_target,
        evaluation_mask=evaluation_mask,
        feedback_due_step=feedback_due,
        switch_steps=[],
        metadata={"task_kind": "fixed_pattern", "feedback": "immediate"},
    )


def delayed_cue_task(*, steps: int, amplitude: float, seed: int, args: argparse.Namespace) -> TaskStream:
    rng = np.random.default_rng(seed + 17)
    delay = int(args.delay)
    period = int(args.period)
    sensory = np.zeros(steps, dtype=float)
    current_target = np.zeros(steps, dtype=float)
    evaluation_target = np.zeros(steps, dtype=float)
    evaluation_mask = np.zeros(steps, dtype=bool)
    feedback_due = np.full(steps, -1, dtype=int)
    starts = list(range(0, steps - delay, period))
    signs = np.asarray([1.0 if i % 2 == 0 else -1.0 for i in range(len(starts))], dtype=float)
    rng.shuffle(signs)
    for start, cue_sign in zip(starts, signs):
        label = -cue_sign
        sensory[start] = amplitude * cue_sign
        current_target[start + delay] = amplitude * label
        evaluation_target[start] = amplitude * label
        evaluation_mask[start] = True
        feedback_due[start] = start + delay
    return TaskStream(
        name="delayed_cue",
        display_name="Delayed Cue",
        domain="signed_delay",
        steps=steps,
        sensory=sensory,
        current_target=current_target,
        evaluation_target=evaluation_target,
        evaluation_mask=evaluation_mask,
        feedback_due_step=feedback_due,
        switch_steps=[],
        metadata={"task_kind": "delayed_cue", "delay": delay, "period": period, "trials": len(starts)},
    )


def sensor_control_task(*, steps: int, amplitude: float, seed: int, args: argparse.Namespace) -> TaskStream:
    rng = np.random.default_rng(seed + 29)
    delay = int(args.sensor_delay)
    period = int(args.sensor_period)
    sensory = np.zeros(steps, dtype=float)
    current_target = np.zeros(steps, dtype=float)
    evaluation_target = np.zeros(steps, dtype=float)
    evaluation_mask = np.zeros(steps, dtype=bool)
    feedback_due = np.full(steps, -1, dtype=int)
    state = float(rng.normal(0.0, 0.4))
    trials = 0
    for step in range(0, steps - delay, period):
        # A tiny one-dimensional plant proxy: the desired control opposes the
        # signed sensor error. Noise keeps it from being a pure finance-shaped copy.
        state = 0.72 * state + float(rng.normal(0.0, 0.85))
        sensor_sign = 1.0 if state >= 0.0 else -1.0
        label = -sensor_sign
        sensory[step] = amplitude * sensor_sign + rng.normal(0.0, amplitude * 0.05)
        current_target[step + delay] = amplitude * label
        evaluation_target[step] = amplitude * label
        evaluation_mask[step] = True
        feedback_due[step] = step + delay
        trials += 1
    return TaskStream(
        name="sensor_control",
        display_name="Sensor Control",
        domain="sensor_control",
        steps=steps,
        sensory=sensory,
        current_target=current_target,
        evaluation_target=evaluation_target,
        evaluation_mask=evaluation_mask,
        feedback_due_step=feedback_due,
        switch_steps=[],
        metadata={"task_kind": "sensor_control", "delay": delay, "period": period, "trials": trials},
    )


def hard_noisy_switching_task(*, steps: int, amplitude: float, seed: int, args: argparse.Namespace) -> TaskStream:
    rng = np.random.default_rng(seed + 41)
    sensory = np.zeros(steps, dtype=float)
    current_target = np.zeros(steps, dtype=float)
    evaluation_target = np.zeros(steps, dtype=float)
    evaluation_mask = np.zeros(steps, dtype=bool)
    feedback_due = np.full(steps, -1, dtype=int)

    switch_steps = [0]
    cursor = 0
    while cursor < steps:
        cursor += int(rng.integers(args.min_switch_interval, args.max_switch_interval + 1))
        if cursor < steps:
            switch_steps.append(cursor)

    initial_rule = 1.0 if rng.random() < 0.5 else -1.0

    def rule_at(step: int) -> float:
        idx = int(np.searchsorted(switch_steps, step, side="right") - 1)
        return initial_rule * (1.0 if idx % 2 == 0 else -1.0)

    trials = 0
    noisy_trials = 0
    delays: list[int] = []
    for start in range(0, steps - args.max_delay, args.hard_period):
        cue_sign = 1.0 if rng.random() < 0.5 else -1.0
        delay = int(rng.integers(args.min_delay, args.max_delay + 1))
        label = rule_at(start) * cue_sign
        if rng.random() < args.noise_prob:
            label *= -1.0
            noisy_trials += 1
        sensory[start] = amplitude * cue_sign + rng.normal(0.0, args.sensory_noise_fraction * amplitude)
        current_target[start + delay] = amplitude * label
        evaluation_target[start] = amplitude * label
        evaluation_mask[start] = True
        feedback_due[start] = start + delay
        trials += 1
        delays.append(delay)

    return TaskStream(
        name="hard_noisy_switching",
        display_name="Hard Noisy Switching",
        domain="hard_switch",
        steps=steps,
        sensory=sensory,
        current_target=current_target,
        evaluation_target=evaluation_target,
        evaluation_mask=evaluation_mask,
        feedback_due_step=feedback_due,
        switch_steps=switch_steps,
        metadata={
            "task_kind": "hard_noisy_switching",
            "trials": trials,
            "noisy_trials": noisy_trials,
            "noise_rate_actual": 0.0 if trials == 0 else noisy_trials / trials,
            "delay_range": [args.min_delay, args.max_delay],
            "mean_delay": mean(delays),
            "switch_steps": switch_steps,
        },
    )


def build_tasks(args: argparse.Namespace, seed: int) -> list[TaskStream]:
    factories = {
        "fixed_pattern": fixed_pattern_task,
        "delayed_cue": delayed_cue_task,
        "sensor_control": sensor_control_task,
        "hard_noisy_switching": hard_noisy_switching_task,
    }
    task_names = [item.strip() for item in args.tasks.split(",") if item.strip()]
    if task_names == ["all"] or not task_names:
        task_names = list(factories)
    return [factories[name](steps=args.steps, amplitude=args.amplitude, seed=seed, args=args) for name in task_names]


def make_config(*, seed: int, steps: int, population_size: int, horizon: int, args: argparse.Namespace) -> ReefConfig:
    cfg = ReefConfig.default()
    cfg.seed = int(seed)
    cfg.lifecycle.initial_population = int(population_size)
    cfg.lifecycle.max_population_from_memory = False
    cfg.lifecycle.max_population_hard = int(population_size)
    cfg.lifecycle.enable_reproduction = False
    cfg.lifecycle.enable_apoptosis = False
    cfg.lifecycle.enable_structural_plasticity = True
    cfg.measurement.stream_history_maxlen = max(steps + 16, 128)
    cfg.spinnaker.sync_interval_steps = 0
    cfg.spinnaker.runtime_ms_per_step = 1000.0
    cfg.learning.evaluation_horizon_bars = int(max(1, horizon))
    cfg.learning.readout_learning_rate = float(args.cra_readout_lr)
    cfg.learning.delayed_readout_learning_rate = float(args.cra_delayed_readout_lr)
    return cfg


def run_cra_case(task: TaskStream, *, seed: int, args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    random.seed(seed)
    np.random.seed(seed)
    sim, backend_name = load_backend(args.backend)
    setup_backend(sim, backend_name)
    max_horizon = int(max(1, np.max(task.feedback_due_step - np.arange(task.steps)))) if np.any(task.feedback_due_step >= 0) else 1
    cfg = make_config(seed=seed, steps=task.steps, population_size=args.cra_population_size, horizon=max_horizon, args=args)
    organism = Organism(cfg, sim, use_default_trading_bridge=(task.domain != "sensor_control"))
    adapter = SensorControlAdapter()
    rows: list[dict[str, Any]] = []
    started = time.perf_counter()
    try:
        organism.initialize(stream_keys=[task.domain])
        bridge_present_after_init = bool(organism.trading_bridge is not None)
        for step in range(task.steps):
            sensory_value = float(task.sensory[step])
            target_value = float(task.current_target[step])
            if task.domain == "sensor_control":
                observation = Observation(
                    stream_id=task.domain,
                    x=np.asarray([sensory_value], dtype=float),
                    target=target_value,
                    metadata={"task": task.name, "step": step},
                )
                metrics = organism.train_adapter_step(adapter, observation, dt_seconds=args.dt_seconds)
            else:
                metrics = organism.train_step(
                    market_return_1m=target_value,
                    sensory_return_1m=sensory_value,
                    dt_seconds=args.dt_seconds,
                )
            prediction = float(metrics.colony_prediction)
            eval_sign = strict_sign(float(task.evaluation_target[step]))
            pred_sign = strict_sign(prediction)
            row = metrics.to_dict()
            row.update(
                {
                    "task": task.name,
                    "model": "cra",
                    "model_family": "CRA",
                    "backend": backend_name,
                    "seed": int(seed),
                    "step": int(step),
                    "sensory_return_1m": sensory_value,
                    "target_return_1m": target_value,
                    "target_signal_horizon": float(task.evaluation_target[step]),
                    "target_signal_sign": eval_sign,
                    "target_signal_nonzero": bool(task.evaluation_mask[step] and eval_sign != 0),
                    "prediction_sign": pred_sign,
                    "strict_direction_correct": bool(task.evaluation_mask[step] and pred_sign != 0 and pred_sign == eval_sign),
                    "feedback_due_step": int(task.feedback_due_step[step]),
                    "trading_bridge_present_after_init": bridge_present_after_init,
                    "trading_bridge_present_after_step": bool(organism.trading_bridge is not None),
                }
            )
            rows.append(row)
    finally:
        organism.shutdown()
        end_backend(sim)
    summary = summarize_rows(rows)
    summary.update(
        {
            "task": task.name,
            "model": "cra",
            "model_family": "CRA",
            "backend": backend_name,
            "seed": int(seed),
            "steps": task.steps,
            "runtime_seconds": time.perf_counter() - started,
            "population_size": int(args.cra_population_size),
            "uses_trading_bridge": task.domain != "sensor_control",
            "trading_bridge_present_after_init": bool(rows[0]["trading_bridge_present_after_init"]) if rows else None,
            "trading_bridge_present_any_step": bool(any(bool(r["trading_bridge_present_after_step"]) for r in rows)),
            "task_metadata": task.metadata,
            "config": cfg.to_dict(),
        }
    )
    return rows, summary


def run_baseline_case(task: TaskStream, model_name: str, *, seed: int, args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    feature_builder = FeatureBuilder(history=args.feature_history, amplitude=args.amplitude)
    learner_cls = LEARNER_FACTORIES[model_name]
    learner = learner_cls(seed=seed, feature_size=feature_builder.size, args=args)
    pending: dict[int, list[tuple[Any, int]]] = {}
    rows: list[dict[str, Any]] = []
    started = time.perf_counter()
    for step in range(task.steps):
        x = feature_builder.step(float(task.sensory[step]))
        prediction, update_state = learner.step(x)
        eval_sign = strict_sign(float(task.evaluation_target[step]))
        pred_sign = strict_sign(float(prediction))
        if bool(task.evaluation_mask[step]) and eval_sign != 0:
            due = int(task.feedback_due_step[step])
            if due >= step and due < task.steps:
                pending.setdefault(due, []).append((update_state, eval_sign))
        row = {
            "task": task.name,
            "model": model_name,
            "model_family": learner.family,
            "backend": "numpy_online",
            "seed": int(seed),
            "step": int(step),
            "sensory_return_1m": float(task.sensory[step]),
            "target_return_1m": float(task.current_target[step]),
            "target_signal_horizon": float(task.evaluation_target[step]),
            "target_signal_sign": eval_sign,
            "target_signal_nonzero": bool(task.evaluation_mask[step] and eval_sign != 0),
            "colony_prediction": float(prediction),
            "prediction_sign": pred_sign,
            "strict_direction_correct": bool(task.evaluation_mask[step] and pred_sign != 0 and pred_sign == eval_sign),
            "feedback_due_step": int(task.feedback_due_step[step]),
        }
        rows.append(row)
        for state, label in pending.pop(step, []):
            learner.update(state, label)
    summary = summarize_rows(rows)
    summary.update(
        {
            "task": task.name,
            "model": model_name,
            "model_family": learner.family,
            "backend": "numpy_online",
            "seed": int(seed),
            "steps": task.steps,
            "runtime_seconds": time.perf_counter() - started,
            "task_metadata": task.metadata,
            "diagnostics": learner.diagnostics(),
        }
    )
    return rows, summary


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {}
    steps = len(rows)
    eval_rows = [r for r in rows if bool(r.get("target_signal_nonzero", False))]
    tail_start = int(steps * 0.75)
    early_end = max(1, int(steps * 0.20))
    tail_rows = [r for r in rows[tail_start:] if bool(r.get("target_signal_nonzero", False))]
    early_rows = [r for r in rows[:early_end] if bool(r.get("target_signal_nonzero", False))]

    def accuracy(source: list[dict[str, Any]]) -> float | None:
        if not source:
            return None
        return float(np.mean([bool(r["strict_direction_correct"]) for r in source]))

    def arr(key: str, source: list[dict[str, Any]] = rows) -> np.ndarray:
        return np.asarray([float(r.get(key, 0.0) or 0.0) for r in source], dtype=float)

    pred_eval = [float(r["colony_prediction"]) for r in eval_rows]
    target_eval = [float(r["target_signal_horizon"]) for r in eval_rows]
    pred_tail = [float(r["colony_prediction"]) for r in tail_rows]
    target_tail = [float(r["target_signal_horizon"]) for r in tail_rows]
    summary = {
        "steps": steps,
        "evaluation_count": len(eval_rows),
        "early_accuracy": accuracy(early_rows),
        "tail_accuracy": accuracy(tail_rows),
        "all_accuracy": accuracy(eval_rows),
        "accuracy_improvement": None,
        "prediction_target_corr": safe_corr(pred_eval, target_eval),
        "tail_prediction_target_corr": safe_corr(pred_tail, target_tail),
        "mean_abs_prediction": float(np.mean(np.abs(arr("colony_prediction")))),
        "max_abs_prediction": float(np.max(np.abs(arr("colony_prediction")))),
    }
    if summary["early_accuracy"] is not None and summary["tail_accuracy"] is not None:
        summary["accuracy_improvement"] = float(summary["tail_accuracy"] - summary["early_accuracy"])
    if "n_alive" in rows[-1]:
        summary.update(
            {
                "final_n_alive": int(arr("n_alive")[-1]),
                "max_n_alive": int(np.max(arr("n_alive"))),
                "total_births": int(np.sum(arr("births_this_step"))),
                "total_deaths": int(np.sum(arr("deaths_this_step"))),
                "max_abs_dopamine": float(np.max(np.abs(arr("raw_dopamine")))),
                "mean_abs_dopamine": float(np.mean(np.abs(arr("raw_dopamine")))),
            }
        )
    return summary


def recovery_steps(rows: list[dict[str, Any]], switch_steps: list[int], *, window_trials: int, threshold: float, steps: int) -> list[int]:
    cue_rows = [r for r in rows if bool(r.get("target_signal_nonzero", False)) and int(r.get("target_signal_sign", 0)) != 0]
    values: list[int] = []
    for switch_step in switch_steps[1:]:
        after = [r for r in cue_rows if int(r["step"]) >= switch_step]
        recovered: int | None = None
        for idx in range(0, max(0, len(after) - window_trials + 1)):
            window = after[idx : idx + window_trials]
            acc = float(np.mean([bool(r["strict_direction_correct"]) for r in window]))
            if acc >= threshold:
                recovered = int(window[0]["step"]) - int(switch_step)
                break
        values.append(int(steps - switch_step) if recovered is None else max(0, int(recovered)))
    return values


def aggregate_summaries(task: TaskStream, model: str, summaries: list[dict[str, Any]], rows_by_seed: dict[int, list[dict[str, Any]]], args: argparse.Namespace) -> dict[str, Any]:
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
    ]
    aggregate = {
        "task": task.name,
        "display_name": task.display_name,
        "domain": task.domain,
        "model": model,
        "model_family": summaries[0].get("model_family") if summaries else None,
        "runs": len(summaries),
        "seeds": [s.get("seed") for s in summaries],
    }
    for key in keys:
        vals = [s.get(key) for s in summaries]
        aggregate[f"{key}_mean"] = mean(vals)
        aggregate[f"{key}_std"] = stdev(vals)
        aggregate[f"{key}_min"] = min_value(vals)
    if task.switch_steps:
        per_seed_recovery = []
        for seed, rows in rows_by_seed.items():
            per_seed_recovery.extend(
                recovery_steps(
                    rows,
                    task.switch_steps,
                    window_trials=args.recovery_window_trials,
                    threshold=args.recovery_accuracy_threshold,
                    steps=task.steps,
                )
            )
        aggregate["mean_recovery_steps"] = mean(per_seed_recovery)
        aggregate["max_recovery_steps"] = max(per_seed_recovery) if per_seed_recovery else None
    else:
        aggregate["mean_recovery_steps"] = None
        aggregate["max_recovery_steps"] = None
    return aggregate


def build_comparisons(aggregates: list[dict[str, Any]], args: argparse.Namespace) -> list[dict[str, Any]]:
    comparisons: list[dict[str, Any]] = []
    tasks = sorted({a["task"] for a in aggregates})
    for task in tasks:
        task_aggs = [a for a in aggregates if a["task"] == task]
        cra = next((a for a in task_aggs if a["model"] == "cra"), None)
        externals = [a for a in task_aggs if a["model"] != "cra"]
        if not cra or not externals:
            continue
        best_tail = max(externals, key=lambda a: -1.0 if a.get("tail_accuracy_mean") is None else float(a["tail_accuracy_mean"]))
        best_corr = max(externals, key=lambda a: abs(float(a.get("prediction_target_corr_mean") or 0.0)))
        tail_values = [float(a.get("tail_accuracy_mean") or 0.0) for a in externals]
        corr_values = [abs(float(a.get("prediction_target_corr_mean") or 0.0)) for a in externals]
        external_median_tail = float(np.median(tail_values)) if tail_values else None
        external_median_abs_corr = float(np.median(corr_values)) if corr_values else None
        cra_tail = float(cra.get("tail_accuracy_mean") or 0.0)
        cra_corr_abs = abs(float(cra.get("prediction_target_corr_mean") or 0.0))
        row = {
            "task": task,
            "cra_tail_accuracy_mean": cra.get("tail_accuracy_mean"),
            "cra_all_accuracy_mean": cra.get("all_accuracy_mean"),
            "cra_abs_corr_mean": cra_corr_abs,
            "best_external_tail_model": best_tail["model"],
            "best_external_tail_accuracy_mean": best_tail.get("tail_accuracy_mean"),
            "best_external_corr_model": best_corr["model"],
            "best_external_abs_corr_mean": abs(float(best_corr.get("prediction_target_corr_mean") or 0.0)),
            "external_median_tail_accuracy": external_median_tail,
            "external_median_abs_corr": external_median_abs_corr,
            "cra_tail_minus_best_external": cra_tail - float(best_tail.get("tail_accuracy_mean") or 0.0),
            "cra_tail_minus_external_median": None if external_median_tail is None else cra_tail - external_median_tail,
            "cra_abs_corr_minus_best_external": cra_corr_abs - abs(float(best_corr.get("prediction_target_corr_mean") or 0.0)),
            "cra_abs_corr_minus_external_median": None if external_median_abs_corr is None else cra_corr_abs - external_median_abs_corr,
        }
        if cra.get("mean_recovery_steps") is not None:
            recovery_candidates = [a for a in externals if a.get("mean_recovery_steps") is not None]
            if recovery_candidates:
                best_recovery = min(recovery_candidates, key=lambda a: float(a["mean_recovery_steps"]))
                external_recovery_values = [float(a["mean_recovery_steps"]) for a in recovery_candidates]
                row.update(
                    {
                        "cra_mean_recovery_steps": cra.get("mean_recovery_steps"),
                        "best_external_recovery_model": best_recovery["model"],
                        "best_external_mean_recovery_steps": best_recovery.get("mean_recovery_steps"),
                        "external_median_recovery_steps": float(np.median(external_recovery_values)),
                        "median_recovery_minus_cra": float(np.median(external_recovery_values)) - float(cra["mean_recovery_steps"]),
                        "best_external_recovery_minus_cra": float(best_recovery["mean_recovery_steps"]) - float(cra["mean_recovery_steps"]),
                    }
                )
        comparisons.append(row)
    return comparisons


def evaluate_tier(aggregates: list[dict[str, Any]], comparisons: list[dict[str, Any]], args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    expected_runs = len(seeds_from_args(args)) * len(parse_models(args.models)) * len([t for t in args.tasks.split(",") if t.strip()] if args.tasks != "all" else ["fixed_pattern", "delayed_cue", "sensor_control", "hard_noisy_switching"])
    observed_runs = sum(int(a.get("runs", 0)) for a in aggregates)
    fixed_external = [a for a in aggregates if a["task"] == "fixed_pattern" and a["model"] != "cra"]
    best_fixed = max([float(a.get("tail_accuracy_mean") or 0.0) for a in fixed_external], default=0.0)
    hard_tasks = {"delayed_cue", "sensor_control", "hard_noisy_switching"}
    hard_comparisons = [c for c in comparisons if c["task"] in hard_tasks]
    median_edges = [float(c.get("cra_tail_minus_external_median") or 0.0) for c in hard_comparisons]
    corr_edges = [float(c.get("cra_abs_corr_minus_external_median") or 0.0) for c in hard_comparisons]
    recovery_edges = [float(c.get("median_recovery_minus_cra") or 0.0) for c in hard_comparisons]
    hard_advantage_tasks = [
        c["task"]
        for c in hard_comparisons
        if float(c.get("cra_tail_minus_external_median") or 0.0) >= args.cra_median_accuracy_edge
        or float(c.get("cra_abs_corr_minus_external_median") or 0.0) >= args.cra_median_corr_edge
        or float(c.get("median_recovery_minus_cra") or 0.0) >= args.cra_median_recovery_edge
    ]
    not_strictly_dominated = [
        c["task"]
        for c in hard_comparisons
        if float(c.get("cra_tail_minus_best_external") or 0.0) >= -args.cra_best_tolerance
        or float(c.get("cra_abs_corr_minus_best_external") or 0.0) >= -args.cra_best_tolerance
        or float(c.get("best_external_recovery_minus_cra") or 0.0) >= -args.cra_recovery_best_tolerance
    ]
    summary = {
        "expected_runs": expected_runs,
        "observed_runs": observed_runs,
        "models": parse_models(args.models),
        "tasks": sorted({a["task"] for a in aggregates}),
        "best_fixed_external_tail_accuracy": best_fixed,
        "hard_advantage_tasks": hard_advantage_tasks,
        "hard_advantage_task_count": len(hard_advantage_tasks),
        "not_strictly_dominated_hard_tasks": not_strictly_dominated,
        "median_tail_edges": median_edges,
        "median_abs_corr_edges": corr_edges,
        "median_recovery_edges": recovery_edges,
    }
    criteria = [
        criterion("full task/model/seed matrix completed", observed_runs, "==", expected_runs, observed_runs == expected_runs),
        criterion(
            "simple external baseline learns fixed-pattern task",
            best_fixed,
            ">=",
            args.fixed_external_tail_threshold,
            best_fixed >= args.fixed_external_tail_threshold,
            "This catches a broken baseline harness.",
        ),
        criterion(
            "CRA has hard-task advantage versus external median",
            len(hard_advantage_tasks),
            ">=",
            args.min_hard_advantage_tasks,
            len(hard_advantage_tasks) >= args.min_hard_advantage_tasks,
            "Advantage may be tail accuracy, abs correlation, or recovery versus the external median.",
        ),
        criterion(
            "CRA is not dominated on every hard task by best external baseline",
            len(not_strictly_dominated),
            ">=",
            max(1, len(hard_comparisons) - 1),
            len(not_strictly_dominated) >= max(1, len(hard_comparisons) - 1),
            "Best-external comparison is documented separately; this criterion prevents overclaiming if CRA is broadly dominated.",
        ),
    ]
    return criteria, summary


def plot_summary(aggregates: list[dict[str, Any]], path: Path) -> None:
    if plt is None or not aggregates:
        return
    tasks = sorted({a["task"] for a in aggregates})
    models = [m for m in parse_models("all") if any(a["model"] == m for a in aggregates)]
    acc = np.zeros((len(tasks), len(models)), dtype=float)
    corr = np.zeros_like(acc)
    for i, task in enumerate(tasks):
        for j, model in enumerate(models):
            agg = next((a for a in aggregates if a["task"] == task and a["model"] == model), None)
            if agg:
                acc[i, j] = float(agg.get("tail_accuracy_mean") or 0.0)
                corr[i, j] = abs(float(agg.get("prediction_target_corr_mean") or 0.0))
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    fig.suptitle("Tier 5.1 External Baselines", fontsize=14, fontweight="bold")
    panels = [(axes[0], acc, "tail accuracy"), (axes[1], corr, "abs prediction/target corr")]
    for ax, data, title in panels:
        im = ax.imshow(data, vmin=0.0, vmax=1.0, cmap="viridis")
        ax.set_title(title)
        ax.set_xticks(range(len(models)))
        ax.set_xticklabels([m.replace("_", "\n") for m in models], rotation=0, fontsize=8)
        ax.set_yticks(range(len(tasks)))
        ax.set_yticklabels([t.replace("_", "\n") for t in tasks], fontsize=9)
        for i in range(len(tasks)):
            for j in range(len(models)):
                ax.text(j, i, f"{data[i, j]:.2f}", ha="center", va="center", color="white" if data[i, j] < 0.55 else "black", fontsize=8)
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_edges(comparisons: list[dict[str, Any]], path: Path) -> None:
    if plt is None or not comparisons:
        return
    tasks = [c["task"].replace("_", "\n") for c in comparisons]
    tail_edges = [float(c.get("cra_tail_minus_external_median") or 0.0) for c in comparisons]
    corr_edges = [float(c.get("cra_abs_corr_minus_external_median") or 0.0) for c in comparisons]
    recovery_edges = [float(c.get("median_recovery_minus_cra") or 0.0) for c in comparisons]
    x = np.arange(len(tasks))
    width = 0.25
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.axhline(0.0, color="black", lw=0.8)
    ax.bar(x - width, tail_edges, width, label="tail acc edge", color="#1f6feb")
    ax.bar(x, corr_edges, width, label="abs corr edge", color="#8250df")
    ax.bar(x + width, recovery_edges, width, label="recovery edge", color="#2f855a")
    ax.set_title("CRA Edge Versus External Median")
    ax.set_xticks(x)
    ax.set_xticklabels(tasks)
    ax.set_ylabel("positive means CRA better")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def summary_csv_rows(aggregates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for a in aggregates:
        rows.append(
            {
                "task": a["task"],
                "model": a["model"],
                "model_family": a.get("model_family"),
                "runs": a["runs"],
                "all_accuracy_mean": a.get("all_accuracy_mean"),
                "all_accuracy_std": a.get("all_accuracy_std"),
                "tail_accuracy_mean": a.get("tail_accuracy_mean"),
                "tail_accuracy_std": a.get("tail_accuracy_std"),
                "prediction_target_corr_mean": a.get("prediction_target_corr_mean"),
                "tail_prediction_target_corr_mean": a.get("tail_prediction_target_corr_mean"),
                "mean_recovery_steps": a.get("mean_recovery_steps"),
                "runtime_seconds_mean": a.get("runtime_seconds_mean"),
                "evaluation_count_mean": a.get("evaluation_count_mean"),
                "final_n_alive_mean": a.get("final_n_alive_mean"),
                "total_births_mean": a.get("total_births_mean"),
                "total_deaths_mean": a.get("total_deaths_mean"),
                "max_abs_dopamine_mean": a.get("max_abs_dopamine_mean"),
            }
        )
    return rows


def write_report(path: Path, result: TestResult, aggregates: list[dict[str, Any]], comparisons: list[dict[str, Any]], args: argparse.Namespace, output_dir: Path) -> None:
    overall = "PASS" if result.passed else "FAIL"
    lines = [
        "# Tier 5.1 External Baselines Findings",
        "",
        f"- Generated: `{utc_now()}`",
        f"- Status: **{overall}**",
        f"- CRA backend: `{args.backend}`",
        f"- Seeds: `{', '.join(str(s) for s in seeds_from_args(args))}`",
        f"- Steps per task: `{args.steps}`",
        f"- Output directory: `{output_dir}`",
        "",
        "Tier 5.1 compares CRA against simpler learners under identical online streams. Every model predicts before seeing the label; delayed tasks only update when consequence feedback matures.",
        "",
        "## Claim Boundary",
        "",
        "- This is a controlled external-baseline comparison, not a hardware result.",
        "- Success does not require CRA to win every task or every metric.",
        "- The claim is limited to whether CRA shows a defensible advantage under delay, sensor/control transfer, noise, nonstationarity, or recovery versus the external median while documenting best external competitors.",
        "",
        "## Models",
        "",
    ]
    for model in parse_models(args.models):
        family = "CRA" if model == "cra" else LEARNER_FACTORIES[model].family
        lines.append(f"- `{model}` ({family})")
    lines.extend(
        [
            "",
            "## Aggregate Summary",
            "",
            "| Task | Model | Family | Tail acc | Overall acc | Corr | Recovery | Runtime s |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for a in aggregates:
        lines.append(
            "| "
            f"{a['task']} | `{a['model']}` | {a.get('model_family')} | "
            f"{markdown_value(a.get('tail_accuracy_mean'))} | "
            f"{markdown_value(a.get('all_accuracy_mean'))} | "
            f"{markdown_value(a.get('prediction_target_corr_mean'))} | "
            f"{markdown_value(a.get('mean_recovery_steps'))} | "
            f"{markdown_value(a.get('runtime_seconds_mean'))} |"
        )
    lines.extend(
        [
            "",
            "## CRA Versus External Baselines",
            "",
            "| Task | CRA tail | Best external tail | Best external model | CRA edge vs median tail | CRA abs corr edge vs median | Recovery edge vs median |",
            "| --- | ---: | ---: | --- | ---: | ---: | ---: |",
        ]
    )
    for c in comparisons:
        lines.append(
            "| "
            f"{c['task']} | "
            f"{markdown_value(c.get('cra_tail_accuracy_mean'))} | "
            f"{markdown_value(c.get('best_external_tail_accuracy_mean'))} | "
            f"`{c.get('best_external_tail_model')}` | "
            f"{markdown_value(c.get('cra_tail_minus_external_median'))} | "
            f"{markdown_value(c.get('cra_abs_corr_minus_external_median'))} | "
            f"{markdown_value(c.get('median_recovery_minus_cra'))} |"
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
            "- `tier5_1_results.json`: machine-readable manifest.",
            "- `tier5_1_summary.csv`: aggregate task/model metrics.",
            "- `tier5_1_comparisons.csv`: CRA-vs-external comparison table.",
            "- `tier5_1_task_model_matrix.png`: task/model heatmap.",
            "- `tier5_1_cra_edges.png`: CRA edge versus external median.",
            "- `*_timeseries.csv`: per-task/per-model/per-seed online traces.",
            "",
            "## Plots",
            "",
            "![task_model_matrix](tier5_1_task_model_matrix.png)",
            "",
            "![cra_edges](tier5_1_cra_edges.png)",
            "",
        ]
    )
    if MATPLOTLIB_ERROR:
        lines.append(f"Plotting unavailable: `{MATPLOTLIB_ERROR}`")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def run_tier(args: argparse.Namespace, output_dir: Path) -> TestResult:
    models = parse_models(args.models)
    all_rows_artifacts: dict[str, str] = {}
    summaries_by_task_model: dict[tuple[str, str], list[dict[str, Any]]] = {}
    rows_by_task_model_seed: dict[tuple[str, str, int], list[dict[str, Any]]] = {}
    task_by_name: dict[str, TaskStream] = {}

    for seed in seeds_from_args(args):
        tasks = build_tasks(args, seed=args.task_seed + seed)
        for task in tasks:
            task_by_name[task.name] = task
            for model in models:
                print(f"[tier5.1] task={task.name} model={model} seed={seed}", flush=True)
                if model == "cra":
                    rows, summary = run_cra_case(task, seed=seed, args=args)
                else:
                    rows, summary = run_baseline_case(task, model, seed=seed, args=args)
                csv_path = output_dir / f"{task.name}_{model}_seed{seed}_timeseries.csv"
                write_csv(csv_path, rows)
                all_rows_artifacts[f"{task.name}_{model}_seed{seed}_timeseries_csv"] = str(csv_path)
                summaries_by_task_model.setdefault((task.name, model), []).append(summary)
                rows_by_task_model_seed[(task.name, model, seed)] = rows

    aggregates: list[dict[str, Any]] = []
    for (task_name, model), summaries in sorted(summaries_by_task_model.items()):
        task = task_by_name[task_name]
        seed_rows = {
            int(summary["seed"]): rows_by_task_model_seed[(task_name, model, int(summary["seed"]))]
            for summary in summaries
        }
        aggregates.append(aggregate_summaries(task, model, summaries, seed_rows, args))

    comparisons = build_comparisons(aggregates, args)
    criteria, tier_summary = evaluate_tier(aggregates, comparisons, args)
    status, failure_reason = pass_fail(criteria)

    summary_csv = output_dir / "tier5_1_summary.csv"
    comparison_csv = output_dir / "tier5_1_comparisons.csv"
    summary_plot = output_dir / "tier5_1_task_model_matrix.png"
    edge_plot = output_dir / "tier5_1_cra_edges.png"
    write_csv(summary_csv, summary_csv_rows(aggregates))
    write_csv(comparison_csv, comparisons)
    plot_summary(aggregates, summary_plot)
    plot_edges(comparisons, edge_plot)

    artifacts = {
        "summary_csv": str(summary_csv),
        "comparisons_csv": str(comparison_csv),
        "summary_plot_png": str(summary_plot) if summary_plot.exists() else "",
        "cra_edges_png": str(edge_plot) if edge_plot.exists() else "",
    }
    artifacts.update(all_rows_artifacts)
    result = TestResult(
        name="external_baselines",
        status=status,
        summary={
            "tier_summary": tier_summary,
            "aggregates": aggregates,
            "comparisons": comparisons,
            "models": models,
            "seeds": seeds_from_args(args),
            "tasks": sorted(task_by_name),
            "backend": args.backend,
            "claim_boundary": "Controlled software comparison only; not a hardware result and not proof that CRA wins every metric.",
        },
        criteria=criteria,
        artifacts=artifacts,
        failure_reason=failure_reason,
    )
    return result


def write_latest(output_dir: Path, report_path: Path, manifest_path: Path, summary_csv: Path, status: str) -> None:
    latest_path = ROOT / "controlled_test_output" / "tier5_1_latest_manifest.json"
    payload = {
        "generated_at_utc": utc_now(),
        "tier": TIER,
        "status": status,
        "output_dir": str(output_dir),
        "manifest": str(manifest_path),
        "report": str(report_path),
        "summary_csv": str(summary_csv),
        "canonical": False,
        "claim": "Latest Tier 5.1 external-baseline comparison; promote only after review.",
    }
    write_json(latest_path, payload)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Tier 5.1 CRA external-baseline comparisons.")
    parser.add_argument("--backend", choices=["nest", "brian2", "mock"], default="nest")
    parser.add_argument("--models", default="all")
    parser.add_argument("--tasks", default="all")
    parser.add_argument("--steps", type=int, default=DEFAULT_STEPS)
    parser.add_argument("--base-seed", type=int, default=42)
    parser.add_argument("--seed-count", type=int, default=3)
    parser.add_argument("--task-seed", type=int, default=5100)
    parser.add_argument("--amplitude", type=float, default=DEFAULT_AMPLITUDE)
    parser.add_argument("--dt-seconds", type=float, default=DEFAULT_DT_SECONDS)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--stop-on-fail", action="store_true")

    parser.add_argument("--cra-population-size", type=int, default=DEFAULT_POPULATION_SIZE)
    parser.add_argument("--cra-readout-lr", type=float, default=0.10)
    parser.add_argument("--cra-delayed-readout-lr", type=float, default=0.05)

    parser.add_argument("--feature-history", type=int, default=4)
    parser.add_argument("--delay", type=int, default=5)
    parser.add_argument("--period", type=int, default=8)
    parser.add_argument("--sensor-delay", type=int, default=3)
    parser.add_argument("--sensor-period", type=int, default=6)
    parser.add_argument("--min-delay", type=int, default=3)
    parser.add_argument("--max-delay", type=int, default=5)
    parser.add_argument("--hard-period", type=int, default=7)
    parser.add_argument("--noise-prob", type=float, default=0.20)
    parser.add_argument("--sensory-noise-fraction", type=float, default=0.25)
    parser.add_argument("--min-switch-interval", type=int, default=32)
    parser.add_argument("--max-switch-interval", type=int, default=48)

    parser.add_argument("--perceptron-lr", type=float, default=0.08)
    parser.add_argument("--perceptron-margin", type=float, default=0.05)
    parser.add_argument("--logistic-lr", type=float, default=0.10)
    parser.add_argument("--logistic-l2", type=float, default=0.001)
    parser.add_argument("--reservoir-hidden", type=int, default=24)
    parser.add_argument("--reservoir-lr", type=float, default=0.04)
    parser.add_argument("--reservoir-leak", type=float, default=0.35)
    parser.add_argument("--reservoir-radius", type=float, default=0.85)
    parser.add_argument("--gru-hidden", type=int, default=16)
    parser.add_argument("--gru-lr", type=float, default=0.04)
    parser.add_argument("--stdp-hidden", type=int, default=24)
    parser.add_argument("--stdp-threshold", type=float, default=0.25)
    parser.add_argument("--stdp-lr", type=float, default=0.0008)
    parser.add_argument("--stdp-trace-decay", type=float, default=0.90)
    parser.add_argument("--evo-population", type=int, default=24)
    parser.add_argument("--evo-mutation", type=float, default=0.06)
    parser.add_argument("--evo-fitness-decay", type=float, default=0.92)

    parser.add_argument("--recovery-window-trials", type=int, default=4)
    parser.add_argument("--recovery-accuracy-threshold", type=float, default=0.75)
    parser.add_argument("--fixed-external-tail-threshold", type=float, default=0.85)
    parser.add_argument("--min-hard-advantage-tasks", type=int, default=2)
    parser.add_argument("--cra-median-accuracy-edge", type=float, default=0.02)
    parser.add_argument("--cra-median-corr-edge", type=float, default=0.02)
    parser.add_argument("--cra-median-recovery-edge", type=float, default=2.0)
    parser.add_argument("--cra-best-tolerance", type=float, default=0.25)
    parser.add_argument("--cra-recovery-best-tolerance", type=float, default=-12.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = args.output_dir or (ROOT / "controlled_test_output" / f"tier5_1_{timestamp}")
    output_dir.mkdir(parents=True, exist_ok=True)

    result = run_tier(args, output_dir)
    manifest_path = output_dir / "tier5_1_results.json"
    report_path = output_dir / "tier5_1_report.md"
    summary_csv = output_dir / "tier5_1_summary.csv"
    comparison_csv = output_dir / "tier5_1_comparisons.csv"
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
        },
        "artifacts": {
            "summary_csv": str(summary_csv),
            "comparisons_csv": str(comparison_csv),
            "report_md": str(report_path),
            "summary_plot_png": str(output_dir / "tier5_1_task_model_matrix.png"),
            "cra_edges_png": str(output_dir / "tier5_1_cra_edges.png"),
        },
    }
    write_json(manifest_path, manifest)
    write_report(report_path, result, result.summary["aggregates"], result.summary["comparisons"], args, output_dir)
    write_latest(output_dir, report_path, manifest_path, summary_csv, result.status)
    print(
        json.dumps(
            {
                "status": result.status,
                "output_dir": str(output_dir),
                "manifest": str(manifest_path),
                "report": str(report_path),
                "summary_csv": str(summary_csv),
                "comparisons_csv": str(comparison_csv),
                "failure_reason": result.failure_reason,
            },
            indent=2,
        )
    )
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
