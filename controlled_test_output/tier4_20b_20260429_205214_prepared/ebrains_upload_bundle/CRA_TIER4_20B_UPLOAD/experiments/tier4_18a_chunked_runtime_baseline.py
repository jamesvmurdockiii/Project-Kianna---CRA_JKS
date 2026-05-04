#!/usr/bin/env python3
"""Tier 4.18a v0.7 chunked hardware runtime baseline.

Tier 4.18a is an engineering characterization of the exact v0.7 hardware path
that already passed Tier 4.16a and Tier 4.16b:

``runtime_mode=chunked`` and ``learning_location=host``.

It is not a new learning claim. It compares chunk sizes on real SpiNNaker to
measure wall time, ``sim.run`` call count, spike readback, task metrics, and
failure/fallback rates. The low-level hardware execution is delegated to the
Tier 4.16 chunked runner so this tier cannot accidentally test a different
learning bridge.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
import sys
import time
import traceback
from argparse import Namespace
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

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

from coral_reef_spinnaker.runtime_modes import chunk_ranges, make_runtime_plan  # noqa: E402
from tier2_learning import (  # noqa: E402
    DEFAULT_AMPLITUDE,
    DEFAULT_DT_SECONDS,
    criterion,
    markdown_value,
    pass_fail,
    plot_case,
    write_csv,
    write_json,
    utc_now,
)
from tier4_harder_spinnaker_capsule import (  # noqa: E402
    DEFAULT_DELAYED_LR,
    DEFAULT_HARD_MAX_DELAY,
    DEFAULT_HARD_MAX_SWITCH_INTERVAL,
    DEFAULT_HARD_MIN_DELAY,
    DEFAULT_HARD_MIN_SWITCH_INTERVAL,
    DEFAULT_HARD_NOISE_PROB,
    DEFAULT_HARD_PERIOD,
    DEFAULT_HARD_SENSORY_NOISE_FRACTION,
    build_parser as build_tier4_16_parser,
    clean_float,
    collect_environment,
    collect_recent_spinnaker_reports,
    run_chunked_spinnaker_task_seed,
    safe_mean,
    safe_std,
    truthy,
)

TIER = "Tier 4.18a - v0.7 Chunked Hardware Runtime Baseline"
DEFAULT_TASKS = "delayed_cue,hard_noisy_switching"
DEFAULT_CHUNKS = "10,25,50"
DEFAULT_SEEDS = "42"
DEFAULT_STEPS = 1200


def parse_csv(value: str) -> list[str]:
    items = [item.strip() for item in value.split(",") if item.strip()]
    if not items:
        raise argparse.ArgumentTypeError("at least one item is required")
    return items


def parse_ints(value: str) -> list[int]:
    try:
        return [int(item) for item in parse_csv(value)]
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def parse_tasks(value: str) -> list[str]:
    allowed = {"delayed_cue", "hard_noisy_switching"}
    tasks = parse_csv(value)
    unknown = [task for task in tasks if task not in allowed]
    if unknown:
        raise argparse.ArgumentTypeError(f"unknown Tier 4.18a task(s): {', '.join(unknown)}")
    return tasks


def finite(value: Any) -> bool:
    return clean_float(value) is not None


def safe_min(values: list[Any]) -> float | None:
    clean = [v for value in values if (v := clean_float(value)) is not None]
    return min(clean) if clean else None


def safe_max(values: list[Any]) -> float | None:
    clean = [v for value in values if (v := clean_float(value)) is not None]
    return max(clean) if clean else None


def write_summary_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(value) if isinstance(value, (dict, list)) else value for key, value in row.items()})


def child_args(args: argparse.Namespace, *, task: str, seed: int, chunk_size: int) -> Namespace:
    """Build a Tier 4.16-compatible argument namespace for one run."""

    base = build_tier4_16_parser().parse_args([])
    base.mode = "run-hardware"
    base.tasks = [task]
    base.seeds = [int(seed)]
    base.steps = int(args.steps)
    base.population_size = int(args.population_size)
    base.amplitude = float(args.amplitude)
    base.dt_seconds = float(args.dt_seconds)
    base.timestep_ms = float(args.timestep_ms)
    base.readout_lr = float(args.readout_lr)
    base.delayed_readout_lr = float(args.delayed_readout_lr)
    base.base_current_na = float(args.base_current_na)
    base.cue_current_gain_na = float(args.cue_current_gain_na)
    base.min_current_na = float(args.min_current_na)
    base.delayed_tail_threshold = float(args.delayed_tail_threshold)
    base.hard_tail_threshold = float(args.hard_tail_threshold)
    base.delay = int(args.delay)
    base.period = int(args.period)
    base.min_delay = int(args.min_delay)
    base.max_delay = int(args.max_delay)
    base.hard_period = int(args.hard_period)
    base.noise_prob = float(args.noise_prob)
    base.sensory_noise_fraction = float(args.sensory_noise_fraction)
    base.min_switch_interval = int(args.min_switch_interval)
    base.max_switch_interval = int(args.max_switch_interval)
    base.runtime_mode = "chunked"
    base.learning_location = "host"
    base.chunk_size_steps = int(chunk_size)
    base.spinnaker_hostname = args.spinnaker_hostname
    base.require_real_hardware = bool(args.require_real_hardware)
    base.stop_on_backend_fallback = bool(args.stop_on_backend_fallback)
    base.stop_on_fail = bool(args.stop_on_fail)
    base.ingest_dir = None
    base.output_dir = None
    return base


def summarize_group(rows: list[dict[str, Any]], *, task: str | None = None, chunk_size: int | None = None) -> dict[str, Any]:
    selected = [
        row
        for row in rows
        if (task is None or row.get("task") == task)
        and (chunk_size is None or int(row.get("chunk_size_steps", -1)) == int(chunk_size))
    ]
    out: dict[str, Any] = {
        "task": task,
        "chunk_size_steps": chunk_size,
        "runs": len(selected),
        "seeds": [row.get("seed") for row in selected],
    }
    keys = [
        "all_accuracy",
        "tail_accuracy",
        "prediction_target_corr",
        "tail_prediction_target_corr",
        "runtime_seconds",
        "runtime_seconds_per_sim_run",
        "sim_run_calls",
        "call_reduction_factor",
        "total_step_spikes",
        "mean_step_spikes",
        "evaluation_count",
        "max_abs_dopamine",
        "mean_abs_dopamine",
    ]
    for key in keys:
        values = [row.get(key) for row in selected]
        out[f"{key}_mean"] = safe_mean(values)
        out[f"{key}_std"] = safe_std(values)
        out[f"{key}_min"] = safe_min(values)
        out[f"{key}_max"] = safe_max(values)
    out["sim_run_failures_sum"] = int(sum(int(row.get("sim_run_failures", 0)) for row in selected))
    out["summary_read_failures_sum"] = int(sum(int(row.get("summary_read_failures", 0)) for row in selected))
    out["synthetic_fallbacks_sum"] = int(sum(int(row.get("synthetic_fallbacks", 0)) for row in selected))
    out["scheduled_input_failures_sum"] = int(sum(int(row.get("scheduled_input_failures", 0)) for row in selected))
    out["spike_readback_failures_sum"] = int(sum(int(row.get("spike_readback_failures", 0)) for row in selected))
    return out


def build_runtime_matrix(summaries: list[dict[str, Any]], tasks: list[str], chunks: list[int]) -> list[dict[str, Any]]:
    matrix: list[dict[str, Any]] = []
    for task in tasks:
        for chunk_size in chunks:
            matrix.append(summarize_group(summaries, task=task, chunk_size=chunk_size))
    return matrix


def recommend_chunk(matrix: list[dict[str, Any]], chunks: list[int]) -> dict[str, Any]:
    """Pick the fastest passing chunk as the default recommendation."""

    viable: list[dict[str, Any]] = []
    for chunk_size in chunks:
        rows = [row for row in matrix if int(row.get("chunk_size_steps") or -1) == int(chunk_size)]
        if not rows:
            continue
        if any(int(row.get("sim_run_failures_sum", 0)) for row in rows):
            continue
        if any(int(row.get("summary_read_failures_sum", 0)) for row in rows):
            continue
        if any(int(row.get("synthetic_fallbacks_sum", 0)) for row in rows):
            continue
        if any((clean_float(row.get("total_step_spikes_min")) or 0.0) <= 0.0 for row in rows):
            continue
        viable.append(
            {
                "chunk_size_steps": int(chunk_size),
                "runtime_seconds_sum": float(sum(clean_float(row.get("runtime_seconds_mean")) or 0.0 for row in rows)),
                "tail_accuracy_min": safe_min([row.get("tail_accuracy_min") for row in rows]),
                "call_reduction_factor": safe_mean([row.get("call_reduction_factor_mean") for row in rows]),
            }
        )
    if not viable:
        return {"chunk_size_steps": None, "reason": "no chunk size passed basic runtime/readback gates"}
    chosen = sorted(viable, key=lambda row: (row["runtime_seconds_sum"], -int(row["chunk_size_steps"])))[0]
    chosen["reason"] = "fastest viable chunk across requested tasks"
    return chosen


def criteria_for_run(
    aggregate: dict[str, Any],
    matrix: list[dict[str, Any]],
    args: argparse.Namespace,
) -> list[dict[str, Any]]:
    expected_runs = len(args.tasks) * len(args.chunk_sizes) * len(args.seeds)
    criteria = [
        criterion("all requested task/chunk/seed runs completed", aggregate.get("runs"), "==", expected_runs, int(aggregate.get("runs", 0)) == expected_runs),
        criterion("sim.run failures sum", aggregate.get("sim_run_failures_sum"), "==", 0, int(aggregate.get("sim_run_failures_sum", 0)) == 0),
        criterion("summary read failures sum", aggregate.get("summary_read_failures_sum"), "==", 0, int(aggregate.get("summary_read_failures_sum", 0)) == 0),
        criterion("synthetic fallback sum", aggregate.get("synthetic_fallbacks_sum"), "==", 0, int(aggregate.get("synthetic_fallbacks_sum", 0)) == 0),
        criterion("scheduled input failures sum", aggregate.get("scheduled_input_failures_sum"), "==", 0, int(aggregate.get("scheduled_input_failures_sum", 0)) == 0),
        criterion("spike readback failures sum", aggregate.get("spike_readback_failures_sum"), "==", 0, int(aggregate.get("spike_readback_failures_sum", 0)) == 0),
        criterion("real spike readback in every run", aggregate.get("total_step_spikes_min"), ">", 0, (clean_float(aggregate.get("total_step_spikes_min")) or 0.0) > 0.0),
        criterion("runtime documented in every run", aggregate.get("runtime_seconds_min"), "is finite", True, finite(aggregate.get("runtime_seconds_min"))),
        criterion("confirmed delayed-credit setting used", args.delayed_readout_lr, "==", DEFAULT_DELAYED_LR, abs(float(args.delayed_readout_lr) - DEFAULT_DELAYED_LR) < 1e-12),
    ]

    for chunk_size in args.chunk_sizes:
        expected_calls = int(math.ceil(float(args.steps) / float(chunk_size)))
        actual_calls = [
            clean_float(row.get("sim_run_calls_mean"))
            for row in matrix
            if int(row.get("chunk_size_steps") or -1) == int(chunk_size)
        ]
        calls_ok = bool(actual_calls) and all(int(v or -1) == expected_calls for v in actual_calls)
        criteria.append(
            criterion(
                f"chunk {chunk_size} sim.run calls match plan",
                actual_calls,
                "==",
                expected_calls,
                calls_ok,
            )
        )

    delayed_rows = [row for row in matrix if row.get("task") == "delayed_cue"]
    if delayed_rows:
        delayed_min = safe_min([row.get("tail_accuracy_min") for row in delayed_rows])
        criteria.append(
            criterion(
                "delayed_cue tail accuracy remains above repaired threshold",
                delayed_min,
                ">=",
                args.delayed_tail_threshold,
                (delayed_min or 0.0) >= float(args.delayed_tail_threshold),
            )
        )

    hard_rows = [row for row in matrix if row.get("task") == "hard_noisy_switching"]
    if hard_rows:
        hard_min = safe_min([row.get("tail_accuracy_min") for row in hard_rows])
        criteria.append(
            criterion(
                "hard_noisy_switching tail accuracy remains above transfer threshold",
                hard_min,
                ">=",
                args.hard_tail_threshold,
                (hard_min or 0.0) >= float(args.hard_tail_threshold),
            )
        )
        criteria.append(
            criterion(
                "hard_noisy_switching tail correlation is finite",
                [row.get("tail_prediction_target_corr_mean") for row in hard_rows],
                "is finite",
                True,
                all(finite(row.get("tail_prediction_target_corr_mean")) for row in hard_rows),
            )
        )

    if 25 in args.chunk_sizes:
        baseline_rows = [row for row in matrix if int(row.get("chunk_size_steps") or -1) == 25]
        for chunk_size in args.chunk_sizes:
            rows = [row for row in matrix if int(row.get("chunk_size_steps") or -1) == int(chunk_size)]
            deltas: list[float] = []
            for row in rows:
                base = next((b for b in baseline_rows if b.get("task") == row.get("task")), None)
                if base is None:
                    continue
                row_tail = clean_float(row.get("tail_accuracy_mean"))
                base_tail = clean_float(base.get("tail_accuracy_mean"))
                if row_tail is not None and base_tail is not None:
                    deltas.append(abs(row_tail - base_tail))
            max_delta = max(deltas) if deltas else None
            criteria.append(
                criterion(
                    f"chunk {chunk_size} tail accuracy close to chunk 25 baseline",
                    max_delta,
                    "<=",
                    args.max_tail_delta_vs_chunk25,
                    max_delta is not None and max_delta <= float(args.max_tail_delta_vs_chunk25),
                )
            )
    return criteria


def plot_runtime_matrix(matrix: list[dict[str, Any]], output_path: Path) -> None:
    if plt is None or not matrix:
        return
    tasks = list(dict.fromkeys(str(row.get("task")) for row in matrix))
    chunks = sorted({int(row.get("chunk_size_steps") or 0) for row in matrix if row.get("chunk_size_steps") is not None})
    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    for task in tasks:
        rows = [row for row in matrix if row.get("task") == task]
        rows = sorted(rows, key=lambda row: int(row.get("chunk_size_steps") or 0))
        xs = [int(row.get("chunk_size_steps") or 0) for row in rows]
        axes[0].plot(xs, [row.get("runtime_seconds_mean") or 0.0 for row in rows], marker="o", label=task)
        axes[1].plot(xs, [row.get("tail_accuracy_mean") or 0.0 for row in rows], marker="o", label=task)
        axes[2].plot(xs, [row.get("total_step_spikes_mean") or 0.0 for row in rows], marker="o", label=task)
    axes[0].set_title("Runtime seconds")
    axes[1].set_title("Tail accuracy")
    axes[1].set_ylim(0, 1.05)
    axes[2].set_title("Spike readback")
    for ax in axes:
        ax.set_xlabel("chunk size")
        ax.set_xticks(chunks)
        ax.grid(alpha=0.25)
        ax.legend()
    fig.suptitle(TIER)
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def write_jobmanager_capsule(output_dir: Path, args: argparse.Namespace) -> dict[str, str]:
    capsule_dir = output_dir / "jobmanager_capsule"
    capsule_dir.mkdir(parents=True, exist_ok=True)
    config_path = capsule_dir / "capsule_config.json"
    command_path = capsule_dir / "run_tier4_18a_on_jobmanager.sh"
    readme_path = capsule_dir / "README_JOBMANAGER.md"
    expected_path = capsule_dir / "expected_outputs.json"

    command = [
        "python3 experiments/tier4_18a_chunked_runtime_baseline.py",
        "--mode run-hardware",
        "--require-real-hardware",
        "--stop-on-fail",
        f"--tasks {','.join(args.tasks)}",
        f"--seeds {','.join(str(seed) for seed in args.seeds)}",
        f"--chunk-sizes {','.join(str(size) for size in args.chunk_sizes)}",
        f"--steps {args.steps}",
        f"--population-size {args.population_size}",
        f"--delayed-readout-lr {args.delayed_readout_lr}",
        f"--readout-lr {args.readout_lr}",
        "--output-dir \"$OUT_DIR\"",
    ]
    payload = {
        "tier": TIER,
        "mode": "prepare",
        "tasks": args.tasks,
        "seeds": args.seeds,
        "chunk_sizes": args.chunk_sizes,
        "steps": args.steps,
        "population_size": args.population_size,
        "runtime_mode": "chunked",
        "learning_location": "host",
        "delayed_readout_lr": args.delayed_readout_lr,
        "claim_boundary": "Prepared capsule is not hardware evidence. Tier 4.18a measures v0.7 chunked-host runtime/resource cost and stability; it is not a new learning or scaling claim.",
    }
    write_json(config_path, payload)
    command_path.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                "",
                "# Run from the repository root inside EBRAINS/JobManager with real SpiNNaker access.",
                "OUT_DIR=${1:-tier4_18a_job_output}",
                " \\\n  ".join(command),
                "",
            ]
        ),
        encoding="utf-8",
    )
    command_path.chmod(0o755)
    expected_path.write_text(
        json.dumps(
            {
                "required": [
                    "tier4_18a_results.json",
                    "tier4_18a_report.md",
                    "tier4_18a_summary.csv",
                    "tier4_18a_runtime_matrix.csv",
                    "tier4_18a_runtime_matrix.png",
                    "spinnaker_hardware_<task>_chunk<chunk>_seed<seed>_timeseries.csv",
                    "spinnaker_hardware_<task>_chunk<chunk>_seed<seed>_timeseries.png",
                ],
                "pass_requires": [
                    "sim_run_failures_sum=0",
                    "summary_read_failures_sum=0",
                    "synthetic_fallbacks_sum=0",
                    "scheduled_input_failures_sum=0",
                    "spike_readback_failures_sum=0",
                    "real spike readback > 0 in every run",
                    "task metrics remain above Tier 4.16 thresholds",
                    "runtime and sim.run call counts documented for every chunk",
                ],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    readme_path.write_text(
        "\n".join(
            [
                "# Tier 4.18a v0.7 Chunked Hardware Runtime Baseline",
                "",
                "This capsule measures runtime/resource behavior for the already-proven v0.7 chunked-host hardware path.",
                "",
                "## Run",
                "",
                "```bash",
                "bash controlled_test_output/<tier4_18a_prepared_run>/jobmanager_capsule/run_tier4_18a_on_jobmanager.sh /tmp/tier4_18a_job_output",
                "```",
                "",
                "## Boundary",
                "",
                "A prepared capsule is not evidence. A pass requires real `pyNN.spiNNaker`, zero fallback/failures, real spike readback, and task metrics above threshold.",
                "",
                "Tier 4.18a is runtime/resource characterization, not a new learning claim, not hardware scaling, and not on-chip learning.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return {
        "capsule_dir": str(capsule_dir),
        "capsule_config_json": str(config_path),
        "jobmanager_run_script": str(command_path),
        "jobmanager_readme": str(readme_path),
        "expected_outputs_json": str(expected_path),
    }


def write_report(
    *,
    path: Path,
    mode: str,
    status: str,
    output_dir: Path,
    summary: dict[str, Any],
    matrix: list[dict[str, Any]],
    criteria: list[dict[str, Any]],
    artifacts: dict[str, str],
    failure_reason: str = "",
) -> None:
    lines = [
        "# Tier 4.18a v0.7 Chunked Hardware Runtime Baseline Findings",
        "",
        f"- Generated: `{utc_now()}`",
        f"- Mode: `{mode}`",
        f"- Status: **{status.upper()}**",
        f"- Output directory: `{output_dir}`",
        "",
        "Tier 4.18a characterizes runtime/resource cost for the v0.7 chunked-host hardware path that already passed Tier 4.16a and Tier 4.16b.",
        "",
        "## Claim Boundary",
        "",
        "- `PREPARED` means the JobManager capsule exists locally; it is not hardware evidence.",
        "- `PASS` requires real `pyNN.spiNNaker`, zero fallback/failures, real spike readback, documented runtime/call counts, and task metrics above threshold.",
        "- This is runtime/resource characterization, not hardware scaling, not on-chip learning, and not a new superiority claim.",
        "",
        "## Summary",
        "",
    ]
    for key in [
        "hardware_run_attempted",
        "hardware_target_configured",
        "backend",
        "tasks",
        "seeds",
        "chunk_sizes",
        "runs",
        "steps",
        "population_size",
        "runtime_mode",
        "learning_location",
        "sim_run_failures_sum",
        "summary_read_failures_sum",
        "synthetic_fallbacks_sum",
        "scheduled_input_failures_sum",
        "spike_readback_failures_sum",
        "total_step_spikes_min",
        "runtime_seconds_mean",
        "recommended_chunk_size",
        "recommendation_reason",
        "jobmanager_cli",
    ]:
        if key in summary:
            lines.append(f"- {key}: `{markdown_value(summary.get(key))}`")
    if failure_reason:
        lines.extend(["", f"Failure: {failure_reason}", ""])
    if matrix:
        lines.extend(
            [
                "",
                "## Runtime Matrix",
                "",
                "| Task | Chunk | Runs | sim.run Calls | Runtime Mean | Tail Acc Mean | Tail Acc Min | Spike Min |",
                "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for row in matrix:
            lines.append(
                "| "
                f"`{row.get('task')}` | {markdown_value(row.get('chunk_size_steps'))} | {markdown_value(row.get('runs'))} | "
                f"{markdown_value(row.get('sim_run_calls_mean'))} | {markdown_value(row.get('runtime_seconds_mean'))} | "
                f"{markdown_value(row.get('tail_accuracy_mean'))} | {markdown_value(row.get('tail_accuracy_min'))} | "
                f"{markdown_value(row.get('total_step_spikes_min'))} |"
            )
    if criteria:
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
                "| "
                f"{item['name']} | {markdown_value(item['value'])} | "
                f"{item['operator']} {markdown_value(item['threshold'])} | "
                f"{'yes' if item['passed'] else 'no'} |"
            )
    lines.extend(["", "## Artifacts", ""])
    for label, artifact in artifacts.items():
        lines.append(f"- `{label}`: `{artifact}`")
    if artifacts.get("runtime_matrix_png"):
        lines.extend(["", "![tier4_18a_runtime_matrix](tier4_18a_runtime_matrix.png)", ""])
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_latest(output_dir: Path, report_path: Path, manifest_path: Path, status: str) -> None:
    write_json(
        ROOT / "controlled_test_output" / "tier4_18a_latest_manifest.json",
        {
            "generated_at_utc": utc_now(),
            "manifest": str(manifest_path),
            "report": str(report_path),
            "output_dir": str(output_dir),
            "status": status,
            "canonical": False,
            "claim": "Latest Tier 4.18a runtime/resource characterization; promote only after hardware review.",
        },
    )


def prepare_capsule(args: argparse.Namespace, output_dir: Path) -> int:
    env = collect_environment(args)
    capsule_artifacts = write_jobmanager_capsule(output_dir, args)
    plans = [
        make_runtime_plan(
            runtime_mode="chunked",
            learning_location="host",
            chunk_size_steps=chunk_size,
            total_steps=args.steps,
            dt_seconds=args.dt_seconds,
        )
        for chunk_size in args.chunk_sizes
    ]
    summary = {
        "mode": "prepare",
        "backend": "pyNN.spiNNaker",
        "hardware_run_attempted": False,
        "hardware_target_configured": bool(env.get("hardware_target_configured")),
        "jobmanager_cli": env.get("jobmanager_cli"),
        "tasks": args.tasks,
        "seeds": args.seeds,
        "chunk_sizes": args.chunk_sizes,
        "steps": args.steps,
        "population_size": args.population_size,
        "runtime_mode": "chunked",
        "learning_location": "host",
        "delayed_readout_lr": args.delayed_readout_lr,
        "capsule_dir": capsule_artifacts.get("capsule_dir"),
    }
    criteria = [
        criterion("capsule directory exists", capsule_artifacts.get("capsule_dir"), "exists", True, Path(capsule_artifacts["capsule_dir"]).exists()),
        criterion("delayed_cue included", "delayed_cue" in args.tasks, "==", True, "delayed_cue" in args.tasks),
        criterion("hard_noisy_switching included", "hard_noisy_switching" in args.tasks, "==", True, "hard_noisy_switching" in args.tasks),
        criterion("chunk sizes include 10,25,50", args.chunk_sizes, "contains", [10, 25, 50], all(size in args.chunk_sizes for size in [10, 25, 50])),
        criterion("confirmed delayed-credit setting selected", args.delayed_readout_lr, "==", DEFAULT_DELAYED_LR, abs(float(args.delayed_readout_lr) - DEFAULT_DELAYED_LR) < 1e-12),
        criterion("all runtime plans implemented", [plan.implementation_stage for plan in plans], "implemented", True, all(plan.implemented for plan in plans)),
    ]
    status, failure = pass_fail(criteria)
    status = "prepared" if status == "pass" else "fail"
    manifest_path = output_dir / "tier4_18a_results.json"
    report_path = output_dir / "tier4_18a_report.md"
    summary_csv_path = output_dir / "tier4_18a_summary.csv"
    write_json(
        manifest_path,
        {
            "generated_at_utc": utc_now(),
            "tier": TIER,
            "mode": "prepare",
            "status": status,
            "failure_reason": failure,
            "summary": summary,
            "criteria": criteria,
            "environment": env,
            "artifacts": capsule_artifacts,
            "runtime_plans": [plan.__dict__ for plan in plans],
        },
    )
    write_summary_csv(summary_csv_path, [summary])
    write_report(
        path=report_path,
        mode="prepare",
        status=status,
        output_dir=output_dir,
        summary=summary,
        matrix=[],
        criteria=criteria,
        artifacts={"manifest_json": str(manifest_path), "summary_csv": str(summary_csv_path), **capsule_artifacts},
        failure_reason=failure,
    )
    write_latest(output_dir, report_path, manifest_path, status)
    return 0 if status == "prepared" else 1


def run_hardware(args: argparse.Namespace, output_dir: Path) -> int:
    run_started_epoch = time.time()
    env = collect_environment(args)
    hardware_target_configured = bool(env.get("hardware_target_configured"))
    virtual_board_requested = truthy((env.get("spynnaker_config") or {}).get("virtual_board"))
    if args.require_real_hardware and virtual_board_requested:
        failure = "sPyNNaker is configured for virtual_board=True. Refusing to run virtual-board output as Tier 4.18a hardware."
        summary = {
            "mode": "run-hardware",
            "backend": "pyNN.spiNNaker",
            "hardware_run_attempted": False,
            "hardware_target_configured": False,
            "jobmanager_cli": env.get("jobmanager_cli"),
            "tasks": args.tasks,
            "seeds": args.seeds,
            "chunk_sizes": args.chunk_sizes,
        }
        criteria = [criterion("real SpiNNaker target configured", {"hardware_target_configured": hardware_target_configured, "virtual_board": True}, "==", {"virtual_board": False}, False)]
        manifest_path = output_dir / "tier4_18a_results.json"
        report_path = output_dir / "tier4_18a_report.md"
        summary_csv_path = output_dir / "tier4_18a_summary.csv"
        write_json(manifest_path, {"generated_at_utc": utc_now(), "tier": TIER, "mode": "run-hardware", "status": "blocked", "failure_reason": failure, "summary": summary, "criteria": criteria, "environment": env})
        write_summary_csv(summary_csv_path, [summary])
        write_report(path=report_path, mode="run-hardware", status="blocked", output_dir=output_dir, summary=summary, matrix=[], criteria=criteria, artifacts={"manifest_json": str(manifest_path), "summary_csv": str(summary_csv_path)}, failure_reason=failure)
        write_latest(output_dir, report_path, manifest_path, "blocked")
        return 1

    summaries: list[dict[str, Any]] = []
    artifacts: dict[str, str] = {}
    failure_reason = ""
    failure_traceback = ""
    hardware_run_attempted = False

    for task in args.tasks:
        for chunk_size in args.chunk_sizes:
            for seed in args.seeds:
                try:
                    hardware_run_attempted = True
                    child = child_args(args, task=task, seed=seed, chunk_size=chunk_size)
                    rows, summary = run_chunked_spinnaker_task_seed(task_name=task, seed=seed, args=child)
                except Exception as exc:
                    failure_reason = f"task {task} chunk {chunk_size} seed {seed} raised {type(exc).__name__}: {exc}"
                    failure_traceback = traceback.format_exc()
                    trace_path = output_dir / f"{task}_chunk{chunk_size}_seed{seed}_failure_traceback.txt"
                    trace_path.write_text(failure_traceback, encoding="utf-8")
                    artifacts[f"{task}_chunk{chunk_size}_seed{seed}_failure_traceback"] = str(trace_path)
                    if args.stop_on_fail:
                        break
                    continue

                for row in rows:
                    row["tier"] = TIER
                    row["test_name"] = f"tier4_18a_{task}_chunk{chunk_size}"
                    row["chunk_size_steps"] = int(chunk_size)
                    row["runtime_mode"] = "chunked"
                    row["learning_location"] = "host"
                summary.update(
                    {
                        "tier": TIER,
                        "test_name": f"tier4_18a_{task}_chunk{chunk_size}",
                        "task": task,
                        "seed": int(seed),
                        "chunk_size_steps": int(chunk_size),
                        "runtime_mode": "chunked",
                        "learning_location": "host",
                        "runtime_seconds_per_sim_run": (
                            float(summary.get("runtime_seconds", 0.0)) / float(summary.get("sim_run_calls", 0))
                            if int(summary.get("sim_run_calls", 0)) > 0
                            else None
                        ),
                    }
                )
                csv_path = output_dir / f"spinnaker_hardware_{task}_chunk{chunk_size}_seed{seed}_timeseries.csv"
                png_path = output_dir / f"spinnaker_hardware_{task}_chunk{chunk_size}_seed{seed}_timeseries.png"
                write_csv(csv_path, rows)
                switch_step = None
                task_meta = summary.get("task_metadata", {})
                if isinstance(task_meta, dict) and task_meta.get("switch_steps"):
                    switches = task_meta.get("switch_steps") or []
                    switch_step = int(switches[1]) if len(switches) > 1 else None
                plot_case(rows, png_path, f"Tier 4.18a {task} chunk {chunk_size} seed {seed}", switch_step=switch_step)
                artifacts[f"{task}_chunk{chunk_size}_seed{seed}_timeseries_csv"] = str(csv_path)
                if png_path.exists():
                    artifacts[f"{task}_chunk{chunk_size}_seed{seed}_timeseries_png"] = str(png_path)
                summaries.append(summary)
            if failure_reason and args.stop_on_fail:
                break
        if failure_reason and args.stop_on_fail:
            break

    matrix = build_runtime_matrix(summaries, args.tasks, args.chunk_sizes)
    recommendation = recommend_chunk(matrix, args.chunk_sizes)
    aggregate = summarize_group(summaries)
    aggregate.update(
        {
            "mode": "run-hardware",
            "backend": "pyNN.spiNNaker",
            "hardware_run_attempted": hardware_run_attempted,
            "hardware_target_configured": hardware_target_configured,
            "jobmanager_cli": env.get("jobmanager_cli"),
            "tasks": args.tasks,
            "seeds": args.seeds,
            "chunk_sizes": args.chunk_sizes,
            "steps": args.steps,
            "population_size": args.population_size,
            "runtime_mode": "chunked",
            "learning_location": "host",
            "recommended_chunk_size": recommendation.get("chunk_size_steps"),
            "recommendation_reason": recommendation.get("reason"),
        }
    )
    criteria = criteria_for_run(aggregate, matrix, args)
    status, failure = pass_fail(criteria)
    if failure_reason:
        status = "fail"
        failure = failure_reason if not failure else f"{failure}; {failure_reason}"

    matrix_path = output_dir / "tier4_18a_runtime_matrix.csv"
    summary_path = output_dir / "tier4_18a_summary.csv"
    report_path = output_dir / "tier4_18a_report.md"
    manifest_path = output_dir / "tier4_18a_results.json"
    plot_path = output_dir / "tier4_18a_runtime_matrix.png"
    write_summary_csv(matrix_path, matrix)
    write_summary_csv(summary_path, summaries if summaries else [aggregate])
    plot_runtime_matrix(matrix, plot_path)
    if plot_path.exists():
        artifacts["runtime_matrix_png"] = str(plot_path)
    artifacts.update(collect_recent_spinnaker_reports(output_dir, run_started_epoch, max_reports=args.max_report_dirs))
    write_json(
        manifest_path,
        {
            "generated_at_utc": utc_now(),
            "tier": TIER,
            "mode": "run-hardware",
            "status": status,
            "failure_reason": failure,
            "summary": aggregate,
            "runtime_matrix": matrix,
            "seed_summaries": summaries,
            "criteria": criteria,
            "environment": env,
            "artifacts": {"summary_csv": str(summary_path), "runtime_matrix_csv": str(matrix_path), **artifacts},
        },
    )
    write_report(
        path=report_path,
        mode="run-hardware",
        status=status,
        output_dir=output_dir,
        summary=aggregate,
        matrix=matrix,
        criteria=criteria,
        artifacts={"manifest_json": str(manifest_path), "summary_csv": str(summary_path), "runtime_matrix_csv": str(matrix_path), **artifacts},
        failure_reason=failure,
    )
    write_latest(output_dir, report_path, manifest_path, status)
    return 0 if status == "pass" else 1


def ingest_results(args: argparse.Namespace, output_dir: Path) -> int:
    if args.ingest_dir is None:
        raise SystemExit("--ingest-dir is required in ingest mode")
    source = args.ingest_dir.resolve()
    if not source.exists():
        raise SystemExit(f"ingest source does not exist: {source}")
    output_dir.mkdir(parents=True, exist_ok=True)
    for item in source.iterdir():
        dest = output_dir / item.name
        if item.is_dir():
            shutil.copytree(item, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dest)
    manifest_path = output_dir / "tier4_18a_results.json"
    report_path = output_dir / "tier4_18a_report.md"
    if not manifest_path.exists():
        raise SystemExit(f"ingested directory does not contain tier4_18a_results.json: {source}")
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    status = str(data.get("status", "unknown"))
    write_latest(output_dir, report_path, manifest_path, status)
    return 0 if status == "pass" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare, run, or ingest Tier 4.18a chunked hardware runtime baseline.")
    parser.add_argument("--mode", choices=["prepare", "run-hardware", "ingest"], default="prepare")
    parser.add_argument("--tasks", type=parse_tasks, default=parse_tasks(DEFAULT_TASKS))
    parser.add_argument("--seeds", type=parse_ints, default=parse_ints(DEFAULT_SEEDS))
    parser.add_argument("--chunk-sizes", type=parse_ints, default=parse_ints(DEFAULT_CHUNKS))
    parser.add_argument("--steps", type=int, default=DEFAULT_STEPS)
    parser.add_argument("--population-size", type=int, default=8)
    parser.add_argument("--amplitude", type=float, default=DEFAULT_AMPLITUDE)
    parser.add_argument("--dt-seconds", type=float, default=DEFAULT_DT_SECONDS)
    parser.add_argument("--timestep-ms", type=float, default=1.0)
    parser.add_argument("--readout-lr", type=float, default=0.10)
    parser.add_argument("--delayed-readout-lr", type=float, default=DEFAULT_DELAYED_LR)
    parser.add_argument("--base-current-na", type=float, default=1.4)
    parser.add_argument("--cue-current-gain-na", type=float, default=0.2)
    parser.add_argument("--min-current-na", type=float, default=0.0)
    parser.add_argument("--delayed-tail-threshold", type=float, default=0.85)
    parser.add_argument("--hard-tail-threshold", type=float, default=0.50)
    parser.add_argument("--max-tail-delta-vs-chunk25", type=float, default=0.10)
    parser.add_argument("--delay", type=int, default=5)
    parser.add_argument("--period", type=int, default=8)
    parser.add_argument("--min-delay", type=int, default=DEFAULT_HARD_MIN_DELAY)
    parser.add_argument("--max-delay", type=int, default=DEFAULT_HARD_MAX_DELAY)
    parser.add_argument("--hard-period", type=int, default=DEFAULT_HARD_PERIOD)
    parser.add_argument("--noise-prob", type=float, default=DEFAULT_HARD_NOISE_PROB)
    parser.add_argument("--sensory-noise-fraction", type=float, default=DEFAULT_HARD_SENSORY_NOISE_FRACTION)
    parser.add_argument("--min-switch-interval", type=int, default=DEFAULT_HARD_MIN_SWITCH_INTERVAL)
    parser.add_argument("--max-switch-interval", type=int, default=DEFAULT_HARD_MAX_SWITCH_INTERVAL)
    parser.add_argument("--spinnaker-hostname", default=None)
    parser.add_argument("--require-real-hardware", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--stop-on-backend-fallback", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--stop-on-fail", action="store_true")
    parser.add_argument("--max-report-dirs", type=int, default=12)
    parser.add_argument("--ingest-dir", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.steps <= 0:
        parser.error("--steps must be positive")
    if args.population_size <= 0:
        parser.error("--population-size must be positive")
    if any(size <= 0 for size in args.chunk_sizes):
        parser.error("--chunk-sizes must all be positive")
    if 25 not in args.chunk_sizes and args.mode != "ingest":
        parser.error("--chunk-sizes must include 25 so Tier 4.18a has the v0.7 reference chunk")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = "prepared" if args.mode == "prepare" else args.mode.replace("-", "_")
    output_dir = args.output_dir or (ROOT / "controlled_test_output" / f"tier4_18a_{timestamp}_{suffix}")
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.mode == "prepare":
        return prepare_capsule(args, output_dir)
    if args.mode == "run-hardware":
        return run_hardware(args, output_dir)
    if args.mode == "ingest":
        return ingest_results(args, output_dir)
    raise AssertionError(args.mode)


if __name__ == "__main__":
    raise SystemExit(main())
