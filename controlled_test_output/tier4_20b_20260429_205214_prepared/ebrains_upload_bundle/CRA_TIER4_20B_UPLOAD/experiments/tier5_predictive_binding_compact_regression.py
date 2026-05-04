#!/usr/bin/env python3
"""Tier 5.17e predictive-binding compact regression and promotion gate.

Tier 5.17d is a bounded pre-reward predictive-binding diagnostic. Tier 5.17e is
not a new capability claim; it is the promotion guardrail before freezing a
v2.0 baseline. It verifies that the prior compact regression stack still passes,
that the v1.9 composition/routing path remains intact, and that the 5.17d
predictive-binding repair still clears its leakage and sham-separation gates.
"""

from __future__ import annotations

import argparse
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
TIER = "Tier 5.17e - Predictive-Binding Compact Regression"


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
    keys: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                keys.append(key)
                seen.add(key)
    import csv

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
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
    proc = subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=True, check=False)
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
    specs: list[tuple[str, str, list[str], Path, str]] = []

    compact_cmd = [
        py,
        "experiments/tier5_predictive_context_compact_regression.py",
        "--backend",
        args.backend,
        "--readout-lr",
        str(args.readout_lr),
        "--delayed-readout-lr",
        str(args.delayed_readout_lr),
        "--stop-on-fail",
        "--output-dir",
        str(output_dir / "v1_8_compact_regression"),
    ]
    if args.smoke:
        compact_cmd.extend(
            [
                "--tier1-steps",
                "80",
                "--tier1-seeds",
                "3",
                "--tier2-steps",
                "120",
                "--tier3-steps",
                "180",
                "--tier3-ecology-steps",
                "220",
                "--tier3-seed-count",
                "3",
                "--smoke-steps",
                "80",
                "--smoke-seed-count",
                "1",
                "--bootstrap-reps",
                "20",
                "--memory-backend",
                "mock",
                "--memory-tasks",
                "silent_context_reentry",
                "--memory-steps",
                "180",
                "--memory-seed-count",
                "1",
                "--memory-models",
                "sign_persistence,online_perceptron",
                "--memory-smoke",
                "--predictive-backend",
                "mock",
                "--predictive-tasks",
                "masked_input_prediction,event_stream_prediction",
                "--predictive-steps",
                "180",
                "--predictive-seed-count",
                "1",
                "--predictive-models",
                "sign_persistence,online_perceptron",
                "--predictive-smoke",
            ]
        )
    specs.append(
        (
            "v1_8_compact_regression",
            "existing compact guardrail: Tier 1/2/3, target smokes, replay/consolidation, and predictive-context checks remain green",
            compact_cmd,
            output_dir / "v1_8_compact_regression",
            "tier5_12d_results.json",
        )
    )

    composition_cmd = [
        py,
        "experiments/tier5_internal_composition_routing.py",
        "--backend",
        "mock",
        "--stop-on-fail",
        "--output-dir",
        str(output_dir / "v1_9_composition_routing_guardrail"),
    ]
    if args.smoke:
        composition_cmd.append("--smoke")
    else:
        composition_cmd.extend(
            [
                "--composition-tasks",
                "heldout_skill_pair,order_sensitive_chain,distractor_skill_chain",
                "--routing-tasks",
                "heldout_context_routing,distractor_router_chain,context_reentry_routing",
                "--composition-steps",
                "720",
                "--routing-steps",
                "960",
                "--seed-count",
                "3",
                "--models",
                "sign_persistence,online_perceptron,online_logistic_regression,echo_state_network,small_gru,stdp_only_snn",
            ]
        )
    specs.append(
        (
            "v1_9_composition_routing_guardrail",
            "v1.9 host-side internal composition/routing remains intact before adding predictive-binding to the baseline lock",
            composition_cmd,
            output_dir / "v1_9_composition_routing_guardrail",
            "tier5_13c_results.json",
        )
    )

    working_memory_cmd = [
        py,
        "experiments/tier5_working_memory_context_binding.py",
        "--backend",
        "mock",
        "--stop-on-fail",
        "--output-dir",
        str(output_dir / "working_memory_context_guardrail"),
    ]
    if args.smoke:
        working_memory_cmd.append("--smoke")
    else:
        working_memory_cmd.extend(
            [
                "--memory-tasks",
                "intervening_contexts,overlapping_contexts,context_reentry_interference",
                "--routing-tasks",
                "heldout_context_routing,distractor_router_chain,context_reentry_routing",
                "--memory-steps",
                "720",
                "--routing-steps",
                "960",
                "--seed-count",
                "3",
                "--models",
                "sign_persistence,online_perceptron,online_logistic_regression,echo_state_network,small_gru,stdp_only_snn",
            ]
        )
    specs.append(
        (
            "working_memory_context_guardrail",
            "Tier 5.14 working-memory/context-binding diagnostic still passes over the carried-forward v1.9-era host-side mechanisms",
            working_memory_cmd,
            output_dir / "working_memory_context_guardrail",
            "tier5_14_results.json",
        )
    )

    binding_cmd = [
        py,
        "experiments/tier5_predictive_binding_repair.py",
        "--stop-on-fail",
        "--output-dir",
        str(output_dir / "predictive_binding_guardrail"),
    ]
    if args.smoke:
        binding_cmd.append("--smoke")
    specs.append(
        (
            "predictive_binding_guardrail",
            "Tier 5.17d predictive-binding repair still clears leakage, dopamine, probe, and sham-separation gates",
            binding_cmd,
            output_dir / "predictive_binding_guardrail",
            "tier5_17d_results.json",
        )
    )
    return specs


def run_tier(args: argparse.Namespace, output_dir: Path) -> tuple[list[ChildRun], list[dict[str, Any]]]:
    child_runs: list[ChildRun] = []
    for name, purpose, command, child_output, manifest_name in build_child_specs(args, output_dir):
        print(f"[tier5.17e] running {name}...", flush=True)
        child = run_child(name, purpose, command, child_output, manifest_name)
        child_runs.append(child)
        print(f"[tier5.17e] {name}: {child.status.upper()} rc={child.return_code}", flush=True)
        if args.stop_on_fail and not child.passed:
            break

    by_name = {child.name: child for child in child_runs}

    def passed(name: str) -> bool:
        child = by_name.get(name)
        return bool(child and child.passed)

    def value(name: str) -> str:
        child = by_name.get(name)
        return child.status if child else "not_run"

    criteria = [
        criterion("v1.8 compact regression stack remains green", passed("v1_8_compact_regression"), value("v1_8_compact_regression"), "status == pass and return_code == 0"),
        criterion("v1.9 composition/routing guardrail remains green", passed("v1_9_composition_routing_guardrail"), value("v1_9_composition_routing_guardrail"), "status == pass and return_code == 0"),
        criterion("Tier 5.14 working-memory/context guardrail remains green", passed("working_memory_context_guardrail"), value("working_memory_context_guardrail"), "status == pass and return_code == 0"),
        criterion("Tier 5.17d predictive-binding guardrail remains green", passed("predictive_binding_guardrail"), value("predictive_binding_guardrail"), "status == pass and return_code == 0"),
    ]
    return child_runs, criteria


def write_report(path: Path, *, child_runs: list[ChildRun], criteria: list[dict[str, Any]], args: argparse.Namespace, output_dir: Path) -> None:
    status = "PASS" if all(item["passed"] for item in criteria) else "FAIL"
    lines = [
        "# Tier 5.17e Predictive-Binding Compact Regression Findings",
        "",
        f"- Generated: `{utc_now()}`",
        f"- Status: **{status}**",
        f"- Backend for compact regression: `{args.backend}`",
        f"- Smoke mode: `{args.smoke}`",
        f"- Candidate baseline: `v2.0_host_predictive_binding`, `readout_lr={args.readout_lr}`, `delayed_readout_lr={args.delayed_readout_lr}`",
        f"- Output directory: `{output_dir}`",
        "",
        "Tier 5.17e is a promotion/regression gate after the Tier 5.17d predictive-binding repair. It is not a new capability claim. It checks that prior compact guardrails, v1.9 composition/routing, Tier 5.14 working-memory/context binding, and Tier 5.17d predictive-binding shams all remain clean before a v2.0 baseline can be frozen.",
        "",
        "## Claim Boundary",
        "",
        "- Software-only promotion/regression evidence.",
        "- A pass authorizes a bounded v2.0 software baseline freeze for host-side predictive-binding pre-reward structure layered on v1.9-era mechanisms.",
        "- A pass does not prove general unsupervised concept learning, hardware/on-chip representation learning, full world modeling, language, planning, AGI, or external-baseline superiority.",
        "- A failure means Tier 5.17d stays noncanonical and v1.9 remains the latest frozen carried-forward baseline.",
        "",
        "## Child Runs",
        "",
        "| Child | Status | Return Code | Runtime Seconds | Purpose | Manifest |",
        "| --- | --- | ---: | ---: | --- | --- |",
    ]
    for child in child_runs:
        lines.append(f"| `{child.name}` | **{child.status.upper()}** | {child.return_code} | {child.runtime_seconds:.3f} | {child.purpose} | `{child.manifest_path}` |")
    lines.extend(["", "## Criteria", "", "| Criterion | Value | Rule | Pass |", "| --- | --- | --- | --- |"])
    for item in criteria:
        lines.append(f"| {item['name']} | `{item['value']}` | {item['rule']} | {'yes' if item['passed'] else 'no'} |")
    lines.extend(
        [
            "",
            "## Required Artifacts",
            "",
            "- `tier5_17e_results.json`: machine-readable promotion/regression manifest.",
            "- `tier5_17e_report.md`: this human-readable report.",
            "- `tier5_17e_summary.csv`: compact child-run summary.",
            "- `tier5_17e_child_manifests.json`: copied child manifest payloads for audit traceability.",
            "- child stdout/stderr logs for every subprocess.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latest(output_dir: Path, report_path: Path, manifest_path: Path, summary_csv: Path, status: str) -> None:
    write_json(
        CONTROLLED / "tier5_17e_latest_manifest.json",
        {
            "generated_at_utc": utc_now(),
            "status": status,
            "output_dir": str(output_dir),
            "manifest": str(manifest_path),
            "report": str(report_path),
            "summary_csv": str(summary_csv),
            "canonical": False,
            "claim": "Latest Tier 5.17e predictive-binding compact regression; passing authorizes bounded v2.0 baseline freeze after review.",
        },
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Tier 5.17e predictive-binding compact regression and promotion gate.")
    parser.add_argument("--backend", choices=["nest", "brian2", "mock"], default="nest")
    parser.add_argument("--readout-lr", type=float, default=0.10)
    parser.add_argument("--delayed-readout-lr", type=float, default=0.20)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--stop-on-fail", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = args.output_dir or (CONTROLLED / f"tier5_17e_{timestamp}")
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    started = time.perf_counter()
    child_runs, criteria = run_tier(args, output_dir)
    status = "pass" if all(item["passed"] for item in criteria) else "fail"
    runtime_seconds = time.perf_counter() - started

    manifest_path = output_dir / "tier5_17e_results.json"
    report_path = output_dir / "tier5_17e_report.md"
    summary_csv = output_dir / "tier5_17e_summary.csv"
    child_manifest_copy = output_dir / "tier5_17e_child_manifests.json"

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
            "baseline": "v2.0_candidate",
            "cra_variant": "host_predictive_binding_pre_reward_structure",
            "learning_location": "host",
            "readout_lr": args.readout_lr,
            "delayed_readout_lr": args.delayed_readout_lr,
            "claim": "bounded software predictive-binding pre-reward structure layered on v1.9-era mechanisms",
        },
        "summary": {
            "children_run": len(child_runs),
            "children_passed": sum(1 for child in child_runs if child.passed),
            "expected_children": 4,
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
            "Tier 5.17e is software-only compact regression and promotion-gate evidence.",
            "It checks prior compact guardrails, v1.9 composition/routing, Tier 5.14 working-memory/context binding, and Tier 5.17d predictive-binding sham separation.",
            "A pass authorizes bounded v2.0 software baseline freeze for host-side predictive-binding pre-reward structure only.",
            "It does not prove general unsupervised concept learning, hardware/on-chip representation learning, full world modeling, language, planning, AGI, or external-baseline superiority.",
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
