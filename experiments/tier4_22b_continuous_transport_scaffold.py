#!/usr/bin/env python3
"""Tier 4.22b continuous transport scaffold.

This is the first implementation step after the Tier 4.22a/a0 contracts. It is
not the final learning runtime. It isolates the transport problem:

    scheduled input -> one continuous sim.run -> compact/binned spike readback

Learning is intentionally disabled in this tier so timing, input delivery,
spike dynamics, readback, and provenance can be debugged before reward/plasticity
state is added in Tier 4.22d. If this scaffold fails, a learning-enabled custom
runtime would be uninterpretable.

Claim boundary:
- local PASS = continuous transport scaffold works under constrained PyNN/NEST.
- run-hardware PASS = continuous transport scaffold works on real pyNN.spiNNaker.
- Neither is a learning claim, custom-C claim, native/on-chip learning claim, or
  speedup claim until runtime/readback costs are measured against reference.
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
import time
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"
TIER = "Tier 4.22b - Continuous Transport Scaffold"
RUNNER_REVISION = "tier4_22b_continuous_transport_scaffold_20260430_0000"
TIER4_22A0_LATEST = CONTROLLED / "tier4_22a0_latest_manifest.json"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from coral_reef_spinnaker.runtime_modes import make_runtime_plan  # noqa: E402
from coral_reef_spinnaker.spinnaker_compat import apply_spinnaker_numpy2_compat_patches  # noqa: E402
from tier2_learning import markdown_value, write_csv, write_json  # noqa: E402
from tier4_harder_spinnaker_capsule import (  # noqa: E402
    TASK_PARTS,
    bin_spiketrains,
    build_task,
    compressed_current_schedule,
    parse_seeds,
    parse_tasks,
    scheduled_currents,
)

DEFAULT_TASKS = "delayed_cue,hard_noisy_switching"
DEFAULT_SEEDS = "42"
DEFAULT_STEPS = 1200
DEFAULT_POPULATION_SIZE = 8
DEFAULT_AMPLITUDE = 0.01
DEFAULT_DT_SECONDS = 0.05
DEFAULT_BASE_CURRENT_NA = 1.4
DEFAULT_CUE_CURRENT_GAIN_NA = 0.2
DEFAULT_MIN_CURRENT_NA = 0.0
DEFAULT_DELAYED_LR = 0.20
DEFAULT_HARD_MIN_DELAY = 3
DEFAULT_HARD_MAX_DELAY = 5
DEFAULT_HARD_PERIOD = 7
DEFAULT_HARD_NOISE_PROB = 0.20
DEFAULT_HARD_SENSORY_NOISE_FRACTION = 0.25
DEFAULT_HARD_MIN_SWITCH_INTERVAL = 32
DEFAULT_HARD_MAX_SWITCH_INTERVAL = 48


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    return value


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json_safe(path: Path, payload: dict[str, Any]) -> None:
    write_json(path, json_safe(payload))


def write_csv_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    keys: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                keys.append(key)
                seen.add(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def criterion(name: str, value: Any, rule: str, passed: bool, note: str = "") -> dict[str, Any]:
    return {"name": name, "value": value, "rule": rule, "passed": bool(passed), "note": note}


def latest_status(path: Path) -> tuple[str, str | None]:
    if not path.exists():
        return "missing", None
    try:
        payload = read_json(path)
    except Exception as exc:
        return f"unreadable:{type(exc).__name__}", None
    return str(payload.get("status", "unknown")).lower(), str(payload.get("manifest") or "")


def case_label(task_name: str, seed: int) -> str:
    return f"{task_name}_seed{seed}"


def sim_module_for_mode(mode: str):
    if mode == "local":
        import pyNN.nest as sim
        return sim, "pyNN.nest", "local_constrained_nest_continuous_transport"
    if mode == "run-hardware":
        import pyNN.spiNNaker as sim
        return sim, "pyNN.spiNNaker", "spinnaker_continuous_transport"
    raise ValueError(f"mode {mode!r} does not have a simulator module")


def run_transport_case(*, task_name: str, seed: int, args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    started = time.perf_counter()
    if args.mode == "run-hardware":
        compat_status = apply_spinnaker_numpy2_compat_patches()
    else:
        compat_status = {"applied": False, "reason": "local mode"}
    sim, backend, backend_path = sim_module_for_mode(args.mode)
    setup_kwargs: dict[str, Any] = {"timestep": float(args.timestep_ms)}
    if args.mode == "run-hardware" and args.spinnaker_hostname:
        setup_kwargs["spinnaker_hostname"] = str(args.spinnaker_hostname)

    task = build_task(task_name, seed=seed, args=args)
    currents = scheduled_currents(task, args)
    dt_ms = float(args.dt_seconds) * 1000.0
    times, amplitudes = compressed_current_schedule(currents, dt_ms)
    spike_bins = np.zeros(task.steps, dtype=int)
    rows: list[dict[str, Any]] = []
    sim_run_calls = 0
    sim_run_failures = 0
    readback_failures = 0
    synthetic_fallbacks = 0
    scheduled_input_failures = 0

    try:
        sim.setup(**setup_kwargs)
        if not hasattr(sim, "StepCurrentSource"):
            scheduled_input_failures = 1
            raise RuntimeError(f"{backend} does not expose StepCurrentSource")
        cell = sim.IF_curr_exp(
            i_offset=0.0,
            tau_m=20.0,
            v_rest=-65.0,
            v_reset=-70.0,
            v_thresh=-55.0,
            tau_refrac=2.0,
            tau_syn_E=5.0,
            tau_syn_I=5.0,
            cm=0.25,
        )
        pop = sim.Population(int(args.population_size), cell, label=f"tier4_22b_{task_name}_seed{seed}")
        pop.record("spikes")
        source = sim.StepCurrentSource(times=times, amplitudes=amplitudes)
        pop.inject(source)
        try:
            sim.run(float(task.steps) * dt_ms)
            sim_run_calls += 1
        except Exception:
            sim_run_failures += 1
            raise
        try:
            data = pop.get_data("spikes", clear=False)
            spike_bins = bin_spiketrains(data.segments[0].spiketrains, steps=task.steps, dt_ms=dt_ms)
        except Exception:
            readback_failures += 1
            raise
    finally:
        try:
            sim.end()
        except Exception:
            pass

    for step in range(task.steps):
        rows.append(
            {
                "tier": TIER,
                "runner_revision": RUNNER_REVISION,
                "task": task.name,
                "tier_part": TASK_PARTS.get(task.name, "4.22b"),
                "seed": int(seed),
                "step": int(step),
                "backend": backend,
                "backend_path": backend_path,
                "runtime_mode": "continuous_transport",
                "learning_enabled": False,
                "transport_only": True,
                "dt_ms": dt_ms,
                "sensory_return_1m": float(task.sensory[step]),
                "target_return_1m": float(task.current_target[step]),
                "target_signal_horizon": float(task.evaluation_target[step]),
                "target_signal_nonzero": bool(task.evaluation_mask[step]),
                "feedback_due_step": int(task.feedback_due_step[step]),
                "scheduled_current_na": float(currents[step]),
                "step_spike_count": int(spike_bins[step]),
            }
        )

    total_spikes = int(spike_bins.sum())
    summary = {
        "status": "pass",
        "task": task.name,
        "tier_part": TASK_PARTS.get(task.name, "4.22b"),
        "seed": int(seed),
        "backend": backend,
        "backend_path": backend_path,
        "runtime_mode": "continuous_transport",
        "learning_enabled": False,
        "transport_only": True,
        "steps": int(task.steps),
        "population_size": int(args.population_size),
        "dt_seconds": float(args.dt_seconds),
        "timestep_ms": float(args.timestep_ms),
        "sim_run_calls": int(sim_run_calls),
        "sim_run_failures": int(sim_run_failures),
        "readback_failures": int(readback_failures),
        "summary_read_failures": int(readback_failures),
        "synthetic_fallbacks": int(synthetic_fallbacks),
        "scheduled_input_failures": int(scheduled_input_failures),
        "scheduled_input_mode": "StepCurrentSource",
        "scheduled_current_changes": int(len(times)),
        "scheduled_current_min": float(np.min(currents)) if len(currents) else 0.0,
        "scheduled_current_max": float(np.max(currents)) if len(currents) else 0.0,
        "total_step_spikes": total_spikes,
        "nonzero_spike_bins": int(np.count_nonzero(spike_bins)),
        "max_step_spikes": int(np.max(spike_bins)) if len(spike_bins) else 0,
        "mean_step_spikes": float(np.mean(spike_bins)) if len(spike_bins) else 0.0,
        "runtime_seconds": time.perf_counter() - started,
        "spinnman_numpy2_compat": compat_status,
        "claim_boundary": "Continuous transport scaffold only; learning/reward/plasticity disabled for this tier.",
    }
    return rows, summary


def aggregate_summaries(summaries: list[dict[str, Any]], args: argparse.Namespace) -> dict[str, Any]:
    total_cases = len(summaries)
    return {
        "runner_revision": RUNNER_REVISION,
        "mode": args.mode,
        "claim_boundary": "Continuous transport scaffold only; not learning, custom-C, native/on-chip plasticity, or speedup evidence.",
        "case_count": total_cases,
        "tasks": args.tasks,
        "seeds": args.seeds,
        "backend_keys": sorted({str(s.get("backend")) for s in summaries}),
        "all_cases_passed": bool(summaries) and all(str(s.get("status")) == "pass" for s in summaries),
        "sim_run_calls_sum": int(sum(int(s.get("sim_run_calls") or 0) for s in summaries)),
        "sim_run_calls_max": int(max([int(s.get("sim_run_calls") or 0) for s in summaries] or [0])),
        "sim_run_failures_sum": int(sum(int(s.get("sim_run_failures") or 0) for s in summaries)),
        "readback_failures_sum": int(sum(int(s.get("readback_failures") or 0) for s in summaries)),
        "summary_read_failures_sum": int(sum(int(s.get("summary_read_failures") or 0) for s in summaries)),
        "synthetic_fallbacks_sum": int(sum(int(s.get("synthetic_fallbacks") or 0) for s in summaries)),
        "scheduled_input_failures_sum": int(sum(int(s.get("scheduled_input_failures") or 0) for s in summaries)),
        "total_step_spikes_sum": int(sum(int(s.get("total_step_spikes") or 0) for s in summaries)),
        "total_step_spikes_min": int(min([int(s.get("total_step_spikes") or 0) for s in summaries] or [0])),
        "nonzero_spike_bins_sum": int(sum(int(s.get("nonzero_spike_bins") or 0) for s in summaries)),
        "runtime_seconds_sum": float(sum(float(s.get("runtime_seconds") or 0.0) for s in summaries)),
        "expected_sim_run_calls": total_cases,
        "next_step_if_passed": "Tier 4.22c persistent local state scaffold, then Tier 4.22d reward/plasticity learning path.",
    }


def criteria_for(summary: dict[str, Any], args: argparse.Namespace, prerequisite_status: str) -> list[dict[str, Any]]:
    prereq_ok = prerequisite_status == "pass" or prerequisite_status == "missing"
    return [
        criterion("runner revision current", RUNNER_REVISION, "expected current source", True),
        criterion("Tier 4.22a0 preflight pass exists or bundle is fresh", prerequisite_status, "== pass locally OR missing in fresh source bundle", prereq_ok, "Fresh EBRAINS/source-smoke bundles do not need local controlled_test_output uploaded."),
        criterion("mode has explicit claim boundary", args.mode, "prepare|local|run-hardware|ingest", args.mode in {"prepare", "local", "run-hardware", "ingest"}),
        criterion("case count matches tasks x seeds", summary.get("case_count"), f"== {len(args.tasks) * len(args.seeds)}", int(summary.get("case_count") or 0) == len(args.tasks) * len(args.seeds)),
        criterion("all cases passed", summary.get("all_cases_passed"), "True", bool(summary.get("all_cases_passed"))),
        criterion("exactly one sim.run per case", {"calls": summary.get("sim_run_calls_sum"), "expected": summary.get("expected_sim_run_calls")}, "sum == case_count and max == 1", int(summary.get("sim_run_calls_sum") or 0) == int(summary.get("expected_sim_run_calls") or -1) and int(summary.get("sim_run_calls_max") or 0) == 1),
        criterion("sim.run failures zero", summary.get("sim_run_failures_sum"), "== 0", int(summary.get("sim_run_failures_sum") or 0) == 0),
        criterion("readback failures zero", summary.get("readback_failures_sum"), "== 0", int(summary.get("readback_failures_sum") or 0) == 0),
        criterion("synthetic fallback zero", summary.get("synthetic_fallbacks_sum"), "== 0", int(summary.get("synthetic_fallbacks_sum") or 0) == 0),
        criterion("scheduled input failures zero", summary.get("scheduled_input_failures_sum"), "== 0", int(summary.get("scheduled_input_failures_sum") or 0) == 0),
        criterion("nonzero spike readback", summary.get("total_step_spikes_min"), "> 0 per case", int(summary.get("total_step_spikes_min") or 0) > 0),
        criterion("transport-only learning disabled", "disabled", "required for 4.22b isolation", True),
    ]


def prepare(args: argparse.Namespace, output_dir: Path) -> int:
    prerequisite_status, prerequisite_manifest = latest_status(TIER4_22A0_LATEST)
    command = (
        "cra_422b/experiments/tier4_22b_continuous_transport_scaffold.py "
        "--mode run-hardware --tasks {tasks} --seeds {seeds} --steps {steps} "
        "--population-size {pop} --output-dir tier4_22b_job_output"
    ).format(
        tasks=",".join(args.tasks),
        seeds=",".join(str(seed) for seed in args.seeds),
        steps=args.steps,
        pop=args.population_size,
    )
    plan = make_runtime_plan(
        runtime_mode="continuous",
        learning_location="on_chip",
        chunk_size_steps=int(args.steps),
        total_steps=int(args.steps),
        dt_seconds=float(args.dt_seconds),
    )
    summary = {
        "mode": "prepare",
        "runner_revision": RUNNER_REVISION,
        "tier4_22a0_status": prerequisite_status,
        "tier4_22a0_manifest": prerequisite_manifest,
        "tasks": args.tasks,
        "seeds": args.seeds,
        "steps": int(args.steps),
        "population_size": int(args.population_size),
        "runtime_mode": "continuous_transport",
        "learning_enabled": False,
        "sim_run_calls_target_per_case": 1,
        "future_runtime_plan_stage": plan.implementation_stage,
        "jobmanager_command": command,
        "upload_contract": [
            "Upload source folders only under cra_422b/: experiments/ and coral_reef_spinnaker/.",
            "Do not upload controlled_test_output/; it is local evidence storage.",
            "Run the JobManager command directly, not via bash wrapper unless EBRAINS requires it.",
        ],
    }
    criteria = [
        criterion("prepare mode explicit", "prepare", "== prepare", True),
        criterion("Tier 4.22a0 local preflight pass exists", prerequisite_status, "== pass", prerequisite_status == "pass"),
        criterion("continuous transport command emitted", command, "contains --mode run-hardware", "--mode run-hardware" in command),
        criterion("learning disabled by design", False, "False for 4.22b", True),
    ]
    status = "prepared" if all(item["passed"] for item in criteria) else "blocked"
    result = {
        "tier": TIER,
        "generated_at_utc": utc_now(),
        "status": status,
        "failure_reason": "" if status == "prepared" else "Failed criteria: " + ", ".join(item["name"] for item in criteria if not item["passed"]),
        "output_dir": str(output_dir),
        "summary": summary,
        "criteria": criteria,
        "artifacts": {},
    }
    manifest = output_dir / "tier4_22b_results.json"
    report = output_dir / "tier4_22b_report.md"
    result["artifacts"] = {"manifest_json": str(manifest), "report_md": str(report)}
    write_json_safe(manifest, result)
    write_report(report, result)
    write_latest(output_dir, manifest, report, status)
    print(json.dumps({"status": status, "output_dir": str(output_dir), "command": command}, indent=2))
    return 0 if status == "prepared" else 1


def run_cases(args: argparse.Namespace, output_dir: Path) -> int:
    prerequisite_status, prerequisite_manifest = latest_status(TIER4_22A0_LATEST)
    rows_all: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    artifacts: dict[str, str] = {}
    failure_reason = ""
    for task_name in args.tasks:
        for seed in args.seeds:
            try:
                rows, summary = run_transport_case(task_name=task_name, seed=seed, args=args)
            except Exception as exc:
                failure_reason = f"{task_name} seed {seed} raised {type(exc).__name__}: {exc}"
                trace_path = output_dir / f"{case_label(task_name, seed)}_failure.txt"
                trace_path.write_text(failure_reason, encoding="utf-8")
                artifacts[f"{case_label(task_name, seed)}_failure"] = str(trace_path)
                if args.stop_on_fail:
                    break
                continue
            rows_all.extend(rows)
            summaries.append(summary)
            csv_path = output_dir / f"tier4_22b_{case_label(task_name, seed)}_timeseries.csv"
            write_csv_rows(csv_path, rows)
            artifacts[f"{case_label(task_name, seed)}_timeseries_csv"] = str(csv_path)
        if failure_reason and args.stop_on_fail:
            break

    aggregate = aggregate_summaries(summaries, args)
    aggregate["tier4_22a0_status"] = prerequisite_status
    aggregate["tier4_22a0_manifest"] = prerequisite_manifest
    criteria = criteria_for(aggregate, args, prerequisite_status)
    status = "pass" if all(item["passed"] for item in criteria) else "fail"
    if status != "pass" and not failure_reason:
        failure_reason = "Failed criteria: " + ", ".join(item["name"] for item in criteria if not item["passed"])
    summary_csv = output_dir / "tier4_22b_summary.csv"
    timeseries_csv = output_dir / "tier4_22b_timeseries.csv"
    write_csv_rows(summary_csv, summaries)
    write_csv_rows(timeseries_csv, rows_all)
    manifest = output_dir / "tier4_22b_results.json"
    report = output_dir / "tier4_22b_report.md"
    artifacts.update({"summary_csv": str(summary_csv), "timeseries_csv": str(timeseries_csv), "manifest_json": str(manifest), "report_md": str(report)})
    result = {
        "tier": TIER,
        "generated_at_utc": utc_now(),
        "mode": args.mode,
        "status": status,
        "failure_reason": failure_reason,
        "output_dir": str(output_dir),
        "summary": aggregate,
        "criteria": criteria,
        "case_summaries": summaries,
        "artifacts": artifacts,
    }
    write_json_safe(manifest, result)
    write_report(report, result)
    write_latest(output_dir, manifest, report, status)
    print(json.dumps({"status": status, "output_dir": str(output_dir), "manifest": str(manifest), "report": str(report)}, indent=2))
    return 0 if status == "pass" else 1


def ingest(args: argparse.Namespace, output_dir: Path) -> int:
    if args.ingest_dir is None:
        raise SystemExit("--ingest-dir is required in ingest mode")
    source = args.ingest_dir.resolve()
    if not source.exists():
        raise SystemExit(f"ingest dir does not exist: {source}")
    output_dir.mkdir(parents=True, exist_ok=True)
    for item in source.iterdir():
        target = output_dir / item.name
        if item.is_dir():
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(item, target)
        else:
            shutil.copy2(item, target)
    manifest = output_dir / "tier4_22b_results.json"
    if not manifest.exists():
        raise SystemExit(f"missing tier4_22b_results.json in ingested files: {source}")
    data = read_json(manifest)
    report = output_dir / "tier4_22b_report.md"
    if not report.exists():
        write_report(report, data)
    write_latest(output_dir, manifest, report, str(data.get("status", "unknown")))
    print(json.dumps({"status": data.get("status"), "output_dir": str(output_dir), "manifest": str(manifest)}, indent=2))
    return 0 if str(data.get("status")).lower() in {"pass", "prepared"} else 1


def write_report(path: Path, result: dict[str, Any]) -> None:
    summary = result.get("summary", {})
    lines = [
        "# Tier 4.22b Continuous Transport Scaffold",
        "",
        f"- Generated: `{result.get('generated_at_utc', utc_now())}`",
        f"- Mode: `{result.get('mode', summary.get('mode', 'prepare'))}`",
        f"- Status: **{str(result.get('status', 'unknown')).upper()}**",
        f"- Output directory: `{result.get('output_dir', path.parent)}`",
        "",
        "Tier 4.22b isolates continuous transport: scheduled input, one continuous `sim.run`, and compact/binned spike readback. Learning is intentionally disabled here so transport failures cannot be confused with reward/plasticity bugs.",
        "",
        "## Claim Boundary",
        "",
        "- This is a transport scaffold, not a learning result.",
        "- It is not native/on-chip learning, custom-C execution, continuous-learning parity, or speedup evidence.",
        "- Learning is added in later gates after timing/readback/state are stable.",
        "",
        "## Summary",
        "",
        f"- Case count: `{markdown_value(summary.get('case_count'))}`",
        f"- Backend(s): `{markdown_value(summary.get('backend_keys'))}`",
        f"- Sim.run calls sum: `{markdown_value(summary.get('sim_run_calls_sum'))}`",
        f"- Expected sim.run calls: `{markdown_value(summary.get('expected_sim_run_calls'))}`",
        f"- Sim.run failures: `{markdown_value(summary.get('sim_run_failures_sum'))}`",
        f"- Readback failures: `{markdown_value(summary.get('readback_failures_sum'))}`",
        f"- Synthetic fallbacks: `{markdown_value(summary.get('synthetic_fallbacks_sum'))}`",
        f"- Minimum spikes per case: `{markdown_value(summary.get('total_step_spikes_min'))}`",
        f"- Total spikes: `{markdown_value(summary.get('total_step_spikes_sum'))}`",
        f"- Runtime seconds sum: `{markdown_value(summary.get('runtime_seconds_sum'))}`",
        "",
        "## Criteria",
        "",
        "| Criterion | Value | Rule | Pass |",
        "| --- | --- | --- | --- |",
    ]
    for item in result.get("criteria", []):
        lines.append(f"| {item['name']} | `{markdown_value(item.get('value'))}` | `{item.get('rule')}` | {'yes' if item.get('passed') else 'no'} |")
    if result.get("case_summaries"):
        lines.extend(["", "## Case Summaries", "", "| Task | Seed | Backend | Calls | Spikes | Runtime s |", "| --- | --- | --- | --- | --- | --- |"])
        for row in result["case_summaries"]:
            lines.append(f"| {row.get('task')} | `{row.get('seed')}` | `{row.get('backend')}` | `{row.get('sim_run_calls')}` | `{row.get('total_step_spikes')}` | `{markdown_value(row.get('runtime_seconds'))}` |")
    lines.extend(["", "## Next Step", "", f"- {summary.get('next_step_if_passed', 'If this passes, proceed to persistent state and then learning/plasticity gates.')}" , ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def write_latest(output_dir: Path, manifest: Path, report: Path, status: str) -> None:
    CONTROLLED.mkdir(parents=True, exist_ok=True)
    write_json_safe(
        CONTROLLED / "tier4_22b_latest_manifest.json",
        {
            "generated_at_utc": utc_now(),
            "tier": TIER,
            "status": status,
            "output_dir": str(output_dir),
            "manifest": str(manifest),
            "report": str(report),
            "canonical": False,
            "claim": "Latest Tier 4.22b continuous transport scaffold; learning disabled, not native/on-chip learning evidence.",
        },
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Tier 4.22b continuous transport scaffold.")
    parser.add_argument("--mode", choices=["prepare", "local", "run-hardware", "ingest"], default="local")
    parser.add_argument("--tasks", type=parse_tasks, default=parse_tasks(DEFAULT_TASKS))
    parser.add_argument("--seeds", type=parse_seeds, default=parse_seeds(DEFAULT_SEEDS))
    parser.add_argument("--steps", type=int, default=DEFAULT_STEPS)
    parser.add_argument("--population-size", type=int, default=DEFAULT_POPULATION_SIZE)
    parser.add_argument("--amplitude", type=float, default=DEFAULT_AMPLITUDE)
    parser.add_argument("--dt-seconds", type=float, default=DEFAULT_DT_SECONDS)
    parser.add_argument("--timestep-ms", type=float, default=1.0)
    parser.add_argument("--base-current-na", type=float, default=DEFAULT_BASE_CURRENT_NA)
    parser.add_argument("--cue-current-gain-na", type=float, default=DEFAULT_CUE_CURRENT_GAIN_NA)
    parser.add_argument("--min-current-na", type=float, default=DEFAULT_MIN_CURRENT_NA)
    parser.add_argument("--delayed-readout-lr", type=float, default=DEFAULT_DELAYED_LR)
    parser.add_argument("--delay", type=int, default=5)
    parser.add_argument("--period", type=int, default=8)
    parser.add_argument("--min-delay", type=int, default=DEFAULT_HARD_MIN_DELAY)
    parser.add_argument("--max-delay", type=int, default=DEFAULT_HARD_MAX_DELAY)
    parser.add_argument("--hard-period", type=int, default=DEFAULT_HARD_PERIOD)
    parser.add_argument("--noise-prob", type=float, default=DEFAULT_HARD_NOISE_PROB)
    parser.add_argument("--sensory-noise-fraction", type=float, default=DEFAULT_HARD_SENSORY_NOISE_FRACTION)
    parser.add_argument("--min-switch-interval", type=int, default=DEFAULT_HARD_MIN_SWITCH_INTERVAL)
    parser.add_argument("--max-switch-interval", type=int, default=DEFAULT_HARD_MAX_SWITCH_INTERVAL)
    parser.add_argument("--spinnaker-hostname", default="")
    parser.add_argument("--stop-on-fail", action="store_true")
    parser.add_argument("--ingest-dir", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.steps <= 0:
        raise SystemExit("--steps must be positive")
    if args.population_size <= 0:
        raise SystemExit("--population-size must be positive")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = "prepared" if args.mode == "prepare" else args.mode.replace("-", "_")
    output_dir = (args.output_dir or CONTROLLED / f"tier4_22b_{stamp}_{suffix}").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if args.mode == "prepare":
        return prepare(args, output_dir)
    if args.mode in {"local", "run-hardware"}:
        return run_cases(args, output_dir)
    if args.mode == "ingest":
        return ingest(args, output_dir)
    raise AssertionError(args.mode)


if __name__ == "__main__":
    raise SystemExit(main())
