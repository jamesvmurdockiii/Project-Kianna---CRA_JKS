#!/usr/bin/env python3
"""Tier 5.14 working memory / context binding diagnostic.

Tier 5.14 is not a new baseline freeze by itself. It asks whether the frozen
v1.9 host-side software stack can hold context, cue history, active module
state, and pending subgoal/routing state across ambiguous gaps. The tier reuses
previously-audited task families, but evaluates them together under the broader
"working memory" question with reset/shuffle/no-write shams and standard
sequence baselines.

Claim boundary: software-only, host-side mechanisms only. This is not SpiNNaker
hardware evidence, not custom-C/on-chip working memory, not language, not
planning, and not AGI evidence.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import os
import sys
import time
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

import tier5_keyed_context_memory as kmem  # noqa: E402
import tier5_internal_composition_routing as internal  # noqa: E402
import tier5_module_routing as route  # noqa: E402
from tier2_learning import criterion, markdown_value, pass_fail, write_csv, write_json  # noqa: E402
from tier4_scaling import seeds_from_args  # noqa: E402
from tier5_external_baselines import parse_models  # noqa: E402


TIER = "Tier 5.14 - Working Memory / Context Binding"
DEFAULT_MEMORY_TASKS = "intervening_contexts,overlapping_contexts,context_reentry_interference"
DEFAULT_ROUTING_TASKS = "heldout_context_routing,distractor_router_chain,context_reentry_routing"
DEFAULT_MODELS = "sign_persistence,online_perceptron,online_logistic_regression,echo_state_network,small_gru,stdp_only_snn"
EPS = 1e-12


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


def make_memory_args(args: argparse.Namespace) -> argparse.Namespace:
    parser = kmem.build_parser()
    mem_args = parser.parse_args([])
    mem_args.backend = args.backend
    mem_args.tasks = args.memory_tasks
    mem_args.steps = args.memory_steps
    mem_args.seed_count = args.seed_count
    mem_args.seeds = args.seeds
    mem_args.base_seed = args.base_seed
    mem_args.models = args.models
    mem_args.variants = args.memory_variants
    mem_args.task_seed = args.task_seed
    mem_args.output_dir = None
    mem_args.stop_on_fail = args.stop_on_fail
    mem_args.smoke = bool(args.smoke)
    mem_args.cra_readout_lr = args.cra_readout_lr
    mem_args.cra_delayed_readout_lr = args.cra_delayed_readout_lr
    mem_args.cra_population_size = args.cra_population_size
    mem_args.amplitude = args.amplitude
    mem_args.dt_seconds = args.dt_seconds
    mem_args.message_passing_steps = args.message_passing_steps
    mem_args.message_context_gain = args.message_context_gain
    mem_args.message_prediction_mix = args.message_prediction_mix
    if args.smoke:
        mem_args.tasks = "intervening_contexts"
        mem_args.steps = min(int(mem_args.steps), int(args.smoke_memory_steps))
        mem_args.seed_count = 1
        mem_args.seeds = ""
        mem_args.models = "sign_persistence,online_perceptron"
        mem_args.smoke = True
    return mem_args


def make_routing_args(args: argparse.Namespace) -> argparse.Namespace:
    parser = internal.build_parser()
    routing_args = parser.parse_args([])
    routing_args.backend = args.backend
    routing_args.routing_tasks = args.routing_tasks
    routing_args.routing_steps = args.routing_steps
    routing_args.seed_count = args.seed_count
    routing_args.seeds = args.seeds
    routing_args.base_seed = args.base_seed
    routing_args.models = args.models
    routing_args.task_seed = args.task_seed
    routing_args.stop_on_fail = args.stop_on_fail
    routing_args.smoke = bool(args.smoke)
    routing_args.cra_readout_lr = args.cra_readout_lr
    routing_args.cra_delayed_readout_lr = args.cra_delayed_readout_lr
    routing_args.cra_population_size = args.cra_population_size
    routing_args.amplitude = args.amplitude
    routing_args.dt_seconds = args.dt_seconds
    routing_args.message_passing_steps = args.message_passing_steps
    routing_args.message_context_gain = args.message_context_gain
    routing_args.message_prediction_mix = args.message_prediction_mix
    routing_args.composition_prediction_gain = args.composition_prediction_gain
    routing_args.route_train_repeats = args.route_train_repeats
    routing_args.heldout_repeats = args.heldout_repeats
    routing_args.routing_gap = args.routing_gap
    routing_args.primitive_repeats = args.primitive_repeats
    if args.smoke:
        routing_args.routing_tasks = "heldout_context_routing"
        routing_args.routing_steps = min(int(routing_args.routing_steps), int(args.smoke_routing_steps))
        routing_args.seed_count = 1
        routing_args.seeds = ""
        routing_args.models = "sign_persistence,online_perceptron"
        routing_args.smoke = True
    return routing_args


def route_variants() -> list[internal.InternalVariant]:
    return internal.selected_internal_variants("routing")


def run_routing_subsuite(args: argparse.Namespace, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    models = parse_models(args.models)
    seeds = seeds_from_args(args)
    variants = route_variants()
    route_scaffold = next(v for v in route.VARIANTS if v.name == "contextual_router_scaffold")
    summaries_by_key: dict[tuple[str, str], list[dict[str, Any]]] = {}
    rows_by_cell_seed: dict[tuple[str, str, int], list[dict[str, Any]]] = {}
    tasks_by_name: dict[str, Any] = {}
    artifacts: dict[str, str] = {}
    started = time.perf_counter()

    task_args = copy.copy(args)
    task_args.tasks = args.routing_tasks
    task_args.steps = int(args.routing_steps)

    for seed in seeds:
        for task in route.build_tasks(task_args, seed=args.task_seed + seed):
            tasks_by_name[task.stream.name] = task
            for variant in variants:
                print(f"[tier5.14] subsuite=routing task={task.stream.name} variant={variant.name} seed={seed}", flush=True)
                rows, summary = internal.run_internal_routing(task, variant, seed=seed, args=args)
                csv_path = output_dir / f"routing_{task.stream.name}_{variant.name}_seed{seed}_timeseries.csv"
                write_csv(csv_path, rows)
                artifacts[f"routing_{task.stream.name}_{variant.name}_seed{seed}_timeseries_csv"] = str(csv_path)
                summaries_by_key.setdefault((task.stream.name, variant.name), []).append(summary)
                rows_by_cell_seed[(f"routing:{task.stream.name}", variant.name, seed)] = rows

            print(f"[tier5.14] subsuite=routing task={task.stream.name} scaffold={route_scaffold.name} seed={seed}", flush=True)
            rows, summary = route.run_rule_variant(task, route_scaffold, seed=seed, args=args)
            csv_path = output_dir / f"routing_{task.stream.name}_{route_scaffold.name}_seed{seed}_timeseries.csv"
            write_csv(csv_path, rows)
            artifacts[f"routing_{task.stream.name}_{route_scaffold.name}_seed{seed}_timeseries_csv"] = str(csv_path)
            summaries_by_key.setdefault((task.stream.name, route_scaffold.name), []).append(summary)
            rows_by_cell_seed[(f"routing:{task.stream.name}", route_scaffold.name, seed)] = rows

            for model in models:
                print(f"[tier5.14] subsuite=routing task={task.stream.name} model={model} seed={seed}", flush=True)
                rows, summary = route.run_external_model(task, model, seed=seed, args=args)
                csv_path = output_dir / f"routing_{task.stream.name}_{model}_seed{seed}_timeseries.csv"
                write_csv(csv_path, rows)
                artifacts[f"routing_{task.stream.name}_{model}_seed{seed}_timeseries_csv"] = str(csv_path)
                summaries_by_key.setdefault((task.stream.name, model), []).append(summary)
                rows_by_cell_seed[(f"routing:{task.stream.name}", model, seed)] = rows

    aggregates = [
        route.aggregate_runs(tasks_by_name[task_name], model, summaries)
        for (task_name, model), summaries in sorted(summaries_by_key.items())
    ]
    for row in aggregates:
        row["subsuite"] = "routing"
    comparisons = internal.build_comparisons(aggregates)
    leakage = internal.leakage_summary(rows_by_cell_seed)
    criteria, summary = evaluate_routing_subsuite(
        aggregates=aggregates,
        comparisons=comparisons,
        leakage=leakage,
        models=models,
        args=args,
        variants=variants,
    )
    status, failure_reason = pass_fail(criteria)

    summary_csv = output_dir / "tier5_14_routing_summary.csv"
    comparisons_csv = output_dir / "tier5_14_routing_comparisons.csv"
    plot_png = output_dir / "tier5_14_routing_edges.png"
    write_csv(summary_csv, internal.aggregate_csv_rows(aggregates))
    write_csv(comparisons_csv, comparisons)
    internal.plot_comparisons(plot_png, comparisons)
    artifacts.update(
        {
            "summary_csv": str(summary_csv),
            "comparisons_csv": str(comparisons_csv),
            "plot_png": str(plot_png),
        }
    )
    return {
        "name": "working_memory_routing_subsuite",
        "status": status,
        "failure_reason": failure_reason,
        "summary": {**summary, "runtime_seconds": time.perf_counter() - started},
        "criteria": criteria,
        "comparisons": comparisons,
        "aggregates": aggregates,
        "artifacts": artifacts,
    }


def evaluate_routing_subsuite(
    *,
    aggregates: list[dict[str, Any]],
    comparisons: list[dict[str, Any]],
    leakage: dict[str, Any],
    models: list[str],
    args: argparse.Namespace,
    variants: list[internal.InternalVariant],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    route_tasks = [item.strip() for item in args.routing_tasks.split(",") if item.strip()]
    seeds = seeds_from_args(args)
    expected_runs = len(seeds) * len(route_tasks) * (len(variants) + 1 + len(models))
    observed_runs = sum(int(row.get("runs", 0)) for row in aggregates)
    route_rows = [row for row in comparisons if row.get("subsuite") == "routing"]
    first_acc = [float(row.get("candidate_first_accuracy") or 0.0) for row in route_rows]
    heldout_acc = [float(row.get("candidate_heldout_accuracy") or 0.0) for row in route_rows]
    router_acc = [float(row.get("candidate_router_accuracy") or 0.0) for row in route_rows]
    raw_edges = [float(row.get("candidate_first_delta_vs_raw") or 0.0) for row in route_rows]
    ablation_edges = [float(row.get("candidate_first_delta_vs_best_ablation") or 0.0) for row in route_rows]
    standard_edges = [float(row.get("candidate_first_delta_vs_best_standard") or 0.0) for row in route_rows]
    router_updates = sum(float(row.get("candidate_router_updates") or 0.0) for row in route_rows)
    pre_feedback = sum(float(row.get("candidate_pre_feedback_select_steps") or 0.0) for row in route_rows)
    base = [
        criterion("routing task/variant/baseline/seed matrix completed", observed_runs, "==", expected_runs, observed_runs == expected_runs),
        criterion("routing feedback timing has no leakage violations", leakage.get("feedback_due_violations"), "==", 0, int(leakage.get("feedback_due_violations", 0)) == 0),
        criterion("routing mechanism receives context-router updates", router_updates, ">", 0, router_updates > 0),
        criterion("routing mechanism selects features before feedback", pre_feedback, ">", 0, pre_feedback > 0),
    ]
    science = [
        criterion("candidate reaches routing first-heldout threshold", min(first_acc) if first_acc else None, ">=", args.min_routing_first_accuracy, bool(first_acc) and min(first_acc) >= args.min_routing_first_accuracy),
        criterion("candidate reaches routing heldout threshold", min(heldout_acc) if heldout_acc else None, ">=", args.min_routing_heldout_accuracy, bool(heldout_acc) and min(heldout_acc) >= args.min_routing_heldout_accuracy),
        criterion("candidate route selection is correct", min(router_acc) if router_acc else None, ">=", args.min_routing_accuracy, bool(router_acc) and min(router_acc) >= args.min_routing_accuracy),
        criterion("candidate improves over routing-off CRA", min(raw_edges) if raw_edges else None, ">=", args.min_edge_vs_raw, bool(raw_edges) and min(raw_edges) >= args.min_edge_vs_raw),
        criterion("routing shams are worse than candidate", min(ablation_edges) if ablation_edges else None, ">=", args.min_edge_vs_ablation, bool(ablation_edges) and min(ablation_edges) >= args.min_edge_vs_ablation),
        criterion("candidate does not underperform selected sequence baselines", min(standard_edges) if standard_edges else None, ">=", -args.max_standard_regression, bool(standard_edges) and min(standard_edges) >= -args.max_standard_regression),
    ]
    criteria = base if args.smoke else base + science
    return criteria, {
        "expected_runs": expected_runs,
        "observed_runs": observed_runs,
        "routing_tasks": route_tasks,
        "seeds": seeds,
        "models": models,
        "leakage": leakage,
        "candidate_router_updates_sum": router_updates,
        "candidate_pre_feedback_select_steps_sum": pre_feedback,
    }


def memory_comparisons_from_result(memory_result: dict[str, Any]) -> list[dict[str, Any]]:
    summary = memory_result.get("summary", {})
    if isinstance(summary, dict):
        tier_summary = summary.get("tier_summary", {})
        comparisons = tier_summary.get("comparisons") or summary.get("comparisons")
        if isinstance(comparisons, list):
            return comparisons
    return []


def evaluate_combined(memory_result: dict[str, Any], routing_result: dict[str, Any], args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    memory_criteria = memory_result.get("criteria", [])
    routing_criteria = routing_result.get("criteria", [])
    memory_comparisons = memory_comparisons_from_result(memory_result)
    routing_comparisons = routing_result.get("comparisons", [])
    memory_status = str(memory_result.get("status", "unknown"))
    routing_status = str(routing_result.get("status", "unknown"))
    memory_edges_vs_ablation = [float(row.get("candidate_all_delta_vs_best_ablation") or 0.0) for row in memory_comparisons]
    memory_edges_vs_sign = [float(row.get("candidate_all_delta_vs_sign_persistence") or 0.0) for row in memory_comparisons]
    routing_edges_vs_ablation = [float(row.get("candidate_first_delta_vs_best_ablation") or 0.0) for row in routing_comparisons]
    routing_edges_vs_raw = [float(row.get("candidate_first_delta_vs_raw") or 0.0) for row in routing_comparisons]
    criteria = [
        criterion("memory/context-binding subsuite passed", memory_status, "==", "pass", memory_status == "pass"),
        criterion("module-state/routing subsuite passed", routing_status, "==", "pass", routing_status == "pass"),
        criterion(
            "context-memory shams lose somewhere on memory pressure",
            min(memory_edges_vs_ablation) if memory_edges_vs_ablation else None,
            ">=",
            args.min_memory_edge_vs_ablation,
            bool(memory_edges_vs_ablation) and min(memory_edges_vs_ablation) >= args.min_memory_edge_vs_ablation,
        ),
        criterion(
            "context-memory beats sign persistence on memory pressure",
            min(memory_edges_vs_sign) if memory_edges_vs_sign else None,
            ">=",
            args.min_memory_edge_vs_sign,
            bool(memory_edges_vs_sign) and min(memory_edges_vs_sign) >= args.min_memory_edge_vs_sign,
        ),
        criterion(
            "routing shams lose on delayed module-state pressure",
            min(routing_edges_vs_ablation) if routing_edges_vs_ablation else None,
            ">=",
            args.min_edge_vs_ablation,
            bool(routing_edges_vs_ablation) and min(routing_edges_vs_ablation) >= args.min_edge_vs_ablation,
        ),
        criterion(
            "routing beats routing-off CRA on delayed module-state pressure",
            min(routing_edges_vs_raw) if routing_edges_vs_raw else None,
            ">=",
            args.min_edge_vs_raw,
            bool(routing_edges_vs_raw) and min(routing_edges_vs_raw) >= args.min_edge_vs_raw,
        ),
    ]
    if args.smoke:
        criteria = criteria[:2]
    summary = {
        "memory_status": memory_status,
        "routing_status": routing_status,
        "memory_comparison_count": len(memory_comparisons),
        "routing_comparison_count": len(routing_comparisons),
        "claim_boundary": "Software diagnostic only: v1.9 host-side context memory and module routing under working-memory pressure; not hardware/on-chip, language, planning, or AGI evidence.",
    }
    return criteria, summary


def plot_combined(path: Path, memory_comparisons: list[dict[str, Any]], routing_comparisons: list[dict[str, Any]]) -> None:
    if plt is None:
        path.with_suffix(".txt").write_text(f"matplotlib unavailable: {MATPLOTLIB_ERROR}\n", encoding="utf-8")
        return
    labels: list[str] = []
    candidate: list[float] = []
    ablation: list[float] = []
    baseline: list[float] = []
    for row in memory_comparisons:
        labels.append("memory\n" + str(row.get("task", "")).replace("_", " "))
        candidate.append(float(row.get("candidate_all_accuracy") or 0.0))
        ablation.append(float(row.get("best_ablation_all_accuracy") or 0.0))
        baseline.append(float(row.get("best_standard_all_accuracy") or 0.0))
    for row in routing_comparisons:
        labels.append("routing\n" + str(row.get("task", "")).replace("_", " "))
        candidate.append(float(row.get("candidate_first_accuracy") or 0.0))
        ablation.append(float(row.get("best_ablation_first_accuracy") or 0.0))
        baseline.append(float(row.get("best_standard_first_accuracy") or 0.0))
    if not labels:
        path.with_suffix(".txt").write_text("no comparison rows to plot\n", encoding="utf-8")
        return
    x = np.arange(len(labels))
    width = 0.25
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.bar(x - width, ablation, width, label="best sham")
    ax.bar(x, baseline, width, label="best selected baseline")
    ax.bar(x + width, candidate, width, label="v1.9 working-memory stack")
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("accuracy")
    ax.set_title("Tier 5.14 working memory / context binding")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=25, ha="right")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def build_fairness_contract(args: argparse.Namespace, memory_args: argparse.Namespace, routing_args: argparse.Namespace) -> dict[str, Any]:
    return {
        "tier": TIER,
        "generated_at_utc": utc_now(),
        "candidate": "frozen v1.9 host-side software stack: keyed context memory plus internal composition/routing",
        "claim_boundary": "Tier 5.14 is a software diagnostic only; no hardware, on-chip memory, language, planning, or AGI claim.",
        "subsystems_under_test": [
            "context/cue binding across ambiguous delayed decisions",
            "multi-slot context retention under interference",
            "active module state and delayed contextual routing",
            "pending subgoal/module selection before feedback",
        ],
        "fairness_rules": [
            "All models receive the same stream, target, evaluation mask, and feedback_due_step arrays per seed.",
            "Candidate memory/routing features may use current visible context cues, but scored decision feedback must not be available before prediction.",
            "Reset, shuffled, wrong-key, no-write, random-router, and always-on shams must separate from the candidate before any promotion claim.",
            "External scaffolds/oracles are reported as upper bounds and are not promoted as internal CRA evidence.",
            "External sequence baselines are run on the same causal online streams with the same feedback schedule.",
        ],
        "memory_tasks": memory_args.tasks,
        "routing_tasks": routing_args.routing_tasks,
        "models": args.models,
        "seeds": seeds_from_args(args),
        "backend": args.backend,
        "smoke": bool(args.smoke),
    }


def write_report(path: Path, result: dict[str, Any], args: argparse.Namespace) -> None:
    memory = result["subresults"]["memory"]
    routing = result["subresults"]["routing"]
    memory_comparisons = result["comparisons"].get("memory", [])
    routing_comparisons = result["comparisons"].get("routing", [])
    lines = [
        "# Tier 5.14 Working Memory / Context Binding Findings",
        "",
        f"- Generated: `{result['generated_at_utc']}`",
        f"- Status: **{result['status'].upper()}**",
        f"- Backend: `{args.backend}`",
        f"- Seeds: `{args.seeds or 'seed_count=' + str(args.seed_count)}`",
        f"- Memory tasks: `{args.memory_tasks}`",
        f"- Routing tasks: `{args.routing_tasks}`",
        f"- Output directory: `{result['output_dir']}`",
        "",
        "Tier 5.14 asks whether the frozen v1.9 host-side software stack can maintain working state across time: context/cue memory, active module state, and pending subgoal/routing state.",
        "",
        "## Claim Boundary",
        "",
        "- Software diagnostic only.",
        "- Host-side mechanisms only; not native SpiNNaker/custom-C working memory.",
        "- Not language, long-horizon planning, AGI, or external-baseline superiority evidence.",
        "- A pass authorizes considering a v2.0 freeze only after compact regression; it does not freeze anything by itself.",
        "",
        "## Subsuite Status",
        "",
        f"- Memory/context binding: **{str(memory.get('status', 'unknown')).upper()}** `{memory.get('failure_reason', '')}`",
        f"- Module-state/routing: **{str(routing.get('status', 'unknown')).upper()}** `{routing.get('failure_reason', '')}`",
        "",
        "## Memory Comparisons",
        "",
        "| Task | Candidate acc | Best sham | Sham acc | Best baseline | Baseline acc | Edge vs sham | Edge vs sign |",
        "| --- | ---: | --- | ---: | --- | ---: | ---: | ---: |",
    ]
    for row in memory_comparisons:
        lines.append(
            "| {task} | {candidate_all_accuracy} | `{best_ablation_model}` | {best_ablation_all_accuracy} | `{best_standard_model}` | {best_standard_all_accuracy} | {candidate_all_delta_vs_best_ablation} | {candidate_all_delta_vs_sign_persistence} |".format(
                **{k: markdown_value(v) for k, v in row.items()}
            )
        )
    lines.extend(
        [
            "",
            "## Routing Comparisons",
            "",
            "| Task | Candidate first | Candidate heldout | Router acc | Best sham | Sham first | Best baseline | Baseline first | Edge vs raw | Edge vs sham |",
            "| --- | ---: | ---: | ---: | --- | ---: | --- | ---: | ---: | ---: |",
        ]
    )
    for row in routing_comparisons:
        lines.append(
            "| {task} | {candidate_first_accuracy} | {candidate_heldout_accuracy} | {candidate_router_accuracy} | `{best_ablation_model}` | {best_ablation_first_accuracy} | `{best_standard_model}` | {best_standard_first_accuracy} | {candidate_first_delta_vs_raw} | {candidate_first_delta_vs_best_ablation} |".format(
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
            "- `tier5_14_results.json`: machine-readable manifest.",
            "- `tier5_14_report.md`: human findings and claim boundary.",
            "- `tier5_14_fairness_contract.json`: fairness/leakage contract.",
            "- `tier5_14_working_memory_summary.png`: candidate/sham/baseline plot.",
            "- `memory_context_binding/`: reused keyed-context-memory traces and summaries.",
            "- `module_state_routing/`: delayed contextual-routing traces and summaries.",
            "",
            "![tier5_14](tier5_14_working_memory_summary.png)",
        ]
    )
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_latest(output_dir: Path, manifest_json: Path, report_md: Path, status: str) -> None:
    latest_path = ROOT / "controlled_test_output" / "tier5_14_latest_manifest.json"
    write_json(
        latest_path,
        {
            "tier": TIER,
            "status": status,
            "canonical": False,
            "output_dir": str(output_dir),
            "manifest_json": str(manifest_json),
            "report_md": str(report_md),
            "generated_at_utc": utc_now(),
        },
    )


def run_tier(args: argparse.Namespace, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    memory_args = make_memory_args(args)
    routing_args = make_routing_args(args)

    memory_dir = output_dir / "memory_context_binding"
    routing_dir = output_dir / "module_state_routing"
    memory_dir.mkdir(parents=True, exist_ok=True)
    routing_dir.mkdir(parents=True, exist_ok=True)

    memory_variants = kmem.parse_variants(memory_args.variants)
    print("[tier5.14] starting memory/context-binding subsuite", flush=True)
    memory_result = kmem.run_tier(memory_args, memory_dir, memory_variants)
    print("[tier5.14] starting module-state/routing subsuite", flush=True)
    routing_result = run_routing_subsuite(routing_args, routing_dir)

    criteria, summary = evaluate_combined(memory_result, routing_result, args)
    status, failure_reason = pass_fail(criteria)
    memory_comparisons = memory_comparisons_from_result(memory_result)
    routing_comparisons = routing_result.get("comparisons", [])

    fairness_json = output_dir / "tier5_14_fairness_contract.json"
    plot_png = output_dir / "tier5_14_working_memory_summary.png"
    report_md = output_dir / "tier5_14_report.md"
    manifest_json = output_dir / "tier5_14_results.json"
    write_json(fairness_json, build_fairness_contract(args, memory_args, routing_args))
    plot_combined(plot_png, memory_comparisons, routing_comparisons)

    result = {
        "tier": TIER,
        "generated_at_utc": utc_now(),
        "status": status,
        "failure_reason": failure_reason,
        "output_dir": str(output_dir),
        "command": " ".join(sys.argv),
        "summary": {**summary, "runtime_seconds": time.perf_counter() - started},
        "criteria": criteria,
        "comparisons": {"memory": memory_comparisons, "routing": routing_comparisons},
        "subresults": {"memory": memory_result, "routing": routing_result},
        "artifacts": {
            "manifest_json": str(manifest_json),
            "report_md": str(report_md),
            "fairness_contract_json": str(fairness_json),
            "plot_png": str(plot_png),
            "memory_output_dir": str(memory_dir),
            "routing_output_dir": str(routing_dir),
        },
    }
    write_json(manifest_json, json_safe(result))
    write_report(report_md, result, args)
    write_json(manifest_json, json_safe(result))
    write_latest(output_dir, manifest_json, report_md, status)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=TIER)
    parser.add_argument("--backend", default="mock")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--memory-tasks", default=DEFAULT_MEMORY_TASKS)
    parser.add_argument("--routing-tasks", default=DEFAULT_ROUTING_TASKS)
    parser.add_argument("--memory-steps", type=int, default=720)
    parser.add_argument("--routing-steps", type=int, default=960)
    parser.add_argument("--seed-count", type=int, default=3)
    parser.add_argument("--seeds", default="")
    parser.add_argument("--base-seed", type=int, default=42)
    parser.add_argument("--models", default=DEFAULT_MODELS)
    parser.add_argument("--memory-variants", default=kmem.DEFAULT_VARIANTS)
    parser.add_argument("--task-seed", type=int, default=0)
    parser.add_argument("--amplitude", type=float, default=0.01)
    parser.add_argument("--dt-seconds", type=float, default=60.0)
    parser.add_argument("--cra-population-size", type=int, default=8)
    parser.add_argument("--cra-readout-lr", type=float, default=0.10)
    parser.add_argument("--cra-delayed-readout-lr", type=float, default=0.20)
    parser.add_argument("--message-passing-steps", type=int, default=2)
    parser.add_argument("--message-context-gain", type=float, default=0.35)
    parser.add_argument("--message-prediction-mix", type=float, default=0.25)
    parser.add_argument("--composition-prediction-gain", type=float, default=100.0)
    parser.add_argument("--primitive-repeats", type=int, default=4)
    parser.add_argument("--route-train-repeats", type=int, default=4)
    parser.add_argument("--heldout-repeats", type=int, default=5)
    parser.add_argument("--routing-gap", type=int, default=10)
    parser.add_argument("--min-routing-first-accuracy", type=float, default=0.95)
    parser.add_argument("--min-routing-heldout-accuracy", type=float, default=0.95)
    parser.add_argument("--min-routing-accuracy", type=float, default=0.95)
    parser.add_argument("--min-edge-vs-raw", type=float, default=0.20)
    parser.add_argument("--min-edge-vs-ablation", type=float, default=0.20)
    parser.add_argument("--max-standard-regression", type=float, default=0.01)
    parser.add_argument("--min-memory-edge-vs-ablation", type=float, default=0.10)
    parser.add_argument("--min-memory-edge-vs-sign", type=float, default=0.20)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--smoke-memory-steps", type=int, default=240)
    parser.add_argument("--smoke-routing-steps", type=int, default=760)
    parser.add_argument("--stop-on-fail", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_dir = args.output_dir or (ROOT / "controlled_test_output" / f"tier5_14_{stamp}")
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
        manifest_json = output_dir / "tier5_14_results.json"
        report_md = output_dir / "tier5_14_report.md"
        write_json(manifest_json, json_safe(failure))
        report_md.write_text(
            f"# Tier 5.14 Working Memory / Context Binding Findings\n\nStatus: **BLOCKED**\n\nFailure: {exc}\n",
            encoding="utf-8",
        )
        print(json.dumps(json_safe(failure), indent=2), file=sys.stderr)
        return 2
    print(json.dumps(json_safe({"status": result["status"], "output_dir": result["output_dir"], "failure_reason": result.get("failure_reason")}), indent=2))
    if result["status"] != "pass" and args.stop_on_fail:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
