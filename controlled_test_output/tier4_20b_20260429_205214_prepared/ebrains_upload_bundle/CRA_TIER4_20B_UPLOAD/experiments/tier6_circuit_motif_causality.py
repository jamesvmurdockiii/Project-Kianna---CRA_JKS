#!/usr/bin/env python3
"""Tier 6.4 circuit-motif causality suite for CRA.

Tier 6.3 defended lifecycle/self-scaling against sham explanations. Tier 6.4
asks the next reviewer question:

    Are the reef graph motifs doing causal work, or are they decorative labels?

The suite seeds a motif-diverse graph, runs intact CRA against predeclared motif
ablations, and records per-step motif message activity before learning/reward
updates. A pass supports a software-only claim that motif structure contributes
measurable behavior under the tested adaptive tasks.
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
from coral_reef_spinnaker.reef_network import EdgeType  # noqa: E402
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


TIER = "Tier 6.4 - Circuit Motif Causality"
DEFAULT_TASKS = "hard_noisy_switching"
DEFAULT_REGIMES = "life4_16,life8_32"
DEFAULT_VARIANTS = (
    "intact,no_feedforward,no_feedback,no_lateral,no_wta,"
    "random_graph_same_edge_count,motif_shuffled,monolithic_same_capacity"
)
PERFORMANCE_VARIANTS = {
    "no_feedforward",
    "no_feedback",
    "no_lateral",
    "no_wta",
    "random_graph_same_edge_count",
    "motif_shuffled",
    "monolithic_same_capacity",
}
RANDOM_OR_MONOLITHIC = {"random_graph_same_edge_count", "monolithic_same_capacity"}
EPS = 1e-12


@dataclass(frozen=True)
class RegimeSpec:
    name: str
    initial_population: int
    max_population: int
    description: str


@dataclass(frozen=True)
class VariantSpec:
    variant_type: str
    label: str
    group: str
    lifecycle_enabled: bool
    seed_graph: bool
    performance_control: bool
    description: str


@dataclass(frozen=True)
class CaseSpec:
    name: str
    regime: str
    variant_type: str
    group: str
    initial_population: int
    max_population: int
    lifecycle_enabled: bool
    seed_graph: bool
    paired_intact: str | None
    description: str


@dataclass(frozen=True)
class PlannedEdge:
    source_id: int
    target_id: int
    edge_type: str
    weight: float
    role: str


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

VARIANTS: dict[str, VariantSpec] = {
    "intact": VariantSpec(
        variant_type="intact",
        label="intact motif graph",
        group="intact",
        lifecycle_enabled=True,
        seed_graph=True,
        performance_control=False,
        description="Motif-diverse lifecycle CRA; the motif structure under test.",
    ),
    "no_feedforward": VariantSpec(
        variant_type="no_feedforward",
        label="no feedforward motif",
        group="motif_ablation",
        lifecycle_enabled=True,
        seed_graph=True,
        performance_control=True,
        description="Seeded graph with feedforward edges removed before the run.",
    ),
    "no_feedback": VariantSpec(
        variant_type="no_feedback",
        label="no feedback motif",
        group="motif_ablation",
        lifecycle_enabled=True,
        seed_graph=True,
        performance_control=True,
        description="Seeded graph with feedback/recurrent edges removed before the run.",
    ),
    "no_lateral": VariantSpec(
        variant_type="no_lateral",
        label="no lateral motif",
        group="motif_ablation",
        lifecycle_enabled=True,
        seed_graph=True,
        performance_control=True,
        description="Seeded graph with lateral coordination and lateral inhibition removed.",
    ),
    "no_wta": VariantSpec(
        variant_type="no_wta",
        label="no WTA / lateral inhibition",
        group="motif_ablation",
        lifecycle_enabled=True,
        seed_graph=True,
        performance_control=True,
        description="All-polyps readout plus no inhibitory lateral motif edges.",
    ),
    "random_graph_same_edge_count": VariantSpec(
        variant_type="random_graph_same_edge_count",
        label="random graph same edge count",
        group="same_capacity_graph_control",
        lifecycle_enabled=True,
        seed_graph=True,
        performance_control=True,
        description="Same number and weight signs as intact, but randomized source/target pairs.",
    ),
    "motif_shuffled": VariantSpec(
        variant_type="motif_shuffled",
        label="motif-label shuffled graph",
        group="same_edges_label_control",
        lifecycle_enabled=True,
        seed_graph=True,
        performance_control=True,
        description="Same source/target/weights as intact with motif labels shuffled.",
    ),
    "monolithic_same_capacity": VariantSpec(
        variant_type="monolithic_same_capacity",
        label="monolithic same capacity",
        group="monolithic_control",
        lifecycle_enabled=False,
        seed_graph=False,
        performance_control=True,
        description="Fixed max-pool CRA with graph message passing disabled.",
    ),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def safe_write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_csv(path, rows)


def safe_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, payload)


def parse_regimes(raw: str) -> list[RegimeSpec]:
    if raw.strip() in {"", "default", "all"}:
        names = [item.strip() for item in DEFAULT_REGIMES.split(",")]
    else:
        names = [item.strip() for item in raw.split(",") if item.strip()]
    missing = [name for name in names if name not in REGIMES]
    if missing:
        known = ", ".join(sorted(REGIMES))
        raise argparse.ArgumentTypeError(f"unknown Tier 6.4 regimes: {', '.join(missing)}; known: {known}")
    out: list[RegimeSpec] = []
    seen: set[str] = set()
    for name in names:
        if name not in seen:
            out.append(REGIMES[name])
            seen.add(name)
    return out


def parse_variants(raw: str) -> list[VariantSpec]:
    if raw.strip() in {"", "default", "all"}:
        names = [item.strip() for item in DEFAULT_VARIANTS.split(",")]
    elif raw.strip() == "smoke":
        names = ["intact", "no_feedforward", "random_graph_same_edge_count", "monolithic_same_capacity"]
    else:
        names = [item.strip() for item in raw.split(",") if item.strip()]
    missing = [name for name in names if name not in VARIANTS]
    if missing:
        known = ", ".join(sorted(VARIANTS))
        raise argparse.ArgumentTypeError(f"unknown Tier 6.4 variants: {', '.join(missing)}; known: {known}")
    if "intact" not in names:
        raise argparse.ArgumentTypeError("Tier 6.4 variants must include 'intact' so motif comparisons have a reference")
    out: list[VariantSpec] = []
    seen: set[str] = set()
    for name in names:
        if name not in seen:
            out.append(VARIANTS[name])
            seen.add(name)
    return out


def case_for(regime: RegimeSpec, variant: VariantSpec) -> CaseSpec:
    if variant.variant_type == "monolithic_same_capacity":
        initial = regime.max_population
        max_pop = regime.max_population
    else:
        initial = regime.initial_population
        max_pop = regime.max_population
    return CaseSpec(
        name=f"{regime.name}_{variant.variant_type}",
        regime=regime.name,
        variant_type=variant.variant_type,
        group=variant.group,
        initial_population=int(initial),
        max_population=int(max_pop),
        lifecycle_enabled=bool(variant.lifecycle_enabled),
        seed_graph=bool(variant.seed_graph),
        paired_intact=f"{regime.name}_intact" if variant.variant_type != "intact" else None,
        description=variant.description,
    )


def max_value(values: list[Any]) -> float | None:
    clean = [finite_float(v) for v in values if v is not None]
    return None if not clean else float(np.max(clean))


def mutate_config_for_case(cfg: ReefConfig, case: CaseSpec, args: argparse.Namespace) -> None:
    cfg.lifecycle.initial_population = int(case.initial_population)
    cfg.lifecycle.max_population_from_memory = False
    cfg.lifecycle.max_population_hard = int(case.max_population)
    cfg.lifecycle.enable_reproduction = bool(case.lifecycle_enabled)
    cfg.lifecycle.enable_apoptosis = bool(case.lifecycle_enabled)
    cfg.lifecycle.enable_structural_plasticity = bool(case.lifecycle_enabled)
    cfg.network.message_passing_steps = 0 if case.variant_type == "monolithic_same_capacity" else int(args.message_passing_steps)
    cfg.network.message_context_gain = float(args.message_context_gain)
    cfg.network.message_prediction_mix = float(args.message_prediction_mix)
    if case.variant_type == "no_wta":
        cfg.learning.winner_take_all_base = int(case.max_population)
        cfg.learning.wta_kappa = 1.0


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
    mutate_config_for_case(cfg, case, args)
    return cfg


def base_motif_plan(alive_ids: list[int], *, inhibitory_weight: float) -> list[PlannedEdge]:
    ids = list(alive_ids)
    if len(ids) < 2:
        return []
    split = max(1, len(ids) // 2)
    lower = ids[:split]
    upper = ids[split:] or ids[:]
    plan: list[PlannedEdge] = []

    for idx, src in enumerate(lower):
        dst = upper[idx % len(upper)]
        if src != dst:
            plan.append(PlannedEdge(src, dst, EdgeType.FEEDFORWARD, 0.35, "feedforward_excitation"))
        dst2 = upper[(idx + 1) % len(upper)]
        if src != dst2 and dst2 != dst:
            plan.append(PlannedEdge(src, dst2, EdgeType.FEEDFORWARD, 0.22, "feedforward_excitation"))

    for idx, src in enumerate(upper):
        dst = lower[idx % len(lower)]
        if src != dst:
            plan.append(PlannedEdge(src, dst, EdgeType.FEEDBACK, 0.24, "feedback_context"))
        dst2 = lower[(idx + 1) % len(lower)]
        if src != dst2 and dst2 != dst:
            plan.append(PlannedEdge(src, dst2, EdgeType.FEEDBACK, 0.16, "feedback_context"))

    groups = [lower, upper]
    for group in groups:
        if len(group) <= 1:
            continue
        for idx, src in enumerate(group):
            dst = group[(idx + 1) % len(group)]
            if src != dst:
                plan.append(PlannedEdge(src, dst, EdgeType.LATERAL, 0.18, "lateral_binding"))
            dst_back = group[(idx - 1) % len(group)]
            if src != dst_back and dst_back != dst:
                plan.append(PlannedEdge(src, dst_back, EdgeType.LATERAL, inhibitory_weight, "wta_lateral_inhibition"))

    # De-duplicate deterministically while preserving roles.
    deduped: list[PlannedEdge] = []
    seen: set[tuple[int, int, str]] = set()
    for edge in plan:
        key = (edge.source_id, edge.target_id, edge.role)
        if key not in seen:
            deduped.append(edge)
            seen.add(key)
    return deduped


def random_same_edge_count(plan: list[PlannedEdge], alive_ids: list[int], *, seed: int) -> list[PlannedEdge]:
    rng = random.Random(seed + 6400)
    ids = list(alive_ids)
    weights_roles = [(edge.edge_type, edge.weight, edge.role) for edge in plan]
    out: list[PlannedEdge] = []
    used: set[tuple[int, int]] = set()
    attempts = 0
    for edge_type, weight, role in weights_roles:
        while attempts < 10000:
            attempts += 1
            src = rng.choice(ids)
            dst = rng.choice(ids)
            if src == dst or (src, dst) in used:
                continue
            used.add((src, dst))
            out.append(PlannedEdge(src, dst, edge_type, weight, f"randomized_{role}"))
            break
    return out


def motif_shuffled_plan(plan: list[PlannedEdge], *, seed: int) -> list[PlannedEdge]:
    rng = random.Random(seed + 6410)
    labels = [edge.edge_type for edge in plan]
    rng.shuffle(labels)
    return [
        PlannedEdge(edge.source_id, edge.target_id, labels[idx], edge.weight, f"motif_label_shuffled_{edge.role}")
        for idx, edge in enumerate(plan)
    ]


def planned_edges_for_case(case: CaseSpec, alive_ids: list[int], *, seed: int, args: argparse.Namespace) -> list[PlannedEdge]:
    if not case.seed_graph:
        return []
    plan = base_motif_plan(alive_ids, inhibitory_weight=-abs(float(args.inhibitory_lateral_weight)))
    if case.variant_type == "no_feedforward":
        return [edge for edge in plan if edge.edge_type != EdgeType.FEEDFORWARD]
    if case.variant_type == "no_feedback":
        return [edge for edge in plan if edge.edge_type != EdgeType.FEEDBACK]
    if case.variant_type == "no_lateral":
        return [edge for edge in plan if edge.edge_type != EdgeType.LATERAL]
    if case.variant_type == "no_wta":
        return [edge for edge in plan if edge.role != "wta_lateral_inhibition"]
    if case.variant_type == "random_graph_same_edge_count":
        return random_same_edge_count(plan, alive_ids, seed=seed)
    if case.variant_type == "motif_shuffled":
        return motif_shuffled_plan(plan, seed=seed)
    return plan


def seed_motif_graph(organism: Organism, case: CaseSpec, *, task_name: str, seed: int, args: argparse.Namespace) -> list[dict[str, Any]]:
    if organism.network is None or organism.polyp_population is None:
        return []
    alive_ids = sorted(int(state.polyp_id) for state in organism.polyp_population.states if getattr(state, "is_alive", False))
    # The motif-causality graph is seeded deliberately so FF/LAT/FB are all
    # present before the first outcome feedback. Existing birth scaffolds are
    # not removed, but normal initialization has no graph edges here.
    plan = planned_edges_for_case(case, alive_ids, seed=seed, args=args)
    graph_rows: list[dict[str, Any]] = []
    for edge in plan:
        if edge.source_id == edge.target_id:
            continue
        organism.network.add_edge(
            edge.source_id,
            edge.target_id,
            weight=float(edge.weight),
            edge_type=edge.edge_type,
        )
        graph_rows.append(
            {
                "task": task_name,
                "case": case.name,
                "regime": case.regime,
                "variant_type": case.variant_type,
                "seed": int(seed),
                "source_id": int(edge.source_id),
                "target_id": int(edge.target_id),
                "edge_type": edge.edge_type,
                "weight": float(edge.weight),
                "role": edge.role,
                "seeded_before_first_step": True,
            }
        )
    try:
        organism.network.sync_to_spinnaker()
    except Exception:
        # Mock and some software paths can run fully host-side; graph rows
        # still audit the seeded host topology.
        pass
    return graph_rows


def run_case(task: TaskStream, case: CaseSpec, *, seed: int, args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    random.seed(seed)
    np.random.seed(seed)
    sim, backend_name = load_backend(args.backend)
    setup_backend(sim, backend_name)
    cfg = make_config(seed=seed, task=task, case=case, args=args)
    organism = Organism(cfg, sim, use_default_trading_bridge=(task.domain != "sensor_control"))
    adapter = SensorControlAdapter()
    rows: list[dict[str, Any]] = []
    started = time.perf_counter()
    lifecycle_event_rows: list[dict[str, Any]] = []
    lineage_rows: list[dict[str, Any]] = []
    graph_rows: list[dict[str, Any]] = []
    lineage_ok = True
    lineage_problems: list[str] = []
    try:
        organism.initialize(stream_keys=[task.domain])
        graph_rows = seed_motif_graph(organism, case, task_name=task.name, seed=seed, args=args)
        for step in range(task.steps):
            sensory_value = float(task.sensory[step])
            target_value = float(task.current_target[step])
            if task.domain == "sensor_control":
                observation = Observation(
                    stream_id=task.domain,
                    x=np.asarray([sensory_value], dtype=float),
                    target=target_value,
                    metadata={"task": task.name, "step": step, "tier": "6.4"},
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
                    "variant_type": case.variant_type,
                    "case_group": case.group,
                    "lifecycle_enabled": bool(case.lifecycle_enabled),
                    "seeded_graph": bool(case.seed_graph),
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
                    "seeded_motif_edge_count": len(graph_rows),
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
    motif_totals = {
        "ff": sum(finite_float(r.get("ff_message_total")) for r in rows),
        "lat": sum(finite_float(r.get("lat_message_total")) for r in rows),
        "fb": sum(finite_float(r.get("fb_message_total")) for r in rows),
        "all": sum(finite_float(r.get("motif_message_total")) for r in rows),
    }
    non_handoff_events = [r for r in lifecycle_event_rows if r.get("event_type") in {"birth", "death", "cleavage"}]
    seeded_counts: dict[str, int] = {EdgeType.FEEDFORWARD: 0, EdgeType.LATERAL: 0, EdgeType.FEEDBACK: 0}
    seeded_inhibitory = 0
    for row in graph_rows:
        edge_type = str(row.get("edge_type"))
        if edge_type in seeded_counts:
            seeded_counts[edge_type] += 1
        if finite_float(row.get("weight")) < 0.0:
            seeded_inhibitory += 1
    summary.update(
        {
            "task": task.name,
            "case": case.name,
            "regime": case.regime,
            "variant_type": case.variant_type,
            "case_group": case.group,
            "lifecycle_enabled": bool(case.lifecycle_enabled),
            "seeded_graph": bool(case.seed_graph),
            "backend": backend_name,
            "seed": int(seed),
            "steps": int(task.steps),
            "runtime_seconds": time.perf_counter() - started,
            "initial_population": int(case.initial_population),
            "max_population": int(case.max_population),
            "paired_intact": case.paired_intact,
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
            "seeded_motif_edge_count": len(graph_rows),
            "seeded_ff_edges": seeded_counts[EdgeType.FEEDFORWARD],
            "seeded_lat_edges": seeded_counts[EdgeType.LATERAL],
            "seeded_fb_edges": seeded_counts[EdgeType.FEEDBACK],
            "seeded_inhibitory_edges": seeded_inhibitory,
            "motif_message_total_sum": motif_totals["all"],
            "ff_message_total_sum": motif_totals["ff"],
            "lat_message_total_sum": motif_totals["lat"],
            "fb_message_total_sum": motif_totals["fb"],
            "motif_active_step_count": int(sum(1 for r in rows if finite_float(r.get("motif_message_total")) > EPS)),
            "graph_context_mean_abs_mean": mean([r.get("graph_context_mean_abs") for r in rows]),
            "graph_context_nonzero_count_sum": int(sum(int(r.get("graph_context_nonzero_count", 0) or 0) for r in rows)),
            "task_metadata": task.metadata,
            "config": cfg.to_dict(),
        }
    )
    return rows, summary, lifecycle_event_rows, lineage_rows, graph_rows


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
        "seeded_motif_edge_count",
        "seeded_ff_edges",
        "seeded_lat_edges",
        "seeded_fb_edges",
        "seeded_inhibitory_edges",
        "motif_message_total_sum",
        "ff_message_total_sum",
        "lat_message_total_sum",
        "fb_message_total_sum",
        "motif_active_step_count",
        "graph_context_mean_abs_mean",
        "graph_context_nonzero_count_sum",
    ]
    agg: dict[str, Any] = {
        "task": task,
        "case": case.name,
        "regime": case.regime,
        "variant_type": case.variant_type,
        "case_group": case.group,
        "lifecycle_enabled": bool(case.lifecycle_enabled),
        "seeded_graph": bool(case.seed_graph),
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


def has_intact_advantage(intact: dict[str, Any], control: dict[str, Any], args: argparse.Namespace) -> tuple[bool, list[str], dict[str, Any]]:
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
    if intact_tail - control_tail >= args.min_tail_loss:
        reasons.append("tail_accuracy_loss")
    if intact_all - control_all >= args.min_all_accuracy_loss:
        reasons.append("all_accuracy_loss")
    if intact_corr - control_corr >= args.min_corr_loss:
        reasons.append("prediction_correlation_loss")
    if recovery_improvement is not None and recovery_improvement >= args.min_recovery_loss_steps:
        reasons.append("switch_recovery_loss")
    if intact_eff - control_eff >= args.min_active_efficiency_loss:
        reasons.append("active_population_efficiency_loss")
    deltas = {
        "tail_delta": intact_tail - control_tail,
        "all_accuracy_delta": intact_all - control_all,
        "abs_corr_delta": intact_corr - control_corr,
        "recovery_improvement_steps": recovery_improvement,
        "active_efficiency_delta": intact_eff - control_eff,
    }
    return bool(reasons), reasons, deltas


def control_dominates_intact(intact: dict[str, Any], control: dict[str, Any], args: argparse.Namespace) -> bool:
    control_tail = finite_float(control.get("tail_accuracy_mean"))
    intact_tail = finite_float(intact.get("tail_accuracy_mean"))
    control_corr = abs(finite_float(control.get("prediction_target_corr_mean")))
    intact_corr = abs(finite_float(intact.get("prediction_target_corr_mean")))
    control_recovery = control.get("mean_recovery_steps")
    intact_recovery = intact.get("mean_recovery_steps")
    control_eff = finite_float(control.get("tail_active_efficiency_proxy_mean"))
    intact_eff = finite_float(intact.get("tail_active_efficiency_proxy_mean"))

    control_beats_primary = (
        control_tail - intact_tail >= args.min_tail_loss
        and control_corr - intact_corr >= args.min_corr_loss
    )
    # Dominance should mean the simpler graph also avoids paying an adaptive
    # cost. A fixed/monolithic control that wins a scalar accuracy column but
    # recovers slower after switches, or uses the active population less
    # efficiently, does not explain away the motif/ecology effect.
    recovery_not_worse = True
    if control_recovery is not None and intact_recovery is not None:
        recovery_not_worse = float(control_recovery) <= float(intact_recovery) + args.min_recovery_loss_steps
    efficiency_not_worse = control_eff >= intact_eff - args.min_active_efficiency_loss
    return bool(control_beats_primary and recovery_not_worse and efficiency_not_worse)


def build_comparisons(aggregates: list[dict[str, Any]], args: argparse.Namespace) -> list[dict[str, Any]]:
    by_key = {(agg["task"], agg["regime"], agg["variant_type"]): agg for agg in aggregates}
    rows: list[dict[str, Any]] = []
    for agg in aggregates:
        if agg["variant_type"] == "intact":
            continue
        intact = by_key.get((agg["task"], agg["regime"], "intact"))
        if intact is None:
            continue
        advantage, reasons, deltas = has_intact_advantage(intact, agg, args)
        dominated = control_dominates_intact(intact, agg, args)
        rows.append(
            {
                "task": agg["task"],
                "regime": agg["regime"],
                "intact_case": intact["case"],
                "control_case": agg["case"],
                "variant_type": agg["variant_type"],
                "case_group": agg["case_group"],
                "performance_control": agg["variant_type"] in PERFORMANCE_VARIANTS,
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
                "intact_motif_message_total_sum_mean": intact.get("motif_message_total_sum_mean"),
                "control_motif_message_total_sum_mean": agg.get("motif_message_total_sum_mean"),
                "intact_seeded_motif_edge_count_mean": intact.get("seeded_motif_edge_count_mean"),
                "control_seeded_motif_edge_count_mean": agg.get("seeded_motif_edge_count_mean"),
                "motif_loss": bool(advantage),
                "loss_reasons": ",".join(reasons),
                "control_dominates_intact": bool(dominated),
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
                "variant_type": agg["variant_type"],
                "case_group": agg["case_group"],
                "initial_population": agg["initial_population"],
                "max_population": agg["max_population"],
                "runs": agg["runs"],
                "seeds": ",".join(str(s) for s in agg["seeds"]),
                "all_accuracy_mean": agg.get("all_accuracy_mean"),
                "tail_accuracy_mean": agg.get("tail_accuracy_mean"),
                "prediction_target_corr_mean": agg.get("prediction_target_corr_mean"),
                "tail_prediction_target_corr_mean": agg.get("tail_prediction_target_corr_mean"),
                "mean_recovery_steps": agg.get("mean_recovery_steps"),
                "total_births_sum": agg.get("total_births_sum"),
                "total_deaths_sum": agg.get("total_deaths_sum"),
                "non_handoff_lifecycle_event_count_sum": agg.get("non_handoff_lifecycle_event_count_sum"),
                "lineage_integrity_failures": agg.get("lineage_integrity_failures"),
                "seeded_motif_edge_count_mean": agg.get("seeded_motif_edge_count_mean"),
                "seeded_ff_edges_mean": agg.get("seeded_ff_edges_mean"),
                "seeded_lat_edges_mean": agg.get("seeded_lat_edges_mean"),
                "seeded_fb_edges_mean": agg.get("seeded_fb_edges_mean"),
                "seeded_inhibitory_edges_mean": agg.get("seeded_inhibitory_edges_mean"),
                "motif_message_total_sum_mean": agg.get("motif_message_total_sum_mean"),
                "ff_message_total_sum_mean": agg.get("ff_message_total_sum_mean"),
                "lat_message_total_sum_mean": agg.get("lat_message_total_sum_mean"),
                "fb_message_total_sum_mean": agg.get("fb_message_total_sum_mean"),
                "motif_active_step_count_mean": agg.get("motif_active_step_count_mean"),
                "graph_context_mean_abs_mean": agg.get("graph_context_mean_abs_mean"),
                "tail_active_efficiency_proxy_mean": agg.get("tail_active_efficiency_proxy_mean"),
                "runtime_seconds_mean": agg.get("runtime_seconds_mean"),
            }
        )
    return rows


def evaluate_tier(aggregates: list[dict[str, Any]], comparisons: list[dict[str, Any]], args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    regimes = parse_regimes(args.regimes)
    variants = parse_variants(args.variants)
    task_names = [item.strip() for item in args.tasks.split(",") if item.strip()]
    expected_runs = len(seeds_from_args(args)) * len(regimes) * len(task_names) * len(variants)
    actual_runs = int(sum(int(agg.get("runs", 0)) for agg in aggregates))
    intact = [agg for agg in aggregates if agg["variant_type"] == "intact"]
    intact_seeded_diverse = int(
        sum(
            1
            for agg in intact
            if finite_float(agg.get("seeded_ff_edges_min")) > 0
            and finite_float(agg.get("seeded_lat_edges_min")) > 0
            and finite_float(agg.get("seeded_fb_edges_min")) > 0
        )
    )
    intact_motif_activity_steps = int(sum(int(agg.get("motif_active_step_count_mean", 0) or 0) for agg in intact))
    lineage_failures = int(sum(int(agg.get("lineage_integrity_failures", 0) or 0) for agg in aggregates))
    extinct_actual = int(sum(1 for agg in aggregates if finite_float(agg.get("final_n_alive_min"), 1.0) <= 0))
    performance_rows = [row for row in comparisons if row.get("performance_control")]
    motif_losses = [row for row in performance_rows if row.get("motif_loss")]
    motif_ablation_losses = [
        row for row in motif_losses
        if row.get("variant_type") in {"no_feedforward", "no_feedback", "no_lateral", "no_wta"}
    ]
    random_or_monolithic_dominates = [
        row for row in performance_rows
        if row.get("variant_type") in RANDOM_OR_MONOLITHIC and row.get("control_dominates_intact")
    ]
    shuffled_rows = [row for row in performance_rows if row.get("variant_type") == "motif_shuffled"]
    no_wta_rows = [row for row in performance_rows if row.get("variant_type") == "no_wta"]
    expected_regime_task_pairs = len(regimes) * len(task_names)
    required_performance_rows = expected_regime_task_pairs * len([v for v in variants if v.performance_control])

    tier_summary = {
        "expected_runs": expected_runs,
        "actual_runs": actual_runs,
        "tasks": task_names,
        "regimes": [regime.name for regime in regimes],
        "variants": [variant.variant_type for variant in variants],
        "backend": args.backend,
        "seeds": seeds_from_args(args),
        "intact_motif_diverse_aggregate_count": intact_seeded_diverse,
        "expected_intact_aggregates": expected_regime_task_pairs,
        "intact_motif_activity_steps_sum": intact_motif_activity_steps,
        "lineage_integrity_failures": lineage_failures,
        "extinct_aggregate_count": extinct_actual,
        "performance_comparison_rows": len(performance_rows),
        "required_performance_comparison_rows": required_performance_rows,
        "motif_loss_count": len(motif_losses),
        "motif_ablation_loss_count": len(motif_ablation_losses),
        "random_or_monolithic_domination_count": len(random_or_monolithic_dominates),
        "motif_shuffled_row_count": len(shuffled_rows),
        "no_wta_row_count": len(no_wta_rows),
    }
    criteria = [
        criterion("matrix completed", actual_runs, "==", expected_runs, actual_runs == expected_runs),
        criterion(
            "intact graph is motif-diverse",
            intact_seeded_diverse,
            "==",
            expected_regime_task_pairs,
            intact_seeded_diverse == expected_regime_task_pairs,
            "Each intact task/regime aggregate must contain seeded FF, LAT, and FB motif edges.",
        ),
        criterion(
            "intact motifs active before reward/learning",
            intact_motif_activity_steps,
            ">=",
            args.min_intact_motif_active_steps,
            intact_motif_activity_steps >= args.min_intact_motif_active_steps,
        ),
        criterion("lineage integrity remains clean", lineage_failures, "==", 0, lineage_failures == 0),
        criterion("no aggregate extinction", extinct_actual, "==", 0, extinct_actual == 0),
        criterion(
            "all performance motif comparisons emitted",
            len(performance_rows),
            ">=",
            required_performance_rows,
            len(performance_rows) >= required_performance_rows,
        ),
        criterion(
            "motif ablations produce predicted losses",
            len(motif_ablation_losses),
            ">=",
            args.min_motif_ablation_losses,
            len(motif_ablation_losses) >= args.min_motif_ablation_losses,
            "Loss can be accuracy, correlation, recovery, or active-population efficiency versus intact motif CRA.",
        ),
        criterion(
            "random/monolithic controls do not dominate intact",
            len(random_or_monolithic_dominates),
            "<=",
            args.max_random_or_monolithic_dominations,
            len(random_or_monolithic_dominates) <= args.max_random_or_monolithic_dominations,
        ),
    ]
    if any(v.variant_type == "motif_shuffled" for v in variants):
        criteria.append(criterion("motif-shuffled control emitted", len(shuffled_rows), ">=", expected_regime_task_pairs, len(shuffled_rows) >= expected_regime_task_pairs))
    if any(v.variant_type == "no_wta" for v in variants):
        criteria.append(criterion("WTA/lateral-inhibition ablation emitted", len(no_wta_rows), ">=", expected_regime_task_pairs, len(no_wta_rows) >= expected_regime_task_pairs))
    return criteria, tier_summary


def plot_summary(aggregates: list[dict[str, Any]], path: Path) -> None:
    if plt is None or not aggregates:
        return
    regimes = sorted({a["regime"] for a in aggregates})
    fig, axes = plt.subplots(len(regimes), 1, figsize=(13, 4 * len(regimes)), squeeze=False)
    for idx, regime in enumerate(regimes):
        ax = axes[idx][0]
        subset = [a for a in aggregates if a["regime"] == regime]
        cases = [a["variant_type"] for a in subset]
        vals = [finite_float(a.get("tail_accuracy_mean")) for a in subset]
        colors = ["#2da44e" if a["variant_type"] == "intact" else "#d1242f" if a["case_group"] == "motif_ablation" else "#0969da" for a in subset]
        ax.bar(range(len(cases)), vals, color=colors)
        ax.set_title(f"{regime}: Tier 6.4 motif-causality tail accuracy")
        ax.set_ylim(0.0, 1.05)
        ax.set_ylabel("tail accuracy")
        ax.set_xticks(range(len(cases)))
        ax.set_xticklabels(cases, rotation=35, ha="right")
        ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_motif_activity(aggregates: list[dict[str, Any]], path: Path) -> None:
    if plt is None or not aggregates:
        return
    regimes = sorted({a["regime"] for a in aggregates})
    fig, axes = plt.subplots(len(regimes), 1, figsize=(13, 4 * len(regimes)), squeeze=False)
    for idx, regime in enumerate(regimes):
        ax = axes[idx][0]
        subset = [a for a in aggregates if a["regime"] == regime]
        labels = [a["variant_type"] for a in subset]
        ff = [finite_float(a.get("ff_message_total_sum_mean")) for a in subset]
        lat = [finite_float(a.get("lat_message_total_sum_mean")) for a in subset]
        fb = [finite_float(a.get("fb_message_total_sum_mean")) for a in subset]
        x = np.arange(len(labels))
        ax.bar(x, ff, label="FF", color="#0969da")
        ax.bar(x, lat, bottom=ff, label="LAT", color="#2da44e")
        ax.bar(x, fb, bottom=np.asarray(ff) + np.asarray(lat), label="FB", color="#bf8700")
        ax.set_title(f"{regime}: motif message activity")
        ax.set_ylabel("absolute message total")
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=35, ha="right")
        ax.grid(axis="y", alpha=0.25)
        ax.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def write_report(*, path: Path, result: TestResult, output_dir: Path, args: argparse.Namespace) -> None:
    summary = result.summary["tier_summary"]
    aggregates = result.summary["aggregates"]
    comparisons = result.summary["comparisons"]
    lines = [
        "# Tier 6.4 Circuit Motif Causality Findings",
        "",
        f"- Generated: `{utc_now()}`",
        f"- Backend: `{args.backend}`",
        f"- Status: **{result.status.upper()}**",
        f"- Output directory: `{output_dir}`",
        "",
        "Tier 6.4 tests whether seeded reef circuit motifs are causal contributors rather than decorative labels.",
        "",
        "## Claim Boundary",
        "",
        "- PASS supports a controlled software claim that motif structure contributes measurable value under the tested tasks/seeds.",
        "- PASS is not hardware motif evidence, not custom-C/on-chip evidence, not proof of compositionality, and not proof that every motif is individually optimal.",
        "- The suite seeds a motif-diverse graph before the first outcome feedback because Tier 6.3 traces were feedforward-only and could not honestly ablate absent motifs.",
        "- FAIL means the reef-motif claim must narrow or the motif implementation needs repair before promotion.",
        "",
        "## Summary",
        "",
        f"- expected_runs: `{summary['expected_runs']}`",
        f"- actual_runs: `{summary['actual_runs']}`",
        f"- intact_motif_diverse_aggregate_count: `{summary['intact_motif_diverse_aggregate_count']}`",
        f"- intact_motif_activity_steps_sum: `{summary['intact_motif_activity_steps_sum']}`",
        f"- motif_ablation_loss_count: `{summary['motif_ablation_loss_count']}`",
        f"- random_or_monolithic_domination_count: `{summary['random_or_monolithic_domination_count']}`",
        f"- lineage_integrity_failures: `{summary['lineage_integrity_failures']}`",
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
            "| Task | Regime | Variant | Group | Tail Acc | Abs Corr | Recovery | Motif Msg | FF/LAT/FB Edges | Events | Lineage Fails |",
            "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |",
        ]
    )
    for agg in aggregates:
        lines.append(
            "| "
            f"`{agg['task']}` | `{agg['regime']}` | `{agg['variant_type']}` | `{agg['case_group']}` | "
            f"{markdown_value(agg.get('tail_accuracy_mean'))} | "
            f"{markdown_value(abs(finite_float(agg.get('prediction_target_corr_mean'))))} | "
            f"{markdown_value(agg.get('mean_recovery_steps'))} | "
            f"{markdown_value(agg.get('motif_message_total_sum_mean'))} | "
            f"{markdown_value(agg.get('seeded_ff_edges_mean'))}/"
            f"{markdown_value(agg.get('seeded_lat_edges_mean'))}/"
            f"{markdown_value(agg.get('seeded_fb_edges_mean'))} | "
            f"{markdown_value(agg.get('non_handoff_lifecycle_event_count_sum'))} | "
            f"{markdown_value(agg.get('lineage_integrity_failures'))} |"
        )

    lines.extend(
        [
            "",
            "## Intact vs Motif Controls",
            "",
            "| Task | Regime | Control | Tail Delta | Corr Delta | Recovery Improvement | Efficiency Delta | Loss | Reason | Dominates Intact |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- | --- |",
        ]
    )
    for row in comparisons:
        lines.append(
            "| "
            f"`{row['task']}` | `{row['regime']}` | `{row['variant_type']}` | "
            f"{markdown_value(row.get('tail_delta_vs_control'))} | "
            f"{markdown_value(row.get('abs_corr_delta_vs_control'))} | "
            f"{markdown_value(row.get('recovery_improvement_steps_vs_control'))} | "
            f"{markdown_value(row.get('active_efficiency_delta_vs_control'))} | "
            f"{'yes' if row.get('motif_loss') else 'no'} | `{row.get('loss_reasons', '')}` | "
            f"{'yes' if row.get('control_dominates_intact') else 'no'} |"
        )

    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            "- `tier6_4_results.json`: machine-readable manifest.",
            "- `tier6_4_summary.csv`: aggregate motif/control metrics.",
            "- `tier6_4_comparisons.csv`: intact-vs-control deltas.",
            "- `tier6_4_motif_graph.csv`: seeded motif graph and roles.",
            "- `tier6_4_lifecycle_events.csv`: lifecycle event log.",
            "- `tier6_4_lineage_final.csv`: final lineage audit table.",
            "- `tier6_4_motif_manifest.json`: variant definitions and claim boundaries.",
            "- `*_timeseries.csv`: per-task/per-regime/per-variant/per-seed traces.",
            "",
            "## Plots",
            "",
            "![summary](tier6_4_motif_summary.png)",
            "",
            "![activity](tier6_4_motif_activity.png)",
        ]
    )
    if MATPLOTLIB_ERROR:
        lines.append(f"Plotting unavailable: `{MATPLOTLIB_ERROR}`")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def run_tier(args: argparse.Namespace, output_dir: Path) -> TestResult:
    regimes = parse_regimes(args.regimes)
    variants = parse_variants(args.variants)
    all_timeseries_rows: list[dict[str, Any]] = []
    all_event_rows: list[dict[str, Any]] = []
    all_lineage_rows: list[dict[str, Any]] = []
    all_graph_rows: list[dict[str, Any]] = []
    summaries_by_task_case: dict[tuple[str, str], list[dict[str, Any]]] = {}
    rows_by_task_case_seed: dict[tuple[str, str, int], list[dict[str, Any]]] = {}
    task_by_seed_name: dict[tuple[int, str], TaskStream] = {}
    case_by_name: dict[str, CaseSpec] = {}
    artifacts: dict[str, str] = {}

    for seed in seeds_from_args(args):
        tasks = build_tasks(args, seed=args.task_seed + seed)
        for task in tasks:
            task_by_seed_name[(seed, task.name)] = task
            for regime in regimes:
                for variant in variants:
                    case = case_for(regime, variant)
                    case_by_name[case.name] = case
                    print(f"[tier6.4] task={task.name} regime={regime.name} variant={variant.variant_type} seed={seed}", flush=True)
                    rows, summary, event_rows, lineage_rows, graph_rows = run_case(task, case, seed=seed, args=args)
                    csv_path = output_dir / f"{task.name}_{case.name}_seed{seed}_timeseries.csv"
                    safe_write_csv(csv_path, rows)
                    artifacts[f"{task.name}_{case.name}_seed{seed}_timeseries_csv"] = str(csv_path)
                    all_timeseries_rows.extend(rows)
                    all_event_rows.extend(event_rows)
                    all_lineage_rows.extend(lineage_rows)
                    all_graph_rows.extend(graph_rows)
                    summaries_by_task_case.setdefault((task.name, case.name), []).append(summary)
                    rows_by_task_case_seed[(task.name, case.name, seed)] = rows

    aggregates: list[dict[str, Any]] = []
    for (task_name, case_name), summaries in sorted(summaries_by_task_case.items()):
        seed_rows = {int(summary["seed"]): rows_by_task_case_seed[(task_name, case_name, int(summary["seed"]))] for summary in summaries}
        seed_tasks = {int(summary["seed"]): task_by_seed_name[(int(summary["seed"]), task_name)] for summary in summaries}
        aggregates.append(aggregate_case(task_name, case_by_name[case_name], summaries, seed_rows, seed_tasks, args))

    comparisons = build_comparisons(aggregates, args)
    criteria, tier_summary = evaluate_tier(aggregates, comparisons, args)
    status, failure_reason = pass_fail(criteria)

    summary_csv = output_dir / "tier6_4_summary.csv"
    comparisons_csv = output_dir / "tier6_4_comparisons.csv"
    graph_csv = output_dir / "tier6_4_motif_graph.csv"
    events_csv = output_dir / "tier6_4_lifecycle_events.csv"
    lineage_csv = output_dir / "tier6_4_lineage_final.csv"
    motif_manifest_path = output_dir / "tier6_4_motif_manifest.json"
    summary_plot = output_dir / "tier6_4_motif_summary.png"
    activity_plot = output_dir / "tier6_4_motif_activity.png"
    safe_write_csv(summary_csv, summary_csv_rows(aggregates))
    safe_write_csv(comparisons_csv, comparisons)
    safe_write_csv(graph_csv, all_graph_rows)
    safe_write_csv(events_csv, all_event_rows)
    safe_write_csv(lineage_csv, all_lineage_rows)
    safe_write_json(
        motif_manifest_path,
        {
            "tier": TIER,
            "generated_at_utc": utc_now(),
            "variant_definitions": {name: variant.__dict__ for name, variant in VARIANTS.items()},
            "requested_variants": [variant.variant_type for variant in variants],
            "performance_variants": sorted(PERFORMANCE_VARIANTS),
            "message_passing": {
                "steps": int(args.message_passing_steps),
                "context_gain": float(args.message_context_gain),
                "prediction_mix": float(args.message_prediction_mix),
            },
            "claim_boundary": "Software motif-causality suite with seeded motif-diverse graph; not hardware/on-chip motif evidence.",
        },
    )
    plot_summary(aggregates, summary_plot)
    plot_motif_activity(aggregates, activity_plot)

    artifacts.update(
        {
            "summary_csv": str(summary_csv),
            "comparisons_csv": str(comparisons_csv),
            "motif_graph_csv": str(graph_csv),
            "lifecycle_events_csv": str(events_csv),
            "lineage_final_csv": str(lineage_csv),
            "motif_manifest_json": str(motif_manifest_path),
            "summary_plot_png": str(summary_plot) if summary_plot.exists() else "",
            "motif_activity_plot_png": str(activity_plot) if activity_plot.exists() else "",
        }
    )
    return TestResult(
        name="circuit_motif_causality",
        status=status,
        summary={
            "tier_summary": tier_summary,
            "aggregates": aggregates,
            "comparisons": comparisons,
            "tasks": tier_summary["tasks"],
            "regimes": tier_summary["regimes"],
            "variants": tier_summary["variants"],
            "seeds": tier_summary["seeds"],
            "backend": args.backend,
            "claim_boundary": "Software-only motif-causality suite; seeded motif graph, not hardware or on-chip evidence.",
        },
        criteria=criteria,
        artifacts=artifacts,
        failure_reason=failure_reason,
    )


def write_latest(output_dir: Path, report_path: Path, manifest_path: Path, summary_csv: Path, status: str) -> None:
    latest_path = ROOT / "controlled_test_output" / "tier6_4_latest_manifest.json"
    safe_write_json(
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
            "claim": "Latest Tier 6.4 circuit motif causality suite; promote only after review.",
        },
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Tier 6.4 CRA circuit motif causality suite.")
    parser.add_argument("--backend", choices=["nest", "brian2", "mock"], default="nest")
    parser.add_argument("--tasks", default=DEFAULT_TASKS)
    parser.add_argument("--regimes", default=DEFAULT_REGIMES)
    parser.add_argument("--variants", default=DEFAULT_VARIANTS)
    parser.add_argument("--steps", type=int, default=960)
    parser.add_argument("--base-seed", type=int, default=42)
    parser.add_argument("--seed-count", type=int, default=3)
    parser.add_argument("--task-seed", type=int, default=6400)
    parser.add_argument("--amplitude", type=float, default=DEFAULT_AMPLITUDE)
    parser.add_argument("--dt-seconds", type=float, default=DEFAULT_DT_SECONDS)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--stop-on-fail", action="store_true")

    parser.add_argument("--cra-readout-lr", type=float, default=0.10)
    parser.add_argument("--cra-delayed-readout-lr", type=float, default=0.20)
    parser.add_argument("--message-passing-steps", type=int, default=1)
    parser.add_argument("--message-context-gain", type=float, default=0.025)
    parser.add_argument("--message-prediction-mix", type=float, default=0.35)
    parser.add_argument("--inhibitory-lateral-weight", type=float, default=0.28)

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
    parser.add_argument("--min-intact-motif-active-steps", type=int, default=100)
    parser.add_argument("--min-motif-ablation-losses", type=int, default=3)
    parser.add_argument("--max-random-or-monolithic-dominations", type=int, default=0)
    parser.add_argument("--min-tail-loss", type=float, default=0.015)
    parser.add_argument("--min-all-accuracy-loss", type=float, default=0.015)
    parser.add_argument("--min-corr-loss", type=float, default=0.015)
    parser.add_argument("--min-recovery-loss-steps", type=float, default=2.0)
    parser.add_argument("--min-active-efficiency-loss", type=float, default=0.0015)
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
    parse_variants(args.variants)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = args.output_dir or (ROOT / "controlled_test_output" / f"tier6_4_{timestamp}")
    output_dir.mkdir(parents=True, exist_ok=True)

    result = run_tier(args, output_dir)
    manifest_path = output_dir / "tier6_4_results.json"
    report_path = output_dir / "tier6_4_report.md"
    summary_csv = output_dir / "tier6_4_summary.csv"
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
            "comparisons_csv": str(output_dir / "tier6_4_comparisons.csv"),
            "motif_graph_csv": str(output_dir / "tier6_4_motif_graph.csv"),
            "lifecycle_events_csv": str(output_dir / "tier6_4_lifecycle_events.csv"),
            "lineage_final_csv": str(output_dir / "tier6_4_lineage_final.csv"),
            "motif_manifest_json": str(output_dir / "tier6_4_motif_manifest.json"),
            "report_md": str(report_path),
            "summary_plot_png": str(output_dir / "tier6_4_motif_summary.png"),
            "motif_activity_plot_png": str(output_dir / "tier6_4_motif_activity.png"),
        },
    }
    safe_write_json(manifest_path, manifest)
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
