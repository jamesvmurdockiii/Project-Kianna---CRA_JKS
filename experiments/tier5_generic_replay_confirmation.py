#!/usr/bin/env python3
"""Tier 5.11d generic replay / consolidation confirmation.

Tier 5.11b and Tier 5.11c showed strong replay repair signal but did not earn
the narrower claim that priority weighting itself is the critical ingredient:
shuffled replay still helped too much. Tier 5.11d changes the predeclared
question to the broader mechanism that remains scientifically alive:
correct-binding replay/consolidation must add causal value beyond no replay and
wrong-memory controls.

This is software evidence only. It is not hardware replay, not on-chip replay,
not biological sleep proof, and not a baseline freeze by itself.
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

from coral_reef_spinnaker import Organism  # noqa: E402
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
from tier4_scaling import min_value, seeds_from_args  # noqa: E402
from tier5_external_baselines import build_parser as build_tier5_1_parser, parse_models, summarize_rows  # noqa: E402
from tier5_memory_pressure_tasks import (  # noqa: E402
    CONTROL_MODELS,
    DEFAULT_MODELS,
    MemoryTask,
    run_control_model,
    run_external_model,
    task_ambiguity_summary,
)
from tier5_sleep_replay_need import (  # noqa: E402
    DEFAULT_TASKS,
    build_tasks,
    context_memory_key_for_step,
    make_config,
    oracle_context_for_step,
    shuffled_context_plan,
    transform_sensory,
)


TIER = "Tier 5.11d - Generic Replay / Consolidation Confirmation"
DEFAULT_VARIANTS = "v1_6_no_replay,prioritized_replay,shuffled_order_replay,random_replay,wrong_key_replay,key_label_permuted_replay,priority_only_ablation,no_consolidation_replay,unbounded_keyed_control,oracle_context_scaffold"
EPS = 1e-12


@dataclass(frozen=True)
class ReplayVariant:
    name: str
    group: str
    runner: str
    feature_mode: str
    replay_mode: str
    hypothesis: str
    overrides: dict[str, Any]


VARIANTS: tuple[ReplayVariant, ...] = (
    ReplayVariant(
        name="v1_6_no_replay",
        group="candidate_no_replay",
        runner="internal",
        feature_mode="keyed",
        replay_mode="none",
        hypothesis="Frozen v1.6 bounded keyed memory without replay/consolidation.",
        overrides={
            "learning.delayed_readout_learning_rate": 0.20,
            "learning.macro_eligibility_enabled": False,
            "learning.context_memory_enabled": True,
            "learning.context_memory_mode": "keyed",
            "learning.context_memory_input_gain": 1.0,
            "learning.context_memory_slot_count": 4,
        },
    ),
    ReplayVariant(
        name="prioritized_replay",
        group="replay_candidate",
        runner="internal",
        feature_mode="keyed",
        replay_mode="prioritized",
        hypothesis="Offline replay selects old/rare observed context episodes and consolidates them back into bounded keyed slots.",
        overrides={
            "learning.delayed_readout_learning_rate": 0.20,
            "learning.macro_eligibility_enabled": False,
            "learning.context_memory_enabled": True,
            "learning.context_memory_mode": "keyed",
            "learning.context_memory_input_gain": 1.0,
            "learning.context_memory_slot_count": 4,
        },
    ),
    ReplayVariant(
        name="shuffled_order_replay",
        group="replay_ablation",
        runner="internal",
        feature_mode="keyed",
        replay_mode="shuffled_order",
        hypothesis="Replay opportunity is matched, but candidate order is shuffled before selection to test whether priority matters.",
        overrides={
            "learning.delayed_readout_learning_rate": 0.20,
            "learning.macro_eligibility_enabled": False,
            "learning.context_memory_enabled": True,
            "learning.context_memory_mode": "keyed",
            "learning.context_memory_input_gain": 1.0,
            "learning.context_memory_slot_count": 4,
        },
    ),
    ReplayVariant(
        name="random_replay",
        group="replay_ablation",
        runner="internal",
        feature_mode="keyed",
        replay_mode="random",
        hypothesis="Replay event count is matched, but contexts are sampled randomly from the observed buffer.",
        overrides={
            "learning.delayed_readout_learning_rate": 0.20,
            "learning.macro_eligibility_enabled": False,
            "learning.context_memory_enabled": True,
            "learning.context_memory_mode": "keyed",
            "learning.context_memory_input_gain": 1.0,
            "learning.context_memory_slot_count": 4,
        },
    ),
    ReplayVariant(
        name="wrong_key_replay",
        group="replay_ablation",
        runner="internal",
        feature_mode="keyed",
        replay_mode="wrong_key",
        hypothesis="Prioritized examples are selected, but each sign is written to the wrong context key.",
        overrides={
            "learning.delayed_readout_learning_rate": 0.20,
            "learning.macro_eligibility_enabled": False,
            "learning.context_memory_enabled": True,
            "learning.context_memory_mode": "keyed",
            "learning.context_memory_input_gain": 1.0,
            "learning.context_memory_slot_count": 4,
        },
    ),
    ReplayVariant(
        name="key_label_permuted_replay",
        group="replay_ablation",
        runner="internal",
        feature_mode="keyed",
        replay_mode="key_label_permuted",
        hypothesis="Prioritized keys are selected, but the replay label/sign is deterministically inverted.",
        overrides={
            "learning.delayed_readout_learning_rate": 0.20,
            "learning.macro_eligibility_enabled": False,
            "learning.context_memory_enabled": True,
            "learning.context_memory_mode": "keyed",
            "learning.context_memory_input_gain": 1.0,
            "learning.context_memory_slot_count": 4,
        },
    ),
    ReplayVariant(
        name="priority_only_ablation",
        group="replay_ablation",
        runner="internal",
        feature_mode="keyed",
        replay_mode="priority_only",
        hypothesis="Prioritized examples are selected and written with matched counts, but into non-task placeholder keys so priority alone cannot restore context binding.",
        overrides={
            "learning.delayed_readout_learning_rate": 0.20,
            "learning.macro_eligibility_enabled": False,
            "learning.context_memory_enabled": True,
            "learning.context_memory_mode": "keyed",
            "learning.context_memory_input_gain": 1.0,
            "learning.context_memory_slot_count": 4,
        },
    ),
    ReplayVariant(
        name="no_consolidation_replay",
        group="replay_ablation",
        runner="internal",
        feature_mode="keyed",
        replay_mode="no_consolidation",
        hypothesis="Replay candidates are selected and logged but not written back into keyed slots.",
        overrides={
            "learning.delayed_readout_learning_rate": 0.20,
            "learning.macro_eligibility_enabled": False,
            "learning.context_memory_enabled": True,
            "learning.context_memory_mode": "keyed",
            "learning.context_memory_input_gain": 1.0,
            "learning.context_memory_slot_count": 4,
        },
    ),
    ReplayVariant(
        name="unbounded_keyed_control",
        group="capacity_upper_bound",
        runner="internal",
        feature_mode="keyed",
        replay_mode="none",
        hypothesis="Capacity upper bound with enough keyed slots to avoid eviction; not a replay mechanism.",
        overrides={
            "learning.delayed_readout_learning_rate": 0.20,
            "learning.macro_eligibility_enabled": False,
            "learning.context_memory_enabled": True,
            "learning.context_memory_mode": "keyed",
            "learning.context_memory_input_gain": 1.0,
            "learning.context_memory_slot_count": 16,
        },
    ),
    ReplayVariant(
        name="oracle_context_scaffold",
        group="external_scaffold",
        runner="external",
        feature_mode="oracle_keyed",
        replay_mode="oracle",
        hypothesis="Oracle scaffold is a solvability upper bound, not replay.",
        overrides={
            "learning.delayed_readout_learning_rate": 0.20,
            "learning.macro_eligibility_enabled": False,
            "learning.context_memory_enabled": False,
        },
    ),
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def parse_variants(raw: str) -> list[ReplayVariant]:
    available = {variant.name: variant for variant in VARIANTS}
    if raw.strip().lower() == "all":
        requested = [variant.name for variant in VARIANTS]
    else:
        requested = [item.strip() for item in raw.split(",") if item.strip()]
    unknown = [name for name in requested if name not in available]
    if unknown:
        raise SystemExit(f"Unknown Tier 5.11d variants: {unknown}; available={sorted(available)}")
    required = {
        "v1_6_no_replay",
        "prioritized_replay",
        "shuffled_order_replay",
        "random_replay",
        "wrong_key_replay",
        "key_label_permuted_replay",
        "priority_only_ablation",
        "no_consolidation_replay",
        "unbounded_keyed_control",
        "oracle_context_scaffold",
    }
    missing = required.difference(requested)
    if missing:
        raise SystemExit(f"Tier 5.11d requires {sorted(required)}; missing={sorted(missing)}")
    return [available[name] for name in requested]


def episode_key_for_step(task: MemoryTask, step: int) -> str:
    return context_memory_key_for_step(task, step)


def observe_context_episode(buffer: list[dict[str, Any]], task: MemoryTask, step: int) -> None:
    raw = float(task.stream.sensory[step])
    sign = strict_sign(raw)
    if task.event_type[step] != "context" or sign == 0:
        return
    key = episode_key_for_step(task, step)
    buffer.append(
        {
            "key": key,
            "sign": int(sign),
            "observed_step": int(step),
            "phase": str(task.phase[step]),
            "trial_id": int(task.trial_id[step]),
        }
    )


def aggregate_buffer(buffer: list[dict[str, Any]], current_step: int) -> list[dict[str, Any]]:
    by_key: dict[str, dict[str, Any]] = {}
    for event in buffer:
        observed = int(event["observed_step"])
        if observed > current_step:
            continue
        key = str(event["key"])
        item = by_key.setdefault(
            key,
            {
                "key": key,
                "sign": int(event["sign"]),
                "first_seen": observed,
                "last_seen": observed,
                "count": 0,
                "phases": set(),
            },
        )
        item["sign"] = int(event["sign"])
        item["first_seen"] = min(int(item["first_seen"]), observed)
        item["last_seen"] = max(int(item["last_seen"]), observed)
        item["count"] = int(item["count"]) + 1
        item["phases"].add(str(event.get("phase", "")))
    rows = []
    for item in by_key.values():
        rows.append(
            {
                **item,
                "age": int(current_step) - int(item["first_seen"]),
                "recency_age": int(current_step) - int(item["last_seen"]),
                "phases": sorted(str(p) for p in item["phases"] if p),
            }
        )
    return rows


def prioritized_selection(buffer: list[dict[str, Any]], current_step: int, limit: int) -> list[dict[str, Any]]:
    rows = aggregate_buffer(buffer, current_step)
    # Rare, old contexts are the target consolidation pressure. This uses only
    # visible context metadata observed before the replay step.
    rows.sort(key=lambda item: (int(item["count"]), int(item["first_seen"]), -int(item["recency_age"]), str(item["key"])))
    return rows[: max(0, int(limit))]


def replay_selection(
    *,
    buffer: list[dict[str, Any]],
    current_step: int,
    variant: ReplayVariant,
    limit: int,
    rng: np.random.Generator,
) -> list[dict[str, Any]]:
    if variant.replay_mode in {"none", "oracle"}:
        return []
    base = prioritized_selection(buffer, current_step, limit)
    if not base:
        return []
    if variant.replay_mode in {"prioritized", "no_consolidation"}:
        return [
            {
                **item,
                "source_key": str(item["key"]),
                "source_sign": int(item["sign"]),
                "replay_transform": variant.replay_mode,
            }
            for item in base
        ]
    if variant.replay_mode == "shuffled_order":
        rows = aggregate_buffer(buffer, current_step)
        order = np.arange(len(rows))
        rng.shuffle(order)
        selected = [rows[int(idx)] for idx in order[: max(0, int(limit))]]
        return [
            {
                **item,
                "source_key": str(item["key"]),
                "source_sign": int(item["sign"]),
                "replay_transform": "shuffled_order",
            }
            for item in selected
        ]
    if variant.replay_mode == "random":
        rows = aggregate_buffer(buffer, current_step)
        if len(rows) <= limit:
            selected = list(rows)
        else:
            idx = rng.choice(len(rows), size=limit, replace=False)
            selected = [rows[int(i)] for i in idx]
        return [
            {
                **item,
                "source_key": str(item["key"]),
                "source_sign": int(item["sign"]),
                "replay_transform": "random",
            }
            for item in selected
        ]
    if variant.replay_mode == "wrong_key":
        keys = [str(item["key"]) for item in base]
        if len(keys) <= 1:
            wrong_keys = [f"wrong_key_for_{keys[0]}"]
        else:
            wrong_keys = keys[1:] + keys[:1]
        return [
            {
                **item,
                "source_key": str(item["key"]),
                "source_sign": int(item["sign"]),
                "key": wrong_keys[idx],
                "sign": int(item["sign"]),
                "replay_transform": "wrong_key",
            }
            for idx, item in enumerate(base)
        ]
    if variant.replay_mode == "key_label_permuted":
        return [
            {
                **item,
                "source_key": str(item["key"]),
                "source_sign": int(item["sign"]),
                "sign": -int(item["sign"]) if int(item["sign"]) != 0 else -1,
                "replay_transform": "key_label_permuted",
            }
            for item in base
        ]
    if variant.replay_mode == "priority_only":
        return [
            {
                **item,
                "source_key": str(item["key"]),
                "source_sign": int(item["sign"]),
                "key": f"priority_only_{idx}",
                "sign": int(item["sign"]),
                "replay_transform": "priority_only_dummy_key",
            }
            for idx, item in enumerate(base)
        ]
    return []


def should_replay_after_step(task: MemoryTask, step: int, args: argparse.Namespace) -> bool:
    if step < int(args.replay_min_step):
        return False
    if bool(task.stream.evaluation_mask[step]):
        return False
    interval = max(1, int(args.replay_offline_interval))
    return (step + 1) % interval == 0


def apply_replay_cycle(
    *,
    organism: Organism,
    task: MemoryTask,
    step: int,
    seed: int,
    variant: ReplayVariant,
    buffer: list[dict[str, Any]],
    args: argparse.Namespace,
    cycle_index: int,
) -> list[dict[str, Any]]:
    if variant.replay_mode in {"none", "oracle"}:
        return []
    rng = np.random.default_rng(seed + 51120 + step * 17 + cycle_index * 31 + sum(ord(c) for c in variant.name))
    limit = int(args.replay_selection_count)
    if limit <= 0:
        limit = max(1, int(getattr(organism.config.learning, "context_memory_slot_count", 4) or 4))
    selected = replay_selection(buffer=buffer, current_step=step, variant=variant, limit=limit, rng=rng)
    events: list[dict[str, Any]] = []
    consolidate = variant.replay_mode != "no_consolidation"
    for rank, item in enumerate(selected):
        replay = organism.replay_context_memory_episode(
            context_memory_key=str(item["key"]),
            context_sign=int(item["sign"]),
            consolidate=consolidate,
            source=f"tier5_11d_{variant.replay_mode}",
        )
        events.append(
            {
                "task": task.stream.name,
                "variant": variant.name,
                "seed": int(seed),
                "replay_cycle": int(cycle_index),
                "replay_step": int(step),
                "rank": int(rank),
                "source_key": str(item.get("source_key", item["key"])),
                "source_sign": int(item.get("source_sign", item["sign"])),
                "selected_key": str(item["key"]),
                "selected_sign": int(item["sign"]),
                "replay_transform": str(item.get("replay_transform", variant.replay_mode)),
                "first_seen": int(item.get("first_seen", -1)),
                "last_seen": int(item.get("last_seen", -1)),
                "count": int(item.get("count", 0)),
                "age": int(item.get("age", 0)),
                "replay_mode": variant.replay_mode,
                "consolidate": bool(consolidate),
                "wrote": bool(replay.get("wrote", False)),
                "future_violation": int(item.get("first_seen", step + 1)) > int(step),
                "slot_count_after": int(replay.get("context_memory_slot_count", 0)),
                "source": str(replay.get("source", "")),
            }
        )
    return events


def run_cra_replay_variant(
    task: MemoryTask,
    *,
    seed: int,
    variant: ReplayVariant,
    args: argparse.Namespace,
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    random.seed(seed)
    np.random.seed(seed)
    sim, backend_name = load_backend(args.backend)
    setup_backend(sim, backend_name)
    cfg = make_config(seed=seed, task=task, variant=variant, args=args)
    organism = Organism(cfg, sim, use_default_trading_bridge=False)
    shuffled = shuffled_context_plan(task, seed)
    external_memory: dict[str, Any] = {"context": 1, "context_updates": 0}
    replay_buffer: list[dict[str, Any]] = []
    replay_events: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    started = time.perf_counter()
    replay_cycle = 0
    try:
        organism.initialize(stream_keys=[task.stream.domain])
        for step in range(task.stream.steps):
            raw_observation = float(task.stream.sensory[step])
            if variant.runner == "external":
                observation, feature = transform_sensory(
                    task=task,
                    step=step,
                    variant=variant,
                    memory=external_memory,
                    shuffled_context_by_trial=shuffled,
                    amplitude=float(args.amplitude),
                )
            else:
                observation = raw_observation
                feature = {
                    "context_memory_value": 0,
                    "visible_cue_sign": 0,
                    "feature_source": "pending_internal",
                    "context_updates": 0,
                    "feature_active": False,
                    "context_memory_key": context_memory_key_for_step(task, step),
                    "context_memory_slot_count": 0,
                }
            consequence = float(task.stream.current_target[step])
            metrics = organism.train_task_step(
                observation_value=observation,
                consequence_value=consequence,
                horizon_signal=consequence,
                dt_seconds=float(args.dt_seconds),
                task_name=task.stream.name,
                metadata={
                    "tier": "5.11d",
                    "variant": variant.name,
                    "event_type": task.event_type[step],
                    "phase": task.phase[step],
                    "trial_id": int(task.trial_id[step]),
                    "context_memory_key": context_memory_key_for_step(task, step),
                },
            )
            if variant.runner == "internal":
                feature = {
                    "context_memory_value": int(metrics.context_memory_value),
                    "visible_cue_sign": int(metrics.context_memory_visible_cue_sign),
                    "feature_source": str(metrics.context_memory_feature_source),
                    "context_updates": int(metrics.context_memory_updates),
                    "feature_active": bool(metrics.context_memory_feature_active),
                    "context_memory_key": str(metrics.context_memory_key),
                    "context_memory_slot_count": int(metrics.context_memory_slot_count),
                }
            prediction = float(metrics.colony_prediction)
            eval_sign = strict_sign(float(task.stream.evaluation_target[step]))
            pred_sign = strict_sign(prediction)
            row = metrics.to_dict()
            injected_observation = float(metrics.context_memory_bound_observation) if variant.runner == "internal" else float(observation)
            row.update(
                {
                    "task": task.stream.name,
                    "model": variant.name,
                    "model_family": "CRA",
                    "variant": variant.name,
                    "variant_group": variant.group,
                    "backend": backend_name,
                    "seed": int(seed),
                    "step": int(step),
                    "event_type": task.event_type[step],
                    "phase": task.phase[step],
                    "trial_id": int(task.trial_id[step]),
                    "context_sign": int(task.context_sign[step]),
                    "decision_cue_sign": int(task.decision_cue_sign[step]),
                    "memory_runner": variant.runner,
                    "replay_mode": variant.replay_mode,
                    "raw_sensory_return_1m": raw_observation,
                    "sensory_return_1m": injected_observation,
                    "target_return_1m": consequence,
                    "target_signal_horizon": float(task.stream.evaluation_target[step]),
                    "target_signal_sign": eval_sign,
                    "target_signal_nonzero": bool(task.stream.evaluation_mask[step] and eval_sign != 0),
                    "prediction_sign": pred_sign,
                    "strict_direction_correct": bool(task.stream.evaluation_mask[step] and pred_sign != 0 and pred_sign == eval_sign),
                    "feedback_due_step": int(task.stream.feedback_due_step[step]),
                    "configured_horizon_bars": int(cfg.learning.evaluation_horizon_bars),
                    "configured_readout_lr": float(cfg.learning.readout_learning_rate),
                    "configured_delayed_readout_lr": float(cfg.learning.delayed_readout_learning_rate),
                    "configured_initial_population": int(cfg.lifecycle.initial_population),
                    "configured_max_population": int(cfg.lifecycle.max_population_hard),
                    **feature,
                }
            )
            rows.append(row)
            observe_context_episode(replay_buffer, task, step)
            if should_replay_after_step(task, step, args):
                cycle_events = apply_replay_cycle(
                    organism=organism,
                    task=task,
                    step=step,
                    seed=seed,
                    variant=variant,
                    buffer=replay_buffer,
                    args=args,
                    cycle_index=replay_cycle,
                )
                replay_cycle += 1 if variant.replay_mode not in {"none", "oracle"} else 0
                replay_events.extend(cycle_events)
                if rows:
                    rows[-1]["replay_events_after_step"] = len(cycle_events)
                    rows[-1]["replay_consolidations_after_step"] = sum(1 for event in cycle_events if event.get("wrote"))
                    rows[-1]["replay_selected_keys_after_step"] = ";".join(str(event.get("selected_key")) for event in cycle_events)
    finally:
        organism.shutdown()
        end_backend(sim)
    summary = summarize_rows(rows)
    feature_active_steps = sum(1 for row in rows if bool(row.get("feature_active", False)))
    context_updates = max([int(row.get("context_updates", 0) or 0) for row in rows], default=0)
    summary.update(
        {
            "task": task.stream.name,
            "model": variant.name,
            "model_family": "CRA",
            "variant": variant.name,
            "variant_group": variant.group,
            "feature_mode": variant.feature_mode,
            "replay_mode": variant.replay_mode,
            "memory_runner": variant.runner,
            "hypothesis": variant.hypothesis,
            "backend": backend_name,
            "seed": int(seed),
            "steps": task.stream.steps,
            "runtime_seconds": time.perf_counter() - started,
            "feature_active_steps": int(feature_active_steps),
            "context_memory_updates": int(context_updates),
            "replay_cycles": len({event["replay_cycle"] for event in replay_events}) if replay_events else 0,
            "replay_events": len(replay_events),
            "replay_consolidations": sum(1 for event in replay_events if bool(event.get("wrote", False))),
            "replay_future_violations": sum(1 for event in replay_events if bool(event.get("future_violation", False))),
            "replay_unique_keys": len({str(event.get("selected_key")) for event in replay_events}),
            "task_metadata": task.stream.metadata,
            "ambiguity": task_ambiguity_summary(task),
            "config_overrides": variant.overrides,
        }
    )
    return rows, summary, replay_events


def leakage_summary(rows_by_cell_seed: dict[tuple[str, str, int], list[dict[str, Any]]], replay_events: list[dict[str, Any]]) -> dict[str, Any]:
    violations: list[dict[str, Any]] = []
    checked = 0
    for (task, model, seed), rows in rows_by_cell_seed.items():
        for row in rows:
            if not bool(row.get("target_signal_nonzero", False)):
                continue
            checked += 1
            step = int(row.get("step", 0))
            due = int(row.get("feedback_due_step", -1))
            if due < step or due < 0:
                violations.append({"task": task, "model": model, "seed": seed, "step": step, "due": due})
    replay_violations = [event for event in replay_events if bool(event.get("future_violation", False))]
    return {
        "checked_feedback_rows": checked,
        "feedback_due_violations": len(violations),
        "example_feedback_violations": violations[:10],
        "checked_replay_events": len(replay_events),
        "replay_future_violations": len(replay_violations),
        "example_replay_violations": replay_violations[:10],
    }


def aggregate_runs(task: MemoryTask, model: str, summaries: list[dict[str, Any]]) -> dict[str, Any]:
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
        "feature_active_steps",
        "context_memory_updates",
        "replay_cycles",
        "replay_events",
        "replay_consolidations",
        "replay_future_violations",
        "replay_unique_keys",
    ]
    aggregate: dict[str, Any] = {
        "task": task.stream.name,
        "display_name": task.stream.display_name,
        "domain": task.stream.domain,
        "model": model,
        "model_family": summaries[0].get("model_family") if summaries else None,
        "variant_group": summaries[0].get("variant_group") if summaries else None,
        "feature_mode": summaries[0].get("feature_mode") if summaries else None,
        "replay_mode": summaries[0].get("replay_mode") if summaries else None,
        "memory_runner": summaries[0].get("memory_runner") if summaries else None,
        "runs": len(summaries),
        "steps": task.stream.steps,
    }
    for key in keys:
        vals = [summary.get(key) for summary in summaries if summary.get(key) is not None]
        valid = [float(v) for v in vals if v is not None]
        aggregate[f"{key}_mean"] = float(np.mean(valid)) if valid else None
        aggregate[f"{key}_min"] = min(valid) if valid else None
        aggregate[f"{key}_max"] = max(valid) if valid else None
        aggregate[f"{key}_sum"] = float(sum(valid)) if valid else None
    return aggregate


def aggregate_csv_rows(aggregates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fields = [
        "task",
        "model",
        "model_family",
        "variant_group",
        "feature_mode",
        "replay_mode",
        "memory_runner",
        "runs",
        "steps",
        "all_accuracy_mean",
        "tail_accuracy_mean",
        "prediction_target_corr_mean",
        "tail_prediction_target_corr_mean",
        "runtime_seconds_mean",
        "evaluation_count_mean",
        "feature_active_steps_sum",
        "context_memory_updates_sum",
        "replay_cycles_sum",
        "replay_events_sum",
        "replay_consolidations_sum",
        "replay_future_violations_sum",
        "replay_unique_keys_sum",
        "mean_abs_prediction_mean",
        "max_abs_prediction_mean",
    ]
    return [{field: row.get(field) for field in fields} for row in aggregates]


def composite_score(row: dict[str, Any]) -> float:
    acc = float(row.get("all_accuracy_mean") or 0.0)
    tail = float(row.get("tail_accuracy_mean") or 0.0)
    corr = abs(float(row.get("prediction_target_corr_mean") or 0.0))
    return acc + 0.50 * tail + 0.10 * corr


def gap_closure(candidate: float, base: float, upper: float) -> float:
    gap = upper - base
    if gap <= EPS:
        return 1.0 if candidate >= upper - EPS else 0.0
    return max(0.0, min(1.0, (candidate - base) / gap))


def build_comparisons(aggregates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    by_task_model = {(row["task"], row["model"]): row for row in aggregates}
    for task in sorted({row["task"] for row in aggregates}):
        no_replay = by_task_model.get((task, "v1_6_no_replay"), {})
        prioritized = by_task_model.get((task, "prioritized_replay"), {})
        shuffled_order = by_task_model.get((task, "shuffled_order_replay"), {})
        random_replay = by_task_model.get((task, "random_replay"), {})
        wrong_key = by_task_model.get((task, "wrong_key_replay"), {})
        key_label = by_task_model.get((task, "key_label_permuted_replay"), {})
        priority_only = by_task_model.get((task, "priority_only_ablation"), {})
        no_consolidation = by_task_model.get((task, "no_consolidation_replay"), {})
        unbounded = by_task_model.get((task, "unbounded_keyed_control"), {})
        oracle = by_task_model.get((task, "oracle_context_scaffold"), {})
        sign = by_task_model.get((task, "sign_persistence"), {})
        standard = [
            row
            for row in aggregates
            if row["task"] == task and row.get("model_family") != "CRA" and row["model"] not in CONTROL_MODELS
        ]
        best_standard = max(standard, key=lambda row: float(row.get("all_accuracy_mean") or 0.0), default={})
        no_acc = float(no_replay.get("all_accuracy_mean") or 0.0)
        prio_acc = float(prioritized.get("all_accuracy_mean") or 0.0)
        upper_acc = float(unbounded.get("all_accuracy_mean") or 0.0)
        no_tail = float(no_replay.get("tail_accuracy_mean") or 0.0)
        prio_tail = float(prioritized.get("tail_accuracy_mean") or 0.0)
        upper_tail = float(unbounded.get("tail_accuracy_mean") or 0.0)
        rows.append(
            {
                "task": task,
                "no_replay_all_accuracy": no_replay.get("all_accuracy_mean"),
                "prioritized_all_accuracy": prioritized.get("all_accuracy_mean"),
                "shuffled_order_all_accuracy": shuffled_order.get("all_accuracy_mean"),
                "random_all_accuracy": random_replay.get("all_accuracy_mean"),
                "wrong_key_all_accuracy": wrong_key.get("all_accuracy_mean"),
                "key_label_permuted_all_accuracy": key_label.get("all_accuracy_mean"),
                "priority_only_all_accuracy": priority_only.get("all_accuracy_mean"),
                "no_consolidation_all_accuracy": no_consolidation.get("all_accuracy_mean"),
                "unbounded_all_accuracy": unbounded.get("all_accuracy_mean"),
                "oracle_all_accuracy": oracle.get("all_accuracy_mean"),
                "prioritized_all_delta_vs_no_replay": prio_acc - no_acc,
                "prioritized_all_delta_vs_shuffled_order": prio_acc - float(shuffled_order.get("all_accuracy_mean") or 0.0),
                "prioritized_all_delta_vs_random": prio_acc - float(random_replay.get("all_accuracy_mean") or 0.0),
                "prioritized_all_delta_vs_wrong_key": prio_acc - float(wrong_key.get("all_accuracy_mean") or 0.0),
                "prioritized_all_delta_vs_key_label_permuted": prio_acc - float(key_label.get("all_accuracy_mean") or 0.0),
                "prioritized_all_delta_vs_priority_only": prio_acc - float(priority_only.get("all_accuracy_mean") or 0.0),
                "prioritized_all_delta_vs_no_consolidation": prio_acc - float(no_consolidation.get("all_accuracy_mean") or 0.0),
                "prioritized_all_gap_closure_vs_unbounded": gap_closure(prio_acc, no_acc, upper_acc),
                "no_replay_tail_accuracy": no_replay.get("tail_accuracy_mean"),
                "prioritized_tail_accuracy": prioritized.get("tail_accuracy_mean"),
                "shuffled_order_tail_accuracy": shuffled_order.get("tail_accuracy_mean"),
                "random_tail_accuracy": random_replay.get("tail_accuracy_mean"),
                "wrong_key_tail_accuracy": wrong_key.get("tail_accuracy_mean"),
                "key_label_permuted_tail_accuracy": key_label.get("tail_accuracy_mean"),
                "priority_only_tail_accuracy": priority_only.get("tail_accuracy_mean"),
                "no_consolidation_tail_accuracy": no_consolidation.get("tail_accuracy_mean"),
                "unbounded_tail_accuracy": unbounded.get("tail_accuracy_mean"),
                "oracle_tail_accuracy": oracle.get("tail_accuracy_mean"),
                "prioritized_tail_delta_vs_no_replay": prio_tail - no_tail,
                "prioritized_tail_delta_vs_shuffled_order": prio_tail - float(shuffled_order.get("tail_accuracy_mean") or 0.0),
                "prioritized_tail_delta_vs_random": prio_tail - float(random_replay.get("tail_accuracy_mean") or 0.0),
                "prioritized_tail_delta_vs_wrong_key": prio_tail - float(wrong_key.get("tail_accuracy_mean") or 0.0),
                "prioritized_tail_delta_vs_key_label_permuted": prio_tail - float(key_label.get("tail_accuracy_mean") or 0.0),
                "prioritized_tail_delta_vs_priority_only": prio_tail - float(priority_only.get("tail_accuracy_mean") or 0.0),
                "prioritized_tail_delta_vs_no_consolidation": prio_tail - float(no_consolidation.get("tail_accuracy_mean") or 0.0),
                "prioritized_tail_gap_closure_vs_unbounded": gap_closure(prio_tail, no_tail, upper_tail),
                "sign_persistence_all_accuracy": sign.get("all_accuracy_mean"),
                "best_standard_model": best_standard.get("model"),
                "best_standard_all_accuracy": best_standard.get("all_accuracy_mean"),
                "prioritized_replay_events": prioritized.get("replay_events_sum"),
                "prioritized_replay_consolidations": prioritized.get("replay_consolidations_sum"),
                "shuffled_order_replay_events": shuffled_order.get("replay_events_sum"),
                "shuffled_order_replay_consolidations": shuffled_order.get("replay_consolidations_sum"),
                "random_replay_consolidations": random_replay.get("replay_consolidations_sum"),
                "wrong_key_replay_consolidations": wrong_key.get("replay_consolidations_sum"),
                "key_label_permuted_replay_consolidations": key_label.get("replay_consolidations_sum"),
                "priority_only_replay_consolidations": priority_only.get("replay_consolidations_sum"),
                "no_consolidation_replay_events": no_consolidation.get("replay_events_sum"),
                "no_consolidation_replay_consolidations": no_consolidation.get("replay_consolidations_sum"),
            }
        )
    return rows


def evaluate_tier(
    *,
    aggregates: list[dict[str, Any]],
    comparisons: list[dict[str, Any]],
    leakage: dict[str, Any],
    variants: list[ReplayVariant],
    models: list[str],
    args: argparse.Namespace,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    tasks = [item.strip() for item in args.tasks.split(",") if item.strip()]
    if not tasks or tasks == ["all"]:
        tasks = [item.strip() for item in DEFAULT_TASKS.split(",") if item.strip()]
    seeds = seeds_from_args(args)
    expected_runs = len(tasks) * len(seeds) * (len(variants) + len(models) + len(CONTROL_MODELS))
    observed_runs = sum(int(row.get("runs", 0)) for row in aggregates)
    prio_all = [float(row.get("prioritized_all_accuracy") or 0.0) for row in comparisons]
    prio_tail = [float(row.get("prioritized_tail_accuracy") or 0.0) for row in comparisons]
    tail_delta_no = [float(row.get("prioritized_tail_delta_vs_no_replay") or 0.0) for row in comparisons]
    all_closure = [float(row.get("prioritized_all_gap_closure_vs_unbounded") or 0.0) for row in comparisons]
    tail_closure = [float(row.get("prioritized_tail_gap_closure_vs_unbounded") or 0.0) for row in comparisons]
    edge_shuffled_order = [float(row.get("prioritized_tail_delta_vs_shuffled_order") or 0.0) for row in comparisons]
    edge_random = [float(row.get("prioritized_tail_delta_vs_random") or 0.0) for row in comparisons]
    edge_wrong_key = [float(row.get("prioritized_tail_delta_vs_wrong_key") or 0.0) for row in comparisons]
    edge_key_label = [float(row.get("prioritized_tail_delta_vs_key_label_permuted") or 0.0) for row in comparisons]
    edge_priority_only = [float(row.get("prioritized_tail_delta_vs_priority_only") or 0.0) for row in comparisons]
    edge_no_cons = [float(row.get("prioritized_tail_delta_vs_no_consolidation") or 0.0) for row in comparisons]
    replay_events = sum(float(row.get("prioritized_replay_events") or 0.0) for row in comparisons)
    replay_writes = sum(float(row.get("prioritized_replay_consolidations") or 0.0) for row in comparisons)
    no_cons_writes = sum(float(row.get("no_consolidation_replay_consolidations") or 0.0) for row in comparisons)
    matched_write_controls = {
        "shuffled_order": sum(float(row.get("shuffled_order_replay_consolidations") or 0.0) for row in comparisons),
        "random": sum(float(row.get("random_replay_consolidations") or 0.0) for row in comparisons),
        "wrong_key": sum(float(row.get("wrong_key_replay_consolidations") or 0.0) for row in comparisons),
        "key_label_permuted": sum(float(row.get("key_label_permuted_replay_consolidations") or 0.0) for row in comparisons),
        "priority_only": sum(float(row.get("priority_only_replay_consolidations") or 0.0) for row in comparisons),
    }
    criteria = [
        criterion("full replay/control/baseline/task/seed matrix completed", observed_runs, "==", expected_runs, observed_runs == expected_runs),
        criterion("feedback timing has no leakage violations", leakage.get("feedback_due_violations"), "==", 0, int(leakage.get("feedback_due_violations", 0)) == 0),
        criterion("replay uses no future context episodes", leakage.get("replay_future_violations"), "==", 0, int(leakage.get("replay_future_violations", 0)) == 0),
        criterion("candidate replay selected episodes", replay_events, ">", 0, replay_events > 0),
        criterion("candidate replay consolidated episodes", replay_writes, ">", 0, replay_writes > 0),
    ]
    if not args.smoke:
        criteria.extend(
            [
                criterion("candidate replay minimum all accuracy", min(prio_all) if prio_all else None, ">=", args.min_prioritized_all_accuracy, bool(prio_all) and min(prio_all) >= float(args.min_prioritized_all_accuracy)),
                criterion("candidate replay minimum tail accuracy", min(prio_tail) if prio_tail else None, ">=", args.min_prioritized_tail_accuracy, bool(prio_tail) and min(prio_tail) >= float(args.min_prioritized_tail_accuracy)),
                criterion("candidate replay improves tail over no replay", min(tail_delta_no) if tail_delta_no else None, ">=", args.min_tail_improvement_vs_no_replay, bool(tail_delta_no) and min(tail_delta_no) >= float(args.min_tail_improvement_vs_no_replay)),
                criterion("candidate replay closes all-accuracy gap toward unbounded", min(all_closure) if all_closure else None, ">=", args.min_gap_closure, bool(all_closure) and min(all_closure) >= float(args.min_gap_closure)),
                criterion("candidate replay closes tail gap toward unbounded", min(tail_closure) if tail_closure else None, ">=", args.min_tail_gap_closure, bool(tail_closure) and min(tail_closure) >= float(args.min_tail_gap_closure)),
                criterion("wrong-key replay does not match candidate tail", min(edge_wrong_key) if edge_wrong_key else None, ">=", args.min_control_tail_edge, bool(edge_wrong_key) and min(edge_wrong_key) >= float(args.min_control_tail_edge)),
                criterion("key-label-permuted replay does not match candidate tail", min(edge_key_label) if edge_key_label else None, ">=", args.min_control_tail_edge, bool(edge_key_label) and min(edge_key_label) >= float(args.min_control_tail_edge)),
                criterion("priority-only ablation does not match candidate tail", min(edge_priority_only) if edge_priority_only else None, ">=", args.min_control_tail_edge, bool(edge_priority_only) and min(edge_priority_only) >= float(args.min_control_tail_edge)),
                criterion("no-consolidation replay is worse than full replay", min(edge_no_cons) if edge_no_cons else None, ">=", args.min_control_tail_edge, bool(edge_no_cons) and min(edge_no_cons) >= float(args.min_control_tail_edge)),
                criterion("no-consolidation replay performs zero writes", no_cons_writes, "==", 0, no_cons_writes == 0),
                criterion("matched replay control write counts match candidate", min(matched_write_controls.values()) if matched_write_controls else None, "==", replay_writes, bool(matched_write_controls) and all(abs(value - replay_writes) <= EPS for value in matched_write_controls.values())),
            ]
        )
    summary = {
        "expected_runs": expected_runs,
        "observed_runs": observed_runs,
        "tasks": tasks,
        "seeds": seeds,
        "variants": [variant.name for variant in variants],
        "selected_baselines": models,
        "control_models": list(CONTROL_MODELS),
        "backend": args.backend,
        "steps": args.steps,
        "smoke": bool(args.smoke),
        "leakage": leakage,
        "prioritized_replay_events_sum": replay_events,
        "prioritized_replay_consolidations_sum": replay_writes,
        "no_consolidation_writes_sum": no_cons_writes,
        "prioritized_min_all_accuracy": min(prio_all) if prio_all else None,
        "prioritized_min_tail_accuracy": min(prio_tail) if prio_tail else None,
        "prioritized_min_tail_delta_vs_no_replay": min(tail_delta_no) if tail_delta_no else None,
        "prioritized_min_all_gap_closure": min(all_closure) if all_closure else None,
        "prioritized_min_tail_gap_closure": min(tail_closure) if tail_closure else None,
        "prioritized_min_tail_edge_vs_shuffled_order": min(edge_shuffled_order) if edge_shuffled_order else None,
        "prioritized_min_tail_edge_vs_random": min(edge_random) if edge_random else None,
        "prioritized_min_tail_edge_vs_wrong_key": min(edge_wrong_key) if edge_wrong_key else None,
        "prioritized_min_tail_edge_vs_key_label_permuted": min(edge_key_label) if edge_key_label else None,
        "prioritized_min_tail_edge_vs_priority_only": min(edge_priority_only) if edge_priority_only else None,
        "prioritized_min_tail_edge_vs_no_consolidation": min(edge_no_cons) if edge_no_cons else None,
        "matched_sham_write_counts": matched_write_controls,
    }
    return criteria, summary


def plot_replay_edges(comparisons: list[dict[str, Any]], path: Path) -> None:
    if plt is None or not comparisons:
        return
    tasks = [row["task"].replace("_", "\n") for row in comparisons]
    no_tail = [float(row.get("no_replay_tail_accuracy") or 0.0) for row in comparisons]
    prio_tail = [float(row.get("prioritized_tail_accuracy") or 0.0) for row in comparisons]
    shuffled_tail = [float(row.get("shuffled_order_tail_accuracy") or 0.0) for row in comparisons]
    random_tail = [float(row.get("random_tail_accuracy") or 0.0) for row in comparisons]
    x = np.arange(len(tasks))
    width = 0.20
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.bar(x - 1.5 * width, no_tail, width, label="v1.6 no replay", color="#718096")
    ax.bar(x - 0.5 * width, prio_tail, width, label="candidate replay", color="#2f855a")
    ax.bar(x + 0.5 * width, shuffled_tail, width, label="shuffled-order replay", color="#b7791f")
    ax.bar(x + 1.5 * width, random_tail, width, label="random replay", color="#805ad5")
    ax.set_title("Tier 5.11d Generic Replay / Consolidation Confirmation")
    ax.set_xticks(x)
    ax.set_xticklabels(tasks)
    ax.set_ylabel("tail accuracy")
    ax.set_ylim(0.0, 1.05)
    ax.grid(axis="y", alpha=0.25)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fairness_contract(args: argparse.Namespace, variants: list[ReplayVariant], models: list[str]) -> dict[str, Any]:
    return {
        "tier": TIER,
        "baseline": "v1_6_no_replay",
        "candidate": "prioritized_replay",
        "replay_controls": [
            "shuffled_order_replay",
            "random_replay",
            "wrong_key_replay",
            "key_label_permuted_replay",
            "priority_only_ablation",
            "no_consolidation_replay",
        ],
        "upper_bounds": ["unbounded_keyed_control", "oracle_context_scaffold"],
        "selected_external_baselines": models,
        "context_controls": list(CONTROL_MODELS),
        "fairness_rules": [
            "all variants use the same silent-reentry streams per seed",
            "replay buffer contains only visible context events observed at or before replay_step",
            "replay cycles run only after non-evaluation online steps",
            "candidate replay selects rare/old observed contexts without reading future labels or targets",
            "wrong-key/key-label-permuted/priority-only/no-consolidation controls match replay opportunity but remove correct-binding replay semantics",
            "shuffled-order/random replay remain reported comparators; they do not gate promotion of the broader replay/consolidation claim",
            "oracle and unbounded keyed controls remain upper bounds, not promoted replay mechanisms",
        ],
        "tasks": args.tasks,
        "steps": args.steps,
        "seeds": seeds_from_args(args),
        "backend": args.backend,
        "replay_offline_interval": args.replay_offline_interval,
        "replay_selection_count": args.replay_selection_count,
    }


def write_report(path: Path, result: dict[str, Any], aggregates: list[dict[str, Any]], comparisons: list[dict[str, Any]], args: argparse.Namespace, output_dir: Path) -> None:
    overall = "PASS" if result["status"] == "pass" else "FAIL"
    tier_summary = result["summary"]["tier_summary"]
    lines = [
        "# Tier 5.11d Generic Replay / Consolidation Confirmation Findings",
        "",
        f"- Generated: `{utc_now()}`",
        f"- Status: **{overall}**",
        f"- Backend: `{args.backend}`",
        f"- Steps: `{args.steps}`",
        f"- Seeds: `{', '.join(str(seed) for seed in seeds_from_args(args))}`",
        f"- Tasks: `{args.tasks}`",
        f"- Variants: `{args.variants}`",
        f"- Selected standard baselines: `{args.models}`",
        f"- Output directory: `{output_dir}`",
        "",
        "Tier 5.11d tests whether correct-binding replay/consolidation itself adds causal value after the Tier 5.11b/5.11c priority-specific gates failed. It is not hardware replay and not native on-chip replay.",
        "",
        "## Claim Boundary",
        "",
        "- A pass promotes correct-binding replay/consolidation only as a software memory mechanism; it does not prove priority weighting is essential.",
        "- A pass does not prove hardware replay, on-chip replay, general working memory, or compositional reuse.",
        "- Replay events must use only previously observed context episodes and must remain outside online scoring steps.",
        "- Wrong-key, key-label-permuted, priority-only, and no-consolidation controls must not match correct-binding replay. Shuffled-order and random replay are reported as generic replay-opportunity comparators, not priority-specific promotion gates.",
        "",
        "## Summary Metrics",
        "",
        f"- candidate replay events: `{tier_summary.get('prioritized_replay_events_sum')}`",
        f"- candidate replay consolidations: `{tier_summary.get('prioritized_replay_consolidations_sum')}`",
        f"- no-consolidation writes: `{tier_summary.get('no_consolidation_writes_sum')}`",
        f"- candidate min all accuracy: `{tier_summary.get('prioritized_min_all_accuracy')}`",
        f"- candidate min tail accuracy: `{tier_summary.get('prioritized_min_tail_accuracy')}`",
        f"- candidate min tail delta vs no replay: `{tier_summary.get('prioritized_min_tail_delta_vs_no_replay')}`",
        f"- candidate min all gap closure: `{tier_summary.get('prioritized_min_all_gap_closure')}`",
        f"- candidate min tail gap closure: `{tier_summary.get('prioritized_min_tail_gap_closure')}`",
        f"- candidate min tail edge vs shuffled-order comparator: `{tier_summary.get('prioritized_min_tail_edge_vs_shuffled_order')}`",
        f"- candidate min tail edge vs random comparator: `{tier_summary.get('prioritized_min_tail_edge_vs_random')}`",
        f"- candidate min tail edge vs wrong-key: `{tier_summary.get('prioritized_min_tail_edge_vs_wrong_key')}`",
        f"- candidate min tail edge vs key-label-permuted: `{tier_summary.get('prioritized_min_tail_edge_vs_key_label_permuted')}`",
        f"- candidate min tail edge vs priority-only: `{tier_summary.get('prioritized_min_tail_edge_vs_priority_only')}`",
        f"- candidate min tail edge vs no-consolidation: `{tier_summary.get('prioritized_min_tail_edge_vs_no_consolidation')}`",
        "",
        "## Task Comparisons",
        "",
        "| Task | No replay tail | Candidate tail | Shuffled-order tail | Random tail | Wrong-key tail | Key-label tail | Priority-only tail | No-consolidation tail | Unbounded tail | Tail gain vs no replay | Tail edge vs shuffled-order | Tail edge vs wrong-key | Gap closure |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in comparisons:
        lines.append(
            "| "
            f"{row['task']} | "
            f"{markdown_value(row.get('no_replay_tail_accuracy'))} | "
            f"{markdown_value(row.get('prioritized_tail_accuracy'))} | "
            f"{markdown_value(row.get('shuffled_order_tail_accuracy'))} | "
            f"{markdown_value(row.get('random_tail_accuracy'))} | "
            f"{markdown_value(row.get('wrong_key_tail_accuracy'))} | "
            f"{markdown_value(row.get('key_label_permuted_tail_accuracy'))} | "
            f"{markdown_value(row.get('priority_only_tail_accuracy'))} | "
            f"{markdown_value(row.get('no_consolidation_tail_accuracy'))} | "
            f"{markdown_value(row.get('unbounded_tail_accuracy'))} | "
            f"{markdown_value(row.get('prioritized_tail_delta_vs_no_replay'))} | "
            f"{markdown_value(row.get('prioritized_tail_delta_vs_shuffled_order'))} | "
            f"{markdown_value(row.get('prioritized_tail_delta_vs_wrong_key'))} | "
            f"{markdown_value(row.get('prioritized_tail_gap_closure_vs_unbounded'))} |"
        )
    lines.extend(["", "## Aggregate Matrix", "", "| Task | Model | Group | All acc | Tail acc | Replay events | Writes | Replay leakage | Runtime s |", "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |"])
    for row in sorted(aggregates, key=lambda r: (r["task"], r.get("model_family") != "CRA", r["model"])):
        lines.append(
            "| "
            f"{row['task']} | `{row['model']}` | {row.get('variant_group') or ''} | "
            f"{markdown_value(row.get('all_accuracy_mean'))} | "
            f"{markdown_value(row.get('tail_accuracy_mean'))} | "
            f"{markdown_value(row.get('replay_events_sum'))} | "
            f"{markdown_value(row.get('replay_consolidations_sum'))} | "
            f"{markdown_value(row.get('replay_future_violations_sum'))} | "
            f"{markdown_value(row.get('runtime_seconds_mean'))} |"
        )
    lines.extend(["", "## Criteria", "", "| Criterion | Value | Rule | Pass | Note |", "| --- | --- | --- | --- | --- |"])
    for item in result["criteria"]:
        lines.append(
            "| "
            f"{item['name']} | {markdown_value(item['value'])} | {item['operator']} {markdown_value(item['threshold'])} | "
            f"{'yes' if item['passed'] else 'no'} | {item.get('note', '')} |"
        )
    if result["failure_reason"]:
        lines.extend(["", f"Failure: {result['failure_reason']}"])
    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            "- `tier5_11d_results.json`: machine-readable manifest.",
            "- `tier5_11d_report.md`: human findings and claim boundary.",
            "- `tier5_11d_summary.csv`: aggregate task/model metrics.",
            "- `tier5_11d_comparisons.csv`: no-replay/replay/control comparison table.",
            "- `tier5_11d_replay_events.csv`: auditable replay selections and writes.",
            "- `tier5_11d_fairness_contract.json`: predeclared replay/fairness/leakage rules.",
            "- `tier5_11d_replay_edges.png`: replay edge plot.",
            "- `*_timeseries.csv`: per-task/per-model/per-seed traces.",
            "",
            "![replay_edges](tier5_11d_replay_edges.png)",
            "",
        ]
    )
    if MATPLOTLIB_ERROR:
        lines.append(f"Plotting unavailable: `{MATPLOTLIB_ERROR}`")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_latest(output_dir: Path, report_path: Path, manifest_path: Path, summary_csv: Path, status: str) -> None:
    latest_path = ROOT / "controlled_test_output" / "tier5_11d_latest_manifest.json"
    payload = {
        "generated_at_utc": utc_now(),
        "tier": TIER,
        "status": status,
        "output_dir": str(output_dir),
        "manifest": str(manifest_path),
        "report": str(report_path),
        "summary_csv": str(summary_csv),
        "canonical": False,
        "claim": "Latest Tier 5.11d generic replay/consolidation confirmation; not hardware replay or native on-chip memory.",
    }
    write_json(latest_path, payload)


def run_tier(args: argparse.Namespace, output_dir: Path, variants: list[ReplayVariant]) -> dict[str, Any]:
    started = time.perf_counter()
    models = parse_models(args.models)
    all_rows: list[dict[str, Any]] = []
    replay_events: list[dict[str, Any]] = []
    summaries_by_cell: dict[tuple[str, str], list[dict[str, Any]]] = {}
    rows_by_seed: dict[tuple[str, str, int], list[dict[str, Any]]] = {}
    tasks_by_name: dict[str, MemoryTask] = {}
    for seed in seeds_from_args(args):
        for task in build_tasks(args, seed):
            tasks_by_name[task.stream.name] = task
            for variant in variants:
                print(f"[tier5.11d] task={task.stream.name} variant={variant.name} seed={seed}", flush=True)
                rows, summary, events = run_cra_replay_variant(task, seed=seed, variant=variant, args=args)
                all_rows.extend(rows)
                replay_events.extend(events)
                rows_by_seed[(task.stream.name, variant.name, seed)] = rows
                summaries_by_cell.setdefault((task.stream.name, variant.name), []).append(summary)
                write_csv(output_dir / f"{task.stream.name}_{variant.name}_seed{seed}_timeseries.csv", rows)
            for model in models:
                print(f"[tier5.11d] task={task.stream.name} model={model} seed={seed}", flush=True)
                rows, summary = run_external_model(task, model, seed=seed, args=args)
                all_rows.extend(rows)
                rows_by_seed[(task.stream.name, model, seed)] = rows
                summaries_by_cell.setdefault((task.stream.name, model), []).append(summary)
                write_csv(output_dir / f"{task.stream.name}_{model}_seed{seed}_timeseries.csv", rows)
            for control in CONTROL_MODELS:
                print(f"[tier5.11d] task={task.stream.name} control={control} seed={seed}", flush=True)
                rows, summary = run_control_model(task, control, seed=seed, args=args)
                all_rows.extend(rows)
                rows_by_seed[(task.stream.name, control, seed)] = rows
                summaries_by_cell.setdefault((task.stream.name, control), []).append(summary)
                write_csv(output_dir / f"{task.stream.name}_{control}_seed{seed}_timeseries.csv", rows)
    aggregates = [aggregate_runs(tasks_by_name[task_name], model, summaries) for (task_name, model), summaries in summaries_by_cell.items()]
    comparisons = build_comparisons(aggregates)
    leakage = leakage_summary(rows_by_seed, replay_events)
    criteria, tier_summary = evaluate_tier(aggregates=aggregates, comparisons=comparisons, leakage=leakage, variants=variants, models=models, args=args)
    status, failure_reason = pass_fail(criteria)
    summary_csv = output_dir / "tier5_11d_summary.csv"
    comparisons_csv = output_dir / "tier5_11d_comparisons.csv"
    replay_events_csv = output_dir / "tier5_11d_replay_events.csv"
    fairness_json = output_dir / "tier5_11d_fairness_contract.json"
    plot_path = output_dir / "tier5_11d_replay_edges.png"
    write_csv(summary_csv, aggregate_csv_rows(aggregates))
    write_csv(comparisons_csv, comparisons)
    write_csv(replay_events_csv, replay_events)
    write_json(fairness_json, fairness_contract(args, variants, models))
    plot_replay_edges(comparisons, plot_path)
    return {
        "name": "generic_replay_confirmation",
        "status": status,
        "summary": {
            "tier_summary": tier_summary,
            "comparisons": comparisons,
            "aggregates": aggregates,
            "runtime_seconds": time.perf_counter() - started,
        },
        "criteria": criteria,
        "artifacts": {
            "summary_csv": str(summary_csv),
            "comparisons_csv": str(comparisons_csv),
            "replay_events_csv": str(replay_events_csv),
            "fairness_contract_json": str(fairness_json),
            "replay_edges_png": str(plot_path),
        },
        "failure_reason": failure_reason,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = build_tier5_1_parser()
    parser.description = "Run Tier 5.11d generic replay / consolidation confirmation."
    parser.set_defaults(
        backend="nest",
        tasks=DEFAULT_TASKS,
        steps=960,
        seed_count=3,
        models=DEFAULT_MODELS,
        feature_history=5,
        cra_delayed_readout_lr=0.20,
    )
    parser.add_argument("--variants", default=DEFAULT_VARIANTS)
    parser.add_argument("--replay-intruder-contexts", type=int, default=6)
    parser.add_argument("--replay-intruder-period", type=int, default=96)
    parser.add_argument("--replay-long-gap-spacing", type=int, default=112)
    parser.add_argument("--replay-return-start", type=int, default=720)
    parser.add_argument("--replay-return-window", type=int, default=216)
    parser.add_argument("--replay-decision-stride", type=int, default=24)
    parser.add_argument("--replay-distractor-density", type=float, default=0.45)
    parser.add_argument("--replay-distractor-scale", type=float, default=0.35)
    parser.add_argument("--message-passing-steps", type=int, default=2)
    parser.add_argument("--message-context-gain", type=float, default=0.35)
    parser.add_argument("--message-prediction-mix", type=float, default=0.25)
    parser.add_argument("--replay-offline-interval", type=int, default=24)
    parser.add_argument("--replay-min-step", type=int, default=48)
    parser.add_argument("--replay-selection-count", type=int, default=4)
    parser.add_argument("--min-prioritized-all-accuracy", type=float, default=0.85)
    parser.add_argument("--min-prioritized-tail-accuracy", type=float, default=0.75)
    parser.add_argument("--min-tail-improvement-vs-no-replay", type=float, default=0.50)
    parser.add_argument("--min-gap-closure", type=float, default=0.75)
    parser.add_argument("--min-tail-gap-closure", type=float, default=0.75)
    parser.add_argument("--min-control-tail-edge", type=float, default=0.50)
    parser.add_argument("--smoke", action="store_true", help="Run harness integrity gates only; promotion criteria are skipped.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    variants = parse_variants(args.variants)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = args.output_dir or (ROOT / "controlled_test_output" / f"tier5_11d_{timestamp}")
    output_dir.mkdir(parents=True, exist_ok=True)
    result = run_tier(args, output_dir, variants)
    manifest_path = output_dir / "tier5_11d_results.json"
    report_path = output_dir / "tier5_11d_report.md"
    summary_csv = output_dir / "tier5_11d_summary.csv"
    comparisons_csv = output_dir / "tier5_11d_comparisons.csv"
    replay_events_csv = output_dir / "tier5_11d_replay_events.csv"
    fairness_json = output_dir / "tier5_11d_fairness_contract.json"
    manifest = {
        "tier": TIER,
        "generated_at_utc": utc_now(),
        "output_dir": str(output_dir),
        "command": " ".join(sys.argv),
        "status": result["status"],
        "result": result,
        "summary": {
            **result["summary"]["tier_summary"],
            "runtime_seconds": result["summary"]["runtime_seconds"],
            "comparisons": result["summary"]["comparisons"],
        },
        "artifacts": {
            "summary_csv": str(summary_csv),
            "comparisons_csv": str(comparisons_csv),
            "replay_events_csv": str(replay_events_csv),
            "fairness_contract_json": str(fairness_json),
            "report_md": str(report_path),
            "replay_edges_png": str(output_dir / "tier5_11d_replay_edges.png"),
        },
    }
    write_json(manifest_path, json_safe(manifest))
    write_report(report_path, result, result["summary"]["aggregates"], result["summary"]["comparisons"], args, output_dir)
    write_latest(output_dir, report_path, manifest_path, summary_csv, result["status"])
    print(
        json.dumps(
            {
                "status": result["status"],
                "output_dir": str(output_dir),
                "manifest": str(manifest_path),
                "report": str(report_path),
                "summary_csv": str(summary_csv),
                "comparisons_csv": str(comparisons_csv),
                "replay_events_csv": str(replay_events_csv),
                "fairness_contract_json": str(fairness_json),
                "failure_reason": result["failure_reason"],
            },
            indent=2,
        )
    )
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
