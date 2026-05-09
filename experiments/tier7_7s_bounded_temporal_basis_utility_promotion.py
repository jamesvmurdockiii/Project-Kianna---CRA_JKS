#!/usr/bin/env python3
"""Tier 7.7s - bounded temporal-basis utility promotion/regression gate.

This gate consumes Tier 7.7q and Tier 7.7r. It asks whether the temporal-basis
interface may be carried forward as a bounded engineering utility, while
explicitly blocking any CRA-specific mechanism claim because strong generic
controls still won in Tier 7.7q.
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
TIER = "Tier 7.7s - Bounded Temporal-Basis Utility Promotion/Regression Gate"
RUNNER_REVISION = "tier7_7s_bounded_temporal_basis_utility_promotion_20260509_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_7s_20260509_bounded_temporal_basis_utility_promotion"
TIER7_7Q_RESULTS = CONTROLLED / "tier7_7q_20260509_cra_native_temporal_interface_internalization_scoring_gate" / "tier7_7q_results.json"
TIER7_7R_RESULTS = CONTROLLED / "tier7_7r_20260509_native_temporal_basis_reframing_contract" / "tier7_7r_results.json"

NATIVE = "cra_native_sparse_temporal_expansion"
CURRENT = "current_cra_baseline"


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


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    return value


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = []
        for row in rows:
            for key in row:
                if key not in fieldnames:
                    fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json_safe(row.get(key, "")) for key in fieldnames})


def criterion(name: str, value: Any, rule: str, passed: bool, details: str = "") -> dict[str, Any]:
    return {
        "name": name,
        "criterion": name,
        "value": json_safe(value),
        "operator": rule,
        "rule": rule,
        "passed": bool(passed),
        "pass": bool(passed),
        "details": details,
        "note": details,
    }


def manifest_status(manifest_path: Path) -> tuple[str, str]:
    if not manifest_path.exists():
        return "fail", f"missing manifest: {manifest_path}"
    try:
        payload = read_json(manifest_path)
    except Exception as exc:  # pragma: no cover - defensive diagnostics
        return "fail", f"could not parse manifest: {exc}"
    explicit = payload.get("status")
    if explicit in {"pass", "fail", "prepared", "blocked"}:
        return str(explicit), str(payload.get("failure_reason") or "")
    result = payload.get("result")
    if isinstance(result, dict) and result.get("status") in {"pass", "fail", "prepared", "blocked"}:
        return str(result["status"]), str(result.get("failure_reason") or "")
    return "fail", "manifest has no explicit status"


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
    if manifest_name == "__returncode__":
        status = "pass" if proc.returncode == 0 else "fail"
        failure_reason = "" if proc.returncode == 0 else f"command exited {proc.returncode}"
        write_json(manifest_path, {"status": status, "return_code": int(proc.returncode), "runtime_seconds": runtime_seconds})
    else:
        status, failure_reason = manifest_status(manifest_path)
    if proc.returncode != 0 and not failure_reason:
        failure_reason = f"command exited {proc.returncode}"
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


def run_compact_guardrail(args: argparse.Namespace, output_dir: Path) -> ChildRun | None:
    if args.compact_mode == "skip":
        return None
    compact_dir = output_dir / "compact_regression_pytest"
    command = [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "coral_reef_spinnaker/tests"]
    return run_child(
        name="compact_regression_pytest",
        purpose="repository pytest regression guard before bounded temporal-interface utility promotion",
        command=command,
        output_dir=compact_dir,
        manifest_name="__returncode__",
    )


def score_lookup(score_summary: list[dict[str, Any]], task: str, family: str, capacity: int = 128) -> float | None:
    for row in score_summary:
        if row.get("task") == task and row.get("probe_family") == family and int(row.get("capacity_units", -1)) == capacity:
            value = row.get("geomean_mse")
            return float(value) if value is not None else None
    return None


def safe_ratio(num: float | None, den: float | None) -> float | None:
    if num is None or den is None or den <= 0.0:
        return None
    return num / den


def task_ratio_rows(q_payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    summary = q_payload.get("score_summary") or []
    for task in ["lorenz", "mackey_glass", "narma10"]:
        native = score_lookup(summary, task, NATIVE)
        current = score_lookup(summary, task, CURRENT)
        rows.append(
            {
                "task": task,
                "capacity_units": 128,
                "native_geomean_mse": native,
                "current_geomean_mse": current,
                "current_divided_by_native": safe_ratio(current, native),
                "native_materially_better": (safe_ratio(current, native) or 0.0) >= 1.10,
                "native_material_regression": (safe_ratio(native, current) or 0.0) > 1.10,
            }
        )
    return rows


def classify(q_payload: dict[str, Any], r_payload: dict[str, Any], compact_child: ChildRun | None, args: argparse.Namespace) -> dict[str, Any]:
    diagnostics = ((q_payload.get("classification") or {}).get("diagnostics") or {})
    task_rows = task_ratio_rows(q_payload)
    compact_pass = compact_child is not None and compact_child.passed
    compact_full = args.compact_mode == "pytest"
    utility_signal = bool(
        q_payload.get("status") == "pass"
        and r_payload.get("status") == "pass"
        and diagnostics.get("useful_vs_current") is True
        and diagnostics.get("guards_ok") is True
        and diagnostics.get("regressions_ok") is True
        and all(not row["native_material_regression"] for row in task_rows)
        and any(row["native_materially_better"] for row in task_rows)
    )
    mechanism_blocked = not bool(diagnostics.get("beats_random_projection") and diagnostics.get("beats_nonlinear_lag"))
    utility_promoted = bool(utility_signal and compact_pass and compact_full and mechanism_blocked)
    if utility_promoted:
        outcome = "utility_promoted_mechanism_not_promoted"
        recommendation = "Carry the temporal-basis interface forward as bounded engineering utility; do not call it a CRA-specific mechanism."
    elif utility_signal and compact_pass:
        outcome = "utility_supported_pending_full_compact"
        recommendation = "Utility signal remains, but run full compact regression before promotion."
    elif utility_signal:
        outcome = "utility_supported_compact_missing_or_failed"
        recommendation = "Utility signal remains, but no promotion without compact regression."
    else:
        outcome = "utility_not_promoted"
        recommendation = "Do not promote; park or redesign through a new contract."
    return {
        "outcome": outcome,
        "recommendation": recommendation,
        "utility_promoted": utility_promoted,
        "mechanism_promoted": False,
        "baseline_freeze_authorized": False,
        "hardware_transfer_authorized": False,
        "broad_usefulness_claim_authorized": False,
        "utility_signal": utility_signal,
        "mechanism_blocked": mechanism_blocked,
        "compact_pass": bool(compact_pass),
        "compact_full": bool(compact_full),
        "compact_backend": "repo_pytest",
        "task_ratios": task_rows,
        "key_diagnostics": {
            "current_divided_by_native_lorenz": diagnostics.get("current_divided_by_native"),
            "random_projection_divided_by_native_lorenz": diagnostics.get("random_projection_divided_by_native"),
            "nonlinear_lag_divided_by_native_lorenz": diagnostics.get("nonlinear_lag_divided_by_native"),
            "target_shuffle_divided_by_native": diagnostics.get("target_shuffle_divided_by_native"),
            "time_shuffle_divided_by_native": diagnostics.get("time_shuffle_divided_by_native"),
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=TIER)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--compact-mode", choices=["skip", "pytest"], default="pytest")
    return parser


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    q_payload = read_json(TIER7_7Q_RESULTS)
    r_payload = read_json(TIER7_7R_RESULTS)
    compact_child = run_compact_guardrail(args, output_dir)
    decision = classify(q_payload, r_payload, compact_child, args)
    criteria = [
        criterion("Tier 7.7q exists", str(TIER7_7Q_RESULTS), "exists", TIER7_7Q_RESULTS.exists()),
        criterion("Tier 7.7q passed", q_payload.get("status"), "== pass", q_payload.get("status") == "pass"),
        criterion("Tier 7.7r exists", str(TIER7_7R_RESULTS), "exists", TIER7_7R_RESULTS.exists()),
        criterion("Tier 7.7r passed", r_payload.get("status"), "== pass", r_payload.get("status") == "pass"),
        criterion("utility signal present", decision["utility_signal"], "true", decision["utility_signal"] is True),
        criterion("mechanism promotion blocked", decision["mechanism_blocked"], "true", decision["mechanism_blocked"] is True),
        criterion("compact regression ran", compact_child is not None, "true", compact_child is not None),
        criterion("compact regression passed", decision["compact_pass"], "true", decision["compact_pass"] is True),
        criterion("compact regression full", decision["compact_full"], "true", decision["compact_full"] is True),
        criterion("bounded utility promoted", decision["utility_promoted"], "true", decision["utility_promoted"] is True),
        criterion("mechanism not promoted", decision["mechanism_promoted"], "false", decision["mechanism_promoted"] is False),
        criterion("baseline freeze not authorized", decision["baseline_freeze_authorized"], "false", decision["baseline_freeze_authorized"] is False),
        criterion("hardware transfer not authorized", decision["hardware_transfer_authorized"], "false", decision["hardware_transfer_authorized"] is False),
    ]
    passed = sum(1 for row in criteria if row["passed"])
    status = "pass" if passed == len(criteria) else "fail"
    claim_boundary = (
        "Tier 7.7s may promote the temporal-basis interface only as bounded "
        "engineering utility. It does not promote a CRA-specific mechanism, "
        "freeze a new core baseline, claim external-baseline superiority, "
        "authorize hardware/native transfer, or support broad public usefulness."
    )
    payload = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "status": status,
        "criteria": criteria,
        "criteria_passed": passed,
        "criteria_total": len(criteria),
        "output_dir": str(output_dir),
        "decision": decision,
        "compact_child": compact_child.to_dict() if compact_child else None,
        "claim_boundary": claim_boundary,
        "nonclaims": [
            "not a CRA-specific mechanism promotion",
            "not a core baseline freeze",
            "not hardware/native transfer",
            "not external-baseline superiority",
            "not broad public usefulness",
            "not language, AGI, or ASI evidence",
        ],
    }
    prefix = "tier7_7s"
    write_json(output_dir / f"{prefix}_results.json", payload)
    write_csv(output_dir / f"{prefix}_summary.csv", criteria)
    write_csv(output_dir / f"{prefix}_task_ratios.csv", decision["task_ratios"])
    write_csv(output_dir / f"{prefix}_utility_decision.csv", [decision])
    write_json(output_dir / f"{prefix}_compact_child.json", payload["compact_child"])
    (output_dir / f"{prefix}_claim_boundary.md").write_text(claim_boundary + "\n", encoding="utf-8")
    report = [
        "# Tier 7.7s Bounded Temporal-Basis Utility Promotion/Regression Gate",
        "",
        f"- Generated: `{payload['generated_at_utc']}`",
        f"- Status: **{status.upper()}**",
        f"- Criteria: `{passed}/{len(criteria)}`",
        f"- Outcome: `{decision['outcome']}`",
        f"- Recommendation: {decision['recommendation']}",
        "",
        "## Boundary",
        "",
        claim_boundary,
        "",
        "## Diagnostics",
        "",
    ]
    for key, value in decision["key_diagnostics"].items():
        report.append(f"- {key}: `{value}`")
    report.extend(["", "## Nonclaims", ""])
    report.extend(f"- {item}" for item in payload["nonclaims"])
    report.append("")
    (output_dir / f"{prefix}_report.md").write_text("\n".join(report), encoding="utf-8")
    manifest = {
        "tier": TIER,
        "status": status,
        "generated_at_utc": payload["generated_at_utc"],
        "output_dir": str(output_dir),
        "results_json": str(output_dir / f"{prefix}_results.json"),
        "report_md": str(output_dir / f"{prefix}_report.md"),
        "summary_csv": str(output_dir / f"{prefix}_summary.csv"),
        "outcome": decision["outcome"],
    }
    write_json(output_dir / f"{prefix}_latest_manifest.json", manifest)
    write_json(CONTROLLED / f"{prefix}_latest_manifest.json", manifest)
    return payload


def main() -> int:
    args = build_parser().parse_args()
    payload = run(args)
    print(json.dumps({"status": payload["status"], "criteria": f"{payload['criteria_passed']}/{payload['criteria_total']}", "outcome": payload["decision"]["outcome"], "output_dir": payload["output_dir"]}, indent=2, sort_keys=True))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
