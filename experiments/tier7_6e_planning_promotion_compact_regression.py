#!/usr/bin/env python3
"""Tier 7.6e - planning/subgoal-control promotion + compact regression.

Tier 7.6d repaired the Tier 7.6c feature-alignment blocker by hiding direct
raw keys and preserving the planning/subgoal-control signal under reduced,
aliased features. This gate asks the promotion question:

Can the reduced-feature planning mechanism be promoted into the host-side
software baseline line without breaking compact regression guardrails?

This is a software-only promotion gate. It can authorize a bounded v2.5
software freeze, but it does not authorize hardware/native transfer or a broad
planning claim.
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
TIER = "Tier 7.6e - Planning/Subgoal-Control Promotion + Compact Regression"
RUNNER_REVISION = "tier7_6e_planning_promotion_compact_regression_20260509_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_6e_20260509_planning_promotion_compact_regression"
TIER7_6D_RESULTS = CONTROLLED / "tier7_6d_20260509_reduced_feature_planning_generalization" / "tier7_6d_results.json"
V24_BASELINE = BASELINES / "CRA_EVIDENCE_BASELINE_v2.4.json"

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
        purpose="rerun the promoted software compact regression stack before any v2.5 planning freeze",
        command=command,
        output_dir=compact_dir,
        manifest_name="tier5_18c_results.json",
    )


def support_from_7_6d(payload: dict[str, Any]) -> dict[str, Any]:
    decision = payload["decision"]
    support_non_oracle = decision["support_vs_best_non_oracle"]
    support_sham = decision["support_vs_best_sham"]
    return {
        "tier7_6d_status": payload.get("status"),
        "tier7_6d_outcome": decision["outcome"],
        "reduced_feature_signal_authorized": bool(decision["reduced_feature_signal_authorized"]),
        "promotion_gate_authorized_by_7_6d": bool(decision["promotion_gate_authorized"]),
        "freeze_authorized_by_7_6d": bool(decision["freeze_authorized"]),
        "hardware_transfer_authorized_by_7_6d": bool(decision["hardware_transfer_authorized"]),
        "broad_planning_claim_authorized_by_7_6d": bool(decision["broad_planning_claim_authorized"]),
        "supported_family_count": int(decision["supported_family_count"]),
        "supported_families": list(decision["supported_families"]),
        "repaired_prior_weak_families_supported": bool(decision["repaired_prior_weak_families_supported"]),
        "candidate_return_mean": float(decision["candidate_return_mean"]),
        "candidate_success_rate": float(decision["candidate_success_rate"]),
        "best_non_oracle_model": str(decision["best_non_oracle_model"]),
        "best_non_oracle_return_mean": float(decision["best_non_oracle_return_mean"]),
        "best_sham_or_ablation": str(decision["best_sham_or_ablation"]),
        "best_sham_return_mean": float(decision["best_sham_return_mean"]),
        "return_margin_vs_best_non_oracle": float(decision["candidate_return_mean"]) - float(decision["best_non_oracle_return_mean"]),
        "return_margin_vs_best_sham": float(decision["candidate_return_mean"]) - float(decision["best_sham_return_mean"]),
        "ci_low_vs_best_non_oracle": float(support_non_oracle["return_delta_ci_low"]),
        "ci_low_vs_best_sham": float(support_sham["return_delta_ci_low"]),
        "effect_size_vs_best_non_oracle": float(support_non_oracle["return_effect_size"]),
        "effect_size_vs_best_sham": float(support_sham["return_effect_size"]),
    }


def classify(support: dict[str, Any], compact_child: ChildRun | None, args: argparse.Namespace) -> dict[str, Any]:
    compact_pass = compact_child is not None and compact_child.passed
    compact_full = args.compact_mode == "full"
    compact_freeze_backend = args.compact_backend in {"nest", "brian2"}
    planning_support = (
        support["tier7_6d_status"] == "PASS"
        and support["tier7_6d_outcome"] == "reduced_feature_planning_signal_supported_requires_promotion_gate"
        and support["reduced_feature_signal_authorized"]
        and support["promotion_gate_authorized_by_7_6d"]
        and support["supported_family_count"] >= 4
        and support["repaired_prior_weak_families_supported"]
        and support["return_margin_vs_best_non_oracle"] > 0.0
        and support["return_margin_vs_best_sham"] > 0.0
        and support["ci_low_vs_best_non_oracle"] > 0.0
        and support["ci_low_vs_best_sham"] > 0.0
        and not support["freeze_authorized_by_7_6d"]
        and not support["hardware_transfer_authorized_by_7_6d"]
        and not support["broad_planning_claim_authorized_by_7_6d"]
    )
    freeze_authorized = bool(
        planning_support
        and compact_pass
        and compact_full
        and compact_freeze_backend
    )
    if freeze_authorized:
        outcome = "reduced_feature_planning_ready_for_v2_5_freeze"
        recommendation = "Freeze v2.5 as a bounded host-side software planning/subgoal-control baseline; keep hardware/native transfer blocked."
    elif planning_support and compact_pass:
        outcome = "reduced_feature_planning_supported_pending_full_compact"
        recommendation = "Run full non-mock compact regression before any v2.5 freeze."
    elif planning_support:
        outcome = "reduced_feature_planning_supported_compact_missing"
        recommendation = "Planning support remains, but no freeze without compact regression."
    else:
        outcome = "reduced_feature_planning_not_promoted"
        recommendation = "Do not freeze; repair reduced-feature planning or narrow the claim."
    return {
        "outcome": outcome,
        "recommendation": recommendation,
        "freeze_authorized": freeze_authorized,
        "hardware_transfer_authorized": False,
        "broad_planning_claim_authorized": False,
        "planning_support": bool(planning_support),
        "compact_pass": bool(compact_pass),
        "compact_full": bool(compact_full),
        "compact_backend": args.compact_backend,
        "compact_freeze_backend": bool(compact_freeze_backend),
        "promotable_claim": (
            "Reduced-feature planning/subgoal-control improves bounded local "
            "planning diagnostics under aliased context/route/memory features "
            "and survives compact regression."
            if freeze_authorized
            else ""
        ),
        "nonclaims": [
            "not public usefulness proof",
            "not broad planning or reasoning",
            "not language",
            "not hardware/native transfer",
            "not autonomous on-chip planning",
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


def make_claim_boundary(classification: dict[str, Any]) -> str:
    lines = [
        "# Tier 7.6e Claim Boundary",
        "",
        f"- Outcome: `{classification['outcome']}`",
        f"- Freeze authorized: `{classification['freeze_authorized']}`",
        f"- Hardware/native transfer authorized: `{classification['hardware_transfer_authorized']}`",
        f"- Broad planning claim authorized: `{classification['broad_planning_claim_authorized']}`",
        "",
        "## Authorized Claim",
        "",
    ]
    if classification["freeze_authorized"]:
        lines.append(classification["promotable_claim"])
    else:
        lines.append("No new planning/subgoal-control baseline is authorized by this run.")
    lines.extend(["", "## Nonclaims", ""])
    lines.extend(f"- {item}" for item in classification["nonclaims"])
    lines.append("")
    return "\n".join(lines)


def write_report(output_dir: Path, payload: dict[str, Any]) -> None:
    s = payload["support"]
    c = payload["classification"]
    lines = [
        "# Tier 7.6e Planning/Subgoal-Control Promotion Gate",
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
        "## Locked Tier 7.6d Support",
        "",
        f"- supported families: `{s['supported_family_count']}` / `5`",
        f"- supported family IDs: `{', '.join(s['supported_families'])}`",
        f"- candidate return mean: `{s['candidate_return_mean']}`",
        f"- best non-oracle baseline: `{s['best_non_oracle_model']}` at `{s['best_non_oracle_return_mean']}`",
        f"- best sham/ablation: `{s['best_sham_or_ablation']}` at `{s['best_sham_return_mean']}`",
        f"- CI low vs best non-oracle: `{s['ci_low_vs_best_non_oracle']}`",
        f"- CI low vs best sham: `{s['ci_low_vs_best_sham']}`",
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
    (output_dir / "tier7_6e_report.md").write_text("\n".join(lines), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=TIER)
    parser.add_argument("--compact-mode", choices=["skip", "smoke", "full"], default="full")
    parser.add_argument("--compact-backend", choices=["mock", "nest", "brian2"], default="nest")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser


def run(args: argparse.Namespace) -> dict[str, Any]:
    started = time.perf_counter()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    prior = read_json(TIER7_6D_RESULTS) if TIER7_6D_RESULTS.exists() else {}
    support = support_from_7_6d(prior) if prior else {}
    compact_child = run_compact_guardrail(args, output_dir)
    classification = classify(support, compact_child, args) if support else {
        "outcome": "reduced_feature_planning_not_promoted",
        "recommendation": "missing Tier 7.6d source result",
        "freeze_authorized": False,
        "hardware_transfer_authorized": False,
        "broad_planning_claim_authorized": False,
        "planning_support": False,
        "compact_pass": bool(compact_child and compact_child.passed),
        "compact_full": args.compact_mode == "full",
        "compact_backend": args.compact_backend,
        "compact_freeze_backend": args.compact_backend in {"nest", "brian2"},
        "promotable_claim": "",
        "nonclaims": ["missing source result"],
    }
    criteria = [
        criterion("runner revision current", RUNNER_REVISION, "expected current source", RUNNER_REVISION.endswith("_0001")),
        criterion("Tier 7.6d exists", str(TIER7_6D_RESULTS), "exists", TIER7_6D_RESULTS.exists()),
        criterion("v2.4 baseline exists", str(V24_BASELINE), "exists", V24_BASELINE.exists()),
        criterion("Tier 7.6d passed", support.get("tier7_6d_status"), "== PASS", support.get("tier7_6d_status") == "PASS"),
        criterion("Tier 7.6d candidate outcome", support.get("tier7_6d_outcome"), "== reduced_feature_planning_signal_supported_requires_promotion_gate", support.get("tier7_6d_outcome") == "reduced_feature_planning_signal_supported_requires_promotion_gate"),
        criterion("Tier 7.6d reduced-feature signal authorized", support.get("reduced_feature_signal_authorized"), "== true", support.get("reduced_feature_signal_authorized") is True),
        criterion("supported family count", support.get("supported_family_count"), ">= 4", support.get("supported_family_count", 0) >= 4),
        criterion("prior weak families repaired", support.get("repaired_prior_weak_families_supported"), "== true", support.get("repaired_prior_weak_families_supported") is True),
        criterion("return margin vs best non-oracle", support.get("return_margin_vs_best_non_oracle"), "> 0", support.get("return_margin_vs_best_non_oracle", 0.0) > 0.0),
        criterion("return CI low vs best non-oracle", support.get("ci_low_vs_best_non_oracle"), "> 0", support.get("ci_low_vs_best_non_oracle", 0.0) > 0.0),
        criterion("return margin vs best sham", support.get("return_margin_vs_best_sham"), "> 0", support.get("return_margin_vs_best_sham", 0.0) > 0.0),
        criterion("return CI low vs best sham", support.get("ci_low_vs_best_sham"), "> 0", support.get("ci_low_vs_best_sham", 0.0) > 0.0),
        criterion("source gate did not already freeze", support.get("freeze_authorized_by_7_6d"), "== false", support.get("freeze_authorized_by_7_6d") is False),
        criterion("source gate did not authorize hardware", support.get("hardware_transfer_authorized_by_7_6d"), "== false", support.get("hardware_transfer_authorized_by_7_6d") is False),
        criterion("source gate did not authorize broad planning", support.get("broad_planning_claim_authorized_by_7_6d"), "== false", support.get("broad_planning_claim_authorized_by_7_6d") is False),
        criterion("compact regression guardrail pass", classification["compact_pass"], "== true", bool(classification["compact_pass"])),
        criterion("full compact regression for freeze", classification["compact_full"], "== true for freeze authorization", not classification["freeze_authorized"] or bool(classification["compact_full"])),
        criterion("freeze compact backend is non-mock", classification["compact_freeze_backend"], "nest or brian2 required for freeze", not classification["freeze_authorized"] or bool(classification["compact_freeze_backend"])),
        criterion("hardware transfer remains blocked", classification["hardware_transfer_authorized"], "== false", classification["hardware_transfer_authorized"] is False),
        criterion("broad planning claim remains blocked", classification["broad_planning_claim_authorized"], "== false", classification["broad_planning_claim_authorized"] is False),
    ]
    status = "pass" if all(item["passed"] for item in criteria) else "fail"
    claim_boundary = make_claim_boundary(classification)
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
            "tier7_6d": str(TIER7_6D_RESULTS),
            "v2_4_baseline": str(V24_BASELINE),
        },
        "claim_boundary": claim_boundary,
    }
    artifacts = {
        "results_json": output_dir / "tier7_6e_results.json",
        "report_md": output_dir / "tier7_6e_report.md",
        "summary_csv": output_dir / "tier7_6e_summary.csv",
        "promotion_json": output_dir / "tier7_6e_promotion.json",
        "promotion_csv": output_dir / "tier7_6e_promotion.csv",
        "compact_child_json": output_dir / "tier7_6e_compact_child.json",
        "claim_boundary_md": output_dir / "tier7_6e_claim_boundary.md",
    }
    write_json(artifacts["results_json"], payload)
    write_csv(artifacts["summary_csv"], [{**support, **classification, "status": status}])
    write_json(artifacts["promotion_json"], classification)
    write_csv(artifacts["promotion_csv"], [classification])
    write_json(artifacts["compact_child_json"], compact_child.to_dict() if compact_child else {"status": "skipped"})
    artifacts["claim_boundary_md"].write_text(claim_boundary, encoding="utf-8")
    write_report(output_dir, payload)
    manifest = make_manifest(output_dir, artifacts, status)
    manifest_path = output_dir / "tier7_6e_latest_manifest.json"
    write_json(manifest_path, manifest)
    artifacts["latest_manifest"] = manifest_path
    latest = CONTROLLED / "tier7_6e_latest_manifest.json"
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
