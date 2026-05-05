#!/usr/bin/env python3
"""Tier 5.19c - Fading-Memory Narrowing / Compact-Regression Decision.

Tier 5.19b supported a narrowed fading-memory story but did not prove bounded
nonlinear recurrence. This gate asks the honest follow-up question: can the
multi-timescale fading-memory substrate earn promotion without claiming
recurrence?

The runner is software-only. It does not move anything to SpiNNaker. A freeze is
allowed only if the narrowed mechanism clears temporal-memory shams and a full
compact v2.1 regression guardrail.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import subprocess
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
V21_BASELINE = ROOT / "baselines" / "CRA_EVIDENCE_BASELINE_v2.1.json"
TIER = "Tier 5.19c - Fading-Memory Narrowing / Compact-Regression Decision"
RUNNER_REVISION = "tier5_19c_fading_memory_regression_20260505_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier5_19c_20260505_fading_memory_regression"
STANDARD_TASKS = {"mackey_glass", "lorenz", "narma10"}
TEMPORAL_MEMORY_TASKS = {"heldout_long_memory", "slow_context_drift", "multiscale_echo"}
DEFAULT_TASKS = "mackey_glass,lorenz,narma10,heldout_long_memory,slow_context_drift,multiscale_echo,recurrence_pressure"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from tier5_19a_temporal_substrate_reference import (  # noqa: E402
    append_timeseries,
    build_task as build_5_19a_task,
    criterion,
    json_safe,
    summarize,
    utc_now,
    write_csv,
    write_json,
)
from tier5_19b_temporal_substrate_gate import (  # noqa: E402
    recurrence_pressure_task,
    run_task,
)
from tier7_0_standard_dynamical_benchmarks import (  # noqa: E402
    SequenceTask,
    chronological_split,
    parse_csv,
    parse_seeds,
    zscore_from_train,
)


@dataclass
class ChildRun:
    name: str
    purpose: str
    command: list[str]
    output_dir: Path
    manifest_path: Path
    stdout_path: Path
    stderr_path: Path
    return_code: int
    status: str
    failure_reason: str
    runtime_seconds: float

    @property
    def passed(self) -> bool:
        return self.return_code == 0 and self.status == "pass"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "purpose": self.purpose,
            "command": self.command,
            "output_dir": str(self.output_dir),
            "manifest_path": str(self.manifest_path),
            "stdout_path": str(self.stdout_path),
            "stderr_path": str(self.stderr_path),
            "return_code": int(self.return_code),
            "status": self.status,
            "failure_reason": self.failure_reason,
            "runtime_seconds": float(self.runtime_seconds),
        }


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def manifest_status(manifest_path: Path) -> tuple[str, str]:
    if not manifest_path.exists():
        return "fail", f"missing manifest: {manifest_path}"
    try:
        manifest = load_json(manifest_path)
    except Exception as exc:
        return "fail", f"could not parse manifest: {exc}"
    explicit = manifest.get("status")
    if explicit in {"pass", "fail", "prepared", "blocked"}:
        return str(explicit), str(manifest.get("failure_reason") or "")
    result = manifest.get("result")
    if isinstance(result, dict) and result.get("status") in {"pass", "fail", "prepared", "blocked"}:
        return str(result["status"]), str(result.get("failure_reason") or "")
    results = manifest.get("results")
    if isinstance(results, list) and results:
        failed = [item for item in results if item.get("status") != "pass"]
        if failed:
            return "fail", "failed child results: " + ", ".join(str(item.get("name", "unknown")) for item in failed)
        return "pass", ""
    return "fail", "manifest has no explicit status or result list"


def run_child(name: str, purpose: str, command: list[str], output_dir: Path, manifest_name: str) -> ChildRun:
    output_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = output_dir / f"{name}_stdout.log"
    stderr_path = output_dir / f"{name}_stderr.log"
    manifest_path = output_dir / manifest_name
    started = time.perf_counter()
    proc = subprocess.run(
        command,
        cwd=ROOT,
        env={**os.environ, "KMP_DUPLICATE_LIB_OK": "TRUE"},
        text=True,
        capture_output=True,
        check=False,
    )
    runtime_seconds = time.perf_counter() - started
    stdout_path.write_text(proc.stdout, encoding="utf-8")
    stderr_path.write_text(proc.stderr, encoding="utf-8")
    status, manifest_failure = manifest_status(manifest_path)
    failure_reason = manifest_failure
    if proc.returncode != 0:
        failure_reason = failure_reason or f"command exited {proc.returncode}"
    return ChildRun(
        name=name,
        purpose=purpose,
        command=command,
        output_dir=output_dir,
        manifest_path=manifest_path,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        return_code=int(proc.returncode),
        status=status,
        failure_reason=failure_reason,
        runtime_seconds=runtime_seconds,
    )


def slow_context_drift_task(length: int, seed: int, *, horizon: int) -> SequenceTask:
    """Slow latent drift target where a fixed short lag should be incomplete."""
    rng = np.random.default_rng(seed + 51931)
    warmup = 300
    total = length + horizon + warmup + 8
    impulses = rng.normal(0.0, 0.65, size=total)
    carrier = np.sin(np.linspace(0.0, 9.0 * math.pi, total))
    drive = np.tanh(0.70 * impulses + 0.25 * np.roll(impulses, 5) + 0.20 * carrier)
    slow = np.zeros(total, dtype=float)
    very_slow = np.zeros(total, dtype=float)
    for t in range(1, total):
        slow[t] = 0.975 * slow[t - 1] + 0.025 * np.tanh(drive[t] + 0.25 * drive[t - 3])
        very_slow[t] = 0.994 * very_slow[t - 1] + 0.006 * np.tanh(slow[t] + 0.4 * drive[t])
    observed_raw = drive[warmup : warmup + length]
    target_raw = (0.55 * slow + 0.45 * very_slow)[warmup + horizon : warmup + horizon + length]
    train_end = chronological_split(length, 0.65)
    observed, obs_mu, obs_sd = zscore_from_train(observed_raw, train_end)
    target, tgt_mu, tgt_sd = zscore_from_train(target_raw, train_end)
    return SequenceTask(
        name="slow_context_drift",
        display_name="Held-out slow context drift diagnostic",
        observed=observed,
        target=target,
        train_end=train_end,
        horizon=horizon,
        metadata={
            "obs_mu": obs_mu,
            "obs_sd": obs_sd,
            "target_mu": tgt_mu,
            "target_sd": tgt_sd,
            "hidden_timescales": "slow decay 0.975 and very_slow decay 0.994",
            "purpose": "test narrowed fading-memory value without a recurrence claim",
        },
    )


def multiscale_echo_task(length: int, seed: int, *, horizon: int) -> SequenceTask:
    """Noisy latent-state diagnostic for adaptive fading memory.

    The observed stream is a noisy readout of a drifting latent variable. A
    frozen state should not track the held-out segment, and a short lag window
    should be less effective than multi-timescale denoising traces.
    """
    rng = np.random.default_rng(seed + 51932)
    warmup = 300
    total = length + horizon + warmup + 8
    latent = np.zeros(total, dtype=float)
    mid = np.zeros(total, dtype=float)
    slow = np.zeros(total, dtype=float)
    burst = np.zeros(total, dtype=float)
    for t in range(1, total):
        innovation = rng.normal(0.0, 0.075)
        if t % 83 == 0:
            innovation += rng.choice([-0.55, 0.55])
        latent[t] = np.tanh(0.992 * latent[t - 1] + innovation)
        mid[t] = 0.965 * mid[t - 1] + 0.035 * latent[t]
        slow[t] = 0.992 * slow[t - 1] + 0.008 * mid[t]
        burst[t] = 0.80 * burst[t - 1] + 0.20 * rng.normal(0.0, 1.0)
    observed_raw = np.tanh(latent + 0.85 * rng.normal(0.0, 1.0, size=total) + 0.15 * burst)[warmup : warmup + length]
    target_raw = (0.55 * mid + 0.45 * slow)[warmup + horizon : warmup + horizon + length]
    train_end = chronological_split(length, 0.65)
    observed, obs_mu, obs_sd = zscore_from_train(observed_raw, train_end)
    target, tgt_mu, tgt_sd = zscore_from_train(target_raw, train_end)
    return SequenceTask(
        name="multiscale_echo",
        display_name="Held-out multi-timescale echo diagnostic",
        observed=observed,
        target=target,
        train_end=train_end,
        horizon=horizon,
        metadata={
            "obs_mu": obs_mu,
            "obs_sd": obs_sd,
            "target_mu": tgt_mu,
            "target_sd": tgt_sd,
            "hidden_timescales": "latent 0.992, mid 0.965, slow 0.992",
            "purpose": "test whether adaptive fading traces denoise and track a latent slow state",
        },
    )


def build_task(name: str, length: int, seed: int, horizon: int) -> SequenceTask:
    if name == "slow_context_drift":
        return slow_context_drift_task(length, seed, horizon=horizon)
    if name == "multiscale_echo":
        return multiscale_echo_task(length, seed, horizon=horizon)
    if name == "recurrence_pressure":
        return recurrence_pressure_task(length, seed, horizon=horizon)
    return build_5_19a_task(name, length, seed, horizon)


def metric(summary_rows: list[dict[str, Any]], task: str, model: str, key: str = "mse_mean") -> float:
    row = next((r for r in summary_rows if r["task"] == task and r["model"] == model), None)
    if not row or row.get(key) is None:
        return math.inf
    return float(row[key])


def ratio(control: float, candidate: float) -> float | None:
    if not math.isfinite(control) or not math.isfinite(candidate) or candidate <= 0.0:
        return None
    return control / candidate


def geometric(values: list[float]) -> float:
    safe = [max(1e-12, float(v)) for v in values if math.isfinite(float(v))]
    if not safe:
        return math.inf
    return float(math.exp(sum(math.log(v) for v in safe) / len(safe)))


def classify(
    summary_rows: list[dict[str, Any]],
    tasks: list[str],
    compact_child: ChildRun | None,
    compact_mode: str,
    compact_backend: str,
) -> dict[str, Any]:
    candidate = "fading_memory_only_ablation"
    full_reference = "temporal_full_candidate"
    lag = "lag_only_online_lms_control"
    raw = "raw_cra_v2_1_online"
    frozen = "frozen_temporal_state_ablation"
    shuffled = "shuffled_temporal_state_sham"
    shuffled_target = "temporal_shuffled_target_control"
    no_plasticity = "temporal_no_plasticity_ablation"
    temporal_tasks = [task for task in tasks if task in TEMPORAL_MEMORY_TASKS]
    standard_tasks = [task for task in tasks if task in STANDARD_TASKS]
    temporal_metrics: dict[str, dict[str, float | None]] = {}
    for task in temporal_tasks:
        cand = metric(summary_rows, task, candidate)
        temporal_metrics[task] = {
            "candidate_mse": cand,
            "lag_mse": metric(summary_rows, task, lag),
            "raw_v2_1_mse": metric(summary_rows, task, raw),
            "full_reference_mse": metric(summary_rows, task, full_reference),
            "frozen_mse": metric(summary_rows, task, frozen),
            "shuffled_state_mse": metric(summary_rows, task, shuffled),
            "shuffled_target_mse": metric(summary_rows, task, shuffled_target),
            "no_plasticity_mse": metric(summary_rows, task, no_plasticity),
            "margin_vs_lag": ratio(metric(summary_rows, task, lag), cand),
            "margin_vs_raw_v2_1": ratio(metric(summary_rows, task, raw), cand),
            "margin_vs_frozen": ratio(metric(summary_rows, task, frozen), cand),
            "margin_vs_shuffled_state": ratio(metric(summary_rows, task, shuffled), cand),
            "margin_vs_shuffled_target": ratio(metric(summary_rows, task, shuffled_target), cand),
            "margin_vs_no_plasticity": ratio(metric(summary_rows, task, no_plasticity), cand),
        }
    standard_candidate = geometric([metric(summary_rows, task, candidate) for task in standard_tasks])
    standard_raw = geometric([metric(summary_rows, task, raw) for task in standard_tasks])
    standard_lag = geometric([metric(summary_rows, task, lag) for task in standard_tasks])
    temporal_candidate = geometric([metric(summary_rows, task, candidate) for task in temporal_tasks])
    temporal_lag = geometric([metric(summary_rows, task, lag) for task in temporal_tasks])
    temporal_raw = geometric([metric(summary_rows, task, raw) for task in temporal_tasks])
    temporal_frozen = geometric([metric(summary_rows, task, frozen) for task in temporal_tasks])
    temporal_shuffled = geometric([metric(summary_rows, task, shuffled) for task in temporal_tasks])
    temporal_shuffled_target = geometric([metric(summary_rows, task, shuffled_target) for task in temporal_tasks])
    temporal_no_plasticity = geometric([metric(summary_rows, task, no_plasticity) for task in temporal_tasks])
    temporal_lag_margin = ratio(temporal_lag, temporal_candidate)
    temporal_raw_margin = ratio(temporal_raw, temporal_candidate)
    task_lag_wins = sum(
        1
        for values in temporal_metrics.values()
        if values["margin_vs_lag"] is not None and float(values["margin_vs_lag"]) >= 1.10
    )
    task_sham_wins = {
        "frozen": ratio(temporal_frozen, temporal_candidate),
        "shuffled_state": ratio(temporal_shuffled, temporal_candidate),
        "shuffled_target": ratio(temporal_shuffled_target, temporal_candidate),
        "no_plasticity": ratio(temporal_no_plasticity, temporal_candidate),
    }
    temporal_pass = (
        len(temporal_tasks) >= 3
        and temporal_lag_margin is not None
        and temporal_lag_margin >= 1.25
        and task_lag_wins >= 2
        and temporal_raw_margin is not None
        and temporal_raw_margin >= 2.0
        and all(value is not None and value >= 1.25 for value in task_sham_wins.values())
    )
    standard_regression_pass = (
        not standard_tasks
        or (
            math.isfinite(standard_candidate)
            and math.isfinite(standard_raw)
            and standard_candidate <= max(standard_raw * 1.05, standard_raw + 1e-9)
        )
    )
    compact_pass = compact_child is not None and compact_child.passed
    compact_full = compact_mode == "full"
    compact_freeze_backend = compact_backend in {"nest", "brian2"}
    if temporal_pass and standard_regression_pass and compact_pass and compact_full and compact_freeze_backend:
        outcome = "fading_memory_ready_for_v2_2_freeze"
        recommendation = "Freeze a bounded v2.2 software baseline for multi-timescale fading-memory temporal state; do not claim nonlinear recurrence."
        freeze_authorized = True
    elif temporal_pass and standard_regression_pass and compact_pass:
        outcome = "fading_memory_supported_pending_full_compact"
        recommendation = "Mechanism criteria pass with smoke compact guardrail; run full compact regression before any baseline freeze."
        freeze_authorized = False
    elif temporal_pass and standard_regression_pass:
        outcome = "fading_memory_supported_compact_missing"
        recommendation = "Mechanism criteria pass, but compact regression was skipped or failed; no freeze."
        freeze_authorized = False
    else:
        outcome = "fading_memory_not_promotable"
        recommendation = "Do not freeze; keep Tier 5.19 as diagnostic or repair the temporal mechanism/task family."
        freeze_authorized = False
    return {
        "outcome": outcome,
        "recommendation": recommendation,
        "freeze_authorized": bool(freeze_authorized),
        "compact_mode": compact_mode,
        "compact_backend": compact_backend,
        "compact_pass": bool(compact_pass),
        "compact_full": bool(compact_full),
        "compact_freeze_backend": bool(compact_freeze_backend),
        "temporal_pass": bool(temporal_pass),
        "standard_regression_pass": bool(standard_regression_pass),
        "temporal_tasks": temporal_tasks,
        "standard_tasks": standard_tasks,
        "task_lag_wins": int(task_lag_wins),
        "temporal_metrics": temporal_metrics,
        "geomean": {
            "temporal_candidate_mse": temporal_candidate,
            "temporal_lag_mse": temporal_lag,
            "temporal_raw_v2_1_mse": temporal_raw,
            "temporal_frozen_mse": temporal_frozen,
            "temporal_shuffled_state_mse": temporal_shuffled,
            "temporal_shuffled_target_mse": temporal_shuffled_target,
            "temporal_no_plasticity_mse": temporal_no_plasticity,
            "temporal_margin_vs_lag": temporal_lag_margin,
            "temporal_margin_vs_raw_v2_1": temporal_raw_margin,
            "temporal_margins_vs_destructive_shams": task_sham_wins,
            "standard_candidate_mse": standard_candidate,
            "standard_raw_v2_1_mse": standard_raw,
            "standard_lag_mse": standard_lag,
            "standard_margin_vs_raw_v2_1": ratio(standard_raw, standard_candidate),
            "standard_margin_vs_lag": ratio(standard_lag, standard_candidate),
        },
        "claim": (
            "bounded multi-timescale fading-memory temporal state"
            if freeze_authorized
            else "no promoted claim from this tier yet"
        ),
        "nonclaims": [
            "not bounded nonlinear recurrence",
            "not hardware evidence",
            "not native on-chip temporal dynamics",
            "not universal benchmark superiority",
            "not language, planning, AGI, or ASI",
        ],
    }


def run_temporal_gate(args: argparse.Namespace, output_dir: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    tasks = parse_csv(args.tasks)
    seeds = parse_seeds(args)
    all_rows: list[dict[str, Any]] = []
    all_timeseries: list[dict[str, Any]] = []
    task_descriptors: list[dict[str, Any]] = []
    task_diagnostics: list[dict[str, Any]] = []
    for seed in seeds:
        for task_name in tasks:
            task = build_task(task_name, args.length, seed, args.horizon)
            rows, timeseries, diagnostics = run_task(task, seed=seed, args=args)
            all_rows.extend(rows)
            all_timeseries.extend(timeseries)
            task_diagnostics.append(diagnostics)
            descriptor = {
                "task": task.name,
                "display_name": task.display_name,
                "seed": int(seed),
                "length": int(len(task.target)),
                "train_end": int(task.train_end),
                "horizon": int(task.horizon),
                "metadata": task.metadata,
            }
            task_descriptors.append(descriptor)
            write_json(output_dir / f"{task.name}_seed{seed}_task.json", descriptor)
    models = sorted({row["model"] for row in all_rows})
    summary_rows, aggregate_rows, aggregate_summary = summarize(all_rows, tasks, models, seeds)
    write_csv(
        output_dir / "tier5_19c_summary.csv",
        summary_rows,
        ["task", "model", "status", "seed_count", "mse_mean", "mse_median", "mse_std", "mse_worst", "nmse_mean", "tail_mse_mean", "test_corr_mean"],
    )
    write_csv(
        output_dir / "tier5_19c_aggregate.csv",
        aggregate_rows,
        ["task", "model", "seed", "status", "geomean_mse", "geomean_nmse"],
    )
    write_csv(
        output_dir / "tier5_19c_timeseries.csv",
        all_timeseries,
        ["task", "seed", "model", "step", "split", "observed", "target", "prediction", "squared_error"],
    )
    write_json(output_dir / "tier5_19c_task_diagnostics.json", {"tasks": task_descriptors, "diagnostics": task_diagnostics})
    return summary_rows, aggregate_rows, aggregate_summary, all_rows


def run_compact_guardrail(args: argparse.Namespace, output_dir: Path) -> ChildRun | None:
    if args.compact_mode == "skip":
        return None
    compact_dir = output_dir / f"v2_1_compact_regression_{args.compact_mode}"
    command = [
        sys.executable or "python3",
        "experiments/tier5_self_evaluation_compact_regression.py",
        "--backend",
        args.compact_backend,
        "--stop-on-fail",
        "--output-dir",
        str(compact_dir),
    ]
    if args.compact_mode == "smoke":
        command.insert(2, "--smoke")
    return run_child(
        name=f"v2_1_compact_regression_{args.compact_mode}",
        purpose="rerun the current v2.1 promotion/regression guardrail before any temporal-substrate freeze",
        command=command,
        output_dir=compact_dir,
        manifest_name="tier5_18c_results.json",
    )


def write_report(output_dir: Path, payload: dict[str, Any]) -> None:
    c = payload["classification"]
    g = c["geomean"]
    lines = [
        "# Tier 5.19c Fading-Memory Narrowing / Compact-Regression Decision",
        "",
        f"- Generated: `{payload['generated_at_utc']}`",
        f"- Status: **{payload['status'].upper()}**",
        f"- Criteria: `{payload['criteria_passed']}/{payload['criteria_total']}`",
        f"- Outcome: `{c['outcome']}`",
        f"- Freeze authorized: `{c['freeze_authorized']}`",
        "",
        "## Claim Boundary",
        "",
        payload["claim_boundary"],
        "",
        "## Interpretation",
        "",
        f"- Temporal-memory geomean candidate MSE: `{g['temporal_candidate_mse']}`",
        f"- Temporal-memory geomean lag-only MSE: `{g['temporal_lag_mse']}`",
        f"- Temporal-memory margin vs lag-only: `{g['temporal_margin_vs_lag']}`",
        f"- Temporal-memory margin vs raw v2.1: `{g['temporal_margin_vs_raw_v2_1']}`",
        f"- Standard-task geomean candidate MSE: `{g['standard_candidate_mse']}`",
        f"- Standard-task geomean lag-only MSE: `{g['standard_lag_mse']}`",
        f"- Recommendation: {c['recommendation']}",
        "",
        "## Per-Task Temporal Metrics",
        "",
        "| Task | Candidate MSE | Lag MSE | Margin vs lag | Raw v2.1 MSE | Margin vs raw |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for task, values in c["temporal_metrics"].items():
        lines.append(
            f"| {task} | {values['candidate_mse']} | {values['lag_mse']} | {values['margin_vs_lag']} | {values['raw_v2_1_mse']} | {values['margin_vs_raw_v2_1']} |"
        )
    lines.extend(
        [
            "",
            "## Compact Guardrail",
            "",
            f"- compact_mode: `{c['compact_mode']}`",
            f"- compact_backend: `{c['compact_backend']}`",
            f"- compact_pass: `{c['compact_pass']}`",
            f"- compact_full: `{c['compact_full']}`",
            f"- compact_freeze_backend: `{c['compact_freeze_backend']}`",
            "",
            "## Nonclaims",
            "",
        ]
    )
    for item in c["nonclaims"]:
        lines.append(f"- {item}")
    lines.append("")
    (output_dir / "tier5_19c_report.md").write_text("\n".join(lines), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=TIER)
    parser.add_argument("--tasks", default=DEFAULT_TASKS)
    parser.add_argument("--seeds", default="42,43,44")
    parser.add_argument("--seed-count", type=int, default=None)
    parser.add_argument("--base-seed", type=int, default=42)
    parser.add_argument("--length", type=int, default=720)
    parser.add_argument("--horizon", type=int, default=8)
    parser.add_argument("--history", type=int, default=12)
    parser.add_argument("--backend", default="mock", choices=["mock", "nest", "brian2"])
    parser.add_argument("--compact-backend", default="nest", choices=["mock", "nest", "brian2"])
    parser.add_argument("--cra-population-size", type=int, default=8)
    parser.add_argument("--cra-readout-lr", type=float, default=0.20)
    parser.add_argument("--cra-delayed-lr", type=float, default=0.20)
    parser.add_argument("--readout-lr", type=float, default=0.08)
    parser.add_argument("--readout-decay", type=float, default=1e-5)
    parser.add_argument("--weight-clip", type=float, default=20.0)
    parser.add_argument("--output-clip", type=float, default=3.0)
    parser.add_argument("--ridge", type=float, default=1e-3)
    parser.add_argument("--temporal-timescales", default="2,4,8,16,32,64,128")
    parser.add_argument("--temporal-hidden-units", type=int, default=16)
    parser.add_argument("--temporal-recurrent-scale", type=float, default=0.65)
    parser.add_argument("--temporal-input-scale", type=float, default=0.45)
    parser.add_argument("--temporal-hidden-decay", type=float, default=0.72)
    parser.add_argument("--state-reset-interval", type=int, default=24)
    parser.add_argument("--reservoir-units", type=int, default=32)
    parser.add_argument("--reservoir-spectral-radius", type=float, default=0.9)
    parser.add_argument("--reservoir-input-scale", type=float, default=0.5)
    parser.add_argument("--esn-units", type=int, default=64)
    parser.add_argument("--esn-spectral-radius", type=float, default=0.9)
    parser.add_argument("--esn-input-scale", type=float, default=0.5)
    parser.add_argument("--compact-mode", choices=["skip", "smoke", "full"], default="smoke")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    tasks = parse_csv(args.tasks)
    seeds = parse_seeds(args)
    summary_rows, aggregate_rows, aggregate_summary, run_rows = run_temporal_gate(args, output_dir)
    compact_child = run_compact_guardrail(args, output_dir)
    classification = classify(summary_rows, tasks, compact_child, args.compact_mode, args.compact_backend)
    criteria = [
        criterion("runner revision current", RUNNER_REVISION, "expected current source", RUNNER_REVISION.endswith("_0001")),
        criterion("v2.1 baseline artifact exists", str(V21_BASELINE), "exists", V21_BASELINE.exists()),
        criterion("all required temporal-memory tasks included", sorted(TEMPORAL_MEMORY_TASKS), "subset of tasks", TEMPORAL_MEMORY_TASKS.issubset(set(tasks))),
        criterion("all standard benchmark guardrails included", sorted(STANDARD_TASKS), "subset of tasks", STANDARD_TASKS.issubset(set(tasks))),
        criterion("all model rows completed", f"{sum(r['status'] == 'pass' for r in run_rows)}/{len(run_rows)}", "all pass", all(r["status"] == "pass" for r in run_rows)),
        criterion("fading-memory temporal criteria pass", classification["temporal_pass"], "== true", bool(classification["temporal_pass"])),
        criterion("standard/raw guardrail does not regress", classification["standard_regression_pass"], "== true", bool(classification["standard_regression_pass"])),
        criterion("compact regression guardrail pass", classification["compact_pass"], "== true unless compact-mode skip", args.compact_mode == "skip" or bool(classification["compact_pass"])),
        criterion("full compact regression for freeze", classification["compact_full"], "== true for freeze authorization", not classification["freeze_authorized"] or bool(classification["compact_full"])),
        criterion("freeze compact backend is non-mock", classification["compact_freeze_backend"], "nest or brian2 required for freeze", not classification["freeze_authorized"] or bool(classification["compact_freeze_backend"])),
        criterion("no recurrence claim", "bounded nonlinear recurrence not claimed", "explicit nonclaim", "not bounded nonlinear recurrence" in classification["nonclaims"]),
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
        "tasks": tasks,
        "seeds": seeds,
        "length": int(args.length),
        "horizon": int(args.horizon),
        "history": int(args.history),
        "backend": args.backend,
        "compact_backend": args.compact_backend,
        "runtime_seconds": time.perf_counter() - started,
        "criteria": criteria,
        "criteria_passed": sum(bool(item["passed"]) for item in criteria),
        "criteria_total": len(criteria),
        "classification": classification,
        "summary": classification,
        "summary_rows": summary_rows,
        "aggregate_rows": aggregate_rows,
        "aggregate_summary": aggregate_summary,
        "compact_child": compact_child.to_dict() if compact_child else None,
        "artifacts": {
            "results_json": str(output_dir / "tier5_19c_results.json"),
            "summary_csv": str(output_dir / "tier5_19c_summary.csv"),
            "aggregate_csv": str(output_dir / "tier5_19c_aggregate.csv"),
            "timeseries_csv": str(output_dir / "tier5_19c_timeseries.csv"),
            "report_md": str(output_dir / "tier5_19c_report.md"),
            "task_diagnostics_json": str(output_dir / "tier5_19c_task_diagnostics.json"),
        },
        "fairness_contract": {
            "tier": TIER,
            "candidate": "fading_memory_only_ablation treated as narrowed mechanism",
            "full_temporal_candidate": "non-promoted reference only",
            "split": "chronological",
            "normalization": "train-prefix z-score for tasks; online readout updates predict before target update",
            "controls": [
                "current v2.1 raw CRA",
                "lag-only causal readout",
                "fixed ESN",
                "random reservoir",
                "full temporal candidate as non-promoted reference",
                "frozen temporal state",
                "shuffled temporal state",
                "shuffled target",
                "no plasticity",
                "compact v2.1 guardrail",
            ],
            "nonclaims": classification["nonclaims"],
        },
        "claim_boundary": (
            "Tier 5.19c is software-only fading-memory promotion/regression "
            "evidence. A pass can authorize a bounded fading-memory baseline "
            "only with full compact regression. It does not prove bounded "
            "nonlinear recurrence, hardware transfer, native on-chip temporal "
            "dynamics, universal benchmark superiority, language, planning, "
            "AGI, or ASI."
        ),
    }
    write_json(output_dir / "tier5_19c_results.json", payload)
    write_json(output_dir / "tier5_19c_fairness_contract.json", payload["fairness_contract"])
    write_report(output_dir, payload)
    write_json(
        CONTROLLED / "tier5_19c_latest_manifest.json",
        {
            "tier": TIER,
            "runner_revision": RUNNER_REVISION,
            "generated_at_utc": payload["generated_at_utc"],
            "status": payload["status"],
            "classification": payload["classification"]["outcome"],
            "manifest": str(output_dir / "tier5_19c_results.json"),
            "output_dir": str(output_dir),
        },
    )
    return payload


def main() -> None:
    args = build_parser().parse_args()
    result = run(args)
    print(
        json.dumps(
            {
                "tier": TIER,
                "status": result["status"],
                "criteria": f"{result['criteria_passed']}/{result['criteria_total']}",
                "classification": result["classification"]["outcome"],
                "freeze_authorized": result["classification"]["freeze_authorized"],
                "output_dir": result["output_dir"],
            },
            indent=2,
        )
    )
    if result["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
