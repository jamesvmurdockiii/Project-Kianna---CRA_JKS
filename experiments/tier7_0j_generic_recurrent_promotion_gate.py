#!/usr/bin/env python3
"""Tier 7.0j - Generic bounded recurrent-state promotion gate.

Tier 7.0h showed that bounded recurrent state improves the public
Mackey-Glass/Lorenz/NARMA10 scoreboard versus v2.2. Tier 7.0i then narrowed the
claim: topology-specific recurrence is not supported, because topology shams
matched or beat the structured candidate. This gate asks the remaining
promotable question:

Can the narrower generic bounded recurrent continuous-state interface earn a
software baseline freeze, without claiming topology-specific recurrence?
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
TIER = "Tier 7.0j - Generic Bounded Recurrent-State Promotion / Compact Regression"
RUNNER_REVISION = "tier7_0j_generic_recurrent_promotion_gate_20260508_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_0j_20260508_generic_recurrent_promotion_gate"
TIER7_0H_RESULTS = CONTROLLED / "tier7_0h_20260508_bounded_recurrent_interface_gate" / "tier7_0h_results.json"
TIER7_0I_RESULTS = CONTROLLED / "tier7_0i_20260508_recurrence_topology_specificity_gate" / "tier7_0i_results.json"
V22_BASELINE = ROOT / "baselines" / "CRA_EVIDENCE_BASELINE_v2.2.json"


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
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def criterion(name: str, value: Any, rule: str, passed: bool, note: str = "") -> dict[str, Any]:
    return {"name": name, "value": json_safe(value), "rule": rule, "passed": bool(passed), "note": note}


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
    compact_dir = output_dir / f"compact_regression_{args.compact_mode}_{args.compact_backend}"
    command = [
        sys.executable,
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
        name=f"compact_regression_{args.compact_mode}_{args.compact_backend}",
        purpose="rerun the promoted software compact regression stack before any v2.3 freeze",
        command=command,
        output_dir=compact_dir,
        manifest_name="tier5_18c_results.json",
    )


def extract_support(h: dict[str, Any], i: dict[str, Any]) -> dict[str, Any]:
    h_class = h["classification"]
    i_class = i["classification"]
    h_longest = str(h_class["longest_length"])
    i_longest = str(i_class["longest_length"])
    h8000 = h_class["by_length"][h_longest]
    i8000 = i_class["by_length"][i_longest]
    return {
        "locked_length": int(h_class["longest_length"]),
        "tier7_0h_status": h.get("status"),
        "tier7_0i_status": i.get("status"),
        "generic_candidate_mse": float(h8000["candidate_mse"]),
        "structured_candidate_mse": float(i8000["structured_mse"]),
        "v2_2_mse": float(h8000["v2_2_mse"]),
        "esn_mse": float(h8000["esn_mse"]),
        "lag_mse": float(h8000["lag_mse"]),
        "reservoir_mse": float(h8000["reservoir_mse"]),
        "generic_margin_vs_v2_2": float(h8000["margin_vs_v2_2"]),
        "generic_margin_vs_lag": float(h8000["margin_vs_lag"]),
        "generic_margin_vs_reservoir": float(h8000["margin_vs_reservoir"]),
        "generic_divided_by_esn": float(h8000["candidate_divided_by_esn"]),
        "v2_2_divided_by_esn": float(h8000["v2_2_divided_by_esn"]),
        "structured_margin_vs_generic": float(i8000["structured_margin_vs_generic"]),
        "tier7_0h_destructive_controls_separated": bool(h_class["destructive_controls_separated"]),
        "tier7_0i_destructive_controls_separated": bool(i_class["destructive_controls_separated"]),
        "tier7_0h_recurrence_controls_separated": bool(h_class["recurrence_controls_separated"]),
        "tier7_0i_topology_controls_separated": bool(i_class["topology_controls_separated"]),
        "tier7_0i_promotion_recommended": bool(i_class["promotion_recommended"]),
    }


def classify(support: dict[str, Any], compact_child: ChildRun | None, args: argparse.Namespace) -> dict[str, Any]:
    compact_pass = compact_child is not None and compact_child.passed
    compact_full = args.compact_mode == "full"
    compact_freeze_backend = args.compact_backend in {"nest", "brian2"}
    generic_public_support = (
        support["tier7_0h_status"] == "pass"
        and support["tier7_0i_status"] == "pass"
        and support["locked_length"] == 8000
        and support["generic_margin_vs_v2_2"] >= args.min_margin_vs_v2_2
        and support["generic_margin_vs_lag"] > 1.0
        and support["generic_margin_vs_reservoir"] > 1.0
        and support["generic_divided_by_esn"] < support["v2_2_divided_by_esn"]
        and support["tier7_0h_destructive_controls_separated"]
        and support["tier7_0i_destructive_controls_separated"]
    )
    topology_nonclaim_preserved = (
        not support["tier7_0h_recurrence_controls_separated"]
        and not support["tier7_0i_topology_controls_separated"]
        and not support["tier7_0i_promotion_recommended"]
    )
    freeze_authorized = bool(
        generic_public_support
        and topology_nonclaim_preserved
        and compact_pass
        and compact_full
        and compact_freeze_backend
    )
    if freeze_authorized:
        outcome = "generic_bounded_recurrent_state_ready_for_v2_3_freeze"
        recommendation = "Freeze v2.3 as a generic bounded recurrent-state software baseline; preserve topology and ESN nonclaims."
    elif generic_public_support and topology_nonclaim_preserved and compact_pass:
        outcome = "generic_recurrent_supported_pending_full_compact"
        recommendation = "Run full non-mock compact regression before freezing v2.3."
    elif generic_public_support and topology_nonclaim_preserved:
        outcome = "generic_recurrent_supported_compact_missing"
        recommendation = "Generic recurrent state remains supported, but no freeze without compact regression."
    else:
        outcome = "generic_recurrent_not_promoted"
        recommendation = "Do not freeze; repair or narrow before continuing."
    return {
        "outcome": outcome,
        "recommendation": recommendation,
        "freeze_authorized": freeze_authorized,
        "generic_public_support": bool(generic_public_support),
        "topology_nonclaim_preserved": bool(topology_nonclaim_preserved),
        "compact_pass": bool(compact_pass),
        "compact_full": bool(compact_full),
        "compact_backend": args.compact_backend,
        "compact_freeze_backend": bool(compact_freeze_backend),
        "promotable_claim": (
            "Generic bounded recurrent continuous-state interface improves the locked 8000-step "
            "Mackey-Glass/Lorenz/NARMA10 public scoreboard versus v2.2."
            if freeze_authorized
            else ""
        ),
        "nonclaims": [
            "not topology-specific recurrence",
            "not ESN superiority",
            "not hardware evidence",
            "not native on-chip recurrence",
            "not language",
            "not planning",
            "not AGI",
            "not ASI",
        ],
    }


def write_report(output_dir: Path, payload: dict[str, Any]) -> None:
    s = payload["support"]
    c = payload["classification"]
    lines = [
        "# Tier 7.0j Generic Bounded Recurrent-State Promotion Gate",
        "",
        f"- Generated: `{payload['generated_at_utc']}`",
        f"- Status: **{payload['status'].upper()}**",
        f"- Outcome: `{c['outcome']}`",
        f"- Freeze authorized: `{c['freeze_authorized']}`",
        "",
        "## Claim Boundary",
        "",
        payload["claim_boundary"],
        "",
        "## Locked 8000-Step Public Scoreboard",
        "",
        "| Model | Aggregate geomean MSE |",
        "| --- | ---: |",
        f"| ESN | {s['esn_mse']} |",
        f"| generic bounded recurrent candidate | {s['generic_candidate_mse']} |",
        f"| structured recurrence candidate | {s['structured_candidate_mse']} |",
        f"| v2.2 fading memory | {s['v2_2_mse']} |",
        f"| lag-only LMS | {s['lag_mse']} |",
        f"| random reservoir | {s['reservoir_mse']} |",
        "",
        "## Promotion Logic",
        "",
        f"- generic margin vs v2.2: `{s['generic_margin_vs_v2_2']}`",
        f"- generic margin vs lag-only: `{s['generic_margin_vs_lag']}`",
        f"- generic margin vs reservoir: `{s['generic_margin_vs_reservoir']}`",
        f"- v2.2 / ESN ratio: `{s['v2_2_divided_by_esn']}`",
        f"- generic / ESN ratio: `{s['generic_divided_by_esn']}`",
        f"- topology nonclaim preserved: `{c['topology_nonclaim_preserved']}`",
        "",
        "## Compact Guardrail",
        "",
        f"- compact mode: `{c['compact_full'] and 'full' or payload['compact_mode']}`",
        f"- compact backend: `{c['compact_backend']}`",
        f"- compact pass: `{c['compact_pass']}`",
        "",
        "## Criteria",
        "",
        "| Criterion | Value | Rule | Pass |",
        "| --- | --- | --- | --- |",
    ]
    for item in payload["criteria"]:
        lines.append(f"| {item['name']} | `{item['value']}` | {item['rule']} | {'yes' if item['passed'] else 'no'} |")
    lines.extend(["", "## Nonclaims", ""])
    for item in c["nonclaims"]:
        lines.append(f"- {item}")
    lines.append("")
    (output_dir / "tier7_0j_report.md").write_text("\n".join(lines), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=TIER)
    parser.add_argument("--compact-mode", choices=["skip", "smoke", "full"], default="smoke")
    parser.add_argument("--compact-backend", choices=["mock", "nest", "brian2"], default="nest")
    parser.add_argument("--min-margin-vs-v2-2", type=float, default=1.25)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser


def run(args: argparse.Namespace) -> dict[str, Any]:
    started = time.perf_counter()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    h = load_json(TIER7_0H_RESULTS)
    i = load_json(TIER7_0I_RESULTS)
    support = extract_support(h, i)
    compact_child = run_compact_guardrail(args, output_dir)
    classification = classify(support, compact_child, args)
    criteria = [
        criterion("runner revision current", RUNNER_REVISION, "expected current source", RUNNER_REVISION.endswith("_0001")),
        criterion("v2.2 baseline artifact exists", str(V22_BASELINE), "exists", V22_BASELINE.exists()),
        criterion("Tier 7.0h source result pass", support["tier7_0h_status"], "== pass", support["tier7_0h_status"] == "pass"),
        criterion("Tier 7.0i source result pass", support["tier7_0i_status"], "== pass", support["tier7_0i_status"] == "pass"),
        criterion("locked public length", support["locked_length"], "== 8000", support["locked_length"] == 8000),
        criterion("generic improves v2.2", support["generic_margin_vs_v2_2"], f">= {args.min_margin_vs_v2_2}", support["generic_margin_vs_v2_2"] >= args.min_margin_vs_v2_2),
        criterion("generic beats lag-only online control", support["generic_margin_vs_lag"], "> 1.0", support["generic_margin_vs_lag"] > 1.0),
        criterion("generic beats random reservoir online control", support["generic_margin_vs_reservoir"], "> 1.0", support["generic_margin_vs_reservoir"] > 1.0),
        criterion("generic narrows ESN gap", support["generic_divided_by_esn"], "< v2.2/ESN", support["generic_divided_by_esn"] < support["v2_2_divided_by_esn"]),
        criterion("destructive controls separated", [support["tier7_0h_destructive_controls_separated"], support["tier7_0i_destructive_controls_separated"]], "both true", support["tier7_0h_destructive_controls_separated"] and support["tier7_0i_destructive_controls_separated"]),
        criterion("topology nonclaim preserved", classification["topology_nonclaim_preserved"], "== true", bool(classification["topology_nonclaim_preserved"])),
        criterion("compact regression guardrail pass", classification["compact_pass"], "== true unless compact-mode skip", args.compact_mode == "skip" or bool(classification["compact_pass"])),
        criterion("full compact regression for freeze", classification["compact_full"], "== true for freeze authorization", not classification["freeze_authorized"] or bool(classification["compact_full"])),
        criterion("freeze compact backend is non-mock", classification["compact_freeze_backend"], "nest or brian2 required for freeze", not classification["freeze_authorized"] or bool(classification["compact_freeze_backend"])),
    ]
    status = "pass" if all(item["passed"] for item in criteria) else "fail"
    payload = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "status": status,
        "failure_reason": "" if status == "pass" else "Failed criteria: " + ", ".join(item["name"] for item in criteria if not item["passed"]),
        "output_dir": str(output_dir),
        "runtime_seconds": time.perf_counter() - started,
        "compact_mode": args.compact_mode,
        "criteria": criteria,
        "criteria_passed": sum(bool(item["passed"]) for item in criteria),
        "criteria_total": len(criteria),
        "support": support,
        "classification": classification,
        "compact_child": compact_child.to_dict() if compact_child else None,
        "source_results": {
            "tier7_0h": str(TIER7_0H_RESULTS),
            "tier7_0i": str(TIER7_0I_RESULTS),
            "v2_2_baseline": str(V22_BASELINE),
        },
        "fairness_contract": {
            "public_tasks": ["mackey_glass", "lorenz", "narma10"],
            "locked_length": 8000,
            "seeds": [42, 43, 44],
            "promotion_rule": "narrow generic recurrent-state claim only; topology-specific recurrence remains a nonclaim",
            "compact_regression": {
                "mode": args.compact_mode,
                "backend": args.compact_backend,
            },
        },
        "claim_boundary": (
            "Tier 7.0j is a software-only promotion/regression gate for a narrow "
            "generic bounded recurrent-state interface. It cannot claim topology-"
            "specific recurrence, ESN superiority, hardware transfer, native/on-chip "
            "recurrence, language, planning, AGI, or ASI."
        ),
    }
    write_json(output_dir / "tier7_0j_results.json", payload)
    write_json(output_dir / "tier7_0j_fairness_contract.json", payload["fairness_contract"])
    write_csv(output_dir / "tier7_0j_summary.csv", [{**support, **classification, "status": status}])
    write_report(output_dir, payload)
    write_json(
        CONTROLLED / "tier7_0j_latest_manifest.json",
        {
            "tier": TIER,
            "runner_revision": RUNNER_REVISION,
            "generated_at_utc": payload["generated_at_utc"],
            "status": payload["status"],
            "classification": payload["classification"]["outcome"],
            "freeze_authorized": payload["classification"]["freeze_authorized"],
            "manifest": str(output_dir / "tier7_0j_results.json"),
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
