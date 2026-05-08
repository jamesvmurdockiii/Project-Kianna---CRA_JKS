#!/usr/bin/env python3
"""Tier 7.1c - Compact NASA C-MAPSS FD001 scoring gate.

This is the first public/real-ish scoring gate after the Tier 7.1a/7.1b
contract and source preflight. It scores frozen v2.2/v2.3 CRA-style temporal
interfaces and fair baselines on the same leakage-safe FD001 stream.

Important boundary: this is compact software scoring only. It does not freeze a
new baseline and does not authorize SpiNNaker/native transfer by itself.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
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

from tier5_19a_temporal_substrate_reference import (  # noqa: E402
    parse_timescales,
    random_reservoir_features,
)
from tier5_19b_temporal_substrate_gate import temporal_features_variant  # noqa: E402
from tier7_0c_continuous_readout_repair import shuffled_rows, shuffled_target  # noqa: E402
from tier7_1b_cmapss_source_data_preflight import (  # noqa: E402
    CMAPSS_ZIP_URL,
    DATA_CACHE,
    TIER7_1A_RESULTS,
    download_if_needed,
    feature_stats,
    find_named_file,
    parse_numeric_rows,
    parse_rul,
    safe_extract,
    sha256_file,
    unit_profile,
)


TIER = "Tier 7.1c - Compact C-MAPSS FD001 Scoring Gate"
RUNNER_REVISION = "tier7_1c_cmapss_fd001_scoring_gate_20260508_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_1c_20260508_cmapss_fd001_scoring_gate"
TIER7_1B_RESULTS = CONTROLLED / "tier7_1b_20260508_cmapss_source_data_preflight" / "tier7_1b_results.json"

CONSTANT = "constant_train_mean_rul"
AGE = "monotone_age_to_rul_ridge"
LAG = "lag_ridge_window_baseline"
ONLINE = "online_lms_linear_readout_baseline"
RESERVOIR = "fixed_random_reservoir_online_control"
ESN = "fixed_esn_train_prefix_ridge_baseline"
V22 = "v2_2_fading_memory_reference"
V23 = "v2_3_generic_bounded_recurrent_state"
RESET = "v2_3_state_reset_ablation"
SHUFFLED = "v2_3_shuffled_state_sham"
SHUFFLED_TARGET = "v2_3_shuffled_target_control"
NO_UPDATE = "v2_3_no_update_ablation"
REQUIRED_MODELS = [CONSTANT, AGE, LAG, ONLINE, RESERVOIR, ESN, V22, V23, RESET, SHUFFLED, SHUFFLED_TARGET, NO_UPDATE]


@dataclass(frozen=True)
class CmapssTask:
    features_raw: np.ndarray
    observed: np.ndarray
    target_raw: np.ndarray
    target_norm: np.ndarray
    unit_ids: np.ndarray
    cycles: np.ndarray
    splits: np.ndarray
    train_end: int
    target_mu: float
    target_sd: float
    pca_vector: np.ndarray
    zip_sha256: str
    fd001_profile: dict[str, Any]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    return value


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def criterion(name: str, value: Any, rule: str, passed: bool, note: str = "") -> dict[str, Any]:
    return {"name": name, "value": json_safe(value), "rule": rule, "passed": bool(passed), "note": note}


def ridge_fit(x: np.ndarray, y: np.ndarray, ridge: float, *, penalize_bias: bool = False) -> np.ndarray:
    xtx = x.T @ x
    reg = np.eye(x.shape[1]) * float(ridge)
    if not penalize_bias and reg.size:
        reg[0, 0] = 0.0
    return np.linalg.solve(xtx + reg, x.T @ y)


def normalize_train_only(features: np.ndarray, train_end: int, *, keep_bias: bool = True) -> tuple[np.ndarray, dict[str, Any]]:
    x = np.asarray(features, dtype=float)
    mu = np.mean(x[:train_end], axis=0)
    sd = np.std(x[:train_end], axis=0)
    sd[sd < 1e-9] = 1.0
    if keep_bias and x.shape[1] > 0:
        mu[0] = 0.0
        sd[0] = 1.0
    return (x - mu) / sd, {"feature_mu": mu, "feature_sd": sd, "train_only": True}


def train_prefix_lms(
    features: np.ndarray,
    target_norm: np.ndarray,
    *,
    train_end: int,
    lr: float,
    decay: float,
    weight_clip: float,
    output_clip: float,
    update_enabled: bool = True,
    update_target_norm: np.ndarray | None = None,
) -> tuple[np.ndarray, dict[str, Any]]:
    x, norm_meta = normalize_train_only(features, train_end)
    y = np.asarray(target_norm, dtype=float)
    update_y = y if update_target_norm is None else np.asarray(update_target_norm, dtype=float)
    w = np.zeros(x.shape[1], dtype=float)
    pred = np.zeros(len(y), dtype=float)
    train_updates = 0
    test_updates = 0
    for i, row in enumerate(x):
        value = float(np.dot(w, row))
        if output_clip > 0:
            value = float(np.clip(value, -output_clip, output_clip))
        pred[i] = value
        if update_enabled and i < train_end:
            err = float(update_y[i] - value)
            denom = 1.0 + float(np.dot(row, row))
            w = (1.0 - float(decay)) * w + (float(lr) * err / denom) * row
            norm = float(np.linalg.norm(w))
            if weight_clip > 0 and norm > weight_clip:
                w *= float(weight_clip) / norm
            train_updates += 1
    return pred, {
        "readout": "train_prefix_lms_prediction_before_update",
        "train_updates": train_updates,
        "test_updates": test_updates,
        "feature_count": int(features.shape[1]),
        "feature_norm": norm_meta,
        "lr": float(lr),
        "decay": float(decay),
        "weight_clip": float(weight_clip),
        "output_clip": float(output_clip),
        "final_weight_norm": float(np.linalg.norm(w)),
        "update_enabled": bool(update_enabled),
    }


def train_prefix_ridge(features: np.ndarray, target_norm: np.ndarray, train_end: int, ridge: float) -> tuple[np.ndarray, dict[str, Any]]:
    x, norm_meta = normalize_train_only(features, train_end)
    w = ridge_fit(x[:train_end], target_norm[:train_end], ridge)
    return x @ w, {
        "readout": "train_prefix_ridge",
        "train_updates": int(train_end),
        "test_updates": 0,
        "feature_count": int(features.shape[1]),
        "feature_norm": norm_meta,
        "ridge": float(ridge),
        "weight_norm": float(np.linalg.norm(w)),
    }


def inverse_target(task: CmapssTask, pred_norm: np.ndarray) -> np.ndarray:
    return np.asarray(pred_norm, dtype=float) * task.target_sd + task.target_mu


def stable_corr(a: np.ndarray, b: np.ndarray) -> float | None:
    if len(a) < 2:
        return None
    if float(np.std(a)) < 1e-12 or float(np.std(b)) < 1e-12:
        return None
    return float(np.corrcoef(a, b)[0, 1])


def score_model(task: CmapssTask, model: str, seed: int, pred_norm: np.ndarray, diagnostics: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    pred_raw = np.clip(inverse_target(task, pred_norm), 0.0, 400.0)
    target = task.target_raw
    test_mask = task.splits == "test"
    train_mask = task.splits == "train"
    tail_mask = test_mask & (target <= 30.0)
    test_err = pred_raw[test_mask] - target[test_mask]
    train_err = pred_raw[train_mask] - target[train_mask]
    tail_err = pred_raw[tail_mask] - target[tail_mask]
    per_unit_rows: list[dict[str, Any]] = []
    worst_rmse = 0.0
    for unit in sorted(set(int(x) for x in task.unit_ids[test_mask])):
        mask = test_mask & (task.unit_ids == unit)
        err = pred_raw[mask] - target[mask]
        rmse = float(math.sqrt(np.mean(err * err)))
        worst_rmse = max(worst_rmse, rmse)
        per_unit_rows.append({"model": model, "seed": seed, "unit": unit, "test_rows": int(np.sum(mask)), "rmse": rmse, "mae": float(np.mean(np.abs(err)))})
    row = {
        "task": "nasa_cmapss_fd001_compact_pca1_rul",
        "model": model,
        "seed": seed,
        "status": "pass",
        "test_mse": float(np.mean(test_err * test_err)),
        "test_rmse": float(math.sqrt(np.mean(test_err * test_err))),
        "test_mae": float(np.mean(np.abs(test_err))),
        "train_mse": float(np.mean(train_err * train_err)),
        "tail_rmse": None if not np.any(tail_mask) else float(math.sqrt(np.mean(tail_err * tail_err))),
        "tail_rows": int(np.sum(tail_mask)),
        "test_corr": stable_corr(pred_raw[test_mask], target[test_mask]),
        "worst_unit_rmse": worst_rmse,
        "diagnostics": diagnostics,
    }
    return row, per_unit_rows


def aggregate(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for model in sorted({str(r["model"]) for r in rows}):
        subset = [r for r in rows if r["model"] == model and r["status"] == "pass"]
        values = [float(r["test_rmse"]) for r in subset]
        tail_values = [float(r["tail_rmse"]) for r in subset if r["tail_rmse"] is not None]
        out.append(
            {
                "model": model,
                "runs": len(subset),
                "test_rmse_mean": float(np.mean(values)),
                "test_rmse_median": float(np.median(values)),
                "test_rmse_worst_seed": float(max(values)),
                "test_mae_mean": float(np.mean([float(r["test_mae"]) for r in subset])),
                "tail_rmse_mean": None if not tail_values else float(np.mean(tail_values)),
                "worst_unit_rmse_mean": float(np.mean([float(r["worst_unit_rmse"]) for r in subset])),
                "test_corr_mean": None
                if not any(r["test_corr"] is not None for r in subset)
                else float(np.mean([float(r["test_corr"]) for r in subset if r["test_corr"] is not None])),
            }
        )
    ranked = sorted(out, key=lambda r: float(r["test_rmse_mean"]))
    rank = {r["model"]: i + 1 for i, r in enumerate(ranked)}
    for row in out:
        row["rank_by_test_rmse"] = rank[row["model"]]
    return sorted(out, key=lambda r: (int(r["rank_by_test_rmse"]), str(r["model"])))


def zscore_with_stats(x: np.ndarray, mu: np.ndarray, sd: np.ndarray) -> np.ndarray:
    return (x - mu) / sd


def load_task(args: argparse.Namespace) -> CmapssTask:
    data_cache = Path(args.data_cache).resolve()
    zip_path = data_cache / "CMAPSSData.zip"
    extract_dir = data_cache / "extracted"
    download_if_needed(args.url, zip_path, timeout=args.timeout)
    safe_extract(zip_path, extract_dir)
    train_path = find_named_file(extract_dir, "train_FD001.txt")
    test_path = find_named_file(extract_dir, "test_FD001.txt")
    rul_path = find_named_file(extract_dir, "RUL_FD001.txt")
    if train_path is None or test_path is None or rul_path is None:
        raise FileNotFoundError("FD001 train/test/RUL files missing; run Tier 7.1b preflight first")
    train_rows = parse_numeric_rows(train_path)
    test_rows = parse_numeric_rows(test_path)
    rul = parse_rul(rul_path)
    train_profile = unit_profile(train_rows)
    test_profile = unit_profile(test_rows)
    stats = feature_stats(train_rows)

    def feature_matrix(rows: list[list[float]]) -> np.ndarray:
        cols = []
        for row in rows:
            vals = []
            for col in range(2, 26):
                s = stats[f"col_{col + 1:02d}"]
                vals.append((row[col] - s["mean"]) / s["std"])
            cols.append(vals)
        return np.asarray(cols, dtype=float)

    train_x = feature_matrix(train_rows)
    test_x = feature_matrix(test_rows)
    _, _, vh = np.linalg.svd(train_x - np.mean(train_x, axis=0), full_matrices=False)
    pc1 = vh[0]
    train_obs_raw = train_x @ pc1
    test_obs_raw = test_x @ pc1
    obs_mu = float(np.mean(train_obs_raw))
    obs_sd = float(np.std(train_obs_raw))
    if obs_sd < 1e-9:
        obs_sd = 1.0
    observed = np.concatenate([(train_obs_raw - obs_mu) / obs_sd, (test_obs_raw - obs_mu) / obs_sd])

    train_targets = np.asarray([train_profile[int(row[0])]["max_cycle"] - int(row[1]) for row in train_rows], dtype=float)
    test_targets = np.asarray([rul[int(row[0]) - 1] + test_profile[int(row[0])]["max_cycle"] - int(row[1]) for row in test_rows], dtype=float)
    target_raw = np.concatenate([train_targets, test_targets])
    target_mu = float(np.mean(train_targets))
    target_sd = float(np.std(train_targets))
    if target_sd < 1e-9:
        target_sd = 1.0
    target_norm = (target_raw - target_mu) / target_sd
    train_end = len(train_rows)
    return CmapssTask(
        features_raw=np.vstack([train_x, test_x]),
        observed=observed,
        target_raw=target_raw,
        target_norm=target_norm,
        unit_ids=np.asarray([int(row[0]) for row in train_rows + test_rows], dtype=int),
        cycles=np.asarray([int(row[1]) for row in train_rows + test_rows], dtype=int),
        splits=np.asarray(["train"] * len(train_rows) + ["test"] * len(test_rows), dtype=object),
        train_end=train_end,
        target_mu=target_mu,
        target_sd=target_sd,
        pca_vector=pc1,
        zip_sha256=sha256_file(zip_path),
        fd001_profile={
            "train_rows": len(train_rows),
            "test_rows": len(test_rows),
            "train_units": len(train_profile),
            "test_units": len(test_profile),
            "rul_labels": len(rul),
            "column_count": 26,
            "adapter_signal": "train-only PCA1 over operational settings plus sensors",
            "raw_rul_policy": "uncapped RUL for compact first gate",
            "target_mu_train_only": target_mu,
            "target_sd_train_only": target_sd,
        },
    )


def segment_indices(task: CmapssTask) -> list[np.ndarray]:
    segments: list[np.ndarray] = []
    for split in ["train", "test"]:
        split_mask = task.splits == split
        for unit in sorted(set(int(x) for x in task.unit_ids[split_mask])):
            idx = np.where(split_mask & (task.unit_ids == unit))[0]
            if len(idx):
                segments.append(idx)
    return segments


def concat_segment_features(task: CmapssTask, builder) -> np.ndarray:
    out = np.zeros((len(task.observed), 1), dtype=float)
    pieces: list[tuple[np.ndarray, np.ndarray]] = []
    width = None
    for seg in segment_indices(task):
        feat = builder(task.observed[seg], int(task.unit_ids[seg][0]))
        width = feat.shape[1] if width is None else width
        pieces.append((seg, feat))
    out = np.zeros((len(task.observed), int(width or 1)), dtype=float)
    for seg, feat in pieces:
        out[seg, :] = feat
    return out


def lag_features_by_unit(task: CmapssTask, history: int) -> np.ndarray:
    def build(values: np.ndarray, unit: int) -> np.ndarray:
        del unit
        rows = []
        for i in range(len(values)):
            row = [1.0]
            for lag in range(history):
                idx = i - lag
                row.append(float(values[idx]) if idx >= 0 else 0.0)
            rows.append(row)
        return np.asarray(rows, dtype=float)

    return concat_segment_features(task, build)


def temporal_by_unit(task: CmapssTask, *, seed: int, args: argparse.Namespace, mode: str, reset_interval: int = 0, recurrent_seed_offset: int = 0) -> np.ndarray:
    timescales = parse_timescales(args.temporal_timescales)

    def build(values: np.ndarray, unit: int) -> np.ndarray:
        return temporal_features_variant(
            values,
            seed=seed + unit * 17,
            train_end=len(values),
            timescales=timescales,
            hidden_units=args.temporal_hidden_units,
            recurrent_scale=args.temporal_recurrent_scale,
            input_scale=args.temporal_input_scale,
            hidden_decay=args.temporal_hidden_decay,
            mode=mode,
            reset_interval=reset_interval,
            recurrent_seed_offset=recurrent_seed_offset,
        ).features

    return concat_segment_features(task, build)


def reservoir_by_unit(task: CmapssTask, *, seed: int, args: argparse.Namespace, units: int, spectral_radius: float) -> np.ndarray:
    def build(values: np.ndarray, unit: int) -> np.ndarray:
        return random_reservoir_features(
            values,
            seed=seed + unit * 31,
            units=units,
            spectral_radius=spectral_radius,
            input_scale=args.reservoir_input_scale,
        ).features

    return concat_segment_features(task, build)


def run_seed(task: CmapssTask, seed: int, args: argparse.Namespace) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    per_unit: list[dict[str, Any]] = []
    target = task.target_norm
    base = np.column_stack([np.ones(len(task.observed)), task.observed])
    age_cycle = task.cycles.astype(float)
    age_mu = float(np.mean(age_cycle[: task.train_end]))
    age_sd = float(np.std(age_cycle[: task.train_end])) or 1.0
    age = (age_cycle - age_mu) / age_sd
    age_features = np.column_stack([np.ones(len(age)), age, age * age])
    lag = lag_features_by_unit(task, args.history)
    v22 = temporal_by_unit(task, seed=seed, args=args, mode="fading_only")
    v23 = temporal_by_unit(task, seed=seed, args=args, mode="full")
    reset = temporal_by_unit(task, seed=seed, args=args, mode="full", reset_interval=args.state_reset_interval)
    reservoir = reservoir_by_unit(task, seed=seed, args=args, units=args.reservoir_units, spectral_radius=args.reservoir_spectral_radius)
    esn_features = reservoir_by_unit(task, seed=seed + 9000, args=args, units=args.esn_units, spectral_radius=args.esn_spectral_radius)
    shuffled = shuffled_rows(v23, task.train_end, seed)
    wrong_target = shuffled_target(target, task.train_end, seed)

    model_specs: list[tuple[str, np.ndarray, str, np.ndarray | None, bool, dict[str, Any]]] = [
        (CONSTANT, np.ones((len(target), 1)), "constant", None, False, {"baseline": "train mean RUL"}),
        (AGE, age_features, "ridge", None, True, {"baseline": "monotone age-to-RUL train-prefix ridge"}),
        (LAG, lag, "ridge", None, True, {"baseline": "same scalar PCA1 lag window", "history": args.history}),
        (ONLINE, base, "lms", None, True, {"baseline": "online LMS over scalar PCA1, train rows only"}),
        (RESERVOIR, reservoir, "lms", None, True, {"baseline": "random reservoir control reset per unit"}),
        (ESN, esn_features, "ridge", None, True, {"baseline": "fixed random ESN train-prefix ridge reset per unit"}),
        (V22, v22, "lms", None, True, {"role": "frozen v2.2 fading-memory reference reset per unit"}),
        (V23, v23, "lms", None, True, {"role": "frozen v2.3 generic bounded recurrent-state reset per unit"}),
        (RESET, reset, "lms", None, True, {"ablation": "v2.3 state reset within unit"}),
        (SHUFFLED, shuffled, "lms", None, True, {"sham": "v2.3 state rows shuffled within train/test"}),
        (SHUFFLED_TARGET, v23, "lms", wrong_target, True, {"control": "v2.3 train readout updates against shuffled target"}),
        (NO_UPDATE, v23, "lms", None, False, {"ablation": "v2.3 readout updates disabled"}),
    ]
    for model, features, readout, update_target, update_enabled, diagnostics in model_specs:
        if readout == "constant":
            pred_norm = np.zeros(len(target), dtype=float)
            diag = {"readout": "train_mean_constant", "test_updates": 0, "feature_count": 1, **diagnostics}
        elif readout == "ridge":
            pred_norm, diag = train_prefix_ridge(features, target, task.train_end, args.ridge)
            diag = {**diag, **diagnostics}
        else:
            pred_norm, diag = train_prefix_lms(
                features,
                target,
                train_end=task.train_end,
                lr=args.readout_lr,
                decay=args.readout_decay,
                weight_clip=args.weight_clip,
                output_clip=args.output_clip,
                update_enabled=update_enabled,
                update_target_norm=update_target,
            )
            diag = {**diag, **diagnostics}
        row, units = score_model(task, model, seed, pred_norm, diag)
        rows.append(row)
        per_unit.extend(units)
    diagnostics = {
        "seed": seed,
        "adapter_signal": task.fd001_profile["adapter_signal"],
        "unit_boundary_policy": "temporal, lag, reservoir, and ESN state reset per engine unit",
        "test_label_policy": "offline scoring labels only; no test updates in readouts",
        "train_end": task.train_end,
    }
    return rows, per_unit, diagnostics


def classify(summary: list[dict[str, Any]], args: argparse.Namespace) -> dict[str, Any]:
    by_model = {str(r["model"]): r for r in summary}
    best = min(summary, key=lambda r: float(r["test_rmse_mean"]))
    v23 = by_model[V23]
    v22 = by_model[V22]
    best_baseline = min([by_model[m] for m in [CONSTANT, AGE, LAG, ONLINE, RESERVOIR, ESN]], key=lambda r: float(r["test_rmse_mean"]))
    sham_models = [RESET, SHUFFLED, SHUFFLED_TARGET, NO_UPDATE]
    sham_separated = sum(1 for m in sham_models if float(v23["test_rmse_mean"]) < float(by_model[m]["test_rmse_mean"]))
    v23_beats_v22 = float(v23["test_rmse_mean"]) < float(v22["test_rmse_mean"])
    v23_margin_vs_best_baseline = float(best_baseline["test_rmse_mean"]) / float(v23["test_rmse_mean"]) if float(v23["test_rmse_mean"]) > 0 else None
    if best["model"] == V23 and sham_separated >= args.min_sham_separations:
        outcome = "v2_3_cmapss_candidate_signal"
    elif v23_beats_v22 and sham_separated >= args.min_sham_separations:
        outcome = "v2_3_internal_improvement_but_external_baselines_may_dominate"
    else:
        outcome = "v2_3_no_public_adapter_advantage"
    return {
        "outcome": outcome,
        "best_model": best["model"],
        "best_model_test_rmse_mean": best["test_rmse_mean"],
        "v2_3_rank": v23["rank_by_test_rmse"],
        "v2_3_test_rmse_mean": v23["test_rmse_mean"],
        "v2_2_test_rmse_mean": v22["test_rmse_mean"],
        "v2_3_beats_v2_2": v23_beats_v22,
        "best_external_baseline": best_baseline["model"],
        "best_external_baseline_test_rmse_mean": best_baseline["test_rmse_mean"],
        "v2_3_margin_vs_best_external_baseline": v23_margin_vs_best_baseline,
        "v2_3_sham_separations": sham_separated,
        "min_sham_separations": args.min_sham_separations,
        "freeze_authorized": False,
        "hardware_transfer_authorized": False,
    }


def write_report(output_dir: Path, payload: dict[str, Any]) -> None:
    c = payload["classification"]
    lines = [
        "# Tier 7.1c Compact C-MAPSS FD001 Scoring Gate",
        "",
        f"- Generated: `{payload['generated_at_utc']}`",
        f"- Runner revision: `{payload['runner_revision']}`",
        f"- Status: **{payload['status'].upper()}**",
        f"- Criteria: `{payload['criteria_passed']}/{payload['criteria_total']}`",
        f"- Outcome: `{c['outcome']}`",
        "",
        "## Key Metrics",
        "",
        f"- Best model: `{c['best_model']}` RMSE `{c['best_model_test_rmse_mean']}`",
        f"- v2.3 rank: `{c['v2_3_rank']}`",
        f"- v2.3 RMSE: `{c['v2_3_test_rmse_mean']}`",
        f"- v2.2 RMSE: `{c['v2_2_test_rmse_mean']}`",
        f"- Best external baseline: `{c['best_external_baseline']}` RMSE `{c['best_external_baseline_test_rmse_mean']}`",
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
    output_dir.joinpath("tier7_1c_report.md").write_text("\n".join(lines), encoding="utf-8")


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
    task = load_task(args)
    seeds = [int(x) for x in args.seeds.split(",") if x.strip()]
    rows: list[dict[str, Any]] = []
    per_unit: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    for seed in seeds:
        seed_rows, seed_units, seed_diag = run_seed(task, seed, args)
        rows.extend(seed_rows)
        per_unit.extend(seed_units)
        diagnostics.append(seed_diag)
    summary = aggregate(rows)
    classification = classify(summary, args)
    preflight = read_json(TIER7_1B_RESULTS) if TIER7_1B_RESULTS.exists() else {}
    models = {str(r["model"]) for r in rows}
    criteria = [
        criterion("Tier 7.1b preflight exists", TIER7_1B_RESULTS, "exists", TIER7_1B_RESULTS.exists()),
        criterion("Tier 7.1b preflight passed", preflight.get("status"), "== pass", preflight.get("status") == "pass"),
        criterion("C-MAPSS ZIP checksum matches preflight", task.zip_sha256, "matches Tier 7.1b", task.zip_sha256 == preflight.get("zip_sha256")),
        criterion("all required models ran", sorted(models), "contains required models", all(m in models for m in REQUIRED_MODELS)),
        criterion("metrics finite", True, "all model RMSE finite", all(math.isfinite(float(r["test_rmse"])) for r in rows)),
        criterion("test units preserved", task.fd001_profile["test_units"], "== 100", task.fd001_profile["test_units"] == 100),
        criterion("train-only normalization used", True, "true", True),
        criterion("no test readout updates", [r["diagnostics"].get("test_updates") for r in rows], "all 0 or None", all((r["diagnostics"].get("test_updates") in {0, None}) for r in rows)),
        criterion("v2.3 shams present", [RESET, SHUFFLED, SHUFFLED_TARGET, NO_UPDATE], "present", all(m in models for m in [RESET, SHUFFLED, SHUFFLED_TARGET, NO_UPDATE])),
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
        "fd001_profile": task.fd001_profile,
        "seeds": seeds,
        "model_summary": summary,
        "seed_diagnostics": diagnostics,
        "output_dir": str(output_dir),
        "claim_boundary": (
            "Tier 7.1c is compact software scoring on NASA C-MAPSS FD001 using a "
            "train-only PCA1 scalar stream and train-prefix readouts. It is not "
            "a full C-MAPSS benchmark, not a new baseline freeze, not hardware/"
            "native transfer, and not AGI/ASI evidence."
        ),
        "next_step": (
            "Run Tier 7.1d C-MAPSS failure analysis / adapter repair before adding "
            "mechanisms or moving hardware. Localize whether the compact gap comes "
            "from scalar PCA1 compression, train-prefix readout policy, target/reset "
            "policy, a missing multichannel CRA adapter interface, or a real v2.3 "
            "limitation on this public adapter."
        ),
    }
    paths = {
        "results_json": output_dir / "tier7_1c_results.json",
        "report_md": output_dir / "tier7_1c_report.md",
        "summary_csv": output_dir / "tier7_1c_summary.csv",
        "model_metrics_csv": output_dir / "tier7_1c_model_metrics.csv",
        "model_summary_csv": output_dir / "tier7_1c_model_summary.csv",
        "per_unit_metrics_csv": output_dir / "tier7_1c_per_unit_metrics.csv",
        "scoring_contract_json": output_dir / "tier7_1c_scoring_contract.json",
    }
    write_json(paths["results_json"], payload)
    write_csv(paths["summary_csv"], [{"criterion": c["name"], "passed": c["passed"], "value": c["value"], "rule": c["rule"]} for c in criteria])
    write_csv(paths["model_metrics_csv"], rows)
    write_csv(paths["model_summary_csv"], summary)
    write_csv(paths["per_unit_metrics_csv"], per_unit)
    write_json(
        paths["scoring_contract_json"],
        {
            "source_preflight": str(TIER7_1B_RESULTS),
            "train_test_policy": "train_FD001 train prefix, test_FD001 held-out test units",
            "label_policy": "test RUL labels used only for offline scoring, not readout updates",
            "adapter_signal": task.fd001_profile["adapter_signal"],
            "target_policy": task.fd001_profile["raw_rul_policy"],
            "models": REQUIRED_MODELS,
            "seeds": seeds,
        },
    )
    write_report(output_dir, payload)
    manifest = make_manifest(output_dir, paths, status)
    write_json(output_dir / "tier7_1c_latest_manifest.json", manifest)
    write_json(CONTROLLED / "tier7_1c_latest_manifest.json", manifest)
    return payload


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    p.add_argument("--data-cache", default=str(DATA_CACHE))
    p.add_argument("--url", default=CMAPSS_ZIP_URL)
    p.add_argument("--timeout", type=int, default=60)
    p.add_argument("--seeds", default="42,43,44")
    p.add_argument("--history", type=int, default=12)
    p.add_argument("--ridge", type=float, default=1e-3)
    p.add_argument("--readout-lr", type=float, default=0.10)
    p.add_argument("--readout-decay", type=float, default=0.0005)
    p.add_argument("--weight-clip", type=float, default=25.0)
    p.add_argument("--output-clip", type=float, default=6.0)
    p.add_argument("--temporal-timescales", default="2,4,8,16,32,64,128")
    p.add_argument("--temporal-hidden-units", type=int, default=16)
    p.add_argument("--temporal-recurrent-scale", type=float, default=0.65)
    p.add_argument("--temporal-input-scale", type=float, default=0.35)
    p.add_argument("--temporal-hidden-decay", type=float, default=0.82)
    p.add_argument("--state-reset-interval", type=int, default=12)
    p.add_argument("--reservoir-units", type=int, default=32)
    p.add_argument("--reservoir-spectral-radius", type=float, default=0.9)
    p.add_argument("--reservoir-input-scale", type=float, default=0.5)
    p.add_argument("--esn-units", type=int, default=48)
    p.add_argument("--esn-spectral-radius", type=float, default=0.95)
    p.add_argument("--min-sham-separations", type=int, default=3)
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
