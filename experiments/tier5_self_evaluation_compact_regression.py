#!/usr/bin/env python3
"""Tier 5.18c self-evaluation compact regression and promotion gate.

Tier 5.18 passed as a noncanonical software diagnostic over frozen v2.0. Tier
5.18c is not a new capability claim; it is the promotion guardrail before a
possible v2.1 freeze. It reruns the v2.0 compact gate and the Tier 5.18
self-evaluation diagnostic, then records whether the stack is stable enough to
freeze bounded host-side software reliability-monitoring evidence.
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
TIER = "Tier 5.18c - Self-Evaluation Compact Regression"
V20_BASELINE = ROOT / "baselines" / "CRA_EVIDENCE_BASELINE_v2.0.json"


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
    v20_dir = output_dir / "v2_0_compact_regression_gate"
    self_eval_dir = output_dir / "tier5_18_self_evaluation_guardrail"

    v20_cmd = [
        py,
        "experiments/tier5_predictive_binding_compact_regression.py",
        "--backend",
        args.backend,
        "--readout-lr",
        str(args.readout_lr),
        "--delayed-readout-lr",
        str(args.delayed_readout_lr),
        "--stop-on-fail",
        "--output-dir",
        str(v20_dir),
    ]
    if args.smoke:
        v20_cmd = [
            py,
            "experiments/tier5_predictive_binding_compact_regression.py",
            "--smoke",
            "--backend",
            "mock",
            "--stop-on-fail",
            "--output-dir",
            str(v20_dir),
        ]

    self_eval_cmd = [
        py,
        "experiments/tier5_self_evaluation_metacognition.py",
        "--stop-on-fail",
        "--output-dir",
        str(self_eval_dir),
    ]
    if args.smoke:
        self_eval_cmd.insert(2, "--smoke")

    return [
        (
            "v2_0_compact_regression_gate",
            "rerun the v2.0 promotion/regression stack: v1.8 compact regression, v1.9 composition/routing, Tier 5.14, and Tier 5.17d guardrails remain green",
            v20_cmd,
            v20_dir,
            "tier5_17e_results.json",
        ),
        (
            "tier5_18_self_evaluation_guardrail",
            "rerun the Tier 5.18 calibrated pre-feedback reliability-monitoring and confidence-gated adaptation diagnostic",
            self_eval_cmd,
            self_eval_dir,
            "tier5_18_results.json",
        ),
    ]


def write_report(path: Path, result: dict[str, Any], children: list[ChildRun]) -> None:
    lines = [
        "# Tier 5.18c Self-Evaluation Compact Regression Findings",
        "",
        f"- Generated: `{result['generated_at_utc']}`",
        f"- Status: **{result['status'].upper()}**",
        f"- Output directory: `{result['output_dir']}`",
        f"- Smoke: `{result['summary']['smoke']}`",
        "",
        "Tier 5.18c is the promotion/regression gate for the Tier 5.18 self-evaluation diagnostic. It does not add a new capability claim; it asks whether v2.0 guardrails and the self-evaluation diagnostic can pass together before a bounded v2.1 freeze.",
        "",
        "## Claim Boundary",
        "",
        "- `PASS` authorizes a bounded host-side software v2.1 freeze for operational self-evaluation / reliability monitoring.",
        "- It is not consciousness, self-awareness, introspection, SpiNNaker hardware self-monitoring, language, planning, AGI, or external-baseline superiority.",
        "- Hardware/custom-C transfer remains future work.",
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
    lines.extend(["", "## Artifacts", ""])
    for key, value in result["artifacts"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=TIER)
    parser.add_argument("--backend", default="nest", choices=["mock", "nest", "brian2"])
    parser.add_argument("--readout-lr", type=float, default=0.10)
    parser.add_argument("--delayed-readout-lr", type=float, default=0.20)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--stop-on-fail", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_dir = args.output_dir or (CONTROLLED / f"tier5_18c_{stamp}")
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()

    children: list[ChildRun] = []
    for name, purpose, command, child_output_dir, manifest_name in build_child_specs(args, output_dir):
        print(f"[tier5.18c] child={name}", flush=True)
        child = run_child(name, purpose, command, child_output_dir, manifest_name)
        children.append(child)
        if args.stop_on_fail and not child.passed:
            break

    criteria = [
        criterion("frozen v2.0 baseline artifact exists", V20_BASELINE.exists(), str(V20_BASELINE), "exists"),
        criterion(
            "v2.0 compact regression gate remains green",
            any(child.name == "v2_0_compact_regression_gate" and child.passed for child in children),
            next((child.status for child in children if child.name == "v2_0_compact_regression_gate"), "not_run"),
            "== pass",
        ),
        criterion(
            "Tier 5.18 self-evaluation guardrail remains green",
            any(child.name == "tier5_18_self_evaluation_guardrail" and child.passed for child in children),
            next((child.status for child in children if child.name == "tier5_18_self_evaluation_guardrail"), "not_run"),
            "== pass",
        ),
        criterion("all child commands succeeded", all(child.passed for child in children) and len(children) == 2, f"{sum(child.passed for child in children)}/2", "== 2/2"),
    ]
    status = "pass" if all(item["passed"] for item in criteria) else "fail"
    failure_reason = "" if status == "pass" else "Failed criteria: " + ", ".join(item["name"] for item in criteria if not item["passed"])
    runtime_seconds = time.perf_counter() - started

    artifacts = {
        "child_manifests_json": str(output_dir / "tier5_18c_child_manifests.json"),
        "summary_csv": str(output_dir / "tier5_18c_summary.csv"),
        "report_md": str(output_dir / "tier5_18c_report.md"),
    }
    result = {
        "tier": TIER,
        "generated_at_utc": utc_now(),
        "status": status,
        "failure_reason": failure_reason,
        "output_dir": str(output_dir),
        "baseline_in": str(V20_BASELINE),
        "criteria": criteria,
        "children": [child.to_dict() for child in children],
        "summary": {
            "smoke": bool(args.smoke),
            "children_total": 2,
            "children_passed": sum(child.passed for child in children),
            "criteria_total": len(criteria),
            "criteria_passed": sum(bool(item["passed"]) for item in criteria),
            "runtime_seconds": runtime_seconds,
            "claim_boundary": "Promotion/regression gate for bounded host-side software self-evaluation evidence. Not consciousness, self-awareness, hardware evidence, AGI, language, planning, or external-baseline superiority.",
        },
        "artifacts": artifacts,
    }
    child_manifest_path = output_dir / "tier5_18c_child_manifests.json"
    write_json(child_manifest_path, {"children": [child.to_dict() for child in children]})
    write_csv(output_dir / "tier5_18c_summary.csv", [child.to_dict() for child in children])
    write_report(output_dir / "tier5_18c_report.md", result, children)
    result["artifacts"]["results_json"] = str(output_dir / "tier5_18c_results.json")
    write_json(output_dir / "tier5_18c_results.json", result)
    write_json(CONTROLLED / "tier5_18c_latest_manifest.json", result)

    print(
        json.dumps(
            {
                "tier": TIER,
                "status": status,
                "failure_reason": failure_reason,
                "output_dir": str(output_dir),
                "report": str(output_dir / "tier5_18c_report.md"),
                "runtime_seconds": runtime_seconds,
                "claim_boundary": result["summary"]["claim_boundary"],
            },
            indent=2,
        )
    )
    if status != "pass" and args.stop_on_fail:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
