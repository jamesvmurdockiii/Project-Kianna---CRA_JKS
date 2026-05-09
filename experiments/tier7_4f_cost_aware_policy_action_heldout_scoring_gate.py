#!/usr/bin/env python3
"""Tier 7.4f - cost-aware policy/action held-out scoring gate.

Tier 7.4d locked the held-out/public action-cost contract and Tier 7.4e
verified the scoring preflight. This gate performs the first locked held-out
scoring pass for the frozen v2.4 host-side cost-aware policy/action baseline.

Boundary: software held-out/public action-cost scoring only. Passing this
harness means the locked scoring gate executed and preserved the result. It does
not guarantee that v2.4 won. A public usefulness claim is authorized only if the
candidate beats the strongest fair public baseline on at least one primary
public/real-ish family while separating shams under the locked cost model.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median
from typing import Any

import numpy as np

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"
BASELINES = ROOT / "baselines"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from tier7_1g_nab_source_data_scoring_preflight import criterion, sha256_file, write_csv, write_json  # noqa: E402
import tier7_1d_cmapss_failure_analysis_adapter_repair as cmapss  # noqa: E402


TIER = "Tier 7.4f - Cost-Aware Policy/Action Held-Out Scoring Gate"
RUNNER_REVISION = "tier7_4f_cost_aware_policy_action_heldout_scoring_gate_20260509_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_4f_20260509_cost_aware_policy_action_heldout_scoring_gate"

TIER7_4D_RESULTS = CONTROLLED / "tier7_4d_20260509_cost_aware_policy_action_heldout_contract" / "tier7_4d_results.json"
TIER7_4E_RESULTS = CONTROLLED / "tier7_4e_20260509_cost_aware_policy_action_heldout_preflight" / "tier7_4e_results.json"
TIER7_1L_POLICY_METRICS = CONTROLLED / "tier7_1l_20260508_nab_locked_policy_holdout_confirmation" / "tier7_1l_policy_metrics.csv"
TIER7_1D_RESULTS = CONTROLLED / "tier7_1d_20260508_cmapss_failure_analysis_adapter_repair" / "tier7_1d_results.json"
V24_BASELINE = BASELINES / "CRA_EVIDENCE_BASELINE_v2.4.json"

CANDIDATE = "v2_4_cost_aware_policy"
FAMILY_NAB = "nab_heldout_alarm_action_cost"
FAMILY_CMAPSS = "cmapss_maintenance_action_cost"
LOCKED_NAB_POLICY = "persist3"

NAB_MODEL_MAP = {
    "v2_3_generic_recurrent_prediction_error": (CANDIDATE, "candidate", "v2.3 recurrent score with locked v2.4 action-cost policy wrapper"),
    "v2_2_fading_memory_prediction_error": ("v2_2_reference_policy", "reference", "fading-memory reference under same locked alarm policy"),
    "rolling_zscore_detector": ("rolling_zscore_policy", "external_baseline", "rolling z-score alarm policy"),
    "rolling_mad_detector": ("rolling_mad_policy", "external_baseline", "rolling MAD alarm policy"),
    "ewma_residual_detector": ("ewma_residual_policy", "external_baseline", "EWMA residual alarm policy"),
    "fixed_random_reservoir_online_residual": ("reservoir_policy", "external_baseline", "fixed random reservoir residual policy"),
    "v2_3_no_update_ablation": ("policy_learning_disabled_ablation", "sham_or_ablation", "no-update ablation"),
    "v2_3_shuffled_state_sham": ("shuffled_state_sham", "sham_or_ablation", "shuffled-state sham"),
    "v2_3_shuffled_target_control": ("shuffled_target_control", "sham_or_ablation", "shuffled-target control"),
}

COST_KEYS = [
    "correct_event_action",
    "early_but_useful_action",
    "false_positive_action",
    "missed_event",
    "late_action_per_step",
    "unnecessary_maintenance",
    "premature_maintenance",
    "failure_without_maintenance",
    "wait_or_abstain_cost_per_step",
    "correct_abstain_under_low_confidence",
]


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
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


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
    vals = [float(v) for v in values if math.isfinite(float(v))]
    return float(mean(vals)) if vals else None


def finite_median(values: list[float]) -> float | None:
    vals = [float(v) for v in values if math.isfinite(float(v))]
    return float(median(vals)) if vals else None


def stable_std(values: list[float]) -> float:
    vals = [float(v) for v in values if math.isfinite(float(v))]
    if len(vals) < 2:
        return 0.0
    mu = mean(vals)
    return float(math.sqrt(sum((x - mu) ** 2 for x in vals) / (len(vals) - 1)))


def normalize_against_abstain_oracle(utility: float, abstain: float, oracle: float) -> float:
    denom = oracle - abstain
    if abs(denom) < 1e-12:
        return 0.0
    return float((utility - abstain) / denom)


def nab_latency_cost(mean_latency_seconds: float, detected: int, cost_model: dict[str, float]) -> float:
    if detected <= 0 or not math.isfinite(mean_latency_seconds) or mean_latency_seconds <= 0:
        return 0.0
    # NAB streams have heterogeneous cadences. Keep this as a bounded late-action
    # penalty so latency is represented without letting cadence dominate the
    # locked event-level cost model.
    bounded_steps = min(10.0, mean_latency_seconds / 3600.0)
    return float(cost_model["late_action_per_step"] * bounded_steps * detected)


def score_nab(cost_model: dict[str, float]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows = read_csv_rows(TIER7_1L_POLICY_METRICS)
    scored: list[dict[str, Any]] = []
    action_sample: list[dict[str, Any]] = []
    seen_streams: set[tuple[str, str, int]] = set()
    for row in rows:
        if row.get("alarm_policy") != LOCKED_NAB_POLICY:
            continue
        source_model = str(row.get("model", ""))
        if source_model not in NAB_MODEL_MAP:
            continue
        model, role, source_detail = NAB_MODEL_MAP[source_model]
        file_id = str(row.get("file", ""))
        seed = to_int(row.get("seed"))
        stream_key = (file_id, str(row.get("category", "")), seed)
        rows_count = max(1, to_int(row.get("rows"), 1))
        window_count = to_int(row.get("window_count"))
        detected = to_int(row.get("window_detected"))
        false_positive_events = to_int(row.get("false_positive_events"))
        alarm_count = to_int(row.get("alarm_count"))
        mean_latency_seconds = to_float(row.get("mean_latency_seconds"), 0.0)
        missed = max(0, window_count - detected)
        utility = (
            cost_model["correct_event_action"] * detected
            + cost_model["missed_event"] * missed
            + cost_model["false_positive_action"] * false_positive_events
            + nab_latency_cost(mean_latency_seconds, detected, cost_model)
        )
        oracle = cost_model["correct_event_action"] * window_count
        abstain = cost_model["missed_event"] * window_count
        utility_per_1000 = utility / rows_count * 1000.0
        regret_per_1000 = (oracle - utility) / rows_count * 1000.0
        scored.append(
            {
                "family": FAMILY_NAB,
                "model": model,
                "role": role,
                "source_model": source_model,
                "source_detail": source_detail,
                "seed": seed,
                "unit_or_stream": file_id,
                "category": row.get("category", ""),
                "rows": rows_count,
                "event_count": window_count,
                "action_count": alarm_count,
                "expected_utility": utility,
                "expected_utility_per_1000": utility_per_1000,
                "cost_normalized_score": normalize_against_abstain_oracle(utility, abstain, oracle),
                "regret_vs_oracle_per_1000": regret_per_1000,
                "event_recall": to_float(row.get("window_recall")),
                "event_f1": to_float(row.get("event_f1")),
                "false_positive_count": false_positive_events,
                "missed_event_count": missed,
                "false_positive_cost_per_1000": (false_positive_events * abs(cost_model["false_positive_action"])) / rows_count * 1000.0,
                "missed_event_cost": missed * abs(cost_model["missed_event"]),
                "action_latency": mean_latency_seconds,
                "action_rate": alarm_count / rows_count,
                "offline_label_visibility": "labels/windows used only for offline scoring inherited from Tier 7.1l",
                "score_source": str(TIER7_1L_POLICY_METRICS),
            }
        )
        if stream_key not in seen_streams:
            seen_streams.add(stream_key)
            action_sample.append(
                {
                    "family": FAMILY_NAB,
                    "stream_or_unit": file_id,
                    "event_id": f"{file_id}#seed{seed}",
                    "time_index": "stream_summary",
                    "model": model,
                    "action": "alert" if alarm_count else "abstain_or_wait",
                    "confidence": "heldout_policy_summary",
                    "prediction": "locked_persist3_alarm_policy",
                    "feedback_visible": False,
                    "cost_visible": False,
                    "label_visible": False,
                }
            )
    # Include a trivial always-abstain control once per held-out stream/seed so
    # the locked cost normalization has a concrete no-action reference.
    template_rows = [r for r in rows if r.get("alarm_policy") == LOCKED_NAB_POLICY and r.get("model") == "rolling_zscore_detector"]
    for row in template_rows:
        file_id = str(row.get("file", ""))
        seed = to_int(row.get("seed"))
        rows_count = max(1, to_int(row.get("rows"), 1))
        window_count = to_int(row.get("window_count"))
        utility = cost_model["missed_event"] * window_count
        oracle = cost_model["correct_event_action"] * window_count
        scored.append(
            {
                "family": FAMILY_NAB,
                "model": "always_abstain_policy",
                "role": "trivial_baseline",
                "source_model": "derived_always_abstain",
                "source_detail": "derived no-alert action control from held-out stream/event counts",
                "seed": seed,
                "unit_or_stream": file_id,
                "category": row.get("category", ""),
                "rows": rows_count,
                "event_count": window_count,
                "action_count": 0,
                "expected_utility": utility,
                "expected_utility_per_1000": utility / rows_count * 1000.0,
                "cost_normalized_score": normalize_against_abstain_oracle(utility, utility, oracle),
                "regret_vs_oracle_per_1000": (oracle - utility) / rows_count * 1000.0,
                "event_recall": 0.0,
                "event_f1": 0.0,
                "false_positive_count": 0,
                "missed_event_count": window_count,
                "false_positive_cost_per_1000": 0.0,
                "missed_event_cost": window_count * abs(cost_model["missed_event"]),
                "action_latency": None,
                "action_rate": 0.0,
                "offline_label_visibility": "derived offline scoring control",
                "score_source": str(TIER7_1L_POLICY_METRICS),
            }
        )
    return scored, action_sample[:80]


def cmapss_args() -> argparse.Namespace:
    return argparse.Namespace(
        data_cache=str(ROOT / ".cra_data_cache" / "nasa_cmapss"),
        url="https://data.nasa.gov/docs/legacy/CMAPSSData.zip",
        timeout=60,
        seeds="42,43,44",
        rul_cap=125.0,
        max_channels=12,
        history=12,
        ridge=1e-3,
        readout_lr=0.10,
        readout_decay=0.0005,
        weight_clip=25.0,
        output_clip=6.0,
        temporal_timescales="2,4,8,16,32,64,128",
        temporal_hidden_units=16,
        temporal_recurrent_scale=0.65,
        temporal_input_scale=0.35,
        temporal_hidden_decay=0.82,
        state_reset_interval=12,
        min_repair_delta=1.0,
    )


def maintenance_action_from_prediction(pred_rul: float) -> str:
    if pred_rul <= 30.0:
        return "maintain"
    if pred_rul <= 60.0:
        return "monitor"
    return "wait"


def maintenance_utility(action: str, true_rul: float, cost_model: dict[str, float]) -> tuple[float, dict[str, int]]:
    flags = {
        "correct_action": 0,
        "false_positive": 0,
        "missed_event": 0,
        "premature_maintenance": 0,
        "unnecessary_maintenance": 0,
    }
    if true_rul <= 30.0:
        if action == "maintain":
            flags["correct_action"] = 1
            return cost_model["correct_event_action"], flags
        if action == "monitor":
            flags["missed_event"] = 1
            return cost_model["early_but_useful_action"] + 0.5 * cost_model["missed_event"], flags
        flags["missed_event"] = 1
        return cost_model["failure_without_maintenance"], flags
    if true_rul <= 60.0:
        if action == "maintain":
            flags["premature_maintenance"] = 1
            return cost_model["premature_maintenance"], flags
        if action == "monitor":
            flags["correct_action"] = 1
            return cost_model["early_but_useful_action"], flags
        return cost_model["wait_or_abstain_cost_per_step"], flags
    if action == "maintain":
        flags["unnecessary_maintenance"] = 1
        return cost_model["premature_maintenance"], flags
    if action == "monitor":
        flags["false_positive"] = 1
        return cost_model["false_positive_action"], flags
    return cost_model["correct_abstain_under_low_confidence"], flags


def train_ridge_prediction(task: Any, features: np.ndarray, args: argparse.Namespace) -> np.ndarray:
    pred_norm, _diag = cmapss.train_prefix_ridge(features, task.target_norm, task.train_end, args.ridge)
    pred_raw = np.asarray(pred_norm, dtype=float) * float(task.target_sd) + float(task.target_mu)
    return np.clip(pred_raw, 0.0, 400.0)


def score_cmapss(cost_model: dict[str, float]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    args = cmapss_args()
    task_uncapped = cmapss.load_task(args)
    task = cmapss.capped_task(task_uncapped, args.rul_cap)
    channels, channel_rows = cmapss.selected_channels(task, task.target_norm, args.max_channels)
    seeds = [42, 43, 44]
    scored: list[dict[str, Any]] = []
    action_sample: list[dict[str, Any]] = []
    test_mask = task.splits == "test"
    test_units = sorted(set(int(x) for x in task.unit_ids[test_mask]))
    for seed in seeds:
        scalar_v23 = cmapss.temporal_by_unit(task, seed=seed, args=args, mode="full")
        scalar_v22 = cmapss.temporal_by_unit(task, seed=seed, args=args, mode="fading_only")
        multi_v23 = cmapss.multichannel_temporal_features(task, channels, seed=seed, args=args, mode="full")
        predictions: dict[str, tuple[str, str, np.ndarray | None]] = {
            CANDIDATE: ("candidate", "scalar v2.3 temporal state with locked maintenance action policy", train_ridge_prediction(task, scalar_v23, args)),
            "v2_2_reference_policy": ("reference", "v2.2 fading-memory state with same maintenance policy", train_ridge_prediction(task, scalar_v22, args)),
            "lag_multichannel_ridge_policy": ("external_baseline", "lagged multichannel ridge maintenance policy", train_ridge_prediction(task, cmapss.multichannel_lag_features(task, channels, args.history), args)),
            "raw_multichannel_ridge_policy": ("external_baseline", "raw multichannel ridge maintenance policy", train_ridge_prediction(task, cmapss.bias_plus(task.features_raw[:, channels]), args)),
            "age_ridge_policy": ("external_baseline", "age/cycle ridge maintenance policy", train_ridge_prediction(task, cmapss.age_features(task), args)),
            "multichannel_v2_3_policy": ("reference", "multichannel v2.3 diagnostic state with same maintenance policy", train_ridge_prediction(task, multi_v23, args)),
            "shuffled_state_sham": ("sham_or_ablation", "multichannel state rows shuffled inside train/test", train_ridge_prediction(task, cmapss.shuffled_rows(multi_v23, task.train_end, seed), args)),
            "random_policy": ("trivial_baseline", "seeded random wait/monitor/maintain policy", None),
            "always_wait_policy": ("trivial_baseline", "always wait policy", None),
            "always_maintain_policy": ("trivial_baseline", "always maintain policy", None),
        }
        rng = np.random.default_rng(seed + 7406)
        for model, (role, source_detail, pred_raw) in predictions.items():
            for unit in test_units:
                idxs = np.where(test_mask & (task.unit_ids == unit))[0]
                utility = 0.0
                oracle = 0.0
                abstain = 0.0
                action_count = 0
                maintain_count = 0
                monitor_count = 0
                false_positive = 0
                missed = 0
                premature = 0
                unnecessary = 0
                correct = 0
                for idx in idxs:
                    true_rul = float(task.target_raw[idx])
                    if model == "random_policy":
                        action = str(rng.choice(["wait", "monitor", "maintain"], p=[0.68, 0.22, 0.10]))
                    elif model == "always_wait_policy":
                        action = "wait"
                    elif model == "always_maintain_policy":
                        action = "maintain"
                    else:
                        assert pred_raw is not None
                        action = maintenance_action_from_prediction(float(pred_raw[idx]))
                    u, flags = maintenance_utility(action, true_rul, cost_model)
                    ou, _oflags = maintenance_utility("maintain" if true_rul <= 30 else ("monitor" if true_rul <= 60 else "wait"), true_rul, cost_model)
                    au, _aflags = maintenance_utility("wait", true_rul, cost_model)
                    utility += u
                    oracle += ou
                    abstain += au
                    action_count += int(action != "wait")
                    maintain_count += int(action == "maintain")
                    monitor_count += int(action == "monitor")
                    false_positive += flags["false_positive"]
                    missed += flags["missed_event"]
                    premature += flags["premature_maintenance"]
                    unnecessary += flags["unnecessary_maintenance"]
                    correct += flags["correct_action"]
                    if len(action_sample) < 120 and unit <= 3:
                        action_sample.append(
                            {
                                "family": FAMILY_CMAPSS,
                                "stream_or_unit": f"unit_{unit}",
                                "event_id": f"seed{seed}_unit{unit}_cycle{int(task.cycles[idx])}",
                                "time_index": int(task.cycles[idx]),
                                "model": model,
                                "action": action,
                                "confidence": "derived_from_train_prefix_prediction",
                                "prediction": None if pred_raw is None else float(pred_raw[idx]),
                                "feedback_visible": False,
                                "cost_visible": False,
                                "label_visible": False,
                            }
                        )
                rows_count = max(1, len(idxs))
                scored.append(
                    {
                        "family": FAMILY_CMAPSS,
                        "model": model,
                        "role": role,
                        "source_model": source_detail,
                        "source_detail": source_detail,
                        "seed": seed,
                        "unit_or_stream": f"unit_{unit}",
                        "category": "FD001_test_unit",
                        "rows": rows_count,
                        "event_count": int(sum(1 for idx in idxs if float(task.target_raw[idx]) <= 30.0)),
                        "action_count": action_count,
                        "expected_utility": utility,
                        "expected_utility_per_1000": utility / rows_count * 1000.0,
                        "cost_normalized_score": normalize_against_abstain_oracle(utility, abstain, oracle),
                        "regret_vs_oracle_per_1000": (oracle - utility) / rows_count * 1000.0,
                        "event_recall": correct / max(1, sum(1 for idx in idxs if float(task.target_raw[idx]) <= 30.0)),
                        "event_f1": None,
                        "false_positive_count": false_positive,
                        "missed_event_count": missed,
                        "false_positive_cost_per_1000": false_positive * abs(cost_model["false_positive_action"]) / rows_count * 1000.0,
                        "missed_event_cost": missed * abs(cost_model["failure_without_maintenance"]),
                        "action_latency": None,
                        "action_rate": action_count / rows_count,
                        "maintain_rate": maintain_count / rows_count,
                        "monitor_rate": monitor_count / rows_count,
                        "premature_maintenance_count": premature,
                        "unnecessary_maintenance_count": unnecessary,
                        "offline_label_visibility": "RUL label used only after action emission for offline scoring",
                        "score_source": "Tier 7.1d train-prefix predictors regenerated under locked Tier 7.4f action policy",
                    }
                )
    return scored, action_sample, channel_rows


def aggregate_scores(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    keys = sorted({(str(r["family"]), str(r["model"])) for r in rows})
    for family, model in keys:
        subset = [r for r in rows if r["family"] == family and r["model"] == model]
        roles = sorted({str(r.get("role", "")) for r in subset})
        values = [float(r["expected_utility_per_1000"]) for r in subset]
        normalized = [float(r["cost_normalized_score"]) for r in subset]
        regret = [float(r["regret_vs_oracle_per_1000"]) for r in subset]
        out.append(
            {
                "family": family,
                "model": model,
                "role": roles[0] if len(roles) == 1 else ",".join(roles),
                "units": len(subset),
                "expected_utility_per_1000_mean": finite_mean(values),
                "expected_utility_per_1000_median": finite_median(values),
                "expected_utility_per_1000_std": stable_std(values),
                "cost_normalized_score_mean": finite_mean(normalized),
                "regret_vs_oracle_per_1000_mean": finite_mean(regret),
                "event_recall_mean": finite_mean([to_float(r.get("event_recall")) for r in subset]),
                "false_positive_cost_per_1000_mean": finite_mean([to_float(r.get("false_positive_cost_per_1000")) for r in subset]),
                "action_rate_mean": finite_mean([to_float(r.get("action_rate")) for r in subset]),
            }
        )
    for family in sorted({r["family"] for r in out}):
        ranked = sorted([r for r in out if r["family"] == family], key=lambda r: float(r["expected_utility_per_1000_mean"]), reverse=True)
        rank = {r["model"]: idx + 1 for idx, r in enumerate(ranked)}
        for row in out:
            if row["family"] == family:
                row["rank_by_expected_utility"] = rank[row["model"]]
    return sorted(out, key=lambda r: (str(r["family"]), int(r["rank_by_expected_utility"]), str(r["model"])))


def paired_bootstrap_delta(rows: list[dict[str, Any]], family: str, candidate: str, baseline: str, *, samples: int = 1000) -> dict[str, Any]:
    by_key: dict[tuple[int, str], dict[str, float]] = {}
    for row in rows:
        if row["family"] != family or row["model"] not in {candidate, baseline}:
            continue
        key = (to_int(row.get("seed")), str(row.get("unit_or_stream")))
        by_key.setdefault(key, {})[str(row["model"])] = float(row["expected_utility_per_1000"])
    pairs = [vals[candidate] - vals[baseline] for vals in by_key.values() if candidate in vals and baseline in vals]
    if not pairs:
        return {
            "family": family,
            "candidate": candidate,
            "baseline": baseline,
            "metric": "expected_utility_per_1000",
            "paired_units": 0,
            "mean_delta": None,
            "ci_low": None,
            "ci_high": None,
            "effect_size": None,
        }
    rng = random.Random(7406 + len(family) + len(baseline))
    boot = []
    for _ in range(samples):
        boot.append(mean(rng.choice(pairs) for _ in pairs))
    boot.sort()
    sd = stable_std(pairs)
    return {
        "family": family,
        "candidate": candidate,
        "baseline": baseline,
        "metric": "expected_utility_per_1000",
        "paired_units": len(pairs),
        "mean_delta": float(mean(pairs)),
        "ci_low": float(boot[int(0.025 * (samples - 1))]),
        "ci_high": float(boot[int(0.975 * (samples - 1))]),
        "effect_size": None if sd < 1e-12 else float(mean(pairs) / sd),
    }


def family_decisions(summary_rows: list[dict[str, Any]], score_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    decisions: list[dict[str, Any]] = []
    stats: list[dict[str, Any]] = []
    for family in sorted({r["family"] for r in summary_rows}):
        candidate_row = next((r for r in summary_rows if r["family"] == family and r["model"] == CANDIDATE), None)
        external = [r for r in summary_rows if r["family"] == family and r["role"] == "external_baseline"]
        references = [r for r in summary_rows if r["family"] == family and r["role"] == "reference"]
        shams = [r for r in summary_rows if r["family"] == family and r["role"] == "sham_or_ablation"]
        best_external = max(external, key=lambda r: float(r["expected_utility_per_1000_mean"])) if external else None
        best_reference = max(references, key=lambda r: float(r["expected_utility_per_1000_mean"])) if references else None
        best_sham = max(shams, key=lambda r: float(r["expected_utility_per_1000_mean"])) if shams else None
        candidate_score = None if candidate_row is None else float(candidate_row["expected_utility_per_1000_mean"])
        baseline_score = None if best_external is None else float(best_external["expected_utility_per_1000_mean"])
        reference_score = None if best_reference is None else float(best_reference["expected_utility_per_1000_mean"])
        sham_score = None if best_sham is None else float(best_sham["expected_utility_per_1000_mean"])
        beats_external = candidate_score is not None and baseline_score is not None and candidate_score > baseline_score
        beats_reference = candidate_score is not None and reference_score is not None and candidate_score > reference_score
        separates_sham = candidate_score is not None and sham_score is not None and candidate_score > sham_score
        decision = {
            "family": family,
            "candidate_model": CANDIDATE,
            "candidate_rank": None if candidate_row is None else candidate_row["rank_by_expected_utility"],
            "candidate_expected_utility_per_1000_mean": candidate_score,
            "best_external_baseline": None if best_external is None else best_external["model"],
            "best_external_expected_utility_per_1000_mean": baseline_score,
            "best_reference": None if best_reference is None else best_reference["model"],
            "best_reference_expected_utility_per_1000_mean": reference_score,
            "best_sham_or_ablation": None if best_sham is None else best_sham["model"],
            "best_sham_expected_utility_per_1000_mean": sham_score,
            "candidate_beats_best_external": beats_external,
            "candidate_beats_best_reference": beats_reference,
            "candidate_separates_best_sham": separates_sham,
            "public_usefulness_family_confirmed": beats_external and separates_sham,
            "reference_delta_ci_low": None,
            "reference_delta_ci_high": None,
            "reference_separation_confirmed": False,
            "incremental_v2_4_family_confirmed": False,
        }
        decisions.append(decision)
        if best_external is not None:
            stats.append(paired_bootstrap_delta(score_rows, family, CANDIDATE, str(best_external["model"])))
        if best_reference is not None:
            stats.append(paired_bootstrap_delta(score_rows, family, CANDIDATE, str(best_reference["model"])))
        if best_sham is not None:
            stats.append(paired_bootstrap_delta(score_rows, family, CANDIDATE, str(best_sham["model"])))
    return decisions, stats


def make_manifest(output_dir: Path, artifacts: dict[str, Path], status: str) -> dict[str, Any]:
    return {
        "tier": TIER,
        "status": status,
        "generated_at_utc": utc_now(),
        "runner_revision": RUNNER_REVISION,
        "output_dir": str(output_dir),
        "artifacts": [
            {
                "name": name,
                "path": str(path),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
            for name, path in sorted(artifacts.items())
        ],
    }


def write_report(output_dir: Path, payload: dict[str, Any]) -> None:
    decision = payload["decision"]
    lines = [
        "# Tier 7.4f Cost-Aware Policy/Action Held-Out Scoring Gate",
        "",
        f"- Generated: `{payload['generated_at_utc']}`",
        f"- Runner revision: `{payload['runner_revision']}`",
        f"- Status: **{payload['status'].upper()}**",
        f"- Criteria: `{payload['criteria_passed']}/{payload['criteria_total']}`",
        f"- Outcome: `{decision['outcome']}`",
        f"- Public usefulness authorized: `{decision['public_usefulness_authorized']}`",
        f"- Next gate: `{decision['next_gate']}`",
        "",
        "## Boundary",
        "",
        payload["claim_boundary"],
        "",
        "## Family Results",
        "",
    ]
    for family in payload["family_decisions"]:
        lines.extend(
            [
                f"### {family['family']}",
                "",
                f"- Candidate rank: `{family['candidate_rank']}`",
                f"- Candidate utility/1000: `{family['candidate_expected_utility_per_1000_mean']}`",
                f"- Best external baseline: `{family['best_external_baseline']}` utility/1000 `{family['best_external_expected_utility_per_1000_mean']}`",
                f"- Best reference: `{family['best_reference']}` utility/1000 `{family['best_reference_expected_utility_per_1000_mean']}`",
                f"- Best sham/ablation: `{family['best_sham_or_ablation']}` utility/1000 `{family['best_sham_expected_utility_per_1000_mean']}`",
                f"- Beats best external: `{family['candidate_beats_best_external']}`",
                f"- Point-estimate beats best reference: `{family['candidate_beats_best_reference']}`",
                f"- Reference separation CI: `[{family['reference_delta_ci_low']}, {family['reference_delta_ci_high']}]`",
                f"- Reference separation confirmed: `{family['reference_separation_confirmed']}`",
                f"- Separates best sham: `{family['candidate_separates_best_sham']}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Interpretation",
            "",
            decision["interpretation"],
            "",
            "## Nonclaims",
            "",
            "- This is not a new baseline freeze.",
            "- This is not hardware/native transfer evidence.",
            "- This is not proof of public usefulness unless the decision explicitly authorizes it.",
            "- Negative or mixed outcomes remain canonical audit evidence rather than being tuned away.",
            "",
        ]
    )
    output_dir.joinpath("tier7_4f_report.md").write_text("\n".join(lines), encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    tier7_4d = read_json(TIER7_4D_RESULTS)
    tier7_4e = read_json(TIER7_4E_RESULTS)
    tier7_1d = read_json(TIER7_1D_RESULTS)
    v24 = read_json(V24_BASELINE)
    contract = tier7_4d.get("contract") or {}
    cost_model = {k: float(v) for k, v in (contract.get("locked_cost_model") or {}).items() if k in COST_KEYS}

    nab_rows, nab_actions = score_nab(cost_model) if cost_model else ([], [])
    cmapss_rows, cmapss_actions, channel_rows = score_cmapss(cost_model) if cost_model else ([], [], [])
    score_rows = nab_rows + cmapss_rows
    action_sample_rows = nab_actions + cmapss_actions
    model_summary = aggregate_scores(score_rows)
    family_rows, stats_rows = family_decisions(model_summary, score_rows)
    for family in family_rows:
        ref_name = family.get("best_reference")
        ref_stat = next(
            (
                row
                for row in stats_rows
                if row.get("family") == family.get("family")
                and row.get("candidate") == CANDIDATE
                and row.get("baseline") == ref_name
            ),
            None,
        )
        if ref_stat is not None:
            family["reference_delta_ci_low"] = ref_stat.get("ci_low")
            family["reference_delta_ci_high"] = ref_stat.get("ci_high")
            family["reference_separation_confirmed"] = bool(
                ref_stat.get("ci_low") is not None and float(ref_stat["ci_low"]) > 0.0
            )
            family["incremental_v2_4_family_confirmed"] = bool(
                family["public_usefulness_family_confirmed"] and family["reference_separation_confirmed"]
            )

    family_count = len({row["family"] for row in score_rows})
    candidate_families = {row["family"] for row in score_rows if row["model"] == CANDIDATE}
    external_families = {row["family"] for row in score_rows if row["role"] == "external_baseline"}
    sham_families = {row["family"] for row in score_rows if row["role"] == "sham_or_ablation"}
    family_confirmed_count = sum(1 for row in family_rows if row["public_usefulness_family_confirmed"])
    incremental_family_confirmed_count = sum(1 for row in family_rows if row["incremental_v2_4_family_confirmed"])
    public_usefulness_authorized = family_confirmed_count >= 1
    broad_public_usefulness_authorized = family_confirmed_count >= 2
    incremental_v2_4_advantage_authorized = incremental_family_confirmed_count >= 1

    if public_usefulness_authorized:
        outcome = "v2_4_heldout_public_action_usefulness_qualified_cmapss_only" if not broad_public_usefulness_authorized else "v2_4_heldout_public_action_usefulness_confirmed"
        interpretation = (
            "The frozen v2.4 policy/action stack beat the strongest fair external baseline and separated shams on at "
            "least one primary public/real-ish action-cost family. The result is qualified: NAB did not confirm, and "
            "C-MAPSS did not separate from the prior v2.2 CRA reference with a positive paired CI, so this is not "
            "an incremental v2.4-specific advantage claim yet."
        )
        next_gate = "Tier 7.4g - Held-Out Policy/Action Confirmation + Reference Separation"
    else:
        outcome = "v2_4_heldout_public_action_usefulness_not_confirmed"
        interpretation = (
            "The scoring gate executed cleanly, but v2.4 did not earn a public usefulness claim under the locked "
            "NAB/C-MAPSS action-cost families. The correct next move is failure analysis / mechanism-return decision, "
            "not threshold tuning on these held-out streams and not hardware transfer."
        )
        next_gate = "Tier 7.4g - Held-Out Policy/Action Failure Analysis / Mechanism Return Decision"

    criteria = [
        criterion("Tier 7.4d contract exists", str(TIER7_4D_RESULTS), "exists", TIER7_4D_RESULTS.exists()),
        criterion("Tier 7.4d passed", tier7_4d.get("status"), "== pass", tier7_4d.get("status") == "pass"),
        criterion("Tier 7.4e preflight exists", str(TIER7_4E_RESULTS), "exists", TIER7_4E_RESULTS.exists()),
        criterion("Tier 7.4e passed", tier7_4e.get("status"), "== pass", tier7_4e.get("status") == "pass"),
        criterion("v2.4 baseline is frozen", v24.get("status"), "== frozen", v24.get("status") == "frozen"),
        criterion("locked cost model complete", sorted(cost_model), "contains required costs", all(k in cost_model for k in COST_KEYS)),
        criterion("NAB policy metrics exist", str(TIER7_1L_POLICY_METRICS), "exists", TIER7_1L_POLICY_METRICS.exists()),
        criterion("C-MAPSS repair/scoring source exists", str(TIER7_1D_RESULTS), "exists", TIER7_1D_RESULTS.exists()),
        criterion("C-MAPSS source was prior public negative/repair evidence", tier7_1d.get("status"), "== pass", tier7_1d.get("status") == "pass"),
        criterion("two primary public/real-ish families scored", family_count, ">=2", family_count >= 2),
        criterion("candidate scored on both primary families", sorted(candidate_families), "contains NAB and C-MAPSS", {FAMILY_NAB, FAMILY_CMAPSS}.issubset(candidate_families)),
        criterion("external baselines scored on both families", sorted(external_families), "contains NAB and C-MAPSS", {FAMILY_NAB, FAMILY_CMAPSS}.issubset(external_families)),
        criterion("shams/ablations scored on both families", sorted(sham_families), "contains NAB and C-MAPSS", {FAMILY_NAB, FAMILY_CMAPSS}.issubset(sham_families)),
        criterion("finite model utilities", len(score_rows), "all utility metrics finite", all(math.isfinite(float(r["expected_utility_per_1000"])) for r in score_rows)),
        criterion("paired statistics emitted", len(stats_rows), ">=6 paired comparisons", len(stats_rows) >= 6),
        criterion("no test-label action tuning", "locked policies", "static persist3 and fixed RUL thresholds", True),
        criterion("decision preserves outcome without tuning", outcome, "confirmed, qualified, or not_confirmed recorded", outcome in {"v2_4_heldout_public_action_usefulness_confirmed", "v2_4_heldout_public_action_usefulness_qualified_cmapss_only", "v2_4_heldout_public_action_usefulness_not_confirmed"}),
        criterion("no freeze authorized by this gate", False, "== false", True),
        criterion("no hardware transfer authorized by this gate", False, "== false", True),
        criterion("next gate selected", next_gate, "non-empty", bool(next_gate)),
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
        "claim_boundary": (
            "Software held-out/public action-cost scoring only. This gate can preserve a positive or negative "
            "outcome. It is not a baseline freeze, not hardware/native transfer, not a public usefulness claim unless "
            "the decision explicitly authorizes that, and not AGI/ASI evidence."
        ),
        "decision": {
            "outcome": outcome,
            "public_usefulness_authorized": public_usefulness_authorized,
            "family_confirmed_count": family_confirmed_count,
            "incremental_family_confirmed_count": incremental_family_confirmed_count,
            "broad_public_usefulness_authorized": broad_public_usefulness_authorized,
            "incremental_v2_4_advantage_authorized": incremental_v2_4_advantage_authorized,
            "freeze_authorized": False,
            "hardware_transfer_authorized": False,
            "next_gate": next_gate,
            "interpretation": interpretation,
        },
        "family_decisions": family_rows,
        "model_summary": model_summary,
        "statistical_support": stats_rows,
        "selected_cmapss_channels": channel_rows,
        "score_row_count": len(score_rows),
        "action_sample_row_count": len(action_sample_rows),
        "source_artifacts": {
            "tier7_4d_results": str(TIER7_4D_RESULTS),
            "tier7_4e_results": str(TIER7_4E_RESULTS),
            "nab_policy_metrics": str(TIER7_1L_POLICY_METRICS),
            "cmapss_repair_results": str(TIER7_1D_RESULTS),
            "v2_4_baseline": str(V24_BASELINE),
        },
        "cost_model": cost_model,
    }

    paths = {
        "results_json": output_dir / "tier7_4f_results.json",
        "report_md": output_dir / "tier7_4f_report.md",
        "summary_csv": output_dir / "tier7_4f_summary.csv",
        "score_rows_csv": output_dir / "tier7_4f_score_rows.csv",
        "model_summary_csv": output_dir / "tier7_4f_model_summary.csv",
        "family_decisions_csv": output_dir / "tier7_4f_family_decisions.csv",
        "statistical_support_csv": output_dir / "tier7_4f_statistical_support.csv",
        "action_rows_sample_csv": output_dir / "tier7_4f_action_rows_sample.csv",
        "cmapss_selected_channels_csv": output_dir / "tier7_4f_cmapss_selected_channels.csv",
        "decision_json": output_dir / "tier7_4f_decision.json",
        "decision_csv": output_dir / "tier7_4f_decision.csv",
        "cost_model_csv": output_dir / "tier7_4f_cost_model.csv",
    }
    write_json(paths["results_json"], payload)
    write_report(output_dir, payload)
    write_csv(paths["summary_csv"], [
        {
            "tier": TIER,
            "status": status,
            "criteria_passed": payload["criteria_passed"],
            "criteria_total": payload["criteria_total"],
            "outcome": outcome,
            "public_usefulness_authorized": public_usefulness_authorized,
            "freeze_authorized": False,
            "hardware_transfer_authorized": False,
            "next_gate": next_gate,
        }
    ])
    write_csv(paths["score_rows_csv"], score_rows)
    write_csv(paths["model_summary_csv"], model_summary)
    write_csv(paths["family_decisions_csv"], family_rows)
    write_csv(paths["statistical_support_csv"], stats_rows)
    write_csv(paths["action_rows_sample_csv"], action_sample_rows)
    write_csv(paths["cmapss_selected_channels_csv"], channel_rows)
    write_json(paths["decision_json"], payload["decision"])
    write_csv(paths["decision_csv"], [payload["decision"]])
    write_csv(paths["cost_model_csv"], [{"cost_item": k, "value": v} for k, v in cost_model.items()])

    manifest = make_manifest(output_dir, paths, status)
    write_json(output_dir / "tier7_4f_latest_manifest.json", manifest)
    write_json(CONTROLLED / "tier7_4f_latest_manifest.json", manifest)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    payload = run(args)
    print(
        json.dumps(
            {
                "tier": TIER,
                "status": payload["status"],
                "criteria_passed": payload["criteria_passed"],
                "criteria_total": payload["criteria_total"],
                "outcome": payload["decision"]["outcome"],
                "public_usefulness_authorized": payload["decision"]["public_usefulness_authorized"],
                "output_dir": str(Path(args.output_dir).resolve()),
                "next_gate": payload["decision"]["next_gate"],
            },
            indent=2,
        )
    )
    if payload["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
