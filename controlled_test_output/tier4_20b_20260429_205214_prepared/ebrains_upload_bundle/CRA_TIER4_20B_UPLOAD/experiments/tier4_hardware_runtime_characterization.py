#!/usr/bin/env python3
"""Tier 4.14 hardware runtime characterization for the CRA SpiNNaker capsule.

Tier 4.14 is intentionally separate from Tier 4.13:

- Tier 4.13 answers: did the minimal fixed-pattern CRA capsule execute on real
  SpiNNaker hardware and preserve expected behavior?
- Tier 4.14 answers: where did the hardware wall-clock time go?

The default mode characterizes the canonical Tier 4.13 hardware-pass bundle by
reading its result JSON, time-series CSV, and sPyNNaker provenance SQLite data.
A fresh hardware mode is also provided for repeating the same measurement inside
an EBRAINS/JobManager environment.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
import sqlite3
import sys
import time
import traceback
from collections import defaultdict
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

from tier2_learning import (  # noqa: E402
    DEFAULT_AMPLITUDE,
    DEFAULT_DT_SECONDS,
    criterion,
    json_safe,
    markdown_value,
    pass_fail,
    plot_case,
    write_csv,
    write_json,
    utc_now,
)
from tier4_spinnaker_hardware_capsule import (  # noqa: E402
    BackendFallbackError,
    aggregate_summaries,
    collect_environment,
    collect_recent_spinnaker_reports,
    hardware_criteria,
    plot_hardware_summary,
    run_spinnaker_seed,
    write_summary_csv,
)

TIER = "Tier 4.14 - Hardware Runtime Characterization"
DEFAULT_SOURCE_DIR = (
    ROOT / "controlled_test_output" / "tier4_13_20260427_011912_hardware_pass"
)
PROVENANCE_MS_SCALE = 1000.0


def clean_float(value: Any) -> float | None:
    try:
        f = float(value)
    except Exception:
        return None
    return f if math.isfinite(f) else None


def safe_mean(values: list[Any]) -> float | None:
    clean = [f for value in values if (f := clean_float(value)) is not None]
    return None if not clean else float(np.mean(clean))


def safe_sum(values: list[Any]) -> float:
    clean = [f for value in values if (f := clean_float(value)) is not None]
    return float(np.sum(clean)) if clean else 0.0


def read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def read_csv_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def find_source_files(source_dir: Path) -> dict[str, Path | None]:
    reports = sorted(source_dir.glob("**/global_provenance.sqlite3"))
    return {
        "results": source_dir / "tier4_13_results.json",
        "summary": source_dir / "tier4_13_summary.csv",
        "timeseries": next(source_dir.glob("spinnaker_hardware_seed*_timeseries.csv"), None),
        "provenance": reports[-1] if reports else None,
    }


def query_rows(con: sqlite3.Connection, sql: str) -> list[dict[str, Any]]:
    cur = con.execute(sql)
    cols = [desc[0] for desc in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def parse_provenance_sqlite(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {
            "path": None if path is None else str(path),
            "exists": False,
            "category_rows": [],
            "algorithm_rows": [],
            "version_rows": [],
            "log_rows": [],
            "error": "global_provenance.sqlite3 not found",
        }

    try:
        con = sqlite3.connect(path)
        try:
            category_rows = query_rows(
                con,
                """
                select
                    category,
                    sum(time_taken) as raw_time_ms,
                    count(*) as count,
                    min(n_run) as first_run,
                    max(n_run) as last_run,
                    sum(case when machine_on then 1 else 0 end) as machine_on_count
                from category_timer_provenance
                group by category
                order by raw_time_ms desc
                """,
            )
            algorithm_rows = query_rows(
                con,
                """
                select
                    coalesce(t.algorithm, '') as algorithm,
                    coalesce(t.work, '') as work,
                    coalesce(c.category, '') as category,
                    sum(t.time_taken) as raw_time_ms,
                    count(*) as count,
                    sum(case when t.skip_reason is null then 0 else 1 end) as skipped_count
                from timer_provenance t
                left join category_timer_provenance c on t.category_id = c.category_id
                group by t.algorithm, t.work, c.category
                order by raw_time_ms desc
                """,
            )
            version_rows = query_rows(
                con,
                "select description, the_value from version_provenance order by version_id",
            )
            log_rows = query_rows(
                con,
                """
                select timestamp, level, message
                from p_log_provenance
                order by log_id
                """,
            )
        finally:
            con.close()
    except Exception as exc:
        return {
            "path": str(path),
            "exists": True,
            "category_rows": [],
            "algorithm_rows": [],
            "version_rows": [],
            "log_rows": [],
            "error": f"{type(exc).__name__}: {exc}",
        }

    total_category_ms = safe_sum([row.get("raw_time_ms") for row in category_rows])
    for row in category_rows:
        raw_ms = clean_float(row.get("raw_time_ms")) or 0.0
        row["seconds"] = raw_ms / PROVENANCE_MS_SCALE
        row["fraction_of_profiled"] = (
            raw_ms / total_category_ms if total_category_ms > 0 else None
        )
    total_algorithm_ms = safe_sum([row.get("raw_time_ms") for row in algorithm_rows])
    for row in algorithm_rows:
        raw_ms = clean_float(row.get("raw_time_ms")) or 0.0
        row["seconds"] = raw_ms / PROVENANCE_MS_SCALE
        row["fraction_of_algorithm_total"] = (
            raw_ms / total_algorithm_ms if total_algorithm_ms > 0 else None
        )

    return {
        "path": str(path),
        "exists": True,
        "category_rows": category_rows,
        "algorithm_rows": algorithm_rows,
        "version_rows": version_rows,
        "log_rows": log_rows,
        "error": "",
    }


def infer_simulated_seconds(summary: dict[str, Any], rows: list[dict[str, Any]]) -> float | None:
    steps = clean_float(summary.get("steps"))
    if steps is None:
        steps = float(len(rows)) if rows else None
    dt_seconds = None
    config = summary.get("config")
    if isinstance(config, dict):
        runtime_ms = (
            config.get("spinnaker", {}) if isinstance(config.get("spinnaker"), dict) else {}
        ).get("runtime_ms_per_step")
        runtime_ms_f = clean_float(runtime_ms)
        if runtime_ms_f is not None:
            dt_seconds = runtime_ms_f / 1000.0
    if dt_seconds is None:
        dt_seconds = DEFAULT_DT_SECONDS
    if steps is None:
        return None
    return float(steps * dt_seconds)


def extract_source_summary(source_manifest: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    summary = dict(source_manifest.get("summary") or {})
    seed_summaries = list(source_manifest.get("seed_summaries") or [])
    if seed_summaries and "steps" not in summary:
        summary["steps"] = seed_summaries[0].get("steps")
    if seed_summaries and "config" not in summary:
        summary["config"] = seed_summaries[0].get("config")
    return summary, seed_summaries


def build_runtime_breakdown(
    *,
    provenance: dict[str, Any],
    source_summary: dict[str, Any],
    rows: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    category_rows = list(provenance.get("category_rows") or [])
    algorithm_rows = list(provenance.get("algorithm_rows") or [])
    total_category_seconds = safe_sum([row.get("seconds") for row in category_rows])
    total_algorithm_seconds = safe_sum([row.get("seconds") for row in algorithm_rows])
    dominant_category = category_rows[0] if category_rows else {}
    dominant_algorithm = algorithm_rows[0] if algorithm_rows else {}

    runtime_seconds = clean_float(
        source_summary.get("runtime_seconds_mean", source_summary.get("runtime_seconds"))
    )
    simulated_seconds = infer_simulated_seconds(source_summary, rows)
    steps = clean_float(source_summary.get("steps")) or float(len(rows) if rows else 0)
    mean_wall_per_step = runtime_seconds / steps if runtime_seconds and steps else None
    wall_to_sim_ratio = (
        runtime_seconds / simulated_seconds
        if runtime_seconds is not None and simulated_seconds and simulated_seconds > 0
        else None
    )

    app_runner_seconds = 0.0
    buffer_extract_seconds = 0.0
    dsg_reload_seconds = 0.0
    runtime_update_seconds = 0.0
    for row in algorithm_rows:
        algorithm = str(row.get("algorithm", ""))
        seconds = clean_float(row.get("seconds")) or 0.0
        if algorithm == "Application runner":
            app_runner_seconds += seconds
        elif algorithm == "Buffer extractor":
            buffer_extract_seconds += seconds
        elif algorithm == "DSG region reloader":
            dsg_reload_seconds += seconds
        elif algorithm == "Runtime Update":
            runtime_update_seconds += seconds

    step_spinnaker_ms = safe_sum([row.get("spinnaker_wall_ms") for row in rows])
    step_total_ms = safe_sum([row.get("total_step_wall_ms") for row in rows])
    step_host_ms = safe_sum([row.get("host_compute_wall_ms") for row in rows])

    summary = {
        "runtime_seconds": runtime_seconds,
        "simulated_biological_seconds": simulated_seconds,
        "wall_to_simulated_ratio": wall_to_sim_ratio,
        "steps": int(steps) if steps else None,
        "mean_wall_per_step_seconds": mean_wall_per_step,
        "provenance_total_category_seconds": total_category_seconds,
        "provenance_total_algorithm_seconds": total_algorithm_seconds,
        "dominant_category": dominant_category.get("category"),
        "dominant_category_seconds": dominant_category.get("seconds"),
        "dominant_category_fraction": dominant_category.get("fraction_of_profiled"),
        "dominant_algorithm": dominant_algorithm.get("algorithm"),
        "dominant_algorithm_work": dominant_algorithm.get("work"),
        "dominant_algorithm_category": dominant_algorithm.get("category"),
        "dominant_algorithm_seconds": dominant_algorithm.get("seconds"),
        "application_runner_seconds": app_runner_seconds,
        "application_runner_seconds_per_step": app_runner_seconds / steps if steps else None,
        "buffer_extractor_seconds": buffer_extract_seconds,
        "buffer_extractor_seconds_per_step": buffer_extract_seconds / steps if steps else None,
        "dsg_reloader_seconds": dsg_reload_seconds,
        "dsg_reloader_seconds_per_step": dsg_reload_seconds / steps if steps else None,
        "runtime_update_seconds": runtime_update_seconds,
        "runtime_update_seconds_per_step": runtime_update_seconds / steps if steps else None,
        "telemetry_step_spinnaker_seconds_sum": step_spinnaker_ms / 1000.0,
        "telemetry_step_total_seconds_sum": step_total_ms / 1000.0,
        "telemetry_step_host_seconds_sum": step_host_ms / 1000.0,
        "category_timer_rows": len(category_rows),
        "algorithm_timer_rows": len(algorithm_rows),
        "provenance_db": provenance.get("path"),
        "provenance_error": provenance.get("error", ""),
    }

    breakdown_rows: list[dict[str, Any]] = []
    for row in category_rows:
        breakdown_rows.append(
            {
                "level": "category",
                "name": row.get("category"),
                "work": "",
                "category": row.get("category"),
                "seconds": row.get("seconds"),
                "raw_time_ms": row.get("raw_time_ms"),
                "count": row.get("count"),
                "fraction": row.get("fraction_of_profiled"),
                "note": "sPyNNaker category_timer_provenance aggregate",
            }
        )
    top_algorithm_rows: list[dict[str, Any]] = []
    for row in algorithm_rows:
        top_row = {
            "level": "algorithm",
            "name": row.get("algorithm"),
            "work": row.get("work"),
            "category": row.get("category"),
            "seconds": row.get("seconds"),
            "raw_time_ms": row.get("raw_time_ms"),
            "count": row.get("count"),
            "fraction": row.get("fraction_of_algorithm_total"),
            "skipped_count": row.get("skipped_count"),
            "note": "sPyNNaker timer_provenance aggregate",
        }
        top_algorithm_rows.append(top_row)
        breakdown_rows.append(top_row)

    return summary, breakdown_rows, top_algorithm_rows


def runtime_criteria(summary: dict[str, Any], source_status: str) -> list[dict[str, Any]]:
    return [
        criterion(
            "source hardware result passed",
            source_status,
            "==",
            "pass",
            source_status == "pass",
        ),
        criterion(
            "zero synthetic fallback preserved",
            summary.get("synthetic_fallbacks_sum"),
            "==",
            0,
            int(summary.get("synthetic_fallbacks_sum") or 0) == 0,
        ),
        criterion(
            "zero sim.run failures preserved",
            summary.get("sim_run_failures_sum"),
            "==",
            0,
            int(summary.get("sim_run_failures_sum") or 0) == 0,
        ),
        criterion(
            "zero summary-read failures preserved",
            summary.get("summary_read_failures_sum"),
            "==",
            0,
            int(summary.get("summary_read_failures_sum") or 0) == 0,
        ),
        criterion(
            "runtime wall-clock measured",
            summary.get("runtime_seconds"),
            ">",
            0,
            (clean_float(summary.get("runtime_seconds")) or 0.0) > 0.0,
        ),
        criterion(
            "simulated task duration measured",
            summary.get("simulated_biological_seconds"),
            ">",
            0,
            (clean_float(summary.get("simulated_biological_seconds")) or 0.0) > 0.0,
        ),
        criterion(
            "category provenance timers parsed",
            summary.get("category_timer_rows"),
            ">",
            0,
            int(summary.get("category_timer_rows") or 0) > 0,
        ),
        criterion(
            "algorithm provenance timers parsed",
            summary.get("algorithm_timer_rows"),
            ">",
            0,
            int(summary.get("algorithm_timer_rows") or 0) > 0,
        ),
        criterion(
            "dominant runtime category identified",
            summary.get("dominant_category"),
            "is not",
            None,
            bool(summary.get("dominant_category")),
        ),
    ]


def plot_runtime_breakdown(category_rows: list[dict[str, Any]], path: Path) -> None:
    if plt is None or not category_rows:
        return
    rows = sorted(category_rows, key=lambda r: clean_float(r.get("seconds")) or 0.0)
    labels = [str(r.get("category")) for r in rows]
    values = [clean_float(r.get("seconds")) or 0.0 for r in rows]
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(labels, values, color="#2f855a")
    ax.set_xlabel("seconds")
    ax.set_title("Tier 4.14 SpiNNaker Runtime Breakdown")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def write_runtime_report(
    *,
    path: Path,
    mode: str,
    status: str,
    output_dir: Path,
    source_dir: Path | None,
    summary: dict[str, Any],
    criteria: list[dict[str, Any]],
    artifacts: dict[str, str],
    failure_reason: str = "",
) -> None:
    lines = [
        "# Tier 4.14 Hardware Runtime Characterization Findings",
        "",
        f"- Generated: `{utc_now()}`",
        f"- Mode: `{mode}`",
        f"- Status: **{status.upper()}**",
        f"- Output directory: `{output_dir}`",
    ]
    if source_dir is not None:
        lines.append(f"- Source hardware bundle: `{source_dir}`")
    lines.extend(
        [
            "",
            "Tier 4.14 is not a new learning claim. It characterizes the wall-clock and sPyNNaker provenance costs behind the Tier 4.13 minimal hardware capsule.",
            "",
            "## Claim Boundary",
            "",
            "- `PASS` means the hardware-pass bundle has enough runtime/provenance telemetry to explain where time went.",
            "- This does not prove multi-seed hardware repeatability, harder hardware learning, or hardware scaling.",
            "- If mode is `characterize-existing`, the evidence is derived from the canonical Tier 4.13 hardware pass rather than a new hardware execution.",
            "",
            "## Summary",
            "",
        ]
    )
    for key in [
        "source_tier4_13_status",
        "runtime_seconds",
        "simulated_biological_seconds",
        "wall_to_simulated_ratio",
        "steps",
        "mean_wall_per_step_seconds",
        "dominant_category",
        "dominant_category_seconds",
        "dominant_category_fraction",
        "dominant_algorithm",
        "dominant_algorithm_work",
        "dominant_algorithm_seconds",
        "application_runner_seconds",
        "application_runner_seconds_per_step",
        "buffer_extractor_seconds",
        "buffer_extractor_seconds_per_step",
        "provenance_total_category_seconds",
        "category_timer_rows",
        "algorithm_timer_rows",
        "synthetic_fallbacks_sum",
        "sim_run_failures_sum",
        "summary_read_failures_sum",
    ]:
        if key in summary:
            lines.append(f"- {key}: `{markdown_value(summary.get(key))}`")

    if failure_reason:
        lines.extend(["", f"Failure: {failure_reason}", ""])

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
                f"{item['name']} | "
                f"{markdown_value(item['value'])} | "
                f"{item['operator']} {markdown_value(item['threshold'])} | "
                f"{'yes' if item['passed'] else 'no'} |"
            )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The important empirical separation is simulated task time versus orchestration wall time. The minimal capsule simulates only a few biological seconds, but the Python/sPyNNaker/hardware loop repeatedly reloads, runs, extracts buffers, and synchronizes each short step. That overhead is real engineering data for the paper, but it should not be confused with evidence that the neural substrate itself is slow.",
            "",
            "The next engineering implication is to batch more closed-loop work per hardware run, reduce readback cadence, or move more of the adaptation loop on-chip before making larger hardware-scaling claims.",
            "",
            "## Artifacts",
            "",
        ]
    )
    for label, artifact in artifacts.items():
        lines.append(f"- `{label}`: `{artifact}`")
    if artifacts.get("runtime_breakdown_png"):
        lines.extend(["", "![runtime_breakdown](tier4_14_runtime_breakdown.png)", ""])

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_latest(output_dir: Path, report_path: Path, manifest_path: Path, status: str) -> None:
    latest_path = ROOT / "controlled_test_output" / "tier4_14_latest_manifest.json"
    write_json(
        latest_path,
        {
            "generated_at_utc": utc_now(),
            "manifest": str(manifest_path),
            "report": str(report_path),
            "output_dir": str(output_dir),
            "status": status,
        },
    )


def characterize_source_bundle(args: argparse.Namespace, output_dir: Path) -> int:
    source_dir = args.source_dir.resolve()
    files = find_source_files(source_dir)
    results_path = files["results"]
    if results_path is None or not results_path.exists():
        raise SystemExit(f"No Tier 4.13 result JSON found in {source_dir}")

    source_manifest = read_json(results_path)
    source_summary, seed_summaries = extract_source_summary(source_manifest)
    source_status = str(source_manifest.get("status", "unknown"))
    rows = read_csv_rows(files["timeseries"]) if files["timeseries"] else []
    provenance = parse_provenance_sqlite(files["provenance"])
    runtime_summary, breakdown_rows, algorithm_rows = build_runtime_breakdown(
        provenance=provenance,
        source_summary=source_summary,
        rows=rows,
    )

    summary = dict(runtime_summary)
    summary.update(
        {
            "mode": "characterize-existing",
            "source_dir": str(source_dir),
            "source_tier4_13_status": source_status,
            "source_tier4_13_results": str(results_path),
            "hardware_run_attempted": source_summary.get("hardware_run_attempted"),
            "hardware_target_configured": source_summary.get("hardware_target_configured"),
            "all_accuracy_mean": source_summary.get("all_accuracy_mean"),
            "tail_accuracy_mean": source_summary.get("tail_accuracy_mean"),
            "tail_prediction_target_corr_mean": source_summary.get(
                "tail_prediction_target_corr_mean"
            ),
            "total_step_spikes_mean": source_summary.get("total_step_spikes_mean"),
            "synthetic_fallbacks_sum": source_summary.get("synthetic_fallbacks_sum"),
            "sim_run_failures_sum": source_summary.get("sim_run_failures_sum"),
            "summary_read_failures_sum": source_summary.get("summary_read_failures_sum"),
        }
    )

    criteria = runtime_criteria(summary, source_status)
    status, failure_reason = pass_fail(criteria)

    artifacts: dict[str, str] = {}
    category_csv = output_dir / "tier4_14_category_timers.csv"
    algorithm_csv = output_dir / "tier4_14_top_algorithms.csv"
    breakdown_csv = output_dir / "tier4_14_runtime_breakdown.csv"
    write_csv(category_csv, provenance.get("category_rows") or [])
    write_csv(algorithm_csv, algorithm_rows)
    write_csv(breakdown_csv, breakdown_rows)
    artifacts["category_timers_csv"] = str(category_csv)
    artifacts["top_algorithms_csv"] = str(algorithm_csv)
    artifacts["runtime_breakdown_csv"] = str(breakdown_csv)

    breakdown_png = output_dir / "tier4_14_runtime_breakdown.png"
    plot_runtime_breakdown(provenance.get("category_rows") or [], breakdown_png)
    if breakdown_png.exists():
        artifacts["runtime_breakdown_png"] = str(breakdown_png)

    if files["provenance"]:
        artifacts["source_provenance_sqlite"] = str(files["provenance"])
    if files["timeseries"]:
        artifacts["source_timeseries_csv"] = str(files["timeseries"])
    artifacts["source_tier4_13_results"] = str(results_path)

    manifest_path = output_dir / "tier4_14_results.json"
    report_path = output_dir / "tier4_14_report.md"
    summary_csv_path = output_dir / "tier4_14_summary.csv"
    write_json(
        manifest_path,
        {
            "generated_at_utc": utc_now(),
            "tier": TIER,
            "mode": "characterize-existing",
            "status": status,
            "failure_reason": failure_reason,
            "source_dir": str(source_dir),
            "source_manifest": source_manifest,
            "seed_summaries": seed_summaries,
            "summary": summary,
            "criteria": criteria,
            "runtime_breakdown": breakdown_rows,
            "provenance_versions": provenance.get("version_rows") or [],
            "artifacts": artifacts,
            "matplotlib_error": MATPLOTLIB_ERROR,
        },
    )
    write_summary_csv(summary_csv_path, [summary])
    artifacts = {
        "manifest_json": str(manifest_path),
        "summary_csv": str(summary_csv_path),
        **artifacts,
    }
    write_runtime_report(
        path=report_path,
        mode="characterize-existing",
        status=status,
        output_dir=output_dir,
        source_dir=source_dir,
        summary=summary,
        criteria=criteria,
        artifacts=artifacts,
        failure_reason=failure_reason,
    )
    write_latest(output_dir, report_path, manifest_path, status)
    return 0 if status == "pass" else 1


def write_jobmanager_capsule(output_dir: Path, args: argparse.Namespace) -> dict[str, str]:
    capsule_dir = output_dir / "jobmanager_capsule"
    capsule_dir.mkdir(parents=True, exist_ok=True)
    config_path = capsule_dir / "capsule_config.json"
    command_path = capsule_dir / "run_tier4_14_on_jobmanager.sh"
    readme_path = capsule_dir / "README_JOBMANAGER.md"
    expected_path = capsule_dir / "expected_outputs.json"

    write_json(
        config_path,
        {
            "tier": TIER,
            "task": "runtime characterization of fixed-pattern hardware capsule",
            "steps": args.steps,
            "seed": args.base_seed,
            "population_size": args.population_size,
            "amplitude": args.amplitude,
            "dt_seconds": args.dt_seconds,
            "timestep_ms": args.timestep_ms,
            "claim_boundary": (
                "Tier 4.14 characterizes runtime/provenance overhead. It is not "
                "a new hardware-learning or scaling claim."
            ),
        },
    )

    command_path.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                "",
                "OUT_DIR=${1:-tier4_14_job_output}",
                "python3 experiments/tier4_hardware_runtime_characterization.py \\",
                "  --mode run-hardware \\",
                "  --require-real-hardware \\",
                "  --stop-on-fail \\",
                "  --output-dir \"$OUT_DIR\"",
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
                    "tier4_14_report.md",
                    "tier4_14_results.json",
                    "tier4_14_summary.csv",
                    "tier4_14_runtime_breakdown.csv",
                    "tier4_14_category_timers.csv",
                    "tier4_14_top_algorithms.csv",
                    "tier4_14_runtime_breakdown.png",
                ],
                "pass_requires": [
                    "source hardware result passed or fresh hardware run passed",
                    "zero synthetic fallback",
                    "zero sim.run failures",
                    "zero summary-read failures",
                    "runtime_seconds > 0",
                    "sPyNNaker category and algorithm provenance timers parsed",
                    "dominant runtime category identified",
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
                "# Tier 4.14 Hardware Runtime Characterization",
                "",
                "Run from the repository root inside EBRAINS/JobManager:",
                "",
                "```bash",
                "bash controlled_test_output/<tier4_14_run>/jobmanager_capsule/run_tier4_14_on_jobmanager.sh",
                "```",
                "",
                "This tier measures wall-clock/provenance cost. It does not expand the Tier 4.13 learning claim.",
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


def prepare_capsule(args: argparse.Namespace, output_dir: Path) -> int:
    env = collect_environment(args)
    capsule_artifacts = write_jobmanager_capsule(output_dir, args)
    summary = {
        "mode": "prepare",
        "hardware_run_attempted": False,
        "hardware_target_configured": env.get("hardware_target_configured"),
        "jobmanager_cli": env.get("jobmanager_cli"),
        "capsule_dir": capsule_artifacts["capsule_dir"],
    }
    criteria = [
        criterion(
            "capsule package generated",
            Path(capsule_artifacts["jobmanager_run_script"]).exists(),
            "==",
            True,
            Path(capsule_artifacts["jobmanager_run_script"]).exists(),
        )
    ]
    status, failure_reason = pass_fail(criteria)
    manifest_path = output_dir / "tier4_14_results.json"
    report_path = output_dir / "tier4_14_report.md"
    summary_csv_path = output_dir / "tier4_14_summary.csv"
    write_json(
        manifest_path,
        {
            "generated_at_utc": utc_now(),
            "tier": TIER,
            "mode": "prepare",
            "status": "prepared" if status == "pass" else status,
            "failure_reason": failure_reason,
            "summary": summary,
            "criteria": criteria,
            "environment": env,
            "artifacts": capsule_artifacts,
        },
    )
    write_summary_csv(summary_csv_path, [summary])
    write_runtime_report(
        path=report_path,
        mode="prepare",
        status="prepared" if status == "pass" else status,
        output_dir=output_dir,
        source_dir=None,
        summary=summary,
        criteria=criteria,
        artifacts={
            "manifest_json": str(manifest_path),
            "summary_csv": str(summary_csv_path),
            **capsule_artifacts,
        },
        failure_reason=failure_reason,
    )
    write_latest(output_dir, report_path, manifest_path, "prepared" if status == "pass" else status)
    return 0 if status == "pass" else 1


def run_hardware(args: argparse.Namespace, output_dir: Path) -> int:
    run_started_epoch = time.time()
    env = collect_environment(args)
    hardware_target_configured = bool(env.get("hardware_target_configured"))
    if args.require_real_hardware and not hardware_target_configured:
        failure = (
            "No real SpiNNaker target is configured locally. Refusing to run a "
            "virtual-board result as Tier 4.14 hardware."
        )
        summary = {
            "mode": "run-hardware",
            "hardware_run_attempted": False,
            "hardware_target_configured": False,
            "jobmanager_cli": env.get("jobmanager_cli"),
        }
        criteria = [
            criterion(
                "real SpiNNaker target configured",
                hardware_target_configured,
                "==",
                True,
                False,
            )
        ]
        manifest_path = output_dir / "tier4_14_results.json"
        report_path = output_dir / "tier4_14_report.md"
        summary_csv_path = output_dir / "tier4_14_summary.csv"
        write_json(
            manifest_path,
            {
                "generated_at_utc": utc_now(),
                "tier": TIER,
                "mode": "run-hardware",
                "status": "blocked",
                "failure_reason": failure,
                "summary": summary,
                "criteria": criteria,
                "environment": env,
            },
        )
        write_summary_csv(summary_csv_path, [summary])
        write_runtime_report(
            path=report_path,
            mode="run-hardware",
            status="blocked",
            output_dir=output_dir,
            source_dir=None,
            summary=summary,
            criteria=criteria,
            artifacts={"manifest_json": str(manifest_path), "summary_csv": str(summary_csv_path)},
            failure_reason=failure,
        )
        write_latest(output_dir, report_path, manifest_path, "blocked")
        return 1

    summaries: list[dict[str, Any]] = []
    artifacts: dict[str, str] = {}
    failure_reason = ""
    failure_traceback = ""
    failure_diagnostics: dict[str, Any] = {}
    hardware_run_attempted = False
    for seed in [args.base_seed]:
        try:
            hardware_run_attempted = True
            rows, summary = run_spinnaker_seed(seed=seed, args=args)
        except Exception as exc:
            failure_reason = f"seed {seed} raised {type(exc).__name__}: {exc}"
            failure_traceback = traceback.format_exc()
            failure_diagnostics = getattr(exc, "diagnostics", {}) or {}
            traceback_path = output_dir / f"seed_{seed}_failure_traceback.txt"
            traceback_path.write_text(failure_traceback, encoding="utf-8")
            artifacts[f"seed_{seed}_failure_traceback"] = str(traceback_path)
            if failure_diagnostics:
                diagnostics_path = output_dir / f"seed_{seed}_backend_diagnostics.json"
                write_json(diagnostics_path, failure_diagnostics)
                artifacts[f"seed_{seed}_backend_diagnostics"] = str(diagnostics_path)
            break

        csv_path = output_dir / f"spinnaker_runtime_seed{seed}_timeseries.csv"
        png_path = output_dir / f"spinnaker_runtime_seed{seed}_timeseries.png"
        write_csv(csv_path, rows)
        plot_case(rows, png_path, f"Tier 4.14 SpiNNaker runtime seed {seed}")
        artifacts[f"seed_{seed}_timeseries_csv"] = str(csv_path)
        if png_path.exists():
            artifacts[f"seed_{seed}_timeseries_png"] = str(png_path)
        summaries.append(summary)

    aggregate = aggregate_summaries(summaries)
    aggregate.update(
        {
            "mode": "run-hardware",
            "source_tier4_13_status": "pass" if summaries else "fail",
            "hardware_run_attempted": hardware_run_attempted,
            "hardware_target_configured": hardware_target_configured,
            "jobmanager_cli": env.get("jobmanager_cli"),
            "failure_reason": failure_reason,
            "failure_diagnostics": failure_diagnostics,
        }
    )
    artifacts.update(collect_recent_spinnaker_reports(output_dir, run_started_epoch))
    provenance_path = next(output_dir.glob("spinnaker_reports/**/global_provenance.sqlite3"), None)
    provenance = parse_provenance_sqlite(provenance_path)
    source_rows = []
    if artifacts:
        first_csv = next((Path(v) for k, v in artifacts.items() if k.endswith("timeseries_csv")), None)
        if first_csv is not None:
            source_rows = read_csv_rows(first_csv)
    runtime_summary, breakdown_rows, algorithm_rows = build_runtime_breakdown(
        provenance=provenance,
        source_summary=summaries[0] if summaries else aggregate,
        rows=source_rows,
    )
    aggregate.update(runtime_summary)

    criteria = []
    if summaries:
        criteria.extend(hardware_criteria(aggregate, args))
    criteria.extend(runtime_criteria(aggregate, "pass" if summaries else "fail"))
    status, criteria_failure = pass_fail(criteria) if criteria else ("fail", failure_reason)
    if criteria_failure:
        failure_reason = criteria_failure

    category_csv = output_dir / "tier4_14_category_timers.csv"
    algorithm_csv = output_dir / "tier4_14_top_algorithms.csv"
    breakdown_csv = output_dir / "tier4_14_runtime_breakdown.csv"
    write_csv(category_csv, provenance.get("category_rows") or [])
    write_csv(algorithm_csv, algorithm_rows)
    write_csv(breakdown_csv, breakdown_rows)
    artifacts["category_timers_csv"] = str(category_csv)
    artifacts["top_algorithms_csv"] = str(algorithm_csv)
    artifacts["runtime_breakdown_csv"] = str(breakdown_csv)
    breakdown_png = output_dir / "tier4_14_runtime_breakdown.png"
    plot_runtime_breakdown(provenance.get("category_rows") or [], breakdown_png)
    if breakdown_png.exists():
        artifacts["runtime_breakdown_png"] = str(breakdown_png)

    summary_png = output_dir / "hardware_capsule_summary.png"
    if summaries:
        plot_hardware_summary(aggregate, summary_png)
        if summary_png.exists():
            artifacts["hardware_summary_png"] = str(summary_png)

    if failure_traceback:
        aggregate["failure_traceback"] = failure_traceback

    manifest_path = output_dir / "tier4_14_results.json"
    report_path = output_dir / "tier4_14_report.md"
    summary_csv_path = output_dir / "tier4_14_summary.csv"
    write_json(
        manifest_path,
        {
            "generated_at_utc": utc_now(),
            "tier": TIER,
            "mode": "run-hardware",
            "status": status,
            "failure_reason": failure_reason,
            "summary": aggregate,
            "criteria": criteria,
            "seed_summaries": summaries,
            "runtime_breakdown": breakdown_rows,
            "provenance_versions": provenance.get("version_rows") or [],
            "artifacts": artifacts,
            "environment": env,
            "matplotlib_error": MATPLOTLIB_ERROR,
        },
    )
    write_summary_csv(summary_csv_path, [aggregate])
    write_runtime_report(
        path=report_path,
        mode="run-hardware",
        status=status,
        output_dir=output_dir,
        source_dir=None,
        summary=aggregate,
        criteria=criteria,
        artifacts={"manifest_json": str(manifest_path), "summary_csv": str(summary_csv_path), **artifacts},
        failure_reason=failure_reason,
    )
    write_latest(output_dir, report_path, manifest_path, status)
    return 0 if status == "pass" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Characterize Tier 4.13/Tier 4.14 SpiNNaker hardware runtime overhead.",
    )
    parser.add_argument(
        "--mode",
        choices=["characterize-existing", "prepare", "run-hardware"],
        default="characterize-existing",
    )
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--steps", type=int, default=120)
    parser.add_argument("--base-seed", type=int, default=42)
    parser.add_argument("--population-size", type=int, default=8)
    parser.add_argument("--amplitude", type=float, default=DEFAULT_AMPLITUDE)
    parser.add_argument("--dt-seconds", type=float, default=DEFAULT_DT_SECONDS)
    parser.add_argument("--timestep-ms", type=float, default=1.0)
    parser.add_argument("--readout-lr", type=float, default=0.10)
    parser.add_argument("--delayed-readout-lr", type=float, default=0.05)
    parser.add_argument("--all-accuracy-threshold", type=float, default=0.65)
    parser.add_argument("--tail-accuracy-threshold", type=float, default=0.75)
    parser.add_argument("--corr-threshold", type=float, default=0.60)
    parser.add_argument("--spinnaker-hostname", default=None)
    parser.add_argument(
        "--require-real-hardware",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument(
        "--stop-on-backend-fallback",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument("--stop-on-fail", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.steps <= 0:
        parser.error("--steps must be positive")
    if args.population_size <= 0:
        parser.error("--population-size must be positive")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = args.output_dir or (
        ROOT / "controlled_test_output" / f"tier4_14_{timestamp}"
    )
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.mode == "characterize-existing":
        return characterize_source_bundle(args, output_dir)
    if args.mode == "prepare":
        return prepare_capsule(args, output_dir)
    if args.mode == "run-hardware":
        return run_hardware(args, output_dir)
    raise AssertionError(args.mode)


if __name__ == "__main__":
    raise SystemExit(main())
