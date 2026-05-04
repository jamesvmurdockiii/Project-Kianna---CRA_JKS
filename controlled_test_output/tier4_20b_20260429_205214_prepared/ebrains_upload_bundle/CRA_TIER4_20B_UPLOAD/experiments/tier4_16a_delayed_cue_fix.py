#!/usr/bin/env python3
"""Tier 4.16a delayed-cue metric/task repair.

The first Tier 4.16 hardware attempt failed `delayed_cue`, and local replay
showed the same failure in NEST/Brian2. The immediate issue was not hardware
execution; the 120-step task had only three tail evaluation events.

This harness keeps the learning rule fixed (`delayed_lr_0_20`) and repairs only
the local confirmation design by running longer delayed-cue traces before any
new hardware allocation.
"""

from __future__ import annotations

import argparse
import math
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from tier2_learning import criterion, markdown_value, pass_fail, write_csv, write_json  # noqa: E402
from tier4_16a_delayed_cue_debug import (  # noqa: E402
    DEFAULT_DELAYED_LR,
    DEFAULT_POPULATION_SIZE,
    DEFAULT_READOUT_LR,
    DEFAULT_SEEDS,
    aggregate_backend_summaries,
    extract_tail_events,
    parse_csv_list,
    parse_seeds,
    plot_debug,
    run_backend_seed,
    utc_now,
)


TIER = "Tier 4.16a-fix - Delayed Cue Metric / Task Repair"
OUTPUT_ROOT = ROOT / "controlled_test_output"
DEFAULT_BACKENDS = "nest,brian2"
DEFAULT_STEPS = 1500
DEFAULT_TAIL_THRESHOLD = 0.85
DEFAULT_MIN_TAIL_EVENTS = 30


def parse_run_lengths(value: str) -> list[int]:
    lengths = [int(item) for item in parse_csv_list(value)]
    if any(length <= 0 for length in lengths):
        raise argparse.ArgumentTypeError("run lengths must be positive")
    return lengths


def finite_numbers(values: list[Any]) -> list[float]:
    out: list[float] = []
    for value in values:
        try:
            f = float(value)
        except Exception:
            continue
        if math.isfinite(f):
            out.append(f)
    return out


def group_by_length_backend(summary_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[int, str], list[dict[str, Any]]] = {}
    for row in summary_rows:
        groups.setdefault((int(row["steps"]), str(row["backend_key"])), []).append(row)
    out: list[dict[str, Any]] = []
    for (steps, backend_key), rows in sorted(groups.items()):
        result = {
            "steps": steps,
            "backend_key": backend_key,
            "backend": rows[0].get("backend"),
            "runs": len(rows),
            "seeds": [r.get("seed") for r in rows],
        }
        for key in [
            "tail_accuracy",
            "all_accuracy",
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
            values = finite_numbers([r.get(key) for r in rows])
            result[f"{key}_mean"] = float(np.mean(values)) if values else None
            result[f"{key}_min"] = float(np.min(values)) if values else None
            result[f"{key}_max"] = float(np.max(values)) if values else None
        result["failed_seeds_at_threshold"] = [
            r.get("seed")
            for r in rows
            if r.get("tail_accuracy") is None
            or float(r.get("tail_accuracy")) < DEFAULT_TAIL_THRESHOLD
        ]
        result["sim_run_failures_sum"] = int(
            sum(int(r.get("sim_run_failures", 0) or 0) for r in rows)
        )
        result["summary_read_failures_sum"] = int(
            sum(int(r.get("summary_read_failures", 0) or 0) for r in rows)
        )
        result["synthetic_fallbacks_sum"] = int(
            sum(int(r.get("synthetic_fallbacks", 0) or 0) for r in rows)
        )
        out.append(result)
    return out


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Tier 4.16a delayed-cue local fix.")
    parser.add_argument("--backends", default=DEFAULT_BACKENDS)
    parser.add_argument("--seeds", type=parse_seeds, default=parse_seeds(DEFAULT_SEEDS))
    parser.add_argument("--run-lengths", type=parse_run_lengths, default=[DEFAULT_STEPS])
    parser.add_argument("--population-size", type=int, default=DEFAULT_POPULATION_SIZE)
    parser.add_argument("--amplitude", type=float, default=0.01)
    parser.add_argument("--dt-seconds", type=float, default=0.05)
    parser.add_argument("--readout-lr", type=float, default=DEFAULT_READOUT_LR)
    parser.add_argument("--delayed-readout-lr", type=float, default=DEFAULT_DELAYED_LR)
    parser.add_argument("--delay", type=int, default=5)
    parser.add_argument("--period", type=int, default=8)
    parser.add_argument("--tail-threshold", type=float, default=DEFAULT_TAIL_THRESHOLD)
    parser.add_argument("--min-tail-events", type=int, default=DEFAULT_MIN_TAIL_EVENTS)
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser


def write_report(
    *,
    path: Path,
    output_dir: Path,
    status: str,
    criteria: list[dict[str, Any]],
    aggregate_rows: list[dict[str, Any]],
    artifacts: dict[str, str],
    diagnosis: dict[str, Any],
) -> None:
    lines = [
        "# Tier 4.16a Delayed Cue Metric / Task Repair",
        "",
        f"- Generated: `{utc_now()}`",
        f"- Status: **{status.upper()}**",
        f"- Output directory: `{output_dir}`",
        "",
        "This local-only repair keeps `delayed_lr_0_20` fixed and increases delayed-cue run length so the tail metric has enough evaluation events.",
        "",
        "## Diagnosis",
        "",
        f"- diagnosis: `{diagnosis['diagnosis']}`",
        f"- next_step: `{diagnosis['next_step']}`",
        f"- min_tail_event_count: `{diagnosis['min_tail_event_count']}`",
        f"- tail_threshold: `{diagnosis['tail_threshold']}`",
        "",
        "## Backend Summary",
        "",
        "| Steps | Backend | Runs | Tail Acc Mean | Tail Acc Min | Tail Events Min | Failed Seeds | Runtime Mean |",
        "| ---: | --- | ---: | ---: | ---: | ---: | --- | ---: |",
    ]
    for row in aggregate_rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    markdown_value(row.get("steps")),
                    str(row.get("backend_key")),
                    markdown_value(row.get("runs")),
                    markdown_value(row.get("tail_accuracy_mean")),
                    markdown_value(row.get("tail_accuracy_min")),
                    markdown_value(row.get("tail_event_count_min")),
                    str(row.get("failed_seeds_at_threshold")),
                    markdown_value(row.get("runtime_seconds_mean")),
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
            f"| {item['name']} | {markdown_value(item['value'])} | {item['operator']} {markdown_value(item['threshold'])} | {'yes' if item['passed'] else 'no'} |"
        )
    lines.extend(["", "## Artifacts", ""])
    for key, value in artifacts.items():
        lines.append(f"- `{key}`: `{value}`")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = build_parser().parse_args()
    backends = parse_csv_list(args.backends)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    output_dir = (
        args.output_dir
        if args.output_dir is not None
        else OUTPUT_ROOT / f"tier4_16a_fix_{timestamp}"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    summary_rows: list[dict[str, Any]] = []
    tail_events: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for steps in args.run_lengths:
        for backend in backends:
            for seed in args.seeds:
                run_args = argparse.Namespace(**vars(args))
                run_args.steps = int(steps)
                try:
                    rows, summary, events = run_backend_seed(
                        backend_key=backend,
                        seed=seed,
                        args=run_args,
                    )
                    rows_path = (
                        output_dir
                        / f"tier4_16a_fix_steps{steps}_{backend}_seed{seed}_timeseries.csv"
                    )
                    write_csv(rows_path, rows)
                    summary["repair_run"] = True
                    summary_rows.append(summary)
                    tail_events.extend(events)
                except Exception as exc:  # pragma: no cover - diagnostic capture
                    failures.append(
                        {
                            "steps": steps,
                            "backend_key": backend,
                            "seed": seed,
                            "error_type": type(exc).__name__,
                            "error": str(exc),
                        }
                    )

    aggregate_rows = group_by_length_backend(summary_rows)
    expected_runs = len(args.run_lengths) * len(backends) * len(args.seeds)
    tail_values = finite_numbers([row.get("tail_accuracy") for row in summary_rows])
    tail_event_values = finite_numbers([row.get("tail_event_count") for row in summary_rows])
    failed_runs = [
        {
            "steps": row.get("steps"),
            "backend_key": row.get("backend_key"),
            "seed": row.get("seed"),
            "tail_accuracy": row.get("tail_accuracy"),
            "tail_event_count": row.get("tail_event_count"),
        }
        for row in summary_rows
        if row.get("tail_accuracy") is None
        or float(row.get("tail_accuracy")) < float(args.tail_threshold)
    ]
    backend_failures = [
        row
        for row in aggregate_rows
        if row.get("sim_run_failures_sum", 0)
        or row.get("summary_read_failures_sum", 0)
        or row.get("synthetic_fallbacks_sum", 0)
    ]
    min_tail_accuracy = min(tail_values) if tail_values else None
    min_tail_events = int(min(tail_event_values)) if tail_event_values else 0
    diagnosis = {
        "diagnosis": "longer_delayed_cue_local_pass" if not failed_runs and not failures else "longer_delayed_cue_local_fail",
        "next_step": "run Tier 4.16b hard_noisy_switching hardware after delayed_cue repeat pass" if not failed_runs and not failures else "debug delayed_cue locally before hardware",
        "failed_runs": failed_runs,
        "backend_failures": backend_failures,
        "software_failures": failures,
        "min_tail_accuracy": min_tail_accuracy,
        "min_tail_event_count": min_tail_events,
        "tail_threshold": float(args.tail_threshold),
        "min_tail_events_threshold": int(args.min_tail_events),
    }
    criteria = [
        criterion("software matrix completed", len(summary_rows), "==", expected_runs, len(summary_rows) == expected_runs),
        criterion("no backend execution failures", len(failures), "==", 0, len(failures) == 0),
        criterion("zero fallback/failure counters", len(backend_failures), "==", 0, len(backend_failures) == 0),
        criterion("minimum tail event count", min_tail_events, ">=", int(args.min_tail_events), min_tail_events >= int(args.min_tail_events)),
        criterion("minimum tail accuracy", min_tail_accuracy, ">=", float(args.tail_threshold), min_tail_accuracy is not None and min_tail_accuracy >= float(args.tail_threshold)),
        criterion("confirmed delayed-credit setting used", float(args.delayed_readout_lr), "==", DEFAULT_DELAYED_LR, abs(float(args.delayed_readout_lr) - DEFAULT_DELAYED_LR) < 1e-12),
    ]
    status, failure_reason = pass_fail(criteria)

    summary_csv = output_dir / "tier4_16a_fix_summary.csv"
    aggregate_csv = output_dir / "tier4_16a_fix_backend_summary.csv"
    tail_csv = output_dir / "tier4_16a_fix_tail_events.csv"
    failure_csv = output_dir / "tier4_16a_fix_failures.csv"
    plot_path = output_dir / "tier4_16a_fix_summary.png"
    manifest_path = output_dir / "tier4_16a_fix_results.json"
    report_path = output_dir / "tier4_16a_fix_report.md"
    write_csv(summary_csv, summary_rows)
    write_csv(aggregate_csv, aggregate_rows)
    write_csv(tail_csv, tail_events)
    if failures:
        write_csv(failure_csv, failures)
    plot_debug(summary_rows, plot_path)
    artifacts = {
        "summary_csv": str(summary_csv),
        "backend_summary_csv": str(aggregate_csv),
        "tail_events_csv": str(tail_csv),
        "summary_png": str(plot_path) if plot_path.exists() else "",
    }
    if failures:
        artifacts["failures_csv"] = str(failure_csv)
    artifacts["manifest_json"] = str(manifest_path)
    artifacts["report_md"] = str(report_path)
    write_json(
        manifest_path,
        {
            "generated_at_utc": utc_now(),
            "tier": TIER,
            "status": status,
            "failure_reason": failure_reason,
            "diagnosis": diagnosis,
            "criteria": criteria,
            "summary_rows": summary_rows,
            "backend_summary_rows": aggregate_rows,
            "artifacts": artifacts,
            "config": {
                "backends": backends,
                "seeds": args.seeds,
                "run_lengths": args.run_lengths,
                "population_size": args.population_size,
                "delay": args.delay,
                "period": args.period,
                "readout_lr": args.readout_lr,
                "delayed_readout_lr": args.delayed_readout_lr,
                "tail_threshold": args.tail_threshold,
                "min_tail_events": args.min_tail_events,
            },
        },
    )
    write_report(
        path=report_path,
        output_dir=output_dir,
        status=status,
        criteria=criteria,
        aggregate_rows=aggregate_rows,
        artifacts=artifacts,
        diagnosis=diagnosis,
    )
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
