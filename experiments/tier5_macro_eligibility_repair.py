#!/usr/bin/env python3
"""Tier 5.9b residual macro-eligibility repair diagnostic.

Tier 5.9a proved that replacing the v1.4 PendingHorizon feature with a macro
trace was too destructive. Tier 5.9b tests the narrow repair: preserve the v1.4
feature and add only a bounded residual trace term. A pass here would justify
compact regression; it still would not be hardware or native-C evidence.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from tier2_learning import markdown_value, pass_fail, write_csv, write_json  # noqa: E402
from tier4_scaling import seeds_from_args  # noqa: E402
from tier5_external_baselines import LEARNER_FACTORIES, parse_models, run_baseline_case  # noqa: E402
from tier5_macro_eligibility import (  # noqa: E402
    DEFAULT_MODELS,
    DEFAULT_TASKS,
    VariantSpec,
    aggregate_csv_rows,
    aggregate_runs,
    build_comparisons,
    build_parser as build_5_9a_parser,
    build_tasks,
    evaluate_tier,
    json_safe,
    leakage_summary,
    plot_macro_comparisons,
    run_cra_variant,
    utc_now,
)


TIER = "Tier 5.9b - Residual Macro Eligibility Repair Diagnostic"
DEFAULT_VARIANTS = "v1_4_pending_horizon,macro_eligibility,macro_eligibility_shuffled,macro_eligibility_zero"


def build_repair_variants(args: argparse.Namespace) -> list[VariantSpec]:
    all_variants = (
        VariantSpec(
            name="v1_4_pending_horizon",
            group="frozen_baseline",
            hypothesis="Frozen v1.4 delayed-credit path: PendingHorizon with delayed_lr_0_20 and no macro trace.",
            overrides={
                "learning.delayed_readout_learning_rate": 0.20,
                "learning.macro_eligibility_enabled": False,
            },
        ),
        VariantSpec(
            name="macro_eligibility",
            group="candidate",
            hypothesis="Tier 5.9b repair: preserve PendingHorizon and add a bounded residual macro trace.",
            overrides={
                "learning.delayed_readout_learning_rate": 0.20,
                "learning.macro_eligibility_enabled": True,
                "learning.macro_eligibility_trace_mode": "normal",
                "learning.macro_eligibility_credit_mode": "residual",
                "learning.macro_eligibility_decay": float(args.repair_decay),
                "learning.macro_eligibility_residual_scale": float(args.repair_residual_scale),
                "learning.macro_eligibility_trace_clip": float(args.repair_trace_clip),
                "learning.macro_eligibility_learning_rate_scale": 1.0,
            },
        ),
        VariantSpec(
            name="macro_eligibility_shuffled",
            group="trace_ablation",
            hypothesis="Control: residual trace is assigned to the wrong polyp while the PendingHorizon base remains intact.",
            overrides={
                "learning.delayed_readout_learning_rate": 0.20,
                "learning.macro_eligibility_enabled": True,
                "learning.macro_eligibility_trace_mode": "shuffled",
                "learning.macro_eligibility_credit_mode": "residual",
                "learning.macro_eligibility_decay": float(args.repair_decay),
                "learning.macro_eligibility_residual_scale": float(args.repair_residual_scale),
                "learning.macro_eligibility_trace_clip": float(args.repair_trace_clip),
                "learning.macro_eligibility_learning_rate_scale": 1.0,
            },
        ),
        VariantSpec(
            name="macro_eligibility_zero",
            group="trace_ablation",
            hypothesis="Control: residual macro path is enabled but the trace contribution is zeroed, leaving the PendingHorizon base.",
            overrides={
                "learning.delayed_readout_learning_rate": 0.20,
                "learning.macro_eligibility_enabled": True,
                "learning.macro_eligibility_trace_mode": "zero",
                "learning.macro_eligibility_credit_mode": "residual",
                "learning.macro_eligibility_decay": float(args.repair_decay),
                "learning.macro_eligibility_residual_scale": float(args.repair_residual_scale),
                "learning.macro_eligibility_trace_clip": float(args.repair_trace_clip),
                "learning.macro_eligibility_learning_rate_scale": 1.0,
            },
        ),
    )
    names = [item.strip() for item in args.variants.split(",") if item.strip()]
    if not names or names == ["all"]:
        return list(all_variants)
    by_name = {variant.name: variant for variant in all_variants}
    missing = [name for name in names if name not in by_name]
    if missing:
        raise argparse.ArgumentTypeError(f"unknown Tier 5.9b variants: {', '.join(missing)}")
    selected = [by_name[name] for name in names]
    required = {"v1_4_pending_horizon", "macro_eligibility"}
    present = {variant.name for variant in selected}
    if not required.issubset(present):
        raise argparse.ArgumentTypeError("Tier 5.9b requires v1_4_pending_horizon and macro_eligibility")
    return selected


def fairness_contract(args: argparse.Namespace, variants: list[VariantSpec], models: list[str]) -> dict[str, Any]:
    return {
        "tier": TIER,
        "frozen_comparator": "v1_4_pending_horizon",
        "candidate": "macro_eligibility",
        "repair_hypothesis": "bounded residual trace added to v1.4 PendingHorizon feature",
        "repair_decay": args.repair_decay,
        "repair_residual_scale": args.repair_residual_scale,
        "repair_trace_clip": args.repair_trace_clip,
        "ablation_controls": [variant.name for variant in variants if variant.group == "trace_ablation"],
        "selected_external_baselines": models,
        "fairness_rules": [
            "same task stream per seed for CRA variants and selected baselines",
            "v1.4 PendingHorizon remains the base update in residual variants",
            "models predict before consequence feedback matures",
            "feedback_due_step must be greater than or equal to prediction step",
            "normal residual trace must beat shuffled/zero trace before promotion",
            "delayed_cue nonregression is mandatory before hard-switch recovery wins count",
            "passing Tier 5.9b only authorizes compact regression, not hardware or custom C",
        ],
        "tasks": args.tasks,
        "steps": args.steps,
        "seeds": seeds_from_args(args),
        "backend": args.backend,
    }


def run_tier(args: argparse.Namespace, output_dir: Path, variants: list[VariantSpec]):
    models = parse_models(args.models)
    summaries_by_cell: dict[tuple[str, str], list[dict[str, Any]]] = {}
    rows_by_cell_seed: dict[tuple[str, str, int], list[dict[str, Any]]] = {}
    task_by_name: dict[str, Any] = {}
    task_by_name_seed: dict[tuple[str, int], Any] = {}
    artifacts: dict[str, str] = {}
    started = time.perf_counter()

    for seed in seeds_from_args(args):
        tasks = build_tasks(args, seed=args.task_seed + seed)
        for task in tasks:
            task_by_name[task.name] = task
            task_by_name_seed[(task.name, seed)] = task
            for variant in variants:
                print(f"[tier5.9b] task={task.name} variant={variant.name} seed={seed}", flush=True)
                rows, summary = run_cra_variant(task, seed=seed, variant=variant, args=args)
                csv_path = output_dir / f"{task.name}_{variant.name}_seed{seed}_timeseries.csv"
                write_csv(csv_path, rows)
                artifacts[f"{task.name}_{variant.name}_seed{seed}_timeseries_csv"] = str(csv_path)
                summaries_by_cell.setdefault((task.name, variant.name), []).append(summary)
                rows_by_cell_seed[(task.name, variant.name, seed)] = rows
            for model in models:
                print(f"[tier5.9b] task={task.name} baseline={model} seed={seed}", flush=True)
                rows, summary = run_baseline_case(task, model, seed=seed, args=args)
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
        seed_tasks = {int(s["seed"]): task_by_name_seed[(task_name, int(s["seed"]))] for s in summaries}
        family = "CRA" if model in variant_by_name else LEARNER_FACTORIES[model].family
        aggregates.append(
            aggregate_runs(
                task=task,
                model=model,
                family=family,
                summaries=summaries,
                rows_by_seed=seed_rows,
                tasks_by_seed=seed_tasks,
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

    summary_csv = output_dir / "tier5_9b_summary.csv"
    comparison_csv = output_dir / "tier5_9b_comparisons.csv"
    fairness_json = output_dir / "tier5_9b_fairness_contract.json"
    plot_path = output_dir / "tier5_9b_macro_edges.png"
    write_csv(summary_csv, aggregate_csv_rows(aggregates))
    write_csv(comparison_csv, comparisons)
    write_json(fairness_json, fairness_contract(args, variants, models))
    plot_macro_comparisons(comparisons, plot_path)

    result = {
        "name": "residual_macro_eligibility_repair",
        "status": status,
        "summary": {
            "tier_summary": tier_summary,
            "aggregates": aggregates,
            "comparisons": comparisons,
            "fairness_contract": fairness_contract(args, variants, models),
            "runtime_seconds": time.perf_counter() - started,
        },
        "criteria": criteria,
        "artifacts": {
            "summary_csv": str(summary_csv),
            "comparisons_csv": str(comparison_csv),
            "fairness_contract_json": str(fairness_json),
            "macro_edges_png": str(plot_path) if plot_path.exists() else "",
            **artifacts,
        },
        "failure_reason": failure_reason,
    }
    return result


def write_report(path: Path, result: dict[str, Any], args: argparse.Namespace, output_dir: Path) -> None:
    overall = "PASS" if result["status"] == "pass" else "FAIL"
    comparisons = result["summary"]["comparisons"]
    aggregates = result["summary"]["aggregates"]
    lines = [
        "# Tier 5.9b Residual Macro Eligibility Repair Findings",
        "",
        f"- Generated: `{utc_now()}`",
        f"- Status: **{overall}**",
        f"- Backend: `{args.backend}`",
        f"- Steps: `{args.steps}`",
        f"- Seeds: `{', '.join(str(s) for s in seeds_from_args(args))}`",
        f"- Tasks: `{args.tasks}`",
        f"- Repair residual scale: `{args.repair_residual_scale}`",
        f"- Repair trace clip: `{args.repair_trace_clip}`",
        f"- Repair decay: `{args.repair_decay}`",
        f"- Output directory: `{output_dir}`",
        "",
        "Tier 5.9b tests the narrow repair after 5.9a failed: keep the v1.4 PendingHorizon feature and add only a bounded macro-trace residual.",
        "",
        "## Claim Boundary",
        "",
        "- This is software diagnostic evidence, not hardware evidence.",
        "- A pass would authorize compact regression only, not SpiNNaker/custom-C migration.",
        "- A fail means the macro-credit mechanism remains unearned; v1.4 stays frozen.",
        "",
        "## Task Comparisons",
        "",
        "| Task | v1.4 tail | Residual tail | Tail delta | Corr delta | Recovery delta | Best ablation | Residual-ablation delta | Trace active | Matured updates |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |",
    ]
    for row in comparisons:
        lines.append(
            "| "
            f"{row['task']} | {markdown_value(row.get('baseline_tail_accuracy_mean'))} | "
            f"{markdown_value(row.get('macro_tail_accuracy_mean'))} | "
            f"{markdown_value(row.get('macro_tail_delta_vs_v1_4'))} | "
            f"{markdown_value(row.get('macro_abs_corr_delta_vs_v1_4'))} | "
            f"{markdown_value(row.get('macro_recovery_delta_vs_v1_4'))} | "
            f"`{row.get('best_ablation_model')}` | "
            f"{markdown_value(row.get('macro_composite_delta_vs_best_ablation'))} | "
            f"{markdown_value(row.get('macro_trace_active_steps_sum'))} | "
            f"{markdown_value(row.get('macro_matured_updates_sum'))} |"
        )
    lines.extend(["", "## Aggregate Matrix", "", "| Task | Model | Family | Group | Tail acc | Corr | Recovery | Runtime s | Matured updates |", "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |"])
    for row in sorted(aggregates, key=lambda r: (r["task"], r.get("model_family") != "CRA", r["model"])):
        lines.append(
            "| "
            f"{row['task']} | `{row['model']}` | {row.get('model_family')} | {row.get('variant_group') or ''} | "
            f"{markdown_value(row.get('tail_accuracy_mean'))} | "
            f"{markdown_value(row.get('prediction_target_corr_mean'))} | "
            f"{markdown_value(row.get('mean_recovery_steps'))} | "
            f"{markdown_value(row.get('runtime_seconds_mean'))} | "
            f"{markdown_value(row.get('macro_matured_updates_sum_sum'))} |"
        )
    lines.extend(["", "## Criteria", "", "| Criterion | Value | Rule | Pass | Note |", "| --- | --- | --- | --- | --- |"])
    for item in result["criteria"]:
        lines.append(
            "| "
            f"{item['name']} | {markdown_value(item['value'])} | "
            f"{item['operator']} {markdown_value(item['threshold'])} | "
            f"{'yes' if item['passed'] else 'no'} | {item.get('note', '')} |"
        )
    if result["failure_reason"]:
        lines.extend(["", f"Failure: {result['failure_reason']}"])
    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            "- `tier5_9b_results.json`: machine-readable manifest.",
            "- `tier5_9b_report.md`: human findings and claim boundary.",
            "- `tier5_9b_summary.csv`: aggregate task/model metrics.",
            "- `tier5_9b_comparisons.csv`: repair-vs-v1.4/ablation/baseline table.",
            "- `tier5_9b_fairness_contract.json`: predeclared comparison and leakage constraints.",
            "- `tier5_9b_macro_edges.png`: residual macro edge plot.",
            "- `*_timeseries.csv`: per-run traces.",
            "",
            "![macro_edges](tier5_9b_macro_edges.png)",
            "",
        ]
    )
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_latest(output_dir: Path, report_path: Path, manifest_path: Path, summary_csv: Path, status: str) -> None:
    latest_path = ROOT / "controlled_test_output" / "tier5_9b_latest_manifest.json"
    write_json(
        latest_path,
        {
            "generated_at_utc": utc_now(),
            "tier": TIER,
            "status": status,
            "output_dir": str(output_dir),
            "manifest": str(manifest_path),
            "report": str(report_path),
            "summary_csv": str(summary_csv),
            "canonical": False,
            "claim": "Latest Tier 5.9b residual macro-eligibility repair diagnostic; promote only after pass plus compact regression.",
        },
    )


def build_parser() -> argparse.ArgumentParser:
    parser = build_5_9a_parser()
    parser.description = "Run Tier 5.9b residual macro-eligibility repair diagnostics."
    parser.set_defaults(
        backend="nest",
        tasks=DEFAULT_TASKS,
        steps=960,
        seed_count=3,
        models=DEFAULT_MODELS,
        variants=DEFAULT_VARIANTS,
        cra_population_size=8,
        cra_readout_lr=0.10,
        cra_delayed_readout_lr=0.20,
        max_delayed_tail_regression=0.02,
        min_hard_tail_delta=0.0,
        min_hard_recovery_delta=1.0,
        min_hard_variance_reduction=0.01,
        min_variable_delay_tail_delta=0.0,
        min_variable_delay_corr_delta=0.0,
        min_ablation_composite_delta=0.005,
    )
    parser.add_argument("--repair-residual-scale", type=float, default=0.10)
    parser.add_argument("--repair-trace-clip", type=float, default=1.0)
    parser.add_argument("--repair-decay", type=float, default=0.92)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    variants = build_repair_variants(args)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = args.output_dir or (ROOT / "controlled_test_output" / f"tier5_9b_{timestamp}")
    output_dir.mkdir(parents=True, exist_ok=True)

    result = run_tier(args, output_dir, variants)
    manifest_path = output_dir / "tier5_9b_results.json"
    report_path = output_dir / "tier5_9b_report.md"
    summary_csv = output_dir / "tier5_9b_summary.csv"
    comparison_csv = output_dir / "tier5_9b_comparisons.csv"
    fairness_json = output_dir / "tier5_9b_fairness_contract.json"
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
            "macro_edges_png": str(output_dir / "tier5_9b_macro_edges.png"),
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
