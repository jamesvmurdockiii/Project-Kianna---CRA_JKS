#!/usr/bin/env python3
"""Tier 5.13b module routing / contextual gating diagnostic.

Tier 5.13 showed that an explicit reusable-module scaffold can compose learned
skills on held-out combinations. Tier 5.13b asks the next question: can a router
select the correct learned module when several modules are available, the current
input is ambiguous, and the context cue must be held across distractors?

This is software diagnostic evidence only. The candidate is an explicit
host-side contextual router scaffold and a CRA feature bridge. A pass authorizes
internal CRA routing/gating work; it is not native CRA routing, hardware routing,
language reasoning, planning, or AGI evidence.
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
    setup_backend,
    strict_sign,
    write_csv,
    write_json,
)
from tier4_scaling import mean, min_value, seeds_from_args, stdev  # noqa: E402
from tier5_compositional_skill_reuse import (  # noqa: E402
    SKILL_CODES,
    SKILL_ORDER,
    apply_skill,
)
from tier5_external_baselines import (  # noqa: E402
    FeatureBuilder,
    LEARNER_FACTORIES,
    TaskStream,
    build_parser as build_tier5_1_parser,
    parse_models,
    summarize_rows,
)
from tier5_macro_eligibility import computed_horizon, set_nested_attr  # noqa: E402


TIER = "Tier 5.13b - Module Routing / Contextual Gating Diagnostic"
DEFAULT_TASKS = "heldout_context_routing,distractor_router_chain,context_reentry_routing"
DEFAULT_MODELS = "sign_persistence,online_perceptron,online_logistic_regression,echo_state_network,small_gru,stdp_only_snn"
DEFAULT_VARIANTS = "v1_8_raw_cra,cra_router_input_scaffold,contextual_router_scaffold,always_on_modules,random_router,router_reset_ablation,context_shuffle_ablation,oracle_router"
EPS = 1e-12

CONTEXT_SPECS = {
    "reef": {"cue": 0.18, "skill": "identity"},
    "lagoon": {"cue": 0.34, "skill": "invert"},
    "storm": {"cue": 0.50, "skill": "set_plus"},
    "deep": {"cue": 0.66, "skill": "set_minus"},
}
CONTEXT_ORDER = tuple(CONTEXT_SPECS)


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
class RoutingTrial:
    trial_id: int
    phase: str
    context: str
    true_skill: str
    input_sign: int
    label_sign: int
    context_step: int
    input_step: int
    decision_step: int
    heldout: bool
    distractor_count: int


@dataclass(frozen=True)
class RoutingTask:
    stream: TaskStream
    event_type: list[str]
    phase: list[str]
    context: list[str]
    true_skill: list[str]
    input_sign: np.ndarray
    trial_id: np.ndarray
    heldout_mask: np.ndarray
    first_heldout_mask: np.ndarray
    trials: list[RoutingTrial]


@dataclass(frozen=True)
class RoutingVariant:
    name: str
    group: str
    runner: str
    mode: str
    hypothesis: str
    overrides: dict[str, Any]


VARIANTS: tuple[RoutingVariant, ...] = (
    RoutingVariant(
        name="v1_8_raw_cra",
        group="frozen_baseline",
        runner="cra",
        mode="raw",
        hypothesis="Frozen v1.8-style CRA sees the raw delayed-context event stream without an explicit router feature.",
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
    RoutingVariant(
        name="cra_router_input_scaffold",
        group="candidate_bridge",
        runner="cra",
        mode="router_input",
        hypothesis="CRA receives the routed module output as a host-computed scalar feature at decision time.",
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
    RoutingVariant(
        name="contextual_router_scaffold",
        group="candidate_scaffold",
        runner="rule",
        mode="contextual_router",
        hypothesis="Learns primitive modules and context-to-module scores, then selects the active module before feedback on held-out routing trials.",
        overrides={},
    ),
    RoutingVariant(
        name="always_on_modules",
        group="routing_ablation",
        runner="rule",
        mode="always_on",
        hypothesis="Control: all modules fire together, so conflicting modules cancel or vote ambiguously.",
        overrides={},
    ),
    RoutingVariant(
        name="random_router",
        group="routing_ablation",
        runner="rule",
        mode="random_router",
        hypothesis="Control: a random learned module is selected at decision time.",
        overrides={},
    ),
    RoutingVariant(
        name="router_reset_ablation",
        group="routing_ablation",
        runner="rule",
        mode="router_reset",
        hypothesis="Control: the learned router table is cleared on held-out routing trials.",
        overrides={},
    ),
    RoutingVariant(
        name="context_shuffle_ablation",
        group="routing_ablation",
        runner="rule",
        mode="context_shuffle",
        hypothesis="Control: context keys retrieve a different context's module scores.",
        overrides={},
    ),
    RoutingVariant(
        name="oracle_router",
        group="oracle_upper_bound",
        runner="rule",
        mode="oracle",
        hypothesis="Oracle upper bound with the true context-to-skill map; reported but not promoted.",
        overrides={},
    ),
)


def parse_variants(raw: str) -> list[RoutingVariant]:
    names = [item.strip() for item in raw.split(",") if item.strip()]
    if not names or names == ["all"]:
        return list(VARIANTS)
    by_name = {variant.name: variant for variant in VARIANTS}
    missing = [name for name in names if name not in by_name]
    if missing:
        raise argparse.ArgumentTypeError(f"unknown Tier 5.13b variants: {', '.join(missing)}")
    selected = [by_name[name] for name in names]
    required = {"v1_8_raw_cra", "contextual_router_scaffold"}
    present = {variant.name for variant in selected}
    if not required.issubset(present):
        raise argparse.ArgumentTypeError("Tier 5.13b requires v1_8_raw_cra and contextual_router_scaffold")
    return selected


def empty_arrays(steps: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[str], list[str], list[str], list[str]]:
    sensory = np.zeros(steps, dtype=float)
    current_target = np.zeros(steps, dtype=float)
    evaluation_target = np.zeros(steps, dtype=float)
    evaluation_mask = np.zeros(steps, dtype=bool)
    feedback_due = np.full(steps, -1, dtype=int)
    input_sign = np.zeros(steps, dtype=int)
    trial_id = np.full(steps, -1, dtype=int)
    event_type = ["none" for _ in range(steps)]
    phase = ["none" for _ in range(steps)]
    context = ["" for _ in range(steps)]
    true_skill = ["" for _ in range(steps)]
    return sensory, current_target, evaluation_target, evaluation_mask, feedback_due, input_sign, trial_id, event_type, phase, context, true_skill


def add_primitive_trial(
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
    context_by_step: list[str],
    skill_by_step: list[str],
    trial_id: int,
    start: int,
    skill: str,
    input_sign: int,
    amplitude: float,
) -> RoutingTrial:
    skill_step = start
    input_step = start + 1
    decision_step = start + 2
    label = apply_skill(skill, input_sign)
    sensory[skill_step] = amplitude * SKILL_CODES[skill]
    sensory[input_step] = amplitude * float(input_sign)
    sensory[decision_step] = amplitude * float(input_sign)
    current_target[decision_step] = amplitude * float(label)
    evaluation_target[decision_step] = amplitude * float(label)
    evaluation_mask[decision_step] = True
    feedback_due[decision_step] = decision_step
    event_type[skill_step] = "skill"
    event_type[input_step] = "input"
    event_type[decision_step] = "decision"
    for step in range(start, decision_step + 1):
        phase_by_step[step] = "primitive_train"
        skill_by_step[step] = skill
        trial_by_step[step] = trial_id
        input_by_step[step] = int(input_sign)
    return RoutingTrial(
        trial_id=trial_id,
        phase="primitive_train",
        context="",
        true_skill=skill,
        input_sign=int(input_sign),
        label_sign=int(label),
        context_step=-1,
        input_step=input_step,
        decision_step=decision_step,
        heldout=False,
        distractor_count=0,
    )


def add_routing_trial(
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
    context_by_step: list[str],
    skill_by_step: list[str],
    trial_id: int,
    start: int,
    phase: str,
    context: str,
    input_sign: int,
    amplitude: float,
    heldout: bool,
    distractor_gap: int,
    rng: np.random.Generator,
) -> RoutingTrial:
    true_skill = str(CONTEXT_SPECS[context]["skill"])
    label = apply_skill(true_skill, input_sign)
    context_step = start
    input_step = start + 1 + distractor_gap
    decision_step = input_step + 1
    sensory[context_step] = amplitude * float(CONTEXT_SPECS[context]["cue"])
    event_type[context_step] = "route_context"
    for offset in range(distractor_gap):
        step = start + 1 + offset
        # Distractors are deliberately plausible context/module-like signals.
        if offset % 2 == 0:
            distractor_context = str(rng.choice([c for c in CONTEXT_ORDER if c != context]))
            sensory[step] = amplitude * float(CONTEXT_SPECS[distractor_context]["cue"])
            event_type[step] = "context_distractor"
        else:
            distractor_skill = str(rng.choice(SKILL_ORDER))
            sensory[step] = amplitude * 0.5 * float(SKILL_CODES[distractor_skill])
            event_type[step] = "skill_distractor"
    sensory[input_step] = amplitude * float(input_sign)
    sensory[decision_step] = amplitude * float(input_sign)
    current_target[decision_step] = amplitude * float(label)
    evaluation_target[decision_step] = amplitude * float(label)
    evaluation_mask[decision_step] = True
    feedback_due[decision_step] = decision_step
    event_type[input_step] = "input"
    event_type[decision_step] = "decision"
    for step in range(start, decision_step + 1):
        phase_by_step[step] = phase
        context_by_step[step] = context
        skill_by_step[step] = true_skill
        trial_by_step[step] = trial_id
        input_by_step[step] = int(input_sign)
    return RoutingTrial(
        trial_id=trial_id,
        phase=phase,
        context=context,
        true_skill=true_skill,
        input_sign=int(input_sign),
        label_sign=int(label),
        context_step=context_step,
        input_step=input_step,
        decision_step=decision_step,
        heldout=bool(heldout),
        distractor_count=int(distractor_gap),
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
    context: list[str],
    true_skill: list[str],
    trials: list[RoutingTrial],
    metadata: dict[str, Any],
) -> RoutingTask:
    heldout_mask = np.zeros(steps, dtype=bool)
    first_heldout_mask = np.zeros(steps, dtype=bool)
    for trial in trials:
        if trial.heldout:
            heldout_mask[trial.decision_step] = True
        if trial.phase == "heldout_routing_first":
            first_heldout_mask[trial.decision_step] = True
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
        switch_steps=sorted({trial.decision_step for trial in trials if trial.heldout}),
        metadata={
            **metadata,
            "task_kind": name,
            "trials": len(trials),
            "decision_events": int(np.sum(evaluation_mask)),
            "heldout_decision_events": int(np.sum(heldout_mask)),
            "trial_records": [trial.__dict__ for trial in trials],
        },
    )
    return RoutingTask(
        stream=stream,
        event_type=event_type,
        phase=phase,
        context=context,
        true_skill=true_skill,
        input_sign=input_sign,
        trial_id=trial_id,
        heldout_mask=heldout_mask,
        first_heldout_mask=first_heldout_mask,
        trials=trials,
    )


def build_routing_task(
    *,
    name: str,
    display_name: str,
    steps: int,
    amplitude: float,
    seed: int,
    args: argparse.Namespace,
    route_train_repeats: int,
    heldout_repeats: int,
    distractor_gap: int,
    first_context_order: list[str] | None = None,
) -> RoutingTask:
    rng = np.random.default_rng(seed)
    arrays = empty_arrays(steps)
    sensory, current_target, evaluation_target, evaluation_mask, feedback_due, input_by_step, trial_by_step, event_type, phase_by_step, context_by_step, skill_by_step = arrays
    trials: list[RoutingTrial] = []
    cursor = 0
    trial_id = 0
    inputs = [1, -1]

    for _ in range(max(1, int(args.primitive_repeats))):
        for skill in SKILL_ORDER:
            for x in inputs:
                if cursor + 3 >= steps:
                    break
                trials.append(
                    add_primitive_trial(
                        sensory=sensory,
                        current_target=current_target,
                        evaluation_target=evaluation_target,
                        evaluation_mask=evaluation_mask,
                        feedback_due=feedback_due,
                        input_by_step=input_by_step,
                        trial_by_step=trial_by_step,
                        event_type=event_type,
                        phase_by_step=phase_by_step,
                        context_by_step=context_by_step,
                        skill_by_step=skill_by_step,
                        trial_id=trial_id,
                        start=cursor,
                        skill=skill,
                        input_sign=x,
                        amplitude=amplitude,
                    )
                )
                trial_id += 1
                cursor += 3

    for _ in range(max(1, route_train_repeats)):
        contexts = list(CONTEXT_ORDER)
        rng.shuffle(contexts)
        for context in contexts:
            for x in inputs:
                needed = 3 + distractor_gap
                if cursor + needed >= steps:
                    break
                trials.append(
                    add_routing_trial(
                        sensory=sensory,
                        current_target=current_target,
                        evaluation_target=evaluation_target,
                        evaluation_mask=evaluation_mask,
                        feedback_due=feedback_due,
                        input_by_step=input_by_step,
                        trial_by_step=trial_by_step,
                        event_type=event_type,
                        phase_by_step=phase_by_step,
                        context_by_step=context_by_step,
                        skill_by_step=skill_by_step,
                        trial_id=trial_id,
                        start=cursor,
                        phase="route_train",
                        context=context,
                        input_sign=x,
                        amplitude=amplitude,
                        heldout=False,
                        distractor_gap=distractor_gap,
                        rng=rng,
                    )
                )
                trial_id += 1
                cursor += needed

    for repeat_idx in range(max(1, heldout_repeats)):
        contexts = list(first_context_order or CONTEXT_ORDER)
        if repeat_idx > 0:
            rng.shuffle(contexts)
        for context in contexts:
            order = [-1, 1] if repeat_idx % 2 == 0 else [1, -1]
            for x in order:
                needed = 3 + distractor_gap
                if cursor + needed >= steps:
                    break
                trials.append(
                    add_routing_trial(
                        sensory=sensory,
                        current_target=current_target,
                        evaluation_target=evaluation_target,
                        evaluation_mask=evaluation_mask,
                        feedback_due=feedback_due,
                        input_by_step=input_by_step,
                        trial_by_step=trial_by_step,
                        event_type=event_type,
                        phase_by_step=phase_by_step,
                        context_by_step=context_by_step,
                        skill_by_step=skill_by_step,
                        trial_id=trial_id,
                        start=cursor,
                        phase="heldout_routing_first" if repeat_idx == 0 else "heldout_routing_repeat",
                        context=context,
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
        context=context_by_step,
        true_skill=skill_by_step,
        trials=trials,
        metadata={
            "contexts": CONTEXT_SPECS,
            "route_train_repeats": route_train_repeats,
            "heldout_repeats": heldout_repeats,
            "distractor_gap": distractor_gap,
            "primitive_repeats": int(args.primitive_repeats),
        },
    )


def heldout_context_routing_task(*, steps: int, amplitude: float, seed: int, args: argparse.Namespace) -> RoutingTask:
    return build_routing_task(
        name="heldout_context_routing",
        display_name="Held-Out Context Routing",
        steps=steps,
        amplitude=amplitude,
        seed=seed + 51311,
        args=args,
        route_train_repeats=int(args.route_train_repeats),
        heldout_repeats=int(args.heldout_repeats),
        distractor_gap=int(args.routing_gap),
        first_context_order=["reef", "lagoon", "storm", "deep"],
    )


def distractor_router_chain_task(*, steps: int, amplitude: float, seed: int, args: argparse.Namespace) -> RoutingTask:
    return build_routing_task(
        name="distractor_router_chain",
        display_name="Distractor Router Chain",
        steps=steps,
        amplitude=amplitude,
        seed=seed + 51312,
        args=args,
        route_train_repeats=int(args.route_train_repeats),
        heldout_repeats=int(args.heldout_repeats),
        distractor_gap=max(int(args.routing_gap) + 3, int(args.feature_history) + 3),
        first_context_order=["storm", "reef", "deep", "lagoon"],
    )


def context_reentry_routing_task(*, steps: int, amplitude: float, seed: int, args: argparse.Namespace) -> RoutingTask:
    return build_routing_task(
        name="context_reentry_routing",
        display_name="Context Reentry Routing",
        steps=steps,
        amplitude=amplitude,
        seed=seed + 51313,
        args=args,
        route_train_repeats=max(1, int(args.route_train_repeats) - 1),
        heldout_repeats=max(int(args.heldout_repeats), 5),
        distractor_gap=max(int(args.routing_gap) + 1, int(args.feature_history) + 2),
        first_context_order=["reef", "storm", "lagoon", "deep"],
    )


def build_tasks(args: argparse.Namespace, seed: int) -> list[RoutingTask]:
    factories = {
        "heldout_context_routing": heldout_context_routing_task,
        "distractor_router_chain": distractor_router_chain_task,
        "context_reentry_routing": context_reentry_routing_task,
    }
    names = [item.strip() for item in args.tasks.split(",") if item.strip()]
    if not names or names == ["all"]:
        names = list(factories)
    missing = [name for name in names if name not in factories]
    if missing:
        raise argparse.ArgumentTypeError(f"unknown Tier 5.13b tasks: {', '.join(missing)}")
    return [factories[name](steps=args.steps, amplitude=args.amplitude, seed=seed, args=args) for name in names]


class ContextRouter:
    def __init__(self, *, mode: str, task: RoutingTask, seed: int):
        self.mode = mode
        self.task = task
        self.rng = np.random.default_rng(seed + 95131)
        self.module_table: dict[str, dict[int, int]] = {skill: {} for skill in SKILL_ORDER}
        self.route_scores: dict[str, dict[str, float]] = {context: {skill: 0.0 for skill in SKILL_ORDER} for context in CONTEXT_ORDER}
        rotated = list(CONTEXT_ORDER[1:]) + [CONTEXT_ORDER[0]]
        self.context_permutation = {context: rotated[idx] for idx, context in enumerate(CONTEXT_ORDER)}
        self.current_context = ""
        self.current_input = 1
        self.current_skill = ""
        self.module_updates = 0
        self.router_updates = 0
        self.router_uses = 0
        self.correct_route_uses = 0
        self.pre_feedback_select_steps = 0

    def observe_event(self, step: int) -> None:
        event = self.task.event_type[step]
        if event == "skill":
            self.current_skill = self.task.true_skill[step]
        elif event == "route_context":
            self.current_context = self.task.context[step]
        elif event == "input":
            self.current_input = int(self.task.input_sign[step]) or strict_sign(float(self.task.stream.sensory[step])) or 1

    def _module_lookup(self, skill: str, x: int) -> int:
        x = 1 if int(x) >= 0 else -1
        if self.mode == "oracle":
            return apply_skill(skill, x)
        return int(self.module_table.get(skill, {}).get(x, 0))

    def _learned_route(self, context: str) -> str:
        scores = self.route_scores.get(context, {})
        if not scores:
            return ""
        best_skill, best_score = max(scores.items(), key=lambda item: (item[1], item[0]))
        return best_skill if best_score > 0 else ""

    def _selected_skill(self, context: str) -> str:
        if self.mode == "oracle":
            return str(CONTEXT_SPECS.get(context, {}).get("skill", ""))
        if self.mode == "context_shuffle":
            context = self.context_permutation.get(context, context)
        if self.mode == "random_router":
            return str(self.rng.choice(SKILL_ORDER))
        return self._learned_route(context)

    def predict(self, step: int) -> tuple[float, dict[str, Any]]:
        self.observe_event(step)
        if self.task.event_type[step] != "decision":
            return 0.0, {"router_active": False, "selected_skill": "", "selected_context": self.current_context}
        context = self.task.context[step] or self.current_context
        x = int(self.task.input_sign[step]) or self.current_input
        true_skill = self.task.true_skill[step]
        selected = ""
        y = 0
        if self.mode == "always_on":
            votes = [self._module_lookup(skill, x) for skill in SKILL_ORDER]
            y = strict_sign(float(sum(votes)))
            selected = "all"
        elif self.mode == "router_reset" and self.task.phase[step].startswith("heldout"):
            selected = ""
            y = 0
        else:
            selected = self._selected_skill(context)
            y = self._module_lookup(selected, x) if selected else 0
        active = bool(self.task.phase[step].startswith("heldout") and selected)
        self.router_uses += int(active)
        self.correct_route_uses += int(active and selected == true_skill)
        self.pre_feedback_select_steps += int(active)
        return float(y), {
            "router_active": active,
            "selected_context": context,
            "selected_skill": selected,
            "true_skill": true_skill,
            "router_correct": bool(active and selected == true_skill),
            "router_updates": int(self.router_updates),
            "module_updates": int(self.module_updates),
            "router_uses": int(self.router_uses),
            "correct_route_uses": int(self.correct_route_uses),
            "pre_feedback_select_steps": int(self.pre_feedback_select_steps),
        }

    def update_after_feedback(self, step: int) -> None:
        if self.task.event_type[step] != "decision":
            return
        label = strict_sign(float(self.task.stream.evaluation_target[step]))
        if label == 0:
            return
        x = int(self.task.input_sign[step]) or self.current_input
        phase = self.task.phase[step]
        if phase == "primitive_train":
            skill = self.task.true_skill[step] or self.current_skill
            if skill:
                self.module_table.setdefault(skill, {})[1 if x >= 0 else -1] = int(label)
                self.module_updates += 1
        elif phase == "route_train":
            context = self.task.context[step] or self.current_context
            for skill in SKILL_ORDER:
                predicted = self._module_lookup(skill, x)
                if predicted == label:
                    self.route_scores.setdefault(context, {}).setdefault(skill, 0.0)
                    self.route_scores[context][skill] += 1.0
                elif predicted != 0:
                    self.route_scores.setdefault(context, {}).setdefault(skill, 0.0)
                    self.route_scores[context][skill] -= 0.25
            self.router_updates += 1


def task_pressure_summary(task: RoutingTask) -> dict[str, Any]:
    decision_steps = [idx for idx, flag in enumerate(task.stream.evaluation_mask) if bool(flag)]
    by_input: dict[int, set[int]] = {-1: set(), 1: set()}
    by_context: dict[str, set[int]] = {}
    context_labels: dict[str, str] = {}
    heldout_contexts: set[str] = set()
    for step in decision_steps:
        label = strict_sign(float(task.stream.evaluation_target[step]))
        x = int(task.input_sign[step]) or strict_sign(float(task.stream.sensory[step]))
        by_input.setdefault(x, set()).add(label)
        ctx = task.context[step]
        if ctx:
            by_context.setdefault(ctx, set()).add(label)
            context_labels[ctx] = task.true_skill[step]
        if bool(task.heldout_mask[step]):
            heldout_contexts.add(ctx)
    ambiguous_inputs = [x for x, labels in by_input.items() if len(labels) > 1]
    return {
        "decision_count": len(decision_steps),
        "heldout_decision_count": int(np.sum(task.heldout_mask & task.stream.evaluation_mask)),
        "first_heldout_decision_count": int(np.sum(task.first_heldout_mask & task.stream.evaluation_mask)),
        "heldout_context_count": len(heldout_contexts),
        "heldout_contexts": sorted(heldout_contexts),
        "context_to_skill": context_labels,
        "same_current_input_opposite_labels": len(ambiguous_inputs) >= 2,
        "ambiguous_input_count": len(ambiguous_inputs),
        "max_context_gap": max([trial.input_step - trial.context_step for trial in task.trials if trial.context_step >= 0], default=0),
    }


def phase_accuracy(rows: list[dict[str, Any]], phase_prefix: str) -> float | None:
    selected = [row for row in rows if bool(row.get("target_signal_nonzero", False)) and str(row.get("phase", "")).startswith(phase_prefix)]
    if not selected:
        return None
    return float(np.mean([bool(row.get("strict_direction_correct", False)) for row in selected]))


def first_heldout_accuracy(rows: list[dict[str, Any]]) -> float | None:
    selected = [row for row in rows if bool(row.get("target_signal_nonzero", False)) and row.get("phase") == "heldout_routing_first"]
    if not selected:
        return None
    return float(np.mean([bool(row.get("strict_direction_correct", False)) for row in selected]))


def router_accuracy(rows: list[dict[str, Any]]) -> float | None:
    selected = [row for row in rows if bool(row.get("router_active", False))]
    if not selected:
        return None
    return float(np.mean([bool(row.get("router_correct", False)) for row in selected]))


def summarize_routing_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary = summarize_rows(rows)
    summary.update(
        {
            "primitive_accuracy": phase_accuracy(rows, "primitive"),
            "route_train_accuracy": phase_accuracy(rows, "route_train"),
            "heldout_accuracy": phase_accuracy(rows, "heldout_routing"),
            "first_heldout_accuracy": first_heldout_accuracy(rows),
            "router_accuracy": router_accuracy(rows),
            "router_active_steps": int(sum(1 for row in rows if bool(row.get("router_active", False)))),
            "router_correct_steps": int(sum(1 for row in rows if bool(row.get("router_correct", False)))),
            "module_updates": int(max([int(row.get("module_updates", 0) or 0) for row in rows], default=0)),
            "router_updates": int(max([int(row.get("router_updates", 0) or 0) for row in rows], default=0)),
            "router_uses": int(max([int(row.get("router_uses", 0) or 0) for row in rows], default=0)),
            "correct_route_uses": int(max([int(row.get("correct_route_uses", 0) or 0) for row in rows], default=0)),
            "pre_feedback_select_steps": int(max([int(row.get("pre_feedback_select_steps", 0) or 0) for row in rows], default=0)),
        }
    )
    return summary


def base_row(task: RoutingTask, model: str, model_family: str, seed: int, step: int, prediction: float, backend: str) -> dict[str, Any]:
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
        "context": task.context[step],
        "true_skill": task.true_skill[step],
        "heldout": bool(task.heldout_mask[step]),
        "first_heldout": bool(task.first_heldout_mask[step]),
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


def run_rule_variant(task: RoutingTask, variant: RoutingVariant, *, seed: int, args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    router = ContextRouter(mode=variant.mode, task=task, seed=seed)
    rows: list[dict[str, Any]] = []
    started = time.perf_counter()
    for step in range(task.stream.steps):
        prediction, feature = router.predict(step)
        row = base_row(task, variant.name, "routing_scaffold", seed, step, prediction, "numpy_rule")
        row.update(
            {
                "variant": variant.name,
                "variant_group": variant.group,
                "feature_mode": variant.mode,
                **feature,
            }
        )
        rows.append(row)
        router.update_after_feedback(step)
    summary = summarize_routing_rows(rows)
    summary.update(
        {
            "task": task.stream.name,
            "model": variant.name,
            "model_family": "routing_scaffold",
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


def make_config(*, seed: int, task: RoutingTask, variant: RoutingVariant, args: argparse.Namespace) -> ReefConfig:
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


def run_cra_variant(task: RoutingTask, variant: RoutingVariant, *, seed: int, args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    random.seed(seed)
    np.random.seed(seed)
    sim, backend_name = load_backend(args.backend)
    setup_backend(sim, backend_name)
    cfg = make_config(seed=seed, task=task, variant=variant, args=args)
    organism = Organism(cfg, sim, use_default_trading_bridge=False)
    router = ContextRouter(mode="contextual_router", task=task, seed=seed)
    rows: list[dict[str, Any]] = []
    started = time.perf_counter()
    try:
        organism.initialize(stream_keys=[task.stream.domain])
        for step in range(task.stream.steps):
            raw = float(task.stream.sensory[step])
            feature: dict[str, Any] = {
                "router_active": False,
                "selected_skill": "",
                "selected_context": task.context[step],
                "router_updates": router.router_updates,
                "module_updates": router.module_updates,
                "router_uses": router.router_uses,
                "correct_route_uses": router.correct_route_uses,
                "pre_feedback_select_steps": router.pre_feedback_select_steps,
            }
            observation = raw
            if variant.mode == "router_input":
                routed_prediction, feature = router.predict(step)
                if task.event_type[step] == "decision" and strict_sign(routed_prediction) != 0:
                    observation = float(args.amplitude) * float(strict_sign(routed_prediction))
            else:
                router.observe_event(step)
            metadata = {
                "tier": "5.13b",
                "variant": variant.name,
                "event_type": f"routing_{task.event_type[step]}",
                "phase": task.phase[step],
                "routing_context": task.context[step],
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
                    "router_injected_observation": float(observation),
                    "configured_readout_lr": float(cfg.learning.readout_learning_rate),
                    "configured_delayed_readout_lr": float(cfg.learning.delayed_readout_learning_rate),
                    "configured_initial_population": int(cfg.lifecycle.initial_population),
                    "configured_max_population": int(cfg.lifecycle.max_population_hard),
                    **feature,
                }
            )
            rows.append(row)
            router.update_after_feedback(step)
    finally:
        organism.shutdown()
        end_backend(sim)
    summary = summarize_routing_rows(rows)
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


def run_external_model(task: RoutingTask, model: str, *, seed: int, args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
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
    summary = summarize_routing_rows(rows)
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


def aggregate_runs(task: RoutingTask, model: str, summaries: list[dict[str, Any]]) -> dict[str, Any]:
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
        "route_train_accuracy",
        "heldout_accuracy",
        "first_heldout_accuracy",
        "router_accuracy",
        "router_active_steps",
        "router_correct_steps",
        "module_updates",
        "router_updates",
        "router_uses",
        "correct_route_uses",
        "pre_feedback_select_steps",
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


def routing_score(row: dict[str, Any]) -> float:
    heldout = float(row.get("heldout_accuracy_mean") or 0.0)
    first = float(row.get("first_heldout_accuracy_mean") or 0.0)
    route = float(row.get("router_accuracy_mean") or 0.0)
    return 0.50 * heldout + 0.35 * first + 0.15 * route


def build_comparisons(aggregates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_task_model = {(row["task"], row["model"]): row for row in aggregates}
    rows: list[dict[str, Any]] = []
    for task in sorted({row["task"] for row in aggregates}):
        candidate = by_task_model.get((task, "contextual_router_scaffold"), {})
        raw = by_task_model.get((task, "v1_8_raw_cra"), {})
        bridge = by_task_model.get((task, "cra_router_input_scaffold"), {})
        oracle = by_task_model.get((task, "oracle_router"), {})
        ablations = [row for row in aggregates if row["task"] == task and row.get("variant_group") == "routing_ablation"]
        standards = [row for row in aggregates if row["task"] == task and row.get("model_family") not in {"CRA", "routing_scaffold"}]
        best_ablation = max(ablations, key=routing_score, default={})
        best_standard = max(standards, key=lambda row: float(row.get("first_heldout_accuracy_mean") or 0.0), default={})
        pressure = candidate.get("task_pressure") or raw.get("task_pressure") or {}
        rows.append(
            {
                "task": task,
                "candidate_first_heldout_accuracy": candidate.get("first_heldout_accuracy_mean"),
                "candidate_heldout_accuracy": candidate.get("heldout_accuracy_mean"),
                "candidate_router_accuracy": candidate.get("router_accuracy_mean"),
                "candidate_router_active_steps": candidate.get("router_active_steps_sum"),
                "candidate_pre_feedback_select_steps": candidate.get("pre_feedback_select_steps_sum"),
                "candidate_module_updates": candidate.get("module_updates_max"),
                "candidate_router_updates": candidate.get("router_updates_max"),
                "v1_8_first_heldout_accuracy": raw.get("first_heldout_accuracy_mean"),
                "bridge_first_heldout_accuracy": bridge.get("first_heldout_accuracy_mean"),
                "oracle_first_heldout_accuracy": oracle.get("first_heldout_accuracy_mean"),
                "best_ablation_model": best_ablation.get("model"),
                "best_ablation_first_heldout_accuracy": best_ablation.get("first_heldout_accuracy_mean"),
                "best_ablation_router_accuracy": best_ablation.get("router_accuracy_mean"),
                "best_standard_model": best_standard.get("model"),
                "best_standard_first_heldout_accuracy": best_standard.get("first_heldout_accuracy_mean"),
                "candidate_first_delta_vs_v1_8": float(candidate.get("first_heldout_accuracy_mean") or 0.0) - float(raw.get("first_heldout_accuracy_mean") or 0.0),
                "candidate_first_delta_vs_best_ablation": float(candidate.get("first_heldout_accuracy_mean") or 0.0) - float(best_ablation.get("first_heldout_accuracy_mean") or 0.0),
                "candidate_first_delta_vs_best_standard": float(candidate.get("first_heldout_accuracy_mean") or 0.0) - float(best_standard.get("first_heldout_accuracy_mean") or 0.0),
                "same_current_input_opposite_labels": bool(pressure.get("same_current_input_opposite_labels", False)),
                "heldout_context_count": pressure.get("heldout_context_count"),
                "first_heldout_decision_count": pressure.get("first_heldout_decision_count"),
                "max_context_gap": pressure.get("max_context_gap"),
            }
        )
    return rows


def evaluate_tier(
    *,
    aggregates: list[dict[str, Any]],
    comparisons: list[dict[str, Any]],
    leakage: dict[str, Any],
    variants: list[RoutingVariant],
    models: list[str],
    args: argparse.Namespace,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    tasks = [item.strip() for item in args.tasks.split(",") if item.strip()]
    if not tasks or tasks == ["all"]:
        tasks = [item.strip() for item in DEFAULT_TASKS.split(",") if item.strip()]
    seeds = seeds_from_args(args)
    expected_runs = len(tasks) * len(seeds) * (len(variants) + len(models))
    observed_runs = sum(int(row.get("runs", 0)) for row in aggregates)
    candidate_first = [float(row.get("candidate_first_heldout_accuracy") or 0.0) for row in comparisons]
    candidate_heldout = [float(row.get("candidate_heldout_accuracy") or 0.0) for row in comparisons]
    candidate_router = [float(row.get("candidate_router_accuracy") or 0.0) for row in comparisons]
    raw_edges = [float(row.get("candidate_first_delta_vs_v1_8") or 0.0) for row in comparisons]
    ablation_edges = [float(row.get("candidate_first_delta_vs_best_ablation") or 0.0) for row in comparisons]
    standard_edges = [float(row.get("candidate_first_delta_vs_best_standard") or 0.0) for row in comparisons]
    active_steps = sum(float(row.get("candidate_router_active_steps") or 0.0) for row in comparisons)
    pre_feedback_steps = sum(float(row.get("candidate_pre_feedback_select_steps") or 0.0) for row in comparisons)
    module_updates = sum(float(row.get("candidate_module_updates") or 0.0) for row in comparisons)
    router_updates = sum(float(row.get("candidate_router_updates") or 0.0) for row in comparisons)
    pressure_ok = all(
        bool(row.get("same_current_input_opposite_labels"))
        and int(row.get("heldout_context_count") or 0) >= 4
        and int(row.get("max_context_gap") or 0) > int(args.feature_history)
        for row in comparisons
    )
    base_criteria = [
        criterion("full variant/baseline/task/seed matrix completed", observed_runs, "==", expected_runs, observed_runs == expected_runs),
        criterion("feedback timing has no leakage violations", leakage.get("feedback_due_violations"), "==", 0, int(leakage.get("feedback_due_violations", 0)) == 0),
        criterion("tasks require context routing beyond current input/history", pressure_ok, "==", True, pressure_ok),
        criterion("candidate learned primitive modules", module_updates, ">", 0, module_updates > 0),
        criterion("candidate learned context router", router_updates, ">", 0, router_updates > 0),
        criterion("candidate selects routes before feedback", pre_feedback_steps, ">", 0, pre_feedback_steps > 0),
        criterion("candidate router activates on held-out trials", active_steps, ">", 0, active_steps > 0),
    ]
    science_criteria = [
        criterion(
            "candidate reaches minimum first-heldout routing accuracy",
            min(candidate_first) if candidate_first else None,
            ">=",
            args.min_candidate_first_accuracy,
            bool(candidate_first) and min(candidate_first) >= args.min_candidate_first_accuracy,
        ),
        criterion(
            "candidate reaches minimum total heldout routing accuracy",
            min(candidate_heldout) if candidate_heldout else None,
            ">=",
            args.min_candidate_heldout_accuracy,
            bool(candidate_heldout) and min(candidate_heldout) >= args.min_candidate_heldout_accuracy,
        ),
        criterion(
            "candidate route selection is correct",
            min(candidate_router) if candidate_router else None,
            ">=",
            args.min_candidate_router_accuracy,
            bool(candidate_router) and min(candidate_router) >= args.min_candidate_router_accuracy,
        ),
        criterion(
            "candidate improves over raw v1.8 on first-heldout routing",
            min(raw_edges) if raw_edges else None,
            ">=",
            args.min_candidate_edge_vs_v1_8,
            bool(raw_edges) and min(raw_edges) >= args.min_candidate_edge_vs_v1_8,
        ),
        criterion(
            "routing shams are worse than candidate",
            min(ablation_edges) if ablation_edges else None,
            ">=",
            args.min_candidate_edge_vs_ablation,
            bool(ablation_edges) and min(ablation_edges) >= args.min_candidate_edge_vs_ablation,
        ),
        criterion(
            "candidate beats best selected standard baseline on first-heldout routing",
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
        "candidate_router_active_steps_sum": active_steps,
        "candidate_pre_feedback_select_steps_sum": pre_feedback_steps,
        "candidate_module_updates_sum": module_updates,
        "candidate_router_updates_sum": router_updates,
        "claim_boundary": "Software diagnostic only: explicit host-side context router scaffold, not native/internal CRA routing, hardware routing, planning, language, or AGI evidence.",
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
        "first_heldout_accuracy_mean",
        "router_accuracy_mean",
        "primitive_accuracy_mean",
        "route_train_accuracy_mean",
        "prediction_target_corr_mean",
        "runtime_seconds_mean",
        "router_active_steps_sum",
        "router_correct_steps_sum",
        "module_updates_max",
        "router_updates_max",
        "pre_feedback_select_steps_sum",
    ]
    return [{field: row.get(field) for field in fields} for row in aggregates]


def build_fairness_contract(args: argparse.Namespace, variants: list[RoutingVariant], models: list[str]) -> dict[str, Any]:
    return {
        "tier": TIER,
        "generated_at_utc": utc_now(),
        "claim_boundary": "Tier 5.13b is a software routing diagnostic; it is not native/internal CRA routing or hardware evidence.",
        "tasks": [item.strip() for item in args.tasks.split(",") if item.strip()],
        "seeds": seeds_from_args(args),
        "variants": [variant.__dict__ for variant in variants],
        "models": models,
        "fairness_rules": [
            "All candidates and baselines see the same event stream, context cues, input signs, decision targets, and feedback timing.",
            "Held-out routing decisions are scored before feedback updates.",
            "The context cue is separated from the decision by more steps than the selected online baseline history window.",
            "Router shams keep comparable module tables but destroy routing, reset routing, or select random/wrong modules.",
            "Oracle routing is reported only as an upper bound and cannot be promoted as CRA evidence.",
        ],
        "leakage_rules": [
            "Feedback due step must never precede the scored decision step.",
            "Candidate route selection telemetry is logged before feedback is applied for that decision.",
        ],
    }


def plot_comparisons(path: Path, comparisons: list[dict[str, Any]]) -> None:
    if plt is None:
        path.with_suffix(".txt").write_text(f"matplotlib unavailable: {MATPLOTLIB_ERROR}\n", encoding="utf-8")
        return
    tasks = [row["task"] for row in comparisons]
    candidate = [float(row.get("candidate_first_heldout_accuracy") or 0.0) for row in comparisons]
    ablation = [float(row.get("best_ablation_first_heldout_accuracy") or 0.0) for row in comparisons]
    baseline = [float(row.get("best_standard_first_heldout_accuracy") or 0.0) for row in comparisons]
    raw = [float(row.get("v1_8_first_heldout_accuracy") or 0.0) for row in comparisons]
    x = np.arange(len(tasks))
    width = 0.2
    fig, ax = plt.subplots(figsize=(11, 5.5))
    ax.bar(x - 1.5 * width, candidate, width, label="router scaffold")
    ax.bar(x - 0.5 * width, ablation, width, label="best routing sham")
    ax.bar(x + 0.5 * width, baseline, width, label="best selected baseline")
    ax.bar(x + 1.5 * width, raw, width, label="raw v1.8")
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("first-heldout routing accuracy")
    ax.set_title("Tier 5.13b module routing / contextual gating")
    ax.set_xticks(x)
    ax.set_xticklabels(tasks, rotation=18, ha="right")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def run_tier(args: argparse.Namespace, output_dir: Path) -> dict[str, Any]:
    variants = parse_variants(args.variants)
    models = parse_models(args.models)
    seeds = seeds_from_args(args)
    output_dir.mkdir(parents=True, exist_ok=True)
    all_rows: list[dict[str, Any]] = []
    summaries_by_key: dict[tuple[str, str], list[dict[str, Any]]] = {}
    tasks_by_name: dict[str, RoutingTask] = {}
    rows_by_cell_seed: dict[tuple[str, str, int], list[dict[str, Any]]] = {}
    artifacts: dict[str, str] = {}

    for seed in seeds:
        for task in build_tasks(args, seed):
            tasks_by_name.setdefault(task.stream.name, task)
            for variant in variants:
                print(f"[tier5.13b] task={task.stream.name} variant={variant.name} seed={seed}", flush=True)
                if variant.runner == "cra":
                    rows, summary = run_cra_variant(task, variant, seed=seed, args=args)
                else:
                    rows, summary = run_rule_variant(task, variant, seed=seed, args=args)
                all_rows.extend(rows)
                summaries_by_key.setdefault((task.stream.name, variant.name), []).append(summary)
                rows_by_cell_seed[(task.stream.name, variant.name, seed)] = rows
                ts_path = output_dir / f"{task.stream.name}_{variant.name}_seed{seed}_timeseries.csv"
                write_csv(ts_path, rows)
                artifacts[f"{task.stream.name}_{variant.name}_seed{seed}_timeseries_csv"] = str(ts_path)
            for model in models:
                print(f"[tier5.13b] task={task.stream.name} model={model} seed={seed}", flush=True)
                rows, summary = run_external_model(task, model, seed=seed, args=args)
                all_rows.extend(rows)
                summaries_by_key.setdefault((task.stream.name, model), []).append(summary)
                rows_by_cell_seed[(task.stream.name, model, seed)] = rows
                ts_path = output_dir / f"{task.stream.name}_{model}_seed{seed}_timeseries.csv"
                write_csv(ts_path, rows)
                artifacts[f"{task.stream.name}_{model}_seed{seed}_timeseries_csv"] = str(ts_path)

    aggregates = [aggregate_runs(tasks_by_name[task_name], model, summaries) for (task_name, model), summaries in sorted(summaries_by_key.items())]
    comparisons = build_comparisons(aggregates)
    leakage = leakage_summary(rows_by_cell_seed)
    criteria, run_summary = evaluate_tier(aggregates=aggregates, comparisons=comparisons, leakage=leakage, variants=variants, models=models, args=args)
    status, failure_reason = pass_fail(criteria)

    summary_csv = output_dir / "tier5_13b_summary.csv"
    comparisons_csv = output_dir / "tier5_13b_comparisons.csv"
    fairness_json = output_dir / "tier5_13b_fairness_contract.json"
    plot_png = output_dir / "tier5_13b_routing.png"
    report_md = output_dir / "tier5_13b_report.md"
    manifest_json = output_dir / "tier5_13b_results.json"
    write_csv(summary_csv, aggregate_csv_rows(aggregates))
    write_csv(comparisons_csv, comparisons)
    write_json(fairness_json, build_fairness_contract(args, variants, models))
    plot_comparisons(plot_png, comparisons)

    artifacts.update(
        {
            "summary_csv": str(summary_csv),
            "comparisons_csv": str(comparisons_csv),
            "fairness_contract_json": str(fairness_json),
            "routing_png": str(plot_png),
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
        "summary": run_summary,
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


def write_latest(output_dir: Path, manifest_json: Path, report_md: Path, summary_csv: Path, status: str) -> None:
    latest = ROOT / "controlled_test_output" / "tier5_13b_latest_manifest.json"
    write_json(
        latest,
        {
            "tier": TIER,
            "status": status,
            "canonical": False,
            "claim": "Latest Tier 5.13b module-routing diagnostic; passing authorizes internal CRA routing/gating work only.",
            "generated_at_utc": utc_now(),
            "output_dir": str(output_dir),
            "manifest": str(manifest_json),
            "report": str(report_md),
            "summary_csv": str(summary_csv),
        },
    )


def write_report(path: Path, result: dict[str, Any], args: argparse.Namespace, output_dir: Path) -> None:
    comparisons = result["comparisons"]
    aggregates = result["aggregates"]
    criteria = result["criteria"]
    lines: list[str] = []
    lines.extend(
        [
            "# Tier 5.13b Module Routing / Contextual Gating Diagnostic Findings",
            "",
            f"- Generated: `{result['generated_at_utc']}`",
            f"- Status: **{result['status'].upper()}**",
            f"- Backend for CRA comparators: `{args.backend}`",
            f"- Steps: `{args.steps}`",
            f"- Seeds: `{', '.join(str(seed) for seed in seeds_from_args(args))}`",
            f"- Tasks: `{args.tasks}`",
            f"- Variants: `{args.variants}`",
            f"- Selected standard baselines: `{args.models}`",
            f"- Smoke mode: `{args.smoke}`",
            f"- Output directory: `{output_dir}`",
            "",
            "Tier 5.13b tests contextual module routing: primitive modules are learned first, context-to-module routing is learned next, and held-out delayed-context trials require selecting the right module before feedback.",
            "",
            "## Claim Boundary",
            "",
            "- This is software diagnostic evidence, not hardware evidence.",
            "- The candidate is an explicit host-side contextual router scaffold, not native/internal CRA routing yet.",
            "- This does not prove language reasoning, long-horizon planning, AGI, or on-chip routing.",
            "- A pass authorizes internal CRA routing/gating implementation; it does not freeze a new baseline by itself.",
            "",
            "## Task Comparisons",
            "",
            "| Task | Candidate first | Candidate heldout | Router acc | v1.8 first | Bridge first | Best sham | Sham first | Best baseline | Baseline first | Edge vs v1.8 | Edge vs sham | Edge vs baseline | Updates | Route uses |",
            "| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in comparisons:
        lines.append(
            "| {task} | {candidate_first_heldout_accuracy} | {candidate_heldout_accuracy} | {candidate_router_accuracy} | {v1_8_first_heldout_accuracy} | {bridge_first_heldout_accuracy} | `{best_ablation_model}` | {best_ablation_first_heldout_accuracy} | `{best_standard_model}` | {best_standard_first_heldout_accuracy} | {candidate_first_delta_vs_v1_8} | {candidate_first_delta_vs_best_ablation} | {candidate_first_delta_vs_best_standard} | {candidate_router_updates} | {candidate_pre_feedback_select_steps} |".format(
                **{k: markdown_value(v) for k, v in row.items()}
            )
        )
    lines.extend(
        [
            "",
            "## Aggregate Matrix",
            "",
            "| Task | Model | Family | Group | All acc | Heldout acc | First heldout | Router acc | Runtime s |",
            "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in sorted(aggregates, key=lambda r: (r["task"], str(r.get("variant_group") or ""), r["model"])):
        lines.append(
            f"| {row['task']} | `{row['model']}` | {row.get('model_family') or ''} | {row.get('variant_group') or ''} | {markdown_value(row.get('all_accuracy_mean'))} | {markdown_value(row.get('heldout_accuracy_mean'))} | {markdown_value(row.get('first_heldout_accuracy_mean'))} | {markdown_value(row.get('router_accuracy_mean'))} | {markdown_value(row.get('runtime_seconds_mean'))} |"
        )
    lines.extend(["", "## Criteria", "", "| Criterion | Value | Rule | Pass | Note |", "| --- | --- | --- | --- | --- |"])
    for item in criteria:
        lines.append(
            f"| {item['name']} | {markdown_value(item.get('value'))} | {item.get('operator')} {markdown_value(item.get('threshold'))} | {'yes' if item.get('passed') else 'no'} | {item.get('note', '')} |"
        )
    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            "- `tier5_13b_results.json`: machine-readable manifest.",
            "- `tier5_13b_report.md`: human findings and claim boundary.",
            "- `tier5_13b_summary.csv`: aggregate task/model metrics.",
            "- `tier5_13b_comparisons.csv`: candidate-vs-sham/baseline table.",
            "- `tier5_13b_fairness_contract.json`: predeclared comparison/leakage rules.",
            "- `tier5_13b_routing.png`: first-heldout routing plot.",
            "- `*_timeseries.csv`: per-task/per-model/per-seed traces.",
            "",
            "![routing](tier5_13b_routing.png)",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parent = build_tier5_1_parser()
    parser = argparse.ArgumentParser(description=TIER, parents=[parent], conflict_handler="resolve")
    parser.set_defaults(backend="mock", tasks=DEFAULT_TASKS, steps=720, seed_count=3, models=DEFAULT_MODELS)
    parser.add_argument("--variants", default=DEFAULT_VARIANTS)
    parser.add_argument("--amplitude", type=float, default=0.01)
    parser.add_argument("--dt-seconds", type=float, default=60.0)
    parser.add_argument("--cra-population-size", type=int, default=8)
    parser.add_argument("--cra-readout-lr", type=float, default=0.10)
    parser.add_argument("--cra-delayed-readout-lr", type=float, default=0.20)
    parser.add_argument("--message-passing-steps", type=int, default=1)
    parser.add_argument("--message-context-gain", type=float, default=0.025)
    parser.add_argument("--message-prediction-mix", type=float, default=0.35)
    parser.add_argument("--primitive-repeats", type=int, default=4)
    parser.add_argument("--route-train-repeats", type=int, default=4)
    parser.add_argument("--heldout-repeats", type=int, default=5)
    parser.add_argument("--routing-gap", type=int, default=10)
    parser.add_argument("--min-candidate-first-accuracy", type=float, default=0.95)
    parser.add_argument("--min-candidate-heldout-accuracy", type=float, default=0.95)
    parser.add_argument("--min-candidate-router-accuracy", type=float, default=0.95)
    parser.add_argument("--min-candidate-edge-vs-v1-8", type=float, default=0.20)
    parser.add_argument("--min-candidate-edge-vs-ablation", type=float, default=0.20)
    parser.add_argument("--min-candidate-edge-vs-standard", type=float, default=0.10)
    parser.add_argument("--smoke", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_dir = ROOT / "controlled_test_output" / f"tier5_13b_{stamp}"
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
            "command": " ".join(sys.argv),
        }
        manifest = output_dir / "tier5_13b_results.json"
        report = output_dir / "tier5_13b_report.md"
        write_json(manifest, failure)
        report.write_text(
            "# Tier 5.13b Module Routing / Contextual Gating Diagnostic Findings\n\n"
            f"- Generated: `{failure['generated_at_utc']}`\n"
            "- Status: **BLOCKED**\n\n"
            f"Failure: {exc}\n",
            encoding="utf-8",
        )
        write_latest(output_dir, manifest, report, output_dir / "tier5_13b_summary.csv", "blocked")
        print(json.dumps(failure, indent=2), flush=True)
        return 1
    print(
        json.dumps(
            {
                "status": result["status"],
                "output_dir": result["output_dir"],
                "manifest": str(output_dir / "tier5_13b_results.json"),
                "report": str(output_dir / "tier5_13b_report.md"),
                "summary_csv": str(output_dir / "tier5_13b_summary.csv"),
                "comparisons_csv": str(output_dir / "tier5_13b_comparisons.csv"),
                "fairness_contract_json": str(output_dir / "tier5_13b_fairness_contract.json"),
                "failure_reason": result.get("failure_reason", ""),
            },
            indent=2,
        ),
        flush=True,
    )
    return 0 if result["status"] == "pass" or not args.stop_on_fail else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
