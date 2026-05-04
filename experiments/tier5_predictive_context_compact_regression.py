#!/usr/bin/env python3
"""Tier 5.12d predictive-context compact regression and promotion gate.

Tier 5.12d is a guardrail, not a new capability claim. It reruns compact
negative controls, positive learning tests, architecture ablations, v1.7
replay/consolidation guardrails, two hard/adaptive task smokes, and a compact
predictive-context sham-separation check before a host-side predictive-context
mechanism can be frozen as a carried-forward baseline.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"
TIER = "Tier 5.12d - Predictive-Context Compact Regression"


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
            "return_code": self.return_code,
            "status": self.status,
            "failure_reason": self.failure_reason,
            "runtime_seconds": self.runtime_seconds,
        }


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    return value


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                fieldnames.append(key)
                seen.add(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


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
            names = ", ".join(str(item.get("name", "unknown")) for item in failed)
            return "fail", f"failed child results: {names}"
        return "pass", ""

    return "fail", "manifest has no explicit status or result list"


def run_child(name: str, purpose: str, command: list[str], output_dir: Path, manifest_name: str) -> ChildRun:
    output_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = output_dir / f"{name}_stdout.log"
    stderr_path = output_dir / f"{name}_stderr.log"
    manifest_path = output_dir / manifest_name
    env = os.environ.copy()
    env.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
    started = time.perf_counter()
    proc = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
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


def criterion(name: str, passed: bool, value: Any, rule: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "value": value, "rule": rule}


def build_child_specs(args: argparse.Namespace, output_dir: Path) -> list[tuple[str, str, list[str], Path, str]]:
    py = sys.executable or "python3"
    lr_args = [
        "--readout-lr",
        str(args.readout_lr),
        "--delayed-readout-lr",
        str(args.delayed_readout_lr),
    ]
    return [
        (
            "tier1_controls",
            "negative controls stay negative under the candidate v1.8 predictive-context baseline",
            [
                py,
                "experiments/tier1_sanity.py",
                "--tests",
                "all",
                "--steps",
                str(args.tier1_steps),
                "--seeds",
                str(args.tier1_seeds),
                "--base-seed",
                str(args.base_seed),
                *lr_args,
                "--stop-on-fail",
                "--output-dir",
                str(output_dir / "tier1_controls"),
            ],
            output_dir / "tier1_controls",
            "tier1_results.json",
        ),
        (
            "tier2_learning",
            "positive learning controls still pass under the candidate v1.8 predictive-context baseline",
            [
                py,
                "experiments/tier2_learning.py",
                "--tests",
                "all",
                "--backend",
                args.backend,
                "--steps",
                str(args.tier2_steps),
                "--base-seed",
                str(args.base_seed),
                *lr_args,
                "--stop-on-fail",
                "--output-dir",
                str(output_dir / "tier2_learning"),
            ],
            output_dir / "tier2_learning",
            "tier2_results.json",
        ),
        (
            "tier3_ablations",
            "core mechanism ablation gaps remain meaningful under the candidate v1.8 predictive-context baseline",
            [
                py,
                "experiments/tier3_ablation.py",
                "--tests",
                "all",
                "--backend",
                args.backend,
                "--steps",
                str(args.tier3_steps),
                "--ecology-steps",
                str(args.tier3_ecology_steps),
                "--seed-count",
                str(args.tier3_seed_count),
                "--base-seed",
                str(args.base_seed),
                *lr_args,
                "--stop-on-fail",
                "--output-dir",
                str(output_dir / "tier3_ablations"),
            ],
            output_dir / "tier3_ablations",
            "tier3_results.json",
        ),
        (
            "target_task_smokes",
            "delayed_cue and hard_noisy_switching smoke matrix still executes with the carried-forward CRA path",
            [
                py,
                "experiments/tier5_baseline_fairness_audit.py",
                "--backend",
                args.backend,
                "--seed-count",
                str(args.smoke_seed_count),
                "--run-lengths",
                str(args.smoke_steps),
                "--tasks",
                "delayed_cue,hard_noisy_switching",
                "--models",
                "online_perceptron,online_logistic_regression",
                "--cra-variants",
                "v0_8",
                "--budget",
                "smoke",
                "--bootstrap-reps",
                str(args.bootstrap_reps),
                "--min-retuned-robust-regimes",
                "0",
                "--min-surviving-advantage-regimes",
                "0",
                "--stop-on-fail",
                "--output-dir",
                str(output_dir / "target_task_smokes"),
            ],
            output_dir / "target_task_smokes",
            "tier5_6_results.json",
        ),
        (
            "replay_consolidation_guardrail",
            "v1.7 replay/consolidation mechanism still passes a compact bounded-memory guardrail",
            [
                py,
                "experiments/tier5_generic_replay_confirmation.py",
                "--backend",
                args.memory_backend,
                "--tasks",
                args.memory_tasks,
                "--steps",
                str(args.memory_steps),
                "--seed-count",
                str(args.memory_seed_count),
                "--models",
                args.memory_models,
                "--variants",
                "all",
                "--output-dir",
                str(output_dir / "replay_consolidation_guardrail"),
                *(("--smoke",) if args.memory_smoke else ()),
                *(("--stop-on-fail",) if not args.memory_smoke else ()),
            ],
            output_dir / "replay_consolidation_guardrail",
            "tier5_11d_results.json",
        ),
        (
            "predictive_context_guardrail",
            "Tier 5.12c predictive-context candidate still beats shams on a compact predictive task matrix",
            [
                py,
                "experiments/tier5_predictive_context_sham_repair.py",
                "--backend",
                args.predictive_backend,
                "--tasks",
                args.predictive_tasks,
                "--steps",
                str(args.predictive_steps),
                "--seed-count",
                str(args.predictive_seed_count),
                "--models",
                args.predictive_models,
                "--variants",
                "all",
                "--min-candidate-accuracy",
                str(args.predictive_min_candidate_accuracy),
                "--min-candidate-tail-accuracy",
                str(args.predictive_min_candidate_tail_accuracy),
                "--min-candidate-edge-vs-v1-7",
                str(args.predictive_min_edge_vs_v1_7),
                "--min-candidate-edge-vs-ablation",
                str(args.predictive_min_edge_vs_ablation),
                "--min-candidate-edge-vs-control",
                str(args.predictive_min_edge_vs_control),
                "--min-candidate-edge-vs-standard",
                str(args.predictive_min_edge_vs_standard),
                "--output-dir",
                str(output_dir / "predictive_context_guardrail"),
                *(("--smoke",) if args.predictive_smoke else ()),
                *(("--stop-on-fail",) if not args.predictive_smoke else ()),
            ],
            output_dir / "predictive_context_guardrail",
            "tier5_12c_results.json",
        ),
    ]


def write_report(path: Path, *, child_runs: list[ChildRun], criteria: list[dict[str, Any]], args: argparse.Namespace, output_dir: Path) -> None:
    status = "PASS" if all(item["passed"] for item in criteria) else "FAIL"
    lines = [
        "# Tier 5.12d Predictive-Context Compact Regression Findings",
        "",
        f"- Generated: `{utc_now()}`",
        f"- Status: **{status}**",
        f"- Backend: `{args.backend}`",
        f"- Candidate baseline: `v1.8_host_predictive_context`, `readout_lr={args.readout_lr}`, `delayed_readout_lr={args.delayed_readout_lr}`",
        f"- Output directory: `{output_dir}`",
        "",
        "Tier 5.12d is a compact regression and promotion guardrail after the Tier 5.12c predictive-context sham-separation pass. It does not prove a new capability beyond 5.12c. It checks that the candidate host-side predictive-context mechanism does not break negative controls, positive learning, architecture ablations, v1.7 replay/consolidation evidence, or the two target hard/adaptive smoke tasks.",
        "",
        "## Claim Boundary",
        "",
        "- This is software-only regression evidence.",
        "- Passing authorizes a bounded v1.8 software baseline freeze for visible predictive-context tasks only.",
        "- Passing does not prove hidden-regime inference, full world modeling, language, planning, lifecycle/self-scaling, hardware prediction, hardware scaling, native on-chip learning, compositionality, or external-baseline superiority.",
        "- Failure means the predictive-context mechanism remains non-promoted and v1.7 stays the active carried-forward baseline.",
        "",
        "## Child Runs",
        "",
        "| Child | Status | Return Code | Runtime Seconds | Purpose | Manifest |",
        "| --- | --- | ---: | ---: | --- | --- |",
    ]
    for child in child_runs:
        lines.append(
            f"| `{child.name}` | **{child.status.upper()}** | {child.return_code} | {child.runtime_seconds:.3f} | {child.purpose} | `{child.manifest_path}` |"
        )
    lines.extend(["", "## Criteria", "", "| Criterion | Value | Rule | Pass |", "| --- | --- | --- | --- |"])
    for item in criteria:
        lines.append(f"| {item['name']} | `{item['value']}` | {item['rule']} | {'yes' if item['passed'] else 'no'} |")
    lines.extend(
        [
            "",
            "## Required Artifacts",
            "",
            "- `tier5_12d_results.json`: machine-readable compact-regression manifest.",
            "- `tier5_12d_report.md`: this human-readable report.",
            "- `tier5_12d_summary.csv`: compact child-run summary.",
            "- `tier5_12d_child_manifests.json`: copied child manifest payloads for audit traceability.",
            "- child stdout/stderr logs for every subprocess.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_tier(args: argparse.Namespace, output_dir: Path) -> tuple[list[ChildRun], list[dict[str, Any]]]:
    child_runs: list[ChildRun] = []
    for name, purpose, command, child_output, manifest_name in build_child_specs(args, output_dir):
        print(f"[tier5.12d] running {name}...", flush=True)
        child = run_child(name, purpose, command, child_output, manifest_name)
        child_runs.append(child)
        print(f"[tier5.12d] {name}: {child.status.upper()} rc={child.return_code}", flush=True)
        if args.stop_on_fail and not child.passed:
            break

    by_name = {child.name: child for child in child_runs}
    criteria = [
        criterion(
            "Tier 1 negative controls pass under candidate v1.8 baseline",
            by_name.get("tier1_controls", ChildRun("", "", [], Path(), Path(), Path(), Path(), 1, "fail", "not run", 0.0)).passed,
            by_name.get("tier1_controls").status if "tier1_controls" in by_name else "not_run",
            "status == pass and return_code == 0",
        ),
        criterion(
            "Tier 2 positive controls pass under candidate v1.8 baseline",
            by_name.get("tier2_learning", ChildRun("", "", [], Path(), Path(), Path(), Path(), 1, "fail", "not run", 0.0)).passed,
            by_name.get("tier2_learning").status if "tier2_learning" in by_name else "not_run",
            "status == pass and return_code == 0",
        ),
        criterion(
            "Tier 3 architecture ablations pass under candidate v1.8 baseline",
            by_name.get("tier3_ablations", ChildRun("", "", [], Path(), Path(), Path(), Path(), 1, "fail", "not run", 0.0)).passed,
            by_name.get("tier3_ablations").status if "tier3_ablations" in by_name else "not_run",
            "status == pass and return_code == 0",
        ),
        criterion(
            "target task smoke matrix completes under candidate v1.8 baseline",
            by_name.get("target_task_smokes", ChildRun("", "", [], Path(), Path(), Path(), Path(), 1, "fail", "not run", 0.0)).passed,
            by_name.get("target_task_smokes").status if "target_task_smokes" in by_name else "not_run",
            "status == pass and return_code == 0",
        ),
        criterion(
            "v1.7 replay/consolidation guardrail remains intact",
            by_name.get("replay_consolidation_guardrail", ChildRun("", "", [], Path(), Path(), Path(), Path(), 1, "fail", "not run", 0.0)).passed,
            by_name.get("replay_consolidation_guardrail").status if "replay_consolidation_guardrail" in by_name else "not_run",
            "status == pass and return_code == 0",
        ),
        criterion(
            "predictive-context sham-separation guardrail passes",
            by_name.get("predictive_context_guardrail", ChildRun("", "", [], Path(), Path(), Path(), Path(), 1, "fail", "not run", 0.0)).passed,
            by_name.get("predictive_context_guardrail").status if "predictive_context_guardrail" in by_name else "not_run",
            "status == pass and return_code == 0",
        ),
    ]
    return child_runs, criteria


def write_latest(output_dir: Path, report_path: Path, manifest_path: Path, summary_csv: Path, status: str) -> None:
    latest_path = CONTROLLED / "tier5_12d_latest_manifest.json"
    payload = {
        "generated_at_utc": utc_now(),
        "status": status,
        "output_dir": str(output_dir),
        "manifest": str(manifest_path),
        "report": str(report_path),
        "summary_csv": str(summary_csv),
        "canonical": False,
        "claim": "Latest Tier 5.12d predictive-context compact regression; passing authorizes bounded v1.8 baseline freeze after review.",
    }
    write_json(latest_path, payload)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Tier 5.12d predictive-context compact regression and promotion gate.")
    parser.set_defaults(
        backend="nest",
        base_seed=42,
        readout_lr=0.10,
        delayed_readout_lr=0.20,
        tier1_steps=200,
        tier1_seeds=20,
        tier2_steps=180,
        tier3_steps=180,
        tier3_ecology_steps=220,
        tier3_seed_count=3,
        smoke_steps=120,
        smoke_seed_count=1,
        bootstrap_reps=50,
        memory_backend="mock",
        memory_tasks="silent_context_reentry",
        memory_steps=240,
        memory_seed_count=1,
        memory_models="sign_persistence,online_perceptron",
        memory_smoke=True,
        predictive_backend="nest",
        predictive_tasks="masked_input_prediction,event_stream_prediction,sensor_anomaly_prediction",
        predictive_steps=240,
        predictive_seed_count=1,
        predictive_models="sign_persistence,online_perceptron",
        predictive_smoke=False,
        predictive_min_candidate_accuracy=0.70,
        predictive_min_candidate_tail_accuracy=0.75,
        predictive_min_edge_vs_v1_7=0.15,
        predictive_min_edge_vs_ablation=0.15,
        predictive_min_edge_vs_control=0.15,
        predictive_min_edge_vs_standard=0.10,
    )
    parser.add_argument("--backend", choices=["nest", "brian2", "mock"], default=argparse.SUPPRESS)
    parser.add_argument("--base-seed", type=int, default=argparse.SUPPRESS)
    parser.add_argument("--readout-lr", type=float, default=argparse.SUPPRESS)
    parser.add_argument("--delayed-readout-lr", type=float, default=argparse.SUPPRESS)
    parser.add_argument("--tier1-steps", type=int, default=argparse.SUPPRESS)
    parser.add_argument("--tier1-seeds", type=int, default=argparse.SUPPRESS)
    parser.add_argument("--tier2-steps", type=int, default=argparse.SUPPRESS)
    parser.add_argument("--tier3-steps", type=int, default=argparse.SUPPRESS)
    parser.add_argument("--tier3-ecology-steps", type=int, default=argparse.SUPPRESS)
    parser.add_argument("--tier3-seed-count", type=int, default=argparse.SUPPRESS)
    parser.add_argument("--smoke-steps", type=int, default=argparse.SUPPRESS)
    parser.add_argument("--smoke-seed-count", type=int, default=argparse.SUPPRESS)
    parser.add_argument("--bootstrap-reps", type=int, default=argparse.SUPPRESS)
    parser.add_argument("--memory-backend", choices=["nest", "brian2", "mock"], default=argparse.SUPPRESS)
    parser.add_argument("--memory-tasks", default=argparse.SUPPRESS)
    parser.add_argument("--memory-steps", type=int, default=argparse.SUPPRESS)
    parser.add_argument("--memory-seed-count", type=int, default=argparse.SUPPRESS)
    parser.add_argument("--memory-models", default=argparse.SUPPRESS)
    parser.add_argument("--memory-smoke", action=argparse.BooleanOptionalAction, default=argparse.SUPPRESS)
    parser.add_argument("--predictive-backend", choices=["nest", "brian2", "mock"], default=argparse.SUPPRESS)
    parser.add_argument("--predictive-tasks", default=argparse.SUPPRESS)
    parser.add_argument("--predictive-steps", type=int, default=argparse.SUPPRESS)
    parser.add_argument("--predictive-seed-count", type=int, default=argparse.SUPPRESS)
    parser.add_argument("--predictive-models", default=argparse.SUPPRESS)
    parser.add_argument("--predictive-smoke", action=argparse.BooleanOptionalAction, default=argparse.SUPPRESS)
    parser.add_argument("--predictive-min-candidate-accuracy", type=float, default=argparse.SUPPRESS)
    parser.add_argument("--predictive-min-candidate-tail-accuracy", type=float, default=argparse.SUPPRESS)
    parser.add_argument("--predictive-min-edge-vs-v1-7", type=float, default=argparse.SUPPRESS)
    parser.add_argument("--predictive-min-edge-vs-ablation", type=float, default=argparse.SUPPRESS)
    parser.add_argument("--predictive-min-edge-vs-control", type=float, default=argparse.SUPPRESS)
    parser.add_argument("--predictive-min-edge-vs-standard", type=float, default=argparse.SUPPRESS)
    parser.add_argument("--stop-on-fail", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.tier1_steps <= 0 or args.tier2_steps <= 0 or args.tier3_steps <= 0 or args.smoke_steps <= 0:
        raise SystemExit("all step counts must be positive")
    if args.tier1_seeds <= 0 or args.tier3_seed_count <= 0 or args.smoke_seed_count <= 0:
        raise SystemExit("all seed counts must be positive")
    if args.memory_steps <= 0 or args.predictive_steps <= 0:
        raise SystemExit("memory/predictive step counts must be positive")
    if args.memory_seed_count <= 0 or args.predictive_seed_count <= 0:
        raise SystemExit("memory/predictive seed counts must be positive")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = args.output_dir or (CONTROLLED / f"tier5_12d_{timestamp}")
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    started = time.perf_counter()
    child_runs, criteria = run_tier(args, output_dir)
    status = "pass" if all(item["passed"] for item in criteria) else "fail"
    runtime_seconds = time.perf_counter() - started

    manifest_path = output_dir / "tier5_12d_results.json"
    report_path = output_dir / "tier5_12d_report.md"
    summary_csv = output_dir / "tier5_12d_summary.csv"
    child_manifest_copy = output_dir / "tier5_12d_child_manifests.json"

    child_manifests: dict[str, Any] = {}
    for child in child_runs:
        if child.manifest_path.exists():
            try:
                child_manifests[child.name] = load_json(child.manifest_path)
            except Exception as exc:
                child_manifests[child.name] = {"error": str(exc)}
    write_json(child_manifest_copy, child_manifests)

    write_csv(
        summary_csv,
        [
            {
                "child": child.name,
                "status": child.status,
                "return_code": child.return_code,
                "runtime_seconds": child.runtime_seconds,
                "manifest_path": str(child.manifest_path),
                "output_dir": str(child.output_dir),
                "failure_reason": child.failure_reason,
            }
            for child in child_runs
        ],
    )
    manifest = {
        "generated_at_utc": utc_now(),
        "tier": TIER,
        "status": status,
        "backend": args.backend,
        "command": " ".join(sys.argv),
        "output_dir": str(output_dir),
        "runtime_seconds": runtime_seconds,
        "candidate_baseline": {
            "readout_lr": args.readout_lr,
            "delayed_readout_lr": args.delayed_readout_lr,
            "baseline": "v1.8_candidate",
            "cra_variant": "cra_v1_8_host_predictive_context",
            "learning_location": "host",
            "claim": "bounded visible predictive-context software mechanism",
        },
        "summary": {
            "children_run": len(child_runs),
            "children_passed": sum(1 for child in child_runs if child.passed),
            "expected_children": 6,
            "criteria_passed": sum(1 for item in criteria if item["passed"]),
            "criteria_total": len(criteria),
        },
        "criteria": criteria,
        "child_runs": [child.to_dict() for child in child_runs],
        "artifacts": {
            "summary_csv": str(summary_csv),
            "report_md": str(report_path),
            "child_manifests_json": str(child_manifest_copy),
        },
        "claim_boundary": [
            "Tier 5.12d is software-only compact regression and promotion-gate evidence.",
            "It checks that the candidate v1.8 host-side predictive-context mechanism does not break controls, learning proofs, ablations, target task smokes, or v1.7 replay/consolidation guardrails.",
            "A pass authorizes bounded v1.8 software baseline freeze for visible predictive-context tasks only.",
            "It does not prove hidden-regime inference, full world modeling, language, planning, lifecycle/self-scaling, hardware prediction, hardware scaling, native on-chip learning, compositionality, or external-baseline superiority.",
        ],
    }
    write_json(manifest_path, manifest)
    write_report(report_path, child_runs=child_runs, criteria=criteria, args=args, output_dir=output_dir)
    write_latest(output_dir, report_path, manifest_path, summary_csv, status)

    print(
        json.dumps(
            {
                "status": status,
                "output_dir": str(output_dir),
                "manifest": str(manifest_path),
                "report": str(report_path),
                "summary_csv": str(summary_csv),
            },
            indent=2,
        ),
        flush=True,
    )
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
