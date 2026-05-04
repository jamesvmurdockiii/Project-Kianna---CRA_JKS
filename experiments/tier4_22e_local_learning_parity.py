#!/usr/bin/env python3
"""Tier 4.22e local continuous-learning parity scaffold.

This tier checks the custom-C reward/plasticity equations before another
hardware allocation. It compares a fixed-point runtime mirror against a floating
reference on delayed-credit task streams and verifies the bounded pending
horizon queue does not store the future target at prediction time.

Claim boundary:
- PASS = minimal delayed-readout learning parity for the audited C equations.
- Not a hardware run, not full CRA parity, not lifecycle/replay/routing parity,
  and not speedup evidence.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"
RUNTIME = ROOT / "coral_reef_spinnaker" / "spinnaker_runtime"
SRC = RUNTIME / "src"
TIER = "Tier 4.22e - Local Continuous-Learning Parity Scaffold"
RUNNER_REVISION = "tier4_22e_local_learning_parity_20260430_0000"
TIER4_22D_LATEST = CONTROLLED / "tier4_22d_latest_manifest.json"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from tier4_harder_spinnaker_capsule import build_task, parse_seeds, parse_tasks  # noqa: E402

FP_SHIFT = 15
FP_ONE = 1 << FP_SHIFT


@dataclass
class PendingFloat:
    due: int
    feature: float
    prediction: float


@dataclass
class PendingFixed:
    due: int
    feature: int
    prediction: int


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sign(value: float) -> int:
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


def fp_from_float(value: float) -> int:
    return int(float(value) * FP_ONE)


def fp_to_float(value: int) -> float:
    return float(value) / float(FP_ONE)


def fp_mul(a: int, b: int) -> int:
    return (int(a) * int(b)) >> FP_SHIFT


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
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


def markdown_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.6g}"
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, sort_keys=True)
    return str(value)


def run_host_tests() -> dict[str, Any]:
    cmd = ["make", "-C", str(RUNTIME), "clean-host", "test"]
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)
    return {
        "command": " ".join(cmd),
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "passed": proc.returncode == 0 and "=== ALL TESTS PASSED ===" in proc.stdout,
    }


def source_checks() -> list[dict[str, Any]]:
    header = (SRC / "state_manager.h").read_text(encoding="utf-8")
    source = (SRC / "state_manager.c").read_text(encoding="utf-8")
    return [
        criterion("bounded pending queue constant", "MAX_PENDING_HORIZONS", "defined in config.h", "MAX_PENDING_HORIZONS" in (SRC / "config.h").read_text(encoding="utf-8")),
        criterion("pending horizon type exists", "pending_horizon_t", "declared", "pending_horizon_t" in header),
        criterion("pending horizon does not store future target", "int32_t target;", "absent from pending struct", "int32_t target;" not in header),
        criterion("schedule pending horizon API exists", "cra_state_schedule_pending_horizon", "declared/implemented", "cra_state_schedule_pending_horizon" in header and "int cra_state_schedule_pending_horizon" in source),
        criterion("mature pending horizon receives target at maturity", "cra_state_mature_pending_horizons(uint32_t timestep, int32_t target", "target supplied to mature API", "cra_state_mature_pending_horizons(uint32_t timestep, int32_t target" in header),
        criterion("pending horizon host tests exist", "pending horizon maturation/bound", "test_runtime.c covers queue", "test_state_pending_horizon_maturation" in (RUNTIME / "tests" / "test_runtime.c").read_text(encoding="utf-8")),
    ]


def task_args(args: argparse.Namespace) -> SimpleNamespace:
    return SimpleNamespace(
        steps=args.steps,
        amplitude=0.01,
        dt_seconds=0.05,
        delay=5,
        period=8,
        min_delay=3,
        max_delay=5,
        hard_period=7,
        noise_prob=0.20,
        sensory_noise_fraction=0.25,
        min_switch_interval=32,
        max_switch_interval=48,
    )


def feature_from_sensory(value: float) -> int:
    # The hardware capsules encode the future target with inverted sensory sign.
    return -sign(value)


def run_float_reference(task: Any, lr: float) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    weight = 0.0
    bias = 0.0
    pending: list[PendingFloat] = []
    rows: list[dict[str, Any]] = []
    matured = 0
    created = 0
    for step in range(task.steps):
        target = sign(float(task.current_target[step]))
        if target:
            kept: list[PendingFloat] = []
            for item in pending:
                if item.due <= step:
                    error = target - item.prediction
                    weight += lr * error * item.feature
                    bias += lr * error
                    matured += 1
                else:
                    kept.append(item)
            pending = kept

        feature = feature_from_sensory(float(task.sensory[step]))
        if feature and int(task.feedback_due_step[step]) >= 0:
            prediction = weight * feature + bias
            pending.append(PendingFloat(due=int(task.feedback_due_step[step]), feature=float(feature), prediction=float(prediction)))
            created += 1
            rows.append(
                {
                    "model": "float_reference",
                    "step": step,
                    "event_index": created - 1,
                    "feature": float(feature),
                    "prediction": float(prediction),
                    "prediction_sign": sign(prediction),
                    "target": sign(float(task.evaluation_target[step])),
                    "due_timestep": int(task.feedback_due_step[step]),
                    "weight": float(weight),
                    "bias": float(bias),
                }
            )
    summary = {"weight": weight, "bias": bias, "pending_created": created, "pending_matured": matured}
    return rows, summary


def run_fixed_runtime_mirror(task: Any, lr: float, *, pending_enabled: bool) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    weight = 0
    bias = 0
    lr_fp = fp_from_float(lr)
    pending: list[PendingFixed] = []
    rows: list[dict[str, Any]] = []
    matured = 0
    created = 0
    dropped = 0
    max_pending = 0
    for step in range(task.steps):
        target = sign(float(task.current_target[step]))
        if target and pending_enabled:
            kept: list[PendingFixed] = []
            for item in pending:
                if item.due <= step:
                    target_fp = fp_from_float(target)
                    error = target_fp - item.prediction
                    weight += fp_mul(lr_fp, fp_mul(error, item.feature))
                    bias += fp_mul(lr_fp, error)
                    matured += 1
                else:
                    kept.append(item)
            pending = kept

        feature_sign = feature_from_sensory(float(task.sensory[step]))
        if feature_sign and int(task.feedback_due_step[step]) >= 0:
            feature = fp_from_float(feature_sign)
            prediction = fp_mul(weight, feature) + bias
            if pending_enabled:
                if len(pending) < 128:
                    pending.append(PendingFixed(due=int(task.feedback_due_step[step]), feature=feature, prediction=prediction))
                    created += 1
                else:
                    dropped += 1
                max_pending = max(max_pending, len(pending))
            rows.append(
                {
                    "model": "fixed_runtime_mirror" if pending_enabled else "no_pending_ablation",
                    "step": step,
                    "event_index": len(rows),
                    "feature": float(feature_sign),
                    "prediction": fp_to_float(prediction),
                    "prediction_sign": sign(prediction),
                    "target": sign(float(task.evaluation_target[step])),
                    "due_timestep": int(task.feedback_due_step[step]),
                    "weight": fp_to_float(weight),
                    "bias": fp_to_float(bias),
                }
            )
    summary = {
        "weight": fp_to_float(weight),
        "bias": fp_to_float(bias),
        "pending_created": created,
        "pending_matured": matured,
        "pending_dropped": dropped,
        "max_pending": max_pending,
    }
    return rows, summary


def metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"event_count": 0, "accuracy": 0.0, "tail_accuracy": 0.0}
    pred = np.array([int(row["prediction_sign"]) for row in rows], dtype=int)
    target = np.array([int(row["target"]) for row in rows], dtype=int)
    correct = pred == target
    tail_n = max(1, len(rows) // 4)
    return {
        "event_count": int(len(rows)),
        "accuracy": float(np.mean(correct)),
        "tail_accuracy": float(np.mean(correct[-tail_n:])),
        "tail_n": int(tail_n),
    }


def run_case(task_name: str, seed: int, args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    task = build_task(task_name, seed=seed, args=task_args(args))
    float_rows, float_summary = run_float_reference(task, args.learning_rate)
    fixed_rows, fixed_summary = run_fixed_runtime_mirror(task, args.learning_rate, pending_enabled=True)
    no_pending_rows, no_pending_summary = run_fixed_runtime_mirror(task, args.learning_rate, pending_enabled=False)

    paired = min(len(float_rows), len(fixed_rows))
    sign_agreement = 0.0
    max_prediction_abs_delta = 0.0
    if paired:
        f_pred = np.array([float(row["prediction"]) for row in float_rows[:paired]])
        c_pred = np.array([float(row["prediction"]) for row in fixed_rows[:paired]])
        sign_agreement = float(np.mean(np.sign(f_pred) == np.sign(c_pred)))
        max_prediction_abs_delta = float(np.max(np.abs(f_pred - c_pred)))

    float_m = metrics(float_rows)
    fixed_m = metrics(fixed_rows)
    no_pending_m = metrics(no_pending_rows)
    summary = {
        "task": task_name,
        "seed": int(seed),
        "steps": int(args.steps),
        "learning_rate": float(args.learning_rate),
        "event_count": int(fixed_m["event_count"]),
        "float_accuracy": float(float_m["accuracy"]),
        "fixed_accuracy": float(fixed_m["accuracy"]),
        "no_pending_accuracy": float(no_pending_m["accuracy"]),
        "float_tail_accuracy": float(float_m["tail_accuracy"]),
        "fixed_tail_accuracy": float(fixed_m["tail_accuracy"]),
        "no_pending_tail_accuracy": float(no_pending_m["tail_accuracy"]),
        "float_weight": float(float_summary["weight"]),
        "fixed_weight": float(fixed_summary["weight"]),
        "float_bias": float(float_summary["bias"]),
        "fixed_bias": float(fixed_summary["bias"]),
        "weight_abs_delta": abs(float(float_summary["weight"]) - float(fixed_summary["weight"])),
        "bias_abs_delta": abs(float(float_summary["bias"]) - float(fixed_summary["bias"])),
        "sign_agreement": sign_agreement,
        "max_prediction_abs_delta": max_prediction_abs_delta,
        "pending_created": int(fixed_summary["pending_created"]),
        "pending_matured": int(fixed_summary["pending_matured"]),
        "pending_dropped": int(fixed_summary["pending_dropped"]),
        "max_pending": int(fixed_summary["max_pending"]),
        "no_pending_weight": float(no_pending_summary["weight"]),
        "no_pending_bias": float(no_pending_summary["bias"]),
    }
    rows: list[dict[str, Any]] = []
    for model_rows in (float_rows, fixed_rows, no_pending_rows):
        for row in model_rows:
            rows.append({"task": task_name, "seed": int(seed), **row})
    return rows, summary


def write_report(path: Path, result: dict[str, Any]) -> None:
    summary = result["summary"]
    lines = [
        "# Tier 4.22e Local Continuous-Learning Parity Scaffold",
        "",
        f"- Generated: `{result['generated_at_utc']}`",
        f"- Status: **{result['status'].upper()}**",
        f"- Output directory: `{result['output_dir']}`",
        "",
        "Tier 4.22e compares the custom-C fixed-point delayed-readout equations against a floating reference on delayed-credit task streams. It also checks that the pending-horizon state does not store future targets at prediction time.",
        "",
        "## Summary",
        "",
        f"- Tier 4.22d latest status: `{summary['tier4_22d_status']}`",
        f"- Host C tests passed: `{summary['host_tests_passed']}`",
        f"- Source checks passed: `{summary['source_checks_passed']}` / `{summary['source_checks_total']}`",
        f"- Minimum fixed/float sign agreement: `{markdown_value(summary['min_sign_agreement'])}`",
        f"- Maximum final weight delta: `{markdown_value(summary['max_weight_abs_delta'])}`",
        f"- Minimum fixed tail accuracy: `{markdown_value(summary['min_fixed_tail_accuracy'])}`",
        f"- Minimum pending advantage over no-pending tail: `{markdown_value(summary['min_pending_tail_advantage'])}`",
        "",
        "## Criteria",
        "",
        "| Criterion | Value | Rule | Pass |",
        "| --- | --- | --- | --- |",
    ]
    for item in result["criteria"]:
        lines.append(f"| {item['name']} | `{markdown_value(item.get('value'))}` | `{item.get('rule')}` | {'yes' if item.get('passed') else 'no'} |")
    lines.extend(["", "## Case Summaries", "", "| Task | Seed | Events | Fixed Tail | No-Pending Tail | Sign Agreement | Weight Delta |", "| --- | --- | --- | --- | --- | --- | --- |"])
    for row in result["case_summaries"]:
        lines.append(
            f"| {row['task']} | `{row['seed']}` | `{row['event_count']}` | `{markdown_value(row['fixed_tail_accuracy'])}` | `{markdown_value(row['no_pending_tail_accuracy'])}` | `{markdown_value(row['sign_agreement'])}` | `{markdown_value(row['weight_abs_delta'])}` |"
        )
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            "- This is local minimal delayed-readout parity evidence.",
            "- It is not a hardware run.",
            "- It is not full CRA parity, lifecycle/replay/routing parity, custom-runtime speedup, or final on-chip proof.",
            "- It authorizes the next hardware/build-oriented gate only if the hardware command/readback path can expose the same state.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_latest(output_dir: Path, manifest: Path, report: Path, status: str) -> None:
    CONTROLLED.mkdir(parents=True, exist_ok=True)
    write_json(
        CONTROLLED / "tier4_22e_latest_manifest.json",
        {
            "generated_at_utc": utc_now(),
            "tier": TIER,
            "status": status,
            "output_dir": str(output_dir),
            "manifest": str(manifest),
            "report": str(report),
            "canonical": False,
            "claim": "Latest Tier 4.22e local fixed-point delayed-readout parity scaffold; not hardware or full CRA parity evidence.",
        },
    )


def run(args: argparse.Namespace) -> int:
    output_dir = (args.output_dir or CONTROLLED / "tier4_22e_20260430_local_learning_parity").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    tier4_22d_status, tier4_22d_manifest = latest_status(TIER4_22D_LATEST)
    host = run_host_tests()
    checks = source_checks()
    all_rows: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    for task_name in args.tasks:
        for seed in args.seeds:
            rows, summary = run_case(task_name, seed, args)
            all_rows.extend(rows)
            summaries.append(summary)

    host_stdout = output_dir / "tier4_22e_host_test_stdout.txt"
    host_stderr = output_dir / "tier4_22e_host_test_stderr.txt"
    host_stdout.write_text(host["stdout"], encoding="utf-8")
    host_stderr.write_text(host["stderr"], encoding="utf-8")
    source_csv = output_dir / "tier4_22e_source_checks.csv"
    summary_csv = output_dir / "tier4_22e_summary.csv"
    timeseries_csv = output_dir / "tier4_22e_parity_timeseries.csv"
    write_csv(source_csv, checks)
    write_csv(summary_csv, summaries)
    write_csv(timeseries_csv, all_rows)

    source_passed = sum(1 for check in checks if check["passed"])
    min_sign_agreement = min([float(row["sign_agreement"]) for row in summaries] or [0.0])
    max_weight_delta = max([float(row["weight_abs_delta"]) for row in summaries] or [999.0])
    max_bias_delta = max([float(row["bias_abs_delta"]) for row in summaries] or [999.0])
    min_tail = min([float(row["fixed_tail_accuracy"]) for row in summaries] or [0.0])
    min_pending_advantage = min([float(row["fixed_tail_accuracy"]) - float(row["no_pending_tail_accuracy"]) for row in summaries] or [0.0])
    max_pending_dropped = max([int(row["pending_dropped"]) for row in summaries] or [1])
    max_pending = max([int(row["max_pending"]) for row in summaries] or [0])
    delayed_tail = min([float(row["fixed_tail_accuracy"]) for row in summaries if row["task"] == "delayed_cue"] or [0.0])
    hard_tail = min([float(row["fixed_tail_accuracy"]) for row in summaries if row["task"] == "hard_noisy_switching"] or [0.0])

    criteria = [
        criterion("runner revision current", RUNNER_REVISION, "expected current source", True),
        criterion("Tier 4.22d reward/plasticity scaffold pass exists", tier4_22d_status, "== pass", tier4_22d_status == "pass"),
        criterion("custom C host tests pass", host["returncode"], "returncode == 0 and ALL TESTS PASSED", bool(host["passed"])),
        criterion("all source checks pass", f"{source_passed}/{len(checks)}", "all pass", source_passed == len(checks)),
        criterion("fixed/float sign agreement", min_sign_agreement, f">= {args.min_sign_agreement}", min_sign_agreement >= args.min_sign_agreement),
        criterion("final weight parity", max_weight_delta, f"<= {args.max_weight_delta}", max_weight_delta <= args.max_weight_delta),
        criterion("final bias parity", max_bias_delta, f"<= {args.max_bias_delta}", max_bias_delta <= args.max_bias_delta),
        criterion("delayed_cue tail accuracy", delayed_tail, f">= {args.min_delayed_tail_accuracy}", delayed_tail >= args.min_delayed_tail_accuracy),
        criterion("hard_noisy_switching tail accuracy", hard_tail, f">= {args.min_hard_tail_accuracy}", hard_tail >= args.min_hard_tail_accuracy),
        criterion("pending queue beats no-pending ablation", min_pending_advantage, f">= {args.min_pending_advantage}", min_pending_advantage >= args.min_pending_advantage),
        criterion("pending queue does not overflow", max_pending_dropped, "== 0", max_pending_dropped == 0),
    ]
    status = "pass" if all(item["passed"] for item in criteria) else "fail"
    failure_reason = "" if status == "pass" else "Failed criteria: " + ", ".join(item["name"] for item in criteria if not item["passed"])
    aggregate = {
        "runner_revision": RUNNER_REVISION,
        "tier4_22d_status": tier4_22d_status,
        "tier4_22d_manifest": tier4_22d_manifest,
        "host_tests_passed": bool(host["passed"]),
        "source_checks_passed": source_passed,
        "source_checks_total": len(checks),
        "tasks": args.tasks,
        "seeds": args.seeds,
        "steps": int(args.steps),
        "learning_rate": float(args.learning_rate),
        "min_sign_agreement": min_sign_agreement,
        "max_weight_abs_delta": max_weight_delta,
        "max_bias_abs_delta": max_bias_delta,
        "min_fixed_tail_accuracy": min_tail,
        "delayed_cue_tail_accuracy_min": delayed_tail,
        "hard_noisy_switching_tail_accuracy_min": hard_tail,
        "min_pending_tail_advantage": min_pending_advantage,
        "max_pending": max_pending,
        "max_pending_dropped": max_pending_dropped,
        "claim_boundary": "Local minimal delayed-readout parity only; not hardware, full CRA parity, speedup, or final on-chip proof.",
        "next_step_if_passed": "Tier 4.22f hardware command/readback acceptance or APLX build/load gate before any learning hardware claim.",
    }
    manifest = output_dir / "tier4_22e_results.json"
    report = output_dir / "tier4_22e_report.md"
    result = {
        "tier": TIER,
        "generated_at_utc": utc_now(),
        "status": status,
        "failure_reason": failure_reason,
        "output_dir": str(output_dir),
        "summary": aggregate,
        "criteria": criteria,
        "source_checks": checks,
        "case_summaries": summaries,
        "host_test": {
            "command": host["command"],
            "returncode": host["returncode"],
            "stdout_artifact": str(host_stdout),
            "stderr_artifact": str(host_stderr),
        },
        "artifacts": {
            "manifest_json": str(manifest),
            "report_md": str(report),
            "summary_csv": str(summary_csv),
            "parity_timeseries_csv": str(timeseries_csv),
            "source_checks_csv": str(source_csv),
            "host_test_stdout": str(host_stdout),
            "host_test_stderr": str(host_stderr),
        },
    }
    write_json(manifest, result)
    write_report(report, result)
    write_latest(output_dir, manifest, report, status)
    print(json.dumps({"status": status, "output_dir": str(output_dir), "manifest": str(manifest)}, indent=2))
    return 0 if status == "pass" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Tier 4.22e local continuous-learning parity scaffold.")
    parser.add_argument("--tasks", type=parse_tasks, default=parse_tasks("delayed_cue,hard_noisy_switching"))
    parser.add_argument("--seeds", type=parse_seeds, default=parse_seeds("42"))
    parser.add_argument("--steps", type=int, default=1200)
    parser.add_argument("--learning-rate", type=float, default=0.25)
    parser.add_argument("--min-sign-agreement", type=float, default=0.999)
    parser.add_argument("--max-weight-delta", type=float, default=0.001)
    parser.add_argument("--max-bias-delta", type=float, default=0.001)
    parser.add_argument("--min-delayed-tail-accuracy", type=float, default=0.95)
    parser.add_argument("--min-hard-tail-accuracy", type=float, default=0.50)
    parser.add_argument("--min-pending-advantage", type=float, default=0.20)
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    return run(build_parser().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
