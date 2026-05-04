#!/usr/bin/env python3
"""Tier 4.17 batched/chunked hardware runtime refactor scaffold.

This is not a learning-result tier. It creates an auditable runtime contract for
moving from proof-grade per-step hardware orchestration toward chunked hardware
runs.

Implemented now:

- `runtime_mode = step | chunked | continuous`
- `learning_location = host | hybrid | on_chip`
- conservative runtime planning for `chunked + host`

Not implemented yet:

- scheduled input delivery inside a hardware chunk
- per-step binned spike readback from a chunk
- host learning replay from binned readback
- custom C/on-chip closed-loop learning

The output is deliberately noncanonical scaffolding until parity and hardware
probe runs pass.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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

from coral_reef_spinnaker.runtime_modes import (  # noqa: E402
    LEARNING_LOCATIONS,
    RUNTIME_MODES,
    chunk_ranges,
    estimate_plans,
    make_runtime_plan,
)

OUTPUT_ROOT = ROOT / "controlled_test_output"
TIER = "Tier 4.17 - Batched / Continuous Hardware Runtime Refactor"
DEFAULT_CHUNK_SIZES = "1,5,10,25,50"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_int_list(value: str) -> list[int]:
    try:
        items = [int(part.strip()) for part in value.split(",") if part.strip()]
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc
    if not items:
        raise argparse.ArgumentTypeError("at least one chunk size is required")
    if any(item < 1 for item in items):
        raise argparse.ArgumentTypeError("chunk sizes must be >= 1")
    return items


def json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, tuple):
        return [json_safe(v) for v in value]
    if isinstance(value, list):
        return [json_safe(v) for v in value]
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(data), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
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
            writer.writerow({key: json_safe(value) for key, value in row.items()})


def criterion(name: str, value: Any, operator: str, threshold: Any, passed: bool) -> dict[str, Any]:
    return {
        "name": name,
        "value": value,
        "operator": operator,
        "threshold": threshold,
        "passed": bool(passed),
    }


def markdown_value(value: Any) -> str:
    if value is None:
        return "None"
    if isinstance(value, float):
        if not math.isfinite(value):
            return "None"
        return f"{value:.6g}"
    return str(value)


def plan_to_row(plan, *, baseline_calls: int, target_delay_steps: int) -> dict[str, Any]:
    ranges = chunk_ranges(plan.total_steps, plan.chunk_size_steps)
    return {
        "tier": TIER,
        "runtime_mode": plan.runtime_mode,
        "learning_location": plan.learning_location,
        "chunk_size_steps": plan.chunk_size_steps,
        "total_steps": plan.total_steps,
        "dt_seconds": plan.dt_seconds,
        "simulated_ms_per_chunk": plan.simulated_ms_per_chunk,
        "sim_run_calls": plan.sim_run_calls,
        "baseline_step_calls": baseline_calls,
        "call_reduction_factor": plan.call_reduction_factor,
        "learning_update_interval_steps": plan.learning_update_interval_steps,
        "target_delay_steps": target_delay_steps,
        "chunk_ranges_preview": ranges[:5],
        "chunk_count": len(ranges),
        "implemented": plan.implemented,
        "implementation_stage": plan.implementation_stage,
        "blockers": list(plan.blockers),
        "uses_scheduled_input": plan.implementation_stage == "chunked_host_stepcurrent_binned_replay",
        "uses_binned_readback": plan.implementation_stage == "chunked_host_stepcurrent_binned_replay",
        "scientific_use": (
            "implemented chunked-host bridge"
            if plan.implemented
            else "future custom-runtime target; not citable as chunked hardware learning"
        ),
    }


def build_rows(args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    plans = estimate_plans(
        total_steps=args.steps,
        dt_seconds=args.dt_seconds,
        chunk_sizes=args.chunk_sizes,
    )
    future_plans = [
        make_runtime_plan(
            runtime_mode="continuous",
            learning_location="on_chip",
            chunk_size_steps=args.steps,
            total_steps=args.steps,
            dt_seconds=args.dt_seconds,
        ),
        make_runtime_plan(
            runtime_mode="chunked",
            learning_location="hybrid",
            chunk_size_steps=max(args.chunk_sizes),
            total_steps=args.steps,
            dt_seconds=args.dt_seconds,
        ),
    ]
    baseline_calls = args.steps
    rows = [
        plan_to_row(plan, baseline_calls=baseline_calls, target_delay_steps=args.delay)
        for plan in plans + future_plans
    ]
    executable = [row for row in rows if row["implemented"]]
    chunked_host_bridge = [
        row
        for row in rows
        if row["runtime_mode"] == "chunked"
        and row["learning_location"] == "host"
        and row["implementation_stage"] == "chunked_host_stepcurrent_binned_replay"
    ]
    future = [row for row in rows if row["implementation_stage"] == "future_custom_runtime"]
    chunked_host_reductions = [
        float(row["call_reduction_factor"])
        for row in rows
        if row["runtime_mode"] == "chunked" and row["learning_location"] == "host"
    ]
    max_reduction = max(chunked_host_reductions) if chunked_host_reductions else 0.0
    summary = {
        "tier": TIER,
        "status_boundary": "noncanonical runtime contract inventory",
        "runtime_modes": list(RUNTIME_MODES),
        "learning_locations": list(LEARNING_LOCATIONS),
        "steps": args.steps,
        "dt_seconds": args.dt_seconds,
        "chunk_sizes": args.chunk_sizes,
        "baseline_step_calls": baseline_calls,
        "max_call_reduction_factor": max_reduction,
        "executable_now_count": len(executable),
        "chunked_host_bridge_count": len(chunked_host_bridge),
        "future_runtime_count": len(future),
        "next_required_engineering": [
            "tier4_16a_delayed_cue_hardware_repeat_passed",
            "run_hard_noisy_switching_chunked_probe_after_delayed_cue_pass",
            "future_hybrid_or_on_chip_closed_loop_runtime",
        ],
        "recommended_first_parity": {
            "tier": "4.17b",
            "task": "delayed_cue",
            "steps": 120,
            "seed": 43,
            "chunk_sizes": [5, 10],
            "pass_boundary": "match old step-mode qualitative learning without synthetic fallback before any long hardware run",
        },
        "recommended_repaired_probe_after_parity": {
            "tier": "4.16a-repaired",
            "task": "delayed_cue",
            "seed": 43,
            "steps": 1200,
            "runtime_mode": "chunked",
            "learning_location": "host",
            "delayed_readout_lr": 0.20,
        },
    }
    return rows, summary


def build_criteria(rows: list[dict[str, Any]], summary: dict[str, Any], args: argparse.Namespace) -> list[dict[str, Any]]:
    has_step = any(row["runtime_mode"] == "step" and row["learning_location"] == "host" for row in rows)
    has_chunked_host = any(row["runtime_mode"] == "chunked" and row["learning_location"] == "host" for row in rows)
    chunked_bridge_implemented = all(
        row["implementation_stage"] == "chunked_host_stepcurrent_binned_replay" and row["implemented"]
        for row in rows
        if row["runtime_mode"] == "chunked" and row["learning_location"] == "host"
    )
    future_marked_future = all(
        row["implementation_stage"] == "future_custom_runtime" and not row["implemented"]
        for row in rows
        if row["learning_location"] in {"hybrid", "on_chip"} or row["runtime_mode"] == "continuous"
    )
    max_reduction = float(summary.get("max_call_reduction_factor") or 0.0)
    baseline_exists = (ROOT / "baselines" / "CRA_EVIDENCE_BASELINE_v0.5.json").exists()
    return [
        criterion("v0.5 baseline exists before runtime refactor", baseline_exists, "==", True, baseline_exists),
        criterion("step+host current path represented", has_step, "==", True, has_step),
        criterion("chunked+host bridge represented", has_chunked_host, "==", True, has_chunked_host),
        criterion("chunked+host bridge marked implemented", chunked_bridge_implemented, "==", True, chunked_bridge_implemented),
        criterion("hybrid/on-chip/continuous explicitly marked future", future_marked_future, "==", True, future_marked_future),
        criterion("candidate chunking reduces sim.run calls", max_reduction, ">=", args.min_reduction_factor, max_reduction >= args.min_reduction_factor),
        criterion(
            "result is noncanonical runtime contract inventory",
            summary.get("status_boundary"),
            "==",
            "noncanonical runtime contract inventory",
            summary.get("status_boundary") == "noncanonical runtime contract inventory",
        ),
    ]


def status_from_criteria(criteria: list[dict[str, Any]]) -> tuple[str, str]:
    failures = [item for item in criteria if not item.get("passed")]
    if not failures:
        return "prepared", ""
    return "fail", "; ".join(str(item["name"]) for item in failures)


def plot_rows(rows: list[dict[str, Any]], output_path: Path) -> None:
    if plt is None:
        return
    candidates = [
        row
        for row in rows
        if row["learning_location"] == "host"
        and row["runtime_mode"] in {"step", "chunked"}
    ]
    labels = [str(row["chunk_size_steps"]) for row in candidates]
    calls = [float(row["sim_run_calls"]) for row in candidates]
    reductions = [float(row["call_reduction_factor"]) for row in candidates]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    axes[0].bar(labels, calls, color="#1f6feb")
    axes[0].set_title("Estimated sim.run calls")
    axes[0].set_xlabel("chunk size")
    axes[0].set_ylabel("calls")
    axes[1].bar(labels, reductions, color="#2f855a")
    axes[1].set_title("Call reduction factor")
    axes[1].set_xlabel("chunk size")
    axes[1].set_ylabel("x step mode")
    for ax in axes:
        ax.grid(axis="y", alpha=0.25)
    fig.suptitle(TIER)
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def write_report(
    *,
    path: Path,
    output_dir: Path,
    status: str,
    failure_reason: str,
    rows: list[dict[str, Any]],
    summary: dict[str, Any],
    criteria: list[dict[str, Any]],
    artifacts: dict[str, str],
) -> None:
    lines = [
        "# Tier 4.17 Batched / Continuous Hardware Runtime Refactor",
        "",
        f"- Generated: `{utc_now()}`",
        f"- Status: **{status.upper()}**",
        f"- Output directory: `{output_dir}`",
        "",
        "Tier 4.17 is a runtime-contract tier, not a learning-result tier.",
        "It freezes the vocabulary for moving from proof-grade per-step hardware",
        "orchestration toward chunked and eventually continuous execution.",
        "",
        "## Claim Boundary",
        "",
        "- `step + host` is the current proven execution path.",
            "- `chunked + host` is implemented as the first batching bridge after Tier 4.17b local parity.",
            "- Valid chunking still requires real hardware confirmation before it becomes hardware-learning evidence.",
        "- `hybrid`, `on_chip`, and `continuous` are future custom-runtime targets.",
        "",
    ]
    if failure_reason:
        lines.extend(["## Failure", "", failure_reason, ""])
    lines.extend(
        [
            "## Summary",
            "",
            f"- steps: `{summary['steps']}`",
            f"- dt_seconds: `{summary['dt_seconds']}`",
            f"- baseline step-mode `sim.run` calls: `{summary['baseline_step_calls']}`",
            f"- max estimated call reduction: `{markdown_value(summary['max_call_reduction_factor'])}x`",
            f"- executable-now plans: `{summary['executable_now_count']}`",
            f"- chunked-host bridge plans: `{summary['chunked_host_bridge_count']}`",
            "",
            "## Runtime Plan Rows",
            "",
            "| Runtime | Learning | Chunk | Calls | Reduction | Stage | Implemented | Blockers |",
            "| --- | --- | ---: | ---: | ---: | --- | --- | --- |",
        ]
    )
    for row in rows:
        lines.append(
            "| "
            f"`{row['runtime_mode']}` | `{row['learning_location']}` | {row['chunk_size_steps']} | "
            f"{row['sim_run_calls']} | {markdown_value(row['call_reduction_factor'])} | "
            f"`{row['implementation_stage']}` | {row['implemented']} | "
            f"{', '.join(row['blockers']) if row['blockers'] else 'none'} |"
        )
    lines.extend(["", "## Criteria", "", "| Criterion | Value | Rule | Pass |", "| --- | --- | --- | --- |"])
    for item in criteria:
        lines.append(
            f"| {item['name']} | {markdown_value(item['value'])} | {item['operator']} {markdown_value(item['threshold'])} | {'yes' if item['passed'] else 'no'} |"
        )
    lines.extend(
        [
            "",
            "## Next Order",
            "",
            "1. Keep Tier 4.17b as the local parity gate for the chunked bridge.",
            "2. Tier 4.16a-repaired delayed_cue has passed on hardware across seeds 42, 43, and 44.",
            "3. Test hard_noisy_switching with the same chunked bridge.",
            "4. Treat hybrid/on-chip/continuous execution as future custom-runtime work.",
            "",
            "## Artifacts",
            "",
        ]
    )
    for key, value in artifacts.items():
        lines.append(f"- `{key}`: `{value}`")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare Tier 4.17 chunked-runtime contract inventory.")
    parser.add_argument("--steps", type=int, default=1200)
    parser.add_argument("--dt-seconds", type=float, default=0.05)
    parser.add_argument("--delay", type=int, default=5)
    parser.add_argument("--chunk-sizes", type=parse_int_list, default=parse_int_list(DEFAULT_CHUNK_SIZES))
    parser.add_argument("--min-reduction-factor", type=float, default=10.0)
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.steps < 1:
        raise SystemExit("--steps must be >= 1")
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    output_dir = args.output_dir or OUTPUT_ROOT / f"tier4_17_{timestamp}_runtime_scaffold"
    output_dir.mkdir(parents=True, exist_ok=True)

    rows, summary = build_rows(args)
    criteria = build_criteria(rows, summary, args)
    status, failure_reason = status_from_criteria(criteria)

    summary_csv = output_dir / "tier4_17_runtime_summary.csv"
    manifest_json = output_dir / "tier4_17_results.json"
    report_md = output_dir / "tier4_17_report.md"
    plot_png = output_dir / "tier4_17_runtime_reduction.png"
    write_csv(summary_csv, rows)
    plot_rows(rows, plot_png)
    artifacts = {
        "summary_csv": str(summary_csv),
        "manifest_json": str(manifest_json),
        "report_md": str(report_md),
    }
    if plot_png.exists():
        artifacts["runtime_reduction_png"] = str(plot_png)
    write_json(
        manifest_json,
        {
            "generated_at_utc": utc_now(),
            "tier": TIER,
            "status": status,
            "failure_reason": failure_reason,
            "summary": summary,
            "runtime_rows": rows,
            "criteria": criteria,
            "artifacts": artifacts,
            "matplotlib_error": MATPLOTLIB_ERROR,
        },
    )
    write_report(
        path=report_md,
        output_dir=output_dir,
        status=status,
        failure_reason=failure_reason,
        rows=rows,
        summary=summary,
        criteria=criteria,
        artifacts=artifacts,
    )
    write_json(
        OUTPUT_ROOT / "tier4_17_latest_manifest.json",
        {
            "generated_at_utc": utc_now(),
            "manifest": str(manifest_json),
            "report": str(report_md),
            "summary_csv": str(summary_csv),
            "output_dir": str(output_dir),
            "status": status,
            "canonical": False,
            "claim": "Tier 4.17 runtime contract only; chunked host bridge still needs real hardware evidence.",
        },
    )
    print(json.dumps({"status": status, "output_dir": str(output_dir)}, indent=2))
    return 0 if status == "prepared" else 1


if __name__ == "__main__":
    raise SystemExit(main())
