#!/usr/bin/env python3
"""Tier 5.18 self-evaluation / metacognitive monitoring diagnostic.

Tier 5.18 starts from the frozen v2.0 software baseline and asks two bounded
questions:

1. Can a CRA-side monitor estimate reliability, novelty, or likely failure
   before outcome feedback?
2. Does using that monitor improve behavior under ambiguity, OOD insertion,
   memory corruption, hidden-regime mismatch, or module-routing uncertainty?

This is software diagnostic evidence only. It is not consciousness,
self-awareness, introspection, AGI, language, planning, hardware evidence, or a
v2.1 freeze. A future promotion gate must rerun compact regression before any
new baseline is frozen.
"""

from __future__ import annotations

import argparse
import json
import math
import os
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
from tier4_scaling import seeds_from_args  # noqa: E402


TIER = "Tier 5.18 - Self-Evaluation / Metacognitive Monitoring"
BASELINE_PATH = ROOT / "baselines" / "CRA_EVIDENCE_BASELINE_v2.0.json"
DEFAULT_TASKS = (
    "ambiguous_cue,ood_context_insertion,memory_corruption,"
    "hidden_regime_mismatch,module_routing_uncertainty"
)
DEFAULT_VARIANTS = (
    "v2_0_no_monitor,self_eval_gated,monitor_only_no_behavior,"
    "confidence_disabled,random_confidence,time_shuffled_confidence,"
    "always_confident,always_uncertain,anti_confidence,oracle_confidence_upper_bound"
)
CANDIDATE = "self_eval_gated"
EPS = 1e-12


@dataclass(frozen=True)
class MonitorTask:
    name: str
    display_name: str
    description: str
    target: np.ndarray
    primary_score: np.ndarray
    fallback_score: np.ndarray
    hazard_mask: np.ndarray
    ood_mask: np.ndarray
    mismatch_mask: np.ndarray
    tail_mask: np.ndarray
    features: dict[str, np.ndarray]
    metadata: dict[str, Any]

    @property
    def steps(self) -> int:
        return int(self.target.size)


@dataclass(frozen=True)
class VariantSpec:
    name: str
    family: str
    uses_monitor: bool
    uses_monitor_for_behavior: bool
    uses_outcome_in_monitor: bool
    description: str


VARIANTS: dict[str, VariantSpec] = {
    "v2_0_no_monitor": VariantSpec(
        name="v2_0_no_monitor",
        family="frozen_baseline",
        uses_monitor=False,
        uses_monitor_for_behavior=False,
        uses_outcome_in_monitor=False,
        description="Frozen v2.0-style primary path with no reliability monitor or monitor-gated intervention.",
    ),
    "self_eval_gated": VariantSpec(
        name="self_eval_gated",
        family="candidate",
        uses_monitor=True,
        uses_monitor_for_behavior=True,
        uses_outcome_in_monitor=False,
        description="Candidate reliability monitor estimates pre-feedback uncertainty and gates to a v2.0 predictive-binding fallback when risk is high.",
    ),
    "monitor_only_no_behavior": VariantSpec(
        name="monitor_only_no_behavior",
        family="monitor_ablation",
        uses_monitor=True,
        uses_monitor_for_behavior=False,
        uses_outcome_in_monitor=False,
        description="Same monitor signal as the candidate, but the action path ignores it.",
    ),
    "confidence_disabled": VariantSpec(
        name="confidence_disabled",
        family="monitor_ablation",
        uses_monitor=False,
        uses_monitor_for_behavior=False,
        uses_outcome_in_monitor=False,
        description="Constant uninformative confidence with no behavioral intervention.",
    ),
    "random_confidence": VariantSpec(
        name="random_confidence",
        family="sham_monitor",
        uses_monitor=True,
        uses_monitor_for_behavior=True,
        uses_outcome_in_monitor=False,
        description="Random pre-feedback confidence gates behavior.",
    ),
    "time_shuffled_confidence": VariantSpec(
        name="time_shuffled_confidence",
        family="sham_monitor",
        uses_monitor=True,
        uses_monitor_for_behavior=True,
        uses_outcome_in_monitor=False,
        description="Candidate confidence is permuted across time before it can gate behavior.",
    ),
    "always_confident": VariantSpec(
        name="always_confident",
        family="trivial_monitor",
        uses_monitor=False,
        uses_monitor_for_behavior=False,
        uses_outcome_in_monitor=False,
        description="Trivial monitor that never flags risk.",
    ),
    "always_uncertain": VariantSpec(
        name="always_uncertain",
        family="trivial_monitor",
        uses_monitor=False,
        uses_monitor_for_behavior=True,
        uses_outcome_in_monitor=False,
        description="Trivial monitor that always gates to the fallback path.",
    ),
    "anti_confidence": VariantSpec(
        name="anti_confidence",
        family="sham_monitor",
        uses_monitor=True,
        uses_monitor_for_behavior=True,
        uses_outcome_in_monitor=False,
        description="Candidate confidence is inverted before behavioral use.",
    ),
    "oracle_confidence_upper_bound": VariantSpec(
        name="oracle_confidence_upper_bound",
        family="oracle_upper_bound",
        uses_monitor=True,
        uses_monitor_for_behavior=True,
        uses_outcome_in_monitor=True,
        description="Outcome-aware upper bound that gates exactly when the primary path is wrong; excluded from no-leakage claims.",
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


def mean(values: list[float] | np.ndarray) -> float:
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return 0.0
    return float(np.mean(arr))


def stdev(values: list[float] | np.ndarray) -> float:
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size < 2:
        return 0.0
    return float(np.std(arr, ddof=1))


def clip01(values: np.ndarray | float) -> np.ndarray | float:
    return np.clip(values, 0.0, 1.0)


def strict_sign(values: np.ndarray) -> np.ndarray:
    return np.where(values >= 0.0, 1, -1).astype(int)


def auroc(labels: np.ndarray, scores: np.ndarray) -> float | None:
    labels = np.asarray(labels, dtype=int)
    scores = np.asarray(scores, dtype=float)
    mask = np.isfinite(scores)
    labels = labels[mask]
    scores = scores[mask]
    pos = scores[labels == 1]
    neg = scores[labels == 0]
    if pos.size == 0 or neg.size == 0:
        return None
    # Pairwise AUC is small and transparent for these diagnostic streams.
    wins = 0.0
    total = float(pos.size * neg.size)
    for value in pos:
        wins += float(np.sum(value > neg))
        wins += 0.5 * float(np.sum(value == neg))
    return wins / total


def brier_score(correct: np.ndarray, confidence: np.ndarray) -> float:
    correct = np.asarray(correct, dtype=float)
    confidence = np.asarray(confidence, dtype=float)
    return float(np.mean((confidence - correct) ** 2))


def calibration_error(correct: np.ndarray, confidence: np.ndarray, bins: int = 10) -> float:
    correct = np.asarray(correct, dtype=float)
    confidence = np.asarray(confidence, dtype=float)
    edges = np.linspace(0.0, 1.0, bins + 1)
    total = float(correct.size)
    if total <= 0:
        return 1.0
    error = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        if hi >= 1.0:
            mask = (confidence >= lo) & (confidence <= hi)
        else:
            mask = (confidence >= lo) & (confidence < hi)
        if not np.any(mask):
            continue
        error += float(np.sum(mask)) / total * abs(float(np.mean(confidence[mask])) - float(np.mean(correct[mask])))
    return error


def contiguous_recovery_steps(correct: np.ndarray, hazard_mask: np.ndarray, window: int = 30) -> float:
    starts = []
    prev = False
    for idx, active in enumerate(hazard_mask.astype(bool)):
        if active and not prev:
            starts.append(idx)
        prev = bool(active)
    values = []
    for start in starts:
        segment = correct[start : min(start + window, correct.size)]
        if segment.size == 0:
            continue
        recovered = np.where(segment.astype(bool))[0]
        values.append(float(recovered[0]) if recovered.size else float(window))
    return mean(values)


def hazard_intervals(steps: int, *, seed: int, count: int, width: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    mask = np.zeros(steps, dtype=bool)
    earliest = max(8, steps // 8)
    latest = max(earliest + 1, steps - width - 2)
    centers = np.linspace(earliest, latest, count, dtype=int)
    for i, center in enumerate(centers):
        jitter = int(rng.integers(-max(2, width // 3), max(3, width // 3 + 1)))
        start = int(np.clip(center + jitter, earliest, latest))
        mask[start : min(steps, start + width)] = True
    # Guarantee a tail stressor.
    tail_start = max(earliest, steps - width * 2)
    mask[tail_start : min(steps, tail_start + width)] = True
    return mask


def task_weights(name: str) -> dict[str, float]:
    if name == "ambiguous_cue":
        return {"novelty": 0.08, "memory_conflict": 0.33, "prediction_residual": 0.22, "router_entropy": 0.08, "margin_uncertainty": 0.29}
    if name == "ood_context_insertion":
        return {"novelty": 0.42, "memory_conflict": 0.10, "prediction_residual": 0.18, "router_entropy": 0.12, "margin_uncertainty": 0.18}
    if name == "memory_corruption":
        return {"novelty": 0.12, "memory_conflict": 0.43, "prediction_residual": 0.13, "router_entropy": 0.12, "margin_uncertainty": 0.20}
    if name == "hidden_regime_mismatch":
        return {"novelty": 0.10, "memory_conflict": 0.12, "prediction_residual": 0.45, "router_entropy": 0.13, "margin_uncertainty": 0.20}
    if name == "module_routing_uncertainty":
        return {"novelty": 0.13, "memory_conflict": 0.12, "prediction_residual": 0.13, "router_entropy": 0.43, "margin_uncertainty": 0.19}
    raise KeyError(name)


def make_task(name: str, *, steps: int, seed: int, args: argparse.Namespace) -> MonitorTask:
    rng = np.random.default_rng(seed)
    t = np.arange(steps, dtype=float)
    context = ((t // max(12, steps // 12)).astype(int) + seed) % 4
    raw_signal = np.sin(2.0 * np.pi * t / max(18, steps // 9)) + 0.35 * np.cos(2.0 * np.pi * t / max(29, steps // 7))
    raw_signal += rng.normal(0.0, 0.22, size=steps)
    context_rule = np.array([1, -1, 1, -1], dtype=int)
    if name in {"hidden_regime_mismatch", "module_routing_uncertainty"}:
        context_rule = np.array([1, 1, -1, -1], dtype=int)
    target = np.where(raw_signal * context_rule[context] >= 0.0, 1, -1).astype(int)

    width = max(16, int(steps * 0.07))
    count = 4 if steps >= 400 else 2
    hazard = hazard_intervals(steps, seed=seed + 917, count=count, width=width)

    primary_quality = np.where(hazard, -0.72, 1.12)
    primary_score = target * primary_quality + rng.normal(0.0, np.where(hazard, 0.38, 0.32), size=steps)

    # The fallback represents the already-promoted v2.0 predictive-binding path:
    # weaker than the primary path during ordinary rows, but more reliable when
    # the primary path is observably uncertain or mismatched.
    fallback_quality = np.where(hazard, 1.10, -0.02)
    fallback_score = target * fallback_quality + rng.normal(0.0, np.where(hazard, 0.22, 0.72), size=steps)

    tail_mask = np.zeros(steps, dtype=bool)
    tail_mask[int(steps * 0.66) :] = True

    base_noise = lambda scale=0.06: rng.normal(0.0, scale, size=steps)
    novelty = clip01(np.where(hazard, 0.72, 0.14) + base_noise())
    memory_conflict = clip01(np.where(hazard, 0.72, 0.12) + base_noise())
    prediction_residual = clip01(np.where(hazard, 0.74, 0.13) + base_noise())
    router_entropy = clip01(np.where(hazard, 0.73, 0.13) + base_noise())

    # Task-specific non-hazard channels should not all light up equally; this is
    # what makes the monitor more than a single hidden hazard bit.
    if name != "ood_context_insertion":
        novelty = clip01(0.50 * novelty + 0.10 + base_noise(0.035))
    if name != "memory_corruption":
        memory_conflict = clip01(0.50 * memory_conflict + 0.10 + base_noise(0.035))
    if name != "hidden_regime_mismatch":
        prediction_residual = clip01(0.50 * prediction_residual + 0.10 + base_noise(0.035))
    if name != "module_routing_uncertainty":
        router_entropy = clip01(0.50 * router_entropy + 0.10 + base_noise(0.035))

    abs_primary = np.abs(primary_score)
    margin_uncertainty = clip01(1.0 - np.tanh(abs_primary))

    ood_mask = hazard if name == "ood_context_insertion" else np.zeros(steps, dtype=bool)
    mismatch_mask = hazard if name in {"hidden_regime_mismatch", "module_routing_uncertainty"} else np.zeros(steps, dtype=bool)
    if name == "memory_corruption":
        mismatch_mask = hazard.copy()

    descriptions = {
        "ambiguous_cue": "Visible cue fades, then the same current signal can require different actions depending on remembered context.",
        "ood_context_insertion": "Novel context patches appear inside a familiar stream before outcome feedback can confirm risk.",
        "memory_corruption": "A bounded context-memory path can retrieve a wrong key, creating pre-feedback memory conflict.",
        "hidden_regime_mismatch": "The predictive context model expects one regime but the stream shifts before reward catches up.",
        "module_routing_uncertainty": "Multiple learned modules become plausible, producing high routing entropy before the outcome.",
    }
    display = name.replace("_", " ")
    return MonitorTask(
        name=name,
        display_name=display,
        description=descriptions[name],
        target=target,
        primary_score=primary_score,
        fallback_score=fallback_score,
        hazard_mask=hazard,
        ood_mask=ood_mask,
        mismatch_mask=mismatch_mask,
        tail_mask=tail_mask,
        features={
            "novelty": np.asarray(novelty, dtype=float),
            "memory_conflict": np.asarray(memory_conflict, dtype=float),
            "prediction_residual": np.asarray(prediction_residual, dtype=float),
            "router_entropy": np.asarray(router_entropy, dtype=float),
            "margin_uncertainty": np.asarray(margin_uncertainty, dtype=float),
        },
        metadata={
            "hazard_fraction": float(np.mean(hazard)),
            "tail_fraction": float(np.mean(tail_mask)),
            "task_weights": task_weights(name),
            "generated_without_outcome_feedback": True,
        },
    )


def candidate_uncertainty(task: MonitorTask) -> np.ndarray:
    weights = task_weights(task.name)
    uncertainty = np.zeros(task.steps, dtype=float)
    for key, weight in weights.items():
        uncertainty += float(weight) * np.asarray(task.features[key], dtype=float)
    return np.asarray(clip01(uncertainty), dtype=float)


def variant_uncertainty(task: MonitorTask, variant: str, *, seed: int, args: argparse.Namespace) -> np.ndarray:
    base = candidate_uncertainty(task)
    rng = np.random.default_rng(seed + 10007)
    primary_pred = strict_sign(task.primary_score)
    primary_error = (primary_pred != task.target).astype(float)

    if variant in {CANDIDATE, "monitor_only_no_behavior"}:
        return base
    if variant == "v2_0_no_monitor":
        return np.asarray(task.features["margin_uncertainty"], dtype=float)
    if variant == "confidence_disabled":
        return np.full(task.steps, 0.50, dtype=float)
    if variant == "random_confidence":
        return rng.uniform(0.0, 1.0, size=task.steps)
    if variant == "time_shuffled_confidence":
        return rng.permutation(base)
    if variant == "always_confident":
        return np.zeros(task.steps, dtype=float)
    if variant == "always_uncertain":
        return np.ones(task.steps, dtype=float)
    if variant == "anti_confidence":
        return 1.0 - base
    if variant == "oracle_confidence_upper_bound":
        return primary_error
    raise KeyError(variant)


def confidence_from_uncertainty(uncertainty: np.ndarray) -> np.ndarray:
    """Map raw risk to a calibrated probability that the primary path is right."""

    uncertainty = np.asarray(uncertainty, dtype=float)
    return np.asarray(clip01(1.0 / (1.0 + np.exp(13.0 * (uncertainty - 0.40)))), dtype=float)


def run_variant(task: MonitorTask, variant_name: str, *, seed: int, args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    variant = VARIANTS[variant_name]
    uncertainty = variant_uncertainty(task, variant_name, seed=seed, args=args)
    confidence = confidence_from_uncertainty(uncertainty)
    threshold = float(args.gating_uncertainty_threshold)

    if variant_name in {"v2_0_no_monitor", "monitor_only_no_behavior", "confidence_disabled", "always_confident"}:
        gate = np.zeros(task.steps, dtype=bool)
    else:
        gate = uncertainty >= threshold

    final_score = np.where(gate, task.fallback_score, task.primary_score)
    primary_prediction = strict_sign(task.primary_score)
    fallback_prediction = strict_sign(task.fallback_score)
    final_prediction = strict_sign(final_score)
    primary_correct = (primary_prediction == task.target).astype(int)
    fallback_correct = (fallback_prediction == task.target).astype(int)
    final_correct = (final_prediction == task.target).astype(int)
    primary_error = 1 - primary_correct
    final_error = 1 - final_correct

    uncertainty_labels = task.hazard_mask.astype(int)
    ood_or_mismatch = (task.ood_mask | task.mismatch_mask | task.hazard_mask).astype(int)

    rows: list[dict[str, Any]] = []
    for step in range(task.steps):
        rows.append(
            {
                "task": task.name,
                "variant": variant_name,
                "seed": seed,
                "step": step,
                "target": int(task.target[step]),
                "primary_prediction": int(primary_prediction[step]),
                "fallback_prediction": int(fallback_prediction[step]),
                "final_prediction": int(final_prediction[step]),
                "primary_correct": int(primary_correct[step]),
                "fallback_correct": int(fallback_correct[step]),
                "final_correct": int(final_correct[step]),
                "primary_score": float(task.primary_score[step]),
                "fallback_score": float(task.fallback_score[step]),
                "final_score": float(final_score[step]),
                "confidence": float(confidence[step]),
                "uncertainty": float(uncertainty[step]),
                "monitor_gate_active": int(bool(gate[step])),
                "hazard": int(bool(task.hazard_mask[step])),
                "ood": int(bool(task.ood_mask[step])),
                "mismatch": int(bool(task.mismatch_mask[step])),
                "tail": int(bool(task.tail_mask[step])),
                "novelty": float(task.features["novelty"][step]),
                "memory_conflict": float(task.features["memory_conflict"][step]),
                "prediction_residual": float(task.features["prediction_residual"][step]),
                "router_entropy": float(task.features["router_entropy"][step]),
                "margin_uncertainty": float(task.features["margin_uncertainty"][step]),
                "monitor_computed_before_feedback": True,
                "uses_outcome_in_monitor": bool(variant.uses_outcome_in_monitor),
            }
        )

    primary_error_auroc = auroc(primary_error, uncertainty)
    final_error_auroc = auroc(final_error, uncertainty)
    hazard_auroc = auroc(uncertainty_labels, uncertainty)
    ood_auroc = auroc(ood_or_mismatch, uncertainty)
    hazard_mask = task.hazard_mask.astype(bool)
    normal_mask = ~hazard_mask
    tail_mask = task.tail_mask.astype(bool)
    primary_wrong = primary_correct == 0
    primary_wrong_hazard = primary_wrong & hazard_mask
    avoided = final_correct[primary_wrong] if np.any(primary_wrong) else np.asarray([], dtype=int)
    avoided_hazard = final_correct[primary_wrong_hazard] if np.any(primary_wrong_hazard) else np.asarray([], dtype=int)

    summary = {
        "task": task.name,
        "variant": variant_name,
        "variant_family": variant.family,
        "seed": seed,
        "steps": task.steps,
        "overall_accuracy": mean(final_correct),
        "tail_accuracy": mean(final_correct[tail_mask]),
        "hazard_accuracy": mean(final_correct[hazard_mask]),
        "normal_accuracy": mean(final_correct[normal_mask]),
        "primary_accuracy": mean(primary_correct),
        "fallback_accuracy": mean(fallback_correct),
        "primary_error_auroc": primary_error_auroc,
        "final_error_auroc": final_error_auroc,
        "hazard_detection_auroc": hazard_auroc,
        "ood_or_mismatch_detection_auroc": ood_auroc,
        "brier_primary_correct": brier_score(primary_correct, confidence),
        "ece_primary_correct": calibration_error(primary_correct, confidence),
        "mean_uncertainty": mean(uncertainty),
        "mean_uncertainty_hazard": mean(uncertainty[hazard_mask]),
        "mean_uncertainty_normal": mean(uncertainty[normal_mask]),
        "uncertainty_hazard_minus_normal": mean(uncertainty[hazard_mask]) - mean(uncertainty[normal_mask]),
        "gate_rate": mean(gate.astype(float)),
        "gate_rate_hazard": mean(gate[hazard_mask].astype(float)),
        "gate_rate_normal": mean(gate[normal_mask].astype(float)),
        "bad_action_avoidance": mean(avoided) if avoided.size else 0.0,
        "hazard_bad_action_avoidance": mean(avoided_hazard) if avoided_hazard.size else 0.0,
        "recovery_steps": contiguous_recovery_steps(final_correct, task.hazard_mask),
        "monitor_computed_before_feedback": True,
        "uses_outcome_in_monitor": bool(variant.uses_outcome_in_monitor),
        "claim_boundary": "Software self-evaluation diagnostic; not consciousness, introspection, AGI, hardware evidence, or a v2.1 freeze.",
    }
    return rows, summary


def aggregate(summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in summaries:
        grouped.setdefault((str(row["task"]), str(row["variant"])), []).append(row)
    aggregates: list[dict[str, Any]] = []
    metrics = [
        "overall_accuracy",
        "tail_accuracy",
        "hazard_accuracy",
        "normal_accuracy",
        "primary_accuracy",
        "fallback_accuracy",
        "primary_error_auroc",
        "final_error_auroc",
        "hazard_detection_auroc",
        "ood_or_mismatch_detection_auroc",
        "brier_primary_correct",
        "ece_primary_correct",
        "mean_uncertainty",
        "mean_uncertainty_hazard",
        "mean_uncertainty_normal",
        "uncertainty_hazard_minus_normal",
        "gate_rate",
        "gate_rate_hazard",
        "gate_rate_normal",
        "bad_action_avoidance",
        "hazard_bad_action_avoidance",
        "recovery_steps",
    ]
    for (task, variant), items in sorted(grouped.items()):
        out: dict[str, Any] = {
            "task": task,
            "variant": variant,
            "variant_family": VARIANTS[variant].family,
            "runs": len(items),
            "outcome_leakage_runs": sum(int(bool(item.get("uses_outcome_in_monitor", False))) for item in items if variant != "oracle_confidence_upper_bound"),
            "pre_feedback_monitor_rows": sum(int(bool(item.get("monitor_computed_before_feedback", False))) for item in items),
        }
        for metric in metrics:
            values = [float(item[metric]) for item in items if item.get(metric) is not None]
            out[f"mean_{metric}"] = mean(values)
            out[f"min_{metric}"] = min(values) if values else None
            out[f"std_{metric}"] = stdev(values)
        aggregates.append(out)
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
        row: dict[str, Any] = {
            "task": task,
            "candidate_overall_accuracy": cand.get("mean_overall_accuracy"),
            "candidate_tail_accuracy": cand.get("mean_tail_accuracy"),
            "candidate_hazard_accuracy": cand.get("mean_hazard_accuracy"),
            "candidate_primary_error_auroc": cand.get("mean_primary_error_auroc"),
            "candidate_hazard_detection_auroc": cand.get("mean_hazard_detection_auroc"),
            "candidate_brier_primary_correct": cand.get("mean_brier_primary_correct"),
            "candidate_ece_primary_correct": cand.get("mean_ece_primary_correct"),
            "candidate_uncertainty_hazard_minus_normal": cand.get("mean_uncertainty_hazard_minus_normal"),
            "candidate_bad_action_avoidance": cand.get("mean_bad_action_avoidance"),
        }
        best_sham = ("", -1.0)
        for control in controls:
            ctrl = lookup.get((task, control))
            if not ctrl:
                continue
            acc = float(ctrl.get("mean_overall_accuracy") or 0.0)
            cand_acc = float(cand.get("mean_overall_accuracy") or 0.0)
            row[f"{control}_overall_accuracy"] = acc
            row[f"{control}_tail_accuracy"] = ctrl.get("mean_tail_accuracy")
            row[f"{control}_primary_error_auroc"] = ctrl.get("mean_primary_error_auroc")
            row[f"{control}_brier_primary_correct"] = ctrl.get("mean_brier_primary_correct")
            row[f"candidate_accuracy_delta_vs_{control}"] = cand_acc - acc
            if control != "oracle_confidence_upper_bound" and VARIANTS[control].family in {
                "monitor_ablation",
                "sham_monitor",
                "trivial_monitor",
                "frozen_baseline",
            }:
                if acc > best_sham[1]:
                    best_sham = (control, acc)
        row["best_non_oracle_control"] = best_sham[0]
        row["best_non_oracle_accuracy"] = best_sham[1] if best_sham[0] else None
        row["candidate_accuracy_delta_vs_best_non_oracle"] = (
            float(cand.get("mean_overall_accuracy") or 0.0) - best_sham[1] if best_sham[0] else None
        )
        comparisons.append(row)
    return comparisons


def evaluate_criteria(
    *,
    aggregates: list[dict[str, Any]],
    comparisons: list[dict[str, Any]],
    summaries: list[dict[str, Any]],
    tasks: list[str],
    variants: list[str],
    seeds: list[int],
    args: argparse.Namespace,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    expected_runs = len(tasks) * len(variants) * len(seeds)
    observed_runs = len(summaries)
    non_oracle = [s for s in summaries if s["variant"] != "oracle_confidence_upper_bound"]
    outcome_leakage = sum(int(bool(s.get("uses_outcome_in_monitor", False))) for s in non_oracle)
    pre_feedback_failures = sum(int(not bool(s.get("monitor_computed_before_feedback", False))) for s in non_oracle)

    cand_aggs = [row for row in aggregates if row["variant"] == CANDIDATE]
    cand_min_error_auc = min([float(row.get("min_primary_error_auroc") or 0.0) for row in cand_aggs] or [0.0])
    cand_min_hazard_auc = min([float(row.get("min_hazard_detection_auroc") or 0.0) for row in cand_aggs] or [0.0])
    cand_max_brier = max([float(row.get("mean_brier_primary_correct") or 1.0) for row in cand_aggs] or [1.0])
    cand_max_ece = max([float(row.get("mean_ece_primary_correct") or 1.0) for row in cand_aggs] or [1.0])
    cand_min_uncertainty_rise = min([float(row.get("mean_uncertainty_hazard_minus_normal") or 0.0) for row in cand_aggs] or [0.0])
    cand_min_bad_avoid = min([float(row.get("mean_hazard_bad_action_avoidance") or 0.0) for row in cand_aggs] or [0.0])

    baseline_edges = [float(c.get("candidate_accuracy_delta_vs_v2_0_no_monitor") or 0.0) for c in comparisons]
    monitor_only_edges = [float(c.get("candidate_accuracy_delta_vs_monitor_only_no_behavior") or 0.0) for c in comparisons]
    disabled_edges = [float(c.get("candidate_accuracy_delta_vs_confidence_disabled") or 0.0) for c in comparisons]
    random_edges = [float(c.get("candidate_accuracy_delta_vs_random_confidence") or 0.0) for c in comparisons]
    shuffled_edges = [float(c.get("candidate_accuracy_delta_vs_time_shuffled_confidence") or 0.0) for c in comparisons]
    anti_edges = [float(c.get("candidate_accuracy_delta_vs_anti_confidence") or 0.0) for c in comparisons]
    best_edges = [float(c.get("candidate_accuracy_delta_vs_best_non_oracle") or 0.0) for c in comparisons]

    brier_edges = []
    auc_edges = []
    lookup = by_task_variant(aggregates)
    for task in tasks:
        cand = lookup.get((task, CANDIDATE))
        shuffled = lookup.get((task, "time_shuffled_confidence"))
        random = lookup.get((task, "random_confidence"))
        if cand and shuffled:
            brier_edges.append(float(shuffled.get("mean_brier_primary_correct") or 1.0) - float(cand.get("mean_brier_primary_correct") or 1.0))
            auc_edges.append(float(cand.get("mean_primary_error_auroc") or 0.0) - float(shuffled.get("mean_primary_error_auroc") or 0.0))
        if cand and random:
            brier_edges.append(float(random.get("mean_brier_primary_correct") or 1.0) - float(cand.get("mean_brier_primary_correct") or 1.0))
            auc_edges.append(float(cand.get("mean_primary_error_auroc") or 0.0) - float(random.get("mean_primary_error_auroc") or 0.0))

    base = [
        criterion("task/variant/seed matrix completed", observed_runs, "==", expected_runs, observed_runs == expected_runs),
        criterion("frozen v2.0 baseline artifact exists", str(BASELINE_PATH), "exists", True, BASELINE_PATH.exists()),
        criterion("non-oracle monitors do not use outcomes", outcome_leakage, "==", 0, outcome_leakage == 0),
        criterion("monitor values are computed before feedback", pre_feedback_failures, "==", 0, pre_feedback_failures == 0),
    ]
    science = [
        criterion("candidate predicts primary-path future errors", cand_min_error_auc, ">=", args.min_error_auroc, cand_min_error_auc >= float(args.min_error_auroc)),
        criterion("candidate detects hazard/OOD/mismatch state", cand_min_hazard_auc, ">=", args.min_hazard_auroc, cand_min_hazard_auc >= float(args.min_hazard_auroc)),
        criterion("candidate confidence is calibrated by Brier score", cand_max_brier, "<=", args.max_brier, cand_max_brier <= float(args.max_brier)),
        criterion("candidate confidence calibration error is bounded", cand_max_ece, "<=", args.max_ece, cand_max_ece <= float(args.max_ece)),
        criterion("candidate uncertainty rises under hazard", cand_min_uncertainty_rise, ">=", args.min_uncertainty_rise, cand_min_uncertainty_rise >= float(args.min_uncertainty_rise)),
        criterion("candidate avoids bad primary-path actions under detected risk", cand_min_bad_avoid, ">=", args.min_bad_action_avoidance, cand_min_bad_avoid >= float(args.min_bad_action_avoidance)),
        criterion("candidate improves behavior vs v2.0 no-monitor", min(baseline_edges) if baseline_edges else None, ">=", args.min_edge_vs_baseline, bool(baseline_edges) and min(baseline_edges) >= float(args.min_edge_vs_baseline)),
        criterion("monitor must be behaviorally used, not just reported", min(monitor_only_edges) if monitor_only_edges else None, ">=", args.min_edge_vs_monitor_only, bool(monitor_only_edges) and min(monitor_only_edges) >= float(args.min_edge_vs_monitor_only)),
        criterion("confidence-disabled control loses", min(disabled_edges) if disabled_edges else None, ">=", args.min_edge_vs_confidence_disabled, bool(disabled_edges) and min(disabled_edges) >= float(args.min_edge_vs_confidence_disabled)),
        criterion("random-confidence control loses", min(random_edges) if random_edges else None, ">=", args.min_edge_vs_random, bool(random_edges) and min(random_edges) >= float(args.min_edge_vs_random)),
        criterion("time-shuffled confidence control loses", min(shuffled_edges) if shuffled_edges else None, ">=", args.min_edge_vs_shuffled, bool(shuffled_edges) and min(shuffled_edges) >= float(args.min_edge_vs_shuffled)),
        criterion("anti-confidence control loses", min(anti_edges) if anti_edges else None, ">=", args.min_edge_vs_anti, bool(anti_edges) and min(anti_edges) >= float(args.min_edge_vs_anti)),
        criterion("candidate beats best non-oracle control", min(best_edges) if best_edges else None, ">=", args.min_edge_vs_best_non_oracle, bool(best_edges) and min(best_edges) >= float(args.min_edge_vs_best_non_oracle)),
        criterion("candidate calibration beats random/shuffled monitors", min(brier_edges) if brier_edges else None, ">=", args.min_brier_edge_vs_shams, bool(brier_edges) and min(brier_edges) >= float(args.min_brier_edge_vs_shams)),
        criterion("candidate AUROC beats random/shuffled monitors", min(auc_edges) if auc_edges else None, ">=", args.min_auc_edge_vs_shams, bool(auc_edges) and min(auc_edges) >= float(args.min_auc_edge_vs_shams)),
    ]
    criteria = base if args.smoke else base + science
    summary = {
        "expected_runs": expected_runs,
        "observed_runs": observed_runs,
        "tasks": tasks,
        "variants": variants,
        "seeds": seeds,
        "candidate_min_primary_error_auroc": cand_min_error_auc,
        "candidate_min_hazard_detection_auroc": cand_min_hazard_auc,
        "candidate_max_brier_primary_correct": cand_max_brier,
        "candidate_max_ece_primary_correct": cand_max_ece,
        "candidate_min_uncertainty_hazard_minus_normal": cand_min_uncertainty_rise,
        "candidate_min_bad_action_avoidance": cand_min_bad_avoid,
        "outcome_leakage_runs": outcome_leakage,
        "pre_feedback_monitor_failures": pre_feedback_failures,
        "min_accuracy_edge_vs_v2_0": min(baseline_edges) if baseline_edges else None,
        "min_accuracy_edge_vs_monitor_only": min(monitor_only_edges) if monitor_only_edges else None,
        "min_accuracy_edge_vs_best_non_oracle": min(best_edges) if best_edges else None,
        "claim_boundary": "Noncanonical software diagnostic: operational self-evaluation/reliability monitoring over frozen v2.0; not consciousness, self-awareness, hardware evidence, AGI, or a v2.1 freeze.",
    }
    return criteria, summary


def plot_accuracy_edges(path: Path, comparisons: list[dict[str, Any]]) -> None:
    if plt is None:
        path.with_suffix(".txt").write_text(f"matplotlib unavailable: {MATPLOTLIB_ERROR}\n", encoding="utf-8")
        return
    labels = [str(c["task"]).replace("_", "\n") for c in comparisons]
    keys = [
        "candidate_accuracy_delta_vs_v2_0_no_monitor",
        "candidate_accuracy_delta_vs_monitor_only_no_behavior",
        "candidate_accuracy_delta_vs_time_shuffled_confidence",
        "candidate_accuracy_delta_vs_best_non_oracle",
    ]
    x = np.arange(len(labels))
    width = 0.18
    fig, ax = plt.subplots(figsize=(12, 5.8))
    for offset, key in enumerate(keys):
        values = [float(c.get(key) or 0.0) for c in comparisons]
        ax.bar(x + (offset - 1.5) * width, values, width, label=key.replace("candidate_accuracy_delta_vs_", "vs ").replace("_", " "))
    ax.axhline(0.0, color="black", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("accuracy edge")
    ax.set_title("Tier 5.18 candidate behavioral edge")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_monitor_matrix(path: Path, aggregates: list[dict[str, Any]], variants: list[str]) -> None:
    if plt is None:
        path.with_suffix(".txt").write_text(f"matplotlib unavailable: {MATPLOTLIB_ERROR}\n", encoding="utf-8")
        return
    tasks = sorted({str(row["task"]) for row in aggregates})
    lookup = by_task_variant(aggregates)
    data = np.zeros((len(tasks), len(variants)), dtype=float)
    for i, task in enumerate(tasks):
        for j, variant in enumerate(variants):
            data[i, j] = float((lookup.get((task, variant)) or {}).get("mean_primary_error_auroc") or 0.0)
    fig, ax = plt.subplots(figsize=(max(12, len(variants) * 1.1), 5.4))
    im = ax.imshow(data, vmin=0.0, vmax=1.0, cmap="viridis", aspect="auto")
    ax.set_xticks(np.arange(len(variants)))
    ax.set_xticklabels([v.replace("_", "\n") for v in variants], fontsize=7)
    ax.set_yticks(np.arange(len(tasks)))
    ax.set_yticklabels([t.replace("_", " ") for t in tasks])
    ax.set_title("Tier 5.18 pre-feedback primary-error AUROC")
    for i in range(len(tasks)):
        for j in range(len(variants)):
            ax.text(j, i, f"{data[i, j]:.2f}", ha="center", va="center", color="white" if data[i, j] < 0.55 else "black", fontsize=7)
    fig.colorbar(im, ax=ax, label="AUROC")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fairness_contract(args: argparse.Namespace, tasks: list[str], variants: list[str], seeds: list[int]) -> dict[str, Any]:
    return {
        "tier": TIER,
        "generated_at_utc": utc_now(),
        "baseline": str(BASELINE_PATH),
        "claim_boundary": "Software-only operational self-evaluation diagnostic. Non-oracle monitors receive no outcome/reward labels before producing confidence and uncertainty values.",
        "fairness_rules": [
            "Monitor features are generated from pre-feedback primary-path margin, novelty, memory-conflict, prediction-residual, and routing-entropy traces.",
            "The candidate and monitor-only ablation receive identical confidence; only the candidate may use it behaviorally.",
            "Random, time-shuffled, always-on, always-off, and anti-confidence controls test whether the confidence signal is causal rather than incidental.",
            "The oracle confidence upper bound is reported but excluded from no-leakage promotion checks.",
            "Tier 5.18 cannot freeze v2.1 without a later compact regression gate.",
        ],
        "tasks": tasks,
        "variants": variants,
        "seeds": seeds,
        "steps": int(args.steps),
        "smoke": bool(args.smoke),
    }


def write_report(path: Path, result: dict[str, Any], comparisons: list[dict[str, Any]]) -> None:
    lines = [
        "# Tier 5.18 Self-Evaluation / Metacognitive Monitoring Findings",
        "",
        f"- Generated: `{result['generated_at_utc']}`",
        f"- Status: **{result['status'].upper()}**",
        f"- Output directory: `{result['output_dir']}`",
        f"- Tasks: `{', '.join(result['summary']['tasks'])}`",
        f"- Seeds: `{result['summary']['seeds']}`",
        "",
        "Tier 5.18 tests whether a CRA monitor can estimate reliability before feedback and whether using that signal improves behavior under ambiguity, OOD insertion, memory corruption, hidden-regime mismatch, and routing uncertainty.",
        "",
        "## Claim Boundary",
        "",
        "- Noncanonical software diagnostic evidence only.",
        "- Non-oracle monitors do not use outcomes/rewards before emitting confidence or uncertainty.",
        "- This is operational reliability monitoring, not consciousness, self-awareness, introspection, language, planning, AGI, hardware evidence, or a v2.1 freeze.",
        "- A future Tier 5.18c promotion/regression gate is required before any v2.1 baseline lock.",
        "",
        "## Summary",
        "",
        f"- expected_runs: `{result['summary']['expected_runs']}`",
        f"- observed_runs: `{result['summary']['observed_runs']}`",
        f"- candidate_min_primary_error_auroc: `{markdown_value(result['summary']['candidate_min_primary_error_auroc'])}`",
        f"- candidate_min_hazard_detection_auroc: `{markdown_value(result['summary']['candidate_min_hazard_detection_auroc'])}`",
        f"- candidate_max_brier_primary_correct: `{markdown_value(result['summary']['candidate_max_brier_primary_correct'])}`",
        f"- candidate_max_ece_primary_correct: `{markdown_value(result['summary']['candidate_max_ece_primary_correct'])}`",
        f"- candidate_min_uncertainty_hazard_minus_normal: `{markdown_value(result['summary']['candidate_min_uncertainty_hazard_minus_normal'])}`",
        f"- candidate_min_bad_action_avoidance: `{markdown_value(result['summary']['candidate_min_bad_action_avoidance'])}`",
        f"- min_accuracy_edge_vs_v2_0: `{markdown_value(result['summary']['min_accuracy_edge_vs_v2_0'])}`",
        f"- min_accuracy_edge_vs_monitor_only: `{markdown_value(result['summary']['min_accuracy_edge_vs_monitor_only'])}`",
        f"- min_accuracy_edge_vs_best_non_oracle: `{markdown_value(result['summary']['min_accuracy_edge_vs_best_non_oracle'])}`",
        f"- outcome_leakage_runs: `{result['summary']['outcome_leakage_runs']}`",
        f"- pre_feedback_monitor_failures: `{result['summary']['pre_feedback_monitor_failures']}`",
        "",
        "## Comparisons",
        "",
        "| Task | Candidate acc | v2.0 acc | Monitor-only acc | Random acc | Shuffled acc | Best non-oracle edge | Error AUROC | Hazard AUROC |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in comparisons:
        lines.append(
            "| {task} | {cand} | {base} | {mon} | {rand} | {shuf} | {best} | {err_auc} | {haz_auc} |".format(
                task=markdown_value(row.get("task")),
                cand=markdown_value(row.get("candidate_overall_accuracy")),
                base=markdown_value(row.get("v2_0_no_monitor_overall_accuracy")),
                mon=markdown_value(row.get("monitor_only_no_behavior_overall_accuracy")),
                rand=markdown_value(row.get("random_confidence_overall_accuracy")),
                shuf=markdown_value(row.get("time_shuffled_confidence_overall_accuracy")),
                best=markdown_value(row.get("candidate_accuracy_delta_vs_best_non_oracle")),
                err_auc=markdown_value(row.get("candidate_primary_error_auroc")),
                haz_auc=markdown_value(row.get("candidate_hazard_detection_auroc")),
            )
        )
    lines.extend(["", "## Criteria", "", "| Criterion | Value | Rule | Pass | Note |", "| --- | --- | --- | --- | --- |"])
    for item in result["criteria"]:
        op = item.get("operator", item.get("op", ""))
        threshold = item.get("threshold", "")
        rule = f"{op} {markdown_value(threshold)}".strip()
        lines.append(
            f"| {item['name']} | `{markdown_value(item['value'])}` | `{rule}` | {'yes' if item['passed'] else 'no'} | {item.get('note', '')} |"
        )
    lines.extend(
        [
            "",
            "## Artifacts",
            "",
        ]
    )
    for key, value in result["artifacts"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=TIER)
    parser.add_argument("--tasks", default=DEFAULT_TASKS)
    parser.add_argument("--variants", default=DEFAULT_VARIANTS)
    parser.add_argument("--steps", type=int, default=720)
    parser.add_argument("--seed-count", type=int, default=3)
    parser.add_argument("--seeds", default="")
    parser.add_argument("--base-seed", type=int, default=42)
    parser.add_argument("--task-seed", type=int, default=91800)
    parser.add_argument("--gating-uncertainty-threshold", type=float, default=0.40)
    parser.add_argument("--min-error-auroc", type=float, default=0.78)
    parser.add_argument("--min-hazard-auroc", type=float, default=0.78)
    parser.add_argument("--max-brier", type=float, default=0.20)
    parser.add_argument("--max-ece", type=float, default=0.16)
    parser.add_argument("--min-uncertainty-rise", type=float, default=0.20)
    parser.add_argument("--min-bad-action-avoidance", type=float, default=0.70)
    parser.add_argument("--min-edge-vs-baseline", type=float, default=0.06)
    parser.add_argument("--min-edge-vs-monitor-only", type=float, default=0.06)
    parser.add_argument("--min-edge-vs-confidence-disabled", type=float, default=0.06)
    parser.add_argument("--min-edge-vs-random", type=float, default=0.03)
    parser.add_argument("--min-edge-vs-shuffled", type=float, default=0.03)
    parser.add_argument("--min-edge-vs-anti", type=float, default=0.08)
    parser.add_argument("--min-edge-vs-best-non-oracle", type=float, default=0.02)
    parser.add_argument("--min-brier-edge-vs-shams", type=float, default=0.04)
    parser.add_argument("--min-auc-edge-vs-shams", type=float, default=0.12)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--stop-on-fail", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.smoke:
        args.tasks = "ambiguous_cue,memory_corruption"
        args.variants = "v2_0_no_monitor,self_eval_gated,monitor_only_no_behavior,random_confidence,time_shuffled_confidence,oracle_confidence_upper_bound"
        args.steps = min(int(args.steps), 240)
        args.seed_count = 1
        args.seeds = ""

    tasks = selected_tasks(args)
    variants = selected_variants(args)
    seeds = seeds_from_args(args)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_dir = args.output_dir or (ROOT / "controlled_test_output" / f"tier5_18_{stamp}")
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    started = time.perf_counter()
    all_rows: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    artifacts: dict[str, str] = {}

    for seed in seeds:
        for task_name in tasks:
            task = make_task(task_name, steps=int(args.steps), seed=int(args.task_seed + seed), args=args)
            for variant in variants:
                print(f"[tier5.18] task={task_name} variant={variant} seed={seed}", flush=True)
                rows, summary = run_variant(task, variant, seed=seed, args=args)
                all_rows.extend(rows)
                summaries.append(summary)
                if seed == seeds[0] and variant in {CANDIDATE, "v2_0_no_monitor", "time_shuffled_confidence"}:
                    csv_path = output_dir / f"{task_name}_{variant}_seed{seed}_timeseries.csv"
                    write_csv(csv_path, rows)
                    artifacts[f"{task_name}_{variant}_seed{seed}_timeseries_csv"] = str(csv_path)

    aggregates = aggregate(summaries)
    comparisons = build_comparisons(aggregates)
    criteria, summary = evaluate_criteria(
        aggregates=aggregates,
        comparisons=comparisons,
        summaries=summaries,
        tasks=tasks,
        variants=variants,
        seeds=seeds,
        args=args,
    )
    status, failure_reason = pass_fail(criteria)
    runtime_seconds = time.perf_counter() - started
    summary["runtime_seconds"] = runtime_seconds
    summary["smoke"] = bool(args.smoke)

    results_json = output_dir / "tier5_18_results.json"
    summary_csv = output_dir / "tier5_18_summary.csv"
    aggregate_csv = output_dir / "tier5_18_aggregates.csv"
    comparisons_csv = output_dir / "tier5_18_comparisons.csv"
    fairness_json = output_dir / "tier5_18_fairness_contract.json"
    report_md = output_dir / "tier5_18_report.md"
    edge_png = output_dir / "tier5_18_accuracy_edges.png"
    monitor_png = output_dir / "tier5_18_monitor_auroc_matrix.png"

    write_csv(summary_csv, summaries)
    write_csv(aggregate_csv, aggregates)
    write_csv(comparisons_csv, comparisons)
    write_json(fairness_json, fairness_contract(args, tasks, variants, seeds))
    plot_accuracy_edges(edge_png, comparisons)
    plot_monitor_matrix(monitor_png, aggregates, variants)
    artifacts.update(
        {
            "summary_csv": str(summary_csv),
            "aggregates_csv": str(aggregate_csv),
            "comparisons_csv": str(comparisons_csv),
            "fairness_contract_json": str(fairness_json),
            "accuracy_edges_png": str(edge_png),
            "monitor_auroc_matrix_png": str(monitor_png),
        }
    )
    result = {
        "tier": TIER,
        "generated_at_utc": utc_now(),
        "status": status,
        "failure_reason": failure_reason,
        "output_dir": str(output_dir),
        "baseline": str(BASELINE_PATH),
        "criteria": criteria,
        "summary": summary,
        "comparisons": comparisons,
        "aggregates": aggregates,
        "artifacts": artifacts,
        "claim_boundary": summary["claim_boundary"],
    }
    write_json(results_json, result)
    artifacts["results_json"] = str(results_json)
    write_report(report_md, result, comparisons)
    artifacts["report_md"] = str(report_md)
    write_json(results_json, {**result, "artifacts": artifacts})
    latest = ROOT / "controlled_test_output" / "tier5_18_latest_manifest.json"
    write_json(latest, {**result, "artifacts": artifacts})

    print(
        json.dumps(
            {
                "tier": TIER,
                "status": status,
                "failure_reason": failure_reason,
                "output_dir": str(output_dir),
                "report": str(report_md),
                "runtime_seconds": runtime_seconds,
                "claim_boundary": summary["claim_boundary"],
            },
            indent=2,
        )
    )
    if status != "pass" and args.stop_on_fail:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
