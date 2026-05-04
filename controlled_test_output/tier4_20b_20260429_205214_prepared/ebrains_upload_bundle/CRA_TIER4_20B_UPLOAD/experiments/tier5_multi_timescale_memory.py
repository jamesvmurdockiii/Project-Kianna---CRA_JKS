#!/usr/bin/env python3
"""Tier 5.10 multi-timescale memory / recurrent-regime diagnostic.

Tier 5.9 showed that macro eligibility traces are not yet earned. Tier 5.10
asks the next architectural question: does CRA retain or rapidly reacquire old
regimes when they return, and do existing fast/slow/structural memory knobs
help beyond the frozen v1.4 baseline?

This is intentionally a software diagnostic tier. A pass here would authorize
compact regression and a sharper memory mechanism design; it is not hardware
evidence and not a sleep/replay claim.
"""

from __future__ import annotations

import argparse
import json
import math
import os
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

from tier2_learning import (  # noqa: E402
    DEFAULT_AMPLITUDE,
    criterion,
    markdown_value,
    pass_fail,
    safe_corr,
    write_csv,
    write_json,
)
from tier4_scaling import mean, min_value, seeds_from_args, stdev  # noqa: E402
from tier5_external_baselines import (  # noqa: E402
    LEARNER_FACTORIES,
    TaskStream,
    TestResult,
    build_parser as build_tier5_1_parser,
    parse_models,
    recovery_steps,
    run_baseline_case,
)
from tier5_macro_eligibility import (  # noqa: E402
    VariantSpec,
    computed_horizon,
    json_safe,
    run_cra_variant,
)


TIER = "Tier 5.10 - Multi-Timescale Memory And Forgetting Diagnostic"
DEFAULT_TASKS = "aba_recurrence,abca_recurrence,hidden_regime_switching"
DEFAULT_MODELS = "sign_persistence,online_perceptron,online_logistic_regression,echo_state_network,stdp_only_snn"
DEFAULT_VARIANTS = "v1_4_pending_horizon,multi_timescale_memory,no_slow_memory,no_structural_memory,no_bocpd_unlock,overrigid_memory"
EPS = 1e-12


@dataclass(frozen=True)
class Phase:
    name: str
    start: int
    end: int
    rule: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def strict_sign_value(value: float) -> int:
    if value > 0.0:
        return 1
    if value < 0.0:
        return -1
    return 0


def phase_for_step(phases: list[Phase], step: int) -> str:
    for phase in phases:
        if phase.start <= step < phase.end:
            return phase.name
    return phases[-1].name if phases else "unknown"


def phase_payload(phases: list[Phase]) -> list[dict[str, Any]]:
    return [
        {"name": phase.name, "start": phase.start, "end": phase.end, "rule": phase.rule}
        for phase in phases
    ]


def rule_label(rule: str, cue_sign: float, previous_cue_sign: float) -> float:
    if rule == "identity":
        return cue_sign
    if rule == "invert":
        return -cue_sign
    if rule == "constant_positive":
        return 1.0
    if rule == "previous":
        return previous_cue_sign if previous_cue_sign != 0.0 else cue_sign
    raise ValueError(f"unknown recurrence rule: {rule}")


def recurrent_rule_task(
    *,
    name: str,
    display_name: str,
    rules: list[tuple[str, str]],
    steps: int,
    amplitude: float,
    seed: int,
    delay: int,
    period: int,
    noise_prob: float,
    sensory_noise_fraction: float,
) -> TaskStream:
    rng = np.random.default_rng(seed)
    sensory = np.zeros(steps, dtype=float)
    current_target = np.zeros(steps, dtype=float)
    evaluation_target = np.zeros(steps, dtype=float)
    evaluation_mask = np.zeros(steps, dtype=bool)
    feedback_due = np.full(steps, -1, dtype=int)

    phase_len = max(period * 2, steps // len(rules))
    phases: list[Phase] = []
    cursor = 0
    for idx, (phase_name, rule) in enumerate(rules):
        start = cursor
        end = steps if idx == len(rules) - 1 else min(steps, cursor + phase_len)
        phases.append(Phase(name=phase_name, start=start, end=end, rule=rule))
        cursor = end

    previous_cue = 1.0
    noisy_trials = 0
    trials = 0
    for start in range(0, steps - delay, period):
        phase = next(p for p in phases if p.start <= start < p.end)
        cue_sign = 1.0 if rng.random() < 0.5 else -1.0
        label = rule_label(phase.rule, cue_sign, previous_cue)
        previous_cue = cue_sign
        if rng.random() < noise_prob:
            label *= -1.0
            noisy_trials += 1
        sensory[start] = amplitude * cue_sign + rng.normal(0.0, sensory_noise_fraction * amplitude)
        current_target[start + delay] = amplitude * label
        evaluation_target[start] = amplitude * label
        evaluation_mask[start] = True
        feedback_due[start] = start + delay
        trials += 1

    return TaskStream(
        name=name,
        display_name=display_name,
        domain=name,
        steps=steps,
        sensory=sensory,
        current_target=current_target,
        evaluation_target=evaluation_target,
        evaluation_mask=evaluation_mask,
        feedback_due_step=feedback_due,
        switch_steps=[p.start for p in phases],
        metadata={
            "task_kind": name,
            "delay": delay,
            "period": period,
            "trials": trials,
            "noise_prob": noise_prob,
            "noisy_trials": noisy_trials,
            "phases": phase_payload(phases),
            "return_phase": phases[-1].name,
            "first_phase": phases[0].name,
        },
    )


def aba_recurrence_task(*, steps: int, amplitude: float, seed: int, args: argparse.Namespace) -> TaskStream:
    return recurrent_rule_task(
        name="aba_recurrence",
        display_name="A-B-A Regime Recurrence",
        rules=[("A0", "identity"), ("B", "invert"), ("A_return", "identity")],
        steps=steps,
        amplitude=amplitude,
        seed=seed + 5101,
        delay=int(args.memory_delay),
        period=int(args.memory_period),
        noise_prob=float(args.memory_noise_prob),
        sensory_noise_fraction=float(args.memory_sensory_noise_fraction),
    )


def abca_recurrence_task(*, steps: int, amplitude: float, seed: int, args: argparse.Namespace) -> TaskStream:
    return recurrent_rule_task(
        name="abca_recurrence",
        display_name="A-B-C-A Regime Recurrence",
        rules=[
            ("A0", "identity"),
            ("B", "invert"),
            ("C", "constant_positive"),
            ("A_return", "identity"),
        ],
        steps=steps,
        amplitude=amplitude,
        seed=seed + 5102,
        delay=int(args.memory_delay),
        period=int(args.memory_period),
        noise_prob=float(args.memory_noise_prob),
        sensory_noise_fraction=float(args.memory_sensory_noise_fraction),
    )


def hidden_regime_switching_task(*, steps: int, amplitude: float, seed: int, args: argparse.Namespace) -> TaskStream:
    rng = np.random.default_rng(seed + 5103)
    rules: list[tuple[str, str]] = []
    cursor = 0
    idx = 0
    rule_names = ["identity", "invert", "identity", "invert", "identity"]
    while cursor < steps:
        phase_len = int(rng.integers(args.hidden_min_phase, args.hidden_max_phase + 1))
        rules.append((f"R{idx}_{rule_names[idx % len(rule_names)]}", rule_names[idx % len(rule_names)]))
        cursor += phase_len
        idx += 1
        if len(rules) >= 5:
            break
    # The recurrent-rule builder uses equal phase lengths; for this diagnostic
    # the "hidden" part is that there is no explicit switch cue, not random
    # phase sizing. Randomizing the number of phases per seed is enough to avoid
    # memorizing a fixed switch count.
    return recurrent_rule_task(
        name="hidden_regime_switching",
        display_name="Hidden Regime Switching",
        rules=rules,
        steps=steps,
        amplitude=amplitude,
        seed=seed + 5104,
        delay=int(args.memory_delay),
        period=int(args.memory_period),
        noise_prob=max(float(args.memory_noise_prob), float(args.hidden_noise_prob)),
        sensory_noise_fraction=float(args.memory_sensory_noise_fraction),
    )


def build_tasks(args: argparse.Namespace, seed: int) -> list[TaskStream]:
    factories = {
        "aba_recurrence": aba_recurrence_task,
        "abca_recurrence": abca_recurrence_task,
        "hidden_regime_switching": hidden_regime_switching_task,
    }
    task_names = [item.strip() for item in args.tasks.split(",") if item.strip()]
    if not task_names or task_names == ["all"]:
        task_names = list(factories)
    missing = [name for name in task_names if name not in factories]
    if missing:
        raise argparse.ArgumentTypeError(f"unknown Tier 5.10 tasks: {', '.join(missing)}")
    return [factories[name](steps=args.steps, amplitude=args.amplitude, seed=seed, args=args) for name in task_names]


VARIANTS: tuple[VariantSpec, ...] = (
    VariantSpec(
        name="v1_4_pending_horizon",
        group="frozen_baseline",
        hypothesis="Frozen v1.4 baseline: PendingHorizon delayed credit and default readout/consolidation dynamics.",
        overrides={
            "learning.delayed_readout_learning_rate": 0.20,
            "learning.macro_eligibility_enabled": False,
        },
    ),
    VariantSpec(
        name="multi_timescale_memory",
        group="candidate",
        hypothesis="Proxy fast/slow/structural memory: lower readout decay, slower accuracy EMA, moderate calcification, and gentler negative surprise.",
        overrides={
            "learning.delayed_readout_learning_rate": 0.20,
            "learning.macro_eligibility_enabled": False,
            "learning.readout_weight_decay": 0.0002,
            "learning.readout_negative_surprise_multiplier": 1.5,
            "learning.directional_accuracy_ema_alpha": 0.006,
            "learning.calcification_rate": 0.003,
            "learning.plasticity_bocpd_weight": 1.0,
        },
    ),
    VariantSpec(
        name="no_slow_memory",
        group="memory_ablation",
        hypothesis="Control: erase slow retention pressure by increasing readout decay and shortening accuracy memory.",
        overrides={
            "learning.delayed_readout_learning_rate": 0.20,
            "learning.macro_eligibility_enabled": False,
            "learning.readout_weight_decay": 0.006,
            "learning.readout_negative_surprise_multiplier": 1.5,
            "learning.directional_accuracy_ema_alpha": 0.05,
            "learning.calcification_rate": 0.003,
            "learning.plasticity_bocpd_weight": 1.0,
        },
    ),
    VariantSpec(
        name="no_structural_memory",
        group="memory_ablation",
        hypothesis="Control: remove structural/calcification consolidation while leaving fast readout adaptation intact.",
        overrides={
            "learning.delayed_readout_learning_rate": 0.20,
            "learning.macro_eligibility_enabled": False,
            "learning.readout_weight_decay": 0.0002,
            "learning.readout_negative_surprise_multiplier": 1.5,
            "learning.directional_accuracy_ema_alpha": 0.006,
            "learning.calcification_rate": 0.0,
            "learning.plasticity_bocpd_weight": 1.0,
            "lifecycle.enable_structural_plasticity": False,
        },
    ),
    VariantSpec(
        name="no_bocpd_unlock",
        group="memory_ablation",
        hypothesis="Control: remove changepoint-driven plasticity-temperature unlocking.",
        overrides={
            "learning.delayed_readout_learning_rate": 0.20,
            "learning.macro_eligibility_enabled": False,
            "learning.readout_weight_decay": 0.0002,
            "learning.readout_negative_surprise_multiplier": 1.5,
            "learning.directional_accuracy_ema_alpha": 0.006,
            "learning.calcification_rate": 0.003,
            "learning.plasticity_bocpd_weight": 0.0,
        },
    ),
    VariantSpec(
        name="overrigid_memory",
        group="memory_ablation",
        hypothesis="Control: over-protect memory to test the adaptation/retention tradeoff.",
        overrides={
            "learning.delayed_readout_learning_rate": 0.20,
            "learning.macro_eligibility_enabled": False,
            "learning.readout_weight_decay": 0.0,
            "learning.readout_negative_surprise_multiplier": 0.75,
            "learning.directional_accuracy_ema_alpha": 0.003,
            "learning.calcification_rate": 0.01,
            "learning.plasticity_bocpd_weight": 0.25,
        },
    ),
)


def parse_variants(raw: str) -> list[VariantSpec]:
    names = [item.strip() for item in raw.split(",") if item.strip()]
    if not names or names == ["all"]:
        return list(VARIANTS)
    by_name = {variant.name: variant for variant in VARIANTS}
    missing = [name for name in names if name not in by_name]
    if missing:
        raise argparse.ArgumentTypeError(f"unknown Tier 5.10 variants: {', '.join(missing)}")
    selected = [by_name[name] for name in names]
    required = {"v1_4_pending_horizon", "multi_timescale_memory"}
    present = {variant.name for variant in selected}
    if not required.issubset(present):
        raise argparse.ArgumentTypeError("Tier 5.10 requires v1_4_pending_horizon and multi_timescale_memory")
    return selected


def annotate_phases(rows: list[dict[str, Any]], task: TaskStream) -> None:
    phases = [
        Phase(
            name=str(item["name"]),
            start=int(item["start"]),
            end=int(item["end"]),
            rule=str(item["rule"]),
        )
        for item in task.metadata.get("phases", [])
    ]
    for row in rows:
        row["phase"] = phase_for_step(phases, int(row.get("step", 0)))


def accuracy(rows: list[dict[str, Any]]) -> float | None:
    eval_rows = [row for row in rows if bool(row.get("target_signal_nonzero", False))]
    if not eval_rows:
        return None
    return float(np.mean([bool(row.get("strict_direction_correct", False)) for row in eval_rows]))


def corr(rows: list[dict[str, Any]]) -> float | None:
    eval_rows = [row for row in rows if bool(row.get("target_signal_nonzero", False))]
    if len(eval_rows) < 2:
        return None
    return safe_corr(
        [float(row.get("colony_prediction", 0.0) or 0.0) for row in eval_rows],
        [float(row.get("target_signal_horizon", 0.0) or 0.0) for row in eval_rows],
    )


def recurrence_summary(rows: list[dict[str, Any]], task: TaskStream, args: argparse.Namespace) -> dict[str, Any]:
    phases = [str(item["name"]) for item in task.metadata.get("phases", [])]
    first_phase = str(task.metadata.get("first_phase", phases[0] if phases else ""))
    return_phase = str(task.metadata.get("return_phase", phases[-1] if phases else ""))
    by_phase: dict[str, list[dict[str, Any]]] = {
        phase: [row for row in rows if row.get("phase") == phase]
        for phase in phases
    }
    first_rows = [row for row in by_phase.get(first_phase, []) if bool(row.get("target_signal_nonzero", False))]
    return_rows = [row for row in by_phase.get(return_phase, []) if bool(row.get("target_signal_nonzero", False))]
    n = int(args.reacquisition_trials)
    first_early = first_rows[:n]
    return_early = return_rows[:n]
    phase_acc = {f"phase_{phase}_accuracy": accuracy(by_phase.get(phase, [])) for phase in phases}
    first_acc = accuracy(first_rows)
    return_acc = accuracy(return_rows)
    first_early_acc = accuracy(first_early)
    return_early_acc = accuracy(return_early)
    return_corr = corr(return_rows)
    return {
        **phase_acc,
        "first_regime_accuracy": first_acc,
        "return_regime_accuracy": return_acc,
        "first_regime_early_accuracy": first_early_acc,
        "return_regime_early_accuracy": return_early_acc,
        "return_regime_corr": return_corr,
        "old_regime_retention_delta": (
            None if first_acc is None or return_acc is None else float(return_acc - first_acc)
        ),
        "old_regime_reacquisition_delta": (
            None if first_early_acc is None or return_early_acc is None else float(return_early_acc - first_early_acc)
        ),
        "first_regime_eval_count": len(first_rows),
        "return_regime_eval_count": len(return_rows),
    }


def run_cra_memory_variant(
    task: TaskStream,
    *,
    seed: int,
    variant: VariantSpec,
    args: argparse.Namespace,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows, summary = run_cra_variant(task, seed=seed, variant=variant, args=args)
    annotate_phases(rows, task)
    for row in rows:
        row["tier"] = "5.10"
    summary.update(recurrence_summary(rows, task, args))
    summary["configured_horizon_bars"] = computed_horizon(task)
    return rows, summary


def run_baseline_memory_case(
    task: TaskStream,
    model: str,
    *,
    seed: int,
    args: argparse.Namespace,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows, summary = run_baseline_case(task, model, seed=seed, args=args)
    annotate_phases(rows, task)
    for row in rows:
        row["tier"] = "5.10"
    summary.update(recurrence_summary(rows, task, args))
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
    return {
        "checked_feedback_rows": checked,
        "feedback_due_violations": len(violations),
        "example_violations": violations[:10],
    }


def aggregate_runs(
    *,
    task: TaskStream,
    model: str,
    family: str,
    group: str | None,
    summaries: list[dict[str, Any]],
    rows_by_seed: dict[int, list[dict[str, Any]]],
    args: argparse.Namespace,
) -> dict[str, Any]:
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
        "first_regime_accuracy",
        "return_regime_accuracy",
        "first_regime_early_accuracy",
        "return_regime_early_accuracy",
        "return_regime_corr",
        "old_regime_retention_delta",
        "old_regime_reacquisition_delta",
        "first_regime_eval_count",
        "return_regime_eval_count",
    ]
    aggregate: dict[str, Any] = {
        "task": task.name,
        "display_name": task.display_name,
        "domain": task.domain,
        "model": model,
        "model_family": family,
        "variant_group": group,
        "runs": len(summaries),
        "seeds": [s.get("seed") for s in summaries],
        "steps": task.steps,
        "task_metadata": task.metadata,
    }
    for key in keys:
        vals = [s.get(key) for s in summaries]
        aggregate[f"{key}_mean"] = mean(vals)
        aggregate[f"{key}_std"] = stdev(vals)
        aggregate[f"{key}_min"] = min_value(vals)
        valid = [float(v) for v in vals if v is not None]
        aggregate[f"{key}_max"] = max(valid) if valid else None
        aggregate[f"{key}_sum"] = float(sum(valid)) if valid else None
    if task.switch_steps:
        per_seed_recovery = []
        for rows in rows_by_seed.values():
            per_seed_recovery.extend(
                recovery_steps(
                    rows,
                    task.switch_steps,
                    window_trials=args.recovery_window_trials,
                    threshold=args.recovery_accuracy_threshold,
                    steps=task.steps,
                )
            )
        aggregate["mean_recovery_steps"] = mean(per_seed_recovery)
        aggregate["max_recovery_steps"] = max(per_seed_recovery) if per_seed_recovery else None
    else:
        aggregate["mean_recovery_steps"] = None
        aggregate["max_recovery_steps"] = None
    return aggregate


def composite_score(row: dict[str, Any]) -> float:
    return_acc = float(row.get("return_regime_accuracy_mean") or 0.0)
    reacq = float(row.get("old_regime_reacquisition_delta_mean") or 0.0)
    corr_value = abs(float(row.get("return_regime_corr_mean") or 0.0))
    recovery = row.get("mean_recovery_steps")
    recovery_bonus = 0.0 if recovery is None else -0.002 * float(recovery)
    return return_acc + 0.35 * reacq + 0.15 * corr_value + recovery_bonus


def build_comparisons(aggregates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    by_task_model = {(row["task"], row["model"]): row for row in aggregates}
    for task in sorted({row["task"] for row in aggregates}):
        baseline = by_task_model.get((task, "v1_4_pending_horizon"), {})
        candidate = by_task_model.get((task, "multi_timescale_memory"), {})
        ablations = [
            row
            for row in aggregates
            if row["task"] == task and row.get("variant_group") == "memory_ablation"
        ]
        externals = [
            row
            for row in aggregates
            if row["task"] == task and row.get("model_family") != "CRA"
        ]
        best_ablation = max(ablations, key=composite_score, default={})
        external_values = [float(row.get("return_regime_accuracy_mean") or 0.0) for row in externals]
        best_external = max(externals, key=lambda row: float(row.get("return_regime_accuracy_mean") or 0.0), default={})
        recovery_delta = None
        if baseline.get("mean_recovery_steps") is not None and candidate.get("mean_recovery_steps") is not None:
            recovery_delta = float(baseline["mean_recovery_steps"]) - float(candidate["mean_recovery_steps"])
        rows.append(
            {
                "task": task,
                "baseline_tail_accuracy_mean": baseline.get("tail_accuracy_mean"),
                "memory_tail_accuracy_mean": candidate.get("tail_accuracy_mean"),
                "memory_tail_delta_vs_v1_4": float(candidate.get("tail_accuracy_mean") or 0.0)
                - float(baseline.get("tail_accuracy_mean") or 0.0),
                "baseline_return_regime_accuracy_mean": baseline.get("return_regime_accuracy_mean"),
                "memory_return_regime_accuracy_mean": candidate.get("return_regime_accuracy_mean"),
                "memory_return_accuracy_delta_vs_v1_4": float(candidate.get("return_regime_accuracy_mean") or 0.0)
                - float(baseline.get("return_regime_accuracy_mean") or 0.0),
                "baseline_reacquisition_delta_mean": baseline.get("old_regime_reacquisition_delta_mean"),
                "memory_reacquisition_delta_mean": candidate.get("old_regime_reacquisition_delta_mean"),
                "memory_reacquisition_delta_vs_v1_4": float(candidate.get("old_regime_reacquisition_delta_mean") or 0.0)
                - float(baseline.get("old_regime_reacquisition_delta_mean") or 0.0),
                "baseline_mean_recovery_steps": baseline.get("mean_recovery_steps"),
                "memory_mean_recovery_steps": candidate.get("mean_recovery_steps"),
                "memory_recovery_delta_vs_v1_4": recovery_delta,
                "baseline_return_corr_mean": baseline.get("return_regime_corr_mean"),
                "memory_return_corr_mean": candidate.get("return_regime_corr_mean"),
                "memory_composite_score": composite_score(candidate),
                "best_ablation_model": best_ablation.get("model"),
                "best_ablation_composite_score": composite_score(best_ablation) if best_ablation else None,
                "memory_composite_delta_vs_best_ablation": None if not best_ablation else composite_score(candidate) - composite_score(best_ablation),
                "external_median_return_accuracy": float(np.median(external_values)) if external_values else None,
                "best_external_return_model": best_external.get("model"),
                "best_external_return_accuracy_mean": best_external.get("return_regime_accuracy_mean"),
                "memory_return_delta_vs_external_median": None
                if not external_values
                else float(candidate.get("return_regime_accuracy_mean") or 0.0) - float(np.median(external_values)),
            }
        )
    return rows


def evaluate_tier(
    *,
    aggregates: list[dict[str, Any]],
    comparisons: list[dict[str, Any]],
    leakage: dict[str, Any],
    variants: list[VariantSpec],
    models: list[str],
    args: argparse.Namespace,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    tasks = [item.strip() for item in args.tasks.split(",") if item.strip()]
    if not tasks or tasks == ["all"]:
        tasks = [item.strip() for item in DEFAULT_TASKS.split(",")]
    seeds = seeds_from_args(args)
    expected_runs = len(tasks) * len(seeds) * (len(variants) + len(models))
    observed_runs = sum(int(row.get("runs", 0)) for row in aggregates)
    tail_edges = [float(row.get("memory_tail_delta_vs_v1_4") or 0.0) for row in comparisons]
    return_edges = [float(row.get("memory_return_accuracy_delta_vs_v1_4") or 0.0) for row in comparisons]
    reacq_edges = [float(row.get("memory_reacquisition_delta_vs_v1_4") or 0.0) for row in comparisons]
    recovery_edges = [float(row.get("memory_recovery_delta_vs_v1_4") or 0.0) for row in comparisons if row.get("memory_recovery_delta_vs_v1_4") is not None]
    ablation_edges = [float(row.get("memory_composite_delta_vs_best_ablation") or 0.0) for row in comparisons if row.get("best_ablation_model")]
    external_edges = [float(row.get("memory_return_delta_vs_external_median") or 0.0) for row in comparisons if row.get("memory_return_delta_vs_external_median") is not None]
    recurrence_benefit = (
        (return_edges and max(return_edges) >= args.min_return_accuracy_delta)
        or (reacq_edges and max(reacq_edges) >= args.min_reacquisition_delta)
        or (recovery_edges and max(recovery_edges) >= args.min_recovery_delta)
    )
    ablation_specific = bool(ablation_edges) and min(ablation_edges) >= args.min_ablation_composite_delta
    external_edge_count = sum(1 for value in external_edges if value >= args.min_external_return_delta)
    base_criteria = [
        criterion("full variant/baseline/task/seed matrix completed", observed_runs, "==", expected_runs, observed_runs == expected_runs),
        criterion("feedback timing has no leakage violations", leakage.get("feedback_due_violations"), "==", 0, int(leakage.get("feedback_due_violations", 0)) == 0),
        criterion("return-regime evaluation events exist", min_value([row.get("memory_return_regime_accuracy_mean") for row in comparisons]), "not None", None, any(row.get("memory_return_regime_accuracy_mean") is not None for row in comparisons)),
    ]
    science_criteria = [
        criterion(
            "multi-timescale memory does not regress tail accuracy versus v1.4",
            min(tail_edges) if tail_edges else None,
            ">=",
            -abs(float(args.max_tail_regression)),
            bool(tail_edges) and min(tail_edges) >= -abs(float(args.max_tail_regression)),
            "The candidate cannot buy recurrence by damaging ordinary tail performance.",
        ),
        criterion(
            "multi-timescale memory improves recurrence or recovery",
            {"return_edges": return_edges, "reacquisition_edges": reacq_edges, "recovery_edges": recovery_edges},
            "any >=",
            {
                "return": args.min_return_accuracy_delta,
                "reacquisition": args.min_reacquisition_delta,
                "recovery": args.min_recovery_delta,
            },
            recurrence_benefit,
            "At least one recurrent-regime metric must improve versus v1.4.",
        ),
        criterion(
            "memory ablations are worse than the candidate",
            min(ablation_edges) if ablation_edges else None,
            ">=",
            args.min_ablation_composite_delta,
            ablation_specific,
            "No-slow/no-structural/no-BOCPD controls must not explain the benefit.",
        ),
        criterion(
            "candidate has at least one external-baseline return-regime edge",
            external_edge_count,
            ">=",
            args.min_external_edge_tasks,
            external_edge_count >= args.min_external_edge_tasks,
            "This is a reviewer-defense gate, not a universal superiority claim.",
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
        "backend": args.backend,
        "steps": args.steps,
        "smoke": bool(args.smoke),
        "leakage": leakage,
        "claim_boundary": "Diagnostic software mechanism test only; v1.4 remains frozen until a candidate passes, ablates cleanly, and survives compact regression.",
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
        "tail_accuracy_mean",
        "tail_accuracy_std",
        "all_accuracy_mean",
        "prediction_target_corr_mean",
        "mean_recovery_steps",
        "first_regime_accuracy_mean",
        "return_regime_accuracy_mean",
        "first_regime_early_accuracy_mean",
        "return_regime_early_accuracy_mean",
        "old_regime_retention_delta_mean",
        "old_regime_reacquisition_delta_mean",
        "return_regime_corr_mean",
        "runtime_seconds_mean",
        "evaluation_count_mean",
    ]
    return [{field: row.get(field) for field in fields} for row in aggregates]


def plot_memory_edges(comparisons: list[dict[str, Any]], path: Path) -> None:
    if plt is None or not comparisons:
        return
    tasks = [row["task"].replace("_", "\n") for row in comparisons]
    return_edges = [float(row.get("memory_return_accuracy_delta_vs_v1_4") or 0.0) for row in comparisons]
    reacq_edges = [float(row.get("memory_reacquisition_delta_vs_v1_4") or 0.0) for row in comparisons]
    ablation_edges = [float(row.get("memory_composite_delta_vs_best_ablation") or 0.0) for row in comparisons]
    x = np.arange(len(tasks))
    width = 0.25
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.axhline(0.0, color="black", lw=0.8)
    ax.bar(x - width, return_edges, width, label="return-regime acc delta", color="#1f6feb")
    ax.bar(x, reacq_edges, width, label="reacquisition delta", color="#2f855a")
    ax.bar(x + width, ablation_edges, width, label="candidate - best ablation", color="#b7791f")
    ax.set_title("Tier 5.10 Multi-Timescale Memory Diagnostic")
    ax.set_xticks(x)
    ax.set_xticklabels(tasks)
    ax.set_ylabel("positive favors memory candidate")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fairness_contract(args: argparse.Namespace, variants: list[VariantSpec], models: list[str]) -> dict[str, Any]:
    return {
        "tier": TIER,
        "frozen_comparator": "v1_4_pending_horizon",
        "candidate": "multi_timescale_memory",
        "ablation_controls": [variant.name for variant in variants if variant.group == "memory_ablation"],
        "selected_external_baselines": models,
        "fairness_rules": [
            "same task stream per seed for CRA variants and selected baselines",
            "same recurrent phase schedule, evaluation_target, evaluation_mask, and feedback_due_step arrays",
            "models predict before consequence feedback matures",
            "feedback_due_step must be greater than or equal to prediction step",
            "return-regime performance and reacquisition speed are scored only on predeclared A-return phases",
            "memory candidate must beat ablations before promotion",
            "passing Tier 5.10 only authorizes compact regression and sharper mechanism design, not hardware migration",
        ],
        "tasks": args.tasks,
        "steps": args.steps,
        "seeds": seeds_from_args(args),
        "backend": args.backend,
        "reacquisition_trials": args.reacquisition_trials,
    }


def run_tier(args: argparse.Namespace, output_dir: Path, variants: list[VariantSpec]) -> dict[str, Any]:
    models = parse_models(args.models)
    summaries_by_cell: dict[tuple[str, str], list[dict[str, Any]]] = {}
    rows_by_cell_seed: dict[tuple[str, str, int], list[dict[str, Any]]] = {}
    task_by_name: dict[str, TaskStream] = {}
    task_by_name_seed: dict[tuple[str, int], TaskStream] = {}
    artifacts: dict[str, str] = {}
    started = time.perf_counter()

    for seed in seeds_from_args(args):
        tasks = build_tasks(args, seed=args.task_seed + seed)
        for task in tasks:
            task_by_name[task.name] = task
            task_by_name_seed[(task.name, seed)] = task
            for variant in variants:
                print(f"[tier5.10] task={task.name} variant={variant.name} seed={seed}", flush=True)
                rows, summary = run_cra_memory_variant(task, seed=seed, variant=variant, args=args)
                csv_path = output_dir / f"{task.name}_{variant.name}_seed{seed}_timeseries.csv"
                write_csv(csv_path, rows)
                artifacts[f"{task.name}_{variant.name}_seed{seed}_timeseries_csv"] = str(csv_path)
                summaries_by_cell.setdefault((task.name, variant.name), []).append(summary)
                rows_by_cell_seed[(task.name, variant.name, seed)] = rows
            for model in models:
                print(f"[tier5.10] task={task.name} baseline={model} seed={seed}", flush=True)
                rows, summary = run_baseline_memory_case(task, model, seed=seed, args=args)
                csv_path = output_dir / f"{task.name}_{model}_seed{seed}_timeseries.csv"
                write_csv(csv_path, rows)
                artifacts[f"{task.name}_{model}_seed{seed}_timeseries_csv"] = str(csv_path)
                summaries_by_cell.setdefault((task.name, model), []).append(summary)
                rows_by_cell_seed[(task.name, model, seed)] = rows

    variant_by_name = {variant.name: variant for variant in variants}
    aggregates: list[dict[str, Any]] = []
    for (task_name, model), summaries in sorted(summaries_by_cell.items()):
        task = task_by_name[task_name]
        seed_rows = {int(s["seed"]): rows_by_cell_seed[(task_name, model, int(s["seed"]))] for s in summaries}
        family = "CRA" if model in variant_by_name else LEARNER_FACTORIES[model].family
        group = variant_by_name[model].group if model in variant_by_name else None
        aggregates.append(
            aggregate_runs(
                task=task,
                model=model,
                family=family,
                group=group,
                summaries=summaries,
                rows_by_seed=seed_rows,
                args=args,
            )
        )

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

    summary_csv = output_dir / "tier5_10_summary.csv"
    comparison_csv = output_dir / "tier5_10_comparisons.csv"
    fairness_json = output_dir / "tier5_10_fairness_contract.json"
    plot_path = output_dir / "tier5_10_memory_edges.png"
    write_csv(summary_csv, aggregate_csv_rows(aggregates))
    write_csv(comparison_csv, comparisons)
    write_json(fairness_json, fairness_contract(args, variants, models))
    plot_memory_edges(comparisons, plot_path)

    result = TestResult(
        name=TIER,
        status=status,
        summary={
            "tier_summary": tier_summary,
            "aggregates": aggregates,
            "comparisons": comparisons,
            "runtime_seconds": time.perf_counter() - started,
        },
        criteria=criteria,
        artifacts={
            **artifacts,
            "summary_csv": str(summary_csv),
            "comparisons_csv": str(comparison_csv),
            "fairness_contract_json": str(fairness_json),
            "memory_edges_png": str(plot_path),
        },
        failure_reason=failure_reason,
    )
    return result.to_dict()


def write_report(path: Path, result: dict[str, Any], args: argparse.Namespace, output_dir: Path) -> None:
    overall = "PASS" if result["status"] == "pass" else "FAIL"
    aggregates = result["summary"]["aggregates"]
    comparisons = result["summary"]["comparisons"]
    lines = [
        "# Tier 5.10 Multi-Timescale Memory Diagnostic Findings",
        "",
        f"- Generated: `{utc_now()}`",
        f"- Status: **{overall}**",
        f"- Backend: `{args.backend}`",
        f"- Steps: `{args.steps}`",
        f"- Seeds: `{', '.join(str(s) for s in seeds_from_args(args))}`",
        f"- Tasks: `{args.tasks}`",
        f"- Variants: `{args.variants}`",
        f"- Selected baselines: `{args.models}`",
        f"- Smoke mode: `{args.smoke}`",
        f"- Output directory: `{output_dir}`",
        "",
        "Tier 5.10 tests whether existing fast/slow/structural memory knobs help CRA retain or reacquire old regimes after they disappear and return.",
        "",
        "## Claim Boundary",
        "",
        "- This is software diagnostic evidence, not hardware evidence.",
        "- The candidate is a proxy memory-timescale configuration, not sleep/replay and not a full learned memory store.",
        "- v1.4 remains the frozen architecture baseline unless the candidate passes this gate and then survives compact regression.",
        "- A failed run is still useful: it identifies that recurrence/forgetting needs a sharper mechanism before promotion.",
        "",
        "## Task Comparisons",
        "",
        "| Task | v1.4 tail | Memory tail | Tail delta | v1.4 return acc | Memory return acc | Return delta | Reacq delta | Recovery delta | Best ablation | Candidate-ablation delta | External return edge |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |",
    ]
    for row in comparisons:
        lines.append(
            "| "
            f"{row['task']} | "
            f"{markdown_value(row.get('baseline_tail_accuracy_mean'))} | "
            f"{markdown_value(row.get('memory_tail_accuracy_mean'))} | "
            f"{markdown_value(row.get('memory_tail_delta_vs_v1_4'))} | "
            f"{markdown_value(row.get('baseline_return_regime_accuracy_mean'))} | "
            f"{markdown_value(row.get('memory_return_regime_accuracy_mean'))} | "
            f"{markdown_value(row.get('memory_return_accuracy_delta_vs_v1_4'))} | "
            f"{markdown_value(row.get('memory_reacquisition_delta_vs_v1_4'))} | "
            f"{markdown_value(row.get('memory_recovery_delta_vs_v1_4'))} | "
            f"`{row.get('best_ablation_model')}` | "
            f"{markdown_value(row.get('memory_composite_delta_vs_best_ablation'))} | "
            f"{markdown_value(row.get('memory_return_delta_vs_external_median'))} |"
        )
    lines.extend(
        [
            "",
            "## Aggregate Matrix",
            "",
            "| Task | Model | Family | Group | Tail acc | Return acc | Reacq delta | Return corr | Recovery | Runtime s |",
            "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in sorted(aggregates, key=lambda r: (r["task"], r.get("model_family") != "CRA", r["model"])):
        lines.append(
            "| "
            f"{row['task']} | `{row['model']}` | {row.get('model_family')} | {row.get('variant_group') or ''} | "
            f"{markdown_value(row.get('tail_accuracy_mean'))} | "
            f"{markdown_value(row.get('return_regime_accuracy_mean'))} | "
            f"{markdown_value(row.get('old_regime_reacquisition_delta_mean'))} | "
            f"{markdown_value(row.get('return_regime_corr_mean'))} | "
            f"{markdown_value(row.get('mean_recovery_steps'))} | "
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
            "- `tier5_10_results.json`: machine-readable manifest.",
            "- `tier5_10_report.md`: human findings and claim boundary.",
            "- `tier5_10_summary.csv`: aggregate task/model metrics.",
            "- `tier5_10_comparisons.csv`: candidate-vs-v1.4/ablation/baseline table.",
            "- `tier5_10_fairness_contract.json`: predeclared comparison and leakage constraints.",
            "- `tier5_10_memory_edges.png`: recurrence edge plot.",
            "- `*_timeseries.csv`: per-run traces with phase labels.",
            "",
            "![memory_edges](tier5_10_memory_edges.png)",
            "",
        ]
    )
    if MATPLOTLIB_ERROR:
        lines.append(f"Plotting unavailable: `{MATPLOTLIB_ERROR}`")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_latest(output_dir: Path, report_path: Path, manifest_path: Path, summary_csv: Path, status: str) -> None:
    latest_path = ROOT / "controlled_test_output" / "tier5_10_latest_manifest.json"
    payload = {
        "generated_at_utc": utc_now(),
        "tier": TIER,
        "status": status,
        "output_dir": str(output_dir),
        "manifest": str(manifest_path),
        "report": str(report_path),
        "summary_csv": str(summary_csv),
        "canonical": False,
        "claim": "Latest Tier 5.10 memory-timescale diagnostic; promote only after pass plus compact regression.",
    }
    write_json(latest_path, payload)


def build_parser() -> argparse.ArgumentParser:
    parser = build_tier5_1_parser()
    parser.description = "Run Tier 5.10 multi-timescale memory/forgetting diagnostics."
    parser.set_defaults(
        backend="nest",
        tasks=DEFAULT_TASKS,
        steps=960,
        seed_count=3,
        models=DEFAULT_MODELS,
        cra_population_size=8,
        cra_readout_lr=0.10,
        cra_delayed_readout_lr=0.20,
    )
    parser.add_argument("--variants", default=DEFAULT_VARIANTS, help="all or comma-separated Tier 5.10 CRA variant names")
    parser.add_argument("--memory-delay", type=int, default=5)
    parser.add_argument("--memory-period", type=int, default=8)
    parser.add_argument("--memory-noise-prob", type=float, default=0.05)
    parser.add_argument("--memory-sensory-noise-fraction", type=float, default=0.03)
    parser.add_argument("--hidden-min-phase", type=int, default=120)
    parser.add_argument("--hidden-max-phase", type=int, default=260)
    parser.add_argument("--hidden-noise-prob", type=float, default=0.10)
    parser.add_argument("--reacquisition-trials", type=int, default=10)
    parser.add_argument("--message-passing-steps", type=int, default=1)
    parser.add_argument("--message-context-gain", type=float, default=0.015)
    parser.add_argument("--message-prediction-mix", type=float, default=0.25)
    parser.add_argument("--max-tail-regression", type=float, default=0.02)
    parser.add_argument("--min-return-accuracy-delta", type=float, default=0.02)
    parser.add_argument("--min-reacquisition-delta", type=float, default=0.02)
    parser.add_argument("--min-recovery-delta", type=float, default=1.0)
    parser.add_argument("--min-ablation-composite-delta", type=float, default=0.005)
    parser.add_argument("--min-external-return-delta", type=float, default=0.0)
    parser.add_argument("--min-external-edge-tasks", type=int, default=1)
    parser.add_argument("--smoke", action="store_true", help="Run harness integrity gates only; scientific promotion gates are skipped.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    variants = parse_variants(args.variants)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = args.output_dir or (ROOT / "controlled_test_output" / f"tier5_10_{timestamp}")
    output_dir.mkdir(parents=True, exist_ok=True)

    result = run_tier(args, output_dir, variants)
    manifest_path = output_dir / "tier5_10_results.json"
    report_path = output_dir / "tier5_10_report.md"
    summary_csv = output_dir / "tier5_10_summary.csv"
    comparison_csv = output_dir / "tier5_10_comparisons.csv"
    fairness_json = output_dir / "tier5_10_fairness_contract.json"
    manifest = {
        "tier": TIER,
        "generated_at_utc": utc_now(),
        "output_dir": str(output_dir),
        "command": " ".join(sys.argv),
        "backend": args.backend,
        "status": result["status"],
        "result": result,
        "summary": {
            **result["summary"]["tier_summary"],
            "runtime_seconds": result["summary"]["runtime_seconds"],
            "comparisons": result["summary"]["comparisons"],
        },
        "artifacts": {
            "summary_csv": str(summary_csv),
            "comparisons_csv": str(comparison_csv),
            "fairness_contract_json": str(fairness_json),
            "report_md": str(report_path),
            "memory_edges_png": str(output_dir / "tier5_10_memory_edges.png"),
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
                "comparisons_csv": str(comparison_csv),
                "fairness_contract_json": str(fairness_json),
                "failure_reason": result["failure_reason"],
            },
            indent=2,
        )
    )
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
