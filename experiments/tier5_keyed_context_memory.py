#!/usr/bin/env python3
"""Tier 5.10g multi-slot / keyed context-memory repair.

Tier 5.10f cleanly narrowed the v1.5 memory claim: the single-slot internal
context-memory path survives retention stress but fails when contexts overlap,
interfere, or re-enter after other regimes. Tier 5.10g tests the targeted
repair: bounded keyed/multi-slot context binding inside CRA.

This is a software mechanism-repair diagnostic. A pass would strengthen the
internal memory claim from "retention only" to "bounded interference with keyed
binding." It is not hardware evidence, not native on-chip memory, and not
sleep/replay consolidation.
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


TIER = "Tier 5.10g - Multi-Slot / Keyed Context Memory Repair"
DEFAULT_TASKS = "intervening_contexts,overlapping_contexts,context_reentry_interference"
DEFAULT_VARIANTS = "v1_4_raw,v1_5_single_slot,oracle_keyed_scaffold,keyed_context_memory,slot_reset_ablation,slot_shuffle_ablation,wrong_key_ablation,overcapacity_keyed_memory"
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
        name="v1_5_single_slot",
        group="single_slot_baseline",
        runner="internal",
        feature_mode="normal",
        hypothesis="Frozen v1.5 internal single-slot context memory carried into the capacity/interference stressor.",
        overrides={
            "learning.delayed_readout_learning_rate": 0.20,
            "learning.macro_eligibility_enabled": False,
            "learning.context_memory_enabled": True,
            "learning.context_memory_mode": "normal",
            "learning.context_memory_input_gain": 1.0,
            "learning.context_memory_slot_count": 1,
        },
    ),
    MemoryVariant(
        name="oracle_keyed_scaffold",
        group="external_scaffold",
        runner="external",
        feature_mode="oracle_keyed",
        hypothesis="Oracle-key scaffold uses the task's visible context routing as an upper-bound reference; it is not the promoted mechanism.",
        overrides={
            "learning.delayed_readout_learning_rate": 0.20,
            "learning.macro_eligibility_enabled": False,
            "learning.context_memory_enabled": False,
        },
    ),
    MemoryVariant(
        name="keyed_context_memory",
        group="candidate",
        runner="internal",
        feature_mode="keyed",
        hypothesis="Internal CRA keyed context memory stores visible context signs in bounded slots and retrieves by visible context key at decision time.",
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


def intervening_contexts_task(*, steps: int, amplitude: float, seed: int, args: argparse.Namespace) -> MemoryTask:
    """Old context must survive intervening visible contexts before decision."""
    rng = np.random.default_rng(seed + 51061)
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
    period = int(args.capacity_period)
    gap = int(args.capacity_decision_gap)
    spacing = max(1, int(args.interference_spacing))
    n_intruders = max(0, int(args.interfering_contexts))
    trials: list[TrialRecord] = []
    trial_id = 0
    for context_step in range(0, steps - gap - 1, period):
        decision_step = context_step + gap
        context_sign = 1 if trial_id % 2 == 0 else -1
        cue_sign = 1 if (trial_id // 2) % 2 == 0 else -1
        _set_context_event(
            sensory=sensory,
            context_by_step=context_by_step,
            trial_by_step=trial_by_step,
            event_type=event_type,
            phase_by_step=phase_by_step,
            step=context_step,
            trial_id=trial_id,
            context_sign=context_sign,
            phase="target_context",
            amplitude=amplitude,
        )
        for intruder in range(n_intruders):
            intruder_step = context_step + spacing * (intruder + 1)
            if intruder_step >= decision_step:
                break
            intruder_sign = -context_sign if intruder % 2 == 0 else int(rng.choice([-1, 1]))
            _set_context_event(
                sensory=sensory,
                context_by_step=context_by_step,
                trial_by_step=trial_by_step,
                event_type=event_type,
                phase_by_step=phase_by_step,
                step=intruder_step,
                trial_id=trial_id,
                context_sign=intruder_sign,
                phase="interfering_context",
                amplitude=amplitude,
                scale=float(args.interfering_context_scale),
            )
        for step in range(context_step + 1, decision_step):
            if rng.random() < float(args.distractor_density):
                _set_distractor(
                    sensory=sensory,
                    trial_by_step=trial_by_step,
                    event_type=event_type,
                    phase_by_step=phase_by_step,
                    step=step,
                    trial_id=trial_id,
                    rng=rng,
                    phase="between_context_and_decision",
                    amplitude=amplitude,
                    scale=float(args.distractor_scale),
                )
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
            context_sign=context_sign,
            cue_sign=cue_sign,
            phase="target_decision_after_interference",
            amplitude=amplitude,
        )
        trials.append(record.__class__(**{**record.__dict__, "context_step": context_step}))
        trial_id += 1
    return task_from_arrays(
        name="intervening_contexts",
        display_name="Intervening Contexts",
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
            "capacity_period": period,
            "decision_gap": gap,
            "interfering_contexts": n_intruders,
            "interference_spacing": spacing,
        },
    )


def overlapping_contexts_task(*, steps: int, amplitude: float, seed: int, args: argparse.Namespace) -> MemoryTask:
    """Two pending context-decision pairs overlap; single-slot memory should struggle on the first decision."""
    rng = np.random.default_rng(seed + 51062)
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
    block = int(args.overlap_period)
    context_gap = int(args.overlap_context_gap)
    first_decision_gap = int(args.overlap_first_decision_gap)
    second_decision_gap = int(args.overlap_second_decision_gap)
    trials: list[TrialRecord] = []
    trial_id = 0
    for start in range(0, steps - second_decision_gap - 1, block):
        context_a = 1 if (trial_id // 2) % 2 == 0 else -1
        context_b = -context_a
        cue_a = 1 if trial_id % 2 == 0 else -1
        cue_b = -cue_a
        a_context_step = start
        b_context_step = start + context_gap
        a_decision_step = start + first_decision_gap
        b_decision_step = start + second_decision_gap
        _set_context_event(
            sensory=sensory,
            context_by_step=context_by_step,
            trial_by_step=trial_by_step,
            event_type=event_type,
            phase_by_step=phase_by_step,
            step=a_context_step,
            trial_id=trial_id,
            context_sign=context_a,
            phase="overlap_context_a",
            amplitude=amplitude,
        )
        _set_context_event(
            sensory=sensory,
            context_by_step=context_by_step,
            trial_by_step=trial_by_step,
            event_type=event_type,
            phase_by_step=phase_by_step,
            step=b_context_step,
            trial_id=trial_id + 1,
            context_sign=context_b,
            phase="overlap_context_b",
            amplitude=amplitude,
        )
        for step in range(start + 1, b_decision_step):
            if rng.random() < float(args.distractor_density):
                _set_distractor(
                    sensory=sensory,
                    trial_by_step=trial_by_step,
                    event_type=event_type,
                    phase_by_step=phase_by_step,
                    step=step,
                    trial_id=trial_id,
                    rng=rng,
                    phase="overlap_distractor",
                    amplitude=amplitude,
                    scale=float(args.distractor_scale),
                )
        trials.append(
            _set_decision_event(
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
                step=a_decision_step,
                trial_id=trial_id,
                context_sign=context_a,
                cue_sign=cue_a,
                phase="overlap_decision_a_after_b_context",
                amplitude=amplitude,
            ).__class__(
                trial_id=trial_id,
                context_step=a_context_step,
                decision_step=a_decision_step,
                context_sign=context_a,
                decision_cue_sign=cue_a,
                label_sign=context_a * cue_a,
                phase="overlap_decision_a_after_b_context",
            )
        )
        trials.append(
            _set_decision_event(
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
                step=b_decision_step,
                trial_id=trial_id + 1,
                context_sign=context_b,
                cue_sign=cue_b,
                phase="overlap_decision_b",
                amplitude=amplitude,
            ).__class__(
                trial_id=trial_id + 1,
                context_step=b_context_step,
                decision_step=b_decision_step,
                context_sign=context_b,
                decision_cue_sign=cue_b,
                label_sign=context_b * cue_b,
                phase="overlap_decision_b",
            )
        )
        trial_id += 2
    return task_from_arrays(
        name="overlapping_contexts",
        display_name="Overlapping Contexts",
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
            "overlap_period": block,
            "overlap_context_gap": context_gap,
            "overlap_first_decision_gap": first_decision_gap,
            "overlap_second_decision_gap": second_decision_gap,
        },
    )


def context_reentry_interference_task(*, steps: int, amplitude: float, seed: int, args: argparse.Namespace) -> MemoryTask:
    """Context A returns after intervening B/C-like contexts; correct action depends on reselecting A."""
    rng = np.random.default_rng(seed + 51063)
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
    phase_len = max(int(args.reentry_phase_len), int(args.capacity_decision_gap) + 4)
    phases = [("A0", 1), ("B", -1), ("C_interference", -1), ("A_return", 1)]
    trials: list[TrialRecord] = []
    trial_id = 0
    for phase_idx, (phase_name, context_sign) in enumerate(phases):
        phase_start = phase_idx * phase_len
        if phase_start + int(args.capacity_decision_gap) >= steps:
            break
        _set_context_event(
            sensory=sensory,
            context_by_step=context_by_step,
            trial_by_step=trial_by_step,
            event_type=event_type,
            phase_by_step=phase_by_step,
            step=phase_start,
            trial_id=trial_id,
            context_sign=context_sign,
            phase=f"{phase_name}_context",
            amplitude=amplitude,
        )
        for offset in range(int(args.interference_spacing), phase_len, int(args.interference_spacing)):
            step = phase_start + offset
            if step >= steps:
                break
            intruder_sign = -context_sign if phase_name.startswith("A") else int(rng.choice([-1, 1]))
            if rng.random() < float(args.reentry_interference_probability):
                _set_context_event(
                    sensory=sensory,
                    context_by_step=context_by_step,
                    trial_by_step=trial_by_step,
                    event_type=event_type,
                    phase_by_step=phase_by_step,
                    step=step,
                    trial_id=trial_id,
                    context_sign=intruder_sign,
                    phase=f"{phase_name}_interfering_context",
                    amplitude=amplitude,
                    scale=float(args.interfering_context_scale),
                )
        first_decision = phase_start + int(args.capacity_decision_gap)
        for decision_step in range(first_decision, min(phase_start + phase_len, steps), int(args.reentry_decision_stride)):
            cue_sign = 1 if trial_id % 2 == 0 else -1
            trials.append(
                _set_decision_event(
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
                    context_sign=context_sign,
                    cue_sign=cue_sign,
                    phase=f"{phase_name}_decision",
                    amplitude=amplitude,
                ).__class__(
                    trial_id=trial_id,
                    context_step=phase_start,
                    decision_step=decision_step,
                    context_sign=context_sign,
                    decision_cue_sign=cue_sign,
                    label_sign=context_sign * cue_sign,
                    phase=f"{phase_name}_decision",
                )
            )
            trial_id += 1
    return task_from_arrays(
        name="context_reentry_interference",
        display_name="Context Reentry Interference",
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
            "phase_len": phase_len,
            "phases": [{"name": name, "context_sign": sign} for name, sign in phases],
            "reentry_interference_probability": float(args.reentry_interference_probability),
            "reentry_decision_stride": int(args.reentry_decision_stride),
        },
    )


def build_tasks(args: argparse.Namespace, seed: int) -> list[MemoryTask]:
    factories = {
        "intervening_contexts": intervening_contexts_task,
        "overlapping_contexts": overlapping_contexts_task,
        "context_reentry_interference": context_reentry_interference_task,
    }
    names = [item.strip() for item in args.tasks.split(",") if item.strip()]
    if not names or names == ["all"]:
        names = list(factories)
    missing = [name for name in names if name not in factories]
    if missing:
        raise argparse.ArgumentTypeError(f"unknown Tier 5.10g tasks: {', '.join(missing)}")
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
        raise argparse.ArgumentTypeError(f"unknown Tier 5.10g variants: {', '.join(missing)}")
    selected = [by_name[name] for name in names]
    required = {"v1_5_single_slot", "oracle_keyed_scaffold", "keyed_context_memory"}
    present = {variant.name for variant in selected}
    if not required.issubset(present):
        raise argparse.ArgumentTypeError(
            "Tier 5.10g requires v1_5_single_slot, oracle_keyed_scaffold, and keyed_context_memory"
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
    """Return the visible context-routing key used by Tier 5.10g.

    The key is derived only from event/phase/trial metadata that the harness
    exposes to the organism; labels and future outcomes are not read.
    """
    event = str(task.event_type[step])
    phase = str(task.phase[step])
    trial_id = int(task.trial_id[step])
    if event == "context" and "interfering_context" in phase:
        return f"intruder:{step}"
    if task.stream.name == "context_reentry_interference":
        if phase.startswith("C_interference"):
            return "phase:C_interference"
        if phase.startswith("A_return"):
            return "phase:A_return"
        if phase.startswith("A0"):
            return "phase:A0"
        if phase.startswith("B"):
            return "phase:B"
    return f"trial:{trial_id}"


def oracle_context_for_step(task: MemoryTask, step: int) -> int:
    context = int(task.context_sign[step])
    if context != 0:
        return context
    key = context_memory_key_for_step(task, step)
    for record in task.trials:
        if key == f"trial:{int(record.trial_id)}":
            return int(record.context_sign)
        if task.stream.name == "context_reentry_interference" and key.endswith(str(record.phase).split("_decision")[0]):
            return int(record.context_sign)
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
                    "tier": "5.10g",
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
        single_slot = by_task_model.get((task, "v1_5_single_slot"), {})
        oracle = by_task_model.get((task, "oracle_keyed_scaffold"), {})
        candidate = by_task_model.get((task, "keyed_context_memory"), {})
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
                "single_slot_all_accuracy": single_slot.get("all_accuracy_mean"),
                "candidate_all_accuracy": candidate.get("all_accuracy_mean"),
                "candidate_all_delta_vs_v1_4": float(candidate.get("all_accuracy_mean") or 0.0) - float(v1_4.get("all_accuracy_mean") or 0.0),
                "candidate_all_delta_vs_single_slot": float(candidate.get("all_accuracy_mean") or 0.0) - float(single_slot.get("all_accuracy_mean") or 0.0),
                "oracle_keyed_all_accuracy": oracle.get("all_accuracy_mean"),
                "candidate_all_delta_vs_oracle_keyed": float(candidate.get("all_accuracy_mean") or 0.0) - float(oracle.get("all_accuracy_mean") or 0.0),
                "overcapacity_all_accuracy": overcapacity.get("all_accuracy_mean"),
                "candidate_all_delta_vs_overcapacity": float(candidate.get("all_accuracy_mean") or 0.0) - float(overcapacity.get("all_accuracy_mean") or 0.0),
                "v1_4_tail_accuracy": v1_4.get("tail_accuracy_mean"),
                "single_slot_tail_accuracy": single_slot.get("tail_accuracy_mean"),
                "candidate_tail_accuracy": candidate.get("tail_accuracy_mean"),
                "candidate_tail_delta_vs_v1_4": float(candidate.get("tail_accuracy_mean") or 0.0) - float(v1_4.get("tail_accuracy_mean") or 0.0),
                "candidate_tail_delta_vs_single_slot": float(candidate.get("tail_accuracy_mean") or 0.0) - float(single_slot.get("tail_accuracy_mean") or 0.0),
                "oracle_keyed_tail_accuracy": oracle.get("tail_accuracy_mean"),
                "candidate_tail_delta_vs_oracle_keyed": float(candidate.get("tail_accuracy_mean") or 0.0) - float(oracle.get("tail_accuracy_mean") or 0.0),
                "candidate_abs_corr": abs(float(candidate.get("prediction_target_corr_mean") or 0.0)),
                "v1_4_abs_corr": abs(float(v1_4.get("prediction_target_corr_mean") or 0.0)),
                "single_slot_abs_corr": abs(float(single_slot.get("prediction_target_corr_mean") or 0.0)),
                "candidate_abs_corr_delta_vs_v1_4": abs(float(candidate.get("prediction_target_corr_mean") or 0.0)) - abs(float(v1_4.get("prediction_target_corr_mean") or 0.0)),
                "candidate_abs_corr_delta_vs_single_slot": abs(float(candidate.get("prediction_target_corr_mean") or 0.0)) - abs(float(single_slot.get("prediction_target_corr_mean") or 0.0)),
                "best_ablation_model": best_ablation.get("model"),
                "best_ablation_all_accuracy": best_ablation.get("all_accuracy_mean"),
                "candidate_all_delta_vs_best_ablation": float(candidate.get("all_accuracy_mean") or 0.0) - float(best_ablation.get("all_accuracy_mean") or 0.0),
                "candidate_composite_delta_vs_best_ablation": composite_score(candidate) - composite_score(best_ablation) if best_ablation else None,
                "sign_persistence_all_accuracy": sign.get("all_accuracy_mean"),
                "candidate_all_delta_vs_sign_persistence": float(candidate.get("all_accuracy_mean") or 0.0) - float(sign.get("all_accuracy_mean") or 0.0),
                "stream_context_memory_all_accuracy": context_control.get("all_accuracy_mean"),
                "candidate_all_delta_vs_context_control": float(candidate.get("all_accuracy_mean") or 0.0) - float(context_control.get("all_accuracy_mean") or 0.0),
                "best_standard_model": best_standard.get("model"),
                "best_standard_all_accuracy": best_standard.get("all_accuracy_mean"),
                "candidate_all_delta_vs_best_standard": float(candidate.get("all_accuracy_mean") or 0.0) - float(best_standard.get("all_accuracy_mean") or 0.0),
                "candidate_feature_active_steps": candidate.get("feature_active_steps_sum"),
                "candidate_context_memory_updates": candidate.get("context_memory_updates_sum"),
            }
        )
    return rows


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
    candidate_edges = [float(row.get("candidate_all_delta_vs_v1_4") or 0.0) for row in comparisons]
    single_slot_edges = [float(row.get("candidate_all_delta_vs_single_slot") or 0.0) for row in comparisons]
    oracle_edges = [float(row.get("candidate_all_delta_vs_oracle_keyed") or 0.0) for row in comparisons]
    overcapacity_edges = [float(row.get("candidate_all_delta_vs_overcapacity") or 0.0) for row in comparisons]
    ablation_edges = [float(row.get("candidate_all_delta_vs_best_ablation") or 0.0) for row in comparisons]
    sign_edges = [float(row.get("candidate_all_delta_vs_sign_persistence") or 0.0) for row in comparisons]
    standard_edges = [float(row.get("candidate_all_delta_vs_best_standard") or 0.0) for row in comparisons]
    candidate_accs = [float(row.get("candidate_all_accuracy") or 0.0) for row in comparisons]
    feature_active = sum(float(row.get("candidate_feature_active_steps") or 0.0) for row in comparisons)
    context_updates = sum(float(row.get("candidate_context_memory_updates") or 0.0) for row in comparisons)
    base_criteria = [
        criterion("full variant/baseline/control/task/seed matrix completed", observed_runs, "==", expected_runs, observed_runs == expected_runs),
        criterion("feedback timing has no leakage violations", leakage.get("feedback_due_violations"), "==", 0, int(leakage.get("feedback_due_violations", 0)) == 0),
        criterion("candidate context feature is active", feature_active, ">", 0, feature_active > 0),
        criterion("candidate memory receives context updates", context_updates, ">", 0, context_updates > 0),
    ]
    science_criteria = [
        criterion(
            "candidate reaches minimum accuracy on capacity-interference tasks",
            min(candidate_accs) if candidate_accs else None,
            ">=",
            args.min_candidate_accuracy,
            bool(candidate_accs) and min(candidate_accs) >= args.min_candidate_accuracy,
        ),
        criterion(
            "keyed candidate improves over v1.4 raw CRA",
            min(candidate_edges) if candidate_edges else None,
            ">=",
            args.min_candidate_edge_vs_v1_4,
            bool(candidate_edges) and min(candidate_edges) >= args.min_candidate_edge_vs_v1_4,
        ),
        criterion(
            "keyed candidate improves over v1.5 single-slot memory",
            min(single_slot_edges) if single_slot_edges else None,
            ">=",
            args.min_candidate_edge_vs_single_slot,
            bool(single_slot_edges) and min(single_slot_edges) >= args.min_candidate_edge_vs_single_slot,
        ),
        criterion(
            "keyed candidate approaches oracle-key scaffold",
            min(oracle_edges) if oracle_edges else None,
            ">=",
            -abs(float(args.max_candidate_gap_vs_external_scaffold)),
            bool(oracle_edges) and min(oracle_edges) >= -abs(float(args.max_candidate_gap_vs_external_scaffold)),
            "Internal keyed memory can trail the oracle-key upper bound slightly but cannot collapse relative to it.",
        ),
        criterion(
            "full keyed memory is not worse than overcapacity keyed control",
            min(overcapacity_edges) if overcapacity_edges else None,
            ">=",
            args.min_candidate_edge_vs_overcapacity,
            bool(overcapacity_edges) and min(overcapacity_edges) >= args.min_candidate_edge_vs_overcapacity,
            "Overcapacity control documents graceful degradation when slots are too few.",
        ),
        criterion(
            "memory ablations are worse than candidate",
            min(ablation_edges) if ablation_edges else None,
            ">=",
            args.min_candidate_edge_vs_ablation,
            bool(ablation_edges) and min(ablation_edges) >= args.min_candidate_edge_vs_ablation,
        ),
        criterion(
            "candidate beats sign persistence",
            min(sign_edges) if sign_edges else None,
            ">=",
            args.min_candidate_edge_vs_sign,
            bool(sign_edges) and min(sign_edges) >= args.min_candidate_edge_vs_sign,
        ),
        criterion(
            "candidate is competitive with best standard baseline",
            min(standard_edges) if standard_edges else None,
            ">=",
            -abs(float(args.max_candidate_gap_vs_best_standard)),
            bool(standard_edges) and min(standard_edges) >= -abs(float(args.max_candidate_gap_vs_best_standard)),
            "Strong baselines may still win some tasks, but candidate cannot be far behind before promotion.",
        ),
    ]
    criteria = base_criteria if args.smoke else base_criteria + science_criteria
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
        "candidate_feature_active_steps_sum": feature_active,
        "candidate_context_memory_updates_sum": context_updates,
        "capacity_interference_profile": {
            "capacity_period": int(args.capacity_period),
            "capacity_decision_gap": int(args.capacity_decision_gap),
            "interfering_contexts": int(args.interfering_contexts),
            "interference_spacing": int(args.interference_spacing),
            "interfering_context_scale": float(args.interfering_context_scale),
            "overlap_period": int(args.overlap_period),
            "overlap_context_gap": int(args.overlap_context_gap),
            "overlap_first_decision_gap": int(args.overlap_first_decision_gap),
            "overlap_second_decision_gap": int(args.overlap_second_decision_gap),
            "reentry_phase_len": int(args.reentry_phase_len),
            "reentry_decision_stride": int(args.reentry_decision_stride),
            "reentry_interference_probability": float(args.reentry_interference_probability),
            "distractor_density": float(args.distractor_density),
            "distractor_scale": float(args.distractor_scale),
        },
        "claim_boundary": "Software stress diagnostic only: internal host-side context binding under capacity/interference pressure, not native on-chip memory, sleep/replay, or hardware evidence.",
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
    single_slot = [float(row.get("candidate_all_delta_vs_single_slot") or 0.0) for row in comparisons]
    ablation = [float(row.get("candidate_all_delta_vs_best_ablation") or 0.0) for row in comparisons]
    oracle = [float(row.get("candidate_all_delta_vs_oracle_keyed") or 0.0) for row in comparisons]
    x = np.arange(len(tasks))
    width = 0.25
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.axhline(0.0, color="black", lw=0.8)
    ax.bar(x - width, single_slot, width, label="keyed delta vs v1.5 single-slot", color="#1f6feb")
    ax.bar(x, ablation, width, label="candidate delta vs best memory ablation", color="#2f855a")
    ax.bar(x + width, oracle, width, label="keyed delta vs oracle-key upper bound", color="#b7791f")
    ax.set_title("Tier 5.10g Multi-Slot / Keyed Context Memory Repair")
    ax.set_xticks(x)
    ax.set_xticklabels(tasks)
    ax.set_ylabel("positive favors internal context memory")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fairness_contract(args: argparse.Namespace, variants: list[MemoryVariant], models: list[str]) -> dict[str, Any]:
    return {
        "tier": TIER,
        "raw_comparator": "v1_4_raw",
        "single_slot_comparator": "v1_5_single_slot",
        "oracle_key_upper_bound": "oracle_keyed_scaffold",
        "candidate": "keyed_context_memory",
        "overcapacity_control": "overcapacity_keyed_memory",
        "ablation_controls": [variant.name for variant in variants if variant.group == "memory_ablation"],
        "selected_external_baselines": models,
        "context_controls": list(CONTROL_MODELS),
        "fairness_rules": [
            "all variants use the same stressed Tier 5.10b-derived task streams per seed",
            "internal candidate receives raw observations and may update memory only on visible context events",
            "keyed candidate binds retained context slots to later visible decision cues inside Organism",
            "oracle-key scaffold is included only as an upper-bound capability reference",
            "slot-reset/slot-shuffle/wrong-key controls must lose the benefit before promotion",
            "overcapacity keyed control documents degradation when too few slots are available",
            "models predict before consequence feedback matures",
            "Tier 5.10g is internal host-side keyed context memory under capacity/interference stress, not native on-chip memory or sleep/replay",
        ],
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
    lines = [
        "# Tier 5.10g Multi-Slot / Keyed Context Memory Repair Findings",
        "",
        f"- Generated: `{utc_now()}`",
        f"- Status: **{overall}**",
        f"- Backend: `{args.backend}`",
        f"- Steps: `{args.steps}`",
        f"- Seeds: `{', '.join(str(seed) for seed in seeds_from_args(args))}`",
        f"- Tasks: `{args.tasks}`",
        f"- Variants: `{args.variants}`",
        f"- Selected standard baselines: `{args.models}`",
        f"- Smoke mode: `{args.smoke}`",
        f"- Output directory: `{output_dir}`",
        "",
        "Tier 5.10g tests whether CRA's internal host-side keyed context-memory pathway repairs the Tier 5.10f capacity/interference failure while still receiving raw observations.",
        "",
        "## Claim Boundary",
        "",
        "- This is software diagnostic evidence, not hardware evidence.",
        "- The candidate is internal to `Organism`, but still host-side software, not native on-chip memory.",
        "- The oracle-key scaffold is included as an upper-bound reference, not the promoted mechanism.",
        "- A pass means keyed multi-slot binding repairs the measured Tier 5.10f capacity/interference limit; it does not promote sleep/replay.",
        "- A failure would not falsify memory as a concept; it would identify where routing, slot policy, consolidation, or decay/capacity controls must be tested next.",
        "",
        "## Capacity / Interference Profile",
        "",
        f"- `capacity_period`: `{args.capacity_period}`",
        f"- `capacity_decision_gap`: `{args.capacity_decision_gap}`",
        f"- `interfering_contexts`: `{args.interfering_contexts}`",
        f"- `interference_spacing`: `{args.interference_spacing}`",
        f"- `interfering_context_scale`: `{args.interfering_context_scale}`",
        f"- `overlap_period`: `{args.overlap_period}`",
        f"- `overlap_context_gap`: `{args.overlap_context_gap}`",
        f"- `overlap_first_decision_gap`: `{args.overlap_first_decision_gap}`",
        f"- `overlap_second_decision_gap`: `{args.overlap_second_decision_gap}`",
        f"- `reentry_phase_len`: `{args.reentry_phase_len}`",
        f"- `reentry_decision_stride`: `{args.reentry_decision_stride}`",
        f"- `reentry_interference_probability`: `{args.reentry_interference_probability}`",
        f"- `distractor_density`: `{args.distractor_density}`",
        f"- `distractor_scale`: `{args.distractor_scale}`",
        "",
        "## Task Comparisons",
        "",
        "| Task | v1.4 all | v1.5 single-slot | Oracle-key all | Keyed all | Delta vs single-slot | Delta vs oracle | Best ablation | Delta vs ablation | Overcapacity all | Delta vs overcapacity | Best standard | Delta vs standard |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- | ---: |",
    ]
    for row in comparisons:
        lines.append(
            "| "
            f"{row['task']} | "
            f"{markdown_value(row.get('v1_4_all_accuracy'))} | "
            f"{markdown_value(row.get('single_slot_all_accuracy'))} | "
            f"{markdown_value(row.get('oracle_keyed_all_accuracy'))} | "
            f"{markdown_value(row.get('candidate_all_accuracy'))} | "
            f"{markdown_value(row.get('candidate_all_delta_vs_single_slot'))} | "
            f"{markdown_value(row.get('candidate_all_delta_vs_oracle_keyed'))} | "
            f"`{row.get('best_ablation_model')}` | "
            f"{markdown_value(row.get('candidate_all_delta_vs_best_ablation'))} | "
            f"{markdown_value(row.get('overcapacity_all_accuracy'))} | "
            f"{markdown_value(row.get('candidate_all_delta_vs_overcapacity'))} | "
            f"`{row.get('best_standard_model')}` | "
            f"{markdown_value(row.get('candidate_all_delta_vs_best_standard'))} | "
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
            "- `tier5_10g_results.json`: machine-readable manifest.",
            "- `tier5_10g_report.md`: human findings and claim boundary.",
            "- `tier5_10g_summary.csv`: aggregate task/model metrics.",
            "- `tier5_10g_comparisons.csv`: keyed candidate vs v1.4/single-slot/oracle/ablation/baseline table.",
            "- `tier5_10g_fairness_contract.json`: predeclared comparison/leakage rules.",
            "- `tier5_10g_memory_edges.png`: internal-memory edge plot.",
            "- `*_timeseries.csv`: per-task/per-model/per-seed traces.",
            "",
            "![memory_edges](tier5_10g_memory_edges.png)",
            "",
        ]
    )
    if MATPLOTLIB_ERROR:
        lines.append(f"Plotting unavailable: `{MATPLOTLIB_ERROR}`")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_latest(output_dir: Path, report_path: Path, manifest_path: Path, summary_csv: Path, status: str) -> None:
    latest_path = ROOT / "controlled_test_output" / "tier5_10g_latest_manifest.json"
    payload = {
        "generated_at_utc": utc_now(),
        "tier": TIER,
        "status": status,
        "output_dir": str(output_dir),
        "manifest": str(manifest_path),
        "report": str(report_path),
        "summary_csv": str(summary_csv),
        "canonical": False,
        "claim": "Latest Tier 5.10g keyed context-memory repair diagnostic; passing is not hardware or native on-chip memory evidence.",
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
                print(f"[tier5.10g] task={task.stream.name} variant={variant.name} seed={seed}", flush=True)
                rows, summary = run_cra_memory_variant(task, seed=seed, variant=variant, args=args)
                write_csv(output_dir / f"{task.stream.name}_{variant.name}_seed{seed}_timeseries.csv", rows)
                summaries_by_cell.setdefault((task.stream.name, variant.name), []).append(summary)
                rows_by_cell_seed[(task.stream.name, variant.name, seed)] = rows
            for model in models:
                print(f"[tier5.10g] task={task.stream.name} model={model} seed={seed}", flush=True)
                rows, summary = run_external_model(task, model, seed=seed, args=args)
                write_csv(output_dir / f"{task.stream.name}_{model}_seed{seed}_timeseries.csv", rows)
                summaries_by_cell.setdefault((task.stream.name, model), []).append(summary)
                rows_by_cell_seed[(task.stream.name, model, seed)] = rows
            for control in CONTROL_MODELS:
                print(f"[tier5.10g] task={task.stream.name} control={control} seed={seed}", flush=True)
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
    summary_csv = output_dir / "tier5_10g_summary.csv"
    comparisons_csv = output_dir / "tier5_10g_comparisons.csv"
    fairness_json = output_dir / "tier5_10g_fairness_contract.json"
    plot_path = output_dir / "tier5_10g_memory_edges.png"
    write_csv(summary_csv, aggregate_csv_rows(aggregates))
    write_csv(comparisons_csv, comparisons)
    write_json(fairness_json, fairness_contract(args, variants, models))
    plot_memory_edges(comparisons, plot_path)
    return {
        "name": "keyed_context_memory_repair",
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
    parser.description = "Run Tier 5.10g multi-slot / keyed context-memory repair diagnostic."
    parser.set_defaults(
        backend="nest",
        tasks=DEFAULT_TASKS,
        steps=720,
        seed_count=3,
        models=DEFAULT_MODELS,
        feature_history=5,
        cra_delayed_readout_lr=0.20,
    )
    parser.add_argument("--variants", default=DEFAULT_VARIANTS)
    parser.add_argument("--capacity-period", type=int, default=120)
    parser.add_argument("--capacity-decision-gap", type=int, default=72)
    parser.add_argument("--interfering-contexts", type=int, default=2)
    parser.add_argument("--interference-spacing", type=int, default=24)
    parser.add_argument("--interfering-context-scale", type=float, default=0.50)
    parser.add_argument("--overlap-period", type=int, default=120)
    parser.add_argument("--overlap-context-gap", type=int, default=36)
    parser.add_argument("--overlap-first-decision-gap", type=int, default=72)
    parser.add_argument("--overlap-second-decision-gap", type=int, default=96)
    parser.add_argument("--reentry-phase-len", type=int, default=180)
    parser.add_argument("--reentry-decision-stride", type=int, default=24)
    parser.add_argument("--reentry-interference-probability", type=float, default=0.70)
    parser.add_argument("--distractor-density", type=float, default=0.55)
    parser.add_argument("--distractor-scale", type=float, default=0.35)
    parser.add_argument("--message-passing-steps", type=int, default=2)
    parser.add_argument("--message-context-gain", type=float, default=0.35)
    parser.add_argument("--message-prediction-mix", type=float, default=0.25)
    parser.add_argument("--min-candidate-accuracy", type=float, default=0.70)
    parser.add_argument("--min-candidate-edge-vs-v1-4", type=float, default=0.10)
    parser.add_argument("--min-candidate-edge-vs-single-slot", type=float, default=0.10)
    parser.add_argument("--max-candidate-gap-vs-external-scaffold", type=float, default=0.05)
    parser.add_argument("--min-candidate-edge-vs-overcapacity", type=float, default=0.0)
    parser.add_argument("--min-candidate-edge-vs-ablation", type=float, default=0.10)
    parser.add_argument("--min-candidate-edge-vs-sign", type=float, default=0.20)
    parser.add_argument("--max-candidate-gap-vs-best-standard", type=float, default=0.05)
    parser.add_argument("--smoke", action="store_true", help="Run harness integrity gates only; mechanism promotion gates are skipped.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    variants = parse_variants(args.variants)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = args.output_dir or (ROOT / "controlled_test_output" / f"tier5_10g_{timestamp}")
    output_dir.mkdir(parents=True, exist_ok=True)
    result = run_tier(args, output_dir, variants)
    manifest_path = output_dir / "tier5_10g_results.json"
    report_path = output_dir / "tier5_10g_report.md"
    summary_csv = output_dir / "tier5_10g_summary.csv"
    comparisons_csv = output_dir / "tier5_10g_comparisons.csv"
    fairness_json = output_dir / "tier5_10g_fairness_contract.json"
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
            "memory_edges_png": str(output_dir / "tier5_10g_memory_edges.png"),
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
