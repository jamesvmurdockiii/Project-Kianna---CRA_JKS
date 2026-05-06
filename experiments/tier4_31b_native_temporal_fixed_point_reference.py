#!/usr/bin/env python3
"""Tier 4.31b - Native Temporal-Substrate Local Fixed-Point Reference.

Tier 4.31a predeclared the smallest native temporal subset for the v2.2
fading-memory mechanism. This gate tests the next question locally: does a
fixed-point mirror of that seven-EMA trace bank preserve the promoted Tier 5.19c
fading-memory behavior and fail the destructive controls?

This is still local software/reference evidence. It does not edit the C runtime,
prepare EBRAINS artifacts, or claim hardware transfer.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
import time
from dataclasses import dataclass
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

from tier4_scaling import mean  # noqa: E402
from tier5_19a_temporal_substrate_reference import (  # noqa: E402
    append_timeseries,
    run_online_model,
    summarize,
    write_json,
)
from tier5_19b_temporal_substrate_gate import temporal_features_variant  # noqa: E402
from tier5_19c_fading_memory_regression import (  # noqa: E402
    TEMPORAL_MEMORY_TASKS,
    build_task,
    geometric,
    ratio,
)
from tier7_0_standard_dynamical_benchmarks import parse_csv, parse_seeds  # noqa: E402
from tier7_0b_continuous_regression_failure_analysis import lag_matrix  # noqa: E402
from tier7_0c_continuous_readout_repair import shuffled_rows, shuffled_target  # noqa: E402


TIER = "Tier 4.31b - Native Temporal-Substrate Local Fixed-Point Reference"
RUNNER_REVISION = "tier4_31b_native_temporal_fixed_point_reference_20260506_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier4_31b_20260506_native_temporal_fixed_point_reference"
TIER431A_RESULTS = CONTROLLED / "tier4_31a_20260506_native_temporal_substrate_readiness" / "tier4_31a_results.json"
TIER519C_RESULTS = CONTROLLED / "tier5_19c_20260505_fading_memory_regression" / "tier5_19c_results.json"
DEFAULT_TASKS = "heldout_long_memory,slow_context_drift,multiscale_echo"

FP_SHIFT = 15
FP_ONE = 1 << FP_SHIFT


@dataclass(frozen=True)
class FixedPointBundle:
    features: np.ndarray
    names: list[str]
    diagnostics: dict[str, Any]
    trace_rows: list[dict[str, Any]]


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
        value = float(value)
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def criterion(name: str, value: Any, rule: str, passed: bool, note: str = "") -> dict[str, Any]:
    return {"name": name, "value": json_safe(value), "rule": rule, "passed": bool(passed), "note": note}


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = []
        seen: set[str] = set()
        for row in rows:
            for key in row:
                if key not in seen:
                    seen.add(key)
                    fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def fp_from_float(value: float) -> int:
    # Match the C FP_FROM_FLOAT macro's truncating cast for positive constants.
    return int(float(value) * float(FP_ONE))


def fp_mul(a: int, b: int) -> int:
    return int((int(a) * int(b)) >> FP_SHIFT)


def fp_to_float(value: int) -> float:
    return float(value) / float(FP_ONE)


def parse_timescales(raw: str) -> list[int]:
    values = [int(float(item)) for item in parse_csv(raw)]
    if not values:
        raise ValueError("at least one temporal timescale is required")
    return values


def fixed_point_table(timescales: list[int]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for tau in timescales:
        decay = math.exp(-1.0 / float(tau))
        alpha = 1.0 - decay
        rows.append(
            {
                "tau_steps": int(tau),
                "decay_float": float(decay),
                "alpha_float": float(alpha),
                "decay_raw_s16_15": fp_from_float(decay),
                "alpha_raw_s16_15": fp_from_float(alpha),
            }
        )
    return rows


def checksum_timescales(rows: list[dict[str, Any]]) -> int:
    checksum = 0
    for row in rows:
        checksum = (
            checksum * 1315423911
            + int(row["tau_steps"]) * 17
            + int(row["alpha_raw_s16_15"])
            + int(row["decay_raw_s16_15"])
        ) & 0xFFFFFFFF
    return checksum


def fixed_point_temporal_features(
    observed: np.ndarray,
    *,
    timescales: list[int],
    trace_bound: float,
    input_bound: float,
    reset_interval: int = 0,
    zero_state: bool = False,
) -> FixedPointBundle:
    values = np.asarray(observed, dtype=float)
    table = fixed_point_table(timescales)
    alpha_raw = [int(row["alpha_raw_s16_15"]) for row in table]
    decay_raw = [int(row["decay_raw_s16_15"]) for row in table]
    traces = [0 for _ in timescales]
    trace_bound_raw = fp_from_float(float(trace_bound))
    input_bound_raw = fp_from_float(float(input_bound))
    novelty_bound_raw = fp_from_float(float(input_bound) + float(trace_bound))
    rows: list[np.ndarray] = []
    trace_rows: list[dict[str, Any]] = []
    saturation_count = 0
    input_clip_count = 0
    reset_count = 0
    trace_abs_sum_max = 0
    trace_checksum = 0

    for step, value in enumerate(values):
        x_raw = fp_from_float(float(value))
        if x_raw > input_bound_raw:
            x_raw = input_bound_raw
            input_clip_count += 1
        elif x_raw < -input_bound_raw:
            x_raw = -input_bound_raw
            input_clip_count += 1
        if reset_interval > 0 and step > 0 and step % int(reset_interval) == 0:
            traces = [0 for _ in timescales]
            reset_count += 1
        previous = traces.copy()
        previous_slowest = previous[-1] if previous else 0
        if zero_state:
            traces = [0 for _ in timescales]
        else:
            for idx in range(len(traces)):
                candidate = fp_mul(decay_raw[idx], traces[idx]) + fp_mul(alpha_raw[idx], x_raw)
                if candidate > trace_bound_raw:
                    candidate = trace_bound_raw
                    saturation_count += 1
                elif candidate < -trace_bound_raw:
                    candidate = -trace_bound_raw
                    saturation_count += 1
                traces[idx] = int(candidate)
        deltas = [traces[idx + 1] - traces[idx] for idx in range(max(0, len(traces) - 1))]
        novelty_raw = 0 if zero_state else x_raw - previous_slowest
        if novelty_raw > novelty_bound_raw:
            novelty_raw = novelty_bound_raw
        elif novelty_raw < -novelty_bound_raw:
            novelty_raw = -novelty_bound_raw
        trace_abs_sum = int(sum(abs(item) for item in traces))
        trace_abs_sum_max = max(trace_abs_sum_max, trace_abs_sum)
        trace_checksum = (trace_checksum * 2654435761 + sum((idx + 1) * item for idx, item in enumerate(traces))) & 0xFFFFFFFF
        rows.append(
            np.asarray(
                [1.0, fp_to_float(x_raw)]
                + [fp_to_float(item) for item in traces]
                + [fp_to_float(item) for item in deltas]
                + [fp_to_float(novelty_raw)],
                dtype=float,
            )
        )
        trace_rows.append(
            {
                "step": int(step),
                "input_raw": int(x_raw),
                "trace_checksum": int(trace_checksum),
                "trace_abs_sum_raw": int(trace_abs_sum),
                "novelty_raw": int(novelty_raw),
                "saturation_count": int(saturation_count),
                "reset_count": int(reset_count),
            }
        )
    names = ["bias", "observed_current"]
    names.extend([f"ema_tau_{tau:g}" for tau in timescales])
    names.extend([f"ema_delta_{idx}_{idx + 1}" for idx in range(max(0, len(timescales) - 1))])
    names.append("novelty_vs_slowest_ema")
    diagnostics = {
        "state_location": "local fixed-point mirror of proposed native temporal trace bank",
        "mode": "fixed_point_fading_memory_ema",
        "timescales": [int(item) for item in timescales],
        "timescale_checksum": int(checksum_timescales(table)),
        "trace_count": int(len(timescales)),
        "trace_bound_raw": int(trace_bound_raw),
        "trace_bound_float": float(trace_bound),
        "input_bound_raw": int(input_bound_raw),
        "input_bound_float": float(input_bound),
        "reset_interval": int(reset_interval),
        "zero_state": bool(zero_state),
        "saturation_count": int(saturation_count),
        "input_clip_count": int(input_clip_count),
        "reset_count": int(reset_count),
        "trace_abs_sum_max_raw": int(trace_abs_sum_max),
        "final_trace_checksum": int(trace_checksum),
        "feature_count": int(len(names)),
        "fixed_point": "s16.15, FP_MUL-compatible",
    }
    return FixedPointBundle(features=np.vstack(rows), names=names, diagnostics=diagnostics, trace_rows=trace_rows)


def freeze_temporal_columns(features: np.ndarray, train_end: int, temporal_start: int = 2) -> np.ndarray:
    out = np.asarray(features, dtype=float).copy()
    if train_end > 0 and train_end < len(out):
        out[train_end:, temporal_start:] = out[train_end - 1, temporal_start:]
    return out


def trace_error_rows(task_name: str, seed: int, fixed: FixedPointBundle, float_features: np.ndarray) -> dict[str, Any]:
    temporal_float = np.asarray(float_features[:, 2:], dtype=float)
    temporal_fixed = np.asarray(fixed.features[:, 2:], dtype=float)
    err = np.abs(temporal_float - temporal_fixed)
    return {
        "task": task_name,
        "seed": int(seed),
        "max_abs_error": float(np.max(err)),
        "mean_abs_error": float(np.mean(err)),
        "p95_abs_error": float(np.quantile(err, 0.95)),
        "saturation_count": int(fixed.diagnostics["saturation_count"]),
        "input_clip_count": int(fixed.diagnostics["input_clip_count"]),
        "reset_count": int(fixed.diagnostics["reset_count"]),
        "final_trace_checksum": int(fixed.diagnostics["final_trace_checksum"]),
    }


def run_one_task(task_name: str, seed: int, args: argparse.Namespace) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    task = build_task(task_name, args.length, seed, args.horizon)
    timescales = parse_timescales(args.temporal_timescales)
    float_reference = temporal_features_variant(
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
    fixed = fixed_point_temporal_features(
        task.observed,
        timescales=timescales,
        trace_bound=args.trace_bound,
        input_bound=args.input_bound,
    )
    conservative_bound = fixed_point_temporal_features(
        task.observed,
        timescales=timescales,
        trace_bound=1.0,
        input_bound=args.input_bound,
    )
    zero_state = fixed_point_temporal_features(
        task.observed,
        timescales=timescales,
        trace_bound=args.trace_bound,
        input_bound=args.input_bound,
        zero_state=True,
    )
    reset_state = fixed_point_temporal_features(
        task.observed,
        timescales=timescales,
        trace_bound=args.trace_bound,
        input_bound=args.input_bound,
        reset_interval=args.state_reset_interval,
    )
    lag = lag_matrix(task.observed, args.history)
    wrong_target = shuffled_target(task.target, task.train_end, seed)
    frozen = freeze_temporal_columns(fixed.features, task.train_end, 2)

    model_specs: list[tuple[str, np.ndarray, np.ndarray | None, bool, dict[str, Any]]] = [
        ("fixed_point_temporal_candidate", fixed.features, None, True, fixed.diagnostics),
        ("float_fading_memory_reference", float_reference.features, None, True, float_reference.diagnostics),
        ("lag_only_online_lms_control", lag, None, True, {"role": "same causal lag budget", "history": int(args.history)}),
        ("zero_temporal_state_ablation", zero_state.features, None, True, zero_state.diagnostics),
        ("frozen_temporal_state_ablation", frozen, None, True, {**fixed.diagnostics, "ablation": "temporal columns frozen after train prefix"}),
        ("shuffled_temporal_state_sham", shuffled_rows(fixed.features, task.train_end, seed), None, True, {**fixed.diagnostics, "sham": "feature rows shuffled within train/test splits"}),
        ("state_reset_interval_control", reset_state.features, None, True, reset_state.diagnostics),
        ("shuffled_target_control", fixed.features, wrong_target, True, {**fixed.diagnostics, "control": "online readout updates against shuffled targets"}),
        ("no_plasticity_ablation", fixed.features, None, False, {**fixed.diagnostics, "ablation": "readout updates disabled"}),
    ]
    rows: list[dict[str, Any]] = []
    timeseries: list[dict[str, Any]] = []
    for model, features, update_target, update_enabled, diagnostics in model_specs:
        row, pred = run_online_model(
            task=task,
            seed=seed,
            model=model,
            features=features,
            args=args,
            update_target=update_target,
            update_enabled=update_enabled,
            diagnostics=diagnostics,
        )
        rows.append(row)
        append_timeseries(timeseries, task=task, seed=seed, model=model, prediction=pred)

    diagnostics = {
        "task": task.name,
        "seed": int(seed),
        "length": int(len(task.target)),
        "train_end": int(task.train_end),
        "horizon": int(task.horizon),
        "fixed_point_feature_names": fixed.names,
        "float_reference_feature_names": float_reference.names,
        "fixed_point_diagnostics": fixed.diagnostics,
        "float_reference_diagnostics": float_reference.diagnostics,
        "conservative_bound_diagnostics": conservative_bound.diagnostics,
        "range_refinement": {
            "conservative_trace_bound": 1.0,
            "selected_trace_bound": float(args.trace_bound),
            "conservative_saturation_count": int(conservative_bound.diagnostics["saturation_count"]),
            "selected_saturation_count": int(fixed.diagnostics["saturation_count"]),
            "reason": "selected bound preserves compact state budget while removing saturation on canonical temporal diagnostics",
        },
    }
    error_rows = [
        {
            **trace_error_rows(task.name, seed, fixed, float_reference.features),
            "variant": "selected_trace_bound",
            "trace_bound": float(args.trace_bound),
        },
        {
            **trace_error_rows(task.name, seed, conservative_bound, float_reference.features),
            "variant": "conservative_trace_bound_1",
            "trace_bound": 1.0,
        },
    ]
    trace_rows = [{**row, "task": task.name, "seed": int(seed)} for row in fixed.trace_rows]
    return rows, timeseries, diagnostics, error_rows, trace_rows


def metric(summary_rows: list[dict[str, Any]], task: str, model: str, key: str = "mse_mean") -> float:
    row = next((item for item in summary_rows if item["task"] == task and item["model"] == model), None)
    if not row or row.get(key) is None:
        return math.inf
    return float(row[key])


def classify(summary_rows: list[dict[str, Any]], trace_error_summary: dict[str, Any], tasks: list[str]) -> dict[str, Any]:
    candidate = "fixed_point_temporal_candidate"
    float_ref = "float_fading_memory_reference"
    controls = [
        "lag_only_online_lms_control",
        "zero_temporal_state_ablation",
        "frozen_temporal_state_ablation",
        "shuffled_temporal_state_sham",
        "state_reset_interval_control",
        "shuffled_target_control",
        "no_plasticity_ablation",
    ]
    candidate_geo = geometric([metric(summary_rows, task, candidate) for task in tasks])
    float_geo = geometric([metric(summary_rows, task, float_ref) for task in tasks])
    control_geo = {model: geometric([metric(summary_rows, task, model) for task in tasks]) for model in controls}
    margins = {model: ratio(value, candidate_geo) for model, value in control_geo.items()}
    per_task = {
        task: {
            "candidate_mse": metric(summary_rows, task, candidate),
            "float_reference_mse": metric(summary_rows, task, float_ref),
            "candidate_vs_float_ratio": ratio(metric(summary_rows, task, candidate), metric(summary_rows, task, float_ref)),
            **{f"{model}_mse": metric(summary_rows, task, model) for model in controls},
            **{f"margin_vs_{model}": ratio(metric(summary_rows, task, model), metric(summary_rows, task, candidate)) for model in controls},
        }
        for task in tasks
    }
    fixed_vs_float_ratio = ratio(candidate_geo, float_geo)
    fixed_point_parity_pass = fixed_vs_float_ratio is not None and 0.90 <= fixed_vs_float_ratio <= 1.10
    control_pass = (
        margins["lag_only_online_lms_control"] is not None
        and margins["lag_only_online_lms_control"] >= 1.25
        and margins["zero_temporal_state_ablation"] is not None
        and margins["zero_temporal_state_ablation"] >= 1.25
        and margins["frozen_temporal_state_ablation"] is not None
        and margins["frozen_temporal_state_ablation"] >= 1.10
        and margins["shuffled_temporal_state_sham"] is not None
        and margins["shuffled_temporal_state_sham"] >= 1.25
        and margins["state_reset_interval_control"] is not None
        and margins["state_reset_interval_control"] >= 1.25
        and margins["shuffled_target_control"] is not None
        and margins["shuffled_target_control"] >= 1.25
        and margins["no_plasticity_ablation"] is not None
        and margins["no_plasticity_ablation"] >= 2.0
    )
    trace_error_pass = (
        trace_error_summary["selected_max_abs_error"] <= 0.01
        and trace_error_summary["selected_mean_abs_error"] <= 0.003
        and trace_error_summary["selected_saturation_count"] == 0
    )
    range_refinement_supported = (
        trace_error_summary["conservative_saturation_count"] > 0
        and trace_error_summary["selected_saturation_count"] == 0
    )
    pass_all = bool(fixed_point_parity_pass and control_pass and trace_error_pass and range_refinement_supported)
    if pass_all:
        outcome = "fixed_point_temporal_reference_ready_for_source_audit"
        recommendation = "Proceed to native temporal source/runtime implementation and local C host tests; do not upload hardware until the source audit passes."
    else:
        outcome = "fixed_point_temporal_reference_not_ready"
        recommendation = "Do not implement hardware path; inspect trace range, fixed-point error, or control separation."
    return {
        "outcome": outcome,
        "recommendation": recommendation,
        "candidate_geomean_mse": candidate_geo,
        "float_reference_geomean_mse": float_geo,
        "fixed_vs_float_ratio": fixed_vs_float_ratio,
        "fixed_point_parity_pass": bool(fixed_point_parity_pass),
        "control_geomean_mse": control_geo,
        "control_margins_vs_candidate": margins,
        "control_pass": bool(control_pass),
        "trace_error_pass": bool(trace_error_pass),
        "range_refinement_supported": bool(range_refinement_supported),
        "trace_error_summary": trace_error_summary,
        "per_task": per_task,
        "claim": "local fixed-point seven-EMA temporal reference parity" if pass_all else "no promoted claim from this tier",
        "nonclaims": [
            "not C runtime implementation",
            "not SpiNNaker hardware evidence",
            "not speedup evidence",
            "not multi-chip scaling",
            "not nonlinear recurrence",
            "not universal benchmark superiority",
            "not language, planning, AGI, or ASI",
        ],
    }


def summarize_trace_errors(error_rows: list[dict[str, Any]]) -> dict[str, Any]:
    selected = [row for row in error_rows if row["variant"] == "selected_trace_bound"]
    conservative = [row for row in error_rows if row["variant"] == "conservative_trace_bound_1"]
    return {
        "selected_max_abs_error": max(float(row["max_abs_error"]) for row in selected),
        "selected_mean_abs_error": mean([float(row["mean_abs_error"]) for row in selected]),
        "selected_p95_abs_error": max(float(row["p95_abs_error"]) for row in selected),
        "selected_saturation_count": sum(int(row["saturation_count"]) for row in selected),
        "selected_input_clip_count": sum(int(row["input_clip_count"]) for row in selected),
        "conservative_max_abs_error": max(float(row["max_abs_error"]) for row in conservative),
        "conservative_mean_abs_error": mean([float(row["mean_abs_error"]) for row in conservative]),
        "conservative_saturation_count": sum(int(row["saturation_count"]) for row in conservative),
    }


def write_report(output_dir: Path, payload: dict[str, Any]) -> None:
    c = payload["classification"]
    lines = [
        "# Tier 4.31b Native Temporal-Substrate Local Fixed-Point Reference",
        "",
        f"- Generated: `{payload['generated_at_utc']}`",
        f"- Status: **{payload['status'].upper()}**",
        f"- Criteria: `{payload['criteria_passed']}/{payload['criteria_total']}`",
        f"- Outcome: `{c['outcome']}`",
        "",
        "## Claim Boundary",
        "",
        payload["claim_boundary"],
        "",
        "## Result",
        "",
        f"- Fixed-point candidate geomean MSE: `{c['candidate_geomean_mse']}`",
        f"- Float fading-memory reference geomean MSE: `{c['float_reference_geomean_mse']}`",
        f"- Fixed/float ratio: `{c['fixed_vs_float_ratio']}`",
        f"- Selected max abs feature error: `{c['trace_error_summary']['selected_max_abs_error']}`",
        f"- Selected mean abs feature error: `{c['trace_error_summary']['selected_mean_abs_error']}`",
        f"- Selected saturation count: `{c['trace_error_summary']['selected_saturation_count']}`",
        f"- Conservative ±1 saturation count: `{c['trace_error_summary']['conservative_saturation_count']}`",
        "",
        "## Control Margins",
        "",
        "| Control | Geomean MSE | Margin vs candidate |",
        "| --- | ---: | ---: |",
    ]
    for model, value in c["control_geomean_mse"].items():
        lines.append(f"| `{model}` | {value} | {c['control_margins_vs_candidate'][model]} |")
    lines.extend(
        [
            "",
            "## Per-Task Metrics",
            "",
            "| Task | Candidate MSE | Float reference MSE | Lag margin | Frozen margin | Shuffled margin |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for task, values in c["per_task"].items():
        lines.append(
            f"| {task} | {values['candidate_mse']} | {values['float_reference_mse']} | "
            f"{values['margin_vs_lag_only_online_lms_control']} | "
            f"{values['margin_vs_frozen_temporal_state_ablation']} | "
            f"{values['margin_vs_shuffled_temporal_state_sham']} |"
        )
    lines.extend(
        [
            "",
            "## Range Refinement",
            "",
            "Tier 4.31a used a conservative initial trace clip in the equation sketch. "
            "Tier 4.31b documents that a ±2 trace bound preserves the compact state "
            "budget while removing saturation on the canonical temporal diagnostics. "
            "This is a local-reference refinement before C implementation, not a "
            "hardware claim.",
            "",
            "## Criteria",
            "",
            "| Criterion | Value | Rule | Pass |",
            "| --- | --- | --- | --- |",
        ]
    )
    for item in payload["criteria"]:
        value = json.dumps(json_safe(item["value"]), sort_keys=True) if isinstance(item["value"], (dict, list, tuple)) else str(item["value"])
        lines.append(f"| {item['name']} | `{value}` | {item['rule']} | {'yes' if item['passed'] else 'no'} |")
    lines.extend(["", "## Nonclaims", ""])
    for item in c["nonclaims"]:
        lines.append(f"- {item}")
    lines.append("")
    (output_dir / "tier4_31b_report.md").write_text("\n".join(lines), encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    tasks = parse_csv(args.tasks)
    seeds = parse_seeds(args)
    rows: list[dict[str, Any]] = []
    timeseries: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    trace_errors: list[dict[str, Any]] = []
    trace_rows: list[dict[str, Any]] = []
    for seed in seeds:
        for task_name in tasks:
            task_rows, task_timeseries, task_diagnostics, task_errors, task_trace = run_one_task(task_name, seed, args)
            rows.extend(task_rows)
            timeseries.extend(task_timeseries)
            diagnostics.append(task_diagnostics)
            trace_errors.extend(task_errors)
            trace_rows.extend(task_trace)
    models = sorted({row["model"] for row in rows})
    summary_rows, aggregate_rows, aggregate_summary = summarize(rows, tasks, models, seeds)
    trace_error_summary = summarize_trace_errors(trace_errors)
    classification = classify(summary_rows, trace_error_summary, tasks)
    tier431a = load_json(TIER431A_RESULTS) if TIER431A_RESULTS.exists() else {}
    tier519c = load_json(TIER519C_RESULTS) if TIER519C_RESULTS.exists() else {}
    criteria = [
        criterion("runner revision current", RUNNER_REVISION, "expected current source", RUNNER_REVISION.endswith("_0001")),
        criterion("Tier 4.31a readiness exists", str(TIER431A_RESULTS), "exists", TIER431A_RESULTS.exists()),
        criterion("Tier 4.31a readiness passed", tier431a.get("status"), "== pass", tier431a.get("status") == "pass"),
        criterion("Tier 5.19c reference exists", str(TIER519C_RESULTS), "exists", TIER519C_RESULTS.exists()),
        criterion("Tier 5.19c reference passed", tier519c.get("status"), "== pass", tier519c.get("status") == "pass"),
        criterion("all temporal-memory tasks included", sorted(TEMPORAL_MEMORY_TASKS), "subset of tasks", TEMPORAL_MEMORY_TASKS.issubset(set(tasks))),
        criterion("all model rows completed", f"{sum(row['status'] == 'pass' for row in rows)}/{len(rows)}", "all pass", all(row["status"] == "pass" for row in rows)),
        criterion("trace count matches 4.31a", args.temporal_timescales, "7 timescales", len(parse_timescales(args.temporal_timescales)) == 7),
        criterion("fixed-point parity passes", classification["fixed_point_parity_pass"], "fixed/float geomean ratio within [0.90, 1.10]", bool(classification["fixed_point_parity_pass"])),
        criterion("trace error bound passes", classification["trace_error_pass"], "max<=0.01 mean<=0.003 saturation=0", bool(classification["trace_error_pass"])),
        criterion("range refinement supported", classification["range_refinement_supported"], "conservative saturates and selected does not", bool(classification["range_refinement_supported"])),
        criterion("control suite passes", classification["control_pass"], "all destructive controls separate", bool(classification["control_pass"])),
        criterion("lag-only remains weaker", classification["control_margins_vs_candidate"].get("lag_only_online_lms_control"), ">= 1.25", (classification["control_margins_vs_candidate"].get("lag_only_online_lms_control") or 0.0) >= 1.25),
        criterion("hidden recurrence remains excluded", "fading_only fixed-point EMA", "no hidden/recurrent features", True),
        criterion("no EBRAINS package prepared", "local-reference only", "no ebrains_jobs output", True),
        criterion("next step remains source/local before hardware", "Tier 4.31c source/runtime implementation + local C host tests", "not hardware upload yet", True),
    ]
    status = "pass" if all(item["passed"] for item in criteria) else "fail"
    failure_reason = "" if status == "pass" else "Failed criteria: " + ", ".join(item["name"] for item in criteria if not item["passed"])
    payload = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "status": status,
        "failure_reason": failure_reason,
        "output_dir": str(output_dir),
        "runtime_seconds": time.perf_counter() - started,
        "tasks": tasks,
        "seeds": seeds,
        "length": int(args.length),
        "horizon": int(args.horizon),
        "history": int(args.history),
        "temporal_timescales": parse_timescales(args.temporal_timescales),
        "trace_bound": float(args.trace_bound),
        "input_bound": float(args.input_bound),
        "state_reset_interval": int(args.state_reset_interval),
        "criteria": criteria,
        "criteria_passed": sum(1 for item in criteria if item["passed"]),
        "criteria_total": len(criteria),
        "classification": classification,
        "summary_rows": summary_rows,
        "aggregate_rows": aggregate_rows,
        "aggregate_summary": aggregate_summary,
        "trace_error_summary": trace_error_summary,
        "diagnostics": diagnostics,
        "claim_boundary": (
            "Tier 4.31b is local fixed-point reference/parity evidence only. A "
            "pass supports C/runtime implementation work for the named seven-EMA "
            "fading-memory temporal subset. It does not prove C implementation, "
            "SpiNNaker hardware transfer, speedup, multi-chip scaling, nonlinear "
            "recurrence, universal benchmark superiority, language, planning, AGI, "
            "or ASI."
        ),
        "next_step": {
            "tier": "Tier 4.31c - Native Temporal-Substrate Source/Runtime Implementation",
            "required_work": [
                "add versioned temporal state structs/counters to the C runtime",
                "add local C host tests matching the fixed-point mirror",
                "verify compact readback schema and command-code collisions",
                "run source audit before any EBRAINS package",
            ],
        },
    }
    write_json(output_dir / "tier4_31b_results.json", payload)
    write_csv(
        output_dir / "tier4_31b_summary.csv",
        summary_rows,
        ["task", "model", "status", "seed_count", "mse_mean", "mse_median", "mse_std", "mse_worst", "nmse_mean", "tail_mse_mean", "test_corr_mean"],
    )
    write_csv(output_dir / "tier4_31b_aggregate.csv", aggregate_rows, ["task", "model", "seed", "status", "geomean_mse", "geomean_nmse"])
    write_csv(output_dir / "tier4_31b_trace_errors.csv", trace_errors)
    write_csv(output_dir / "tier4_31b_trace_readback_mirror.csv", trace_rows[: min(len(trace_rows), int(args.max_trace_rows))])
    write_csv(output_dir / "tier4_31b_timeseries.csv", timeseries, ["task", "seed", "model", "step", "split", "observed", "target", "prediction", "squared_error"])
    write_json(output_dir / "tier4_31b_diagnostics.json", {"diagnostics": diagnostics})
    write_report(output_dir, payload)
    manifest = {
        "tier": TIER,
        "status": status,
        "generated_at_utc": payload["generated_at_utc"],
        "output_dir": str(output_dir),
        "results_json": str(output_dir / "tier4_31b_results.json"),
        "report_md": str(output_dir / "tier4_31b_report.md"),
        "criteria_passed": payload["criteria_passed"],
        "criteria_total": payload["criteria_total"],
        "claim_boundary": payload["claim_boundary"],
    }
    write_json(output_dir / "tier4_31b_latest_manifest.json", manifest)
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=TIER)
    parser.add_argument("--tasks", default=DEFAULT_TASKS)
    parser.add_argument("--seeds", default="42,43,44")
    parser.add_argument("--seed-count", type=int, default=None)
    parser.add_argument("--base-seed", type=int, default=42)
    parser.add_argument("--length", type=int, default=720)
    parser.add_argument("--horizon", type=int, default=8)
    parser.add_argument("--history", type=int, default=12)
    parser.add_argument("--temporal-timescales", default="2,4,8,16,32,64,128")
    parser.add_argument("--temporal-hidden-units", type=int, default=16)
    parser.add_argument("--temporal-recurrent-scale", type=float, default=0.65)
    parser.add_argument("--temporal-input-scale", type=float, default=0.45)
    parser.add_argument("--temporal-hidden-decay", type=float, default=0.72)
    parser.add_argument("--trace-bound", type=float, default=2.0)
    parser.add_argument("--input-bound", type=float, default=3.0)
    parser.add_argument("--state-reset-interval", type=int, default=24)
    parser.add_argument("--readout-lr", type=float, default=0.08)
    parser.add_argument("--readout-decay", type=float, default=1e-5)
    parser.add_argument("--weight-clip", type=float, default=20.0)
    parser.add_argument("--output-clip", type=float, default=3.0)
    parser.add_argument("--max-trace-rows", type=int, default=2048)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    payload = run(args)
    print(f"{TIER}: {payload['status']} ({payload['criteria_passed']}/{payload['criteria_total']} criteria)")
    if payload["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
