#!/usr/bin/env python3
"""Tier 5.15 spike encoding / temporal code diagnostic.

Tier 5.15 asks whether CRA-style online readout can use temporal spike
structure as information, rather than only treating spikes as a scalar transport
layer. The harness encodes the same controlled task streams through rate,
latency, burst, population, and temporal-interval spike codes, then compares a
bounded temporal CRA readout against time-shuffled and rate-only controls plus
standard online sequence baselines.

Claim boundary: software diagnostic only. This is not SpiNNaker hardware
evidence, not a custom-C/on-chip temporal code implementation, not a frozen
baseline by itself, and not proof of general world modeling or language.
"""

from __future__ import annotations

import argparse
import copy
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

from tier2_learning import (  # noqa: E402
    DEFAULT_AMPLITUDE,
    DEFAULT_DT_SECONDS,
    criterion,
    markdown_value,
    pass_fail,
    safe_corr,
    strict_sign,
    write_csv,
    write_json,
)
from tier4_scaling import mean, min_value, seeds_from_args, stdev  # noqa: E402
from tier5_external_baselines import (  # noqa: E402
    LEARNER_FACTORIES,
    TaskStream,
    build_tasks,
)

TIER = "Tier 5.15 - Spike Encoding / Temporal Code Suite"
DEFAULT_TASKS = "fixed_pattern,delayed_cue,hard_noisy_switching,sensor_control"
DEFAULT_ENCODINGS = "rate,latency,burst,population,temporal_interval"
DEFAULT_MODELS = "temporal_cra,time_shuffle_control,rate_only_control,sign_persistence,online_perceptron,echo_state_network,stdp_only_snn"
GENUINELY_TEMPORAL_ENCODINGS = {"latency", "burst", "temporal_interval"}
CONTROL_MODELS = {"time_shuffle_control", "rate_only_control"}
CRA_MODEL = "temporal_cra"
EPS = 1e-12


@dataclass(frozen=True)
class SpikeEvent:
    step: int
    channel: int
    channel_name: str
    bin: int
    count: int = 1


@dataclass(frozen=True)
class EncodedStep:
    step: int
    encoding: str
    sensory_value: float
    events: tuple[SpikeEvent, ...]
    metadata: dict[str, Any]


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


def parse_csv_list(raw: str, default: list[str]) -> list[str]:
    values = [item.strip() for chunk in str(raw).split(",") for item in chunk.split() if item.strip()]
    if not values or values == ["all"]:
        return list(default)
    return values


def parse_models(raw: str) -> list[str]:
    default = [
        "temporal_cra",
        "time_shuffle_control",
        "rate_only_control",
        "sign_persistence",
        "online_perceptron",
        "online_logistic_regression",
        "echo_state_network",
        "small_gru",
        "stdp_only_snn",
    ]
    return parse_csv_list(raw, default)


def selected_encodings(args: argparse.Namespace) -> list[str]:
    allowed = ["rate", "latency", "burst", "population", "temporal_interval"]
    values = parse_csv_list(args.encodings, allowed)
    unknown = sorted(set(values) - set(allowed))
    if unknown:
        raise ValueError(f"Unknown encoding(s): {unknown}")
    return values


def selected_tasks(args: argparse.Namespace) -> list[str]:
    allowed = ["fixed_pattern", "delayed_cue", "hard_noisy_switching", "sensor_control"]
    values = parse_csv_list(args.tasks, allowed)
    unknown = sorted(set(values) - set(allowed))
    if unknown:
        raise ValueError(f"Unknown task(s): {unknown}")
    return values


def normalize_value(value: float, amplitude: float) -> float:
    scale = float(amplitude) if abs(amplitude) > EPS else 1.0
    return float(np.clip(float(value) / scale, -1.0, 1.0))


def jittered_bin(base: int, rng: np.random.Generator, args: argparse.Namespace) -> int:
    jitter = int(rng.integers(-args.temporal_jitter_bins, args.temporal_jitter_bins + 1)) if args.temporal_jitter_bins > 0 else 0
    return int(np.clip(base + jitter, 0, args.spike_bins_per_step - 1))


def add_event(events: list[SpikeEvent], *, step: int, channel: int, channel_name: str, bin_index: int, args: argparse.Namespace) -> None:
    events.append(
        SpikeEvent(
            step=int(step),
            channel=int(channel),
            channel_name=str(channel_name),
            bin=int(np.clip(bin_index, 0, args.spike_bins_per_step - 1)),
            count=1,
        )
    )


def add_background_noise(events: list[SpikeEvent], *, step: int, rng: np.random.Generator, args: argparse.Namespace) -> None:
    if args.spike_noise_prob <= 0.0:
        return
    for channel, name in enumerate(["cue", "pos", "neg", "pop0", "pop1", "pop2", "pop3", "pop4"]):
        if rng.random() < args.spike_noise_prob:
            add_event(
                events,
                step=step,
                channel=channel,
                channel_name=name,
                bin_index=int(rng.integers(0, args.spike_bins_per_step)),
                args=args,
            )


def encode_step(step: int, value: float, encoding: str, *, rng: np.random.Generator, args: argparse.Namespace) -> EncodedStep:
    scaled = normalize_value(value, args.amplitude)
    sign = strict_sign(scaled)
    magnitude = abs(float(scaled))
    events: list[SpikeEvent] = []
    mid = args.spike_bins_per_step // 2
    last = args.spike_bins_per_step - 1

    if sign != 0:
        if encoding == "rate":
            # Rate code intentionally makes counts/channel informative. It is the
            # scalar-like control encoding, not counted as temporal-code evidence.
            channel = 1 if sign > 0 else 2
            channel_name = "pos" if sign > 0 else "neg"
            count = max(1, int(round(args.rate_base_spikes + magnitude * args.rate_extra_spikes)))
            bins = rng.choice(np.arange(args.spike_bins_per_step), size=count, replace=True)
            for b in bins:
                add_event(events, step=step, channel=channel, channel_name=channel_name, bin_index=int(b), args=args)
        elif encoding == "latency":
            # Same channel and same count for both signs. Only timing carries sign.
            base = 1 + int(round((1.0 - magnitude) * 2.0)) if sign > 0 else last - 1 - int(round((1.0 - magnitude) * 2.0))
            for offset in range(args.fixed_temporal_spikes):
                add_event(events, step=step, channel=0, channel_name="cue", bin_index=jittered_bin(base + offset, rng, args), args=args)
        elif encoding == "burst":
            # Same count, different burst shape. Rate-only controls see identical totals.
            if sign > 0:
                bases = [1, 2, 3, 4]
            else:
                bases = [1, mid, max(mid + 2, last - 2), last - 1]
            for base in bases[: args.fixed_temporal_spikes]:
                add_event(events, step=step, channel=0, channel_name="cue", bin_index=jittered_bin(base, rng, args), args=args)
        elif encoding == "population":
            # Population code uses tuned channels; useful SNN coverage, but not
            # treated as genuinely temporal for pass criteria.
            centers = np.linspace(-1.0, 1.0, args.population_channels)
            tuning = np.exp(-((scaled - centers) ** 2) / (2.0 * args.population_sigma**2))
            tuning = tuning / (np.max(tuning) + EPS)
            for idx, strength in enumerate(tuning):
                count = int(round(args.population_min_spikes + strength * args.population_extra_spikes))
                for _ in range(max(0, count)):
                    add_event(
                        events,
                        step=step,
                        channel=3 + idx,
                        channel_name=f"pop{idx}",
                        bin_index=int(rng.integers(0, args.spike_bins_per_step)),
                        args=args,
                    )
        elif encoding == "temporal_interval":
            # Same channel/count, sign encoded by interval pattern.
            if sign > 0:
                bases = [1, 3, 7]
            else:
                bases = [1, 6, 8]
            for base in bases:
                add_event(events, step=step, channel=0, channel_name="cue", bin_index=jittered_bin(base, rng, args), args=args)
        else:  # pragma: no cover - guarded by parser
            raise ValueError(f"Unknown encoding: {encoding}")

    add_background_noise(events, step=step, rng=rng, args=args)
    metadata = spike_metadata(events, args=args)
    metadata.update(
        {
            "scaled_sensory": scaled,
            "sensory_sign": sign,
            "encoding": encoding,
            "is_genuinely_temporal": encoding in GENUINELY_TEMPORAL_ENCODINGS,
        }
    )
    return EncodedStep(step=int(step), encoding=encoding, sensory_value=float(value), events=tuple(events), metadata=metadata)


def encode_task(task: TaskStream, encoding: str, *, seed: int, args: argparse.Namespace) -> list[EncodedStep]:
    rng = np.random.default_rng(seed + 9150 + stable_hash(encoding))
    return [encode_step(step, float(task.sensory[step]), encoding, rng=rng, args=args) for step in range(task.steps)]


def stable_hash(value: str) -> int:
    return sum((idx + 1) * ord(ch) for idx, ch in enumerate(value))


def shuffled_events(events: tuple[SpikeEvent, ...], *, seed: int, step: int, args: argparse.Namespace) -> tuple[SpikeEvent, ...]:
    rng = np.random.default_rng(seed + 17000 + step * 97)
    shuffled: list[SpikeEvent] = []
    for event in events:
        shuffled.append(
            SpikeEvent(
                step=event.step,
                channel=event.channel,
                channel_name=event.channel_name,
                bin=int(rng.integers(0, args.spike_bins_per_step)),
                count=event.count,
            )
        )
    return tuple(shuffled)


def spike_metadata(events: tuple[SpikeEvent, ...] | list[SpikeEvent], *, args: argparse.Namespace) -> dict[str, Any]:
    bins: list[int] = []
    channels: list[int] = []
    for event in events:
        for _ in range(int(event.count)):
            bins.append(int(event.bin))
            channels.append(int(event.channel))
    total = len(bins)
    unique_bins = len(set((int(c), int(b)) for c, b in zip(channels, bins)))
    if total == 0:
        return {
            "spike_total": 0,
            "spike_sparsity": 0.0,
            "mean_latency_bin": None,
            "first_spike_bin": None,
            "last_spike_bin": None,
            "mean_isi_bins": None,
            "early_fraction": 0.0,
            "late_fraction": 0.0,
        }
    sorted_bins = sorted(bins)
    intervals = [b - a for a, b in zip(sorted_bins[:-1], sorted_bins[1:])]
    mid = args.spike_bins_per_step / 2.0
    return {
        "spike_total": int(total),
        "spike_sparsity": float(unique_bins / max(1, args.total_spike_channels * args.spike_bins_per_step)),
        "mean_latency_bin": float(np.mean(bins)),
        "first_spike_bin": int(min(bins)),
        "last_spike_bin": int(max(bins)),
        "mean_isi_bins": None if not intervals else float(np.mean(intervals)),
        "early_fraction": float(np.mean([b < mid for b in bins])),
        "late_fraction": float(np.mean([b >= mid for b in bins])),
    }


def feature_vector(events: tuple[SpikeEvent, ...], *, args: argparse.Namespace, include_timing: bool) -> np.ndarray:
    channel_counts = np.zeros(args.total_spike_channels, dtype=float)
    bins: list[int] = []
    for event in events:
        channel_counts[int(event.channel)] += float(event.count)
        bins.extend([int(event.bin)] * int(event.count))
    norm = max(1.0, float(args.fixed_temporal_spikes + args.rate_base_spikes + args.rate_extra_spikes))
    channel_counts = channel_counts / norm
    total = float(np.sum(channel_counts))
    timing_features = np.zeros(10, dtype=float)
    if include_timing and bins:
        sorted_bins = sorted(bins)
        intervals = np.diff(sorted_bins) if len(sorted_bins) > 1 else np.asarray([0.0])
        denom = max(1.0, float(args.spike_bins_per_step - 1))
        early = float(np.mean([b < args.spike_bins_per_step / 3.0 for b in bins]))
        late = float(np.mean([b >= 2.0 * args.spike_bins_per_step / 3.0 for b in bins]))
        timing_features = np.asarray(
            [
                float(np.mean(bins)) / denom,
                float(min(bins)) / denom,
                float(max(bins)) / denom,
                float(np.std(bins)) / denom,
                float(np.mean(intervals)) / denom,
                float(np.min(intervals)) / denom if len(intervals) else 0.0,
                early,
                late,
                early - late,
                float(sorted_bins[1] - sorted_bins[0]) / denom if len(sorted_bins) > 1 else 0.0,
            ],
            dtype=float,
        )
    # index 1 is intentionally a signed scalar proxy for sign-persistence-style
    # baselines. Temporal encodings keep this near zero because sign is in time.
    signed_rate_proxy = float(channel_counts[1] - channel_counts[2]) if len(channel_counts) > 2 else 0.0
    return np.asarray([1.0, signed_rate_proxy, total, *channel_counts, *timing_features], dtype=float)


class TemporalReadoutLearner:
    family = "temporal_cra_readout"

    def __init__(self, *, name: str, seed: int, feature_size: int, args: argparse.Namespace):
        self.name = name
        self.lr = float(args.temporal_lr)
        self.l2 = float(args.temporal_l2)
        self.w = np.zeros(feature_size, dtype=float)
        self.update_count = 0

    def step(self, x: np.ndarray) -> tuple[float, Any]:
        return float(np.tanh(np.dot(self.w, x))), x.copy()

    def update(self, state: np.ndarray, label: int) -> None:
        score = float(np.tanh(np.dot(self.w, state)))
        self.w += self.lr * (float(label) - score) * state - self.l2 * self.w
        norm = float(np.linalg.norm(self.w))
        if norm > 100.0:
            self.w *= 100.0 / norm
        self.update_count += 1

    def diagnostics(self) -> dict[str, Any]:
        return {"weight_norm": float(np.linalg.norm(self.w)), "update_count": int(self.update_count)}


class RawSignPersistenceLearner:
    name = "sign_persistence"
    family = "rule"

    def __init__(self, *, seed: int, feature_size: int, args: argparse.Namespace):
        self.last_nonzero = 1.0

    def step(self, x: np.ndarray) -> tuple[float, Any]:
        current = float(x[1]) if len(x) > 1 else 0.0
        sign = strict_sign(current)
        if sign != 0:
            self.last_nonzero = float(sign)
        return self.last_nonzero, None

    def update(self, state: Any, label: int) -> None:
        return None

    def diagnostics(self) -> dict[str, Any]:
        return {"last_nonzero": self.last_nonzero}


def make_learner(model: str, *, seed: int, feature_size: int, args: argparse.Namespace) -> OnlineLearner:
    if model in {"temporal_cra", "time_shuffle_control", "rate_only_control"}:
        return TemporalReadoutLearner(name=model, seed=seed, feature_size=feature_size, args=args)
    if model == "sign_persistence":
        return RawSignPersistenceLearner(seed=seed, feature_size=feature_size, args=args)
    if model not in LEARNER_FACTORIES:
        raise ValueError(f"Unknown model: {model}")
    return LEARNER_FACTORIES[model](seed=seed, feature_size=feature_size, args=args)


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

    pred_eval = [float(r["colony_prediction"]) for r in eval_rows]
    target_eval = [float(r["target_signal_horizon"]) for r in eval_rows]
    pred_tail = [float(r["colony_prediction"]) for r in tail_rows]
    target_tail = [float(r["target_signal_horizon"]) for r in tail_rows]
    spike_totals = [float(r.get("spike_total", 0.0) or 0.0) for r in rows]
    sparsity = [float(r.get("spike_sparsity", 0.0) or 0.0) for r in rows]
    latencies = [float(r["mean_latency_bin"]) for r in rows if r.get("mean_latency_bin") is not None]
    summary = {
        "steps": steps,
        "evaluation_count": len(eval_rows),
        "early_accuracy": accuracy(early_rows),
        "tail_accuracy": accuracy(tail_rows),
        "all_accuracy": accuracy(eval_rows),
        "accuracy_improvement": None,
        "prediction_target_corr": safe_corr(pred_eval, target_eval),
        "tail_prediction_target_corr": safe_corr(pred_tail, target_tail),
        "mean_abs_prediction": float(np.mean([abs(float(r.get("colony_prediction", 0.0) or 0.0)) for r in rows])),
        "mean_spike_total": mean(spike_totals),
        "mean_spike_sparsity": mean(sparsity),
        "mean_latency_bin": mean(latencies),
    }
    if summary["early_accuracy"] is not None and summary["tail_accuracy"] is not None:
        summary["accuracy_improvement"] = float(summary["tail_accuracy"] - summary["early_accuracy"])
    return summary


def run_model_case(task: TaskStream, encoded_steps: list[EncodedStep], model: str, *, seed: int, args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    include_timing = model != "rate_only_control"
    feature_seed = seed + stable_hash(model) + stable_hash(encoded_steps[0].encoding if encoded_steps else "")
    first_events = encoded_steps[0].events if encoded_steps else tuple()
    first_features = feature_vector(first_events, args=args, include_timing=include_timing)
    learner = make_learner(model, seed=feature_seed, feature_size=len(first_features), args=args)
    pending: dict[int, list[tuple[Any, int]]] = {}
    rows: list[dict[str, Any]] = []
    started = time.perf_counter()

    for step, encoded in enumerate(encoded_steps):
        events = encoded.events
        if model == "time_shuffle_control":
            events = shuffled_events(events, seed=feature_seed, step=step, args=args)
        features = feature_vector(events, args=args, include_timing=include_timing)
        prediction, update_state = learner.step(features)
        eval_sign = strict_sign(float(task.evaluation_target[step]))
        pred_sign = strict_sign(float(prediction))
        if bool(task.evaluation_mask[step]) and eval_sign != 0:
            due = int(task.feedback_due_step[step])
            if due >= step and due < task.steps:
                pending.setdefault(due, []).append((update_state, eval_sign))
        meta = spike_metadata(events, args=args)
        row = {
            "task": task.name,
            "encoding": encoded.encoding,
            "model": model,
            "model_family": learner.family,
            "backend": "numpy_temporal_code",
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
            "spike_total": meta["spike_total"],
            "spike_sparsity": meta["spike_sparsity"],
            "mean_latency_bin": meta["mean_latency_bin"],
            "first_spike_bin": meta["first_spike_bin"],
            "last_spike_bin": meta["last_spike_bin"],
            "mean_isi_bins": meta["mean_isi_bins"],
            "early_fraction": meta["early_fraction"],
            "late_fraction": meta["late_fraction"],
            "is_time_shuffled": model == "time_shuffle_control",
            "is_rate_only": model == "rate_only_control",
            "include_timing_features": include_timing,
        }
        rows.append(row)
        for state, label in pending.pop(step, []):
            learner.update(state, label)

    summary = summarize_rows(rows)
    summary.update(
        {
            "task": task.name,
            "encoding": encoded_steps[0].encoding if encoded_steps else "unknown",
            "model": model,
            "model_family": learner.family,
            "backend": "numpy_temporal_code",
            "seed": int(seed),
            "steps": task.steps,
            "runtime_seconds": time.perf_counter() - started,
            "diagnostics": learner.diagnostics(),
            "task_metadata": task.metadata,
        }
    )
    return rows, summary


def spike_trace_rows(task: TaskStream, encoded_steps: list[EncodedStep], *, seed: int, args: argparse.Namespace) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    max_steps = min(task.steps, int(args.spike_trace_steps))
    for encoded in encoded_steps[:max_steps]:
        if not encoded.events:
            rows.append(
                {
                    "task": task.name,
                    "encoding": encoded.encoding,
                    "seed": int(seed),
                    "step": int(encoded.step),
                    "channel": -1,
                    "channel_name": "none",
                    "bin": -1,
                    "count": 0,
                    "sensory_return_1m": float(encoded.sensory_value),
                }
            )
            continue
        for event in encoded.events:
            rows.append(
                {
                    "task": task.name,
                    "encoding": encoded.encoding,
                    "seed": int(seed),
                    "step": int(event.step),
                    "channel": int(event.channel),
                    "channel_name": event.channel_name,
                    "bin": int(event.bin),
                    "count": int(event.count),
                    "sensory_return_1m": float(encoded.sensory_value),
                }
            )
    return rows


def aggregate_summaries(summaries: list[dict[str, Any]]) -> dict[str, Any]:
    if not summaries:
        return {}
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
        "mean_spike_total",
        "mean_spike_sparsity",
        "mean_latency_bin",
    ]
    aggregate = {
        "task": summaries[0]["task"],
        "encoding": summaries[0]["encoding"],
        "model": summaries[0]["model"],
        "model_family": summaries[0].get("model_family"),
        "backend": summaries[0].get("backend"),
        "runs": len(summaries),
        "seeds": [int(s["seed"]) for s in summaries],
    }
    for key in keys:
        vals = [s.get(key) for s in summaries]
        aggregate[f"{key}_mean"] = mean(vals)
        aggregate[f"{key}_std"] = stdev(vals)
        aggregate[f"{key}_min"] = min_value(vals)
    return aggregate


def build_comparisons(aggregates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    comparisons: list[dict[str, Any]] = []
    keys = sorted({(a["task"], a["encoding"]) for a in aggregates})
    for task, encoding in keys:
        cell = [a for a in aggregates if a["task"] == task and a["encoding"] == encoding]
        temporal = next((a for a in cell if a["model"] == CRA_MODEL), None)
        shuffle = next((a for a in cell if a["model"] == "time_shuffle_control"), None)
        rate_only = next((a for a in cell if a["model"] == "rate_only_control"), None)
        externals = [a for a in cell if a["model"] not in {CRA_MODEL, "time_shuffle_control", "rate_only_control"}]
        if not temporal:
            continue
        best_external = max(externals, key=lambda a: -1.0 if a.get("tail_accuracy_mean") is None else float(a["tail_accuracy_mean"]), default=None)
        temporal_tail = float(temporal.get("tail_accuracy_mean") or 0.0)
        row = {
            "task": task,
            "encoding": encoding,
            "is_genuinely_temporal_encoding": encoding in GENUINELY_TEMPORAL_ENCODINGS,
            "temporal_tail_accuracy_mean": temporal.get("tail_accuracy_mean"),
            "temporal_all_accuracy_mean": temporal.get("all_accuracy_mean"),
            "temporal_corr_mean": temporal.get("prediction_target_corr_mean"),
            "time_shuffle_tail_accuracy_mean": None if shuffle is None else shuffle.get("tail_accuracy_mean"),
            "rate_only_tail_accuracy_mean": None if rate_only is None else rate_only.get("tail_accuracy_mean"),
            "temporal_minus_time_shuffle_tail": None if shuffle is None else temporal_tail - float(shuffle.get("tail_accuracy_mean") or 0.0),
            "temporal_minus_rate_only_tail": None if rate_only is None else temporal_tail - float(rate_only.get("tail_accuracy_mean") or 0.0),
            "best_external_model": None if best_external is None else best_external["model"],
            "best_external_tail_accuracy_mean": None if best_external is None else best_external.get("tail_accuracy_mean"),
            "temporal_minus_best_external_tail": None if best_external is None else temporal_tail - float(best_external.get("tail_accuracy_mean") or 0.0),
            "mean_spike_total": temporal.get("mean_spike_total_mean"),
            "mean_spike_sparsity": temporal.get("mean_spike_sparsity_mean"),
            "mean_latency_bin": temporal.get("mean_latency_bin_mean"),
        }
        comparisons.append(row)
    return comparisons


def evaluate_tier(aggregates: list[dict[str, Any]], comparisons: list[dict[str, Any]], artifacts: dict[str, str], args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    seeds = seeds_from_args(args)
    models = parse_models(args.models)
    tasks = selected_tasks(args)
    encodings = selected_encodings(args)
    expected_runs = len(seeds) * len(models) * len(tasks) * len(encodings)
    observed_runs = sum(int(a.get("runs", 0)) for a in aggregates)
    genuine = [c for c in comparisons if c.get("is_genuinely_temporal_encoding")]
    good_temporal_rows = [
        c
        for c in genuine
        if float(c.get("temporal_tail_accuracy_mean") or 0.0) >= args.min_temporal_tail_accuracy
        and (
            float(c.get("temporal_minus_time_shuffle_tail") or 0.0) >= args.min_time_shuffle_tail_edge
            or float(c.get("temporal_minus_rate_only_tail") or 0.0) >= args.min_rate_only_tail_edge
        )
    ]
    nonfinance_good = [c for c in good_temporal_rows if c["task"] == "sensor_control"]
    time_shuffle_losses = [c for c in genuine if float(c.get("temporal_minus_time_shuffle_tail") or 0.0) >= args.min_time_shuffle_tail_edge]
    rate_only_losses = [c for c in genuine if float(c.get("temporal_minus_rate_only_tail") or 0.0) >= args.min_rate_only_tail_edge]
    not_best_dominated = [
        c
        for c in good_temporal_rows
        if c.get("temporal_minus_best_external_tail") is None
        or float(c.get("temporal_minus_best_external_tail") or 0.0) >= -args.best_external_tail_tolerance
    ]
    trace_artifacts = [k for k in artifacts if k.endswith("spike_trace_csv")]
    metadata_artifacts = [k for k in artifacts if k.endswith("encoding_metadata_json")]
    summary = {
        "expected_runs": expected_runs,
        "observed_runs": observed_runs,
        "models": models,
        "tasks": tasks,
        "encodings": encodings,
        "genuinely_temporal_encodings": sorted(GENUINELY_TEMPORAL_ENCODINGS & set(encodings)),
        "good_temporal_rows": good_temporal_rows,
        "good_temporal_row_count": len(good_temporal_rows),
        "nonfinance_good_temporal_row_count": len(nonfinance_good),
        "time_shuffle_loss_count": len(time_shuffle_losses),
        "rate_only_loss_count": len(rate_only_losses),
        "not_best_dominated_good_temporal_count": len(not_best_dominated),
        "spike_trace_artifacts": len(trace_artifacts),
        "encoding_metadata_artifacts": len(metadata_artifacts),
        "claim_boundary": "Software-only temporal-code diagnostic; not hardware, not custom C, and not a frozen promoted baseline by itself.",
    }
    criteria = [
        criterion("full task/encoding/model/seed matrix completed", observed_runs, "==", expected_runs, observed_runs == expected_runs),
        criterion(
            "spike trace artifacts exported",
            len(trace_artifacts),
            ">=",
            len(tasks) * len(encodings) * len(seeds),
            len(trace_artifacts) >= len(tasks) * len(encodings) * len(seeds),
        ),
        criterion(
            "encoding metadata artifacts exported",
            len(metadata_artifacts),
            ">=",
            len(tasks) * len(encodings) * len(seeds),
            len(metadata_artifacts) >= len(tasks) * len(encodings) * len(seeds),
        ),
        criterion(
            "CRA learns under genuinely temporal encoding above controls",
            len(good_temporal_rows),
            ">=",
            args.min_good_temporal_rows,
            len(good_temporal_rows) >= args.min_good_temporal_rows,
            "Requires a genuinely temporal encoding plus loss in time-shuffle or rate-only controls.",
        ),
        criterion(
            "at least one non-finance temporal task passes",
            len(nonfinance_good),
            ">=",
            1,
            len(nonfinance_good) >= 1,
            "Sensor-control prevents this from being only a finance-shaped task result.",
        ),
        criterion(
            "time-shuffle control loses somewhere temporal",
            len(time_shuffle_losses),
            ">=",
            1,
            len(time_shuffle_losses) >= 1,
        ),
        criterion(
            "rate-only control loses somewhere temporal",
            len(rate_only_losses),
            ">=",
            1,
            len(rate_only_losses) >= 1,
        ),
        criterion(
            "not explained by standard temporal-feature baselines everywhere",
            len(not_best_dominated),
            ">=",
            max(1, args.min_good_temporal_rows - 1),
            len(not_best_dominated) >= max(1, args.min_good_temporal_rows - 1),
            "External baselines are reviewer-defense references; Tier 5.15 is primarily a spike-timing causality diagnostic.",
        ),
    ]
    return criteria, summary


def summary_csv_rows(aggregates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for a in aggregates:
        rows.append(
            {
                "task": a["task"],
                "encoding": a["encoding"],
                "model": a["model"],
                "model_family": a.get("model_family"),
                "runs": a.get("runs"),
                "tail_accuracy_mean": a.get("tail_accuracy_mean"),
                "tail_accuracy_std": a.get("tail_accuracy_std"),
                "all_accuracy_mean": a.get("all_accuracy_mean"),
                "prediction_target_corr_mean": a.get("prediction_target_corr_mean"),
                "tail_prediction_target_corr_mean": a.get("tail_prediction_target_corr_mean"),
                "mean_spike_total_mean": a.get("mean_spike_total_mean"),
                "mean_spike_sparsity_mean": a.get("mean_spike_sparsity_mean"),
                "mean_latency_bin_mean": a.get("mean_latency_bin_mean"),
                "runtime_seconds_mean": a.get("runtime_seconds_mean"),
                "evaluation_count_mean": a.get("evaluation_count_mean"),
            }
        )
    return rows


def plot_edges(comparisons: list[dict[str, Any]], path: Path) -> None:
    if plt is None or not comparisons:
        return
    temporal = [c for c in comparisons if c.get("is_genuinely_temporal_encoding")]
    if not temporal:
        return
    labels = [f"{c['task']}\n{c['encoding']}" for c in temporal]
    shuffle_edges = [float(c.get("temporal_minus_time_shuffle_tail") or 0.0) for c in temporal]
    rate_edges = [float(c.get("temporal_minus_rate_only_tail") or 0.0) for c in temporal]
    external_edges = [float(c.get("temporal_minus_best_external_tail") or 0.0) for c in temporal]
    x = np.arange(len(labels))
    width = 0.25
    fig, ax = plt.subplots(figsize=(max(12, len(labels) * 0.7), 6))
    ax.axhline(0.0, color="black", lw=0.8)
    ax.bar(x - width, shuffle_edges, width, label="vs time shuffle", color="#1f6feb")
    ax.bar(x, rate_edges, width, label="vs rate-only", color="#2f855a")
    ax.bar(x + width, external_edges, width, label="vs best external", color="#8250df")
    ax.set_title("Tier 5.15 Temporal-Code Edges")
    ax.set_ylabel("positive means temporal CRA better")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
    ax.grid(axis="y", alpha=0.25)
    ax.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_encoding_matrix(aggregates: list[dict[str, Any]], path: Path) -> None:
    if plt is None or not aggregates:
        return
    rows = [a for a in aggregates if a["model"] == CRA_MODEL]
    if not rows:
        return
    tasks = sorted({a["task"] for a in rows})
    encodings = [e for e in ["rate", "latency", "burst", "population", "temporal_interval"] if any(a["encoding"] == e for a in rows)]
    data = np.zeros((len(tasks), len(encodings)), dtype=float)
    for i, task in enumerate(tasks):
        for j, encoding in enumerate(encodings):
            agg = next((a for a in rows if a["task"] == task and a["encoding"] == encoding), None)
            data[i, j] = float(agg.get("tail_accuracy_mean") or 0.0) if agg else 0.0
    fig, ax = plt.subplots(figsize=(10, 6))
    im = ax.imshow(data, vmin=0.0, vmax=1.0, cmap="viridis")
    ax.set_title("Temporal CRA Tail Accuracy by Encoding")
    ax.set_xticks(range(len(encodings)))
    ax.set_xticklabels([e.replace("_", "\n") for e in encodings])
    ax.set_yticks(range(len(tasks)))
    ax.set_yticklabels([t.replace("_", "\n") for t in tasks])
    for i in range(len(tasks)):
        for j in range(len(encodings)):
            ax.text(j, i, f"{data[i, j]:.2f}", ha="center", va="center", color="white" if data[i, j] < 0.55 else "black")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


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


def write_report(path: Path, result: TestResult, aggregates: list[dict[str, Any]], comparisons: list[dict[str, Any]], args: argparse.Namespace, output_dir: Path) -> None:
    overall = "PASS" if result.passed else "FAIL"
    lines = [
        "# Tier 5.15 Spike Encoding / Temporal Code Findings",
        "",
        f"- Generated: `{utc_now()}`",
        f"- Status: **{overall}**",
        f"- Backend: `numpy_temporal_code`",
        f"- Seeds: `{', '.join(str(s) for s in seeds_from_args(args))}`",
        f"- Tasks: `{', '.join(selected_tasks(args))}`",
        f"- Encodings: `{', '.join(selected_encodings(args))}`",
        f"- Models: `{', '.join(parse_models(args.models))}`",
        f"- Output directory: `{output_dir}`",
        "",
        "Tier 5.15 tests whether spike timing can carry task-relevant information, rather than only using spikes as a scalar transport layer.",
        "",
        "## Claim Boundary",
        "",
        "- Software diagnostic only; no SpiNNaker hardware claim.",
        "- No custom-C/on-chip temporal-code claim.",
        "- Not a frozen baseline by itself; promotion would require a separate compact regression/freeze gate.",
        "- Passing means temporal spike structure was causally useful under this controlled diagnostic.",
        "",
        "## Aggregate Summary",
        "",
        "| Task | Encoding | Model | Family | Tail acc | Overall acc | Corr | Spike total | Sparsity | Runtime s |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for a in aggregates:
        lines.append(
            "| "
            f"{a['task']} | {a['encoding']} | `{a['model']}` | {a.get('model_family')} | "
            f"{markdown_value(a.get('tail_accuracy_mean'))} | "
            f"{markdown_value(a.get('all_accuracy_mean'))} | "
            f"{markdown_value(a.get('prediction_target_corr_mean'))} | "
            f"{markdown_value(a.get('mean_spike_total_mean'))} | "
            f"{markdown_value(a.get('mean_spike_sparsity_mean'))} | "
            f"{markdown_value(a.get('runtime_seconds_mean'))} |"
        )
    lines.extend(
        [
            "",
            "## Temporal-Code Comparisons",
            "",
            "| Task | Encoding | Temporal? | CRA tail | Time-shuffle tail | Rate-only tail | Edge vs shuffle | Edge vs rate-only | Best external | Edge vs best external |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- | ---: |",
        ]
    )
    for c in comparisons:
        lines.append(
            "| "
            f"{c['task']} | {c['encoding']} | {'yes' if c.get('is_genuinely_temporal_encoding') else 'no'} | "
            f"{markdown_value(c.get('temporal_tail_accuracy_mean'))} | "
            f"{markdown_value(c.get('time_shuffle_tail_accuracy_mean'))} | "
            f"{markdown_value(c.get('rate_only_tail_accuracy_mean'))} | "
            f"{markdown_value(c.get('temporal_minus_time_shuffle_tail'))} | "
            f"{markdown_value(c.get('temporal_minus_rate_only_tail'))} | "
            f"`{c.get('best_external_model')}` | "
            f"{markdown_value(c.get('temporal_minus_best_external_tail'))} |"
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
            "- `tier5_15_results.json`: machine-readable manifest.",
            "- `tier5_15_summary.csv`: aggregate task/encoding/model metrics.",
            "- `tier5_15_comparisons.csv`: temporal CRA versus controls/external baselines.",
            "- `tier5_15_temporal_edges.png`: timing-control edge plot.",
            "- `tier5_15_encoding_matrix.png`: temporal CRA tail accuracy matrix.",
            "- `*_timeseries.csv`: per-task/per-encoding/per-model/per-seed traces.",
            "- `*_spike_trace.csv`: sampled input spike trains.",
            "- `*_encoding_metadata.json`: spike timing/sparsity metadata.",
            "",
            "## Plots",
            "",
            "![temporal_edges](tier5_15_temporal_edges.png)",
            "",
            "![encoding_matrix](tier5_15_encoding_matrix.png)",
            "",
        ]
    )
    if MATPLOTLIB_ERROR:
        lines.append(f"Plotting unavailable: `{MATPLOTLIB_ERROR}`")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def run_tier(args: argparse.Namespace, output_dir: Path) -> TestResult:
    models = parse_models(args.models)
    encodings = selected_encodings(args)
    tasks_arg = ",".join(selected_tasks(args))
    all_artifacts: dict[str, str] = {}
    summaries_by_cell: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    metadata_summaries: list[dict[str, Any]] = []

    task_args = copy.copy(args)
    task_args.tasks = tasks_arg

    for seed in seeds_from_args(args):
        tasks = build_tasks(task_args, seed=args.task_seed + seed)
        for task in tasks:
            for encoding in encodings:
                encoded_steps = encode_task(task, encoding, seed=seed, args=args)
                trace_path = output_dir / f"{task.name}_{encoding}_seed{seed}_spike_trace.csv"
                write_csv(trace_path, spike_trace_rows(task, encoded_steps, seed=seed, args=args))
                all_artifacts[f"{task.name}_{encoding}_seed{seed}_spike_trace_csv"] = str(trace_path)

                metadata = {
                    "task": task.name,
                    "encoding": encoding,
                    "seed": int(seed),
                    "steps": task.steps,
                    "is_genuinely_temporal": encoding in GENUINELY_TEMPORAL_ENCODINGS,
                    "mean_spike_total": mean([s.metadata.get("spike_total") for s in encoded_steps]),
                    "mean_spike_sparsity": mean([s.metadata.get("spike_sparsity") for s in encoded_steps]),
                    "mean_latency_bin": mean([s.metadata.get("mean_latency_bin") for s in encoded_steps if s.metadata.get("mean_latency_bin") is not None]),
                    "nonzero_steps": int(sum(1 for s in encoded_steps if int(s.metadata.get("spike_total", 0)) > 0)),
                    "task_metadata": task.metadata,
                }
                metadata_path = output_dir / f"{task.name}_{encoding}_seed{seed}_encoding_metadata.json"
                write_json(metadata_path, metadata)
                all_artifacts[f"{task.name}_{encoding}_seed{seed}_encoding_metadata_json"] = str(metadata_path)
                metadata_summaries.append(metadata)

                for model in models:
                    print(f"[tier5.15] task={task.name} encoding={encoding} model={model} seed={seed}", flush=True)
                    rows, summary = run_model_case(task, encoded_steps, model, seed=seed, args=args)
                    csv_path = output_dir / f"{task.name}_{encoding}_{model}_seed{seed}_timeseries.csv"
                    write_csv(csv_path, rows)
                    all_artifacts[f"{task.name}_{encoding}_{model}_seed{seed}_timeseries_csv"] = str(csv_path)
                    summaries_by_cell.setdefault((task.name, encoding, model), []).append(summary)

    aggregates = [aggregate_summaries(summaries) for _, summaries in sorted(summaries_by_cell.items())]
    comparisons = build_comparisons(aggregates)
    summary_csv = output_dir / "tier5_15_summary.csv"
    comparisons_csv = output_dir / "tier5_15_comparisons.csv"
    metadata_csv = output_dir / "tier5_15_encoding_metadata_summary.csv"
    fairness_json = output_dir / "tier5_15_fairness_contract.json"
    edge_plot = output_dir / "tier5_15_temporal_edges.png"
    matrix_plot = output_dir / "tier5_15_encoding_matrix.png"
    write_csv(summary_csv, summary_csv_rows(aggregates))
    write_csv(comparisons_csv, comparisons)
    write_csv(metadata_csv, metadata_summaries)
    write_json(
        fairness_json,
        {
            "generated_at_utc": utc_now(),
            "tier": TIER,
            "same_task_stream_and_labels_across_encodings": True,
            "same_feedback_due_step_as_task_stream": True,
            "prediction_before_feedback": True,
            "time_shuffle_preserves_count_and_channel_but_randomizes_bins": True,
            "rate_only_preserves_counts_but_removes_timing_features": True,
            "non_finance_adapter_required": "sensor_control",
            "claim_boundary": "Software-only temporal-code diagnostic; promote only after review and separate freeze gate.",
        },
    )
    all_artifacts.update(
        {
            "summary_csv": str(summary_csv),
            "comparisons_csv": str(comparisons_csv),
            "metadata_summary_csv": str(metadata_csv),
            "fairness_contract_json": str(fairness_json),
            "temporal_edges_png": str(edge_plot),
            "encoding_matrix_png": str(matrix_plot),
        }
    )
    plot_edges(comparisons, edge_plot)
    plot_encoding_matrix(aggregates, matrix_plot)
    criteria, tier_summary = evaluate_tier(aggregates, comparisons, all_artifacts, args)
    status, failure_reason = pass_fail(criteria)
    return TestResult(
        name="spike_encoding_temporal_code",
        status=status,
        summary={
            "tier_summary": tier_summary,
            "aggregates": aggregates,
            "comparisons": comparisons,
            "encoding_metadata": metadata_summaries,
            "models": models,
            "encodings": encodings,
            "tasks": selected_tasks(args),
            "seeds": seeds_from_args(args),
            "claim_boundary": tier_summary["claim_boundary"],
        },
        criteria=criteria,
        artifacts=all_artifacts,
        failure_reason=failure_reason,
    )


def write_latest(output_dir: Path, report_path: Path, manifest_path: Path, summary_csv: Path, status: str) -> None:
    latest_path = ROOT / "controlled_test_output" / "tier5_15_latest_manifest.json"
    payload = {
        "generated_at_utc": utc_now(),
        "tier": TIER,
        "status": status,
        "output_dir": str(output_dir),
        "manifest": str(manifest_path),
        "report": str(report_path),
        "summary_csv": str(summary_csv),
        "canonical": False,
        "claim": "Latest Tier 5.15 temporal-code software diagnostic; promote only after review/freeze gate.",
    }
    write_json(latest_path, payload)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Tier 5.15 spike encoding / temporal code diagnostic.")
    parser.add_argument("--backend", choices=["mock", "nest", "brian2"], default="mock", help="Metadata-only backend selector; this tier uses numpy temporal coding.")
    parser.add_argument("--models", default=DEFAULT_MODELS)
    parser.add_argument("--tasks", default=DEFAULT_TASKS)
    parser.add_argument("--encodings", default=DEFAULT_ENCODINGS)
    parser.add_argument("--steps", type=int, default=720)
    parser.add_argument("--base-seed", type=int, default=42)
    parser.add_argument("--seed-count", type=int, default=3)
    parser.add_argument("--seeds", default="")
    parser.add_argument("--task-seed", type=int, default=51500)
    parser.add_argument("--amplitude", type=float, default=DEFAULT_AMPLITUDE)
    parser.add_argument("--dt-seconds", type=float, default=DEFAULT_DT_SECONDS)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--stop-on-fail", action="store_true")
    parser.add_argument("--smoke", action="store_true")

    parser.add_argument("--spike-bins-per-step", type=int, default=12)
    parser.add_argument("--total-spike-channels", type=int, default=8)
    parser.add_argument("--spike-trace-steps", type=int, default=96)
    parser.add_argument("--fixed-temporal-spikes", type=int, default=4)
    parser.add_argument("--rate-base-spikes", type=int, default=1)
    parser.add_argument("--rate-extra-spikes", type=int, default=5)
    parser.add_argument("--spike-noise-prob", type=float, default=0.01)
    parser.add_argument("--temporal-jitter-bins", type=int, default=0)
    parser.add_argument("--population-channels", type=int, default=5)
    parser.add_argument("--population-sigma", type=float, default=0.35)
    parser.add_argument("--population-min-spikes", type=int, default=0)
    parser.add_argument("--population-extra-spikes", type=int, default=4)

    parser.add_argument("--temporal-lr", type=float, default=0.22)
    parser.add_argument("--temporal-l2", type=float, default=0.0002)

    # Task parameters reused by tier5_external_baselines.build_tasks.
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

    # Baseline learner parameters reused by tier5_external_baselines.
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

    parser.add_argument("--min-temporal-tail-accuracy", type=float, default=0.80)
    parser.add_argument("--min-time-shuffle-tail-edge", type=float, default=0.20)
    parser.add_argument("--min-rate-only-tail-edge", type=float, default=0.20)
    parser.add_argument("--min-good-temporal-rows", type=int, default=2)
    parser.add_argument("--best-external-tail-tolerance", type=float, default=0.20)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.smoke:
        args.tasks = "delayed_cue,sensor_control"
        args.encodings = "latency,rate"
        args.steps = min(int(args.steps), 220)
        args.seed_count = 1
        args.seeds = ""
        args.models = "temporal_cra,time_shuffle_control,rate_only_control,sign_persistence,online_perceptron"
        args.min_good_temporal_rows = 1
    random.seed(int(args.base_seed))
    np.random.seed(int(args.base_seed))
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = args.output_dir or (ROOT / "controlled_test_output" / f"tier5_15_{timestamp}")
    output_dir.mkdir(parents=True, exist_ok=True)

    result = run_tier(args, output_dir)
    manifest_path = output_dir / "tier5_15_results.json"
    report_path = output_dir / "tier5_15_report.md"
    summary_csv = output_dir / "tier5_15_summary.csv"
    comparisons_csv = output_dir / "tier5_15_comparisons.csv"
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
            "encodings": result.summary["encodings"],
            "seeds": result.summary["seeds"],
        },
        "artifacts": {
            "summary_csv": str(summary_csv),
            "comparisons_csv": str(comparisons_csv),
            "report_md": str(report_path),
            "temporal_edges_png": str(output_dir / "tier5_15_temporal_edges.png"),
            "encoding_matrix_png": str(output_dir / "tier5_15_encoding_matrix.png"),
            "fairness_contract_json": str(output_dir / "tier5_15_fairness_contract.json"),
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
                "comparisons_csv": str(comparisons_csv),
                "failure_reason": result.failure_reason,
            },
            indent=2,
        )
    )
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
