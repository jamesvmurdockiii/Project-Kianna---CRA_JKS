#!/usr/bin/env python3
"""Tier 4.32h native-scale evidence closeout / baseline decision.

This gate freezes the current native-scale SpiNNaker substrate only if the
completed Tier 4.32 evidence bundle is internally consistent. It deliberately
does not run hardware. The point is to stop broad native migration after the
MCPL/native-scale path is proven enough, then pivot back to software usefulness
benchmarks and real-task baselines.
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"
BASELINES = ROOT / "baselines"

TIER = "Tier 4.32h - Native-Scale Evidence Closeout / Baseline Decision"
RUNNER_REVISION = "tier4_32h_native_scale_evidence_closeout_20260508_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier4_32h_20260508_native_scale_evidence_closeout"
LATEST_MANIFEST = CONTROLLED / "tier4_32h_latest_manifest.json"
BASELINE_ID = "CRA_NATIVE_SCALE_BASELINE_v0.5"
BASELINE_JSON = BASELINES / f"{BASELINE_ID}.json"
BASELINE_MD = BASELINES / f"{BASELINE_ID}.md"
BASELINE_SNAPSHOT = BASELINES / f"{BASELINE_ID}_STUDY_REGISTRY.snapshot.json"
REGISTRY_PATH = CONTROLLED / "STUDY_REGISTRY.json"

CLAIM_BOUNDARY = (
    "Tier 4.32h is a local evidence closeout and baseline decision over already "
    "returned native-scale hardware evidence. It is not a new SpiNNaker run, "
    "not speedup evidence, not benchmark evidence, not real-task usefulness "
    "evidence, not true two-partition learning, not lifecycle scaling, not "
    "multi-shard learning, and not AGI/ASI evidence."
)

STRONGEST_CLAIM = (
    "CRA has a bounded native-scale SpiNNaker substrate baseline: replicated "
    "single-chip MCPL stress, two-chip MCPL communication/readback, a two-chip "
    "learning-bearing micro-task, and two-chip lifecycle traffic/resource "
    "counters have all passed canonical evidence gates with preserved returned "
    "artifacts, zero synthetic fallback, and explicit claim boundaries."
)

FREEZE_RULE = (
    "Freeze only because Tier 4.32a replicated single-chip stress, Tier 4.32d "
    "two-chip communication, Tier 4.32e two-chip learning micro-task, and "
    "Tier 4.32g two-chip lifecycle traffic/resource evidence all passed after "
    "ingest. This freezes the native-scale substrate boundary, not usefulness."
)

CLAIM_BOUNDARIES = [
    "Native-scale substrate baseline only; not a software capability baseline.",
    "Not speedup evidence; wall-clock efficiency remains separately measurable.",
    "Not benchmark or real-task usefulness evidence.",
    "Not true two-partition learning or multi-shard learning.",
    "Not lifecycle scaling or autonomous organism ecology.",
    "Not proof that every v2.2 software mechanism is fully chip-native.",
    "Not language, planning, AGI, or ASI evidence.",
    "Hardware/native work should pause here except for targeted transfer of mechanisms that win software usefulness gates.",
]

NEXT_STEPS = [
    "Stop broad native migration after v0.5 freeze.",
    "Run Tier 6.2 hard synthetic usefulness suite in software with strong baselines.",
    "Run Tier 7.1 real-ish adapter suite, Tier 7.2 held-out task challenge, and Tier 7.3 real-data tasks before more broad porting.",
    "Only port winning tasks/mechanisms back to SpiNNaker/native C after they show bounded usefulness against fair baselines.",
    "If native v0.5 evidence is later contradicted, return to the failing 4.32 tier before citing v0.5.",
]


@dataclass(frozen=True)
class EvidenceBundle:
    entry_id: str
    label: str
    path: Path
    results_file: str
    expected_runner_revision: str
    min_returned_artifacts: int
    summary_expectations: dict[str, Any]
    required_criteria: tuple[str, ...]
    claim: str
    boundary: str


@dataclass(frozen=True)
class Criterion:
    name: str
    value: Any
    rule: str
    passed: bool
    note: str = ""


BUNDLES: tuple[EvidenceBundle, ...] = (
    EvidenceBundle(
        entry_id="tier4_32a_hw_replicated_shard_stress",
        label="Tier 4.32a-hw-replicated single-chip replicated-shard stress",
        path=CONTROLLED / "tier4_32a_hw_replicated_20260507_hardware_pass_ingested",
        results_file="tier4_32a_hw_replicated_results.json",
        expected_runner_revision="tier4_32a_hw_replicated_shard_stress_20260507_0001",
        min_returned_artifacts=80,
        summary_expectations={
            "raw_remote_status": "pass",
            "point08_status": "pass",
            "point12_status": "pass",
            "point16_status": "pass",
        },
        required_criteria=(
            "hardware mode was run-hardware",
            "raw hardware status pass",
            "point08 pass",
            "point12 pass",
            "point16 pass",
            "single-chip replicated-shard only",
            "synthetic fallback zero",
        ),
        claim=(
            "Single-chip replicated-shard MCPL stress passed at 8/12/16-core "
            "stress points with returned artifacts preserved."
        ),
        boundary="Single-chip replicated-shard stress only; not multi-chip or speedup evidence.",
    ),
    EvidenceBundle(
        entry_id="tier4_32d_two_chip_mcpl_lookup_hardware_smoke",
        label="Tier 4.32d two-chip MCPL communication/readback smoke",
        path=CONTROLLED / "tier4_32d_20260507_hardware_pass_ingested",
        results_file="tier4_32d_results.json",
        expected_runner_revision="tier4_32d_interchip_mcpl_smoke_20260507_0001",
        min_returned_artifacts=40,
        summary_expectations={
            "raw_remote_status": "pass",
            "interchip_smoke_status": "pass",
        },
        required_criteria=(
            "hardware mode was run-hardware",
            "raw hardware status pass",
            "interchip smoke pass",
            "true two-partition learning not attempted",
            "synthetic fallback zero",
        ),
        claim=(
            "Two-chip MCPL lookup communication/readback passed with zero stale "
            "replies, duplicate replies, timeouts, or synthetic fallback."
        ),
        boundary="Two-chip communication/readback smoke only; not learning scale or speedup evidence.",
    ),
    EvidenceBundle(
        entry_id="tier4_32e_multi_chip_learning_microtask",
        label="Tier 4.32e two-chip learning-bearing micro-task",
        path=CONTROLLED / "tier4_32e_20260507_hardware_pass_ingested",
        results_file="tier4_32e_results.json",
        expected_runner_revision="tier4_32e_multichip_learning_microtask_20260507_0001",
        min_returned_artifacts=42,
        summary_expectations={
            "raw_remote_status": "pass",
            "learning_microtask_status": "pass",
        },
        required_criteria=(
            "hardware mode was run-hardware",
            "raw hardware status pass",
            "learning microtask pass",
            "enabled case present",
            "no-learning case present",
            "true two-partition learning not attempted",
            "synthetic fallback zero",
        ),
        claim=(
            "Two-chip single-shard learning-bearing micro-task passed with the "
            "enabled-learning case separated from the no-learning control."
        ),
        boundary="Two-chip learning micro-task only; not true two-partition or benchmark evidence.",
    ),
    EvidenceBundle(
        entry_id="tier4_32g_two_chip_lifecycle_traffic_resource_smoke",
        label="Tier 4.32g two-chip lifecycle traffic/resource smoke",
        path=CONTROLLED / "tier4_32g_20260508_hardware_pass_ingested",
        results_file="tier4_32g_results.json",
        expected_runner_revision="tier4_32g_multichip_lifecycle_traffic_resource_smoke_20260508_0003",
        min_returned_artifacts=30,
        summary_expectations={
            "raw_remote_status": "pass",
            "lifecycle_traffic_status": "pass",
            "traffic_counter_core_pass": True,
            "stale_package_detected": False,
        },
        required_criteria=(
            "hardware mode was run-hardware",
            "raw hardware status pass",
            "lifecycle traffic smoke pass",
            "traffic counters internally passed",
            "synthetic fallback zero",
        ),
        claim=(
            "Two-chip lifecycle traffic/resource smoke passed with source "
            "event/trophic requests, remote lifecycle mutation, mask sync, and "
            "zero stale/duplicate/missing-ack counters."
        ),
        boundary="Two-chip lifecycle traffic/resource smoke only; not lifecycle scaling evidence.",
    ),
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "__dataclass_fields__"):
        return json_safe(asdict(value))
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    return value


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json_safe(row.get(key, "")) for key in keys})


def criterion(name: str, value: Any, rule: str, passed: bool, note: str = "") -> dict[str, Any]:
    return asdict(Criterion(name=name, value=value, rule=rule, passed=bool(passed), note=note))


def criteria_names(data: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    for item in data.get("criteria") or []:
        if isinstance(item, dict):
            name = item.get("name") or item.get("criterion")
            if name:
                names.add(str(name))
    return names


def criterion_passed(data: dict[str, Any], name: str) -> bool:
    for item in data.get("criteria") or []:
        if not isinstance(item, dict):
            continue
        item_name = item.get("name") or item.get("criterion")
        if item_name == name:
            return bool(item.get("passed") if "passed" in item else item.get("pass"))
    return False


def summary_value(data: dict[str, Any], key: str) -> Any:
    summary = data.get("summary") if isinstance(data.get("summary"), dict) else {}
    if key in summary:
        return summary[key]
    hardware = data.get("hardware_results") if isinstance(data.get("hardware_results"), dict) else {}
    hsummary = hardware.get("summary") if isinstance(hardware.get("summary"), dict) else {}
    return hsummary.get(key)


def runner_revision(data: dict[str, Any]) -> Any:
    if data.get("runner_revision"):
        return data.get("runner_revision")
    hardware = data.get("hardware_results") if isinstance(data.get("hardware_results"), dict) else {}
    return hardware.get("runner_revision")


def returned_artifact_count(data: dict[str, Any]) -> int:
    summary = data.get("summary") if isinstance(data.get("summary"), dict) else {}
    if "returned_artifact_count" in summary:
        return int(summary["returned_artifact_count"])
    returned = data.get("returned_artifacts")
    if isinstance(returned, list):
        return len(returned)
    return 0


def claim_boundary_text(data: dict[str, Any]) -> str:
    parts = []
    if data.get("claim_boundary"):
        parts.append(str(data["claim_boundary"]))
    hardware = data.get("hardware_results") if isinstance(data.get("hardware_results"), dict) else {}
    if hardware.get("claim_boundary"):
        parts.append(str(hardware["claim_boundary"]))
    return " ".join(parts)


def evaluate_bundle(bundle: EvidenceBundle) -> dict[str, Any]:
    path = bundle.path / bundle.results_file
    checks: list[dict[str, Any]] = []
    checks.append(criterion("results file exists", str(path), "exists", path.exists()))
    data: dict[str, Any] = {}
    if path.exists():
        data = read_json(path)
    checks.append(criterion("status pass", data.get("status"), "== pass", data.get("status") == "pass"))
    checks.append(
        criterion(
            "runner revision matches",
            runner_revision(data),
            f"== {bundle.expected_runner_revision}",
            runner_revision(data) == bundle.expected_runner_revision,
        )
    )
    checks.append(
        criterion(
            "returned artifacts preserved",
            returned_artifact_count(data),
            f">= {bundle.min_returned_artifacts}",
            returned_artifact_count(data) >= bundle.min_returned_artifacts,
        )
    )
    for key, expected in bundle.summary_expectations.items():
        actual = summary_value(data, key)
        checks.append(criterion(f"summary {key}", actual, f"== {expected}", actual == expected))
    names = criteria_names(data)
    for required in bundle.required_criteria:
        checks.append(
            criterion(
                f"criterion present and passed: {required}",
                required,
                "present and passed",
                required in names and criterion_passed(data, required),
            )
        )
    boundary = claim_boundary_text(data).lower()
    checks.append(
        criterion(
            "claim boundary rejects speedup/benchmark",
            claim_boundary_text(data),
            "contains not speedup and not benchmark",
            "not speedup" in boundary and "not benchmark" in boundary,
        )
    )
    failed = [item for item in checks if not item["passed"]]
    return {
        "entry_id": bundle.entry_id,
        "label": bundle.label,
        "canonical_dir": str(bundle.path),
        "results_file": str(path),
        "status": "pass" if not failed else "fail",
        "criteria_passed": len(checks) - len(failed),
        "criteria_total": len(checks),
        "failed_criteria": failed,
        "criteria": checks,
        "runner_revision": runner_revision(data),
        "returned_artifact_count": returned_artifact_count(data),
        "claim": bundle.claim,
        "boundary": bundle.boundary,
    }


def build_baseline_payload(generated_at: str, bundle_rows: list[dict[str, Any]], criteria: list[dict[str, Any]]) -> dict[str, Any]:
    registry_generated_at = None
    registry_status = None
    registry_evidence_count = None
    if REGISTRY_PATH.exists():
        registry = read_json(REGISTRY_PATH)
        registry_generated_at = registry.get("generated_at_utc")
        registry_status = registry.get("registry_status") or registry.get("status")
        entries = registry.get("entries") or registry.get("evidence") or []
        registry_evidence_count = len(entries) if isinstance(entries, list) else registry.get("evidence_count")
    return {
        "baseline_id": BASELINE_ID,
        "status": "frozen",
        "frozen_at": generated_at,
        "runner_revision": RUNNER_REVISION,
        "source_output_dir": str(DEFAULT_OUTPUT_DIR),
        "source_registry_generated_at": registry_generated_at,
        "registry_status": registry_status,
        "registry_evidence_count": registry_evidence_count,
        "supersedes": "CRA_LIFECYCLE_NATIVE_BASELINE_v0.4 for native scale/substrate evidence",
        "does_not_supersede": [
            "v2.2 software capability baseline",
            "CRA_LIFECYCLE_NATIVE_BASELINE_v0.4 lifecycle task-benefit boundary",
        ],
        "freeze_rule": FREEZE_RULE,
        "strongest_claim": STRONGEST_CLAIM,
        "claim_boundaries": CLAIM_BOUNDARIES,
        "canonical_evidence_entries": bundle_rows,
        "freeze_criteria": criteria,
        "next_steps": NEXT_STEPS,
        "re_entry_condition": (
            "If future native multi-chip, lifecycle-scaling, benchmark, or real-task work "
            "invalidates any included Tier 4.32 evidence boundary, return to the failing "
            "4.32 tier and rerun its local/source/hardware/ingest gate before citing v0.5."
        ),
    }


def write_baseline_markdown(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# CRA Native Scale Baseline v0.5",
        "",
        f"- Frozen at: `{payload['frozen_at']}`",
        f"- Runner revision: `{payload['runner_revision']}`",
        f"- Registry status at freeze time: `{payload.get('registry_status')}`",
        f"- Registry evidence count at freeze time: `{payload.get('registry_evidence_count')}`",
        "- Supersedes: `CRA_LIFECYCLE_NATIVE_BASELINE_v0.4` for native scale/substrate evidence only",
        "",
        "## Freeze Rule",
        "",
        payload["freeze_rule"],
        "",
        "## Strongest Current Claim",
        "",
        payload["strongest_claim"],
        "",
        "## Claim Boundaries",
        "",
    ]
    lines.extend(f"- {item}" for item in payload["claim_boundaries"])
    lines.extend(["", "## Frozen Native-Scale Evidence", "", "| Entry | Status | Audit Criteria | Returned Artifacts | Claim | Boundary |", "| --- | --- | ---: | ---: | --- | --- |"])
    for row in payload["canonical_evidence_entries"]:
        lines.append(
            "| "
            f"`{row['entry_id']}` | `{row['status']}` | "
            f"{row['criteria_passed']}/{row['criteria_total']} | "
            f"{row['returned_artifact_count']} | {row['claim']} | {row['boundary']} |"
        )
    lines.extend(["", "## Next Steps", ""])
    lines.extend(f"- {item}" for item in payload["next_steps"])
    lines.extend(["", "## Re-entry Condition", "", payload["re_entry_condition"], ""])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_report(path: Path, results: dict[str, Any]) -> None:
    lines = [
        "# Tier 4.32h Native-Scale Evidence Closeout / Baseline Decision",
        "",
        f"- Generated: `{results['generated_at_utc']}`",
        f"- Status: **{results['status'].upper()}**",
        f"- Runner revision: `{results['runner_revision']}`",
        f"- Criteria: `{results['criteria_passed']}/{results['criteria_total']}`",
        f"- Baseline decision: `{results['baseline_decision']}`",
        "",
        "## Claim Boundary",
        "",
        results["claim_boundary"],
        "",
        "## Interpretation",
        "",
        results["interpretation"],
        "",
        "## Evidence Rows",
        "",
        "| Entry | Status | Audit Criteria | Returned Artifacts |",
        "| --- | --- | ---: | ---: |",
    ]
    for row in results["evidence_bundles"]:
        lines.append(
            f"| `{row['entry_id']}` | `{row['status']}` | "
            f"{row['criteria_passed']}/{row['criteria_total']} | {row['returned_artifact_count']} |"
        )
    lines.extend(["", "## Next", "", results["next_gate"], ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def run(output_dir: Path) -> dict[str, Any]:
    generated_at = utc_now()
    output_dir.mkdir(parents=True, exist_ok=True)
    bundle_rows = [evaluate_bundle(bundle) for bundle in BUNDLES]
    criteria: list[dict[str, Any]] = [
        criterion("runner revision current", RUNNER_REVISION, "expected", RUNNER_REVISION.endswith("_0001")),
        criterion("all evidence bundles pass", [row["status"] for row in bundle_rows], "all == pass", all(row["status"] == "pass" for row in bundle_rows)),
        criterion("4.32a replicated stress included", any(row["entry_id"] == "tier4_32a_hw_replicated_shard_stress" for row in bundle_rows), "== True", True),
        criterion("4.32d two-chip communication included", any(row["entry_id"] == "tier4_32d_two_chip_mcpl_lookup_hardware_smoke" for row in bundle_rows), "== True", True),
        criterion("4.32e learning microtask included", any(row["entry_id"] == "tier4_32e_multi_chip_learning_microtask" for row in bundle_rows), "== True", True),
        criterion("4.32g lifecycle traffic included", any(row["entry_id"] == "tier4_32g_two_chip_lifecycle_traffic_resource_smoke" for row in bundle_rows), "== True", True),
        criterion("native baseline freeze is bounded", CLAIM_BOUNDARY, "rejects speedup/benchmark/usefulness", "not speedup" in CLAIM_BOUNDARY and "not benchmark" in CLAIM_BOUNDARY),
        criterion("software usefulness pivot declared", NEXT_STEPS[1], "Tier 6.2/7.x next", "Tier 6.2" in NEXT_STEPS[1] and "software" in NEXT_STEPS[1]),
    ]
    for row in bundle_rows:
        for item in row["criteria"]:
            criteria.append({**item, "name": f"{row['entry_id']} {item['name']}"})
    failed = [item for item in criteria if not item["passed"]]
    status = "pass" if not failed else "fail"
    baseline_decision = "freeze_authorized" if status == "pass" else "freeze_blocked"
    interpretation = (
        "The native MCPL/substrate path is stable enough to freeze as v0.5, so broad native migration should pause. "
        "The next make-or-break question is software usefulness against hard synthetic, real-ish, held-out, and real-data baselines."
        if status == "pass"
        else "The native evidence bundle is not stable enough to freeze; repair the failed 4.32 evidence row before more hardware work."
    )
    results = {
        "tier": "4.32h",
        "tier_name": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": generated_at,
        "mode": "local-evidence-closeout",
        "status": status,
        "output_dir": str(output_dir),
        "criteria_passed": len(criteria) - len(failed),
        "criteria_total": len(criteria),
        "criteria": criteria,
        "failed_criteria": failed,
        "evidence_bundles": bundle_rows,
        "baseline_decision": baseline_decision,
        "baseline_id": BASELINE_ID if status == "pass" else None,
        "baseline_files": {
            "json": str(BASELINE_JSON) if status == "pass" else None,
            "markdown": str(BASELINE_MD) if status == "pass" else None,
            "registry_snapshot": str(BASELINE_SNAPSHOT) if status == "pass" else None,
        },
        "claim_boundary": CLAIM_BOUNDARY,
        "interpretation": interpretation,
        "next_gate": (
            "Phase H: Tier 6.2 hard synthetic software usefulness suite, then Tier 7.1 real-ish adapters and external baseline/fairness gates."
            if status == "pass"
            else "Repair the failed 4.32 evidence row before freezing v0.5."
        ),
    }
    write_json(output_dir / "tier4_32h_results.json", results)
    write_csv(output_dir / "tier4_32h_summary.csv", bundle_rows)
    write_report(output_dir / "tier4_32h_report.md", results)
    write_json(
        LATEST_MANIFEST,
        {
            "tier": "4.32h",
            "tier_name": TIER,
            "runner_revision": RUNNER_REVISION,
            "generated_at_utc": generated_at,
            "status": status,
            "manifest": str(output_dir / "tier4_32h_results.json"),
            "output_dir": str(output_dir),
            "registry_entry_id": "tier4_32h_native_scale_evidence_closeout",
            "baseline_decision": baseline_decision,
        },
    )
    if status == "pass":
        baseline_payload = build_baseline_payload(generated_at, bundle_rows, criteria)
        write_json(BASELINE_JSON, baseline_payload)
        write_baseline_markdown(BASELINE_MD, baseline_payload)
        if REGISTRY_PATH.exists():
            BASELINE_SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REGISTRY_PATH, BASELINE_SNAPSHOT)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=TIER)
    parser.add_argument("--mode", choices=("local", "closeout"), default="local")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    results = run(args.output_dir)
    print(json.dumps({"status": results["status"], "criteria": f"{results['criteria_passed']}/{results['criteria_total']}", "baseline_decision": results["baseline_decision"], "output_dir": str(args.output_dir)}, indent=2))
    if results["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
