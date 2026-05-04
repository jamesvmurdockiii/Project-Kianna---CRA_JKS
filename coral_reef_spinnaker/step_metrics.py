"""
Step telemetry dataclass and assembly helpers for Coral Reef Architecture.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

import numpy as np

from .reef_network import ReefEdge


@dataclass
class StepMetrics:
    """Comprehensive step telemetry."""

    step: int = 0
    dt_ms: float = 100.0

    n_polyps: int = 0
    n_alive: int = 0
    n_juvenile: int = 0
    n_adult: int = 0
    births_this_step: int = 0
    deaths_this_step: int = 0

    mean_trophic_health: float = 0.0
    min_trophic_health: float = 0.0
    max_trophic_health: float = 0.0

    colony_prediction: float = 0.0
    raw_dopamine: float = 0.0
    mean_directional_accuracy_ema: float = 0.5

    capital: float = 1.0
    position_size: float = 0.0
    direction_correct: bool = False

    n_edges: int = 0
    n_gap_junctions: int = 0
    n_ff: int = 0
    n_lat: int = 0
    n_fb: int = 0
    motif_message_total: float = 0.0
    ff_message_total: float = 0.0
    lat_message_total: float = 0.0
    fb_message_total: float = 0.0
    graph_context_mean_abs: float = 0.0
    graph_context_nonzero_count: int = 0
    macro_eligibility_trace_abs_sum: float = 0.0
    macro_eligibility_trace_nonzero_count: int = 0
    macro_eligibility_matured_updates: int = 0
    macro_eligibility_trace_mode: str = "disabled"
    macro_eligibility_credit_mode: str = "disabled"
    context_memory_enabled: bool = False
    context_memory_mode: str = "disabled"
    context_memory_value: int = 0
    context_memory_updates: int = 0
    context_memory_feature_active: bool = False
    context_memory_feature_source: str = "disabled"
    context_memory_visible_cue_sign: int = 0
    context_memory_raw_observation: float = 0.0
    context_memory_bound_observation: float = 0.0
    context_memory_key: str = ""
    context_memory_slot_count: int = 0
    predictive_context_enabled: bool = False
    predictive_context_mode: str = "disabled"
    predictive_context_value: int = 0
    predictive_context_updates: int = 0
    predictive_context_feature_active: bool = False
    predictive_context_feature_source: str = "disabled"
    predictive_context_visible_signal: int = 0
    predictive_context_raw_observation: float = 0.0
    predictive_context_bound_observation: float = 0.0
    predictive_context_key: str = ""
    predictive_context_slot_count: int = 0
    composition_routing_enabled: bool = False
    composition_routing_mode: str = "disabled"
    composition_routing_feature_active: bool = False
    composition_routing_feature_source: str = "disabled"
    composition_routing_raw_observation: float = 0.0
    composition_routing_bound_observation: float = 0.0
    composition_routing_event_type: str = ""
    composition_routing_phase: str = ""
    composition_routing_skill_a: str = ""
    composition_routing_skill_b: str = ""
    composition_routing_selected_skill: str = ""
    composition_routing_context: str = ""
    composition_routing_true_skill: str = ""
    composition_routing_router_correct: bool = False
    composition_routing_module_updates: int = 0
    composition_routing_router_updates: int = 0
    composition_routing_module_uses: int = 0
    composition_routing_router_uses: int = 0
    composition_routing_correct_route_uses: int = 0
    composition_routing_pre_feedback_select_steps: int = 0

    I_union_bits: float = 0.0
    changepoint_probability: float = 0.0

    spinnaker_wall_ms: float = 0.0
    host_compute_wall_ms: float = 0.0
    total_step_wall_ms: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=float)


def empty_metrics(step: int, t_spinnaker: float) -> StepMetrics:
    """Return a minimal StepMetrics for an extinct or failed step."""
    return StepMetrics(
        step=step,
        spinnaker_wall_ms=t_spinnaker,
        host_compute_wall_ms=0.0,
        total_step_wall_ms=t_spinnaker,
    )


def assemble_step_metrics(
    *,
    step: int,
    dt_ms: float,
    population_size: int,
    polyp_states: list,
    network_edges: dict,
    gap_junctions: dict,
    energy_result: Any,
    learning_result: Any,
    task_outcome: Any,
    stream_mi: dict[str, float],
    timing: dict[str, float],
    lifecycle_events: list | None = None,
    accuracy_ema: float = 0.5,
    changepoint_probability: float = 0.0,
    motif_activity: dict[str, Any] | None = None,
    context_memory_activity: dict[str, Any] | None = None,
    predictive_context_activity: dict[str, Any] | None = None,
    composition_routing_activity: dict[str, Any] | None = None,
) -> StepMetrics:
    """Assemble a StepMetrics object from subsystem results.

    This is a pure function — it has no side effects and depends only on
    its arguments.  Extracted from :class:`Organism` to keep the
    orchestrator focused on control flow.
    """
    alive = [s for s in polyp_states if getattr(s, "is_alive", False)]
    n_alive = len(alive)
    n_juv = sum(1 for s in alive if getattr(s, "is_juvenile", False))
    n_adt = n_alive - n_juv

    trophic_vals = [s.trophic_health for s in alive]
    mean_trophic = float(np.mean(trophic_vals)) if trophic_vals else 0.0
    min_trophic = float(np.min(trophic_vals)) if trophic_vals else 0.0
    max_trophic = float(np.max(trophic_vals)) if trophic_vals else 0.0

    n_edges = 0
    n_ff = n_lat = n_fb = 0
    for edge in network_edges.values():
        if isinstance(edge, ReefEdge) and not edge.is_pruned:
            n_edges += 1
            if edge.edge_type == "ff":
                n_ff += 1
            elif edge.edge_type == "lat":
                n_lat += 1
            elif edge.edge_type == "fb":
                n_fb += 1

    births_this_step = 0
    deaths_this_step = 0
    if lifecycle_events:
        births_this_step = sum(
            1 for e in lifecycle_events if e.event_type in ("birth", "cleavage")
        )
        deaths_this_step = sum(
            1 for e in lifecycle_events if e.event_type == "death"
        )
    motif_activity = motif_activity or {}
    context_memory_activity = context_memory_activity or {}
    predictive_context_activity = predictive_context_activity or {}
    composition_routing_activity = composition_routing_activity or {}

    return StepMetrics(
        step=step,
        dt_ms=dt_ms,
        n_polyps=population_size,
        n_alive=n_alive,
        n_juvenile=n_juv,
        n_adult=n_adt,
        births_this_step=births_this_step,
        deaths_this_step=deaths_this_step,
        mean_trophic_health=mean_trophic,
        min_trophic_health=min_trophic,
        max_trophic_health=max_trophic,
        colony_prediction=task_outcome.colony_prediction,
        raw_dopamine=task_outcome.raw_dopamine,
        mean_directional_accuracy_ema=accuracy_ema,
        capital=task_outcome.capital,
        position_size=task_outcome.position_size,
        direction_correct=task_outcome.direction_correct,
        n_edges=n_edges,
        n_gap_junctions=len(gap_junctions),
        n_ff=n_ff,
        n_lat=n_lat,
        n_fb=n_fb,
        motif_message_total=float(motif_activity.get("motif_message_total", 0.0) or 0.0),
        ff_message_total=float(motif_activity.get("ff_message_total", 0.0) or 0.0),
        lat_message_total=float(motif_activity.get("lat_message_total", 0.0) or 0.0),
        fb_message_total=float(motif_activity.get("fb_message_total", 0.0) or 0.0),
        graph_context_mean_abs=float(motif_activity.get("graph_context_mean_abs", 0.0) or 0.0),
        graph_context_nonzero_count=int(motif_activity.get("graph_context_nonzero_count", 0) or 0),
        macro_eligibility_trace_abs_sum=float(
            getattr(learning_result, "macro_eligibility_trace_abs_sum", 0.0) or 0.0
        ),
        macro_eligibility_trace_nonzero_count=int(
            getattr(learning_result, "macro_eligibility_trace_nonzero_count", 0) or 0
        ),
        macro_eligibility_matured_updates=int(
            getattr(learning_result, "macro_eligibility_matured_updates", 0) or 0
        ),
        macro_eligibility_trace_mode=str(
            getattr(learning_result, "macro_eligibility_trace_mode", "disabled") or "disabled"
        ),
        macro_eligibility_credit_mode=str(
            getattr(learning_result, "macro_eligibility_credit_mode", "disabled") or "disabled"
        ),
        context_memory_enabled=bool(context_memory_activity.get("enabled", False)),
        context_memory_mode=str(context_memory_activity.get("mode", "disabled") or "disabled"),
        context_memory_value=int(context_memory_activity.get("context_memory_value", 0) or 0),
        context_memory_updates=int(context_memory_activity.get("context_memory_updates", 0) or 0),
        context_memory_feature_active=bool(context_memory_activity.get("feature_active", False)),
        context_memory_feature_source=str(context_memory_activity.get("feature_source", "disabled") or "disabled"),
        context_memory_visible_cue_sign=int(context_memory_activity.get("visible_cue_sign", 0) or 0),
        context_memory_raw_observation=float(context_memory_activity.get("raw_observation", 0.0) or 0.0),
        context_memory_bound_observation=float(context_memory_activity.get("bound_observation", 0.0) or 0.0),
        context_memory_key=str(context_memory_activity.get("context_memory_key", "") or ""),
        context_memory_slot_count=int(context_memory_activity.get("context_memory_slot_count", 0) or 0),
        predictive_context_enabled=bool(predictive_context_activity.get("enabled", False)),
        predictive_context_mode=str(predictive_context_activity.get("mode", "disabled") or "disabled"),
        predictive_context_value=int(predictive_context_activity.get("predictive_context_value", 0) or 0),
        predictive_context_updates=int(predictive_context_activity.get("predictive_context_updates", 0) or 0),
        predictive_context_feature_active=bool(predictive_context_activity.get("feature_active", False)),
        predictive_context_feature_source=str(predictive_context_activity.get("feature_source", "disabled") or "disabled"),
        predictive_context_visible_signal=int(predictive_context_activity.get("visible_signal", 0) or 0),
        predictive_context_raw_observation=float(predictive_context_activity.get("raw_observation", 0.0) or 0.0),
        predictive_context_bound_observation=float(predictive_context_activity.get("bound_observation", 0.0) or 0.0),
        predictive_context_key=str(predictive_context_activity.get("predictive_context_key", "") or ""),
        predictive_context_slot_count=int(predictive_context_activity.get("predictive_context_slot_count", 0) or 0),
        composition_routing_enabled=bool(composition_routing_activity.get("enabled", False)),
        composition_routing_mode=str(composition_routing_activity.get("mode", "disabled") or "disabled"),
        composition_routing_feature_active=bool(composition_routing_activity.get("feature_active", False)),
        composition_routing_feature_source=str(composition_routing_activity.get("feature_source", "disabled") or "disabled"),
        composition_routing_raw_observation=float(composition_routing_activity.get("raw_observation", 0.0) or 0.0),
        composition_routing_bound_observation=float(composition_routing_activity.get("bound_observation", 0.0) or 0.0),
        composition_routing_event_type=str(composition_routing_activity.get("event_type", "") or ""),
        composition_routing_phase=str(composition_routing_activity.get("phase", "") or ""),
        composition_routing_skill_a=str(composition_routing_activity.get("skill_a", "") or ""),
        composition_routing_skill_b=str(composition_routing_activity.get("skill_b", "") or ""),
        composition_routing_selected_skill=str(composition_routing_activity.get("selected_skill", "") or ""),
        composition_routing_context=str(composition_routing_activity.get("context", "") or ""),
        composition_routing_true_skill=str(composition_routing_activity.get("true_skill", "") or ""),
        composition_routing_router_correct=bool(composition_routing_activity.get("router_correct", False)),
        composition_routing_module_updates=int(composition_routing_activity.get("module_updates", 0) or 0),
        composition_routing_router_updates=int(composition_routing_activity.get("router_updates", 0) or 0),
        composition_routing_module_uses=int(composition_routing_activity.get("module_uses", 0) or 0),
        composition_routing_router_uses=int(composition_routing_activity.get("router_uses", 0) or 0),
        composition_routing_correct_route_uses=int(composition_routing_activity.get("correct_route_uses", 0) or 0),
        composition_routing_pre_feedback_select_steps=int(composition_routing_activity.get("pre_feedback_select_steps", 0) or 0),
        I_union_bits=sum(stream_mi.values()),
        changepoint_probability=changepoint_probability,
        spinnaker_wall_ms=timing.get("spinnaker", 0.0),
        host_compute_wall_ms=timing.get("host", 0.0),
        total_step_wall_ms=timing.get("total", 0.0),
    )
