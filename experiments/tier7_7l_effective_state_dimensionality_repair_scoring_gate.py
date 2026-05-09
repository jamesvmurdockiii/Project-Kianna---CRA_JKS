#!/usr/bin/env python3
"""Tier 7.7l - effective-state-dimensionality repair scoring gate.

This scores the Tier 7.7k contract. The gate tests one predeclared repair:
partitioned causal drivers plus diverse recurrent state. It is still a software
diagnostic, not a baseline freeze or hardware/native transfer.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
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

from tier5_19a_temporal_substrate_reference import FeatureBundle, criterion, json_safe, parse_timescales  # noqa: E402
from tier5_19b_temporal_substrate_gate import temporal_features_variant  # noqa: E402
from tier7_0_standard_dynamical_benchmarks import parse_csv, parse_seeds  # noqa: E402
from tier7_0c_continuous_readout_repair import shuffled_rows, shuffled_target  # noqa: E402
from tier7_7j_capacity_sham_separation_scoring_gate import (  # noqa: E402
    BLOCK,
    DELAY_EMBED,
    ORTHOGONAL,
    PERMUTED,
    TARGET_SHUFFLE,
    TIME_SHUFFLE,
    basis_features,
    build_task,
    geomean,
    geometry_metrics,
    hidden_columns,
    metric,
    readout_metrics,
    run_delay_embedding,
    run_probe_model,
    safe_float,
    summarize_numeric,
    summarize_scoreboard,
    utc_now,
    write_json,
    write_rows,
)


TIER = "Tier 7.7l - Effective-State-Dimensionality Repair Scoring Gate"
RUNNER_REVISION = "tier7_7l_effective_state_dimensionality_repair_scoring_gate_20260509_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_7l_20260509_effective_state_dimensionality_repair_scoring_gate"
CONTRACT_77K = CONTROLLED / "tier7_7k_20260509_effective_state_dimensionality_repair_contract" / "tier7_7k_results.json"
PREREQ_77J = CONTROLLED / "tier7_7j_20260509_capacity_sham_separation_scoring_gate" / "tier7_7j_results.json"

DEFAULT_TASKS = "mackey_glass,lorenz,narma10"
DEFAULT_LENGTHS = "8000,16000,32000"
DEFAULT_SEEDS = "42,43,44"
DEFAULT_CAPACITIES = "16,32,64,128"
DEFAULT_PERMUTED_OFFSETS = "11,23,37,71,101"

REPAIR = "partitioned_driver_diverse_recurrent_state"
DIVERSITY_DISABLED = "diversity_pressure_disabled"
SINGLE_POOL = "single_pool_same_capacity"


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def parse_int_csv(raw: str) -> list[int]:
    values = [int(item) for item in parse_csv(raw)]
    if not values:
        raise ValueError("at least one integer value is required")
    return values


def ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator <= 0.0:
        return None
    if not (math.isfinite(numerator) and math.isfinite(denominator)):
        return None
    return numerator / denominator


def driver_vector(
    *,
    partition: int,
    x: float,
    traces: np.ndarray,
    previous_traces: np.ndarray,
    lags: list[float],
) -> np.ndarray:
    trace_deltas = np.diff(traces) if traces.size > 1 else np.asarray([], dtype=float)
    novelty = x - float(previous_traces[-1] if previous_traces.size else 0.0)
    fast = traces[: min(3, len(traces))]
    slow = traces[max(0, len(traces) - 3) :]
    if partition == 0:
        return np.concatenate([[x, novelty], fast, trace_deltas[: min(3, len(trace_deltas))], lags[:2]])
    if partition == 1:
        return np.concatenate([[x, novelty], slow, trace_deltas[max(0, len(trace_deltas) - 3) :], lags[2:5]])
    if partition == 2:
        cross = float(fast[-1] * slow[-1]) if fast.size and slow.size else 0.0
        return np.asarray([x, x * x, math.tanh(2.0 * x), math.sin(x), math.cos(x), novelty, novelty * novelty, cross], dtype=float)
    lag_arr = np.asarray(lags, dtype=float)
    lag_deltas = x - lag_arr if lag_arr.size else np.asarray([], dtype=float)
    return np.concatenate([[x, novelty], lag_arr, lag_deltas, [float(np.mean(traces)) if traces.size else 0.0]])


def partitioned_driver_diverse_features(
    observed: np.ndarray,
    *,
    seed: int,
    train_end: int,
    timescales: list[float],
    hidden_units: int,
    recurrent_scale: float,
    input_scale: float,
    hidden_decay: float,
    diversity_strength: float,
    partition_count: int,
) -> FeatureBundle:
    values = np.asarray(observed, dtype=float)
    hidden_units = max(1, int(hidden_units))
    partition_count = max(1, min(int(partition_count), hidden_units))
    partitions = [np.asarray(part, dtype=int) for part in np.array_split(np.arange(hidden_units), partition_count)]
    traces = np.zeros(len(timescales), dtype=float)
    hidden = np.zeros(hidden_units, dtype=float)
    rng = np.random.default_rng(seed + 77711)
    lag_steps = [1, 2, 4, 8, 16, 32]

    rec_mats: list[np.ndarray] = []
    in_mats: list[np.ndarray] = []
    decays: list[float] = []
    for part_idx, part in enumerate(partitions):
        sample_driver = driver_vector(partition=part_idx % 4, x=0.0, traces=traces, previous_traces=traces.copy(), lags=[0.0] * len(lag_steps))
        raw = rng.normal(0.0, 1.0, size=(len(part), len(part)))
        q, _r = np.linalg.qr(raw)
        scale = float(recurrent_scale) * (0.72 + 0.12 * (part_idx % 4))
        rec_mats.append(q * scale)
        in_scale = float(input_scale) * (0.85 + 0.10 * ((part_idx + 1) % 4))
        in_mats.append(rng.normal(0.0, in_scale, size=(len(part), len(sample_driver))))
        decays.append(min(0.96, max(0.35, float(hidden_decay) + 0.06 * (part_idx - (partition_count - 1) / 2.0))))

    rows: list[np.ndarray] = []
    for step, value in enumerate(values):
        x = float(value)
        previous = traces.copy()
        for idx, tau in enumerate(timescales):
            alpha = 1.0 - math.exp(-1.0 / max(1e-6, float(tau)))
            traces[idx] = traces[idx] + alpha * (x - traces[idx])
        lags = [float(values[step - lag]) if step - lag >= 0 else 0.0 for lag in lag_steps]
        next_hidden = hidden.copy()
        for part_idx, part in enumerate(partitions):
            driver = driver_vector(partition=part_idx % 4, x=x, traces=traces, previous_traces=previous, lags=lags)
            current = hidden[part]
            next_hidden[part] = np.tanh(decays[part_idx] * current + rec_mats[part_idx] @ current + in_mats[part_idx] @ driver)
            if diversity_strength > 0.0 and len(part) > 1:
                centered = next_hidden[part] - float(np.mean(next_hidden[part]))
                next_hidden[part] = (1.0 - diversity_strength) * next_hidden[part] + diversity_strength * centered
        hidden = np.tanh(next_hidden)
        trace_deltas = np.diff(traces) if traces.size > 1 else np.asarray([], dtype=float)
        novelty = x - float(previous[-1] if previous.size else 0.0)
        rows.append(np.concatenate([[1.0, x], traces, trace_deltas, [novelty], hidden]))
    names = (
        ["bias", "observed_current"]
        + [f"ema_tau_{tau:g}" for tau in timescales]
        + [f"ema_delta_{idx}_{idx+1}" for idx in range(max(0, len(timescales) - 1))]
        + ["novelty_vs_slowest_ema"]
        + [f"hidden_{idx}" for idx in range(hidden_units)]
    )
    features = np.vstack(rows)
    return FeatureBundle(
        features=features,
        temporal_start=len(names) - hidden_units,
        names=names,
        diagnostics={
            "state_location": "partitioned causal-driver recurrent repair",
            "mode": REPAIR if diversity_strength > 0.0 else DIVERSITY_DISABLED,
            "timescales": timescales,
            "hidden_units": int(hidden_units),
            "partition_count": int(partition_count),
            "diversity_strength": float(diversity_strength),
            "driver_groups": "fast,slow,nonlinear,lag",
            "anti_synchronization": "partition-wise deterministic centering",
            "recurrent_scale": float(recurrent_scale),
            "input_scale": float(input_scale),
            "hidden_decay": float(hidden_decay),
            "feature_count": int(features.shape[1]),
            "train_end": int(train_end),
        },
    )


def run_family(
    task: Any,
    *,
    seed: int,
    length: int,
    capacity: int,
    args: argparse.Namespace,
) -> tuple[list[Any], list[dict[str, Any]]]:
    timescales = parse_timescales(args.temporal_timescales)
    base_kwargs = {
        "seed": seed,
        "train_end": task.train_end,
        "timescales": timescales,
        "hidden_units": capacity,
        "recurrent_scale": args.temporal_recurrent_scale,
        "input_scale": args.temporal_input_scale,
        "hidden_decay": args.temporal_hidden_decay,
    }
    results: list[Any] = []
    kernel_rows: list[dict[str, Any]] = []
    repair = partitioned_driver_diverse_features(
        task.observed,
        diversity_strength=args.diversity_strength,
        partition_count=args.partition_count,
        **base_kwargs,
    )
    repair_result = run_probe_model(
        task,
        seed=seed,
        length=length,
        capacity=capacity,
        probe_family=REPAIR,
        probe_id=f"{REPAIR}_{capacity}",
        features=repair.features,
        feature_names=repair.names,
        hidden_columns=hidden_columns(repair.names),
        args=args,
        diagnostics={**repair.diagnostics, "role": "locked 7.7k repair candidate"},
    )
    results.append(repair_result)

    disabled = partitioned_driver_diverse_features(
        task.observed,
        diversity_strength=0.0,
        partition_count=args.partition_count,
        **base_kwargs,
    )
    results.append(
        run_probe_model(
            task,
            seed=seed,
            length=length,
            capacity=capacity,
            probe_family=DIVERSITY_DISABLED,
            probe_id=f"{DIVERSITY_DISABLED}_{capacity}",
            features=disabled.features,
            feature_names=disabled.names,
            hidden_columns=hidden_columns(disabled.names),
            args=args,
            diagnostics={**disabled.diagnostics, "role": "diversity disabled ablation"},
        )
    )

    single = temporal_features_variant(task.observed, mode="full", **base_kwargs)
    results.append(
        run_probe_model(
            task,
            seed=seed,
            length=length,
            capacity=capacity,
            probe_family=SINGLE_POOL,
            probe_id=f"{SINGLE_POOL}_{capacity}",
            features=single.features,
            feature_names=single.names,
            hidden_columns=hidden_columns(single.names),
            args=args,
            diagnostics={**single.diagnostics, "role": "locked same-capacity single-pool reference"},
        )
    )

    for offset in parse_int_csv(args.permuted_offsets):
        permuted = temporal_features_variant(task.observed, mode="permuted_recurrence", recurrent_seed_offset=offset, **base_kwargs)
        results.append(
            run_probe_model(
                task,
                seed=seed,
                length=length,
                capacity=capacity,
                probe_family=PERMUTED,
                probe_id=f"{PERMUTED}_{capacity}_offset_{offset}",
                features=permuted.features,
                feature_names=permuted.names,
                hidden_columns=hidden_columns(permuted.names),
                args=args,
                diagnostics={**permuted.diagnostics, "role": "permuted recurrence ensemble", "offset": int(offset)},
            )
        )

    for mode, family in [("orthogonal", ORTHOGONAL), ("block", BLOCK)]:
        bundle = basis_features(task.observed, mode=mode, **base_kwargs)
        results.append(
            run_probe_model(
                task,
                seed=seed,
                length=length,
                capacity=capacity,
                probe_family=family,
                probe_id=f"{family}_{capacity}",
                features=bundle.features,
                feature_names=bundle.names,
                hidden_columns=hidden_columns(bundle.names),
                args=args,
                diagnostics={**bundle.diagnostics, "role": f"{mode} basis reference"},
            )
        )

    wrong_target = shuffled_target(task.target, task.train_end, seed)
    results.append(
        run_probe_model(
            task,
            seed=seed,
            length=length,
            capacity=capacity,
            probe_family=TARGET_SHUFFLE,
            probe_id=f"{TARGET_SHUFFLE}_{capacity}",
            features=repair.features,
            feature_names=repair.names,
            hidden_columns=hidden_columns(repair.names),
            args=args,
            update_target=wrong_target,
            diagnostics={**repair.diagnostics, "control": "target shuffle repair candidate"},
        )
    )
    shuffled = shuffled_rows(repair.features, task.train_end, seed)
    results.append(
        run_probe_model(
            task,
            seed=seed,
            length=length,
            capacity=capacity,
            probe_family=TIME_SHUFFLE,
            probe_id=f"{TIME_SHUFFLE}_{capacity}",
            features=shuffled,
            feature_names=repair.names,
            hidden_columns=hidden_columns(repair.names),
            args=args,
            diagnostics={**repair.diagnostics, "control": "time/row shuffle repair candidate"},
        )
    )

    repair_hidden = repair_result.features[task.train_end:, repair_result.hidden_columns]
    for result in results:
        if result.row["probe_id"] == repair_result.row["probe_id"] or not result.hidden_columns:
            continue
        other = result.features[task.train_end:, result.hidden_columns]
        from tier7_7j_capacity_sham_separation_scoring_gate import linear_cka

        kernel_rows.append(
            {
                "task": task.name,
                "length": int(length),
                "seed": int(seed),
                "capacity_units": int(capacity),
                "reference_probe_id": repair_result.row["probe_id"],
                "probe_id": result.row["probe_id"],
                "probe_family": result.row["probe_family"],
                "linear_cka_to_candidate": linear_cka(repair_hidden, other),
            }
        )
    return results, kernel_rows


def classify(score_summary: list[dict[str, Any]], geometry_summary: list[dict[str, Any]], readout_summary: list[dict[str, Any]], prereq_77j: dict[str, Any]) -> dict[str, Any]:
    prior_diag = (prereq_77j.get("classification") or {}).get("diagnostics") or {}
    prior_lorenz = safe_float(prior_diag.get("lorenz_candidate_128_geomean_mse"))
    prior_pr = safe_float(prior_diag.get("candidate_pr_128"))
    lorenz_candidate = metric(score_summary, "lorenz", REPAIR, 128)
    lorenz_single = metric(score_summary, "lorenz", SINGLE_POOL, 128)
    lorenz_disabled = metric(score_summary, "lorenz", DIVERSITY_DISABLED, 128)
    lorenz_target = metric(score_summary, "lorenz", TARGET_SHUFFLE, 128)
    lorenz_time = metric(score_summary, "lorenz", TIME_SHUFFLE, 128)
    generic_values = [(family, metric(score_summary, "lorenz", family, 128)) for family in [PERMUTED, ORTHOGONAL, BLOCK]]
    generic_values = [(family, value) for family, value in generic_values if value is not None]
    best_generic = min(generic_values, key=lambda item: item[1]) if generic_values else (None, None)

    def geom_value(task: str, family: str, capacity: int, key: str) -> float | None:
        row = next((item for item in geometry_summary if item["task"] == task and item["probe_family"] == family and int(item["capacity_units"]) == int(capacity)), None)
        return safe_float(row.get(f"{key}_mean")) if row else None

    candidate_pr = geom_value("lorenz", REPAIR, 128, "participation_ratio")
    candidate_rank95 = geom_value("lorenz", REPAIR, 128, "rank95_variance_count")
    top_pc = geom_value("lorenz", REPAIR, 128, "top_pc_fraction")

    def score_ratio(task: str) -> float | None:
        cand = metric(score_summary, task, REPAIR, 128)
        ref = metric(score_summary, task, SINGLE_POOL, 128)
        return ratio(cand, ref)

    mackey_regression_ratio = score_ratio("mackey_glass")
    narma_regression_ratio = score_ratio("narma10")
    lorenz_vs_prior = ratio(prior_lorenz, lorenz_candidate)
    lorenz_vs_single = ratio(lorenz_single, lorenz_candidate)
    diversity_margin = ratio(lorenz_disabled, lorenz_candidate)
    generic_margin = ratio(best_generic[1], lorenz_candidate)
    target_guard = ratio(lorenz_target, lorenz_candidate)
    time_guard = ratio(lorenz_time, lorenz_candidate)
    dimension_rises = candidate_pr is not None and (
        candidate_pr >= 6.0 or (prior_pr is not None and candidate_pr >= 2.0 * prior_pr)
    )
    task_gain = (lorenz_vs_prior is not None and lorenz_vs_prior >= 1.10) or (lorenz_vs_single is not None and lorenz_vs_single >= 1.10)
    sham_sep = (generic_margin is not None and generic_margin >= 1.05) and (diversity_margin is not None and diversity_margin >= 1.05)
    guards_ok = (target_guard is not None and target_guard >= 5.0) and (time_guard is not None and time_guard >= 5.0)
    regressions_ok = (mackey_regression_ratio is not None and mackey_regression_ratio <= 1.10) and (narma_regression_ratio is not None and narma_regression_ratio <= 1.10)

    if not guards_ok or not regressions_ok:
        outcome = "regression_or_leakage_blocked"
        recommendation = "Do not promote; repair failed leakage/regression guardrails."
    elif dimension_rises and task_gain and sham_sep:
        outcome = "effective_dimension_repair_confirmed"
        recommendation = "Repair candidate is diagnostically supported; route to a separate promotion/compact-regression gate before any freeze."
    elif dimension_rises and not task_gain:
        outcome = "dimension_rises_but_no_task_gain"
        recommendation = "State geometry changed, but Lorenz usefulness did not follow; do not promote."
    elif generic_margin is not None and generic_margin <= 1.02:
        outcome = "generic_basis_still_explains"
        recommendation = "Generic/permuted basis still explains the signal; do not promote."
    elif task_gain and not dimension_rises:
        outcome = "task_gain_without_dimension"
        recommendation = "Treat as a performance diagnostic requiring attribution repair before promotion."
    else:
        outcome = "inconclusive"
        recommendation = "No clean decision class; inspect artifacts before further repair."
    return {
        "outcome": outcome,
        "recommendation": recommendation,
        "diagnostics": {
            "prior_lorenz_candidate_128_geomean_mse": prior_lorenz,
            "prior_candidate_pr_128": prior_pr,
            "lorenz_repair_128_geomean_mse": lorenz_candidate,
            "lorenz_single_pool_128_geomean_mse": lorenz_single,
            "lorenz_diversity_disabled_128_geomean_mse": lorenz_disabled,
            "best_generic_family_128": best_generic[0],
            "best_generic_128_geomean_mse": best_generic[1],
            "lorenz_prior_divided_by_repair": lorenz_vs_prior,
            "lorenz_single_pool_divided_by_repair": lorenz_vs_single,
            "diversity_disabled_divided_by_repair": diversity_margin,
            "best_generic_divided_by_repair": generic_margin,
            "target_shuffle_divided_by_repair": target_guard,
            "time_shuffle_divided_by_repair": time_guard,
            "repair_pr_128": candidate_pr,
            "repair_rank95_128": candidate_rank95,
            "repair_top_pc_fraction_128": top_pc,
            "mackey_repair_divided_by_single_pool": mackey_regression_ratio,
            "narma_repair_divided_by_single_pool": narma_regression_ratio,
            "dimension_rises": dimension_rises,
            "task_gain": task_gain,
            "sham_sep": sham_sep,
            "guards_ok": guards_ok,
            "regressions_ok": regressions_ok,
        },
        "claim_allowed": {
            "diagnostic_repair_support": outcome == "effective_dimension_repair_confirmed",
            "mechanism_promotion": False,
            "baseline_freeze": False,
            "hardware_or_native_transfer": False,
            "public_usefulness": False,
        },
        "nonclaims": [
            "not a baseline freeze",
            "not a mechanism promotion",
            "not hardware/native transfer",
            "not external-baseline superiority",
            "not broad public usefulness",
            "not language, AGI, or ASI evidence",
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=TIER)
    parser.add_argument("--tasks", default=DEFAULT_TASKS)
    parser.add_argument("--lengths", default=DEFAULT_LENGTHS)
    parser.add_argument("--seeds", default=DEFAULT_SEEDS)
    parser.add_argument("--capacities", default=DEFAULT_CAPACITIES)
    parser.add_argument("--permuted-offsets", default=DEFAULT_PERMUTED_OFFSETS)
    parser.add_argument("--horizon", type=int, default=8)
    parser.add_argument("--readout-lr", type=float, default=0.08)
    parser.add_argument("--readout-decay", type=float, default=1e-5)
    parser.add_argument("--weight-clip", type=float, default=20.0)
    parser.add_argument("--output-clip", type=float, default=3.0)
    parser.add_argument("--temporal-timescales", default="2,4,8,16,32,64,128")
    parser.add_argument("--temporal-recurrent-scale", type=float, default=0.65)
    parser.add_argument("--temporal-input-scale", type=float, default=0.45)
    parser.add_argument("--temporal-hidden-decay", type=float, default=0.72)
    parser.add_argument("--partition-count", type=int, default=4)
    parser.add_argument("--diversity-strength", type=float, default=0.35)
    parser.add_argument("--delay-embedding-history", type=int, default=64)
    parser.add_argument("--state-reset-interval", type=int, default=64)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--smoke", action="store_true")
    return parser


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if args.smoke:
        args.tasks = "lorenz"
        args.lengths = "720"
        args.seeds = "42"
        args.capacities = "16,32"
        args.permuted_offsets = "71"
    tasks = parse_csv(args.tasks)
    lengths = parse_int_csv(args.lengths)
    seeds = parse_seeds(argparse.Namespace(seeds=args.seeds, seed_count=None, base_seed=42))
    capacities = parse_int_csv(args.capacities)
    started = time.perf_counter()
    contract_77k = read_json(CONTRACT_77K)
    prereq_77j = read_json(PREREQ_77J)
    scoreboard_rows: list[dict[str, Any]] = []
    geometry_rows: list[dict[str, Any]] = []
    readout_rows: list[dict[str, Any]] = []
    kernel_rows: list[dict[str, Any]] = []
    task_descriptors: list[dict[str, Any]] = []
    invalid_tasks: list[dict[str, Any]] = []
    for length in lengths:
        for seed in seeds:
            for task_name in tasks:
                task = build_task(task_name, length, seed, args.horizon)
                finite = bool(np.all(np.isfinite(task.observed)) and np.all(np.isfinite(task.target)))
                task_descriptors.append(
                    {
                        "task": task.name,
                        "length": int(length),
                        "seed": int(seed),
                        "horizon": int(task.horizon),
                        "train_end": int(task.train_end),
                        "sample_count": int(len(task.target)),
                        "finite": finite,
                        "metadata": task.metadata,
                    }
                )
                if not finite:
                    invalid_tasks.append(task_descriptors[-1])
                    continue
                delay = run_delay_embedding(task, seed=seed, length=length, args=args)
                scoreboard_rows.append(delay.row)
                geometry_rows.append(
                    {
                        "task": task.name,
                        "length": int(length),
                        "seed": int(seed),
                        "capacity_units": 0,
                        "probe_family": DELAY_EMBED,
                        "probe_id": DELAY_EMBED,
                        **geometry_metrics(delay.features, delay.hidden_columns, task.train_end),
                    }
                )
                readout_rows.append(
                    {
                        "task": task.name,
                        "length": int(length),
                        "seed": int(seed),
                        "capacity_units": 0,
                        "probe_family": DELAY_EMBED,
                        "probe_id": DELAY_EMBED,
                        **readout_metrics(delay.weights, delay.hidden_columns),
                    }
                )
                for capacity in capacities:
                    results, kernels = run_family(task, seed=seed, length=length, capacity=capacity, args=args)
                    kernel_rows.extend(kernels)
                    for result in results:
                        scoreboard_rows.append(result.row)
                        geometry_rows.append(
                            {
                                "task": task.name,
                                "length": int(length),
                                "seed": int(seed),
                                "capacity_units": int(capacity),
                                "probe_family": result.row["probe_family"],
                                "probe_id": result.row["probe_id"],
                                **geometry_metrics(result.features, result.hidden_columns, task.train_end),
                            }
                        )
                        readout_rows.append(
                            {
                                "task": task.name,
                                "length": int(length),
                                "seed": int(seed),
                                "capacity_units": int(capacity),
                                "probe_family": result.row["probe_family"],
                                "probe_id": result.row["probe_id"],
                                **readout_metrics(result.weights, result.hidden_columns),
                            }
                        )
    score_summary = summarize_scoreboard(scoreboard_rows)
    geometry_summary = summarize_numeric(
        geometry_rows,
        ["participation_ratio", "participation_ratio_per_unit", "rank95_variance_count", "top_pc_fraction", "state_norm_mean", "state_norm_std", "step_delta_mean", "step_delta_std", "total_state_variance"],
        ["task", "probe_family", "capacity_units"],
    )
    readout_summary = summarize_numeric(
        readout_rows,
        ["readout_weight_pr", "top_weight_fraction", "hidden_weight_energy_fraction", "final_weight_norm"],
        ["task", "probe_family", "capacity_units"],
    )
    kernel_summary = summarize_numeric(kernel_rows, ["linear_cka_to_candidate"], ["task", "probe_family", "capacity_units"])
    classification = classify(score_summary, geometry_summary, readout_summary, prereq_77j)
    regression_summary = {
        "compact_regression_inside_gate": False,
        "required_before_promotion": True,
        "reason": "Tier 7.7l is a scoring/diagnostic gate. If diagnostically supported, route to a separate promotion plus compact-regression gate before freeze.",
    }
    criteria = [
        criterion("Tier 7.7k contract exists", str(CONTRACT_77K), "exists and pass", bool(contract_77k) and contract_77k.get("status") == "pass"),
        criterion("Tier 7.7j prerequisite exists", str(PREREQ_77J), "exists and pass", bool(prereq_77j) and prereq_77j.get("status") == "pass"),
        criterion("locked tasks", tasks, "Mackey/Lorenz/NARMA", set(tasks) == {"mackey_glass", "lorenz", "narma10"} or bool(args.smoke)),
        criterion("locked lengths", lengths, "8000/16000/32000", lengths == [8000, 16000, 32000] or bool(args.smoke)),
        criterion("locked seeds", seeds, "42/43/44", seeds == [42, 43, 44] or bool(args.smoke)),
        criterion("locked capacities", capacities, "16/32/64/128", capacities == [16, 32, 64, 128] or bool(args.smoke)),
        criterion("finite generated streams", len(invalid_tasks), "== 0", len(invalid_tasks) == 0),
        criterion("scoreboard produced", len(scoreboard_rows), "> 0", len(scoreboard_rows) > 0),
        criterion("state geometry produced", len(geometry_rows), "> 0", len(geometry_rows) > 0),
        criterion("readout concentration produced", len(readout_rows), "> 0", len(readout_rows) > 0),
        criterion("kernel alignment produced", len(kernel_rows), "> 0", len(kernel_rows) > 0),
        criterion("classification produced", classification["outcome"], "non-empty", bool(classification["outcome"])),
        criterion("no baseline freeze", classification["claim_allowed"]["baseline_freeze"], "false", classification["claim_allowed"]["baseline_freeze"] is False),
        criterion("no mechanism promotion", classification["claim_allowed"]["mechanism_promotion"], "false", classification["claim_allowed"]["mechanism_promotion"] is False),
        criterion("hardware/native transfer blocked", classification["claim_allowed"]["hardware_or_native_transfer"], "false", classification["claim_allowed"]["hardware_or_native_transfer"] is False),
    ]
    passed = sum(1 for item in criteria if item["passed"])
    status = "pass" if passed == len(criteria) else "fail"
    claim_boundary = (
        "Tier 7.7l scores the locked 7.7k effective-state-dimensionality repair. It may support or block the repair diagnostically, but it does not freeze a baseline, promote a mechanism, authorize hardware/native transfer, or claim broad public usefulness."
    )
    payload = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "status": status,
        "criteria": criteria,
        "criteria_passed": passed,
        "criteria_total": len(criteria),
        "output_dir": str(output_dir),
        "tasks": tasks,
        "lengths": lengths,
        "seeds": seeds,
        "capacities": capacities,
        "classification": classification,
        "scoreboard_rows": scoreboard_rows,
        "score_summary": score_summary,
        "state_geometry": geometry_rows,
        "state_geometry_summary": geometry_summary,
        "state_kernel_alignment": kernel_rows,
        "state_kernel_alignment_summary": kernel_summary,
        "readout_concentration": readout_rows,
        "readout_concentration_summary": readout_summary,
        "task_descriptors": task_descriptors,
        "invalid_tasks": invalid_tasks,
        "regression_summary": regression_summary,
        "claim_boundary": claim_boundary,
        "runtime_seconds": time.perf_counter() - started,
    }
    write_json(output_dir / "tier7_7l_results.json", payload)
    write_rows(output_dir / "tier7_7l_summary.csv", criteria)
    write_rows(output_dir / "tier7_7l_scoreboard.csv", scoreboard_rows)
    write_rows(output_dir / "tier7_7l_score_summary.csv", score_summary)
    write_rows(output_dir / "tier7_7l_state_geometry.csv", geometry_rows)
    write_rows(output_dir / "tier7_7l_state_geometry_summary.csv", geometry_summary)
    write_rows(output_dir / "tier7_7l_state_kernel_alignment.csv", kernel_rows)
    write_rows(output_dir / "tier7_7l_state_kernel_alignment_summary.csv", kernel_summary)
    write_rows(output_dir / "tier7_7l_readout_concentration.csv", readout_rows)
    write_rows(output_dir / "tier7_7l_readout_concentration_summary.csv", readout_summary)
    write_rows(output_dir / "tier7_7l_sham_controls.csv", [row for row in scoreboard_rows if row.get("probe_family") in {DIVERSITY_DISABLED, PERMUTED, ORTHOGONAL, BLOCK, TARGET_SHUFFLE, TIME_SHUFFLE}])
    write_json(output_dir / "tier7_7l_regression_summary.json", regression_summary)
    write_json(output_dir / "tier7_7l_task_descriptors.json", task_descriptors)
    write_json(output_dir / "tier7_7l_probe_manifest.json", {"tasks": tasks, "lengths": lengths, "seeds": seeds, "capacities": capacities, "candidate": REPAIR, "permuted_offsets": parse_int_csv(args.permuted_offsets)})
    (output_dir / "tier7_7l_claim_boundary.md").write_text(claim_boundary + "\n", encoding="utf-8")
    report = [
        "# Tier 7.7l Effective-State-Dimensionality Repair Scoring Gate",
        "",
        f"- Generated: `{payload['generated_at_utc']}`",
        f"- Status: **{status.upper()}**",
        f"- Criteria: `{passed}/{len(criteria)}`",
        f"- Outcome: `{classification['outcome']}`",
        f"- Recommendation: {classification['recommendation']}",
        "",
        "## Boundary",
        "",
        claim_boundary,
        "",
        "## Diagnostics",
        "",
    ]
    for key, value in classification["diagnostics"].items():
        report.append(f"- {key}: `{value}`")
    report.extend(["", "## Nonclaims", ""])
    report.extend(f"- {item}" for item in classification["nonclaims"])
    report.append("")
    (output_dir / "tier7_7l_report.md").write_text("\n".join(report), encoding="utf-8")
    manifest = {
        "tier": TIER,
        "status": status,
        "generated_at_utc": payload["generated_at_utc"],
        "output_dir": str(output_dir),
        "results_json": str(output_dir / "tier7_7l_results.json"),
        "report_md": str(output_dir / "tier7_7l_report.md"),
        "summary_csv": str(output_dir / "tier7_7l_summary.csv"),
        "classification_outcome": classification["outcome"],
    }
    write_json(output_dir / "tier7_7l_latest_manifest.json", manifest)
    write_json(CONTROLLED / "tier7_7l_latest_manifest.json", manifest)
    return payload


def main() -> int:
    args = build_parser().parse_args()
    payload = run(args)
    print(json.dumps(json_safe({"status": payload["status"], "criteria": f"{payload['criteria_passed']}/{payload['criteria_total']}", "classification": payload["classification"]["outcome"], "output_dir": payload["output_dir"]}), indent=2, sort_keys=True))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
