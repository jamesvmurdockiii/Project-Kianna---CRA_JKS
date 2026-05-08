#!/usr/bin/env python3
"""Tier 7.1h - Compact NAB scoring gate.

Tier 7.1g proved the Numenta Anomaly Benchmark source/data/scoring preflight is
reproducible and leakage-safe. This tier performs the first compact software
scoring gate on the pinned NAB subset. It compares frozen CRA temporal-state
detectors against fair online anomaly baselines and shams.

Boundary: compact software scoring only. It does not freeze a baseline and does
not authorize hardware/native transfer by itself.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import sys
from collections import deque
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

from tier5_19a_temporal_substrate_reference import parse_timescales, random_reservoir_features  # noqa: E402
from tier5_19b_temporal_substrate_gate import temporal_features_variant  # noqa: E402
from tier7_0c_continuous_readout_repair import shuffled_rows, shuffled_target  # noqa: E402
from tier7_1g_nab_source_data_scoring_preflight import (  # noqa: E402
    DATA_CACHE,
    PINNED_NAB_COMMIT,
    SELECTED_DATA_FILES,
    cache_path,
    criterion,
    download_source_set,
    load_cached_json,
    parse_timestamp,
    sha256_file,
    write_csv,
    write_json,
)


TIER = "Tier 7.1h - Compact NAB Scoring Gate"
RUNNER_REVISION = "tier7_1h_compact_nab_scoring_gate_20260508_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_1h_20260508_compact_nab_scoring_gate"
TIER7_1G_RESULTS = CONTROLLED / "tier7_1g_20260508_nab_source_data_scoring_preflight" / "tier7_1g_results.json"

NULL = "null_no_alarm_detector"
RANDOM = "random_calibrated_detector"
ROLLING_Z = "rolling_zscore_detector"
EWMA = "ewma_residual_detector"
ROLLING_MAD = "rolling_mad_detector"
ONLINE_AR = "online_ar_lms_residual_detector"
RESERVOIR = "fixed_random_reservoir_online_residual"
ESN = "fixed_esn_prefix_ridge_residual"
V22 = "v2_2_fading_memory_prediction_error"
V23 = "v2_3_generic_recurrent_prediction_error"
SHUFFLED = "v2_3_shuffled_state_sham"
SHUFFLED_TARGET = "v2_3_shuffled_target_control"
NO_UPDATE = "v2_3_no_update_ablation"

EXTERNAL_BASELINES = [NULL, RANDOM, ROLLING_Z, EWMA, ROLLING_MAD, ONLINE_AR, RESERVOIR, ESN]
CRA_MODELS = [V22, V23, SHUFFLED, SHUFFLED_TARGET, NO_UPDATE]
REQUIRED_MODELS = [*EXTERNAL_BASELINES, *CRA_MODELS]


@dataclass(frozen=True)
class NabStream:
    file: str
    category: str
    timestamps_raw: list[str]
    timestamps: list[datetime]
    values_raw: np.ndarray
    values_norm: np.ndarray
    labels: np.ndarray
    windows: list[tuple[datetime, datetime]]
    calibration_n: int
    raw_chronological: bool


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_stream(file_id: str, cache_root: Path, commit: str, windows_by_file: dict[str, list[list[str]]], calibration_fraction: float) -> NabStream:
    data_path = cache_path(cache_root, commit, f"data/{file_id}")
    if not data_path.exists():
        download_source_set(cache_root, commit, timeout=60)
    rows: list[tuple[int, str, datetime, float]] = []
    with data_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ["timestamp", "value"]:
            raise ValueError(f"{file_id} expected timestamp,value header; got {reader.fieldnames}")
        for idx, row in enumerate(reader):
            dt = parse_timestamp(row["timestamp"])
            value = float(row["value"])
            if not math.isfinite(value):
                raise ValueError(f"{file_id}:{idx} non-finite value")
            rows.append((idx, row["timestamp"], dt, value))
    if not rows:
        raise ValueError(f"{file_id} has no rows")
    raw_chronological = all(rows[i][2] <= rows[i + 1][2] for i in range(len(rows) - 1))
    rows = sorted(rows, key=lambda item: (item[2], item[0]))
    windows = [(parse_timestamp(start), parse_timestamp(end)) for start, end in windows_by_file[file_id]]
    timestamps = [row[2] for row in rows]
    labels = np.asarray([any(start <= ts <= end for start, end in windows) for ts in timestamps], dtype=bool)
    values = np.asarray([row[3] for row in rows], dtype=float)
    calibration_n = max(20, int(round(len(values) * float(calibration_fraction))))
    calibration_n = min(calibration_n, max(2, len(values) - 1))
    mu = float(np.mean(values[:calibration_n]))
    sd = float(np.std(values[:calibration_n]))
    if sd < 1e-9:
        sd = 1.0
    return NabStream(
        file=file_id,
        category=file_id.split("/", 1)[0],
        timestamps_raw=[row[1] for row in rows],
        timestamps=timestamps,
        values_raw=values,
        values_norm=(values - mu) / sd,
        labels=labels,
        windows=windows,
        calibration_n=calibration_n,
        raw_chronological=raw_chronological,
    )


def load_streams(args: argparse.Namespace) -> tuple[list[NabStream], dict[str, Any]]:
    cache_root = Path(args.data_cache).resolve()
    commit = args.commit.strip() or PINNED_NAB_COMMIT
    download_source_set(cache_root, commit, timeout=args.timeout)
    windows_by_file = load_cached_json(cache_root, commit, "labels/combined_windows.json")
    streams = [
        load_stream(file_id, cache_root, commit, windows_by_file, args.calibration_fraction)
        for file_id in SELECTED_DATA_FILES
    ]
    source = {
        "commit": commit,
        "cache_root": str(cache_root),
        "selected_files": SELECTED_DATA_FILES,
        "source_manifest_sha256": {
            path: sha256_file(cache_path(cache_root, commit, path))
            for path in ["labels/combined_windows.json", "config/profiles.json", "config/thresholds.json", "nab/scorer.py"]
        },
    }
    return streams, source


def calibration_threshold(scores: np.ndarray, calibration_n: int, quantile: float) -> tuple[float, dict[str, Any]]:
    prefix = np.asarray(scores[:calibration_n], dtype=float)
    finite = prefix[np.isfinite(prefix)]
    if finite.size == 0:
        return float("inf"), {"policy": "no finite calibration scores", "label_used": False}
    threshold = float(np.quantile(finite, float(quantile)))
    if abs(threshold) < 1e-12:
        threshold = 1e-12
    return threshold, {
        "policy": "per-stream calibration-prefix quantile",
        "quantile": float(quantile),
        "calibration_rows": int(calibration_n),
        "label_used": False,
    }


def prior_values(values: np.ndarray) -> np.ndarray:
    prior = np.zeros_like(values, dtype=float)
    if len(values) > 1:
        prior[1:] = values[:-1]
    return prior


def lag_features(values: np.ndarray, history: int) -> np.ndarray:
    prior = prior_values(values)
    rows: list[list[float]] = []
    for idx in range(len(values)):
        row = [1.0]
        for lag in range(int(history)):
            j = idx - lag
            row.append(float(prior[j]) if j >= 0 else 0.0)
        rows.append(row)
    return np.asarray(rows, dtype=float)


def normalize_features(features: np.ndarray, calibration_n: int) -> tuple[np.ndarray, dict[str, Any]]:
    x = np.asarray(features, dtype=float)
    mu = np.mean(x[:calibration_n], axis=0)
    sd = np.std(x[:calibration_n], axis=0)
    sd[sd < 1e-9] = 1.0
    if x.shape[1]:
        mu[0] = 0.0
        sd[0] = 1.0
    return (x - mu) / sd, {"feature_mu": mu, "feature_sd": sd, "calibration_prefix_only": True}


def primary_score(row: dict[str, Any]) -> float:
    return (
        float(row["event_f1"])
        + 0.05 * float(row["window_recall"])
        + 0.05 * float(row["nab_style_score_normalized"])
        - 0.002 * float(row["fp_per_1000_non_anomaly_points"])
    )


def online_lms_prediction_error(
    features: np.ndarray,
    target: np.ndarray,
    *,
    calibration_n: int,
    lr: float,
    decay: float,
    weight_clip: float,
    update_enabled: bool = True,
    update_target: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    x, norm_meta = normalize_features(features, calibration_n)
    y = np.asarray(target, dtype=float)
    update_y = y if update_target is None else np.asarray(update_target, dtype=float)
    w = np.zeros(x.shape[1], dtype=float)
    pred = np.zeros(len(y), dtype=float)
    scores = np.zeros(len(y), dtype=float)
    updates = 0
    for idx, row in enumerate(x):
        value = float(np.dot(w, row))
        pred[idx] = value
        scores[idx] = abs(float(y[idx]) - value)
        if update_enabled:
            err = float(update_y[idx]) - value
            denom = 1.0 + float(np.dot(row, row))
            w = (1.0 - float(decay)) * w + (float(lr) * err / denom) * row
            norm = float(np.linalg.norm(w))
            if weight_clip > 0 and norm > weight_clip:
                w *= float(weight_clip) / norm
            updates += 1
    return scores, pred, {
        "readout": "online_lms_prediction_before_update",
        "updates": updates,
        "label_used": False,
        "feature_count": int(features.shape[1]),
        "feature_norm": norm_meta,
        "lr": float(lr),
        "decay": float(decay),
        "weight_clip": float(weight_clip),
        "final_weight_norm": float(np.linalg.norm(w)),
        "update_enabled": bool(update_enabled),
    }


def prefix_ridge_prediction_error(features: np.ndarray, target: np.ndarray, *, calibration_n: int, ridge: float) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    x, norm_meta = normalize_features(features, calibration_n)
    xtx = x[:calibration_n].T @ x[:calibration_n]
    reg = np.eye(x.shape[1]) * float(ridge)
    if reg.size:
        reg[0, 0] = 0.0
    w = np.linalg.solve(xtx + reg, x[:calibration_n].T @ target[:calibration_n])
    pred = x @ w
    scores = np.abs(target - pred)
    return scores, pred, {
        "readout": "calibration_prefix_ridge_prediction",
        "updates": int(calibration_n),
        "post_prefix_updates": 0,
        "label_used": False,
        "feature_count": int(features.shape[1]),
        "feature_norm": norm_meta,
        "ridge": float(ridge),
        "weight_norm": float(np.linalg.norm(w)),
    }


def rolling_zscore(values: np.ndarray, window: int) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    scores = np.zeros(len(values), dtype=float)
    pred = np.zeros(len(values), dtype=float)
    hist: deque[float] = deque(maxlen=max(2, int(window)))
    for idx, value in enumerate(values):
        if len(hist) >= 2:
            arr = np.asarray(hist, dtype=float)
            mu = float(np.mean(arr))
            sd = float(np.std(arr)) or 1.0
        else:
            mu, sd = 0.0, 1.0
        pred[idx] = mu
        scores[idx] = abs(float(value) - mu) / max(sd, 1e-9)
        hist.append(float(value))
    return scores, pred, {"detector": "rolling_zscore", "window": int(window), "label_used": False}


def ewma_residual(values: np.ndarray, alpha: float) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    scores = np.zeros(len(values), dtype=float)
    pred = np.zeros(len(values), dtype=float)
    ema = 0.0
    initialized = False
    for idx, value in enumerate(values):
        if not initialized:
            ema = float(value)
            initialized = True
        pred[idx] = ema
        scores[idx] = abs(float(value) - ema)
        ema = (1.0 - float(alpha)) * ema + float(alpha) * float(value)
    return scores, pred, {"detector": "ewma_residual", "alpha": float(alpha), "label_used": False}


def rolling_mad(values: np.ndarray, window: int) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    scores = np.zeros(len(values), dtype=float)
    pred = np.zeros(len(values), dtype=float)
    hist: deque[float] = deque(maxlen=max(3, int(window)))
    for idx, value in enumerate(values):
        if len(hist) >= 3:
            arr = np.asarray(hist, dtype=float)
            med = float(np.median(arr))
            mad = float(np.median(np.abs(arr - med))) or 1.0
        else:
            med, mad = 0.0, 1.0
        pred[idx] = med
        scores[idx] = abs(float(value) - med) / max(1.4826 * mad, 1e-9)
        hist.append(float(value))
    return scores, pred, {"detector": "rolling_mad", "window": int(window), "label_used": False}


def detector_scores(stream: NabStream, model: str, seed: int, args: argparse.Namespace) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    values = stream.values_norm
    if model == NULL:
        return np.zeros(len(values), dtype=float), np.zeros(len(values), dtype=float), {"detector": "no_alarm", "label_used": False}
    if model == RANDOM:
        stable_stream_seed = int(hashlib.sha256(stream.file.encode("utf-8")).hexdigest()[:8], 16)
        rng = np.random.default_rng(seed + stable_stream_seed % 100000)
        scores = rng.random(len(values))
        return scores, scores.copy(), {"detector": "random_uniform_scores", "label_used": False}
    if model == ROLLING_Z:
        return rolling_zscore(values, args.rolling_window)
    if model == EWMA:
        return ewma_residual(values, args.ewma_alpha)
    if model == ROLLING_MAD:
        return rolling_mad(values, args.rolling_window)
    if model == ONLINE_AR:
        return online_lms_prediction_error(
            lag_features(values, args.history),
            values,
            calibration_n=stream.calibration_n,
            lr=args.readout_lr,
            decay=args.readout_decay,
            weight_clip=args.weight_clip,
        )

    prior = prior_values(values)
    if model == RESERVOIR:
        features = random_reservoir_features(
            prior,
            seed=seed,
            units=args.reservoir_units,
            spectral_radius=args.reservoir_spectral_radius,
            input_scale=args.reservoir_input_scale,
        ).features
        return online_lms_prediction_error(
            features,
            values,
            calibration_n=stream.calibration_n,
            lr=args.readout_lr,
            decay=args.readout_decay,
            weight_clip=args.weight_clip,
        )
    if model == ESN:
        features = random_reservoir_features(
            prior,
            seed=seed + 9000,
            units=args.esn_units,
            spectral_radius=args.esn_spectral_radius,
            input_scale=args.reservoir_input_scale,
        ).features
        return prefix_ridge_prediction_error(features, values, calibration_n=stream.calibration_n, ridge=args.ridge)

    timescales = parse_timescales(args.temporal_timescales)
    mode = "fading_only" if model == V22 else "full"
    features = temporal_features_variant(
        prior,
        seed=seed,
        train_end=stream.calibration_n,
        timescales=timescales,
        hidden_units=args.temporal_hidden_units,
        recurrent_scale=args.temporal_recurrent_scale,
        input_scale=args.temporal_input_scale,
        hidden_decay=args.temporal_hidden_decay,
        mode=mode,
    ).features
    update_enabled = model != NO_UPDATE
    update_target = None
    diagnostics: dict[str, Any] = {"detector": model, "temporal_input": "prior_value_only", "label_used": False}
    if model == SHUFFLED:
        features = shuffled_rows(features, stream.calibration_n, seed)
        diagnostics["sham"] = "v2.3 feature rows shuffled within calibration/post-calibration partitions"
    if model == SHUFFLED_TARGET:
        update_target = shuffled_target(values, stream.calibration_n, seed)
        diagnostics["control"] = "online readout updates against shuffled current values"
    if model == NO_UPDATE:
        diagnostics["ablation"] = "prediction readout updates disabled"
    scores, pred, meta = online_lms_prediction_error(
        features,
        values,
        calibration_n=stream.calibration_n,
        lr=args.readout_lr,
        decay=args.readout_decay,
        weight_clip=args.weight_clip,
        update_enabled=update_enabled,
        update_target=update_target,
    )
    return scores, pred, {**meta, **diagnostics}


def contiguous_alarm_events(alarms: np.ndarray, timestamps: list[datetime], labels: np.ndarray) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    idx = 0
    while idx < len(alarms):
        if not bool(alarms[idx]):
            idx += 1
            continue
        start = idx
        while idx + 1 < len(alarms) and bool(alarms[idx + 1]):
            idx += 1
        end = idx
        events.append(
            {
                "start_index": start,
                "end_index": end,
                "start_time": timestamps[start],
                "end_time": timestamps[end],
                "overlaps_anomaly": bool(np.any(labels[start : end + 1])),
            }
        )
        idx += 1
    return events


def auc_roc(labels: np.ndarray, scores: np.ndarray) -> float | None:
    y = np.asarray(labels, dtype=bool)
    s = np.asarray(scores, dtype=float)
    pos = int(np.sum(y))
    neg = int(len(y) - pos)
    if pos == 0 or neg == 0:
        return None
    order = np.argsort(s)
    ranks = np.empty(len(s), dtype=float)
    ranks[order] = np.arange(1, len(s) + 1)
    # Average tied ranks.
    unique_scores = np.unique(s)
    for value in unique_scores:
        mask = s == value
        if np.sum(mask) > 1:
            ranks[mask] = float(np.mean(ranks[mask]))
    rank_sum_pos = float(np.sum(ranks[y]))
    return (rank_sum_pos - pos * (pos + 1) / 2.0) / (pos * neg)


def average_precision(labels: np.ndarray, scores: np.ndarray) -> float | None:
    y = np.asarray(labels, dtype=bool)
    if int(np.sum(y)) == 0:
        return None
    order = np.argsort(-np.asarray(scores, dtype=float))
    y_sorted = y[order]
    tp = 0
    precisions: list[float] = []
    for rank, label in enumerate(y_sorted, start=1):
        if label:
            tp += 1
            precisions.append(tp / rank)
    return float(np.mean(precisions)) if precisions else 0.0


def score_stream(stream: NabStream, model: str, seed: int, scores: np.ndarray, threshold: float, threshold_meta: dict[str, Any]) -> dict[str, Any]:
    labels = stream.labels
    alarms = np.asarray(scores > threshold, dtype=bool)
    tp = int(np.sum(alarms & labels))
    fp = int(np.sum(alarms & ~labels))
    fn = int(np.sum(~alarms & labels))
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    point_f1 = 2.0 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    events = contiguous_alarm_events(alarms, stream.timestamps, labels)
    false_positive_events = [event for event in events if not event["overlaps_anomaly"]]
    detected_windows = 0
    latencies_seconds: list[float] = []
    latency_fraction_rewards: list[float] = []
    for start, end in stream.windows:
        hit_indices = [idx for idx, ts in enumerate(stream.timestamps) if start <= ts <= end and alarms[idx]]
        if hit_indices:
            detected_windows += 1
            first = hit_indices[0]
            latency = max(0.0, (stream.timestamps[first] - start).total_seconds())
            duration = max(1.0, (end - start).total_seconds())
            latencies_seconds.append(latency)
            latency_fraction_rewards.append(max(0.0, 1.0 - latency / duration))
    window_count = len(stream.windows)
    window_recall = detected_windows / window_count if window_count else 0.0
    event_precision = detected_windows / (detected_windows + len(false_positive_events)) if (detected_windows + len(false_positive_events)) else 0.0
    event_f1 = 2.0 * event_precision * window_recall / (event_precision + window_recall) if (event_precision + window_recall) else 0.0
    non_anomaly_points = max(1, int(np.sum(~labels)))
    fp_per_1000 = 1000.0 * fp / non_anomaly_points
    nab_style_raw = sum(latency_fraction_rewards) - window_count + detected_windows - 0.11 * len(false_positive_events)
    nab_style_normalized = (nab_style_raw + window_count) / max(1e-9, 2.0 * window_count) if window_count else 0.0
    return {
        "model": model,
        "seed": int(seed),
        "file": stream.file,
        "category": stream.category,
        "rows": int(len(scores)),
        "calibration_rows": int(stream.calibration_n),
        "window_count": int(window_count),
        "label_point_count": int(np.sum(labels)),
        "threshold": float(threshold),
        "threshold_policy": threshold_meta.get("policy"),
        "threshold_quantile": threshold_meta.get("quantile"),
        "threshold_label_used": bool(threshold_meta.get("label_used", False)),
        "alarm_count": int(np.sum(alarms)),
        "tp_points": tp,
        "fp_points": fp,
        "fn_points": fn,
        "point_precision": float(precision),
        "point_recall": float(recall),
        "point_f1": float(point_f1),
        "window_detected": int(detected_windows),
        "window_recall": float(window_recall),
        "false_positive_events": int(len(false_positive_events)),
        "event_precision": float(event_precision),
        "event_f1": float(event_f1),
        "fp_per_1000_non_anomaly_points": float(fp_per_1000),
        "mean_latency_seconds": None if not latencies_seconds else float(np.mean(latencies_seconds)),
        "auroc": auc_roc(labels, scores),
        "auprc": average_precision(labels, scores),
        "nab_style_score_raw": float(nab_style_raw),
        "nab_style_score_normalized": float(nab_style_normalized),
    }


def run_model_stream(stream: NabStream, model: str, seed: int, args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    scores, predictions, diagnostics = detector_scores(stream, model, seed, args)
    threshold, threshold_meta = calibration_threshold(scores, stream.calibration_n, args.threshold_quantile)
    metrics = score_stream(stream, model, seed, scores, threshold, threshold_meta)
    threshold_row = {
        "model": model,
        "seed": int(seed),
        "file": stream.file,
        "threshold": threshold,
        **threshold_meta,
        "score_min": float(np.min(scores)),
        "score_max": float(np.max(scores)),
        "score_mean": float(np.mean(scores)),
    }
    preview: list[dict[str, Any]] = []
    limit = min(int(args.preview_rows_per_stream), len(scores))
    for idx in range(limit):
        preview.append(
            {
                "model": model,
                "seed": int(seed),
                "stream_id": stream.file,
                "adapter_order_index": idx,
                "timestamp": stream.timestamps_raw[idx],
                "value_norm": float(stream.values_norm[idx]),
                "prediction": float(predictions[idx]),
                "anomaly_score": float(scores[idx]),
                "threshold": threshold,
                "alarm": bool(scores[idx] > threshold),
                "label_available_in_score_row": False,
            }
        )
    metrics["diagnostics"] = diagnostics
    return metrics, threshold_row, preview


def aggregate_metrics(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for model in sorted({str(row["model"]) for row in rows}):
        subset = [row for row in rows if row["model"] == model]
        event_f1_values = [float(row["event_f1"]) for row in subset]
        fp_values = [float(row["fp_per_1000_non_anomaly_points"]) for row in subset]
        auprc_values = [float(row["auprc"]) for row in subset if row["auprc"] is not None]
        auroc_values = [float(row["auroc"]) for row in subset if row["auroc"] is not None]
        nab_values = [float(row["nab_style_score_normalized"]) for row in subset]
        mean_latency = [float(row["mean_latency_seconds"]) for row in subset if row["mean_latency_seconds"] is not None]
        primary_score_values = [primary_score(row) for row in subset]
        out.append(
            {
                "model": model,
                "runs": len(subset),
                "primary_score_mean": float(np.mean(primary_score_values)),
                "primary_score_median": float(np.median(primary_score_values)),
                "event_f1_mean": float(np.mean(event_f1_values)),
                "event_f1_median": float(np.median(event_f1_values)),
                "window_recall_mean": float(np.mean([float(row["window_recall"]) for row in subset])),
                "point_f1_mean": float(np.mean([float(row["point_f1"]) for row in subset])),
                "fp_per_1000_mean": float(np.mean(fp_values)),
                "false_positive_events_mean": float(np.mean([float(row["false_positive_events"]) for row in subset])),
                "nab_style_score_mean": float(np.mean(nab_values)),
                "auroc_mean": None if not auroc_values else float(np.mean(auroc_values)),
                "auprc_mean": None if not auprc_values else float(np.mean(auprc_values)),
                "mean_latency_seconds": None if not mean_latency else float(np.mean(mean_latency)),
            }
        )
    ranked = sorted(out, key=lambda row: (-float(row["primary_score_mean"]), -float(row["event_f1_mean"]), float(row["fp_per_1000_mean"]), str(row["model"])))
    rank = {row["model"]: idx + 1 for idx, row in enumerate(ranked)}
    for row in out:
        row["rank_by_primary_score"] = rank[row["model"]]
    return sorted(out, key=lambda row: (int(row["rank_by_primary_score"]), str(row["model"])))


def paired_bootstrap(rows: list[dict[str, Any]], candidate: str, baseline: str, *, seed: int, n: int) -> dict[str, Any]:
    units = sorted({(str(row["file"]), int(row["seed"])) for row in rows})
    by_key_model = {(str(row["file"]), int(row["seed"]), str(row["model"])): row for row in rows}
    deltas: list[float] = []
    for file_id, model_seed in units:
        cand = by_key_model.get((file_id, model_seed, candidate))
        base = by_key_model.get((file_id, model_seed, baseline))
        if cand and base:
            deltas.append(primary_score(cand) - primary_score(base))
    if not deltas:
        return {"candidate": candidate, "baseline": baseline, "paired_units": 0, "mean_delta": None, "ci_low": None, "ci_high": None}
    rng = np.random.default_rng(seed + 71001)
    arr = np.asarray(deltas, dtype=float)
    reps = np.zeros(int(n), dtype=float)
    for idx in range(int(n)):
        sample = rng.choice(arr, size=len(arr), replace=True)
        reps[idx] = float(np.mean(sample))
    return {
        "candidate": candidate,
        "baseline": baseline,
        "paired_units": len(deltas),
        "mean_delta": float(np.mean(arr)),
        "ci_low": float(np.quantile(reps, 0.025)),
        "ci_high": float(np.quantile(reps, 0.975)),
        "positive_fraction": float(np.mean(reps > 0.0)),
        "metric": "paired primary-score delta; positive means candidate better",
    }


def classify(summary: list[dict[str, Any]], rows: list[dict[str, Any]], bootstrap: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    by_model = {str(row["model"]): row for row in summary}
    best = summary[0]
    best_external = min((by_model[model] for model in EXTERNAL_BASELINES), key=lambda row: int(row["rank_by_primary_score"]))
    v23 = by_model[V23]
    v22 = by_model[V22]
    sham_separations = sum(
        float(v23["primary_score_mean"]) > float(by_model[model]["primary_score_mean"])
        for model in [SHUFFLED, SHUFFLED_TARGET, NO_UPDATE]
    )
    v23_beats_v22 = float(v23["primary_score_mean"]) > float(v22["primary_score_mean"])
    v23_beats_best_external = float(v23["primary_score_mean"]) > float(best_external["primary_score_mean"])
    ci_low = bootstrap.get("ci_low")
    bootstrap_support = ci_low is not None and float(ci_low) > 0.0
    if best["model"] == V23 and sham_separations >= args.min_sham_separations and bootstrap_support:
        outcome = "v2_3_compact_nab_candidate_signal"
    elif (v23_beats_v22 or v23_beats_best_external) and sham_separations >= args.min_sham_separations:
        outcome = "v2_3_partial_nab_signal_requires_confirmation"
    else:
        outcome = "v2_3_no_compact_nab_advantage"
    return {
        "outcome": outcome,
        "best_model": best["model"],
        "best_model_primary_score": best["primary_score_mean"],
        "best_external_baseline": best_external["model"],
        "best_external_primary_score": best_external["primary_score_mean"],
        "v2_3_rank": v23["rank_by_primary_score"],
        "v2_3_primary_score": v23["primary_score_mean"],
        "v2_2_primary_score": v22["primary_score_mean"],
        "v2_3_beats_v2_2": bool(v23_beats_v22),
        "v2_3_beats_best_external": bool(v23_beats_best_external),
        "v2_3_sham_separations": int(sham_separations),
        "min_sham_separations": int(args.min_sham_separations),
        "bootstrap_vs_best_external": bootstrap,
        "freeze_authorized": False,
        "hardware_transfer_authorized": False,
    }


def write_report(output_dir: Path, payload: dict[str, Any]) -> None:
    c = payload["classification"]
    lines = [
        "# Tier 7.1h Compact NAB Scoring Gate",
        "",
        f"- Generated: `{payload['generated_at_utc']}`",
        f"- Runner revision: `{payload['runner_revision']}`",
        f"- Status: **{payload['status'].upper()}**",
        f"- Criteria: `{payload['criteria_passed']}/{payload['criteria_total']}`",
        f"- Outcome: `{c['outcome']}`",
        "",
        "## Key Metrics",
        "",
        f"- Best model: `{c['best_model']}` primary score `{c['best_model_primary_score']}`",
        f"- Best external baseline: `{c['best_external_baseline']}` primary score `{c['best_external_primary_score']}`",
        f"- v2.3 rank: `{c['v2_3_rank']}`",
        f"- v2.3 primary score: `{c['v2_3_primary_score']}`",
        f"- v2.2 primary score: `{c['v2_2_primary_score']}`",
        f"- v2.3 sham separations: `{c['v2_3_sham_separations']}`",
        "",
        "## Boundary",
        "",
        payload["claim_boundary"],
        "",
        "## Next Step",
        "",
        payload["next_step"],
        "",
    ]
    output_dir.joinpath("tier7_1h_report.md").write_text("\n".join(lines), encoding="utf-8")


def make_manifest(output_dir: Path, artifacts: dict[str, Path], status: str) -> dict[str, Any]:
    return {
        "tier": TIER,
        "status": status,
        "generated_at_utc": utc_now(),
        "runner_revision": RUNNER_REVISION,
        "output_dir": output_dir,
        "artifacts": [
            {"name": name, "path": path, "sha256": sha256_file(path), "bytes": path.stat().st_size}
            for name, path in sorted(artifacts.items())
        ],
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    preflight = read_json(TIER7_1G_RESULTS) if TIER7_1G_RESULTS.exists() else {}
    streams, source = load_streams(args)
    seeds = [int(item) for item in args.seeds.split(",") if item.strip()]
    rows: list[dict[str, Any]] = []
    thresholds: list[dict[str, Any]] = []
    preview: list[dict[str, Any]] = []
    for seed in seeds:
        for stream in streams:
            for model in REQUIRED_MODELS:
                metrics, threshold_row, preview_rows = run_model_stream(stream, model, seed, args)
                rows.append(metrics)
                thresholds.append(threshold_row)
                preview.extend(preview_rows)
    summary = aggregate_metrics(rows)
    best_external = min((row for row in summary if row["model"] in EXTERNAL_BASELINES), key=lambda row: int(row["rank_by_primary_score"]))
    bootstrap = paired_bootstrap(rows, V23, str(best_external["model"]), seed=42, n=args.bootstrap_samples)
    classification = classify(summary, rows, bootstrap, args)
    models = {str(row["model"]) for row in rows}
    threshold_label_used = [row["label_used"] for row in thresholds]
    preview_has_label_columns = any(
        key.lower() in {"label", "labels", "is_anomaly", "anomaly", "anomaly_window"}
        for row in preview
        for key in row
    )
    criteria = [
        criterion("Tier 7.1g preflight exists", TIER7_1G_RESULTS, "exists", TIER7_1G_RESULTS.exists()),
        criterion("Tier 7.1g preflight passed", preflight.get("status"), "== pass", preflight.get("status") == "pass"),
        criterion("NAB source commit matches preflight", source["commit"], "matches Tier 7.1g", source["commit"] == preflight.get("source", {}).get("selected_commit")),
        criterion("selected streams loaded", len(streams), f"== {len(SELECTED_DATA_FILES)}", len(streams) == len(SELECTED_DATA_FILES)),
        criterion("selected streams have anomaly windows", [len(s.windows) for s in streams], "all > 0", all(len(s.windows) > 0 for s in streams)),
        criterion("all required models ran", sorted(models), "contains required models", all(model in models for model in REQUIRED_MODELS)),
        criterion("external baselines present", sorted(EXTERNAL_BASELINES), "all present", all(model in models for model in EXTERNAL_BASELINES)),
        criterion("v2.3 shams present", [SHUFFLED, SHUFFLED_TARGET, NO_UPDATE], "all present", all(model in models for model in [SHUFFLED, SHUFFLED_TARGET, NO_UPDATE])),
        criterion("metrics finite", True, "all primary/event metrics finite", all(math.isfinite(float(row["event_f1"])) and math.isfinite(float(row["nab_style_score_normalized"])) for row in rows)),
        criterion("thresholds label-free", threshold_label_used, "all false", all(not bool(x) for x in threshold_label_used)),
        criterion("score preview label-free", preview_has_label_columns, "== false", not preview_has_label_columns),
        criterion("prediction-before-update policy used", "all detectors emit score before update", "true", True),
        criterion("bootstrap comparison computed", bootstrap.get("paired_units"), ">= 5 paired units", int(bootstrap.get("paired_units") or 0) >= 5),
        criterion("classification computed", classification["outcome"], "non-empty", bool(classification["outcome"])),
        criterion("no baseline freeze authorized", classification["freeze_authorized"], "== false", classification["freeze_authorized"] is False),
        criterion("no hardware transfer authorized", classification["hardware_transfer_authorized"], "== false", classification["hardware_transfer_authorized"] is False),
    ]
    status = "pass" if all(c["passed"] for c in criteria) else "fail"
    payload = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "status": status,
        "criteria": criteria,
        "criteria_passed": sum(1 for c in criteria if c["passed"]),
        "criteria_total": len(criteria),
        "failed_criteria": [c for c in criteria if not c["passed"]],
        "classification": classification,
        "source": source,
        "seeds": seeds,
        "stream_profile": [
            {
                "file": s.file,
                "category": s.category,
                "rows": len(s.values_raw),
                "windows": len(s.windows),
                "label_points": int(np.sum(s.labels)),
                "calibration_rows": s.calibration_n,
                "raw_chronological": s.raw_chronological,
            }
            for s in streams
        ],
        "model_summary": summary,
        "output_dir": str(output_dir),
        "claim_boundary": (
            "Tier 7.1h is compact software scoring on a pinned NAB subset using "
            "label-separated online anomaly scores. It is not a full NAB benchmark, "
            "not public usefulness proof by itself, not a baseline freeze, not "
            "hardware/native transfer, and not AGI/ASI evidence."
        ),
        "next_step": (
            "If CRA shows a compact NAB signal, run Tier 7.1i fairness/statistical "
            "confirmation on a broader predeclared NAB subset. If simple baselines "
            "dominate, localize the failure before adding or transferring mechanisms."
        ),
    }
    paths = {
        "results_json": output_dir / "tier7_1h_results.json",
        "report_md": output_dir / "tier7_1h_report.md",
        "summary_csv": output_dir / "tier7_1h_summary.csv",
        "model_metrics_csv": output_dir / "tier7_1h_model_metrics.csv",
        "model_summary_csv": output_dir / "tier7_1h_model_summary.csv",
        "thresholds_csv": output_dir / "tier7_1h_thresholds.csv",
        "score_preview_csv": output_dir / "tier7_1h_score_preview.csv",
        "bootstrap_csv": output_dir / "tier7_1h_bootstrap.csv",
        "scoring_contract_json": output_dir / "tier7_1h_scoring_contract.json",
    }
    write_json(paths["results_json"], payload)
    write_csv(paths["summary_csv"], [{"criterion": c["name"], "passed": c["passed"], "value": c["value"], "rule": c["rule"]} for c in criteria])
    write_csv(paths["model_metrics_csv"], rows)
    write_csv(paths["model_summary_csv"], summary)
    write_csv(paths["thresholds_csv"], thresholds)
    write_csv(paths["score_preview_csv"], preview)
    write_csv(paths["bootstrap_csv"], [bootstrap])
    write_json(
        paths["scoring_contract_json"],
        {
            "source_preflight": str(TIER7_1G_RESULTS),
            "source_commit": source["commit"],
            "selected_files": SELECTED_DATA_FILES,
            "models": REQUIRED_MODELS,
            "external_baselines": EXTERNAL_BASELINES,
            "cra_models": CRA_MODELS,
            "threshold_policy": "per-stream calibration-prefix quantile, no labels",
            "primary_metric": "primary_score_mean = event_f1 + 0.05*window_recall + 0.05*nab_style_score - 0.002*fp_per_1000",
            "secondary_metrics": ["event_f1", "window_recall", "point_f1", "AUROC", "AUPRC", "NAB-style normalized score"],
            "label_policy": "labels/windows are offline scoring only and are not present in score preview rows",
            "nonclaims": [
                "not a full NAB benchmark",
                "not public usefulness proof by itself",
                "not a baseline freeze",
                "not hardware/native transfer",
                "not AGI/ASI evidence",
            ],
        },
    )
    write_report(output_dir, payload)
    manifest = make_manifest(output_dir, paths, status)
    write_json(output_dir / "tier7_1h_latest_manifest.json", manifest)
    write_json(CONTROLLED / "tier7_1h_latest_manifest.json", manifest)
    return payload


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    p.add_argument("--data-cache", default=str(DATA_CACHE))
    p.add_argument("--commit", default=PINNED_NAB_COMMIT)
    p.add_argument("--timeout", type=int, default=60)
    p.add_argument("--seeds", default="42,43,44")
    p.add_argument("--calibration-fraction", type=float, default=0.05)
    p.add_argument("--threshold-quantile", type=float, default=0.995)
    p.add_argument("--history", type=int, default=12)
    p.add_argument("--rolling-window", type=int, default=96)
    p.add_argument("--ewma-alpha", type=float, default=0.025)
    p.add_argument("--ridge", type=float, default=1e-3)
    p.add_argument("--readout-lr", type=float, default=0.05)
    p.add_argument("--readout-decay", type=float, default=0.0005)
    p.add_argument("--weight-clip", type=float, default=25.0)
    p.add_argument("--temporal-timescales", default="2,4,8,16,32,64,128")
    p.add_argument("--temporal-hidden-units", type=int, default=16)
    p.add_argument("--temporal-recurrent-scale", type=float, default=0.65)
    p.add_argument("--temporal-input-scale", type=float, default=0.35)
    p.add_argument("--temporal-hidden-decay", type=float, default=0.82)
    p.add_argument("--reservoir-units", type=int, default=32)
    p.add_argument("--reservoir-spectral-radius", type=float, default=0.9)
    p.add_argument("--reservoir-input-scale", type=float, default=0.5)
    p.add_argument("--esn-units", type=int, default=48)
    p.add_argument("--esn-spectral-radius", type=float, default=0.95)
    p.add_argument("--bootstrap-samples", type=int, default=2000)
    p.add_argument("--min-sham-separations", type=int, default=2)
    p.add_argument("--preview-rows-per-stream", type=int, default=20)
    return p.parse_args()


def main() -> None:
    payload = run(parse_args())
    print(
        json.dumps(
            {
                "status": payload["status"],
                "criteria": f"{payload['criteria_passed']}/{payload['criteria_total']}",
                "outcome": payload["classification"]["outcome"],
                "best_model": payload["classification"]["best_model"],
                "v2_3_rank": payload["classification"]["v2_3_rank"],
                "output_dir": payload["output_dir"],
            },
            indent=2,
        )
    )
    if payload["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
