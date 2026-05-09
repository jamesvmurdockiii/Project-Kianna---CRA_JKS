#!/usr/bin/env python3
"""Tier 7.7j - capacity sham-separation / state-specificity scoring gate.

This gate scores the Tier 7.7i contract. It is a diagnostic only: no new CRA
mechanism, no repair, no baseline freeze, no hardware/native transfer, and no
benchmark tuning.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
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

from tier4_scaling import mean, stdev  # noqa: E402
from tier5_19a_temporal_substrate_reference import (  # noqa: E402
    FeatureBundle,
    criterion,
    json_safe,
    parse_timescales,
)
from tier5_19b_temporal_substrate_gate import temporal_features_variant  # noqa: E402
from tier7_0_standard_dynamical_benchmarks import (  # noqa: E402
    build_task as build_standard_task,
    parse_csv,
    parse_seeds,
)
from tier7_0b_continuous_regression_failure_analysis import evaluate_probe, lag_matrix  # noqa: E402
from tier7_0c_continuous_readout_repair import normalize_features, shuffled_rows, shuffled_target  # noqa: E402
from tier7_7f_repaired_finite_stream_long_run_scoreboard import (  # noqa: E402
    REPAIRED_GENERATOR_ID,
    repaired_narma10_series,
)


TIER = "Tier 7.7j - Capacity Sham-Separation / State-Specificity Scoring Gate"
RUNNER_REVISION = "tier7_7j_capacity_sham_separation_scoring_gate_20260509_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_7j_20260509_capacity_sham_separation_scoring_gate"
CONTRACT_77I = CONTROLLED / "tier7_7i_20260509_capacity_sham_separation_contract" / "tier7_7i_results.json"
PREREQ_77H = CONTROLLED / "tier7_7h_20260509_lorenz_capacity_narma_memory_scoring_gate" / "tier7_7h_results.json"

DEFAULT_TASKS = "mackey_glass,lorenz,narma10"
DEFAULT_LENGTHS = "8000,16000,32000"
DEFAULT_SEEDS = "42,43,44"
DEFAULT_CAPACITIES = "16,32,64,128"
DEFAULT_PERMUTED_OFFSETS = "11,23,37,71,101"

CANDIDATE = "candidate_full_recurrence"
PERMUTED = "permuted_recurrence"
STATE_RESET = "state_reset_by_capacity"
ORTHOGONAL = "orthogonal_random_basis"
BLOCK = "block_structured_basis"
DELAY_EMBED = "causal_delay_embedding_reference"
TARGET_SHUFFLE = "target_shuffle_candidate"
TIME_SHUFFLE = "time_shuffle_candidate"


@dataclass(frozen=True)
class ProbeResult:
    row: dict[str, Any]
    prediction: np.ndarray
    features: np.ndarray
    feature_names: list[str]
    hidden_columns: list[int]
    weights: np.ndarray


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


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


def safe_float(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def parse_int_csv(raw: str) -> list[int]:
    values = [int(item) for item in parse_csv(raw)]
    if not values:
        raise ValueError("at least one integer value is required")
    return values


def ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator <= 0.0:
        return None
    if not (math.isfinite(numerator) and math.isfinite(denominator)):
        return None
    return numerator / denominator


def geomean(values: list[float]) -> float | None:
    clean = [float(value) for value in values if value > 0.0 and math.isfinite(float(value))]
    if not clean:
        return None
    return float(math.exp(sum(math.log(value) for value in clean) / len(clean)))


def build_task(name: str, length: int, seed: int, horizon: int) -> Any:
    if name == "narma10":
        return repaired_narma10_series(length, seed, horizon=horizon)
    return build_standard_task(name, length, seed, horizon)


def online_lms_with_weights(
    features: np.ndarray,
    target: np.ndarray,
    *,
    train_end: int,
    lr: float,
    decay: float,
    weight_clip: float,
    output_clip: float,
    update_target: np.ndarray | None = None,
    update_enabled: bool = True,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    del train_end
    x = np.asarray(features, dtype=float)
    y = np.asarray(target, dtype=float)
    update_y = y if update_target is None else np.asarray(update_target, dtype=float)
    w = np.zeros(x.shape[1], dtype=float)
    pred = np.zeros(len(y), dtype=float)
    norm_trace: list[float] = []
    for step, row in enumerate(x):
        value = float(np.dot(w, row))
        if output_clip > 0.0:
            value = float(np.clip(value, -output_clip, output_clip))
        pred[step] = value
        if update_enabled:
            err = float(update_y[step] - value)
            denom = 1.0 + float(np.dot(row, row))
            w = (1.0 - float(decay)) * w + (float(lr) * err / denom) * row
            norm = float(np.linalg.norm(w))
            if weight_clip > 0.0 and norm > weight_clip:
                w *= float(weight_clip) / norm
        norm_trace.append(float(np.linalg.norm(w)))
    return pred, w, {
        "lr": float(lr),
        "decay": float(decay),
        "weight_clip": float(weight_clip),
        "output_clip": float(output_clip),
        "final_weight_norm": float(np.linalg.norm(w)),
        "max_weight_norm": max(norm_trace) if norm_trace else 0.0,
        "update_enabled": bool(update_enabled),
    }


def run_probe_model(
    task: Any,
    *,
    seed: int,
    length: int,
    capacity: int,
    probe_family: str,
    probe_id: str,
    features: np.ndarray,
    feature_names: list[str],
    hidden_columns: list[int],
    args: argparse.Namespace,
    update_target: np.ndarray | None = None,
    diagnostics: dict[str, Any] | None = None,
) -> ProbeResult:
    norm_features, norm_meta = normalize_features(features, task.train_end)
    pred, weights, online_meta = online_lms_with_weights(
        norm_features,
        task.target,
        train_end=task.train_end,
        lr=args.readout_lr,
        decay=args.readout_decay,
        weight_clip=args.weight_clip,
        output_clip=args.output_clip,
        update_target=update_target,
        update_enabled=True,
    )
    row = evaluate_probe(
        task.name,
        seed,
        task.train_end,
        task.target,
        pred,
        probe_id,
        {
            **(diagnostics or {}),
            "readout": "online_normalized_lms_prediction_before_update",
            "feature_norm": "train_prefix_only",
            "online_meta": online_meta,
            "norm_columns": int(len(norm_meta["feature_mu"])),
            "feature_count": int(features.shape[1]),
            "hidden_feature_count": int(len(hidden_columns)),
        },
    )
    row.update(
        {
            "length": int(length),
            "capacity_units": int(capacity),
            "probe_family": probe_family,
            "probe_id": probe_id,
            "feature_count": int(features.shape[1]),
            "hidden_feature_count": int(len(hidden_columns)),
        }
    )
    return ProbeResult(row=row, prediction=pred, features=features, feature_names=feature_names, hidden_columns=hidden_columns, weights=weights)


def basis_features(
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
) -> FeatureBundle:
    values = np.asarray(observed, dtype=float)
    hidden_units = max(1, int(hidden_units))
    traces = np.zeros(len(timescales), dtype=float)
    hidden = np.zeros(hidden_units, dtype=float)
    rng = np.random.default_rng(seed + (77101 if mode == "orthogonal" else 77203))

    def driver_for(x: float, previous_traces: np.ndarray) -> np.ndarray:
        trace_deltas = np.diff(traces) if traces.size > 1 else np.asarray([], dtype=float)
        novelty = x - float(previous_traces[-1] if previous_traces.size else 0.0)
        return np.concatenate([[x], traces, trace_deltas, [novelty]])

    sample_driver = driver_for(0.0, traces.copy())
    w_in = rng.normal(0.0, float(input_scale), size=(hidden_units, len(sample_driver)))
    if mode == "orthogonal":
        raw = rng.normal(0.0, 1.0, size=(hidden_units, hidden_units))
        q, _r = np.linalg.qr(raw)
        w_rec = q * float(recurrent_scale)
        decay = np.full(hidden_units, float(hidden_decay), dtype=float)
    elif mode == "block":
        w_rec = np.zeros((hidden_units, hidden_units), dtype=float)
        decay = np.zeros(hidden_units, dtype=float)
        blocks = np.array_split(np.arange(hidden_units), min(4, hidden_units))
        decay_values = [0.52, 0.66, 0.78, 0.88]
        scale_values = [0.35, 0.50, 0.65, 0.80]
        for idx, block in enumerate(blocks):
            raw = rng.normal(0.0, 1.0, size=(len(block), len(block)))
            q, _r = np.linalg.qr(raw)
            w_rec[np.ix_(block, block)] = q * float(scale_values[idx % len(scale_values)])
            decay[block] = float(decay_values[idx % len(decay_values)])
    else:
        raise ValueError(f"unknown basis mode {mode!r}")

    rows: list[np.ndarray] = []
    for value in values:
        x = float(value)
        previous = traces.copy()
        for idx, tau in enumerate(timescales):
            alpha = 1.0 - math.exp(-1.0 / max(1e-6, float(tau)))
            traces[idx] = traces[idx] + alpha * (x - traces[idx])
        driver = driver_for(x, previous)
        hidden = np.tanh(decay * hidden + w_rec @ hidden + w_in @ driver)
        trace_deltas = np.diff(traces) if traces.size > 1 else np.asarray([], dtype=float)
        novelty = x - float(previous[-1] if previous.size else 0.0)
        rows.append(np.concatenate([[1.0, x], traces, trace_deltas, [novelty], hidden]))
    names = (
        ["bias", "observed_current"]
        + [f"ema_tau_{tau:g}" for tau in timescales]
        + [f"ema_delta_{i}_{i+1}" for i in range(max(0, len(timescales) - 1))]
        + ["novelty_vs_slowest_ema"]
        + [f"hidden_{idx}" for idx in range(hidden_units)]
    )
    features = np.vstack(rows)
    return FeatureBundle(
        features=features,
        temporal_start=len(names) - hidden_units,
        names=names,
        diagnostics={
            "state_location": f"{mode}_basis_reference",
            "mode": mode,
            "timescales": timescales,
            "hidden_units": int(hidden_units),
            "recurrent_scale": float(recurrent_scale),
            "input_scale": float(input_scale),
            "hidden_decay": float(hidden_decay),
            "feature_count": int(features.shape[1]),
            "train_end": int(train_end),
        },
    )


def hidden_columns(names: list[str]) -> list[int]:
    return [idx for idx, name in enumerate(names) if name.startswith("hidden_")]


def geometry_metrics(features: np.ndarray, columns: list[int], train_end: int, *, split: str = "test") -> dict[str, Any]:
    if not columns:
        return {
            "participation_ratio": None,
            "participation_ratio_per_unit": None,
            "rank95_variance_count": None,
            "top_pc_fraction": None,
            "state_norm_mean": None,
            "state_norm_std": None,
            "step_delta_mean": None,
            "step_delta_std": None,
            "total_state_variance": None,
        }
    x = np.asarray(features[:, columns], dtype=float)
    seg = x[train_end:] if split == "test" else x[:train_end]
    if len(seg) < 3:
        return {}
    norms = np.linalg.norm(seg, axis=1)
    deltas = np.linalg.norm(np.diff(seg, axis=0), axis=1)
    centered = seg - np.mean(seg, axis=0, keepdims=True)
    cov = (centered.T @ centered) / max(1, len(seg) - 1)
    eig = np.maximum(np.linalg.eigvalsh(cov), 0.0)
    total = float(np.sum(eig))
    total_sq = float(np.sum(eig * eig))
    pr = (total * total / total_sq) if total_sq > 1e-18 else 0.0
    desc = np.sort(eig)[::-1]
    rank95 = int(np.searchsorted(np.cumsum(desc) / total, 0.95) + 1) if total > 1e-18 else 0
    top = float(desc[0] / total) if total > 1e-18 and desc.size else 0.0
    return {
        "participation_ratio": float(pr),
        "participation_ratio_per_unit": float(pr / max(1, len(columns))),
        "rank95_variance_count": rank95,
        "top_pc_fraction": top,
        "state_norm_mean": float(np.mean(norms)),
        "state_norm_std": float(np.std(norms)),
        "step_delta_mean": float(np.mean(deltas)),
        "step_delta_std": float(np.std(deltas)),
        "total_state_variance": float(np.sum(np.var(seg, axis=0))),
    }


def linear_cka(x: np.ndarray, y: np.ndarray) -> float | None:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if x.size == 0 or y.size == 0 or x.shape[0] != y.shape[0]:
        return None
    x = x - np.mean(x, axis=0, keepdims=True)
    y = y - np.mean(y, axis=0, keepdims=True)
    xy = float(np.linalg.norm(x.T @ y, ord="fro") ** 2)
    xx = float(np.linalg.norm(x.T @ x, ord="fro"))
    yy = float(np.linalg.norm(y.T @ y, ord="fro"))
    if xx <= 1e-18 or yy <= 1e-18:
        return None
    return xy / (xx * yy)


def readout_metrics(weights: np.ndarray, hidden_cols: list[int]) -> dict[str, Any]:
    w = np.asarray(weights, dtype=float)
    energy = w * w
    total = float(np.sum(energy))
    pr = (total * total / float(np.sum(energy * energy))) if total > 1e-18 and float(np.sum(energy * energy)) > 1e-18 else 0.0
    top = float(np.max(energy) / total) if total > 1e-18 and energy.size else 0.0
    hidden_energy = float(np.sum(energy[hidden_cols])) if hidden_cols else 0.0
    return {
        "readout_weight_pr": float(pr),
        "top_weight_fraction": top,
        "hidden_weight_energy_fraction": hidden_energy / total if total > 1e-18 else 0.0,
        "final_weight_norm": float(np.linalg.norm(w)),
    }


def run_task_capacity(task: Any, *, seed: int, length: int, capacity: int, args: argparse.Namespace) -> tuple[list[ProbeResult], list[dict[str, Any]]]:
    timescales = parse_timescales(args.temporal_timescales)
    base_kwargs = {
        "seed": seed,
        "train_end": task.train_end,
        "timescales": timescales,
        "hidden_units": capacity,
        "recurrent_scale": args.temporal_recurrent_scale,
        "input_scale": args.temporal_input_scale,
        "hidden_decay": args.temporal_hidden_decay,
    }
    results: list[ProbeResult] = []
    kernel_rows: list[dict[str, Any]] = []

    candidate = temporal_features_variant(task.observed, mode="full", **base_kwargs)
    candidate_result = run_probe_model(
        task,
        seed=seed,
        length=length,
        capacity=capacity,
        probe_family=CANDIDATE,
        probe_id=f"{CANDIDATE}_{capacity}",
        features=candidate.features,
        feature_names=candidate.names,
        hidden_columns=hidden_columns(candidate.names),
        args=args,
        diagnostics={**candidate.diagnostics, "role": "locked candidate full recurrence"},
    )
    results.append(candidate_result)

    state_reset = temporal_features_variant(
        task.observed,
        mode="full",
        reset_interval=args.state_reset_interval,
        **base_kwargs,
    )
    results.append(
        run_probe_model(
            task,
            seed=seed,
            length=length,
            capacity=capacity,
            probe_family=STATE_RESET,
            probe_id=f"{STATE_RESET}_{capacity}",
            features=state_reset.features,
            feature_names=state_reset.names,
            hidden_columns=hidden_columns(state_reset.names),
            args=args,
            diagnostics={**state_reset.diagnostics, "role": "state reset control"},
        )
    )

    for offset in parse_int_csv(args.permuted_offsets):
        permuted = temporal_features_variant(
            task.observed,
            mode="permuted_recurrence",
            recurrent_seed_offset=offset,
            **base_kwargs,
        )
        results.append(
            run_probe_model(
                task,
                seed=seed,
                length=length,
                capacity=capacity,
                probe_family=PERMUTED,
                probe_id=f"{PERMUTED}_{capacity}_offset_{offset}",
                features=permuted.features,
                feature_names=permuted.names,
                hidden_columns=hidden_columns(permuted.names),
                args=args,
                diagnostics={**permuted.diagnostics, "role": "permuted recurrence ensemble", "offset": int(offset)},
            )
        )

    for mode, family in [("orthogonal", ORTHOGONAL), ("block", BLOCK)]:
        bundle = basis_features(task.observed, mode=mode, **base_kwargs)
        results.append(
            run_probe_model(
                task,
                seed=seed,
                length=length,
                capacity=capacity,
                probe_family=family,
                probe_id=f"{family}_{capacity}",
                features=bundle.features,
                feature_names=bundle.names,
                hidden_columns=hidden_columns(bundle.names),
                args=args,
                diagnostics={**bundle.diagnostics, "role": f"{mode} basis reference"},
            )
        )

    wrong_target = shuffled_target(task.target, task.train_end, seed)
    results.append(
        run_probe_model(
            task,
            seed=seed,
            length=length,
            capacity=capacity,
            probe_family=TARGET_SHUFFLE,
            probe_id=f"{TARGET_SHUFFLE}_{capacity}",
            features=candidate.features,
            feature_names=candidate.names,
            hidden_columns=hidden_columns(candidate.names),
            args=args,
            update_target=wrong_target,
            diagnostics={**candidate.diagnostics, "control": "target shuffle candidate"},
        )
    )
    shuffled = shuffled_rows(candidate.features, task.train_end, seed)
    results.append(
        run_probe_model(
            task,
            seed=seed,
            length=length,
            capacity=capacity,
            probe_family=TIME_SHUFFLE,
            probe_id=f"{TIME_SHUFFLE}_{capacity}",
            features=shuffled,
            feature_names=candidate.names,
            hidden_columns=hidden_columns(candidate.names),
            args=args,
            diagnostics={**candidate.diagnostics, "control": "time/row shuffle candidate"},
        )
    )

    cand_hidden = candidate_result.features[task.train_end:, candidate_result.hidden_columns]
    for result in results:
        if result.row["probe_id"] == candidate_result.row["probe_id"] or not result.hidden_columns:
            continue
        other = result.features[task.train_end:, result.hidden_columns]
        kernel_rows.append(
            {
                "task": task.name,
                "length": int(length),
                "seed": int(seed),
                "capacity_units": int(capacity),
                "reference_probe_id": candidate_result.row["probe_id"],
                "probe_id": result.row["probe_id"],
                "probe_family": result.row["probe_family"],
                "linear_cka_to_candidate": linear_cka(cand_hidden, other),
            }
        )
    return results, kernel_rows


def run_delay_embedding(task: Any, *, seed: int, length: int, args: argparse.Namespace) -> ProbeResult:
    features = lag_matrix(task.observed, args.delay_embedding_history)
    names = ["bias"] + [f"lag_{idx}" for idx in range(args.delay_embedding_history)]
    return run_probe_model(
        task,
        seed=seed,
        length=length,
        capacity=0,
        probe_family=DELAY_EMBED,
        probe_id=DELAY_EMBED,
        features=features,
        feature_names=names,
        hidden_columns=list(range(1, features.shape[1])),
        args=args,
        diagnostics={"role": "causal delay embedding observability reference", "history": int(args.delay_embedding_history)},
    )


def summarize_scoreboard(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(row["task"], row["probe_family"], row["capacity_units"])].append(row)
    out: list[dict[str, Any]] = []
    for (task, family, capacity), subset in sorted(groups.items()):
        pass_rows = [row for row in subset if row.get("status") == "pass" and safe_float(row.get("mse")) is not None]
        mses = [float(row["mse"]) for row in pass_rows]
        tails = [float(row["tail_mse"]) for row in pass_rows if safe_float(row.get("tail_mse")) is not None]
        corrs = [float(row["test_corr"]) for row in pass_rows if safe_float(row.get("test_corr")) is not None]
        out.append(
            {
                "task": task,
                "probe_family": family,
                "capacity_units": int(capacity),
                "status": "pass" if pass_rows else "fail",
                "run_count": len(pass_rows),
                "geomean_mse": geomean(mses),
                "mse_mean": mean(mses),
                "mse_std": stdev(mses),
                "tail_mse_mean": mean(tails),
                "test_corr_mean": mean(corrs),
            }
        )
    return out


def summarize_numeric(rows: list[dict[str, Any]], value_keys: list[str], group_keys: list[str]) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[tuple(row.get(key) for key in group_keys)].append(row)
    out: list[dict[str, Any]] = []
    for key_tuple, subset in sorted(groups.items()):
        item = {key: value for key, value in zip(group_keys, key_tuple)}
        item["run_count"] = len(subset)
        for value_key in value_keys:
            values = [float(row[value_key]) for row in subset if safe_float(row.get(value_key)) is not None]
            item[f"{value_key}_mean"] = mean(values)
            item[f"{value_key}_std"] = stdev(values)
            item[f"{value_key}_max"] = max(values) if values else None
            item[f"{value_key}_min"] = min(values) if values else None
        out.append(item)
    return out


def metric(summary: list[dict[str, Any]], task: str, family: str, capacity: int, key: str = "geomean_mse") -> float | None:
    row = next((item for item in summary if item["task"] == task and item["probe_family"] == family and int(item["capacity_units"]) == int(capacity)), None)
    return safe_float(row.get(key)) if row else None


def classify(score_summary: list[dict[str, Any]], geometry_summary: list[dict[str, Any]], readout_summary: list[dict[str, Any]], kernel_summary: list[dict[str, Any]]) -> dict[str, Any]:
    lorenz_candidate = metric(score_summary, "lorenz", CANDIDATE, 128)
    lorenz_target = metric(score_summary, "lorenz", TARGET_SHUFFLE, 128)
    lorenz_time = metric(score_summary, "lorenz", TIME_SHUFFLE, 128)
    lorenz_delay = metric(score_summary, "lorenz", DELAY_EMBED, 0)
    generic_families = [PERMUTED, ORTHOGONAL, BLOCK]
    generic_values = [(family, metric(score_summary, "lorenz", family, 128)) for family in generic_families]
    generic_values = [(family, value) for family, value in generic_values if value is not None]
    best_generic = min(generic_values, key=lambda item: item[1]) if generic_values else (None, None)

    def geom_value(family: str, capacity: int, key: str) -> float | None:
        row = next((item for item in geometry_summary if item["task"] == "lorenz" and item["probe_family"] == family and int(item["capacity_units"]) == int(capacity)), None)
        return safe_float(row.get(f"{key}_mean")) if row else None

    candidate_pr_128 = geom_value(CANDIDATE, 128, "participation_ratio")
    candidate_pr_64 = geom_value(CANDIDATE, 64, "participation_ratio")
    max_probe_pr_128 = max([value for value in [geom_value(family, 128, "participation_ratio") for family in [CANDIDATE, PERMUTED, ORTHOGONAL, BLOCK]] if value is not None], default=None)

    def readout_value(family: str, capacity: int, key: str) -> float | None:
        row = next((item for item in readout_summary if item["task"] == "lorenz" and item["probe_family"] == family and int(item["capacity_units"]) == int(capacity)), None)
        return safe_float(row.get(f"{key}_mean")) if row else None

    candidate_readout_pr = readout_value(CANDIDATE, 128, "readout_weight_pr")
    candidate_top_weight = readout_value(CANDIDATE, 128, "top_weight_fraction")
    target_guard = ratio(lorenz_target, lorenz_candidate)
    time_guard = ratio(lorenz_time, lorenz_candidate)
    generic_margin = ratio(best_generic[1], lorenz_candidate)
    delay_margin = ratio(lorenz_delay, lorenz_candidate)
    guards_ok = (target_guard is not None and target_guard >= 5.0) and (time_guard is not None and time_guard >= 5.0)
    low_rank = (
        candidate_pr_64 is not None
        and candidate_pr_128 is not None
        and max_probe_pr_128 is not None
        and candidate_pr_64 <= 3.0
        and candidate_pr_128 <= 3.0
        and max_probe_pr_128 <= 3.5
    )
    generic_explains = generic_margin is not None and generic_margin <= 1.02
    observability = delay_margin is not None and delay_margin <= 0.75
    readout_limited = (
        candidate_pr_128 is not None
        and candidate_pr_128 >= 8.0
        and candidate_readout_pr is not None
        and candidate_readout_pr <= 3.0
        and candidate_top_weight is not None
        and candidate_top_weight >= 0.45
    )
    candidate_specific = (
        guards_ok
        and not low_rank
        and generic_margin is not None
        and generic_margin >= 1.05
        and candidate_pr_128 is not None
        and candidate_pr_128 > 3.0
    )
    if not guards_ok:
        outcome = "inconclusive_or_sham_blocked"
        recommendation = "Do not repair or promote; first fix target/time-shuffle guard separation."
    elif low_rank:
        outcome = "low_rank_collapse_confirmed"
        recommendation = "Document low-rank dynamic-state collapse; next repair should target effective state dimensionality rather than nominal capacity."
    elif generic_explains:
        outcome = "generic_basis_explains_gain"
        recommendation = "Capacity gain is real but not CRA-specific; route to state-interface/connectivity redesign before mechanism promotion."
    elif readout_limited:
        outcome = "readout_bottleneck"
        recommendation = "State geometry exists but readout is concentrated; repair readout/state interface before changing recurrence."
    elif observability:
        outcome = "observability_bottleneck"
        recommendation = "Causal delay embedding strongly outperforms; disclose single-channel Lorenz observability as the main bottleneck."
    elif candidate_specific:
        outcome = "candidate_specific_state_confirmed"
        recommendation = "Candidate-specific state geometry is supported; proceed to a predeclared repair/promotion decision gate."
    else:
        outcome = "inconclusive_or_sham_blocked"
        recommendation = "No stable state-specificity class was isolated; do not add mechanisms yet."
    return {
        "outcome": outcome,
        "recommendation": recommendation,
        "diagnostics": {
            "lorenz_candidate_128_geomean_mse": lorenz_candidate,
            "best_generic_family_128": best_generic[0],
            "best_generic_128_geomean_mse": best_generic[1],
            "best_generic_divided_by_candidate": generic_margin,
            "target_shuffle_divided_by_candidate": target_guard,
            "time_shuffle_divided_by_candidate": time_guard,
            "delay_embedding_divided_by_candidate": delay_margin,
            "candidate_pr_64": candidate_pr_64,
            "candidate_pr_128": candidate_pr_128,
            "max_probe_pr_128": max_probe_pr_128,
            "candidate_readout_pr_128": candidate_readout_pr,
            "candidate_top_weight_fraction_128": candidate_top_weight,
            "guards_ok": guards_ok,
            "low_rank": low_rank,
            "generic_explains": generic_explains,
            "readout_limited": readout_limited,
            "observability": observability,
        },
        "claim_allowed": {
            "candidate_specific_state": outcome == "candidate_specific_state_confirmed",
            "generic_basis_explains_gain": outcome == "generic_basis_explains_gain",
            "low_rank_collapse": outcome == "low_rank_collapse_confirmed",
            "readout_bottleneck": outcome == "readout_bottleneck",
            "observability_bottleneck": outcome == "observability_bottleneck",
            "baseline_freeze": False,
            "mechanism_promotion": False,
            "hardware_or_native_transfer": False,
            "public_usefulness": False,
        },
        "nonclaims": [
            "not a baseline freeze",
            "not a mechanism promotion",
            "not hardware/native transfer",
            "not external-baseline superiority",
            "not broad public usefulness",
            "not language, AGI, or ASI evidence",
        ],
    }


def write_report(output_dir: Path, payload: dict[str, Any]) -> None:
    c = payload["classification"]
    d = c["diagnostics"]
    lines = [
        "# Tier 7.7j Capacity Sham-Separation / State-Specificity Scoring Gate",
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
        "## Lorenz 128 Diagnostic",
        "",
        f"- Candidate geomean MSE: `{d['lorenz_candidate_128_geomean_mse']}`",
        f"- Best generic family: `{d['best_generic_family_128']}`",
        f"- Best generic geomean MSE: `{d['best_generic_128_geomean_mse']}`",
        f"- Generic / candidate: `{d['best_generic_divided_by_candidate']}`",
        f"- Candidate PR at 64: `{d['candidate_pr_64']}`",
        f"- Candidate PR at 128: `{d['candidate_pr_128']}`",
        f"- Max probe PR at 128: `{d['max_probe_pr_128']}`",
        f"- Candidate readout PR at 128: `{d['candidate_readout_pr_128']}`",
        f"- Candidate top-weight fraction at 128: `{d['candidate_top_weight_fraction_128']}`",
        "",
        "## Nonclaims",
        "",
    ]
    for item in c["nonclaims"]:
        lines.append(f"- {item}")
    lines.append("")
    (output_dir / "tier7_7j_report.md").write_text("\n".join(lines), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=TIER)
    parser.add_argument("--tasks", default=DEFAULT_TASKS)
    parser.add_argument("--lengths", default=DEFAULT_LENGTHS)
    parser.add_argument("--seeds", default=DEFAULT_SEEDS)
    parser.add_argument("--capacities", default=DEFAULT_CAPACITIES)
    parser.add_argument("--permuted-offsets", default=DEFAULT_PERMUTED_OFFSETS)
    parser.add_argument("--horizon", type=int, default=8)
    parser.add_argument("--history", type=int, default=12)
    parser.add_argument("--delay-embedding-history", type=int, default=64)
    parser.add_argument("--readout-lr", type=float, default=0.08)
    parser.add_argument("--readout-decay", type=float, default=1e-5)
    parser.add_argument("--weight-clip", type=float, default=20.0)
    parser.add_argument("--output-clip", type=float, default=3.0)
    parser.add_argument("--temporal-timescales", default="2,4,8,16,32,64,128")
    parser.add_argument("--temporal-recurrent-scale", type=float, default=0.65)
    parser.add_argument("--temporal-input-scale", type=float, default=0.45)
    parser.add_argument("--temporal-hidden-decay", type=float, default=0.72)
    parser.add_argument("--state-reset-interval", type=int, default=64)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--smoke", action="store_true")
    return parser


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if args.smoke:
        args.tasks = "lorenz"
        args.lengths = "720"
        args.seeds = "42"
        args.capacities = "16,32"
        args.permuted_offsets = "71"
    tasks = parse_csv(args.tasks)
    lengths = parse_int_csv(args.lengths)
    seeds = parse_seeds(argparse.Namespace(seeds=args.seeds, seed_count=None, base_seed=42))
    capacities = parse_int_csv(args.capacities)
    started = time.perf_counter()
    prereq_77i = read_json(CONTRACT_77I)
    prereq_77h = read_json(PREREQ_77H)
    scoreboard_rows: list[dict[str, Any]] = []
    state_geometry_rows: list[dict[str, Any]] = []
    readout_rows: list[dict[str, Any]] = []
    kernel_rows: list[dict[str, Any]] = []
    task_descriptors: list[dict[str, Any]] = []
    invalid_tasks: list[dict[str, Any]] = []
    for length in lengths:
        for seed in seeds:
            for task_name in tasks:
                task = build_task(task_name, length, seed, args.horizon)
                finite = bool(np.all(np.isfinite(task.observed)) and np.all(np.isfinite(task.target)))
                task_descriptors.append(
                    {
                        "task": task.name,
                        "length": int(length),
                        "seed": int(seed),
                        "horizon": int(task.horizon),
                        "train_end": int(task.train_end),
                        "sample_count": int(len(task.target)),
                        "finite": finite,
                        "metadata": task.metadata,
                    }
                )
                if not finite:
                    invalid_tasks.append(task_descriptors[-1])
                    continue
                delay = run_delay_embedding(task, seed=seed, length=length, args=args)
                scoreboard_rows.append(delay.row)
                state_geometry_rows.append(
                    {
                        "task": task.name,
                        "length": int(length),
                        "seed": int(seed),
                        "capacity_units": 0,
                        "probe_family": DELAY_EMBED,
                        "probe_id": DELAY_EMBED,
                        **geometry_metrics(delay.features, delay.hidden_columns, task.train_end),
                    }
                )
                readout_rows.append(
                    {
                        "task": task.name,
                        "length": int(length),
                        "seed": int(seed),
                        "capacity_units": 0,
                        "probe_family": DELAY_EMBED,
                        "probe_id": DELAY_EMBED,
                        **readout_metrics(delay.weights, delay.hidden_columns),
                    }
                )
                for capacity in capacities:
                    results, kernels = run_task_capacity(task, seed=seed, length=length, capacity=capacity, args=args)
                    kernel_rows.extend(kernels)
                    for result in results:
                        scoreboard_rows.append(result.row)
                        state_geometry_rows.append(
                            {
                                "task": task.name,
                                "length": int(length),
                                "seed": int(seed),
                                "capacity_units": int(capacity),
                                "probe_family": result.row["probe_family"],
                                "probe_id": result.row["probe_id"],
                                **geometry_metrics(result.features, result.hidden_columns, task.train_end),
                            }
                        )
                        readout_rows.append(
                            {
                                "task": task.name,
                                "length": int(length),
                                "seed": int(seed),
                                "capacity_units": int(capacity),
                                "probe_family": result.row["probe_family"],
                                "probe_id": result.row["probe_id"],
                                **readout_metrics(result.weights, result.hidden_columns),
                            }
                        )
    score_summary = summarize_scoreboard(scoreboard_rows)
    geometry_summary = summarize_numeric(
        state_geometry_rows,
        [
            "participation_ratio",
            "participation_ratio_per_unit",
            "rank95_variance_count",
            "top_pc_fraction",
            "state_norm_mean",
            "state_norm_std",
            "step_delta_mean",
            "step_delta_std",
            "total_state_variance",
        ],
        ["task", "probe_family", "capacity_units"],
    )
    readout_summary = summarize_numeric(
        readout_rows,
        ["readout_weight_pr", "top_weight_fraction", "hidden_weight_energy_fraction", "final_weight_norm"],
        ["task", "probe_family", "capacity_units"],
    )
    kernel_summary = summarize_numeric(
        kernel_rows,
        ["linear_cka_to_candidate"],
        ["task", "probe_family", "capacity_units"],
    )
    classification = classify(score_summary, geometry_summary, readout_summary, kernel_summary)
    criteria = [
        criterion("Tier 7.7i contract exists", str(CONTRACT_77I), "exists and pass", bool(prereq_77i) and prereq_77i.get("status") == "pass"),
        criterion("Tier 7.7h prerequisite exists", str(PREREQ_77H), "exists and pass", bool(prereq_77h) and prereq_77h.get("status") == "pass"),
        criterion("locked tasks", tasks, "Mackey/Lorenz/NARMA", set(tasks) == {"mackey_glass", "lorenz", "narma10"} or bool(args.smoke)),
        criterion("locked lengths", lengths, "8000/16000/32000", lengths == [8000, 16000, 32000] or bool(args.smoke)),
        criterion("locked seeds", seeds, "42/43/44", seeds == [42, 43, 44] or bool(args.smoke)),
        criterion("locked capacities", capacities, "16/32/64/128", capacities == [16, 32, 64, 128] or bool(args.smoke)),
        criterion("finite generated streams", len(invalid_tasks), "== 0", len(invalid_tasks) == 0),
        criterion("scoreboard produced", len(scoreboard_rows), "> 0", len(scoreboard_rows) > 0),
        criterion("state geometry produced", len(state_geometry_rows), "> 0", len(state_geometry_rows) > 0),
        criterion("readout concentration produced", len(readout_rows), "> 0", len(readout_rows) > 0),
        criterion("kernel alignment produced", len(kernel_rows), "> 0", len(kernel_rows) > 0),
        criterion("classification produced", classification["outcome"], "non-empty", bool(classification["outcome"])),
        criterion("no baseline freeze", classification["claim_allowed"]["baseline_freeze"], "false", classification["claim_allowed"]["baseline_freeze"] is False),
        criterion("no mechanism promotion", classification["claim_allowed"]["mechanism_promotion"], "false", classification["claim_allowed"]["mechanism_promotion"] is False),
        criterion("hardware/native transfer blocked", classification["claim_allowed"]["hardware_or_native_transfer"], "false", classification["claim_allowed"]["hardware_or_native_transfer"] is False),
    ]
    passed = sum(1 for item in criteria if item["passed"])
    status = "pass" if passed == len(criteria) else "fail"
    claim_boundary = (
        "Tier 7.7j scores the locked 7.7i state-specificity diagnostic. It may classify the capacity signal as candidate-specific, generic-basis explained, low-rank collapsed, readout-limited, observability-limited, or inconclusive, but it does not freeze a baseline, promote a mechanism, authorize hardware/native transfer, or claim broad public usefulness."
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
        "tasks": tasks,
        "lengths": lengths,
        "seeds": seeds,
        "capacities": capacities,
        "permuted_offsets": parse_int_csv(args.permuted_offsets),
        "repaired_stream_manifest": {
            "selected_generator": REPAIRED_GENERATOR_ID,
            "input_distribution": "Uniform(0,0.2)",
            "labeling_rule": "Repaired NARMA10 U(0,0.2); do not silently mix with prior U(0,0.5) NARMA scores.",
        },
        "classification": classification,
        "scoreboard_rows": scoreboard_rows,
        "score_summary": score_summary,
        "state_geometry": state_geometry_rows,
        "state_geometry_summary": geometry_summary,
        "state_kernel_alignment": kernel_rows,
        "state_kernel_alignment_summary": kernel_summary,
        "readout_concentration": readout_rows,
        "readout_concentration_summary": readout_summary,
        "task_descriptors": task_descriptors,
        "invalid_tasks": invalid_tasks,
        "claim_boundary": claim_boundary,
        "runtime_seconds": time.perf_counter() - started,
    }
    write_json(output_dir / "tier7_7j_results.json", payload)
    write_rows(output_dir / "tier7_7j_summary.csv", criteria)
    write_rows(output_dir / "tier7_7j_scoreboard.csv", scoreboard_rows)
    write_rows(output_dir / "tier7_7j_score_summary.csv", score_summary)
    write_rows(output_dir / "tier7_7j_state_geometry.csv", state_geometry_rows)
    write_rows(output_dir / "tier7_7j_state_geometry_summary.csv", geometry_summary)
    write_rows(output_dir / "tier7_7j_state_kernel_alignment.csv", kernel_rows)
    write_rows(output_dir / "tier7_7j_state_kernel_alignment_summary.csv", kernel_summary)
    write_rows(output_dir / "tier7_7j_readout_concentration.csv", readout_rows)
    write_rows(output_dir / "tier7_7j_readout_concentration_summary.csv", readout_summary)
    write_json(output_dir / "tier7_7j_task_descriptors.json", task_descriptors)
    write_json(output_dir / "tier7_7j_probe_manifest.json", {"tasks": tasks, "lengths": lengths, "seeds": seeds, "capacities": capacities, "permuted_offsets": parse_int_csv(args.permuted_offsets)})
    (output_dir / "tier7_7j_claim_boundary.md").write_text(claim_boundary + "\n", encoding="utf-8")
    write_report(output_dir, payload)
    manifest = {
        "tier": TIER,
        "status": status,
        "generated_at_utc": payload["generated_at_utc"],
        "output_dir": str(output_dir),
        "results_json": str(output_dir / "tier7_7j_results.json"),
        "report_md": str(output_dir / "tier7_7j_report.md"),
        "summary_csv": str(output_dir / "tier7_7j_summary.csv"),
        "classification_outcome": classification["outcome"],
    }
    write_json(output_dir / "tier7_7j_latest_manifest.json", manifest)
    write_json(CONTROLLED / "tier7_7j_latest_manifest.json", manifest)
    return payload


def main() -> int:
    args = build_parser().parse_args()
    payload = run(args)
    print(json.dumps(json_safe({"status": payload["status"], "criteria": f"{payload['criteria_passed']}/{payload['criteria_total']}", "classification": payload["classification"]["outcome"], "output_dir": payload["output_dir"]}), indent=2, sort_keys=True))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
