#!/usr/bin/env python3
"""Tier 5.20a - Resonant Branch Polyp Internal-Model Diagnostic.

This tier tests a proposed polyp-internal substrate change without replacing
the canonical CRA organism yet. The candidate keeps the same 32-neuron polyp
budget assumption and treats the current 16 excitatory neurons as structured
LIF-safe branch filters with different delays and time constants.

The gate is software-only. A pass here can only promote the idea to the next
integration step; it is not hardware evidence and not a baseline freeze.
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
from tier5_19b_temporal_substrate_gate import build_task as build_temporal_task  # noqa: E402
from tier5_19b_temporal_substrate_gate import temporal_features_variant  # noqa: E402
from tier6_2a_targeted_usefulness_validation import TASK_BUILDERS as TIER6_TASK_BUILDERS  # noqa: E402
from tier6_2a_targeted_usefulness_validation import build_task as build_targeted_task  # noqa: E402
from tier7_0_standard_dynamical_benchmarks import parse_csv, parse_seeds  # noqa: E402
from tier7_0b_continuous_regression_failure_analysis import lag_matrix  # noqa: E402


TIER = "Tier 5.20a - Resonant Branch Polyp Internal-Model Diagnostic"
RUNNER_REVISION = "tier5_20a_resonant_branch_polyp_diagnostic_20260508_0001"
DEFAULT_OUTPUT_DIR = OUTPUT_ROOT / "tier5_20a_20260508_resonant_branch_polyp_diagnostic"
DEFAULT_TASKS = (
    "mackey_glass,lorenz,narma10,"
    "variable_delay_multi_cue,hidden_context_reentry,anomaly_detection_stream"
)

V23 = "v2_3_generic_bounded_recurrent_state"
V22 = "v2_2_fading_memory_reference"
RESONANT = "resonant_branch_polyp_candidate"
FLAT = "resonant_flat_tau_sham"
RATE = "resonant_rate_only_sham"
SHUFFLED = "resonant_shuffled_branch_state_sham"
LAG = "lag_only_online_lms_control"
RESERVOIR = "fixed_random_reservoir_online_control"
ESN = "fixed_esn_train_prefix_ridge_baseline"
REQUIRED_MODELS = [V23, V22, RESONANT, FLAT, RATE, SHUFFLED, LAG, RESERVOIR, ESN]


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


def build_task(name: str, length: int, seed: int, horizon: int):
    if name in TIER6_TASK_BUILDERS:
        return build_targeted_task(name, length, seed, horizon)
    return build_temporal_task(name, length, seed, horizon)


def resonant_branch_features(
    observed: np.ndarray,
    *,
    seed: int,
    train_end: int,
    branch_count: int,
    mode: str,
    max_delay: int,
    gain: float,
) -> FeatureBundle:
    """Build same-budget LIF-style branch filters over the input stream.

    The candidate is intentionally expressible as PyNN/SpiNNaker-safe LIF
    subcircuits later: branch-specific delays plus fast/slow low-pass traces.
    """
    del train_end
    values = np.asarray(observed, dtype=float)
    n = max(1, int(branch_count))
    if mode == "flat_tau":
        delays = np.ones(n, dtype=int) * max(1, min(8, int(max_delay)))
        fast_taus = np.ones(n, dtype=float) * 4.0
        slow_taus = np.ones(n, dtype=float) * 24.0
    else:
        delays = np.unique(np.rint(np.geomspace(1, max(1, int(max_delay)), num=max(n, 2))).astype(int))
        if delays.size < n:
            delays = np.pad(delays, (0, n - delays.size), mode="edge")
        delays = delays[:n]
        fast_taus = np.geomspace(2.0, 18.0, num=n)
        slow_taus = np.geomspace(8.0, 96.0, num=n)
    if mode == "permuted_assignment":
        rng = np.random.default_rng(seed + 52031)
        rng.shuffle(delays)
        rng.shuffle(fast_taus)
        rng.shuffle(slow_taus)

    fast = np.zeros(n, dtype=float)
    slow = np.zeros(n, dtype=float)
    rows: list[np.ndarray] = []
    for step, value in enumerate(values):
        x_now = float(value)
        outputs = np.zeros(n, dtype=float)
        for idx in range(n):
            delayed_index = max(0, step - int(delays[idx]))
            x_delayed = float(values[delayed_index])
            fast_alpha = 1.0 - math.exp(-1.0 / max(1e-6, float(fast_taus[idx])))
            slow_alpha = 1.0 - math.exp(-1.0 / max(1e-6, float(slow_taus[idx])))
            fast[idx] += fast_alpha * (x_delayed - fast[idx])
            slow[idx] += slow_alpha * (x_delayed - slow[idx])
            if mode == "rate_only":
                outputs[idx] = slow[idx]
            else:
                outputs[idx] = math.tanh(float(gain) * (fast[idx] - slow[idx]))
        rows.append(np.concatenate([[1.0, x_now], outputs]))

    features = np.vstack(rows)
    names = ["bias", "observed_current"] + [f"branch_{idx}" for idx in range(n)]
    return FeatureBundle(
        features=features,
        temporal_start=2,
        names=names,
        diagnostics={
            "state_location": "polyp_internal_excitatory_branch_proxy",
            "mode": mode,
            "branch_count": int(n),
            "same_polyp_budget": "16 branch neurons replace the current 16 excitatory LIF neurons",
            "lif_safe_approximation": "branch-specific delay plus fast/slow low-pass traces",
            "delays": [int(x) for x in delays.tolist()],
            "fast_taus": [float(x) for x in fast_taus.tolist()],
            "slow_taus": [float(x) for x in slow_taus.tolist()],
            "gain": float(gain),
            "feature_count": int(features.shape[1]),
        },
    )


def shuffled_branch_state(features: np.ndarray, train_end: int, seed: int, temporal_start: int) -> np.ndarray:
    rng = np.random.default_rng(seed + 52097)
    out = np.asarray(features, dtype=float).copy()
    for start, stop in ((0, train_end), (train_end, len(out))):
        idx = np.arange(start, stop)
        rng.shuffle(idx)
        out[start:stop, temporal_start:] = out[idx, temporal_start:]
    return out


def run_task_models(task: Any, *, seed: int, args: argparse.Namespace, capture_timeseries: bool) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    timeseries: list[dict[str, Any]] = []
    timescales = parse_timescales(args.temporal_timescales)
    temporal_kwargs = {
        "seed": seed,
        "train_end": task.train_end,
        "timescales": timescales,
        "hidden_units": int(args.temporal_hidden_units),
        "recurrent_scale": float(args.temporal_recurrent_scale),
        "input_scale": float(args.temporal_input_scale),
        "hidden_decay": float(args.temporal_hidden_decay),
    }
    v23 = temporal_features_variant(task.observed, mode="full", **temporal_kwargs)
    v22 = temporal_features_variant(task.observed, mode="fading_only", **temporal_kwargs)
    resonant = resonant_branch_features(
        task.observed,
        seed=seed,
        train_end=task.train_end,
        branch_count=int(args.branch_count),
        mode="resonant",
        max_delay=int(args.max_branch_delay),
        gain=float(args.branch_gain),
    )
    flat = resonant_branch_features(
        task.observed,
        seed=seed,
        train_end=task.train_end,
        branch_count=int(args.branch_count),
        mode="flat_tau",
        max_delay=int(args.max_branch_delay),
        gain=float(args.branch_gain),
    )
    rate = resonant_branch_features(
        task.observed,
        seed=seed,
        train_end=task.train_end,
        branch_count=int(args.branch_count),
        mode="rate_only",
        max_delay=int(args.max_branch_delay),
        gain=float(args.branch_gain),
    )
    shuffled = FeatureBundle(
        features=shuffled_branch_state(resonant.features, task.train_end, seed, resonant.temporal_start),
        temporal_start=resonant.temporal_start,
        names=resonant.names,
        diagnostics={**resonant.diagnostics, "sham": "branch state rows shuffled within train/test splits"},
    )
    lag = lag_matrix(task.observed, int(args.history))
    reservoir = random_reservoir_features(
        task.observed,
        seed=seed,
        units=int(args.reservoir_units),
        spectral_radius=float(args.reservoir_spectral_radius),
        input_scale=float(args.reservoir_input_scale),
    )
    model_specs = [
        (V23, v23.features, v23.diagnostics),
        (V22, v22.features, v22.diagnostics),
        (RESONANT, resonant.features, resonant.diagnostics),
        (FLAT, flat.features, flat.diagnostics),
        (RATE, rate.features, rate.diagnostics),
        (SHUFFLED, shuffled.features, shuffled.diagnostics),
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
        "branch_count": int(args.branch_count),
        "same_budget_branch_proxy": int(args.branch_count) == 16,
        "v23_feature_count": int(v23.features.shape[1]),
        "resonant_feature_count": int(resonant.features.shape[1]),
        "lag_feature_count": int(lag.shape[1]),
        "resonant_delays": resonant.diagnostics.get("delays"),
    }
    return rows, timeseries, diagnostics


def metric(summary_rows: list[dict[str, Any]], task: str, model: str, key: str = "mse_mean") -> float:
    row = next((r for r in summary_rows if r["task"] == task and r["model"] == model), None)
    return finite_float(row.get(key) if row else None)


def aggregate_metric(aggregate_summary: list[dict[str, Any]], scope: str, model: str) -> float:
    row = next((r for r in aggregate_summary if r["task"] == scope and r["model"] == model), None)
    return finite_float(row.get("geomean_mse_mean") if row else None)


def classify(summary_rows: list[dict[str, Any]], aggregate_summary: list[dict[str, Any]], tasks: list[str]) -> dict[str, Any]:
    wins_vs_v23 = []
    wins_vs_v22 = []
    sham_separations = []
    regressions_vs_v23 = []
    per_task: list[dict[str, Any]] = []
    for task in tasks:
        resonant_mse = metric(summary_rows, task, RESONANT)
        v23_mse = metric(summary_rows, task, V23)
        v22_mse = metric(summary_rows, task, V22)
        flat_mse = metric(summary_rows, task, FLAT)
        rate_mse = metric(summary_rows, task, RATE)
        shuffled_mse = metric(summary_rows, task, SHUFFLED)
        task_win_v23 = resonant_mse < v23_mse * 0.98
        task_win_v22 = resonant_mse < v22_mse * 0.98
        task_sham = (
            ratio(flat_mse, resonant_mse) is not None
            and ratio(rate_mse, resonant_mse) is not None
            and ratio(shuffled_mse, resonant_mse) is not None
            and min(ratio(flat_mse, resonant_mse) or 0.0, ratio(rate_mse, resonant_mse) or 0.0, ratio(shuffled_mse, resonant_mse) or 0.0) >= 1.05
        )
        task_regression = resonant_mse > v23_mse * 1.10
        wins_vs_v23.append(task_win_v23)
        wins_vs_v22.append(task_win_v22)
        sham_separations.append(task_sham)
        regressions_vs_v23.append(task_regression)
        per_task.append(
            {
                "task": task,
                "resonant_mse": resonant_mse,
                "v2_3_mse": v23_mse,
                "v2_2_mse": v22_mse,
                "flat_tau_mse": flat_mse,
                "rate_only_mse": rate_mse,
                "shuffled_branch_mse": shuffled_mse,
                "resonant_vs_v2_3_margin": ratio(v23_mse, resonant_mse),
                "resonant_vs_v2_2_margin": ratio(v22_mse, resonant_mse),
                "flat_tau_vs_resonant_margin": ratio(flat_mse, resonant_mse),
                "rate_only_vs_resonant_margin": ratio(rate_mse, resonant_mse),
                "shuffled_branch_vs_resonant_margin": ratio(shuffled_mse, resonant_mse),
                "win_vs_v2_3": task_win_v23,
                "win_vs_v2_2": task_win_v22,
                "sham_separated": task_sham,
                "regression_vs_v2_3": task_regression,
            }
        )

    all_resonant = aggregate_metric(aggregate_summary, "all_tasks_geomean", RESONANT)
    all_v23 = aggregate_metric(aggregate_summary, "all_tasks_geomean", V23)
    all_v22 = aggregate_metric(aggregate_summary, "all_tasks_geomean", V22)
    standard_resonant = aggregate_metric(aggregate_summary, "standard_three_geomean", RESONANT)
    standard_v23 = aggregate_metric(aggregate_summary, "standard_three_geomean", V23)
    win_count = sum(wins_vs_v23)
    sham_count = sum(sham_separations)
    regression_count = sum(regressions_vs_v23)
    no_material_regression = regression_count == 0 and all_resonant <= all_v23 * 1.05
    useful_signal = win_count >= int(math.ceil(len(tasks) / 3.0)) and sham_count >= max(1, int(math.ceil(len(tasks) / 3.0)))

    if useful_signal and no_material_regression:
        outcome = "resonant_branch_candidate_for_integration_gate"
        recommendation = "Proceed to Tier 5.20b: integrate optional resonant_lif_branches polyp model with compact regression."
    elif no_material_regression and sham_count >= 1:
        outcome = "resonant_branch_research_scaffold_not_promoted"
        recommendation = "Keep as a documented scaffold; do not replace the canonical polyp until a sharper task shows causal value."
    else:
        outcome = "resonant_branch_not_promoted"
        recommendation = "Do not integrate into the core organism; either park it or redesign the branch objective/tasks."

    return {
        "outcome": outcome,
        "recommendation": recommendation,
        "wins_vs_v2_3_count": int(win_count),
        "wins_vs_v2_2_count": int(sum(wins_vs_v22)),
        "sham_separation_count": int(sham_count),
        "material_regression_count_vs_v2_3": int(regression_count),
        "no_material_regression_vs_v2_3": bool(no_material_regression),
        "useful_signal": bool(useful_signal),
        "all_tasks_resonant_geomean_mse": all_resonant,
        "all_tasks_v2_3_geomean_mse": all_v23,
        "all_tasks_v2_2_geomean_mse": all_v22,
        "all_tasks_resonant_vs_v2_3_margin": ratio(all_v23, all_resonant),
        "standard_three_resonant_geomean_mse": standard_resonant,
        "standard_three_v2_3_geomean_mse": standard_v23,
        "standard_three_resonant_vs_v2_3_margin": ratio(standard_v23, standard_resonant),
        "per_task": per_task,
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
        "",
        "## Claim Boundary",
        "",
        payload["claim_boundary"],
        "",
        "## Summary",
        "",
        f"- Recommendation: {classification['recommendation']}",
        f"- Wins versus v2.3: `{classification['wins_vs_v2_3_count']}`",
        f"- Sham-separated tasks: `{classification['sham_separation_count']}`",
        f"- Material regressions versus v2.3: `{classification['material_regression_count_vs_v2_3']}`",
        f"- All-task resonant geomean MSE: `{classification['all_tasks_resonant_geomean_mse']}`",
        f"- All-task v2.3 geomean MSE: `{classification['all_tasks_v2_3_geomean_mse']}`",
        f"- All-task resonant/v2.3 margin: `{classification['all_tasks_resonant_vs_v2_3_margin']}`",
        "",
        "## Criteria",
        "",
        "| Criterion | Value | Rule | Pass |",
        "| --- | --- | --- | --- |",
    ]
    for item in payload["criteria"]:
        lines.append(f"| {item['name']} | `{item['value']}` | {item['rule']} | {'yes' if item['passed'] else 'no'} |")
    lines.extend(
        [
            "",
            "## Per-Task Diagnostic",
            "",
            "| Task | Resonant MSE | v2.3 MSE | Margin vs v2.3 | Sham separated |",
            "| --- | ---: | ---: | ---: | --- |",
        ]
    )
    for row in classification["per_task"]:
        lines.append(
            "| {task} | `{res}` | `{v23}` | `{margin}` | {sham} |".format(
                task=row["task"],
                res=row["resonant_mse"],
                v23=row["v2_3_mse"],
                margin=row["resonant_vs_v2_3_margin"],
                sham="yes" if row["sham_separated"] else "no",
            )
        )
    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            "- `tier5_20a_results.json`",
            "- `tier5_20a_summary.csv`",
            "- `tier5_20a_aggregate.csv`",
            "- `tier5_20a_timeseries.csv` if `--no-timeseries` was not used",
            "- `tier5_20a_branch_contract.json`",
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
    known_tasks = set(TIER6_TASK_BUILDERS) | {"mackey_glass", "lorenz", "narma10", "heldout_long_memory", "recurrence_pressure"}
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
        criterion("all tasks known", tasks, "subset of standard/Tier 6.2a diagnostics", all(task in known_tasks for task in tasks)),
        criterion("same branch budget declared", int(args.branch_count), "== 16 current excitatory neurons", int(args.branch_count) == 16),
        criterion("all required models present", sorted(REQUIRED_MODELS), "all present", all(model in models for model in REQUIRED_MODELS)),
        criterion("all runs completed", f"{sum(r['status'] == 'pass' for r in all_rows)}/{len(all_rows)}", "all pass", all(r["status"] == "pass" for r in all_rows)),
        criterion("resonant shams present", [FLAT, RATE, SHUFFLED], "all present", all(model in models for model in [FLAT, RATE, SHUFFLED])),
        criterion("v2.3 reference present", V23 in models, "== true", V23 in models),
        criterion("public standard tasks included", ["mackey_glass", "lorenz", "narma10"], "all included", all(task in tasks for task in ["mackey_glass", "lorenz", "narma10"])),
        criterion("targeted temporal/anomaly task included", "anomaly_detection_stream" in tasks, "== true", "anomaly_detection_stream" in tasks),
        criterion("classification produced", classification["outcome"], "non-empty", bool(classification["outcome"])),
        criterion("software only", "no PyNN/SpiNNaker calls", "true", True),
    ]
    failed = [item for item in criteria if not item["passed"]]
    branch_contract = {
        "candidate": RESONANT,
        "mechanism": "resonant_lif_branches",
        "polyp_budget": {
            "current_polyp_neurons": 32,
            "input": 8,
            "excitatory_branch_budget": 16,
            "inhibitory": 4,
            "readout": 4,
        },
        "first_test_policy": "software diagnostic proxy before touching canonical organism classes",
        "implementation_hint": "structured LIF subcircuits with delays/time constants; no custom neuron model required for first PyNN/SpiNNaker-safe version",
        "promotion_rule": "promote only to integration gate if benefit or mechanistic sham-separated value appears with no material regression",
        "nonclaims": [
            "not a core polyp replacement",
            "not hardware evidence",
            "not a v2.x baseline freeze",
            "not proof of custom resonate-and-fire neurons",
            "not language/planning/AGI/ASI evidence",
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
        "history": int(args.history),
        "branch_count": int(args.branch_count),
        "runtime_seconds": time.perf_counter() - started,
        "summary_rows": summary_rows,
        "aggregate_rows": aggregate_rows,
        "aggregate_summary": aggregate_summary,
        "classification": classification,
        "summary": classification,
        "run_rows": all_rows,
        "task_diagnostics": task_diagnostics,
        "branch_contract": branch_contract,
        "claim_boundary": (
            "Tier 5.20a is a software-only diagnostic for an optional polyp "
            "internal model. It keeps the current 16-excitatory-neuron budget "
            "as 16 resonant LIF-style branches and compares against v2.3, "
            "v2.2, lag/reservoir/ESN controls, and branch shams. It is not a "
            "canonical organism change, not hardware evidence, and not a "
            "baseline freeze."
        ),
    }
    write_json(output_dir / "tier5_20a_results.json", payload)
    write_json(output_dir / "tier5_20a_branch_contract.json", branch_contract)
    write_csv_rows(output_dir / "tier5_20a_summary.csv", summary_rows)
    write_csv_rows(output_dir / "tier5_20a_aggregate.csv", aggregate_rows)
    write_csv_rows(output_dir / "tier5_20a_aggregate_summary.csv", aggregate_summary)
    if capture_timeseries:
        write_csv_rows(output_dir / "tier5_20a_timeseries.csv", all_timeseries)
    write_report(output_dir / "tier5_20a_report.md", payload)
    latest = {
        "tier": TIER,
        "status": payload["status"],
        "generated_at_utc": payload["generated_at_utc"],
        "output_dir": str(output_dir),
        "results_json": str(output_dir / "tier5_20a_results.json"),
        "report_md": str(output_dir / "tier5_20a_report.md"),
        "summary_csv": str(output_dir / "tier5_20a_summary.csv"),
        "classification": classification["outcome"],
    }
    write_json(OUTPUT_ROOT / "tier5_20a_latest_manifest.json", latest)
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
    parser.add_argument("--branch-count", type=int, default=16)
    parser.add_argument("--max-branch-delay", type=int, default=96)
    parser.add_argument("--branch-gain", type=float, default=1.5)
    parser.add_argument("--temporal-timescales", default="2,4,8,16,32,64,128")
    parser.add_argument("--temporal-hidden-units", type=int, default=16)
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
