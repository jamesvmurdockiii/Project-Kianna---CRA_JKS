#!/usr/bin/env python3
"""Tier 5.17c intrinsic predictive preexposure diagnostic.

Tier 5.17 failed because the no-history-input scaffold did not prove useful
pre-reward representation formation. Tier 5.17b classified the failure and
pointed to a specific repair: give CRA a label-free intrinsic reason to organize
unlabeled streams before reward arrives.

This tier tests that repair with self-supervised predictive preexposure. During
preexposure, non-oracle variants receive no hidden labels, no reward, no task
correctness, and zero dopamine. The candidate learns only from visible
stream-continuation targets such as masked-channel or next-state prediction.
Frozen representations are then evaluated by offline probes and downstream
sample-efficiency checks.

A pass is still noncanonical software evidence only. It is not hardware evidence,
not native/custom-C on-chip representation learning, not language, not full world
modeling, and not a v2.0 freeze.
"""

from __future__ import annotations

import argparse
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
from tier5_unsupervised_representation import (  # noqa: E402
    centroid_probe_accuracy,
    knn_probe_accuracy,
    labels_to_threshold,
    latent_factor_corr,
    make_short_history_features,
    ridge_probe_accuracy,
    silhouette_score,
    stable_standardize,
)

TIER = "Tier 5.17c - Intrinsic Predictive Preexposure"
DEFAULT_TASKS = "masked_channel_context,long_gap_temporal_continuation,same_visible_different_latent"
DEFAULT_VARIANTS = (
    "intrinsic_predictive_preexposure,no_preexposure,shuffled_time_preexposure,"
    "target_shuffled_preexposure,wrong_domain_preexposure,current_input_only,"
    "fixed_history_baseline,random_projection_history,reservoir_baseline,"
    "stdp_only_unsupervised,oracle_latent_upper_bound"
)
CANDIDATE = "intrinsic_predictive_preexposure"
EPS = 1e-12


@dataclass(frozen=True)
class PredictivePreexposureTask:
    name: str
    display_name: str
    description: str
    encoder_input: np.ndarray
    intrinsic_target: np.ndarray
    latent_labels: np.ndarray
    latent_factor: np.ndarray
    temporal_pressure: bool
    metadata: dict[str, Any]

    @property
    def steps(self) -> int:
        return int(self.encoder_input.shape[0])


@dataclass(frozen=True)
class VariantSpec:
    name: str
    family: str
    description: str
    uses_hidden_labels: bool = False
    uses_intrinsic_target: bool = False
    destroys_temporal_order: bool = False
    wrong_domain: bool = False
    target_shuffled: bool = False


VARIANTS: dict[str, VariantSpec] = {
    "intrinsic_predictive_preexposure": VariantSpec(
        name="intrinsic_predictive_preexposure",
        family="candidate",
        description="label-free recurrent predictor trained on visible stream-continuation targets",
        uses_intrinsic_target=True,
    ),
    "no_preexposure": VariantSpec(
        name="no_preexposure",
        family="candidate ablation",
        description="same predictor shell with learning and recurrent state updates disabled",
    ),
    "shuffled_time_preexposure": VariantSpec(
        name="shuffled_time_preexposure",
        family="temporal sham",
        description="same candidate trained on the same input/target pairs in shuffled temporal order",
        uses_intrinsic_target=True,
        destroys_temporal_order=True,
    ),
    "target_shuffled_preexposure": VariantSpec(
        name="target_shuffled_preexposure",
        family="binding sham",
        description="same candidate trained on a shuffled intrinsic target sequence",
        uses_intrinsic_target=True,
        target_shuffled=True,
    ),
    "wrong_domain_preexposure": VariantSpec(
        name="wrong_domain_preexposure",
        family="domain sham",
        description="same candidate trained on a mismatched stream from a different task family",
        uses_intrinsic_target=True,
        wrong_domain=True,
    ),
    "current_input_only": VariantSpec(
        name="current_input_only",
        family="encoder-only baseline",
        description="probe sees only current visible encoder input; no learned state",
    ),
    "fixed_history_baseline": VariantSpec(
        name="fixed_history_baseline",
        family="history baseline",
        description="probe sees a fixed short input history; no learned predictive state",
    ),
    "random_projection_history": VariantSpec(
        name="random_projection_history",
        family="history baseline",
        description="fixed random projection of short visible-input history",
    ),
    "reservoir_baseline": VariantSpec(
        name="reservoir_baseline",
        family="sequence baseline",
        description="fixed random recurrent reservoir driven by visible input only",
    ),
    "stdp_only_unsupervised": VariantSpec(
        name="stdp_only_unsupervised",
        family="unsupervised SNN-style baseline",
        description="competitive Hebbian/prototype state without predictive target binding",
    ),
    "oracle_latent_upper_bound": VariantSpec(
        name="oracle_latent_upper_bound",
        family="oracle upper bound",
        description="hidden latent one-hot upper bound; excluded from no-leakage checks",
        uses_hidden_labels=True,
    ),
}


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


def one_hot(labels: np.ndarray, count: int | None = None) -> np.ndarray:
    labels = np.asarray(labels, dtype=int)
    if count is None:
        count = int(np.max(labels)) + 1
    out = np.zeros((labels.size, int(count)), dtype=float)
    out[np.arange(labels.size), labels] = 1.0
    return out


def make_masked_channel_context(*, steps: int, seed: int) -> PredictivePreexposureTask:
    rng = np.random.default_rng(seed + 5101)
    labels = np.zeros(steps, dtype=int)
    encoder = np.zeros((steps, 4), dtype=float)
    target = np.zeros((steps, 2), dtype=float)
    context = int(rng.integers(0, 4))
    next_switch = 0
    cue = np.zeros(4, dtype=float)
    context_values = np.asarray([-1.05, -0.35, 0.35, 1.05], dtype=float)
    for t in range(steps):
        if t >= next_switch:
            context = int((context + int(rng.integers(1, 4))) % 4)
            cue = np.zeros(4, dtype=float)
            cue[context] = 1.0
            next_switch = t + int(rng.integers(58, 96))
        labels[t] = context
        phase = math.sin(t / 7.0)
        nuisance = rng.normal(0.0, 0.55)
        # The cue is brief. After decay, current input marginals are similar;
        # the self-supervised masked target remains context-dependent.
        cue_drive = cue.copy()
        encoder[t] = np.asarray(
            [
                cue_drive[0] - cue_drive[2] + rng.normal(0.0, 0.035),
                cue_drive[1] - cue_drive[3] + rng.normal(0.0, 0.035),
                0.25 * phase + 0.15 * nuisance,
                rng.normal(0.0, 0.35),
            ],
            dtype=float,
        )
        val = context_values[context]
        target[t] = np.asarray(
            [
                val + 0.18 * math.sin(t / 13.0) + rng.normal(0.0, 0.08),
                (1.0 if context in (1, 3) else -1.0) + 0.12 * math.cos(t / 17.0) + rng.normal(0.0, 0.08),
            ],
            dtype=float,
        )
        cue *= 0.70
    return PredictivePreexposureTask(
        name="masked_channel_context",
        display_name="Masked Channel Context",
        description="brief context cues must support prediction of a masked visible channel through long ambiguous spans",
        encoder_input=stable_standardize(encoder),
        intrinsic_target=stable_standardize(target),
        latent_labels=labels,
        latent_factor=labels.astype(float),
        temporal_pressure=True,
        metadata={"intrinsic_objective": "masked_channel_prediction", "labels_visible_during_exposure": False},
    )


def make_long_gap_temporal_continuation(*, steps: int, seed: int) -> PredictivePreexposureTask:
    rng = np.random.default_rng(seed + 6203)
    labels = np.zeros(steps, dtype=int)
    encoder = np.zeros((steps, 4), dtype=float)
    target = np.zeros((steps, 2), dtype=float)
    state = int(rng.integers(0, 3))
    next_switch = 0
    cue_amp = 0.0
    cue_sign = 0.0
    phases = np.asarray([0.0, 2.0 * math.pi / 3.0, 4.0 * math.pi / 3.0], dtype=float)
    for t in range(steps):
        if t >= next_switch:
            state = int((state + int(rng.integers(1, 3))) % 3)
            cue_amp = 1.0
            cue_sign = [-1.0, 0.0, 1.0][state]
            next_switch = t + int(rng.integers(70, 118))
        labels[t] = state
        local = rng.choice([-1.0, 1.0])
        encoder[t] = np.asarray(
            [
                cue_amp * cue_sign + rng.normal(0.0, 0.04),
                local + rng.normal(0.0, 0.22),
                0.45 * math.sin(t / 5.0) + rng.normal(0.0, 0.18),
                rng.normal(0.0, 0.42),
            ],
            dtype=float,
        )
        # Continuation target is a label-free future waveform governed by the
        # hidden state; the current local symbol is intentionally distracting.
        target[t] = np.asarray(
            [
                math.sin(t / 9.0 + phases[state]) + rng.normal(0.0, 0.08),
                math.cos(t / 11.0 + phases[state]) + rng.normal(0.0, 0.08),
            ],
            dtype=float,
        )
        cue_amp *= 0.68
    return PredictivePreexposureTask(
        name="long_gap_temporal_continuation",
        display_name="Long-Gap Temporal Continuation",
        description="brief cues determine future visible continuation over gaps longer than fixed history",
        encoder_input=stable_standardize(encoder),
        intrinsic_target=stable_standardize(target),
        latent_labels=labels,
        latent_factor=labels.astype(float),
        temporal_pressure=True,
        metadata={"intrinsic_objective": "next_state_continuation", "labels_visible_during_exposure": False},
    )


def make_same_visible_different_latent(*, steps: int, seed: int) -> PredictivePreexposureTask:
    rng = np.random.default_rng(seed + 7307)
    labels = np.zeros(steps, dtype=int)
    encoder = np.zeros((steps, 4), dtype=float)
    target = np.zeros((steps, 2), dtype=float)
    context = int(rng.integers(0, 2))
    substate = int(rng.integers(0, 2))
    next_context = 0
    cue = 0.0
    for t in range(steps):
        if t >= next_context:
            context = 1 - context
            cue = 1.0 if context else -1.0
            next_context = t + int(rng.integers(64, 102))
        if rng.random() < 0.09:
            substate = 1 - substate
        label = context * 2 + substate
        labels[t] = label
        visible_symbol = 1.0 if substate else -1.0
        # Current input carries substate and a decayed context cue only. After
        # the cue fades, the same visible symbol has different latent meaning.
        encoder[t] = np.asarray(
            [
                cue + rng.normal(0.0, 0.035),
                visible_symbol + rng.normal(0.0, 0.2),
                visible_symbol * math.sin(t / 8.0) + rng.normal(0.0, 0.18),
                rng.normal(0.0, 0.38),
            ],
            dtype=float,
        )
        sign = (1.0 if context else -1.0) * visible_symbol
        target[t] = np.asarray(
            [
                sign + 0.15 * math.sin(t / 10.0) + rng.normal(0.0, 0.08),
                (1.0 if label in (1, 2) else -1.0) + rng.normal(0.0, 0.08),
            ],
            dtype=float,
        )
        cue *= 0.66
    return PredictivePreexposureTask(
        name="same_visible_different_latent",
        display_name="Same Visible, Different Latent",
        description="same current symbol requires retained context to predict the visible continuation",
        encoder_input=stable_standardize(encoder),
        intrinsic_target=stable_standardize(target),
        latent_labels=labels,
        latent_factor=labels.astype(float),
        temporal_pressure=True,
        metadata={"intrinsic_objective": "contextual_continuation_prediction", "labels_visible_during_exposure": False},
    )


def build_task(name: str, *, steps: int, seed: int) -> PredictivePreexposureTask:
    if name == "masked_channel_context":
        return make_masked_channel_context(steps=steps, seed=seed)
    if name == "long_gap_temporal_continuation":
        return make_long_gap_temporal_continuation(steps=steps, seed=seed)
    if name == "same_visible_different_latent":
        return make_same_visible_different_latent(steps=steps, seed=seed)
    raise ValueError(f"unknown task {name}")


class IntrinsicPredictiveEncoder:
    """Label-free recurrent predictor used only for Tier 5.17c diagnostics."""

    def __init__(
        self,
        *,
        input_dim: int,
        target_dim: int,
        state_dim: int,
        seed: int,
        lr: float,
        state_decay: float,
        update_enabled: bool = True,
        state_enabled: bool = True,
    ) -> None:
        self.rng = np.random.default_rng(seed)
        self.input_dim = int(input_dim)
        self.target_dim = int(target_dim)
        self.state_dim = int(state_dim)
        self.lr = float(lr)
        self.state_decay = float(state_decay)
        self.update_enabled = bool(update_enabled)
        self.state_enabled = bool(state_enabled)
        feature_dim = self.input_dim + self.state_dim + 1
        self.w = self.rng.normal(0.0, 0.06, size=(self.target_dim, feature_dim))
        self.state_in = self.rng.normal(0.0, 0.35, size=(self.state_dim, self.input_dim))
        self.state_pred = self.rng.normal(0.0, 0.25, size=(self.state_dim, self.target_dim))
        self.state_err = self.rng.normal(0.0, 0.22, size=(self.state_dim, self.target_dim))
        self.state = np.zeros(self.state_dim, dtype=float)
        self.step_index = 0

    def step(self, x: np.ndarray, target: np.ndarray | None) -> np.ndarray:
        x = np.asarray(x, dtype=float).reshape(-1)
        if x.size != self.input_dim:
            raise ValueError(f"expected input_dim={self.input_dim}, got {x.size}")
        feature = np.concatenate([x, self.state, np.ones(1, dtype=float)])
        pred = self.w @ feature
        pre_state = self.state.copy()
        if target is None:
            error = np.zeros(self.target_dim, dtype=float)
        else:
            y = np.asarray(target, dtype=float).reshape(-1)
            if y.size != self.target_dim:
                raise ValueError(f"expected target_dim={self.target_dim}, got {y.size}")
            error = y - pred
            if self.update_enabled:
                lr = self.lr / math.sqrt(1.0 + 0.0015 * self.step_index)
                self.w += lr * np.outer(error, feature)
                # Mild regularization keeps the diagnostic stable without labels.
                self.w *= 0.9995
        if self.state_enabled:
            drive = self.state_in @ x + self.state_pred @ pred + self.state_err @ error
            candidate = np.tanh(drive)
            self.state = self.state_decay * self.state + (1.0 - self.state_decay) * candidate
        else:
            self.state = np.zeros_like(self.state)
        self.step_index += 1
        # Return the pre-update representation. The intrinsic target may update
        # future state, but it cannot be read back into the same timestep probe.
        return np.concatenate([x, pred, pre_state])


def reservoir_representations(task: PredictivePreexposureTask, *, seed: int, state_dim: int) -> np.ndarray:
    rng = np.random.default_rng(seed + 8101)
    x = np.asarray(task.encoder_input, dtype=float)
    win = rng.normal(0.0, 0.55, size=(state_dim, x.shape[1]))
    wrec = rng.normal(0.0, 0.18, size=(state_dim, state_dim))
    # Normalize spectral scale cheaply.
    radius = max(1e-6, float(np.max(np.sum(np.abs(wrec), axis=1))))
    wrec = wrec / radius * 0.85
    state = np.zeros(state_dim, dtype=float)
    rows = []
    for row in x:
        state = np.tanh(win @ row + wrec @ state)
        rows.append(np.concatenate([row, state]))
    return stable_standardize(np.vstack(rows))


def stdp_only_representations(task: PredictivePreexposureTask, *, seed: int, prototype_count: int, lr: float) -> np.ndarray:
    rng = np.random.default_rng(seed + 9203)
    x = np.asarray(task.encoder_input, dtype=float)
    centers = rng.normal(0.0, 0.4, size=(prototype_count, x.shape[1]))
    centers /= np.linalg.norm(centers, axis=1, keepdims=True) + EPS
    trace = np.zeros(prototype_count, dtype=float)
    rows = []
    for t, row in enumerate(x):
        row_norm = row / (np.linalg.norm(row) + EPS)
        sims = centers @ row_norm
        winner = int(np.argmax(sims))
        step_lr = lr / math.sqrt(1.0 + 0.002 * t)
        centers[winner] = (1.0 - step_lr) * centers[winner] + step_lr * row_norm
        centers[winner] /= np.linalg.norm(centers[winner]) + EPS
        logits = sims - float(np.max(sims))
        act = np.exp(logits)
        act /= np.sum(act) + EPS
        trace = 0.985 * trace + 0.015 * act
        hot = np.zeros(prototype_count, dtype=float)
        hot[winner] = 1.0
        rows.append(np.concatenate([row_norm, act, trace, hot]))
    return stable_standardize(np.vstack(rows))


def wrong_domain_task(task: PredictivePreexposureTask, *, seed: int) -> PredictivePreexposureTask:
    if task.name != "masked_channel_context":
        return make_masked_channel_context(steps=task.steps, seed=seed + 991)
    return make_long_gap_temporal_continuation(steps=task.steps, seed=seed + 991)


def predictive_representations(task: PredictivePreexposureTask, variant: VariantSpec, *, seed: int, args: argparse.Namespace) -> tuple[np.ndarray, dict[str, Any]]:
    x = np.asarray(task.encoder_input, dtype=float)
    target = np.asarray(task.intrinsic_target, dtype=float)
    labels = np.asarray(task.latent_labels, dtype=int)
    n = x.shape[0]
    rng = np.random.default_rng(seed + 44011 + abs(hash((task.name, variant.name))) % 100000)
    metadata = {
        "labels_visible_during_exposure": bool(variant.uses_hidden_labels),
        "reward_visible_during_exposure": False,
        "max_abs_raw_dopamine": 0.0,
        "uses_hidden_labels": bool(variant.uses_hidden_labels),
        "uses_intrinsic_target": bool(variant.uses_intrinsic_target),
        "destroys_temporal_order": bool(variant.destroys_temporal_order),
        "target_shuffled": bool(variant.target_shuffled),
        "wrong_domain": bool(variant.wrong_domain),
        "state_updates_enabled": variant.name != "no_preexposure",
    }

    if variant.name == "oracle_latent_upper_bound":
        reps = one_hot(labels)
        reps += rng.normal(0.0, 0.01, size=reps.shape)
        return reps, metadata
    if variant.name == "current_input_only":
        return stable_standardize(x), metadata
    history = make_short_history_features(x, history=int(args.history_length))
    if variant.name == "fixed_history_baseline":
        return history, metadata
    if variant.name == "random_projection_history":
        mat = rng.normal(0.0, 1.0 / math.sqrt(history.shape[1]), size=(history.shape[1], int(args.random_projection_dim)))
        return stable_standardize(history @ mat), metadata
    if variant.name == "reservoir_baseline":
        return reservoir_representations(task, seed=seed, state_dim=int(args.state_dim)), metadata
    if variant.name == "stdp_only_unsupervised":
        return stdp_only_representations(task, seed=seed, prototype_count=int(args.prototype_count), lr=float(args.stdp_lr)), metadata

    train_x = x
    train_target = target.copy()
    if variant.wrong_domain:
        other = wrong_domain_task(task, seed=seed)
        train_x = np.asarray(other.encoder_input, dtype=float)
        train_target = np.asarray(other.intrinsic_target, dtype=float)
        # Use a mismatched but dimension-compatible stream. If lengths differ,
        # trim/pad deterministically; current tasks use equal lengths.
        train_x = train_x[:n]
        train_target = train_target[:n]
    if variant.target_shuffled:
        order = np.arange(n)
        rng.shuffle(order)
        train_target = train_target[order]
    order = np.arange(n)
    if variant.destroys_temporal_order:
        rng.shuffle(order)

    encoder = IntrinsicPredictiveEncoder(
        input_dim=x.shape[1],
        target_dim=target.shape[1],
        state_dim=int(args.state_dim),
        seed=seed + 5519,
        lr=float(args.predictive_lr),
        state_decay=float(args.state_decay),
        update_enabled=(variant.name != "no_preexposure"),
        state_enabled=(variant.name != "no_preexposure"),
    )
    reps = np.zeros((n, x.shape[1] + target.shape[1] + int(args.state_dim)), dtype=float)
    if variant.name == "no_preexposure":
        for idx in range(n):
            reps[idx] = encoder.step(x[idx], None)
        return stable_standardize(reps), metadata

    for idx in order:
        use_x = train_x[int(idx)] if variant.wrong_domain else x[int(idx)]
        use_target = train_target[int(idx)]
        rep = encoder.step(use_x, use_target)
        if variant.wrong_domain:
            # Evaluate the mismatched-trained state on the actual sample without
            # allowing a corrective target update.
            rep = encoder.step(x[int(idx)], None)
        reps[int(idx)] = rep
    return stable_standardize(reps), metadata


def evaluate_representation(task: PredictivePreexposureTask, variant_name: str, reps: np.ndarray, metadata: dict[str, Any], *, seed: int, args: argparse.Namespace) -> dict[str, Any]:
    train_idx, test_idx = temporal_episode_probe_split(task.latent_labels, seed=seed, block_size=int(args.probe_block_size))
    labels = np.asarray(task.latent_labels, dtype=int)
    ridge_acc = ridge_probe_accuracy(reps, labels, train_idx, test_idx)
    centroid_acc = centroid_probe_accuracy(reps, labels, train_idx, test_idx)
    knn_acc = knn_probe_accuracy(reps, labels, train_idx, test_idx, k=int(args.knn_k))
    sil = silhouette_score(reps[test_idx], labels[test_idx], seed=seed)
    corr = latent_factor_corr(reps[test_idx], task.latent_factor[test_idx])
    label_count = labels_to_threshold(reps, labels, train_idx, test_idx, threshold=float(args.sample_efficiency_threshold))
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
        "uses_intrinsic_target": bool(metadata.get("uses_intrinsic_target", False)),
        "destroys_temporal_order": bool(metadata.get("destroys_temporal_order", False)),
        "target_shuffled": bool(metadata.get("target_shuffled", False)),
        "wrong_domain": bool(metadata.get("wrong_domain", False)),
        "state_updates_enabled": bool(metadata.get("state_updates_enabled", False)),
    }


def temporal_episode_probe_split(labels: np.ndarray, *, seed: int, block_size: int = 48) -> tuple[np.ndarray, np.ndarray]:
    """Held-out contiguous latent episodes for offline probes.

    Random splits can let smooth random traces act like time-index memorization,
    and simple alternating blocks can still straddle one long regime. This split
    uses hidden labels only after exposure to hold out whole recurring episodes.
    """
    labels = np.asarray(labels, dtype=int)
    n = int(labels.size)
    segments: list[tuple[int, int, int]] = []
    start = 0
    for idx in range(1, n + 1):
        if idx == n or labels[idx] != labels[start]:
            segments.append((start, idx, int(labels[start])))
            start = idx
    by_label: dict[int, list[tuple[int, int, int]]] = {}
    for seg in segments:
        by_label.setdefault(seg[2], []).append(seg)
    train_parts: list[np.ndarray] = []
    test_parts: list[np.ndarray] = []
    for label, segs in sorted(by_label.items()):
        for ordinal, (seg_start, seg_end, _label) in enumerate(segs):
            block = np.arange(seg_start, seg_end, dtype=int)
            if ordinal % 2 == 0:
                train_parts.append(block)
            else:
                test_parts.append(block)
    train_idx = np.concatenate(train_parts) if train_parts else np.arange(0, n // 2, dtype=int)
    test_idx = np.concatenate(test_parts) if test_parts else np.arange(n // 2, n, dtype=int)
    classes = set(int(c) for c in np.unique(labels))
    if set(int(c) for c in np.unique(labels[train_idx])) != classes or set(int(c) for c in np.unique(labels[test_idx])) != classes:
        block_size = max(8, int(block_size))
        train_parts = []
        test_parts = []
        for start in range(0, n, block_size):
            end = min(n, start + block_size)
            block = np.arange(start, end, dtype=int)
            if (start // block_size) % 2 == 0:
                train_parts.append(block)
            else:
                test_parts.append(block)
        train_idx = np.concatenate(train_parts) if train_parts else np.arange(0, n // 2, dtype=int)
        test_idx = np.concatenate(test_parts) if test_parts else np.arange(n // 2, n, dtype=int)
    if set(int(c) for c in np.unique(labels[train_idx])) != classes or set(int(c) for c in np.unique(labels[test_idx])) != classes:
        rng = np.random.default_rng(seed + 9091)
        train_parts = []
        test_parts = []
        for label in sorted(classes):
            idx = np.flatnonzero(labels == label)
            rng.shuffle(idx)
            cut = max(1, min(idx.size - 1, int(round(idx.size * 0.5))))
            train_parts.append(np.sort(idx[:cut]))
            test_parts.append(np.sort(idx[cut:]))
        train_idx = np.sort(np.concatenate(train_parts)).astype(int)
        test_idx = np.sort(np.concatenate(test_parts)).astype(int)
    return np.asarray(train_idx, dtype=int), np.asarray(test_idx, dtype=int)


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
    controls = [name for name in VARIANTS if name != CANDIDATE]
    comparisons: list[dict[str, Any]] = []
    for task in tasks:
        cand = lookup.get((task, CANDIDATE))
        if not cand:
            continue
        cand_acc = float(cand.get("mean_ridge_probe_accuracy") or 0.0)
        row: dict[str, Any] = {
            "task": task,
            "temporal_pressure": bool(cand.get("temporal_pressure", False)),
            "candidate_ridge_accuracy": cand_acc,
            "candidate_min_ridge_accuracy": cand.get("min_ridge_probe_accuracy"),
            "candidate_knn_accuracy": cand.get("mean_knn_probe_accuracy"),
            "candidate_silhouette": cand.get("mean_silhouette_score"),
            "candidate_labels_to_threshold": cand.get("mean_labels_to_threshold"),
        }
        best_non_oracle = ("", -1.0)
        for control in controls:
            ctrl = lookup.get((task, control))
            if not ctrl:
                continue
            acc = float(ctrl.get("mean_ridge_probe_accuracy") or 0.0)
            row[f"{control}_ridge_accuracy"] = acc
            row[f"candidate_delta_vs_{control}"] = cand_acc - acc
            row[f"{control}_labels_to_threshold"] = ctrl.get("mean_labels_to_threshold")
            if control != "oracle_latent_upper_bound" and acc > best_non_oracle[1]:
                best_non_oracle = (control, acc)
        row["best_non_oracle_control"] = best_non_oracle[0]
        row["best_non_oracle_ridge_accuracy"] = best_non_oracle[1] if best_non_oracle[0] else None
        row["candidate_delta_vs_best_non_oracle"] = cand_acc - best_non_oracle[1] if best_non_oracle[0] else None
        comparisons.append(row)
    return comparisons


def evaluate_criteria(*, aggregates: list[dict[str, Any]], comparisons: list[dict[str, Any]], rows: list[dict[str, Any]], tasks: list[str], variants: list[str], seeds: list[int], args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    expected_runs = len(tasks) * len(variants) * len(seeds)
    observed_runs = len(rows)
    non_oracle_rows = [r for r in rows if not bool(r.get("uses_hidden_labels", False))]
    label_leakage = sum(int(bool(r.get("labels_visible_during_exposure", False))) for r in non_oracle_rows)
    reward_leakage = sum(int(bool(r.get("reward_visible_during_exposure", False))) for r in rows)
    max_abs_da = max([abs(float(r.get("max_abs_raw_dopamine", 0.0) or 0.0)) for r in non_oracle_rows] or [0.0])
    cand_rows = [r for r in aggregates if r.get("variant") == CANDIDATE]
    cand_min_ridge = min([float(r.get("min_ridge_probe_accuracy") or 0.0) for r in cand_rows] or [0.0])
    cand_min_knn = min([float(r.get("min_knn_probe_accuracy") or 0.0) for r in cand_rows] or [0.0])

    no_pre_edges = [float(c.get("candidate_delta_vs_no_preexposure") or 0.0) for c in comparisons]
    shuffled_edges = [float(c.get("candidate_delta_vs_shuffled_time_preexposure") or 0.0) for c in comparisons]
    target_edges = [float(c.get("candidate_delta_vs_target_shuffled_preexposure") or 0.0) for c in comparisons]
    wrong_domain_edges = [float(c.get("candidate_delta_vs_wrong_domain_preexposure") or 0.0) for c in comparisons]
    history_edges = [float(c.get("candidate_delta_vs_fixed_history_baseline") or 0.0) for c in comparisons]
    reservoir_edges = [float(c.get("candidate_delta_vs_reservoir_baseline") or 0.0) for c in comparisons]
    stdp_edges = [float(c.get("candidate_delta_vs_stdp_only_unsupervised") or 0.0) for c in comparisons]
    best_edges = [float(c.get("candidate_delta_vs_best_non_oracle") or 0.0) for c in comparisons]

    sample_efficiency_wins = 0
    for c in comparisons:
        cand_labels = c.get("candidate_labels_to_threshold")
        if cand_labels is None:
            continue
        wins = 0
        for key in [
            "no_preexposure_labels_to_threshold",
            "shuffled_time_preexposure_labels_to_threshold",
            "target_shuffled_preexposure_labels_to_threshold",
            "fixed_history_baseline_labels_to_threshold",
            "reservoir_baseline_labels_to_threshold",
        ]:
            other = c.get(key)
            if other is None or float(cand_labels) <= float(other) * float(args.max_sample_efficiency_ratio):
                wins += 1
        if wins >= int(args.min_sample_efficiency_control_wins_per_task):
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
        criterion("candidate beats no-preexposure control", min(no_pre_edges) if no_pre_edges else None, ">=", args.min_edge_vs_no_preexposure, bool(no_pre_edges) and min(no_pre_edges) >= float(args.min_edge_vs_no_preexposure)),
        criterion("time-shuffled preexposure loses", min(shuffled_edges) if shuffled_edges else None, ">=", args.min_edge_vs_shuffled_time, bool(shuffled_edges) and min(shuffled_edges) >= float(args.min_edge_vs_shuffled_time)),
        criterion("target-shuffled preexposure loses", min(target_edges) if target_edges else None, ">=", args.min_edge_vs_target_shuffled, bool(target_edges) and min(target_edges) >= float(args.min_edge_vs_target_shuffled)),
        criterion("wrong-domain preexposure loses", min(wrong_domain_edges) if wrong_domain_edges else None, ">=", args.min_edge_vs_wrong_domain, bool(wrong_domain_edges) and min(wrong_domain_edges) >= float(args.min_edge_vs_wrong_domain)),
        criterion("fixed-history baseline does not explain result", min(history_edges) if history_edges else None, ">=", args.min_edge_vs_fixed_history, bool(history_edges) and min(history_edges) >= float(args.min_edge_vs_fixed_history)),
        criterion("reservoir baseline does not explain result", min(reservoir_edges) if reservoir_edges else None, ">=", args.min_edge_vs_reservoir, bool(reservoir_edges) and min(reservoir_edges) >= float(args.min_edge_vs_reservoir)),
        criterion("STDP-only baseline does not explain result", min(stdp_edges) if stdp_edges else None, ">=", args.min_edge_vs_stdp, bool(stdp_edges) and min(stdp_edges) >= float(args.min_edge_vs_stdp)),
        criterion("candidate beats best non-oracle control", min(best_edges) if best_edges else None, ">=", args.min_edge_vs_best_non_oracle, bool(best_edges) and min(best_edges) >= float(args.min_edge_vs_best_non_oracle)),
        criterion("downstream sample-efficiency improves", sample_efficiency_wins, ">=", args.min_sample_efficiency_wins, sample_efficiency_wins >= int(args.min_sample_efficiency_wins)),
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
        "sample_efficiency_wins": sample_efficiency_wins,
        "claim_boundary": "Noncanonical software diagnostic: intrinsic predictive preexposure under zero-label/zero-reward exposure; not hardware/on-chip representation learning or a v2.0 freeze.",
    }
    return criteria, summary


def plot_matrix(path: Path, aggregates: list[dict[str, Any]], variants: list[str]) -> None:
    if plt is None:
        path.with_suffix(".txt").write_text(f"matplotlib unavailable: {MATPLOTLIB_ERROR}\n", encoding="utf-8")
        return
    tasks = sorted({str(r["task"]) for r in aggregates})
    lookup = by_task_variant(aggregates)
    data = np.zeros((len(tasks), len(variants)), dtype=float)
    for i, task in enumerate(tasks):
        for j, variant in enumerate(variants):
            data[i, j] = float((lookup.get((task, variant)) or {}).get("mean_ridge_probe_accuracy") or 0.0)
    fig, ax = plt.subplots(figsize=(max(12, len(variants) * 1.25), 4.8))
    im = ax.imshow(data, vmin=0.0, vmax=1.0, cmap="magma", aspect="auto")
    ax.set_xticks(np.arange(len(variants)))
    ax.set_xticklabels([v.replace("_", "\n") for v in variants], fontsize=7)
    ax.set_yticks(np.arange(len(tasks)))
    ax.set_yticklabels([t.replace("_", " ") for t in tasks])
    ax.set_title("Tier 5.17c frozen-representation ridge probe accuracy")
    for i in range(len(tasks)):
        for j in range(len(variants)):
            ax.text(j, i, f"{data[i, j]:.2f}", ha="center", va="center", color="white" if data[i, j] < 0.62 else "black", fontsize=7)
    fig.colorbar(im, ax=ax, label="accuracy")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_edges(path: Path, comparisons: list[dict[str, Any]]) -> None:
    if plt is None:
        path.with_suffix(".txt").write_text(f"matplotlib unavailable: {MATPLOTLIB_ERROR}\n", encoding="utf-8")
        return
    labels = [str(c["task"]).replace("_", "\n") for c in comparisons]
    edge_names = [
        "candidate_delta_vs_no_preexposure",
        "candidate_delta_vs_shuffled_time_preexposure",
        "candidate_delta_vs_target_shuffled_preexposure",
        "candidate_delta_vs_fixed_history_baseline",
        "candidate_delta_vs_best_non_oracle",
    ]
    x = np.arange(len(labels))
    width = 0.15
    fig, ax = plt.subplots(figsize=(12, 5.8))
    for offset, name in enumerate(edge_names):
        vals = [float(c.get(name) or 0.0) for c in comparisons]
        ax.bar(x + (offset - 2.0) * width, vals, width, label=name.replace("candidate_delta_vs_", "vs ").replace("_", " "))
    ax.axhline(0.0, color="black", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("ridge accuracy edge")
    ax.set_title("Tier 5.17c candidate edge against controls")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fairness_contract(args: argparse.Namespace, tasks: list[str], variants: list[str], seeds: list[int]) -> dict[str, Any]:
    return {
        "tier": TIER,
        "generated_at_utc": utc_now(),
        "claim_boundary": "Software-only intrinsic preexposure diagnostic. Non-oracle variants receive no hidden labels, reward, correctness, or dopamine during preexposure. Hidden labels are used only after frozen representation generation for offline probes.",
        "fairness_rules": [
            "Candidate uses only visible encoder input and visible intrinsic targets such as masked-channel or temporal-continuation signals.",
            "No non-oracle row receives latent labels during representation exposure.",
            "No row receives task reward, correctness, or dopamine during representation exposure.",
            "Shuffled-time, target-shuffled, and wrong-domain controls receive comparable target volume but broken temporal/binding/domain alignment.",
            "Current-input, fixed-history, random-projection, reservoir, and STDP-only baselines test whether simple encoders or unsupervised dynamics explain the result.",
            "Oracle latent upper bound is reported but cannot support no-leakage or promotion claims.",
        ],
        "tasks": tasks,
        "variants": variants,
        "seeds": seeds,
        "steps": int(args.steps),
        "smoke": bool(args.smoke),
        "primary_objective": "intrinsic predictive preexposure",
    }


def write_report(path: Path, result: dict[str, Any], comparisons: list[dict[str, Any]]) -> None:
    lines = [
        "# Tier 5.17c Intrinsic Predictive Preexposure Findings",
        "",
        f"- Generated: `{result['generated_at_utc']}`",
        f"- Status: **{result['status'].upper()}**",
        f"- Output directory: `{result['output_dir']}`",
        f"- Tasks: `{', '.join(result['summary']['tasks'])}`",
        f"- Seeds: `{result['summary']['seeds']}`",
        "",
        "Tier 5.17c tests whether label-free predictive/sensory pressure can make preexposure useful before reward arrives.",
        "",
        "## Claim Boundary",
        "",
        "- Noncanonical software diagnostic evidence only.",
        "- Non-oracle variants receive no labels, reward, correctness feedback, or dopamine during preexposure.",
        "- Hidden labels are used only after representations are frozen/snapshotted for offline probes.",
        "- This is not SpiNNaker hardware evidence, native/custom-C on-chip representation learning, full world modeling, language, planning, AGI, or a v2.0 freeze.",
        "- Oracle rows are upper bounds and excluded from no-leakage promotion checks.",
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
        f"- sample_efficiency_wins: `{result['summary']['sample_efficiency_wins']}`",
        "",
        "## Comparisons",
        "",
        "| Task | Candidate | No preexposure | Time shuffled | Target shuffled | Wrong domain | Fixed history | Reservoir | STDP-only | Best non-oracle edge |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in comparisons:
        lines.append(
            "| {task} | {cand} | {no_pre} | {time} | {target} | {wrong} | {hist} | {reservoir} | {stdp} | {best} |".format(
                task=markdown_value(row.get("task")),
                cand=markdown_value(row.get("candidate_ridge_accuracy")),
                no_pre=markdown_value(row.get("no_preexposure_ridge_accuracy")),
                time=markdown_value(row.get("shuffled_time_preexposure_ridge_accuracy")),
                target=markdown_value(row.get("target_shuffled_preexposure_ridge_accuracy")),
                wrong=markdown_value(row.get("wrong_domain_preexposure_ridge_accuracy")),
                hist=markdown_value(row.get("fixed_history_baseline_ridge_accuracy")),
                reservoir=markdown_value(row.get("reservoir_baseline_ridge_accuracy")),
                stdp=markdown_value(row.get("stdp_only_unsupervised_ridge_accuracy")),
                best=markdown_value(row.get("candidate_delta_vs_best_non_oracle")),
            )
        )
    lines.extend(["", "## Criteria", "", "| Criterion | Value | Rule | Pass | Note |", "| --- | --- | --- | --- | --- |"])
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
            "- `tier5_17c_results.json`: machine-readable manifest.",
            "- `tier5_17c_report.md`: human findings and claim boundary.",
            "- `tier5_17c_runs.csv`: per-task/variant/seed probe rows.",
            "- `tier5_17c_summary.csv`: aggregate probe metrics.",
            "- `tier5_17c_comparisons.csv`: candidate-control edges.",
            "- `tier5_17c_fairness_contract.json`: no-label/no-reward intrinsic preexposure contract.",
            "- `tier5_17c_representation_matrix.png`: ridge-probe accuracy heatmap.",
            "- `tier5_17c_control_edges.png`: candidate-control edge plot.",
            "",
            "![tier5_17c_representation_matrix](tier5_17c_representation_matrix.png)",
            "",
            "![tier5_17c_control_edges](tier5_17c_control_edges.png)",
        ]
    )
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_latest(output_dir: Path, report_path: Path, manifest_path: Path, summary_csv: Path, status: str) -> None:
    write_json(
        ROOT / "controlled_test_output" / "tier5_17c_latest_manifest.json",
        {
            "tier": TIER,
            "status": status,
            "canonical": False,
            "output_dir": str(output_dir),
            "manifest_json": str(manifest_path),
            "report_md": str(report_path),
            "summary_csv": str(summary_csv),
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
        variants = [CANDIDATE, "no_preexposure", "target_shuffled_preexposure", "fixed_history_baseline", "oracle_latent_upper_bound"]
        seeds = seeds[:1]

    output_dir = Path(args.output_dir) if args.output_dir else ROOT / "controlled_test_output" / f"tier5_17c_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    output_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    steps = int(args.steps if not args.smoke else min(args.steps, args.smoke_steps))
    for seed in seeds:
        for task_name in tasks:
            task = build_task(task_name, steps=steps, seed=seed)
            for variant_name in variants:
                print(f"[tier5.17c] task={task_name} variant={variant_name} seed={seed}", flush=True)
                variant = VARIANTS[variant_name]
                reps, metadata = predictive_representations(task, variant, seed=seed, args=args)
                rows.append(evaluate_representation(task, variant_name, reps, metadata, seed=seed, args=args))

    aggregates = aggregate(rows)
    comparisons = build_comparisons(aggregates)
    criteria, summary = evaluate_criteria(aggregates=aggregates, comparisons=comparisons, rows=rows, tasks=tasks, variants=variants, seeds=seeds, args=args)
    status, failure_reason = pass_fail(criteria)

    run_csv = output_dir / "tier5_17c_runs.csv"
    summary_csv = output_dir / "tier5_17c_summary.csv"
    comparisons_csv = output_dir / "tier5_17c_comparisons.csv"
    fairness_json = output_dir / "tier5_17c_fairness_contract.json"
    matrix_png = output_dir / "tier5_17c_representation_matrix.png"
    edges_png = output_dir / "tier5_17c_control_edges.png"
    manifest_json = output_dir / "tier5_17c_results.json"
    report_md = output_dir / "tier5_17c_report.md"

    write_csv(run_csv, rows)
    write_csv(summary_csv, aggregates)
    write_csv(comparisons_csv, comparisons)
    write_json(fairness_json, fairness_contract(args, tasks, variants, seeds))
    plot_matrix(matrix_png, aggregates, variants)
    plot_edges(edges_png, comparisons)

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
    write_report(report_md, result, comparisons)
    if not bool(args.smoke):
        write_latest(output_dir, report_md, manifest_json, summary_csv, status)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks", default=DEFAULT_TASKS)
    parser.add_argument("--variants", default=DEFAULT_VARIANTS)
    parser.add_argument("--steps", type=int, default=640)
    parser.add_argument("--smoke-steps", type=int, default=180)
    parser.add_argument("--seed-count", type=int, default=3)
    parser.add_argument("--seeds", default="42,43,44")
    parser.add_argument("--base-seed", type=int, default=42)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--smoke", action="store_true", help="Run harness integrity gates only; science gates are skipped.")
    parser.add_argument("--stop-on-fail", action="store_true")
    parser.add_argument("--state-dim", type=int, default=18)
    parser.add_argument("--history-length", type=int, default=5)
    parser.add_argument("--random-projection-dim", type=int, default=24)
    parser.add_argument("--prototype-count", type=int, default=14)
    parser.add_argument("--predictive-lr", type=float, default=0.032)
    parser.add_argument("--state-decay", type=float, default=0.992)
    parser.add_argument("--stdp-lr", type=float, default=0.08)
    parser.add_argument("--probe-train-fraction", type=float, default=0.45)
    parser.add_argument("--probe-block-size", type=int, default=48)
    parser.add_argument("--knn-k", type=int, default=5)
    parser.add_argument("--sample-efficiency-threshold", type=float, default=0.78)
    parser.add_argument("--max-abs-raw-dopamine", type=float, default=1e-12)
    parser.add_argument("--min-candidate-probe-accuracy", type=float, default=0.74)
    parser.add_argument("--min-candidate-knn-accuracy", type=float, default=0.68)
    parser.add_argument("--min-edge-vs-no-preexposure", type=float, default=0.08)
    parser.add_argument("--min-edge-vs-shuffled-time", type=float, default=0.05)
    parser.add_argument("--min-edge-vs-target-shuffled", type=float, default=0.05)
    parser.add_argument("--min-edge-vs-wrong-domain", type=float, default=0.05)
    parser.add_argument("--min-edge-vs-fixed-history", type=float, default=0.02)
    parser.add_argument("--min-edge-vs-reservoir", type=float, default=0.02)
    parser.add_argument("--min-edge-vs-stdp", type=float, default=0.02)
    parser.add_argument("--min-edge-vs-best-non-oracle", type=float, default=0.01)
    parser.add_argument("--max-sample-efficiency-ratio", type=float, default=1.0)
    parser.add_argument("--min-sample-efficiency-control-wins-per-task", type=int, default=3)
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
