#!/usr/bin/env python3
"""Tier 5.11a sleep/replay need diagnostic.

Tier 5.10g froze v1.6 after keyed/multi-slot context memory repaired the measured single-slot interference failure. Tier 5.11a asks whether replay is actually needed next by stressing v1.6 with silent context reentry, overcapacity, and partial/noisy key pressure before implementing any replay mechanism.

This is a software need-test diagnostic. It can conclude that replay is needed, not needed yet, or inconclusive. It is not a replay implementation, not hardware evidence, and not native on-chip memory.
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

from coral_reef_spinnaker import Organism, ReefConfig  # noqa: E402
from tier2_learning import (  # noqa: E402
    DEFAULT_AMPLITUDE,
    DEFAULT_DT_SECONDS,
    criterion,
    end_backend,
    load_backend,
    markdown_value,
    pass_fail,
    safe_corr,
    setup_backend,
    strict_sign,
    write_csv,
    write_json,
)
from tier4_scaling import mean, min_value, seeds_from_args, stdev  # noqa: E402
from tier5_external_baselines import build_parser as build_tier5_1_parser, parse_models, summarize_rows  # noqa: E402
from tier5_macro_eligibility import computed_horizon, set_nested_attr  # noqa: E402
from tier5_memory_pressure_tasks import (  # noqa: E402
    CONTROL_MODELS,
    DEFAULT_MODELS,
    MemoryTask,
    TrialRecord,
    make_empty_task_arrays,
    run_control_model,
    run_external_model,
    task_from_arrays,
    task_ambiguity_summary,
)


TIER = "Tier 5.11a - Sleep/Replay Need Test"
DEFAULT_TASKS = "silent_context_reentry,long_gap_silent_reentry,partial_key_reentry"
DEFAULT_VARIANTS = "v1_4_raw,v1_6_no_replay,unbounded_keyed_control,oracle_context_scaffold,slot_reset_ablation,slot_shuffle_ablation,wrong_key_ablation,overcapacity_keyed_memory"
EPS = 1e-12


@dataclass(frozen=True)
class MemoryVariant:
    name: str
    group: str
    runner: str
    feature_mode: str
    hypothesis: str
    overrides: dict[str, Any]


VARIANTS: tuple[MemoryVariant, ...] = (
    MemoryVariant(
        name="v1_4_raw",
        group="frozen_baseline",
        runner="internal",
        feature_mode="raw",
        hypothesis="Frozen v1.4 CRA receives the repaired task stream without explicit context binding.",
        overrides={
            "learning.delayed_readout_learning_rate": 0.20,
            "learning.macro_eligibility_enabled": False,
            "learning.context_memory_enabled": False,
        },
    ),
    MemoryVariant(
        name="v1_6_no_replay",
        group="candidate_no_replay",
        runner="internal",
        feature_mode="keyed",
        hypothesis="Frozen v1.6 keyed context memory with bounded slots and no replay/consolidation.",
        overrides={
            "learning.delayed_readout_learning_rate": 0.20,
            "learning.macro_eligibility_enabled": False,
            "learning.context_memory_enabled": True,
            "learning.context_memory_mode": "keyed",
            "learning.context_memory_input_gain": 1.0,
            "learning.context_memory_slot_count": 4,
        },
    ),
    MemoryVariant(
        name="unbounded_keyed_control",
        group="capacity_upper_bound",
        runner="internal",
        feature_mode="keyed",
        hypothesis="Capacity upper bound: keyed memory with enough slots to avoid eviction; this is not replay.",
        overrides={
            "learning.delayed_readout_learning_rate": 0.20,
            "learning.macro_eligibility_enabled": False,
            "learning.context_memory_enabled": True,
            "learning.context_memory_mode": "keyed",
            "learning.context_memory_input_gain": 1.0,
            "learning.context_memory_slot_count": 16,
        },
    ),
    MemoryVariant(
        name="oracle_context_scaffold",
        group="external_scaffold",
        runner="external",
        feature_mode="oracle_keyed",
        hypothesis="Oracle scaffold binds the task's true visible/probed context to the decision cue as a solvability upper bound.",
        overrides={
            "learning.delayed_readout_learning_rate": 0.20,
            "learning.macro_eligibility_enabled": False,
            "learning.context_memory_enabled": False,
        },
    ),
    MemoryVariant(
        name="slot_reset_ablation",
        group="memory_ablation",
        runner="internal",
        feature_mode="slot_reset",
        hypothesis="Control: keyed path is active but decision cue is presented without retained slot context.",
        overrides={
            "learning.delayed_readout_learning_rate": 0.20,
            "learning.macro_eligibility_enabled": False,
            "learning.context_memory_enabled": True,
            "learning.context_memory_mode": "slot_reset",
            "learning.context_memory_input_gain": 1.0,
            "learning.context_memory_slot_count": 4,
        },
    ),
    MemoryVariant(
        name="slot_shuffle_ablation",
        group="memory_ablation",
        runner="internal",
        feature_mode="slot_shuffle",
        hypothesis="Control: keyed memory is present but a different slot is deliberately retrieved.",
        overrides={
            "learning.delayed_readout_learning_rate": 0.20,
            "learning.macro_eligibility_enabled": False,
            "learning.context_memory_enabled": True,
            "learning.context_memory_mode": "slot_shuffle",
            "learning.context_memory_input_gain": 1.0,
            "learning.context_memory_slot_count": 4,
        },
    ),
    MemoryVariant(
        name="wrong_key_ablation",
        group="memory_ablation",
        runner="internal",
        feature_mode="wrong_key",
        hypothesis="Control: keyed memory retrieves a nonmatching slot instead of the requested context key.",
        overrides={
            "learning.delayed_readout_learning_rate": 0.20,
            "learning.macro_eligibility_enabled": False,
            "learning.context_memory_enabled": True,
            "learning.context_memory_mode": "wrong_key",
            "learning.context_memory_input_gain": 1.0,
            "learning.context_memory_slot_count": 4,
        },
    ),
    MemoryVariant(
        name="overcapacity_keyed_memory",
        group="overcapacity_control",
        runner="internal",
        feature_mode="keyed_overcapacity",
        hypothesis="Control: keyed memory with too few slots documents graceful degradation when contexts exceed capacity.",
        overrides={
            "learning.delayed_readout_learning_rate": 0.20,
            "learning.macro_eligibility_enabled": False,
            "learning.context_memory_enabled": True,
            "learning.context_memory_mode": "keyed",
            "learning.context_memory_input_gain": 1.0,
            "learning.context_memory_slot_count": 2,
        },
    ),
)


def _set_context_event(
    *,
    sensory: np.ndarray,
    context_by_step: np.ndarray,
    trial_by_step: np.ndarray,
    event_type: list[str],
    phase_by_step: list[str],
    step: int,
    trial_id: int,
    context_sign: int,
    phase: str,
    amplitude: float,
    scale: float = 0.55,
) -> None:
    if step < 0 or step >= len(sensory):
        return
    sensory[step] = float(scale * amplitude * int(context_sign))
    context_by_step[step] = int(context_sign)
    trial_by_step[step] = int(trial_id)
    event_type[step] = "context"
    phase_by_step[step] = phase


def _set_distractor(
    *,
    sensory: np.ndarray,
    trial_by_step: np.ndarray,
    event_type: list[str],
    phase_by_step: list[str],
    step: int,
    trial_id: int,
    rng: np.random.Generator,
    phase: str,
    amplitude: float,
    scale: float,
) -> None:
    if step < 0 or step >= len(sensory) or event_type[step] != "none":
        return
    sensory[step] = float(scale * amplitude * int(rng.choice([-1, 1])))
    trial_by_step[step] = int(trial_id)
    event_type[step] = "distractor"
    phase_by_step[step] = phase


def _set_decision_event(
    *,
    current_target: np.ndarray,
    evaluation_target: np.ndarray,
    evaluation_mask: np.ndarray,
    feedback_due: np.ndarray,
    context_by_step: np.ndarray,
    cue_by_step: np.ndarray,
    trial_by_step: np.ndarray,
    event_type: list[str],
    phase_by_step: list[str],
    sensory: np.ndarray,
    step: int,
    trial_id: int,
    context_sign: int,
    cue_sign: int,
    phase: str,
    amplitude: float,
) -> TrialRecord:
    label_sign = int(context_sign * cue_sign)
    sensory[step] = float(amplitude * cue_sign)
    current_target[step] = float(amplitude * label_sign)
    evaluation_target[step] = float(amplitude * label_sign)
    evaluation_mask[step] = True
    feedback_due[step] = int(step)
    context_by_step[step] = int(context_sign)
    cue_by_step[step] = int(cue_sign)
    trial_by_step[step] = int(trial_id)
    event_type[step] = "decision"
    phase_by_step[step] = phase
    return TrialRecord(
        trial_id=int(trial_id),
        context_step=-1,
        decision_step=int(step),
        context_sign=int(context_sign),
        decision_cue_sign=int(cue_sign),
        label_sign=int(label_sign),
        phase=phase,
    )


def _capacity_arrays(steps: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[str], list[str]]:
    return make_empty_task_arrays(steps)


def _context_key_label(index: int) -> str:
    labels = ("A", "B", "C", "D", "E", "F", "G", "H")
    return labels[index % len(labels)]


def _intruder_context_sign(index: int) -> int:
    # Keep intruders opposite to A so an evicted A slot produces a clear tail error.
    return -1


def _silent_reentry_task(
    *,
    name: str,
    display_name: str,
    steps: int,
    amplitude: float,
    seed: int,
    args: argparse.Namespace,
    long_gap: bool = False,
    alias_keys: bool = False,
) -> MemoryTask:
    """Context A is learned early, many contexts intervene, then A is queried without refresh.

    v1.6 has four keyed slots and no replay/consolidation. With more than four
    intervening keys, A should be evicted. An unbounded keyed control can retain
    A, which distinguishes "task impossible" from "bounded memory/replay need".
    """
    rng = np.random.default_rng(seed + (51110 if not long_gap else 51120) + (17 if alias_keys else 0))
    (
        sensory,
        current_target,
        evaluation_target,
        evaluation_mask,
        feedback_due,
        context_by_step,
        cue_by_step,
        trial_by_step,
        event_type,
        phase_by_step,
    ) = _capacity_arrays(steps)
    trials: list[TrialRecord] = []
    trial_id = 0
    initial_decision_stride = max(12, int(args.replay_decision_stride))
    intruder_period = max(36, int(args.replay_intruder_period))
    return_stride = max(12, int(args.replay_decision_stride))
    return_start = int(args.replay_return_start)
    if return_start <= 0:
        return_start = max(steps - int(args.replay_return_window), steps // 2)
    return_start = min(max(return_start, 120), steps - return_stride - 1)
    return_window = min(int(args.replay_return_window), steps - return_start)
    intruder_count = max(5, int(args.replay_intruder_contexts))
    if long_gap:
        intruder_count = max(intruder_count, 7)
        intruder_period = max(intruder_period, int(args.replay_long_gap_spacing))

    def context_event(step: int, key_label: str, sign: int, phase: str, scale: float = 0.55) -> None:
        _set_context_event(
            sensory=sensory,
            context_by_step=context_by_step,
            trial_by_step=trial_by_step,
            event_type=event_type,
            phase_by_step=phase_by_step,
            step=step,
            trial_id=trial_id,
            context_sign=sign,
            phase=phase,
            amplitude=amplitude,
            scale=scale,
        )

    context_event(0, "A", 1, "context_A_initial")
    if alias_keys:
        # A second visible alias key for A, so partial-key probes have a legitimate
        # stored slot when capacity is sufficient.
        context_event(initial_decision_stride // 2, "A_alias", 1, "context_A_alias_initial", scale=0.45)
    for offset, cue_sign in enumerate((1, -1, 1, -1)):
        step = initial_decision_stride * (offset + 1)
        if step >= return_start:
            break
        phase = "decision_A_alias_initial" if alias_keys and offset % 2 else "decision_A_initial"
        record = _set_decision_event(
            current_target=current_target,
            evaluation_target=evaluation_target,
            evaluation_mask=evaluation_mask,
            feedback_due=feedback_due,
            context_by_step=context_by_step,
            cue_by_step=cue_by_step,
            trial_by_step=trial_by_step,
            event_type=event_type,
            phase_by_step=phase_by_step,
            sensory=sensory,
            step=step,
            trial_id=trial_id,
            context_sign=1,
            cue_sign=cue_sign,
            phase=phase,
            amplitude=amplitude,
        )
        trials.append(record.__class__(**{**record.__dict__, "context_step": 0}))
        trial_id += 1

    first_intruder = max(96, initial_decision_stride * 6)
    for idx in range(intruder_count):
        step = first_intruder + idx * intruder_period
        if step >= return_start - return_stride:
            break
        label = _context_key_label(idx + 1)
        sign = _intruder_context_sign(idx)
        context_event(step, label, sign, f"context_{label}_intruder")
        for cue_offset, cue_sign in enumerate((1, -1)):
            decision_step = step + return_stride * (cue_offset + 1)
            if decision_step >= return_start or decision_step >= steps:
                break
            record = _set_decision_event(
                current_target=current_target,
                evaluation_target=evaluation_target,
                evaluation_mask=evaluation_mask,
                feedback_due=feedback_due,
                context_by_step=context_by_step,
                cue_by_step=cue_by_step,
                trial_by_step=trial_by_step,
                event_type=event_type,
                phase_by_step=phase_by_step,
                sensory=sensory,
                step=decision_step,
                trial_id=trial_id,
                context_sign=sign,
                cue_sign=cue_sign,
                phase=f"decision_{label}_intruder",
                amplitude=amplitude,
            )
            trials.append(record.__class__(**{**record.__dict__, "context_step": step}))
            trial_id += 1
        gap_end = min(step + intruder_period, return_start)
        for distractor_step in range(step + 1, gap_end):
            if rng.random() < float(args.replay_distractor_density):
                _set_distractor(
                    sensory=sensory,
                    trial_by_step=trial_by_step,
                    event_type=event_type,
                    phase_by_step=phase_by_step,
                    step=distractor_step,
                    trial_id=trial_id,
                    rng=rng,
                    phase="replay_need_distractor",
                    amplitude=amplitude,
                    scale=float(args.replay_distractor_scale),
                )

    return_decisions = max(4, return_window // return_stride)
    for idx in range(return_decisions):
        step = return_start + idx * return_stride
        if step >= steps:
            break
        cue_sign = 1 if idx % 2 == 0 else -1
        phase = "decision_A_silent_return"
        if alias_keys and idx % 2 == 1:
            phase = "decision_A_alias_silent_return"
        record = _set_decision_event(
            current_target=current_target,
            evaluation_target=evaluation_target,
            evaluation_mask=evaluation_mask,
            feedback_due=feedback_due,
            context_by_step=context_by_step,
            cue_by_step=cue_by_step,
            trial_by_step=trial_by_step,
            event_type=event_type,
            phase_by_step=phase_by_step,
            sensory=sensory,
            step=step,
            trial_id=trial_id,
            context_sign=1,
            cue_sign=cue_sign,
            phase=phase,
            amplitude=amplitude,
        )
        # No fresh context event in return phase: the query key must retrieve an
        # old slot or expose a consolidation/replay need.
        trials.append(record.__class__(**{**record.__dict__, "context_step": 0}))
        trial_id += 1

    return task_from_arrays(
        name=name,
        display_name=display_name,
        steps=steps,
        sensory=sensory,
        current_target=current_target,
        evaluation_target=evaluation_target,
        evaluation_mask=evaluation_mask,
        feedback_due=feedback_due,
        context_sign=context_by_step,
        decision_cue_sign=cue_by_step,
        trial_id=trial_by_step,
        event_type=event_type,
        phase=phase_by_step,
        trials=trials,
        metadata={
            "replay_need_profile": "silent_reentry",
            "return_start": return_start,
            "return_window": return_window,
            "intruder_contexts_requested": intruder_count,
            "slot_count_under_test": 4,
            "context_refresh_on_return": False,
            "alias_keys": bool(alias_keys),
            "long_gap": bool(long_gap),
        },
    )


def silent_context_reentry_task(*, steps: int, amplitude: float, seed: int, args: argparse.Namespace) -> MemoryTask:
    return _silent_reentry_task(
        name="silent_context_reentry",
        display_name="Silent Context Reentry",
        steps=steps,
        amplitude=amplitude,
        seed=seed,
        args=args,
    )


def long_gap_silent_reentry_task(*, steps: int, amplitude: float, seed: int, args: argparse.Namespace) -> MemoryTask:
    return _silent_reentry_task(
        name="long_gap_silent_reentry",
        display_name="Long-Gap Silent Reentry",
        steps=steps,
        amplitude=amplitude,
        seed=seed,
        args=args,
        long_gap=True,
    )


def partial_key_reentry_task(*, steps: int, amplitude: float, seed: int, args: argparse.Namespace) -> MemoryTask:
    return _silent_reentry_task(
        name="partial_key_reentry",
        display_name="Partial-Key Silent Reentry",
        steps=steps,
        amplitude=amplitude,
        seed=seed,
        args=args,
        alias_keys=True,
    )


def build_tasks(args: argparse.Namespace, seed: int) -> list[MemoryTask]:
    factories = {
        "silent_context_reentry": silent_context_reentry_task,
        "long_gap_silent_reentry": long_gap_silent_reentry_task,
        "partial_key_reentry": partial_key_reentry_task,
    }
    names = [item.strip() for item in args.tasks.split(",") if item.strip()]
    if not names or names == ["all"]:
        names = list(factories)
    missing = [name for name in names if name not in factories]
    if missing:
        raise argparse.ArgumentTypeError(f"unknown Tier 5.11a tasks: {', '.join(missing)}")
    return [factories[name](steps=args.steps, amplitude=args.amplitude, seed=seed, args=args) for name in names]


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


def parse_variants(raw: str) -> list[MemoryVariant]:
    names = [item.strip() for item in raw.split(",") if item.strip()]
    if not names or names == ["all"]:
        return list(VARIANTS)
    by_name = {variant.name: variant for variant in VARIANTS}
    missing = [name for name in names if name not in by_name]
    if missing:
        raise argparse.ArgumentTypeError(f"unknown Tier 5.11a variants: {', '.join(missing)}")
    selected = [by_name[name] for name in names]
    required = {"v1_6_no_replay", "unbounded_keyed_control", "oracle_context_scaffold"}
    present = {variant.name for variant in selected}
    if not required.issubset(present):
        raise argparse.ArgumentTypeError(
            "Tier 5.11a requires v1_6_no_replay, unbounded_keyed_control, and oracle_context_scaffold"
        )
    return selected


def make_config(*, seed: int, task: MemoryTask, variant: MemoryVariant, args: argparse.Namespace) -> ReefConfig:
    cfg = ReefConfig.default()
    cfg.seed = int(seed)
    cfg.lifecycle.initial_population = int(args.cra_population_size)
    cfg.lifecycle.max_population_from_memory = False
    cfg.lifecycle.max_population_hard = int(args.cra_population_size)
    cfg.lifecycle.enable_reproduction = False
    cfg.lifecycle.enable_apoptosis = False
    cfg.lifecycle.enable_structural_plasticity = True
    cfg.measurement.stream_history_maxlen = max(task.stream.steps + 32, 128)
    cfg.spinnaker.sync_interval_steps = 0
    cfg.spinnaker.runtime_ms_per_step = 1000.0
    cfg.learning.evaluation_horizon_bars = computed_horizon(task.stream)
    cfg.learning.readout_learning_rate = float(args.cra_readout_lr)
    cfg.learning.delayed_readout_learning_rate = float(args.cra_delayed_readout_lr)
    if hasattr(cfg.network, "message_passing_steps"):
        cfg.network.message_passing_steps = int(args.message_passing_steps)
        cfg.network.message_context_gain = float(args.message_context_gain)
        cfg.network.message_prediction_mix = float(args.message_prediction_mix)
    for key, value in variant.overrides.items():
        set_nested_attr(cfg, key, value)
    if cfg.lifecycle.max_population_hard < cfg.lifecycle.initial_population:
        cfg.lifecycle.max_population_hard = cfg.lifecycle.initial_population
    return cfg


def shuffled_context_plan(task: MemoryTask, seed: int) -> dict[int, int]:
    rng = np.random.default_rng(seed + 8510)
    contexts = [int(record.context_sign) for record in task.trials]
    shuffled = list(contexts)
    rng.shuffle(shuffled)
    return {int(record.trial_id): int(shuffled[idx]) for idx, record in enumerate(task.trials)}


def context_memory_key_for_step(task: MemoryTask, step: int) -> str:
    """Return the visible context-routing key used by Tier 5.11a.

    The key is derived only from event/phase/trial metadata that the harness
    exposes to the organism; labels and future outcomes are not read.
    """
    phase = str(task.phase[step])
    if "A_alias" in phase:
        return "ctx:A_alias"
    for label in ("A", "B", "C", "D", "E", "F", "G", "H"):
        if f"_{label}_" in phase or phase.endswith(f"_{label}") or phase.startswith(f"context_{label}"):
            return f"ctx:{label}"
    trial_id = int(task.trial_id[step])
    return f"trial:{trial_id}"


def oracle_context_for_step(task: MemoryTask, step: int) -> int:
    context = int(task.context_sign[step])
    if context != 0:
        return context
    return 1


def transform_sensory(
    *,
    task: MemoryTask,
    step: int,
    variant: MemoryVariant,
    memory: dict[str, Any],
    shuffled_context_by_trial: dict[int, int],
    amplitude: float,
) -> tuple[float, dict[str, Any]]:
    raw = float(task.stream.sensory[step])
    event = task.event_type[step]
    sensory_sign = strict_sign(raw)
    if event == "context" and sensory_sign != 0:
        memory["context"] = int(sensory_sign)
        memory["context_updates"] = int(memory.get("context_updates", 0)) + 1

    context = int(memory.get("context", 1))
    cue = sensory_sign if event == "decision" and sensory_sign != 0 else 0
    transformed = raw
    source = "raw"
    if event == "decision" and cue != 0:
        if variant.feature_mode == "oracle_keyed":
            transformed = float(amplitude * oracle_context_for_step(task, step) * cue)
            source = "oracle_keyed_context"
        elif variant.feature_mode == "context_bound":
            transformed = float(amplitude * context * cue)
            source = "context_bound"
        elif variant.feature_mode == "reset":
            transformed = float(amplitude * cue)
            source = "reset_no_context"
        elif variant.feature_mode == "shuffled":
            trial_id = int(task.trial_id[step])
            transformed = float(amplitude * int(shuffled_context_by_trial.get(trial_id, 1)) * cue)
            source = "shuffled_context"
        elif variant.feature_mode == "wrong":
            transformed = float(amplitude * -context * cue)
            source = "wrong_context"
        else:
            transformed = raw
            source = "raw"

    return transformed, {
        "context_memory_value": int(context),
        "visible_cue_sign": int(cue),
        "feature_source": source,
        "context_updates": int(memory.get("context_updates", 0)),
        "feature_active": bool(source != "raw" and event == "decision"),
        "context_memory_key": context_memory_key_for_step(task, step),
    }


def run_cra_memory_variant(
    task: MemoryTask,
    *,
    seed: int,
    variant: MemoryVariant,
    args: argparse.Namespace,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    random.seed(seed)
    np.random.seed(seed)
    sim, backend_name = load_backend(args.backend)
    setup_backend(sim, backend_name)
    cfg = make_config(seed=seed, task=task, variant=variant, args=args)
    organism = Organism(cfg, sim, use_default_trading_bridge=False)
    shuffled = shuffled_context_plan(task, seed)
    memory: dict[str, Any] = {"context": 1, "context_updates": 0}
    rows: list[dict[str, Any]] = []
    started = time.perf_counter()
    try:
        organism.initialize(stream_keys=[task.stream.domain])
        for step in range(task.stream.steps):
            raw_observation = float(task.stream.sensory[step])
            if variant.runner == "external":
                observation, feature = transform_sensory(
                    task=task,
                    step=step,
                    variant=variant,
                    memory=memory,
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
                }
            consequence = float(task.stream.current_target[step])
            metrics = organism.train_task_step(
                observation_value=observation,
                consequence_value=consequence,
                horizon_signal=consequence,
                dt_seconds=float(args.dt_seconds),
                task_name=task.stream.name,
                metadata={
                    "tier": "5.11a",
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
            injected_observation = (
                float(metrics.context_memory_bound_observation)
                if variant.runner == "internal"
                else float(observation)
            )
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
            "memory_runner": variant.runner,
            "hypothesis": variant.hypothesis,
            "backend": backend_name,
            "seed": int(seed),
            "steps": task.stream.steps,
            "runtime_seconds": time.perf_counter() - started,
            "feature_active_steps": int(feature_active_steps),
            "context_memory_updates": int(context_updates),
            "task_metadata": task.stream.metadata,
            "ambiguity": task_ambiguity_summary(task),
            "config_overrides": variant.overrides,
        }
    )
    return rows, summary


def leakage_summary(rows_by_cell_seed: dict[tuple[str, str, int], list[dict[str, Any]]]) -> dict[str, Any]:
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
    return {"checked_feedback_rows": checked, "feedback_due_violations": len(violations), "example_violations": violations[:10]}


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
        "final_n_alive",
        "total_births",
        "total_deaths",
        "max_abs_dopamine",
        "mean_abs_dopamine",
        "feature_active_steps",
        "context_memory_updates",
    ]
    aggregate: dict[str, Any] = {
        "task": task.stream.name,
        "display_name": task.stream.display_name,
        "domain": task.stream.domain,
        "model": model,
        "model_family": summaries[0].get("model_family") if summaries else None,
        "variant_group": summaries[0].get("variant_group") if summaries else None,
        "feature_mode": summaries[0].get("feature_mode") if summaries else None,
        "memory_runner": summaries[0].get("memory_runner") if summaries else None,
        "runs": len(summaries),
        "seeds": [s.get("seed") for s in summaries],
        "steps": task.stream.steps,
        "ambiguity": task_ambiguity_summary(task),
        "task_metadata": task.stream.metadata,
    }
    for key in keys:
        vals = [s.get(key) for s in summaries]
        aggregate[f"{key}_mean"] = mean(vals)
        aggregate[f"{key}_std"] = stdev(vals)
        aggregate[f"{key}_min"] = min_value(vals)
        valid = [float(v) for v in vals if v is not None]
        aggregate[f"{key}_max"] = max(valid) if valid else None
        aggregate[f"{key}_sum"] = float(sum(valid)) if valid else None
    return aggregate


def composite_score(row: dict[str, Any]) -> float:
    acc = float(row.get("all_accuracy_mean") or 0.0)
    tail = float(row.get("tail_accuracy_mean") or 0.0)
    corr = abs(float(row.get("prediction_target_corr_mean") or 0.0))
    return acc + 0.30 * tail + 0.15 * corr


def build_comparisons(aggregates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    by_task_model = {(row["task"], row["model"]): row for row in aggregates}
    for task in sorted({row["task"] for row in aggregates}):
        v1_4 = by_task_model.get((task, "v1_4_raw"), {})
        no_replay = by_task_model.get((task, "v1_6_no_replay"), {})
        unbounded = by_task_model.get((task, "unbounded_keyed_control"), {})
        oracle = by_task_model.get((task, "oracle_context_scaffold"), {})
        overcapacity = by_task_model.get((task, "overcapacity_keyed_memory"), {})
        sign = by_task_model.get((task, "sign_persistence"), {})
        context_control = by_task_model.get((task, "stream_context_memory"), {})
        ablations = [
            row
            for row in aggregates
            if row["task"] == task and row.get("variant_group") == "memory_ablation"
        ]
        standard = [
            row
            for row in aggregates
            if row["task"] == task
            and row.get("model_family") != "CRA"
            and row["model"] not in CONTROL_MODELS
        ]
        best_ablation = max(ablations, key=composite_score, default={})
        best_standard = max(standard, key=lambda row: float(row.get("all_accuracy_mean") or 0.0), default={})
        rows.append(
            {
                "task": task,
                "v1_4_all_accuracy": v1_4.get("all_accuracy_mean"),
                "no_replay_all_accuracy": no_replay.get("all_accuracy_mean"),
                "unbounded_all_accuracy": unbounded.get("all_accuracy_mean"),
                "oracle_all_accuracy": oracle.get("all_accuracy_mean"),
                "overcapacity_all_accuracy": overcapacity.get("all_accuracy_mean"),
                "no_replay_all_delta_vs_v1_4": float(no_replay.get("all_accuracy_mean") or 0.0) - float(v1_4.get("all_accuracy_mean") or 0.0),
                "no_replay_all_delta_vs_unbounded": float(no_replay.get("all_accuracy_mean") or 0.0) - float(unbounded.get("all_accuracy_mean") or 0.0),
                "no_replay_all_delta_vs_oracle": float(no_replay.get("all_accuracy_mean") or 0.0) - float(oracle.get("all_accuracy_mean") or 0.0),
                "unbounded_all_delta_vs_no_replay": float(unbounded.get("all_accuracy_mean") or 0.0) - float(no_replay.get("all_accuracy_mean") or 0.0),
                "oracle_all_delta_vs_no_replay": float(oracle.get("all_accuracy_mean") or 0.0) - float(no_replay.get("all_accuracy_mean") or 0.0),
                "no_replay_tail_accuracy": no_replay.get("tail_accuracy_mean"),
                "unbounded_tail_accuracy": unbounded.get("tail_accuracy_mean"),
                "oracle_tail_accuracy": oracle.get("tail_accuracy_mean"),
                "unbounded_tail_delta_vs_no_replay": float(unbounded.get("tail_accuracy_mean") or 0.0) - float(no_replay.get("tail_accuracy_mean") or 0.0),
                "oracle_tail_delta_vs_no_replay": float(oracle.get("tail_accuracy_mean") or 0.0) - float(no_replay.get("tail_accuracy_mean") or 0.0),
                "best_ablation_model": best_ablation.get("model"),
                "best_ablation_all_accuracy": best_ablation.get("all_accuracy_mean"),
                "no_replay_all_delta_vs_best_ablation": float(no_replay.get("all_accuracy_mean") or 0.0) - float(best_ablation.get("all_accuracy_mean") or 0.0),
                "sign_persistence_all_accuracy": sign.get("all_accuracy_mean"),
                "no_replay_all_delta_vs_sign_persistence": float(no_replay.get("all_accuracy_mean") or 0.0) - float(sign.get("all_accuracy_mean") or 0.0),
                "stream_context_memory_all_accuracy": context_control.get("all_accuracy_mean"),
                "best_standard_model": best_standard.get("model"),
                "best_standard_all_accuracy": best_standard.get("all_accuracy_mean"),
                "no_replay_all_delta_vs_best_standard": float(no_replay.get("all_accuracy_mean") or 0.0) - float(best_standard.get("all_accuracy_mean") or 0.0),
                "no_replay_feature_active_steps": no_replay.get("feature_active_steps_sum"),
                "no_replay_context_memory_updates": no_replay.get("context_memory_updates_sum"),
                "unbounded_feature_active_steps": unbounded.get("feature_active_steps_sum"),
                "unbounded_context_memory_updates": unbounded.get("context_memory_updates_sum"),
            }
        )
    return rows


def replay_need_decision(comparisons: list[dict[str, Any]], args: argparse.Namespace) -> tuple[str, dict[str, Any]]:
    no_replay_accs = [float(row.get("no_replay_all_accuracy") or 0.0) for row in comparisons]
    unbounded_accs = [float(row.get("unbounded_all_accuracy") or 0.0) for row in comparisons]
    oracle_accs = [float(row.get("oracle_all_accuracy") or 0.0) for row in comparisons]
    unbounded_gaps = [float(row.get("unbounded_all_delta_vs_no_replay") or 0.0) for row in comparisons]
    oracle_gaps = [float(row.get("oracle_all_delta_vs_no_replay") or 0.0) for row in comparisons]
    tail_gaps = [float(row.get("unbounded_tail_delta_vs_no_replay") or 0.0) for row in comparisons]
    no_replay_min = min(no_replay_accs) if no_replay_accs else 0.0
    unbounded_min = min(unbounded_accs) if unbounded_accs else 0.0
    oracle_min = min(oracle_accs) if oracle_accs else 0.0
    unbounded_gap_max = max(unbounded_gaps) if unbounded_gaps else 0.0
    oracle_gap_max = max(oracle_gaps) if oracle_gaps else 0.0
    tail_gap_max = max(tail_gaps) if tail_gaps else 0.0
    need = (
        no_replay_min <= float(args.replay_need_no_replay_max_accuracy)
        and unbounded_min >= float(args.replay_need_upper_bound_min_accuracy)
        and unbounded_gap_max >= float(args.replay_need_min_gap)
    )
    not_needed = (
        no_replay_min >= float(args.replay_not_needed_min_accuracy)
        and max(oracle_gaps or [0.0]) <= float(args.replay_not_needed_max_gap)
        and max(unbounded_gaps or [0.0]) <= float(args.replay_not_needed_max_gap)
    )
    if need:
        decision = "replay_or_consolidation_needed"
    elif not_needed:
        decision = "replay_not_needed_yet"
    else:
        decision = "inconclusive"
    return decision, {
        "no_replay_min_accuracy": no_replay_min,
        "unbounded_min_accuracy": unbounded_min,
        "oracle_min_accuracy": oracle_min,
        "unbounded_gap_max": unbounded_gap_max,
        "oracle_gap_max": oracle_gap_max,
        "unbounded_tail_gap_max": tail_gap_max,
        "need_condition": need,
        "not_needed_condition": not_needed,
    }


def evaluate_tier(
    *,
    aggregates: list[dict[str, Any]],
    comparisons: list[dict[str, Any]],
    leakage: dict[str, Any],
    variants: list[MemoryVariant],
    models: list[str],
    args: argparse.Namespace,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    tasks = [item.strip() for item in args.tasks.split(",") if item.strip()]
    if not tasks or tasks == ["all"]:
        tasks = [item.strip() for item in DEFAULT_TASKS.split(",") if item.strip()]
    seeds = seeds_from_args(args)
    expected_runs = len(tasks) * len(seeds) * (len(variants) + len(models) + len(CONTROL_MODELS))
    observed_runs = sum(int(row.get("runs", 0)) for row in aggregates)
    no_replay_accs = [float(row.get("no_replay_all_accuracy") or 0.0) for row in comparisons]
    unbounded_accs = [float(row.get("unbounded_all_accuracy") or 0.0) for row in comparisons]
    oracle_accs = [float(row.get("oracle_all_accuracy") or 0.0) for row in comparisons]
    upper_bound_gaps = [float(row.get("unbounded_all_delta_vs_no_replay") or 0.0) for row in comparisons]
    feature_active = sum(float(row.get("no_replay_feature_active_steps") or 0.0) for row in comparisons)
    context_updates = sum(float(row.get("no_replay_context_memory_updates") or 0.0) for row in comparisons)
    decision, decision_metrics = replay_need_decision(comparisons, args)
    base_criteria = [
        criterion("full variant/baseline/control/task/seed matrix completed", observed_runs, "==", expected_runs, observed_runs == expected_runs),
        criterion("feedback timing has no leakage violations", leakage.get("feedback_due_violations"), "==", 0, int(leakage.get("feedback_due_violations", 0)) == 0),
        criterion("v1.6 no-replay context feature is active", feature_active, ">", 0, feature_active > 0),
        criterion("v1.6 no-replay memory receives context updates", context_updates, ">", 0, context_updates > 0),
    ]
    diagnostic_criteria = [
        criterion(
            "upper-bound condition is solvable",
            min(unbounded_accs) if unbounded_accs else None,
            ">=",
            args.replay_need_upper_bound_min_accuracy,
            bool(unbounded_accs) and min(unbounded_accs) >= float(args.replay_need_upper_bound_min_accuracy),
            "If unbounded keyed memory cannot solve the stressor, replay is not the next justified repair.",
        ),
        criterion(
            "oracle scaffold condition is solvable",
            min(oracle_accs) if oracle_accs else None,
            ">=",
            args.replay_need_upper_bound_min_accuracy,
            bool(oracle_accs) and min(oracle_accs) >= float(args.replay_need_upper_bound_min_accuracy),
        ),
        criterion(
            "diagnostic decision produced",
            decision,
            "in",
            "replay_or_consolidation_needed,replay_not_needed_yet,inconclusive",
            decision in {"replay_or_consolidation_needed", "replay_not_needed_yet", "inconclusive"},
        ),
    ]
    criteria = base_criteria if args.smoke else base_criteria + diagnostic_criteria
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
        "no_replay_feature_active_steps_sum": feature_active,
        "no_replay_context_memory_updates_sum": context_updates,
        "replay_need_decision": decision,
        "replay_need_metrics": decision_metrics,
        "no_replay_min_accuracy": min(no_replay_accs) if no_replay_accs else None,
        "unbounded_min_accuracy": min(unbounded_accs) if unbounded_accs else None,
        "max_unbounded_gap_vs_no_replay": max(upper_bound_gaps) if upper_bound_gaps else None,
        "replay_need_profile": {
            "intruder_contexts": int(args.replay_intruder_contexts),
            "intruder_period": int(args.replay_intruder_period),
            "long_gap_spacing": int(args.replay_long_gap_spacing),
            "return_start": int(args.replay_return_start),
            "return_window": int(args.replay_return_window),
            "decision_stride": int(args.replay_decision_stride),
            "distractor_density": float(args.replay_distractor_density),
            "distractor_scale": float(args.replay_distractor_scale),
            "v1_6_slot_count": 4,
            "unbounded_slot_count": 16,
        },
        "claim_boundary": "Software need-test diagnostic only: tests whether v1.6 no-replay keyed memory degrades under replay/consolidation pressure before implementing replay. Not a replay mechanism, hardware evidence, or native on-chip memory.",
    }
    return criteria, summary

def aggregate_csv_rows(aggregates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fields = [
        "task",
        "model",
        "model_family",
        "variant_group",
        "feature_mode",
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
        "mean_abs_prediction_mean",
        "max_abs_prediction_mean",
        "mean_abs_dopamine_mean",
    ]
    return [{field: row.get(field) for field in fields} for row in aggregates]


def plot_memory_edges(comparisons: list[dict[str, Any]], path: Path) -> None:
    if plt is None or not comparisons:
        return
    tasks = [row["task"].replace("_", "\n") for row in comparisons]
    unbounded_gap = [float(row.get("unbounded_all_delta_vs_no_replay") or 0.0) for row in comparisons]
    oracle_gap = [float(row.get("oracle_all_delta_vs_no_replay") or 0.0) for row in comparisons]
    no_replay = [float(row.get("no_replay_all_accuracy") or 0.0) for row in comparisons]
    x = np.arange(len(tasks))
    width = 0.25
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.axhline(0.0, color="black", lw=0.8)
    ax.bar(x - width, unbounded_gap, width, label="unbounded keyed delta vs v1.6 no-replay", color="#1f6feb")
    ax.bar(x, oracle_gap, width, label="oracle scaffold delta vs v1.6 no-replay", color="#b7791f")
    ax.bar(x + width, no_replay, width, label="v1.6 no-replay all accuracy", color="#2f855a")
    ax.set_title("Tier 5.11a Sleep/Replay Need Test")
    ax.set_xticks(x)
    ax.set_xticklabels(tasks)
    ax.set_ylabel("accuracy / positive gap implies replay-consolidation pressure")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fairness_contract(args: argparse.Namespace, variants: list[MemoryVariant], models: list[str]) -> dict[str, Any]:
    return {
        "tier": TIER,
        "raw_comparator": "v1_4_raw",
        "no_replay_candidate": "v1_6_no_replay",
        "capacity_upper_bound": "unbounded_keyed_control",
        "oracle_upper_bound": "oracle_context_scaffold",
        "overcapacity_control": "overcapacity_keyed_memory",
        "ablation_controls": [variant.name for variant in variants if variant.group == "memory_ablation"],
        "selected_external_baselines": models,
        "context_controls": list(CONTROL_MODELS),
        "fairness_rules": [
            "all variants use the same silent-reentry task streams per seed",
            "v1.6 no-replay receives raw observations and can update keyed slots only on visible context events",
            "return phases query old context keys without refreshing the context slot",
            "unbounded keyed control is a capacity upper bound, not a replay mechanism",
            "oracle scaffold is included only as a solvability upper bound",
            "slot-reset/slot-shuffle/wrong-key controls document whether key binding, not metadata alone, explains behavior",
            "models predict before consequence feedback matures",
            "Tier 5.11a is a need test; it does not implement sleep/replay or promote hardware memory",
        ],
        "decision_rules": {
            "replay_or_consolidation_needed": "v1.6 no-replay degrades while unbounded keyed memory solves and the gap exceeds the predeclared threshold",
            "replay_not_needed_yet": "v1.6 no-replay solves and remains close to oracle/unbounded controls",
            "inconclusive": "upper bounds fail or gaps do not clearly support either decision",
        },
        "tasks": args.tasks,
        "steps": args.steps,
        "seeds": seeds_from_args(args),
        "backend": args.backend,
    }


def write_report(
    path: Path,
    result: dict[str, Any],
    aggregates: list[dict[str, Any]],
    comparisons: list[dict[str, Any]],
    args: argparse.Namespace,
    output_dir: Path,
) -> None:
    overall = "PASS" if result["status"] == "pass" else "FAIL"
    decision = result["summary"]["tier_summary"].get("replay_need_decision")
    decision_metrics = result["summary"]["tier_summary"].get("replay_need_metrics", {})
    lines = [
        "# Tier 5.11a Sleep/Replay Need Test Findings",
        "",
        f"- Generated: `{utc_now()}`",
        f"- Status: **{overall}**",
        f"- Diagnostic decision: **{decision}**",
        f"- Backend: `{args.backend}`",
        f"- Steps: `{args.steps}`",
        f"- Seeds: `{', '.join(str(seed) for seed in seeds_from_args(args))}`",
        f"- Tasks: `{args.tasks}`",
        f"- Variants: `{args.variants}`",
        f"- Selected standard baselines: `{args.models}`",
        f"- Smoke mode: `{args.smoke}`",
        f"- Output directory: `{output_dir}`",
        "",
        "Tier 5.11a does not implement replay. It first asks whether the frozen v1.6 keyed-memory baseline degrades under a stressor replay/consolidation is supposed to solve.",
        "",
        "## Claim Boundary",
        "",
        "- This is software diagnostic evidence, not hardware evidence.",
        "- The candidate is v1.6 no-replay keyed memory inside `Organism`.",
        "- Unbounded keyed memory and oracle scaffold are upper bounds, not replay mechanisms.",
        "- A `replay_or_consolidation_needed` decision authorizes Tier 5.11b replay intervention testing; it does not prove replay works.",
        "- A `replay_not_needed_yet` decision means replay should be deferred in favor of routing/composition or harder stressors.",
        "",
        "## Replay-Need Decision Metrics",
        "",
        f"- v1.6 no-replay min accuracy: `{decision_metrics.get('no_replay_min_accuracy')}`",
        f"- unbounded keyed min accuracy: `{decision_metrics.get('unbounded_min_accuracy')}`",
        f"- oracle scaffold min accuracy: `{decision_metrics.get('oracle_min_accuracy')}`",
        f"- max unbounded gap vs no-replay: `{decision_metrics.get('unbounded_gap_max')}`",
        f"- max oracle gap vs no-replay: `{decision_metrics.get('oracle_gap_max')}`",
        f"- max tail unbounded gap vs no-replay: `{decision_metrics.get('unbounded_tail_gap_max')}`",
        "",
        "## Stress Profile",
        "",
        f"- `replay_intruder_contexts`: `{args.replay_intruder_contexts}`",
        f"- `replay_intruder_period`: `{args.replay_intruder_period}`",
        f"- `replay_long_gap_spacing`: `{args.replay_long_gap_spacing}`",
        f"- `replay_return_start`: `{args.replay_return_start}`",
        f"- `replay_return_window`: `{args.replay_return_window}`",
        f"- `replay_decision_stride`: `{args.replay_decision_stride}`",
        f"- `replay_distractor_density`: `{args.replay_distractor_density}`",
        f"- `replay_distractor_scale`: `{args.replay_distractor_scale}`",
        "",
        "## Task Comparisons",
        "",
        "| Task | v1.4 all | v1.6 no replay | Unbounded keyed | Oracle | Gap unbounded-v1.6 | Gap oracle-v1.6 | Best ablation | Sign persistence | Best standard |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- |",
    ]
    for row in comparisons:
        lines.append(
            "| "
            f"{row['task']} | "
            f"{markdown_value(row.get('v1_4_all_accuracy'))} | "
            f"{markdown_value(row.get('no_replay_all_accuracy'))} | "
            f"{markdown_value(row.get('unbounded_all_accuracy'))} | "
            f"{markdown_value(row.get('oracle_all_accuracy'))} | "
            f"{markdown_value(row.get('unbounded_all_delta_vs_no_replay'))} | "
            f"{markdown_value(row.get('oracle_all_delta_vs_no_replay'))} | "
            f"`{row.get('best_ablation_model')}` {markdown_value(row.get('best_ablation_all_accuracy'))} | "
            f"{markdown_value(row.get('sign_persistence_all_accuracy'))} | "
            f"`{row.get('best_standard_model')}` {markdown_value(row.get('best_standard_all_accuracy'))} |"
        )
    lines.extend(["", "## Aggregate Matrix", "", "| Task | Model | Family | Group | All acc | Tail acc | Corr | Runtime s | Feature active | Context updates |", "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |"])
    for row in sorted(aggregates, key=lambda r: (r["task"], r.get("model_family") != "CRA", r["model"])):
        lines.append(
            "| "
            f"{row['task']} | `{row['model']}` | {row.get('model_family')} | {row.get('variant_group') or ''} | "
            f"{markdown_value(row.get('all_accuracy_mean'))} | "
            f"{markdown_value(row.get('tail_accuracy_mean'))} | "
            f"{markdown_value(row.get('prediction_target_corr_mean'))} | "
            f"{markdown_value(row.get('runtime_seconds_mean'))} | "
            f"{markdown_value(row.get('feature_active_steps_sum'))} | "
            f"{markdown_value(row.get('context_memory_updates_sum'))} |"
        )
    lines.extend(["", "## Criteria", "", "| Criterion | Value | Rule | Pass | Note |", "| --- | --- | --- | --- | --- |"])
    for item in result["criteria"]:
        lines.append(
            "| "
            f"{item['name']} | "
            f"{markdown_value(item['value'])} | "
            f"{item['operator']} {markdown_value(item['threshold'])} | "
            f"{'yes' if item['passed'] else 'no'} | "
            f"{item.get('note', '')} |"
        )
    if result["failure_reason"]:
        lines.extend(["", f"Failure: {result['failure_reason']}"])
    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            "- `tier5_11a_results.json`: machine-readable manifest.",
            "- `tier5_11a_report.md`: human findings and claim boundary.",
            "- `tier5_11a_summary.csv`: aggregate task/model metrics.",
            "- `tier5_11a_comparisons.csv`: no-replay versus upper-bound/control/baseline table.",
            "- `tier5_11a_fairness_contract.json`: predeclared comparison/leakage rules.",
            "- `tier5_11a_memory_edges.png`: replay-need edge plot.",
            "- `*_timeseries.csv`: per-task/per-model/per-seed traces.",
            "",
            "![memory_edges](tier5_11a_memory_edges.png)",
            "",
        ]
    )
    if MATPLOTLIB_ERROR:
        lines.append(f"Plotting unavailable: `{MATPLOTLIB_ERROR}`")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_latest(output_dir: Path, report_path: Path, manifest_path: Path, summary_csv: Path, status: str) -> None:
    latest_path = ROOT / "controlled_test_output" / "tier5_11a_latest_manifest.json"
    payload = {
        "generated_at_utc": utc_now(),
        "tier": TIER,
        "status": status,
        "output_dir": str(output_dir),
        "manifest": str(manifest_path),
        "report": str(report_path),
        "summary_csv": str(summary_csv),
        "canonical": False,
        "claim": "Latest Tier 5.11a sleep/replay need diagnostic; not replay implementation, hardware evidence, or native on-chip memory.",
    }
    write_json(latest_path, payload)


def run_tier(args: argparse.Namespace, output_dir: Path, variants: list[MemoryVariant]) -> dict[str, Any]:
    models = parse_models(args.models)
    summaries_by_cell: dict[tuple[str, str], list[dict[str, Any]]] = {}
    rows_by_cell_seed: dict[tuple[str, str, int], list[dict[str, Any]]] = {}
    task_by_name: dict[str, MemoryTask] = {}
    started = time.perf_counter()

    for seed in seeds_from_args(args):
        tasks = build_tasks(args, seed=args.task_seed + seed)
        for task in tasks:
            task_by_name[task.stream.name] = task
            for variant in variants:
                print(f"[tier5.11a] task={task.stream.name} variant={variant.name} seed={seed}", flush=True)
                rows, summary = run_cra_memory_variant(task, seed=seed, variant=variant, args=args)
                write_csv(output_dir / f"{task.stream.name}_{variant.name}_seed{seed}_timeseries.csv", rows)
                summaries_by_cell.setdefault((task.stream.name, variant.name), []).append(summary)
                rows_by_cell_seed[(task.stream.name, variant.name, seed)] = rows
            for model in models:
                print(f"[tier5.11a] task={task.stream.name} model={model} seed={seed}", flush=True)
                rows, summary = run_external_model(task, model, seed=seed, args=args)
                write_csv(output_dir / f"{task.stream.name}_{model}_seed{seed}_timeseries.csv", rows)
                summaries_by_cell.setdefault((task.stream.name, model), []).append(summary)
                rows_by_cell_seed[(task.stream.name, model, seed)] = rows
            for control in CONTROL_MODELS:
                print(f"[tier5.11a] task={task.stream.name} control={control} seed={seed}", flush=True)
                rows, summary = run_control_model(task, control, seed=seed, args=args)
                write_csv(output_dir / f"{task.stream.name}_{control}_seed{seed}_timeseries.csv", rows)
                summaries_by_cell.setdefault((task.stream.name, control), []).append(summary)
                rows_by_cell_seed[(task.stream.name, control, seed)] = rows

    aggregates = [
        aggregate_runs(task_by_name[task], model, summaries)
        for (task, model), summaries in sorted(summaries_by_cell.items())
    ]
    comparisons = build_comparisons(aggregates)
    leakage = leakage_summary(rows_by_cell_seed)
    criteria, tier_summary = evaluate_tier(
        aggregates=aggregates,
        comparisons=comparisons,
        leakage=leakage,
        variants=variants,
        models=models,
        args=args,
    )
    status, failure_reason = pass_fail(criteria)
    summary_csv = output_dir / "tier5_11a_summary.csv"
    comparisons_csv = output_dir / "tier5_11a_comparisons.csv"
    fairness_json = output_dir / "tier5_11a_fairness_contract.json"
    plot_path = output_dir / "tier5_11a_memory_edges.png"
    write_csv(summary_csv, aggregate_csv_rows(aggregates))
    write_csv(comparisons_csv, comparisons)
    write_json(fairness_json, fairness_contract(args, variants, models))
    plot_memory_edges(comparisons, plot_path)
    return {
        "name": "sleep_replay_need_test",
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
            "fairness_contract_json": str(fairness_json),
            "memory_edges_png": str(plot_path),
        },
        "failure_reason": failure_reason,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = build_tier5_1_parser()
    parser.description = "Run Tier 5.11a sleep/replay need diagnostic."
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
    parser.add_argument("--replay-need-no-replay-max-accuracy", type=float, default=0.70)
    parser.add_argument("--replay-need-upper-bound-min-accuracy", type=float, default=0.85)
    parser.add_argument("--replay-need-min-gap", type=float, default=0.20)
    parser.add_argument("--replay-not-needed-min-accuracy", type=float, default=0.90)
    parser.add_argument("--replay-not-needed-max-gap", type=float, default=0.05)
    parser.add_argument("--smoke", action="store_true", help="Run harness integrity gates only; need classification gates are skipped.")
    return parser

def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    variants = parse_variants(args.variants)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = args.output_dir or (ROOT / "controlled_test_output" / f"tier5_11a_{timestamp}")
    output_dir.mkdir(parents=True, exist_ok=True)
    result = run_tier(args, output_dir, variants)
    manifest_path = output_dir / "tier5_11a_results.json"
    report_path = output_dir / "tier5_11a_report.md"
    summary_csv = output_dir / "tier5_11a_summary.csv"
    comparisons_csv = output_dir / "tier5_11a_comparisons.csv"
    fairness_json = output_dir / "tier5_11a_fairness_contract.json"
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
            "fairness_contract_json": str(fairness_json),
            "report_md": str(report_path),
            "memory_edges_png": str(output_dir / "tier5_11a_memory_edges.png"),
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
                "fairness_contract_json": str(fairness_json),
                "failure_reason": result["failure_reason"],
            },
            indent=2,
        )
    )
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
