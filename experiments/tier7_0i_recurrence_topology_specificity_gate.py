#!/usr/bin/env python3
"""Tier 7.0i - Recurrence / topology specificity repair gate.

Tier 7.0h showed a useful public-scoreboard improvement from bounded recurrent
state, but the permuted-recurrence sham stayed too close. This tier asks the
next bounded question:

    Is there evidence for a topology-specific recurrent mechanism, or is the
    useful effect better described as a generic bounded recurrent state bank?

The runner keeps the same public Mackey-Glass, Lorenz, and NARMA10 suite,
lengths, seeds, and baselines. It adds a structured cascade recurrence candidate
with stricter topology shams. It is software-only and cannot freeze a baseline
or authorize hardware transfer by itself.
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
    FeatureBundle,
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
    parse_lengths,
    ratio,
    write_rows,
)


TIER = "Tier 7.0i - Recurrence / Topology Specificity Repair Gate"
RUNNER_REVISION = "tier7_0i_recurrence_topology_specificity_gate_20260508_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_0i_20260508_recurrence_topology_specificity_gate"
DEFAULT_TASKS = "mackey_glass,lorenz,narma10"
DEFAULT_LENGTHS = "720,2000,8000"
STANDARD_THREE = {"mackey_glass", "lorenz", "narma10"}

V22 = "fading_memory_only_ablation"
GENERIC_70H = "generic_bounded_recurrent_reference_7_0h"
STRUCTURED = "structured_cascade_recurrent_candidate"
SHUFFLED_TOPOLOGY = "structured_topology_shuffle_sham"
REVERSED_TOPOLOGY = "structured_reversed_cascade_sham"
RANDOM_REWIRE = "structured_random_rewire_sham"
NO_RECURRENT_TOPOLOGY = "structured_no_recurrence_ablation"
STRUCTURED_FROZEN = "structured_frozen_state_ablation"
STRUCTURED_SHUFFLED_STATE = "structured_shuffled_state_sham"
STRUCTURED_SHUFFLED_TARGET = "structured_shuffled_target_control"
STRUCTURED_NO_UPDATE = "structured_no_update_ablation"
ESN = "fixed_esn_train_prefix_ridge_baseline"
LAG = "lag_only_online_lms_control"
RESERVOIR = "fixed_random_reservoir_online_control"


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


def _structured_recurrence_matrix(
    hidden_units: int,
    *,
    coupling: float,
    mode: str,
    seed: int,
) -> np.ndarray:
    """Build a bounded recurrent topology with matched sham variants.

    The candidate is a sparse signed cascade: adjacent state channels exchange
    fast-to-slow excitation and slow-to-fast contrast. Shams preserve most gross
    properties while disrupting the ordered topology.
    """
    size = int(hidden_units)
    matrix = np.zeros((size, size), dtype=float)
    for idx in range(size):
        if idx > 0:
            matrix[idx, idx - 1] += float(coupling)
        if idx + 1 < size:
            matrix[idx, idx + 1] -= 0.45 * float(coupling)
        if idx >= 4:
            matrix[idx, idx - 4] += 0.25 * float(coupling)
    if mode == "candidate":
        return matrix
    if mode == "reversed":
        return matrix[::-1, ::-1]
    if mode == "shuffle":
        rng = np.random.default_rng(seed + 7011)
        perm = np.arange(size)
        rng.shuffle(perm)
        # Keep row ownership and input assignment fixed; shuffle recurrence
        # sources only so the readout cannot dismiss this as column relabeling.
        return matrix[:, perm]
    if mode == "random_rewire":
        rng = np.random.default_rng(seed + 7027)
        positions = np.argwhere(np.abs(matrix) > 0.0)
        values = matrix[np.abs(matrix) > 0.0].copy()
        rng.shuffle(values)
        rewired = np.zeros_like(matrix)
        for value in values:
            for _ in range(1000):
                dst = int(rng.integers(0, size))
                src = int(rng.integers(0, size))
                if dst != src and rewired[dst, src] == 0.0:
                    rewired[dst, src] = float(value)
                    break
            else:
                # Fallback should be unreachable at this sparsity, but keep
                # deterministic behavior if the matrix changes later.
                dst, src = positions[int(rng.integers(0, len(positions)))]
                rewired[int(dst), int(src)] = float(value)
        return rewired
    if mode == "no_recurrence":
        return np.zeros_like(matrix)
    raise ValueError(f"unknown structured recurrence mode {mode!r}")


def structured_cascade_features(
    observed: np.ndarray,
    *,
    seed: int,
    train_end: int,
    timescales: list[float],
    hidden_units: int,
    input_scale: float,
    coupling: float,
    hidden_decay: float,
    mode: str,
) -> FeatureBundle:
    values = np.asarray(observed, dtype=float)
    traces = np.zeros(len(timescales), dtype=float)
    hidden_size = max(int(hidden_units), len(timescales))
    hidden = np.zeros(hidden_size, dtype=float)
    matrix = _structured_recurrence_matrix(hidden_size, coupling=coupling, mode=mode, seed=seed)
    tau_assignment = np.arange(hidden_size) % len(timescales)
    if mode == "shuffle":
        rng = np.random.default_rng(seed + 7039)
        rng.shuffle(tau_assignment)
    elif mode == "reversed":
        tau_assignment = tau_assignment[::-1]
    leak = np.asarray([math.exp(-1.0 / max(1.0, timescales[idx])) for idx in tau_assignment], dtype=float)
    rows: list[np.ndarray] = []
    for value in values:
        x = float(value)
        previous_traces = traces.copy()
        for idx, tau in enumerate(timescales):
            alpha = 1.0 - math.exp(-1.0 / max(1e-6, float(tau)))
            traces[idx] = traces[idx] + alpha * (x - traces[idx])
        trace_deltas = np.diff(traces) if traces.size > 1 else np.asarray([], dtype=float)
        novelty = x - float(previous_traces[-1] if previous_traces.size else 0.0)
        driver = np.zeros(hidden_size, dtype=float)
        for idx, tau_idx in enumerate(tau_assignment):
            base = traces[tau_idx]
            delta = trace_deltas[min(tau_idx, len(trace_deltas) - 1)] if len(trace_deltas) else 0.0
            driver[idx] = base + 0.35 * delta + 0.15 * novelty
        hidden = np.tanh(leak * hidden + matrix @ hidden + float(input_scale) * driver)
        row = np.concatenate([[1.0, x], traces, trace_deltas, [novelty], hidden])
        rows.append(row)
    names = ["bias", "observed_current"]
    names.extend([f"ema_tau_{tau:g}" for tau in timescales])
    names.extend([f"ema_delta_{i}_{i + 1}" for i in range(max(0, len(timescales) - 1))])
    names.append("novelty_vs_slowest_ema")
    names.extend([f"structured_hidden_{idx}" for idx in range(hidden_size)])
    features = np.vstack(rows)
    return FeatureBundle(
        features=features,
        temporal_start=2,
        names=names,
        diagnostics={
            "state_location": "structured_cascade_recurrent_state_interface",
            "mode": mode,
            "timescales": timescales,
            "hidden_units": int(hidden_size),
            "input_scale": float(input_scale),
            "coupling": float(coupling),
            "hidden_decay": float(hidden_decay),
            "feature_count": int(features.shape[1]),
            "nonzero_recurrent_edges": int(np.count_nonzero(matrix)),
            "train_prefix_state_norm_mean": float(np.mean(np.linalg.norm(features[:train_end, 2:], axis=1))),
            "test_state_norm_mean": float(np.mean(np.linalg.norm(features[train_end:, 2:], axis=1))),
            "topology_hypothesis": "ordered sparse cascade should outperform matched rewiring if topology is causal",
        },
    )


def run_task_models(task: Any, *, seed: int, args: argparse.Namespace, capture_timeseries: bool) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    timeseries: list[dict[str, Any]] = []
    timescales = parse_timescales(args.temporal_timescales)
    common = {
        "seed": seed,
        "train_end": task.train_end,
        "timescales": timescales,
        "hidden_units": args.temporal_hidden_units,
        "input_scale": args.structured_input_scale,
        "coupling": args.structured_coupling,
        "hidden_decay": args.temporal_hidden_decay,
    }
    structured = structured_cascade_features(task.observed, mode="candidate", **common)
    topo_shuffle = structured_cascade_features(task.observed, mode="shuffle", **common)
    reversed_topology = structured_cascade_features(task.observed, mode="reversed", **common)
    random_rewire = structured_cascade_features(task.observed, mode="random_rewire", **common)
    no_recurrence = structured_cascade_features(task.observed, mode="no_recurrence", **common)
    generic_70h = temporal_features_variant(
        task.observed,
        seed=seed,
        train_end=task.train_end,
        timescales=timescales,
        hidden_units=args.temporal_hidden_units,
        recurrent_scale=args.temporal_recurrent_scale,
        input_scale=args.temporal_input_scale,
        hidden_decay=args.temporal_hidden_decay,
        mode="full",
    )
    fading = temporal_features_variant(
        task.observed,
        seed=seed,
        train_end=task.train_end,
        timescales=timescales,
        hidden_units=args.temporal_hidden_units,
        recurrent_scale=args.temporal_recurrent_scale,
        input_scale=args.temporal_input_scale,
        hidden_decay=args.temporal_hidden_decay,
        mode="fading_only",
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
        (GENERIC_70H, generic_70h.features, None, True, {**generic_70h.diagnostics, "role": "Tier 7.0h generic bounded recurrent reference"}),
        (STRUCTURED, structured.features, None, True, {**structured.diagnostics, "role": "structured sparse cascade recurrence candidate"}),
        (SHUFFLED_TOPOLOGY, topo_shuffle.features, None, True, {**topo_shuffle.diagnostics, "sham": "input assignment and recurrence sources shuffled"}),
        (REVERSED_TOPOLOGY, reversed_topology.features, None, True, {**reversed_topology.diagnostics, "sham": "cascade direction reversed"}),
        (RANDOM_REWIRE, random_rewire.features, None, True, {**random_rewire.diagnostics, "sham": "same sparse edge count randomly rewired"}),
        (NO_RECURRENT_TOPOLOGY, no_recurrence.features, None, True, {**no_recurrence.diagnostics, "ablation": "structured candidate without recurrent topology"}),
        (
            STRUCTURED_FROZEN,
            freeze_temporal_columns(structured.features, task.train_end, structured.temporal_start),
            None,
            True,
            {**structured.diagnostics, "ablation": "structured recurrent state frozen after train prefix"},
        ),
        (STRUCTURED_SHUFFLED_STATE, shuffled_rows(structured.features, task.train_end, seed), None, True, {**structured.diagnostics, "sham": "structured rows shuffled within train/test splits"}),
        (STRUCTURED_SHUFFLED_TARGET, structured.features, wrong_target, True, {**structured.diagnostics, "control": "structured readout updates against shuffled target"}),
        (STRUCTURED_NO_UPDATE, structured.features, None, False, {**structured.diagnostics, "ablation": "structured readout updates disabled"}),
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
            diagnostics={**diagnostics, "tier7_0i_model_family": "recurrence_topology_specificity_gate"},
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
        "structured_feature_count": int(structured.features.shape[1]),
        "generic_7_0h_feature_count": int(generic_70h.features.shape[1]),
        "v2_2_feature_count": int(fading.features.shape[1]),
        "lag_feature_count": int(lag.shape[1]),
        "reservoir_feature_count": int(reservoir.features.shape[1]),
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
    write_csv_rows(length_dir / "tier7_0i_summary.csv", summary_rows)
    write_csv_rows(length_dir / "tier7_0i_seed_aggregate.csv", seed_aggregate_rows)
    write_csv_rows(length_dir / "tier7_0i_model_aggregate.csv", model_aggregate_rows)
    if capture_timeseries:
        write_csv_rows(length_dir / "tier7_0i_timeseries.csv", all_timeseries)
    write_json(
        length_dir / "tier7_0i_length_results.json",
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
        structured = model_metric(aggregate, STRUCTURED)
        generic = model_metric(aggregate, GENERIC_70H)
        v22 = model_metric(aggregate, V22)
        esn = model_metric(aggregate, ESN)
        lag = model_metric(aggregate, LAG)
        reservoir = model_metric(aggregate, RESERVOIR)
        controls = {
            SHUFFLED_TOPOLOGY: model_metric(aggregate, SHUFFLED_TOPOLOGY),
            REVERSED_TOPOLOGY: model_metric(aggregate, REVERSED_TOPOLOGY),
            RANDOM_REWIRE: model_metric(aggregate, RANDOM_REWIRE),
            NO_RECURRENT_TOPOLOGY: model_metric(aggregate, NO_RECURRENT_TOPOLOGY),
            STRUCTURED_FROZEN: model_metric(aggregate, STRUCTURED_FROZEN),
            STRUCTURED_SHUFFLED_STATE: model_metric(aggregate, STRUCTURED_SHUFFLED_STATE),
            STRUCTURED_SHUFFLED_TARGET: model_metric(aggregate, STRUCTURED_SHUFFLED_TARGET),
            STRUCTURED_NO_UPDATE: model_metric(aggregate, STRUCTURED_NO_UPDATE),
        }
        by_length[length] = {
            "structured_mse": structured,
            "generic_7_0h_mse": generic,
            "v2_2_mse": v22,
            "esn_mse": esn,
            "lag_mse": lag,
            "reservoir_mse": reservoir,
            "structured_margin_vs_v2_2": ratio(v22, structured),
            "generic_margin_vs_v2_2": ratio(v22, generic),
            "structured_divided_by_esn": ratio(structured, esn),
            "generic_divided_by_esn": ratio(generic, esn),
            "structured_margin_vs_generic": ratio(generic, structured),
            "structured_margin_vs_lag": ratio(lag, structured),
            "structured_margin_vs_reservoir": ratio(reservoir, structured),
            "control_mse": controls,
            "control_margins": {name: ratio(value, structured) for name, value in controls.items()},
        }
    completed_lengths = sorted(by_length)
    longest_length = max(completed_lengths) if completed_lengths else None
    longest = by_length.get(longest_length, {})
    structured_improves_v22 = longest.get("structured_margin_vs_v2_2") is not None and float(longest["structured_margin_vs_v2_2"]) >= 1.25
    generic_improves_v22 = longest.get("generic_margin_vs_v2_2") is not None and float(longest["generic_margin_vs_v2_2"]) >= 1.25
    structured_beats_public_online = (
        longest.get("structured_margin_vs_lag") is not None
        and float(longest["structured_margin_vs_lag"]) >= 1.0
        and longest.get("structured_margin_vs_reservoir") is not None
        and float(longest["structured_margin_vs_reservoir"]) >= 1.0
    )
    topology_margins = longest.get("control_margins", {})
    topology_controls_separated = all(
        topology_margins.get(name) is not None and float(topology_margins[name]) >= 1.10
        for name in [SHUFFLED_TOPOLOGY, REVERSED_TOPOLOGY, RANDOM_REWIRE, NO_RECURRENT_TOPOLOGY]
    )
    destructive_controls_separated = all(
        topology_margins.get(name) is not None and float(topology_margins[name]) >= 1.25
        for name in [STRUCTURED_FROZEN, STRUCTURED_SHUFFLED_STATE, STRUCTURED_SHUFFLED_TARGET, STRUCTURED_NO_UPDATE]
    )
    structured_matches_or_beats_generic = (
        longest.get("structured_margin_vs_generic") is not None
        and float(longest["structured_margin_vs_generic"]) >= 0.95
    )
    if structured_improves_v22 and structured_beats_public_online and topology_controls_separated and destructive_controls_separated and structured_matches_or_beats_generic:
        outcome = "topology_specific_recurrence_promotable_pending_compact_regression"
        recommendation = "Run compact regression before any freeze or hardware transfer."
        promotion_recommended = True
    elif generic_improves_v22 and not topology_controls_separated:
        outcome = "generic_bounded_recurrent_state_supported_topology_specificity_not_supported"
        recommendation = "Do not claim topology-specific recurrence; consider a narrower generic bounded recurrent-state promotion gate."
        promotion_recommended = False
    elif structured_improves_v22:
        outcome = "structured_recurrence_improves_v2_2_but_controls_block_promotion"
        recommendation = "Keep as diagnostic; inspect which topology/destructive controls explain the gain."
        promotion_recommended = False
    else:
        outcome = "topology_specific_recurrence_not_supported"
        recommendation = "Park topology-specific recurrence; return to mechanism-selection loop."
        promotion_recommended = False
    return {
        "outcome": outcome,
        "recommendation": recommendation,
        "promotion_recommended": bool(promotion_recommended),
        "requested_lengths": requested_lengths,
        "completed_lengths": completed_lengths,
        "all_requested_lengths_completed": completed_lengths == sorted(requested_lengths),
        "longest_length": longest_length,
        "by_length": by_length,
        "structured_improves_v2_2": bool(structured_improves_v22),
        "generic_improves_v2_2": bool(generic_improves_v22),
        "structured_beats_public_online": bool(structured_beats_public_online),
        "topology_controls_separated": bool(topology_controls_separated),
        "destructive_controls_separated": bool(destructive_controls_separated),
        "structured_matches_or_beats_generic": bool(structured_matches_or_beats_generic),
        "claim": (
            "generic bounded recurrent state remains useful, but topology specificity is not supported"
            if generic_improves_v22 and not topology_controls_separated
            else "topology-specific recurrence evidence"
            if promotion_recommended
            else "no promoted topology-specific recurrence claim"
        ),
        "nonclaims": [
            "not hardware evidence",
            "not native on-chip recurrence",
            "not a baseline freeze",
            "not ESN superiority",
            "not universal benchmark superiority",
            "not lifecycle, sleep/replay, planning, language, AGI, or ASI",
        ],
    }


def write_report(output_dir: Path, payload: dict[str, Any]) -> None:
    c = payload["classification"]
    lines = [
        "# Tier 7.0i Recurrence / Topology Specificity Gate",
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
        "| Length | Structured MSE | Generic 7.0h MSE | v2.2 MSE | ESN MSE | Structured/v2.2 improvement | Structured/generic margin |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for length, values in sorted(c["by_length"].items()):
        lines.append(
            "| "
            f"{length} | "
            f"{values['structured_mse']} | "
            f"{values['generic_7_0h_mse']} | "
            f"{values['v2_2_mse']} | "
            f"{values['esn_mse']} | "
            f"{values['structured_margin_vs_v2_2']} | "
            f"{values['structured_margin_vs_generic']} |"
        )
    lines.extend(["", "## Longest-Length Topology / Control Margins", ""])
    longest = c["by_length"].get(c["longest_length"], {})
    for name, value in sorted((longest.get("control_margins") or {}).items()):
        lines.append(f"- `{name}` margin vs structured candidate: `{value}`")
    lines.extend(
        [
            "",
            "## Promotion Checks",
            "",
            f"- Structured improves versus v2.2: `{c['structured_improves_v2_2']}`",
            f"- Generic 7.0h reference improves versus v2.2: `{c['generic_improves_v2_2']}`",
            f"- Structured beats public online controls: `{c['structured_beats_public_online']}`",
            f"- Topology controls separated: `{c['topology_controls_separated']}`",
            f"- Destructive controls separated: `{c['destructive_controls_separated']}`",
            f"- Structured matches/beats generic reference: `{c['structured_matches_or_beats_generic']}`",
            f"- Promotion recommended: `{c['promotion_recommended']}`",
            "",
            "## Nonclaims",
            "",
        ]
    )
    for item in c["nonclaims"]:
        lines.append(f"- {item}")
    lines.append("")
    (output_dir / "tier7_0i_report.md").write_text("\n".join(lines), encoding="utf-8")


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
    parser.add_argument("--structured-input-scale", type=float, default=0.42)
    parser.add_argument("--structured-coupling", type=float, default=0.18)
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
        criterion("generic 7.0h reference present", GENERIC_70H, "present for every length", all(model_metric(result["model_aggregate_rows"], GENERIC_70H) is not None for result in length_results)),
        criterion("structured candidate present", STRUCTURED, "present for every length", all(model_metric(result["model_aggregate_rows"], STRUCTURED) is not None for result in length_results)),
        criterion("public baselines present", [ESN, LAG, RESERVOIR], "present for every length", all(all(model_metric(result["model_aggregate_rows"], model) is not None for model in [ESN, LAG, RESERVOIR]) for result in length_results)),
        criterion("topology controls present", [SHUFFLED_TOPOLOGY, REVERSED_TOPOLOGY, RANDOM_REWIRE, NO_RECURRENT_TOPOLOGY], "present for every length", all(all(model_metric(result["model_aggregate_rows"], model) is not None for model in [SHUFFLED_TOPOLOGY, REVERSED_TOPOLOGY, RANDOM_REWIRE, NO_RECURRENT_TOPOLOGY]) for result in length_results)),
        criterion("destructive controls present", [STRUCTURED_FROZEN, STRUCTURED_SHUFFLED_STATE, STRUCTURED_SHUFFLED_TARGET, STRUCTURED_NO_UPDATE], "present for every length", all(all(model_metric(result["model_aggregate_rows"], model) is not None for model in [STRUCTURED_FROZEN, STRUCTURED_SHUFFLED_STATE, STRUCTURED_SHUFFLED_TARGET, STRUCTURED_NO_UPDATE]) for result in length_results)),
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
            "Tier 7.0i is software public-benchmark topology-specificity evidence only. It tests whether the Tier 7.0h "
            "bounded recurrent gain can be attributed to a structured recurrent topology rather than generic bounded recurrent features. "
            "It is not hardware evidence, not native on-chip recurrence, not a baseline freeze, and not AGI/ASI evidence."
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
    write_json(output_dir / "tier7_0i_results.json", payload)
    write_json(output_dir / "tier7_0i_fairness_contract.json", payload["fairness_contract"])
    write_report(output_dir, payload)
    summary_rows = [
        {
            "status": payload["status"],
            "criteria_passed": criteria_passed,
            "criteria_total": len(criteria),
            "outcome": classification["outcome"],
            "promotion_recommended": classification["promotion_recommended"],
            "longest_length": classification["longest_length"],
            "structured_improves_v2_2": classification["structured_improves_v2_2"],
            "generic_improves_v2_2": classification["generic_improves_v2_2"],
            "structured_beats_public_online": classification["structured_beats_public_online"],
            "topology_controls_separated": classification["topology_controls_separated"],
            "destructive_controls_separated": classification["destructive_controls_separated"],
            "structured_matches_or_beats_generic": classification["structured_matches_or_beats_generic"],
        }
    ]
    write_csv_rows(output_dir / "tier7_0i_summary.csv", summary_rows)
    all_model_aggregate_rows: list[dict[str, Any]] = []
    for result in length_results:
        all_model_aggregate_rows.extend(result["model_aggregate_rows"])
    write_csv_rows(output_dir / "tier7_0i_model_aggregate.csv", all_model_aggregate_rows)
    manifest = {
        "tier": TIER,
        "status": payload["status"],
        "generated_at_utc": payload["generated_at_utc"],
        "output_dir": str(output_dir),
        "results_json": str(output_dir / "tier7_0i_results.json"),
        "report_md": str(output_dir / "tier7_0i_report.md"),
        "summary_csv": str(output_dir / "tier7_0i_summary.csv"),
        "model_aggregate_csv": str(output_dir / "tier7_0i_model_aggregate.csv"),
    }
    write_json(output_dir / "tier7_0i_latest_manifest.json", manifest)
    write_json(CONTROLLED / "tier7_0i_latest_manifest.json", manifest)
    return payload


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    payload = run(args)
    print(json.dumps(json_safe({"status": payload["status"], "classification": payload["classification"]}), indent=2, sort_keys=True))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
