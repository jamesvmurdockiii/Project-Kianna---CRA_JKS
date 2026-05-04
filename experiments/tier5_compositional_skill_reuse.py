#!/usr/bin/env python3
"""Tier 5.13 compositional skill-reuse diagnostic.

Tier 5.13 is the first compositionality gate. It does not claim native CRA
composition yet. It validates held-out skill-composition tasks and asks whether
an explicit reusable-module scaffold can solve combinations that v1.8/raw CRA,
combo memorization, shuffled modules, order shams, and standard online baselines
cannot solve reliably.

A pass here authorizes an internal CRA composition/routing implementation. It is
software diagnostic evidence only: not hardware evidence, not module routing,
not language reasoning, and not general planning.
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
from tier5_external_baselines import (  # noqa: E402
    FeatureBuilder,
    LEARNER_FACTORIES,
    TaskStream,
    build_parser as build_tier5_1_parser,
    parse_models,
    summarize_rows,
)
from tier5_macro_eligibility import computed_horizon, set_nested_attr  # noqa: E402


TIER = "Tier 5.13 - Compositional Skill Reuse Diagnostic"
DEFAULT_TASKS = "heldout_skill_pair,order_sensitive_chain,distractor_skill_chain"
DEFAULT_MODELS = "sign_persistence,online_perceptron,online_logistic_regression,echo_state_network,small_gru,stdp_only_snn"
DEFAULT_VARIANTS = "v1_8_raw_cra,cra_composition_input_scaffold,module_composition_scaffold,module_reset_ablation,module_shuffle_ablation,module_order_shuffle_ablation,combo_memorization_control,oracle_composition"
EPS = 1e-12

SKILL_CODES = {
    "identity": 0.20,
    "invert": -0.20,
    "set_plus": 0.55,
    "set_minus": -0.55,
}
SKILL_ORDER = tuple(SKILL_CODES)


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


@dataclass(frozen=True)
class CompositionTrial:
    trial_id: int
    phase: str
    skill_a: str
    skill_b: str
    input_sign: int
    label_sign: int
    cue_steps: tuple[int, ...]
    decision_step: int
    pair_key: str
    heldout: bool


@dataclass(frozen=True)
class CompositionTask:
    stream: TaskStream
    event_type: list[str]
    phase: list[str]
    skill_a: list[str]
    skill_b: list[str]
    input_sign: np.ndarray
    trial_id: np.ndarray
    heldout_mask: np.ndarray
    pair_key: list[str]
    trials: list[CompositionTrial]


@dataclass(frozen=True)
class CompositionVariant:
    name: str
    group: str
    runner: str
    mode: str
    hypothesis: str
    overrides: dict[str, Any]


VARIANTS: tuple[CompositionVariant, ...] = (
    CompositionVariant(
        name="v1_8_raw_cra",
        group="frozen_baseline",
        runner="cra",
        mode="raw",
        hypothesis="Frozen v1.8-style CRA sees only the raw scalar event stream without a reusable composition feature.",
        overrides={
            "learning.delayed_readout_learning_rate": 0.20,
            "learning.macro_eligibility_enabled": False,
            "learning.context_memory_enabled": True,
            "learning.context_memory_mode": "keyed",
            "learning.context_memory_slot_count": 4,
            "learning.predictive_context_enabled": True,
            "learning.predictive_context_mode": "keyed",
            "learning.predictive_context_slot_count": 8,
        },
    ),
    CompositionVariant(
        name="cra_composition_input_scaffold",
        group="candidate_bridge",
        runner="cra",
        mode="module_scaffold_input",
        hypothesis="CRA receives a host-composed scalar feature produced by a reusable primitive skill table learned from primitive examples.",
        overrides={
            "learning.delayed_readout_learning_rate": 0.20,
            "learning.macro_eligibility_enabled": False,
            "learning.context_memory_enabled": True,
            "learning.context_memory_mode": "keyed",
            "learning.context_memory_slot_count": 4,
            "learning.predictive_context_enabled": True,
            "learning.predictive_context_mode": "keyed",
            "learning.predictive_context_slot_count": 8,
        },
    ),
    CompositionVariant(
        name="module_composition_scaffold",
        group="candidate_scaffold",
        runner="rule",
        mode="module_scaffold",
        hypothesis="Reusable primitive skill tables are learned on primitive trials and composed on held-out pairs.",
        overrides={},
    ),
    CompositionVariant(
        name="module_reset_ablation",
        group="composition_ablation",
        runner="rule",
        mode="reset",
        hypothesis="Control: primitive module memory is cleared at composition time.",
        overrides={},
    ),
    CompositionVariant(
        name="module_shuffle_ablation",
        group="composition_ablation",
        runner="rule",
        mode="shuffle",
        hypothesis="Control: primitive skill labels are shuffled before composition.",
        overrides={},
    ),
    CompositionVariant(
        name="module_order_shuffle_ablation",
        group="composition_ablation",
        runner="rule",
        mode="order_shuffle",
        hypothesis="Control: skill modules are present but composed in the wrong order.",
        overrides={},
    ),
    CompositionVariant(
        name="combo_memorization_control",
        group="shortcut_control",
        runner="rule",
        mode="combo_memorization",
        hypothesis="Control: memorizes seen skill-pair/input combinations but cannot recombine unseen pairs zero-shot.",
        overrides={},
    ),
    CompositionVariant(
        name="oracle_composition",
        group="oracle_upper_bound",
        runner="rule",
        mode="oracle",
        hypothesis="Oracle upper bound with the true skill functions; reported but not used as a candidate mechanism.",
        overrides={},
    ),
)


def parse_variants(raw: str) -> list[CompositionVariant]:
    names = [item.strip() for item in raw.split(",") if item.strip()]
    if not names or names == ["all"]:
        return list(VARIANTS)
    by_name = {variant.name: variant for variant in VARIANTS}
    missing = [name for name in names if name not in by_name]
    if missing:
        raise argparse.ArgumentTypeError(f"unknown Tier 5.13 variants: {', '.join(missing)}")
    selected = [by_name[name] for name in names]
    required = {"v1_8_raw_cra", "module_composition_scaffold"}
    present = {variant.name for variant in selected}
    if not required.issubset(present):
        raise argparse.ArgumentTypeError("Tier 5.13 requires v1_8_raw_cra and module_composition_scaffold")
    return selected


def apply_skill(skill: str, x: int) -> int:
    x = 1 if int(x) >= 0 else -1
    if skill == "identity":
        return x
    if skill == "invert":
        return -x
    if skill == "set_plus":
        return 1
    if skill == "set_minus":
        return -1
    raise ValueError(f"unknown skill {skill}")


def compose_label(skill_a: str, skill_b: str, x: int) -> int:
    return apply_skill(skill_b, apply_skill(skill_a, x))


def empty_arrays(steps: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[str], list[str], list[str], list[str], list[str]]:
    sensory = np.zeros(steps, dtype=float)
    current_target = np.zeros(steps, dtype=float)
    evaluation_target = np.zeros(steps, dtype=float)
    evaluation_mask = np.zeros(steps, dtype=bool)
    feedback_due = np.full(steps, -1, dtype=int)
    input_sign = np.zeros(steps, dtype=int)
    trial_id = np.full(steps, -1, dtype=int)
    event_type = ["none" for _ in range(steps)]
    phase = ["none" for _ in range(steps)]
    skill_a = ["" for _ in range(steps)]
    skill_b = ["" for _ in range(steps)]
    pair_key = ["" for _ in range(steps)]
    return sensory, current_target, evaluation_target, evaluation_mask, feedback_due, input_sign, trial_id, event_type, phase, skill_a, skill_b, pair_key


def add_trial(
    *,
    sensory: np.ndarray,
    current_target: np.ndarray,
    evaluation_target: np.ndarray,
    evaluation_mask: np.ndarray,
    feedback_due: np.ndarray,
    input_by_step: np.ndarray,
    trial_by_step: np.ndarray,
    event_type: list[str],
    phase_by_step: list[str],
    skill_a_by_step: list[str],
    skill_b_by_step: list[str],
    pair_key_by_step: list[str],
    trial_id: int,
    start: int,
    phase: str,
    skill_a: str,
    skill_b: str,
    input_sign: int,
    amplitude: float,
    heldout: bool,
    distractor_gap: int = 0,
    rng: np.random.Generator | None = None,
) -> CompositionTrial:
    rng = rng or np.random.default_rng(0)
    if skill_b:
        steps = [start, start + 1]
        for idx in range(distractor_gap):
            steps.append(start + 2 + idx)
        steps.extend([start + 2 + distractor_gap, start + 3 + distractor_gap])
        skill_a_step = steps[0]
        skill_b_step = steps[1]
        input_step = steps[-2]
        decision_step = steps[-1]
        sensory[skill_a_step] = amplitude * SKILL_CODES[skill_a]
        sensory[skill_b_step] = amplitude * SKILL_CODES[skill_b]
        event_type[skill_a_step] = "skill_a"
        event_type[skill_b_step] = "skill_b"
        cue_steps = (skill_a_step, skill_b_step, input_step)
        for step in steps[2:-2]:
            sensory[step] = amplitude * 0.10 * int(rng.choice([-1, 1]))
            event_type[step] = "distractor"
    else:
        skill_a_step = start
        input_step = start + 1
        decision_step = start + 2
        sensory[skill_a_step] = amplitude * SKILL_CODES[skill_a]
        event_type[skill_a_step] = "skill_a"
        cue_steps = (skill_a_step, input_step)

    label = apply_skill(skill_a, input_sign) if not skill_b else compose_label(skill_a, skill_b, input_sign)
    sensory[input_step] = amplitude * float(input_sign)
    sensory[decision_step] = amplitude * float(input_sign)
    current_target[decision_step] = amplitude * float(label)
    evaluation_target[decision_step] = amplitude * float(label)
    evaluation_mask[decision_step] = True
    feedback_due[decision_step] = decision_step
    event_type[input_step] = "input"
    event_type[decision_step] = "decision"
    key = f"{skill_a}->{skill_b or 'single'}"
    for step in range(start, decision_step + 1):
        phase_by_step[step] = phase
        skill_a_by_step[step] = skill_a
        skill_b_by_step[step] = skill_b
        pair_key_by_step[step] = key
        trial_by_step[step] = trial_id
        input_by_step[step] = int(input_sign)
    return CompositionTrial(
        trial_id=int(trial_id),
        phase=phase,
        skill_a=skill_a,
        skill_b=skill_b,
        input_sign=int(input_sign),
        label_sign=int(label),
        cue_steps=tuple(int(s) for s in cue_steps),
        decision_step=int(decision_step),
        pair_key=key,
        heldout=bool(heldout),
    )


def task_from_trials(
    *,
    name: str,
    display_name: str,
    steps: int,
    sensory: np.ndarray,
    current_target: np.ndarray,
    evaluation_target: np.ndarray,
    evaluation_mask: np.ndarray,
    feedback_due: np.ndarray,
    input_sign: np.ndarray,
    trial_id: np.ndarray,
    event_type: list[str],
    phase: list[str],
    skill_a: list[str],
    skill_b: list[str],
    pair_key: list[str],
    trials: list[CompositionTrial],
    metadata: dict[str, Any],
) -> CompositionTask:
    heldout_mask = np.zeros(steps, dtype=bool)
    for trial in trials:
        if trial.heldout:
            heldout_mask[trial.decision_step] = True
    stream = TaskStream(
        name=name,
        display_name=display_name,
        domain=name,
        steps=steps,
        sensory=sensory,
        current_target=current_target,
        evaluation_target=evaluation_target,
        evaluation_mask=evaluation_mask,
        feedback_due_step=feedback_due,
        switch_steps=sorted({trial.decision_step for trial in trials if trial.phase.startswith("heldout")}),
        metadata={
            **metadata,
            "task_kind": name,
            "trials": len(trials),
            "decision_events": int(np.sum(evaluation_mask)),
            "heldout_decision_events": int(np.sum(heldout_mask)),
            "trial_records": [trial.__dict__ for trial in trials],
        },
    )
    return CompositionTask(
        stream=stream,
        event_type=event_type,
        phase=phase,
        skill_a=skill_a,
        skill_b=skill_b,
        input_sign=input_sign,
        trial_id=trial_id,
        heldout_mask=heldout_mask,
        pair_key=pair_key,
        trials=trials,
    )


def build_composition_task(
    *,
    name: str,
    display_name: str,
    steps: int,
    amplitude: float,
    seed: int,
    args: argparse.Namespace,
    train_pairs: list[tuple[str, str]],
    heldout_pairs: list[tuple[str, str]],
    distractor_gap: int = 0,
) -> CompositionTask:
    rng = np.random.default_rng(seed)
    arrays = empty_arrays(steps)
    sensory, current_target, evaluation_target, evaluation_mask, feedback_due, input_by_step, trial_by_step, event_type, phase_by_step, skill_a_by_step, skill_b_by_step, pair_key_by_step = arrays
    trials: list[CompositionTrial] = []
    cursor = 0
    trial_id = 0

    primitive_repeats = max(1, int(args.primitive_repeats))
    composition_repeats = max(1, int(args.composition_repeats))
    heldout_repeats = max(1, int(args.heldout_repeats))
    inputs = [1, -1]

    for _ in range(primitive_repeats):
        for skill in SKILL_ORDER:
            for x in inputs:
                if cursor + 3 >= steps:
                    break
                trials.append(
                    add_trial(
                        sensory=sensory,
                        current_target=current_target,
                        evaluation_target=evaluation_target,
                        evaluation_mask=evaluation_mask,
                        feedback_due=feedback_due,
                        input_by_step=input_by_step,
                        trial_by_step=trial_by_step,
                        event_type=event_type,
                        phase_by_step=phase_by_step,
                        skill_a_by_step=skill_a_by_step,
                        skill_b_by_step=skill_b_by_step,
                        pair_key_by_step=pair_key_by_step,
                        trial_id=trial_id,
                        start=cursor,
                        phase="primitive_train",
                        skill_a=skill,
                        skill_b="",
                        input_sign=x,
                        amplitude=amplitude,
                        heldout=False,
                        rng=rng,
                    )
                )
                trial_id += 1
                cursor += 3

    for _ in range(composition_repeats):
        for skill_a, skill_b in train_pairs:
            for x in inputs:
                needed = 4 + distractor_gap
                if cursor + needed >= steps:
                    break
                trials.append(
                    add_trial(
                        sensory=sensory,
                        current_target=current_target,
                        evaluation_target=evaluation_target,
                        evaluation_mask=evaluation_mask,
                        feedback_due=feedback_due,
                        input_by_step=input_by_step,
                        trial_by_step=trial_by_step,
                        event_type=event_type,
                        phase_by_step=phase_by_step,
                        skill_a_by_step=skill_a_by_step,
                        skill_b_by_step=skill_b_by_step,
                        pair_key_by_step=pair_key_by_step,
                        trial_id=trial_id,
                        start=cursor,
                        phase="composition_train",
                        skill_a=skill_a,
                        skill_b=skill_b,
                        input_sign=x,
                        amplitude=amplitude,
                        heldout=False,
                        distractor_gap=distractor_gap,
                        rng=rng,
                    )
                )
                trial_id += 1
                cursor += needed

    for repeat_idx in range(heldout_repeats):
        shuffled = list(heldout_pairs)
        rng.shuffle(shuffled)
        for skill_a, skill_b in shuffled:
            for x in inputs:
                needed = 4 + distractor_gap
                if cursor + needed >= steps:
                    break
                trials.append(
                    add_trial(
                        sensory=sensory,
                        current_target=current_target,
                        evaluation_target=evaluation_target,
                        evaluation_mask=evaluation_mask,
                        feedback_due=feedback_due,
                        input_by_step=input_by_step,
                        trial_by_step=trial_by_step,
                        event_type=event_type,
                        phase_by_step=phase_by_step,
                        skill_a_by_step=skill_a_by_step,
                        skill_b_by_step=skill_b_by_step,
                        pair_key_by_step=pair_key_by_step,
                        trial_id=trial_id,
                        start=cursor,
                        phase="heldout_composition_first" if repeat_idx == 0 else "heldout_composition_repeat",
                        skill_a=skill_a,
                        skill_b=skill_b,
                        input_sign=x,
                        amplitude=amplitude,
                        heldout=True,
                        distractor_gap=distractor_gap,
                        rng=rng,
                    )
                )
                trial_id += 1
                cursor += needed

    return task_from_trials(
        name=name,
        display_name=display_name,
        steps=steps,
        sensory=sensory,
        current_target=current_target,
        evaluation_target=evaluation_target,
        evaluation_mask=evaluation_mask,
        feedback_due=feedback_due,
        input_sign=input_by_step,
        trial_id=trial_by_step,
        event_type=event_type,
        phase=phase_by_step,
        skill_a=skill_a_by_step,
        skill_b=skill_b_by_step,
        pair_key=pair_key_by_step,
        trials=trials,
        metadata={
            "train_pairs": train_pairs,
            "heldout_pairs": heldout_pairs,
            "distractor_gap": distractor_gap,
            "primitive_repeats": primitive_repeats,
            "composition_repeats": composition_repeats,
            "heldout_repeats": heldout_repeats,
        },
    )


def heldout_skill_pair_task(*, steps: int, amplitude: float, seed: int, args: argparse.Namespace) -> CompositionTask:
    train_pairs = [("identity", "invert"), ("invert", "identity"), ("identity", "set_plus"), ("identity", "set_minus")]
    heldout_pairs = [("invert", "set_plus"), ("invert", "set_minus"), ("set_plus", "invert"), ("set_minus", "invert")]
    return build_composition_task(
        name="heldout_skill_pair",
        display_name="Held-Out Skill Pair Reuse",
        steps=steps,
        amplitude=amplitude,
        seed=seed + 51301,
        args=args,
        train_pairs=train_pairs,
        heldout_pairs=heldout_pairs,
    )


def order_sensitive_chain_task(*, steps: int, amplitude: float, seed: int, args: argparse.Namespace) -> CompositionTask:
    train_pairs = [("set_plus", "invert"), ("set_minus", "invert"), ("identity", "set_plus"), ("identity", "set_minus")]
    heldout_pairs = [("invert", "set_plus"), ("invert", "set_minus"), ("set_plus", "set_minus"), ("set_minus", "set_plus")]
    return build_composition_task(
        name="order_sensitive_chain",
        display_name="Order-Sensitive Skill Chain",
        steps=steps,
        amplitude=amplitude,
        seed=seed + 51302,
        args=args,
        train_pairs=train_pairs,
        heldout_pairs=heldout_pairs,
    )


def distractor_skill_chain_task(*, steps: int, amplitude: float, seed: int, args: argparse.Namespace) -> CompositionTask:
    train_pairs = [("identity", "invert"), ("set_plus", "identity"), ("set_minus", "identity")]
    heldout_pairs = [("invert", "set_plus"), ("invert", "set_minus"), ("set_plus", "invert"), ("set_minus", "invert")]
    return build_composition_task(
        name="distractor_skill_chain",
        display_name="Distractor Skill Chain",
        steps=steps,
        amplitude=amplitude,
        seed=seed + 51303,
        args=args,
        train_pairs=train_pairs,
        heldout_pairs=heldout_pairs,
        distractor_gap=int(args.distractor_gap),
    )


def build_tasks(args: argparse.Namespace, seed: int) -> list[CompositionTask]:
    factories = {
        "heldout_skill_pair": heldout_skill_pair_task,
        "order_sensitive_chain": order_sensitive_chain_task,
        "distractor_skill_chain": distractor_skill_chain_task,
    }
    names = [item.strip() for item in args.tasks.split(",") if item.strip()]
    if not names or names == ["all"]:
        names = list(factories)
    missing = [name for name in names if name not in factories]
    if missing:
        raise argparse.ArgumentTypeError(f"unknown Tier 5.13 tasks: {', '.join(missing)}")
    return [factories[name](steps=args.steps, amplitude=args.amplitude, seed=seed, args=args) for name in names]


class ModuleComposer:
    def __init__(self, *, mode: str, task: CompositionTask, seed: int):
        self.mode = mode
        self.module_table: dict[str, dict[int, int]] = {skill: {} for skill in SKILL_ORDER}
        self.combo_table: dict[tuple[str, str, int], int] = {}
        self.current_skill_a = ""
        self.current_skill_b = ""
        self.current_input = 1
        rng = np.random.default_rng(seed + 9513)
        shuffled = list(SKILL_ORDER)
        rng.shuffle(shuffled)
        self.skill_permutation = {skill: shuffled[idx] for idx, skill in enumerate(SKILL_ORDER)}
        if all(self.skill_permutation[s] == s for s in SKILL_ORDER):
            self.skill_permutation = {skill: shuffled[(idx + 1) % len(shuffled)] for idx, skill in enumerate(SKILL_ORDER)}
        self.updates = 0
        self.composition_uses = 0
        self.task = task

    def _module_lookup(self, skill: str, x: int) -> int:
        x = 1 if int(x) >= 0 else -1
        if self.mode == "oracle":
            return apply_skill(skill, x)
        lookup_skill = self.skill_permutation.get(skill, skill) if self.mode == "shuffle" else skill
        table = self.module_table.get(lookup_skill, {})
        return int(table.get(x, 0))

    def observe_event(self, step: int) -> None:
        event = self.task.event_type[step]
        if event == "skill_a":
            self.current_skill_a = self.task.skill_a[step]
            self.current_skill_b = ""
        elif event == "skill_b":
            self.current_skill_b = self.task.skill_b[step]
        elif event == "input":
            self.current_input = int(self.task.input_sign[step]) or strict_sign(float(self.task.stream.sensory[step])) or 1

    def predict(self, step: int) -> tuple[float, dict[str, Any]]:
        self.observe_event(step)
        if self.task.event_type[step] != "decision":
            return 0.0, {"feature_active": False, "feature_source": "none"}
        skill_a = self.task.skill_a[step] or self.current_skill_a
        skill_b = self.task.skill_b[step] or self.current_skill_b
        x = int(self.task.input_sign[step]) or self.current_input
        feature_source = self.mode
        y = 0
        if self.mode == "combo_memorization":
            y = int(self.combo_table.get((skill_a, skill_b, x), 0))
        else:
            if self.mode == "reset" and self.task.phase[step].startswith("heldout"):
                y = 0
            else:
                first = self._module_lookup(skill_a, x)
                if skill_b:
                    if self.mode == "order_shuffle":
                        first = self._module_lookup(skill_b, x)
                        y = self._module_lookup(skill_a, first) if first != 0 else 0
                    else:
                        y = self._module_lookup(skill_b, first) if first != 0 else 0
                else:
                    y = first
        active = bool(y != 0 and self.task.phase[step].startswith("heldout"))
        if skill_a and (skill_b or self.task.phase[step] == "primitive_train"):
            self.composition_uses += int(active)
        return float(y), {
            "feature_active": active,
            "feature_source": feature_source,
            "skill_a": skill_a,
            "skill_b": skill_b,
            "input_sign": int(x),
            "module_updates": int(self.updates),
            "module_composition_uses": int(self.composition_uses),
            "skill_permutation": dict(self.skill_permutation),
        }

    def update_after_feedback(self, step: int) -> None:
        if self.task.event_type[step] != "decision":
            return
        label = strict_sign(float(self.task.stream.evaluation_target[step]))
        if label == 0:
            return
        skill_a = self.task.skill_a[step] or self.current_skill_a
        skill_b = self.task.skill_b[step] or self.current_skill_b
        x = int(self.task.input_sign[step]) or self.current_input
        if self.task.phase[step] == "primitive_train" and skill_a:
            self.module_table.setdefault(skill_a, {})[1 if x >= 0 else -1] = int(label)
            self.updates += 1
        if self.task.phase[step] == "composition_train" and skill_a and skill_b:
            self.combo_table[(skill_a, skill_b, 1 if x >= 0 else -1)] = int(label)


def task_pressure_summary(task: CompositionTask) -> dict[str, Any]:
    decision_steps = [idx for idx, flag in enumerate(task.stream.evaluation_mask) if bool(flag)]
    by_input: dict[int, set[int]] = {-1: set(), 1: set()}
    by_pair: dict[str, set[int]] = {}
    heldout_pairs: set[str] = set()
    train_pairs: set[str] = set()
    for step in decision_steps:
        label = strict_sign(float(task.stream.evaluation_target[step]))
        x = int(task.input_sign[step]) or strict_sign(float(task.stream.sensory[step]))
        by_input.setdefault(x, set()).add(label)
        by_pair.setdefault(task.pair_key[step], set()).add(label)
        if bool(task.heldout_mask[step]):
            heldout_pairs.add(task.pair_key[step])
        elif task.phase[step] == "composition_train":
            train_pairs.add(task.pair_key[step])
    ambiguous_inputs = [x for x, labels in by_input.items() if len(labels) > 1]
    return {
        "decision_count": len(decision_steps),
        "heldout_decision_count": int(np.sum(task.heldout_mask & task.stream.evaluation_mask)),
        "heldout_pair_count": len(heldout_pairs),
        "train_pair_count": len(train_pairs),
        "heldout_pairs": sorted(heldout_pairs),
        "train_pairs": sorted(train_pairs),
        "same_current_input_opposite_labels": len(ambiguous_inputs) >= 2,
        "ambiguous_input_count": len(ambiguous_inputs),
    }


def phase_accuracy(rows: list[dict[str, Any]], phase_prefix: str) -> float | None:
    selected = [row for row in rows if bool(row.get("target_signal_nonzero", False)) and str(row.get("phase", "")).startswith(phase_prefix)]
    if not selected:
        return None
    return float(np.mean([bool(row.get("strict_direction_correct", False)) for row in selected]))


def heldout_first_accuracy(rows: list[dict[str, Any]]) -> float | None:
    selected = [row for row in rows if bool(row.get("target_signal_nonzero", False)) and row.get("phase") == "heldout_composition_first"]
    if not selected:
        return None
    return float(np.mean([bool(row.get("strict_direction_correct", False)) for row in selected]))


def summarize_composition_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary = summarize_rows(rows)
    summary.update(
        {
            "primitive_accuracy": phase_accuracy(rows, "primitive"),
            "composition_train_accuracy": phase_accuracy(rows, "composition_train"),
            "heldout_accuracy": phase_accuracy(rows, "heldout_composition"),
            "heldout_first_accuracy": heldout_first_accuracy(rows),
            "feature_active_steps": int(sum(1 for row in rows if bool(row.get("feature_active", False)))),
            "module_updates": int(max([int(row.get("module_updates", 0) or 0) for row in rows], default=0)),
            "module_composition_uses": int(max([int(row.get("module_composition_uses", 0) or 0) for row in rows], default=0)),
        }
    )
    return summary


def base_row(task: CompositionTask, model: str, model_family: str, seed: int, step: int, prediction: float, backend: str) -> dict[str, Any]:
    eval_sign = strict_sign(float(task.stream.evaluation_target[step]))
    pred_sign = strict_sign(float(prediction))
    return {
        "task": task.stream.name,
        "model": model,
        "model_family": model_family,
        "backend": backend,
        "seed": int(seed),
        "step": int(step),
        "event_type": task.event_type[step],
        "phase": task.phase[step],
        "trial_id": int(task.trial_id[step]),
        "skill_a": task.skill_a[step],
        "skill_b": task.skill_b[step],
        "pair_key": task.pair_key[step],
        "heldout": bool(task.heldout_mask[step]),
        "input_sign": int(task.input_sign[step]),
        "sensory_return_1m": float(task.stream.sensory[step]),
        "target_return_1m": float(task.stream.current_target[step]),
        "target_signal_horizon": float(task.stream.evaluation_target[step]),
        "target_signal_sign": eval_sign,
        "target_signal_nonzero": bool(task.stream.evaluation_mask[step] and eval_sign != 0),
        "colony_prediction": float(prediction),
        "prediction_sign": pred_sign,
        "strict_direction_correct": bool(task.stream.evaluation_mask[step] and pred_sign != 0 and pred_sign == eval_sign),
        "feedback_due_step": int(task.stream.feedback_due_step[step]),
    }


def run_rule_variant(task: CompositionTask, variant: CompositionVariant, *, seed: int, args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    composer = ModuleComposer(mode=variant.mode, task=task, seed=seed)
    rows: list[dict[str, Any]] = []
    started = time.perf_counter()
    for step in range(task.stream.steps):
        prediction, feature = composer.predict(step)
        row = base_row(task, variant.name, "composition_scaffold", seed, step, prediction, "numpy_rule")
        row.update(
            {
                "variant": variant.name,
                "variant_group": variant.group,
                "feature_mode": variant.mode,
                **{k: v for k, v in feature.items() if k != "skill_permutation"},
            }
        )
        rows.append(row)
        composer.update_after_feedback(step)
    summary = summarize_composition_rows(rows)
    summary.update(
        {
            "task": task.stream.name,
            "model": variant.name,
            "model_family": "composition_scaffold",
            "variant": variant.name,
            "variant_group": variant.group,
            "feature_mode": variant.mode,
            "backend": "numpy_rule",
            "seed": int(seed),
            "steps": task.stream.steps,
            "runtime_seconds": time.perf_counter() - started,
            "task_metadata": task.stream.metadata,
            "task_pressure": task_pressure_summary(task),
            "hypothesis": variant.hypothesis,
        }
    )
    return rows, summary


def make_config(*, seed: int, task: CompositionTask, variant: CompositionVariant, args: argparse.Namespace) -> ReefConfig:
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
    return cfg


def run_cra_variant(task: CompositionTask, variant: CompositionVariant, *, seed: int, args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    random.seed(seed)
    np.random.seed(seed)
    sim, backend_name = load_backend(args.backend)
    setup_backend(sim, backend_name)
    cfg = make_config(seed=seed, task=task, variant=variant, args=args)
    organism = Organism(cfg, sim, use_default_trading_bridge=False)
    composer = ModuleComposer(mode="module_scaffold", task=task, seed=seed)
    rows: list[dict[str, Any]] = []
    started = time.perf_counter()
    try:
        organism.initialize(stream_keys=[task.stream.domain])
        for step in range(task.stream.steps):
            raw = float(task.stream.sensory[step])
            feature: dict[str, Any] = {"feature_active": False, "feature_source": "raw", "module_updates": composer.updates, "module_composition_uses": composer.composition_uses}
            observation = raw
            if variant.mode == "module_scaffold_input":
                predicted_feature, feature = composer.predict(step)
                if task.event_type[step] == "decision" and strict_sign(predicted_feature) != 0:
                    observation = float(args.amplitude) * float(strict_sign(predicted_feature))
            else:
                composer.observe_event(step)
            metadata = {
                "tier": "5.13",
                "variant": variant.name,
                "event_type": task.event_type[step],
                "phase": task.phase[step],
                "composition_pair_key": task.pair_key[step],
            }
            consequence = float(task.stream.current_target[step])
            metrics = organism.train_task_step(
                observation_value=observation,
                consequence_value=consequence,
                horizon_signal=consequence,
                dt_seconds=float(args.dt_seconds),
                task_name=task.stream.name,
                metadata=metadata,
            )
            prediction = float(metrics.colony_prediction)
            row = metrics.to_dict()
            row.update(base_row(task, variant.name, "CRA", seed, step, prediction, backend_name))
            row.update(
                {
                    "variant": variant.name,
                    "variant_group": variant.group,
                    "feature_mode": variant.mode,
                    "raw_sensory_return_1m": raw,
                    "composition_injected_observation": float(observation),
                    "configured_readout_lr": float(cfg.learning.readout_learning_rate),
                    "configured_delayed_readout_lr": float(cfg.learning.delayed_readout_learning_rate),
                    "configured_initial_population": int(cfg.lifecycle.initial_population),
                    "configured_max_population": int(cfg.lifecycle.max_population_hard),
                    **{k: v for k, v in feature.items() if k != "skill_permutation"},
                }
            )
            rows.append(row)
            composer.update_after_feedback(step)
    finally:
        organism.shutdown()
        end_backend(sim)
    summary = summarize_composition_rows(rows)
    summary.update(
        {
            "task": task.stream.name,
            "model": variant.name,
            "model_family": "CRA",
            "variant": variant.name,
            "variant_group": variant.group,
            "feature_mode": variant.mode,
            "backend": backend_name,
            "seed": int(seed),
            "steps": task.stream.steps,
            "runtime_seconds": time.perf_counter() - started,
            "task_metadata": task.stream.metadata,
            "task_pressure": task_pressure_summary(task),
            "hypothesis": variant.hypothesis,
        }
    )
    return rows, summary


def run_external_model(task: CompositionTask, model: str, *, seed: int, args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    feature_builder = FeatureBuilder(history=args.feature_history, amplitude=args.amplitude)
    learner_cls = LEARNER_FACTORIES[model]
    learner = learner_cls(seed=seed, feature_size=feature_builder.size, args=args)
    pending: dict[int, list[tuple[Any, int]]] = {}
    rows: list[dict[str, Any]] = []
    started = time.perf_counter()
    for step in range(task.stream.steps):
        x = feature_builder.step(float(task.stream.sensory[step]))
        prediction, update_state = learner.step(x)
        row = base_row(task, model, learner.family, seed, step, prediction, "numpy_online")
        rows.append(row)
        eval_sign = int(row["target_signal_sign"])
        if bool(task.stream.evaluation_mask[step]) and eval_sign != 0:
            due = int(task.stream.feedback_due_step[step])
            if due >= step and due < task.stream.steps:
                pending.setdefault(due, []).append((update_state, eval_sign))
        for state, label in pending.pop(step, []):
            learner.update(state, label)
    summary = summarize_composition_rows(rows)
    summary.update(
        {
            "task": task.stream.name,
            "model": model,
            "model_family": learner.family,
            "backend": "numpy_online",
            "seed": int(seed),
            "steps": task.stream.steps,
            "runtime_seconds": time.perf_counter() - started,
            "task_metadata": task.stream.metadata,
            "task_pressure": task_pressure_summary(task),
            "diagnostics": learner.diagnostics(),
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


def aggregate_runs(task: CompositionTask, model: str, summaries: list[dict[str, Any]]) -> dict[str, Any]:
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
        "primitive_accuracy",
        "composition_train_accuracy",
        "heldout_accuracy",
        "heldout_first_accuracy",
        "feature_active_steps",
        "module_updates",
        "module_composition_uses",
    ]
    aggregate: dict[str, Any] = {
        "task": task.stream.name,
        "display_name": task.stream.display_name,
        "domain": task.stream.domain,
        "model": model,
        "model_family": summaries[0].get("model_family") if summaries else None,
        "variant_group": summaries[0].get("variant_group") if summaries else None,
        "feature_mode": summaries[0].get("feature_mode") if summaries else None,
        "runs": len(summaries),
        "seeds": [summary.get("seed") for summary in summaries],
        "steps": task.stream.steps,
        "task_pressure": task_pressure_summary(task),
        "task_metadata": task.stream.metadata,
    }
    for key in keys:
        vals = [summary.get(key) for summary in summaries]
        aggregate[f"{key}_mean"] = mean(vals)
        aggregate[f"{key}_std"] = stdev(vals)
        aggregate[f"{key}_min"] = min_value(vals)
        valid = [float(v) for v in vals if v is not None]
        aggregate[f"{key}_max"] = max(valid) if valid else None
        aggregate[f"{key}_sum"] = float(sum(valid)) if valid else None
    return aggregate


def score(row: dict[str, Any]) -> float:
    heldout = float(row.get("heldout_accuracy_mean") or 0.0)
    first = float(row.get("heldout_first_accuracy_mean") or 0.0)
    all_acc = float(row.get("all_accuracy_mean") or 0.0)
    return 0.55 * heldout + 0.35 * first + 0.10 * all_acc


def build_comparisons(aggregates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_task_model = {(row["task"], row["model"]): row for row in aggregates}
    rows: list[dict[str, Any]] = []
    for task in sorted({row["task"] for row in aggregates}):
        candidate = by_task_model.get((task, "module_composition_scaffold"), {})
        raw = by_task_model.get((task, "v1_8_raw_cra"), {})
        bridge = by_task_model.get((task, "cra_composition_input_scaffold"), {})
        oracle = by_task_model.get((task, "oracle_composition"), {})
        ablations = [row for row in aggregates if row["task"] == task and row.get("variant_group") == "composition_ablation"]
        shortcut = by_task_model.get((task, "combo_memorization_control"), {})
        standards = [
            row
            for row in aggregates
            if row["task"] == task
            and row.get("model_family") not in {"CRA", "composition_scaffold"}
        ]
        best_ablation = max(ablations, key=score, default={})
        best_standard = max(standards, key=lambda row: float(row.get("heldout_first_accuracy_mean") or 0.0), default={})
        pressure = candidate.get("task_pressure") or raw.get("task_pressure") or {}
        rows.append(
            {
                "task": task,
                "candidate_heldout_accuracy": candidate.get("heldout_accuracy_mean"),
                "candidate_heldout_first_accuracy": candidate.get("heldout_first_accuracy_mean"),
                "candidate_all_accuracy": candidate.get("all_accuracy_mean"),
                "candidate_feature_active_steps": candidate.get("feature_active_steps_sum"),
                "candidate_module_updates": candidate.get("module_updates_max"),
                "candidate_module_uses": candidate.get("module_composition_uses_sum"),
                "v1_8_heldout_first_accuracy": raw.get("heldout_first_accuracy_mean"),
                "bridge_heldout_first_accuracy": bridge.get("heldout_first_accuracy_mean"),
                "oracle_heldout_first_accuracy": oracle.get("heldout_first_accuracy_mean"),
                "best_ablation_model": best_ablation.get("model"),
                "best_ablation_heldout_first_accuracy": best_ablation.get("heldout_first_accuracy_mean"),
                "combo_memorization_heldout_first_accuracy": shortcut.get("heldout_first_accuracy_mean"),
                "best_standard_model": best_standard.get("model"),
                "best_standard_heldout_first_accuracy": best_standard.get("heldout_first_accuracy_mean"),
                "candidate_first_delta_vs_v1_8": float(candidate.get("heldout_first_accuracy_mean") or 0.0) - float(raw.get("heldout_first_accuracy_mean") or 0.0),
                "candidate_first_delta_vs_best_ablation": float(candidate.get("heldout_first_accuracy_mean") or 0.0) - float(best_ablation.get("heldout_first_accuracy_mean") or 0.0),
                "candidate_first_delta_vs_combo_memorization": float(candidate.get("heldout_first_accuracy_mean") or 0.0) - float(shortcut.get("heldout_first_accuracy_mean") or 0.0),
                "candidate_first_delta_vs_best_standard": float(candidate.get("heldout_first_accuracy_mean") or 0.0) - float(best_standard.get("heldout_first_accuracy_mean") or 0.0),
                "same_current_input_opposite_labels": bool(pressure.get("same_current_input_opposite_labels", False)),
                "heldout_pair_count": pressure.get("heldout_pair_count"),
                "heldout_decision_count": pressure.get("heldout_decision_count"),
            }
        )
    return rows


def evaluate_tier(
    *,
    aggregates: list[dict[str, Any]],
    comparisons: list[dict[str, Any]],
    leakage: dict[str, Any],
    variants: list[CompositionVariant],
    models: list[str],
    args: argparse.Namespace,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    tasks = [item.strip() for item in args.tasks.split(",") if item.strip()]
    if not tasks or tasks == ["all"]:
        tasks = [item.strip() for item in DEFAULT_TASKS.split(",") if item.strip()]
    seeds = seeds_from_args(args)
    expected_runs = len(tasks) * len(seeds) * (len(variants) + len(models))
    observed_runs = sum(int(row.get("runs", 0)) for row in aggregates)
    candidate_first = [float(row.get("candidate_heldout_first_accuracy") or 0.0) for row in comparisons]
    candidate_heldout = [float(row.get("candidate_heldout_accuracy") or 0.0) for row in comparisons]
    raw_edges = [float(row.get("candidate_first_delta_vs_v1_8") or 0.0) for row in comparisons]
    ablation_edges = [float(row.get("candidate_first_delta_vs_best_ablation") or 0.0) for row in comparisons]
    combo_edges = [float(row.get("candidate_first_delta_vs_combo_memorization") or 0.0) for row in comparisons]
    standard_edges = [float(row.get("candidate_first_delta_vs_best_standard") or 0.0) for row in comparisons]
    active_steps = sum(float(row.get("candidate_feature_active_steps") or 0.0) for row in comparisons)
    module_updates = sum(float(row.get("candidate_module_updates") or 0.0) for row in comparisons)
    module_uses = sum(float(row.get("candidate_module_uses") or 0.0) for row in comparisons)
    pressure_ok = all(bool(row.get("same_current_input_opposite_labels")) and int(row.get("heldout_pair_count") or 0) > 0 for row in comparisons)
    base_criteria = [
        criterion("full variant/baseline/task/seed matrix completed", observed_runs, "==", expected_runs, observed_runs == expected_runs),
        criterion("feedback timing has no leakage violations", leakage.get("feedback_due_violations"), "==", 0, int(leakage.get("feedback_due_violations", 0)) == 0),
        criterion("tasks contain shortcut-ambiguous held-out compositions", pressure_ok, "==", True, pressure_ok),
        criterion("candidate module scaffold activates on held-out composition", active_steps, ">", 0, active_steps > 0),
        criterion("candidate learns primitive module tables before composition", module_updates, ">", 0, module_updates > 0),
        criterion("candidate performs held-out module composition", module_uses, ">", 0, module_uses > 0),
    ]
    science_criteria = [
        criterion(
            "candidate reaches minimum first-heldout composition accuracy",
            min(candidate_first) if candidate_first else None,
            ">=",
            args.min_candidate_heldout_first_accuracy,
            bool(candidate_first) and min(candidate_first) >= args.min_candidate_heldout_first_accuracy,
        ),
        criterion(
            "candidate reaches minimum total heldout composition accuracy",
            min(candidate_heldout) if candidate_heldout else None,
            ">=",
            args.min_candidate_heldout_accuracy,
            bool(candidate_heldout) and min(candidate_heldout) >= args.min_candidate_heldout_accuracy,
        ),
        criterion(
            "candidate improves over raw v1.8 CRA on first heldout compositions",
            min(raw_edges) if raw_edges else None,
            ">=",
            args.min_candidate_edge_vs_v1_8,
            bool(raw_edges) and min(raw_edges) >= args.min_candidate_edge_vs_v1_8,
        ),
        criterion(
            "composition shams are worse than candidate",
            min(ablation_edges) if ablation_edges else None,
            ">=",
            args.min_candidate_edge_vs_ablation,
            bool(ablation_edges) and min(ablation_edges) >= args.min_candidate_edge_vs_ablation,
        ),
        criterion(
            "candidate beats combo memorization on first heldout compositions",
            min(combo_edges) if combo_edges else None,
            ">=",
            args.min_candidate_edge_vs_combo,
            bool(combo_edges) and min(combo_edges) >= args.min_candidate_edge_vs_combo,
        ),
        criterion(
            "candidate beats best selected standard baseline on first heldout compositions",
            min(standard_edges) if standard_edges else None,
            ">=",
            args.min_candidate_edge_vs_standard,
            bool(standard_edges) and min(standard_edges) >= args.min_candidate_edge_vs_standard,
        ),
    ]
    criteria = base_criteria if args.smoke else base_criteria + science_criteria
    summary = {
        "expected_runs": expected_runs,
        "observed_runs": observed_runs,
        "tasks": tasks,
        "seeds": seeds,
        "models": models,
        "variants": [variant.name for variant in variants],
        "steps": args.steps,
        "smoke": bool(args.smoke),
        "leakage": leakage,
        "candidate_feature_active_steps_sum": active_steps,
        "candidate_module_updates_sum": module_updates,
        "candidate_module_uses_sum": module_uses,
        "claim_boundary": "Software diagnostic only: explicit reusable-module composition scaffold, not internal/native CRA composition, routing, planning, language, or hardware evidence.",
    }
    return criteria, summary


def aggregate_csv_rows(aggregates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fields = [
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
        "primitive_accuracy_mean",
        "composition_train_accuracy_mean",
        "prediction_target_corr_mean",
        "runtime_seconds_mean",
        "feature_active_steps_sum",
        "module_updates_max",
        "module_composition_uses_sum",
    ]
    return [{field: row.get(field) for field in fields} for row in aggregates]


def plot_composition(comparisons: list[dict[str, Any]], path: Path) -> None:
    if plt is None or not comparisons:
        return
    tasks = [row["task"].replace("_", "\n") for row in comparisons]
    raw = [float(row.get("v1_8_heldout_first_accuracy") or 0.0) for row in comparisons]
    candidate = [float(row.get("candidate_heldout_first_accuracy") or 0.0) for row in comparisons]
    ablation = [float(row.get("best_ablation_heldout_first_accuracy") or 0.0) for row in comparisons]
    standard = [float(row.get("best_standard_heldout_first_accuracy") or 0.0) for row in comparisons]
    x = np.arange(len(tasks))
    width = 0.20
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.bar(x - 1.5 * width, raw, width, label="v1.8 raw CRA", color="#9f1239")
    ax.bar(x - 0.5 * width, ablation, width, label="best composition sham", color="#737373")
    ax.bar(x + 0.5 * width, standard, width, label="best standard baseline", color="#b7791f")
    ax.bar(x + 1.5 * width, candidate, width, label="module composition scaffold", color="#1d4ed8")
    ax.set_title("Tier 5.13 Held-Out Composition Accuracy")
    ax.set_xticks(x)
    ax.set_xticklabels(tasks)
    ax.set_ylim(0.0, 1.05)
    ax.set_ylabel("first held-out composition accuracy")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fairness_contract(args: argparse.Namespace, variants: list[CompositionVariant], models: list[str]) -> dict[str, Any]:
    return {
        "tier": TIER,
        "purpose": "test held-out compositional skill reuse before internal CRA/routing implementation",
        "candidate": "module_composition_scaffold",
        "frozen_comparator": "v1_8_raw_cra",
        "ablation_controls": [variant.name for variant in variants if variant.group == "composition_ablation"],
        "shortcut_control": "combo_memorization_control",
        "oracle_upper_bound": "oracle_composition",
        "selected_external_baselines": models,
        "fairness_rules": [
            "all models see the same scalar event stream, target stream, evaluation mask, and feedback_due_step arrays per seed",
            "standard baselines receive no skill metadata beyond the scalar sensory event stream",
            "the module scaffold may update primitive module tables only after primitive decision feedback is available",
            "held-out pair accuracy is scored before pair-specific combo memorization can learn the new combination",
            "module-reset, module-shuffle, and order-shuffle shams must lose before a composition claim is promoted",
            "raw v1.8 CRA is included as a frozen comparator, not as a tuned composition model",
            "passing Tier 5.13 does not prove internal/native CRA composition or module routing",
        ],
        "tasks": args.tasks,
        "steps": args.steps,
        "seeds": seeds_from_args(args),
        "feature_history": args.feature_history,
    }


def run_tier(args: argparse.Namespace, output_dir: Path) -> dict[str, Any]:
    variants = parse_variants(args.variants)
    models = [model for model in parse_models(args.models) if model != "cra"]
    summaries_by_cell: dict[tuple[str, str], list[dict[str, Any]]] = {}
    rows_by_cell_seed: dict[tuple[str, str, int], list[dict[str, Any]]] = {}
    task_by_name: dict[str, CompositionTask] = {}
    artifacts: dict[str, str] = {}
    started = time.perf_counter()
    for seed in seeds_from_args(args):
        for task in build_tasks(args, seed=args.task_seed + seed):
            task_by_name[task.stream.name] = task
            for variant in variants:
                print(f"[tier5.13] task={task.stream.name} variant={variant.name} seed={seed}", flush=True)
                if variant.runner == "cra":
                    rows, summary = run_cra_variant(task, variant, seed=seed, args=args)
                else:
                    rows, summary = run_rule_variant(task, variant, seed=seed, args=args)
                csv_path = output_dir / f"{task.stream.name}_{variant.name}_seed{seed}_timeseries.csv"
                write_csv(csv_path, rows)
                artifacts[f"{task.stream.name}_{variant.name}_seed{seed}_timeseries_csv"] = str(csv_path)
                summaries_by_cell.setdefault((task.stream.name, variant.name), []).append(summary)
                rows_by_cell_seed[(task.stream.name, variant.name, seed)] = rows
            for model in models:
                print(f"[tier5.13] task={task.stream.name} model={model} seed={seed}", flush=True)
                rows, summary = run_external_model(task, model, seed=seed, args=args)
                csv_path = output_dir / f"{task.stream.name}_{model}_seed{seed}_timeseries.csv"
                write_csv(csv_path, rows)
                artifacts[f"{task.stream.name}_{model}_seed{seed}_timeseries_csv"] = str(csv_path)
                summaries_by_cell.setdefault((task.stream.name, model), []).append(summary)
                rows_by_cell_seed[(task.stream.name, model, seed)] = rows
    aggregates = [
        aggregate_runs(task_by_name[task_name], model, summaries)
        for (task_name, model), summaries in sorted(summaries_by_cell.items())
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
    summary_csv = output_dir / "tier5_13_summary.csv"
    comparisons_csv = output_dir / "tier5_13_comparisons.csv"
    fairness_json = output_dir / "tier5_13_fairness_contract.json"
    plot_path = output_dir / "tier5_13_composition.png"
    write_csv(summary_csv, aggregate_csv_rows(aggregates))
    write_csv(comparisons_csv, comparisons)
    write_json(fairness_json, fairness_contract(args, variants, models))
    plot_composition(comparisons, plot_path)
    return {
        "name": TIER,
        "status": status,
        "summary": {
            "tier_summary": tier_summary,
            "aggregates": aggregates,
            "comparisons": comparisons,
            "runtime_seconds": time.perf_counter() - started,
        },
        "criteria": criteria,
        "artifacts": {
            **artifacts,
            "summary_csv": str(summary_csv),
            "comparisons_csv": str(comparisons_csv),
            "fairness_contract_json": str(fairness_json),
            "composition_png": str(plot_path),
        },
        "failure_reason": failure_reason,
    }


def write_report(path: Path, result: dict[str, Any], args: argparse.Namespace, output_dir: Path) -> None:
    overall = "PASS" if result["status"] == "pass" else "FAIL"
    comparisons = result["summary"]["comparisons"]
    aggregates = result["summary"]["aggregates"]
    lines = [
        "# Tier 5.13 Compositional Skill Reuse Diagnostic Findings",
        "",
        f"- Generated: `{utc_now()}`",
        f"- Status: **{overall}**",
        f"- Backend for CRA comparators: `{args.backend}`",
        f"- Steps: `{args.steps}`",
        f"- Seeds: `{', '.join(str(seed) for seed in seeds_from_args(args))}`",
        f"- Tasks: `{args.tasks}`",
        f"- Variants: `{args.variants}`",
        f"- Selected standard baselines: `{args.models}`",
        f"- Smoke mode: `{args.smoke}`",
        f"- Output directory: `{output_dir}`",
        "",
        "Tier 5.13 tests held-out skill composition: primitive skills are learned separately, then reused on unseen skill-pair combinations.",
        "",
        "## Claim Boundary",
        "",
        "- This is software diagnostic evidence, not hardware evidence.",
        "- The candidate is an explicit host-side reusable-module scaffold, not native/internal CRA composition yet.",
        "- This does not prove module routing, language reasoning, long-horizon planning, or AGI.",
        "- A pass authorizes an internal CRA composition/routing implementation; it does not freeze a new baseline by itself.",
        "",
        "## Task Comparisons",
        "",
        "| Task | Candidate heldout first | Candidate heldout all | v1.8 heldout first | Bridge heldout first | Best sham | Sham heldout first | Combo heldout first | Best baseline | Baseline heldout first | Edge vs v1.8 | Edge vs sham | Edge vs combo | Edge vs baseline | Updates | Uses |",
        "| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in comparisons:
        lines.append(
            "| "
            f"{row['task']} | "
            f"{markdown_value(row.get('candidate_heldout_first_accuracy'))} | "
            f"{markdown_value(row.get('candidate_heldout_accuracy'))} | "
            f"{markdown_value(row.get('v1_8_heldout_first_accuracy'))} | "
            f"{markdown_value(row.get('bridge_heldout_first_accuracy'))} | "
            f"`{row.get('best_ablation_model')}` | "
            f"{markdown_value(row.get('best_ablation_heldout_first_accuracy'))} | "
            f"{markdown_value(row.get('combo_memorization_heldout_first_accuracy'))} | "
            f"`{row.get('best_standard_model')}` | "
            f"{markdown_value(row.get('best_standard_heldout_first_accuracy'))} | "
            f"{markdown_value(row.get('candidate_first_delta_vs_v1_8'))} | "
            f"{markdown_value(row.get('candidate_first_delta_vs_best_ablation'))} | "
            f"{markdown_value(row.get('candidate_first_delta_vs_combo_memorization'))} | "
            f"{markdown_value(row.get('candidate_first_delta_vs_best_standard'))} | "
            f"{markdown_value(row.get('candidate_module_updates'))} | "
            f"{markdown_value(row.get('candidate_module_uses'))} |"
        )
    lines.extend(["", "## Aggregate Matrix", "", "| Task | Model | Family | Group | All acc | Heldout acc | Heldout first | Primitive acc | Runtime s |", "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |"])
    for row in sorted(aggregates, key=lambda item: (item["task"], item.get("model_family") != "composition_scaffold", item["model"])):
        lines.append(
            "| "
            f"{row['task']} | `{row['model']}` | {row.get('model_family')} | {row.get('variant_group') or ''} | "
            f"{markdown_value(row.get('all_accuracy_mean'))} | "
            f"{markdown_value(row.get('heldout_accuracy_mean'))} | "
            f"{markdown_value(row.get('heldout_first_accuracy_mean'))} | "
            f"{markdown_value(row.get('primitive_accuracy_mean'))} | "
            f"{markdown_value(row.get('runtime_seconds_mean'))} |"
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
            "- `tier5_13_results.json`: machine-readable manifest.",
            "- `tier5_13_report.md`: human findings and claim boundary.",
            "- `tier5_13_summary.csv`: aggregate task/model metrics.",
            "- `tier5_13_comparisons.csv`: candidate-vs-sham/baseline table.",
            "- `tier5_13_fairness_contract.json`: predeclared comparison/leakage rules.",
            "- `tier5_13_composition.png`: held-out composition plot.",
            "- `*_timeseries.csv`: per-task/per-model/per-seed traces.",
            "",
            "![composition](tier5_13_composition.png)",
            "",
        ]
    )
    if MATPLOTLIB_ERROR:
        lines.append(f"Plotting unavailable: `{MATPLOTLIB_ERROR}`")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_latest(output_dir: Path, report_path: Path, manifest_path: Path, summary_csv: Path, status: str) -> None:
    latest_path = ROOT / "controlled_test_output" / "tier5_13_latest_manifest.json"
    payload = {
        "generated_at_utc": utc_now(),
        "tier": TIER,
        "status": status,
        "output_dir": str(output_dir),
        "manifest": str(manifest_path),
        "report": str(report_path),
        "summary_csv": str(summary_csv),
        "canonical": False,
        "claim": "Latest Tier 5.13 compositional skill-reuse diagnostic; passing authorizes internal CRA composition/routing work only.",
    }
    write_json(latest_path, payload)


def build_parser() -> argparse.ArgumentParser:
    parser = build_tier5_1_parser()
    parser.description = "Run Tier 5.13 compositional skill-reuse diagnostic."
    parser.set_defaults(
        backend="mock",
        tasks=DEFAULT_TASKS,
        steps=720,
        seed_count=3,
        models=DEFAULT_MODELS,
        feature_history=8,
        cra_delayed_readout_lr=0.20,
    )
    parser.add_argument("--variants", default=DEFAULT_VARIANTS)
    parser.add_argument("--primitive-repeats", type=int, default=4)
    parser.add_argument("--composition-repeats", type=int, default=2)
    parser.add_argument("--heldout-repeats", type=int, default=5)
    parser.add_argument("--distractor-gap", type=int, default=3)
    parser.add_argument("--message-passing-steps", type=int, default=2)
    parser.add_argument("--message-context-gain", type=float, default=0.35)
    parser.add_argument("--message-prediction-mix", type=float, default=0.25)
    parser.add_argument("--min-candidate-heldout-first-accuracy", type=float, default=0.95)
    parser.add_argument("--min-candidate-heldout-accuracy", type=float, default=0.95)
    parser.add_argument("--min-candidate-edge-vs-v1-8", type=float, default=0.20)
    parser.add_argument("--min-candidate-edge-vs-ablation", type=float, default=0.20)
    parser.add_argument("--min-candidate-edge-vs-combo", type=float, default=0.20)
    parser.add_argument("--min-candidate-edge-vs-standard", type=float, default=0.10)
    parser.add_argument("--smoke", action="store_true", help="Run harness integrity gates only; mechanism promotion gates are skipped.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = args.output_dir or (ROOT / "controlled_test_output" / f"tier5_13_{timestamp}")
    output_dir.mkdir(parents=True, exist_ok=True)
    result = run_tier(args, output_dir)
    manifest_path = output_dir / "tier5_13_results.json"
    report_path = output_dir / "tier5_13_report.md"
    summary_csv = output_dir / "tier5_13_summary.csv"
    comparisons_csv = output_dir / "tier5_13_comparisons.csv"
    fairness_json = output_dir / "tier5_13_fairness_contract.json"
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
            "composition_png": str(output_dir / "tier5_13_composition.png"),
        },
    }
    write_json(manifest_path, json_safe(manifest))
    write_report(report_path, result, args, output_dir)
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
