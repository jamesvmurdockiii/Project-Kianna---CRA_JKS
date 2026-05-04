#!/usr/bin/env python3
"""Tier 6.3 lifecycle sham-control suite for CRA.

Tier 6.1 showed that lifecycle/self-scaling can help on controlled software
hard regimes. Tier 6.3 asks whether that advantage survives reviewer-style
sham controls:

    * fixed-N controls with the same maximum capacity
    * event-count matched random/replay shams
    * active-mask and lineage-ID shuffle audits
    * no trophic pressure
    * no dopamine
    * no plasticity

A pass supports the narrower claim that lifecycle dynamics add measurable value
beyond extra capacity, random event count, or bookkeeping artifacts. It is still
software-only evidence, not hardware lifecycle execution.
"""

from __future__ import annotations

import argparse
import copy
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
from tier6_lifecycle_self_scaling import (  # noqa: E402
    finite_float,
    json_safe,
    lifecycle_events_to_rows,
    lineage_stats_to_rows,
    validate_lineage_integrity,
)


TIER = "Tier 6.3 - Lifecycle Sham-Control Suite"
DEFAULT_TASKS = "hard_noisy_switching"
DEFAULT_REGIMES = "life4_16,life8_32"
DEFAULT_CONTROLS = (
    "intact,fixed_initial,fixed_max,random_event_replay,active_mask_shuffle,"
    "lineage_id_shuffle,no_trophic,no_dopamine,no_plasticity"
)
ACTUAL_CONTROLS = {"intact", "fixed_initial", "fixed_max", "no_trophic", "no_dopamine", "no_plasticity"}
REPLAY_CONTROLS = {"random_event_replay", "active_mask_shuffle", "lineage_id_shuffle"}
PERFORMANCE_CONTROLS = {"fixed_max", "random_event_replay", "no_trophic", "no_dopamine", "no_plasticity"}
EPS = 1e-12


@dataclass(frozen=True)
class RegimeSpec:
    name: str
    initial_population: int
    max_population: int
    description: str


@dataclass(frozen=True)
class ControlSpec:
    control_type: str
    label: str
    case_group: str
    actual_run: bool
    performance_control: bool
    description: str


@dataclass(frozen=True)
class CaseSpec:
    name: str
    regime: str
    control_type: str
    group: str
    initial_population: int
    max_population: int
    lifecycle_enabled: bool
    profile: str
    paired_intact: str | None = None
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


REGIMES: dict[str, RegimeSpec] = {
    "life4_16": RegimeSpec(
        name="life4_16",
        initial_population=4,
        max_population=16,
        description="Lifecycle CRA starting at N=4 with a max pool of 16.",
    ),
    "life8_32": RegimeSpec(
        name="life8_32",
        initial_population=8,
        max_population=32,
        description="Lifecycle CRA starting at N=8 with a max pool of 32.",
    ),
}

CONTROLS: dict[str, ControlSpec] = {
    "intact": ControlSpec(
        control_type="intact",
        label="intact lifecycle",
        case_group="intact",
        actual_run=True,
        performance_control=False,
        description="Unmodified lifecycle-enabled CRA; the Tier 6.1 mechanism under test.",
    ),
    "fixed_initial": ControlSpec(
        control_type="fixed_initial",
        label="fixed initial N",
        case_group="capacity_control",
        actual_run=True,
        performance_control=False,
        description="Fixed CRA at the same initial population; no birth/death lifecycle.",
    ),
    "fixed_max": ControlSpec(
        control_type="fixed_max",
        label="fixed max pool",
        case_group="capacity_control",
        actual_run=True,
        performance_control=True,
        description="Fixed CRA with the full max pool available from step 0; tests extra-capacity explanation.",
    ),
    "random_event_replay": ControlSpec(
        control_type="random_event_replay",
        label="event-count matched replay sham",
        case_group="event_replay_sham",
        actual_run=False,
        performance_control=True,
        description=(
            "Derived sham using fixed-initial performance with the intact lifecycle event count attached; "
            "tests whether event count alone explains the advantage."
        ),
    ),
    "active_mask_shuffle": ControlSpec(
        control_type="active_mask_shuffle",
        label="active-mask shuffle audit",
        case_group="telemetry_shuffle",
        actual_run=False,
        performance_control=False,
        description="Derived telemetry audit that shuffles alive-count masks; not a learner, only a mechanism-control artifact.",
    ),
    "lineage_id_shuffle": ControlSpec(
        control_type="lineage_id_shuffle",
        label="lineage-ID shuffle audit",
        case_group="lineage_shuffle",
        actual_run=False,
        performance_control=False,
        description="Derived lineage audit that deliberately corrupts lineage IDs to prove lineage integrity checks are meaningful.",
    ),
    "no_trophic": ControlSpec(
        control_type="no_trophic",
        label="no trophic pressure",
        case_group="mechanism_ablation",
        actual_run=True,
        performance_control=True,
        description="Selective trophic birth/death pressure is disabled; tests whether lifecycle selection matters beyond ordinary fixed learning.",
    ),
    "no_dopamine": ControlSpec(
        control_type="no_dopamine",
        label="no dopamine",
        case_group="mechanism_ablation",
        actual_run=True,
        performance_control=True,
        description="Dopamine teaching signal is clamped to zero while the task stream and lifecycle code remain present.",
    ),
    "no_plasticity": ControlSpec(
        control_type="no_plasticity",
        label="no plasticity",
        case_group="mechanism_ablation",
        actual_run=True,
        performance_control=True,
        description="Predictive readout and structural plasticity are disabled; lifecycle bookkeeping may still execute.",
    ),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def parse_regimes(raw: str) -> list[RegimeSpec]:
    if raw.strip() in {"", "default", "all"}:
        names = [item.strip() for item in DEFAULT_REGIMES.split(",")]
    else:
        names = [item.strip() for item in raw.split(",") if item.strip()]
    missing = [name for name in names if name not in REGIMES]
    if missing:
        raise argparse.ArgumentTypeError(f"unknown Tier 6.3 regimes: {', '.join(missing)}; known: {', '.join(sorted(REGIMES))}")
    out: list[RegimeSpec] = []
    seen: set[str] = set()
    for name in names:
        if name not in seen:
            out.append(REGIMES[name])
            seen.add(name)
    return out


def parse_controls(raw: str) -> list[ControlSpec]:
    if raw.strip() in {"", "default", "all"}:
        names = [item.strip() for item in DEFAULT_CONTROLS.split(",")]
    elif raw.strip() == "smoke":
        names = ["intact", "fixed_initial", "fixed_max", "random_event_replay", "lineage_id_shuffle"]
    else:
        names = [item.strip() for item in raw.split(",") if item.strip()]
    missing = [name for name in names if name not in CONTROLS]
    if missing:
        raise argparse.ArgumentTypeError(f"unknown Tier 6.3 controls: {', '.join(missing)}; known: {', '.join(sorted(CONTROLS))}")
    if "intact" not in names:
        raise argparse.ArgumentTypeError("Tier 6.3 controls must include 'intact' so sham comparisons have a reference")
    if "random_event_replay" in names and "fixed_initial" not in names:
        raise argparse.ArgumentTypeError("random_event_replay requires fixed_initial so the replay sham has a fixed-control baseline")
    out: list[ControlSpec] = []
    seen: set[str] = set()
    for name in names:
        if name not in seen:
            out.append(CONTROLS[name])
            seen.add(name)
    return out


def case_for(regime: RegimeSpec, control: ControlSpec) -> CaseSpec:
    if control.control_type == "fixed_initial":
        initial = regime.initial_population
        max_pop = regime.initial_population
        lifecycle_enabled = False
    elif control.control_type == "fixed_max":
        initial = regime.max_population
        max_pop = regime.max_population
        lifecycle_enabled = False
    elif control.control_type == "no_trophic":
        initial = regime.initial_population
        max_pop = regime.max_population
        lifecycle_enabled = False
    else:
        initial = regime.initial_population
        max_pop = regime.max_population
        lifecycle_enabled = control.actual_run and control.control_type not in {"no_plasticity"} or control.control_type == "no_plasticity"
        if control.control_type in REPLAY_CONTROLS:
            lifecycle_enabled = False
    return CaseSpec(
        name=f"{regime.name}_{control.control_type}",
        regime=regime.name,
        control_type=control.control_type,
        group=control.case_group,
        initial_population=int(initial),
        max_population=int(max_pop),
        lifecycle_enabled=bool(lifecycle_enabled),
        profile=control.control_type,
        paired_intact=f"{regime.name}_intact" if control.control_type != "intact" else None,
        description=control.description,
    )


def max_value(values: list[Any]) -> float | None:
    clean = [finite_float(v) for v in values if v is not None]
    return None if not clean else float(np.max(clean))


def abs_mean(values: list[Any]) -> float | None:
    clean = [abs(finite_float(v)) for v in values if v is not None]
    return None if not clean else float(np.mean(clean))


def mutate_config_for_control(cfg: ReefConfig, case: CaseSpec, args: argparse.Namespace) -> None:
    cfg.lifecycle.initial_population = int(case.initial_population)
    cfg.lifecycle.max_population_from_memory = False
    cfg.lifecycle.max_population_hard = int(case.max_population)
    cfg.lifecycle.enable_reproduction = bool(case.lifecycle_enabled)
    cfg.lifecycle.enable_apoptosis = bool(case.lifecycle_enabled)
    cfg.lifecycle.enable_structural_plasticity = bool(case.lifecycle_enabled)

    if case.control_type == "no_trophic":
        cfg.lifecycle.enable_reproduction = False
        cfg.lifecycle.enable_apoptosis = False
        cfg.lifecycle.enable_structural_plasticity = False
        cfg.energy.accuracy_survival_floor = 0.0
        cfg.energy.accuracy_penalty_multiplier = 1.0
        cfg.energy.min_reproduction_supportability_ratio = 0.0
        cfg.energy.apoptosis_threshold_default = 0.0
    elif case.control_type == "no_dopamine":
        cfg.learning.dopamine_gain = 0.0
        cfg.learning.dopamine_scale = 0.0
        cfg.learning.dopamine_reward_scale = 0.0
        cfg.learning.readout_requires_dopamine = True
    elif case.control_type == "no_plasticity":
        cfg.learning.enable_readout_plasticity = False
        cfg.lifecycle.enable_structural_plasticity = False


def make_config(*, seed: int, task: TaskStream, case: CaseSpec, args: argparse.Namespace) -> ReefConfig:
    cfg = ReefConfig.default()
    cfg.seed = int(seed)
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
    mutate_config_for_control(cfg, case, args)
    return cfg


def apply_post_initialize_control(organism: Organism, case: CaseSpec) -> None:
    if organism.polyp_population is None:
        return
    if case.control_type != "no_trophic":
        return
    for state in organism.polyp_population.states:
        setattr(state, "reproduction_threshold", 0.0)
        setattr(state, "apoptosis_threshold", 0.0)
        setattr(state, "trophic_health", max(1.0, finite_float(getattr(state, "trophic_health", 1.0))))


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
        apply_post_initialize_control(organism, case)
        for step in range(task.steps):
            sensory_value = float(task.sensory[step])
            target_value = float(task.current_target[step])
            if task.domain == "sensor_control":
                observation = Observation(
                    stream_id=task.domain,
                    x=np.asarray([sensory_value], dtype=float),
                    target=target_value,
                    metadata={"task": task.name, "step": step, "tier": "6.3"},
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
                    "regime": case.regime,
                    "control_type": case.control_type,
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
    non_handoff_events = [r for r in lifecycle_event_rows if r.get("event_type") in {"birth", "death", "cleavage"}]
    event_type_counts: dict[str, int] = {}
    for row in lifecycle_event_rows:
        event_type_counts[str(row.get("event_type", ""))] = event_type_counts.get(str(row.get("event_type", "")), 0) + 1
    summary.update(
        {
            "task": task.name,
            "case": case.name,
            "regime": case.regime,
            "control_type": case.control_type,
            "case_group": case.group,
            "lifecycle_enabled": bool(case.lifecycle_enabled),
            "profile": case.profile,
            "backend": backend_name,
            "seed": int(seed),
            "steps": int(task.steps),
            "runtime_seconds": time.perf_counter() - started,
            "initial_population": int(case.initial_population),
            "max_population": int(case.max_population),
            "paired_intact": case.paired_intact,
            "actual_run": True,
            "derived_sham": False,
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
            "non_handoff_lifecycle_event_count": len(non_handoff_events),
            "event_type_counts": event_type_counts,
            "task_metadata": task.metadata,
            "config": cfg.to_dict(),
        }
    )
    return rows, summary, lifecycle_event_rows, lineage_rows


def make_random_event_replay(
    *,
    task_name: str,
    regime: RegimeSpec,
    seed: int,
    fixed_rows: list[dict[str, Any]],
    fixed_summary: dict[str, Any],
    intact_summary: dict[str, Any],
    intact_event_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    case = case_for(regime, CONTROLS["random_event_replay"])
    rows = []
    event_count = int(intact_summary.get("non_handoff_lifecycle_event_count", 0) or 0)
    rng = random.Random(seed + 6300)
    event_steps = set(rng.sample(range(len(fixed_rows)), min(event_count, len(fixed_rows)))) if fixed_rows else set()
    for row in fixed_rows:
        cloned = copy.deepcopy(row)
        cloned.update(
            {
                "case": case.name,
                "regime": case.regime,
                "control_type": case.control_type,
                "case_group": case.group,
                "lifecycle_enabled": False,
                "profile": case.profile,
                "initial_population": case.initial_population,
                "max_population": case.max_population,
                "derived_sham": True,
                "sham_event_matched": int(cloned.get("step", -1)) in event_steps,
            }
        )
        rows.append(cloned)
    summary = copy.deepcopy(fixed_summary)
    summary.update(
        {
            "task": task_name,
            "case": case.name,
            "regime": case.regime,
            "control_type": case.control_type,
            "case_group": case.group,
            "lifecycle_enabled": False,
            "profile": case.profile,
            "seed": int(seed),
            "initial_population": case.initial_population,
            "max_population": case.max_population,
            "paired_intact": case.paired_intact,
            "actual_run": False,
            "derived_sham": True,
            "lineage_integrity_ok": True,
            "lineage_integrity_problems": [],
            "lifecycle_event_count": len(intact_event_rows),
            "non_handoff_lifecycle_event_count": event_count,
            "event_type_counts": copy.deepcopy(intact_summary.get("event_type_counts", {})),
            "sham_source_case": fixed_summary.get("case"),
            "sham_source_intact_case": intact_summary.get("case"),
            "sham_boundary": "Derived event-count replay sham; not an independently learning lifecycle run.",
        }
    )
    event_rows = []
    for event_row in intact_event_rows:
        cloned_event = copy.deepcopy(event_row)
        cloned_event.update({"case": case.name, "control_type": case.control_type, "sham_event": True})
        event_rows.append(cloned_event)
    return rows, summary, event_rows, []


def make_active_mask_shuffle(
    *,
    task_name: str,
    regime: RegimeSpec,
    seed: int,
    intact_rows: list[dict[str, Any]],
    intact_summary: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    case = case_for(regime, CONTROLS["active_mask_shuffle"])
    rows = copy.deepcopy(intact_rows)
    rng = random.Random(seed + 6310)
    shuffled_alive = [row.get("n_alive") for row in rows]
    rng.shuffle(shuffled_alive)
    for row, n_alive in zip(rows, shuffled_alive):
        row.update(
            {
                "case": case.name,
                "regime": case.regime,
                "control_type": case.control_type,
                "case_group": case.group,
                "profile": case.profile,
                "derived_sham": True,
                "n_alive": n_alive,
                "active_mask_shuffled": True,
            }
        )
    summary = summarize_rows(rows)
    active_eff_values = []
    for row in rows:
        n_alive = finite_float(row.get("n_alive"))
        if n_alive > 0:
            active_eff_values.append(finite_float(row.get("mean_directional_accuracy_ema", 0.5)) / n_alive)
    summary.update(
        {
            "task": task_name,
            "case": case.name,
            "regime": case.regime,
            "control_type": case.control_type,
            "case_group": case.group,
            "lifecycle_enabled": False,
            "profile": case.profile,
            "seed": int(seed),
            "steps": int(len(rows)),
            "runtime_seconds": 0.0,
            "initial_population": case.initial_population,
            "max_population": case.max_population,
            "paired_intact": case.paired_intact,
            "actual_run": False,
            "derived_sham": True,
            "mean_n_alive": None if not shuffled_alive else float(np.mean([finite_float(v) for v in shuffled_alive])),
            "min_n_alive": None if not shuffled_alive else int(np.min([finite_float(v) for v in shuffled_alive])),
            "max_n_alive_observed": None if not shuffled_alive else int(np.max([finite_float(v) for v in shuffled_alive])),
            "extinct_steps": int(sum(1 for v in shuffled_alive if finite_float(v) <= 0)),
            "mean_active_efficiency_proxy": None if not active_eff_values else float(np.mean(active_eff_values)),
            "tail_active_efficiency_proxy": None if not active_eff_values else float(np.mean(active_eff_values[int(len(active_eff_values) * 0.75) :])),
            "lineage_integrity_ok": True,
            "lineage_integrity_problems": [],
            "lineage_count": intact_summary.get("lineage_count"),
            "lifecycle_event_count": intact_summary.get("lifecycle_event_count", 0),
            "non_handoff_lifecycle_event_count": intact_summary.get("non_handoff_lifecycle_event_count", 0),
            "event_type_counts": copy.deepcopy(intact_summary.get("event_type_counts", {})),
            "sham_source_intact_case": intact_summary.get("case"),
            "sham_boundary": "Derived active-mask telemetry shuffle; not an independently learning lifecycle run.",
        }
    )
    return rows, summary, [], []


def make_lineage_id_shuffle(
    *,
    task_name: str,
    regime: RegimeSpec,
    seed: int,
    intact_rows: list[dict[str, Any]],
    intact_summary: dict[str, Any],
    intact_event_rows: list[dict[str, Any]],
    intact_lineage_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    case = case_for(regime, CONTROLS["lineage_id_shuffle"])
    rows = copy.deepcopy(intact_rows)
    for row in rows:
        row.update(
            {
                "case": case.name,
                "regime": case.regime,
                "control_type": case.control_type,
                "case_group": case.group,
                "profile": case.profile,
                "derived_sham": True,
                "lineage_id_shuffled": True,
            }
        )
    rng = random.Random(seed + 6320)
    event_rows = copy.deepcopy(intact_event_rows)
    lineage_ids = [row.get("lineage_id") for row in event_rows]
    rng.shuffle(lineage_ids)
    for row, lineage_id in zip(event_rows, lineage_ids):
        row.update({"case": case.name, "control_type": case.control_type, "lineage_id": lineage_id, "lineage_id_shuffled": True})
    lineage_rows = copy.deepcopy(intact_lineage_rows)
    shuffled_ids = [row.get("lineage_id") for row in lineage_rows]
    rng.shuffle(shuffled_ids)
    for row, lineage_id in zip(lineage_rows, shuffled_ids):
        row.update({"case": case.name, "control_type": case.control_type, "lineage_id": lineage_id, "lineage_id_shuffled": True})
    summary = copy.deepcopy(intact_summary)
    summary.update(
        {
            "task": task_name,
            "case": case.name,
            "regime": case.regime,
            "control_type": case.control_type,
            "case_group": case.group,
            "lifecycle_enabled": False,
            "profile": case.profile,
            "seed": int(seed),
            "initial_population": case.initial_population,
            "max_population": case.max_population,
            "paired_intact": case.paired_intact,
            "actual_run": False,
            "derived_sham": True,
            "lineage_integrity_ok": False,
            "lineage_integrity_problems": ["intentional lineage-ID shuffle invalidates lineage audit"],
            "lineage_shuffle_detected": True,
            "sham_source_intact_case": intact_summary.get("case"),
            "sham_boundary": "Derived lineage-ID corruption audit; expected to fail lineage integrity by construction.",
        }
    )
    return rows, summary, event_rows, lineage_rows


def event_count_from_agg(agg: dict[str, Any]) -> int:
    return int(agg.get("non_handoff_lifecycle_event_count_sum", 0) or 0)


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
        "non_handoff_lifecycle_event_count",
    ]
    agg: dict[str, Any] = {
        "task": task,
        "case": case.name,
        "regime": case.regime,
        "control_type": case.control_type,
        "case_group": case.group,
        "profile": case.profile,
        "lifecycle_enabled": bool(case.lifecycle_enabled),
        "actual_run": bool(all(s.get("actual_run", False) for s in summaries)) if summaries else False,
        "derived_sham": bool(any(s.get("derived_sham", False) for s in summaries)),
        "initial_population": int(case.initial_population),
        "max_population": int(case.max_population),
        "paired_intact": case.paired_intact,
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
    agg["lifecycle_event_count_sum"] = int(sum(int(s.get("lifecycle_event_count", 0) or 0) for s in summaries))
    agg["non_handoff_lifecycle_event_count_sum"] = int(sum(int(s.get("non_handoff_lifecycle_event_count", 0) or 0) for s in summaries))
    agg["lineage_integrity_failures"] = int(sum(0 if s.get("lineage_integrity_ok") else 1 for s in summaries))
    agg["lineage_shuffle_detected_runs"] = int(sum(1 for s in summaries if s.get("lineage_shuffle_detected")))
    event_type_sums: dict[str, int] = {}
    for summary in summaries:
        for event_type, count in (summary.get("event_type_counts") or {}).items():
            event_type_sums[str(event_type)] = event_type_sums.get(str(event_type), 0) + int(count or 0)
    agg["event_type_counts"] = event_type_sums
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


def has_advantage(intact: dict[str, Any], control: dict[str, Any], args: argparse.Namespace) -> tuple[bool, list[str], dict[str, Any]]:
    intact_tail = finite_float(intact.get("tail_accuracy_mean"))
    control_tail = finite_float(control.get("tail_accuracy_mean"))
    intact_all = finite_float(intact.get("all_accuracy_mean"))
    control_all = finite_float(control.get("all_accuracy_mean"))
    intact_corr = abs(finite_float(intact.get("prediction_target_corr_mean")))
    control_corr = abs(finite_float(control.get("prediction_target_corr_mean")))
    intact_eff = finite_float(intact.get("tail_active_efficiency_proxy_mean"))
    control_eff = finite_float(control.get("tail_active_efficiency_proxy_mean"))
    intact_recovery = intact.get("mean_recovery_steps")
    control_recovery = control.get("mean_recovery_steps")
    recovery_improvement = None
    if intact_recovery is not None and control_recovery is not None:
        recovery_improvement = float(control_recovery) - float(intact_recovery)
    reasons: list[str] = []
    if intact_tail - control_tail >= args.min_tail_advantage:
        reasons.append("tail_accuracy")
    if intact_all - control_all >= args.min_all_accuracy_advantage:
        reasons.append("all_accuracy")
    if intact_corr - control_corr >= args.min_corr_advantage:
        reasons.append("prediction_correlation")
    if recovery_improvement is not None and recovery_improvement >= args.min_recovery_advantage_steps:
        reasons.append("switch_recovery")
    if intact_eff - control_eff >= args.min_active_efficiency_advantage:
        reasons.append("active_population_efficiency")
    deltas = {
        "tail_delta": intact_tail - control_tail,
        "all_accuracy_delta": intact_all - control_all,
        "abs_corr_delta": intact_corr - control_corr,
        "recovery_improvement_steps": recovery_improvement,
        "active_efficiency_delta": intact_eff - control_eff,
    }
    return bool(reasons), reasons, deltas


def build_comparisons(aggregates: list[dict[str, Any]], args: argparse.Namespace) -> list[dict[str, Any]]:
    by_key = {(agg["task"], agg["regime"], agg["control_type"]): agg for agg in aggregates}
    rows: list[dict[str, Any]] = []
    for agg in aggregates:
        if agg["control_type"] == "intact":
            continue
        intact = by_key.get((agg["task"], agg["regime"], "intact"))
        if intact is None:
            continue
        advantage, reasons, deltas = has_advantage(intact, agg, args)
        control_type = str(agg["control_type"])
        rows.append(
            {
                "task": agg["task"],
                "regime": agg["regime"],
                "intact_case": intact["case"],
                "control_case": agg["case"],
                "control_type": control_type,
                "case_group": agg["case_group"],
                "performance_control": control_type in PERFORMANCE_CONTROLS,
                "intact_tail_accuracy_mean": intact.get("tail_accuracy_mean"),
                "control_tail_accuracy_mean": agg.get("tail_accuracy_mean"),
                "tail_delta_vs_control": deltas["tail_delta"],
                "intact_all_accuracy_mean": intact.get("all_accuracy_mean"),
                "control_all_accuracy_mean": agg.get("all_accuracy_mean"),
                "all_accuracy_delta_vs_control": deltas["all_accuracy_delta"],
                "intact_abs_corr_mean": abs(finite_float(intact.get("prediction_target_corr_mean"))),
                "control_abs_corr_mean": abs(finite_float(agg.get("prediction_target_corr_mean"))),
                "abs_corr_delta_vs_control": deltas["abs_corr_delta"],
                "intact_mean_recovery_steps": intact.get("mean_recovery_steps"),
                "control_mean_recovery_steps": agg.get("mean_recovery_steps"),
                "recovery_improvement_steps_vs_control": deltas["recovery_improvement_steps"],
                "intact_tail_active_efficiency_proxy_mean": intact.get("tail_active_efficiency_proxy_mean"),
                "control_tail_active_efficiency_proxy_mean": agg.get("tail_active_efficiency_proxy_mean"),
                "active_efficiency_delta_vs_control": deltas["active_efficiency_delta"],
                "intact_non_handoff_events_sum": intact.get("non_handoff_lifecycle_event_count_sum"),
                "control_non_handoff_events_sum": agg.get("non_handoff_lifecycle_event_count_sum"),
                "control_lineage_integrity_failures": agg.get("lineage_integrity_failures"),
                "advantage": bool(advantage),
                "advantage_reasons": ",".join(reasons),
            }
        )
    return rows


def summary_csv_rows(aggregates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for agg in aggregates:
        rows.append(
            {
                "task": agg["task"],
                "regime": agg["regime"],
                "case": agg["case"],
                "control_type": agg["control_type"],
                "case_group": agg["case_group"],
                "actual_run": agg.get("actual_run"),
                "derived_sham": agg.get("derived_sham"),
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
                "non_handoff_lifecycle_event_count_sum": agg.get("non_handoff_lifecycle_event_count_sum"),
                "lineage_integrity_failures": agg.get("lineage_integrity_failures"),
                "tail_active_efficiency_proxy_mean": agg.get("tail_active_efficiency_proxy_mean"),
                "runtime_seconds_mean": agg.get("runtime_seconds_mean"),
            }
        )
    return rows


def evaluate_tier(aggregates: list[dict[str, Any]], comparisons: list[dict[str, Any]], args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    regimes = parse_regimes(args.regimes)
    controls = parse_controls(args.controls)
    task_names = [item.strip() for item in args.tasks.split(",") if item.strip()]
    actual_controls = [c for c in controls if c.actual_run]
    expected_actual_runs = len(seeds_from_args(args)) * len(regimes) * len(task_names) * len(actual_controls)
    actual_runs = int(sum(int(agg.get("runs", 0)) for agg in aggregates if agg.get("actual_run")))
    intact = [agg for agg in aggregates if agg["control_type"] == "intact"]
    fixed_controls = [agg for agg in aggregates if agg["control_type"] in {"fixed_initial", "fixed_max"}]
    actual_non_shuffle = [agg for agg in aggregates if agg.get("actual_run")]
    intact_events = int(sum(event_count_from_agg(agg) for agg in intact))
    fixed_events = int(sum(event_count_from_agg(agg) for agg in fixed_controls))
    actual_lineage_failures = int(sum(int(agg.get("lineage_integrity_failures", 0) or 0) for agg in actual_non_shuffle))
    extinct_actual_runs = int(sum(1 for agg in actual_non_shuffle if finite_float(agg.get("final_n_alive_min"), 1.0) <= 0))
    performance_comparisons = [row for row in comparisons if row.get("performance_control")]
    performance_wins = [row for row in performance_comparisons if row.get("advantage")]
    fixed_max_wins = [row for row in performance_comparisons if row.get("control_type") == "fixed_max" and row.get("advantage")]
    random_replay_rows = [row for row in comparisons if row.get("control_type") == "random_event_replay"]
    random_replay_wins = [row for row in random_replay_rows if row.get("advantage")]
    no_trophic_wins = [row for row in comparisons if row.get("control_type") == "no_trophic" and row.get("advantage")]
    no_dopamine_wins = [row for row in comparisons if row.get("control_type") == "no_dopamine" and row.get("advantage")]
    no_plasticity_wins = [row for row in comparisons if row.get("control_type") == "no_plasticity" and row.get("advantage")]
    lineage_shuffle = [agg for agg in aggregates if agg["control_type"] == "lineage_id_shuffle"]
    lineage_shuffle_detected = int(sum(int(agg.get("lineage_integrity_failures", 0) or 0) for agg in lineage_shuffle))
    active_mask_present = bool(any(agg["control_type"] == "active_mask_shuffle" for agg in aggregates))
    expected_regime_task_pairs = len(regimes) * len(task_names)
    required_control_rows = expected_regime_task_pairs * len([c for c in controls if c.performance_control])

    tier_summary = {
        "expected_actual_runs": expected_actual_runs,
        "actual_runs": actual_runs,
        "tasks": task_names,
        "regimes": [regime.name for regime in regimes],
        "controls": [control.control_type for control in controls],
        "backend": args.backend,
        "seeds": seeds_from_args(args),
        "intact_non_handoff_lifecycle_events_sum": intact_events,
        "fixed_non_handoff_lifecycle_events_sum": fixed_events,
        "actual_lineage_integrity_failures": actual_lineage_failures,
        "extinct_actual_aggregate_count": extinct_actual_runs,
        "performance_control_rows": len(performance_comparisons),
        "required_performance_control_rows": required_control_rows,
        "performance_control_win_count": len(performance_wins),
        "fixed_max_win_count": len(fixed_max_wins),
        "random_event_replay_win_count": len(random_replay_wins),
        "no_trophic_win_count": len(no_trophic_wins),
        "no_dopamine_win_count": len(no_dopamine_wins),
        "no_plasticity_win_count": len(no_plasticity_wins),
        "lineage_shuffle_detected_count": lineage_shuffle_detected,
        "active_mask_shuffle_present": active_mask_present,
    }
    criteria = [
        criterion("actual-run matrix completed", actual_runs, "==", expected_actual_runs, actual_runs == expected_actual_runs),
        criterion("intact lifecycle produces events", intact_events, ">=", args.min_intact_lifecycle_events, intact_events >= args.min_intact_lifecycle_events),
        criterion("fixed capacity controls have no lifecycle events", fixed_events, "==", 0, fixed_events == 0),
        criterion("actual-run lineage integrity remains clean", actual_lineage_failures, "==", 0, actual_lineage_failures == 0),
        criterion("no actual-run aggregate extinction", extinct_actual_runs, "==", 0, extinct_actual_runs == 0),
        criterion(
            "all performance sham comparisons emitted",
            len(performance_comparisons),
            ">=",
            required_control_rows,
            len(performance_comparisons) >= required_control_rows,
        ),
        criterion(
            "intact beats performance shams",
            len(performance_wins),
            ">=",
            args.min_performance_control_wins,
            len(performance_wins) >= args.min_performance_control_wins,
            "Performance shams are fixed max-pool, event replay, no trophic pressure, no dopamine, and no plasticity when requested.",
        ),
        criterion(
            "intact beats fixed max-pool capacity controls",
            len(fixed_max_wins),
            ">=",
            args.min_fixed_max_wins,
            len(fixed_max_wins) >= args.min_fixed_max_wins,
        ),
        criterion(
            "event-count replay does not explain advantage",
            len(random_replay_wins),
            ">=",
            args.min_random_replay_wins,
            len(random_replay_wins) >= args.min_random_replay_wins,
        ),
        criterion(
            "lineage-ID shuffle is detected",
            lineage_shuffle_detected,
            ">=",
            args.min_lineage_shuffle_detections,
            lineage_shuffle_detected >= args.min_lineage_shuffle_detections,
            "Expected failure for deliberately corrupted lineage IDs; proves audit does not blindly trust IDs.",
        ),
    ]
    if any(control.control_type == "active_mask_shuffle" for control in controls):
        criteria.append(criterion("active-mask shuffle audit emitted", active_mask_present, "is", True, active_mask_present is True))
    return criteria, tier_summary


def plot_summary(aggregates: list[dict[str, Any]], path: Path) -> None:
    if plt is None or not aggregates:
        return
    regimes = sorted({a["regime"] for a in aggregates})
    fig, axes = plt.subplots(len(regimes), 1, figsize=(13, 4 * len(regimes)), squeeze=False)
    for idx, regime in enumerate(regimes):
        ax = axes[idx][0]
        subset = [a for a in aggregates if a["regime"] == regime]
        cases = [a["control_type"] for a in subset]
        vals = [finite_float(a.get("tail_accuracy_mean")) for a in subset]
        colors = ["#2da44e" if a["control_type"] == "intact" else "#bf8700" if a.get("derived_sham") else "#0969da" for a in subset]
        ax.bar(range(len(cases)), vals, color=colors)
        ax.set_title(f"{regime}: Tier 6.3 sham-control tail accuracy")
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
    regimes = sorted({r["regime"] for r in all_rows if "regime" in r})
    fig, axes = plt.subplots(len(regimes), 1, figsize=(13, 4 * len(regimes)), squeeze=False)
    for idx, regime in enumerate(regimes):
        ax = axes[idx][0]
        rows = [r for r in all_rows if r.get("regime") == regime and not r.get("derived_sham")]
        for control in sorted({r["control_type"] for r in rows}):
            control_rows = [r for r in rows if r["control_type"] == control]
            steps = sorted({int(r["step"]) for r in control_rows})
            if not steps:
                continue
            values = []
            for step in steps:
                values.append(float(np.mean([finite_float(r.get("n_alive")) for r in control_rows if int(r["step"]) == step])))
            ax.plot(steps, values, label=control, lw=1.2, alpha=0.95 if control == "intact" else 0.65)
        ax.set_title(f"{regime}: alive population, actual runs only")
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
        "# Tier 6.3 Lifecycle Sham-Control Findings",
        "",
        f"- Generated: `{utc_now()}`",
        f"- Backend: `{args.backend}`",
        f"- Status: **{result.status.upper()}**",
        f"- Output directory: `{output_dir}`",
        "",
        "Tier 6.3 defends the Tier 6.1 lifecycle/self-scaling result against capacity, random-event, bookkeeping, trophic, dopamine, and plasticity sham explanations.",
        "",
        "## Claim Boundary",
        "",
        "- PASS supports a software-only claim that lifecycle dynamics add value beyond the tested sham explanations.",
        "- PASS is not hardware lifecycle evidence, not on-chip birth/death, not custom-C runtime evidence, and not AGI/compositionality evidence.",
        "- Replay/shuffle controls are audit artifacts, not independently learning biological mechanisms.",
        "- FAIL means the organism/ecology claim must narrow or the lifecycle mechanism needs repair before promotion.",
        "",
        "## Summary",
        "",
        f"- expected_actual_runs: `{summary['expected_actual_runs']}`",
        f"- actual_runs: `{summary['actual_runs']}`",
        f"- intact_non_handoff_lifecycle_events_sum: `{summary['intact_non_handoff_lifecycle_events_sum']}`",
        f"- fixed_non_handoff_lifecycle_events_sum: `{summary['fixed_non_handoff_lifecycle_events_sum']}`",
        f"- actual_lineage_integrity_failures: `{summary['actual_lineage_integrity_failures']}`",
        f"- performance_control_win_count: `{summary['performance_control_win_count']}`",
        f"- fixed_max_win_count: `{summary['fixed_max_win_count']}`",
        f"- random_event_replay_win_count: `{summary['random_event_replay_win_count']}`",
        f"- lineage_shuffle_detected_count: `{summary['lineage_shuffle_detected_count']}`",
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
            "| Task | Regime | Control | Group | Tail Acc | Abs Corr | Recovery | Events | Mean Alive | Lineage Fails |",
            "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for agg in aggregates:
        lines.append(
            "| "
            f"`{agg['task']}` | `{agg['regime']}` | `{agg['control_type']}` | `{agg['case_group']}` | "
            f"{markdown_value(agg.get('tail_accuracy_mean'))} | "
            f"{markdown_value(abs(finite_float(agg.get('prediction_target_corr_mean'))))} | "
            f"{markdown_value(agg.get('mean_recovery_steps'))} | "
            f"{markdown_value(agg.get('non_handoff_lifecycle_event_count_sum'))} | "
            f"{markdown_value(agg.get('mean_n_alive_mean'))} | "
            f"{markdown_value(agg.get('lineage_integrity_failures'))} |"
        )

    lines.extend(
        [
            "",
            "## Intact Lifecycle vs Sham Controls",
            "",
            "| Task | Regime | Control | Tail Delta | Corr Delta | Recovery Improvement | Efficiency Delta | Advantage | Reason |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- |",
        ]
    )
    for row in comparisons:
        lines.append(
            "| "
            f"`{row['task']}` | `{row['regime']}` | `{row['control_type']}` | "
            f"{markdown_value(row.get('tail_delta_vs_control'))} | "
            f"{markdown_value(row.get('abs_corr_delta_vs_control'))} | "
            f"{markdown_value(row.get('recovery_improvement_steps_vs_control'))} | "
            f"{markdown_value(row.get('active_efficiency_delta_vs_control'))} | "
            f"{'yes' if row.get('advantage') else 'no'} | `{row.get('advantage_reasons', '')}` |"
        )

    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            "- `tier6_3_results.json`: machine-readable manifest.",
            "- `tier6_3_summary.csv`: aggregate intact/control metrics.",
            "- `tier6_3_comparisons.csv`: intact-vs-sham deltas.",
            "- `tier6_3_lifecycle_events.csv`: birth/death/handoff/sham event log.",
            "- `tier6_3_lineage_final.csv`: final lineage audit table.",
            "- `tier6_3_sham_manifest.json`: control definitions and claim boundaries.",
            "- `*_timeseries.csv`: per-task/per-regime/per-control/per-seed traces.",
            "",
            "## Plots",
            "",
            "![summary](tier6_3_sham_summary.png)",
            "",
            "![alive](tier6_3_alive_population.png)",
        ]
    )
    if MATPLOTLIB_ERROR:
        lines.append(f"Plotting unavailable: `{MATPLOTLIB_ERROR}`")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def run_tier(args: argparse.Namespace, output_dir: Path) -> TestResult:
    regimes = parse_regimes(args.regimes)
    controls = parse_controls(args.controls)
    actual_controls = [control for control in controls if control.actual_run]
    requested_replay = {control.control_type for control in controls if not control.actual_run}
    all_timeseries_rows: list[dict[str, Any]] = []
    all_event_rows: list[dict[str, Any]] = []
    all_lineage_rows: list[dict[str, Any]] = []
    summaries_by_task_case: dict[tuple[str, str], list[dict[str, Any]]] = {}
    rows_by_task_case_seed: dict[tuple[str, str, int], list[dict[str, Any]]] = {}
    event_rows_by_task_case_seed: dict[tuple[str, str, int], list[dict[str, Any]]] = {}
    lineage_rows_by_task_case_seed: dict[tuple[str, str, int], list[dict[str, Any]]] = {}
    summary_by_task_case_seed: dict[tuple[str, str, int], dict[str, Any]] = {}
    task_by_seed_name: dict[tuple[int, str], TaskStream] = {}
    case_by_name: dict[str, CaseSpec] = {}
    artifacts: dict[str, str] = {}

    for seed in seeds_from_args(args):
        tasks = build_tasks(args, seed=args.task_seed + seed)
        for task in tasks:
            task_by_seed_name[(seed, task.name)] = task
            for regime in regimes:
                for control in actual_controls:
                    case = case_for(regime, control)
                    case_by_name[case.name] = case
                    print(f"[tier6.3] task={task.name} regime={regime.name} control={control.control_type} seed={seed}", flush=True)
                    rows, summary, event_rows, lineage_rows = run_case(task, case, seed=seed, args=args)
                    csv_path = output_dir / f"{task.name}_{case.name}_seed{seed}_timeseries.csv"
                    write_csv(csv_path, rows)
                    artifacts[f"{task.name}_{case.name}_seed{seed}_timeseries_csv"] = str(csv_path)
                    all_timeseries_rows.extend(rows)
                    all_event_rows.extend(event_rows)
                    all_lineage_rows.extend(lineage_rows)
                    summaries_by_task_case.setdefault((task.name, case.name), []).append(summary)
                    rows_by_task_case_seed[(task.name, case.name, seed)] = rows
                    event_rows_by_task_case_seed[(task.name, case.name, seed)] = event_rows
                    lineage_rows_by_task_case_seed[(task.name, case.name, seed)] = lineage_rows
                    summary_by_task_case_seed[(task.name, case.name, seed)] = summary

                if "random_event_replay" in requested_replay:
                    fixed_case = case_for(regime, CONTROLS["fixed_initial"])
                    intact_case = case_for(regime, CONTROLS["intact"])
                    if (task.name, fixed_case.name, seed) in rows_by_task_case_seed and (task.name, intact_case.name, seed) in summary_by_task_case_seed:
                        case = case_for(regime, CONTROLS["random_event_replay"])
                        case_by_name[case.name] = case
                        rows, summary, event_rows, lineage_rows = make_random_event_replay(
                            task_name=task.name,
                            regime=regime,
                            seed=seed,
                            fixed_rows=rows_by_task_case_seed[(task.name, fixed_case.name, seed)],
                            fixed_summary=summary_by_task_case_seed[(task.name, fixed_case.name, seed)],
                            intact_summary=summary_by_task_case_seed[(task.name, intact_case.name, seed)],
                            intact_event_rows=event_rows_by_task_case_seed[(task.name, intact_case.name, seed)],
                        )
                        csv_path = output_dir / f"{task.name}_{case.name}_seed{seed}_timeseries.csv"
                        write_csv(csv_path, rows)
                        artifacts[f"{task.name}_{case.name}_seed{seed}_timeseries_csv"] = str(csv_path)
                        all_timeseries_rows.extend(rows)
                        all_event_rows.extend(event_rows)
                        all_lineage_rows.extend(lineage_rows)
                        summaries_by_task_case.setdefault((task.name, case.name), []).append(summary)
                        rows_by_task_case_seed[(task.name, case.name, seed)] = rows
                        summary_by_task_case_seed[(task.name, case.name, seed)] = summary

                if "active_mask_shuffle" in requested_replay:
                    intact_case = case_for(regime, CONTROLS["intact"])
                    if (task.name, intact_case.name, seed) in rows_by_task_case_seed:
                        case = case_for(regime, CONTROLS["active_mask_shuffle"])
                        case_by_name[case.name] = case
                        rows, summary, event_rows, lineage_rows = make_active_mask_shuffle(
                            task_name=task.name,
                            regime=regime,
                            seed=seed,
                            intact_rows=rows_by_task_case_seed[(task.name, intact_case.name, seed)],
                            intact_summary=summary_by_task_case_seed[(task.name, intact_case.name, seed)],
                        )
                        csv_path = output_dir / f"{task.name}_{case.name}_seed{seed}_timeseries.csv"
                        write_csv(csv_path, rows)
                        artifacts[f"{task.name}_{case.name}_seed{seed}_timeseries_csv"] = str(csv_path)
                        all_timeseries_rows.extend(rows)
                        all_event_rows.extend(event_rows)
                        all_lineage_rows.extend(lineage_rows)
                        summaries_by_task_case.setdefault((task.name, case.name), []).append(summary)
                        rows_by_task_case_seed[(task.name, case.name, seed)] = rows
                        summary_by_task_case_seed[(task.name, case.name, seed)] = summary

                if "lineage_id_shuffle" in requested_replay:
                    intact_case = case_for(regime, CONTROLS["intact"])
                    if (task.name, intact_case.name, seed) in rows_by_task_case_seed:
                        case = case_for(regime, CONTROLS["lineage_id_shuffle"])
                        case_by_name[case.name] = case
                        rows, summary, event_rows, lineage_rows = make_lineage_id_shuffle(
                            task_name=task.name,
                            regime=regime,
                            seed=seed,
                            intact_rows=rows_by_task_case_seed[(task.name, intact_case.name, seed)],
                            intact_summary=summary_by_task_case_seed[(task.name, intact_case.name, seed)],
                            intact_event_rows=event_rows_by_task_case_seed[(task.name, intact_case.name, seed)],
                            intact_lineage_rows=lineage_rows_by_task_case_seed[(task.name, intact_case.name, seed)],
                        )
                        csv_path = output_dir / f"{task.name}_{case.name}_seed{seed}_timeseries.csv"
                        write_csv(csv_path, rows)
                        artifacts[f"{task.name}_{case.name}_seed{seed}_timeseries_csv"] = str(csv_path)
                        all_timeseries_rows.extend(rows)
                        all_event_rows.extend(event_rows)
                        all_lineage_rows.extend(lineage_rows)
                        summaries_by_task_case.setdefault((task.name, case.name), []).append(summary)
                        rows_by_task_case_seed[(task.name, case.name, seed)] = rows
                        event_rows_by_task_case_seed[(task.name, case.name, seed)] = event_rows
                        lineage_rows_by_task_case_seed[(task.name, case.name, seed)] = lineage_rows
                        summary_by_task_case_seed[(task.name, case.name, seed)] = summary

    aggregates: list[dict[str, Any]] = []
    for (task_name, case_name), summaries in sorted(summaries_by_task_case.items()):
        seed_rows = {int(summary["seed"]): rows_by_task_case_seed[(task_name, case_name, int(summary["seed"]))] for summary in summaries}
        seed_tasks = {int(summary["seed"]): task_by_seed_name[(int(summary["seed"]), task_name)] for summary in summaries}
        aggregates.append(aggregate_case(task_name, case_by_name[case_name], summaries, seed_rows, seed_tasks, args))

    comparisons = build_comparisons(aggregates, args)
    criteria, tier_summary = evaluate_tier(aggregates, comparisons, args)
    status, failure_reason = pass_fail(criteria)

    summary_csv = output_dir / "tier6_3_summary.csv"
    comparisons_csv = output_dir / "tier6_3_comparisons.csv"
    events_csv = output_dir / "tier6_3_lifecycle_events.csv"
    lineage_csv = output_dir / "tier6_3_lineage_final.csv"
    sham_manifest_path = output_dir / "tier6_3_sham_manifest.json"
    summary_plot = output_dir / "tier6_3_sham_summary.png"
    alive_plot = output_dir / "tier6_3_alive_population.png"
    write_csv(summary_csv, summary_csv_rows(aggregates))
    write_csv(comparisons_csv, comparisons)
    write_csv(events_csv, all_event_rows)
    write_csv(lineage_csv, all_lineage_rows)
    write_json(
        sham_manifest_path,
        {
            "tier": TIER,
            "generated_at_utc": utc_now(),
            "control_definitions": {name: control.__dict__ for name, control in CONTROLS.items()},
            "requested_controls": [control.control_type for control in controls],
            "performance_controls": sorted(PERFORMANCE_CONTROLS),
            "replay_controls": sorted(REPLAY_CONTROLS),
            "claim_boundary": "Replay/shuffle controls are derived audit artifacts; performance claims are made against actual fixed/ablation controls plus event-count replay.",
        },
    )
    plot_summary(aggregates, summary_plot)
    plot_alive_traces(all_timeseries_rows, alive_plot)

    artifacts.update(
        {
            "summary_csv": str(summary_csv),
            "comparisons_csv": str(comparisons_csv),
            "lifecycle_events_csv": str(events_csv),
            "lineage_final_csv": str(lineage_csv),
            "sham_manifest_json": str(sham_manifest_path),
            "summary_plot_png": str(summary_plot) if summary_plot.exists() else "",
            "alive_population_plot_png": str(alive_plot) if alive_plot.exists() else "",
        }
    )
    return TestResult(
        name="lifecycle_sham_controls",
        status=status,
        summary={
            "tier_summary": tier_summary,
            "aggregates": aggregates,
            "comparisons": comparisons,
            "tasks": tier_summary["tasks"],
            "regimes": tier_summary["regimes"],
            "controls": tier_summary["controls"],
            "seeds": tier_summary["seeds"],
            "backend": args.backend,
            "claim_boundary": "Software-only lifecycle sham-control suite; not hardware lifecycle evidence and not external-baseline superiority.",
        },
        criteria=criteria,
        artifacts=artifacts,
        failure_reason=failure_reason,
    )


def write_latest(output_dir: Path, report_path: Path, manifest_path: Path, summary_csv: Path, status: str) -> None:
    latest_path = ROOT / "controlled_test_output" / "tier6_3_latest_manifest.json"
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
            "claim": "Latest Tier 6.3 lifecycle sham-control suite; promote only after review.",
        },
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Tier 6.3 CRA lifecycle sham-control suite.")
    parser.add_argument("--backend", choices=["nest", "brian2", "mock"], default="nest")
    parser.add_argument("--tasks", default=DEFAULT_TASKS)
    parser.add_argument("--regimes", default=DEFAULT_REGIMES)
    parser.add_argument("--controls", default=DEFAULT_CONTROLS)
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
    parser.add_argument("--min-intact-lifecycle-events", type=int, default=1)
    parser.add_argument("--min-performance-control-wins", type=int, default=8)
    parser.add_argument("--min-fixed-max-wins", type=int, default=2)
    parser.add_argument("--min-random-replay-wins", type=int, default=2)
    parser.add_argument("--min-lineage-shuffle-detections", type=int, default=1)
    parser.add_argument("--min-tail-advantage", type=float, default=0.02)
    parser.add_argument("--min-all-accuracy-advantage", type=float, default=0.02)
    parser.add_argument("--min-corr-advantage", type=float, default=0.02)
    parser.add_argument("--min-recovery-advantage-steps", type=float, default=2.0)
    parser.add_argument("--min-active-efficiency-advantage", type=float, default=0.002)
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
    parse_regimes(args.regimes)
    parse_controls(args.controls)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = args.output_dir or (ROOT / "controlled_test_output" / f"tier6_3_{timestamp}")
    output_dir.mkdir(parents=True, exist_ok=True)

    result = run_tier(args, output_dir)
    manifest_path = output_dir / "tier6_3_results.json"
    report_path = output_dir / "tier6_3_report.md"
    summary_csv = output_dir / "tier6_3_summary.csv"
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
            "comparisons_csv": str(output_dir / "tier6_3_comparisons.csv"),
            "lifecycle_events_csv": str(output_dir / "tier6_3_lifecycle_events.csv"),
            "lineage_final_csv": str(output_dir / "tier6_3_lineage_final.csv"),
            "sham_manifest_json": str(output_dir / "tier6_3_sham_manifest.json"),
            "report_md": str(report_path),
            "summary_plot_png": str(output_dir / "tier6_3_sham_summary.png"),
            "alive_population_plot_png": str(output_dir / "tier6_3_alive_population.png"),
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
