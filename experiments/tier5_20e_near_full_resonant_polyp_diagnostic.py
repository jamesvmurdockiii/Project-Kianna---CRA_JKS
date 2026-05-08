#!/usr/bin/env python3
"""Tier 5.20e - Near-Full Resonant Hybrid LIF Polyp Diagnostic.

Tier 5.20b showed that 8/8 and 12/4 hybrid resonant/LIF polyp proxies still
regressed too much versus v2.3. This final resonant-dose check tests the
near-full resonant specialist allocation:

* 2 standard bounded recurrent/LIF-style excitatory units + 14 resonant branches

The point is to ask whether a near-full resonant specialist subpool can preserve
broad v2.3 behavior while keeping any variable-delay/anomaly benefit. This is a
software diagnostic only, not a baseline freeze or hardware transfer.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "controlled_test_output"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from tier5_19a_temporal_substrate_reference import (  # noqa: E402
    append_timeseries,
    criterion,
    json_safe,
    random_reservoir_features,
    run_online_model,
    run_train_prefix_esn,
    summarize,
    write_json,
)
from tier5_19b_temporal_substrate_gate import temporal_features_variant  # noqa: E402
from tier5_20a_resonant_branch_polyp_diagnostic import resonant_branch_features  # noqa: E402
from tier5_20b_hybrid_resonant_polyp_diagnostic import (  # noqa: E402
    DEFAULT_TASKS,
    ESN,
    FULL_RESONANT,
    LAG,
    RESERVOIR,
    V22,
    V23,
    build_task,
    evaluate_candidate,
    hybrid_features,
    write_csv_rows,
)
from tier7_0_standard_dynamical_benchmarks import parse_csv, parse_seeds  # noqa: E402
from tier7_0b_continuous_regression_failure_analysis import lag_matrix  # noqa: E402


TIER = "Tier 5.20e - Near-Full Resonant Hybrid LIF Polyp Diagnostic"
RUNNER_REVISION = "tier5_20e_near_full_resonant_polyp_diagnostic_20260508_0001"
DEFAULT_OUTPUT_DIR = OUTPUT_ROOT / "tier5_20e_20260508_near_full_resonant_polyp_diagnostic"

HYBRID_2_14 = "hybrid_2_lif_14_resonant"
HYBRID_2_14_FLAT = "hybrid_2_lif_14_flat_tau_sham"
HYBRID_2_14_RATE = "hybrid_2_lif_14_rate_only_sham"
HYBRID_2_14_SHUFFLED = "hybrid_2_lif_14_shuffled_branch_sham"
REQUIRED_MODELS = [
    V23,
    V22,
    FULL_RESONANT,
    HYBRID_2_14,
    HYBRID_2_14_FLAT,
    HYBRID_2_14_RATE,
    HYBRID_2_14_SHUFFLED,
    LAG,
    RESERVOIR,
    ESN,
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_task_models(task: Any, *, seed: int, args: argparse.Namespace, capture_timeseries: bool) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    timeseries: list[dict[str, Any]] = []
    temporal_kwargs = {
        "seed": seed,
        "train_end": task.train_end,
        "timescales": [2.0, 4.0, 8.0, 16.0, 32.0, 64.0, 128.0],
        "recurrent_scale": float(args.temporal_recurrent_scale),
        "input_scale": float(args.temporal_input_scale),
        "hidden_decay": float(args.temporal_hidden_decay),
    }
    model_bundles = {
        V23: temporal_features_variant(task.observed, hidden_units=16, mode="full", **temporal_kwargs),
        V22: temporal_features_variant(task.observed, hidden_units=16, mode="fading_only", **temporal_kwargs),
        FULL_RESONANT: resonant_branch_features(
            task.observed,
            seed=seed,
            train_end=task.train_end,
            branch_count=16,
            mode="resonant",
            max_delay=int(args.max_branch_delay),
            gain=float(args.branch_gain),
        ),
        HYBRID_2_14: hybrid_features(task.observed, seed=seed, train_end=task.train_end, lif_units=2, branch_count=14, branch_mode="resonant", args=args),
        HYBRID_2_14_FLAT: hybrid_features(task.observed, seed=seed, train_end=task.train_end, lif_units=2, branch_count=14, branch_mode="flat_tau", args=args),
        HYBRID_2_14_RATE: hybrid_features(task.observed, seed=seed, train_end=task.train_end, lif_units=2, branch_count=14, branch_mode="rate_only", args=args),
        HYBRID_2_14_SHUFFLED: hybrid_features(task.observed, seed=seed, train_end=task.train_end, lif_units=2, branch_count=14, branch_mode="shuffled", args=args),
    }
    lag = lag_matrix(task.observed, int(args.history))
    reservoir = random_reservoir_features(
        task.observed,
        seed=seed,
        units=int(args.reservoir_units),
        spectral_radius=float(args.reservoir_spectral_radius),
        input_scale=float(args.reservoir_input_scale),
    )
    model_specs: list[tuple[str, np.ndarray, dict[str, Any]]] = [
        *[(name, bundle.features, bundle.diagnostics) for name, bundle in model_bundles.items()],
        (LAG, lag, {"state_location": "causal_lag_matrix", "history": int(args.history)}),
        (RESERVOIR, reservoir.features, reservoir.diagnostics),
    ]
    for model, features, diagnostics in model_specs:
        row, pred = run_online_model(
            task=task,
            seed=seed,
            model=model,
            features=features,
            args=args,
            diagnostics=diagnostics,
        )
        rows.append(row)
        if capture_timeseries:
            append_timeseries(timeseries, task=task, seed=seed, model=model, prediction=pred)
    esn_row, esn_pred = run_train_prefix_esn(task, seed=seed, args=args)
    rows.append(esn_row)
    if capture_timeseries:
        append_timeseries(timeseries, task=task, seed=seed, model=ESN, prediction=esn_pred)
    diagnostics = {
        "task": task.name,
        "seed": int(seed),
        "same_budget_variant": "2_lif_14_resonant",
        "v23_feature_count": int(model_bundles[V23].features.shape[1]),
        "hybrid_2_14_feature_count": int(model_bundles[HYBRID_2_14].features.shape[1]),
    }
    return rows, timeseries, diagnostics


def classify(summary_rows: list[dict[str, Any]], aggregate_summary: list[dict[str, Any]], tasks: list[str]) -> dict[str, Any]:
    candidate = evaluate_candidate(
        candidate=HYBRID_2_14,
        shams=[HYBRID_2_14_FLAT, HYBRID_2_14_RATE, HYBRID_2_14_SHUFFLED],
        tasks=tasks,
        summary_rows=summary_rows,
        aggregate_summary=aggregate_summary,
    )
    if candidate["useful_signal"] and candidate["no_material_regression_vs_v2_3"]:
        outcome = "near_full_resonant_candidate_for_integration_gate"
        recommendation = "Proceed to optional-polyp integration gate for 2 LIF / 14 resonant branches."
    elif candidate["no_material_regression_vs_v2_3"] and candidate["sham_separation_count"] >= 1:
        outcome = "near_full_resonant_research_scaffold_not_promoted"
        recommendation = "Keep 2/14 as a documented scaffold; do not integrate until stronger task value appears."
    else:
        outcome = "near_full_resonant_not_promoted"
        recommendation = "Do not integrate the 2/14 resonant variant into the core organism."
    return {
        "outcome": outcome,
        "recommendation": recommendation,
        "candidate": candidate,
    }


def write_report(path: Path, payload: dict[str, Any]) -> None:
    classification = payload["classification"]
    candidate = classification["candidate"]
    lines = [
        f"# {TIER}",
        "",
        f"- Generated: `{payload['generated_at_utc']}`",
        f"- Status: **{payload['status'].upper()}**",
        f"- Output directory: `{payload['output_dir']}`",
        f"- Outcome: `{classification['outcome']}`",
        "",
        "## Claim Boundary",
        "",
        payload["claim_boundary"],
        "",
        "## Summary",
        "",
        f"- Recommendation: {classification['recommendation']}",
        f"- All-task candidate geomean MSE: `{candidate['all_tasks_candidate_geomean_mse']}`",
        f"- All-task v2.3 geomean MSE: `{candidate['all_tasks_v2_3_geomean_mse']}`",
        f"- Margin vs v2.3: `{candidate['all_tasks_candidate_vs_v2_3_margin']}`",
        f"- Wins vs v2.3: `{candidate['wins_vs_v2_3_count']}`",
        f"- Material regressions vs v2.3: `{candidate['material_regression_count_vs_v2_3']}`",
        f"- Sham-separated tasks: `{candidate['sham_separation_count']}`",
        "",
        "## Criteria",
        "",
        "| Criterion | Value | Rule | Pass |",
        "| --- | --- | --- | --- |",
    ]
    for item in payload["criteria"]:
        lines.append(f"| {item['name']} | `{item['value']}` | {item['rule']} | {'yes' if item['passed'] else 'no'} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    started = time.perf_counter()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    tasks = parse_csv(args.tasks)
    seeds = parse_seeds(args)
    all_rows: list[dict[str, Any]] = []
    all_timeseries: list[dict[str, Any]] = []
    task_diagnostics: list[dict[str, Any]] = []
    capture_timeseries = not bool(args.no_timeseries)
    for seed in seeds:
        for task_name in tasks:
            task = build_task(task_name, int(args.length), seed, int(args.horizon))
            rows, timeseries, diagnostics = run_task_models(task, seed=seed, args=args, capture_timeseries=capture_timeseries)
            all_rows.extend(rows)
            all_timeseries.extend(timeseries)
            task_diagnostics.append(diagnostics)
            write_json(
                output_dir / f"{task.name}_seed{seed}_task.json",
                {
                    "task": task.name,
                    "display_name": task.display_name,
                    "seed": int(seed),
                    "length": int(len(task.target)),
                    "train_end": int(task.train_end),
                    "horizon": int(task.horizon),
                    "metadata": task.metadata,
                },
            )
    models = sorted({row["model"] for row in all_rows})
    summary_rows, aggregate_rows, aggregate_summary = summarize(all_rows, tasks, models, seeds)
    classification = classify(summary_rows, aggregate_summary, tasks)
    criteria = [
        criterion("runner revision current", RUNNER_REVISION, "expected current source", RUNNER_REVISION.endswith("_0001")),
        criterion("Tier 5.20b hybrid diagnostic present", "tier5_20b", "results exist", (OUTPUT_ROOT / "tier5_20b_20260508_hybrid_resonant_polyp_diagnostic" / "tier5_20b_results.json").exists()),
        criterion("same budget 2/14 variant declared", "2 LIF + 14 resonant", "sum == 16 excitatory units", True),
        criterion("all required models present", sorted(REQUIRED_MODELS), "all present", all(model in models for model in REQUIRED_MODELS)),
        criterion("all runs completed", f"{sum(r['status'] == 'pass' for r in all_rows)}/{len(all_rows)}", "all pass", all(r["status"] == "pass" for r in all_rows)),
        criterion("2/14 shams present", [HYBRID_2_14_FLAT, HYBRID_2_14_RATE, HYBRID_2_14_SHUFFLED], "all present", all(model in models for model in [HYBRID_2_14_FLAT, HYBRID_2_14_RATE, HYBRID_2_14_SHUFFLED])),
        criterion("public standard tasks included", ["mackey_glass", "lorenz", "narma10"], "all included", all(task in tasks for task in ["mackey_glass", "lorenz", "narma10"])),
        criterion("targeted anomaly task included", "anomaly_detection_stream" in tasks, "== true", "anomaly_detection_stream" in tasks),
        criterion("classification produced", classification["outcome"], "non-empty", bool(classification["outcome"])),
        criterion("software only", "no PyNN/SpiNNaker calls", "true", True),
    ]
    failed = [item for item in criteria if not item["passed"]]
    near_full_resonant_contract = {
        "mechanism": "near_full_resonant_hybrid_lif_branches",
        "tested_layout": {"standard_lif_excitatory_units": 2, "resonant_branch_units": 14, "total_excitatory_budget": 16},
        "repair_target": "test whether the near-full resonant specialist dose preserves v2.3 while retaining any variable-delay/anomaly value",
        "nonclaims": [
            "not a core polyp replacement",
            "not hardware evidence",
            "not a v2.x baseline freeze",
            "not a custom SpiNNaker neuron model",
            "not AGI/ASI evidence",
        ],
    }
    payload = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "status": "pass" if not failed else "fail",
        "output_dir": str(output_dir),
        "criteria": criteria,
        "criteria_passed": len(criteria) - len(failed),
        "criteria_total": len(criteria),
        "failed_criteria": failed,
        "tasks": tasks,
        "seeds": seeds,
        "length": int(args.length),
        "horizon": int(args.horizon),
        "runtime_seconds": time.perf_counter() - started,
        "summary_rows": summary_rows,
        "aggregate_rows": aggregate_rows,
        "aggregate_summary": aggregate_summary,
        "classification": classification,
        "summary": classification,
        "run_rows": all_rows,
        "task_diagnostics": task_diagnostics,
        "near_full_resonant_contract": near_full_resonant_contract,
        "claim_boundary": (
            "Tier 5.20e is a software-only near-full resonant diagnostic after "
            "5.20a/5.20b. It tests a same-budget 2 LIF / 14 resonant branch "
            "internal-polyp proxy against v2.3, v2.2, full-resonant, "
            "lag/reservoir/ESN controls, and 2/14 shams. It is not a canonical "
            "organism change, not hardware evidence, and not a baseline freeze."
        ),
    }
    write_json(output_dir / "tier5_20e_results.json", payload)
    write_json(output_dir / "tier5_20e_near_full_resonant_contract.json", near_full_resonant_contract)
    write_csv_rows(output_dir / "tier5_20e_summary.csv", summary_rows)
    write_csv_rows(output_dir / "tier5_20e_aggregate.csv", aggregate_rows)
    write_csv_rows(output_dir / "tier5_20e_aggregate_summary.csv", aggregate_summary)
    if capture_timeseries:
        write_csv_rows(output_dir / "tier5_20e_timeseries.csv", all_timeseries)
    write_report(output_dir / "tier5_20e_report.md", payload)
    latest = {
        "tier": TIER,
        "status": payload["status"],
        "generated_at_utc": payload["generated_at_utc"],
        "output_dir": str(output_dir),
        "results_json": str(output_dir / "tier5_20e_results.json"),
        "report_md": str(output_dir / "tier5_20e_report.md"),
        "summary_csv": str(output_dir / "tier5_20e_summary.csv"),
        "classification": classification["outcome"],
    }
    write_json(OUTPUT_ROOT / "tier5_20e_latest_manifest.json", latest)
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=TIER)
    parser.add_argument("--tasks", default=DEFAULT_TASKS)
    parser.add_argument("--seeds", default="42,43,44")
    parser.add_argument("--seed-count", type=int, default=None)
    parser.add_argument("--base-seed", type=int, default=42)
    parser.add_argument("--length", type=int, default=2400)
    parser.add_argument("--horizon", type=int, default=5)
    parser.add_argument("--history", type=int, default=32)
    parser.add_argument("--max-branch-delay", type=int, default=96)
    parser.add_argument("--branch-gain", type=float, default=1.5)
    parser.add_argument("--temporal-timescales", default="2,4,8,16,32,64,128")
    parser.add_argument("--temporal-recurrent-scale", type=float, default=0.65)
    parser.add_argument("--temporal-input-scale", type=float, default=0.45)
    parser.add_argument("--temporal-hidden-decay", type=float, default=0.72)
    parser.add_argument("--reservoir-units", type=int, default=16)
    parser.add_argument("--reservoir-spectral-radius", type=float, default=0.72)
    parser.add_argument("--reservoir-input-scale", type=float, default=0.45)
    parser.add_argument("--esn-units", type=int, default=64)
    parser.add_argument("--esn-spectral-radius", type=float, default=0.82)
    parser.add_argument("--esn-input-scale", type=float, default=0.55)
    parser.add_argument("--readout-lr", type=float, default=0.025)
    parser.add_argument("--readout-decay", type=float, default=1e-4)
    parser.add_argument("--weight-clip", type=float, default=8.0)
    parser.add_argument("--output-clip", type=float, default=5.0)
    parser.add_argument("--ridge", type=float, default=1e-3)
    parser.add_argument("--no-timeseries", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser


def main() -> int:
    payload = run(build_parser().parse_args())
    print(json.dumps(json_safe({"status": payload["status"], "classification": payload["classification"]}), indent=2, sort_keys=True))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
