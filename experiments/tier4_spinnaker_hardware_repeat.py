#!/usr/bin/env python3
"""Tier 4.15 multi-seed SpiNNaker hardware repeat capsule.

Tier 4.15 is deliberately simple: rerun the same minimal fixed-pattern hardware
capsule from Tier 4.13 across multiple seeds. It is not a harder task and not a
scaling claim. It answers the repeatability question: does the hardware result
survive seeds 42, 43, and 44 with zero fallback/failures?
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
import traceback
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
    collect_environment,
    collect_recent_spinnaker_reports,
    run_spinnaker_seed,
    safe_mean,
    safe_std,
    write_summary_csv,
)

TIER = "Tier 4.15 - SpiNNaker Hardware Multi-Seed Repeat"
DEFAULT_SEEDS = "42,43,44"


def parse_seeds(value: str) -> list[int]:
    seeds: list[int] = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        seeds.append(int(part))
    if not seeds:
        raise argparse.ArgumentTypeError("at least one seed is required")
    return seeds


def clean_float(value: Any) -> float | None:
    try:
        f = float(value)
    except Exception:
        return None
    return f if math.isfinite(f) else None


def seed_criteria(summary: dict[str, Any], args: argparse.Namespace) -> list[dict[str, Any]]:
    return [
        criterion(
            "sim.run has no failures",
            summary.get("sim_run_failures"),
            "==",
            0,
            int(summary.get("sim_run_failures", 0)) == 0,
        ),
        criterion(
            "summary read has no failures",
            summary.get("summary_read_failures"),
            "==",
            0,
            int(summary.get("summary_read_failures", 0)) == 0,
        ),
        criterion(
            "no synthetic fallback",
            summary.get("synthetic_fallbacks"),
            "==",
            0,
            int(summary.get("synthetic_fallbacks", 0)) == 0,
        ),
        criterion(
            "real spike readback is active",
            summary.get("total_step_spikes"),
            ">",
            0,
            (clean_float(summary.get("total_step_spikes")) or 0.0) > 0.0,
        ),
        criterion(
            "no extinction/collapse",
            summary.get("final_n_alive"),
            "==",
            args.population_size,
            clean_float(summary.get("final_n_alive")) == float(args.population_size),
        ),
        criterion(
            "fixed population has no births/deaths",
            {
                "births": summary.get("total_births"),
                "deaths": summary.get("total_deaths"),
            },
            "==",
            {"births": 0, "deaths": 0},
            int(summary.get("total_births", 0)) == 0
            and int(summary.get("total_deaths", 0)) == 0,
        ),
        criterion(
            "overall strict accuracy",
            summary.get("all_accuracy"),
            ">=",
            args.all_accuracy_threshold,
            (clean_float(summary.get("all_accuracy")) or 0.0)
            >= args.all_accuracy_threshold,
        ),
        criterion(
            "tail strict accuracy",
            summary.get("tail_accuracy"),
            ">=",
            args.tail_accuracy_threshold,
            (clean_float(summary.get("tail_accuracy")) or 0.0)
            >= args.tail_accuracy_threshold,
        ),
        criterion(
            "tail prediction/target correlation",
            summary.get("tail_prediction_target_corr"),
            ">=",
            args.corr_threshold,
            (clean_float(summary.get("tail_prediction_target_corr")) or 0.0)
            >= args.corr_threshold,
        ),
    ]


def aggregate_repeat(seed_summaries: list[dict[str, Any]], seed_statuses: dict[int, str]) -> dict[str, Any]:
    keys = [
        "all_accuracy",
        "tail_accuracy",
        "prediction_target_corr",
        "tail_prediction_target_corr",
        "final_n_alive",
        "total_births",
        "total_deaths",
        "final_mean_readout_weight",
        "runtime_seconds",
        "total_step_spikes",
        "mean_step_spikes",
        "sim_run_failures",
        "summary_read_failures",
        "synthetic_fallbacks",
    ]
    aggregate: dict[str, Any] = {
        "runs": len(seed_summaries),
        "seeds": [s.get("seed") for s in seed_summaries],
        "backend": "pyNN.spiNNaker",
        "seed_statuses": {str(k): v for k, v in seed_statuses.items()},
    }
    for key in keys:
        values = [s.get(key) for s in seed_summaries]
        aggregate[f"{key}_mean"] = safe_mean(values)
        aggregate[f"{key}_std"] = safe_std(values)
        numeric = [clean_float(v) for v in values]
        numeric = [v for v in numeric if v is not None]
        aggregate[f"{key}_min"] = min(numeric) if numeric else None
        aggregate[f"{key}_max"] = max(numeric) if numeric else None
    aggregate["sim_run_failures_sum"] = int(
        sum(int(s.get("sim_run_failures", 0)) for s in seed_summaries)
    )
    aggregate["summary_read_failures_sum"] = int(
        sum(int(s.get("summary_read_failures", 0)) for s in seed_summaries)
    )
    aggregate["synthetic_fallbacks_sum"] = int(
        sum(int(s.get("synthetic_fallbacks", 0)) for s in seed_summaries)
    )
    aggregate["total_births_sum"] = int(sum(int(s.get("total_births", 0)) for s in seed_summaries))
    aggregate["total_deaths_sum"] = int(sum(int(s.get("total_deaths", 0)) for s in seed_summaries))
    aggregate["all_seed_statuses_pass"] = all(v == "pass" for v in seed_statuses.values())
    return aggregate


def repeat_criteria(
    aggregate: dict[str, Any],
    args: argparse.Namespace,
    requested_seeds: list[int],
) -> list[dict[str, Any]]:
    return [
        criterion(
            "all requested seeds completed",
            aggregate.get("runs"),
            "==",
            len(requested_seeds),
            int(aggregate.get("runs", 0)) == len(requested_seeds),
        ),
        criterion(
            "all per-seed criteria pass",
            aggregate.get("all_seed_statuses_pass"),
            "==",
            True,
            bool(aggregate.get("all_seed_statuses_pass")),
        ),
        criterion(
            "sim.run failures sum",
            aggregate.get("sim_run_failures_sum"),
            "==",
            0,
            int(aggregate.get("sim_run_failures_sum", 0)) == 0,
        ),
        criterion(
            "summary read failures sum",
            aggregate.get("summary_read_failures_sum"),
            "==",
            0,
            int(aggregate.get("summary_read_failures_sum", 0)) == 0,
        ),
        criterion(
            "synthetic fallback sum",
            aggregate.get("synthetic_fallbacks_sum"),
            "==",
            0,
            int(aggregate.get("synthetic_fallbacks_sum", 0)) == 0,
        ),
        criterion(
            "real spike readback in every seed",
            aggregate.get("total_step_spikes_min"),
            ">",
            0,
            (clean_float(aggregate.get("total_step_spikes_min")) or 0.0) > 0.0,
        ),
        criterion(
            "fixed population has no births/deaths",
            {
                "births": aggregate.get("total_births_sum"),
                "deaths": aggregate.get("total_deaths_sum"),
            },
            "==",
            {"births": 0, "deaths": 0},
            int(aggregate.get("total_births_sum", 0)) == 0
            and int(aggregate.get("total_deaths_sum", 0)) == 0,
        ),
        criterion(
            "no extinction/collapse in any seed",
            aggregate.get("final_n_alive_min"),
            "==",
            args.population_size,
            clean_float(aggregate.get("final_n_alive_min")) == float(args.population_size)
            and clean_float(aggregate.get("final_n_alive_max")) == float(args.population_size),
        ),
        criterion(
            "minimum overall strict accuracy",
            aggregate.get("all_accuracy_min"),
            ">=",
            args.all_accuracy_threshold,
            (clean_float(aggregate.get("all_accuracy_min")) or 0.0)
            >= args.all_accuracy_threshold,
        ),
        criterion(
            "minimum tail strict accuracy",
            aggregate.get("tail_accuracy_min"),
            ">=",
            args.tail_accuracy_threshold,
            (clean_float(aggregate.get("tail_accuracy_min")) or 0.0)
            >= args.tail_accuracy_threshold,
        ),
        criterion(
            "minimum tail prediction/target correlation",
            aggregate.get("tail_prediction_target_corr_min"),
            ">=",
            args.corr_threshold,
            (clean_float(aggregate.get("tail_prediction_target_corr_min")) or 0.0)
            >= args.corr_threshold,
        ),
        criterion(
            "runtime documented for every seed",
            aggregate.get("runtime_seconds_min"),
            ">",
            0,
            (clean_float(aggregate.get("runtime_seconds_min")) or 0.0) > 0.0,
        ),
    ]


def plot_repeat_summary(seed_summaries: list[dict[str, Any]], output_path: Path) -> None:
    if plt is None or not seed_summaries:
        return
    seeds = [str(s.get("seed")) for s in seed_summaries]
    x = np.arange(len(seeds))
    metrics = [
        ("overall accuracy", "all_accuracy", "#1f6feb"),
        ("tail accuracy", "tail_accuracy", "#2f855a"),
        ("tail corr", "tail_prediction_target_corr", "#8250df"),
        ("runtime seconds", "runtime_seconds", "#9a6700"),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(10, 6.5))
    for ax, (title, key, color) in zip(axes.ravel(), metrics):
        values = [clean_float(s.get(key)) or 0.0 for s in seed_summaries]
        ax.bar(x, values, color=color)
        ax.set_title(title)
        ax.set_xticks(x)
        ax.set_xticklabels(seeds)
        ax.grid(axis="y", alpha=0.25)
    fig.suptitle("Tier 4.15 SpiNNaker Hardware Multi-Seed Repeat")
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def write_report(
    *,
    path: Path,
    mode: str,
    status: str,
    output_dir: Path,
    requested_seeds: list[int],
    criteria: list[dict[str, Any]],
    artifacts: dict[str, str],
    summary: dict[str, Any],
    seed_summaries: list[dict[str, Any]],
    failure_reason: str = "",
) -> None:
    lines = [
        "# Tier 4.15 SpiNNaker Hardware Multi-Seed Repeat Findings",
        "",
        f"- Generated: `{utc_now()}`",
        f"- Mode: `{mode}`",
        f"- Status: **{status.upper()}**",
        f"- Output directory: `{output_dir}`",
        f"- Requested seeds: `{requested_seeds}`",
        "",
        "Tier 4.15 repeats the same minimal fixed-pattern hardware capsule from Tier 4.13 across multiple seeds. It is repeatability evidence, not a harder task and not hardware scaling.",
        "",
        "## Claim Boundary",
        "",
        "- `PREPARED` means the JobManager package exists locally; it is not hardware evidence.",
        "- `PASS` requires every requested seed to run through real `pyNN.spiNNaker` with zero fallback/failures, nonzero spike readback, and learning metrics above threshold.",
        "- A pass supports repeatability of the minimal capsule only; it does not prove full hardware scaling or full CRA hardware deployment.",
        "",
        "## Summary",
        "",
    ]
    for key in [
        "hardware_run_attempted",
        "hardware_target_configured",
        "runs",
        "all_accuracy_mean",
        "all_accuracy_std",
        "all_accuracy_min",
        "tail_accuracy_mean",
        "tail_accuracy_std",
        "tail_prediction_target_corr_mean",
        "tail_prediction_target_corr_min",
        "total_step_spikes_mean",
        "runtime_seconds_mean",
        "runtime_seconds_std",
        "synthetic_fallbacks_sum",
        "sim_run_failures_sum",
        "summary_read_failures_sum",
        "all_seed_statuses_pass",
        "jobmanager_cli",
    ]:
        if key in summary:
            lines.append(f"- {key}: `{markdown_value(summary.get(key))}`")
    if failure_reason:
        lines.extend(["", f"Failure: {failure_reason}", ""])

    if seed_summaries:
        lines.extend(
            [
                "",
                "## Per-Seed Summary",
                "",
                "| Seed | Overall Acc | Tail Acc | Tail Corr | Spikes | Runtime s | Fallbacks | Status |",
                "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
            ]
        )
        statuses = summary.get("seed_statuses") or {}
        for seed_summary in seed_summaries:
            seed = str(seed_summary.get("seed"))
            lines.append(
                "| "
                f"{seed} | "
                f"{markdown_value(seed_summary.get('all_accuracy'))} | "
                f"{markdown_value(seed_summary.get('tail_accuracy'))} | "
                f"{markdown_value(seed_summary.get('tail_prediction_target_corr'))} | "
                f"{markdown_value(seed_summary.get('total_step_spikes'))} | "
                f"{markdown_value(seed_summary.get('runtime_seconds'))} | "
                f"{markdown_value(seed_summary.get('synthetic_fallbacks'))} | "
                f"{statuses.get(seed, 'unknown')} |"
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
                f"{item['name']} | "
                f"{markdown_value(item['value'])} | "
                f"{item['operator']} {markdown_value(item['threshold'])} | "
                f"{'yes' if item['passed'] else 'no'} |"
            )

    lines.extend(["", "## Artifacts", ""])
    for label, artifact in artifacts.items():
        lines.append(f"- `{label}`: `{artifact}`")
    if artifacts.get("multi_seed_summary_png"):
        lines.extend(["", "![multi_seed_summary](tier4_15_multi_seed_summary.png)", ""])
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_latest(output_dir: Path, report_path: Path, manifest_path: Path, status: str) -> None:
    latest_path = ROOT / "controlled_test_output" / "tier4_15_latest_manifest.json"
    write_json(
        latest_path,
        {
            "generated_at_utc": utc_now(),
            "manifest": str(manifest_path),
            "report": str(report_path),
            "output_dir": str(output_dir),
            "status": status,
            "canonical": False,
            "claim": "Prepared or latest Tier 4.15 multi-seed hardware repeat result; promote only after a PASS is reviewed.",
        },
    )


def write_jobmanager_capsule(output_dir: Path, args: argparse.Namespace) -> dict[str, str]:
    capsule_dir = output_dir / "jobmanager_capsule"
    capsule_dir.mkdir(parents=True, exist_ok=True)
    config_path = capsule_dir / "capsule_config.json"
    command_path = capsule_dir / "run_tier4_15_on_jobmanager.sh"
    readme_path = capsule_dir / "README_JOBMANAGER.md"
    expected_path = capsule_dir / "expected_outputs.json"

    config_payload = {
        "tier": TIER,
        "task": "fixed_pattern multi-seed hardware repeat",
        "seeds": args.seeds,
        "steps": args.steps,
        "population_size": args.population_size,
        "amplitude": args.amplitude,
        "dt_seconds": args.dt_seconds,
        "timestep_ms": args.timestep_ms,
        "thresholds": {
            "all_accuracy_threshold": args.all_accuracy_threshold,
            "tail_accuracy_threshold": args.tail_accuracy_threshold,
            "corr_threshold": args.corr_threshold,
        },
        "claim_boundary": "Prepared capsule is not evidence. PASS requires every seed to complete on real hardware with zero fallback/failures.",
    }
    write_json(config_path, config_payload)

    command_path.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                "",
                "OUT_DIR=${1:-tier4_15_job_output}",
                "python3 experiments/tier4_spinnaker_hardware_repeat.py \\",
                "  --mode run-hardware \\",
                f"  --seeds {','.join(str(s) for s in args.seeds)} \\",
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
                    "tier4_15_report.md",
                    "tier4_15_results.json",
                    "tier4_15_summary.csv",
                    "tier4_15_seed_summary.csv",
                    "tier4_15_multi_seed_summary.png",
                    "spinnaker_hardware_seed<seed>_timeseries.csv",
                    "spinnaker_hardware_seed<seed>_timeseries.png",
                ],
                "pass_requires": [
                    "all requested seeds completed",
                    "zero synthetic fallback for every seed",
                    "zero sim.run failures for every seed",
                    "zero summary-read failures for every seed",
                    "real spike readback > 0 for every seed",
                    "accuracy/correlation above thresholds for every seed",
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
                "# Tier 4.15 SpiNNaker Hardware Multi-Seed Repeat",
                "",
                "Run from the repository root inside EBRAINS/JobManager:",
                "",
                "```bash",
                "bash controlled_test_output/<tier4_15_run>/jobmanager_capsule/run_tier4_15_on_jobmanager.sh",
                "```",
                "",
                "This repeats the minimal fixed-pattern Tier 4.13 capsule across seeds. It is repeatability evidence only.",
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
        "requested_seeds": args.seeds,
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
    status = "prepared" if status == "pass" else status
    manifest_path = output_dir / "tier4_15_results.json"
    report_path = output_dir / "tier4_15_report.md"
    summary_csv_path = output_dir / "tier4_15_summary.csv"
    write_json(
        manifest_path,
        {
            "generated_at_utc": utc_now(),
            "tier": TIER,
            "mode": "prepare",
            "status": status,
            "failure_reason": failure_reason,
            "summary": summary,
            "criteria": criteria,
            "environment": env,
            "artifacts": capsule_artifacts,
        },
    )
    write_summary_csv(summary_csv_path, [summary])
    write_report(
        path=report_path,
        mode="prepare",
        status=status,
        output_dir=output_dir,
        requested_seeds=args.seeds,
        criteria=criteria,
        artifacts={"manifest_json": str(manifest_path), "summary_csv": str(summary_csv_path), **capsule_artifacts},
        summary=summary,
        seed_summaries=[],
        failure_reason=failure_reason,
    )
    write_latest(output_dir, report_path, manifest_path, status)
    return 0 if status == "prepared" else 1


def run_hardware(args: argparse.Namespace, output_dir: Path) -> int:
    run_started_epoch = time.time()
    env = collect_environment(args)
    hardware_target_configured = bool(env.get("hardware_target_configured"))
    if args.require_real_hardware and not hardware_target_configured:
        failure = "No real SpiNNaker target is configured locally. Refusing to run a virtual-board result as Tier 4.15 hardware."
        summary = {
            "mode": "run-hardware",
            "hardware_run_attempted": False,
            "hardware_target_configured": False,
            "requested_seeds": args.seeds,
            "jobmanager_cli": env.get("jobmanager_cli"),
        }
        criteria = [criterion("real SpiNNaker target configured", hardware_target_configured, "==", True, False)]
        manifest_path = output_dir / "tier4_15_results.json"
        report_path = output_dir / "tier4_15_report.md"
        summary_csv_path = output_dir / "tier4_15_summary.csv"
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
        write_report(
            path=report_path,
            mode="run-hardware",
            status="blocked",
            output_dir=output_dir,
            requested_seeds=args.seeds,
            criteria=criteria,
            artifacts={"manifest_json": str(manifest_path), "summary_csv": str(summary_csv_path)},
            summary=summary,
            seed_summaries=[],
            failure_reason=failure,
        )
        write_latest(output_dir, report_path, manifest_path, "blocked")
        return 1

    summaries: list[dict[str, Any]] = []
    seed_statuses: dict[int, str] = {}
    per_seed_criteria: dict[str, list[dict[str, Any]]] = {}
    artifacts: dict[str, str] = {}
    failure_reason = ""
    failure_traceback = ""
    failure_diagnostics: dict[str, Any] = {}
    hardware_run_attempted = False

    for seed in args.seeds:
        try:
            hardware_run_attempted = True
            rows, summary = run_spinnaker_seed(seed=seed, args=args)
            criteria = seed_criteria(summary, args)
            seed_status, seed_failure = pass_fail(criteria)
            seed_statuses[int(seed)] = seed_status
            per_seed_criteria[str(seed)] = criteria
            if seed_failure and args.stop_on_fail:
                failure_reason = f"seed {seed}: {seed_failure}"
            csv_path = output_dir / f"spinnaker_hardware_seed{seed}_timeseries.csv"
            png_path = output_dir / f"spinnaker_hardware_seed{seed}_timeseries.png"
            write_csv(csv_path, rows)
            plot_case(rows, png_path, f"Tier 4.15 SpiNNaker hardware seed {seed}")
            artifacts[f"seed_{seed}_timeseries_csv"] = str(csv_path)
            if png_path.exists():
                artifacts[f"seed_{seed}_timeseries_png"] = str(png_path)
            summaries.append(summary)
            if failure_reason and args.stop_on_fail:
                break
        except Exception as exc:
            seed_statuses[int(seed)] = "fail"
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
                inner = str(failure_diagnostics.get("last_backend_traceback", ""))
                if inner:
                    inner_path = output_dir / f"seed_{seed}_inner_backend_traceback.txt"
                    inner_path.write_text(inner, encoding="utf-8")
                    artifacts[f"seed_{seed}_inner_backend_traceback"] = str(inner_path)
            break

    aggregate = aggregate_repeat(summaries, seed_statuses)
    aggregate.update(
        {
            "mode": "run-hardware",
            "hardware_run_attempted": hardware_run_attempted,
            "hardware_target_configured": hardware_target_configured,
            "requested_seeds": args.seeds,
            "jobmanager_cli": env.get("jobmanager_cli"),
            "failure_reason": failure_reason,
            "failure_diagnostics": failure_diagnostics,
        }
    )
    criteria = repeat_criteria(aggregate, args, args.seeds) if summaries else []
    status, criteria_failure = pass_fail(criteria) if criteria else ("fail", failure_reason)
    if criteria_failure:
        failure_reason = criteria_failure

    seed_summary_csv = output_dir / "tier4_15_seed_summary.csv"
    write_summary_csv(seed_summary_csv, summaries)
    artifacts["seed_summary_csv"] = str(seed_summary_csv)
    summary_png = output_dir / "tier4_15_multi_seed_summary.png"
    plot_repeat_summary(summaries, summary_png)
    if summary_png.exists():
        artifacts["multi_seed_summary_png"] = str(summary_png)
    artifacts.update(collect_recent_spinnaker_reports(output_dir, run_started_epoch))
    if failure_traceback:
        aggregate["failure_traceback"] = failure_traceback

    manifest_path = output_dir / "tier4_15_results.json"
    report_path = output_dir / "tier4_15_report.md"
    summary_csv_path = output_dir / "tier4_15_summary.csv"
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
            "per_seed_criteria": per_seed_criteria,
            "seed_summaries": summaries,
            "artifacts": artifacts,
            "environment": env,
            "matplotlib_error": MATPLOTLIB_ERROR,
        },
    )
    write_summary_csv(summary_csv_path, [aggregate])
    write_report(
        path=report_path,
        mode="run-hardware",
        status=status,
        output_dir=output_dir,
        requested_seeds=args.seeds,
        criteria=criteria,
        artifacts={"manifest_json": str(manifest_path), "summary_csv": str(summary_csv_path), **artifacts},
        summary=aggregate,
        seed_summaries=summaries,
        failure_reason=failure_reason,
    )
    write_latest(output_dir, report_path, manifest_path, status)
    return 0 if status == "pass" else 1


def ingest_results(args: argparse.Namespace, output_dir: Path) -> int:
    if args.ingest_dir is None:
        raise SystemExit("--ingest-dir is required in ingest mode")
    ingest_dir = args.ingest_dir.resolve()
    source = ingest_dir / "tier4_15_results.json"
    if not source.exists():
        raise SystemExit(f"No tier4_15_results.json found in {ingest_dir}")
    data = json.loads(source.read_text(encoding="utf-8"))
    status = str(data.get("status", "unknown"))
    summary = dict(data.get("summary") or {})
    summary.update({"mode": "ingest", "ingested_from": str(source)})
    criteria = list(data.get("criteria") or [])
    seed_summaries = list(data.get("seed_summaries") or [])

    manifest_path = output_dir / "tier4_15_results.json"
    report_path = output_dir / "tier4_15_report.md"
    summary_csv_path = output_dir / "tier4_15_summary.csv"
    write_json(
        manifest_path,
        {
            "generated_at_utc": utc_now(),
            "tier": TIER,
            "mode": "ingest",
            "status": status,
            "ingested_from": str(source),
            "summary": summary,
            "criteria": criteria,
            "seed_summaries": seed_summaries,
            "source_manifest": data,
        },
    )
    write_summary_csv(summary_csv_path, [summary])
    artifacts = {"manifest_json": str(manifest_path), "summary_csv": str(summary_csv_path), "ingested_source": str(source)}
    write_report(
        path=report_path,
        mode="ingest",
        status=status,
        output_dir=output_dir,
        requested_seeds=list(summary.get("requested_seeds") or args.seeds),
        criteria=criteria,
        artifacts=artifacts,
        summary=summary,
        seed_summaries=seed_summaries,
        failure_reason=str(data.get("failure_reason", "")),
    )
    write_latest(output_dir, report_path, manifest_path, status)
    return 0 if status == "pass" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepare, run, or ingest Tier 4.15 multi-seed SpiNNaker hardware repeat.",
    )
    parser.add_argument("--mode", choices=["prepare", "run-hardware", "ingest"], default="prepare")
    parser.add_argument("--seeds", type=parse_seeds, default=parse_seeds(DEFAULT_SEEDS))
    parser.add_argument("--steps", type=int, default=120)
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
    parser.add_argument("--require-real-hardware", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--stop-on-backend-fallback", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--stop-on-fail", action="store_true")
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
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = args.output_dir or (ROOT / "controlled_test_output" / f"tier4_15_{timestamp}")
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
