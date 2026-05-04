#!/usr/bin/env python3
"""Tier 5.10c explicit context-memory mechanism diagnostic.

Tier 5.10b validated repaired tasks where the same current cue can require
opposite actions depending on remembered context. Tier 5.10c now asks the next
question: can CRA use an explicit, auditable context-memory feature on those
tasks, and do reset/shuffled/wrong-memory ablations remove the benefit?

This is a software mechanism diagnostic. A pass here would authorize compact
regression and a cleaner internal-memory design. It is not hardware evidence,
not sleep/replay evidence, and not native on-chip memory evidence.
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
    DEFAULT_TASKS,
    MemoryTask,
    build_tasks,
    run_control_model,
    run_external_model,
    task_ambiguity_summary,
)


TIER = "Tier 5.10c - Explicit Context Memory Mechanism Diagnostic"
DEFAULT_VARIANTS = "v1_4_raw,explicit_context_memory,memory_reset_ablation,shuffled_memory_ablation,wrong_memory_ablation"
EPS = 1e-12


@dataclass(frozen=True)
class MemoryVariant:
    name: str
    group: str
    feature_mode: str
    hypothesis: str
    overrides: dict[str, Any]


VARIANTS: tuple[MemoryVariant, ...] = (
    MemoryVariant(
        name="v1_4_raw",
        group="frozen_baseline",
        feature_mode="raw",
        hypothesis="Frozen v1.4 CRA receives the repaired task stream without explicit context binding.",
        overrides={
            "learning.delayed_readout_learning_rate": 0.20,
            "learning.macro_eligibility_enabled": False,
        },
    ),
    MemoryVariant(
        name="explicit_context_memory",
        group="candidate",
        feature_mode="context_bound",
        hypothesis="Host-side context memory stores the visible context cue and binds it to the later decision cue.",
        overrides={
            "learning.delayed_readout_learning_rate": 0.20,
            "learning.macro_eligibility_enabled": False,
        },
    ),
    MemoryVariant(
        name="memory_reset_ablation",
        group="memory_ablation",
        feature_mode="reset",
        hypothesis="Control: decision cue is presented without retained context memory.",
        overrides={
            "learning.delayed_readout_learning_rate": 0.20,
            "learning.macro_eligibility_enabled": False,
        },
    ),
    MemoryVariant(
        name="shuffled_memory_ablation",
        group="memory_ablation",
        feature_mode="shuffled",
        hypothesis="Control: context memory is present but assigned to the wrong trial.",
        overrides={
            "learning.delayed_readout_learning_rate": 0.20,
            "learning.macro_eligibility_enabled": False,
        },
    ),
    MemoryVariant(
        name="wrong_memory_ablation",
        group="memory_ablation",
        feature_mode="wrong",
        hypothesis="Control: context memory is systematically inverted.",
        overrides={
            "learning.delayed_readout_learning_rate": 0.20,
            "learning.macro_eligibility_enabled": False,
        },
    ),
)


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
        raise argparse.ArgumentTypeError(f"unknown Tier 5.10c variants: {', '.join(missing)}")
    selected = [by_name[name] for name in names]
    required = {"v1_4_raw", "explicit_context_memory"}
    present = {variant.name for variant in selected}
    if not required.issubset(present):
        raise argparse.ArgumentTypeError("Tier 5.10c requires v1_4_raw and explicit_context_memory")
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
        if variant.feature_mode == "context_bound":
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
            observation, feature = transform_sensory(
                task=task,
                step=step,
                variant=variant,
                memory=memory,
                shuffled_context_by_trial=shuffled,
                amplitude=float(args.amplitude),
            )
            consequence = float(task.stream.current_target[step])
            metrics = organism.train_task_step(
                observation_value=observation,
                consequence_value=consequence,
                horizon_signal=consequence,
                dt_seconds=float(args.dt_seconds),
                task_name=task.stream.name,
                metadata={
                    "tier": "5.10c",
                    "variant": variant.name,
                    "event_type": task.event_type[step],
                    "phase": task.phase[step],
                },
            )
            prediction = float(metrics.colony_prediction)
            eval_sign = strict_sign(float(task.stream.evaluation_target[step]))
            pred_sign = strict_sign(prediction)
            row = metrics.to_dict()
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
                    "raw_sensory_return_1m": float(task.stream.sensory[step]),
                    "sensory_return_1m": float(observation),
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
        baseline = by_task_model.get((task, "v1_4_raw"), {})
        candidate = by_task_model.get((task, "explicit_context_memory"), {})
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
                "baseline_all_accuracy": baseline.get("all_accuracy_mean"),
                "candidate_all_accuracy": candidate.get("all_accuracy_mean"),
                "candidate_all_delta_vs_v1_4": float(candidate.get("all_accuracy_mean") or 0.0) - float(baseline.get("all_accuracy_mean") or 0.0),
                "baseline_tail_accuracy": baseline.get("tail_accuracy_mean"),
                "candidate_tail_accuracy": candidate.get("tail_accuracy_mean"),
                "candidate_tail_delta_vs_v1_4": float(candidate.get("tail_accuracy_mean") or 0.0) - float(baseline.get("tail_accuracy_mean") or 0.0),
                "candidate_abs_corr": abs(float(candidate.get("prediction_target_corr_mean") or 0.0)),
                "baseline_abs_corr": abs(float(baseline.get("prediction_target_corr_mean") or 0.0)),
                "candidate_abs_corr_delta_vs_v1_4": abs(float(candidate.get("prediction_target_corr_mean") or 0.0)) - abs(float(baseline.get("prediction_target_corr_mean") or 0.0)),
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
            "candidate reaches minimum accuracy on repaired tasks",
            min(candidate_accs) if candidate_accs else None,
            ">=",
            args.min_candidate_accuracy,
            bool(candidate_accs) and min(candidate_accs) >= args.min_candidate_accuracy,
        ),
        criterion(
            "candidate improves over v1.4 raw CRA",
            min(candidate_edges) if candidate_edges else None,
            ">=",
            args.min_candidate_edge_vs_v1_4,
            bool(candidate_edges) and min(candidate_edges) >= args.min_candidate_edge_vs_v1_4,
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
        "claim_boundary": "Software diagnostic only: explicit host-side context binding, not native CRA memory, sleep/replay, or hardware evidence.",
    }
    return criteria, summary


def aggregate_csv_rows(aggregates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fields = [
        "task",
        "model",
        "model_family",
        "variant_group",
        "feature_mode",
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
    v14 = [float(row.get("candidate_all_delta_vs_v1_4") or 0.0) for row in comparisons]
    ablation = [float(row.get("candidate_all_delta_vs_best_ablation") or 0.0) for row in comparisons]
    standard = [float(row.get("candidate_all_delta_vs_best_standard") or 0.0) for row in comparisons]
    x = np.arange(len(tasks))
    width = 0.25
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.axhline(0.0, color="black", lw=0.8)
    ax.bar(x - width, v14, width, label="candidate all-accuracy delta vs v1.4", color="#1f6feb")
    ax.bar(x, ablation, width, label="candidate delta vs best memory ablation", color="#2f855a")
    ax.bar(x + width, standard, width, label="candidate delta vs best standard", color="#b7791f")
    ax.set_title("Tier 5.10c Explicit Context Memory Diagnostic")
    ax.set_xticks(x)
    ax.set_xticklabels(tasks)
    ax.set_ylabel("positive favors explicit context memory")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fairness_contract(args: argparse.Namespace, variants: list[MemoryVariant], models: list[str]) -> dict[str, Any]:
    return {
        "tier": TIER,
        "frozen_comparator": "v1_4_raw",
        "candidate": "explicit_context_memory",
        "ablation_controls": [variant.name for variant in variants if variant.group == "memory_ablation"],
        "selected_external_baselines": models,
        "context_controls": list(CONTROL_MODELS),
        "fairness_rules": [
            "all variants use the same repaired Tier 5.10b task streams per seed",
            "candidate may update memory only on visible context events",
            "candidate binds retained context to the later visible decision cue",
            "reset/shuffled/wrong-memory controls must lose the benefit before promotion",
            "models predict before consequence feedback matures",
            "Tier 5.10c is host-side explicit-memory scaffolding, not native on-chip memory",
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
        "# Tier 5.10c Explicit Context Memory Mechanism Diagnostic Findings",
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
        "Tier 5.10c tests whether CRA can use an explicit host-side context-memory feature on the repaired Tier 5.10b streams.",
        "",
        "## Claim Boundary",
        "",
        "- This is software diagnostic evidence, not hardware evidence.",
        "- The candidate is an explicit host-side context-binding scaffold, not native on-chip memory.",
        "- A pass authorizes compact regression and a cleaner internal-memory design; it does not promote sleep/replay.",
        "",
        "## Task Comparisons",
        "",
        "| Task | v1.4 all | Candidate all | Delta vs v1.4 | Best ablation | Delta vs ablation | Sign acc | Best standard | Delta vs standard | Feature-active steps |",
        "| --- | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: |",
    ]
    for row in comparisons:
        lines.append(
            "| "
            f"{row['task']} | "
            f"{markdown_value(row.get('baseline_all_accuracy'))} | "
            f"{markdown_value(row.get('candidate_all_accuracy'))} | "
            f"{markdown_value(row.get('candidate_all_delta_vs_v1_4'))} | "
            f"`{row.get('best_ablation_model')}` | "
            f"{markdown_value(row.get('candidate_all_delta_vs_best_ablation'))} | "
            f"{markdown_value(row.get('sign_persistence_all_accuracy'))} | "
            f"`{row.get('best_standard_model')}` | "
            f"{markdown_value(row.get('candidate_all_delta_vs_best_standard'))} | "
            f"{markdown_value(row.get('candidate_feature_active_steps'))} |"
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
            "- `tier5_10c_results.json`: machine-readable manifest.",
            "- `tier5_10c_report.md`: human findings and claim boundary.",
            "- `tier5_10c_summary.csv`: aggregate task/model metrics.",
            "- `tier5_10c_comparisons.csv`: candidate-vs-v1.4/ablation/baseline table.",
            "- `tier5_10c_fairness_contract.json`: predeclared comparison/leakage rules.",
            "- `tier5_10c_memory_edges.png`: explicit-memory edge plot.",
            "- `*_timeseries.csv`: per-task/per-model/per-seed traces.",
            "",
            "![memory_edges](tier5_10c_memory_edges.png)",
            "",
        ]
    )
    if MATPLOTLIB_ERROR:
        lines.append(f"Plotting unavailable: `{MATPLOTLIB_ERROR}`")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_latest(output_dir: Path, report_path: Path, manifest_path: Path, summary_csv: Path, status: str) -> None:
    latest_path = ROOT / "controlled_test_output" / "tier5_10c_latest_manifest.json"
    payload = {
        "generated_at_utc": utc_now(),
        "tier": TIER,
        "status": status,
        "output_dir": str(output_dir),
        "manifest": str(manifest_path),
        "report": str(report_path),
        "summary_csv": str(summary_csv),
        "canonical": False,
        "claim": "Latest Tier 5.10c explicit context-memory diagnostic; passing is not hardware or native-memory evidence.",
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
                print(f"[tier5.10c] task={task.stream.name} variant={variant.name} seed={seed}", flush=True)
                rows, summary = run_cra_memory_variant(task, seed=seed, variant=variant, args=args)
                write_csv(output_dir / f"{task.stream.name}_{variant.name}_seed{seed}_timeseries.csv", rows)
                summaries_by_cell.setdefault((task.stream.name, variant.name), []).append(summary)
                rows_by_cell_seed[(task.stream.name, variant.name, seed)] = rows
            for model in models:
                print(f"[tier5.10c] task={task.stream.name} model={model} seed={seed}", flush=True)
                rows, summary = run_external_model(task, model, seed=seed, args=args)
                write_csv(output_dir / f"{task.stream.name}_{model}_seed{seed}_timeseries.csv", rows)
                summaries_by_cell.setdefault((task.stream.name, model), []).append(summary)
                rows_by_cell_seed[(task.stream.name, model, seed)] = rows
            for control in CONTROL_MODELS:
                print(f"[tier5.10c] task={task.stream.name} control={control} seed={seed}", flush=True)
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
    summary_csv = output_dir / "tier5_10c_summary.csv"
    comparisons_csv = output_dir / "tier5_10c_comparisons.csv"
    fairness_json = output_dir / "tier5_10c_fairness_contract.json"
    plot_path = output_dir / "tier5_10c_memory_edges.png"
    write_csv(summary_csv, aggregate_csv_rows(aggregates))
    write_csv(comparisons_csv, comparisons)
    write_json(fairness_json, fairness_contract(args, variants, models))
    plot_memory_edges(comparisons, plot_path)
    return {
        "name": "explicit_context_memory_mechanism",
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
    parser.description = "Run Tier 5.10c explicit context-memory mechanism diagnostic."
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
    parser.add_argument("--context-gap", type=int, default=12)
    parser.add_argument("--context-period", type=int, default=24)
    parser.add_argument("--long-context-gap", type=int, default=32)
    parser.add_argument("--long-context-period", type=int, default=48)
    parser.add_argument("--distractor-density", type=float, default=0.65)
    parser.add_argument("--distractor-scale", type=float, default=0.30)
    parser.add_argument("--recurrence-phase-len", type=int, default=240)
    parser.add_argument("--recurrence-trial-gap", type=int, default=12)
    parser.add_argument("--recurrence-decision-gap", type=int, default=16)
    parser.add_argument("--message-passing-steps", type=int, default=2)
    parser.add_argument("--message-context-gain", type=float, default=0.35)
    parser.add_argument("--message-prediction-mix", type=float, default=0.25)
    parser.add_argument("--min-candidate-accuracy", type=float, default=0.70)
    parser.add_argument("--min-candidate-edge-vs-v1-4", type=float, default=0.10)
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
    output_dir = args.output_dir or (ROOT / "controlled_test_output" / f"tier5_10c_{timestamp}")
    output_dir.mkdir(parents=True, exist_ok=True)
    result = run_tier(args, output_dir, variants)
    manifest_path = output_dir / "tier5_10c_results.json"
    report_path = output_dir / "tier5_10c_report.md"
    summary_csv = output_dir / "tier5_10c_summary.csv"
    comparisons_csv = output_dir / "tier5_10c_comparisons.csv"
    fairness_json = output_dir / "tier5_10c_fairness_contract.json"
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
            "memory_edges_png": str(output_dir / "tier5_10c_memory_edges.png"),
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
