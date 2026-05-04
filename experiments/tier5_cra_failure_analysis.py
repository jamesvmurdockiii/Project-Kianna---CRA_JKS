#!/usr/bin/env python3
"""Tier 5.3 CRA failure analysis / learning dynamics debug.

Tier 5.2 showed that CRA's comparative edge did not strengthen at longer run
lengths. Tier 5.3 is diagnostic: it runs CRA-only mechanism/tuning variants on
the failing tasks and compares them against the already-recorded Tier 5.2
external baseline reference. A pass here means the diagnostic matrix completed
and produced an honest interpretation; it does not require CRA to recover a
competitive advantage.
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
from typing import Any

import numpy as np

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except Exception as exc:  # pragma: no cover
    plt = None
    MATPLOTLIB_ERROR = str(exc)
else:
    MATPLOTLIB_ERROR = None

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from coral_reef_spinnaker import Observation, Organism, ReefConfig, SensorControlAdapter  # noqa: E402
from tier2_learning import (  # noqa: E402
    DEFAULT_AMPLITUDE,
    DEFAULT_DT_SECONDS,
    criterion,
    end_backend,
    load_backend,
    markdown_value,
    pass_fail,
    setup_backend,
    strict_sign,
    write_csv,
    write_json,
)
from tier4_scaling import mean, min_value, seeds_from_args, stdev  # noqa: E402
from tier5_external_baselines import (  # noqa: E402
    TaskStream,
    TestResult,
    build_parser as build_tier5_1_parser,
    build_tasks,
    recovery_steps,
    summarize_rows,
)


TIER = "Tier 5.3 - CRA Failure Analysis / Learning Dynamics Debug"
DEFAULT_TASKS = "delayed_cue,hard_noisy_switching"
DEFAULT_VARIANTS = "core"
DEFAULT_REFERENCE = ROOT / "controlled_test_output" / "tier5_2_20260426_234500" / "tier5_2_comparisons.csv"
EPS = 1e-12


@dataclass(frozen=True)
class VariantSpec:
    name: str
    group: str
    hypothesis: str
    overrides: dict[str, Any]


CORE_VARIANTS: tuple[VariantSpec, ...] = (
    VariantSpec(
        "baseline_current",
        "control",
        "Current Tier 5.2 CRA configuration at the diagnostic run length.",
        {},
    ),
    VariantSpec(
        "readout_lr_0_20",
        "readout_lr",
        "If the immediate/local readout is adapting too slowly, a higher readout LR should improve tail accuracy.",
        {"learning.readout_learning_rate": 0.20},
    ),
    VariantSpec(
        "readout_lr_0_35",
        "readout_lr",
        "Stronger immediate readout update; tests whether faster adaptation helps or destabilizes.",
        {"learning.readout_learning_rate": 0.35},
    ),
    VariantSpec(
        "delayed_lr_0_10",
        "delayed_credit_lr",
        "If delayed credit is too weak, doubling matured-credit LR should help delayed tasks.",
        {"learning.delayed_readout_learning_rate": 0.10},
    ),
    VariantSpec(
        "delayed_lr_0_20",
        "delayed_credit_lr",
        "Strong delayed-credit update; tests whether the delayed path is underpowered.",
        {"learning.delayed_readout_learning_rate": 0.20},
    ),
    VariantSpec(
        "horizon_3",
        "eligibility_horizon",
        "Shorter eligibility horizon; tests whether delayed consequences are arriving too late for hard switching.",
        {"learning.evaluation_horizon_bars": 3},
    ),
    VariantSpec(
        "horizon_8",
        "eligibility_horizon",
        "Longer eligibility horizon; tests whether the credit window is too short/noisy.",
        {"learning.evaluation_horizon_bars": 8},
    ),
    VariantSpec(
        "dopamine_tau_25",
        "dopamine_smoothing",
        "Faster dopamine EMA; tests whether reward smoothing is washing out switches.",
        {"learning.dopamine_tau": 25.0},
    ),
    VariantSpec(
        "dopamine_tau_250",
        "dopamine_smoothing",
        "Slower dopamine EMA; tests whether more smoothing stabilizes noisy credit.",
        {"learning.dopamine_tau": 250.0},
    ),
    VariantSpec(
        "negative_surprise_6",
        "switch_adaptation",
        "Increase punishment for wrong signed actions; tests whether old specialists persist too long.",
        {"learning.readout_negative_surprise_multiplier": 6.0},
    ),
    VariantSpec(
        "readout_decay_zero",
        "plasticity_retention",
        "Remove readout shrinkage; tests whether long-run decay erases useful specialists.",
        {"learning.readout_weight_decay": 0.0},
    ),
    VariantSpec(
        "population_16_fixed",
        "population_diversity",
        "More fixed polyps; tests whether diversity/capacity is the bottleneck without lifecycle churn.",
        {
            "lifecycle.initial_population": 16,
            "lifecycle.max_population_hard": 16,
            "lifecycle.enable_reproduction": False,
            "lifecycle.enable_apoptosis": False,
        },
    ),
    VariantSpec(
        "ecology_fast_replacement",
        "ecology_replacement",
        "Turn lifecycle back on with faster replacement; tests whether stale specialists need birth/death pressure.",
        {
            "lifecycle.initial_population": 8,
            "lifecycle.max_population_hard": 16,
            "lifecycle.enable_reproduction": True,
            "lifecycle.enable_apoptosis": True,
            "lifecycle.reproduction_cooldown_steps": 3,
            "lifecycle.maturity_age_estimate_steps": 10,
            "lifecycle.max_children_per_step": 2,
            "energy.accuracy_survival_floor": 0.52,
            "energy.accuracy_penalty_multiplier": 0.35,
        },
    ),
)

EXTENDED_VARIANTS: tuple[VariantSpec, ...] = CORE_VARIANTS + (
    VariantSpec(
        "horizon_4",
        "eligibility_horizon",
        "Intermediate eligibility horizon for variable-delay hard switching.",
        {"learning.evaluation_horizon_bars": 4},
    ),
    VariantSpec(
        "horizon_12",
        "eligibility_horizon",
        "Long eligibility horizon stress test; may help noisy delayed credit or smear it further.",
        {"learning.evaluation_horizon_bars": 12},
    ),
    VariantSpec(
        "delayed_lr_0_35",
        "delayed_credit_lr",
        "Very strong matured-credit update; tests overshoot versus underpowered delayed credit.",
        {"learning.delayed_readout_learning_rate": 0.35},
    ),
    VariantSpec(
        "no_dopamine_readout_gate",
        "dopamine_gate",
        "Diagnostic only: allow readout updates without nonzero dopamine gate to test whether gating blocks learning.",
        {"learning.readout_requires_dopamine": False},
    ),
    VariantSpec(
        "wta_base_5",
        "population_diversity",
        "More readout winners; tests whether WTA is too narrow and loses useful minority specialists.",
        {"learning.winner_take_all_base": 5},
    ),
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


def set_nested_attr(obj: Any, dotted: str, value: Any) -> None:
    target = obj
    parts = dotted.split(".")
    for part in parts[:-1]:
        target = getattr(target, part)
    setattr(target, parts[-1], value)


def parse_variants(raw: str) -> list[VariantSpec]:
    raw = raw.strip()
    if raw in {"core", "default", ""}:
        return list(CORE_VARIANTS)
    if raw in {"extended", "all"}:
        return list(EXTENDED_VARIANTS)
    by_name = {variant.name: variant for variant in EXTENDED_VARIANTS}
    names = [item.strip() for item in raw.split(",") if item.strip()]
    missing = [name for name in names if name not in by_name]
    if missing:
        raise argparse.ArgumentTypeError(f"unknown variants: {', '.join(missing)}")
    ordered: list[VariantSpec] = []
    for name in names:
        variant = by_name[name]
        if variant not in ordered:
            ordered.append(variant)
    return ordered


def computed_horizon(task: TaskStream) -> int:
    due = task.feedback_due_step - np.arange(task.steps)
    if np.any(task.feedback_due_step >= 0):
        return int(max(1, np.max(due[task.feedback_due_step >= 0])))
    return 1


def make_config(*, seed: int, task: TaskStream, variant: VariantSpec, args: argparse.Namespace) -> ReefConfig:
    cfg = ReefConfig.default()
    cfg.seed = int(seed)
    cfg.lifecycle.initial_population = int(args.cra_population_size)
    cfg.lifecycle.max_population_from_memory = False
    cfg.lifecycle.max_population_hard = int(args.cra_population_size)
    cfg.lifecycle.enable_reproduction = False
    cfg.lifecycle.enable_apoptosis = False
    cfg.lifecycle.enable_structural_plasticity = True
    cfg.measurement.stream_history_maxlen = max(task.steps + 16, 128)
    cfg.spinnaker.sync_interval_steps = 0
    cfg.spinnaker.runtime_ms_per_step = 1000.0
    cfg.learning.evaluation_horizon_bars = computed_horizon(task)
    cfg.learning.readout_learning_rate = float(args.cra_readout_lr)
    cfg.learning.delayed_readout_learning_rate = float(args.cra_delayed_readout_lr)
    for key, value in variant.overrides.items():
        set_nested_attr(cfg, key, value)
    cfg.lifecycle.max_population_from_memory = False
    if cfg.lifecycle.max_population_hard < cfg.lifecycle.initial_population:
        cfg.lifecycle.max_population_hard = cfg.lifecycle.initial_population
    return cfg


def run_cra_variant(task: TaskStream, *, seed: int, variant: VariantSpec, args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    random.seed(seed)
    np.random.seed(seed)
    sim, backend_name = load_backend(args.backend)
    setup_backend(sim, backend_name)
    cfg = make_config(seed=seed, task=task, variant=variant, args=args)
    organism = Organism(cfg, sim, use_default_trading_bridge=(task.domain != "sensor_control"))
    adapter = SensorControlAdapter()
    rows: list[dict[str, Any]] = []
    started = time.perf_counter()
    try:
        organism.initialize(stream_keys=[task.domain])
        bridge_present_after_init = bool(organism.trading_bridge is not None)
        for step in range(task.steps):
            sensory_value = float(task.sensory[step])
            target_value = float(task.current_target[step])
            if task.domain == "sensor_control":
                observation = Observation(
                    stream_id=task.domain,
                    x=np.asarray([sensory_value], dtype=float),
                    target=target_value,
                    metadata={"task": task.name, "step": step, "tier": "5.3"},
                )
                metrics = organism.train_adapter_step(adapter, observation, dt_seconds=args.dt_seconds)
            else:
                metrics = organism.train_step(
                    market_return_1m=target_value,
                    sensory_return_1m=sensory_value,
                    dt_seconds=args.dt_seconds,
                )
            prediction = float(metrics.colony_prediction)
            eval_sign = strict_sign(float(task.evaluation_target[step]))
            pred_sign = strict_sign(prediction)
            row = metrics.to_dict()
            row.update(
                {
                    "task": task.name,
                    "variant": variant.name,
                    "variant_group": variant.group,
                    "model": "cra",
                    "backend": backend_name,
                    "seed": int(seed),
                    "step": int(step),
                    "sensory_return_1m": sensory_value,
                    "target_return_1m": target_value,
                    "target_signal_horizon": float(task.evaluation_target[step]),
                    "target_signal_sign": eval_sign,
                    "target_signal_nonzero": bool(task.evaluation_mask[step] and eval_sign != 0),
                    "prediction_sign": pred_sign,
                    "strict_direction_correct": bool(task.evaluation_mask[step] and pred_sign != 0 and pred_sign == eval_sign),
                    "feedback_due_step": int(task.feedback_due_step[step]),
                    "configured_horizon_bars": int(cfg.learning.evaluation_horizon_bars),
                    "configured_readout_lr": float(cfg.learning.readout_learning_rate),
                    "configured_delayed_readout_lr": float(cfg.learning.delayed_readout_learning_rate),
                    "configured_dopamine_tau": float(cfg.learning.dopamine_tau),
                    "configured_readout_weight_decay": float(cfg.learning.readout_weight_decay),
                    "configured_negative_surprise_multiplier": float(cfg.learning.readout_negative_surprise_multiplier),
                    "configured_initial_population": int(cfg.lifecycle.initial_population),
                    "configured_max_population": int(cfg.lifecycle.max_population_hard),
                    "configured_reproduction": bool(cfg.lifecycle.enable_reproduction),
                    "configured_apoptosis": bool(cfg.lifecycle.enable_apoptosis),
                    "trading_bridge_present_after_init": bridge_present_after_init,
                    "trading_bridge_present_after_step": bool(organism.trading_bridge is not None),
                }
            )
            rows.append(row)
    finally:
        organism.shutdown()
        end_backend(sim)
    summary = summarize_rows(rows)
    summary.update(
        {
            "task": task.name,
            "variant": variant.name,
            "variant_group": variant.group,
            "hypothesis": variant.hypothesis,
            "backend": backend_name,
            "seed": int(seed),
            "steps": task.steps,
            "runtime_seconds": time.perf_counter() - started,
            "configured_horizon_bars": int(cfg.learning.evaluation_horizon_bars),
            "configured_readout_lr": float(cfg.learning.readout_learning_rate),
            "configured_delayed_readout_lr": float(cfg.learning.delayed_readout_learning_rate),
            "configured_dopamine_tau": float(cfg.learning.dopamine_tau),
            "configured_readout_weight_decay": float(cfg.learning.readout_weight_decay),
            "configured_negative_surprise_multiplier": float(cfg.learning.readout_negative_surprise_multiplier),
            "configured_initial_population": int(cfg.lifecycle.initial_population),
            "configured_max_population": int(cfg.lifecycle.max_population_hard),
            "configured_reproduction": bool(cfg.lifecycle.enable_reproduction),
            "configured_apoptosis": bool(cfg.lifecycle.enable_apoptosis),
            "uses_trading_bridge": task.domain != "sensor_control",
            "trading_bridge_present_after_init": bool(rows[0]["trading_bridge_present_after_init"]) if rows else None,
            "trading_bridge_present_any_step": bool(any(bool(r["trading_bridge_present_after_step"]) for r in rows)),
            "task_metadata": task.metadata,
            "config_overrides": variant.overrides,
        }
    )
    return rows, summary


def aggregate_variant(
    task: TaskStream,
    variant: VariantSpec,
    summaries: list[dict[str, Any]],
    rows_by_seed: dict[int, list[dict[str, Any]]],
    tasks_by_seed: dict[int, TaskStream],
    args: argparse.Namespace,
) -> dict[str, Any]:
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
        "max_abs_prediction",
        "final_n_alive",
        "total_births",
        "total_deaths",
        "max_abs_dopamine",
        "mean_abs_dopamine",
        "configured_horizon_bars",
        "configured_readout_lr",
        "configured_delayed_readout_lr",
        "configured_dopamine_tau",
        "configured_initial_population",
        "configured_max_population",
    ]
    aggregate: dict[str, Any] = {
        "task": task.name,
        "display_name": task.display_name,
        "domain": task.domain,
        "variant": variant.name,
        "variant_group": variant.group,
        "hypothesis": variant.hypothesis,
        "runs": len(summaries),
        "seeds": [s.get("seed") for s in summaries],
        "steps": task.steps,
    }
    for key in keys:
        vals = [s.get(key) for s in summaries]
        aggregate[f"{key}_mean"] = mean(vals)
        aggregate[f"{key}_std"] = stdev(vals)
        aggregate[f"{key}_min"] = min_value(vals)
        valid = [float(v) for v in vals if v is not None]
        aggregate[f"{key}_max"] = max(valid) if valid else None
    if any(seed_task.switch_steps for seed_task in tasks_by_seed.values()):
        per_seed_recovery = []
        for seed, rows in rows_by_seed.items():
            seed_task = tasks_by_seed.get(seed, task)
            if not seed_task.switch_steps:
                continue
            per_seed_recovery.extend(
                recovery_steps(
                    rows,
                    seed_task.switch_steps,
                    window_trials=args.recovery_window_trials,
                    threshold=args.recovery_accuracy_threshold,
                    steps=seed_task.steps,
                )
            )
        aggregate["mean_recovery_steps"] = mean(per_seed_recovery)
        aggregate["max_recovery_steps"] = max(per_seed_recovery) if per_seed_recovery else None
    else:
        aggregate["mean_recovery_steps"] = None
        aggregate["max_recovery_steps"] = None
    return aggregate


def load_reference(path: Path, steps: int) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    reference: dict[str, dict[str, Any]] = {}
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                row_steps = int(float(row.get("run_length_steps") or 0))
            except ValueError:
                continue
            if row_steps != int(steps):
                continue
            task = row.get("task") or ""
            reference[task] = {k: parse_float_or_str(v) for k, v in row.items()}
    return reference


def parse_float_or_str(value: str) -> Any:
    if value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return value


def build_comparisons(aggregates: list[dict[str, Any]], reference: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    by_task_baseline = {
        a["task"]: a
        for a in aggregates
        if a["variant"] == "baseline_current"
    }
    rows: list[dict[str, Any]] = []
    for agg in aggregates:
        ref = reference.get(agg["task"], {})
        baseline = by_task_baseline.get(agg["task"], {})
        variant_tail = float(agg.get("tail_accuracy_mean") or 0.0)
        baseline_tail = float(baseline.get("tail_accuracy_mean") or 0.0)
        variant_corr = abs(float(agg.get("prediction_target_corr_mean") or 0.0))
        baseline_corr = abs(float(baseline.get("prediction_target_corr_mean") or 0.0))
        ref_median_tail = ref.get("external_median_tail_accuracy")
        ref_best_tail = ref.get("best_external_tail_accuracy_mean")
        ref_median_corr = ref.get("external_median_abs_corr")
        ref_best_corr = ref.get("best_external_abs_corr_mean")
        row = {
            "task": agg["task"],
            "variant": agg["variant"],
            "variant_group": agg["variant_group"],
            "hypothesis": agg["hypothesis"],
            "steps": agg["steps"],
            "cra_tail_accuracy_mean": agg.get("tail_accuracy_mean"),
            "baseline_cra_tail_accuracy_mean": baseline.get("tail_accuracy_mean"),
            "tail_delta_vs_current_cra": variant_tail - baseline_tail,
            "prediction_target_abs_corr_mean": variant_corr,
            "baseline_cra_abs_corr_mean": baseline_corr,
            "abs_corr_delta_vs_current_cra": variant_corr - baseline_corr,
            "mean_recovery_steps": agg.get("mean_recovery_steps"),
            "baseline_mean_recovery_steps": baseline.get("mean_recovery_steps"),
            "recovery_delta_vs_current_cra": (
                None
                if agg.get("mean_recovery_steps") is None or baseline.get("mean_recovery_steps") is None
                else float(baseline["mean_recovery_steps"]) - float(agg["mean_recovery_steps"])
            ),
            "external_median_tail_accuracy_reference": ref_median_tail,
            "best_external_tail_accuracy_reference": ref_best_tail,
            "best_external_tail_model_reference": ref.get("best_external_tail_model"),
            "external_median_abs_corr_reference": ref_median_corr,
            "best_external_abs_corr_reference": ref_best_corr,
            "tail_delta_vs_external_median": None if ref_median_tail is None else variant_tail - float(ref_median_tail),
            "tail_delta_vs_best_external": None if ref_best_tail is None else variant_tail - float(ref_best_tail),
            "abs_corr_delta_vs_external_median": None if ref_median_corr is None else variant_corr - float(ref_median_corr),
            "abs_corr_delta_vs_best_external": None if ref_best_corr is None else variant_corr - float(ref_best_corr),
            "runtime_seconds_mean": agg.get("runtime_seconds_mean"),
            "final_n_alive_mean": agg.get("final_n_alive_mean"),
            "total_births_mean": agg.get("total_births_mean"),
            "total_deaths_mean": agg.get("total_deaths_mean"),
            "configured_horizon_bars_mean": agg.get("configured_horizon_bars_mean"),
            "configured_readout_lr_mean": agg.get("configured_readout_lr_mean"),
            "configured_delayed_readout_lr_mean": agg.get("configured_delayed_readout_lr_mean"),
            "configured_dopamine_tau_mean": agg.get("configured_dopamine_tau_mean"),
            "configured_initial_population_mean": agg.get("configured_initial_population_mean"),
        }
        rows.append(row)
    return rows


def best_by_task(comparisons: list[dict[str, Any]]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for task in sorted({row["task"] for row in comparisons}):
        rows = [row for row in comparisons if row["task"] == task]
        if not rows:
            continue
        best_tail = max(rows, key=lambda row: float(row.get("cra_tail_accuracy_mean") or 0.0))
        best_improvement = max(rows, key=lambda row: float(row.get("tail_delta_vs_current_cra") or 0.0))
        best_corr = max(rows, key=lambda row: float(row.get("prediction_target_abs_corr_mean") or 0.0))
        recovery_rows = [row for row in rows if row.get("mean_recovery_steps") not in (None, "")]
        best_recovery = min(recovery_rows, key=lambda row: float(row.get("mean_recovery_steps") or 1e9)) if recovery_rows else None
        external_median = best_tail.get("external_median_tail_accuracy_reference")
        recovered_vs_median = (
            False
            if external_median is None
            else float(best_tail.get("cra_tail_accuracy_mean") or 0.0) >= float(external_median)
        )
        if task == "delayed_cue":
            if best_improvement["variant_group"] == "delayed_credit_lr":
                likely = "delayed credit is underpowered"
            elif best_improvement["variant_group"] == "eligibility_horizon":
                likely = "eligibility horizon is misaligned"
            elif best_improvement["variant_group"] == "readout_lr":
                likely = "readout adaptation speed matters"
            else:
                likely = "no single tested mechanism clearly explains delayed-cue weakness"
        elif task == "hard_noisy_switching":
            best_external_delta = best_tail.get("tail_delta_vs_best_external")
            beats_best_external = (
                best_external_delta is not None
                and float(best_external_delta) >= 0.0
            )
            if best_improvement["variant_group"] == "delayed_credit_lr" and not beats_best_external:
                likely = "delayed credit improves hard-switch tail accuracy, but the best external baseline still leads"
            elif best_improvement["variant_group"] == "delayed_credit_lr":
                likely = "delayed credit is underpowered and restores hard-switch competitiveness"
            elif best_recovery and best_recovery.get("variant_group") == "ecology_replacement":
                likely = "replacement pressure helps switch recovery"
            elif best_improvement["variant_group"] == "switch_adaptation":
                likely = "old readout specialists need stronger negative surprise"
            elif best_improvement["variant_group"] == "dopamine_smoothing":
                likely = "dopamine smoothing affects switch adaptation"
            elif best_improvement["variant_group"] == "eligibility_horizon":
                likely = "credit window interacts with variable delay"
            else:
                likely = "no single tested mechanism restores hard-switch advantage"
        else:
            likely = "sensor_control is treated as saturated/easy, not an advantage task"
        findings.append(
            {
                "task": task,
                "best_tail_variant": best_tail["variant"],
                "best_tail_accuracy_mean": best_tail.get("cra_tail_accuracy_mean"),
                "best_tail_delta_vs_current_cra": best_tail.get("tail_delta_vs_current_cra"),
                "best_tail_delta_vs_external_median": best_tail.get("tail_delta_vs_external_median"),
                "best_improvement_variant": best_improvement["variant"],
                "best_improvement_group": best_improvement["variant_group"],
                "best_improvement_tail_delta": best_improvement.get("tail_delta_vs_current_cra"),
                "best_corr_variant": best_corr["variant"],
                "best_abs_corr_mean": best_corr.get("prediction_target_abs_corr_mean"),
                "best_recovery_variant": None if best_recovery is None else best_recovery["variant"],
                "best_recovery_steps": None if best_recovery is None else best_recovery.get("mean_recovery_steps"),
                "recovered_vs_external_median_tail": recovered_vs_median,
                "likely_diagnosis": likely,
            }
        )
    return findings


def evaluate_tier(*, aggregates: list[dict[str, Any]], comparisons: list[dict[str, Any]], findings: list[dict[str, Any]], variants: list[VariantSpec], args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    tasks = [item.strip() for item in args.tasks.split(",") if item.strip()]
    seeds = seeds_from_args(args)
    expected_runs = len(tasks) * len(seeds) * len(variants)
    observed_runs = sum(int(a.get("runs", 0)) for a in aggregates)
    expected_cells = len(tasks) * len(variants)
    observed_cells = len(aggregates)
    recovered_tasks = [row["task"] for row in findings if row.get("recovered_vs_external_median_tail")]
    improvement_tasks = [
        row["task"]
        for row in findings
        if float(row.get("best_improvement_tail_delta") or 0.0) >= args.meaningful_tail_delta
    ]
    sensor_removed = "sensor_control" not in tasks
    summary = {
        "expected_runs": expected_runs,
        "observed_runs": observed_runs,
        "expected_cells": expected_cells,
        "observed_cells": observed_cells,
        "tasks": tasks,
        "seeds": seeds,
        "variants": [v.name for v in variants],
        "variant_count": len(variants),
        "backend": args.backend,
        "steps": args.steps,
        "recovered_tasks_vs_external_median_tail": recovered_tasks,
        "meaningfully_improved_tasks_vs_current_cra": improvement_tasks,
        "sensor_control_removed_from_advantage_claims": sensor_removed,
        "claim_boundary": "Controlled CRA failure-analysis/tuning evidence only; not hardware evidence and not proof of competitive recovery unless recovered_tasks is non-empty.",
    }
    criteria = [
        criterion("full CRA diagnostic matrix completed", observed_runs, "==", expected_runs, observed_runs == expected_runs),
        criterion("all aggregate diagnostic cells produced", observed_cells, "==", expected_cells, observed_cells == expected_cells),
        criterion("task-level diagnoses produced", len(findings), "==", len(tasks), len(findings) == len(tasks)),
        criterion("sensor_control removed from advantage probe", sensor_removed, "==", True, sensor_removed, "Tier 5.2 saturated sensor_control, so Tier 5.3 should not use it as a CRA advantage task."),
        criterion("comparison rows generated", len(comparisons), "==", expected_cells, len(comparisons) == expected_cells),
    ]
    return criteria, summary


def plot_variant_matrix(comparisons: list[dict[str, Any]], path: Path) -> None:
    if plt is None or not comparisons:
        return
    tasks = sorted({row["task"] for row in comparisons})
    variants = [row["variant"] for row in comparisons if row["task"] == tasks[0]] if tasks else []
    data = np.zeros((len(tasks), len(variants)), dtype=float)
    edges = np.zeros_like(data)
    for i, task in enumerate(tasks):
        for j, variant in enumerate(variants):
            row = next((r for r in comparisons if r["task"] == task and r["variant"] == variant), None)
            if row:
                data[i, j] = float(row.get("cra_tail_accuracy_mean") or 0.0)
                edges[i, j] = float(row.get("tail_delta_vs_current_cra") or 0.0)
    fig, axes = plt.subplots(1, 2, figsize=(max(14, len(variants) * 0.9), 5))
    fig.suptitle("Tier 5.3 CRA Diagnostic Variants", fontsize=14, fontweight="bold")
    for ax, values, title, cmap, vmin, vmax in [
        (axes[0], data, "tail accuracy", "viridis", 0.0, 1.0),
        (axes[1], edges, "tail delta vs current CRA", "coolwarm", -0.25, 0.25),
    ]:
        im = ax.imshow(values, cmap=cmap, vmin=vmin, vmax=vmax)
        ax.set_title(title)
        ax.set_xticks(range(len(variants)))
        ax.set_xticklabels([v.replace("_", "\n") for v in variants], fontsize=7)
        ax.set_yticks(range(len(tasks)))
        ax.set_yticklabels([t.replace("_", "\n") for t in tasks], fontsize=9)
        for i in range(len(tasks)):
            for j in range(len(variants)):
                ax.text(j, i, f"{values[i, j]:.2f}", ha="center", va="center", fontsize=7, color="white" if abs(values[i, j]) < 0.45 else "black")
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_group_effects(comparisons: list[dict[str, Any]], path: Path) -> None:
    if plt is None or not comparisons:
        return
    rows = [row for row in comparisons if row["variant"] != "baseline_current"]
    groups = sorted({row["variant_group"] for row in rows})
    tasks = sorted({row["task"] for row in rows})
    x = np.arange(len(groups))
    width = 0.8 / max(1, len(tasks))
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.axhline(0.0, color="black", lw=0.8)
    for idx, task in enumerate(tasks):
        vals = []
        for group in groups:
            group_vals = [float(row.get("tail_delta_vs_current_cra") or 0.0) for row in rows if row["task"] == task and row["variant_group"] == group]
            vals.append(max(group_vals) if group_vals else 0.0)
        ax.bar(x + (idx - (len(tasks) - 1) / 2) * width, vals, width, label=task.replace("_", " "))
    ax.set_title("Best Tail-Accuracy Improvement By Mechanism Group")
    ax.set_xticks(x)
    ax.set_xticklabels([g.replace("_", "\n") for g in groups], fontsize=8)
    ax.set_ylabel("positive means better than current CRA")
    ax.grid(axis="y", alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def aggregate_csv_rows(aggregates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fields = [
        "task",
        "variant",
        "variant_group",
        "runs",
        "steps",
        "tail_accuracy_mean",
        "tail_accuracy_std",
        "all_accuracy_mean",
        "prediction_target_corr_mean",
        "tail_prediction_target_corr_mean",
        "mean_recovery_steps",
        "runtime_seconds_mean",
        "final_n_alive_mean",
        "total_births_mean",
        "total_deaths_mean",
        "max_abs_dopamine_mean",
        "configured_horizon_bars_mean",
        "configured_readout_lr_mean",
        "configured_delayed_readout_lr_mean",
        "configured_dopamine_tau_mean",
        "configured_initial_population_mean",
        "configured_max_population_mean",
        "hypothesis",
    ]
    return [{field: row.get(field) for field in fields} for row in aggregates]


def write_report(path: Path, result: TestResult, comparisons: list[dict[str, Any]], findings: list[dict[str, Any]], args: argparse.Namespace, output_dir: Path) -> None:
    overall = "PASS" if result.passed else "FAIL"
    lines = [
        "# Tier 5.3 CRA Failure Analysis / Learning Dynamics Debug Findings",
        "",
        f"- Generated: `{utc_now()}`",
        f"- Status: **{overall}**",
        f"- CRA backend: `{args.backend}`",
        f"- Steps: `{args.steps}`",
        f"- Seeds: `{', '.join(str(s) for s in seeds_from_args(args))}`",
        f"- Tasks: `{args.tasks}`",
        f"- Variants: `{args.variants}`",
        f"- Output directory: `{output_dir}`",
        "",
        "Tier 5.3 is diagnostic, not a new hardware or superiority claim. It asks which CRA learning-dynamics knobs move the failing Tier 5.2 tasks, using Tier 5.2 external baselines as reference.",
        "",
        "## Claim Boundary",
        "",
        "- This is controlled software tuning/failure-analysis evidence only.",
        "- A pass means the diagnostic matrix completed and produced interpretable findings.",
        "- It does not mean CRA is competitively recovered unless a variant beats the external reference.",
        "- `sensor_control` is removed from advantage claims because Tier 5.2 showed it saturates for both CRA and baselines.",
        "",
        "## Task Diagnoses",
        "",
        "| Task | Likely diagnosis | Best variant | Best tail | Delta vs current CRA | Delta vs external median | Recovered vs external median? |",
        "| --- | --- | --- | ---: | ---: | ---: | --- |",
    ]
    for row in findings:
        lines.append(
            "| "
            f"{row['task']} | {row['likely_diagnosis']} | `{row['best_tail_variant']}` | "
            f"{markdown_value(row.get('best_tail_accuracy_mean'))} | "
            f"{markdown_value(row.get('best_tail_delta_vs_current_cra'))} | "
            f"{markdown_value(row.get('best_tail_delta_vs_external_median'))} | "
            f"{'yes' if row.get('recovered_vs_external_median_tail') else 'no'} |"
        )
    lines.extend(
        [
            "",
            "## Variant Comparisons",
            "",
            "| Task | Variant | Group | Tail acc | Delta vs current CRA | Delta vs external median | Abs corr delta vs current | Recovery delta vs current |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in sorted(comparisons, key=lambda r: (r["task"], r["variant_group"], r["variant"])):
        lines.append(
            "| "
            f"{row['task']} | `{row['variant']}` | `{row['variant_group']}` | "
            f"{markdown_value(row.get('cra_tail_accuracy_mean'))} | "
            f"{markdown_value(row.get('tail_delta_vs_current_cra'))} | "
            f"{markdown_value(row.get('tail_delta_vs_external_median'))} | "
            f"{markdown_value(row.get('abs_corr_delta_vs_current_cra'))} | "
            f"{markdown_value(row.get('recovery_delta_vs_current_cra'))} |"
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
            "- `tier5_3_results.json`: machine-readable manifest.",
            "- `tier5_3_summary.csv`: aggregate task/variant metrics.",
            "- `tier5_3_comparisons.csv`: variant comparisons versus current CRA and Tier 5.2 external references.",
            "- `tier5_3_findings.csv`: task-level diagnoses.",
            "- `tier5_3_variant_matrix.png`: tail accuracy and deltas by variant.",
            "- `tier5_3_group_effects.png`: best mechanism-group improvements.",
            "- `*_timeseries.csv`: per-task/per-variant/per-seed CRA traces.",
            "",
            "## Plots",
            "",
            "![variant_matrix](tier5_3_variant_matrix.png)",
            "",
            "![group_effects](tier5_3_group_effects.png)",
            "",
        ]
    )
    if MATPLOTLIB_ERROR:
        lines.append(f"Plotting unavailable: `{MATPLOTLIB_ERROR}`")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def run_tier(args: argparse.Namespace, output_dir: Path, variants: list[VariantSpec]) -> TestResult:
    summaries_by_cell: dict[tuple[str, str], list[dict[str, Any]]] = {}
    rows_by_cell_seed: dict[tuple[str, str, int], list[dict[str, Any]]] = {}
    task_by_name: dict[str, TaskStream] = {}
    task_by_name_seed: dict[tuple[str, int], TaskStream] = {}
    artifacts: dict[str, str] = {}
    started = time.perf_counter()

    for seed in seeds_from_args(args):
        tasks = build_tasks(args, seed=args.task_seed + seed)
        for task in tasks:
            task_by_name[task.name] = task
            task_by_name_seed[(task.name, seed)] = task
            for variant in variants:
                print(f"[tier5.3] steps={args.steps} task={task.name} variant={variant.name} seed={seed}", flush=True)
                rows, summary = run_cra_variant(task, seed=seed, variant=variant, args=args)
                csv_path = output_dir / f"{task.name}_{variant.name}_seed{seed}_timeseries.csv"
                write_csv(csv_path, rows)
                artifacts[f"{task.name}_{variant.name}_seed{seed}_timeseries_csv"] = str(csv_path)
                summaries_by_cell.setdefault((task.name, variant.name), []).append(summary)
                rows_by_cell_seed[(task.name, variant.name, seed)] = rows

    variant_by_name = {variant.name: variant for variant in variants}
    aggregates: list[dict[str, Any]] = []
    for (task_name, variant_name), summaries in sorted(summaries_by_cell.items()):
        task = task_by_name[task_name]
        variant = variant_by_name[variant_name]
        seed_rows = {
            int(summary["seed"]): rows_by_cell_seed[(task_name, variant_name, int(summary["seed"]))]
            for summary in summaries
        }
        seed_tasks = {
            int(summary["seed"]): task_by_name_seed[(task_name, int(summary["seed"]))]
            for summary in summaries
        }
        aggregates.append(aggregate_variant(task, variant, summaries, seed_rows, seed_tasks, args))

    reference = load_reference(args.reference_comparisons, args.steps)
    comparisons = build_comparisons(aggregates, reference)
    findings = best_by_task(comparisons)
    criteria, tier_summary = evaluate_tier(
        aggregates=aggregates,
        comparisons=comparisons,
        findings=findings,
        variants=variants,
        args=args,
    )
    status, failure_reason = pass_fail(criteria)

    summary_csv = output_dir / "tier5_3_summary.csv"
    comparison_csv = output_dir / "tier5_3_comparisons.csv"
    findings_csv = output_dir / "tier5_3_findings.csv"
    matrix_plot = output_dir / "tier5_3_variant_matrix.png"
    group_plot = output_dir / "tier5_3_group_effects.png"
    write_csv(summary_csv, aggregate_csv_rows(aggregates))
    write_csv(comparison_csv, comparisons)
    write_csv(findings_csv, findings)
    plot_variant_matrix(comparisons, matrix_plot)
    plot_group_effects(comparisons, group_plot)

    result_artifacts = {
        "summary_csv": str(summary_csv),
        "comparisons_csv": str(comparison_csv),
        "findings_csv": str(findings_csv),
        "variant_matrix_png": str(matrix_plot) if matrix_plot.exists() else "",
        "group_effects_png": str(group_plot) if group_plot.exists() else "",
    }
    result_artifacts.update(artifacts)
    return TestResult(
        name="cra_failure_analysis_learning_dynamics_debug",
        status=status,
        summary={
            "tier_summary": tier_summary,
            "aggregates": aggregates,
            "comparisons": comparisons,
            "findings": findings,
            "reference_comparisons": str(args.reference_comparisons),
            "runtime_seconds": time.perf_counter() - started,
        },
        criteria=criteria,
        artifacts=result_artifacts,
        failure_reason=failure_reason,
    )


def write_latest(output_dir: Path, report_path: Path, manifest_path: Path, summary_csv: Path, status: str) -> None:
    latest_path = ROOT / "controlled_test_output" / "tier5_3_latest_manifest.json"
    payload = {
        "generated_at_utc": utc_now(),
        "tier": TIER,
        "status": status,
        "output_dir": str(output_dir),
        "manifest": str(manifest_path),
        "report": str(report_path),
        "summary_csv": str(summary_csv),
        "canonical": False,
        "claim": "Latest Tier 5.3 CRA failure-analysis diagnostic; promote only after review.",
    }
    write_json(latest_path, payload)


def build_parser() -> argparse.ArgumentParser:
    parser = build_tier5_1_parser()
    parser.description = "Run Tier 5.3 CRA failure-analysis/tuning diagnostics."
    parser.set_defaults(
        backend="nest",
        tasks=DEFAULT_TASKS,
        steps=960,
        seed_count=3,
        models="cra",
        cra_population_size=8,
    )
    parser.add_argument("--variants", default=DEFAULT_VARIANTS, help="core, extended, all, or comma-separated variant names")
    parser.add_argument("--reference-comparisons", type=Path, default=DEFAULT_REFERENCE)
    parser.add_argument("--meaningful-tail-delta", type=float, default=0.05)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    variants = parse_variants(args.variants)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = args.output_dir or (ROOT / "controlled_test_output" / f"tier5_3_{timestamp}")
    output_dir.mkdir(parents=True, exist_ok=True)

    result = run_tier(args, output_dir, variants)
    manifest_path = output_dir / "tier5_3_results.json"
    report_path = output_dir / "tier5_3_report.md"
    summary_csv = output_dir / "tier5_3_summary.csv"
    comparison_csv = output_dir / "tier5_3_comparisons.csv"
    findings_csv = output_dir / "tier5_3_findings.csv"
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
            "runtime_seconds": result.summary["runtime_seconds"],
            "reference_comparisons": result.summary["reference_comparisons"],
            "findings": result.summary["findings"],
        },
        "artifacts": {
            "summary_csv": str(summary_csv),
            "comparisons_csv": str(comparison_csv),
            "findings_csv": str(findings_csv),
            "report_md": str(report_path),
            "variant_matrix_png": str(output_dir / "tier5_3_variant_matrix.png"),
            "group_effects_png": str(output_dir / "tier5_3_group_effects.png"),
        },
    }
    write_json(manifest_path, json_safe(manifest))
    write_report(report_path, result, result.summary["comparisons"], result.summary["findings"], args, output_dir)
    write_latest(output_dir, report_path, manifest_path, summary_csv, result.status)
    print(
        json.dumps(
            {
                "status": result.status,
                "output_dir": str(output_dir),
                "manifest": str(manifest_path),
                "report": str(report_path),
                "summary_csv": str(summary_csv),
                "comparisons_csv": str(comparison_csv),
                "findings_csv": str(findings_csv),
                "failure_reason": result.failure_reason,
            },
            indent=2,
        )
    )
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
