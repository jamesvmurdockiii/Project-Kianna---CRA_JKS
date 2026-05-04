#!/usr/bin/env python3
"""Tier 5.13c internal composition/routing promotion gate.

Tier 5.13 and 5.13b passed with explicit host-side composition and router
scaffolds. Tier 5.13c asks whether the same capability can be internalized into
CRA as a bounded, auditable mechanism with reset/shuffle/no-write shams.

This is still software evidence. It is not hardware evidence, not native on-chip
routing, not language reasoning, and not long-horizon planning.
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

from coral_reef_spinnaker import Organism, ReefConfig  # noqa: E402
import tier5_compositional_skill_reuse as comp  # noqa: E402
import tier5_module_routing as route  # noqa: E402
from tier2_learning import (  # noqa: E402
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
    build_parser as build_tier5_1_parser,
    parse_models,
)
from tier5_macro_eligibility import computed_horizon  # noqa: E402


TIER = "Tier 5.13c - Internal Composition / Routing Promotion Gate"
DEFAULT_COMPOSITION_TASKS = "heldout_skill_pair,order_sensitive_chain,distractor_skill_chain"
DEFAULT_ROUTING_TASKS = "heldout_context_routing,distractor_router_chain,context_reentry_routing"
DEFAULT_MODELS = "sign_persistence,online_perceptron,online_logistic_regression,echo_state_network,small_gru,stdp_only_snn"
EPS = 1e-12


@dataclass(frozen=True)
class InternalVariant:
    name: str
    group: str
    mode: str
    mechanism_enabled: bool
    prediction_mix: float
    hypothesis: str


INTERNAL_VARIANTS: tuple[InternalVariant, ...] = (
    InternalVariant(
        name="v1_8_raw_cra",
        group="frozen_baseline",
        mode="disabled",
        mechanism_enabled=False,
        prediction_mix=0.0,
        hypothesis="Frozen v1.8-style CRA with composition/routing disabled.",
    ),
    InternalVariant(
        name="internal_composition_routing",
        group="candidate_internal",
        mode="normal",
        mechanism_enabled=True,
        prediction_mix=1.0,
        hypothesis="Internal CRA module table plus context router selects composed/routed decision features before feedback.",
    ),
    InternalVariant(
        name="internal_no_write_ablation",
        group="internal_ablation",
        mode="no_write",
        mechanism_enabled=True,
        prediction_mix=1.0,
        hypothesis="Control: the internal mechanism may read events but cannot write module/router memory.",
    ),
    InternalVariant(
        name="internal_reset_ablation",
        group="internal_ablation",
        mode="reset",
        mechanism_enabled=True,
        prediction_mix=1.0,
        hypothesis="Control: held-out composition cannot reuse learned primitive modules.",
    ),
    InternalVariant(
        name="internal_shuffle_ablation",
        group="internal_ablation",
        mode="shuffle",
        mechanism_enabled=True,
        prediction_mix=1.0,
        hypothesis="Control: learned module identities are deterministically shuffled.",
    ),
    InternalVariant(
        name="internal_order_shuffle_ablation",
        group="internal_ablation",
        mode="order_shuffle",
        mechanism_enabled=True,
        prediction_mix=1.0,
        hypothesis="Control: composition uses the learned skills in the wrong order.",
    ),
    InternalVariant(
        name="internal_router_reset_ablation",
        group="internal_ablation",
        mode="router_reset",
        mechanism_enabled=True,
        prediction_mix=1.0,
        hypothesis="Control: held-out routing cannot use the learned context-to-module router.",
    ),
    InternalVariant(
        name="internal_context_shuffle_ablation",
        group="internal_ablation",
        mode="context_shuffle",
        mechanism_enabled=True,
        prediction_mix=1.0,
        hypothesis="Control: routing context retrieves a different context table.",
    ),
    InternalVariant(
        name="internal_random_router_ablation",
        group="internal_ablation",
        mode="random_router",
        mechanism_enabled=True,
        prediction_mix=1.0,
        hypothesis="Control: routing selects a random learned module.",
    ),
    InternalVariant(
        name="internal_always_on_ablation",
        group="internal_ablation",
        mode="always_on",
        mechanism_enabled=True,
        prediction_mix=1.0,
        hypothesis="Control: routing activates all modules together instead of selecting one.",
    ),
)

COMPOSITION_VARIANT_NAMES = {
    "v1_8_raw_cra",
    "internal_composition_routing",
    "internal_no_write_ablation",
    "internal_reset_ablation",
    "internal_shuffle_ablation",
    "internal_order_shuffle_ablation",
}
ROUTING_VARIANT_NAMES = {
    "v1_8_raw_cra",
    "internal_composition_routing",
    "internal_no_write_ablation",
    "internal_router_reset_ablation",
    "internal_context_shuffle_ablation",
    "internal_random_router_ablation",
    "internal_always_on_ablation",
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


def variant_by_name(name: str) -> InternalVariant:
    for variant in INTERNAL_VARIANTS:
        if variant.name == name:
            return variant
    raise KeyError(name)


def selected_internal_variants(kind: str) -> list[InternalVariant]:
    names = COMPOSITION_VARIANT_NAMES if kind == "composition" else ROUTING_VARIANT_NAMES
    return [variant for variant in INTERNAL_VARIANTS if variant.name in names]


def make_task_args(args: argparse.Namespace, *, tasks: str, steps: int) -> argparse.Namespace:
    task_args = copy.copy(args)
    task_args.tasks = tasks
    task_args.steps = int(steps)
    return task_args


def make_config(*, seed: int, task: Any, variant: InternalVariant, args: argparse.Namespace) -> ReefConfig:
    cfg = ReefConfig.default()
    cfg.seed = int(seed)
    cfg.lifecycle.initial_population = int(args.cra_population_size)
    cfg.lifecycle.max_population_from_memory = False
    cfg.lifecycle.max_population_hard = int(args.cra_population_size)
    cfg.lifecycle.enable_reproduction = False
    cfg.lifecycle.enable_apoptosis = False
    cfg.lifecycle.enable_structural_plasticity = True
    cfg.measurement.stream_history_maxlen = max(int(task.stream.steps) + 32, 128)
    cfg.spinnaker.sync_interval_steps = 0
    cfg.spinnaker.runtime_ms_per_step = 1000.0
    cfg.learning.evaluation_horizon_bars = computed_horizon(task.stream)
    cfg.learning.readout_learning_rate = float(args.cra_readout_lr)
    cfg.learning.delayed_readout_learning_rate = float(args.cra_delayed_readout_lr)
    cfg.learning.macro_eligibility_enabled = False
    cfg.learning.context_memory_enabled = True
    cfg.learning.context_memory_mode = "keyed"
    cfg.learning.context_memory_slot_count = 8
    cfg.learning.predictive_context_enabled = True
    cfg.learning.predictive_context_mode = "keyed"
    cfg.learning.predictive_context_slot_count = 8
    cfg.learning.composition_routing_enabled = bool(variant.mechanism_enabled)
    cfg.learning.composition_routing_mode = "normal" if variant.mode == "disabled" else variant.mode
    cfg.learning.composition_routing_input_gain = float(args.amplitude)
    cfg.learning.composition_routing_prediction_mix = float(variant.prediction_mix)
    cfg.learning.composition_routing_prediction_gain = float(args.composition_prediction_gain)
    if hasattr(cfg.network, "message_passing_steps"):
        cfg.network.message_passing_steps = int(args.message_passing_steps)
        cfg.network.message_context_gain = float(args.message_context_gain)
        cfg.network.message_prediction_mix = float(args.message_prediction_mix)
    return cfg


def run_internal_composition(task: comp.CompositionTask, variant: InternalVariant, *, seed: int, args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    random.seed(seed)
    np.random.seed(seed)
    sim, backend_name = load_backend(args.backend)
    setup_backend(sim, backend_name)
    cfg = make_config(seed=seed, task=task, variant=variant, args=args)
    organism = Organism(cfg, sim, use_default_trading_bridge=False)
    rows: list[dict[str, Any]] = []
    started = time.perf_counter()
    try:
        organism.initialize(stream_keys=[task.stream.domain])
        for step in range(task.stream.steps):
            raw = float(task.stream.sensory[step])
            metadata = {
                "tier": "5.13c",
                "subsuite": "composition",
                "variant": variant.name,
                "event_type": task.event_type[step],
                "phase": task.phase[step],
                "composition_skill_a": task.skill_a[step],
                "composition_skill_b": task.skill_b[step],
                "composition_skill": task.skill_a[step],
                "composition_input_sign": int(task.input_sign[step]),
                "composition_pair_key": task.pair_key[step],
            }
            consequence = float(task.stream.current_target[step])
            metrics = organism.train_task_step(
                observation_value=raw,
                consequence_value=consequence,
                horizon_signal=consequence,
                dt_seconds=float(args.dt_seconds),
                task_name=task.stream.name,
                metadata=metadata,
            )
            prediction = float(metrics.colony_prediction)
            row = metrics.to_dict()
            row.update(comp.base_row(task, variant.name, "CRA_internal", seed, step, prediction, backend_name))
            row.update(
                {
                    "variant": variant.name,
                    "variant_group": variant.group,
                    "feature_mode": variant.mode,
                    "raw_sensory_return_1m": raw,
                    "feature_active": bool(metrics.composition_routing_feature_active),
                    "feature_source": metrics.composition_routing_feature_source,
                    "module_updates": int(metrics.composition_routing_module_updates),
                    "module_composition_uses": int(metrics.composition_routing_module_uses),
                    "composition_bound_observation": float(metrics.composition_routing_bound_observation),
                    "configured_readout_lr": float(cfg.learning.readout_learning_rate),
                    "configured_delayed_readout_lr": float(cfg.learning.delayed_readout_learning_rate),
                    "configured_initial_population": int(cfg.lifecycle.initial_population),
                    "configured_max_population": int(cfg.lifecycle.max_population_hard),
                }
            )
            rows.append(row)
    finally:
        organism.shutdown()
        end_backend(sim)
    summary = comp.summarize_composition_rows(rows)
    summary.update(
        {
            "task": task.stream.name,
            "model": variant.name,
            "model_family": "CRA_internal",
            "variant": variant.name,
            "variant_group": variant.group,
            "feature_mode": variant.mode,
            "backend": backend_name,
            "seed": int(seed),
            "steps": task.stream.steps,
            "runtime_seconds": time.perf_counter() - started,
            "task_metadata": task.stream.metadata,
            "task_pressure": comp.task_pressure_summary(task),
            "hypothesis": variant.hypothesis,
        }
    )
    return rows, summary


def run_internal_routing(task: route.RoutingTask, variant: InternalVariant, *, seed: int, args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    random.seed(seed)
    np.random.seed(seed)
    sim, backend_name = load_backend(args.backend)
    setup_backend(sim, backend_name)
    cfg = make_config(seed=seed, task=task, variant=variant, args=args)
    organism = Organism(cfg, sim, use_default_trading_bridge=False)
    rows: list[dict[str, Any]] = []
    started = time.perf_counter()
    try:
        organism.initialize(stream_keys=[task.stream.domain])
        for step in range(task.stream.steps):
            raw = float(task.stream.sensory[step])
            metadata = {
                "tier": "5.13c",
                "subsuite": "routing",
                "variant": variant.name,
                "event_type": task.event_type[step],
                "phase": task.phase[step],
                "composition_skill": task.true_skill[step],
                "routing_true_skill": task.true_skill[step],
                "routing_context": task.context[step],
                "composition_input_sign": int(task.input_sign[step]),
            }
            consequence = float(task.stream.current_target[step])
            metrics = organism.train_task_step(
                observation_value=raw,
                consequence_value=consequence,
                horizon_signal=consequence,
                dt_seconds=float(args.dt_seconds),
                task_name=task.stream.name,
                metadata=metadata,
            )
            prediction = float(metrics.colony_prediction)
            row = metrics.to_dict()
            row.update(route.base_row(task, variant.name, "CRA_internal", seed, step, prediction, backend_name))
            router_active = bool(
                task.heldout_mask[step]
                and metrics.composition_routing_feature_active
                and str(metrics.composition_routing_context)
            )
            router_correct = bool(
                router_active
                and metrics.composition_routing_selected_skill == task.true_skill[step]
            )
            row.update(
                {
                    "variant": variant.name,
                    "variant_group": variant.group,
                    "feature_mode": variant.mode,
                    "raw_sensory_return_1m": raw,
                    "router_active": router_active,
                    "selected_context": metrics.composition_routing_context,
                    "selected_skill": metrics.composition_routing_selected_skill,
                    "true_skill": task.true_skill[step],
                    "router_correct": router_correct,
                    "module_updates": int(metrics.composition_routing_module_updates),
                    "router_updates": int(metrics.composition_routing_router_updates),
                    "router_uses": int(metrics.composition_routing_router_uses),
                    "correct_route_uses": int(metrics.composition_routing_correct_route_uses),
                    "pre_feedback_select_steps": int(metrics.composition_routing_pre_feedback_select_steps),
                    "router_bound_observation": float(metrics.composition_routing_bound_observation),
                    "configured_readout_lr": float(cfg.learning.readout_learning_rate),
                    "configured_delayed_readout_lr": float(cfg.learning.delayed_readout_learning_rate),
                    "configured_initial_population": int(cfg.lifecycle.initial_population),
                    "configured_max_population": int(cfg.lifecycle.max_population_hard),
                }
            )
            rows.append(row)
    finally:
        organism.shutdown()
        end_backend(sim)
    summary = route.summarize_routing_rows(rows)
    summary.update(
        {
            "task": task.stream.name,
            "model": variant.name,
            "model_family": "CRA_internal",
            "variant": variant.name,
            "variant_group": variant.group,
            "feature_mode": variant.mode,
            "backend": backend_name,
            "seed": int(seed),
            "steps": task.stream.steps,
            "runtime_seconds": time.perf_counter() - started,
            "task_metadata": task.stream.metadata,
            "task_pressure": route.task_pressure_summary(task),
            "hypothesis": variant.hypothesis,
        }
    )
    return rows, summary


def leakage_summary(rows_by_cell_seed: dict[tuple[str, str, int], list[dict[str, Any]]]) -> dict[str, Any]:
    violations: list[dict[str, Any]] = []
    checked = 0
    pre_feedback_selects = 0
    for (task, model, seed), rows in rows_by_cell_seed.items():
        for row in rows:
            if bool(row.get("target_signal_nonzero", False)):
                checked += 1
                step = int(row.get("step", 0))
                due = int(row.get("feedback_due_step", -1))
                if due < step or due < 0:
                    violations.append({"task": task, "model": model, "seed": seed, "step": step, "due": due})
            if bool(row.get("composition_routing_feature_active", False)) or bool(row.get("router_active", False)):
                pre_feedback_selects += 1
    return {
        "checked_feedback_rows": checked,
        "feedback_due_violations": len(violations),
        "pre_feedback_feature_selections": pre_feedback_selects,
        "example_violations": violations[:10],
    }


def aggregate_generic(task: Any, model: str, summaries: list[dict[str, Any]], *, kind: str) -> dict[str, Any]:
    if kind == "composition":
        row = comp.aggregate_runs(task, model, summaries)
        row["subsuite"] = "composition"
        return row
    row = route.aggregate_runs(task, model, summaries)
    row["subsuite"] = "routing"
    return row


def composition_score(row: dict[str, Any]) -> float:
    return 0.60 * float(row.get("heldout_first_accuracy_mean") or 0.0) + 0.40 * float(row.get("heldout_accuracy_mean") or 0.0)


def routing_score(row: dict[str, Any]) -> float:
    return 0.45 * float(row.get("first_heldout_accuracy_mean") or 0.0) + 0.40 * float(row.get("heldout_accuracy_mean") or 0.0) + 0.15 * float(row.get("router_accuracy_mean") or 0.0)


def build_comparisons(aggregates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    by_task_model = {(row["subsuite"], row["task"], row["model"]): row for row in aggregates}
    for subsuite, scorer in (("composition", composition_score), ("routing", routing_score)):
        for task in sorted({row["task"] for row in aggregates if row.get("subsuite") == subsuite}):
            candidate = by_task_model.get((subsuite, task, "internal_composition_routing"), {})
            raw = by_task_model.get((subsuite, task, "v1_8_raw_cra"), {})
            scaffold_name = "module_composition_scaffold" if subsuite == "composition" else "contextual_router_scaffold"
            scaffold = by_task_model.get((subsuite, task, scaffold_name), {})
            ablations = [
                row
                for row in aggregates
                if row.get("subsuite") == subsuite
                and row.get("task") == task
                and row.get("variant_group") == "internal_ablation"
            ]
            standards = [
                row
                for row in aggregates
                if row.get("subsuite") == subsuite
                and row.get("task") == task
                and row.get("model_family") not in {"CRA_internal", "composition_scaffold", "routing_scaffold"}
            ]
            best_ablation = max(ablations, key=scorer, default={})
            best_standard = max(standards, key=scorer, default={})
            first_key = "heldout_first_accuracy_mean" if subsuite == "composition" else "first_heldout_accuracy_mean"
            heldout_key = "heldout_accuracy_mean"
            row = {
                "subsuite": subsuite,
                "task": task,
                "candidate_first_accuracy": candidate.get(first_key),
                "candidate_heldout_accuracy": candidate.get(heldout_key),
                "candidate_router_accuracy": candidate.get("router_accuracy_mean"),
                "candidate_feature_active_steps": candidate.get("feature_active_steps_sum") or candidate.get("router_active_steps_sum"),
                "candidate_module_updates": candidate.get("module_updates_max"),
                "candidate_router_updates": candidate.get("router_updates_max"),
                "candidate_pre_feedback_select_steps": candidate.get("pre_feedback_select_steps_sum"),
                "raw_first_accuracy": raw.get(first_key),
                "scaffold_first_accuracy": scaffold.get(first_key),
                "best_ablation_model": best_ablation.get("model"),
                "best_ablation_first_accuracy": best_ablation.get(first_key),
                "best_standard_model": best_standard.get("model"),
                "best_standard_first_accuracy": best_standard.get(first_key),
                "candidate_first_delta_vs_raw": float(candidate.get(first_key) or 0.0) - float(raw.get(first_key) or 0.0),
                "candidate_first_delta_vs_best_ablation": float(candidate.get(first_key) or 0.0) - float(best_ablation.get(first_key) or 0.0),
                "candidate_first_delta_vs_best_standard": float(candidate.get(first_key) or 0.0) - float(best_standard.get(first_key) or 0.0),
            }
            rows.append(row)
    return rows


def evaluate_tier(
    *,
    aggregates: list[dict[str, Any]],
    comparisons: list[dict[str, Any]],
    leakage: dict[str, Any],
    args: argparse.Namespace,
    models: list[str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    seeds = seeds_from_args(args)
    comp_tasks = [item.strip() for item in args.composition_tasks.split(",") if item.strip()]
    route_tasks = [item.strip() for item in args.routing_tasks.split(",") if item.strip()]
    expected_runs = (
        len(seeds) * len(comp_tasks) * (len(selected_internal_variants("composition")) + 1 + len(models))
        + len(seeds) * len(route_tasks) * (len(selected_internal_variants("routing")) + 1 + len(models))
    )
    observed_runs = sum(int(row.get("runs", 0)) for row in aggregates)
    comp_rows = [row for row in comparisons if row["subsuite"] == "composition"]
    route_rows = [row for row in comparisons if row["subsuite"] == "routing"]
    candidate_comp_first = [float(row.get("candidate_first_accuracy") or 0.0) for row in comp_rows]
    candidate_comp_heldout = [float(row.get("candidate_heldout_accuracy") or 0.0) for row in comp_rows]
    candidate_route_first = [float(row.get("candidate_first_accuracy") or 0.0) for row in route_rows]
    candidate_route_heldout = [float(row.get("candidate_heldout_accuracy") or 0.0) for row in route_rows]
    candidate_route_acc = [float(row.get("candidate_router_accuracy") or 0.0) for row in route_rows]
    raw_edges = [float(row.get("candidate_first_delta_vs_raw") or 0.0) for row in comparisons]
    ablation_edges = [float(row.get("candidate_first_delta_vs_best_ablation") or 0.0) for row in comparisons]
    standard_edges = [float(row.get("candidate_first_delta_vs_best_standard") or 0.0) for row in comparisons]
    module_updates = sum(float(row.get("candidate_module_updates") or 0.0) for row in comparisons)
    router_updates = sum(float(row.get("candidate_router_updates") or 0.0) for row in route_rows)
    pre_feedback = sum(float(row.get("candidate_pre_feedback_select_steps") or 0.0) for row in route_rows)
    active_steps = sum(float(row.get("candidate_feature_active_steps") or 0.0) for row in comparisons)
    base_criteria = [
        criterion("full internal/scaffold/baseline/task/seed matrix completed", observed_runs, "==", expected_runs, observed_runs == expected_runs),
        criterion("feedback timing has no leakage violations", leakage.get("feedback_due_violations"), "==", 0, int(leakage.get("feedback_due_violations", 0)) == 0),
        criterion("internal candidate learned primitive module tables", module_updates, ">", 0, module_updates > 0),
        criterion("internal candidate learned context router", router_updates, ">", 0, router_updates > 0),
        criterion("internal candidate selected routed/composed features before feedback", active_steps + pre_feedback, ">", 0, active_steps + pre_feedback > 0),
    ]
    science_criteria = [
        criterion("internal candidate reaches composition first-heldout threshold", min(candidate_comp_first) if candidate_comp_first else None, ">=", args.min_composition_first_accuracy, bool(candidate_comp_first) and min(candidate_comp_first) >= args.min_composition_first_accuracy),
        criterion("internal candidate reaches composition heldout threshold", min(candidate_comp_heldout) if candidate_comp_heldout else None, ">=", args.min_composition_heldout_accuracy, bool(candidate_comp_heldout) and min(candidate_comp_heldout) >= args.min_composition_heldout_accuracy),
        criterion("internal candidate reaches routing first-heldout threshold", min(candidate_route_first) if candidate_route_first else None, ">=", args.min_routing_first_accuracy, bool(candidate_route_first) and min(candidate_route_first) >= args.min_routing_first_accuracy),
        criterion("internal candidate reaches routing heldout threshold", min(candidate_route_heldout) if candidate_route_heldout else None, ">=", args.min_routing_heldout_accuracy, bool(candidate_route_heldout) and min(candidate_route_heldout) >= args.min_routing_heldout_accuracy),
        criterion("internal candidate route selection is correct", min(candidate_route_acc) if candidate_route_acc else None, ">=", args.min_routing_accuracy, bool(candidate_route_acc) and min(candidate_route_acc) >= args.min_routing_accuracy),
        criterion("internal candidate improves over raw CRA", min(raw_edges) if raw_edges else None, ">=", args.min_edge_vs_raw, bool(raw_edges) and min(raw_edges) >= args.min_edge_vs_raw),
        criterion("internal shams are worse than candidate", min(ablation_edges) if ablation_edges else None, ">=", args.min_edge_vs_ablation, bool(ablation_edges) and min(ablation_edges) >= args.min_edge_vs_ablation),
        criterion(
            "internal candidate does not underperform selected standard baselines",
            min(standard_edges) if standard_edges else None,
            ">=",
            -args.max_standard_regression,
            bool(standard_edges) and min(standard_edges) >= -args.max_standard_regression,
        ),
        criterion(
            "internal candidate has a meaningful edge over selected standard baselines somewhere",
            max(standard_edges) if standard_edges else None,
            ">=",
            args.min_edge_vs_standard,
            bool(standard_edges) and max(standard_edges) >= args.min_edge_vs_standard,
        ),
    ]
    criteria = base_criteria if args.smoke else base_criteria + science_criteria
    summary = {
        "expected_runs": expected_runs,
        "observed_runs": observed_runs,
        "composition_tasks": comp_tasks,
        "routing_tasks": route_tasks,
        "seeds": seeds,
        "models": models,
        "smoke": bool(args.smoke),
        "leakage": leakage,
        "candidate_module_updates_sum": module_updates,
        "candidate_router_updates_sum": router_updates,
        "candidate_pre_feedback_select_steps_sum": pre_feedback,
        "claim_boundary": "Software promotion gate only: internal host-side composition/routing mechanism, not hardware/on-chip routing, language, planning, or AGI evidence.",
    }
    return criteria, summary


def aggregate_csv_rows(aggregates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fields = [
        "subsuite",
        "task",
        "model",
        "model_family",
        "variant_group",
        "runs",
        "steps",
        "all_accuracy_mean",
        "tail_accuracy_mean",
        "heldout_accuracy_mean",
        "heldout_first_accuracy_mean",
        "first_heldout_accuracy_mean",
        "router_accuracy_mean",
        "primitive_accuracy_mean",
        "composition_train_accuracy_mean",
        "route_train_accuracy_mean",
        "prediction_target_corr_mean",
        "runtime_seconds_mean",
        "feature_active_steps_sum",
        "router_active_steps_sum",
        "module_updates_max",
        "router_updates_max",
        "pre_feedback_select_steps_sum",
    ]
    return [{field: row.get(field) for field in fields} for row in aggregates]


def build_fairness_contract(args: argparse.Namespace, models: list[str]) -> dict[str, Any]:
    return {
        "tier": TIER,
        "generated_at_utc": utc_now(),
        "claim_boundary": "Tier 5.13c is software evidence for an internal host-side composition/routing mechanism only.",
        "candidate": "internal_composition_routing",
        "frozen_comparator": "v1_8_raw_cra",
        "scaffold_upper_bounds": ["module_composition_scaffold", "contextual_router_scaffold"],
        "internal_ablation_controls": [variant.name for variant in INTERNAL_VARIANTS if variant.group == "internal_ablation"],
        "selected_external_baselines": models,
        "fairness_rules": [
            "All models see the same scalar stream, target stream, evaluation mask, and feedback_due_step arrays per seed.",
            "The internal mechanism can update current visible cues before a decision, but module/router learning occurs only after feedback for that decision is scored.",
            "Held-out composition and routing metrics are scored before held-out-specific feedback can update the mechanism.",
            "Reset, no-write, skill-shuffle, order-shuffle, context-shuffle, random-router, and always-on shams must lose before promotion.",
            "External scaffold upper bounds are reported but are not native/internal CRA evidence.",
        ],
        "leakage_rules": [
            "feedback_due_step must never precede the scored decision step",
            "routed/composed feature telemetry must be selected before feedback update counters advance for the same step",
        ],
        "composition_tasks": args.composition_tasks,
        "routing_tasks": args.routing_tasks,
        "steps": {"composition": args.composition_steps, "routing": args.routing_steps},
        "seeds": seeds_from_args(args),
    }


def plot_comparisons(path: Path, comparisons: list[dict[str, Any]]) -> None:
    if plt is None:
        path.with_suffix(".txt").write_text(f"matplotlib unavailable: {MATPLOTLIB_ERROR}\n", encoding="utf-8")
        return
    labels = [f"{row['subsuite']}\n{row['task'].replace('_', ' ')}" for row in comparisons]
    candidate = [float(row.get("candidate_first_accuracy") or 0.0) for row in comparisons]
    raw = [float(row.get("raw_first_accuracy") or 0.0) for row in comparisons]
    ablation = [float(row.get("best_ablation_first_accuracy") or 0.0) for row in comparisons]
    standard = [float(row.get("best_standard_first_accuracy") or 0.0) for row in comparisons]
    x = np.arange(len(labels))
    width = 0.2
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.bar(x - 1.5 * width, raw, width, label="raw v1.8 CRA")
    ax.bar(x - 0.5 * width, ablation, width, label="best internal sham")
    ax.bar(x + 0.5 * width, standard, width, label="best selected baseline")
    ax.bar(x + 1.5 * width, candidate, width, label="internal composition/routing")
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("first held-out accuracy")
    ax.set_title("Tier 5.13c internal composition/routing promotion gate")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=20, ha="right")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def write_report(path: Path, result: dict[str, Any], args: argparse.Namespace, output_dir: Path) -> None:
    lines = [
        "# Tier 5.13c Internal Composition / Routing Promotion Findings",
        "",
        f"- Generated: `{result['generated_at_utc']}`",
        f"- Status: **{result['status'].upper()}**",
        f"- Backend for CRA comparators: `{args.backend}`",
        f"- Composition steps: `{args.composition_steps}`",
        f"- Routing steps: `{args.routing_steps}`",
        f"- Seeds: `{', '.join(str(seed) for seed in seeds_from_args(args))}`",
        f"- Composition tasks: `{args.composition_tasks}`",
        f"- Routing tasks: `{args.routing_tasks}`",
        f"- Selected standard baselines: `{args.models}`",
        f"- Smoke mode: `{args.smoke}`",
        f"- Output directory: `{output_dir}`",
        "",
        "Tier 5.13c tests whether the composition/router scaffolds from Tier 5.13 and 5.13b can be internalized into CRA as a bounded host-side mechanism with causal sham controls.",
        "",
        "## Claim Boundary",
        "",
        "- This is software evidence, not SpiNNaker hardware evidence.",
        "- The mechanism is internal to the CRA host loop, but not native on-chip routing.",
        "- This does not prove language reasoning, long-horizon planning, AGI, or autonomous tool use.",
        "- A pass authorizes a new composition/routing candidate baseline only after compact regression also passes.",
        "",
        "## Comparisons",
        "",
        "| Suite | Task | Candidate first | Candidate heldout | Router acc | Raw first | Scaffold first | Best sham | Sham first | Best baseline | Baseline first | Edge vs raw | Edge vs sham | Edge vs baseline |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in result["comparisons"]:
        lines.append(
            "| {subsuite} | {task} | {candidate_first_accuracy} | {candidate_heldout_accuracy} | {candidate_router_accuracy} | {raw_first_accuracy} | {scaffold_first_accuracy} | `{best_ablation_model}` | {best_ablation_first_accuracy} | `{best_standard_model}` | {best_standard_first_accuracy} | {candidate_first_delta_vs_raw} | {candidate_first_delta_vs_best_ablation} | {candidate_first_delta_vs_best_standard} |".format(
                **{k: markdown_value(v) for k, v in row.items()}
            )
        )
    lines.extend(["", "## Criteria", "", "| Criterion | Value | Rule | Pass | Note |", "| --- | --- | --- | --- | --- |"])
    for item in result["criteria"]:
        lines.append(
            f"| {item['name']} | {markdown_value(item.get('value'))} | {item.get('operator')} {markdown_value(item.get('threshold'))} | {'yes' if item.get('passed') else 'no'} | {item.get('note', '')} |"
        )
    if result.get("failure_reason"):
        lines.extend(["", f"Failure: {result['failure_reason']}"])
    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            "- `tier5_13c_results.json`: machine-readable manifest.",
            "- `tier5_13c_report.md`: human findings and claim boundary.",
            "- `tier5_13c_summary.csv`: aggregate task/model metrics.",
            "- `tier5_13c_comparisons.csv`: candidate-vs-sham/baseline table.",
            "- `tier5_13c_fairness_contract.json`: predeclared fairness/leakage rules.",
            "- `tier5_13c_internal_composition_routing.png`: first-heldout plot.",
            "- `*_timeseries.csv`: per-task/per-model/per-seed traces.",
            "",
            "![tier5_13c](tier5_13c_internal_composition_routing.png)",
        ]
    )
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_latest(output_dir: Path, manifest_json: Path, report_md: Path, summary_csv: Path, status: str) -> None:
    latest = ROOT / "controlled_test_output" / "tier5_13c_latest_manifest.json"
    write_json(
        latest,
        {
            "tier": TIER,
            "status": status,
            "canonical": False,
            "claim": "Latest Tier 5.13c internal composition/routing promotion gate; requires compact regression before baseline freeze.",
            "generated_at_utc": utc_now(),
            "output_dir": str(output_dir),
            "manifest": str(manifest_json),
            "report": str(report_md),
            "summary_csv": str(summary_csv),
        },
    )


def run_tier(args: argparse.Namespace, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    models = parse_models(args.models)
    seeds = seeds_from_args(args)
    artifacts: dict[str, str] = {}
    summaries_by_key: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    tasks_by_key: dict[tuple[str, str], Any] = {}
    rows_by_cell_seed: dict[tuple[str, str, int], list[dict[str, Any]]] = {}
    started = time.perf_counter()

    comp_args = make_task_args(args, tasks=args.composition_tasks, steps=args.composition_steps)
    route_args = make_task_args(args, tasks=args.routing_tasks, steps=args.routing_steps)
    comp_scaffold = next(v for v in comp.VARIANTS if v.name == "module_composition_scaffold")
    route_scaffold = next(v for v in route.VARIANTS if v.name == "contextual_router_scaffold")

    for seed in seeds:
        for task in comp.build_tasks(comp_args, seed=args.task_seed + seed):
            tasks_by_key[("composition", task.stream.name)] = task
            for variant in selected_internal_variants("composition"):
                print(f"[tier5.13c] suite=composition task={task.stream.name} variant={variant.name} seed={seed}", flush=True)
                rows, summary = run_internal_composition(task, variant, seed=seed, args=args)
                csv_path = output_dir / f"composition_{task.stream.name}_{variant.name}_seed{seed}_timeseries.csv"
                write_csv(csv_path, rows)
                artifacts[f"composition_{task.stream.name}_{variant.name}_seed{seed}_timeseries_csv"] = str(csv_path)
                summaries_by_key.setdefault(("composition", task.stream.name, variant.name), []).append(summary)
                rows_by_cell_seed[(f"composition:{task.stream.name}", variant.name, seed)] = rows
            print(f"[tier5.13c] suite=composition task={task.stream.name} scaffold={comp_scaffold.name} seed={seed}", flush=True)
            rows, summary = comp.run_rule_variant(task, comp_scaffold, seed=seed, args=args)
            csv_path = output_dir / f"composition_{task.stream.name}_{comp_scaffold.name}_seed{seed}_timeseries.csv"
            write_csv(csv_path, rows)
            artifacts[f"composition_{task.stream.name}_{comp_scaffold.name}_seed{seed}_timeseries_csv"] = str(csv_path)
            summaries_by_key.setdefault(("composition", task.stream.name, comp_scaffold.name), []).append(summary)
            rows_by_cell_seed[(f"composition:{task.stream.name}", comp_scaffold.name, seed)] = rows
            for model in models:
                print(f"[tier5.13c] suite=composition task={task.stream.name} model={model} seed={seed}", flush=True)
                rows, summary = comp.run_external_model(task, model, seed=seed, args=args)
                csv_path = output_dir / f"composition_{task.stream.name}_{model}_seed{seed}_timeseries.csv"
                write_csv(csv_path, rows)
                artifacts[f"composition_{task.stream.name}_{model}_seed{seed}_timeseries_csv"] = str(csv_path)
                summaries_by_key.setdefault(("composition", task.stream.name, model), []).append(summary)
                rows_by_cell_seed[(f"composition:{task.stream.name}", model, seed)] = rows

        for task in route.build_tasks(route_args, seed):
            tasks_by_key[("routing", task.stream.name)] = task
            for variant in selected_internal_variants("routing"):
                print(f"[tier5.13c] suite=routing task={task.stream.name} variant={variant.name} seed={seed}", flush=True)
                rows, summary = run_internal_routing(task, variant, seed=seed, args=args)
                csv_path = output_dir / f"routing_{task.stream.name}_{variant.name}_seed{seed}_timeseries.csv"
                write_csv(csv_path, rows)
                artifacts[f"routing_{task.stream.name}_{variant.name}_seed{seed}_timeseries_csv"] = str(csv_path)
                summaries_by_key.setdefault(("routing", task.stream.name, variant.name), []).append(summary)
                rows_by_cell_seed[(f"routing:{task.stream.name}", variant.name, seed)] = rows
            print(f"[tier5.13c] suite=routing task={task.stream.name} scaffold={route_scaffold.name} seed={seed}", flush=True)
            rows, summary = route.run_rule_variant(task, route_scaffold, seed=seed, args=args)
            csv_path = output_dir / f"routing_{task.stream.name}_{route_scaffold.name}_seed{seed}_timeseries.csv"
            write_csv(csv_path, rows)
            artifacts[f"routing_{task.stream.name}_{route_scaffold.name}_seed{seed}_timeseries_csv"] = str(csv_path)
            summaries_by_key.setdefault(("routing", task.stream.name, route_scaffold.name), []).append(summary)
            rows_by_cell_seed[(f"routing:{task.stream.name}", route_scaffold.name, seed)] = rows
            for model in models:
                print(f"[tier5.13c] suite=routing task={task.stream.name} model={model} seed={seed}", flush=True)
                rows, summary = route.run_external_model(task, model, seed=seed, args=args)
                csv_path = output_dir / f"routing_{task.stream.name}_{model}_seed{seed}_timeseries.csv"
                write_csv(csv_path, rows)
                artifacts[f"routing_{task.stream.name}_{model}_seed{seed}_timeseries_csv"] = str(csv_path)
                summaries_by_key.setdefault(("routing", task.stream.name, model), []).append(summary)
                rows_by_cell_seed[(f"routing:{task.stream.name}", model, seed)] = rows

    aggregates = [
        aggregate_generic(tasks_by_key[(subsuite, task_name)], model, summaries, kind=subsuite)
        for (subsuite, task_name, model), summaries in sorted(summaries_by_key.items())
    ]
    comparisons = build_comparisons(aggregates)
    leakage = leakage_summary(rows_by_cell_seed)
    criteria, run_summary = evaluate_tier(aggregates=aggregates, comparisons=comparisons, leakage=leakage, args=args, models=models)
    status, failure_reason = pass_fail(criteria)

    summary_csv = output_dir / "tier5_13c_summary.csv"
    comparisons_csv = output_dir / "tier5_13c_comparisons.csv"
    fairness_json = output_dir / "tier5_13c_fairness_contract.json"
    plot_png = output_dir / "tier5_13c_internal_composition_routing.png"
    report_md = output_dir / "tier5_13c_report.md"
    manifest_json = output_dir / "tier5_13c_results.json"
    write_csv(summary_csv, aggregate_csv_rows(aggregates))
    write_csv(comparisons_csv, comparisons)
    write_json(fairness_json, build_fairness_contract(args, models))
    plot_comparisons(plot_png, comparisons)
    artifacts.update(
        {
            "summary_csv": str(summary_csv),
            "comparisons_csv": str(comparisons_csv),
            "fairness_contract_json": str(fairness_json),
            "plot_png": str(plot_png),
            "report_md": str(report_md),
        }
    )
    result = {
        "tier": TIER,
        "generated_at_utc": utc_now(),
        "status": status,
        "failure_reason": failure_reason,
        "output_dir": str(output_dir),
        "command": " ".join(sys.argv),
        "summary": {**run_summary, "runtime_seconds": time.perf_counter() - started},
        "criteria": criteria,
        "comparisons": comparisons,
        "aggregates": aggregates,
        "artifacts": artifacts,
    }
    write_json(manifest_json, result)
    artifacts["manifest_json"] = str(manifest_json)
    write_report(report_md, result, args, output_dir)
    write_json(manifest_json, result)
    write_latest(output_dir, manifest_json, report_md, summary_csv, status)
    return result


def build_parser() -> argparse.ArgumentParser:
    parent = build_tier5_1_parser()
    parser = argparse.ArgumentParser(description=TIER, parents=[parent], conflict_handler="resolve")
    parser.set_defaults(backend="mock", seed_count=3, models=DEFAULT_MODELS)
    parser.add_argument("--composition-tasks", default=DEFAULT_COMPOSITION_TASKS)
    parser.add_argument("--routing-tasks", default=DEFAULT_ROUTING_TASKS)
    parser.add_argument("--composition-steps", type=int, default=720)
    parser.add_argument("--routing-steps", type=int, default=960)
    parser.add_argument("--amplitude", type=float, default=0.01)
    parser.add_argument("--dt-seconds", type=float, default=60.0)
    parser.add_argument("--cra-population-size", type=int, default=8)
    parser.add_argument("--cra-readout-lr", type=float, default=0.10)
    parser.add_argument("--cra-delayed-readout-lr", type=float, default=0.20)
    parser.add_argument("--composition-prediction-gain", type=float, default=100.0)
    parser.add_argument("--message-passing-steps", type=int, default=1)
    parser.add_argument("--message-context-gain", type=float, default=0.025)
    parser.add_argument("--message-prediction-mix", type=float, default=0.35)
    parser.add_argument("--primitive-repeats", type=int, default=4)
    parser.add_argument("--composition-repeats", type=int, default=4)
    parser.add_argument("--heldout-repeats", type=int, default=5)
    parser.add_argument("--distractor-gap", type=int, default=8)
    parser.add_argument("--route-train-repeats", type=int, default=4)
    parser.add_argument("--routing-gap", type=int, default=10)
    parser.add_argument("--task-seed", type=int, default=0)
    parser.add_argument("--min-composition-first-accuracy", type=float, default=0.95)
    parser.add_argument("--min-composition-heldout-accuracy", type=float, default=0.95)
    parser.add_argument("--min-routing-first-accuracy", type=float, default=0.95)
    parser.add_argument("--min-routing-heldout-accuracy", type=float, default=0.95)
    parser.add_argument("--min-routing-accuracy", type=float, default=0.95)
    parser.add_argument("--min-edge-vs-raw", type=float, default=0.20)
    parser.add_argument("--min-edge-vs-ablation", type=float, default=0.20)
    parser.add_argument("--min-edge-vs-standard", type=float, default=0.10)
    parser.add_argument("--max-standard-regression", type=float, default=0.01)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--stop-on-fail", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.smoke:
        args.composition_tasks = "heldout_skill_pair"
        args.routing_tasks = "heldout_context_routing"
        args.composition_steps = min(int(args.composition_steps), 360)
        args.routing_steps = min(int(args.routing_steps), 760)
        args.seed_count = min(int(args.seed_count), 1)
        args.models = "sign_persistence,online_perceptron"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_dir = args.output_dir or (ROOT / "controlled_test_output" / f"tier5_13c_{stamp}")
    output_dir = output_dir.resolve()
    try:
        result = run_tier(args, output_dir)
    except Exception as exc:
        output_dir.mkdir(parents=True, exist_ok=True)
        failure = {
            "tier": TIER,
            "generated_at_utc": utc_now(),
            "status": "blocked",
            "failure_reason": str(exc),
            "output_dir": str(output_dir),
        }
        manifest_json = output_dir / "tier5_13c_results.json"
        report_md = output_dir / "tier5_13c_report.md"
        write_json(manifest_json, failure)
        report_md.write_text(f"# Tier 5.13c Internal Composition / Routing Promotion Findings\n\nStatus: **BLOCKED**\n\nFailure: {exc}\n", encoding="utf-8")
        print(json.dumps(json_safe(failure), indent=2), file=sys.stderr)
        return 2
    print(json.dumps(json_safe({"status": result["status"], "output_dir": result["output_dir"], "failure_reason": result.get("failure_reason")}), indent=2))
    if result["status"] != "pass" and args.stop_on_fail:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
