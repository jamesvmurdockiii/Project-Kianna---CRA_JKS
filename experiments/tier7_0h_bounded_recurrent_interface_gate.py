#!/usr/bin/env python3
"""Tier 7.0h - Bounded nonlinear recurrent continuous-state/interface gate.

Tier 7.0g selected this mechanism from the measured public benchmark gap:
v2.2 fading memory improves raw CRA, but Mackey-Glass/Lorenz still favor ESN
and NARMA10 still exposes causal-memory/readout limits.

This runner is intentionally software-only. It tests a bounded recurrent
continuous-state candidate against v2.2, public baselines, and recurrence/state
shams on the same standard dynamical tasks. It may recommend promotion,
topology repair, or parking; it does not freeze a baseline and does not
authorize hardware transfer by itself.
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
CONTROLLED = ROOT / "controlled_test_output"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from tier5_19a_temporal_substrate_reference import (  # noqa: E402
    append_timeseries,
    criterion,
    freeze_temporal_columns,
    json_safe,
    parse_timescales,
    random_reservoir_features,
    run_online_model,
    run_train_prefix_esn,
    summarize,
    write_json,
)
from tier5_19b_temporal_substrate_gate import temporal_features_variant  # noqa: E402
from tier5_19c_fading_memory_regression import build_task  # noqa: E402
from tier7_0_standard_dynamical_benchmarks import parse_csv, parse_seeds  # noqa: E402
from tier7_0b_continuous_regression_failure_analysis import lag_matrix  # noqa: E402
from tier7_0c_continuous_readout_repair import shuffled_rows, shuffled_target  # noqa: E402
from tier7_0e_standard_dynamical_v2_2_sweep import (  # noqa: E402
    aggregate_by_model,
    finite_task_descriptor,
    geomean,
    parse_lengths,
    ratio,
    write_rows,
)


TIER = "Tier 7.0h - Bounded Nonlinear Recurrent Continuous-State / Interface Gate"
RUNNER_REVISION = "tier7_0h_bounded_recurrent_interface_gate_20260508_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_0h_20260508_bounded_recurrent_interface_gate"
DEFAULT_TASKS = "mackey_glass,lorenz,narma10"
DEFAULT_LENGTHS = "720,2000,8000"
STANDARD_THREE = {"mackey_glass", "lorenz", "narma10"}

V22 = "fading_memory_only_ablation"
CANDIDATE = "bounded_nonlinear_recurrent_online_candidate"
ESN = "fixed_esn_train_prefix_ridge_baseline"
LAG = "lag_only_online_lms_control"
RESERVOIR = "fixed_random_reservoir_online_control"
RECURRENT_ONLY = "recurrent_hidden_only_ablation"
RESET = "state_reset_ablation"
PERMUTED = "permuted_recurrence_sham"
FROZEN = "frozen_state_ablation"
SHUFFLED = "shuffled_state_sham"
SHUFFLED_TARGET = "shuffled_target_control"
NO_UPDATE = "no_update_ablation"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def model_metric(model_aggregate_rows: list[dict[str, Any]], model: str, key: str = "geomean_mse") -> float | None:
    row = next((item for item in model_aggregate_rows if item.get("model") == model), None)
    if not row or row.get(key) is None:
        return None
    value = float(row[key])
    return value if math.isfinite(value) else None


def write_csv_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        write_rows(path, [])
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def run_task_models(task: Any, *, seed: int, args: argparse.Namespace, capture_timeseries: bool) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    timeseries: list[dict[str, Any]] = []
    timescales = parse_timescales(args.temporal_timescales)
    base_kwargs = {
        "seed": seed,
        "train_end": task.train_end,
        "timescales": timescales,
        "hidden_units": args.temporal_hidden_units,
        "recurrent_scale": args.temporal_recurrent_scale,
        "input_scale": args.temporal_input_scale,
        "hidden_decay": args.temporal_hidden_decay,
    }
    fading = temporal_features_variant(task.observed, mode="fading_only", **base_kwargs)
    full = temporal_features_variant(task.observed, mode="full", **base_kwargs)
    recurrent_only = temporal_features_variant(task.observed, mode="recurrent_only", **base_kwargs)
    reset = temporal_features_variant(
        task.observed,
        mode="full",
        reset_interval=args.state_reset_interval,
        **base_kwargs,
    )
    permuted = temporal_features_variant(
        task.observed,
        mode="permuted_recurrence",
        recurrent_seed_offset=args.permuted_recurrent_seed_offset,
        **base_kwargs,
    )
    lag = lag_matrix(task.observed, args.history)
    reservoir = random_reservoir_features(
        task.observed,
        seed=seed,
        units=args.reservoir_units,
        spectral_radius=args.reservoir_spectral_radius,
        input_scale=args.reservoir_input_scale,
    )
    wrong_target = shuffled_target(task.target, task.train_end, seed)
    specs: list[tuple[str, np.ndarray, np.ndarray | None, bool, dict[str, Any]]] = [
        (LAG, lag, None, True, {"role": "same causal lag budget", "history": int(args.history)}),
        (RESERVOIR, reservoir.features, None, True, reservoir.diagnostics),
        (V22, fading.features, None, True, {**fading.diagnostics, "role": "v2.2 bounded fading-memory reference"}),
        (CANDIDATE, full.features, None, True, {**full.diagnostics, "role": "selected bounded nonlinear recurrent state/interface candidate"}),
        (RECURRENT_ONLY, recurrent_only.features, None, True, {**recurrent_only.diagnostics, "ablation": "recurrent hidden state without fading traces"}),
        (RESET, reset.features, None, True, {**reset.diagnostics, "ablation": "candidate state reset on a fixed interval"}),
        (PERMUTED, permuted.features, None, True, {**permuted.diagnostics, "sham": "recurrent topology permuted while preserving input projection"}),
        (
            FROZEN,
            freeze_temporal_columns(full.features, task.train_end, full.temporal_start),
            None,
            True,
            {**full.diagnostics, "ablation": "recurrent/state columns frozen after train prefix"},
        ),
        (SHUFFLED, shuffled_rows(full.features, task.train_end, seed), None, True, {**full.diagnostics, "sham": "state rows shuffled within train/test splits"}),
        (SHUFFLED_TARGET, full.features, wrong_target, True, {**full.diagnostics, "control": "candidate readout updates against shuffled targets"}),
        (NO_UPDATE, full.features, None, False, {**full.diagnostics, "ablation": "candidate readout updates disabled"}),
    ]
    for model, features, update_target, update_enabled, diagnostics in specs:
        row, pred = run_online_model(
            task=task,
            seed=seed,
            model=model,
            features=features,
            args=args,
            update_target=update_target,
            update_enabled=update_enabled,
            diagnostics={**diagnostics, "tier7_0h_model_family": "bounded_recurrent_interface_gate"},
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
        "candidate_feature_count": int(full.features.shape[1]),
        "v2_2_feature_count": int(fading.features.shape[1]),
        "lag_feature_count": int(lag.shape[1]),
        "reservoir_feature_count": int(reservoir.features.shape[1]),
        "candidate_state_norm_train_mean": full.diagnostics.get("train_prefix_state_norm_mean"),
        "candidate_state_norm_test_mean": full.diagnostics.get("test_state_norm_mean"),
    }
    return rows, timeseries, diagnostics


def run_one_length(length: int, args: argparse.Namespace, output_dir: Path) -> dict[str, Any]:
    tasks = parse_csv(args.tasks)
    seeds = parse_seeds(args)
    length_dir = output_dir / f"length_{length}"
    length_dir.mkdir(parents=True, exist_ok=True)
    capture_timeseries = int(length) <= int(args.timeseries_max_length)
    all_rows: list[dict[str, Any]] = []
    all_timeseries: list[dict[str, Any]] = []
    task_descriptors: list[dict[str, Any]] = []
    task_diagnostics: list[dict[str, Any]] = []
    invalid_tasks: list[dict[str, Any]] = []
    started = time.perf_counter()
    for seed in seeds:
        for task_name in tasks:
            task = build_task(task_name, length, seed, args.horizon)
            finite_descriptor = finite_task_descriptor(task)
            descriptor = {
                "length": int(length),
                "task": task.name,
                "display_name": task.display_name,
                "seed": int(seed),
                "sample_count": int(len(task.target)),
                "train_end": int(task.train_end),
                "test_count": int(len(task.target) - task.train_end),
                "horizon": int(task.horizon),
                "metadata": task.metadata,
                "finite_check": finite_descriptor,
            }
            task_descriptors.append(descriptor)
            write_json(length_dir / f"{task.name}_seed{seed}_task.json", descriptor)
            if not (finite_descriptor["observed_finite"] and finite_descriptor["target_finite"]):
                invalid_tasks.append(descriptor)
                task_diagnostics.append(
                    {
                        "length": int(length),
                        "task": task.name,
                        "seed": int(seed),
                        "status": "invalid_task_stream",
                        "finite_check": finite_descriptor,
                        "reason": "generated observed/target stream contains non-finite values; model scoring skipped",
                    }
                )
                continue
            rows, timeseries, diagnostics = run_task_models(task, seed=seed, args=args, capture_timeseries=capture_timeseries)
            for row in rows:
                row["length"] = int(length)
            for row in timeseries:
                row["length"] = int(length)
            all_rows.extend(rows)
            if capture_timeseries:
                all_timeseries.extend(timeseries)
            task_diagnostics.append({"length": int(length), **diagnostics})
    models = sorted({str(row["model"]) for row in all_rows})
    summary_rows, seed_aggregate_rows, seed_aggregate_summary = summarize(all_rows, tasks, models, seeds)
    for row in summary_rows:
        row["length"] = int(length)
    for row in seed_aggregate_rows:
        row["length"] = int(length)
    for row in seed_aggregate_summary:
        row["length"] = int(length)
    model_aggregate_rows = aggregate_by_model(summary_rows, tasks)
    for row in model_aggregate_rows:
        row["length"] = int(length)
    runtime_seconds = time.perf_counter() - started
    write_csv_rows(length_dir / "tier7_0h_summary.csv", summary_rows)
    write_csv_rows(length_dir / "tier7_0h_seed_aggregate.csv", seed_aggregate_rows)
    write_csv_rows(length_dir / "tier7_0h_model_aggregate.csv", model_aggregate_rows)
    if capture_timeseries:
        write_csv_rows(length_dir / "tier7_0h_timeseries.csv", all_timeseries)
    write_json(
        length_dir / "tier7_0h_length_results.json",
        {
            "tier": TIER,
            "runner_revision": RUNNER_REVISION,
            "length": int(length),
            "tasks": tasks,
            "seeds": seeds,
            "models": models,
            "summary_rows": summary_rows,
            "seed_aggregate_rows": seed_aggregate_rows,
            "seed_aggregate_summary": seed_aggregate_summary,
            "model_aggregate_rows": model_aggregate_rows,
            "task_descriptors": task_descriptors,
            "invalid_tasks": invalid_tasks,
            "task_diagnostics": task_diagnostics,
            "timeseries_policy": {
                "captured": bool(capture_timeseries),
                "timeseries_max_length": int(args.timeseries_max_length),
            },
            "runtime_seconds": runtime_seconds,
        },
    )
    return {
        "length": int(length),
        "runtime_seconds": runtime_seconds,
        "timeseries_captured": bool(capture_timeseries),
        "tasks": tasks,
        "seeds": seeds,
        "models": models,
        "summary_rows": summary_rows,
        "seed_aggregate_rows": seed_aggregate_rows,
        "seed_aggregate_summary": seed_aggregate_summary,
        "model_aggregate_rows": model_aggregate_rows,
        "invalid_tasks": invalid_tasks,
    }


def classify(length_results: list[dict[str, Any]], requested_lengths: list[int]) -> dict[str, Any]:
    by_length: dict[int, dict[str, Any]] = {}
    for result in length_results:
        length = int(result["length"])
        aggregate = result["model_aggregate_rows"]
        candidate = model_metric(aggregate, CANDIDATE)
        v22 = model_metric(aggregate, V22)
        esn = model_metric(aggregate, ESN)
        lag = model_metric(aggregate, LAG)
        reservoir = model_metric(aggregate, RESERVOIR)
        controls = {
            RESET: model_metric(aggregate, RESET),
            PERMUTED: model_metric(aggregate, PERMUTED),
            RECURRENT_ONLY: model_metric(aggregate, RECURRENT_ONLY),
            FROZEN: model_metric(aggregate, FROZEN),
            SHUFFLED: model_metric(aggregate, SHUFFLED),
            SHUFFLED_TARGET: model_metric(aggregate, SHUFFLED_TARGET),
            NO_UPDATE: model_metric(aggregate, NO_UPDATE),
        }
        by_length[length] = {
            "candidate_mse": candidate,
            "v2_2_mse": v22,
            "esn_mse": esn,
            "lag_mse": lag,
            "reservoir_mse": reservoir,
            "margin_vs_v2_2": ratio(v22, candidate),
            "candidate_divided_by_esn": ratio(candidate, esn),
            "v2_2_divided_by_esn": ratio(v22, esn),
            "margin_vs_lag": ratio(lag, candidate),
            "margin_vs_reservoir": ratio(reservoir, candidate),
            "control_mse": controls,
            "control_margins": {name: ratio(value, candidate) for name, value in controls.items()},
        }
    completed_lengths = sorted(by_length)
    longest_length = max(completed_lengths) if completed_lengths else None
    longest = by_length.get(longest_length, {})
    improvement_vs_v22 = longest.get("margin_vs_v2_2")
    beats_simple_online = (
        longest.get("margin_vs_lag") is not None
        and float(longest["margin_vs_lag"]) >= 1.0
        and longest.get("margin_vs_reservoir") is not None
        and float(longest["margin_vs_reservoir"]) >= 1.0
    )
    esn_gap_narrowed = (
        longest.get("candidate_divided_by_esn") is not None
        and longest.get("v2_2_divided_by_esn") is not None
        and float(longest["candidate_divided_by_esn"]) < float(longest["v2_2_divided_by_esn"])
    )
    control_margins = longest.get("control_margins", {})
    destructive_controls_separated = all(
        control_margins.get(name) is not None and float(control_margins[name]) >= 1.25
        for name in [FROZEN, SHUFFLED, SHUFFLED_TARGET, NO_UPDATE]
    )
    recurrence_controls_separated = all(
        control_margins.get(name) is not None and float(control_margins[name]) >= threshold
        for name, threshold in [(RESET, 1.05), (PERMUTED, 1.10), (RECURRENT_ONLY, 1.10)]
    )
    improves_materially = improvement_vs_v22 is not None and float(improvement_vs_v22) >= 1.25
    all_requested_completed = sorted(requested_lengths) == completed_lengths
    if improves_materially and beats_simple_online and esn_gap_narrowed and destructive_controls_separated and recurrence_controls_separated:
        outcome = "bounded_recurrent_candidate_promotable_pending_compact_regression"
        recommendation = "Run compact regression/promotion gate before any baseline freeze or hardware transfer."
        promotion_recommended = True
    elif improves_materially and beats_simple_online and esn_gap_narrowed and destructive_controls_separated:
        outcome = "bounded_recurrent_candidate_improves_scoreboard_but_topology_specificity_unproven"
        recommendation = "Do not freeze yet; run topology-specificity repair/gate before promoting bounded nonlinear recurrence."
        promotion_recommended = False
    elif improves_materially:
        outcome = "bounded_recurrent_candidate_improves_v2_2_but_controls_or_baselines_block_promotion"
        recommendation = "Keep as diagnostic; inspect which controls or public baselines still explain the gain."
        promotion_recommended = False
    else:
        outcome = "bounded_recurrent_candidate_not_supported"
        recommendation = "Park or redesign; do not layer hardware/native work on this mechanism."
        promotion_recommended = False
    return {
        "outcome": outcome,
        "recommendation": recommendation,
        "promotion_recommended": bool(promotion_recommended),
        "requested_lengths": requested_lengths,
        "completed_lengths": completed_lengths,
        "all_requested_lengths_completed": bool(all_requested_completed),
        "longest_length": longest_length,
        "by_length": by_length,
        "longest_improvement_vs_v2_2": improvement_vs_v22,
        "longest_beats_simple_online": bool(beats_simple_online),
        "longest_esn_gap_narrowed": bool(esn_gap_narrowed),
        "destructive_controls_separated": bool(destructive_controls_separated),
        "recurrence_controls_separated": bool(recurrence_controls_separated),
        "claim": (
            "bounded nonlinear recurrent continuous-state candidate improved public scoreboard versus v2.2"
            if improves_materially
            else "no bounded nonlinear recurrent public-scoreboard improvement"
        ),
        "nonclaims": [
            "not hardware evidence",
            "not native on-chip recurrence",
            "not a baseline freeze",
            "not ESN superiority",
            "not universal benchmark superiority",
            "not sleep/replay, lifecycle, planning, language, AGI, or ASI",
        ],
    }


def write_report(output_dir: Path, payload: dict[str, Any]) -> None:
    c = payload["classification"]
    lines = [
        "# Tier 7.0h Bounded Recurrent Interface Gate",
        "",
        f"- Generated: `{payload['generated_at_utc']}`",
        f"- Status: **{payload['status'].upper()}**",
        f"- Criteria: `{payload['criteria_passed']}/{payload['criteria_total']}`",
        f"- Outcome: `{c['outcome']}`",
        f"- Recommendation: {c['recommendation']}",
        "",
        "## Claim Boundary",
        "",
        payload["claim_boundary"],
        "",
        "## Length Results",
        "",
        "| Length | Candidate MSE | v2.2 MSE | ESN MSE | Candidate/v2.2 improvement | Candidate/ESN | Lag margin | Reservoir margin |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for length, values in sorted(c["by_length"].items()):
        lines.append(
            "| "
            f"{length} | "
            f"{values['candidate_mse']} | "
            f"{values['v2_2_mse']} | "
            f"{values['esn_mse']} | "
            f"{values['margin_vs_v2_2']} | "
            f"{values['candidate_divided_by_esn']} | "
            f"{values['margin_vs_lag']} | "
            f"{values['margin_vs_reservoir']} |"
        )
    lines.extend(
        [
            "",
            "## Longest-Length Control Margins",
            "",
        ]
    )
    longest = c["by_length"].get(c["longest_length"], {})
    for name, value in sorted((longest.get("control_margins") or {}).items()):
        lines.append(f"- `{name}` margin vs candidate: `{value}`")
    lines.extend(
        [
            "",
            "## Promotion Checks",
            "",
            f"- Material improvement versus v2.2: `{c['longest_improvement_vs_v2_2']}`",
            f"- Beats lag and random-reservoir online controls: `{c['longest_beats_simple_online']}`",
            f"- ESN gap narrowed: `{c['longest_esn_gap_narrowed']}`",
            f"- Destructive controls separated: `{c['destructive_controls_separated']}`",
            f"- Recurrence/topology controls separated: `{c['recurrence_controls_separated']}`",
            f"- Promotion recommended: `{c['promotion_recommended']}`",
            "",
            "## Nonclaims",
            "",
        ]
    )
    for item in c["nonclaims"]:
        lines.append(f"- {item}")
    lines.append("")
    (output_dir / "tier7_0h_report.md").write_text("\n".join(lines), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=TIER)
    parser.add_argument("--tasks", default=DEFAULT_TASKS)
    parser.add_argument("--seeds", default="42,43,44")
    parser.add_argument("--seed-count", type=int, default=None)
    parser.add_argument("--base-seed", type=int, default=42)
    parser.add_argument("--lengths", default=DEFAULT_LENGTHS)
    parser.add_argument("--horizon", type=int, default=8)
    parser.add_argument("--history", type=int, default=12)
    parser.add_argument("--readout-lr", type=float, default=0.08)
    parser.add_argument("--readout-decay", type=float, default=1e-5)
    parser.add_argument("--weight-clip", type=float, default=20.0)
    parser.add_argument("--output-clip", type=float, default=3.0)
    parser.add_argument("--ridge", type=float, default=1e-3)
    parser.add_argument("--temporal-timescales", default="2,4,8,16,32,64,128")
    parser.add_argument("--temporal-hidden-units", type=int, default=16)
    parser.add_argument("--temporal-recurrent-scale", type=float, default=0.65)
    parser.add_argument("--temporal-input-scale", type=float, default=0.45)
    parser.add_argument("--temporal-hidden-decay", type=float, default=0.72)
    parser.add_argument("--state-reset-interval", type=int, default=24)
    parser.add_argument("--permuted-recurrent-seed-offset", type=int, default=71)
    parser.add_argument("--reservoir-units", type=int, default=32)
    parser.add_argument("--reservoir-spectral-radius", type=float, default=0.9)
    parser.add_argument("--reservoir-input-scale", type=float, default=0.5)
    parser.add_argument("--esn-units", type=int, default=64)
    parser.add_argument("--esn-spectral-radius", type=float, default=0.9)
    parser.add_argument("--esn-input-scale", type=float, default=0.5)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--timeseries-max-length", type=int, default=720)
    return parser


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if args.smoke:
        args.tasks = "mackey_glass"
        args.seeds = "42"
        args.lengths = "720"
    tasks = parse_csv(args.tasks)
    lengths = parse_lengths(args.lengths)
    started = time.perf_counter()
    length_results = [run_one_length(length, args, output_dir) for length in lengths]
    classification = classify(length_results, lengths)
    invalid_count = sum(len(result["invalid_tasks"]) for result in length_results)
    criteria = [
        criterion("standard task subset only", sorted(tasks), "subset of standard three", set(tasks).issubset(STANDARD_THREE)),
        criterion("generated benchmark streams finite", invalid_count, "0 invalid task streams", invalid_count == 0),
        criterion("length sweep completed", classification["completed_lengths"], "== requested lengths", classification["all_requested_lengths_completed"]),
        criterion("v2.2 reference present", V22, "present for every length", all(model_metric(result["model_aggregate_rows"], V22) is not None for result in length_results)),
        criterion("bounded recurrent candidate present", CANDIDATE, "present for every length", all(model_metric(result["model_aggregate_rows"], CANDIDATE) is not None for result in length_results)),
        criterion("public baselines present", [ESN, LAG, RESERVOIR], "present for every length", all(all(model_metric(result["model_aggregate_rows"], model) is not None for model in [ESN, LAG, RESERVOIR]) for result in length_results)),
        criterion("destructive controls present", [FROZEN, SHUFFLED, SHUFFLED_TARGET, NO_UPDATE], "present for every length", all(all(model_metric(result["model_aggregate_rows"], model) is not None for model in [FROZEN, SHUFFLED, SHUFFLED_TARGET, NO_UPDATE]) for result in length_results)),
        criterion("recurrence controls present", [RESET, PERMUTED, RECURRENT_ONLY], "present for every length", all(all(model_metric(result["model_aggregate_rows"], model) is not None for model in [RESET, PERMUTED, RECURRENT_ONLY]) for result in length_results)),
        criterion("classification produced", classification["outcome"], "non-empty", bool(classification["outcome"])),
        criterion("no baseline freeze authorized by this tier", classification["promotion_recommended"], "may recommend only; never freeze", True),
    ]
    criteria_passed = sum(1 for item in criteria if item["passed"])
    payload = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "status": "pass" if criteria_passed == len(criteria) else "fail",
        "criteria": criteria,
        "criteria_passed": criteria_passed,
        "criteria_total": len(criteria),
        "output_dir": str(output_dir),
        "tasks": tasks,
        "seeds": parse_seeds(args),
        "lengths": lengths,
        "classification": classification,
        "length_results": length_results,
        "runtime_seconds": time.perf_counter() - started,
        "claim_boundary": (
            "Tier 7.0h is software public-benchmark mechanism evidence only. It tests a bounded nonlinear recurrent "
            "continuous-state/interface candidate against v2.2, public baselines, and shams. It is not hardware evidence, "
            "not native on-chip recurrence, not a baseline freeze, and not AGI/ASI evidence."
        ),
        "fairness_contract": {
            "public_tasks": tasks,
            "lengths": lengths,
            "seeds": parse_seeds(args),
            "readout_policy": "online normalized LMS prediction-before-update for candidate/v2.2/controls; ESN keeps train-prefix ridge baseline role",
            "finite_stream_policy": "all generated task streams must be finite; 8000 is the largest original-seed finite length from Tier 7.0f",
            "hardware_policy": "blocked until software usefulness and compact regression earn transfer",
            "custom_task_policy": "no private synthetic tasks in this runner",
        },
    }
    write_json(output_dir / "tier7_0h_results.json", payload)
    write_json(output_dir / "tier7_0h_fairness_contract.json", payload["fairness_contract"])
    write_report(output_dir, payload)
    summary_rows = [
        {
            "status": payload["status"],
            "criteria_passed": criteria_passed,
            "criteria_total": len(criteria),
            "outcome": classification["outcome"],
            "promotion_recommended": classification["promotion_recommended"],
            "longest_length": classification["longest_length"],
            "longest_improvement_vs_v2_2": classification["longest_improvement_vs_v2_2"],
            "longest_beats_simple_online": classification["longest_beats_simple_online"],
            "longest_esn_gap_narrowed": classification["longest_esn_gap_narrowed"],
            "destructive_controls_separated": classification["destructive_controls_separated"],
            "recurrence_controls_separated": classification["recurrence_controls_separated"],
        }
    ]
    write_csv_rows(output_dir / "tier7_0h_summary.csv", summary_rows)
    all_model_aggregate_rows: list[dict[str, Any]] = []
    for result in length_results:
        all_model_aggregate_rows.extend(result["model_aggregate_rows"])
    write_csv_rows(output_dir / "tier7_0h_model_aggregate.csv", all_model_aggregate_rows)
    manifest = {
        "tier": TIER,
        "status": payload["status"],
        "generated_at_utc": payload["generated_at_utc"],
        "output_dir": str(output_dir),
        "results_json": str(output_dir / "tier7_0h_results.json"),
        "report_md": str(output_dir / "tier7_0h_report.md"),
        "summary_csv": str(output_dir / "tier7_0h_summary.csv"),
        "model_aggregate_csv": str(output_dir / "tier7_0h_model_aggregate.csv"),
    }
    write_json(output_dir / "tier7_0h_latest_manifest.json", manifest)
    write_json(CONTROLLED / "tier7_0h_latest_manifest.json", manifest)
    return payload


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    payload = run(args)
    print(json.dumps(json_safe({"status": payload["status"], "classification": payload["classification"]}), indent=2, sort_keys=True))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
