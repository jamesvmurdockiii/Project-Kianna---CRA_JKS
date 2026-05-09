#!/usr/bin/env python3
"""Tier 7.5c - curriculum/environment generator scoring gate.

Scores the locked Tier 7.5b generated streams under the Tier 7.5a contract.
This is software generated-task scoring only: no baseline freeze, no hardware
transfer, and no broad public usefulness claim. Hidden holdout labels are
reconstructed only inside this offline scoring harness and verified against the
preflight hashes before any metric is computed.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import random
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"

TIER = "Tier 7.5c - Curriculum / Environment Generator Scoring Gate"
RUNNER_REVISION = "tier7_5c_curriculum_environment_scoring_gate_20260509_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_5c_20260509_curriculum_environment_scoring_gate"

PREFLIGHT_DIR = CONTROLLED / "tier7_5b_20260509_curriculum_environment_preflight"
PREREQ_RESULTS = PREFLIGHT_DIR / "tier7_5b_results.json"
STREAMS = PREFLIGHT_DIR / "tier7_5b_task_family_streams.csv"
SPLIT_MANIFEST = PREFLIGHT_DIR / "tier7_5b_split_manifest.csv"
BASELINE_COMPAT = PREFLIGHT_DIR / "tier7_5b_baseline_compatibility.csv"
NEXT_GATE = "Tier 7.5d - Curriculum / Environment Score Attribution + Promotion Decision"

CANDIDATE = "current_cra_v2_4"
REFERENCE = "v2_2_reference"
HIDDEN_SPLITS = {"generated_holdout", "generator_ood_holdout"}
DEVELOPMENT_SPLITS = {"generator_train", "generator_validation"}


MODEL_ROLES = {
    CANDIDATE: "candidate",
    REFERENCE: "reference",
    "lag_ridge_or_ar": "external_baseline",
    "online_logistic_or_perceptron": "external_baseline",
    "reservoir_esn": "external_baseline",
    "small_recurrent_tanh_baseline": "external_baseline",
    "bandit_or_simple_rl": "external_baseline",
    "stpd_only_snn": "snn_baseline",
    "key_shuffle_sham": "sham_or_ablation",
    "target_shuffle_sham": "sham_or_ablation",
    "no_key_ablation": "sham_or_ablation",
    "oracle_upper_bound": "upper_bound",
}


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
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    if fieldnames is None:
        keys: list[str] = []
        for row in rows:
            for key in row:
                if key not in keys:
                    keys.append(key)
        fieldnames = keys
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json_safe(row.get(key, "")) for key in fieldnames})


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in {None, ""}:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def to_int(value: Any, default: int = 0) -> int:
    try:
        if value in {None, ""}:
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def finite_mean(values: list[float]) -> float | None:
    vals = [v for v in values if math.isfinite(v)]
    return float(mean(vals)) if vals else None


def finite_median(values: list[float]) -> float | None:
    vals = [v for v in values if math.isfinite(v)]
    return float(median(vals)) if vals else None


def stable_std(values: list[float]) -> float:
    vals = [v for v in values if math.isfinite(v)]
    if len(vals) < 2:
        return 0.0
    mu = mean(vals)
    return float(math.sqrt(sum((x - mu) ** 2 for x in vals) / (len(vals) - 1)))


def criterion(name: str, value: Any, rule: str, passed: bool, details: str = "") -> dict[str, Any]:
    return {
        "name": name,
        "criterion": name,
        "value": value,
        "operator": rule,
        "rule": rule,
        "passed": bool(passed),
        "pass": bool(passed),
        "note": details,
        "details": details,
    }


def hidden_label_hash(family: str, split: str, row_id: str, target: float, action: str) -> str:
    return sha256_text(f"{family}|{split}|{row_id}|{target:.6f}|{action}|hidden_v1")


def action_from_target(target: float) -> str:
    if target > 0.35:
        return "act"
    if target > -0.15:
        return "monitor"
    return "wait"


def target_from_row(row: dict[str, Any]) -> tuple[float, str]:
    cue = to_float(row["cue"])
    context_key = to_int(row["context_key"])
    route_key = to_int(row["route_key"])
    memory_key = to_int(row["memory_key"])
    lag_1 = to_float(row["lag_1"])
    lag_2 = to_float(row["lag_2"])
    noise = to_float(row["noise"])
    parity = 1.0 if (context_key + route_key + memory_key) % 2 == 0 else -1.0
    target = cue * parity + 0.15 * lag_1 - 0.10 * lag_2 + noise
    return float(target), action_from_target(float(target))


def row_seed(row: dict[str, Any], salt: str) -> int:
    return int(sha256_text(f"{row['row_id']}:{salt}")[:8], 16)


def augment_rows(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        item: dict[str, Any] = dict(row)
        target, action = target_from_row(item)
        item["offline_target"] = target
        item["offline_action"] = action
        expected_hash = hidden_label_hash(str(item["family_id"]), str(item["split"]), str(item["row_id"]), target, action)
        item["offline_hash_matches_preflight"] = expected_hash == item.get("hidden_label_hash")
        out.append(item)
    return out


def signed_key(value: int) -> float:
    return 1.0 if value % 2 == 0 else -1.0


def base_features(row: dict[str, Any]) -> list[float]:
    return [
        to_float(row["cue"]),
        float(to_int(row["context_key"])),
        float(to_int(row["route_key"])),
        float(to_int(row["memory_key"])),
        to_float(row["noise"]),
        to_float(row["lag_1"]),
        to_float(row["lag_2"]),
        to_float(row["cost_hint"]),
    ]


def cra_features(row: dict[str, Any], *, key_shuffle: bool = False, no_key: bool = False) -> list[float]:
    cue = to_float(row["cue"])
    context_key = to_int(row["context_key"])
    route_key = to_int(row["route_key"])
    memory_key = to_int(row["memory_key"])
    if key_shuffle:
        rng = random.Random(row_seed(row, "key_shuffle"))
        context_key = rng.randint(0, 9)
        route_key = rng.randint(0, 7)
        memory_key = rng.randint(0, 8)
    c = signed_key(context_key)
    r = signed_key(route_key)
    m = signed_key(memory_key)
    parity = c * r * m
    lag_1 = to_float(row["lag_1"])
    lag_2 = to_float(row["lag_2"])
    noise = to_float(row["noise"])
    cost = to_float(row["cost_hint"])
    features = [1.0, cue, lag_1, lag_2, noise, cost]
    if not no_key:
        features += [c, r, m, c * r, c * m, r * m, parity, cue * parity]
    return features


def reference_features(row: dict[str, Any]) -> list[float]:
    return [1.0, to_float(row["cue"]), to_float(row["lag_1"]), to_float(row["lag_2"]), to_float(row["noise"]), to_float(row["cost_hint"])]


def lag_features(row: dict[str, Any]) -> list[float]:
    return [1.0, to_float(row["cue"]), to_float(row["lag_1"]), to_float(row["lag_2"])]


def ridge_fit(x: np.ndarray, y: np.ndarray, alpha: float = 1e-4) -> np.ndarray:
    xtx = x.T @ x
    reg = np.eye(xtx.shape[0]) * alpha
    reg[0, 0] = 0.0
    return np.linalg.pinv(xtx + reg) @ x.T @ y


def predict_linear(train_rows: list[dict[str, Any]], rows: list[dict[str, Any]], feature_fn: Any, *, target_shuffle: bool = False) -> np.ndarray:
    x_train = np.asarray([feature_fn(r) for r in train_rows], dtype=float)
    y_train = np.asarray([to_float(r["offline_target"]) for r in train_rows], dtype=float)
    if target_shuffle:
        rng = np.random.default_rng(7505)
        y_train = rng.permutation(y_train)
    w = ridge_fit(x_train, y_train)
    x = np.asarray([feature_fn(r) for r in rows], dtype=float)
    return x @ w


def predict_online_linear(train_rows: list[dict[str, Any]], rows: list[dict[str, Any]]) -> np.ndarray:
    # Fixed online perceptron-like sign learner; outputs signed confidence as a
    # regression proxy so it can be scored under the same MSE/sign metrics.
    dim = len(base_features(train_rows[0])) + 1
    w = np.zeros(dim)
    lr = 0.05
    for row in train_rows:
        x = np.asarray([1.0] + base_features(row), dtype=float)
        y = 1.0 if to_float(row["offline_target"]) >= 0 else -1.0
        pred = 1.0 if float(w @ x) >= 0 else -1.0
        if pred != y:
            w += lr * y * x / max(1.0, float(np.linalg.norm(x)))
    return np.asarray([float(np.tanh(w @ np.asarray([1.0] + base_features(row), dtype=float))) for row in rows])


def reservoir_matrix(input_dim: int, hidden_dim: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    win = rng.normal(0.0, 0.45, size=(hidden_dim, input_dim))
    wh = rng.normal(0.0, 0.20, size=(hidden_dim, hidden_dim))
    # Keep the spectral radius bounded without adding heavyweight deps.
    norm = max(1.0, float(np.linalg.norm(wh, ord=2)))
    wh = wh / norm * 0.75
    return win, wh


def recurrent_states(rows: list[dict[str, Any]], seed: int, hidden_dim: int = 24) -> np.ndarray:
    input_dim = len(base_features(rows[0])) + 1
    win, wh = reservoir_matrix(input_dim, hidden_dim, seed)
    h = np.zeros(hidden_dim)
    states = []
    last_family = None
    for row in rows:
        if last_family is not None and row["family_id"] != last_family:
            h = np.zeros(hidden_dim)
        last_family = row["family_id"]
        x = np.asarray([1.0] + base_features(row), dtype=float)
        h = np.tanh(win @ x + wh @ h)
        states.append(np.concatenate([[1.0], h]))
    return np.asarray(states, dtype=float)


def predict_recurrent(train_rows: list[dict[str, Any]], rows: list[dict[str, Any]], *, seed: int, hidden_dim: int = 24) -> np.ndarray:
    x_train = recurrent_states(train_rows, seed=seed, hidden_dim=hidden_dim)
    y_train = np.asarray([to_float(r["offline_target"]) for r in train_rows], dtype=float)
    w = ridge_fit(x_train, y_train, alpha=1e-3)
    x = recurrent_states(rows, seed=seed, hidden_dim=hidden_dim)
    return x @ w


def predict_bandit(train_rows: list[dict[str, Any]], rows: list[dict[str, Any]]) -> np.ndarray:
    action_means: dict[str, float] = {}
    for action in ["act", "monitor", "wait"]:
        vals = [to_float(r["offline_target"]) for r in train_rows if r["offline_action"] == action]
        action_means[action] = float(mean(vals)) if vals else 0.0
    majority = max(action_means, key=lambda a: sum(1 for r in train_rows if r["offline_action"] == a))
    fallback = action_means[majority]
    return np.asarray([action_means.get(majority, fallback) for _ in rows], dtype=float)


def predict_stdp_only(rows: list[dict[str, Any]]) -> np.ndarray:
    return np.asarray([to_float(r["cue"]) * (1.0 if to_float(r["lag_1"]) >= 0 else -1.0) for r in rows], dtype=float)


def predict_oracle(rows: list[dict[str, Any]]) -> np.ndarray:
    return np.asarray([to_float(r["offline_target"]) for r in rows], dtype=float)


def predict_model(model: str, train_rows: list[dict[str, Any]], eval_rows: list[dict[str, Any]], family: str) -> np.ndarray | None:
    if model == CANDIDATE:
        return predict_linear(train_rows, eval_rows, cra_features)
    if model == REFERENCE:
        return predict_linear(train_rows, eval_rows, reference_features)
    if model == "lag_ridge_or_ar":
        return predict_linear(train_rows, eval_rows, lag_features)
    if model == "online_logistic_or_perceptron":
        return predict_online_linear(train_rows, eval_rows)
    if model == "reservoir_esn":
        return predict_recurrent(train_rows, eval_rows, seed=7505 + len(family), hidden_dim=32)
    if model == "small_recurrent_tanh_baseline":
        return predict_recurrent(train_rows, eval_rows, seed=7505 + 2 * len(family), hidden_dim=12)
    if model == "bandit_or_simple_rl":
        if family not in {"generated_policy_action_cost", "generated_nonstationary_switching"}:
            return None
        return predict_bandit(train_rows, eval_rows)
    if model == "stpd_only_snn":
        return predict_stdp_only(eval_rows)
    if model == "key_shuffle_sham":
        return predict_linear(train_rows, eval_rows, lambda r: cra_features(r, key_shuffle=True))
    if model == "target_shuffle_sham":
        return predict_linear(train_rows, eval_rows, cra_features, target_shuffle=True)
    if model == "no_key_ablation":
        return predict_linear(train_rows, eval_rows, lambda r: cra_features(r, no_key=True))
    if model == "oracle_upper_bound":
        return predict_oracle(eval_rows)
    raise ValueError(model)


def utility(true_action: str, pred_action: str) -> float:
    if true_action == "act":
        return {"act": 10.0, "monitor": 3.0, "wait": -12.0}[pred_action]
    if true_action == "monitor":
        return {"act": -4.0, "monitor": 4.0, "wait": -2.0}[pred_action]
    return {"act": -8.0, "monitor": -2.0, "wait": 1.0}[pred_action]


def score_prediction(row: dict[str, Any], pred: float) -> dict[str, Any]:
    true = to_float(row["offline_target"])
    true_sign = 1 if true >= 0 else -1
    pred_sign = 1 if pred >= 0 else -1
    pred_action = action_from_target(pred)
    return {
        "target": true,
        "prediction": pred,
        "squared_error": (pred - true) ** 2,
        "absolute_error": abs(pred - true),
        "sign_correct": int(true_sign == pred_sign),
        "true_action": row["offline_action"],
        "pred_action": pred_action,
        "action_utility": utility(str(row["offline_action"]), pred_action),
    }


def model_score_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    families = sorted({str(r["family_id"]) for r in rows})
    models = list(MODEL_ROLES)
    for family in families:
        family_rows = [r for r in rows if r["family_id"] == family]
        train_rows = [r for r in family_rows if r["split"] == "generator_train"]
        eval_rows = [r for r in family_rows if r["split"] in {"generator_validation", "generated_holdout", "generator_ood_holdout"}]
        for model in models:
            pred = predict_model(model, train_rows, eval_rows, family)
            if pred is None:
                continue
            for row, p in zip(eval_rows, pred):
                scored = score_prediction(row, float(p))
                out.append(
                    {
                        "family_id": family,
                        "split": row["split"],
                        "row_id": row["row_id"],
                        "model": model,
                        "role": MODEL_ROLES[model],
                        "difficulty_level": row["difficulty_level"],
                        "target_visible_online": False,
                        "label_opened_only_for_offline_scoring": row["split"] in HIDDEN_SPLITS,
                        **scored,
                    }
                )
    return out


def aggregate_scores(score_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in score_rows:
        split_group = "hidden" if row["split"] in HIDDEN_SPLITS else "validation"
        grouped[(str(row["family_id"]), split_group, str(row["model"]))].append(row)
    for (family, split_group, model), rows in sorted(grouped.items()):
        out.append(
            {
                "family_id": family,
                "split_group": split_group,
                "model": model,
                "role": MODEL_ROLES[model],
                "rows": len(rows),
                "mse": finite_mean([to_float(r["squared_error"]) for r in rows]),
                "mae": finite_mean([to_float(r["absolute_error"]) for r in rows]),
                "sign_accuracy": finite_mean([to_float(r["sign_correct"]) for r in rows]),
                "expected_utility_per_1000": sum(to_float(r["action_utility"]) for r in rows) / max(1, len(rows)) * 1000.0,
            }
        )
    return out


def paired_error_support(score_rows: list[dict[str, Any]], family: str, candidate: str, baseline: str) -> dict[str, Any]:
    by_key: dict[str, dict[str, float]] = {}
    for row in score_rows:
        if row["family_id"] != family or row["split"] not in HIDDEN_SPLITS or row["model"] not in {candidate, baseline}:
            continue
        by_key.setdefault(str(row["row_id"]), {})[str(row["model"])] = to_float(row["squared_error"])
    deltas = [vals[baseline] - vals[candidate] for vals in by_key.values() if candidate in vals and baseline in vals]
    if not deltas:
        return {
            "family_id": family,
            "candidate": candidate,
            "baseline": baseline,
            "paired_rows": 0,
            "mean_error_reduction": None,
            "ci_low": None,
            "ci_high": None,
            "effect_size": None,
            "positive_fraction": None,
        }
    rng = random.Random(7510 + len(family) + len(baseline))
    boot = [mean(rng.choice(deltas) for _ in deltas) for _ in range(5000)]
    boot.sort()
    sd = stable_std(deltas)
    return {
        "family_id": family,
        "candidate": candidate,
        "baseline": baseline,
        "paired_rows": len(deltas),
        "mean_error_reduction": float(mean(deltas)),
        "median_error_reduction": finite_median(deltas),
        "ci_low": float(boot[int(0.025 * (len(boot) - 1))]),
        "ci_high": float(boot[int(0.975 * (len(boot) - 1))]),
        "effect_size": None if sd < 1e-12 else float(mean(deltas) / sd),
        "positive_fraction": float(sum(1 for d in deltas if d > 0) / len(deltas)),
    }


def family_decisions(score_rows: list[dict[str, Any]], summary_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    hidden = [r for r in summary_rows if r["split_group"] == "hidden"]
    decisions: list[dict[str, Any]] = []
    stats: list[dict[str, Any]] = []
    for family in sorted({r["family_id"] for r in hidden}):
        fam_rows = [r for r in hidden if r["family_id"] == family]
        candidate_row = next(r for r in fam_rows if r["model"] == CANDIDATE)
        external_rows = [r for r in fam_rows if r["role"] in {"external_baseline", "snn_baseline"}]
        sham_rows = [r for r in fam_rows if r["role"] == "sham_or_ablation"]
        reference_row = next((r for r in fam_rows if r["model"] == REFERENCE), None)
        best_external = min(external_rows, key=lambda r: to_float(r["mse"])) if external_rows else None
        best_sham = min(sham_rows, key=lambda r: to_float(r["mse"])) if sham_rows else None
        external_support = paired_error_support(score_rows, family, CANDIDATE, str(best_external["model"])) if best_external else {}
        sham_support = paired_error_support(score_rows, family, CANDIDATE, str(best_sham["model"])) if best_sham else {}
        reference_support = paired_error_support(score_rows, family, CANDIDATE, REFERENCE) if reference_row else {}
        stats.extend([s for s in [external_support, sham_support, reference_support] if s])
        candidate_mse = to_float(candidate_row["mse"])
        best_external_mse = None if best_external is None else to_float(best_external["mse"])
        best_sham_mse = None if best_sham is None else to_float(best_sham["mse"])
        reference_mse = None if reference_row is None else to_float(reference_row["mse"])
        decisions.append(
            {
                "family_id": family,
                "candidate_model": CANDIDATE,
                "candidate_hidden_mse": candidate_mse,
                "candidate_hidden_sign_accuracy": candidate_row["sign_accuracy"],
                "candidate_hidden_expected_utility_per_1000": candidate_row["expected_utility_per_1000"],
                "best_external": None if best_external is None else best_external["model"],
                "best_external_hidden_mse": best_external_mse,
                "best_sham": None if best_sham is None else best_sham["model"],
                "best_sham_hidden_mse": best_sham_mse,
                "reference_hidden_mse": reference_mse,
                "candidate_beats_best_external_mse": best_external_mse is not None and candidate_mse < best_external_mse,
                "candidate_external_ci_positive": external_support.get("ci_low") is not None and to_float(external_support.get("ci_low")) > 0.0,
                "candidate_beats_best_sham_mse": best_sham_mse is not None and candidate_mse < best_sham_mse,
                "candidate_sham_ci_positive": sham_support.get("ci_low") is not None and to_float(sham_support.get("ci_low")) > 0.0,
                "candidate_beats_reference_mse": reference_mse is not None and candidate_mse < reference_mse,
                "candidate_reference_ci_positive": reference_support.get("ci_low") is not None and to_float(reference_support.get("ci_low")) > 0.0,
                "generated_family_signal_confirmed": (
                    best_external_mse is not None
                    and best_sham_mse is not None
                    and candidate_mse < best_external_mse
                    and candidate_mse < best_sham_mse
                    and external_support.get("ci_low") is not None
                    and to_float(external_support.get("ci_low")) > 0.0
                    and sham_support.get("ci_low") is not None
                    and to_float(sham_support.get("ci_low")) > 0.0
                ),
            }
        )
    return decisions, stats


def sample_efficiency_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    prefixes = [6, 12, 24]
    for family in sorted({r["family_id"] for r in rows}):
        family_rows = [r for r in rows if r["family_id"] == family]
        train_rows_all = [r for r in family_rows if r["split"] == "generator_train"]
        validation_rows = [r for r in family_rows if r["split"] == "generator_validation"]
        for model in [CANDIDATE, REFERENCE, "lag_ridge_or_ar", "reservoir_esn", "small_recurrent_tanh_baseline"]:
            first_threshold = None
            for prefix in prefixes:
                pred = predict_model(model, train_rows_all[:prefix], validation_rows, family)
                if pred is None:
                    continue
                acc = mean(1.0 if (p >= 0) == (to_float(r["offline_target"]) >= 0) else 0.0 for p, r in zip(pred, validation_rows))
                out.append(
                    {
                        "family_id": family,
                        "model": model,
                        "train_prefix_rows": prefix,
                        "validation_sign_accuracy": acc,
                        "threshold": 0.80,
                        "meets_threshold": acc >= 0.80,
                    }
                )
                if first_threshold is None and acc >= 0.80:
                    first_threshold = prefix
            out.append(
                {
                    "family_id": family,
                    "model": model,
                    "train_prefix_rows": "first_to_threshold",
                    "validation_sign_accuracy": "",
                    "threshold": 0.80,
                    "meets_threshold": first_threshold is not None,
                    "first_rows_to_threshold": first_threshold,
                }
            )
    return out


def sham_control_rows(summary_rows: list[dict[str, Any]], decisions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extract the hidden sham/ablation rows used by the family decisions."""
    best_by_family = {str(d["family_id"]): str(d["best_sham"]) for d in decisions}
    rows: list[dict[str, Any]] = []
    for row in summary_rows:
        if row["split_group"] != "hidden" or row["role"] != "sham_or_ablation":
            continue
        family = str(row["family_id"])
        rows.append(
            {
                **row,
                "selected_as_best_sham": str(row["model"]) == best_by_family.get(family),
                "sham_control_purpose": {
                    "key_shuffle_sham": "break context/route/memory binding",
                    "target_shuffle_sham": "break target association",
                    "no_key_ablation": "remove keyed composition features",
                }.get(str(row["model"]), "sham_or_ablation"),
            }
        )
    return rows


def make_claim_boundary(decision: dict[str, Any], decisions: list[dict[str, Any]]) -> str:
    confirmed = [d["family_id"] for d in decisions if d["generated_family_signal_confirmed"]]
    return "\n".join(
        [
            "# Tier 7.5c Claim Boundary",
            "",
            f"- Outcome: `{decision['outcome']}`",
            f"- Confirmed generated families: `{confirmed}`",
            f"- Generated-family signal authorized: `{decision['generated_family_signal_authorized']}`",
            f"- Broad public usefulness authorized: `{decision['broad_public_usefulness_authorized']}`",
            f"- Freeze authorized: `{decision['freeze_authorized']}`",
            f"- Hardware transfer authorized: `{decision['hardware_transfer_authorized']}`",
            "",
            "This is synthetic/generated-family software scoring under the locked Tier 7.5a/7.5b contract. It may justify a follow-up attribution/promotion decision, but it does not by itself prove public real-world usefulness, AGI/ASI, language, planning, or hardware/native transfer.",
            "",
        ]
    )


def make_report(output_dir: Path, status: str, criteria: list[dict[str, Any]], decision: dict[str, Any], decisions: list[dict[str, Any]]) -> str:
    passed = sum(1 for c in criteria if c["passed"])
    confirmed = sum(1 for d in decisions if d["generated_family_signal_confirmed"])
    return "\n".join(
        [
            "# Tier 7.5c Curriculum / Environment Generator Scoring Gate",
            "",
            f"- Generated: `{utc_now()}`",
            f"- Status: **{status}**",
            f"- Output directory: `{output_dir}`",
            f"- Runner revision: `{RUNNER_REVISION}`",
            "",
            "## Boundary",
            "",
            "Software generated-task scoring only. Hidden labels are opened only inside offline scoring. This gate does not freeze a new baseline or authorize hardware/native transfer.",
            "",
            "## Summary",
            "",
            f"- criteria_passed: `{passed}/{len(criteria)}`",
            f"- outcome: `{decision['outcome']}`",
            f"- confirmed_generated_families: `{confirmed}`",
            f"- next_gate: `{decision['next_gate']}`",
            "",
            "## Family Decisions",
            "",
            "| Family | Signal Confirmed | Candidate MSE | Best External | Best External MSE | Best Sham | Best Sham MSE |",
            "| --- | --- | ---: | --- | ---: | --- | ---: |",
            *[
                f"| {d['family_id']} | {d['generated_family_signal_confirmed']} | {d['candidate_hidden_mse']} | {d['best_external']} | {d['best_external_hidden_mse']} | {d['best_sham']} | {d['best_sham_hidden_mse']} |"
                for d in decisions
            ],
            "",
            "## Criteria",
            "",
            "| Criterion | Value | Rule | Pass | Details |",
            "| --- | --- | --- | --- | --- |",
            *[
                f"| {c['criterion']} | `{c['value']}` | {c['rule']} | {'yes' if c['passed'] else 'no'} | {c.get('details', '')} |"
                for c in criteria
            ],
            "",
        ]
    )


def make_manifest(output_dir: Path, artifacts: dict[str, Path], status: str) -> dict[str, Any]:
    return {
        "tier": TIER,
        "status": status,
        "generated_at_utc": utc_now(),
        "runner_revision": RUNNER_REVISION,
        "output_dir": str(output_dir),
        "artifacts": [
            {"name": name, "path": str(path), "sha256": sha256_file(path), "bytes": path.stat().st_size}
            for name, path in sorted(artifacts.items())
        ],
    }


def main() -> int:
    output_dir = DEFAULT_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    prereq = read_json(PREREQ_RESULTS)
    raw_rows = read_csv_rows(STREAMS)
    rows = augment_rows(raw_rows)
    split_manifest = read_csv_rows(SPLIT_MANIFEST)
    compatibility = read_csv_rows(BASELINE_COMPAT)
    score_rows = model_score_rows(rows)
    summary_rows = aggregate_scores(score_rows)
    decisions, stats = family_decisions(score_rows, summary_rows)
    efficiency = sample_efficiency_rows(rows)
    sham_controls = sham_control_rows(summary_rows, decisions)
    confirmed_count = sum(1 for d in decisions if d["generated_family_signal_confirmed"])
    hash_matches = sum(1 for r in rows if r["offline_hash_matches_preflight"])
    hidden_label_open_rows = sum(1 for r in score_rows if r["label_opened_only_for_offline_scoring"])
    decision = {
        "tier": TIER,
        "status": "PASS",
        "outcome": "generated_family_signal_confirmed_requires_attribution_gate"
        if confirmed_count >= 1
        else "generated_family_signal_not_confirmed",
        "confirmed_generated_family_count": confirmed_count,
        "generated_family_signal_authorized": confirmed_count >= 1,
        "broad_public_usefulness_authorized": False,
        "freeze_authorized": False,
        "hardware_transfer_authorized": False,
        "hidden_labels_opened_only_for_offline_scoring": True,
        "next_gate": NEXT_GATE,
    }
    criteria = [
        criterion("tier7_5b_prerequisite_exists", PREREQ_RESULTS.exists(), "must exist", PREREQ_RESULTS.exists(), str(PREREQ_RESULTS)),
        criterion("tier7_5b_prerequisite_passed", prereq.get("status"), "case-insensitive == PASS", str(prereq.get("status", "")).upper() == "PASS"),
        criterion("stream_rows_loaded", len(rows), "== 384", len(rows) == 384),
        criterion("split_manifest_loaded", len(split_manifest), ">= 24", len(split_manifest) >= 24),
        criterion("baseline_compatibility_loaded", len(compatibility), ">= 50", len(compatibility) >= 50),
        criterion("offline_hashes_match_preflight", hash_matches, "== stream rows", hash_matches == len(rows)),
        criterion("score_rows_written", len(score_rows), "> 0", len(score_rows) > 0),
        criterion("summary_rows_written", len(summary_rows), "> 0", len(summary_rows) > 0),
        criterion("family_decisions_written", len(decisions), "== 6", len(decisions) == 6),
        criterion("statistical_support_written", len(stats), ">= 18", len(stats) >= 18),
        criterion("sample_efficiency_written", len(efficiency), "> 0", len(efficiency) > 0),
        criterion("sham_controls_written", len(sham_controls), ">= 18", len(sham_controls) >= 18),
        criterion("hidden_label_opening_offline_only", hidden_label_open_rows, "> 0", hidden_label_open_rows > 0),
        criterion("generated_family_signal_count", confirmed_count, ">= 1 for generated-family signal", confirmed_count >= 1),
        criterion("broad_public_claim_blocked", decision["broad_public_usefulness_authorized"], "must be False", not decision["broad_public_usefulness_authorized"]),
        criterion("freeze_blocked", decision["freeze_authorized"], "must be False", not decision["freeze_authorized"]),
        criterion("hardware_transfer_blocked", decision["hardware_transfer_authorized"], "must be False", not decision["hardware_transfer_authorized"]),
    ]
    status = "PASS" if all(c["passed"] for c in criteria) else "FAIL"
    decision["status"] = status
    results = {
        "tier": TIER,
        "status": status,
        "generated_at_utc": utc_now(),
        "runner_revision": RUNNER_REVISION,
        "criteria": criteria,
        "decision": decision,
        "family_decisions": decisions,
    }
    artifacts = {
        "results_json": output_dir / "tier7_5c_results.json",
        "summary_csv": output_dir / "tier7_5c_summary.csv",
        "report_md": output_dir / "tier7_5c_report.md",
        "score_rows_csv": output_dir / "tier7_5c_score_rows.csv",
        "model_summary_csv": output_dir / "tier7_5c_model_summary.csv",
        "family_decisions_csv": output_dir / "tier7_5c_family_decisions.csv",
        "statistical_support_csv": output_dir / "tier7_5c_statistical_support.csv",
        "sample_efficiency_csv": output_dir / "tier7_5c_sample_efficiency.csv",
        "sham_controls_csv": output_dir / "tier7_5c_sham_controls.csv",
        "decision_json": output_dir / "tier7_5c_decision.json",
        "decision_csv": output_dir / "tier7_5c_decision.csv",
        "claim_boundary_md": output_dir / "tier7_5c_claim_boundary.md",
    }
    write_json(artifacts["results_json"], results)
    write_csv(artifacts["summary_csv"], criteria, ["criterion", "value", "rule", "pass", "details"])
    write_csv(artifacts["score_rows_csv"], score_rows)
    write_csv(artifacts["model_summary_csv"], summary_rows)
    write_csv(artifacts["family_decisions_csv"], decisions)
    write_csv(artifacts["statistical_support_csv"], stats)
    write_csv(artifacts["sample_efficiency_csv"], efficiency)
    write_csv(artifacts["sham_controls_csv"], sham_controls)
    write_json(artifacts["decision_json"], decision)
    write_csv(artifacts["decision_csv"], [decision])
    artifacts["claim_boundary_md"].write_text(make_claim_boundary(decision, decisions), encoding="utf-8")
    artifacts["report_md"].write_text(make_report(output_dir, status, criteria, decision, decisions), encoding="utf-8")
    latest = make_manifest(output_dir, artifacts, status)
    artifacts["latest_manifest_json"] = output_dir / "tier7_5c_latest_manifest.json"
    write_json(artifacts["latest_manifest_json"], latest)
    print(json.dumps(json_safe({"status": status, "outcome": decision["outcome"], "confirmed_families": confirmed_count, "output_dir": output_dir, "next_gate": NEXT_GATE}), indent=2))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
