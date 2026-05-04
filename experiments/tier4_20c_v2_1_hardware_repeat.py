#!/usr/bin/env python3
"""Tier 4.20c v2.1 three-seed chunked SpiNNaker hardware repeat.

Tier 4.20c repeats the Tier 4.20b v2.1 chunked-host bridge across seeds
42, 43, and 44. It deliberately uses the same proven Tier 4.16 hardware runner
and the same v2.1 bridge profile rather than claiming native/on-chip v2.1
mechanism execution.

Claim boundary:
- Prepared output is not hardware evidence.
- A run-hardware PASS means the v2.1 bridge/transport path repeats across the
  three predeclared seeds with real spike readback.
- It does not prove full v2.1 hardware execution, custom C, on-chip memory,
  on-chip self-evaluation, language, planning, AGI, or macro eligibility.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
TIER = "Tier 4.20c - v2.1 Three-Seed Chunked Hardware Repeat"
TIER4_16_RUNNER = ROOT / "experiments" / "tier4_harder_spinnaker_capsule.py"
TIER4_20B_LATEST = CONTROLLED / "tier4_20b_latest_manifest.json"
DEFAULT_TASKS = "delayed_cue,hard_noisy_switching"
DEFAULT_SEEDS = "42,43,44"
EXPECTED_SEEDS = [42, 43, 44]
DEFAULT_STEPS = 1200
DEFAULT_CHUNK_SIZE = 50
DEFAULT_POPULATION_SIZE = 8
DEFAULT_DELAYED_LR = 0.20
RUNNER_REVISION = "tier4_20c_inprocess_no_baselines_20260430_0000"

from experiments import tier4_20b_v2_1_hardware_probe as bridge


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    bridge.write_json(path, payload)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    bridge.write_csv(path, rows)


def parse_tasks(value: str) -> list[str]:
    return bridge.parse_tasks(value)


def parse_seeds(value: str) -> list[int]:
    return bridge.parse_seeds(value)


def criterion(name: str, value: Any, rule: str, passed: bool) -> dict[str, Any]:
    return bridge.criterion(name, value, rule, passed)


def pass_fail(criteria: list[dict[str, Any]]) -> tuple[str, str]:
    return bridge.pass_fail(criteria)


def read_json(path: Path) -> dict[str, Any]:
    return bridge.read_json(path)


def expected_runs(args: argparse.Namespace) -> int:
    return len(args.tasks) * len(args.seeds)


def latest_420b_status() -> tuple[str, str | None]:
    if not TIER4_20B_LATEST.exists():
        return "missing", None
    try:
        payload = read_json(TIER4_20B_LATEST)
    except Exception:
        return "unreadable", None
    return str(payload.get("status", "unknown")).lower(), str(payload.get("manifest") or "")


def preflight_criteria(args: argparse.Namespace, mode: str) -> list[dict[str, Any]]:
    source_layout = bridge.ensure_source_layout()
    b_status, b_manifest = latest_420b_status()
    # EBRAINS JobManager runs from a deliberately small source bundle that
    # excludes controlled_test_output/.  The local prepare path should still
    # verify that Tier 4.20b passed, but run-hardware must not require uploading
    # the prior evidence archive just to repeat the hardware bridge.
    prerequisite_ok = b_status == "pass" or (mode == "run-hardware" and b_status == "missing")
    prerequisite_rule = "status == pass locally OR fresh run-hardware bundle"
    return [
        criterion("Tier 4.20c runner revision", RUNNER_REVISION, "expected current source", True),
        criterion("source package import path available", source_layout, "coral_reef_spinnaker exists", bool(source_layout.get("canonical_package_exists"))),
        criterion("Tier 4.16 child hardware runner exists", str(TIER4_16_RUNNER), "exists", TIER4_16_RUNNER.exists()),
        criterion(
            "Tier 4.20b prerequisite satisfied for execution context",
            {"status": b_status, "manifest": b_manifest, "mode": mode},
            prerequisite_rule,
            prerequisite_ok,
        ),
        criterion("three predeclared seeds requested", args.seeds, "== [42, 43, 44]", list(args.seeds) == EXPECTED_SEEDS),
        criterion("tasks match v2.1 bridge repeat", args.tasks, "delayed_cue + hard_noisy_switching", list(args.tasks) == ["delayed_cue", "hard_noisy_switching"]),
        criterion("runtime mode is chunked", "chunked", "fixed", True),
        criterion("learning location is host", "host", "fixed", True),
        criterion("chunk size uses 4.20b default", args.chunk_size_steps, "== 50", int(args.chunk_size_steps) == DEFAULT_CHUNK_SIZE),
        criterion("macro eligibility disabled", False, "== false", True),
        criterion("delayed_lr_0_20 selected", args.delayed_readout_lr, "== 0.20", abs(float(args.delayed_readout_lr) - DEFAULT_DELAYED_LR) < 1e-12),
        criterion("mode has explicit claim boundary", mode, "prepare|run-hardware|ingest", mode in {"prepare", "run-hardware", "ingest"}),
    ]


def write_jobmanager_capsule(output_dir: Path, args: argparse.Namespace) -> dict[str, str]:
    capsule_dir = output_dir / "jobmanager_capsule"
    capsule_dir.mkdir(parents=True, exist_ok=True)
    config_path = capsule_dir / "capsule_config.json"
    expected_path = capsule_dir / "expected_outputs.json"
    readme_path = capsule_dir / "README_JOBMANAGER.md"
    bridge_path = capsule_dir / "v2_1_bridge_profile.json"

    config = {
        "tier": TIER,
        "mode": "prepare",
        "baseline": "v2.1",
        "prerequisite": "Tier 4.20b one-seed bridge pass",
        "tasks": args.tasks,
        "seeds": args.seeds,
        "steps": args.steps,
        "population_size": args.population_size,
        "runtime_mode": "chunked",
        "learning_location": "host",
        "chunk_size_steps": args.chunk_size_steps,
        "delayed_readout_lr": args.delayed_readout_lr,
        "macro_eligibility_enabled": False,
        "expected_child_runs": expected_runs(args),
        "direct_jobmanager_command": "cra_420c/experiments/tier4_20c_v2_1_hardware_repeat.py --mode run-hardware --tasks delayed_cue,hard_noisy_switching --seeds 42,43,44 --steps 1200 --population-size 8 --chunk-size-steps 50 --delayed-readout-lr 0.20 --no-require-real-hardware --output-dir tier4_20c_job_output",
        "claim_boundary": [
            "Prepared capsule is not hardware evidence.",
            "A PASS requires six child pyNN.spiNNaker runs, zero fallback/failures, and nonzero real spike readback across the three predeclared seeds.",
            "This is v2.1 bridge repeatability evidence, not native/on-chip v2.1 mechanism execution.",
        ],
    }
    write_json(config_path, config)
    write_json(bridge_path, {"generated_at_utc": utc_now(), "profile": bridge.bridge_profile_summary(), "rows": bridge.PROMOTED_BRIDGE_PROFILE})
    write_json(
        expected_path,
        {
            "required": [
                "tier4_20c_results.json",
                "tier4_20c_report.md",
                "tier4_20c_summary.csv",
                "child_tier4_16/tier4_16_results.json",
                "child_tier4_16/tier4_16_report.md",
                "child_tier4_16/spinnaker_hardware_<task>_seed<seed>_timeseries.csv",
            ],
            "pass_requires": [
                "Tier 4.20b prerequisite pass recorded locally",
                "seeds exactly 42,43,44",
                "tasks delayed_cue and hard_noisy_switching",
                "six child hardware runs",
                "chunked host mode with chunk_size_steps=50",
                "macro eligibility disabled/excluded",
                "child Tier 4.16 hardware run status=pass",
                "zero sim.run failures, read failures, and synthetic fallback",
                "real spike readback > 0",
            ],
        },
    )
    readme_path.write_text(
        "\n".join(
            [
                "# Tier 4.20c v2.1 Three-Seed Chunked Hardware Repeat",
                "",
                "Upload only `experiments/` and `coral_reef_spinnaker/` under a fresh `cra_420c/` folder.",
                "",
                "Use the EBRAINS JobManager command line directly:",
                "",
                "```text",
                "cra_420c/experiments/tier4_20c_v2_1_hardware_repeat.py --mode run-hardware --tasks delayed_cue,hard_noisy_switching --seeds 42,43,44 --steps 1200 --population-size 8 --chunk-size-steps 50 --delayed-readout-lr 0.20 --no-require-real-hardware --output-dir tier4_20c_job_output",
                "```",
                "",
                "Do not upload `controlled_test_output/`, `baselines/`, old reports, or downloaded artifacts.",
                "",
                "A pass is repeatability evidence for the v2.1 bridge/transport path, not native/on-chip v2.1 execution.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return {
        "capsule_dir": str(capsule_dir),
        "capsule_config_json": str(config_path),
        "expected_outputs_json": str(expected_path),
        "jobmanager_readme": str(readme_path),
        "v2_1_bridge_profile_json": str(bridge_path),
    }


def build_child_args(args: argparse.Namespace, child_dir: Path) -> argparse.Namespace:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from experiments.tier4_harder_spinnaker_capsule import build_parser as build_tier4_16_parser

    child = build_tier4_16_parser().parse_args([])
    child.mode = "run-hardware"
    child.tasks = list(args.tasks)
    child.seeds = list(args.seeds)
    child.steps = int(args.steps)
    child.population_size = int(args.population_size)
    child.runtime_mode = "chunked"
    child.learning_location = "host"
    child.chunk_size_steps = int(args.chunk_size_steps)
    child.delayed_readout_lr = float(args.delayed_readout_lr)
    child.spinnaker_hostname = args.spinnaker_hostname
    child.require_real_hardware = bool(args.require_real_hardware)
    child.stop_on_fail = bool(args.stop_on_fail)
    child.output_dir = child_dir
    child.ingest_dir = None
    return child


def child_command(args: argparse.Namespace, child_dir: Path) -> list[str]:
    return [
        sys.executable,
        str(TIER4_16_RUNNER),
        "--mode",
        "run-hardware",
        "--require-real-hardware" if args.require_real_hardware else "--no-require-real-hardware",
        "--tasks",
        ",".join(args.tasks),
        "--seeds",
        ",".join(str(seed) for seed in args.seeds),
        "--steps",
        str(args.steps),
        "--population-size",
        str(args.population_size),
        "--runtime-mode",
        "chunked",
        "--learning-location",
        "host",
        "--chunk-size-steps",
        str(args.chunk_size_steps),
        "--delayed-readout-lr",
        str(args.delayed_readout_lr),
        "--output-dir",
        str(child_dir),
    ]


def child_seed_coverage(child_summary: dict[str, Any]) -> tuple[list[int], list[str], int]:
    seeds = sorted({int(seed) for seed in (child_summary.get("child_seeds") or [])})
    tasks = sorted(str(task) for task in (child_summary.get("child_tasks") or []))
    runs = int(child_summary.get("child_runs") or 0)
    return seeds, tasks, runs


def write_report(path: Path, result: dict[str, Any]) -> None:
    summary = result.get("summary", {})
    lines = [
        "# Tier 4.20c v2.1 Three-Seed Chunked Hardware Repeat",
        "",
        f"- Generated: `{result['generated_at_utc']}`",
        f"- Mode: `{result['mode']}`",
        f"- Status: **{result['status'].upper()}**",
        f"- Output directory: `{result['output_dir']}`",
        "",
        "Tier 4.20c repeats the passed Tier 4.20b v2.1 bridge/transport path across seeds `42`, `43`, and `44`.",
        "",
        "## Claim Boundary",
        "",
        "- `PREPARED` means the JobManager capsule exists locally; it is not hardware evidence.",
        "- `PASS` in `run-hardware` requires a passing child pyNN.spiNNaker run, zero fallback/failures, nonzero real spike readback, and six expected child runs.",
        "- This is repeatability evidence for the current v2.1 bridge/transport path, not full v2.1 native/on-chip execution, custom C, language, planning, AGI, or macro eligibility evidence.",
        "",
        "## Summary",
        "",
    ]
    for key in [
        "baseline",
        "runner_revision",
        "tasks",
        "seeds",
        "steps",
        "population_size",
        "runtime_mode",
        "learning_location",
        "chunk_size_steps",
        "expected_child_runs",
        "macro_eligibility_enabled",
        "hardware_run_attempted",
        "child_status",
        "child_hardware_run_attempted",
        "child_runs",
        "child_total_step_spikes_min",
        "child_sim_run_failures_sum",
        "child_summary_read_failures_sum",
        "child_synthetic_fallbacks_sum",
        "capsule_dir",
    ]:
        if key in summary:
            lines.append(f"- {key}: `{summary.get(key)}`")
    if result.get("failure_reason"):
        lines.extend(["", f"Failure: {result['failure_reason']}", ""])
    task_summaries = summary.get("child_task_summaries") or []
    if task_summaries:
        lines.extend(["", "## Child Task Summary", "", "| Task | Runs | Tail min | Tail mean | Corr mean | Spikes min |", "| --- | --- | --- | --- | --- | --- |"])
        for row in task_summaries:
            lines.append(
                f"| `{row.get('task')}` | `{row.get('runs')}` | `{row.get('tail_accuracy_min')}` | `{row.get('tail_accuracy_mean')}` | `{row.get('tail_prediction_target_corr_mean')}` | `{row.get('total_step_spikes_min')}` |"
            )
    lines.extend(["", "## Bridge Profile", "", "| Mechanism | Status | Probe Role | Boundary |", "| --- | --- | --- | --- |"])
    for row in bridge.PROMOTED_BRIDGE_PROFILE:
        lines.append(f"| {row['mechanism']} | `{row['status']}` | `{row['probe_role']}` | {row['boundary']} |")
    lines.extend(["", "## Criteria", "", "| Criterion | Value | Rule | Pass |", "| --- | --- | --- | --- |"])
    for item in result.get("criteria", []):
        lines.append(f"| {item['name']} | `{item['value']}` | `{item['rule']}` | {'yes' if item.get('passed') else 'no'} |")
    lines.extend(["", "## Artifacts", ""])
    for key, value in sorted((result.get("artifacts") or {}).items()):
        lines.append(f"- `{key}`: `{value}`")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_latest(output_dir: Path, report_path: Path, manifest_path: Path, status: str) -> None:
    write_json(
        CONTROLLED / "tier4_20c_latest_manifest.json",
        {
            "generated_at_utc": utc_now(),
            "manifest": str(manifest_path),
            "report": str(report_path),
            "output_dir": str(output_dir),
            "status": status,
            "canonical": False,
            "claim": "Latest Tier 4.20c v2.1 three-seed chunked hardware repeat; pass means bridge repeatability, not native/on-chip v2.1.",
        },
    )


def finalize(output_dir: Path, result: dict[str, Any]) -> int:
    manifest_path = output_dir / "tier4_20c_results.json"
    report_path = output_dir / "tier4_20c_report.md"
    summary_path = output_dir / "tier4_20c_summary.csv"
    bridge_path = output_dir / "tier4_20c_bridge_profile.json"
    result["artifacts"]["results_json"] = str(manifest_path)
    result["artifacts"]["report_md"] = str(report_path)
    result["artifacts"]["summary_csv"] = str(summary_path)
    result["artifacts"]["bridge_profile_json"] = str(bridge_path)
    write_json(bridge_path, {"generated_at_utc": utc_now(), "profile": bridge.bridge_profile_summary(), "rows": bridge.PROMOTED_BRIDGE_PROFILE})
    write_json(manifest_path, result)
    write_csv(summary_path, [result.get("summary", {})])
    write_report(report_path, result)
    write_latest(output_dir, report_path, manifest_path, result["status"])
    return 0 if result["status"] in {"pass", "prepared"} else 1


def prepare_capsule(args: argparse.Namespace, output_dir: Path) -> int:
    artifacts = write_jobmanager_capsule(output_dir, args)
    criteria = preflight_criteria(args, "prepare")
    criteria.append(criterion("capsule directory exists", artifacts["capsule_dir"], "exists", Path(artifacts["capsule_dir"]).exists()))
    status, failure = pass_fail(criteria)
    status = "prepared" if status == "pass" else "fail"
    result = {
        "tier": TIER,
        "generated_at_utc": utc_now(),
        "mode": "prepare",
        "status": status,
        "failure_reason": failure,
        "output_dir": str(output_dir),
        "summary": {
            "baseline": "v2.1",
            "runner_revision": RUNNER_REVISION,
            "tasks": args.tasks,
            "seeds": args.seeds,
            "steps": args.steps,
            "population_size": args.population_size,
            "runtime_mode": "chunked",
            "learning_location": "host",
            "chunk_size_steps": args.chunk_size_steps,
            "expected_child_runs": expected_runs(args),
            "macro_eligibility_enabled": False,
            "hardware_run_attempted": False,
            "capsule_dir": artifacts.get("capsule_dir"),
            "bridge_profile": bridge.bridge_profile_summary(),
        },
        "criteria": criteria,
        "artifacts": artifacts,
    }
    return finalize(output_dir, result)


def run_hardware(args: argparse.Namespace, output_dir: Path) -> int:
    criteria = preflight_criteria(args, "run-hardware")
    child_dir = output_dir / "child_tier4_16"
    child_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = output_dir / "tier4_20c_child_stdout.log"
    stderr_path = output_dir / "tier4_20c_child_stderr.log"
    started = time.perf_counter()
    cmd = child_command(args, child_dir)
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from experiments.tier4_harder_spinnaker_capsule import run_hardware as run_tier4_16_hardware

    stdout_path.write_text("Tier 4.16 executed in-process by Tier 4.20c; JobManager captures live stdout.\n", encoding="utf-8")
    stderr_path.write_text("Tier 4.16 executed in-process by Tier 4.20c; JobManager captures live stderr.\n", encoding="utf-8")
    child_args = build_child_args(args, child_dir)
    child_return_code = run_tier4_16_hardware(child_args, child_dir)
    child_manifest_path = child_dir / "tier4_16_results.json"
    child_manifest: dict[str, Any] = {}
    if child_manifest_path.exists():
        child_manifest = read_json(child_manifest_path)
    child_summary = bridge.summarize_child(child_manifest) if child_manifest else {"child_status": "missing_manifest"}
    child_seeds, child_tasks, child_runs = child_seed_coverage(child_summary)
    criteria.extend(
        [
            criterion("child Tier 4.16 in-process runner exited cleanly", child_return_code, "== 0", child_return_code == 0),
            criterion("child Tier 4.16 manifest exists", str(child_manifest_path), "exists", child_manifest_path.exists()),
            criterion("child hardware status passed", child_summary.get("child_status"), "== pass", child_summary.get("child_status") == "pass"),
            criterion("child hardware was attempted", child_summary.get("child_hardware_run_attempted"), "== true", bool(child_summary.get("child_hardware_run_attempted"))),
            criterion("child seeds match repeat plan", child_seeds, "== [42, 43, 44]", child_seeds == EXPECTED_SEEDS),
            criterion("child tasks match repeat plan", child_tasks, "== delayed_cue + hard_noisy_switching", child_tasks == ["delayed_cue", "hard_noisy_switching"]),
            criterion("child run count matches task x seed grid", child_runs, f"== {expected_runs(args)}", child_runs == expected_runs(args)),
            criterion("child sim.run failures zero", child_summary.get("child_sim_run_failures_sum"), "== 0", int(child_summary.get("child_sim_run_failures_sum") or 0) == 0),
            criterion("child summary read failures zero", child_summary.get("child_summary_read_failures_sum"), "== 0", int(child_summary.get("child_summary_read_failures_sum") or 0) == 0),
            criterion("child synthetic fallback zero", child_summary.get("child_synthetic_fallbacks_sum"), "== 0", int(child_summary.get("child_synthetic_fallbacks_sum") or 0) == 0),
            criterion("child real spike readback nonzero", child_summary.get("child_total_step_spikes_min"), "> 0", float(child_summary.get("child_total_step_spikes_min") or 0.0) > 0.0),
            criterion("child runtime documented", child_summary.get("child_runtime_seconds_mean"), "finite", bridge.finite_number(child_summary.get("child_runtime_seconds_mean"))),
        ]
    )
    status, failure = pass_fail(criteria)
    artifacts = {
        "child_output_dir": str(child_dir),
        "child_stdout_log": str(stdout_path),
        "child_stderr_log": str(stderr_path),
    }
    for name in [
        "tier4_16_results.json",
        "tier4_16_report.md",
        "tier4_16_summary.csv",
        "tier4_16_task_summary.csv",
        "tier4_16_hardware_summary.png",
    ]:
        path = child_dir / name
        if path.exists():
            artifacts[f"child_{name}"] = str(path)
    for path in sorted(child_dir.glob("spinnaker_hardware_*_timeseries.*")):
        artifacts[f"child_{path.name}"] = str(path)
    result = {
        "tier": TIER,
        "generated_at_utc": utc_now(),
        "mode": "run-hardware",
        "status": status,
        "failure_reason": failure or str(child_manifest.get("failure_reason") or ""),
        "output_dir": str(output_dir),
        "summary": {
            "baseline": "v2.1",
            "runner_revision": RUNNER_REVISION,
            "tasks": args.tasks,
            "seeds": args.seeds,
            "steps": args.steps,
            "population_size": args.population_size,
            "runtime_mode": "chunked",
            "learning_location": "host",
            "chunk_size_steps": args.chunk_size_steps,
            "expected_child_runs": expected_runs(args),
            "macro_eligibility_enabled": False,
            "hardware_run_attempted": bool(child_summary.get("child_hardware_run_attempted")),
            "bridge_profile": bridge.bridge_profile_summary(),
            "runtime_seconds": time.perf_counter() - started,
            "child_return_code": child_return_code,
            "child_execution_mode": "in_process",
            **child_summary,
        },
        "criteria": criteria,
        "artifacts": artifacts,
        "child_manifest": child_manifest,
        "child_command": cmd,
    }
    return finalize(output_dir, result)


def ingest_results(args: argparse.Namespace, output_dir: Path) -> int:
    if args.ingest_dir is None:
        raise SystemExit("--ingest-dir is required in ingest mode")
    source_dir = args.ingest_dir.resolve()
    source_manifest = source_dir / "tier4_20c_results.json"
    if not source_manifest.exists():
        raise SystemExit(f"No tier4_20c_results.json found in {source_dir}")
    source = read_json(source_manifest)
    status = str(source.get("status", "unknown")).lower()
    artifacts = {"ingested_source": str(source_manifest)}
    for pattern in [
        "tier4_20c_*",
        "child_tier4_16/tier4_16_*",
        "child_tier4_16/spinnaker_hardware_*",
        "child_tier4_16/raw_hardware_artifacts/*",
    ]:
        for src in sorted(source_dir.glob(pattern)):
            if src.is_dir():
                continue
            rel = src.relative_to(source_dir)
            dest = output_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            artifacts[str(rel)] = str(dest)
    result = {
        "tier": TIER,
        "generated_at_utc": utc_now(),
        "mode": "ingest",
        "status": status,
        "failure_reason": source.get("failure_reason", ""),
        "output_dir": str(output_dir),
        "summary": {**dict(source.get("summary") or {}), "ingested_from": str(source_manifest)},
        "criteria": source.get("criteria") or [],
        "artifacts": artifacts,
        "source_manifest": source,
    }
    return finalize(output_dir, result)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare, run, or ingest Tier 4.20c v2.1 three-seed chunked SpiNNaker hardware repeat.")
    parser.add_argument("--mode", choices=["prepare", "run-hardware", "ingest"], default="prepare")
    parser.add_argument("--tasks", type=parse_tasks, default=parse_tasks(DEFAULT_TASKS))
    parser.add_argument("--seeds", type=parse_seeds, default=parse_seeds(DEFAULT_SEEDS))
    parser.add_argument("--steps", type=int, default=DEFAULT_STEPS)
    parser.add_argument("--population-size", type=int, default=DEFAULT_POPULATION_SIZE)
    parser.add_argument("--chunk-size-steps", type=int, default=DEFAULT_CHUNK_SIZE)
    parser.add_argument("--delayed-readout-lr", type=float, default=DEFAULT_DELAYED_LR)
    parser.add_argument("--spinnaker-hostname", default=None)
    parser.add_argument("--require-real-hardware", action=argparse.BooleanOptionalAction, default=True)
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
    if args.chunk_size_steps <= 0:
        parser.error("--chunk-size-steps must be positive")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = "prepared" if args.mode == "prepare" else args.mode.replace("-", "_")
    output_dir = args.output_dir or (CONTROLLED / f"tier4_20c_{stamp}_{suffix}")
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
