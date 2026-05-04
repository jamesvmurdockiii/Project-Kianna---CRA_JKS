#!/usr/bin/env python3
"""Tier 6.1 lifecycle / self-scaling benchmark for CRA.

Tier 6.1 is the first direct test of the organism claim. Earlier tiers showed
that CRA can learn, survive controls/ablations, transfer across backends, and
run on SpiNNaker. This tier asks a different question:

    Does lifecycle/self-scaling add measurable value over fixed-N CRA?

The harness compares fixed populations against lifecycle-enabled populations on
identical hard/adaptive task streams. A pass requires real birth/death/lineage
telemetry, clean fixed-N controls, no extinction, and at least one predeclared
lifecycle advantage regime. If fixed-N dominates, the harness fails honestly and
narrows the organism claim.
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
except Exception as exc:  # pragma: no cover - plotting dependency is optional
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
    build_tasks,
    recovery_steps,
    summarize_rows,
)


TIER = "Tier 6.1 - Software Lifecycle / Self-Scaling Benchmark"
DEFAULT_TASKS = "hard_noisy_switching,delayed_cue"
DEFAULT_CASES = "fixed4,fixed8,fixed16,life4_16,life8_32,life16_64"
EPS = 1e-12


@dataclass(frozen=True)
class CaseSpec:
    name: str
    group: str
    initial_population: int
    max_population: int
    lifecycle_enabled: bool
    profile: str
    paired_fixed: str | None = None
    description: str = ""


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


CASE_LIBRARY: dict[str, CaseSpec] = {
    "fixed4": CaseSpec(
        name="fixed4",
        group="fixed",
        initial_population=4,
        max_population=4,
        lifecycle_enabled=False,
        profile="fixed",
        description="Fixed N=4 CRA control; no birth/death lifecycle.",
    ),
    "fixed8": CaseSpec(
        name="fixed8",
        group="fixed",
        initial_population=8,
        max_population=8,
        lifecycle_enabled=False,
        profile="fixed",
        description="Fixed N=8 CRA control; current hardware-sized baseline.",
    ),
    "fixed16": CaseSpec(
        name="fixed16",
        group="fixed",
        initial_population=16,
        max_population=16,
        lifecycle_enabled=False,
        profile="fixed",
        description="Fixed N=16 CRA capacity control.",
    ),
    "life4_16": CaseSpec(
        name="life4_16",
        group="lifecycle",
        initial_population=4,
        max_population=16,
        lifecycle_enabled=True,
        profile="standard",
        paired_fixed="fixed4",
        description="Lifecycle-enabled CRA starting at N=4 with max pool 16.",
    ),
    "life8_32": CaseSpec(
        name="life8_32",
        group="lifecycle",
        initial_population=8,
        max_population=32,
        lifecycle_enabled=True,
        profile="standard",
        paired_fixed="fixed8",
        description="Lifecycle-enabled CRA starting at N=8 with max pool 32.",
    ),
    "life16_64": CaseSpec(
        name="life16_64",
        group="lifecycle",
        initial_population=16,
        max_population=64,
        lifecycle_enabled=True,
        profile="standard",
        paired_fixed="fixed16",
        description="Lifecycle-enabled CRA starting at N=16 with max pool 64.",
    ),
    "life4_16_fast": CaseSpec(
        name="life4_16_fast",
        group="lifecycle",
        initial_population=4,
        max_population=16,
        lifecycle_enabled=True,
        profile="fast_replacement",
        paired_fixed="fixed4",
        description="Lifecycle N=4->16 with faster maturity/replacement pressure.",
    ),
    "life8_32_fast": CaseSpec(
        name="life8_32_fast",
        group="lifecycle",
        initial_population=8,
        max_population=32,
        lifecycle_enabled=True,
        profile="fast_replacement",
        paired_fixed="fixed8",
        description="Lifecycle N=8->32 with faster maturity/replacement pressure.",
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


def parse_cases(raw: str) -> list[CaseSpec]:
    raw = raw.strip()
    if raw in {"", "default", "all"}:
        names = [item.strip() for item in DEFAULT_CASES.split(",")]
    elif raw == "smoke":
        names = ["fixed4", "life4_16"]
    else:
        names = [item.strip() for item in raw.split(",") if item.strip()]
    missing = [name for name in names if name not in CASE_LIBRARY]
    if missing:
        known = ", ".join(sorted(CASE_LIBRARY))
        raise argparse.ArgumentTypeError(f"unknown Tier 6.1 cases: {', '.join(missing)}; known: {known}")
    ordered: list[CaseSpec] = []
    seen: set[str] = set()
    for name in names:
        if name not in seen:
            ordered.append(CASE_LIBRARY[name])
            seen.add(name)
    return ordered


def finite_float(value: Any, default: float = 0.0) -> float:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return default
    return f if math.isfinite(f) else default


def max_value(values: list[Any]) -> float | None:
    clean = [finite_float(v) for v in values if v is not None]
    return None if not clean else float(np.max(clean))


def case_mean_n_alive(rows: list[dict[str, Any]]) -> float | None:
    vals = [finite_float(r.get("n_alive")) for r in rows if "n_alive" in r]
    return None if not vals else float(np.mean(vals))


def case_min_n_alive(rows: list[dict[str, Any]]) -> int | None:
    vals = [int(finite_float(r.get("n_alive"))) for r in rows if "n_alive" in r]
    return None if not vals else int(np.min(vals))


def lifecycle_events_to_rows(events: list[Any], *, task: str, case: CaseSpec, seed: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for event in events:
        rows.append(
            {
                "task": task,
                "case": case.name,
                "seed": int(seed),
                "event_type": str(getattr(event, "event_type", "")),
                "step": int(getattr(event, "step", -1)),
                "polyp_id": int(getattr(event, "polyp_id", -1)),
                "lineage_id": int(getattr(event, "lineage_id", -1)),
                "parent_id": getattr(event, "parent_id", None),
                "details": json.dumps(json_safe(getattr(event, "details", {}) or {}), sort_keys=True),
            }
        )
    return rows


def lineage_stats_to_rows(stats: dict[Any, Any], *, task: str, case: CaseSpec, seed: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for lineage_id, item in sorted(stats.items(), key=lambda kv: int(kv[0])):
        row = {
            "task": task,
            "case": case.name,
            "seed": int(seed),
            "lineage_id": int(lineage_id),
        }
        row.update(item)
        rows.append(row)
    return rows


def validate_lineage_integrity(organism: Organism, events: list[Any], lineage_stats: dict[Any, Any]) -> tuple[bool, list[str]]:
    problems: list[str] = []
    states = [] if organism.polyp_population is None else list(organism.polyp_population.states)
    alive = [s for s in states if getattr(s, "is_alive", False)]
    alive_ids = [int(getattr(s, "polyp_id", -1)) for s in alive]
    if len(alive_ids) != len(set(alive_ids)):
        problems.append("duplicate alive polyp_id")
    if any(pid < 0 for pid in alive_ids):
        problems.append("negative alive polyp_id")
    alive_lineages = [int(getattr(s, "lineage_id", -1)) for s in alive]
    if any(lid < 0 for lid in alive_lineages):
        problems.append("negative alive lineage_id")
    known_lineages = {int(k) for k in lineage_stats.keys()}
    missing_lineages = sorted({lid for lid in alive_lineages if lid not in known_lineages})
    if missing_lineages:
        problems.append(f"alive lineages missing from registry: {missing_lineages[:8]}")
    for event in events:
        event_type = str(getattr(event, "event_type", ""))
        polyp_id = int(getattr(event, "polyp_id", -1))
        lineage_id = int(getattr(event, "lineage_id", -1))
        if event_type not in {"birth", "death", "handoff", "cleavage"}:
            problems.append(f"unknown lifecycle event type: {event_type}")
        if polyp_id < 0:
            problems.append(f"negative event polyp_id: {event_type}")
        if lineage_id < 0:
            problems.append(f"negative event lineage_id: {event_type}")
    return len(problems) == 0, problems


def make_config(*, seed: int, task: TaskStream, case: CaseSpec, args: argparse.Namespace) -> ReefConfig:
    cfg = ReefConfig.default()
    cfg.seed = int(seed)
    cfg.lifecycle.initial_population = int(case.initial_population)
    cfg.lifecycle.max_population_from_memory = False
    cfg.lifecycle.max_population_hard = int(case.max_population)
    cfg.lifecycle.enable_reproduction = bool(case.lifecycle_enabled)
    cfg.lifecycle.enable_apoptosis = bool(case.lifecycle_enabled)
    cfg.lifecycle.enable_structural_plasticity = bool(case.lifecycle_enabled)
    cfg.measurement.stream_history_maxlen = max(task.steps + 16, 128)
    cfg.spinnaker.sync_interval_steps = 0
    cfg.spinnaker.runtime_ms_per_step = 1000.0
    if np.any(task.feedback_due_step >= 0):
        due = task.feedback_due_step - np.arange(task.steps)
        cfg.learning.evaluation_horizon_bars = int(max(1, np.max(due[task.feedback_due_step >= 0])))
    else:
        cfg.learning.evaluation_horizon_bars = 1
    cfg.learning.readout_learning_rate = float(args.cra_readout_lr)
    cfg.learning.delayed_readout_learning_rate = float(args.cra_delayed_readout_lr)

    if case.profile == "fast_replacement":
        cfg.lifecycle.reproduction_cooldown_steps = int(args.fast_reproduction_cooldown_steps)
        cfg.lifecycle.maturity_age_estimate_steps = int(args.fast_maturity_steps)
        cfg.lifecycle.max_children_per_step = int(args.fast_max_children_per_step)
        cfg.energy.accuracy_survival_floor = float(args.fast_accuracy_survival_floor)
        cfg.energy.accuracy_penalty_multiplier = float(args.fast_accuracy_penalty_multiplier)
    return cfg


def run_case(task: TaskStream, case: CaseSpec, *, seed: int, args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    random.seed(seed)
    np.random.seed(seed)
    sim, backend_name = load_backend(args.backend)
    setup_backend(sim, backend_name)
    cfg = make_config(seed=seed, task=task, case=case, args=args)
    organism = Organism(cfg, sim, use_default_trading_bridge=(task.domain != "sensor_control"))
    adapter = SensorControlAdapter()
    rows: list[dict[str, Any]] = []
    started = time.perf_counter()
    lineage_ok = True
    lineage_problems: list[str] = []
    lifecycle_event_rows: list[dict[str, Any]] = []
    lineage_rows: list[dict[str, Any]] = []
    try:
        organism.initialize(stream_keys=[task.domain])
        for step in range(task.steps):
            sensory_value = float(task.sensory[step])
            target_value = float(task.current_target[step])
            if task.domain == "sensor_control":
                observation = Observation(
                    stream_id=task.domain,
                    x=np.asarray([sensory_value], dtype=float),
                    target=target_value,
                    metadata={"task": task.name, "step": step, "tier": "6.1"},
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
            active_efficiency = None
            if int(row.get("n_alive", 0) or 0) > 0:
                active_efficiency = float(row.get("mean_directional_accuracy_ema", 0.5) or 0.5) / float(row["n_alive"])
            row.update(
                {
                    "task": task.name,
                    "case": case.name,
                    "case_group": case.group,
                    "lifecycle_enabled": bool(case.lifecycle_enabled),
                    "profile": case.profile,
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
                    "initial_population": int(case.initial_population),
                    "max_population": int(case.max_population),
                    "active_efficiency_proxy": active_efficiency,
                }
            )
            rows.append(row)
        events = organism.lifecycle_manager.get_all_events() if organism.lifecycle_manager is not None else []
        lineage_stats = organism.lifecycle_manager.get_lineage_stats() if organism.lifecycle_manager is not None else {}
        lineage_ok, lineage_problems = validate_lineage_integrity(organism, events, lineage_stats)
        lifecycle_event_rows = lifecycle_events_to_rows(events, task=task.name, case=case, seed=seed)
        lineage_rows = lineage_stats_to_rows(lineage_stats, task=task.name, case=case, seed=seed)
    finally:
        organism.shutdown()
        end_backend(sim)

    summary = summarize_rows(rows)
    n_alive_values = [finite_float(r.get("n_alive")) for r in rows if "n_alive" in r]
    active_eff_values = [finite_float(r.get("active_efficiency_proxy")) for r in rows if r.get("active_efficiency_proxy") is not None]
    summary.update(
        {
            "task": task.name,
            "case": case.name,
            "case_group": case.group,
            "lifecycle_enabled": bool(case.lifecycle_enabled),
            "profile": case.profile,
            "backend": backend_name,
            "seed": int(seed),
            "steps": int(task.steps),
            "runtime_seconds": time.perf_counter() - started,
            "initial_population": int(case.initial_population),
            "max_population": int(case.max_population),
            "paired_fixed": case.paired_fixed,
            "mean_n_alive": None if not n_alive_values else float(np.mean(n_alive_values)),
            "min_n_alive": None if not n_alive_values else int(np.min(n_alive_values)),
            "max_n_alive_observed": None if not n_alive_values else int(np.max(n_alive_values)),
            "extinct_steps": int(sum(1 for v in n_alive_values if v <= 0)),
            "mean_active_efficiency_proxy": None if not active_eff_values else float(np.mean(active_eff_values)),
            "tail_active_efficiency_proxy": None if not active_eff_values else float(np.mean(active_eff_values[int(len(active_eff_values) * 0.75) :])),
            "lineage_integrity_ok": bool(lineage_ok),
            "lineage_integrity_problems": lineage_problems,
            "lineage_count": len({int(row["lineage_id"]) for row in lineage_rows}) if lineage_rows else 0,
            "lifecycle_event_count": len(lifecycle_event_rows),
            "task_metadata": task.metadata,
            "config": cfg.to_dict(),
        }
    )
    return rows, summary, lifecycle_event_rows, lineage_rows


def aggregate_case(task: str, case: CaseSpec, summaries: list[dict[str, Any]], rows_by_seed: dict[int, list[dict[str, Any]]], task_by_seed: dict[int, TaskStream], args: argparse.Namespace) -> dict[str, Any]:
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
        "max_n_alive",
        "total_births",
        "total_deaths",
        "max_abs_dopamine",
        "mean_abs_dopamine",
        "mean_n_alive",
        "min_n_alive",
        "max_n_alive_observed",
        "extinct_steps",
        "mean_active_efficiency_proxy",
        "tail_active_efficiency_proxy",
        "lineage_count",
        "lifecycle_event_count",
    ]
    agg: dict[str, Any] = {
        "task": task,
        "case": case.name,
        "case_group": case.group,
        "profile": case.profile,
        "lifecycle_enabled": bool(case.lifecycle_enabled),
        "initial_population": int(case.initial_population),
        "max_population": int(case.max_population),
        "paired_fixed": case.paired_fixed,
        "runs": len(summaries),
        "seeds": [int(s.get("seed")) for s in summaries],
    }
    for key in keys:
        values = [s.get(key) for s in summaries]
        agg[f"{key}_mean"] = mean(values)
        agg[f"{key}_std"] = stdev(values)
        agg[f"{key}_min"] = min_value(values)
        agg[f"{key}_max"] = max_value(values)
    agg["total_births_sum"] = int(sum(int(s.get("total_births", 0) or 0) for s in summaries))
    agg["total_deaths_sum"] = int(sum(int(s.get("total_deaths", 0) or 0) for s in summaries))
    agg["lineage_integrity_failures"] = int(sum(0 if s.get("lineage_integrity_ok") else 1 for s in summaries))
    if any(seed_task.switch_steps for seed_task in task_by_seed.values()):
        per_seed_recovery: list[int] = []
        for seed, rows in rows_by_seed.items():
            seed_task = task_by_seed.get(seed)
            if seed_task is None or not seed_task.switch_steps:
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
        agg["mean_recovery_steps"] = mean(per_seed_recovery)
        agg["max_recovery_steps"] = max(per_seed_recovery) if per_seed_recovery else None
    else:
        agg["mean_recovery_steps"] = None
        agg["max_recovery_steps"] = None
    return agg


def summary_csv_rows(aggregates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for agg in aggregates:
        rows.append(
            {
                "task": agg["task"],
                "case": agg["case"],
                "case_group": agg["case_group"],
                "profile": agg["profile"],
                "initial_population": agg["initial_population"],
                "max_population": agg["max_population"],
                "runs": agg["runs"],
                "seeds": ",".join(str(s) for s in agg["seeds"]),
                "all_accuracy_mean": agg.get("all_accuracy_mean"),
                "tail_accuracy_mean": agg.get("tail_accuracy_mean"),
                "prediction_target_corr_mean": agg.get("prediction_target_corr_mean"),
                "tail_prediction_target_corr_mean": agg.get("tail_prediction_target_corr_mean"),
                "mean_recovery_steps": agg.get("mean_recovery_steps"),
                "final_n_alive_mean": agg.get("final_n_alive_mean"),
                "mean_n_alive_mean": agg.get("mean_n_alive_mean"),
                "max_n_alive_observed_mean": agg.get("max_n_alive_observed_mean"),
                "total_births_sum": agg.get("total_births_sum"),
                "total_deaths_sum": agg.get("total_deaths_sum"),
                "lineage_integrity_failures": agg.get("lineage_integrity_failures"),
                "tail_active_efficiency_proxy_mean": agg.get("tail_active_efficiency_proxy_mean"),
                "runtime_seconds_mean": agg.get("runtime_seconds_mean"),
            }
        )
    return rows


def build_comparisons(aggregates: list[dict[str, Any]], args: argparse.Namespace) -> list[dict[str, Any]]:
    by_key = {(agg["task"], agg["case"]): agg for agg in aggregates}
    rows: list[dict[str, Any]] = []
    for agg in aggregates:
        if agg["case_group"] != "lifecycle":
            continue
        task = agg["task"]
        paired_name = agg.get("paired_fixed")
        paired = by_key.get((task, paired_name)) if paired_name else None
        fixed_controls = [a for a in aggregates if a["task"] == task and a["case_group"] == "fixed"]
        best_fixed_tail = max(fixed_controls, key=lambda a: finite_float(a.get("tail_accuracy_mean")), default=None)
        best_fixed_corr = max(fixed_controls, key=lambda a: abs(finite_float(a.get("prediction_target_corr_mean"))), default=None)
        if paired is None:
            continue
        life_tail = finite_float(agg.get("tail_accuracy_mean"))
        fixed_tail = finite_float(paired.get("tail_accuracy_mean"))
        life_all = finite_float(agg.get("all_accuracy_mean"))
        fixed_all = finite_float(paired.get("all_accuracy_mean"))
        life_corr = abs(finite_float(agg.get("prediction_target_corr_mean")))
        fixed_corr = abs(finite_float(paired.get("prediction_target_corr_mean")))
        life_eff = finite_float(agg.get("tail_active_efficiency_proxy_mean"))
        fixed_eff = finite_float(paired.get("tail_active_efficiency_proxy_mean"))
        fixed_recovery = paired.get("mean_recovery_steps")
        life_recovery = agg.get("mean_recovery_steps")
        recovery_improvement = None
        if fixed_recovery is not None and life_recovery is not None:
            recovery_improvement = float(fixed_recovery) - float(life_recovery)
        advantage_reasons: list[str] = []
        if life_tail - fixed_tail >= args.min_tail_advantage:
            advantage_reasons.append("tail_accuracy")
        if life_all - fixed_all >= args.min_all_accuracy_advantage:
            advantage_reasons.append("all_accuracy")
        if life_corr - fixed_corr >= args.min_corr_advantage:
            advantage_reasons.append("prediction_correlation")
        if recovery_improvement is not None and recovery_improvement >= args.min_recovery_advantage_steps:
            advantage_reasons.append("switch_recovery")
        if life_eff - fixed_eff >= args.min_active_efficiency_advantage:
            advantage_reasons.append("active_population_efficiency")
        row = {
            "task": task,
            "lifecycle_case": agg["case"],
            "paired_fixed_case": paired_name,
            "initial_population": agg["initial_population"],
            "max_population": agg["max_population"],
            "lifecycle_tail_accuracy_mean": agg.get("tail_accuracy_mean"),
            "paired_fixed_tail_accuracy_mean": paired.get("tail_accuracy_mean"),
            "tail_delta_vs_paired_fixed": life_tail - fixed_tail,
            "lifecycle_all_accuracy_mean": agg.get("all_accuracy_mean"),
            "paired_fixed_all_accuracy_mean": paired.get("all_accuracy_mean"),
            "all_accuracy_delta_vs_paired_fixed": life_all - fixed_all,
            "lifecycle_abs_corr_mean": life_corr,
            "paired_fixed_abs_corr_mean": fixed_corr,
            "abs_corr_delta_vs_paired_fixed": life_corr - fixed_corr,
            "lifecycle_mean_recovery_steps": life_recovery,
            "paired_fixed_mean_recovery_steps": fixed_recovery,
            "recovery_improvement_steps_vs_paired_fixed": recovery_improvement,
            "lifecycle_tail_active_efficiency_proxy_mean": agg.get("tail_active_efficiency_proxy_mean"),
            "paired_fixed_tail_active_efficiency_proxy_mean": paired.get("tail_active_efficiency_proxy_mean"),
            "active_efficiency_delta_vs_paired_fixed": life_eff - fixed_eff,
            "best_fixed_tail_case": None if best_fixed_tail is None else best_fixed_tail["case"],
            "best_fixed_tail_accuracy_mean": None if best_fixed_tail is None else best_fixed_tail.get("tail_accuracy_mean"),
            "tail_delta_vs_best_fixed": None if best_fixed_tail is None else life_tail - finite_float(best_fixed_tail.get("tail_accuracy_mean")),
            "best_fixed_corr_case": None if best_fixed_corr is None else best_fixed_corr["case"],
            "best_fixed_abs_corr_mean": None if best_fixed_corr is None else abs(finite_float(best_fixed_corr.get("prediction_target_corr_mean"))),
            "abs_corr_delta_vs_best_fixed": None if best_fixed_corr is None else life_corr - abs(finite_float(best_fixed_corr.get("prediction_target_corr_mean"))),
            "total_births_sum": agg.get("total_births_sum"),
            "total_deaths_sum": agg.get("total_deaths_sum"),
            "mean_n_alive_mean": agg.get("mean_n_alive_mean"),
            "lineage_integrity_failures": agg.get("lineage_integrity_failures"),
            "advantage": bool(advantage_reasons),
            "advantage_reasons": ",".join(advantage_reasons),
        }
        rows.append(row)
    return rows


def evaluate_tier(aggregates: list[dict[str, Any]], comparisons: list[dict[str, Any]], args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    cases = parse_cases(args.cases)
    task_names = [item.strip() for item in args.tasks.split(",") if item.strip()]
    expected_runs = len(seeds_from_args(args)) * len(cases) * len(task_names)
    actual_runs = int(sum(int(agg.get("runs", 0)) for agg in aggregates))
    fixed = [agg for agg in aggregates if agg["case_group"] == "fixed"]
    lifecycle = [agg for agg in aggregates if agg["case_group"] == "lifecycle"]
    fixed_births = int(sum(int(agg.get("total_births_sum", 0) or 0) for agg in fixed))
    fixed_deaths = int(sum(int(agg.get("total_deaths_sum", 0) or 0) for agg in fixed))
    lifecycle_births = int(sum(int(agg.get("total_births_sum", 0) or 0) for agg in lifecycle))
    lifecycle_deaths = int(sum(int(agg.get("total_deaths_sum", 0) or 0) for agg in lifecycle))
    lineage_failures = int(sum(int(agg.get("lineage_integrity_failures", 0) or 0) for agg in aggregates))
    extinct_runs = int(sum(1 for agg in aggregates if finite_float(agg.get("final_n_alive_min"), 1.0) <= 0))
    advantage_regimes = [row for row in comparisons if row.get("advantage")]
    task_coverage = sorted({row["task"] for row in advantage_regimes})
    max_tail_delta = max([finite_float(row.get("tail_delta_vs_paired_fixed")) for row in comparisons], default=0.0)
    max_corr_delta = max([finite_float(row.get("abs_corr_delta_vs_paired_fixed")) for row in comparisons], default=0.0)
    max_recovery_delta = max([finite_float(row.get("recovery_improvement_steps_vs_paired_fixed")) for row in comparisons if row.get("recovery_improvement_steps_vs_paired_fixed") is not None], default=0.0)

    tier_summary = {
        "expected_runs": expected_runs,
        "actual_runs": actual_runs,
        "tasks": task_names,
        "cases": [case.name for case in cases],
        "seeds": seeds_from_args(args),
        "backend": args.backend,
        "fixed_births_sum": fixed_births,
        "fixed_deaths_sum": fixed_deaths,
        "lifecycle_births_sum": lifecycle_births,
        "lifecycle_deaths_sum": lifecycle_deaths,
        "lineage_integrity_failures": lineage_failures,
        "extinct_aggregate_count": extinct_runs,
        "advantage_regime_count": len(advantage_regimes),
        "advantage_tasks": task_coverage,
        "max_tail_delta_vs_paired_fixed": max_tail_delta,
        "max_abs_corr_delta_vs_paired_fixed": max_corr_delta,
        "max_recovery_improvement_steps_vs_paired_fixed": max_recovery_delta,
    }
    criteria = [
        criterion(
            "matrix completed",
            actual_runs,
            "==",
            expected_runs,
            actual_runs == expected_runs,
        ),
        criterion(
            "fixed controls have no births",
            fixed_births,
            "==",
            0,
            fixed_births == 0,
        ),
        criterion(
            "fixed controls have no deaths",
            fixed_deaths,
            "==",
            0,
            fixed_deaths == 0,
        ),
        criterion(
            "lifecycle produces real births",
            lifecycle_births,
            ">=",
            args.min_lifecycle_births,
            lifecycle_births >= args.min_lifecycle_births,
        ),
        criterion(
            "lineage integrity remains clean",
            lineage_failures,
            "==",
            0,
            lineage_failures == 0,
        ),
        criterion(
            "no aggregate extinction",
            extinct_runs,
            "==",
            0,
            extinct_runs == 0,
        ),
        criterion(
            "lifecycle advantage regimes",
            len(advantage_regimes),
            ">=",
            args.min_advantage_regimes,
            len(advantage_regimes) >= args.min_advantage_regimes,
            "Advantage can be accuracy, correlation, recovery, or active-population efficiency versus same-initial fixed control.",
        ),
    ]
    return criteria, tier_summary


def plot_summary(aggregates: list[dict[str, Any]], path: Path) -> None:
    if plt is None or not aggregates:
        return
    tasks = sorted({a["task"] for a in aggregates})
    cases = [a["case"] for a in aggregates if a["task"] == tasks[0]] if tasks else []
    fig, axes = plt.subplots(len(tasks), 1, figsize=(max(10, len(cases) * 1.1), 4 * len(tasks)), squeeze=False)
    for row_idx, task in enumerate(tasks):
        ax = axes[row_idx][0]
        vals = []
        colors = []
        for case in cases:
            agg = next((a for a in aggregates if a["task"] == task and a["case"] == case), None)
            vals.append(float(agg.get("tail_accuracy_mean") or 0.0) if agg else 0.0)
            colors.append("#2da44e" if agg and agg.get("case_group") == "lifecycle" else "#0969da")
        ax.bar(range(len(cases)), vals, color=colors)
        ax.set_title(f"{task}: tail accuracy by fixed/lifecycle case")
        ax.set_ylim(0.0, 1.05)
        ax.set_ylabel("tail accuracy")
        ax.set_xticks(range(len(cases)))
        ax.set_xticklabels(cases, rotation=35, ha="right")
        ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_alive_traces(all_rows: list[dict[str, Any]], path: Path) -> None:
    if plt is None or not all_rows:
        return
    tasks = sorted({r["task"] for r in all_rows})
    fig, axes = plt.subplots(len(tasks), 1, figsize=(12, 4 * len(tasks)), squeeze=False)
    for row_idx, task in enumerate(tasks):
        ax = axes[row_idx][0]
        task_rows = [r for r in all_rows if r["task"] == task]
        for case in sorted({r["case"] for r in task_rows}):
            case_rows = [r for r in task_rows if r["case"] == case]
            steps = sorted({int(r["step"]) for r in case_rows})
            if not steps:
                continue
            values = []
            for step in steps:
                values.append(float(np.mean([finite_float(r.get("n_alive")) for r in case_rows if int(r["step"]) == step])))
            alpha = 0.95 if case.startswith("life") else 0.55
            ax.plot(steps, values, label=case, lw=1.2, alpha=alpha)
        ax.set_title(f"{task}: alive population over time")
        ax.set_xlabel("step")
        ax.set_ylabel("alive polyps")
        ax.grid(alpha=0.2)
        ax.legend(loc="upper left", ncol=2, fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def write_report(*, path: Path, result: TestResult, output_dir: Path, args: argparse.Namespace) -> None:
    summary = result.summary["tier_summary"]
    aggregates = result.summary["aggregates"]
    comparisons = result.summary["comparisons"]
    lines = [
        "# Tier 6.1 Lifecycle / Self-Scaling Findings",
        "",
        f"- Generated: `{utc_now()}`",
        f"- Backend: `{args.backend}`",
        f"- Status: **{result.status.upper()}**",
        f"- Output directory: `{output_dir}`",
        "",
        "Tier 6.1 asks whether CRA's lifecycle/self-scaling machinery adds measurable value over fixed-N CRA controls on identical hard/adaptive streams.",
        "",
        "## Claim Boundary",
        "",
        "- PASS would support a software-only lifecycle/self-scaling claim for the tested tasks and seeds.",
        "- PASS is not hardware lifecycle evidence, not on-chip birth/death, not continuous/custom-C runtime evidence, and not external-baseline superiority.",
        "- FAIL means the organism/ecology claim must narrow until repaired by later mechanisms or sham controls.",
        "",
        "## Summary",
        "",
        f"- expected_runs: `{summary['expected_runs']}`",
        f"- actual_runs: `{summary['actual_runs']}`",
        f"- fixed_births_sum: `{summary['fixed_births_sum']}`",
        f"- lifecycle_births_sum: `{summary['lifecycle_births_sum']}`",
        f"- lifecycle_deaths_sum: `{summary['lifecycle_deaths_sum']}`",
        f"- lineage_integrity_failures: `{summary['lineage_integrity_failures']}`",
        f"- advantage_regime_count: `{summary['advantage_regime_count']}`",
        f"- advantage_tasks: `{summary['advantage_tasks']}`",
        "",
        "## Criteria",
        "",
        "| Criterion | Value | Rule | Pass |",
        "| --- | ---: | --- | --- |",
    ]
    for item in result.criteria:
        lines.append(
            f"| {item['name']} | {markdown_value(item['value'])} | {item['operator']} {markdown_value(item['threshold'])} | {'yes' if item['passed'] else 'no'} |"
        )
    if result.failure_reason:
        lines.extend(["", f"Failure: {result.failure_reason}", ""])

    lines.extend(
        [
            "",
            "## Case Aggregates",
            "",
            "| Task | Case | Group | Tail Acc | Abs Corr | Recovery | Births | Deaths | Mean Alive | Lineage Fails |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for agg in aggregates:
        lines.append(
            "| "
            f"`{agg['task']}` | `{agg['case']}` | `{agg['case_group']}` | "
            f"{markdown_value(agg.get('tail_accuracy_mean'))} | "
            f"{markdown_value(abs(finite_float(agg.get('prediction_target_corr_mean'))))} | "
            f"{markdown_value(agg.get('mean_recovery_steps'))} | "
            f"{markdown_value(agg.get('total_births_sum'))} | "
            f"{markdown_value(agg.get('total_deaths_sum'))} | "
            f"{markdown_value(agg.get('mean_n_alive_mean'))} | "
            f"{markdown_value(agg.get('lineage_integrity_failures'))} |"
        )

    lines.extend(
        [
            "",
            "## Lifecycle vs Fixed Comparisons",
            "",
            "| Task | Lifecycle | Fixed Pair | Tail Delta | Corr Delta | Recovery Improvement | Efficiency Delta | Advantage | Reason |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- |",
        ]
    )
    for row in comparisons:
        lines.append(
            "| "
            f"`{row['task']}` | `{row['lifecycle_case']}` | `{row['paired_fixed_case']}` | "
            f"{markdown_value(row.get('tail_delta_vs_paired_fixed'))} | "
            f"{markdown_value(row.get('abs_corr_delta_vs_paired_fixed'))} | "
            f"{markdown_value(row.get('recovery_improvement_steps_vs_paired_fixed'))} | "
            f"{markdown_value(row.get('active_efficiency_delta_vs_paired_fixed'))} | "
            f"{'yes' if row.get('advantage') else 'no'} | `{row.get('advantage_reasons', '')}` |"
        )

    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            "- `tier6_1_results.json`: machine-readable manifest.",
            "- `tier6_1_summary.csv`: aggregate fixed/lifecycle metrics.",
            "- `tier6_1_comparisons.csv`: lifecycle-vs-fixed deltas.",
            "- `tier6_1_lifecycle_events.csv`: birth/death/handoff event log.",
            "- `tier6_1_lineage_final.csv`: final lineage audit table.",
            "- `*_timeseries.csv`: per-task/per-case/per-seed traces.",
            "",
            "## Plots",
            "",
            "![summary](tier6_1_lifecycle_summary.png)",
            "",
            "![alive](tier6_1_alive_population.png)",
        ]
    )
    if MATPLOTLIB_ERROR:
        lines.append(f"Plotting unavailable: `{MATPLOTLIB_ERROR}`")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def run_tier(args: argparse.Namespace, output_dir: Path) -> TestResult:
    cases = parse_cases(args.cases)
    all_timeseries_rows: list[dict[str, Any]] = []
    all_event_rows: list[dict[str, Any]] = []
    all_lineage_rows: list[dict[str, Any]] = []
    summaries_by_task_case: dict[tuple[str, str], list[dict[str, Any]]] = {}
    rows_by_task_case_seed: dict[tuple[str, str, int], list[dict[str, Any]]] = {}
    task_by_seed_name: dict[tuple[int, str], TaskStream] = {}
    artifacts: dict[str, str] = {}

    for seed in seeds_from_args(args):
        tasks = build_tasks(args, seed=args.task_seed + seed)
        for task in tasks:
            task_by_seed_name[(seed, task.name)] = task
            for case in cases:
                print(f"[tier6.1] task={task.name} case={case.name} seed={seed}", flush=True)
                rows, summary, event_rows, lineage_rows = run_case(task, case, seed=seed, args=args)
                csv_path = output_dir / f"{task.name}_{case.name}_seed{seed}_timeseries.csv"
                write_csv(csv_path, rows)
                artifacts[f"{task.name}_{case.name}_seed{seed}_timeseries_csv"] = str(csv_path)
                all_timeseries_rows.extend(rows)
                all_event_rows.extend(event_rows)
                all_lineage_rows.extend(lineage_rows)
                summaries_by_task_case.setdefault((task.name, case.name), []).append(summary)
                rows_by_task_case_seed[(task.name, case.name, seed)] = rows

    aggregates: list[dict[str, Any]] = []
    case_by_name = {case.name: case for case in cases}
    for (task_name, case_name), summaries in sorted(summaries_by_task_case.items()):
        seed_rows = {
            int(summary["seed"]): rows_by_task_case_seed[(task_name, case_name, int(summary["seed"]))]
            for summary in summaries
        }
        seed_tasks = {
            int(summary["seed"]): task_by_seed_name[(int(summary["seed"]), task_name)]
            for summary in summaries
        }
        aggregates.append(aggregate_case(task_name, case_by_name[case_name], summaries, seed_rows, seed_tasks, args))

    comparisons = build_comparisons(aggregates, args)
    criteria, tier_summary = evaluate_tier(aggregates, comparisons, args)
    status, failure_reason = pass_fail(criteria)

    summary_csv = output_dir / "tier6_1_summary.csv"
    comparisons_csv = output_dir / "tier6_1_comparisons.csv"
    events_csv = output_dir / "tier6_1_lifecycle_events.csv"
    lineage_csv = output_dir / "tier6_1_lineage_final.csv"
    summary_plot = output_dir / "tier6_1_lifecycle_summary.png"
    alive_plot = output_dir / "tier6_1_alive_population.png"
    write_csv(summary_csv, summary_csv_rows(aggregates))
    write_csv(comparisons_csv, comparisons)
    write_csv(events_csv, all_event_rows)
    write_csv(lineage_csv, all_lineage_rows)
    plot_summary(aggregates, summary_plot)
    plot_alive_traces(all_timeseries_rows, alive_plot)

    artifacts.update(
        {
            "summary_csv": str(summary_csv),
            "comparisons_csv": str(comparisons_csv),
            "lifecycle_events_csv": str(events_csv),
            "lineage_final_csv": str(lineage_csv),
            "summary_plot_png": str(summary_plot) if summary_plot.exists() else "",
            "alive_population_plot_png": str(alive_plot) if alive_plot.exists() else "",
        }
    )
    return TestResult(
        name="lifecycle_self_scaling",
        status=status,
        summary={
            "tier_summary": tier_summary,
            "aggregates": aggregates,
            "comparisons": comparisons,
            "tasks": tier_summary["tasks"],
            "cases": tier_summary["cases"],
            "seeds": tier_summary["seeds"],
            "backend": args.backend,
            "claim_boundary": "Software-only lifecycle/self-scaling benchmark; not hardware lifecycle evidence and not external-baseline superiority.",
        },
        criteria=criteria,
        artifacts=artifacts,
        failure_reason=failure_reason,
    )


def write_latest(output_dir: Path, report_path: Path, manifest_path: Path, summary_csv: Path, status: str) -> None:
    latest_path = ROOT / "controlled_test_output" / "tier6_1_latest_manifest.json"
    write_json(
        latest_path,
        {
            "generated_at_utc": utc_now(),
            "tier": TIER,
            "status": status,
            "output_dir": str(output_dir),
            "manifest": str(manifest_path),
            "report": str(report_path),
            "summary_csv": str(summary_csv),
            "canonical": False,
            "claim": "Latest Tier 6.1 lifecycle/self-scaling benchmark; promote only after review.",
        },
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Tier 6.1 CRA lifecycle/self-scaling benchmark.")
    parser.add_argument("--backend", choices=["nest", "brian2", "mock"], default="nest")
    parser.add_argument("--tasks", default=DEFAULT_TASKS)
    parser.add_argument("--cases", default=DEFAULT_CASES)
    parser.add_argument("--steps", type=int, default=960)
    parser.add_argument("--base-seed", type=int, default=42)
    parser.add_argument("--seed-count", type=int, default=3)
    parser.add_argument("--task-seed", type=int, default=6100)
    parser.add_argument("--amplitude", type=float, default=DEFAULT_AMPLITUDE)
    parser.add_argument("--dt-seconds", type=float, default=DEFAULT_DT_SECONDS)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--stop-on-fail", action="store_true")

    parser.add_argument("--cra-readout-lr", type=float, default=0.10)
    parser.add_argument("--cra-delayed-readout-lr", type=float, default=0.20)

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

    parser.add_argument("--recovery-window-trials", type=int, default=4)
    parser.add_argument("--recovery-accuracy-threshold", type=float, default=0.75)
    parser.add_argument("--min-lifecycle-births", type=int, default=1)
    parser.add_argument("--min-advantage-regimes", type=int, default=1)
    parser.add_argument("--min-tail-advantage", type=float, default=0.02)
    parser.add_argument("--min-all-accuracy-advantage", type=float, default=0.02)
    parser.add_argument("--min-corr-advantage", type=float, default=0.02)
    parser.add_argument("--min-recovery-advantage-steps", type=float, default=2.0)
    parser.add_argument("--min-active-efficiency-advantage", type=float, default=0.002)

    parser.add_argument("--fast-reproduction-cooldown-steps", type=int, default=3)
    parser.add_argument("--fast-maturity-steps", type=int, default=10)
    parser.add_argument("--fast-max-children-per-step", type=int, default=2)
    parser.add_argument("--fast-accuracy-survival-floor", type=float, default=0.52)
    parser.add_argument("--fast-accuracy-penalty-multiplier", type=float, default=0.35)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.steps <= 0:
        parser.error("--steps must be positive")
    if args.seed_count <= 0:
        parser.error("--seed-count must be positive")
    if args.max_delay < args.min_delay:
        parser.error("--max-delay must be >= --min-delay")
    parse_cases(args.cases)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = args.output_dir or (ROOT / "controlled_test_output" / f"tier6_1_{timestamp}")
    output_dir.mkdir(parents=True, exist_ok=True)

    result = run_tier(args, output_dir)
    manifest_path = output_dir / "tier6_1_results.json"
    report_path = output_dir / "tier6_1_report.md"
    summary_csv = output_dir / "tier6_1_summary.csv"
    manifest = {
        "tier": TIER,
        "generated_at_utc": utc_now(),
        "output_dir": str(output_dir),
        "command": " ".join(sys.argv),
        "backend": args.backend,
        "status": result.status,
        "result": result.to_dict(),
        "summary": result.summary["tier_summary"],
        "artifacts": {
            "summary_csv": str(summary_csv),
            "comparisons_csv": str(output_dir / "tier6_1_comparisons.csv"),
            "lifecycle_events_csv": str(output_dir / "tier6_1_lifecycle_events.csv"),
            "lineage_final_csv": str(output_dir / "tier6_1_lineage_final.csv"),
            "report_md": str(report_path),
            "summary_plot_png": str(output_dir / "tier6_1_lifecycle_summary.png"),
            "alive_population_plot_png": str(output_dir / "tier6_1_alive_population.png"),
        },
    }
    write_json(manifest_path, manifest)
    write_report(path=report_path, result=result, output_dir=output_dir, args=args)
    write_latest(output_dir, report_path, manifest_path, summary_csv, result.status)
    print(
        json.dumps(
            {
                "status": result.status,
                "output_dir": str(output_dir),
                "manifest": str(manifest_path),
                "report": str(report_path),
                "summary_csv": str(summary_csv),
                "failure_reason": result.failure_reason,
            },
            indent=2,
        ),
        flush=True,
    )
    return 0 if result.passed or not args.stop_on_fail else 1


if __name__ == "__main__":
    raise SystemExit(main())
