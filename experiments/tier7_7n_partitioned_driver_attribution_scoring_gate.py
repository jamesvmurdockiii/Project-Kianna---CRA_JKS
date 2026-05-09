#!/usr/bin/env python3
"""Tier 7.7n - partitioned-driver attribution scoring gate.

This scores the Tier 7.7m contract. Tier 7.7l produced a useful standardized
benchmark gain, but did not prove the claimed state-dimensionality repair or
attribute the gain to diversity pressure. This gate asks what caused the gain
before any promotion, freeze, or hardware/native transfer.
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
    PERMUTED,
    TARGET_SHUFFLE,
    TIME_SHUFFLE,
    build_task,
    geometry_metrics,
    hidden_columns,
    linear_cka,
    metric,
    readout_metrics,
    run_probe_model,
    safe_float,
    summarize_numeric,
    summarize_scoreboard,
    utc_now,
    write_json,
    write_rows,
)
from tier7_7l_effective_state_dimensionality_repair_scoring_gate import (  # noqa: E402
    DIVERSITY_DISABLED,
    REPAIR,
    SINGLE_POOL,
    driver_vector,
    partitioned_driver_diverse_features,
    ratio,
)


TIER = "Tier 7.7n - Partitioned-Driver Attribution Scoring Gate"
RUNNER_REVISION = "tier7_7n_partitioned_driver_attribution_scoring_gate_20260509_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_7n_20260509_partitioned_driver_attribution_scoring_gate"
CONTRACT_77M = CONTROLLED / "tier7_7m_20260509_partitioned_driver_attribution_contract" / "tier7_7m_results.json"
PREREQ_77L = CONTROLLED / "tier7_7l_20260509_effective_state_dimensionality_repair_scoring_gate" / "tier7_7l_results.json"

DEFAULT_TASKS = "mackey_glass,lorenz,narma10"
DEFAULT_LENGTHS = "8000,16000,32000"
DEFAULT_SEEDS = "42,43,44"
DEFAULT_CAPACITIES = "16,32,64,128"
DEFAULT_PERMUTED_OFFSETS = "71,101,131"

FULL = "partitioned_driver_full"
PARTITION_SHUFFLED = "partition_labels_shuffled"
MERGED = "partition_merged_unpartitioned"
NONLINEAR_LAG = "nonlinear_lag_unpartitioned_same_budget"
LINEAR_LAG = "linear_lag_partitioned"
DIVERSITY_REPEAT = "diversity_pressure_disabled_repeat"
RANDOM_PROJECTION = "same_feature_count_random_projection"
SINGLE_POOL_MATCHED = "readout_budget_matched_single_pool"
DRIVER_ABLATIONS = {
    "remove_fast_trace_drivers",
    "remove_slow_trace_drivers",
    "remove_lag_drivers",
    "remove_nonlinear_drivers",
}


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def parse_int_csv(raw: str) -> list[int]:
    values = [int(item) for item in parse_csv(raw)]
    if not values:
        raise ValueError("at least one integer value is required")
    return values


def causal_driver_basis(values: np.ndarray, timescales: list[float]) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    traces = np.zeros(len(timescales), dtype=float)
    lag_steps = [1, 2, 4, 8, 16, 32]
    rows: list[np.ndarray] = []
    for step, value in enumerate(values):
        x = float(value)
        previous = traces.copy()
        for idx, tau in enumerate(timescales):
            alpha = 1.0 - math.exp(-1.0 / max(1e-6, float(tau)))
            traces[idx] = traces[idx] + alpha * (x - traces[idx])
        lags = [float(values[step - lag]) if step - lag >= 0 else 0.0 for lag in lag_steps]
        parts = [driver_vector(partition=idx, x=x, traces=traces, previous_traces=previous, lags=lags) for idx in range(4)]
        rows.append(np.concatenate(parts))
    return np.vstack(rows)


def make_bundle(features: np.ndarray, names: list[str], temporal_start: int, diagnostics: dict[str, Any]) -> FeatureBundle:
    return FeatureBundle(features=features, temporal_start=temporal_start, names=names, diagnostics=diagnostics)


def rename_family(bundle: FeatureBundle, family: str, extra: dict[str, Any] | None = None) -> FeatureBundle:
    diagnostics = dict(bundle.diagnostics)
    diagnostics.update(extra or {})
    diagnostics["mode"] = family
    return make_bundle(bundle.features, bundle.names, bundle.temporal_start, diagnostics)


def partition_variant_features(
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
    family: str,
) -> FeatureBundle:
    if family == FULL:
        base = partitioned_driver_diverse_features(
            observed,
            seed=seed,
            train_end=train_end,
            timescales=timescales,
            hidden_units=hidden_units,
            recurrent_scale=recurrent_scale,
            input_scale=input_scale,
            hidden_decay=hidden_decay,
            diversity_strength=diversity_strength,
            partition_count=partition_count,
        )
        return rename_family(base, family, {"role": "full partitioned-driver attribution candidate"})
    if family == DIVERSITY_REPEAT:
        base = partitioned_driver_diverse_features(
            observed,
            seed=seed,
            train_end=train_end,
            timescales=timescales,
            hidden_units=hidden_units,
            recurrent_scale=recurrent_scale,
            input_scale=input_scale,
            hidden_decay=hidden_decay,
            diversity_strength=0.0,
            partition_count=partition_count,
        )
        return rename_family(base, family, {"role": "diversity-disabled attribution repeat"})
    if family == MERGED:
        base = partitioned_driver_diverse_features(
            observed,
            seed=seed,
            train_end=train_end,
            timescales=timescales,
            hidden_units=hidden_units,
            recurrent_scale=recurrent_scale,
            input_scale=input_scale,
            hidden_decay=hidden_decay,
            diversity_strength=0.0,
            partition_count=1,
        )
        return rename_family(base, family, {"role": "merged/unpartitioned control"})

    values = np.asarray(observed, dtype=float)
    hidden_units = max(1, int(hidden_units))
    partition_count = max(1, min(int(partition_count), hidden_units))
    partitions = [np.asarray(part, dtype=int) for part in np.array_split(np.arange(hidden_units), partition_count)]
    traces = np.zeros(len(timescales), dtype=float)
    hidden = np.zeros(hidden_units, dtype=float)
    rng = np.random.default_rng(seed + 91337 + hidden_units)
    lag_steps = [1, 2, 4, 8, 16, 32]
    driver_label_map = list(range(partition_count))
    if family == PARTITION_SHUFFLED:
        rng.shuffle(driver_label_map)
    rec_mats: list[np.ndarray] = []
    in_mats: list[np.ndarray] = []
    decays: list[float] = []
    sample_driver = driver_vector(partition=0, x=0.0, traces=traces, previous_traces=traces.copy(), lags=[0.0] * len(lag_steps))
    for part_idx, part in enumerate(partitions):
        raw = rng.normal(0.0, 1.0, size=(len(part), len(part)))
        q, _r = np.linalg.qr(raw)
        rec_mats.append(q * float(recurrent_scale) * (0.72 + 0.12 * (part_idx % 4)))
        in_mats.append(rng.normal(0.0, float(input_scale), size=(len(part), len(sample_driver))))
        decays.append(min(0.96, max(0.35, float(hidden_decay) + 0.05 * (part_idx - (partition_count - 1) / 2.0))))
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
            label = driver_label_map[part_idx] % 4
            driver = driver_vector(partition=label, x=x, traces=traces, previous_traces=previous, lags=lags)
            if family == LINEAR_LAG and label == 2:
                driver = np.asarray([x, traces[0] if traces.size else 0.0, traces[-1] if traces.size else 0.0, lags[0], lags[1], lags[2], x - lags[0], x - lags[1]], dtype=float)
            current = hidden[part]
            local_in = in_mats[part_idx]
            if local_in.shape[1] != driver.shape[0]:
                local_in = rng.normal(0.0, float(input_scale), size=(len(part), driver.shape[0]))
                in_mats[part_idx] = local_in
            next_hidden[part] = np.tanh(decays[part_idx] * current + rec_mats[part_idx] @ current + local_in @ driver)
            if diversity_strength > 0.0 and family not in {PARTITION_SHUFFLED, LINEAR_LAG} and len(part) > 1:
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
    return make_bundle(
        np.vstack(rows),
        names,
        len(names) - hidden_units,
        {
            "state_location": "partitioned-driver attribution variant",
            "mode": family,
            "hidden_units": int(hidden_units),
            "partition_count": int(partition_count),
            "diversity_strength": float(diversity_strength),
            "feature_count": int(len(names)),
            "train_end": int(train_end),
        },
    )


def nonlinear_lag_unpartitioned_features(observed: np.ndarray, *, seed: int, train_end: int, timescales: list[float], hidden_units: int, recurrent_scale: float, input_scale: float, hidden_decay: float) -> FeatureBundle:
    drivers = causal_driver_basis(np.asarray(observed, dtype=float), timescales)
    rng = np.random.default_rng(seed + 52201 + hidden_units)
    w_in = rng.normal(0.0, input_scale, size=(hidden_units, drivers.shape[1]))
    raw = rng.normal(0.0, 1.0, size=(hidden_units, hidden_units))
    q, _r = np.linalg.qr(raw)
    rec = q * recurrent_scale
    hidden = np.zeros(hidden_units, dtype=float)
    rows: list[np.ndarray] = []
    for driver in drivers:
        hidden = np.tanh(hidden_decay * hidden + rec @ hidden + w_in @ driver)
        rows.append(np.concatenate([[1.0], driver, hidden]))
    names = ["bias"] + [f"driver_{idx}" for idx in range(drivers.shape[1])] + [f"hidden_{idx}" for idx in range(hidden_units)]
    return make_bundle(np.vstack(rows), names, len(names) - hidden_units, {"mode": NONLINEAR_LAG, "feature_count": len(names), "train_end": int(train_end)})


def random_projection_features(observed: np.ndarray, *, seed: int, train_end: int, timescales: list[float], hidden_units: int, input_scale: float) -> FeatureBundle:
    drivers = causal_driver_basis(np.asarray(observed, dtype=float), timescales)
    rng = np.random.default_rng(seed + 88223 + hidden_units)
    proj = rng.normal(0.0, input_scale, size=(drivers.shape[1], hidden_units))
    hidden = np.tanh(drivers @ proj)
    features = np.concatenate([np.ones((len(drivers), 1)), drivers, hidden], axis=1)
    names = ["bias"] + [f"driver_{idx}" for idx in range(drivers.shape[1])] + [f"hidden_{idx}" for idx in range(hidden_units)]
    return make_bundle(features, names, len(names) - hidden_units, {"mode": RANDOM_PROJECTION, "feature_count": len(names), "train_end": int(train_end)})


def driver_group_ablation_features(full: FeatureBundle, family: str) -> FeatureBundle:
    features = np.array(full.features, copy=True)
    names = list(full.names)
    groups = {
        "remove_fast_trace_drivers": [idx for idx, name in enumerate(names) if name.startswith("ema_tau_2") or name.startswith("ema_tau_4") or name.startswith("ema_delta_0")],
        "remove_slow_trace_drivers": [idx for idx, name in enumerate(names) if name.startswith("ema_tau_64") or name.startswith("ema_tau_128") or name.startswith("ema_delta_5")],
        "remove_lag_drivers": [idx for idx, name in enumerate(names) if "lag" in name.lower()],
        "remove_nonlinear_drivers": [idx for idx, name in enumerate(names) if "hidden_" in name and int(name.split("_")[-1]) % 4 == 2],
    }
    for idx in groups.get(family, []):
        if idx < features.shape[1]:
            features[:, idx] = 0.0
    diagnostics = dict(full.diagnostics)
    diagnostics.update({"mode": family, "ablated_columns": len(groups.get(family, []))})
    return make_bundle(features, names, full.temporal_start, diagnostics)


def run_family(task: Any, *, seed: int, length: int, capacity: int, args: argparse.Namespace) -> tuple[list[Any], list[dict[str, Any]]]:
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
    bundles: list[tuple[str, FeatureBundle, str]] = []
    full = partition_variant_features(
        task.observed,
        diversity_strength=args.diversity_strength,
        partition_count=args.partition_count,
        family=FULL,
        **base_kwargs,
    )
    bundles.append((FULL, full, "full partitioned-driver candidate"))
    for family, role in [
        (PARTITION_SHUFFLED, "partition-label shuffle control"),
        (MERGED, "merged/unpartitioned control"),
        (LINEAR_LAG, "linear-lag partitioned control"),
        (DIVERSITY_REPEAT, "diversity-disabled repeat"),
    ]:
        bundles.append((family, partition_variant_features(task.observed, diversity_strength=args.diversity_strength, partition_count=args.partition_count, family=family, **base_kwargs), role))
    bundles.append((NONLINEAR_LAG, nonlinear_lag_unpartitioned_features(task.observed, **base_kwargs), "nonlinear/lag same-budget unpartitioned control"))
    bundles.append((RANDOM_PROJECTION, random_projection_features(task.observed, seed=seed, train_end=task.train_end, timescales=timescales, hidden_units=capacity, input_scale=args.temporal_input_scale), "same-feature random projection control"))
    single = temporal_features_variant(task.observed, mode="full", **base_kwargs)
    bundles.append((SINGLE_POOL_MATCHED, make_bundle(single.features, single.names, single.temporal_start, {**single.diagnostics, "mode": SINGLE_POOL_MATCHED}), "locked readout-budget-matched single-pool reference"))
    for family in sorted(DRIVER_ABLATIONS):
        bundles.append((family, driver_group_ablation_features(full, family), "driver-group ablation"))
    for offset in parse_int_csv(args.permuted_offsets):
        permuted = temporal_features_variant(task.observed, mode="permuted_recurrence", recurrent_seed_offset=offset, **base_kwargs)
        bundles.append((PERMUTED, make_bundle(permuted.features, permuted.names, permuted.temporal_start, {**permuted.diagnostics, "mode": PERMUTED, "offset": int(offset)}), f"permuted recurrence offset {offset}"))

    results: list[Any] = []
    for family, bundle, role in bundles:
        results.append(
            run_probe_model(
                task,
                seed=seed,
                length=length,
                capacity=capacity,
                probe_family=family,
                probe_id=f"{family}_{capacity}" if family != PERMUTED else f"{PERMUTED}_{capacity}_offset_{bundle.diagnostics.get('offset')}",
                features=bundle.features,
                feature_names=bundle.names,
                hidden_columns=hidden_columns(bundle.names),
                args=args,
                diagnostics={**bundle.diagnostics, "role": role},
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
            features=full.features,
            feature_names=full.names,
            hidden_columns=hidden_columns(full.names),
            args=args,
            update_target=wrong_target,
            diagnostics={**full.diagnostics, "control": "target shuffle full candidate"},
        )
    )
    shuffled = shuffled_rows(full.features, task.train_end, seed)
    results.append(
        run_probe_model(
            task,
            seed=seed,
            length=length,
            capacity=capacity,
            probe_family=TIME_SHUFFLE,
            probe_id=f"{TIME_SHUFFLE}_{capacity}",
            features=shuffled,
            feature_names=full.names,
            hidden_columns=hidden_columns(full.names),
            args=args,
            diagnostics={**full.diagnostics, "control": "time/row shuffle full candidate"},
        )
    )
    candidate = next(result for result in results if result.row["probe_family"] == FULL)
    candidate_hidden = candidate.features[task.train_end:, candidate.hidden_columns]
    kernel_rows: list[dict[str, Any]] = []
    for result in results:
        if result.row["probe_id"] == candidate.row["probe_id"] or not result.hidden_columns:
            continue
        kernel_rows.append(
            {
                "task": task.name,
                "length": int(length),
                "seed": int(seed),
                "capacity_units": int(capacity),
                "reference_probe_id": candidate.row["probe_id"],
                "probe_id": result.row["probe_id"],
                "probe_family": result.row["probe_family"],
                "linear_cka_to_candidate": linear_cka(candidate_hidden, result.features[task.train_end:, result.hidden_columns]),
            }
        )
    return results, kernel_rows


def classify(score_summary: list[dict[str, Any]], geometry_summary: list[dict[str, Any]], prereq_77l: dict[str, Any]) -> dict[str, Any]:
    def score(task: str, family: str, capacity: int = 128) -> float | None:
        return metric(score_summary, task, family, capacity)

    full_lorenz = score("lorenz", FULL)
    single_lorenz = score("lorenz", SINGLE_POOL_MATCHED)
    shuffled_lorenz = score("lorenz", PARTITION_SHUFFLED)
    merged_lorenz = score("lorenz", MERGED)
    nonlinear_lag_lorenz = score("lorenz", NONLINEAR_LAG)
    linear_lag_lorenz = score("lorenz", LINEAR_LAG)
    diversity_lorenz = score("lorenz", DIVERSITY_REPEAT)
    random_lorenz = score("lorenz", RANDOM_PROJECTION)
    target_lorenz = score("lorenz", TARGET_SHUFFLE)
    time_lorenz = score("lorenz", TIME_SHUFFLE)
    permuted_lorenz = score("lorenz", PERMUTED)
    ablation_scores = {family: score("lorenz", family) for family in sorted(DRIVER_ABLATIONS)}
    prior_diag = (prereq_77l.get("classification") or {}).get("diagnostics") or {}
    prior_repair = safe_float(prior_diag.get("lorenz_repair_128_geomean_mse"))

    def better(control: float | None) -> float | None:
        return ratio(control, full_lorenz)

    partition_margin = min([item for item in [better(shuffled_lorenz), better(merged_lorenz)] if item is not None], default=None)
    feature_margin = better(nonlinear_lag_lorenz)
    linear_margin = better(linear_lag_lorenz)
    diversity_margin = better(diversity_lorenz)
    random_margin = better(random_lorenz)
    single_margin = better(single_lorenz)
    permuted_margin = better(permuted_lorenz)
    target_guard = better(target_lorenz)
    time_guard = better(time_lorenz)
    ablation_margins = {family: better(value) for family, value in ablation_scores.items()}
    coherent_ablation_loss = any(value is not None and value >= 1.05 for value in ablation_margins.values())
    guards_ok = (target_guard is not None and target_guard >= 5.0) and (time_guard is not None and time_guard >= 5.0)
    regressions_ok = all(
        ratio(score(task, FULL), score(task, SINGLE_POOL_MATCHED)) is not None and ratio(score(task, FULL), score(task, SINGLE_POOL_MATCHED)) <= 1.10
        for task in ["mackey_glass", "narma10"]
    )
    full_useful = single_margin is not None and single_margin >= 1.10
    partition_sep = partition_margin is not None and partition_margin >= 1.05
    generic_sep = all(value is not None and value >= 1.05 for value in [random_margin, permuted_margin])
    feature_explains = feature_margin is not None and feature_margin <= 1.02 and any(value is not None and value >= 1.05 for value in [linear_margin, *ablation_margins.values()])
    budget_explains = random_margin is not None and random_margin <= 1.02
    diversity_explains = diversity_margin is not None and diversity_margin >= 1.05

    if not guards_ok or not regressions_ok:
        outcome = "regression_or_leakage_blocked"
        recommendation = "Do not promote; attribution gate failed leakage or regression guards."
    elif not full_useful:
        outcome = "negative_result"
        recommendation = "The 7.7l gain did not reproduce under the attribution matrix; park the repair."
    elif budget_explains or (permuted_margin is not None and permuted_margin <= 1.02):
        outcome = "generic_projection_explains_gain"
        recommendation = "Useful gain remains generic-basis/interface explainable; do not promote."
    elif feature_explains:
        outcome = "nonlinear_lag_features_explain_gain"
        recommendation = "Refactor claim toward causal lag/nonlinear feature enrichment before promotion."
    elif partition_sep and generic_sep and coherent_ablation_loss:
        outcome = "driver_partition_attribution_confirmed"
        recommendation = "Attribution is supported; route to compact promotion/regression gate before any freeze."
    elif diversity_explains and generic_sep:
        outcome = "diversity_pressure_attribution_confirmed"
        recommendation = "Diversity pressure may be causal; route to compact promotion/regression gate before freeze."
    else:
        outcome = "task_gain_but_attribution_inconclusive"
        recommendation = "Keep as diagnostic candidate; no promotion, freeze, or hardware/native transfer."
    return {
        "outcome": outcome,
        "recommendation": recommendation,
        "diagnostics": {
            "prior_7_7l_lorenz_repair_128_geomean_mse": prior_repair,
            "full_lorenz_128_geomean_mse": full_lorenz,
            "single_pool_lorenz_128_geomean_mse": single_lorenz,
            "partition_shuffled_lorenz_128_geomean_mse": shuffled_lorenz,
            "merged_lorenz_128_geomean_mse": merged_lorenz,
            "nonlinear_lag_lorenz_128_geomean_mse": nonlinear_lag_lorenz,
            "linear_lag_lorenz_128_geomean_mse": linear_lag_lorenz,
            "diversity_disabled_lorenz_128_geomean_mse": diversity_lorenz,
            "random_projection_lorenz_128_geomean_mse": random_lorenz,
            "permuted_lorenz_128_geomean_mse": permuted_lorenz,
            "single_pool_divided_by_full": single_margin,
            "partition_control_min_divided_by_full": partition_margin,
            "nonlinear_lag_divided_by_full": feature_margin,
            "linear_lag_divided_by_full": linear_margin,
            "diversity_disabled_divided_by_full": diversity_margin,
            "random_projection_divided_by_full": random_margin,
            "permuted_divided_by_full": permuted_margin,
            "target_shuffle_divided_by_full": target_guard,
            "time_shuffle_divided_by_full": time_guard,
            "driver_group_ablation_margins": ablation_margins,
            "full_useful": full_useful,
            "partition_sep": partition_sep,
            "generic_sep": generic_sep,
            "coherent_ablation_loss": coherent_ablation_loss,
            "guards_ok": guards_ok,
            "regressions_ok": regressions_ok,
        },
        "claim_allowed": {
            "attribution_support": outcome in {"driver_partition_attribution_confirmed", "diversity_pressure_attribution_confirmed"},
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
    parser.add_argument("--state-reset-interval", type=int, default=64)
    parser.add_argument("--delay-embedding-history", type=int, default=64)
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
    contract_77m = read_json(CONTRACT_77M)
    prereq_77l = read_json(PREREQ_77L)
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
                task_descriptors.append({"task": task.name, "length": int(length), "seed": int(seed), "horizon": int(task.horizon), "train_end": int(task.train_end), "sample_count": int(len(task.target)), "finite": finite, "metadata": task.metadata})
                if not finite:
                    invalid_tasks.append(task_descriptors[-1])
                    continue
                for capacity in capacities:
                    results, kernels = run_family(task, seed=seed, length=length, capacity=capacity, args=args)
                    kernel_rows.extend(kernels)
                    for result in results:
                        scoreboard_rows.append(result.row)
                        geometry_rows.append({"task": task.name, "length": int(length), "seed": int(seed), "capacity_units": int(capacity), "probe_family": result.row["probe_family"], "probe_id": result.row["probe_id"], **geometry_metrics(result.features, result.hidden_columns, task.train_end)})
                        readout_rows.append({"task": task.name, "length": int(length), "seed": int(seed), "capacity_units": int(capacity), "probe_family": result.row["probe_family"], "probe_id": result.row["probe_id"], **readout_metrics(result.weights, result.hidden_columns)})
    score_summary = summarize_scoreboard(scoreboard_rows)
    geometry_summary = summarize_numeric(geometry_rows, ["participation_ratio", "participation_ratio_per_unit", "rank95_variance_count", "top_pc_fraction", "state_norm_mean", "state_norm_std", "step_delta_mean", "step_delta_std", "total_state_variance"], ["task", "probe_family", "capacity_units"])
    readout_summary = summarize_numeric(readout_rows, ["readout_weight_pr", "top_weight_fraction", "hidden_weight_energy_fraction", "final_weight_norm"], ["task", "probe_family", "capacity_units"])
    kernel_summary = summarize_numeric(kernel_rows, ["linear_cka_to_candidate"], ["task", "probe_family", "capacity_units"])
    classification = classify(score_summary, geometry_summary, prereq_77l)
    regression_summary = {"compact_regression_inside_gate": False, "required_before_promotion": True, "reason": "Tier 7.7n is an attribution scoring gate. If attribution passes, route to separate promotion plus compact-regression gate before freeze."}
    criteria = [
        criterion("Tier 7.7m contract exists", str(CONTRACT_77M), "exists and pass", bool(contract_77m) and contract_77m.get("status") == "pass"),
        criterion("Tier 7.7l prerequisite exists", str(PREREQ_77L), "exists and pass", bool(prereq_77l) and prereq_77l.get("status") == "pass"),
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
    claim_boundary = "Tier 7.7n scores the locked 7.7m partitioned-driver attribution contract. It may support or block attribution diagnostically, but it does not freeze a baseline, promote a mechanism, authorize hardware/native transfer, or claim broad public usefulness."
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
    prefix = "tier7_7n"
    write_json(output_dir / f"{prefix}_results.json", payload)
    write_rows(output_dir / f"{prefix}_summary.csv", criteria)
    write_rows(output_dir / f"{prefix}_scoreboard.csv", scoreboard_rows)
    write_rows(output_dir / f"{prefix}_score_summary.csv", score_summary)
    write_rows(output_dir / f"{prefix}_attribution_margins.csv", [{"metric": key, "value": json_safe(value)} for key, value in classification["diagnostics"].items() if key.endswith("_divided_by_full") or key in {"full_lorenz_128_geomean_mse", "full_useful", "partition_sep", "generic_sep", "coherent_ablation_loss"}])
    write_rows(output_dir / f"{prefix}_driver_group_ablations.csv", [{"ablation": key, "margin_divided_by_full": value} for key, value in classification["diagnostics"].get("driver_group_ablation_margins", {}).items()])
    write_rows(output_dir / f"{prefix}_state_geometry.csv", geometry_rows)
    write_rows(output_dir / f"{prefix}_state_geometry_summary.csv", geometry_summary)
    write_rows(output_dir / f"{prefix}_state_kernel_alignment.csv", kernel_rows)
    write_rows(output_dir / f"{prefix}_readout_budget_audit.csv", readout_rows)
    write_rows(output_dir / f"{prefix}_sham_controls.csv", [row for row in scoreboard_rows if row.get("probe_family") != FULL])
    write_json(output_dir / f"{prefix}_regression_summary.json", regression_summary)
    write_json(output_dir / f"{prefix}_task_descriptors.json", task_descriptors)
    write_json(output_dir / f"{prefix}_probe_manifest.json", {"tasks": tasks, "lengths": lengths, "seeds": seeds, "capacities": capacities, "candidate": FULL, "permuted_offsets": parse_int_csv(args.permuted_offsets)})
    (output_dir / f"{prefix}_claim_boundary.md").write_text(claim_boundary + "\n", encoding="utf-8")
    report = [
        "# Tier 7.7n Partitioned-Driver Attribution Scoring Gate",
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
    (output_dir / f"{prefix}_report.md").write_text("\n".join(report), encoding="utf-8")
    manifest = {"tier": TIER, "status": status, "generated_at_utc": payload["generated_at_utc"], "output_dir": str(output_dir), "results_json": str(output_dir / f"{prefix}_results.json"), "report_md": str(output_dir / f"{prefix}_report.md"), "summary_csv": str(output_dir / f"{prefix}_summary.csv"), "classification_outcome": classification["outcome"]}
    write_json(output_dir / f"{prefix}_latest_manifest.json", manifest)
    write_json(CONTROLLED / f"{prefix}_latest_manifest.json", manifest)
    return payload


def main() -> int:
    args = build_parser().parse_args()
    payload = run(args)
    print(json.dumps(json_safe({"status": payload["status"], "criteria": f"{payload['criteria_passed']}/{payload['criteria_total']}", "classification": payload["classification"]["outcome"], "output_dir": payload["output_dir"]}), indent=2, sort_keys=True))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
