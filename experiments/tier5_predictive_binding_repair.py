#!/usr/bin/env python3
"""Tier 5.17d predictive preexposure binding/sham repair.

Tier 5.17c tested intrinsic predictive preexposure but failed promotion because
strong shams were still too close under reviewer-grade controls. Tier 5.17d is a
single focused repair cycle for that failure mode.

The repair has two parts:

1. Score only held-out ambiguous episodes after visible context cues fade.
2. Use a binding-oriented predictive state where future/masked sensory targets
   can influence future state, but never the same timestep probe.

Non-oracle variants still receive no hidden labels, no reward, no task
correctness, and zero dopamine during preexposure. This is a software diagnostic
only: not hardware evidence, not on-chip representation learning, not language,
not full world modeling, and not a v2.0 freeze.
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

TIER = "Tier 5.17d - Predictive Preexposure Binding/Sham Repair"
DEFAULT_TASKS = "cross_modal_binding,reentry_binding"
DEFAULT_VARIANTS = (
    "predictive_binding_preexposure,no_preexposure,target_shuffled_binding,"
    "wrong_domain_binding,current_input_only,fixed_history_baseline,"
    "random_projection_history,reservoir_baseline,stdp_only_unsupervised,"
    "oracle_latent_upper_bound"
)
CANDIDATE = "predictive_binding_preexposure"
EPS = 1e-12


@dataclass(frozen=True)
class BindingTask:
    name: str
    display_name: str
    description: str
    encoder_input: np.ndarray
    intrinsic_target: np.ndarray
    latent_labels: np.ndarray
    latent_factor: np.ndarray
    probe_mask: np.ndarray
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
    target_shuffled: bool = False
    wrong_domain: bool = False
    state_enabled: bool = True


VARIANTS: dict[str, VariantSpec] = {
    "predictive_binding_preexposure": VariantSpec(
        name="predictive_binding_preexposure",
        family="candidate",
        description="future/masked sensory target is bound into future recurrent state; no same-step target readout",
        uses_intrinsic_target=True,
    ),
    "no_preexposure": VariantSpec(
        name="no_preexposure",
        family="candidate ablation",
        description="same shell without target-driven binding state",
        state_enabled=False,
    ),
    "target_shuffled_binding": VariantSpec(
        name="target_shuffled_binding",
        family="binding sham",
        description="same inputs but globally shuffled intrinsic target stream",
        uses_intrinsic_target=True,
        target_shuffled=True,
    ),
    "wrong_domain_binding": VariantSpec(
        name="wrong_domain_binding",
        family="domain sham",
        description="same inputs paired with intrinsic targets from a mismatched task/domain",
        uses_intrinsic_target=True,
        wrong_domain=True,
    ),
    "current_input_only": VariantSpec(
        name="current_input_only",
        family="encoder-only baseline",
        description="probe sees only current visible input on the held-out ambiguous tail rows",
    ),
    "fixed_history_baseline": VariantSpec(
        name="fixed_history_baseline",
        family="history baseline",
        description="probe sees fixed short visible-input history",
    ),
    "random_projection_history": VariantSpec(
        name="random_projection_history",
        family="history baseline",
        description="fixed random projection of short visible-input history",
    ),
    "reservoir_baseline": VariantSpec(
        name="reservoir_baseline",
        family="sequence baseline",
        description="fixed random recurrent reservoir driven only by visible input",
    ),
    "stdp_only_unsupervised": VariantSpec(
        name="stdp_only_unsupervised",
        family="unsupervised SNN-style baseline",
        description="competitive Hebbian state driven only by visible input; no predictive target binding",
    ),
    "oracle_latent_upper_bound": VariantSpec(
        name="oracle_latent_upper_bound",
        family="oracle upper bound",
        description="hidden latent one-hot upper bound; excluded from no-leakage promotion checks",
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
    for value in values:
        if value not in ordered:
            ordered.append(value)
    return ordered


def one_hot(labels: np.ndarray, count: int | None = None) -> np.ndarray:
    labels = np.asarray(labels, dtype=int)
    if count is None:
        count = int(np.max(labels)) + 1
    out = np.zeros((labels.size, int(count)), dtype=float)
    out[np.arange(labels.size), labels] = 1.0
    return out


def context_codes(count: int, dim: int, *, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    codes = rng.normal(0.0, 1.0, size=(count, dim))
    codes /= np.linalg.norm(codes, axis=1, keepdims=True) + EPS
    return codes


def make_masked_code_binding(*, steps: int, seed: int) -> BindingTask:
    rng = np.random.default_rng(seed + 1701)
    context_count = 4
    target_dim = 6
    codes = context_codes(context_count, target_dim, seed=seed + 101)
    labels = np.zeros(steps, dtype=int)
    encoder = np.zeros((steps, 5), dtype=float)
    target = np.zeros((steps, target_dim), dtype=float)
    probe_mask = np.zeros(steps, dtype=bool)
    context = int(rng.integers(0, context_count))
    next_switch = 0
    cue_vec = np.zeros(context_count, dtype=float)
    age = 0
    for t in range(steps):
        if t >= next_switch:
            context = int((context + int(rng.integers(1, context_count))) % context_count)
            cue_vec = np.zeros(context_count, dtype=float)
            cue_vec[context] = 1.0
            next_switch = t + int(rng.integers(76, 126))
            age = 0
        labels[t] = context
        nuisance = rng.normal(0.0, 0.45)
        encoder[t] = np.asarray(
            [
                cue_vec[0] - cue_vec[2] + rng.normal(0.0, 0.025),
                cue_vec[1] - cue_vec[3] + rng.normal(0.0, 0.025),
                rng.choice([-1.0, 1.0]) + rng.normal(0.0, 0.22),
                0.22 * math.sin(t / 11.0) + 0.12 * nuisance,
                rng.normal(0.0, 0.35),
            ],
            dtype=float,
        )
        target[t] = codes[context] + 0.08 * np.asarray([math.sin(t / (9.0 + i)) for i in range(target_dim)]) + rng.normal(0.0, 0.035, size=target_dim)
        # Score only the deep ambiguous tail. Earlier rows are still too close
        # to the visible cue and can be solved by generic trace dynamics.
        probe_mask[t] = age >= 45
        cue_vec *= 0.62
        age += 1
    return BindingTask(
        name="masked_code_binding",
        display_name="Masked Code Binding",
        description="brief cues must bind future masked sensory code through long ambiguous tails",
        encoder_input=stable_standardize(encoder),
        intrinsic_target=stable_standardize(target),
        latent_labels=labels,
        latent_factor=labels.astype(float),
        probe_mask=probe_mask,
        metadata={"objective": "masked_sensory_code_prediction", "target_dim": target_dim},
    )


def make_cross_modal_binding(*, steps: int, seed: int) -> BindingTask:
    rng = np.random.default_rng(seed + 2803)
    context_count = 3
    sub_count = 2
    target_dim = 7
    codes = context_codes(context_count * sub_count, target_dim, seed=seed + 202)
    labels = np.zeros(steps, dtype=int)
    encoder = np.zeros((steps, 5), dtype=float)
    target = np.zeros((steps, target_dim), dtype=float)
    probe_mask = np.zeros(steps, dtype=bool)
    context = int(rng.integers(0, context_count))
    sub = int(rng.integers(0, sub_count))
    next_switch = 0
    cue = 0.0
    age = 0
    for t in range(steps):
        if t >= next_switch:
            context = int((context + int(rng.integers(1, context_count))) % context_count)
            cue = [-1.0, 0.0, 1.0][context]
            next_switch = t + int(rng.integers(72, 116))
            age = 0
        if rng.random() < 0.075:
            sub = 1 - sub
        label = context * sub_count + sub
        labels[t] = label
        symbol = 1.0 if sub else -1.0
        encoder[t] = np.asarray(
            [
                cue + rng.normal(0.0, 0.025),
                symbol + rng.normal(0.0, 0.20),
                symbol * math.sin(t / 7.0) + rng.normal(0.0, 0.16),
                math.cos(t / 13.0) + rng.normal(0.0, 0.18),
                rng.normal(0.0, 0.32),
            ],
            dtype=float,
        )
        target[t] = codes[label] + 0.06 * np.asarray([math.cos(t / (8.0 + i)) for i in range(target_dim)]) + rng.normal(0.0, 0.035, size=target_dim)
        probe_mask[t] = age >= 30
        cue *= 0.60
        age += 1
    return BindingTask(
        name="cross_modal_binding",
        display_name="Cross-Modal Binding",
        description="same visible symbol has different latent cross-modal target depending on faded context",
        encoder_input=stable_standardize(encoder),
        intrinsic_target=stable_standardize(target),
        latent_labels=labels,
        latent_factor=labels.astype(float),
        probe_mask=probe_mask,
        metadata={"objective": "cross_modal_masked_prediction", "target_dim": target_dim},
    )


def make_reentry_binding(*, steps: int, seed: int) -> BindingTask:
    rng = np.random.default_rng(seed + 3907)
    context_count = 4
    target_dim = 6
    codes = context_codes(context_count, target_dim, seed=seed + 303)
    labels = np.zeros(steps, dtype=int)
    encoder = np.zeros((steps, 5), dtype=float)
    target = np.zeros((steps, target_dim), dtype=float)
    probe_mask = np.zeros(steps, dtype=bool)
    schedule = [0, 1, 2, 3, 0, 2, 1, 3, 0, 1]
    seg_len = max(32, steps // len(schedule))
    age = 0
    last_context = None
    for t in range(steps):
        seg = min(len(schedule) - 1, t // seg_len)
        context = schedule[seg]
        if context != last_context:
            age = 0
            last_context = context
        cue = (1.0 if context in (1, 3) else -1.0) * math.exp(-age / 3.5)
        aux_cue = (1.0 if context in (2, 3) else -1.0) * math.exp(-age / 4.0)
        labels[t] = context
        encoder[t] = np.asarray(
            [
                cue + rng.normal(0.0, 0.025),
                aux_cue + rng.normal(0.0, 0.025),
                rng.choice([-1.0, 1.0]) + rng.normal(0.0, 0.24),
                0.25 * math.sin(t / 6.0) + rng.normal(0.0, 0.18),
                rng.normal(0.0, 0.36),
            ],
            dtype=float,
        )
        target[t] = codes[context] + 0.07 * np.asarray([math.sin(t / (10.0 + i)) for i in range(target_dim)]) + rng.normal(0.0, 0.035, size=target_dim)
        probe_mask[t] = age >= 28
        age += 1
    return BindingTask(
        name="reentry_binding",
        display_name="Reentry Binding",
        description="old contexts return after intervening segments; masked targets should stabilize recurring structure",
        encoder_input=stable_standardize(encoder),
        intrinsic_target=stable_standardize(target),
        latent_labels=labels,
        latent_factor=labels.astype(float),
        probe_mask=probe_mask,
        metadata={"objective": "recurrent_context_masked_prediction", "target_dim": target_dim},
    )


def build_task(name: str, *, steps: int, seed: int) -> BindingTask:
    if name == "masked_code_binding":
        return make_masked_code_binding(steps=steps, seed=seed)
    if name == "cross_modal_binding":
        return make_cross_modal_binding(steps=steps, seed=seed)
    if name == "reentry_binding":
        return make_reentry_binding(steps=steps, seed=seed)
    raise ValueError(f"unknown task {name}")


class PredictiveBinder:
    """Binding-oriented self-supervised predictor.

    The representation returned for timestep t is computed before target_t is
    consumed. target_t can shape future state only. This avoids same-step target
    leakage while allowing a visible masked/future channel to act as intrinsic
    training signal.
    """

    def __init__(self, *, input_dim: int, target_dim: int, state_dim: int, seed: int, lr: float, state_decay: float, state_enabled: bool = True) -> None:
        self.rng = np.random.default_rng(seed)
        self.input_dim = int(input_dim)
        self.target_dim = int(target_dim)
        self.state_dim = int(state_dim)
        self.lr = float(lr)
        self.state_decay = float(state_decay)
        self.state_enabled = bool(state_enabled)
        feature_dim = self.input_dim + self.state_dim + 1
        self.w = self.rng.normal(0.0, 0.04, size=(self.target_dim, feature_dim))
        self.target_to_state = self.rng.normal(0.0, 0.55, size=(self.state_dim, self.target_dim))
        self.error_to_state = self.rng.normal(0.0, 0.25, size=(self.state_dim, self.target_dim))
        self.input_gate = self.rng.normal(0.0, 0.10, size=(self.state_dim, self.input_dim))
        self.state = np.zeros(self.state_dim, dtype=float)
        self.step_index = 0

    def step(self, x: np.ndarray, target: np.ndarray | None) -> np.ndarray:
        x = np.asarray(x, dtype=float).reshape(-1)
        feature = np.concatenate([x, self.state, np.ones(1, dtype=float)])
        pred = self.w @ feature
        pre_state = self.state.copy()
        if target is not None and self.state_enabled:
            y = np.asarray(target, dtype=float).reshape(-1)
            error = y - pred
            lr = self.lr / math.sqrt(1.0 + 0.001 * self.step_index)
            self.w += lr * np.outer(error, feature)
            self.w *= 0.9993
            state_drive = self.target_to_state @ y + self.error_to_state @ error + self.input_gate @ x
            self.state = self.state_decay * self.state + (1.0 - self.state_decay) * np.tanh(state_drive)
        elif not self.state_enabled:
            self.state = np.zeros_like(self.state)
        self.step_index += 1
        return np.concatenate([x, pred, pre_state])


def reservoir_representations(task: BindingTask, *, seed: int, state_dim: int) -> np.ndarray:
    rng = np.random.default_rng(seed + 8101)
    x = np.asarray(task.encoder_input, dtype=float)
    win = rng.normal(0.0, 0.55, size=(state_dim, x.shape[1]))
    wrec = rng.normal(0.0, 0.16, size=(state_dim, state_dim))
    radius = max(1e-6, float(np.max(np.sum(np.abs(wrec), axis=1))))
    wrec = wrec / radius * 0.82
    state = np.zeros(state_dim, dtype=float)
    rows = []
    for row in x:
        state = np.tanh(win @ row + wrec @ state)
        rows.append(np.concatenate([row, state]))
    return stable_standardize(np.vstack(rows))


def stdp_only_representations(task: BindingTask, *, seed: int, prototype_count: int, lr: float) -> np.ndarray:
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


def wrong_domain_target(task: BindingTask, *, seed: int) -> np.ndarray:
    if task.name != "masked_code_binding":
        other = make_masked_code_binding(steps=task.steps, seed=seed + 997)
    else:
        other = make_cross_modal_binding(steps=task.steps, seed=seed + 997)
    y = np.asarray(other.intrinsic_target, dtype=float)
    if y.shape[1] != task.intrinsic_target.shape[1]:
        rng = np.random.default_rng(seed + 998)
        proj = rng.normal(0.0, 1.0 / math.sqrt(y.shape[1]), size=(y.shape[1], task.intrinsic_target.shape[1]))
        y = y @ proj
    return stable_standardize(y[: task.steps])


def representations_for_variant(task: BindingTask, variant: VariantSpec, *, seed: int, args: argparse.Namespace) -> tuple[np.ndarray, dict[str, Any]]:
    x = np.asarray(task.encoder_input, dtype=float)
    target = np.asarray(task.intrinsic_target, dtype=float)
    labels = np.asarray(task.latent_labels, dtype=int)
    n = int(x.shape[0])
    rng = np.random.default_rng(seed + 44011 + sum(ord(c) for c in f"{task.name}:{variant.name}"))
    metadata = {
        "labels_visible_during_exposure": bool(variant.uses_hidden_labels),
        "reward_visible_during_exposure": False,
        "max_abs_raw_dopamine": 0.0,
        "uses_hidden_labels": bool(variant.uses_hidden_labels),
        "uses_intrinsic_target": bool(variant.uses_intrinsic_target),
        "target_shuffled": bool(variant.target_shuffled),
        "wrong_domain": bool(variant.wrong_domain),
        "state_updates_enabled": bool(variant.state_enabled),
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

    train_target = target.copy()
    if variant.target_shuffled:
        order = np.arange(n)
        rng.shuffle(order)
        train_target = train_target[order]
    if variant.wrong_domain:
        train_target = wrong_domain_target(task, seed=seed)

    binder = PredictiveBinder(
        input_dim=x.shape[1],
        target_dim=target.shape[1],
        state_dim=int(args.state_dim),
        seed=seed + 5519,
        lr=float(args.binding_lr),
        state_decay=float(args.state_decay),
        state_enabled=bool(variant.state_enabled),
    )
    reps = np.zeros((n, x.shape[1] + target.shape[1] + int(args.state_dim)), dtype=float)
    for idx in range(n):
        reps[idx] = binder.step(x[idx], train_target[idx] if variant.uses_intrinsic_target else None)
    return stable_standardize(reps), metadata


def episode_probe_split(labels: np.ndarray, mask: np.ndarray, *, seed: int) -> tuple[np.ndarray, np.ndarray]:
    labels = np.asarray(labels, dtype=int)
    mask = np.asarray(mask, dtype=bool)
    n = labels.size
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
            idx = np.arange(seg_start, seg_end, dtype=int)
            idx = idx[mask[idx]]
            if idx.size == 0:
                continue
            if ordinal % 2 == 0:
                train_parts.append(idx)
            else:
                test_parts.append(idx)
    classes = set(int(c) for c in np.unique(labels))
    if not train_parts or not test_parts:
        return fallback_stratified_split(labels, mask, seed=seed)
    train_idx = np.sort(np.concatenate(train_parts)).astype(int)
    test_idx = np.sort(np.concatenate(test_parts)).astype(int)
    if set(int(c) for c in np.unique(labels[train_idx])) != classes or set(int(c) for c in np.unique(labels[test_idx])) != classes:
        return fallback_stratified_split(labels, mask, seed=seed)
    return train_idx, test_idx


def fallback_stratified_split(labels: np.ndarray, mask: np.ndarray, *, seed: int) -> tuple[np.ndarray, np.ndarray]:
    labels = np.asarray(labels, dtype=int)
    mask = np.asarray(mask, dtype=bool)
    rng = np.random.default_rng(seed + 9091)
    train_parts = []
    test_parts = []
    for label in sorted(int(c) for c in np.unique(labels)):
        idx = np.flatnonzero((labels == label) & mask)
        if idx.size < 2:
            idx = np.flatnonzero(labels == label)
        rng.shuffle(idx)
        cut = max(1, min(idx.size - 1, int(round(idx.size * 0.5))))
        train_parts.append(np.sort(idx[:cut]))
        test_parts.append(np.sort(idx[cut:]))
    return np.sort(np.concatenate(train_parts)).astype(int), np.sort(np.concatenate(test_parts)).astype(int)


def evaluate_representation(task: BindingTask, variant_name: str, reps: np.ndarray, metadata: dict[str, Any], *, seed: int, args: argparse.Namespace) -> dict[str, Any]:
    labels = np.asarray(task.latent_labels, dtype=int)
    train_idx, test_idx = episode_probe_split(labels, task.probe_mask, seed=seed)
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
        "probe_rows": int(test_idx.size),
        "representation_dim": int(reps.shape[1]),
        "latent_count": int(np.unique(labels).size),
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
        "target_shuffled": bool(metadata.get("target_shuffled", False)),
        "wrong_domain": bool(metadata.get("wrong_domain", False)),
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
                "mean_probe_rows": mean(float(i.get("probe_rows") or 0.0) for i in items),
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
    comparisons = []
    for task in tasks:
        cand = lookup.get((task, CANDIDATE))
        if not cand:
            continue
        cand_acc = float(cand.get("mean_ridge_probe_accuracy") or 0.0)
        row: dict[str, Any] = {
            "task": task,
            "candidate_ridge_accuracy": cand_acc,
            "candidate_min_ridge_accuracy": cand.get("min_ridge_probe_accuracy"),
            "candidate_knn_accuracy": cand.get("mean_knn_probe_accuracy"),
            "candidate_labels_to_threshold": cand.get("mean_labels_to_threshold"),
            "candidate_probe_rows": cand.get("mean_probe_rows"),
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
    target_edges = [float(c.get("candidate_delta_vs_target_shuffled_binding") or 0.0) for c in comparisons]
    wrong_edges = [float(c.get("candidate_delta_vs_wrong_domain_binding") or 0.0) for c in comparisons]
    history_edges = [float(c.get("candidate_delta_vs_fixed_history_baseline") or 0.0) for c in comparisons]
    reservoir_edges = [float(c.get("candidate_delta_vs_reservoir_baseline") or 0.0) for c in comparisons]
    stdp_edges = [float(c.get("candidate_delta_vs_stdp_only_unsupervised") or 0.0) for c in comparisons]
    best_edges = [float(c.get("candidate_delta_vs_best_non_oracle") or 0.0) for c in comparisons]
    probe_rows = [float(c.get("candidate_probe_rows") or 0.0) for c in comparisons]

    sample_efficiency_wins = 0
    for c in comparisons:
        cand_labels = c.get("candidate_labels_to_threshold")
        if cand_labels is None:
            continue
        wins = 0
        for key in [
            "no_preexposure_labels_to_threshold",
            "target_shuffled_binding_labels_to_threshold",
            "wrong_domain_binding_labels_to_threshold",
            "fixed_history_baseline_labels_to_threshold",
            "reservoir_baseline_labels_to_threshold",
            "stdp_only_unsupervised_labels_to_threshold",
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
        criterion("held-out ambiguous probe rows available", min(probe_rows) if probe_rows else 0, ">=", args.min_probe_rows, bool(probe_rows) and min(probe_rows) >= int(args.min_probe_rows)),
    ]
    science = [
        criterion("candidate reaches minimum ridge-probe accuracy", cand_min_ridge, ">=", args.min_candidate_probe_accuracy, cand_min_ridge >= float(args.min_candidate_probe_accuracy)),
        criterion("candidate reaches minimum kNN-probe accuracy", cand_min_knn, ">=", args.min_candidate_knn_accuracy, cand_min_knn >= float(args.min_candidate_knn_accuracy)),
        criterion("candidate beats no-preexposure control", min(no_pre_edges) if no_pre_edges else None, ">=", args.min_edge_vs_no_preexposure, bool(no_pre_edges) and min(no_pre_edges) >= float(args.min_edge_vs_no_preexposure)),
        criterion("target-shuffled binding loses", min(target_edges) if target_edges else None, ">=", args.min_edge_vs_target_shuffled, bool(target_edges) and min(target_edges) >= float(args.min_edge_vs_target_shuffled)),
        criterion("wrong-domain binding loses", min(wrong_edges) if wrong_edges else None, ">=", args.min_edge_vs_wrong_domain, bool(wrong_edges) and min(wrong_edges) >= float(args.min_edge_vs_wrong_domain)),
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
        "min_candidate_probe_rows": min(probe_rows) if probe_rows else 0,
        "sample_efficiency_wins": sample_efficiency_wins,
        "claim_boundary": "Noncanonical software diagnostic: predictive binding preexposure under zero-label/zero-reward exposure; not hardware/on-chip representation learning or a v2.0 freeze.",
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
    im = ax.imshow(data, vmin=0.0, vmax=1.0, cmap="cividis", aspect="auto")
    ax.set_xticks(np.arange(len(variants)))
    ax.set_xticklabels([v.replace("_", "\n") for v in variants], fontsize=7)
    ax.set_yticks(np.arange(len(tasks)))
    ax.set_yticklabels([t.replace("_", " ") for t in tasks])
    ax.set_title("Tier 5.17d held-out ambiguous-episode ridge probe accuracy")
    for i in range(len(tasks)):
        for j in range(len(variants)):
            ax.text(j, i, f"{data[i, j]:.2f}", ha="center", va="center", color="white" if data[i, j] < 0.55 else "black", fontsize=7)
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
        "candidate_delta_vs_target_shuffled_binding",
        "candidate_delta_vs_wrong_domain_binding",
        "candidate_delta_vs_stdp_only_unsupervised",
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
    ax.set_title("Tier 5.17d candidate edge against binding controls")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fairness_contract(args: argparse.Namespace, tasks: list[str], variants: list[str], seeds: list[int]) -> dict[str, Any]:
    return {
        "tier": TIER,
        "generated_at_utc": utc_now(),
        "claim_boundary": "Software-only predictive binding repair diagnostic. Non-oracle variants receive no hidden labels, reward, correctness, or dopamine during preexposure. Hidden labels are used only after representation generation for held-out ambiguous-episode probes.",
        "fairness_rules": [
            "Candidate returns pre-target-update representations only; intrinsic targets can influence future state, not same-step probe rows.",
            "Probe rows exclude visible cue-onset spans and hold out recurring ambiguous episodes where possible.",
            "Target-shuffled and wrong-domain controls receive comparable target volume but broken binding/domain alignment.",
            "Visible-input, fixed-history, random-projection, reservoir, and STDP-only controls test whether input dynamics alone explain the effect.",
            "Oracle latent upper bound is reported but cannot support no-leakage claims.",
        ],
        "tasks": tasks,
        "variants": variants,
        "seeds": seeds,
        "steps": int(args.steps),
        "smoke": bool(args.smoke),
    }


def write_report(path: Path, result: dict[str, Any], comparisons: list[dict[str, Any]]) -> None:
    lines = [
        "# Tier 5.17d Predictive Preexposure Binding/Sham Repair Findings",
        "",
        f"- Generated: `{result['generated_at_utc']}`",
        f"- Status: **{result['status'].upper()}**",
        f"- Output directory: `{result['output_dir']}`",
        f"- Tasks: `{', '.join(result['summary']['tasks'])}`",
        f"- Seeds: `{result['summary']['seeds']}`",
        "",
        "Tier 5.17d repairs the 5.17c sham-separation failure by testing target/domain binding on held-out ambiguous episodes after context cues fade.",
        "",
        "## Claim Boundary",
        "",
        "- Noncanonical software diagnostic evidence only.",
        "- Non-oracle variants receive no labels, reward, correctness feedback, or dopamine during preexposure.",
        "- Hidden labels are used only after representations are generated, for held-out ambiguous-episode probes.",
        "- This is not SpiNNaker hardware evidence, native/custom-C on-chip representation learning, full world modeling, language, planning, AGI, or a v2.0 freeze.",
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
        f"- min_candidate_probe_rows: `{markdown_value(result['summary']['min_candidate_probe_rows'])}`",
        f"- sample_efficiency_wins: `{result['summary']['sample_efficiency_wins']}`",
        "",
        "## Comparisons",
        "",
        "| Task | Candidate | No preexposure | Target shuffled | Wrong domain | Fixed history | Reservoir | STDP-only | Best non-oracle edge |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in comparisons:
        lines.append(
            "| {task} | {cand} | {no_pre} | {target} | {wrong} | {hist} | {reservoir} | {stdp} | {best} |".format(
                task=markdown_value(row.get("task")),
                cand=markdown_value(row.get("candidate_ridge_accuracy")),
                no_pre=markdown_value(row.get("no_preexposure_ridge_accuracy")),
                target=markdown_value(row.get("target_shuffled_binding_ridge_accuracy")),
                wrong=markdown_value(row.get("wrong_domain_binding_ridge_accuracy")),
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
            "- `tier5_17d_results.json`: machine-readable manifest.",
            "- `tier5_17d_report.md`: human findings and claim boundary.",
            "- `tier5_17d_runs.csv`: per-task/variant/seed probe rows.",
            "- `tier5_17d_summary.csv`: aggregate probe metrics.",
            "- `tier5_17d_comparisons.csv`: candidate-control edges.",
            "- `tier5_17d_fairness_contract.json`: predeclared no-label/no-reward binding contract.",
            "- `tier5_17d_representation_matrix.png`: ridge-probe accuracy heatmap.",
            "- `tier5_17d_control_edges.png`: binding-control edge plot.",
            "",
            "![tier5_17d_representation_matrix](tier5_17d_representation_matrix.png)",
            "",
            "![tier5_17d_control_edges](tier5_17d_control_edges.png)",
        ]
    )
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_latest(output_dir: Path, report_path: Path, manifest_path: Path, summary_csv: Path, status: str) -> None:
    write_json(
        ROOT / "controlled_test_output" / "tier5_17d_latest_manifest.json",
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
        variants = [CANDIDATE, "no_preexposure", "target_shuffled_binding", "fixed_history_baseline", "oracle_latent_upper_bound"]
        seeds = seeds[:1]
    steps = int(args.steps if not args.smoke else min(args.steps, args.smoke_steps))
    output_dir = Path(args.output_dir) if args.output_dir else ROOT / "controlled_test_output" / f"tier5_17d_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    output_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    for seed in seeds:
        for task_name in tasks:
            task = build_task(task_name, steps=steps, seed=seed)
            for variant_name in variants:
                print(f"[tier5.17d] task={task_name} variant={variant_name} seed={seed}", flush=True)
                variant = VARIANTS[variant_name]
                reps, metadata = representations_for_variant(task, variant, seed=seed, args=args)
                rows.append(evaluate_representation(task, variant_name, reps, metadata, seed=seed, args=args))

    aggregates = aggregate(rows)
    comparisons = build_comparisons(aggregates)
    criteria, summary = evaluate_criteria(aggregates=aggregates, comparisons=comparisons, rows=rows, tasks=tasks, variants=variants, seeds=seeds, args=args)
    status, failure_reason = pass_fail(criteria)

    run_csv = output_dir / "tier5_17d_runs.csv"
    summary_csv = output_dir / "tier5_17d_summary.csv"
    comparisons_csv = output_dir / "tier5_17d_comparisons.csv"
    fairness_json = output_dir / "tier5_17d_fairness_contract.json"
    matrix_png = output_dir / "tier5_17d_representation_matrix.png"
    edges_png = output_dir / "tier5_17d_control_edges.png"
    manifest_json = output_dir / "tier5_17d_results.json"
    report_md = output_dir / "tier5_17d_report.md"

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
    parser.add_argument("--steps", type=int, default=720)
    parser.add_argument("--smoke-steps", type=int, default=220)
    parser.add_argument("--seed-count", type=int, default=3)
    parser.add_argument("--seeds", default="42,43,44")
    parser.add_argument("--base-seed", type=int, default=42)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--stop-on-fail", action="store_true")
    parser.add_argument("--state-dim", type=int, default=24)
    parser.add_argument("--history-length", type=int, default=5)
    parser.add_argument("--random-projection-dim", type=int, default=24)
    parser.add_argument("--prototype-count", type=int, default=14)
    parser.add_argument("--binding-lr", type=float, default=0.05)
    parser.add_argument("--state-decay", type=float, default=0.94)
    parser.add_argument("--stdp-lr", type=float, default=0.08)
    parser.add_argument("--knn-k", type=int, default=5)
    parser.add_argument("--sample-efficiency-threshold", type=float, default=0.78)
    parser.add_argument("--max-abs-raw-dopamine", type=float, default=1e-12)
    parser.add_argument("--min-probe-rows", type=int, default=70)
    parser.add_argument("--min-candidate-probe-accuracy", type=float, default=0.76)
    parser.add_argument("--min-candidate-knn-accuracy", type=float, default=0.64)
    parser.add_argument("--min-edge-vs-no-preexposure", type=float, default=0.10)
    parser.add_argument("--min-edge-vs-target-shuffled", type=float, default=0.08)
    parser.add_argument("--min-edge-vs-wrong-domain", type=float, default=0.08)
    parser.add_argument("--min-edge-vs-fixed-history", type=float, default=0.05)
    parser.add_argument("--min-edge-vs-reservoir", type=float, default=0.05)
    parser.add_argument("--min-edge-vs-stdp", type=float, default=0.04)
    parser.add_argument("--min-edge-vs-best-non-oracle", type=float, default=0.03)
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
