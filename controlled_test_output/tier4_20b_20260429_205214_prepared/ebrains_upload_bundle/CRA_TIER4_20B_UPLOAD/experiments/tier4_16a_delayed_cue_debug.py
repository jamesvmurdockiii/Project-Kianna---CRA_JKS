#!/usr/bin/env python3
"""Tier 4.16a delayed-cue hardware failure analysis.

This diagnostic replays the exact Tier 4.16 `delayed_cue` configuration on
local software backends before spending another SpiNNaker allocation. It answers
one narrow question:

    Did seeds 43/44 fail because the task/config/metric is brittle in software
    too, or because the confirmed software setting failed specifically during
    SpiNNaker transfer?

The result is diagnostic evidence, not a Tier 4.16 pass.
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
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except Exception as exc:  # pragma: no cover - optional plotting dependency
    plt = None
    MATPLOTLIB_ERROR = str(exc)
else:
    MATPLOTLIB_ERROR = None

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from coral_reef_spinnaker import Organism, ReefConfig  # noqa: E402
from tier2_learning import (  # noqa: E402
    DEFAULT_AMPLITUDE,
    DEFAULT_DT_SECONDS,
    criterion,
    end_backend,
    json_safe,
    load_backend,
    markdown_value,
    pass_fail,
    setup_backend,
    strict_sign,
    write_csv,
    write_json,
)
from tier4_scaling import alive_readout_weights, alive_trophic_health  # noqa: E402
from tier5_external_baselines import TaskStream, delayed_cue_task, summarize_rows  # noqa: E402


TIER = "Tier 4.16a-debug - Delayed Cue Hardware Failure Analysis"
DEFAULT_BACKENDS = "nest,brian2"
DEFAULT_SEEDS = "42,43,44"
DEFAULT_STEPS = 120
DEFAULT_POPULATION_SIZE = 8
DEFAULT_DELAYED_LR = 0.20
DEFAULT_READOUT_LR = 0.10
DEFAULT_TAIL_THRESHOLD = 0.85
DEFAULT_HARDWARE_FAIL_DIR = (
    ROOT / "controlled_test_output" / "tier4_16_20260427_124916_hardware_fail"
)
OUTPUT_ROOT = ROOT / "controlled_test_output"


def utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "+00:00"


def parse_csv_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_seeds(value: str) -> list[int]:
    return [int(item) for item in parse_csv_list(value)]


def task_horizon(task: TaskStream) -> int:
    due = np.asarray(task.feedback_due_step, dtype=int)
    offsets = due - np.arange(task.steps, dtype=int)
    valid = offsets[due >= 0]
    return int(max(1, int(np.max(valid)))) if valid.size else 1


def make_task(seed: int, args: argparse.Namespace) -> TaskStream:
    return delayed_cue_task(steps=args.steps, amplitude=args.amplitude, seed=seed, args=args)


def make_config(*, seed: int, task: TaskStream, args: argparse.Namespace) -> ReefConfig:
    cfg = ReefConfig.default()
    cfg.seed = int(seed)
    cfg.lifecycle.initial_population = int(args.population_size)
    cfg.lifecycle.max_population_from_memory = False
    cfg.lifecycle.max_population_hard = int(args.population_size)
    cfg.lifecycle.enable_reproduction = False
    cfg.lifecycle.enable_apoptosis = False
    cfg.lifecycle.enable_structural_plasticity = True
    cfg.measurement.stream_history_maxlen = max(task.steps + 16, 128)
    cfg.spinnaker.sync_interval_steps = 0
    cfg.spinnaker.runtime_ms_per_step = float(args.dt_seconds) * 1000.0
    cfg.learning.evaluation_horizon_bars = task_horizon(task)
    cfg.learning.readout_learning_rate = float(args.readout_lr)
    cfg.learning.delayed_readout_learning_rate = float(args.delayed_readout_lr)
    return cfg


def run_backend_seed(
    *, backend_key: str, seed: int, args: argparse.Namespace
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    random.seed(seed)
    np.random.seed(seed)
    task = make_task(seed, args)
    sim, backend_name = load_backend(backend_key)
    setup_backend(sim, backend_name)
    cfg = make_config(seed=seed, task=task, args=args)
    organism: Organism | None = Organism(cfg, sim)
    rows: list[dict[str, Any]] = []
    diagnostics: dict[str, Any] = {}
    started = time.perf_counter()

    try:
        organism.initialize(stream_keys=[task.domain])
        for step in range(task.steps):
            sensory_value = float(task.sensory[step])
            target_value = float(task.current_target[step])
            metrics = organism.train_step(
                market_return_1m=target_value,
                dt_seconds=args.dt_seconds,
                sensory_return_1m=sensory_value,
            )
            prediction = float(metrics.colony_prediction)
            eval_sign = strict_sign(float(task.evaluation_target[step]))
            pred_sign = strict_sign(prediction)
            weights = alive_readout_weights(organism)
            trophic = alive_trophic_health(organism)
            learning_status = (
                organism.learning_manager.get_summary()
                if organism.learning_manager is not None
                else {}
            )
            latest_spikes = organism.spike_buffer[-1] if organism.spike_buffer else {}
            row = metrics.to_dict()
            row.update(
                {
                    "tier": TIER,
                    "task": task.name,
                    "backend_key": backend_key,
                    "backend": backend_name,
                    "seed": int(seed),
                    "step": int(step),
                    "sensory_return_1m": sensory_value,
                    "target_return_1m": target_value,
                    "target_signal_horizon": float(task.evaluation_target[step]),
                    "target_signal_sign": eval_sign,
                    "target_signal_nonzero": bool(task.evaluation_mask[step] and eval_sign != 0),
                    "prediction_sign": pred_sign,
                    "strict_direction_correct": bool(
                        task.evaluation_mask[step]
                        and pred_sign != 0
                        and pred_sign == eval_sign
                    ),
                    "feedback_due_step": int(task.feedback_due_step[step]),
                    "configured_horizon_bars": int(cfg.learning.evaluation_horizon_bars),
                    "configured_readout_lr": float(cfg.learning.readout_learning_rate),
                    "configured_delayed_readout_lr": float(
                        cfg.learning.delayed_readout_learning_rate
                    ),
                    "mean_readout_weight": float(np.mean(weights)) if weights else 0.0,
                    "min_readout_weight": float(np.min(weights)) if weights else 0.0,
                    "max_readout_weight": float(np.max(weights)) if weights else 0.0,
                    "mean_abs_readout_weight": float(np.mean(np.abs(weights))) if weights else 0.0,
                    "mean_trophic_health": float(np.mean(trophic)) if trophic else 0.0,
                    "min_trophic_health": float(np.min(trophic)) if trophic else 0.0,
                    "max_trophic_health": float(np.max(trophic)) if trophic else 0.0,
                    "pending_horizons": int(learning_status.get("pending_horizons", 0)),
                    "matured_horizons": int(learning_status.get("matured_horizons", 0)),
                    "step_spike_count": int(sum(int(v) for v in latest_spikes.values())),
                }
            )
            rows.append(row)
        diagnostics = organism.backend_diagnostics()
    finally:
        if organism is not None:
            if not diagnostics:
                diagnostics = organism.backend_diagnostics()
            organism.shutdown()
        end_backend(sim)

    summary = summarize_rows(rows)
    tail_events = extract_tail_events(rows)
    step_spikes = [float(r.get("step_spike_count", 0.0)) for r in rows]
    summary.update(
        {
            "source": "software",
            "task": "delayed_cue",
            "backend_key": backend_key,
            "backend": backend_name,
            "seed": int(seed),
            "steps": int(task.steps),
            "population_size": int(args.population_size),
            "delay": int(args.delay),
            "period": int(args.period),
            "evaluation_horizon_bars": int(cfg.learning.evaluation_horizon_bars),
            "readout_lr": float(args.readout_lr),
            "delayed_readout_lr": float(args.delayed_readout_lr),
            "tail_event_count": len(tail_events),
            "one_tail_event_accuracy_step": (1.0 / len(tail_events)) if tail_events else None,
            "runtime_seconds": time.perf_counter() - started,
            "total_step_spikes": int(sum(step_spikes)),
            "mean_step_spikes": float(np.mean(step_spikes)) if step_spikes else 0.0,
            "final_mean_readout_weight": float(rows[-1].get("mean_readout_weight", 0.0)) if rows else None,
            "final_mean_abs_readout_weight": float(rows[-1].get("mean_abs_readout_weight", 0.0)) if rows else None,
            "final_matured_horizons": int(rows[-1].get("matured_horizons", 0)) if rows else 0,
            "final_pending_horizons": int(rows[-1].get("pending_horizons", 0)) if rows else 0,
        }
    )
    summary.update(diagnostics)
    return rows, summary, tail_events


def extract_tail_events(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rows:
        return []
    tail_start = int(len(rows) * 0.75)
    events: list[dict[str, Any]] = []
    for row in rows:
        step = int(row.get("step", 0))
        if step < tail_start or not bool(row.get("target_signal_nonzero", False)):
            continue
        events.append(
            {
                "source": row.get("source", "software"),
                "backend_key": row.get("backend_key", row.get("backend", "")),
                "backend": row.get("backend", ""),
                "seed": int(row.get("seed", 0)),
                "step": step,
                "target_signal_horizon": float(row.get("target_signal_horizon", 0.0) or 0.0),
                "target_signal_sign": int(row.get("target_signal_sign", 0) or 0),
                "colony_prediction": float(row.get("colony_prediction", 0.0) or 0.0),
                "prediction_sign": int(row.get("prediction_sign", 0) or 0),
                "strict_direction_correct": bool(row.get("strict_direction_correct", False)),
                "raw_dopamine": float(row.get("raw_dopamine", 0.0) or 0.0),
                "mean_readout_weight": float(row.get("mean_readout_weight", 0.0) or 0.0),
                "matured_horizons": int(float(row.get("matured_horizons", 0) or 0)),
                "pending_horizons": int(float(row.get("pending_horizons", 0) or 0)),
            }
        )
    return events


def load_hardware_failure(fail_dir: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    if not fail_dir.exists():
        return [], [], []
    summary_path = fail_dir / "tier4_16_summary.csv"
    hardware_summaries: list[dict[str, Any]] = []
    if summary_path.exists():
        with summary_path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("task") != "delayed_cue":
                    continue
                converted = {
                    key: _coerce_csv_value(value)
                    for key, value in row.items()
                }
                converted["source"] = "hardware_failed_4_16"
                converted["backend_key"] = "spinnaker"
                converted["backend"] = "pyNN.spiNNaker"
                hardware_summaries.append(converted)

    rows: list[dict[str, Any]] = []
    tail_events: list[dict[str, Any]] = []
    for csv_path in sorted(fail_dir.glob("spinnaker_hardware_delayed_cue_seed*_timeseries.csv")):
        with csv_path.open(newline="", encoding="utf-8") as f:
            seed_rows = []
            for row in csv.DictReader(f):
                converted = {key: _coerce_csv_value(value) for key, value in row.items()}
                converted["source"] = "hardware_failed_4_16"
                converted["backend_key"] = "spinnaker"
                converted["backend"] = "pyNN.spiNNaker"
                seed_rows.append(converted)
        rows.extend(seed_rows)
        tail_events.extend(extract_tail_events(seed_rows))
    return rows, hardware_summaries, tail_events


def _coerce_csv_value(value: str) -> Any:
    if value == "":
        return None
    if value in {"True", "False"}:
        return value == "True"
    try:
        if "." not in value and "e" not in value.lower():
            return int(value)
        return float(value)
    except Exception:
        return value


def aggregate_backend_summaries(summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for summary in summaries:
        groups.setdefault((str(summary.get("source", "software")), str(summary.get("backend_key"))), []).append(summary)
    aggregate_rows: list[dict[str, Any]] = []
    for (source, backend_key), group in sorted(groups.items()):
        row: dict[str, Any] = {
            "source": source,
            "backend_key": backend_key,
            "backend": group[0].get("backend"),
            "runs": len(group),
            "seeds": [g.get("seed") for g in group],
        }
        for key in [
            "all_accuracy",
            "tail_accuracy",
            "prediction_target_corr",
            "tail_prediction_target_corr",
            "evaluation_count",
            "tail_event_count",
            "one_tail_event_accuracy_step",
            "runtime_seconds",
            "total_step_spikes",
            "final_mean_readout_weight",
            "final_mean_abs_readout_weight",
            "mean_abs_dopamine",
            "max_abs_dopamine",
        ]:
            values = [g.get(key) for g in group if g.get(key) is not None]
            numeric = [float(v) for v in values if _is_number(v)]
            row[f"{key}_mean"] = float(np.mean(numeric)) if numeric else None
            row[f"{key}_min"] = float(np.min(numeric)) if numeric else None
            row[f"{key}_max"] = float(np.max(numeric)) if numeric else None
        row["failed_seeds_at_threshold"] = [
            g.get("seed") for g in group if (g.get("tail_accuracy") is not None and float(g["tail_accuracy"]) < DEFAULT_TAIL_THRESHOLD)
        ]
        row["sim_run_failures_sum"] = int(sum(int(g.get("sim_run_failures", 0) or 0) for g in group))
        row["summary_read_failures_sum"] = int(sum(int(g.get("summary_read_failures", 0) or 0) for g in group))
        row["synthetic_fallbacks_sum"] = int(sum(int(g.get("synthetic_fallbacks", 0) or 0) for g in group))
        aggregate_rows.append(row)
    return aggregate_rows


def _is_number(value: Any) -> bool:
    try:
        f = float(value)
    except Exception:
        return False
    return math.isfinite(f)


def diagnose(
    *,
    software_summaries: list[dict[str, Any]],
    hardware_summaries: list[dict[str, Any]],
    args: argparse.Namespace,
) -> dict[str, Any]:
    threshold = float(args.tail_threshold)
    software_failures = [
        {
            "backend_key": s.get("backend_key"),
            "seed": s.get("seed"),
            "tail_accuracy": s.get("tail_accuracy"),
            "tail_event_count": s.get("tail_event_count"),
        }
        for s in software_summaries
        if s.get("tail_accuracy") is None or float(s.get("tail_accuracy")) < threshold
    ]
    hardware_failures = [
        {
            "backend_key": s.get("backend_key", "spinnaker"),
            "seed": s.get("seed"),
            "tail_accuracy": s.get("tail_accuracy"),
            "tail_event_count": s.get("tail_event_count"),
        }
        for s in hardware_summaries
        if s.get("tail_accuracy") is None or float(s.get("tail_accuracy")) < threshold
    ]
    min_tail_events = min(
        [
            int(s.get("tail_event_count", 0) or 0)
            for s in software_summaries
            if s.get("tail_event_count") is not None
        ]
        or [0]
    )
    metric_brittle = min_tail_events > 0 and min_tail_events < int(args.min_tail_events_for_stable_metric)
    if software_failures:
        diagnosis = "software_config_or_metric_issue"
        next_step = "debug locally before another hardware run"
    elif hardware_failures:
        diagnosis = "hardware_transfer_or_timing_issue"
        next_step = "repair delayed_cue locally before hardware repeat"
    else:
        diagnosis = "hardware_failure_not_reproduced_in_local_backends"
        next_step = "run repaired delayed_cue hardware repeat only after local repair"
    return {
        "diagnosis": diagnosis,
        "next_step": next_step,
        "software_failures": software_failures,
        "hardware_failures": hardware_failures,
        "metric_brittle": metric_brittle,
        "min_tail_event_count": min_tail_events,
        "tail_threshold": threshold,
        "min_tail_events_for_stable_metric": int(args.min_tail_events_for_stable_metric),
    }


def plot_debug(summary_rows: list[dict[str, Any]], output: Path) -> None:
    if plt is None:
        return
    labels = [f"{r.get('backend_key')}:{r.get('seed')}" for r in summary_rows]
    tail = [float(r.get("tail_accuracy", 0.0) or 0.0) for r in summary_rows]
    corr = [
        float(r.get("tail_prediction_target_corr", 0.0) or 0.0)
        if r.get("tail_prediction_target_corr") is not None
        else 0.0
        for r in summary_rows
    ]
    colors = ["#2d6cdf" if r.get("source") == "software" else "#c04747" for r in summary_rows]
    fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
    axes[0].bar(labels, tail, color=colors)
    axes[0].axhline(DEFAULT_TAIL_THRESHOLD, color="black", linestyle="--", linewidth=1)
    axes[0].set_ylabel("tail accuracy")
    axes[0].set_ylim(0.0, 1.05)
    axes[0].set_title("Tier 4.16a delayed_cue debug")
    axes[1].bar(labels, corr, color=colors)
    axes[1].axhline(0.0, color="black", linewidth=1)
    axes[1].set_ylabel("tail corr")
    axes[1].set_ylim(-1.05, 1.05)
    axes[1].tick_params(axis="x", rotation=35)
    fig.tight_layout()
    fig.savefig(output, dpi=160)
    plt.close(fig)


def write_report(
    *,
    path: Path,
    status: str,
    output_dir: Path,
    criteria: list[dict[str, Any]],
    summary_rows: list[dict[str, Any]],
    aggregate_rows: list[dict[str, Any]],
    diagnosis: dict[str, Any],
    artifacts: dict[str, str],
) -> None:
    lines = [
        "# Tier 4.16a Delayed Cue Hardware Failure Analysis",
        "",
        f"- Generated: `{utc_now()}`",
        f"- Status: **{status.upper()}**",
        f"- Output directory: `{output_dir}`",
        "",
        "This diagnostic replays the exact Tier 4.16 `delayed_cue` config on local software backends and compares it to the failed hardware run.",
        "",
        "## Diagnosis",
        "",
        f"- diagnosis: `{diagnosis['diagnosis']}`",
        f"- next_step: `{diagnosis['next_step']}`",
        f"- metric_brittle: `{diagnosis['metric_brittle']}`",
        f"- min_tail_event_count: `{diagnosis['min_tail_event_count']}`",
        f"- tail_threshold: `{diagnosis['tail_threshold']}`",
        "",
        "## Summary Rows",
        "",
        "| Source | Backend | Seed | Tail Acc | Tail Corr | Tail Events | All Acc | Runtime |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary_rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.get("source", "software")),
                    str(row.get("backend_key", "")),
                    markdown_value(row.get("seed")),
                    markdown_value(row.get("tail_accuracy")),
                    markdown_value(row.get("tail_prediction_target_corr")),
                    markdown_value(row.get("tail_event_count")),
                    markdown_value(row.get("all_accuracy")),
                    markdown_value(row.get("runtime_seconds")),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Aggregate Rows",
            "",
            "| Source | Backend | Runs | Tail Acc Mean | Tail Acc Min | Failed Seeds |",
            "| --- | --- | ---: | ---: | ---: | --- |",
        ]
    )
    for row in aggregate_rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.get("source")),
                    str(row.get("backend_key")),
                    markdown_value(row.get("runs")),
                    markdown_value(row.get("tail_accuracy_mean")),
                    markdown_value(row.get("tail_accuracy_min")),
                    str(row.get("failed_seeds_at_threshold")),
                ]
            )
            + " |"
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
    for item in criteria:
        lines.append(
            f"| {item['name']} | {markdown_value(item['value'])} | {item['operator']} {markdown_value(item['threshold'])} | {pass_fail_mark(item['passed'])} |"
        )
    lines.extend(["", "## Artifacts", ""])
    for key, value in artifacts.items():
        lines.append(f"- `{key}`: `{value}`")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def pass_fail_mark(value: bool) -> str:
    return "yes" if value else "no"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Tier 4.16a delayed-cue debug locally.")
    parser.add_argument("--backends", default=DEFAULT_BACKENDS)
    parser.add_argument("--seeds", type=parse_seeds, default=parse_seeds(DEFAULT_SEEDS))
    parser.add_argument("--steps", type=int, default=DEFAULT_STEPS)
    parser.add_argument("--population-size", type=int, default=DEFAULT_POPULATION_SIZE)
    parser.add_argument("--amplitude", type=float, default=DEFAULT_AMPLITUDE)
    parser.add_argument("--dt-seconds", type=float, default=DEFAULT_DT_SECONDS)
    parser.add_argument("--readout-lr", type=float, default=DEFAULT_READOUT_LR)
    parser.add_argument("--delayed-readout-lr", type=float, default=DEFAULT_DELAYED_LR)
    parser.add_argument("--delay", type=int, default=5)
    parser.add_argument("--period", type=int, default=8)
    parser.add_argument("--tail-threshold", type=float, default=DEFAULT_TAIL_THRESHOLD)
    parser.add_argument("--min-tail-events-for-stable-metric", type=int, default=8)
    parser.add_argument("--hardware-fail-dir", type=Path, default=DEFAULT_HARDWARE_FAIL_DIR)
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    backends = parse_csv_list(args.backends)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    output_dir = (
        args.output_dir
        if args.output_dir is not None
        else OUTPUT_ROOT / f"tier4_16a_debug_{timestamp}"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    all_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    tail_events: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for backend in backends:
        for seed in args.seeds:
            try:
                rows, summary, events = run_backend_seed(
                    backend_key=backend, seed=seed, args=args
                )
                rows_path = output_dir / f"tier4_16a_debug_{backend}_seed{seed}_timeseries.csv"
                write_csv(rows_path, rows)
                all_rows.extend(rows)
                summary_rows.append(summary)
                tail_events.extend(events)
            except Exception as exc:  # pragma: no cover - diagnostic failure capture
                failures.append(
                    {
                        "backend_key": backend,
                        "seed": seed,
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    }
                )

    hardware_rows, hardware_summaries, hardware_tail_events = load_hardware_failure(
        args.hardware_fail_dir
    )
    for summary in hardware_summaries:
        if summary.get("tail_event_count") is None:
            seed_events = [
                event
                for event in hardware_tail_events
                if int(event.get("seed", -1)) == int(summary.get("seed", -2))
            ]
            summary["tail_event_count"] = len(seed_events)
            summary["one_tail_event_accuracy_step"] = (
                1.0 / len(seed_events) if seed_events else None
            )
    combined_summaries = summary_rows + hardware_summaries
    combined_tail_events = tail_events + hardware_tail_events
    aggregate_rows = aggregate_backend_summaries(combined_summaries)
    diagnosis = diagnose(
        software_summaries=summary_rows,
        hardware_summaries=hardware_summaries,
        args=args,
    )

    expected_runs = len(backends) * len(args.seeds)
    criteria = [
        criterion("software matrix completed", len(summary_rows), "==", expected_runs, len(summary_rows) == expected_runs),
        criterion("hardware failure artifact loaded", len(hardware_summaries), ">", 0, len(hardware_summaries) > 0),
        criterion("confirmed delayed-credit setting used", args.delayed_readout_lr, "==", DEFAULT_DELAYED_LR, abs(float(args.delayed_readout_lr) - DEFAULT_DELAYED_LR) < 1e-12),
        criterion("diagnosis generated", bool(diagnosis.get("diagnosis")), "==", True, bool(diagnosis.get("diagnosis"))),
    ]
    status, failure_reason = pass_fail(criteria)

    summary_csv = output_dir / "tier4_16a_debug_summary.csv"
    aggregate_csv = output_dir / "tier4_16a_debug_backend_summary.csv"
    tail_csv = output_dir / "tier4_16a_debug_tail_events.csv"
    failure_csv = output_dir / "tier4_16a_debug_failures.csv"
    plot_path = output_dir / "tier4_16a_debug_summary.png"
    manifest_path = output_dir / "tier4_16a_debug_results.json"
    report_path = output_dir / "tier4_16a_debug_report.md"
    write_csv(summary_csv, combined_summaries)
    write_csv(aggregate_csv, aggregate_rows)
    write_csv(tail_csv, combined_tail_events)
    if failures:
        write_csv(failure_csv, failures)
    plot_debug(combined_summaries, plot_path)

    artifacts = {
        "summary_csv": str(summary_csv),
        "backend_summary_csv": str(aggregate_csv),
        "tail_events_csv": str(tail_csv),
        "summary_png": str(plot_path) if plot_path.exists() else "",
        "hardware_fail_dir": str(args.hardware_fail_dir),
    }
    if failures:
        artifacts["failures_csv"] = str(failure_csv)
    write_json(
        manifest_path,
        {
            "generated_at_utc": utc_now(),
            "tier": TIER,
            "status": status,
            "failure_reason": failure_reason,
            "diagnosis": diagnosis,
            "criteria": criteria,
            "summary_rows": combined_summaries,
            "backend_summary_rows": aggregate_rows,
            "software_failures": failures,
            "artifacts": artifacts,
            "config": {
                "backends": backends,
                "seeds": args.seeds,
                "steps": args.steps,
                "population_size": args.population_size,
                "delay": args.delay,
                "period": args.period,
                "readout_lr": args.readout_lr,
                "delayed_readout_lr": args.delayed_readout_lr,
                "tail_threshold": args.tail_threshold,
            },
        },
    )
    artifacts["manifest_json"] = str(manifest_path)
    artifacts["report_md"] = str(report_path)
    write_report(
        path=report_path,
        status=status,
        output_dir=output_dir,
        criteria=criteria,
        summary_rows=combined_summaries,
        aggregate_rows=aggregate_rows,
        diagnosis=diagnosis,
        artifacts=artifacts,
    )
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
