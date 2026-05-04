#!/usr/bin/env python3
"""Tier 5.9c macro-eligibility recheck against the frozen v2.1 evidence state.

Tier 5.9a and 5.9b were clean non-promotions under the v1.4-era delayed-credit
harness. Since the project now has a frozen v2.1 host-side software baseline,
this tier performs a bounded recheck before deciding whether macro eligibility
should remain parked.

This is intentionally not a silent promotion. It runs two child gates:

1. the v2.1 self-evaluation compact/regression gate remains green; and
2. the residual macro-eligibility diagnostic earns its own promotion gate.

A pass would authorize a later *integration* tier that combines macro credit with
v2.1 mechanisms. A fail keeps macro eligibility parked. This script does not
claim native eligibility, hardware eligibility, or custom-C readiness.
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
TIER = "Tier 5.9c - Macro Eligibility v2.1 Recheck"
V21_BASELINE = ROOT / "baselines" / "CRA_EVIDENCE_BASELINE_v2.1.json"


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
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    import csv

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


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def manifest_status(manifest_path: Path) -> tuple[str, str]:
    if not manifest_path.exists():
        return "fail", f"missing manifest: {manifest_path}"
    try:
        manifest = load_json(manifest_path)
    except Exception as exc:  # pragma: no cover - defensive report path
        return "fail", f"could not parse manifest: {exc}"

    explicit = manifest.get("status")
    if explicit in {"pass", "fail", "prepared", "blocked"}:
        return str(explicit), str(manifest.get("failure_reason") or "")

    result = manifest.get("result")
    if isinstance(result, dict) and result.get("status") in {"pass", "fail", "prepared", "blocked"}:
        return str(result["status"]), str(result.get("failure_reason") or "")

    return "fail", "manifest has no explicit status or result status"


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
    v21_dir = output_dir / "v2_1_guardrail"
    macro_dir = output_dir / "macro_residual_recheck"

    if args.smoke:
        v21_cmd = [
            py,
            "experiments/tier5_self_evaluation_compact_regression.py",
            "--smoke",
            "--output-dir",
            str(v21_dir),
        ]
        macro_cmd = [
            py,
            "experiments/tier5_macro_eligibility_repair.py",
            "--backend",
            "mock",
            "--tasks",
            "delayed_cue,variable_delay_cue",
            "--steps",
            str(args.smoke_steps),
            "--seed-count",
            "1",
            "--models",
            "sign_persistence,online_perceptron",
            "--variants",
            "all",
            "--smoke",
            "--output-dir",
            str(macro_dir),
        ]
    else:
        v21_cmd = [
            py,
            "experiments/tier5_self_evaluation_compact_regression.py",
            "--backend",
            args.backend,
            "--readout-lr",
            str(args.readout_lr),
            "--delayed-readout-lr",
            str(args.delayed_readout_lr),
            "--stop-on-fail",
            "--output-dir",
            str(v21_dir),
        ]
        macro_cmd = [
            py,
            "experiments/tier5_macro_eligibility_repair.py",
            "--backend",
            args.backend,
            "--tasks",
            args.tasks,
            "--steps",
            str(args.steps),
            "--seed-count",
            str(args.seed_count),
            "--models",
            args.models,
            "--variants",
            "all",
            "--repair-residual-scale",
            str(args.repair_residual_scale),
            "--repair-trace-clip",
            str(args.repair_trace_clip),
            "--repair-decay",
            str(args.repair_decay),
            "--stop-on-fail",
            "--output-dir",
            str(macro_dir),
        ]

    return [
        (
            "v2_1_guardrail",
            "rerun the v2.1 promotion/regression gate so the current baseline remains intact before interpreting macro-credit work",
            v21_cmd,
            v21_dir,
            "tier5_18c_results.json",
        ),
        (
            "macro_residual_recheck",
            "rerun the residual macro-eligibility diagnostic that previously failed trace-ablation separation",
            macro_cmd,
            macro_dir,
            "tier5_9b_results.json",
        ),
    ]


def run_tier(args: argparse.Namespace, output_dir: Path) -> tuple[list[ChildRun], list[dict[str, Any]]]:
    children: list[ChildRun] = []
    for name, purpose, command, child_output, manifest_name in build_child_specs(args, output_dir):
        print(f"[tier5.9c] running {name}...", flush=True)
        child = run_child(name, purpose, command, child_output, manifest_name)
        children.append(child)
        print(f"[tier5.9c] {name}: {child.status.upper()} rc={child.return_code}", flush=True)
        if args.stop_on_fail and not child.passed:
            break

    by_name = {child.name: child for child in children}

    def passed(name: str) -> bool:
        child = by_name.get(name)
        return bool(child and child.passed)

    def value(name: str) -> str:
        child = by_name.get(name)
        return child.status if child else "not_run"

    criteria = [
        criterion("frozen v2.1 baseline artifact exists", V21_BASELINE.exists(), str(V21_BASELINE), "exists"),
        criterion("v2.1 guardrail remains green", passed("v2_1_guardrail"), value("v2_1_guardrail"), "status == pass and return_code == 0"),
        criterion("residual macro eligibility earns promotion gate", passed("macro_residual_recheck"), value("macro_residual_recheck"), "status == pass and return_code == 0"),
        criterion("all child commands succeeded", all(child.passed for child in children) and len(children) == 2, f"{sum(child.passed for child in children)}/2", "== 2/2"),
    ]
    return children, criteria


def write_report(path: Path, *, result: dict[str, Any], children: list[ChildRun]) -> None:
    lines = [
        "# Tier 5.9c Macro Eligibility v2.1 Recheck Findings",
        "",
        f"- Generated: `{result['generated_at_utc']}`",
        f"- Status: **{result['status'].upper()}**",
        f"- Output directory: `{result['output_dir']}`",
        f"- Smoke: `{result['summary']['smoke']}`",
        "",
        "Tier 5.9c rechecks the parked macro-eligibility mechanism after the v2.1 software baseline. It asks whether the current v2.1 guardrails remain green and whether the residual macro trace now earns its own delayed-credit promotion gate.",
        "",
        "## Claim Boundary",
        "",
        "- `PASS` would authorize a later v2.1-plus-macro integration tier, not immediate baseline freeze.",
        "- `FAIL` keeps macro eligibility parked as non-promoted diagnostic evidence.",
        "- This is not SpiNNaker hardware evidence, native/on-chip eligibility, custom-C runtime evidence, or external-baseline superiority.",
        "- The child macro diagnostic still uses the delayed-credit harness; v2.1 integration requires a separate follow-up gate if this passes.",
        "",
        "## Summary",
        "",
        f"- children_passed: `{result['summary']['children_passed']}` / `{result['summary']['children_total']}`",
        f"- criteria_passed: `{result['summary']['criteria_passed']}` / `{result['summary']['criteria_total']}`",
        f"- runtime_seconds: `{result['summary']['runtime_seconds']:.3f}`",
        "",
        "## Child Runs",
        "",
        "| Child | Status | Runtime seconds | Purpose | Failure |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for child in children:
        lines.append(
            f"| `{child.name}` | **{child.status.upper()}** | `{child.runtime_seconds:.3f}` | {child.purpose} | {child.failure_reason or ''} |"
        )
    lines.extend(["", "## Criteria", "", "| Criterion | Value | Rule | Pass |", "| --- | --- | --- | --- |"])
    for item in result["criteria"]:
        lines.append(f"| {item['name']} | `{item['value']}` | `{item['rule']}` | {'yes' if item['passed'] else 'no'} |")
    if result.get("failure_reason"):
        lines.extend(["", f"Failure: {result['failure_reason']}"])
    lines.extend(["", "## Artifacts", ""])
    for key, value in result["artifacts"].items():
        lines.append(f"- `{key}`: `{value}`")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_latest(output_dir: Path, manifest_path: Path, report_path: Path, summary_csv: Path, status: str) -> None:
    write_json(
        CONTROLLED / "tier5_9c_latest_manifest.json",
        {
            "generated_at_utc": utc_now(),
            "tier": TIER,
            "status": status,
            "output_dir": str(output_dir),
            "manifest": str(manifest_path),
            "report": str(report_path),
            "summary_csv": str(summary_csv),
            "canonical": False,
            "claim": "Latest Tier 5.9c macro-eligibility recheck; macro remains parked unless this passes and a later integration gate passes.",
        },
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Tier 5.9c macro-eligibility recheck against v2.1 guardrails.")
    parser.add_argument("--backend", default="nest")
    parser.add_argument("--tasks", default="delayed_cue,hard_noisy_switching,variable_delay_cue,aba_recurrence")
    parser.add_argument("--steps", type=int, default=960)
    parser.add_argument("--seed-count", type=int, default=3)
    parser.add_argument("--models", default="sign_persistence,online_perceptron,online_logistic_regression,echo_state_network,stdp_only_snn")
    parser.add_argument("--readout-lr", type=float, default=0.10)
    parser.add_argument("--delayed-readout-lr", type=float, default=0.20)
    parser.add_argument("--repair-residual-scale", type=float, default=0.10)
    parser.add_argument("--repair-trace-clip", type=float, default=1.0)
    parser.add_argument("--repair-decay", type=float, default=0.92)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--smoke-steps", type=int, default=160)
    parser.add_argument("--stop-on-fail", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = args.output_dir or (CONTROLLED / f"tier5_9c_{timestamp}")
    output_dir.mkdir(parents=True, exist_ok=True)

    started = time.perf_counter()
    children, criteria = run_tier(args, output_dir)
    status = "pass" if all(item["passed"] for item in criteria) else "fail"
    failure_reason = "" if status == "pass" else "Failed criteria: " + ", ".join(item["name"] for item in criteria if not item["passed"])
    result = {
        "tier": TIER,
        "generated_at_utc": utc_now(),
        "output_dir": str(output_dir),
        "command": " ".join(sys.argv),
        "status": status,
        "failure_reason": failure_reason,
        "criteria": criteria,
        "children": [child.to_dict() for child in children],
        "summary": {
            "smoke": bool(args.smoke),
            "children_passed": int(sum(child.passed for child in children)),
            "children_total": 2,
            "criteria_passed": int(sum(item["passed"] for item in criteria)),
            "criteria_total": len(criteria),
            "runtime_seconds": time.perf_counter() - started,
        },
        "artifacts": {
            "child_manifests_json": str(output_dir / "tier5_9c_child_manifests.json"),
            "summary_csv": str(output_dir / "tier5_9c_summary.csv"),
            "report_md": str(output_dir / "tier5_9c_report.md"),
        },
    }
    child_manifest_path = output_dir / "tier5_9c_child_manifests.json"
    summary_csv = output_dir / "tier5_9c_summary.csv"
    manifest_path = output_dir / "tier5_9c_results.json"
    report_path = output_dir / "tier5_9c_report.md"
    write_json(child_manifest_path, {"children": [child.to_dict() for child in children]})
    write_csv(summary_csv, [{"child": child.name, "status": child.status, "return_code": child.return_code, "runtime_seconds": child.runtime_seconds, "manifest": str(child.manifest_path)} for child in children])
    write_json(manifest_path, result)
    write_report(report_path, result=result, children=children)
    write_latest(output_dir, manifest_path, report_path, summary_csv, status)
    print(json.dumps({"status": status, "output_dir": str(output_dir), "manifest": str(manifest_path), "report": str(report_path), "failure_reason": failure_reason}, indent=2))
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
