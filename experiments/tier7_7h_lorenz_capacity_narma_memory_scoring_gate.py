#!/usr/bin/env python3
"""Tier 7.7h - Lorenz capacity / NARMA memory-depth scoring gate.

Tier 7.7g pre-registered this diagnostic after Tier 7.7f localized the
standardized long-run signal to Mackey-Glass. This gate scores the locked
capacity matrix only. It does not add a new CRA mechanism, tune benchmarks, or
freeze a new baseline.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
import time
from collections import defaultdict
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

from tier4_scaling import mean, stdev  # noqa: E402
from tier5_19a_temporal_substrate_reference import (  # noqa: E402
    criterion,
    json_safe,
    parse_timescales,
    random_reservoir_features,
    run_online_model,
    run_train_prefix_esn,
    write_json,
)
from tier5_19b_temporal_substrate_gate import temporal_features_variant  # noqa: E402
from tier7_0_standard_dynamical_benchmarks import (  # noqa: E402
    build_task as build_standard_task,
    parse_csv,
    parse_seeds,
)
from tier7_0b_continuous_regression_failure_analysis import lag_matrix  # noqa: E402
from tier7_0c_continuous_readout_repair import shuffled_rows, shuffled_target  # noqa: E402
from tier7_7b_v2_5_standardized_scoreboard_scoring_gate import (  # noqa: E402
    causal_v2_5_meta_features,
    run_sequence_model,
    select_meta_columns,
)
from tier7_7f_repaired_finite_stream_long_run_scoreboard import (  # noqa: E402
    REPAIRED_GENERATOR_ID,
    repaired_narma10_series,
)


TIER = "Tier 7.7h - Lorenz Capacity / NARMA Memory-Depth Scoring Gate"
RUNNER_REVISION = "tier7_7h_lorenz_capacity_narma_memory_scoring_gate_20260509_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_7h_20260509_lorenz_capacity_narma_memory_scoring_gate"
CONTRACT_77G = CONTROLLED / "tier7_7g_20260509_lorenz_capacity_narma_memory_contract" / "tier7_7g_results.json"
PREREQ_77F = CONTROLLED / "tier7_7f_20260509_repaired_finite_stream_long_run_scoreboard" / "tier7_7f_results.json"
PREREQ_77E = CONTROLLED / "tier7_7e_20260509_finite_stream_repair_preflight" / "tier7_7e_results.json"

DEFAULT_TASKS = "mackey_glass,lorenz,narma10"
DEFAULT_LENGTHS = "8000,16000,32000"
DEFAULT_SEEDS = "42,43,44"
DEFAULT_CAPACITIES = "16,32,64,128"

CRA = "cra_v2_5_temporal_state"
ESN = "esn_train_prefix_ridge"
RESERVOIR = "random_reservoir_online"
LAG_RIDGE = "lag_ridge_reference"
ONLINE_LMS = "online_lms_reference"
STATE_RESET = "state_reset"
PERMUTED_RECURRENCE = "permuted_recurrence"
TARGET_SHUFFLE = "target_shuffle"
TIME_SHUFFLE = "time_shuffle"
PREDICTION_DISABLED = "prediction_disabled_meta"
MEMORY_DISABLED = "memory_disabled_meta"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_rows(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = []
        for row in rows:
            for key in row:
                if key not in fieldnames:
                    fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json_safe(row.get(key, "")) for key in fieldnames})


def safe_float(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


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


def geomean(values: list[float]) -> float | None:
    clean = [float(value) for value in values if value > 0.0 and math.isfinite(float(value))]
    if not clean:
        return None
    return float(math.exp(sum(math.log(value) for value in clean) / len(clean)))


def build_task(name: str, length: int, seed: int, horizon: int) -> Any:
    if name == "narma10":
        return repaired_narma10_series(length, seed, horizon=horizon)
    return build_standard_task(name, length, seed, horizon)


def model_name(prefix: str, units: int) -> str:
    return f"{prefix}_{int(units)}"


def make_base_kwargs(task: Any, seed: int, units: int, args: argparse.Namespace) -> dict[str, Any]:
    return {
        "seed": int(seed),
        "train_end": int(task.train_end),
        "timescales": parse_timescales(args.temporal_timescales),
        "hidden_units": int(units),
        "recurrent_scale": float(args.temporal_recurrent_scale),
        "input_scale": float(args.temporal_input_scale),
        "hidden_decay": float(args.temporal_hidden_decay),
    }


def run_capacity_models(task: Any, *, seed: int, length: int, units: int, args: argparse.Namespace) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    sham_rows: list[dict[str, Any]] = []
    base_kwargs = make_base_kwargs(task, seed, units, args)
    full = temporal_features_variant(task.observed, mode="full", **base_kwargs)
    state_reset = temporal_features_variant(
        task.observed,
        mode="full",
        reset_interval=max(8, int(args.state_reset_interval)),
        **base_kwargs,
    )
    permuted = temporal_features_variant(
        task.observed,
        mode="permuted_recurrence",
        recurrent_seed_offset=71,
        **base_kwargs,
    )
    meta, meta_diagnostics = causal_v2_5_meta_features(task.observed, horizon=args.horizon)
    candidate_features = np.column_stack([full.features, select_meta_columns(meta, "full")])
    target_shuffle = shuffled_target(task.target, task.train_end, seed)

    specs: list[tuple[str, np.ndarray, np.ndarray | None, dict[str, Any], bool]] = [
        (
            model_name(CRA, units),
            candidate_features,
            None,
            {
                **full.diagnostics,
                **meta_diagnostics,
                "capacity_units": int(units),
                "role": "locked v2.5 CRA temporal-state capacity candidate",
            },
            False,
        ),
        (
            model_name(STATE_RESET, units),
            np.column_stack([state_reset.features, select_meta_columns(meta, "full")]),
            None,
            {**state_reset.diagnostics, **meta_diagnostics, "sham": "state reset by capacity"},
            True,
        ),
        (
            model_name(PERMUTED_RECURRENCE, units),
            np.column_stack([permuted.features, select_meta_columns(meta, "full")]),
            None,
            {**permuted.diagnostics, **meta_diagnostics, "sham": "recurrent wiring permuted by capacity"},
            True,
        ),
        (
            model_name(TARGET_SHUFFLE, units),
            candidate_features,
            target_shuffle,
            {**full.diagnostics, **meta_diagnostics, "control": "candidate readout updates against shuffled target"},
            True,
        ),
        (
            model_name(TIME_SHUFFLE, units),
            shuffled_rows(candidate_features, task.train_end, seed),
            None,
            {**full.diagnostics, **meta_diagnostics, "control": "candidate feature rows shuffled inside train/test splits"},
            True,
        ),
        (
            model_name(PREDICTION_DISABLED, units),
            np.column_stack([full.features, select_meta_columns(meta, "prediction_disabled")]),
            None,
            {**full.diagnostics, **meta_diagnostics, "ablation": "remove predictive meta columns"},
            True,
        ),
        (
            model_name(MEMORY_DISABLED, units),
            np.column_stack([full.features, select_meta_columns(meta, "memory_disabled")]),
            None,
            {**full.diagnostics, **meta_diagnostics, "ablation": "remove memory/replay bridge meta columns"},
            True,
        ),
    ]
    for model, features, update_target, diagnostics, is_sham in specs:
        row, _pred = run_online_model(
            task=task,
            seed=seed,
            model=model,
            features=features,
            args=args,
            update_target=update_target,
            update_enabled=True,
            diagnostics={
                **diagnostics,
                "length": int(length),
                "feature_count": int(features.shape[1]),
                "tier7_7h_family": "capacity_candidate_or_sham",
            },
        )
        row.update({"length": int(length), "capacity_units": int(units), "model_family": model.rsplit("_", 1)[0]})
        rows.append(row)
        if is_sham:
            sham_rows.append(row)

    reservoir = random_reservoir_features(
        task.observed,
        seed=seed,
        units=int(units),
        spectral_radius=args.reservoir_spectral_radius,
        input_scale=args.reservoir_input_scale,
    )
    reservoir_row, _reservoir_pred = run_online_model(
        task=task,
        seed=seed,
        model=model_name(RESERVOIR, units),
        features=reservoir.features,
        args=args,
        diagnostics={**reservoir.diagnostics, "capacity_units": int(units), "role": "matched-capacity random reservoir"},
    )
    reservoir_row.update({"length": int(length), "capacity_units": int(units), "model_family": RESERVOIR})
    rows.append(reservoir_row)

    esn_args = argparse.Namespace(**vars(args))
    esn_args.esn_units = int(units)
    esn_row, _esn_pred = run_train_prefix_esn(task, seed=seed, args=esn_args)
    esn_row["model"] = model_name(ESN, units)
    esn_row["diagnostics"] = {**dict(esn_row.get("diagnostics") or {}), "capacity_units": int(units), "role": "matched-capacity ESN train-prefix ridge"}
    esn_row.update({"length": int(length), "capacity_units": int(units), "model_family": ESN})
    rows.append(esn_row)
    return rows, sham_rows


def run_reference_models(task: Any, *, seed: int, length: int, args: argparse.Namespace) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    lag = lag_matrix(task.observed, args.history)
    lag_row, _lag_pred = run_online_model(
        task=task,
        seed=seed,
        model="lag_only_online_lms_reference",
        features=lag,
        args=args,
        diagnostics={"role": "same causal lag budget online reference", "history": int(args.history)},
    )
    lag_row.update({"length": int(length), "capacity_units": 0, "model_family": "lag_online_lms"})
    rows.append(lag_row)

    for source, target_name in [("ridge_lag", LAG_RIDGE), ("online_lms", ONLINE_LMS)]:
        row, _pred = run_sequence_model(task, seed=seed, model_name=source, args=args)
        row["model"] = target_name
        row["diagnostics"] = {**dict(row.get("diagnostics") or {}), "role": f"{source} reference"}
        row.update({"length": int(length), "capacity_units": 0, "model_family": target_name})
        rows.append(row)
    return rows


def summarize_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(row["length"], row["task"], row["model"], row.get("capacity_units", 0))].append(row)
    out: list[dict[str, Any]] = []
    for (length, task, model, units), subset in sorted(groups.items()):
        pass_rows = [row for row in subset if row.get("status") == "pass" and safe_float(row.get("mse")) is not None]
        mses = [float(row["mse"]) for row in pass_rows]
        nmses = [float(row["nmse"]) for row in pass_rows if safe_float(row.get("nmse")) is not None]
        tails = [float(row["tail_mse"]) for row in pass_rows if safe_float(row.get("tail_mse")) is not None]
        corrs = [float(row["test_corr"]) for row in pass_rows if safe_float(row.get("test_corr")) is not None]
        train_mses = [float(row["train_mse"]) for row in pass_rows if safe_float(row.get("train_mse")) is not None]
        out.append(
            {
                "length": int(length),
                "task": task,
                "model": model,
                "capacity_units": int(units),
                "status": "pass" if len(pass_rows) == len(subset) and pass_rows else "fail",
                "seed_count": len(pass_rows),
                "mse_mean": mean(mses),
                "mse_median": float(np.median(mses)) if mses else None,
                "mse_std": stdev(mses),
                "mse_worst": max(mses) if mses else None,
                "nmse_mean": mean(nmses),
                "tail_mse_mean": mean(tails),
                "test_corr_mean": mean(corrs),
                "train_mse_mean": mean(train_mses),
                "train_test_gap": (mean(mses) / mean(train_mses)) if mses and train_mses and mean(train_mses) and mean(train_mses) > 0 else None,
            }
        )
    return out


def summary_metric(summary: list[dict[str, Any]], *, task: str, length: int, model: str, key: str = "mse_mean") -> float | None:
    row = next((item for item in summary if item["task"] == task and int(item["length"]) == int(length) and item["model"] == model), None)
    if not row:
        return None
    return safe_float(row.get(key))


def task_capacity_geomean(summary: list[dict[str, Any]], *, task: str, model: str, lengths: list[int]) -> float | None:
    values = [summary_metric(summary, task=task, length=length, model=model) for length in lengths]
    return geomean([float(value) for value in values if value is not None])


def build_capacity_curves(summary: list[dict[str, Any]], *, tasks: list[str], lengths: list[int], capacities: list[int]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for task in tasks:
        for length in lengths:
            base16 = summary_metric(summary, task=task, length=length, model=model_name(CRA, 16))
            for units in capacities:
                candidate = summary_metric(summary, task=task, length=length, model=model_name(CRA, units))
                esn = summary_metric(summary, task=task, length=length, model=model_name(ESN, units))
                reservoir = summary_metric(summary, task=task, length=length, model=model_name(RESERVOIR, units))
                closure = None
                if base16 is not None and candidate is not None and esn is not None and base16 > esn:
                    closure = (base16 - candidate) / (base16 - esn)
                rows.append(
                    {
                        "task": task,
                        "length": int(length),
                        "capacity_units": int(units),
                        "cra_mse_mean": candidate,
                        "esn_mse_mean": esn,
                        "reservoir_mse_mean": reservoir,
                        "cra16_divided_by_cra_capacity": ratio(base16, candidate),
                        "cra_capacity_divided_by_esn": ratio(candidate, esn),
                        "gap_closure_to_matched_esn": closure,
                        "cra_tail_mse_mean": summary_metric(summary, task=task, length=length, model=model_name(CRA, units), key="tail_mse_mean"),
                        "cra_test_corr_mean": summary_metric(summary, task=task, length=length, model=model_name(CRA, units), key="test_corr_mean"),
                    }
                )
    return rows


def build_capacity_aggregate(summary: list[dict[str, Any]], *, tasks: list[str], lengths: list[int], capacities: list[int]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for task in tasks:
        base16 = task_capacity_geomean(summary, task=task, model=model_name(CRA, 16), lengths=lengths)
        for units in capacities:
            candidate = task_capacity_geomean(summary, task=task, model=model_name(CRA, units), lengths=lengths)
            esn = task_capacity_geomean(summary, task=task, model=model_name(ESN, units), lengths=lengths)
            reservoir = task_capacity_geomean(summary, task=task, model=model_name(RESERVOIR, units), lengths=lengths)
            closure = None
            if base16 is not None and candidate is not None and esn is not None and base16 > esn:
                closure = (base16 - candidate) / (base16 - esn)
            rows.append(
                {
                    "task": task,
                    "capacity_units": int(units),
                    "cra_geomean_mse": candidate,
                    "esn_geomean_mse": esn,
                    "reservoir_geomean_mse": reservoir,
                    "cra16_divided_by_cra_capacity": ratio(base16, candidate),
                    "gap_closure_to_matched_esn": closure,
                    "cra_capacity_divided_by_esn": ratio(candidate, esn),
                    "best_external_model": "esn" if esn is not None and (reservoir is None or esn <= reservoir) else "random_reservoir",
                    "best_external_geomean_mse": min([value for value in [esn, reservoir] if value is not None], default=None),
                }
            )
    return rows


def build_matched_capacity_baselines(summary: list[dict[str, Any]], *, tasks: list[str], lengths: list[int], capacities: list[int]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    model_specs = [(CRA, "CRA candidate"), (ESN, "matched ESN"), (RESERVOIR, "matched random reservoir")]
    for task in tasks:
        for units in capacities:
            for prefix, family in model_specs:
                rows.append(
                    {
                        "task": task,
                        "capacity_units": int(units),
                        "family": family,
                        "model": model_name(prefix, units),
                        "geomean_mse": task_capacity_geomean(summary, task=task, model=model_name(prefix, units), lengths=lengths),
                    }
                )
        for model in ["lag_only_online_lms_reference", LAG_RIDGE, ONLINE_LMS]:
            rows.append(
                {
                    "task": task,
                    "capacity_units": 0,
                    "family": "simple reference",
                    "model": model,
                    "geomean_mse": task_capacity_geomean(summary, task=task, model=model, lengths=lengths),
                }
            )
    return rows


def build_sham_summary(summary: list[dict[str, Any]], *, tasks: list[str], lengths: list[int], capacities: list[int]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    sham_prefixes = [STATE_RESET, PERMUTED_RECURRENCE, TARGET_SHUFFLE, TIME_SHUFFLE, PREDICTION_DISABLED, MEMORY_DISABLED]
    for task in tasks:
        for units in capacities:
            candidate = task_capacity_geomean(summary, task=task, model=model_name(CRA, units), lengths=lengths)
            for prefix in sham_prefixes:
                sham = task_capacity_geomean(summary, task=task, model=model_name(prefix, units), lengths=lengths)
                rows.append(
                    {
                        "task": task,
                        "capacity_units": int(units),
                        "sham_model": model_name(prefix, units),
                        "candidate_geomean_mse": candidate,
                        "sham_geomean_mse": sham,
                        "sham_divided_by_candidate": ratio(sham, candidate),
                        "candidate_separates": ratio(sham, candidate) is not None and float(ratio(sham, candidate)) >= 1.02,
                    }
                )
    return rows


def best_task_capacity(aggregate: list[dict[str, Any]], task: str) -> dict[str, Any] | None:
    rows = [row for row in aggregate if row["task"] == task and row.get("cra_geomean_mse") is not None]
    if not rows:
        return None
    return min(rows, key=lambda row: float(row["cra_geomean_mse"]))


def classify(aggregate: list[dict[str, Any]], sham_summary: list[dict[str, Any]], *, tasks: list[str]) -> dict[str, Any]:
    task_diagnostics: list[dict[str, Any]] = []
    any_material = False
    any_gap_closing = False
    sham_blocked_tasks: list[str] = []
    for task in tasks:
        base = next((row for row in aggregate if row["task"] == task and int(row["capacity_units"]) == 16), None)
        best = best_task_capacity(aggregate, task)
        if base is None or best is None:
            continue
        improvement = ratio(safe_float(base.get("cra_geomean_mse")), safe_float(best.get("cra_geomean_mse")))
        closure = safe_float(best.get("gap_closure_to_matched_esn"))
        material = improvement is not None and improvement >= 1.25
        gap_closing = material and closure is not None and closure >= 0.30
        any_material = any_material or bool(material and task in {"lorenz", "narma10"})
        any_gap_closing = any_gap_closing or bool(gap_closing and task in {"lorenz", "narma10"})
        task_shams = [
            row
            for row in sham_summary
            if row["task"] == task
            and int(row["capacity_units"]) == int(best["capacity_units"])
            and row["sham_model"].split("_")[0] in {"target", "time", "permuted", "state"}
        ]
        sham_block = any(row.get("sham_divided_by_candidate") is not None and float(row["sham_divided_by_candidate"]) < 1.02 for row in task_shams)
        if sham_block and task in {"lorenz", "narma10"} and material:
            sham_blocked_tasks.append(task)
        task_diagnostics.append(
            {
                "task": task,
                "base16_cra_geomean_mse": base.get("cra_geomean_mse"),
                "best_capacity_units": int(best["capacity_units"]),
                "best_cra_geomean_mse": best.get("cra_geomean_mse"),
                "best_esn_geomean_mse": best.get("esn_geomean_mse"),
                "best_reservoir_geomean_mse": best.get("reservoir_geomean_mse"),
                "base16_divided_by_best_capacity": improvement,
                "gap_closure_to_matched_esn": closure,
                "material_capacity_improvement": bool(material),
                "gap_closing": bool(gap_closing),
                "sham_blocked": bool(sham_block),
            }
        )

    mackey = next((row for row in task_diagnostics if row["task"] == "mackey_glass"), {})
    lorenz = next((row for row in task_diagnostics if row["task"] == "lorenz"), {})
    narma = next((row for row in task_diagnostics if row["task"] == "narma10"), {})
    mackey_regression = (
        mackey.get("best_capacity_units") not in {None, 16}
        and mackey.get("base16_divided_by_best_capacity") is not None
        and float(mackey["base16_divided_by_best_capacity"]) < 0.90
        and not any_material
    )
    if sham_blocked_tasks:
        outcome = "overfit_or_sham_blocked"
        recommendation = "Do not promote capacity or a mechanism; repair sham separation before using this diagnostic as evidence."
    elif any_gap_closing:
        outcome = "capacity_limited_closing"
        recommendation = "Capacity/state-interface limitation is supported; design a capacity/state-interface follow-up before adding new mechanisms."
    elif any_material:
        outcome = "capacity_helps_but_baseline_gap_persists"
        recommendation = "Capacity helps at least one blocked task but does not close the external-baseline gap; do targeted state-interface repair rather than blind mechanism layering."
    elif mackey_regression:
        outcome = "mackey_regression"
        recommendation = "Do not promote larger capacity; preserve the v2.5 localized Mackey claim and inspect why larger state damaged the anchor."
    else:
        outcome = "architecture_limited_flat"
        recommendation = "Capacity alone did not materially repair Lorenz/NARMA; move to a predeclared structural mechanism/interface gate."
    return {
        "outcome": outcome,
        "recommendation": recommendation,
        "task_diagnostics": task_diagnostics,
        "lorenz_material_capacity_improvement": bool(lorenz.get("material_capacity_improvement")),
        "narma_material_capacity_improvement": bool(narma.get("material_capacity_improvement")),
        "mackey_anchor": mackey,
        "sham_blocked_tasks": sham_blocked_tasks,
        "claim_allowed": {
            "capacity_limited_closing": outcome == "capacity_limited_closing",
            "capacity_helps": outcome in {"capacity_limited_closing", "capacity_helps_but_baseline_gap_persists"},
            "architecture_limited_flat": outcome == "architecture_limited_flat",
            "baseline_freeze": False,
            "mechanism_promotion": False,
            "hardware_or_native_transfer": False,
            "external_baseline_superiority": False,
        },
        "nonclaims": [
            "not a new CRA baseline freeze",
            "not a mechanism promotion",
            "not hardware/native transfer",
            "not external-baseline superiority unless the table explicitly shows it",
            "not broad public usefulness",
            "not language, general reasoning, AGI, or ASI evidence",
        ],
    }


def finite_descriptor(task: Any) -> dict[str, Any]:
    return {
        "observed_finite": bool(np.all(np.isfinite(task.observed))),
        "target_finite": bool(np.all(np.isfinite(task.target))),
        "observed_min": float(np.nanmin(task.observed)),
        "observed_max": float(np.nanmax(task.observed)),
        "target_min": float(np.nanmin(task.target)),
        "target_max": float(np.nanmax(task.target)),
        "train_end": int(task.train_end),
        "sample_count": int(len(task.target)),
        "metadata": task.metadata,
    }


def write_report(output_dir: Path, payload: dict[str, Any]) -> None:
    c = payload["classification"]
    lines = [
        "# Tier 7.7h Lorenz Capacity / NARMA Memory-Depth Scoring Gate",
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
        "## Task Diagnostics",
        "",
        "| Task | Best capacity | Base16 MSE | Best CRA MSE | ESN MSE | Improvement | Gap closure | Material |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in c["task_diagnostics"]:
        lines.append(
            f"| {row['task']} | {row['best_capacity_units']} | {row['base16_cra_geomean_mse']} | {row['best_cra_geomean_mse']} | {row['best_esn_geomean_mse']} | {row['base16_divided_by_best_capacity']} | {row['gap_closure_to_matched_esn']} | {row['material_capacity_improvement']} |"
        )
    lines.extend(["", "## Nonclaims", ""])
    for item in c["nonclaims"]:
        lines.append(f"- {item}")
    lines.append("")
    (output_dir / "tier7_7h_report.md").write_text("\n".join(lines), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=TIER)
    parser.add_argument("--tasks", default=DEFAULT_TASKS)
    parser.add_argument("--lengths", default=DEFAULT_LENGTHS)
    parser.add_argument("--seeds", default=DEFAULT_SEEDS)
    parser.add_argument("--capacities", default=DEFAULT_CAPACITIES)
    parser.add_argument("--horizon", type=int, default=8)
    parser.add_argument("--history", type=int, default=12)
    parser.add_argument("--readout-lr", type=float, default=0.08)
    parser.add_argument("--readout-decay", type=float, default=1e-5)
    parser.add_argument("--weight-clip", type=float, default=20.0)
    parser.add_argument("--output-clip", type=float, default=3.0)
    parser.add_argument("--online-lr", type=float, default=0.04)
    parser.add_argument("--online-decay", type=float, default=1e-5)
    parser.add_argument("--ridge", type=float, default=1e-3)
    parser.add_argument("--temporal-timescales", default="2,4,8,16,32,64,128")
    parser.add_argument("--temporal-recurrent-scale", type=float, default=0.65)
    parser.add_argument("--temporal-input-scale", type=float, default=0.45)
    parser.add_argument("--temporal-hidden-decay", type=float, default=0.72)
    parser.add_argument("--state-reset-interval", type=int, default=64)
    parser.add_argument("--reservoir-spectral-radius", type=float, default=0.9)
    parser.add_argument("--reservoir-input-scale", type=float, default=0.5)
    parser.add_argument("--esn-spectral-radius", type=float, default=0.9)
    parser.add_argument("--esn-input-scale", type=float, default=0.5)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--smoke", action="store_true")
    return parser


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if args.smoke:
        args.tasks = "mackey_glass"
        args.lengths = "720"
        args.seeds = "42"
        args.capacities = "16,32"
    tasks = parse_csv(args.tasks)
    lengths = parse_int_csv(args.lengths)
    seeds = parse_seeds(argparse.Namespace(seeds=args.seeds, seed_count=None, base_seed=42))
    capacities = parse_int_csv(args.capacities)
    started = time.perf_counter()
    prereq_77g = read_json(CONTRACT_77G)
    prereq_77f = read_json(PREREQ_77F)
    prereq_77e = read_json(PREREQ_77E)
    rows: list[dict[str, Any]] = []
    task_descriptors: list[dict[str, Any]] = []
    invalid_tasks: list[dict[str, Any]] = []
    for length in lengths:
        for seed in seeds:
            for task_name in tasks:
                task = build_task(task_name, length, seed, args.horizon)
                descriptor = {
                    "length": int(length),
                    "task": task.name,
                    "display_name": task.display_name,
                    "seed": int(seed),
                    "horizon": int(task.horizon),
                    "finite_check": finite_descriptor(task),
                }
                task_descriptors.append(descriptor)
                if not (descriptor["finite_check"]["observed_finite"] and descriptor["finite_check"]["target_finite"]):
                    invalid_tasks.append(descriptor)
                    continue
                rows.extend(run_reference_models(task, seed=seed, length=length, args=args))
                for units in capacities:
                    capacity_rows, _capacity_shams = run_capacity_models(task, seed=seed, length=length, units=units, args=args)
                    rows.extend(capacity_rows)
    summary = summarize_rows(rows)
    capacity_curves = build_capacity_curves(summary, tasks=tasks, lengths=lengths, capacities=capacities)
    capacity_aggregate = build_capacity_aggregate(summary, tasks=tasks, lengths=lengths, capacities=capacities)
    matched_baselines = build_matched_capacity_baselines(summary, tasks=tasks, lengths=lengths, capacities=capacities)
    sham_summary = build_sham_summary(summary, tasks=tasks, lengths=lengths, capacities=capacities)
    classification = classify(capacity_aggregate, sham_summary, tasks=tasks)
    repaired_manifest = {
        "selected_generator": REPAIRED_GENERATOR_ID,
        "input_distribution": "Uniform(0,0.2)",
        "equation_coefficients": {"alpha": 0.3, "beta": 0.05, "gamma": 1.5, "delta": 0.1, "order": 10},
        "output_wrapper": "none",
        "source_gate": str(PREREQ_77E),
        "labeling_rule": "Repaired NARMA10 U(0,0.2); do not silently mix with prior U(0,0.5) NARMA scores.",
    }
    required_candidate_models = [model_name(CRA, units) for units in capacities]
    required_esn_models = [model_name(ESN, units) for units in capacities]
    required_reservoir_models = [model_name(RESERVOIR, units) for units in capacities]
    observed_models = {row["model"] for row in rows}
    criteria = [
        criterion("Tier 7.7g contract exists", str(CONTRACT_77G), "exists and pass", bool(prereq_77g) and prereq_77g.get("status") == "pass"),
        criterion("Tier 7.7g authorizes scoring", (prereq_77g.get("classification") or {}).get("scoring_authorized"), "true", bool((prereq_77g.get("classification") or {}).get("scoring_authorized"))),
        criterion("Tier 7.7f prerequisite exists", str(PREREQ_77F), "exists and pass", bool(prereq_77f) and prereq_77f.get("status") == "pass"),
        criterion("Tier 7.7e prerequisite exists", str(PREREQ_77E), "exists and pass", bool(prereq_77e) and prereq_77e.get("status") == "pass"),
        criterion("repaired NARMA stream locked", repaired_manifest["selected_generator"], f"== {REPAIRED_GENERATOR_ID}", repaired_manifest["selected_generator"] == REPAIRED_GENERATOR_ID),
        criterion("locked tasks", tasks, "== Mackey/Lorenz/NARMA", set(tasks) == {"mackey_glass", "lorenz", "narma10"} or bool(args.smoke)),
        criterion("locked lengths", lengths, "== 8000/16000/32000", lengths == [8000, 16000, 32000] or bool(args.smoke)),
        criterion("locked seeds", seeds, "== 42/43/44", seeds == [42, 43, 44] or bool(args.smoke)),
        criterion("locked capacities", capacities, "== 16/32/64/128", capacities == [16, 32, 64, 128] or bool(args.smoke)),
        criterion("finite generated streams", len(invalid_tasks), "== 0", len(invalid_tasks) == 0),
        criterion("candidate capacity models present", required_candidate_models, "all present", all(model in observed_models for model in required_candidate_models)),
        criterion("matched ESN models present", required_esn_models, "all present", all(model in observed_models for model in required_esn_models)),
        criterion("matched reservoir models present", required_reservoir_models, "all present", all(model in observed_models for model in required_reservoir_models)),
        criterion("capacity curves produced", len(capacity_curves), ">= tasks*lengths*capacities", len(capacity_curves) >= len(tasks) * len(lengths) * len(capacities)),
        criterion("sham controls produced", len(sham_summary), ">= tasks*capacities*6", len(sham_summary) >= len(tasks) * len(capacities) * 6),
        criterion("classification produced", classification["outcome"], "non-empty", bool(classification["outcome"])),
        criterion("no baseline freeze", classification["claim_allowed"]["baseline_freeze"], "false", classification["claim_allowed"]["baseline_freeze"] is False),
        criterion("no mechanism promotion", classification["claim_allowed"]["mechanism_promotion"], "false", classification["claim_allowed"]["mechanism_promotion"] is False),
        criterion("hardware/native transfer blocked", classification["claim_allowed"]["hardware_or_native_transfer"], "false", classification["claim_allowed"]["hardware_or_native_transfer"] is False),
    ]
    passed = sum(1 for item in criteria if item["passed"])
    status = "pass" if passed == len(criteria) else "fail"
    claim_boundary = (
        "Tier 7.7h scores the pre-registered 7.7g Lorenz/NARMA capacity matrix. "
        "It may classify whether the remaining gap is capacity-limited, capacity-helpful but baseline-gap limited, architecture-limited flat, sham-blocked, or Mackey-regressing. "
        "It does not freeze a baseline, promote a mechanism, authorize hardware/native transfer, or claim broad public usefulness."
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
        "horizon": int(args.horizon),
        "prerequisites": {
            "tier7_7g": str(CONTRACT_77G),
            "tier7_7g_status": prereq_77g.get("status"),
            "tier7_7f": str(PREREQ_77F),
            "tier7_7f_status": prereq_77f.get("status"),
            "tier7_7e": str(PREREQ_77E),
            "tier7_7e_status": prereq_77e.get("status"),
        },
        "classification": classification,
        "scoreboard_rows": rows,
        "summary_rows": summary,
        "capacity_curves": capacity_curves,
        "capacity_aggregate": capacity_aggregate,
        "matched_capacity_baselines": matched_baselines,
        "sham_controls": sham_summary,
        "task_descriptors": task_descriptors,
        "invalid_tasks": invalid_tasks,
        "repaired_stream_manifest": repaired_manifest,
        "claim_boundary": claim_boundary,
        "runtime_seconds": time.perf_counter() - started,
    }
    write_json(output_dir / "tier7_7h_results.json", payload)
    write_rows(output_dir / "tier7_7h_summary.csv", criteria)
    write_rows(output_dir / "tier7_7h_capacity_scoreboard.csv", rows)
    write_rows(output_dir / "tier7_7h_capacity_summary.csv", summary)
    write_rows(output_dir / "tier7_7h_capacity_curves.csv", capacity_curves)
    write_rows(output_dir / "tier7_7h_capacity_aggregate.csv", capacity_aggregate)
    write_rows(output_dir / "tier7_7h_matched_capacity_baselines.csv", matched_baselines)
    write_rows(output_dir / "tier7_7h_sham_controls.csv", sham_summary)
    write_json(output_dir / "tier7_7h_repaired_stream_manifest.json", repaired_manifest)
    write_json(output_dir / "tier7_7h_task_descriptors.json", task_descriptors)
    (output_dir / "tier7_7h_claim_boundary.md").write_text(claim_boundary + "\n", encoding="utf-8")
    write_report(output_dir, payload)
    manifest = {
        "tier": TIER,
        "status": status,
        "generated_at_utc": payload["generated_at_utc"],
        "output_dir": str(output_dir),
        "results_json": str(output_dir / "tier7_7h_results.json"),
        "report_md": str(output_dir / "tier7_7h_report.md"),
        "summary_csv": str(output_dir / "tier7_7h_summary.csv"),
        "classification_outcome": classification["outcome"],
    }
    write_json(output_dir / "tier7_7h_latest_manifest.json", manifest)
    write_json(CONTROLLED / "tier7_7h_latest_manifest.json", manifest)
    return payload


def main() -> int:
    args = build_parser().parse_args()
    payload = run(args)
    print(
        json.dumps(
            json_safe(
                {
                    "status": payload["status"],
                    "criteria": f"{payload['criteria_passed']}/{payload['criteria_total']}",
                    "classification": payload["classification"]["outcome"],
                    "output_dir": payload["output_dir"],
                }
            ),
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
