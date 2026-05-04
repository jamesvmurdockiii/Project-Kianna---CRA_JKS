#!/usr/bin/env python3
"""Tier 5.17 pre-reward representation-formation diagnostic.

Tier 5.17 asks a narrow reviewer-defense question:

    Can a CRA-compatible state module form useful latent structure before labels
    or reward are introduced?

The exposure phase is deliberately label-free: the candidate and non-oracle
controls receive only visible input streams. Hidden labels are retained only for
post-hoc probes after the representation has been frozen/snapshotted. This is a
software diagnostic, not a new frozen baseline, not hardware evidence, and not a
claim that CRA has concepts, language, or world modeling.
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

from tier2_learning import criterion, markdown_value, pass_fail, write_csv, write_json  # noqa: E402
from tier4_scaling import mean, seeds_from_args, stdev  # noqa: E402

TIER = "Tier 5.17 - Pre-Reward Representation Formation"
DEFAULT_TASKS = "latent_cluster_sequence,temporal_motif_sequence,ambiguous_reentry_context"
DEFAULT_VARIANTS = (
    "cra_pre_reward_state,no_state_plasticity,time_shuffled_exposure,"
    "temporal_destroyed_exposure,current_input_only,rolling_history_input,"
    "random_projection_history,random_untrained_state,oracle_latent_upper_bound"
)
CANDIDATE = "cra_pre_reward_state"
EPS = 1e-12


@dataclass(frozen=True)
class RepresentationTask:
    name: str
    display_name: str
    description: str
    observations: np.ndarray
    latent_labels: np.ndarray
    latent_factor: np.ndarray
    temporal_pressure: bool
    metadata: dict[str, Any]

    @property
    def steps(self) -> int:
        return int(self.observations.shape[0])


@dataclass(frozen=True)
class VariantSpec:
    name: str
    family: str
    description: str
    uses_hidden_labels: bool = False
    destroys_temporal_order: bool = False
    freezes_state_updates: bool = False


VARIANTS: dict[str, VariantSpec] = {
    "cra_pre_reward_state": VariantSpec(
        name="cra_pre_reward_state",
        family="CRA-compatible label-free state",
        description="competitive Hebbian/Oja prototype state with slow temporal traces; visible inputs only",
    ),
    "no_state_plasticity": VariantSpec(
        name="no_state_plasticity",
        family="CRA sham",
        description="same encoder shell with prototype and state-trace updates disabled",
        freezes_state_updates=True,
    ),
    "time_shuffled_exposure": VariantSpec(
        name="time_shuffled_exposure",
        family="CRA sham",
        description="same candidate exposed to the same visible samples in shuffled order, then restored to original indices",
        destroys_temporal_order=True,
    ),
    "temporal_destroyed_exposure": VariantSpec(
        name="temporal_destroyed_exposure",
        family="CRA sham",
        description="same candidate exposed through local block shuffles that preserve marginal input statistics but damage sequence structure",
        destroys_temporal_order=True,
    ),
    "current_input_only": VariantSpec(
        name="current_input_only",
        family="encoder-only baseline",
        description="probe sees only the current visible observation; no learned or recurrent state",
    ),
    "rolling_history_input": VariantSpec(
        name="rolling_history_input",
        family="encoder-only baseline",
        description="probe sees a short fixed visible-input history; no learned state",
    ),
    "random_projection_history": VariantSpec(
        name="random_projection_history",
        family="random projection baseline",
        description="fixed random projection of visible input history; no learning",
    ),
    "random_untrained_state": VariantSpec(
        name="random_untrained_state",
        family="random baseline",
        description="random representation unrelated to the input stream",
    ),
    "oracle_latent_upper_bound": VariantSpec(
        name="oracle_latent_upper_bound",
        family="oracle upper bound",
        description="hidden label one-hot upper bound; excluded from no-leakage promotion checks",
        uses_hidden_labels=True,
    ),
}


class LabelFreeCraStateEncoder:
    """Small CRA-compatible label-free representation scaffold.

    It intentionally uses no labels, no reward, and no downstream correctness
    signal. The update is competitive and local: a visible feature activates a
    prototype bank; the winning prototype is nudged by an Oja-like rule; a slow
    trace stores recent activation context. This is a diagnostic scaffold, not a
    claim that the existing SpiNNaker runtime already contains native on-chip
    representation learning.
    """

    def __init__(
        self,
        *,
        input_dim: int,
        seed: int,
        prototype_count: int = 14,
        learning_rate: float = 0.075,
        trace_decay: float = 0.985,
        temperature: float = 1.25,
        plasticity: bool = True,
        trace_enabled: bool = True,
    ) -> None:
        self.rng = np.random.default_rng(int(seed))
        self.prototype_count = int(prototype_count)
        self.input_dim = int(input_dim)
        self.learning_rate = float(learning_rate)
        self.trace_decay = float(trace_decay)
        self.temperature = max(1e-3, float(temperature))
        self.plasticity = bool(plasticity)
        self.trace_enabled = bool(trace_enabled)
        self.centers = self.rng.normal(0.0, 0.45, size=(self.prototype_count, self.input_dim))
        norms = np.linalg.norm(self.centers, axis=1, keepdims=True) + EPS
        self.centers = self.centers / norms
        self.trace = np.zeros(self.prototype_count, dtype=float)
        self.long_trace = np.zeros(self.prototype_count, dtype=float)
        self.step_index = 0

    def step(self, x: np.ndarray) -> np.ndarray:
        x = np.asarray(x, dtype=float).reshape(-1)
        if x.size != self.input_dim:
            raise ValueError(f"expected input_dim={self.input_dim}, got {x.size}")
        x_norm = x / (np.linalg.norm(x) + EPS)
        distances = np.sum((self.centers - x_norm[None, :]) ** 2, axis=1)
        logits = -distances / self.temperature
        logits -= float(np.max(logits))
        activations = np.exp(logits)
        activations /= float(np.sum(activations) + EPS)
        winner = int(np.argmax(activations))

        if self.plasticity:
            lr = self.learning_rate / math.sqrt(1.0 + 0.0025 * self.step_index)
            # Oja-style competitive update: local winner moves toward the
            # visible pattern and is renormalized; no label or reward appears.
            self.centers[winner] = (1.0 - lr) * self.centers[winner] + lr * x_norm
            self.centers[winner] /= float(np.linalg.norm(self.centers[winner]) + EPS)

        if self.trace_enabled:
            self.trace = self.trace_decay * self.trace + (1.0 - self.trace_decay) * activations
            self.long_trace = 0.997 * self.long_trace + 0.003 * activations
        else:
            self.trace = np.zeros_like(self.trace)
            self.long_trace = np.zeros_like(self.long_trace)

        winner_one_hot = np.zeros(self.prototype_count, dtype=float)
        winner_one_hot[winner] = 1.0
        novelty = np.asarray([float(np.min(distances)), float(np.max(activations))], dtype=float)
        self.step_index += 1
        return np.concatenate(
            [
                x_norm,
                activations,
                self.trace,
                self.long_trace,
                winner_one_hot,
                novelty,
            ]
        )


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


def parse_csv_list(raw: str, default: list[str]) -> list[str]:
    values = [item.strip() for chunk in str(raw).split(",") for item in chunk.split() if item.strip()]
    if not values or values == ["all"]:
        return list(default)
    return values


def selected_tasks(args: argparse.Namespace) -> list[str]:
    allowed = list(DEFAULT_TASKS.split(","))
    values = parse_csv_list(args.tasks, allowed)
    unknown = sorted(set(values) - set(allowed))
    if unknown:
        raise ValueError(f"Unknown task(s): {unknown}")
    return values


def selected_variants(args: argparse.Namespace) -> list[str]:
    allowed = list(VARIANTS)
    values = parse_csv_list(args.variants, allowed)
    unknown = sorted(set(values) - set(allowed))
    if unknown:
        raise ValueError(f"Unknown variant(s): {unknown}")
    if CANDIDATE not in values:
        values = [CANDIDATE, *values]
    ordered: list[str] = []
    for item in values:
        if item not in ordered:
            ordered.append(item)
    return ordered


def stable_standardize(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    mu = np.mean(x, axis=0, keepdims=True)
    sigma = np.std(x, axis=0, keepdims=True)
    return (x - mu) / np.where(sigma <= EPS, 1.0, sigma)


def make_latent_cluster_sequence(*, steps: int, seed: int) -> RepresentationTask:
    rng = np.random.default_rng(seed + 1101)
    centers = np.asarray(
        [
            [-1.1, -0.4, 0.6],
            [-0.35, 1.05, -0.55],
            [0.45, -0.9, -0.25],
            [1.15, 0.45, 0.65],
        ],
        dtype=float,
    )
    labels = np.zeros(steps, dtype=int)
    observations = np.zeros((steps, 3), dtype=float)
    z = int(rng.integers(0, len(centers)))
    for t in range(steps):
        if t > 0 and rng.random() > 0.88:
            choices = [i for i in range(len(centers)) if i != z]
            z = int(rng.choice(choices))
        labels[t] = z
        drift = 0.16 * np.asarray([math.sin(t / 23.0), math.cos(t / 31.0), math.sin(t / 41.0)])
        observations[t] = centers[z] + drift + rng.normal(0.0, 0.26, size=3)
    return RepresentationTask(
        name="latent_cluster_sequence",
        display_name="Latent Cluster Sequence",
        description="persistent unlabeled clusters with noisy visible features",
        observations=stable_standardize(observations),
        latent_labels=labels,
        latent_factor=labels.astype(float),
        temporal_pressure=False,
        metadata={"latent_count": 4, "labels_visible_during_exposure": False},
    )


def make_temporal_motif_sequence(*, steps: int, seed: int) -> RepresentationTask:
    rng = np.random.default_rng(seed + 2203)
    symbols = rng.choice([-1.0, 1.0], size=steps)
    # Add motifs with repeated local grammar so current input alone is ambiguous.
    for start in range(0, steps, 17):
        motif = rng.choice(
            [np.asarray([1.0, 1.0, -1.0]), np.asarray([-1.0, 1.0, 1.0]), np.asarray([1.0, -1.0, -1.0])]
        )
        end = min(steps, start + motif.size)
        symbols[start:end] = motif[: end - start]
    labels = np.zeros(steps, dtype=int)
    obs = np.zeros((steps, 3), dtype=float)
    ema = 0.0
    for t in range(steps):
        ema = 0.86 * ema + 0.14 * symbols[t]
        s0 = symbols[t]
        s1 = symbols[t - 1] if t >= 1 else 0.0
        s2 = symbols[t - 2] if t >= 2 else 0.0
        # Four labels from temporal motifs, not the current symbol alone.
        if s1 > 0 and s2 > 0:
            label = 0
        elif s1 < 0 and s2 < 0:
            label = 1
        elif s1 > 0 and s2 < 0:
            label = 2
        else:
            label = 3
        labels[t] = int(label)
        obs[t] = np.asarray(
            [
                s0 + rng.normal(0.0, 0.16),
                0.55 * s0 + 0.45 * ema + rng.normal(0.0, 0.18),
                (s0 - s1) + rng.normal(0.0, 0.2),
            ]
        )
    return RepresentationTask(
        name="temporal_motif_sequence",
        display_name="Temporal Motif Sequence",
        description="same current symbols require recent temporal context to recover hidden motifs",
        observations=stable_standardize(obs),
        latent_labels=labels,
        latent_factor=labels.astype(float),
        temporal_pressure=True,
        metadata={"latent_count": 4, "labels_visible_during_exposure": False},
    )


def make_ambiguous_reentry_context(*, steps: int, seed: int) -> RepresentationTask:
    rng = np.random.default_rng(seed + 3307)
    labels = np.zeros(steps, dtype=int)
    obs = np.zeros((steps, 3), dtype=float)
    context = int(rng.integers(0, 2))
    next_switch = 0
    cue_decay = 0.0
    cue_sign = 1.0 if context == 1 else -1.0
    for t in range(steps):
        if t >= next_switch:
            context = 1 - context
            cue_sign = 1.0 if context == 1 else -1.0
            cue_decay = 1.0
            next_switch = t + int(rng.integers(45, 86))
        labels[t] = int(context)
        # After the short cue, observations have nearly identical marginals;
        # useful structure comes from retaining visible cue history.
        cue_channel = cue_decay * cue_sign
        shared_noise = rng.normal(0.0, 0.55)
        obs[t] = np.asarray(
            [
                cue_channel + rng.normal(0.0, 0.05),
                shared_noise,
                0.25 * math.sin(t / 9.0) + rng.normal(0.0, 0.2),
            ]
        )
        cue_decay *= 0.76
    return RepresentationTask(
        name="ambiguous_reentry_context",
        display_name="Ambiguous Reentry Context",
        description="brief visible context cues must be retained through long ambiguous stretches",
        observations=stable_standardize(obs),
        latent_labels=labels,
        latent_factor=labels.astype(float),
        temporal_pressure=True,
        metadata={"latent_count": 2, "labels_visible_during_exposure": False},
    )


def build_task(name: str, *, steps: int, seed: int) -> RepresentationTask:
    if name == "latent_cluster_sequence":
        return make_latent_cluster_sequence(steps=steps, seed=seed)
    if name == "temporal_motif_sequence":
        return make_temporal_motif_sequence(steps=steps, seed=seed)
    if name == "ambiguous_reentry_context":
        return make_ambiguous_reentry_context(steps=steps, seed=seed)
    raise ValueError(f"unknown task {name}")


def make_visible_features(observations: np.ndarray, *, history: int = 4) -> np.ndarray:
    obs = np.asarray(observations, dtype=float)
    steps, dim = obs.shape
    rows: list[np.ndarray] = []
    for t in range(steps):
        x = obs[t]
        # Deliberately hand the candidate only the current visible sample.
        # Temporal context must be built by internal state/traces; explicit
        # short-history features are reported as separate encoder-only controls.
        rows.append(np.asarray(x, dtype=float))
    return stable_standardize(np.vstack(rows))


def make_short_history_features(observations: np.ndarray, *, history: int = 5) -> np.ndarray:
    obs = np.asarray(observations, dtype=float)
    rows = []
    for t in range(obs.shape[0]):
        parts = []
        for lag in range(history):
            idx = t - lag
            parts.append(obs[idx] if idx >= 0 else np.zeros(obs.shape[1], dtype=float))
        rows.append(np.concatenate(parts))
    return stable_standardize(np.vstack(rows))


def shuffled_order(n: int, rng: np.random.Generator, mode: str) -> np.ndarray:
    if mode == "time_shuffled_exposure":
        order = np.arange(n)
        rng.shuffle(order)
        return order
    if mode == "temporal_destroyed_exposure":
        # Preserve marginal samples and order, but the caller disables the
        # candidate's slow temporal traces for this control.
        return np.arange(n)
    return np.arange(n)


def representations_for_variant(task: RepresentationTask, variant: VariantSpec, *, seed: int, args: argparse.Namespace) -> tuple[np.ndarray, dict[str, Any]]:
    observations = np.asarray(task.observations, dtype=float)
    labels = np.asarray(task.latent_labels, dtype=int)
    n = observations.shape[0]
    rng = np.random.default_rng(seed + 17017 + abs(hash((task.name, variant.name))) % 100000)
    hidden_count = int(np.max(labels)) + 1

    metadata = {
        "labels_visible_during_exposure": bool(variant.uses_hidden_labels),
        "reward_visible_during_exposure": False,
        "max_abs_raw_dopamine": 0.0,
        "uses_hidden_labels": bool(variant.uses_hidden_labels),
        "destroys_temporal_order": bool(variant.destroys_temporal_order),
        "state_updates_enabled": not bool(variant.freezes_state_updates),
    }

    if variant.name == "oracle_latent_upper_bound":
        reps = np.zeros((n, hidden_count), dtype=float)
        reps[np.arange(n), labels] = 1.0
        reps += rng.normal(0.0, 0.01, size=reps.shape)
        return reps, metadata

    if variant.name == "current_input_only":
        return stable_standardize(observations), metadata

    history = make_short_history_features(observations, history=int(args.history_length))
    if variant.name == "rolling_history_input":
        return history, metadata

    if variant.name == "random_projection_history":
        width = int(args.random_projection_dim)
        mat = rng.normal(0.0, 1.0 / math.sqrt(history.shape[1]), size=(history.shape[1], width))
        return stable_standardize(history @ mat), metadata

    if variant.name == "random_untrained_state":
        return rng.normal(0.0, 1.0, size=(n, int(args.representation_dim))), metadata

    features = make_visible_features(observations, history=int(args.feature_history))
    encoder = LabelFreeCraStateEncoder(
        input_dim=features.shape[1],
        seed=seed + 3911,
        prototype_count=int(args.prototype_count),
        learning_rate=float(args.label_free_lr),
        trace_decay=float(args.trace_decay),
        temperature=float(args.prototype_temperature),
        plasticity=not bool(variant.freezes_state_updates),
        trace_enabled=(not bool(variant.freezes_state_updates) and variant.name != "temporal_destroyed_exposure"),
    )
    reps = np.zeros((n, features.shape[1] + 4 * int(args.prototype_count) + 2), dtype=float)
    order = shuffled_order(n, rng, variant.name)
    for original_idx in order:
        rep = encoder.step(features[int(original_idx)])
        reps[int(original_idx)] = rep
    return stable_standardize(reps), metadata


def stratified_probe_split(labels: np.ndarray, *, seed: int, train_fraction: float = 0.55) -> tuple[np.ndarray, np.ndarray]:
    """Deterministic post-exposure split for offline probes.

    Hidden labels are used only here, after representations have already been
    produced. Stratification prevents a probe failure caused by one latent class
    being absent from the train or test side, which would test split luck rather
    than representation geometry.
    """
    labels = np.asarray(labels, dtype=int)
    rng = np.random.default_rng(int(seed) + 9091)
    train_parts: list[np.ndarray] = []
    test_parts: list[np.ndarray] = []
    for label in sorted(int(c) for c in np.unique(labels)):
        idx = np.flatnonzero(labels == label)
        rng.shuffle(idx)
        if idx.size <= 2:
            train_parts.append(idx[:1])
            test_parts.append(idx[1:])
            continue
        cut = max(1, min(idx.size - 1, int(round(idx.size * train_fraction))))
        train_parts.append(np.sort(idx[:cut]))
        test_parts.append(np.sort(idx[cut:]))
    train_idx = np.sort(np.concatenate(train_parts)).astype(int) if train_parts else np.asarray([], dtype=int)
    test_idx = np.sort(np.concatenate(test_parts)).astype(int) if test_parts else np.asarray([], dtype=int)
    return train_idx, test_idx


def standardize_train_test(x: np.ndarray, train_idx: np.ndarray, test_idx: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    train = np.asarray(x[train_idx], dtype=float)
    test = np.asarray(x[test_idx], dtype=float)
    mu = np.mean(train, axis=0, keepdims=True)
    sigma = np.std(train, axis=0, keepdims=True)
    sigma = np.where(sigma <= EPS, 1.0, sigma)
    return (train - mu) / sigma, (test - mu) / sigma


def ridge_probe_accuracy(x: np.ndarray, labels: np.ndarray, train_idx: np.ndarray, test_idx: np.ndarray, *, reg: float = 1e-2) -> float:
    y_train = labels[train_idx].astype(int)
    y_test = labels[test_idx].astype(int)
    classes = sorted(int(c) for c in np.unique(labels))
    x_train, x_test = standardize_train_test(x, train_idx, test_idx)
    x_train = np.column_stack([x_train, np.ones(x_train.shape[0])])
    x_test = np.column_stack([x_test, np.ones(x_test.shape[0])])
    y = np.zeros((x_train.shape[0], len(classes)), dtype=float)
    class_to_col = {c: i for i, c in enumerate(classes)}
    for row, label in enumerate(y_train):
        y[row, class_to_col[int(label)]] = 1.0
    eye = np.eye(x_train.shape[1])
    eye[-1, -1] = 0.0
    try:
        weights = np.linalg.solve(x_train.T @ x_train + reg * eye, x_train.T @ y)
    except np.linalg.LinAlgError:
        weights = np.linalg.pinv(x_train.T @ x_train + reg * eye) @ x_train.T @ y
    scores = x_test @ weights
    pred = np.asarray([classes[int(i)] for i in np.argmax(scores, axis=1)], dtype=int)
    return float(np.mean(pred == y_test)) if y_test.size else 0.0


def centroid_probe_accuracy(x: np.ndarray, labels: np.ndarray, train_idx: np.ndarray, test_idx: np.ndarray) -> float:
    y_train = labels[train_idx].astype(int)
    y_test = labels[test_idx].astype(int)
    x_train, x_test = standardize_train_test(x, train_idx, test_idx)
    centroids: dict[int, np.ndarray] = {}
    for c in sorted(int(v) for v in np.unique(y_train)):
        mask = y_train == c
        centroids[c] = np.mean(x_train[mask], axis=0) if np.any(mask) else np.zeros(x_train.shape[1])
    preds = []
    for row in x_test:
        best = min(centroids, key=lambda c: float(np.sum((row - centroids[c]) ** 2)))
        preds.append(best)
    return float(np.mean(np.asarray(preds, dtype=int) == y_test)) if y_test.size else 0.0


def knn_probe_accuracy(x: np.ndarray, labels: np.ndarray, train_idx: np.ndarray, test_idx: np.ndarray, *, k: int = 5) -> float:
    y_train = labels[train_idx].astype(int)
    y_test = labels[test_idx].astype(int)
    x_train, x_test = standardize_train_test(x, train_idx, test_idx)
    preds = []
    for row in x_test:
        d = np.sum((x_train - row[None, :]) ** 2, axis=1)
        idx = np.argsort(d)[: max(1, min(k, d.size))]
        vals, counts = np.unique(y_train[idx], return_counts=True)
        preds.append(int(vals[int(np.argmax(counts))]))
    return float(np.mean(np.asarray(preds, dtype=int) == y_test)) if y_test.size else 0.0


def silhouette_score(x: np.ndarray, labels: np.ndarray, *, max_samples: int = 240, seed: int = 0) -> float | None:
    labels = np.asarray(labels, dtype=int)
    if np.unique(labels).size < 2:
        return None
    rng = np.random.default_rng(seed)
    if x.shape[0] > max_samples:
        idx = np.sort(rng.choice(np.arange(x.shape[0]), size=max_samples, replace=False))
        x = x[idx]
        labels = labels[idx]
    x = stable_standardize(x)
    distances = np.sqrt(np.maximum(0.0, np.sum((x[:, None, :] - x[None, :, :]) ** 2, axis=2)))
    scores = []
    for i in range(x.shape[0]):
        same = labels == labels[i]
        other_labels = [c for c in np.unique(labels) if c != labels[i]]
        if int(np.sum(same)) <= 1 or not other_labels:
            continue
        a = float(np.mean(distances[i, same & (np.arange(x.shape[0]) != i)]))
        b = min(float(np.mean(distances[i, labels == c])) for c in other_labels)
        denom = max(a, b, EPS)
        scores.append((b - a) / denom)
    if not scores:
        return None
    return float(np.mean(scores))


def latent_factor_corr(x: np.ndarray, latent_factor: np.ndarray) -> float | None:
    if x.shape[0] < 4:
        return None
    x_std = stable_standardize(x)
    try:
        _u, _s, vt = np.linalg.svd(x_std, full_matrices=False)
        pc1 = x_std @ vt[0]
    except np.linalg.LinAlgError:
        return None
    y = np.asarray(latent_factor, dtype=float)
    if float(np.std(pc1)) <= EPS or float(np.std(y)) <= EPS:
        return None
    return float(abs(np.corrcoef(pc1, y)[0, 1]))


def labels_to_threshold(x: np.ndarray, labels: np.ndarray, train_idx: np.ndarray, test_idx: np.ndarray, *, threshold: float) -> int | None:
    train_idx = np.asarray(train_idx, dtype=int)
    candidates = sorted(set(max(4, int(round(len(train_idx) * frac))) for frac in [0.04, 0.08, 0.12, 0.2, 0.35, 0.55, 1.0]))
    for count in candidates:
        sub_train = train_idx[: min(count, len(train_idx))]
        acc = ridge_probe_accuracy(x, labels, sub_train, test_idx)
        if acc >= threshold:
            return int(len(sub_train))
    return None


def evaluate_representation(task: RepresentationTask, variant_name: str, reps: np.ndarray, metadata: dict[str, Any], *, seed: int, args: argparse.Namespace) -> dict[str, Any]:
    train_idx, test_idx = stratified_probe_split(task.latent_labels, seed=seed, train_fraction=float(args.probe_train_fraction))
    labels = np.asarray(task.latent_labels, dtype=int)
    ridge_acc = ridge_probe_accuracy(reps, labels, train_idx, test_idx)
    centroid_acc = centroid_probe_accuracy(reps, labels, train_idx, test_idx)
    knn_acc = knn_probe_accuracy(reps, labels, train_idx, test_idx, k=int(args.knn_k))
    sil = silhouette_score(reps[test_idx], labels[test_idx], seed=seed)
    corr = latent_factor_corr(reps[test_idx], task.latent_factor[test_idx])
    label_count = labels_to_threshold(
        reps,
        labels,
        train_idx,
        test_idx,
        threshold=float(args.sample_efficiency_threshold),
    )
    return {
        "task": task.name,
        "task_display_name": task.display_name,
        "variant": variant_name,
        "variant_family": VARIANTS[variant_name].family,
        "seed": int(seed),
        "steps": int(task.steps),
        "representation_dim": int(reps.shape[1]),
        "latent_count": int(np.unique(labels).size),
        "temporal_pressure": bool(task.temporal_pressure),
        "ridge_probe_accuracy": ridge_acc,
        "centroid_probe_accuracy": centroid_acc,
        "knn_probe_accuracy": knn_acc,
        "silhouette_score": sil,
        "latent_factor_abs_corr": corr,
        "labels_to_threshold": label_count,
        "label_efficiency_threshold": float(args.sample_efficiency_threshold),
        "labels_visible_during_exposure": bool(metadata.get("labels_visible_during_exposure", False)),
        "reward_visible_during_exposure": bool(metadata.get("reward_visible_during_exposure", False)),
        "max_abs_raw_dopamine": float(metadata.get("max_abs_raw_dopamine", 0.0) or 0.0),
        "uses_hidden_labels": bool(metadata.get("uses_hidden_labels", False)),
        "destroys_temporal_order": bool(metadata.get("destroys_temporal_order", False)),
        "state_updates_enabled": bool(metadata.get("state_updates_enabled", False)),
    }


def aggregate(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault((row["task"], row["variant"]), []).append(row)
    aggregates: list[dict[str, Any]] = []
    for (task, variant), items in sorted(grouped.items()):
        label_counts = [float(item["labels_to_threshold"]) for item in items if item.get("labels_to_threshold") is not None]
        aggregates.append(
            {
                "task": task,
                "variant": variant,
                "variant_family": VARIANTS[variant].family,
                "runs": len(items),
                "temporal_pressure": bool(items[0].get("temporal_pressure", False)),
                "mean_ridge_probe_accuracy": mean(float(i["ridge_probe_accuracy"]) for i in items),
                "min_ridge_probe_accuracy": min(float(i["ridge_probe_accuracy"]) for i in items),
                "std_ridge_probe_accuracy": stdev(float(i["ridge_probe_accuracy"]) for i in items),
                "mean_centroid_probe_accuracy": mean(float(i["centroid_probe_accuracy"]) for i in items),
                "mean_knn_probe_accuracy": mean(float(i["knn_probe_accuracy"]) for i in items),
                "min_knn_probe_accuracy": min(float(i["knn_probe_accuracy"]) for i in items),
                "mean_silhouette_score": mean(float(i["silhouette_score"]) for i in items if i.get("silhouette_score") is not None),
                "mean_latent_factor_abs_corr": mean(float(i["latent_factor_abs_corr"]) for i in items if i.get("latent_factor_abs_corr") is not None),
                "mean_labels_to_threshold": mean(label_counts),
                "min_labels_to_threshold": min(label_counts) if label_counts else None,
                "max_abs_raw_dopamine": max(abs(float(i.get("max_abs_raw_dopamine", 0.0) or 0.0)) for i in items),
                "label_leakage_runs": sum(int(bool(i.get("labels_visible_during_exposure", False))) for i in items if not bool(i.get("uses_hidden_labels", False))),
                "reward_leakage_runs": sum(int(bool(i.get("reward_visible_during_exposure", False))) for i in items),
            }
        )
    return aggregates


def by_task_variant(aggregates: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    return {(str(row["task"]), str(row["variant"])): row for row in aggregates}


def build_comparisons(aggregates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    lookup = by_task_variant(aggregates)
    tasks = sorted({str(row["task"]) for row in aggregates})
    control_names = [
        "no_state_plasticity",
        "time_shuffled_exposure",
        "temporal_destroyed_exposure",
        "current_input_only",
        "rolling_history_input",
        "random_projection_history",
        "random_untrained_state",
        "oracle_latent_upper_bound",
    ]
    comparisons = []
    for task in tasks:
        cand = lookup.get((task, CANDIDATE))
        if not cand:
            continue
        row: dict[str, Any] = {
            "task": task,
            "temporal_pressure": bool(cand.get("temporal_pressure", False)),
            "candidate_ridge_accuracy": cand.get("mean_ridge_probe_accuracy"),
            "candidate_min_ridge_accuracy": cand.get("min_ridge_probe_accuracy"),
            "candidate_knn_accuracy": cand.get("mean_knn_probe_accuracy"),
            "candidate_silhouette": cand.get("mean_silhouette_score"),
            "candidate_labels_to_threshold": cand.get("mean_labels_to_threshold"),
        }
        best_non_oracle = ("", -1.0)
        for control in control_names:
            ctrl = lookup.get((task, control))
            if not ctrl:
                continue
            acc = float(ctrl.get("mean_ridge_probe_accuracy") or 0.0)
            row[f"{control}_ridge_accuracy"] = acc
            row[f"candidate_delta_vs_{control}"] = float(cand.get("mean_ridge_probe_accuracy") or 0.0) - acc
            row[f"{control}_labels_to_threshold"] = ctrl.get("mean_labels_to_threshold")
            if control != "oracle_latent_upper_bound" and acc > best_non_oracle[1]:
                best_non_oracle = (control, acc)
        row["best_non_oracle_control"] = best_non_oracle[0]
        row["best_non_oracle_ridge_accuracy"] = best_non_oracle[1] if best_non_oracle[0] else None
        row["candidate_delta_vs_best_non_oracle"] = (
            float(cand.get("mean_ridge_probe_accuracy") or 0.0) - best_non_oracle[1]
            if best_non_oracle[0]
            else None
        )
        comparisons.append(row)
    return comparisons


def evaluate_criteria(
    *,
    aggregates: list[dict[str, Any]],
    comparisons: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    tasks: list[str],
    variants: list[str],
    seeds: list[int],
    args: argparse.Namespace,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    expected_runs = len(tasks) * len(variants) * len(seeds)
    observed_runs = len(rows)
    non_oracle_rows = [r for r in rows if not bool(r.get("uses_hidden_labels", False))]
    label_leakage = sum(int(bool(r.get("labels_visible_during_exposure", False))) for r in non_oracle_rows)
    reward_leakage = sum(int(bool(r.get("reward_visible_during_exposure", False))) for r in rows)
    max_abs_da = max([abs(float(r.get("max_abs_raw_dopamine", 0.0) or 0.0)) for r in non_oracle_rows] or [0.0])
    cand_rows = [r for r in aggregates if r.get("variant") == CANDIDATE]
    cand_min_ridge = min([float(r.get("min_ridge_probe_accuracy") or 0.0) for r in cand_rows] or [0.0])
    cand_min_knn = min([float(r.get("min_knn_probe_accuracy") or 0.0) for r in cand_rows] or [0.0])
    no_plasticity_edges = [float(c.get("candidate_delta_vs_no_state_plasticity") or 0.0) for c in comparisons]
    random_edges = [float(c.get("candidate_delta_vs_random_untrained_state") or 0.0) for c in comparisons]
    shuffled_edges = [float(c.get("candidate_delta_vs_time_shuffled_exposure") or 0.0) for c in comparisons if c.get("temporal_pressure")]
    destroyed_edges = [float(c.get("candidate_delta_vs_temporal_destroyed_exposure") or 0.0) for c in comparisons if c.get("temporal_pressure")]
    input_edges = [float(c.get("candidate_delta_vs_current_input_only") or 0.0) for c in comparisons if c.get("temporal_pressure")]
    non_encoder_wins = sum(1 for edge in input_edges if edge >= float(args.min_edge_vs_current_input))
    temporal_control_losses = sum(1 for edge in shuffled_edges + destroyed_edges if edge >= float(args.min_temporal_control_edge))

    sample_efficiency_wins = 0
    for c in comparisons:
        cand_labels = c.get("candidate_labels_to_threshold")
        no_plasticity_labels = c.get("no_state_plasticity_labels_to_threshold")
        shuffled_labels = c.get("time_shuffled_exposure_labels_to_threshold")
        if cand_labels is None:
            continue
        win_count = 0
        for other in [no_plasticity_labels, shuffled_labels]:
            if other is None or float(cand_labels) <= float(other):
                win_count += 1
        if win_count >= 1:
            sample_efficiency_wins += 1

    base = [
        criterion("task/variant/seed matrix completed", observed_runs, "==", expected_runs, observed_runs == expected_runs),
        criterion("non-oracle exposure has no hidden-label leakage", label_leakage, "==", 0, label_leakage == 0),
        criterion("exposure has no reward visibility", reward_leakage, "==", 0, reward_leakage == 0),
        criterion("pre-reward raw dopamine remains zero", max_abs_da, "<=", args.max_abs_raw_dopamine, max_abs_da <= float(args.max_abs_raw_dopamine)),
    ]
    science = [
        criterion("candidate reaches minimum ridge-probe accuracy", cand_min_ridge, ">=", args.min_candidate_probe_accuracy, cand_min_ridge >= float(args.min_candidate_probe_accuracy)),
        criterion("candidate reaches minimum kNN-probe accuracy", cand_min_knn, ">=", args.min_candidate_knn_accuracy, cand_min_knn >= float(args.min_candidate_knn_accuracy)),
        criterion("candidate beats no-state-plasticity control", min(no_plasticity_edges) if no_plasticity_edges else None, ">=", args.min_edge_vs_no_plasticity, bool(no_plasticity_edges) and min(no_plasticity_edges) >= float(args.min_edge_vs_no_plasticity)),
        criterion("candidate beats random untrained state", min(random_edges) if random_edges else None, ">=", args.min_edge_vs_random, bool(random_edges) and min(random_edges) >= float(args.min_edge_vs_random)),
        criterion("temporal shams lose on temporal-pressure tasks", temporal_control_losses, ">=", args.min_temporal_control_losses, temporal_control_losses >= int(args.min_temporal_control_losses)),
        criterion("candidate beats current-input-only on temporal-pressure tasks", non_encoder_wins, ">=", args.min_non_encoder_wins, non_encoder_wins >= int(args.min_non_encoder_wins)),
        criterion("candidate improves downstream sample efficiency somewhere", sample_efficiency_wins, ">=", args.min_sample_efficiency_wins, sample_efficiency_wins >= int(args.min_sample_efficiency_wins)),
    ]
    criteria = base if args.smoke else base + science
    summary = {
        "expected_runs": expected_runs,
        "observed_runs": observed_runs,
        "tasks": tasks,
        "variants": variants,
        "seeds": seeds,
        "candidate_min_ridge_probe_accuracy": cand_min_ridge,
        "candidate_min_knn_probe_accuracy": cand_min_knn,
        "non_oracle_label_leakage_runs": label_leakage,
        "reward_leakage_runs": reward_leakage,
        "max_abs_raw_dopamine_non_oracle": max_abs_da,
        "temporal_control_losses": temporal_control_losses,
        "non_encoder_wins": non_encoder_wins,
        "sample_efficiency_wins": sample_efficiency_wins,
        "claim_boundary": "Noncanonical software diagnostic: CRA-compatible label-free representation scaffold, offline probes only, not hardware/on-chip representation learning or a v2.0 freeze.",
    }
    return criteria, summary


def plot_representation_matrix(path: Path, aggregates: list[dict[str, Any]], variants: list[str]) -> None:
    if plt is None:
        path.with_suffix(".txt").write_text(f"matplotlib unavailable: {MATPLOTLIB_ERROR}\n", encoding="utf-8")
        return
    tasks = sorted({str(r["task"]) for r in aggregates})
    lookup = by_task_variant(aggregates)
    data = np.zeros((len(tasks), len(variants)), dtype=float)
    for i, task in enumerate(tasks):
        for j, variant in enumerate(variants):
            data[i, j] = float((lookup.get((task, variant)) or {}).get("mean_ridge_probe_accuracy") or 0.0)
    fig, ax = plt.subplots(figsize=(max(10, len(variants) * 1.2), 4.8))
    im = ax.imshow(data, vmin=0.0, vmax=1.0, cmap="viridis", aspect="auto")
    ax.set_xticks(np.arange(len(variants)))
    ax.set_xticklabels([v.replace("_", "\n") for v in variants], rotation=0, fontsize=8)
    ax.set_yticks(np.arange(len(tasks)))
    ax.set_yticklabels([t.replace("_", " ") for t in tasks])
    ax.set_title("Tier 5.17 frozen-representation ridge probe accuracy")
    for i in range(len(tasks)):
        for j in range(len(variants)):
            ax.text(j, i, f"{data[i, j]:.2f}", ha="center", va="center", color="white" if data[i, j] < 0.55 else "black", fontsize=8)
    fig.colorbar(im, ax=ax, label="accuracy")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_control_edges(path: Path, comparisons: list[dict[str, Any]]) -> None:
    if plt is None:
        path.with_suffix(".txt").write_text(f"matplotlib unavailable: {MATPLOTLIB_ERROR}\n", encoding="utf-8")
        return
    labels = [str(c["task"]).replace("_", "\n") for c in comparisons]
    edge_names = [
        "candidate_delta_vs_no_state_plasticity",
        "candidate_delta_vs_time_shuffled_exposure",
        "candidate_delta_vs_current_input_only",
        "candidate_delta_vs_random_untrained_state",
    ]
    x = np.arange(len(labels))
    width = 0.18
    fig, ax = plt.subplots(figsize=(12, 5.6))
    for offset, name in enumerate(edge_names):
        vals = [float(c.get(name) or 0.0) for c in comparisons]
        ax.bar(x + (offset - 1.5) * width, vals, width, label=name.replace("candidate_delta_vs_", "vs ").replace("_", " "))
    ax.axhline(0.0, color="black", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("ridge accuracy edge")
    ax.set_title("Tier 5.17 candidate edge against controls")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def write_fairness_contract(path: Path, args: argparse.Namespace, tasks: list[str], variants: list[str], seeds: list[int]) -> None:
    write_json(
        path,
        {
            "tier": TIER,
            "generated_at_utc": utc_now(),
            "claim_boundary": "Software-only, noncanonical pre-reward representation diagnostic. Hidden labels are used only after exposure for probes, except oracle upper bound rows which are explicitly excluded from no-leakage promotion checks.",
            "exposure_rules": [
                "No non-oracle variant receives latent labels during representation exposure.",
                "No variant receives reward, correctness, dopamine, or downstream task outcome during representation exposure.",
                "Representations are snapshotted/frozen before offline probes read hidden labels.",
                "Current-input and rolling-history encoders are included to test whether the visible encoder alone explains the result.",
                "Time-shuffled and temporal-destroyed controls preserve visible sample statistics while damaging order information.",
                "Oracle latent upper bound is reported but cannot support a no-leakage claim.",
            ],
            "tasks": tasks,
            "variants": variants,
            "seeds": seeds,
            "steps": int(args.steps),
            "smoke": bool(args.smoke),
            "probe_train_fraction": float(args.probe_train_fraction),
        },
    )


def write_report(path: Path, result: dict[str, Any], aggregates: list[dict[str, Any]], comparisons: list[dict[str, Any]], args: argparse.Namespace) -> None:
    lines = [
        "# Tier 5.17 Pre-Reward Representation Formation Findings",
        "",
        f"- Generated: `{result['generated_at_utc']}`",
        f"- Status: **{result['status'].upper()}**",
        f"- Output directory: `{result['output_dir']}`",
        f"- Tasks: `{', '.join(result['summary']['tasks'])}`",
        f"- Seeds: `{result['summary']['seeds']}`",
        "",
        "Tier 5.17 asks whether a CRA-compatible label-free state module can form useful latent structure before labels, reward, correctness feedback, or dopamine are introduced.",
        "",
        "## Claim Boundary",
        "",
        "- Noncanonical software diagnostic evidence only.",
        "- Exposure is label-free and reward-free for all non-oracle rows.",
        "- Hidden labels are used only after frozen/snapshotted representations are produced, for offline probes.",
        "- This is not SpiNNaker hardware evidence, native/custom-C on-chip representation learning, language, planning, AGI, or a v2.0 freeze.",
        "- The oracle row is an upper bound and is excluded from no-leakage promotion checks.",
        "",
        "## Summary",
        "",
        f"- expected_runs: `{result['summary']['expected_runs']}`",
        f"- observed_runs: `{result['summary']['observed_runs']}`",
        f"- candidate_min_ridge_probe_accuracy: `{markdown_value(result['summary']['candidate_min_ridge_probe_accuracy'])}`",
        f"- candidate_min_knn_probe_accuracy: `{markdown_value(result['summary']['candidate_min_knn_probe_accuracy'])}`",
        f"- non_oracle_label_leakage_runs: `{result['summary']['non_oracle_label_leakage_runs']}`",
        f"- reward_leakage_runs: `{result['summary']['reward_leakage_runs']}`",
        f"- max_abs_raw_dopamine_non_oracle: `{markdown_value(result['summary']['max_abs_raw_dopamine_non_oracle'])}`",
        f"- temporal_control_losses: `{result['summary']['temporal_control_losses']}`",
        f"- non_encoder_wins: `{result['summary']['non_encoder_wins']}`",
        f"- sample_efficiency_wins: `{result['summary']['sample_efficiency_wins']}`",
        "",
        "## Comparisons",
        "",
        "| Task | Candidate ridge | No-plasticity | Time-shuffled | Input-only | History-only | Random projection | Oracle | Edge vs best non-oracle |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    comparison_columns = [
        "task",
        "candidate_ridge_accuracy",
        "no_state_plasticity_ridge_accuracy",
        "time_shuffled_exposure_ridge_accuracy",
        "current_input_only_ridge_accuracy",
        "rolling_history_input_ridge_accuracy",
        "random_projection_history_ridge_accuracy",
        "oracle_latent_upper_bound_ridge_accuracy",
        "candidate_delta_vs_best_non_oracle",
    ]
    for row in comparisons:
        values = {key: markdown_value(row.get(key)) for key in comparison_columns}
        lines.append(
            "| {task} | {candidate_ridge_accuracy} | {no_state_plasticity_ridge_accuracy} | {time_shuffled_exposure_ridge_accuracy} | {current_input_only_ridge_accuracy} | {rolling_history_input_ridge_accuracy} | {random_projection_history_ridge_accuracy} | {oracle_latent_upper_bound_ridge_accuracy} | {candidate_delta_vs_best_non_oracle} |".format(
                **values
            )
        )
    lines.extend(
        [
            "",
            "## Criteria",
            "",
            "| Criterion | Value | Rule | Pass | Note |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for item in result["criteria"]:
        lines.append(
            f"| {item['name']} | {markdown_value(item.get('value'))} | {item.get('operator')} {markdown_value(item.get('threshold'))} | {'yes' if item.get('passed') else 'no'} | {item.get('note', '')} |"
        )
    if result.get("failure_reason"):
        lines.extend(["", f"Failure: {result['failure_reason']}"])
    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            "- `tier5_17_results.json`: machine-readable manifest.",
            "- `tier5_17_report.md`: human findings and claim boundary.",
            "- `tier5_17_summary.csv`: aggregate probe metrics by task and variant.",
            "- `tier5_17_comparisons.csv`: candidate edges against controls.",
            "- `tier5_17_fairness_contract.json`: no-label/no-reward exposure contract.",
            "- `tier5_17_representation_matrix.png`: ridge-probe accuracy heatmap.",
            "- `tier5_17_control_edges.png`: candidate-control edge plot.",
            "",
            "![representation_matrix](tier5_17_representation_matrix.png)",
            "",
            "![control_edges](tier5_17_control_edges.png)",
        ]
    )
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_latest(output_dir: Path, manifest_json: Path, report_md: Path, status: str) -> None:
    write_json(
        ROOT / "controlled_test_output" / "tier5_17_latest_manifest.json",
        {
            "tier": TIER,
            "status": status,
            "canonical": False,
            "output_dir": str(output_dir),
            "manifest_json": str(manifest_json),
            "report_md": str(report_md),
            "updated_at_utc": utc_now(),
        },
    )


def run(args: argparse.Namespace) -> dict[str, Any]:
    started = time.perf_counter()
    random.seed(int(args.base_seed))
    np.random.seed(int(args.base_seed))
    tasks = selected_tasks(args)
    variants = selected_variants(args)
    seeds = seeds_from_args(args)
    if args.smoke:
        tasks = tasks[:1]
        variants = [CANDIDATE, "no_state_plasticity", "time_shuffled_exposure", "current_input_only", "random_untrained_state"]
        seeds = seeds[:1]

    output_dir = Path(args.output_dir) if args.output_dir else ROOT / "controlled_test_output" / f"tier5_17_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    output_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    for seed in seeds:
        for task_name in tasks:
            task = build_task(task_name, steps=int(args.steps if not args.smoke else min(args.steps, args.smoke_steps)), seed=seed)
            for variant_name in variants:
                print(f"[tier5.17] task={task_name} variant={variant_name} seed={seed}", flush=True)
                variant = VARIANTS[variant_name]
                reps, metadata = representations_for_variant(task, variant, seed=seed, args=args)
                row = evaluate_representation(task, variant_name, reps, metadata, seed=seed, args=args)
                rows.append(row)

    aggregates = aggregate(rows)
    comparisons = build_comparisons(aggregates)
    criteria, summary = evaluate_criteria(
        aggregates=aggregates,
        comparisons=comparisons,
        rows=rows,
        tasks=tasks,
        variants=variants,
        seeds=seeds,
        args=args,
    )
    status, failure_reason = pass_fail(criteria)

    summary_csv = output_dir / "tier5_17_summary.csv"
    run_csv = output_dir / "tier5_17_runs.csv"
    comparisons_csv = output_dir / "tier5_17_comparisons.csv"
    fairness_json = output_dir / "tier5_17_fairness_contract.json"
    matrix_png = output_dir / "tier5_17_representation_matrix.png"
    edges_png = output_dir / "tier5_17_control_edges.png"
    manifest_json = output_dir / "tier5_17_results.json"
    report_md = output_dir / "tier5_17_report.md"

    write_csv(run_csv, rows)
    write_csv(summary_csv, aggregates)
    write_csv(comparisons_csv, comparisons)
    write_fairness_contract(fairness_json, args, tasks, variants, seeds)
    plot_representation_matrix(matrix_png, aggregates, variants)
    plot_control_edges(edges_png, comparisons)

    result = {
        "name": TIER,
        "status": status,
        "generated_at_utc": utc_now(),
        "output_dir": str(output_dir),
        "failure_reason": failure_reason,
        "summary": {**summary, "runtime_seconds": time.perf_counter() - started},
        "criteria": criteria,
        "artifacts": {
            "manifest_json": str(manifest_json),
            "report_md": str(report_md),
            "run_csv": str(run_csv),
            "summary_csv": str(summary_csv),
            "comparisons_csv": str(comparisons_csv),
            "fairness_contract_json": str(fairness_json),
            "representation_matrix_png": str(matrix_png),
            "control_edges_png": str(edges_png),
        },
        "canonical": False,
        "claim_boundary": summary["claim_boundary"],
    }
    write_json(manifest_json, result)
    write_report(report_md, result, aggregates, comparisons, args)
    if not bool(args.smoke):
        write_latest(output_dir, manifest_json, report_md, status)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks", default=DEFAULT_TASKS)
    parser.add_argument("--variants", default=DEFAULT_VARIANTS)
    parser.add_argument("--steps", type=int, default=520)
    parser.add_argument("--smoke-steps", type=int, default=180)
    parser.add_argument("--seed-count", type=int, default=3)
    parser.add_argument("--seeds", default="42,43,44")
    parser.add_argument("--base-seed", type=int, default=42)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--smoke", action="store_true", help="Run harness integrity gates only; science gates are skipped.")
    parser.add_argument("--stop-on-fail", action="store_true")
    parser.add_argument("--prototype-count", type=int, default=14)
    parser.add_argument("--representation-dim", type=int, default=58)
    parser.add_argument("--feature-history", type=int, default=3)
    parser.add_argument("--history-length", type=int, default=5)
    parser.add_argument("--random-projection-dim", type=int, default=22)
    parser.add_argument("--label-free-lr", type=float, default=0.08)
    parser.add_argument("--trace-decay", type=float, default=0.988)
    parser.add_argument("--prototype-temperature", type=float, default=0.85)
    parser.add_argument("--probe-train-fraction", type=float, default=0.55)
    parser.add_argument("--knn-k", type=int, default=5)
    parser.add_argument("--sample-efficiency-threshold", type=float, default=0.78)
    parser.add_argument("--max-abs-raw-dopamine", type=float, default=1e-12)
    parser.add_argument("--min-candidate-probe-accuracy", type=float, default=0.72)
    parser.add_argument("--min-candidate-knn-accuracy", type=float, default=0.70)
    parser.add_argument("--min-edge-vs-no-plasticity", type=float, default=0.05)
    parser.add_argument("--min-edge-vs-random", type=float, default=0.20)
    parser.add_argument("--min-temporal-control-edge", type=float, default=0.05)
    parser.add_argument("--min-temporal-control-losses", type=int, default=2)
    parser.add_argument("--min-edge-vs-current-input", type=float, default=0.05)
    parser.add_argument("--min-non-encoder-wins", type=int, default=2)
    parser.add_argument("--min-sample-efficiency-wins", type=int, default=2)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = run(args)
    print(json.dumps(json_safe({"status": result["status"], "summary": result["summary"], "output_dir": result["output_dir"]}), indent=2, sort_keys=True))
    if args.stop_on_fail and result["status"] != "pass":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
