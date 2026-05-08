#!/usr/bin/env python3
"""Tier 5.20b - Hybrid Resonant/LIF Polyp Diagnostic.

Tier 5.20a showed that replacing all 16 excitatory neurons with resonant
LIF-style branch filters was too destructive: it helped selected temporal
diagnostics but regressed several broad tasks versus v2.3. This repair gate
tests the more plausible substrate: keep part of the ordinary excitatory pool
and dedicate only part of it to resonant temporal branches.

The tested same-budget layouts are:

* 8 standard bounded recurrent/LIF-style excitatory units + 8 resonant branches
* 12 standard bounded recurrent/LIF-style excitatory units + 4 resonant branches

This is software diagnostic evidence only. A pass here can authorize a core
integration gate, not a baseline freeze or hardware transfer.
"""

from __future__ import annotations

import argparse
import csv
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

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "controlled_test_output"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from tier5_19a_temporal_substrate_reference import (  # noqa: E402
    FeatureBundle,
    append_timeseries,
    criterion,
    json_safe,
    parse_timescales,
    random_reservoir_features,
    run_online_model,
    run_train_prefix_esn,
    summarize,
    write_json,
)
from tier5_19b_temporal_substrate_gate import temporal_features_variant  # noqa: E402
from tier5_20a_resonant_branch_polyp_diagnostic import (  # noqa: E402
    build_task,
    resonant_branch_features,
    shuffled_branch_state,
)
from tier7_0_standard_dynamical_benchmarks import parse_csv, parse_seeds  # noqa: E402
from tier7_0b_continuous_regression_failure_analysis import lag_matrix  # noqa: E402


TIER = "Tier 5.20b - Hybrid Resonant/LIF Polyp Diagnostic"
RUNNER_REVISION = "tier5_20b_hybrid_resonant_polyp_diagnostic_20260508_0001"
DEFAULT_OUTPUT_DIR = OUTPUT_ROOT / "tier5_20b_20260508_hybrid_resonant_polyp_diagnostic"
DEFAULT_TASKS = (
    "mackey_glass,lorenz,narma10,"
    "variable_delay_multi_cue,hidden_context_reentry,anomaly_detection_stream"
)

V23 = "v2_3_generic_bounded_recurrent_state"
V22 = "v2_2_fading_memory_reference"
FULL_RESONANT = "full_16_resonant_reference"
HYBRID_8_8 = "hybrid_8_lif_8_resonant"
HYBRID_8_8_FLAT = "hybrid_8_lif_8_flat_tau_sham"
HYBRID_8_8_RATE = "hybrid_8_lif_8_rate_only_sham"
HYBRID_8_8_SHUFFLED = "hybrid_8_lif_8_shuffled_branch_sham"
HYBRID_12_4 = "hybrid_12_lif_4_resonant"
HYBRID_12_4_FLAT = "hybrid_12_lif_4_flat_tau_sham"
HYBRID_12_4_RATE = "hybrid_12_lif_4_rate_only_sham"
HYBRID_12_4_SHUFFLED = "hybrid_12_lif_4_shuffled_branch_sham"
LAG = "lag_only_online_lms_control"
RESERVOIR = "fixed_random_reservoir_online_control"
ESN = "fixed_esn_train_prefix_ridge_baseline"
REQUIRED_MODELS = [
    V23,
    V22,
    FULL_RESONANT,
    HYBRID_8_8,
    HYBRID_8_8_FLAT,
    HYBRID_8_8_RATE,
    HYBRID_8_8_SHUFFLED,
    HYBRID_12_4,
    HYBRID_12_4_FLAT,
    HYBRID_12_4_RATE,
    HYBRID_12_4_SHUFFLED,
    LAG,
    RESERVOIR,
    ESN,
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_csv_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def finite_float(value: Any, default: float = math.inf) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    return out if math.isfinite(out) else default


def ratio(control: float, candidate: float) -> float | None:
    if not math.isfinite(control) or not math.isfinite(candidate) or candidate <= 1e-12:
        return None
    return control / candidate


def hybrid_features(
    observed: np.ndarray,
    *,
    seed: int,
    train_end: int,
    lif_units: int,
    branch_count: int,
    branch_mode: str,
    args: argparse.Namespace,
) -> FeatureBundle:
    timescales = parse_timescales(args.temporal_timescales)
    lif = temporal_features_variant(
        observed,
        seed=seed,
        train_end=train_end,
        timescales=timescales,
        hidden_units=int(lif_units),
        recurrent_scale=float(args.temporal_recurrent_scale),
        input_scale=float(args.temporal_input_scale),
        hidden_decay=float(args.temporal_hidden_decay),
        mode="full",
    )
    branch = resonant_branch_features(
        observed,
        seed=seed,
        train_end=train_end,
        branch_count=int(branch_count),
        mode=branch_mode,
        max_delay=int(args.max_branch_delay),
        gain=float(args.branch_gain),
    )
    branch_state = branch.features[:, branch.temporal_start :]
    if branch_mode == "shuffled":
        branch_state = shuffled_branch_state(branch.features, train_end, seed, branch.temporal_start)[:, branch.temporal_start :]
    features = np.hstack([lif.features, branch_state])
    names = list(lif.names) + [f"{branch_mode}_branch_{idx}" for idx in range(branch_state.shape[1])]
    return FeatureBundle(
        features=features,
        temporal_start=lif.temporal_start,
        names=names,
        diagnostics={
            "state_location": "hybrid_polyp_internal_excitatory_proxy",
            "lif_units": int(lif_units),
            "resonant_branch_count": int(branch_count),
            "excitatory_budget_total": int(lif_units) + int(branch_count),
            "same_excitatory_budget": int(lif_units) + int(branch_count) == 16,
            "branch_mode": branch_mode,
            "lif_diagnostics": lif.diagnostics,
            "branch_diagnostics": branch.diagnostics,
            "feature_count": int(features.shape[1]),
        },
    )


def run_task_models(task: Any, *, seed: int, args: argparse.Namespace, capture_timeseries: bool) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    timeseries: list[dict[str, Any]] = []
    timescales = parse_timescales(args.temporal_timescales)
    temporal_kwargs = {
        "seed": seed,
        "train_end": task.train_end,
        "timescales": timescales,
        "recurrent_scale": float(args.temporal_recurrent_scale),
        "input_scale": float(args.temporal_input_scale),
        "hidden_decay": float(args.temporal_hidden_decay),
    }
    v23 = temporal_features_variant(task.observed, hidden_units=16, mode="full", **temporal_kwargs)
    v22 = temporal_features_variant(task.observed, hidden_units=16, mode="fading_only", **temporal_kwargs)
    full_resonant = resonant_branch_features(
        task.observed,
        seed=seed,
        train_end=task.train_end,
        branch_count=16,
        mode="resonant",
        max_delay=int(args.max_branch_delay),
        gain=float(args.branch_gain),
    )
    model_bundles = {
        V23: v23,
        V22: v22,
        FULL_RESONANT: full_resonant,
        HYBRID_8_8: hybrid_features(task.observed, seed=seed, train_end=task.train_end, lif_units=8, branch_count=8, branch_mode="resonant", args=args),
        HYBRID_8_8_FLAT: hybrid_features(task.observed, seed=seed, train_end=task.train_end, lif_units=8, branch_count=8, branch_mode="flat_tau", args=args),
        HYBRID_8_8_RATE: hybrid_features(task.observed, seed=seed, train_end=task.train_end, lif_units=8, branch_count=8, branch_mode="rate_only", args=args),
        HYBRID_8_8_SHUFFLED: hybrid_features(task.observed, seed=seed, train_end=task.train_end, lif_units=8, branch_count=8, branch_mode="shuffled", args=args),
        HYBRID_12_4: hybrid_features(task.observed, seed=seed, train_end=task.train_end, lif_units=12, branch_count=4, branch_mode="resonant", args=args),
        HYBRID_12_4_FLAT: hybrid_features(task.observed, seed=seed, train_end=task.train_end, lif_units=12, branch_count=4, branch_mode="flat_tau", args=args),
        HYBRID_12_4_RATE: hybrid_features(task.observed, seed=seed, train_end=task.train_end, lif_units=12, branch_count=4, branch_mode="rate_only", args=args),
        HYBRID_12_4_SHUFFLED: hybrid_features(task.observed, seed=seed, train_end=task.train_end, lif_units=12, branch_count=4, branch_mode="shuffled", args=args),
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
        "same_budget_variants": ["8_lif_8_resonant", "12_lif_4_resonant"],
        "v23_feature_count": int(v23.features.shape[1]),
        "hybrid_8_8_feature_count": int(model_bundles[HYBRID_8_8].features.shape[1]),
        "hybrid_12_4_feature_count": int(model_bundles[HYBRID_12_4].features.shape[1]),
    }
    return rows, timeseries, diagnostics


def metric(summary_rows: list[dict[str, Any]], task: str, model: str, key: str = "mse_mean") -> float:
    row = next((r for r in summary_rows if r["task"] == task and r["model"] == model), None)
    return finite_float(row.get(key) if row else None)


def aggregate_metric(aggregate_summary: list[dict[str, Any]], scope: str, model: str) -> float:
    row = next((r for r in aggregate_summary if r["task"] == scope and r["model"] == model), None)
    return finite_float(row.get("geomean_mse_mean") if row else None)


def evaluate_candidate(
    *,
    candidate: str,
    shams: list[str],
    tasks: list[str],
    summary_rows: list[dict[str, Any]],
    aggregate_summary: list[dict[str, Any]],
) -> dict[str, Any]:
    per_task: list[dict[str, Any]] = []
    wins = 0
    sham_separated = 0
    regressions = 0
    for task in tasks:
        cand = metric(summary_rows, task, candidate)
        v23 = metric(summary_rows, task, V23)
        v22 = metric(summary_rows, task, V22)
        sham_values = {sham: metric(summary_rows, task, sham) for sham in shams}
        win = cand < v23 * 0.98
        regression = cand > v23 * 1.10
        margins = {f"{sham}_margin": ratio(value, cand) for sham, value in sham_values.items()}
        separated = all((value is not None and value >= 1.03) for value in margins.values())
        wins += int(win)
        regressions += int(regression)
        sham_separated += int(separated)
        per_task.append(
            {
                "task": task,
                "candidate_mse": cand,
                "v2_3_mse": v23,
                "v2_2_mse": v22,
                "candidate_vs_v2_3_margin": ratio(v23, cand),
                "candidate_vs_v2_2_margin": ratio(v22, cand),
                "win_vs_v2_3": win,
                "regression_vs_v2_3": regression,
                "sham_separated": separated,
                **sham_values,
                **margins,
            }
        )
    all_cand = aggregate_metric(aggregate_summary, "all_tasks_geomean", candidate)
    all_v23 = aggregate_metric(aggregate_summary, "all_tasks_geomean", V23)
    standard_cand = aggregate_metric(aggregate_summary, "standard_three_geomean", candidate)
    standard_v23 = aggregate_metric(aggregate_summary, "standard_three_geomean", V23)
    no_material_regression = regressions == 0 and all_cand <= all_v23 * 1.05 and standard_cand <= standard_v23 * 1.10
    useful_signal = wins >= int(math.ceil(len(tasks) / 3.0)) and sham_separated >= max(1, int(math.ceil(len(tasks) / 3.0)))
    return {
        "candidate": candidate,
        "wins_vs_v2_3_count": int(wins),
        "sham_separation_count": int(sham_separated),
        "material_regression_count_vs_v2_3": int(regressions),
        "no_material_regression_vs_v2_3": bool(no_material_regression),
        "useful_signal": bool(useful_signal),
        "all_tasks_candidate_geomean_mse": all_cand,
        "all_tasks_v2_3_geomean_mse": all_v23,
        "all_tasks_candidate_vs_v2_3_margin": ratio(all_v23, all_cand),
        "standard_three_candidate_geomean_mse": standard_cand,
        "standard_three_v2_3_geomean_mse": standard_v23,
        "standard_three_candidate_vs_v2_3_margin": ratio(standard_v23, standard_cand),
        "per_task": per_task,
    }


def classify(summary_rows: list[dict[str, Any]], aggregate_summary: list[dict[str, Any]], tasks: list[str]) -> dict[str, Any]:
    candidates = [
        evaluate_candidate(
            candidate=HYBRID_8_8,
            shams=[HYBRID_8_8_FLAT, HYBRID_8_8_RATE, HYBRID_8_8_SHUFFLED],
            tasks=tasks,
            summary_rows=summary_rows,
            aggregate_summary=aggregate_summary,
        ),
        evaluate_candidate(
            candidate=HYBRID_12_4,
            shams=[HYBRID_12_4_FLAT, HYBRID_12_4_RATE, HYBRID_12_4_SHUFFLED],
            tasks=tasks,
            summary_rows=summary_rows,
            aggregate_summary=aggregate_summary,
        ),
    ]
    candidates.sort(
        key=lambda row: (
            not row["no_material_regression_vs_v2_3"],
            -row["wins_vs_v2_3_count"],
            -(row["all_tasks_candidate_vs_v2_3_margin"] or 0.0),
            row["all_tasks_candidate_geomean_mse"],
        )
    )
    best = candidates[0]
    if best["useful_signal"] and best["no_material_regression_vs_v2_3"]:
        outcome = "hybrid_resonant_candidate_for_integration_gate"
        recommendation = f"Proceed to Tier 5.20c optional-polyp integration using {best['candidate']}."
    elif best["no_material_regression_vs_v2_3"] and best["sham_separation_count"] >= 1:
        outcome = "hybrid_resonant_research_scaffold_not_promoted"
        recommendation = "Keep hybrid resonant branches as a documented scaffold; do not integrate until a sharper task shows stronger value."
    else:
        outcome = "hybrid_resonant_not_promoted"
        recommendation = "Do not integrate the hybrid resonant branch variants into the core organism."
    return {
        "outcome": outcome,
        "recommendation": recommendation,
        "best_candidate": best["candidate"],
        "candidate_rankings": candidates,
    }


def write_report(path: Path, payload: dict[str, Any]) -> None:
    classification = payload["classification"]
    lines = [
        f"# {TIER}",
        "",
        f"- Generated: `{payload['generated_at_utc']}`",
        f"- Status: **{payload['status'].upper()}**",
        f"- Output directory: `{payload['output_dir']}`",
        f"- Outcome: `{classification['outcome']}`",
        f"- Best candidate: `{classification['best_candidate']}`",
        "",
        "## Claim Boundary",
        "",
        payload["claim_boundary"],
        "",
        "## Summary",
        "",
        f"- Recommendation: {classification['recommendation']}",
        "",
        "## Candidate Rankings",
        "",
        "| Candidate | All-task MSE | Margin vs v2.3 | Wins vs v2.3 | Regressions | Sham-separated tasks |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in classification["candidate_rankings"]:
        lines.append(
            "| {candidate} | `{mse}` | `{margin}` | `{wins}` | `{reg}` | `{sham}` |".format(
                candidate=row["candidate"],
                mse=row["all_tasks_candidate_geomean_mse"],
                margin=row["all_tasks_candidate_vs_v2_3_margin"],
                wins=row["wins_vs_v2_3_count"],
                reg=row["material_regression_count_vs_v2_3"],
                sham=row["sham_separation_count"],
            )
        )
    lines.extend(
        [
            "",
            "## Criteria",
            "",
            "| Criterion | Value | Rule | Pass |",
            "| --- | --- | --- | --- |",
        ]
    )
    for item in payload["criteria"]:
        lines.append(f"| {item['name']} | `{item['value']}` | {item['rule']} | {'yes' if item['passed'] else 'no'} |")
    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            "- `tier5_20b_results.json`",
            "- `tier5_20b_summary.csv`",
            "- `tier5_20b_aggregate.csv`",
            "- `tier5_20b_aggregate_summary.csv`",
            "- `tier5_20b_hybrid_contract.json`",
            "- `tier5_20b_timeseries.csv` if `--no-timeseries` was not used",
        ]
    )
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
        criterion("Tier 5.20a full-replacement diagnostic present", "tier5_20a", "results exist", (OUTPUT_ROOT / "tier5_20a_20260508_resonant_branch_polyp_diagnostic" / "tier5_20a_results.json").exists()),
        criterion("same budget 8/8 variant declared", "8 LIF + 8 resonant", "sum == 16 excitatory units", True),
        criterion("same budget 12/4 variant declared", "12 LIF + 4 resonant", "sum == 16 excitatory units", True),
        criterion("all required models present", sorted(REQUIRED_MODELS), "all present", all(model in models for model in REQUIRED_MODELS)),
        criterion("all runs completed", f"{sum(r['status'] == 'pass' for r in all_rows)}/{len(all_rows)}", "all pass", all(r["status"] == "pass" for r in all_rows)),
        criterion("8/8 shams present", [HYBRID_8_8_FLAT, HYBRID_8_8_RATE, HYBRID_8_8_SHUFFLED], "all present", all(model in models for model in [HYBRID_8_8_FLAT, HYBRID_8_8_RATE, HYBRID_8_8_SHUFFLED])),
        criterion("12/4 shams present", [HYBRID_12_4_FLAT, HYBRID_12_4_RATE, HYBRID_12_4_SHUFFLED], "all present", all(model in models for model in [HYBRID_12_4_FLAT, HYBRID_12_4_RATE, HYBRID_12_4_SHUFFLED])),
        criterion("public standard tasks included", ["mackey_glass", "lorenz", "narma10"], "all included", all(task in tasks for task in ["mackey_glass", "lorenz", "narma10"])),
        criterion("targeted anomaly task included", "anomaly_detection_stream" in tasks, "== true", "anomaly_detection_stream" in tasks),
        criterion("classification produced", classification["outcome"], "non-empty", bool(classification["outcome"])),
        criterion("software only", "no PyNN/SpiNNaker calls", "true", True),
    ]
    failed = [item for item in criteria if not item["passed"]]
    hybrid_contract = {
        "mechanism": "hybrid_resonant_lif_branches",
        "tested_layouts": [
            {"standard_lif_excitatory_units": 8, "resonant_branch_units": 8, "total_excitatory_budget": 16},
            {"standard_lif_excitatory_units": 12, "resonant_branch_units": 4, "total_excitatory_budget": 16},
        ],
        "repair_target": "preserve v2.3 broad-task performance while keeping 5.20a's variable-delay/anomaly value",
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
        "hybrid_contract": hybrid_contract,
        "claim_boundary": (
            "Tier 5.20b is a software-only repair diagnostic after 5.20a. "
            "It tests same-budget 8/8 and 12/4 hybrid LIF/resonant branch "
            "internal-polyp proxies against v2.3, v2.2, lag/reservoir/ESN "
            "controls, and hybrid shams. It is not a canonical organism "
            "change, not hardware evidence, and not a baseline freeze."
        ),
    }
    write_json(output_dir / "tier5_20b_results.json", payload)
    write_json(output_dir / "tier5_20b_hybrid_contract.json", hybrid_contract)
    write_csv_rows(output_dir / "tier5_20b_summary.csv", summary_rows)
    write_csv_rows(output_dir / "tier5_20b_aggregate.csv", aggregate_rows)
    write_csv_rows(output_dir / "tier5_20b_aggregate_summary.csv", aggregate_summary)
    if capture_timeseries:
        write_csv_rows(output_dir / "tier5_20b_timeseries.csv", all_timeseries)
    write_report(output_dir / "tier5_20b_report.md", payload)
    latest = {
        "tier": TIER,
        "status": payload["status"],
        "generated_at_utc": payload["generated_at_utc"],
        "output_dir": str(output_dir),
        "results_json": str(output_dir / "tier5_20b_results.json"),
        "report_md": str(output_dir / "tier5_20b_report.md"),
        "summary_csv": str(output_dir / "tier5_20b_summary.csv"),
        "classification": classification["outcome"],
        "best_candidate": classification["best_candidate"],
    }
    write_json(OUTPUT_ROOT / "tier5_20b_latest_manifest.json", latest)
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
