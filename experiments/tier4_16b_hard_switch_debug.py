#!/usr/bin/env python3
"""Tier 4.16b hard-switch local debug.

This is a local-only diagnostic for the failed Tier 4.16b
``hard_noisy_switching`` SpiNNaker run. It asks four separate questions:

1. Does full step-mode CRA pass locally on the exact hard-switch task?
2. Does the direct scheduled-input + host-replay bridge pass locally?
3. Does chunking change that bridge relative to step-sized chunks?
4. Do returned hardware traces look like the local chunked bridge?

The output is diagnostic, not canonical hardware evidence.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except Exception as exc:  # pragma: no cover
    plt = None
    MATPLOTLIB_ERROR = str(exc)
else:
    MATPLOTLIB_ERROR = None

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from tier2_learning import (  # noqa: E402
    DEFAULT_AMPLITUDE,
    DEFAULT_DT_SECONDS,
    criterion,
    end_backend,
    load_backend,
    markdown_value,
    pass_fail,
    safe_corr,
    setup_backend,
    write_csv,
    write_json,
)
from tier4_harder_spinnaker_capsule import (  # noqa: E402
    ChunkedHostReplay,
    DEFAULT_HARD_MAX_DELAY,
    DEFAULT_HARD_MAX_SWITCH_INTERVAL,
    DEFAULT_HARD_MIN_DELAY,
    DEFAULT_HARD_MIN_SWITCH_INTERVAL,
    DEFAULT_HARD_NOISE_PROB,
    DEFAULT_HARD_PERIOD,
    DEFAULT_HARD_SENSORY_NOISE_FRACTION,
    DEFAULT_HARD_TAIL_THRESHOLD,
    bin_spiketrains,
    compressed_current_schedule,
    scheduled_currents,
)
from tier4_scaling import mean, min_value, stdev  # noqa: E402
from tier5_cra_failure_analysis import VariantSpec, run_cra_variant  # noqa: E402
from tier5_external_baselines import (  # noqa: E402
    TaskStream,
    hard_noisy_switching_task,
    recovery_steps,
    summarize_rows,
)


TIER = "Tier 4.16b-debug - Hard Noisy Switching Local Root-Cause Diagnostic"
OUTPUT_ROOT = ROOT / "controlled_test_output"
DEFAULT_BACKENDS = "nest,brian2"
DEFAULT_SEEDS = "42,43,44"
DEFAULT_HARDWARE_DIR = (
    OUTPUT_ROOT / "tier4_16_20260427_194526_hard_noisy_switching_3seed_hardware_fail"
)
BOOL_FIELDS = {
    "binned_readback",
    "configured_apoptosis",
    "configured_reproduction",
    "direction_correct",
    "host_replay",
    "same_targets",
    "strict_direction_correct",
    "synthetic_fallback_used",
    "target_signal_nonzero",
    "trading_bridge_present_after_init",
    "trading_bridge_present_any_step",
    "uses_trading_bridge",
}

CRA_DELAYED_020 = VariantSpec(
    "cra_delayed_lr_0_20",
    "delayed_credit_candidate",
    "Tier 5.4 confirmed candidate: stronger matured delayed-credit readout learning.",
    {"learning.delayed_readout_learning_rate": 0.20},
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def parse_csv_list(raw: str) -> list[str]:
    values = [item.strip() for item in raw.replace(";", ",").split(",") if item.strip()]
    if not values:
        raise argparse.ArgumentTypeError("at least one item is required")
    return values


def parse_seeds(raw: str) -> list[int]:
    try:
        return [int(item) for item in parse_csv_list(raw)]
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


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
        f = float(value)
        return None if not math.isfinite(f) else f
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def finite(value: Any) -> float | None:
    try:
        f = float(value)
    except Exception:
        return None
    return f if math.isfinite(f) else None


def boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y"}
    return bool(value)


def parse_record_value(key: str, value: Any) -> Any:
    if key in BOOL_FIELDS:
        return boolish(value)
    if isinstance(value, str) and not value.strip():
        return None
    fval = finite(value)
    return fval if fval is not None else value


def read_csv_records(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as f:
        return [
            {key: parse_record_value(key, value) for key, value in row.items()}
            for row in csv.DictReader(f)
        ]


def row_group_key(row: dict[str, Any]) -> tuple[str, str, int]:
    return (str(row.get("path")), str(row.get("backend_key")), int(float(row.get("seed", 0))))


def build_task(seed: int, args: argparse.Namespace) -> TaskStream:
    return hard_noisy_switching_task(
        steps=args.steps,
        amplitude=args.amplitude,
        seed=seed,
        args=args,
    )


def run_direct_local_mode(
    *,
    task: TaskStream,
    backend_key: str,
    seed: int,
    chunk_size_steps: int,
    args: argparse.Namespace,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    random.seed(seed)
    np.random.seed(seed)
    sim, backend_name = load_backend(backend_key)
    setup_backend(sim, backend_name)
    started = time.perf_counter()
    diagnostics = {
        "synthetic_fallbacks": 0,
        "sim_run_failures": 0,
        "summary_read_failures": 0,
        "scheduled_input_failures": 0,
        "spike_readback_failures": 0,
    }
    rows: list[dict[str, Any]] = []
    spike_bins = np.zeros(task.steps, dtype=int)
    calls = 0
    try:
        if not hasattr(sim, "StepCurrentSource"):
            diagnostics["scheduled_input_failures"] = 1
            raise RuntimeError(f"{backend_name} does not expose StepCurrentSource")
        dt_ms = float(args.dt_seconds) * 1000.0
        currents = scheduled_currents(task, args)
        cell = sim.IF_curr_exp(
            i_offset=0.0,
            tau_m=20.0,
            v_rest=-65.0,
            v_reset=-70.0,
            v_thresh=-55.0,
            tau_refrac=2.0,
            cm=0.25,
        )
        pop = sim.Population(
            int(args.population_size),
            cell,
            label=f"tier4_16b_debug_{backend_key}_{seed}_{chunk_size_steps}",
        )
        pop.record("spikes")
        times, amplitudes = compressed_current_schedule(currents, dt_ms)
        source = sim.StepCurrentSource(times=times, amplitudes=amplitudes)
        pop.inject(source)
        replay = ChunkedHostReplay(
            lr=float(args.delayed_readout_lr),
            amplitude=float(args.amplitude),
            population_size=int(args.population_size),
        )
        for start in range(0, task.steps, int(chunk_size_steps)):
            stop = min(task.steps, start + int(chunk_size_steps))
            try:
                sim.run(float(stop - start) * dt_ms)
                calls += 1
            except Exception:
                diagnostics["sim_run_failures"] += 1
                raise
            try:
                data = pop.get_data("spikes", clear=False)
                spiketrains = data.segments[0].spiketrains
                spike_bins = bin_spiketrains(spiketrains, steps=task.steps, dt_ms=dt_ms)
            except Exception:
                diagnostics["summary_read_failures"] += 1
                diagnostics["spike_readback_failures"] += 1
                raise
            for step in range(start, stop):
                row = replay.step(task=task, step=step, spike_count=int(spike_bins[step]))
                row.update(
                    {
                        "tier": TIER,
                        "task": task.name,
                        "path": "direct_step_host_replay"
                        if int(chunk_size_steps) == 1
                        else "direct_chunked_host_replay",
                        "backend_key": backend_key,
                        "backend": backend_name,
                        "seed": int(seed),
                        "runtime_mode": "step" if int(chunk_size_steps) == 1 else "chunked",
                        "learning_location": "host",
                        "chunk_size_steps": int(chunk_size_steps),
                        "sim_run_calls": int(calls),
                        "configured_delayed_readout_lr": float(args.delayed_readout_lr),
                        "configured_readout_lr": float(args.readout_lr),
                        "mean_trophic_health": 1.0,
                        "min_trophic_health": 1.0,
                        "max_trophic_health": 1.0,
                        "sim_run_failures": int(diagnostics["sim_run_failures"]),
                        "summary_read_failures": int(diagnostics["summary_read_failures"]),
                        "synthetic_fallbacks": int(diagnostics["synthetic_fallbacks"]),
                    }
                )
                rows.append(row)
    finally:
        try:
            end_backend(sim)
        except Exception:
            pass
    summary = summarize_rows(rows)
    step_spikes = [float(row.get("step_spike_count", 0.0)) for row in rows]
    summary.update(
        {
            "tier": TIER,
            "task": task.name,
            "path": "direct_step_host_replay"
            if int(chunk_size_steps) == 1
            else "direct_chunked_host_replay",
            "backend_key": backend_key,
            "backend": backend_name,
            "seed": int(seed),
            "steps": int(task.steps),
            "population_size": int(args.population_size),
            "runtime_mode": "step" if int(chunk_size_steps) == 1 else "chunked",
            "learning_location": "host",
            "chunk_size_steps": int(chunk_size_steps),
            "sim_run_calls": int(calls),
            "call_reduction_factor": float(task.steps) / float(calls) if calls else None,
            "runtime_seconds": time.perf_counter() - started,
            "total_step_spikes": int(sum(step_spikes)),
            "mean_step_spikes": mean(step_spikes),
            "scheduled_input_mode": "StepCurrentSource",
            "binned_readback": True,
            "host_replay": True,
            "final_mean_readout_weight": float(rows[-1].get("host_replay_weight", 0.0)) if rows else 0.0,
            "task_metadata": task.metadata,
        }
    )
    summary.update(diagnostics)
    return rows, summary


def run_full_cra_step(
    *,
    task: TaskStream,
    backend_key: str,
    seed: int,
    args: argparse.Namespace,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    local_args = argparse.Namespace(**vars(args))
    local_args.backend = backend_key
    local_args.cra_population_size = int(args.population_size)
    local_args.cra_readout_lr = float(args.readout_lr)
    local_args.cra_delayed_readout_lr = float(args.delayed_readout_lr)
    rows, summary = run_cra_variant(task, seed=seed, variant=CRA_DELAYED_020, args=local_args)
    for row in rows:
        row.update(
            {
                "tier": TIER,
                "path": "full_step_cra",
                "backend_key": backend_key,
                "runtime_mode": "step",
                "learning_location": "host",
                "chunk_size_steps": 1,
                "configured_delayed_readout_lr": float(args.delayed_readout_lr),
                "configured_readout_lr": float(args.readout_lr),
            }
        )
    summary.update(
        {
            "tier": TIER,
            "path": "full_step_cra",
            "backend_key": backend_key,
            "runtime_mode": "step",
            "learning_location": "host",
            "chunk_size_steps": 1,
            "sim_run_calls": int(task.steps),
            "call_reduction_factor": 1.0,
        }
    )
    return rows, summary


def load_hardware_rows(hardware_dir: Path, seed: int) -> tuple[list[dict[str, Any]], dict[str, Any]] | None:
    path = hardware_dir / f"spinnaker_hardware_hard_noisy_switching_seed{seed}_timeseries.csv"
    if not path.exists():
        return None
    rows: list[dict[str, Any]] = []
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            parsed: dict[str, Any] = {}
            for key, value in row.items():
                parsed[key] = parse_record_value(key, value)
            parsed.update(
                {
                    "tier": TIER,
                    "path": "returned_hardware_chunked_host_replay",
                    "backend_key": "spinnaker",
                    "backend": "pyNN.spiNNaker",
                    "runtime_mode": "chunked",
                    "learning_location": "host",
                }
            )
            rows.append(parsed)
    summary = summarize_rows(rows)
    step_spikes = [float(row.get("step_spike_count", 0.0) or 0.0) for row in rows]
    summary.update(
        {
            "tier": TIER,
            "task": "hard_noisy_switching",
            "path": "returned_hardware_chunked_host_replay",
            "backend_key": "spinnaker",
            "backend": "pyNN.spiNNaker",
            "seed": int(seed),
            "steps": len(rows),
            "runtime_mode": "chunked",
            "learning_location": "host",
            "chunk_size_steps": int(rows[-1].get("chunk_size_steps", 25)) if rows else 25,
            "sim_run_calls": int(rows[-1].get("sim_run_calls", 0)) if rows else 0,
            "total_step_spikes": int(sum(step_spikes)),
            "mean_step_spikes": mean(step_spikes),
            "runtime_seconds": None,
            "source_csv": str(path),
        }
    )
    return rows, summary


def aggregate_path(summaries: list[dict[str, Any]], *, path: str, backend_key: str | None = None) -> dict[str, Any]:
    rows = [s for s in summaries if s.get("path") == path and (backend_key is None or s.get("backend_key") == backend_key)]
    keys = [
        "all_accuracy",
        "tail_accuracy",
        "early_accuracy",
        "accuracy_improvement",
        "prediction_target_corr",
        "tail_prediction_target_corr",
        "runtime_seconds",
        "evaluation_count",
        "mean_abs_prediction",
        "max_abs_prediction",
        "final_n_alive",
        "max_abs_dopamine",
        "mean_abs_dopamine",
        "total_step_spikes",
        "mean_step_spikes",
    ]
    out: dict[str, Any] = {
        "path": path,
        "backend_key": backend_key or "all",
        "runs": len(rows),
        "seeds": [int(s.get("seed")) for s in rows if s.get("seed") is not None],
    }
    for key in keys:
        vals = [s.get(key) for s in rows]
        out[f"{key}_mean"] = mean(vals)
        out[f"{key}_std"] = stdev(vals)
        out[f"{key}_min"] = min_value(vals)
        numeric = [finite(v) for v in vals]
        numeric = [v for v in numeric if v is not None]
        out[f"{key}_max"] = max(numeric) if numeric else None
    return out


def comparison_row(
    *,
    left_name: str,
    left_rows: list[dict[str, Any]],
    left_summary: dict[str, Any],
    right_name: str,
    right_rows: list[dict[str, Any]],
    right_summary: dict[str, Any],
    comparison_type: str,
) -> dict[str, Any]:
    left_pred = [float(r.get("colony_prediction", 0.0) or 0.0) for r in left_rows]
    right_pred = [float(r.get("colony_prediction", 0.0) or 0.0) for r in right_rows]
    left_spikes = [float(r.get("step_spike_count", 0.0) or 0.0) for r in left_rows]
    right_spikes = [float(r.get("step_spike_count", 0.0) or 0.0) for r in right_rows]
    left_target = [float(r.get("target_signal_horizon", 0.0) or 0.0) for r in left_rows]
    right_target = [float(r.get("target_signal_horizon", 0.0) or 0.0) for r in right_rows]
    n = min(len(left_pred), len(right_pred))
    pred_delta = [right_pred[i] - left_pred[i] for i in range(n)]
    spike_delta = [right_spikes[i] - left_spikes[i] for i in range(n)]
    return {
        "comparison_type": comparison_type,
        "left": left_name,
        "right": right_name,
        "seed": left_summary.get("seed", right_summary.get("seed")),
        "backend_key": left_summary.get("backend_key", right_summary.get("backend_key")),
        "same_targets": left_target == right_target,
        "left_tail_accuracy": left_summary.get("tail_accuracy"),
        "right_tail_accuracy": right_summary.get("tail_accuracy"),
        "tail_accuracy_delta_right_minus_left": (
            None
            if left_summary.get("tail_accuracy") is None or right_summary.get("tail_accuracy") is None
            else float(right_summary.get("tail_accuracy")) - float(left_summary.get("tail_accuracy"))
        ),
        "left_all_accuracy": left_summary.get("all_accuracy"),
        "right_all_accuracy": right_summary.get("all_accuracy"),
        "all_accuracy_delta_right_minus_left": (
            None
            if left_summary.get("all_accuracy") is None or right_summary.get("all_accuracy") is None
            else float(right_summary.get("all_accuracy")) - float(left_summary.get("all_accuracy"))
        ),
        "prediction_corr": safe_corr(left_pred[:n], right_pred[:n]) if n else None,
        "max_abs_prediction_delta": max([abs(x) for x in pred_delta], default=None),
        "spike_corr": safe_corr(left_spikes[:n], right_spikes[:n]) if n else None,
        "max_abs_step_spike_delta": max([abs(x) for x in spike_delta], default=None),
        "left_total_spikes": left_summary.get("total_step_spikes"),
        "right_total_spikes": right_summary.get("total_step_spikes"),
    }


def build_decision(
    *,
    path_aggs: list[dict[str, Any]],
    comparisons: list[dict[str, Any]],
    args: argparse.Namespace,
) -> dict[str, Any]:
    def agg(path: str, backend: str | None = None) -> dict[str, Any]:
        return next((r for r in path_aggs if r["path"] == path and r["backend_key"] == (backend or "all")), {})

    full = agg("full_step_cra")
    direct_step = agg("direct_step_host_replay")
    direct_chunk = agg("direct_chunked_host_replay")
    hardware = agg("returned_hardware_chunked_host_replay")
    bridge_comps = [r for r in comparisons if r["comparison_type"] == "direct_step_vs_chunked"]
    hardware_comps = [r for r in comparisons if r["comparison_type"] == "local_chunked_vs_hardware"]
    bridge_tail_deltas = [abs(float(r.get("tail_accuracy_delta_right_minus_left") or 0.0)) for r in bridge_comps]
    hardware_tail_deltas = [abs(float(r.get("tail_accuracy_delta_right_minus_left") or 0.0)) for r in hardware_comps]
    full_tail_min = finite(full.get("tail_accuracy_min"))
    direct_chunk_tail_min = finite(direct_chunk.get("tail_accuracy_min"))
    hardware_tail_min = finite(hardware.get("tail_accuracy_min"))
    threshold = float(args.hard_tail_threshold)

    if full_tail_min is not None and full_tail_min < threshold:
        classification = "cra_dynamics_or_task_failure"
        next_step = "debug CRA hard-switch learning dynamics before hardware or C-runtime work"
    elif direct_chunk_tail_min is not None and direct_chunk_tail_min < threshold:
        classification = "chunked_host_bridge_learning_failure"
        next_step = "repair host-replay bridge or macro delayed-credit path before hardware rerun"
    elif hardware_tail_min is not None and hardware_tail_min < threshold:
        classification = "hardware_transfer_or_timing_failure"
        next_step = "compare spike/readback timing and run one repaired hardware probe only"
    else:
        classification = "no_local_failure_reproduced"
        next_step = "inspect hardware metrics and thresholds before rerunning one seed"

    return {
        "classification": classification,
        "next_step": next_step,
        "hard_tail_threshold": threshold,
        "full_step_cra_tail_min": full_tail_min,
        "direct_step_host_tail_min": finite(direct_step.get("tail_accuracy_min")),
        "direct_chunked_host_tail_min": direct_chunk_tail_min,
        "hardware_tail_min": hardware_tail_min,
        "max_bridge_tail_delta": max(bridge_tail_deltas) if bridge_tail_deltas else None,
        "max_hardware_tail_delta": max(hardware_tail_deltas) if hardware_tail_deltas else None,
        "bridge_chunking_changes_accuracy": (
            max(bridge_tail_deltas) > args.bridge_tail_delta_tolerance if bridge_tail_deltas else None
        ),
        "hardware_differs_from_local_chunked": (
            max(hardware_tail_deltas) > args.hardware_tail_delta_tolerance if hardware_tail_deltas else None
        ),
    }


def plot_summary(path_aggs: list[dict[str, Any]], output_path: Path) -> None:
    if plt is None or not path_aggs:
        return
    rows = [r for r in path_aggs if r["backend_key"] == "all"]
    labels = [r["path"].replace("_", "\n") for r in rows]
    tail = [float(r.get("tail_accuracy_mean") or 0.0) for r in rows]
    corr = [float(r.get("tail_prediction_target_corr_mean") or 0.0) for r in rows]
    spikes = [float(r.get("total_step_spikes_mean") or 0.0) for r in rows]
    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    axes[0].bar(labels, tail, color="#1f6feb")
    axes[0].axhline(0.5, color="black", lw=0.8, linestyle="--")
    axes[0].set_title("Tail accuracy")
    axes[0].set_ylim(0, 1.05)
    axes[1].bar(labels, corr, color="#2f855a")
    axes[1].axhline(0.0, color="black", lw=0.8)
    axes[1].set_title("Tail correlation")
    axes[2].bar(labels, spikes, color="#8250df")
    axes[2].set_title("Mean total spikes")
    for ax in axes:
        ax.grid(axis="y", alpha=0.25)
        ax.tick_params(axis="x", labelrotation=35)
    fig.suptitle("Tier 4.16b-debug Hard Noisy Switching")
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def write_report(
    *,
    path: Path,
    output_dir: Path,
    status: str,
    failure_reason: str,
    criteria: list[dict[str, Any]],
    decision: dict[str, Any],
    path_aggs: list[dict[str, Any]],
    comparisons: list[dict[str, Any]],
    artifacts: dict[str, str],
) -> None:
    lines = [
        "# Tier 4.16b Hard-Switch Local Debug Findings",
        "",
        f"- Generated: `{utc_now()}`",
        f"- Status: **{status.upper()}**",
        f"- Output directory: `{output_dir}`",
        "",
        "This is a local-only root-cause diagnostic for the failed Tier 4.16b",
        "`hard_noisy_switching` hardware run. It is not canonical hardware evidence.",
        "",
        "## Decision",
        "",
        f"- classification: `{decision.get('classification')}`",
        f"- next_step: `{decision.get('next_step')}`",
        f"- full_step_cra_tail_min: `{markdown_value(decision.get('full_step_cra_tail_min'))}`",
        f"- direct_chunked_host_tail_min: `{markdown_value(decision.get('direct_chunked_host_tail_min'))}`",
        f"- hardware_tail_min: `{markdown_value(decision.get('hardware_tail_min'))}`",
        f"- max_bridge_tail_delta: `{markdown_value(decision.get('max_bridge_tail_delta'))}`",
        f"- max_hardware_tail_delta: `{markdown_value(decision.get('max_hardware_tail_delta'))}`",
        "",
    ]
    if failure_reason:
        lines.extend(["## Failure", "", failure_reason, ""])
    lines.extend(
        [
            "## Path Aggregates",
            "",
            "| Path | Backend | Runs | Tail Mean | Tail Min | All Mean | Corr Mean | Spikes Mean | Runtime Mean |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in path_aggs:
        lines.append(
            "| "
            f"`{row['path']}` | `{row['backend_key']}` | {markdown_value(row.get('runs'))} | "
            f"{markdown_value(row.get('tail_accuracy_mean'))} | {markdown_value(row.get('tail_accuracy_min'))} | "
            f"{markdown_value(row.get('all_accuracy_mean'))} | {markdown_value(row.get('tail_prediction_target_corr_mean'))} | "
            f"{markdown_value(row.get('total_step_spikes_mean'))} | {markdown_value(row.get('runtime_seconds_mean'))} |"
        )
    lines.extend(
        [
            "",
            "## Key Comparisons",
            "",
            "| Type | Left | Right | Seed | Backend | Tail Delta | Prediction Corr | Spike Corr |",
            "| --- | --- | --- | ---: | --- | ---: | ---: | ---: |",
        ]
    )
    for row in comparisons:
        lines.append(
            "| "
            f"`{row.get('comparison_type')}` | `{row.get('left')}` | `{row.get('right')}` | "
            f"{markdown_value(row.get('seed'))} | `{row.get('backend_key')}` | "
            f"{markdown_value(row.get('tail_accuracy_delta_right_minus_left'))} | "
            f"{markdown_value(row.get('prediction_corr'))} | {markdown_value(row.get('spike_corr'))} |"
        )
    lines.extend(["", "## Criteria", "", "| Criterion | Value | Rule | Pass |", "| --- | --- | --- | --- |"])
    for item in criteria:
        lines.append(
            f"| {item['name']} | {markdown_value(item['value'])} | {item['operator']} {markdown_value(item['threshold'])} | {'yes' if item['passed'] else 'no'} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "- If full step-mode CRA fails locally, the hard-switch weakness is not primarily a SpiNNaker transfer bug.",
            "- If direct step and direct chunked match, chunking itself is not the primary failure.",
            "- If local chunked and returned hardware are similar, the returned hardware failure is reproducing the local bridge behavior.",
            "- Architecture fixes should be added one at a time only after this diagnosis is accepted.",
            "",
            "## Artifacts",
            "",
        ]
    )
    for key, value in artifacts.items():
        lines.append(f"- `{key}`: `{value}`")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def recompute_existing(args: argparse.Namespace) -> int:
    existing_dir = args.recompute_existing.resolve()
    manifest_path = existing_dir / "tier4_16b_debug_results.json"
    timeseries_path = existing_dir / "tier4_16b_debug_timeseries.csv"
    old_summary_path = existing_dir / "tier4_16b_debug_summary.csv"
    old_failures_path = existing_dir / "tier4_16b_debug_failures.csv"
    if not timeseries_path.exists():
        raise FileNotFoundError(f"missing existing timeseries: {timeseries_path}")

    manifest: dict[str, Any] = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    summary_meta = manifest.get("summary", {}) if isinstance(manifest.get("summary", {}), dict) else {}

    backends = [str(item) for item in summary_meta.get("backends", parse_csv_list(args.backends))]
    seeds = [int(seed) for seed in summary_meta.get("seeds", args.seeds)]
    args.steps = int(summary_meta.get("steps", args.steps))
    args.chunk_size_steps = int(summary_meta.get("chunk_size_steps", args.chunk_size_steps))
    if summary_meta.get("hardware_dir"):
        args.hardware_dir = Path(summary_meta["hardware_dir"])

    output_dir = args.output_dir or existing_dir.with_name(f"{existing_dir.name}_corrected")
    output_dir.mkdir(parents=True, exist_ok=True)

    all_rows = read_csv_records(timeseries_path)
    rows_by_key: dict[tuple[str, str, int], list[dict[str, Any]]] = {}
    for row in all_rows:
        if row.get("path") in (None, "") or row.get("backend_key") in (None, "") or row.get("seed") in (None, ""):
            continue
        rows_by_key.setdefault(row_group_key(row), []).append(row)

    old_summaries: dict[tuple[str, str, int], dict[str, Any]] = {}
    if old_summary_path.exists():
        for row in read_csv_records(old_summary_path):
            if row.get("path") and row.get("backend_key") and row.get("seed") not in (None, ""):
                old_summaries[row_group_key(row)] = row

    summaries: list[dict[str, Any]] = []
    summaries_by_key: dict[tuple[str, str, int], dict[str, Any]] = {}
    for key, rows in sorted(rows_by_key.items(), key=lambda item: (item[0][0], item[0][1], item[0][2])):
        path_name, backend_key, seed = key
        prior = dict(old_summaries.get(key, {}))
        summary = dict(prior)
        summary.update(summarize_rows(rows))
        last = rows[-1] if rows else {}
        for field in [
            "tier",
            "task",
            "backend",
            "runtime_mode",
            "learning_location",
            "chunk_size_steps",
            "sim_run_calls",
            "configured_horizon_bars",
            "configured_readout_lr",
            "configured_delayed_readout_lr",
            "task_metadata",
            "variant",
            "variant_group",
        ]:
            if summary.get(field) in (None, "") and last.get(field) not in (None, ""):
                summary[field] = last.get(field)
        spike_values = [finite(row.get("step_spike_count")) for row in rows]
        spike_values = [value for value in spike_values if value is not None]
        summary.update(
            {
                "tier": TIER,
                "path": path_name,
                "backend_key": backend_key,
                "seed": int(seed),
                "steps": len(rows),
            }
        )
        if spike_values:
            summary["total_step_spikes"] = int(sum(spike_values))
            summary["mean_step_spikes"] = mean(spike_values)
        summaries.append(summary)
        summaries_by_key[key] = summary

    failures = read_csv_records(old_failures_path) if old_failures_path.exists() else []

    comparisons: list[dict[str, Any]] = []
    for seed in seeds:
        for backend_key in backends:
            step_key = ("direct_step_host_replay", backend_key, seed)
            chunk_key = ("direct_chunked_host_replay", backend_key, seed)
            full_key = ("full_step_cra", backend_key, seed)
            if step_key in rows_by_key and chunk_key in rows_by_key:
                comparisons.append(
                    comparison_row(
                        left_name="direct_step_host_replay",
                        left_rows=rows_by_key[step_key],
                        left_summary=summaries_by_key[step_key],
                        right_name="direct_chunked_host_replay",
                        right_rows=rows_by_key[chunk_key],
                        right_summary=summaries_by_key[chunk_key],
                        comparison_type="direct_step_vs_chunked",
                    )
                )
            if full_key in rows_by_key and chunk_key in rows_by_key:
                comparisons.append(
                    comparison_row(
                        left_name="full_step_cra",
                        left_rows=rows_by_key[full_key],
                        left_summary=summaries_by_key[full_key],
                        right_name="direct_chunked_host_replay",
                        right_rows=rows_by_key[chunk_key],
                        right_summary=summaries_by_key[chunk_key],
                        comparison_type="full_cra_vs_direct_chunked",
                    )
                )
            hw_key = ("returned_hardware_chunked_host_replay", "spinnaker", seed)
            if hw_key in rows_by_key and chunk_key in rows_by_key:
                comparisons.append(
                    comparison_row(
                        left_name="direct_chunked_host_replay",
                        left_rows=rows_by_key[chunk_key],
                        left_summary=summaries_by_key[chunk_key],
                        right_name="returned_hardware_chunked_host_replay",
                        right_rows=rows_by_key[hw_key],
                        right_summary=summaries_by_key[hw_key],
                        comparison_type="local_chunked_vs_hardware",
                    )
                )

    path_aggs: list[dict[str, Any]] = []
    paths = [
        "full_step_cra",
        "direct_step_host_replay",
        "direct_chunked_host_replay",
        "returned_hardware_chunked_host_replay",
    ]
    for path_name in paths:
        path_aggs.append(aggregate_path(summaries, path=path_name))
        for backend_key in ([*backends] if path_name != "returned_hardware_chunked_host_replay" else ["spinnaker"]):
            path_aggs.append(aggregate_path(summaries, path=path_name, backend_key=backend_key))

    decision = build_decision(path_aggs=path_aggs, comparisons=comparisons, args=args)
    expected_local_runs = len(seeds) * len(backends) * 3
    expected_hardware_runs = len(seeds)
    criteria = [
        criterion(
            "corrected boolean parser applied",
            True,
            "==",
            True,
            True,
        ),
        criterion(
            "full diagnostic matrix completed",
            len([s for s in summaries if s.get("path") != "returned_hardware_chunked_host_replay"]),
            "==",
            expected_local_runs,
            len([s for s in summaries if s.get("path") != "returned_hardware_chunked_host_replay"]) == expected_local_runs,
        ),
        criterion(
            "hardware traces loaded",
            len([s for s in summaries if s.get("path") == "returned_hardware_chunked_host_replay"]),
            "==",
            expected_hardware_runs,
            len([s for s in summaries if s.get("path") == "returned_hardware_chunked_host_replay"]) == expected_hardware_runs,
        ),
        criterion("no execution exceptions", len(failures), "==", 0, len(failures) == 0),
        criterion("failure class assigned", bool(decision.get("classification")), "==", True, bool(decision.get("classification"))),
        criterion(
            "direct step/chunked comparison produced",
            len([c for c in comparisons if c["comparison_type"] == "direct_step_vs_chunked"]),
            "==",
            len(seeds) * len(backends),
            len([c for c in comparisons if c["comparison_type"] == "direct_step_vs_chunked"]) == len(seeds) * len(backends),
        ),
        criterion(
            "hardware/local comparison produced",
            len([c for c in comparisons if c["comparison_type"] == "local_chunked_vs_hardware"]),
            "==",
            len(seeds) * len(backends),
            len([c for c in comparisons if c["comparison_type"] == "local_chunked_vs_hardware"]) == len(seeds) * len(backends),
        ),
    ]
    status, failure_reason = pass_fail(criteria)

    summary_csv = output_dir / "tier4_16b_debug_summary.csv"
    path_summary_csv = output_dir / "tier4_16b_debug_path_summary.csv"
    comparisons_csv = output_dir / "tier4_16b_debug_comparisons.csv"
    timeseries_csv = output_dir / "tier4_16b_debug_timeseries.csv"
    failures_csv = output_dir / "tier4_16b_debug_failures.csv"
    report_md = output_dir / "tier4_16b_debug_report.md"
    manifest_json = output_dir / "tier4_16b_debug_results.json"
    plot_png = output_dir / "tier4_16b_debug_summary.png"

    write_csv(summary_csv, summaries)
    write_csv(path_summary_csv, path_aggs)
    write_csv(comparisons_csv, comparisons)
    write_csv(timeseries_csv, all_rows)
    if failures:
        write_csv(failures_csv, failures)
    plot_summary(path_aggs, plot_png)

    artifacts = {
        "source_existing_output_dir": str(existing_dir),
        "summary_csv": str(summary_csv),
        "path_summary_csv": str(path_summary_csv),
        "comparisons_csv": str(comparisons_csv),
        "timeseries_csv": str(timeseries_csv),
        "report_md": str(report_md),
        "manifest_json": str(manifest_json),
    }
    if failures:
        artifacts["failures_csv"] = str(failures_csv)
    if plot_png.exists():
        artifacts["summary_png"] = str(plot_png)

    write_json(
        manifest_json,
        {
            "generated_at_utc": utc_now(),
            "tier": TIER,
            "status": status,
            "failure_reason": failure_reason,
            "summary": {
                "classification": decision.get("classification"),
                "next_step": decision.get("next_step"),
                "backends": backends,
                "seeds": seeds,
                "steps": args.steps,
                "chunk_size_steps": args.chunk_size_steps,
                "hardware_dir": str(args.hardware_dir),
                "recomputed_from": str(existing_dir),
                "corrected_fields": sorted(BOOL_FIELDS),
                "failures": failures,
            },
            "decision": decision,
            "criteria": criteria,
            "path_summaries": path_aggs,
            "comparisons": comparisons,
            "run_summaries": summaries,
            "artifacts": artifacts,
            "matplotlib_error": MATPLOTLIB_ERROR,
        },
    )
    write_report(
        path=report_md,
        output_dir=output_dir,
        status=status,
        failure_reason=failure_reason,
        criteria=criteria,
        decision=decision,
        path_aggs=path_aggs,
        comparisons=comparisons,
        artifacts=artifacts,
    )
    write_json(
        OUTPUT_ROOT / "tier4_16b_debug_latest_manifest.json",
        {
            "generated_at_utc": utc_now(),
            "manifest": str(manifest_json),
            "report": str(report_md),
            "summary_csv": str(summary_csv),
            "output_dir": str(output_dir),
            "status": status,
            "canonical": False,
            "claim": "Tier 4.16b local hard-switch root-cause diagnostic; corrected boolean parsing; not hardware success evidence.",
            "classification": decision.get("classification"),
            "next_step": decision.get("next_step"),
        },
    )
    print(
        json.dumps(
            {
                "status": status,
                "output_dir": str(output_dir),
                "classification": decision.get("classification"),
                "next_step": decision.get("next_step"),
            },
            indent=2,
        )
    )
    return 0 if status == "pass" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Tier 4.16b hard-switch local debug.")
    parser.add_argument("--backends", default=DEFAULT_BACKENDS)
    parser.add_argument("--seeds", type=parse_seeds, default=parse_seeds(DEFAULT_SEEDS))
    parser.add_argument("--steps", type=int, default=1200)
    parser.add_argument("--chunk-size-steps", type=int, default=25)
    parser.add_argument("--population-size", type=int, default=8)
    parser.add_argument("--amplitude", type=float, default=DEFAULT_AMPLITUDE)
    parser.add_argument("--dt-seconds", type=float, default=DEFAULT_DT_SECONDS)
    parser.add_argument("--readout-lr", type=float, default=0.10)
    parser.add_argument("--delayed-readout-lr", type=float, default=0.20)
    parser.add_argument("--base-current-na", type=float, default=1.4)
    parser.add_argument("--cue-current-gain-na", type=float, default=0.2)
    parser.add_argument("--min-current-na", type=float, default=0.0)
    parser.add_argument("--hard-period", type=int, default=DEFAULT_HARD_PERIOD)
    parser.add_argument("--min-delay", type=int, default=DEFAULT_HARD_MIN_DELAY)
    parser.add_argument("--max-delay", type=int, default=DEFAULT_HARD_MAX_DELAY)
    parser.add_argument("--noise-prob", type=float, default=DEFAULT_HARD_NOISE_PROB)
    parser.add_argument("--sensory-noise-fraction", type=float, default=DEFAULT_HARD_SENSORY_NOISE_FRACTION)
    parser.add_argument("--min-switch-interval", type=int, default=DEFAULT_HARD_MIN_SWITCH_INTERVAL)
    parser.add_argument("--max-switch-interval", type=int, default=DEFAULT_HARD_MAX_SWITCH_INTERVAL)
    parser.add_argument("--recovery-window-trials", type=int, default=5)
    parser.add_argument("--recovery-accuracy-threshold", type=float, default=0.60)
    parser.add_argument("--hard-tail-threshold", type=float, default=DEFAULT_HARD_TAIL_THRESHOLD)
    parser.add_argument("--bridge-tail-delta-tolerance", type=float, default=1e-12)
    parser.add_argument("--hardware-tail-delta-tolerance", type=float, default=0.05)
    parser.add_argument("--hardware-dir", type=Path, default=DEFAULT_HARDWARE_DIR)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument(
        "--recompute-existing",
        type=Path,
        default=None,
        help="Recompute summaries from an existing tier4_16b_debug output directory without rerunning backends.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.recompute_existing is not None:
        return recompute_existing(args)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    output_dir = args.output_dir or OUTPUT_ROOT / f"tier4_16b_debug_{timestamp}_hard_switch"
    output_dir.mkdir(parents=True, exist_ok=True)
    backends = parse_csv_list(args.backends)
    seeds = [int(seed) for seed in args.seeds]

    all_rows: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    comparisons: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    rows_by_key: dict[tuple[str, str, int], list[dict[str, Any]]] = {}
    summaries_by_key: dict[tuple[str, str, int], dict[str, Any]] = {}

    for seed in seeds:
        task = build_task(seed, args)
        loaded_hw = load_hardware_rows(args.hardware_dir, seed)
        if loaded_hw is not None:
            rows, summary = loaded_hw
            all_rows.extend(rows)
            summaries.append(summary)
            rows_by_key[("returned_hardware_chunked_host_replay", "spinnaker", seed)] = rows
            summaries_by_key[("returned_hardware_chunked_host_replay", "spinnaker", seed)] = summary
        else:
            failures.append(
                {
                    "path": "returned_hardware_chunked_host_replay",
                    "backend_key": "spinnaker",
                    "seed": seed,
                    "error_type": "MissingHardwareTrace",
                    "error": str(args.hardware_dir),
                }
            )
        for backend_key in backends:
            try:
                rows, summary = run_full_cra_step(task=task, backend_key=backend_key, seed=seed, args=args)
                all_rows.extend(rows)
                summaries.append(summary)
                rows_by_key[("full_step_cra", backend_key, seed)] = rows
                summaries_by_key[("full_step_cra", backend_key, seed)] = summary
            except Exception as exc:
                failures.append(
                    {
                        "path": "full_step_cra",
                        "backend_key": backend_key,
                        "seed": seed,
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    }
                )
            for chunk in [1, int(args.chunk_size_steps)]:
                try:
                    rows, summary = run_direct_local_mode(
                        task=task,
                        backend_key=backend_key,
                        seed=seed,
                        chunk_size_steps=chunk,
                        args=args,
                    )
                    all_rows.extend(rows)
                    summaries.append(summary)
                    path_name = "direct_step_host_replay" if chunk == 1 else "direct_chunked_host_replay"
                    rows_by_key[(path_name, backend_key, seed)] = rows
                    summaries_by_key[(path_name, backend_key, seed)] = summary
                except Exception as exc:
                    failures.append(
                        {
                            "path": "direct_step_host_replay" if chunk == 1 else "direct_chunked_host_replay",
                            "backend_key": backend_key,
                            "seed": seed,
                            "error_type": type(exc).__name__,
                            "error": str(exc),
                        }
                    )

    for seed in seeds:
        for backend_key in backends:
            step_key = ("direct_step_host_replay", backend_key, seed)
            chunk_key = ("direct_chunked_host_replay", backend_key, seed)
            full_key = ("full_step_cra", backend_key, seed)
            if step_key in rows_by_key and chunk_key in rows_by_key:
                comparisons.append(
                    comparison_row(
                        left_name="direct_step_host_replay",
                        left_rows=rows_by_key[step_key],
                        left_summary=summaries_by_key[step_key],
                        right_name="direct_chunked_host_replay",
                        right_rows=rows_by_key[chunk_key],
                        right_summary=summaries_by_key[chunk_key],
                        comparison_type="direct_step_vs_chunked",
                    )
                )
            if full_key in rows_by_key and chunk_key in rows_by_key:
                comparisons.append(
                    comparison_row(
                        left_name="full_step_cra",
                        left_rows=rows_by_key[full_key],
                        left_summary=summaries_by_key[full_key],
                        right_name="direct_chunked_host_replay",
                        right_rows=rows_by_key[chunk_key],
                        right_summary=summaries_by_key[chunk_key],
                        comparison_type="full_cra_vs_direct_chunked",
                    )
                )
            hw_key = ("returned_hardware_chunked_host_replay", "spinnaker", seed)
            if hw_key in rows_by_key and chunk_key in rows_by_key:
                comparisons.append(
                    comparison_row(
                        left_name="direct_chunked_host_replay",
                        left_rows=rows_by_key[chunk_key],
                        left_summary=summaries_by_key[chunk_key],
                        right_name="returned_hardware_chunked_host_replay",
                        right_rows=rows_by_key[hw_key],
                        right_summary=summaries_by_key[hw_key],
                        comparison_type="local_chunked_vs_hardware",
                    )
                )

    path_aggs: list[dict[str, Any]] = []
    paths = [
        "full_step_cra",
        "direct_step_host_replay",
        "direct_chunked_host_replay",
        "returned_hardware_chunked_host_replay",
    ]
    for path_name in paths:
        path_aggs.append(aggregate_path(summaries, path=path_name))
        for backend_key in ([*backends] if path_name != "returned_hardware_chunked_host_replay" else ["spinnaker"]):
            path_aggs.append(aggregate_path(summaries, path=path_name, backend_key=backend_key))

    decision = build_decision(path_aggs=path_aggs, comparisons=comparisons, args=args)
    expected_local_runs = len(seeds) * len(backends) * 3
    expected_hardware_runs = len(seeds)
    criteria = [
        criterion(
            "full diagnostic matrix completed",
            len([s for s in summaries if s.get("path") != "returned_hardware_chunked_host_replay"]),
            "==",
            expected_local_runs,
            len([s for s in summaries if s.get("path") != "returned_hardware_chunked_host_replay"]) == expected_local_runs,
        ),
        criterion(
            "hardware traces loaded",
            len([s for s in summaries if s.get("path") == "returned_hardware_chunked_host_replay"]),
            "==",
            expected_hardware_runs,
            len([s for s in summaries if s.get("path") == "returned_hardware_chunked_host_replay"]) == expected_hardware_runs,
        ),
        criterion("no execution exceptions", len(failures), "==", 0, len(failures) == 0),
        criterion("failure class assigned", bool(decision.get("classification")), "==", True, bool(decision.get("classification"))),
        criterion(
            "direct step/chunked comparison produced",
            len([c for c in comparisons if c["comparison_type"] == "direct_step_vs_chunked"]),
            "==",
            len(seeds) * len(backends),
            len([c for c in comparisons if c["comparison_type"] == "direct_step_vs_chunked"]) == len(seeds) * len(backends),
        ),
        criterion(
            "hardware/local comparison produced",
            len([c for c in comparisons if c["comparison_type"] == "local_chunked_vs_hardware"]),
            "==",
            len(seeds) * len(backends),
            len([c for c in comparisons if c["comparison_type"] == "local_chunked_vs_hardware"]) == len(seeds) * len(backends),
        ),
    ]
    status, failure_reason = pass_fail(criteria)

    summary_csv = output_dir / "tier4_16b_debug_summary.csv"
    path_summary_csv = output_dir / "tier4_16b_debug_path_summary.csv"
    comparisons_csv = output_dir / "tier4_16b_debug_comparisons.csv"
    timeseries_csv = output_dir / "tier4_16b_debug_timeseries.csv"
    failures_csv = output_dir / "tier4_16b_debug_failures.csv"
    report_md = output_dir / "tier4_16b_debug_report.md"
    manifest_json = output_dir / "tier4_16b_debug_results.json"
    plot_png = output_dir / "tier4_16b_debug_summary.png"

    write_csv(summary_csv, summaries)
    write_csv(path_summary_csv, path_aggs)
    write_csv(comparisons_csv, comparisons)
    write_csv(timeseries_csv, all_rows)
    if failures:
        write_csv(failures_csv, failures)
    plot_summary(path_aggs, plot_png)
    artifacts = {
        "summary_csv": str(summary_csv),
        "path_summary_csv": str(path_summary_csv),
        "comparisons_csv": str(comparisons_csv),
        "timeseries_csv": str(timeseries_csv),
        "report_md": str(report_md),
        "manifest_json": str(manifest_json),
    }
    if failures:
        artifacts["failures_csv"] = str(failures_csv)
    if plot_png.exists():
        artifacts["summary_png"] = str(plot_png)

    write_json(
        manifest_json,
        {
            "generated_at_utc": utc_now(),
            "tier": TIER,
            "status": status,
            "failure_reason": failure_reason,
            "summary": {
                "classification": decision.get("classification"),
                "next_step": decision.get("next_step"),
                "backends": backends,
                "seeds": seeds,
                "steps": args.steps,
                "chunk_size_steps": args.chunk_size_steps,
                "hardware_dir": str(args.hardware_dir),
                "failures": failures,
            },
            "decision": decision,
            "criteria": criteria,
            "path_summaries": path_aggs,
            "comparisons": comparisons,
            "run_summaries": summaries,
            "artifacts": artifacts,
            "matplotlib_error": MATPLOTLIB_ERROR,
        },
    )
    write_report(
        path=report_md,
        output_dir=output_dir,
        status=status,
        failure_reason=failure_reason,
        criteria=criteria,
        decision=decision,
        path_aggs=path_aggs,
        comparisons=comparisons,
        artifacts=artifacts,
    )
    write_json(
        OUTPUT_ROOT / "tier4_16b_debug_latest_manifest.json",
        {
            "generated_at_utc": utc_now(),
            "manifest": str(manifest_json),
            "report": str(report_md),
            "summary_csv": str(summary_csv),
            "output_dir": str(output_dir),
            "status": status,
            "canonical": False,
            "claim": "Tier 4.16b local hard-switch root-cause diagnostic; not hardware success evidence.",
            "classification": decision.get("classification"),
            "next_step": decision.get("next_step"),
        },
    )
    print(
        json.dumps(
            {
                "status": status,
                "output_dir": str(output_dir),
                "classification": decision.get("classification"),
                "next_step": decision.get("next_step"),
            },
            indent=2,
        )
    )
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
