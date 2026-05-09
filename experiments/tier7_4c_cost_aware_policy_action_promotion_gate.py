#!/usr/bin/env python3
"""Tier 7.4c - cost-aware policy/action promotion + compact regression.

Tier 7.4b produced candidate local evidence for cost-aware action selection.
This gate asks the promotion question before any baseline changes:

Can the locked Tier 7.4b candidate survive compact regression and preserve its
utility, sham-separation, no-action, and leakage boundaries?

This runner can authorize a v2.4 software freeze, but it does not perform
hardware/native transfer.
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
BASELINES = ROOT / "baselines"
TIER = "Tier 7.4c - Cost-Aware Policy/Action Promotion + Compact Regression"
RUNNER_REVISION = "tier7_4c_cost_aware_policy_action_promotion_gate_20260509_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_4c_20260509_cost_aware_policy_action_promotion_gate"
TIER7_4B_RESULTS = CONTROLLED / "tier7_4b_20260509_cost_aware_policy_action_local_diagnostic" / "tier7_4b_results.json"
V23_BASELINE = BASELINES / "CRA_EVIDENCE_BASELINE_v2.3.json"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from tier7_1g_nab_source_data_scoring_preflight import criterion, sha256_file, write_csv, write_json  # noqa: E402


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


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def manifest_status(manifest_path: Path) -> tuple[str, str]:
    if not manifest_path.exists():
        return "fail", f"missing manifest: {manifest_path}"
    try:
        manifest = read_json(manifest_path)
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
        runtime_seconds=float(runtime_seconds),
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
        purpose="rerun compact v2.x guardrails before any cost-aware policy/action freeze",
        command=command,
        output_dir=compact_dir,
        manifest_name="tier5_18c_results.json",
    )


def support_from_7_4b(payload: dict[str, Any]) -> dict[str, Any]:
    decision = payload["decision"]
    model_summary = {row["model"]: row for row in payload["model_summary"]}
    v23 = model_summary["v2_3_cost_aware_policy"]
    best_external = decision["best_external_baseline"]
    best_sham = decision["best_sham_or_ablation"]
    return {
        "tier7_4b_status": payload.get("status"),
        "tier7_4b_outcome": decision["outcome"],
        "best_non_oracle_model": decision["best_non_oracle_model"],
        "best_external_baseline": best_external,
        "best_sham_or_ablation": best_sham,
        "v2_3_expected_utility_mean": float(v23["expected_utility_mean"]),
        "best_external_expected_utility_mean": float(decision["best_external_expected_utility_mean"]),
        "best_sham_expected_utility_mean": float(decision["best_sham_expected_utility_mean"]),
        "utility_margin_vs_external": float(v23["expected_utility_mean"]) - float(decision["best_external_expected_utility_mean"]),
        "utility_margin_vs_sham": float(v23["expected_utility_mean"]) - float(decision["best_sham_expected_utility_mean"]),
        "task_family_wins_vs_external": int(decision["task_family_wins_vs_external"]),
        "action_rate_mean": float(v23["action_rate_mean"]),
        "window_recall_mean": float(v23["window_recall_mean"]),
        "false_positive_cost_per_1000_mean": float(v23["false_positive_cost_per_1000_mean"]),
        "freeze_authorized_by_7_4b": bool(decision["freeze_authorized"]),
        "hardware_transfer_authorized_by_7_4b": bool(decision["hardware_transfer_authorized"]),
    }


def classify(support: dict[str, Any], compact_child: ChildRun | None, args: argparse.Namespace) -> dict[str, Any]:
    compact_pass = compact_child is not None and compact_child.passed
    compact_full = args.compact_mode == "full"
    compact_freeze_backend = args.compact_backend in {"nest", "brian2"}
    policy_support = (
        support["tier7_4b_status"] == "pass"
        and support["tier7_4b_outcome"] == "cost_aware_policy_candidate_requires_regression"
        and support["best_non_oracle_model"] == "v2_3_cost_aware_policy"
        and support["utility_margin_vs_external"] > 0.0
        and support["utility_margin_vs_sham"] > 0.0
        and support["task_family_wins_vs_external"] >= 2
        and 0.01 <= support["action_rate_mean"] <= 0.35
        and support["window_recall_mean"] >= 0.65
        and not support["freeze_authorized_by_7_4b"]
        and not support["hardware_transfer_authorized_by_7_4b"]
    )
    freeze_authorized = bool(policy_support and compact_pass and compact_full and compact_freeze_backend)
    if freeze_authorized:
        outcome = "cost_aware_policy_ready_for_v2_4_freeze"
        recommendation = "Freeze v2.4 as a software cost-aware policy/action baseline; do not authorize hardware transfer without a separate transfer contract."
    elif policy_support and compact_pass:
        outcome = "cost_aware_policy_supported_pending_full_compact"
        recommendation = "Run full non-mock compact regression before any v2.4 freeze."
    elif policy_support:
        outcome = "cost_aware_policy_supported_compact_missing"
        recommendation = "Candidate remains supported, but compact regression did not pass; no freeze."
    else:
        outcome = "cost_aware_policy_not_promoted"
        recommendation = "Do not freeze; repair policy/action local diagnostic or narrow the claim."
    return {
        "outcome": outcome,
        "recommendation": recommendation,
        "freeze_authorized": freeze_authorized,
        "hardware_transfer_authorized": False,
        "policy_support": bool(policy_support),
        "compact_pass": bool(compact_pass),
        "compact_full": bool(compact_full),
        "compact_backend": args.compact_backend,
        "compact_freeze_backend": bool(compact_freeze_backend),
        "promotable_claim": (
            "Cost-aware policy/action selection improves local expected utility under asymmetric action costs while preserving sham/ablation separation."
            if freeze_authorized
            else ""
        ),
        "nonclaims": [
            "not public usefulness proof",
            "not broad anomaly benchmark superiority",
            "not reinforcement learning solved",
            "not long-horizon planning",
            "not hardware/native transfer",
            "not language",
            "not AGI",
            "not ASI",
        ],
    }


def make_manifest(output_dir: Path, artifacts: dict[str, Path], status: str) -> dict[str, Any]:
    return {
        "tier": TIER,
        "status": status,
        "generated_at_utc": utc_now(),
        "runner_revision": RUNNER_REVISION,
        "output_dir": output_dir,
        "artifacts": [
            {"name": name, "path": path, "sha256": sha256_file(path), "bytes": path.stat().st_size}
            for name, path in sorted(artifacts.items())
        ],
    }


def write_report(output_dir: Path, payload: dict[str, Any]) -> None:
    s = payload["support"]
    c = payload["classification"]
    lines = [
        "# Tier 7.4c Cost-Aware Policy/Action Promotion Gate",
        "",
        f"- Generated: `{payload['generated_at_utc']}`",
        f"- Status: **{payload['status'].upper()}**",
        f"- Criteria: `{payload['criteria_passed']}/{payload['criteria_total']}`",
        f"- Outcome: `{c['outcome']}`",
        f"- Freeze authorized: `{c['freeze_authorized']}`",
        f"- Hardware transfer authorized: `{c['hardware_transfer_authorized']}`",
        "",
        "## Claim Boundary",
        "",
        payload["claim_boundary"],
        "",
        "## Locked Tier 7.4b Support",
        "",
        f"- v2.3 expected utility mean: `{s['v2_3_expected_utility_mean']}`",
        f"- best external baseline: `{s['best_external_baseline']}` at `{s['best_external_expected_utility_mean']}`",
        f"- best sham/ablation: `{s['best_sham_or_ablation']}` at `{s['best_sham_expected_utility_mean']}`",
        f"- utility margin vs external: `{s['utility_margin_vs_external']}`",
        f"- utility margin vs sham: `{s['utility_margin_vs_sham']}`",
        f"- task-family wins vs external: `{s['task_family_wins_vs_external']}`",
        f"- action rate mean: `{s['action_rate_mean']}`",
        f"- window recall mean: `{s['window_recall_mean']}`",
        "",
        "## Compact Guardrail",
        "",
        f"- compact mode: `{payload['compact_mode']}`",
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
    output_dir.joinpath("tier7_4c_report.md").write_text("\n".join(lines), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=TIER)
    parser.add_argument("--compact-mode", choices=["skip", "smoke", "full"], default="full")
    parser.add_argument("--compact-backend", choices=["mock", "nest", "brian2"], default="nest")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Output directory")
    return parser


def run(args: argparse.Namespace) -> dict[str, Any]:
    started = time.perf_counter()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    prior = read_json(TIER7_4B_RESULTS) if TIER7_4B_RESULTS.exists() else {}
    support = support_from_7_4b(prior) if prior else {}
    compact_child = run_compact_guardrail(args, output_dir)
    classification = classify(support, compact_child, args) if support else {
        "outcome": "cost_aware_policy_not_promoted",
        "recommendation": "missing Tier 7.4b source result",
        "freeze_authorized": False,
        "hardware_transfer_authorized": False,
        "policy_support": False,
        "compact_pass": bool(compact_child and compact_child.passed),
        "compact_full": args.compact_mode == "full",
        "compact_backend": args.compact_backend,
        "compact_freeze_backend": args.compact_backend in {"nest", "brian2"},
        "promotable_claim": "",
        "nonclaims": ["missing source result"],
    }
    criteria = [
        criterion("runner revision current", RUNNER_REVISION, "expected current source", RUNNER_REVISION.endswith("_0001")),
        criterion("Tier 7.4b exists", str(TIER7_4B_RESULTS), "exists", TIER7_4B_RESULTS.exists()),
        criterion("v2.3 baseline exists", str(V23_BASELINE), "exists", V23_BASELINE.exists()),
        criterion("Tier 7.4b passed", support.get("tier7_4b_status"), "== pass", support.get("tier7_4b_status") == "pass"),
        criterion("Tier 7.4b candidate outcome", support.get("tier7_4b_outcome"), "== cost_aware_policy_candidate_requires_regression", support.get("tier7_4b_outcome") == "cost_aware_policy_candidate_requires_regression"),
        criterion("v2.3 policy best non-oracle", support.get("best_non_oracle_model"), "== v2_3_cost_aware_policy", support.get("best_non_oracle_model") == "v2_3_cost_aware_policy"),
        criterion("utility margin vs external positive", support.get("utility_margin_vs_external"), "> 0", support.get("utility_margin_vs_external", 0.0) > 0.0),
        criterion("utility margin vs sham positive", support.get("utility_margin_vs_sham"), "> 0", support.get("utility_margin_vs_sham", 0.0) > 0.0),
        criterion("task-family wins vs external", support.get("task_family_wins_vs_external"), ">= 2", support.get("task_family_wins_vs_external", 0) >= 2),
        criterion("no-action collapse blocked", {"action_rate": support.get("action_rate_mean"), "window_recall": support.get("window_recall_mean")}, "0.01 <= action_rate <= 0.35 and recall >= 0.65", 0.01 <= support.get("action_rate_mean", 0.0) <= 0.35 and support.get("window_recall_mean", 0.0) >= 0.65),
        criterion("source gate did not already freeze", support.get("freeze_authorized_by_7_4b"), "== false", support.get("freeze_authorized_by_7_4b") is False),
        criterion("source gate did not authorize hardware transfer", support.get("hardware_transfer_authorized_by_7_4b"), "== false", support.get("hardware_transfer_authorized_by_7_4b") is False),
        criterion("compact regression guardrail pass", classification["compact_pass"], "== true", bool(classification["compact_pass"])),
        criterion("full compact regression for freeze", classification["compact_full"], "== true for freeze authorization", not classification["freeze_authorized"] or bool(classification["compact_full"])),
        criterion("freeze compact backend is non-mock", classification["compact_freeze_backend"], "nest or brian2 required for freeze", not classification["freeze_authorized"] or bool(classification["compact_freeze_backend"])),
        criterion("hardware transfer remains blocked", classification["hardware_transfer_authorized"], "== false", classification["hardware_transfer_authorized"] is False),
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
        "failed_criteria": [item for item in criteria if not item["passed"]],
        "support": support,
        "classification": classification,
        "compact_child": compact_child.to_dict() if compact_child else None,
        "source_results": {
            "tier7_4b": str(TIER7_4B_RESULTS),
            "v2_3_baseline": str(V23_BASELINE),
        },
        "claim_boundary": (
            "Tier 7.4c is a software-only promotion/regression gate for the "
            "cost-aware policy/action candidate. It may authorize a v2.4 "
            "software freeze, but it is not public usefulness proof, not "
            "hardware/native transfer, not planning, and not AGI/ASI evidence."
        ),
    }
    paths = {
        "results_json": output_dir / "tier7_4c_results.json",
        "report_md": output_dir / "tier7_4c_report.md",
        "summary_csv": output_dir / "tier7_4c_summary.csv",
        "promotion_json": output_dir / "tier7_4c_promotion.json",
        "promotion_csv": output_dir / "tier7_4c_promotion.csv",
        "compact_child_json": output_dir / "tier7_4c_compact_child.json",
    }
    write_json(paths["results_json"], payload)
    write_csv(paths["summary_csv"], [{**support, **classification, "status": status}])
    write_json(paths["promotion_json"], classification)
    write_csv(paths["promotion_csv"], [classification])
    write_json(paths["compact_child_json"], compact_child.to_dict() if compact_child else {"status": "skipped"})
    write_report(output_dir, payload)
    manifest = make_manifest(output_dir, paths, status)
    manifest_path = output_dir / "tier7_4c_latest_manifest.json"
    write_json(manifest_path, manifest)
    paths["latest_manifest"] = manifest_path
    latest = CONTROLLED / "tier7_4c_latest_manifest.json"
    write_json(latest, manifest)
    return payload


def main() -> None:
    args = build_parser().parse_args()
    result = run(args)
    print(
        json.dumps(
            json_safe(
                {
                    "tier": TIER,
                    "status": result["status"],
                    "criteria": f"{result['criteria_passed']}/{result['criteria_total']}",
                    "classification": result["classification"]["outcome"],
                    "freeze_authorized": result["classification"]["freeze_authorized"],
                    "hardware_transfer_authorized": result["classification"]["hardware_transfer_authorized"],
                    "output_dir": result["output_dir"],
                }
            ),
            indent=2,
            sort_keys=True,
        )
    )
    if result["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
