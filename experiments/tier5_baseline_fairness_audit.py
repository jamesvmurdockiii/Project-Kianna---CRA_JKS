#!/usr/bin/env python3
"""Tier 5.6 baseline hyperparameter fairness audit.

Tier 5.6 follows the canonical Tier 5.5 expanded-baseline result. It keeps the
promoted CRA setting locked and gives external baselines a predeclared tuning
budget. The goal is not to make CRA win by construction. The goal is to document
whether any CRA advantage survives when simple/recurrent/population baselines are
allowed reasonable settings under the same causal task streams.
"""

from __future__ import annotations

import argparse
import copy
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

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from tier2_learning import criterion, markdown_value, pass_fail, write_csv, write_json  # noqa: E402
from tier4_scaling import seeds_from_args  # noqa: E402
from tier5_cra_failure_analysis import VariantSpec, run_cra_variant  # noqa: E402
from tier5_expanded_baselines import (  # noqa: E402
    CRA_VARIANT_LIBRARY,
    aggregate_cell,
    aggregate_csv_rows,
    build_comparisons,
    build_parser as build_tier5_5_parser,
    comparison_csv_rows,
    enrich_summary,
    json_safe,
    parse_cra_variants,
    parse_external_models,
    parse_run_lengths,
    per_seed_summary_rows,
    plot_edge_summary,
    selected_task_names,
)
from tier5_external_baselines import (  # noqa: E402
    LEARNER_FACTORIES,
    TaskStream,
    TestResult,
    build_tasks,
    run_baseline_case,
)


TIER = "Tier 5.6 - Baseline Hyperparameter Fairness Audit"
DEFAULT_RUN_LENGTHS = "960,1500"
DEFAULT_TASKS = "delayed_cue,hard_noisy_switching,sensor_control"
DEFAULT_MODELS = (
    "random_sign,sign_persistence,online_perceptron,online_logistic_regression,"
    "echo_state_network,small_gru,stdp_only_snn,evolutionary_population"
)


@dataclass(frozen=True)
class RunKey:
    run_length: int
    task: str
    model: str
    seed: int


@dataclass(frozen=True)
class CandidateSpec:
    base_model: str
    candidate_id: str
    family: str
    overrides: dict[str, Any]
    description: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _safe_float(value: Any, default: float = -1.0) -> float:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return default
    return f if math.isfinite(f) else default


def _slug_value(value: Any) -> str:
    if isinstance(value, float):
        text = f"{value:g}"
    else:
        text = str(value)
    return text.replace("-", "m").replace("+", "p").replace(".", "p")


def _candidate_id(model: str, overrides: dict[str, Any], *, prefix: str = "") -> str:
    if not overrides:
        return f"{model}__default" if not prefix else f"{model}__{prefix}"
    parts = [prefix] if prefix else []
    parts.extend(f"{key}_{_slug_value(value)}" for key, value in sorted(overrides.items()))
    return f"{model}__{'_'.join(parts)}"


def _spec(model: str, overrides: dict[str, Any], description: str, *, prefix: str = "") -> CandidateSpec:
    family = LEARNER_FACTORIES[model].family
    return CandidateSpec(
        base_model=model,
        candidate_id=_candidate_id(model, overrides, prefix=prefix),
        family=family,
        overrides=dict(overrides),
        description=description,
    )


def candidate_library(model: str, budget: str) -> list[CandidateSpec]:
    """Return predeclared external-baseline profiles for one model.

    The standard budget is intentionally modest: enough to defeat a lazy-default
    critique, not an open-ended leaderboard search. Smoke uses only a tiny
    subset for CI/local validation.
    """
    if model not in LEARNER_FACTORIES:
        raise argparse.ArgumentTypeError(f"unknown external model {model!r}")
    if model in {"random_sign", "sign_persistence"}:
        return [_spec(model, {}, "deterministic/control baseline with no tunable learning budget")]

    smoke = budget == "smoke"
    if model == "online_perceptron":
        profiles = [
            {"perceptron_lr": 0.02, "perceptron_margin": 0.0},
            {"perceptron_lr": 0.05, "perceptron_margin": 0.0},
            {"perceptron_lr": 0.08, "perceptron_margin": 0.05},
            {"perceptron_lr": 0.15, "perceptron_margin": 0.05},
            {"perceptron_lr": 0.25, "perceptron_margin": 0.10},
        ]
    elif model == "online_logistic_regression":
        profiles = [
            {"logistic_lr": 0.02, "logistic_l2": 0.0},
            {"logistic_lr": 0.05, "logistic_l2": 0.0},
            {"logistic_lr": 0.10, "logistic_l2": 0.001},
            {"logistic_lr": 0.20, "logistic_l2": 0.001},
            {"logistic_lr": 0.30, "logistic_l2": 0.005},
        ]
    elif model == "echo_state_network":
        profiles = [
            {"reservoir_hidden": 16, "reservoir_lr": 0.03, "reservoir_leak": 0.25, "reservoir_radius": 0.75},
            {"reservoir_hidden": 24, "reservoir_lr": 0.04, "reservoir_leak": 0.35, "reservoir_radius": 0.85},
            {"reservoir_hidden": 32, "reservoir_lr": 0.06, "reservoir_leak": 0.50, "reservoir_radius": 0.95},
            {"reservoir_hidden": 32, "reservoir_lr": 0.10, "reservoir_leak": 0.30, "reservoir_radius": 1.10},
            {"reservoir_hidden": 48, "reservoir_lr": 0.08, "reservoir_leak": 0.55, "reservoir_radius": 1.20},
        ]
    elif model == "small_gru":
        profiles = [
            {"gru_hidden": 8, "gru_lr": 0.03},
            {"gru_hidden": 16, "gru_lr": 0.04},
            {"gru_hidden": 16, "gru_lr": 0.08},
            {"gru_hidden": 24, "gru_lr": 0.06},
            {"gru_hidden": 32, "gru_lr": 0.10},
        ]
    elif model == "stdp_only_snn":
        profiles = [
            {"stdp_hidden": 16, "stdp_threshold": 0.15, "stdp_lr": 0.0005, "stdp_trace_decay": 0.85},
            {"stdp_hidden": 24, "stdp_threshold": 0.25, "stdp_lr": 0.0008, "stdp_trace_decay": 0.90},
            {"stdp_hidden": 32, "stdp_threshold": 0.20, "stdp_lr": 0.0015, "stdp_trace_decay": 0.95},
            {"stdp_hidden": 32, "stdp_threshold": 0.35, "stdp_lr": 0.0030, "stdp_trace_decay": 0.95},
            {"stdp_hidden": 48, "stdp_threshold": 0.25, "stdp_lr": 0.0050, "stdp_trace_decay": 0.98},
        ]
    elif model == "evolutionary_population":
        profiles = [
            {"evo_population": 12, "evo_mutation": 0.03, "evo_fitness_decay": 0.85},
            {"evo_population": 24, "evo_mutation": 0.06, "evo_fitness_decay": 0.92},
            {"evo_population": 32, "evo_mutation": 0.04, "evo_fitness_decay": 0.90},
            {"evo_population": 48, "evo_mutation": 0.08, "evo_fitness_decay": 0.95},
            {"evo_population": 64, "evo_mutation": 0.12, "evo_fitness_decay": 0.97},
        ]
    else:  # pragma: no cover - guarded above, kept defensive for future models
        profiles = [{}]

    if smoke:
        profiles = profiles[:2]
    return [_spec(model, overrides, "predeclared Tier 5.6 tuned profile") for overrides in profiles]


def build_candidate_specs(models: list[str], budget: str, max_candidates_per_model: int | None) -> list[CandidateSpec]:
    specs: list[CandidateSpec] = []
    seen: set[str] = set()
    for model in models:
        model_specs = candidate_library(model, budget)
        if max_candidates_per_model is not None and max_candidates_per_model > 0:
            model_specs = model_specs[: int(max_candidates_per_model)]
        for spec in model_specs:
            if spec.candidate_id in seen:
                raise RuntimeError(f"duplicate candidate id generated: {spec.candidate_id}")
            specs.append(spec)
            seen.add(spec.candidate_id)
    return specs


def candidate_budget_rows(specs: list[CandidateSpec]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for spec in specs:
        rows.append(
            {
                "base_model": spec.base_model,
                "candidate_id": spec.candidate_id,
                "model_family": spec.family,
                "overrides_json": json.dumps(spec.overrides, sort_keys=True),
                "description": spec.description,
            }
        )
    return rows


def tuned_args(args: argparse.Namespace, overrides: dict[str, Any]) -> argparse.Namespace:
    new_args = copy.copy(args)
    for key, value in overrides.items():
        setattr(new_args, key, value)
    return new_args


def rank_key(row: dict[str, Any]) -> tuple[float, float, float, float]:
    return (
        _safe_float(row.get("tail_accuracy_mean")),
        _safe_float(row.get("area_under_learning_curve_mean")),
        abs(_safe_float(row.get("prediction_target_corr_mean"), default=0.0)),
        -_safe_float(row.get("runtime_seconds_mean"), default=1e9),
    )


def build_best_profile_rows(aggregates: list[dict[str, Any]], specs: list[CandidateSpec]) -> list[dict[str, Any]]:
    spec_by_id = {spec.candidate_id: spec for spec in specs}
    rows: list[dict[str, Any]] = []
    keys = sorted({(int(a["run_length_steps"]), a["task"], spec_by_id[a["model"]].base_model) for a in aggregates if a["model"] in spec_by_id})
    for run_length, task, base_model in keys:
        candidates = [
            a for a in aggregates
            if int(a["run_length_steps"]) == run_length
            and a["task"] == task
            and a["model"] in spec_by_id
            and spec_by_id[a["model"]].base_model == base_model
        ]
        if not candidates:
            continue
        ordered = sorted(candidates, key=rank_key, reverse=True)
        best = ordered[0]
        median_tail = float(np.median([_safe_float(a.get("tail_accuracy_mean"), default=0.0) for a in candidates]))
        median_auc = float(np.median([_safe_float(a.get("area_under_learning_curve_mean"), default=0.0) for a in candidates]))
        spec = spec_by_id[best["model"]]
        rows.append(
            {
                "run_length_steps": run_length,
                "task": task,
                "base_model": base_model,
                "model_family": spec.family,
                "candidate_count": len(candidates),
                "best_candidate_id": best["model"],
                "best_tail_accuracy_mean": best.get("tail_accuracy_mean"),
                "best_all_accuracy_mean": best.get("all_accuracy_mean"),
                "best_prediction_target_corr_mean": best.get("prediction_target_corr_mean"),
                "best_area_under_learning_curve_mean": best.get("area_under_learning_curve_mean"),
                "best_runtime_seconds_mean": best.get("runtime_seconds_mean"),
                "median_candidate_tail_accuracy": median_tail,
                "median_candidate_area_under_learning_curve": median_auc,
                "best_overrides_json": json.dumps(spec.overrides, sort_keys=True),
            }
        )
    return rows


def build_fairness_contract(
    args: argparse.Namespace,
    run_lengths: list[int],
    cra_variants: list[VariantSpec],
    external_models: list[str],
    candidate_specs: list[CandidateSpec],
) -> dict[str, Any]:
    by_model: dict[str, list[str]] = {}
    for spec in candidate_specs:
        by_model.setdefault(spec.base_model, []).append(spec.candidate_id)
    return {
        "claim_boundary": "Controlled software hyperparameter fairness audit only; not hardware evidence and not proof of universal superiority.",
        "baseline_version_under_audit": "CRA evidence baseline v0.9 / locked CRA v0.8 delayed_lr_0_20 model setting",
        "audit_rule": "CRA setting is locked; external baselines receive the documented tuning budget below.",
        "causal_rules": [
            "all candidates receive the same task stream for the same task seed and seed",
            "all candidates predict before seeing the current evaluation label",
            "delayed tasks update only when feedback_due_step matures",
            "no candidate receives future labels, switch locations, reward signs, or privileged task metadata",
            "CRA and all external candidates share train/evaluation windows and task masks",
            "candidate selection is reported after the run rather than silently substituted into the task stream",
        ],
        "matrix": {
            "run_lengths": run_lengths,
            "tasks": selected_task_names(args.tasks),
            "seeds": seeds_from_args(args),
            "cra_variants": [variant.name for variant in cra_variants],
            "external_models": external_models,
            "candidate_count": len(candidate_specs),
            "candidate_count_by_model": {model: len(ids) for model, ids in by_model.items()},
        },
        "candidate_budget": candidate_budget_rows(candidate_specs),
        "predeclared_ranking": [
            "tail_accuracy_mean",
            "area_under_learning_curve_mean",
            "absolute prediction_target_corr_mean",
            "lower runtime_seconds_mean as tie-breaker only",
        ],
        "not_implemented_in_this_tier": [
            "surrogate_gradient_snn",
            "ann_trained_readout",
            "ann_to_snn_conversion",
            "contextual_bandit_or_actor_critic",
            "liquid_state_machine_variant",
        ],
    }


def evaluate_tier(
    *,
    aggregates: list[dict[str, Any]],
    comparisons: list[dict[str, Any]],
    best_profiles: list[dict[str, Any]],
    observed_runs: int,
    run_lengths: list[int],
    cra_variants: list[VariantSpec],
    candidate_specs: list[CandidateSpec],
    args: argparse.Namespace,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    tasks = selected_task_names(args.tasks)
    seeds = seeds_from_args(args)
    expected_runs = len(run_lengths) * len(tasks) * len(seeds) * (len(cra_variants) + len(candidate_specs))
    expected_cells = len(run_lengths) * len(tasks) * (len(cra_variants) + len(candidate_specs))
    expected_profile_groups = len(run_lengths) * len(tasks) * len({spec.base_model for spec in candidate_specs})
    expected_comparison_rows = len(run_lengths) * len(tasks) * len(cra_variants)
    observed_lengths = sorted({int(a["run_length_steps"]) for a in aggregates})
    candidate_ids = {spec.candidate_id for spec in candidate_specs}
    fixed_external = [a for a in aggregates if a["task"] == "fixed_pattern" and a["model"] in candidate_ids]
    best_fixed = max([_safe_float(a.get("tail_accuracy_mean"), default=0.0) for a in fixed_external], default=None)
    target_tasks = {item.strip() for item in args.target_tasks.split(",") if item.strip()}
    target_rows = [row for row in comparisons if row["task"] in target_tasks]
    robust_rows = [row for row in target_rows if bool(row.get("robust_advantage_regime"))]
    surviving_rows = [row for row in target_rows if bool(row.get("robust_advantage_regime")) and bool(row.get("not_dominated_by_best_external"))]
    not_dominated_rows = [row for row in target_rows if bool(row.get("not_dominated_by_best_external"))]
    ci_rows = [row for row in comparisons if row.get("paired_tail_delta_vs_external_median_ci_low") is not None]
    summary = {
        "expected_runs": expected_runs,
        "observed_runs": observed_runs,
        "expected_cells": expected_cells,
        "observed_cells": len(aggregates),
        "expected_profile_groups": expected_profile_groups,
        "observed_profile_groups": len(best_profiles),
        "expected_comparison_rows": expected_comparison_rows,
        "observed_comparison_rows": len(comparisons),
        "run_lengths": run_lengths,
        "observed_run_lengths": observed_lengths,
        "tasks": tasks,
        "target_tasks": sorted(target_tasks),
        "seeds": seeds,
        "cra_variants": [variant.name for variant in cra_variants],
        "candidate_count": len(candidate_specs),
        "external_models": sorted({spec.base_model for spec in candidate_specs}),
        "robust_target_regime_count": len(robust_rows),
        "not_dominated_target_regime_count": len(not_dominated_rows),
        "surviving_target_regime_count": len(surviving_rows),
        "surviving_target_regimes": [
            {"run_length_steps": row["run_length_steps"], "task": row["task"], "cra_model": row["cra_model"]}
            for row in surviving_rows
        ],
        "best_fixed_external_tail_accuracy": best_fixed,
        "claim_boundary": "Controlled software hyperparameter fairness audit; CRA locked, external candidates tuned; not hardware evidence and not proof of universal superiority.",
    }
    fixed_requested = "fixed_pattern" in tasks
    fixed_pass = (not fixed_requested) or (best_fixed is not None and best_fixed >= args.fixed_external_tail_threshold)
    criteria = [
        criterion("full tuned-baseline run matrix completed", observed_runs, "==", expected_runs, observed_runs == expected_runs),
        criterion("all aggregate cells produced", len(aggregates), "==", expected_cells, len(aggregates) == expected_cells),
        criterion("all requested run lengths represented", observed_lengths, "==", run_lengths, observed_lengths == run_lengths),
        criterion("all best-profile groups reported", len(best_profiles), "==", expected_profile_groups, len(best_profiles) == expected_profile_groups),
        criterion("all comparison rows produced", len(comparisons), "==", expected_comparison_rows, len(comparisons) == expected_comparison_rows),
        criterion(
            "simple tuned external baseline learns fixed-pattern sanity task",
            best_fixed,
            ">=",
            args.fixed_external_tail_threshold,
            fixed_pass,
            "Skipped if fixed_pattern is not part of this run.",
        ),
        criterion(
            "paired confidence intervals produced for comparisons",
            len(ci_rows),
            "==",
            expected_comparison_rows,
            len(ci_rows) == expected_comparison_rows,
        ),
        criterion(
            "CRA has a target-regime edge after baseline retuning",
            len(robust_rows),
            ">=",
            args.min_retuned_robust_regimes,
            len(robust_rows) >= args.min_retuned_robust_regimes,
            "Set --min-retuned-robust-regimes 0 for smoke runs only.",
        ),
        criterion(
            "CRA has a surviving target regime versus retuned baselines",
            len(surviving_rows),
            ">=",
            args.min_surviving_advantage_regimes,
            len(surviving_rows) >= args.min_surviving_advantage_regimes,
            "A surviving regime is robust versus tuned external median and not dominated by the best tuned external candidate.",
        ),
    ]
    return criteria, summary


def write_report(
    path: Path,
    result: TestResult,
    aggregates: list[dict[str, Any]],
    comparisons: list[dict[str, Any]],
    best_profiles: list[dict[str, Any]],
    fairness_contract: dict[str, Any],
    args: argparse.Namespace,
    run_lengths: list[int],
    output_dir: Path,
) -> None:
    overall = "PASS" if result.passed else "FAIL"
    lines = [
        "# Tier 5.6 Baseline Hyperparameter Fairness Audit Findings",
        "",
        f"- Generated: `{utc_now()}`",
        f"- Status: **{overall}**",
        f"- CRA backend: `{args.backend}`",
        f"- Seeds: `{', '.join(str(s) for s in seeds_from_args(args))}`",
        f"- Run lengths: `{', '.join(str(v) for v in run_lengths)}`",
        f"- Tasks: `{args.tasks}`",
        f"- Candidate budget: `{args.budget}`",
        f"- Output directory: `{output_dir}`",
        "",
        "Tier 5.6 locks the promoted CRA delayed-credit setting and gives external baselines a documented hyperparameter budget. It is a reviewer-defense audit against the claim that Tier 5.5 only beat weak/default baselines.",
        "",
        "## Claim Boundary",
        "",
        "- This is controlled software evidence, not hardware evidence.",
        "- Passing does not mean CRA wins every task, metric, or tuned baseline.",
        "- Failing is actionable: it narrows the paper claim or forces mechanism work before stronger claims.",
        "",
        "## Fairness Contract",
        "",
    ]
    for rule in fairness_contract["causal_rules"]:
        lines.append(f"- {rule}")
    lines.extend(
        [
            "",
            "## Candidate Budget",
            "",
            "| Base model | Candidate count |",
            "| --- | ---: |",
        ]
    )
    for model, count in sorted(fairness_contract["matrix"]["candidate_count_by_model"].items()):
        lines.append(f"| `{model}` | {count} |")
    lines.extend(
        [
            "",
            "## Best Tuned Profiles",
            "",
            "| Steps | Task | Base model | Candidates | Best candidate | Best tail | Median candidate tail | Best AULC | Overrides |",
            "| ---: | --- | --- | ---: | --- | ---: | ---: | ---: | --- |",
        ]
    )
    for row in sorted(best_profiles, key=lambda r: (r["task"], int(r["run_length_steps"]), r["base_model"])):
        lines.append(
            "| "
            f"{row['run_length_steps']} | {row['task']} | `{row['base_model']}` | {row['candidate_count']} | "
            f"`{row['best_candidate_id']}` | {markdown_value(row.get('best_tail_accuracy_mean'))} | "
            f"{markdown_value(row.get('median_candidate_tail_accuracy'))} | "
            f"{markdown_value(row.get('best_area_under_learning_curve_mean'))} | "
            f"`{row.get('best_overrides_json')}` |"
        )
    lines.extend(
        [
            "",
            "## CRA Versus Retuned External Candidates",
            "",
            "| Steps | Task | CRA | CRA tail | Median tuned external tail | Best tuned external tail | Best tuned candidate | Paired delta vs median | CI low | CI high | Robust edge | Survives best |",
            "| ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- | --- |",
        ]
    )
    for row in sorted(comparisons, key=lambda r: (r["task"], int(r["run_length_steps"]), r["cra_model"])):
        lines.append(
            "| "
            f"{row['run_length_steps']} | {row['task']} | `{row['cra_model']}` | "
            f"{markdown_value(row.get('cra_tail_accuracy_mean'))} | "
            f"{markdown_value(row.get('external_median_tail_accuracy'))} | "
            f"{markdown_value(row.get('best_external_tail_accuracy_mean'))} | "
            f"`{row.get('best_external_tail_model')}` | "
            f"{markdown_value(row.get('paired_tail_delta_vs_external_median_mean'))} | "
            f"{markdown_value(row.get('paired_tail_delta_vs_external_median_ci_low'))} | "
            f"{markdown_value(row.get('paired_tail_delta_vs_external_median_ci_high'))} | "
            f"{'yes' if row.get('robust_advantage_regime') else 'no'} | "
            f"{'yes' if row.get('not_dominated_by_best_external') else 'no'} |"
        )
    lines.extend(
        [
            "",
            "## Criteria",
            "",
            "| Criterion | Value | Rule | Pass | Note |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for item in result.criteria:
        lines.append(
            "| "
            f"{item['name']} | "
            f"{markdown_value(item['value'])} | "
            f"{item['operator']} {markdown_value(item['threshold'])} | "
            f"{'yes' if item['passed'] else 'no'} | "
            f"{item.get('note', '')} |"
        )
    if result.failure_reason:
        lines.extend(["", f"Failure: {result.failure_reason}"])
    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            "- `tier5_6_results.json`: machine-readable manifest.",
            "- `tier5_6_report.md`: this report.",
            "- `tier5_6_summary.csv`: aggregate task/model/run-length statistics.",
            "- `tier5_6_comparisons.csv`: CRA-vs-retuned-baseline paired comparison rows.",
            "- `tier5_6_best_profiles.csv`: best/median baseline settings by task/run length.",
            "- `tier5_6_candidate_budget.csv`: predeclared candidate budget.",
            "- `tier5_6_fairness_contract.json`: causal/fairness contract and full budget.",
            "- `tier5_6_per_seed.csv`: per-seed audit table.",
            "- `tier5_6_edge_summary.png`: CRA edge versus tuned external median.",
            "- `*_timeseries.csv`: per-run traces for reproducibility.",
            "",
            "## Plots",
            "",
            "![edge_summary](tier5_6_edge_summary.png)",
            "",
        ]
    )
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def run_tier(args: argparse.Namespace, output_dir: Path, run_lengths: list[int], cra_variants: list[VariantSpec]) -> TestResult:
    external_models = parse_external_models(args.models)
    candidate_specs = build_candidate_specs(external_models, args.budget, args.max_candidates_per_model)
    candidate_ids = [spec.candidate_id for spec in candidate_specs]
    spec_by_id = {spec.candidate_id: spec for spec in candidate_specs}
    cra_model_names = [variant.name for variant in cra_variants]
    summaries_by_cell: dict[tuple[int, str, str], list[dict[str, Any]]] = {}
    rows_by_cell_seed: dict[RunKey, list[dict[str, Any]]] = {}
    task_by_length_name_seed: dict[tuple[int, str, int], TaskStream] = {}
    artifacts: dict[str, str] = {}
    observed_runs = 0
    started = time.perf_counter()

    for run_length in run_lengths:
        length_args = copy.copy(args)
        length_args.steps = int(run_length)
        for seed in seeds_from_args(args):
            tasks = build_tasks(length_args, seed=length_args.task_seed + seed)
            for task in tasks:
                task_by_length_name_seed[(run_length, task.name, seed)] = task
                for variant in cra_variants:
                    print(f"[tier5.6] steps={run_length} task={task.name} model={variant.name} seed={seed}", flush=True)
                    rows, summary = run_cra_variant(task, seed=seed, variant=variant, args=length_args)
                    for row in rows:
                        row["run_length_steps"] = int(run_length)
                        row["model"] = variant.name
                        row["model_family"] = variant.group
                    summary = enrich_summary(summary, rows, args)
                    summary["run_length_steps"] = int(run_length)
                    summary["model"] = variant.name
                    summary["model_family"] = variant.group
                    csv_path = output_dir / f"steps{run_length}_{task.name}_{variant.name}_seed{seed}_timeseries.csv"
                    write_csv(csv_path, rows)
                    artifacts[f"steps{run_length}_{task.name}_{variant.name}_seed{seed}_timeseries_csv"] = str(csv_path)
                    summaries_by_cell.setdefault((run_length, task.name, variant.name), []).append(summary)
                    rows_by_cell_seed[RunKey(run_length, task.name, variant.name, seed)] = rows
                    observed_runs += 1
                for spec in candidate_specs:
                    print(f"[tier5.6] steps={run_length} task={task.name} candidate={spec.candidate_id} seed={seed}", flush=True)
                    profile_args = tuned_args(length_args, spec.overrides)
                    rows, summary = run_baseline_case(task, spec.base_model, seed=seed, args=profile_args)
                    for row in rows:
                        row["run_length_steps"] = int(run_length)
                        row["model"] = spec.candidate_id
                        row["base_model"] = spec.base_model
                        row["model_family"] = spec.family
                    summary = enrich_summary(summary, rows, args)
                    summary["run_length_steps"] = int(run_length)
                    summary["model"] = spec.candidate_id
                    summary["base_model"] = spec.base_model
                    summary["model_family"] = spec.family
                    summary["hyperparameter_overrides"] = spec.overrides
                    csv_path = output_dir / f"steps{run_length}_{task.name}_{spec.candidate_id}_seed{seed}_timeseries.csv"
                    write_csv(csv_path, rows)
                    artifacts[f"steps{run_length}_{task.name}_{spec.candidate_id}_seed{seed}_timeseries_csv"] = str(csv_path)
                    summaries_by_cell.setdefault((run_length, task.name, spec.candidate_id), []).append(summary)
                    rows_by_cell_seed[RunKey(run_length, task.name, spec.candidate_id, seed)] = rows
                    observed_runs += 1

    aggregates: list[dict[str, Any]] = []
    for (run_length, task_name, model), summaries in sorted(summaries_by_cell.items()):
        seed_rows = {
            int(summary["seed"]): rows_by_cell_seed[RunKey(run_length, task_name, model, int(summary["seed"]))]
            for summary in summaries
        }
        seed_tasks = {
            int(summary["seed"]): task_by_length_name_seed[(run_length, task_name, int(summary["seed"]))]
            for summary in summaries
        }
        model_family = next((variant.group for variant in cra_variants if variant.name == model), None)
        if model_family is None:
            model_family = spec_by_id[model].family
        aggregate = aggregate_cell(
            run_length=run_length,
            task_name=task_name,
            model=model,
            model_family=model_family,
            summaries=summaries,
            rows_by_seed=seed_rows,
            task_by_seed=seed_tasks,
            args=args,
        )
        if model in spec_by_id:
            aggregate["base_model"] = spec_by_id[model].base_model
            aggregate["hyperparameter_overrides"] = spec_by_id[model].overrides
        aggregates.append(aggregate)

    comparisons = build_comparisons(aggregates, summaries_by_cell, cra_model_names, candidate_ids, args)
    best_profiles = build_best_profile_rows(aggregates, candidate_specs)
    fairness_contract = build_fairness_contract(args, run_lengths, cra_variants, external_models, candidate_specs)
    criteria, tier_summary = evaluate_tier(
        aggregates=aggregates,
        comparisons=comparisons,
        best_profiles=best_profiles,
        observed_runs=observed_runs,
        run_lengths=run_lengths,
        cra_variants=cra_variants,
        candidate_specs=candidate_specs,
        args=args,
    )
    status, failure_reason = pass_fail(criteria)

    summary_csv = output_dir / "tier5_6_summary.csv"
    comparison_csv = output_dir / "tier5_6_comparisons.csv"
    best_profiles_csv = output_dir / "tier5_6_best_profiles.csv"
    candidate_budget_csv = output_dir / "tier5_6_candidate_budget.csv"
    per_seed_csv = output_dir / "tier5_6_per_seed.csv"
    fairness_json = output_dir / "tier5_6_fairness_contract.json"
    edge_plot = output_dir / "tier5_6_edge_summary.png"
    write_csv(summary_csv, aggregate_csv_rows(aggregates))
    write_csv(comparison_csv, comparison_csv_rows(comparisons))
    write_csv(best_profiles_csv, best_profiles)
    write_csv(candidate_budget_csv, candidate_budget_rows(candidate_specs))
    write_csv(per_seed_csv, per_seed_summary_rows(summaries_by_cell))
    write_json(fairness_json, json_safe(fairness_contract))
    plot_edge_summary(comparisons, edge_plot)

    result_artifacts = {
        "summary_csv": str(summary_csv),
        "comparisons_csv": str(comparison_csv),
        "best_profiles_csv": str(best_profiles_csv),
        "candidate_budget_csv": str(candidate_budget_csv),
        "per_seed_csv": str(per_seed_csv),
        "fairness_contract_json": str(fairness_json),
        "edge_summary_png": str(edge_plot) if edge_plot.exists() else "",
    }
    result_artifacts.update(artifacts)
    return TestResult(
        name="baseline_hyperparameter_fairness_audit",
        status=status,
        summary={
            "tier_summary": tier_summary,
            "aggregates": aggregates,
            "comparisons": comparisons,
            "best_profiles": best_profiles,
            "fairness_contract": fairness_contract,
            "models": cra_model_names + candidate_ids,
            "cra_variants": cra_model_names,
            "external_models": external_models,
            "candidate_ids": candidate_ids,
            "seeds": seeds_from_args(args),
            "tasks": selected_task_names(args.tasks),
            "run_lengths": run_lengths,
            "backend": args.backend,
            "runtime_seconds": time.perf_counter() - started,
            "claim_boundary": tier_summary["claim_boundary"],
        },
        criteria=criteria,
        artifacts=result_artifacts,
        failure_reason=failure_reason,
    )


def write_latest(output_dir: Path, report_path: Path, manifest_path: Path, summary_csv: Path, status: str) -> None:
    latest_path = ROOT / "controlled_test_output" / "tier5_6_latest_manifest.json"
    payload = {
        "generated_at_utc": utc_now(),
        "tier": TIER,
        "status": status,
        "output_dir": str(output_dir),
        "manifest": str(manifest_path),
        "report": str(report_path),
        "summary_csv": str(summary_csv),
        "canonical": False,
        "claim": "Latest Tier 5.6 tuned-baseline fairness audit; promote only after review.",
    }
    write_json(latest_path, payload)


def build_parser() -> argparse.ArgumentParser:
    parser = build_tier5_5_parser()
    parser.description = "Run Tier 5.6 tuned-baseline fairness audit."
    parser.set_defaults(
        backend="nest",
        tasks=DEFAULT_TASKS,
        models=DEFAULT_MODELS,
        seed_count=5,
        run_lengths=DEFAULT_RUN_LENGTHS,
        cra_variants="v0_8",
        cra_population_size=8,
        cra_delayed_readout_lr=0.20,
    )
    parser.add_argument("--budget", choices=["smoke", "standard"], default="standard")
    parser.add_argument("--max-candidates-per-model", type=int, default=0, help="Limit candidate profiles per external model; 0 means no limit.")
    parser.add_argument("--target-tasks", default="delayed_cue,hard_noisy_switching,sensor_control")
    parser.add_argument("--min-retuned-robust-regimes", type=int, default=1)
    parser.add_argument("--min-surviving-advantage-regimes", type=int, default=1)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.max_candidates_per_model <= 0:
        args.max_candidates_per_model = None
    run_lengths = parse_run_lengths(args.run_lengths)
    cra_variants = parse_cra_variants(args.cra_variants)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = args.output_dir or (ROOT / "controlled_test_output" / f"tier5_6_{timestamp}")
    output_dir.mkdir(parents=True, exist_ok=True)

    result = run_tier(args, output_dir, run_lengths, cra_variants)
    manifest_path = output_dir / "tier5_6_results.json"
    report_path = output_dir / "tier5_6_report.md"
    summary_csv = output_dir / "tier5_6_summary.csv"
    comparison_csv = output_dir / "tier5_6_comparisons.csv"
    best_profiles_csv = output_dir / "tier5_6_best_profiles.csv"
    candidate_budget_csv = output_dir / "tier5_6_candidate_budget.csv"
    per_seed_csv = output_dir / "tier5_6_per_seed.csv"
    fairness_json = output_dir / "tier5_6_fairness_contract.json"
    manifest = {
        "tier": TIER,
        "generated_at_utc": utc_now(),
        "output_dir": str(output_dir),
        "command": " ".join(sys.argv),
        "backend": args.backend,
        "status": result.status,
        "result": result.to_dict(),
        "summary": {
            **result.summary["tier_summary"],
            "backend": args.backend,
            "models": result.summary["models"],
            "cra_variants": result.summary["cra_variants"],
            "external_models": result.summary["external_models"],
            "candidate_ids": result.summary["candidate_ids"],
            "tasks": result.summary["tasks"],
            "seeds": result.summary["seeds"],
            "run_lengths": run_lengths,
            "runtime_seconds": result.summary["runtime_seconds"],
        },
        "artifacts": {
            "summary_csv": str(summary_csv),
            "comparisons_csv": str(comparison_csv),
            "best_profiles_csv": str(best_profiles_csv),
            "candidate_budget_csv": str(candidate_budget_csv),
            "per_seed_csv": str(per_seed_csv),
            "fairness_contract_json": str(fairness_json),
            "report_md": str(report_path),
            "edge_summary_png": str(output_dir / "tier5_6_edge_summary.png"),
        },
    }
    write_json(manifest_path, json_safe(manifest))
    write_report(
        report_path,
        result,
        result.summary["aggregates"],
        result.summary["comparisons"],
        result.summary["best_profiles"],
        result.summary["fairness_contract"],
        args,
        run_lengths,
        output_dir,
    )
    write_latest(output_dir, report_path, manifest_path, summary_csv, result.status)
    print(
        json.dumps(
            {
                "status": result.status,
                "output_dir": str(output_dir),
                "manifest": str(manifest_path),
                "report": str(report_path),
                "summary_csv": str(summary_csv),
                "comparisons_csv": str(comparison_csv),
                "best_profiles_csv": str(best_profiles_csv),
                "candidate_budget_csv": str(candidate_budget_csv),
                "per_seed_csv": str(per_seed_csv),
                "fairness_contract_json": str(fairness_json),
                "failure_reason": result.failure_reason,
            },
            indent=2,
        )
    )
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
