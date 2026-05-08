#!/usr/bin/env python3
"""Research-grade repository audit for CRA.

The audit is intentionally conservative: it does not decide scientific truth, but
it checks whether the repository is clean, readable, internally consistent, and
safe to cite from the canonical evidence registry.
"""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"
DOC_PATH = ROOT / "docs" / "RESEARCH_GRADE_AUDIT.md"
JSON_PATH = CONTROLLED / "RESEARCH_GRADE_AUDIT.json"
EXPECTED_CANONICAL_EVIDENCE_COUNT = 85

REQUIRED_SOURCE_DOCS = [
    "README.md",
    "RUNBOOK.md",
    "CONTROLLED_TEST_PLAN.md",
    "ARTIFACTS.md",
    "ARCHITECTURE.md",
    "docs/ABSTRACT.md",
    "docs/WHITEPAPER.md",
    "docs/REVIEWER_DEFENSE_PLAN.md",
    "docs/MECHANISM_STATUS.md",
    "docs/CODEBASE_MAP.md",
    "docs/PAPER_RESULTS_TABLE.md",
    "experiments/README.md",
    "experiments/EVIDENCE_SCHEMA.md",
    "STUDY_EVIDENCE_INDEX.md",
]

REQUIRED_BASELINE_FILES = [
    "baselines/CRA_EVIDENCE_BASELINE_v0.1.md",
    "baselines/CRA_EVIDENCE_BASELINE_v0.1.json",
    "baselines/CRA_EVIDENCE_BASELINE_v0.1_STUDY_REGISTRY.snapshot.json",
    "baselines/CRA_EVIDENCE_BASELINE_v0.2.md",
    "baselines/CRA_EVIDENCE_BASELINE_v0.2.json",
    "baselines/CRA_EVIDENCE_BASELINE_v0.2_STUDY_REGISTRY.snapshot.json",
    "baselines/CRA_EVIDENCE_BASELINE_v0.3.md",
    "baselines/CRA_EVIDENCE_BASELINE_v0.3.json",
    "baselines/CRA_EVIDENCE_BASELINE_v0.3_STUDY_REGISTRY.snapshot.json",
    "baselines/CRA_EVIDENCE_BASELINE_v0.4.md",
    "baselines/CRA_EVIDENCE_BASELINE_v0.4.json",
    "baselines/CRA_EVIDENCE_BASELINE_v0.4_STUDY_REGISTRY.snapshot.json",
    "baselines/CRA_EVIDENCE_BASELINE_v0.5.md",
    "baselines/CRA_EVIDENCE_BASELINE_v0.5.json",
    "baselines/CRA_EVIDENCE_BASELINE_v0.5_STUDY_REGISTRY.snapshot.json",
    "baselines/CRA_EVIDENCE_BASELINE_v0.6.md",
    "baselines/CRA_EVIDENCE_BASELINE_v0.6.json",
    "baselines/CRA_EVIDENCE_BASELINE_v0.6_STUDY_REGISTRY.snapshot.json",
    "baselines/CRA_EVIDENCE_BASELINE_v0.7.md",
    "baselines/CRA_EVIDENCE_BASELINE_v0.7.json",
    "baselines/CRA_EVIDENCE_BASELINE_v0.7_STUDY_REGISTRY.snapshot.json",
    "baselines/CRA_EVIDENCE_BASELINE_v0.8.md",
    "baselines/CRA_EVIDENCE_BASELINE_v0.8.json",
    "baselines/CRA_EVIDENCE_BASELINE_v0.8_STUDY_REGISTRY.snapshot.json",
    "baselines/CRA_EVIDENCE_BASELINE_v0.9.md",
    "baselines/CRA_EVIDENCE_BASELINE_v0.9.json",
    "baselines/CRA_EVIDENCE_BASELINE_v0.9_STUDY_REGISTRY.snapshot.json",
    "baselines/CRA_EVIDENCE_BASELINE_v1.0.md",
    "baselines/CRA_EVIDENCE_BASELINE_v1.0.json",
    "baselines/CRA_EVIDENCE_BASELINE_v1.0_STUDY_REGISTRY.snapshot.json",
    "baselines/CRA_EVIDENCE_BASELINE_v1.1.md",
    "baselines/CRA_EVIDENCE_BASELINE_v1.1.json",
    "baselines/CRA_EVIDENCE_BASELINE_v1.1_STUDY_REGISTRY.snapshot.json",
    "baselines/CRA_EVIDENCE_BASELINE_v1.2.md",
    "baselines/CRA_EVIDENCE_BASELINE_v1.2.json",
    "baselines/CRA_EVIDENCE_BASELINE_v1.2_STUDY_REGISTRY.snapshot.json",
    "baselines/CRA_EVIDENCE_BASELINE_v1.3.md",
    "baselines/CRA_EVIDENCE_BASELINE_v1.3.json",
    "baselines/CRA_EVIDENCE_BASELINE_v1.3_STUDY_REGISTRY.snapshot.json",
    "baselines/CRA_EVIDENCE_BASELINE_v1.4.md",
    "baselines/CRA_EVIDENCE_BASELINE_v1.4.json",
    "baselines/CRA_EVIDENCE_BASELINE_v1.4_STUDY_REGISTRY.snapshot.json",
    "baselines/CRA_EVIDENCE_BASELINE_v1.5.md",
    "baselines/CRA_EVIDENCE_BASELINE_v1.5.json",
    "baselines/CRA_EVIDENCE_BASELINE_v1.5_STUDY_REGISTRY.snapshot.json",
    "baselines/CRA_EVIDENCE_BASELINE_v1.6.md",
    "baselines/CRA_EVIDENCE_BASELINE_v1.6.json",
    "baselines/CRA_EVIDENCE_BASELINE_v1.6_STUDY_REGISTRY.snapshot.json",
    "baselines/CRA_EVIDENCE_BASELINE_v1.7.md",
    "baselines/CRA_EVIDENCE_BASELINE_v1.7.json",
    "baselines/CRA_EVIDENCE_BASELINE_v1.7_STUDY_REGISTRY.snapshot.json",
    "baselines/CRA_EVIDENCE_BASELINE_v1.8.md",
    "baselines/CRA_EVIDENCE_BASELINE_v1.8.json",
    "baselines/CRA_EVIDENCE_BASELINE_v1.8_STUDY_REGISTRY.snapshot.json",
    "baselines/CRA_EVIDENCE_BASELINE_v1.9.md",
    "baselines/CRA_EVIDENCE_BASELINE_v1.9.json",
    "baselines/CRA_EVIDENCE_BASELINE_v1.9_STUDY_REGISTRY.snapshot.json",
    "baselines/CRA_EVIDENCE_BASELINE_v2.0.md",
    "baselines/CRA_EVIDENCE_BASELINE_v2.0.json",
    "baselines/CRA_EVIDENCE_BASELINE_v2.0_STUDY_REGISTRY.snapshot.json",
    "baselines/CRA_EVIDENCE_BASELINE_v2.1.md",
    "baselines/CRA_EVIDENCE_BASELINE_v2.1.json",
    "baselines/CRA_EVIDENCE_BASELINE_v2.1_STUDY_REGISTRY.snapshot.json",
    "baselines/CRA_EVIDENCE_BASELINE_v2.2.md",
    "baselines/CRA_EVIDENCE_BASELINE_v2.2.json",
    "baselines/CRA_EVIDENCE_BASELINE_v2.2_STUDY_REGISTRY.snapshot.json",
    "baselines/CRA_NATIVE_RUNTIME_BASELINE_v0.1.md",
    "baselines/CRA_NATIVE_TASK_BASELINE_v0.2.md",
    "baselines/CRA_NATIVE_TASK_BASELINE_v0.2_STUDY_REGISTRY.snapshot.json",
    "baselines/CRA_NATIVE_MECHANISM_BRIDGE_v0.3.md",
    "baselines/CRA_NATIVE_MECHANISM_BRIDGE_v0.3.json",
    "baselines/CRA_NATIVE_MECHANISM_BRIDGE_v0.3_STUDY_REGISTRY.snapshot.json",
    "baselines/CRA_LIFECYCLE_NATIVE_BASELINE_v0.4.md",
    "baselines/CRA_LIFECYCLE_NATIVE_BASELINE_v0.4.json",
    "baselines/CRA_LIFECYCLE_NATIVE_BASELINE_v0.4_STUDY_REGISTRY.snapshot.json",
    "baselines/CRA_NATIVE_SCALE_BASELINE_v0.5.md",
    "baselines/CRA_NATIVE_SCALE_BASELINE_v0.5.json",
    "baselines/CRA_NATIVE_SCALE_BASELINE_v0.5_STUDY_REGISTRY.snapshot.json",
]

FORBIDDEN_GENERATED_NAMES = {".DS_Store", ".pytest_cache", "__pycache__"}
FORBIDDEN_SUFFIXES = {".pyc", ".pyo"}

STALE_DOC_PATTERNS = [
    ("obsolete 14-entry current claim", re.compile(r"\b14\s+(tracked\s+)?(test[- ]entry|entries)\b", re.I)),
    ("obsolete 15-entry current claim", re.compile(r"\b15\s+(tracked\s+)?(test[- ]entry|entries)\b", re.I)),
    ("obsolete 16-entry current claim", re.compile(r"\b16\s+(tracked\s+)?(test[- ]entry|entries)\b", re.I)),
    ("obsolete 17-entry current claim", re.compile(r"\b17\s+(tracked\s+)?(test[- ]entry|entries)\b", re.I)),
    ("obsolete 18-entry current claim", re.compile(r"\b18\s+(tracked\s+)?(test[- ]entry|entries)\b", re.I)),
    ("obsolete 19-entry current claim", re.compile(r"\b19\s+(tracked\s+)?(test[- ]entry|entries)\b", re.I)),
    ("obsolete 20-entry current claim", re.compile(r"\b20\s+(tracked\s+)?(test[- ]entry|entries)\b", re.I)),
    ("obsolete 21-entry current claim", re.compile(r"\b21\s+(tracked\s+)?(test[- ]entry|entries)\b", re.I)),
    ("obsolete 22-entry current claim", re.compile(r"\b22\s+(tracked\s+)?(test[- ]entry|entries)\b", re.I)),
    ("obsolete 23-entry current claim", re.compile(r"\b23\s+(tracked\s+)?(test[- ]entry|entries)\b", re.I)),
    ("obsolete 24-entry current claim", re.compile(r"\b24\s+(tracked\s+)?(test[- ]entry|entries)\b", re.I)),
    ("obsolete 25-entry current claim", re.compile(r"\b25\s+(tracked\s+)?(test[- ]entry|entries)\b", re.I)),
    ("obsolete 8-bundle current claim", re.compile(r"\b8\s+canonical\s+(evidence\s+)?bundles\b", re.I)),
    ("obsolete 9-bundle current claim", re.compile(r"\b9\s+canonical\s+(evidence\s+)?bundles\b", re.I)),
    ("obsolete 10-bundle current claim", re.compile(r"\b10\s+canonical\s+(evidence\s+)?bundles\b", re.I)),
    ("obsolete 11-bundle current claim", re.compile(r"\b11\s+canonical\s+(evidence\s+)?bundles\b", re.I)),
    ("obsolete 12-bundle current claim", re.compile(r"\b12\s+canonical\s+(evidence\s+)?bundles\b", re.I)),
    ("obsolete 13-bundle current claim", re.compile(r"\b13\s+canonical\s+(evidence\s+)?bundles\b", re.I)),
    ("obsolete 14-bundle current claim", re.compile(r"\b14\s+canonical\s+(evidence\s+)?bundles\b", re.I)),
    ("obsolete 15-bundle current claim", re.compile(r"\b15\s+canonical\s+(evidence\s+)?bundles\b", re.I)),
    ("obsolete 16-bundle current claim", re.compile(r"\b16\s+canonical\s+(evidence\s+)?bundles\b", re.I)),
    ("obsolete 17-bundle current claim", re.compile(r"\b17\s+canonical\s+(evidence\s+)?bundles\b", re.I)),
    ("obsolete 18-bundle current claim", re.compile(r"\b18\s+canonical\s+(evidence\s+)?bundles\b", re.I)),
    ("obsolete 19-bundle current claim", re.compile(r"\b19\s+canonical\s+(evidence\s+)?bundles\b", re.I)),
    ("obsolete 20-bundle current claim", re.compile(r"\b20\s+canonical\s+(evidence\s+)?bundles\b", re.I)),
    ("obsolete 21-bundle current claim", re.compile(r"\b21\s+canonical\s+(evidence\s+)?bundles\b", re.I)),
    ("obsolete 22-bundle current claim", re.compile(r"\b22\s+canonical\s+(evidence\s+)?bundles\b", re.I)),
    ("Tier 4.14 described as future/planned", re.compile(r"Tier\s+4\.14[^\n]{0,80}\b(planned|future|next planned)\b", re.I)),
    ("Tier 4.15 described as noncanonical", re.compile(r"Tier\s+4\.15[^\n]{0,100}\b(noncanonical|not canonical|do not cite|prepared as the next)\b", re.I)),
]

STALE_SCAN_FILES = [
    "README.md",
    "RUNBOOK.md",
    "CONTROLLED_TEST_PLAN.md",
    "ARTIFACTS.md",
    "docs/ABSTRACT.md",
    "docs/WHITEPAPER.md",
    "docs/CODEBASE_MAP.md",
    "docs/PAPER_RESULTS_TABLE.md",
    "experiments/README.md",
    "experiments/EVIDENCE_SCHEMA.md",
    "STUDY_EVIDENCE_INDEX.md",
]


@dataclass
class Check:
    name: str
    passed: bool
    details: str = ""
    severity: str = "error"

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "severity": self.severity,
            "details": self.details,
        }


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def check_required_files(paths: list[str], label: str) -> Check:
    missing = [p for p in paths if not (ROOT / p).exists()]
    return Check(
        name=f"required {label} files exist",
        passed=not missing,
        details="missing: " + ", ".join(missing) if missing else f"{len(paths)} files present",
    )


def check_generated_clutter() -> Check:
    offenders: list[str] = []
    for path in ROOT.rglob("*"):
        parts = set(path.parts)
        if ".git" in parts:
            continue
        if path.name in FORBIDDEN_GENERATED_NAMES or path.suffix in FORBIDDEN_SUFFIXES:
            offenders.append(rel(path))
    return Check(
        name="no transient generated clutter in repo tree",
        passed=not offenders,
        details="; ".join(offenders[:30]) if offenders else "no .DS_Store, caches, or pyc files found",
    )


def check_registry() -> tuple[Check, dict[str, Any]]:
    path = CONTROLLED / "STUDY_REGISTRY.json"
    if not path.exists():
        return Check("canonical registry exists and passes", False, "missing STUDY_REGISTRY.json"), {}
    registry = load_json(path)
    failures: list[str] = []
    if registry.get("registry_status") != "pass":
        failures.append(f"registry_status={registry.get('registry_status')}")
    if registry.get("evidence_count") != EXPECTED_CANONICAL_EVIDENCE_COUNT:
        failures.append(
            f"evidence_count={registry.get('evidence_count')} "
            f"expected {EXPECTED_CANONICAL_EVIDENCE_COUNT}"
        )
    if registry.get("expanded_test_entry_count") != EXPECTED_CANONICAL_EVIDENCE_COUNT:
        failures.append(
            f"expanded_test_entry_count={registry.get('expanded_test_entry_count')} "
            f"expected {EXPECTED_CANONICAL_EVIDENCE_COUNT}"
        )
    integrity = registry.get("integrity") or {}
    if integrity.get("missing_expected_artifacts"):
        failures.append("missing_expected_artifacts is non-empty")
    if integrity.get("failed_criteria"):
        failures.append("failed_criteria is non-empty")
    entries = registry.get("entries") or []
    if any(entry.get("status") != "pass" for entry in entries):
        failures.append("one or more canonical entries are not pass")
    return Check(
        name="canonical registry exists and passes",
        passed=not failures,
        details=(
            "; ".join(failures)
            if failures
            else f"{registry.get('evidence_count')} canonical bundles, 0 missing artifacts, 0 failed criteria"
        ),
    ), registry


def check_latest_manifests(registry: dict[str, Any]) -> Check:
    failures: list[str] = []
    for entry in registry.get("entries", []):
        entry_id = entry.get("entry_id")
        run_dir = Path(entry.get("canonical_output_dir") or "")
        expected_manifest = Path(entry.get("results_json") or "")
        latest_names = []
        # The registry updates latest pointers from EvidenceSpec. Reading the
        # pointer files directly catches accidental hand edits after registry generation.
        for path in CONTROLLED.glob("*_latest_manifest.json"):
            try:
                data = load_json(path)
            except Exception:
                continue
            if data.get("registry_entry_id") == entry_id:
                latest_names.append(path)
                if Path(data.get("manifest", "")) != expected_manifest:
                    failures.append(f"{rel(path)} points away from {rel(expected_manifest)}")
                if data.get("status") != "pass":
                    failures.append(f"{rel(path)} status={data.get('status')}")
        if not latest_names:
            failures.append(f"no latest manifest pointer for {entry_id}")
        if not run_dir.exists():
            failures.append(f"canonical dir missing for {entry_id}: {run_dir}")
    return Check(
        name="latest manifest pointers match canonical registry",
        passed=not failures,
        details="; ".join(failures) if failures else "all canonical latest pointers are aligned",
    )


def check_frozen_baselines() -> Check:
    expectations = {
        "v0.1": {
            "status": "frozen",
            "registry_status": "pass",
            "evidence_count": 8,
            "core_test_count": 12,
            "expanded_test_entry_count": 14,
        },
        "v0.2": {
            "status": "frozen",
            "registry_status": "pass",
            "evidence_count": 11,
            "core_test_count": 12,
            "expanded_test_entry_count": 17,
        },
        "v0.3": {
            "status": "frozen",
            "registry_status": "pass",
            "evidence_count": 13,
            "core_test_count": 12,
            "expanded_test_entry_count": 19,
        },
        "v0.4": {
            "status": "frozen",
            "registry_status": "pass",
            "evidence_count": 14,
            "core_test_count": 12,
            "expanded_test_entry_count": 20,
        },
        "v0.5": {
            "status": "frozen",
            "registry_status": "pass",
            "evidence_count": 14,
            "core_test_count": 12,
            "expanded_test_entry_count": 20,
        },
        "v0.6": {
            "status": "frozen",
            "registry_status": "pass",
            "evidence_count": 15,
            "core_test_count": 12,
            "expanded_test_entry_count": 21,
        },
        "v0.7": {
            "status": "frozen",
            "registry_status": "pass",
            "evidence_count": 16,
            "core_test_count": 12,
            "expanded_test_entry_count": 22,
        },
        "v0.8": {
            "status": "frozen",
            "registry_status": "pass",
            "evidence_count": 17,
            "core_test_count": 12,
            "expanded_test_entry_count": 23,
        },
        "v0.9": {
            "status": "frozen",
            "registry_status": "pass",
            "evidence_count": 18,
            "core_test_count": 12,
            "expanded_test_entry_count": 24,
        },
        "v1.0": {
            "status": "frozen",
            "registry_status": "pass",
            "evidence_count": 19,
            "core_test_count": 12,
            "expanded_test_entry_count": 24,
        },
        "v1.1": {
            "status": "frozen",
            "registry_status": "pass",
            "evidence_count": 20,
            "core_test_count": 12,
            "expanded_test_entry_count": 24,
        },
        "v1.2": {
            "status": "frozen",
            "registry_status": "pass",
            "evidence_count": 21,
            "core_test_count": 12,
            "expanded_test_entry_count": 25,
        },
        "v1.3": {
            "status": "frozen",
            "registry_status": "pass",
            "evidence_count": 22,
            "core_test_count": 12,
            "expanded_test_entry_count": 26,
        },
        "v1.4": {
            "status": "frozen",
            "registry_status": "pass",
            "evidence_count": 23,
            "core_test_count": 12,
            "expanded_test_entry_count": 27,
        },
        "v1.5": {
            "status": "frozen",
            "registry_status": "pass",
            "evidence_count": 23,
            "core_test_count": 12,
            "expanded_test_entry_count": 27,
        },
        "v1.6": {
            "status": "frozen",
            "registry_status": "pass",
            "evidence_count": 23,
            "core_test_count": 12,
            "expanded_test_entry_count": 27,
        },
        "v1.7": {
            "status": "frozen",
            "registry_status": "pass",
            "evidence_count": 23,
            "core_test_count": 12,
            "expanded_test_entry_count": 27,
        },
        "v1.8": {
            "status": "frozen",
            "registry_status": "pass",
            "evidence_count": 26,
            "core_test_count": 12,
            "expanded_test_entry_count": 28,
        },
        "v1.9": {
            "status": "frozen",
            "registry_status": "pass",
            "evidence_count": 26,
            "core_test_count": 12,
            "expanded_test_entry_count": 28,
        },
        "v2.0": {
            "status": "frozen",
            "registry_status": "pass",
            "evidence_count": 26,
            "core_test_count": 12,
            "expanded_test_entry_count": 28,
        },
        "v2.1": {
            "status": "frozen",
            "registry_status": "pass",
            "evidence_count": 26,
            "core_test_count": 12,
            "expanded_test_entry_count": 28,
        },
        "v2.2": {
            "status": "frozen",
            "registry_status": "pass",
            "evidence_count": 47,
            "core_test_count": 12,
            "expanded_test_entry_count": 47,
            "noncanonical_output_count": 294,
        },
    }
    failures: list[str] = []
    for version, expected in expectations.items():
        baseline_path = ROOT / "baselines" / f"CRA_EVIDENCE_BASELINE_{version}.json"
        if not baseline_path.exists():
            failures.append(f"missing {version} baseline JSON")
            continue
        baseline = load_json(baseline_path)
        for key, value in expected.items():
            if baseline.get(key) != value:
                failures.append(f"{version}:{key}={baseline.get(key)} expected {value}")
        snapshot = ROOT / "baselines" / f"CRA_EVIDENCE_BASELINE_{version}_STUDY_REGISTRY.snapshot.json"
        if not snapshot.exists():
            failures.append(f"missing {version} registry snapshot")
    return Check(
        name="frozen evidence baselines are intact",
        passed=not failures,
        details="; ".join(failures) if failures else "v0.1 through v2.2 baselines remain frozen at their recorded counts",
    )


def check_paper_table(registry: dict[str, Any]) -> Check:
    md = ROOT / "docs" / "PAPER_RESULTS_TABLE.md"
    csv_path = CONTROLLED / "PAPER_RESULTS_TABLE.csv"
    failures: list[str] = []
    if not md.exists():
        failures.append("missing docs/PAPER_RESULTS_TABLE.md")
    if not csv_path.exists():
        failures.append("missing controlled_test_output/PAPER_RESULTS_TABLE.csv")
    if csv_path.exists():
        with csv_path.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        if len(rows) != registry.get("evidence_count"):
            failures.append(f"paper CSV rows={len(rows)} expected {registry.get('evidence_count')}")
    if md.exists():
        text = md.read_text(encoding="utf-8")
        if f"Canonical bundles: `{registry.get('evidence_count')}`" not in text:
            failures.append("paper table canonical bundle count is stale")
        if f"Expanded entries: `{registry.get('expanded_test_entry_count')}`" not in text:
            failures.append("paper table expanded entry count is stale")
    return Check(
        name="paper-facing results table matches registry",
        passed=not failures,
        details="; ".join(failures) if failures else "paper Markdown and CSV are aligned with registry",
    )


def check_stale_doc_claims() -> Check:
    findings: list[str] = []
    for rel_path in STALE_SCAN_FILES:
        path = ROOT / rel_path
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for label, pattern in STALE_DOC_PATTERNS:
            for match in pattern.finditer(text):
                line_no = text.count("\n", 0, match.start()) + 1
                findings.append(f"{rel_path}:{line_no}: {label}: {match.group(0)}")
    return Check(
        name="current docs have no stale evidence-count claims",
        passed=not findings,
        details="; ".join(findings[:20]) if findings else "no stale current evidence-count claims outside frozen baselines",
    )


def build_report(checks: list[Check], registry: dict[str, Any]) -> str:
    status = "PASS" if all(c.passed for c in checks if c.severity == "error") else "FAIL"
    lines = [
        "# Research-Grade Repository Audit",
        "",
        "This report is generated by `python3 experiments/repo_audit.py`.",
        "It checks repository hygiene and evidence-paperwork alignment; it does not",
        "replace scientific review of the underlying methods.",
        "",
        f"- Generated: `{utc_now()}`",
        f"- Status: **{status}**",
        f"- Registry status: `{registry.get('registry_status', 'unknown')}`",
        f"- Canonical evidence bundles: `{registry.get('evidence_count', 'unknown')}`",
        f"- Expanded evidence entries: `{registry.get('expanded_test_entry_count', 'unknown')}`",
        "",
        "## Checks",
        "",
        "| Check | Status | Details |",
        "| --- | --- | --- |",
    ]
    for check in checks:
        mark = "PASS" if check.passed else "FAIL"
        detail = check.details.replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {check.name} | **{mark}** | {detail} |")
    lines.extend(
        [
            "",
            "## Source Of Truth",
            "",
            "- Current canonical evidence: `controlled_test_output/STUDY_REGISTRY.json`",
            "- Paper-facing table: `docs/PAPER_RESULTS_TABLE.md`",
            "- Frozen v0.1 baseline: `baselines/CRA_EVIDENCE_BASELINE_v0.1.md`",
            "- Frozen v0.2 baseline: `baselines/CRA_EVIDENCE_BASELINE_v0.2.md`",
            "- Frozen v0.3 baseline: `baselines/CRA_EVIDENCE_BASELINE_v0.3.md`",
            "- Frozen v0.4 baseline: `baselines/CRA_EVIDENCE_BASELINE_v0.4.md`",
            "- Frozen v0.5 baseline: `baselines/CRA_EVIDENCE_BASELINE_v0.5.md`",
            "- Frozen v0.6 baseline: `baselines/CRA_EVIDENCE_BASELINE_v0.6.md`",
            "- Frozen v0.7 baseline: `baselines/CRA_EVIDENCE_BASELINE_v0.7.md`",
            "- Frozen v0.8 baseline: `baselines/CRA_EVIDENCE_BASELINE_v0.8.md`",
            "- Frozen v0.9 baseline: `baselines/CRA_EVIDENCE_BASELINE_v0.9.md`",
            "- Frozen v1.0 baseline: `baselines/CRA_EVIDENCE_BASELINE_v1.0.md`",
            "- Frozen v1.1 baseline: `baselines/CRA_EVIDENCE_BASELINE_v1.1.md`",
            "- Frozen v1.2 baseline: `baselines/CRA_EVIDENCE_BASELINE_v1.2.md`",
            "- Frozen v1.3 baseline: `baselines/CRA_EVIDENCE_BASELINE_v1.3.md`",
            "- Frozen v1.4 baseline: `baselines/CRA_EVIDENCE_BASELINE_v1.4.md`",
            "- Frozen v1.5 baseline: `baselines/CRA_EVIDENCE_BASELINE_v1.5.md`",
            "- Frozen v1.6 baseline: `baselines/CRA_EVIDENCE_BASELINE_v1.6.md`",
            "- Frozen v1.7 baseline: `baselines/CRA_EVIDENCE_BASELINE_v1.7.md`",
            "- Frozen v1.8 baseline: `baselines/CRA_EVIDENCE_BASELINE_v1.8.md`",
            "- Frozen v1.9 baseline: `baselines/CRA_EVIDENCE_BASELINE_v1.9.md`",
            "- Frozen v2.0 baseline: `baselines/CRA_EVIDENCE_BASELINE_v2.0.md`",
            "- Frozen v2.1 baseline: `baselines/CRA_EVIDENCE_BASELINE_v2.1.md`",
            "- Frozen v2.2 baseline: `baselines/CRA_EVIDENCE_BASELINE_v2.2.md`",
            "- Frozen native runtime baseline: `baselines/CRA_NATIVE_RUNTIME_BASELINE_v0.1.md`",
            "- Frozen native task baseline: `baselines/CRA_NATIVE_TASK_BASELINE_v0.2.md`",
            "- Frozen native mechanism bridge: `baselines/CRA_NATIVE_MECHANISM_BRIDGE_v0.3.md`",
            "- Frozen lifecycle native baseline: `baselines/CRA_LIFECYCLE_NATIVE_BASELINE_v0.4.md`",
            "- Frozen native-scale substrate baseline: `baselines/CRA_NATIVE_SCALE_BASELINE_v0.5.md`",
            "- Full narrative: `docs/WHITEPAPER.md`",
            "- Reviewer defense plan: `docs/REVIEWER_DEFENSE_PLAN.md`",
            "- Codebase map: `docs/CODEBASE_MAP.md`",
            "",
            "## Evidence Categories",
            "",
            "- Canonical registry evidence: entries in `controlled_test_output/STUDY_REGISTRY.json` that populate the paper-facing results table.",
            "- Baseline-frozen mechanism evidence: passed mechanism/promotion diagnostics with compact regression and a frozen `baselines/CRA_EVIDENCE_BASELINE_vX.Y.*` lock, even when the source bundle is not a canonical registry entry.",
            "- Noncanonical diagnostic evidence: useful pass/fail diagnostics that answer a design question but do not freeze a new baseline by themselves.",
            "- Failed/parked diagnostic evidence: clean negative evidence retained to prevent p-hacking and explain why a mechanism was not promoted.",
            "- Hardware prepare/probe evidence: run packages and one-off probes that are not hardware claims until reviewed and promoted.",
            "",
            "## Claim Boundaries",
            "",
            "- Tier 4.13 is a single-seed N=8 fixed-pattern SpiNNaker hardware capsule pass.",
            "- Tier 4.14 is runtime/provenance characterization of that pass.",
            "- Tier 4.15 is a three-seed repeatability pass for the same minimal hardware capsule.",
            "- Tier 5.1 is a controlled software baseline comparison and explicitly documents where simpler learners beat CRA.",
            "- Tier 5.2 is a controlled software learning-curve sweep; its result is mixed/negative for CRA at the 1500-step horizon.",
            "- Tier 5.3 is a controlled software failure-analysis matrix; stronger delayed credit is the leading candidate fix, but hard switching still trails the best external baseline.",
            "- Tier 5.4 is a controlled software confirmation; delayed credit is confirmed versus median criteria, but hard switching still trails the best external baseline.",
            "- Tier 4.16a is repaired delayed-cue SpiNNaker transfer across three seeds; it is not hard_noisy_switching transfer, hardware scaling, on-chip learning, or full Tier 4.16.",
            "- Tier 4.16b hard_noisy_switching now passes as repaired three-seed SpiNNaker transfer under chunked host replay; it is close to threshold and is not hardware scaling, on-chip learning, or external-baseline superiority.",
            "- Tier 4.18a is v0.7 chunked-host runtime/resource characterization and recommends chunk 50; it is not hardware scaling, on-chip learning, or external-baseline superiority.",
            "- Tier 5.5 is controlled software expanded-baseline evidence; it completed the full matrix and supports robust/not-dominated regimes, but it is not hardware evidence, not hyperparameter fairness completion, and not universal or best-baseline superiority.",
            "- Tier 5.6 is controlled software tuned-baseline fairness evidence; it keeps CRA locked and retunes implemented external baselines, but it is not hardware evidence, not an all-possible-baselines proof, and not universal best-baseline superiority.",
            "- Tier 5.7 is controlled software compact-regression evidence; it proves the promoted setting still passes compact guardrails, not a new capability claim.",
            "- Tier 5.10g is baseline-frozen host-side keyed-memory evidence; it freezes v1.6 but is not native/on-chip memory, sleep/replay, hardware memory transfer, compositionality, module routing, or general working memory.",
            "- Tier 5.11d is baseline-frozen host-side software replay/consolidation evidence; it freezes v1.7 but is not native/on-chip replay, hardware memory transfer, priority-weighting proof, compositionality, or world-model evidence.",
            "- Tier 5.12a is predictive task-validation evidence; it validates predictive pressure but is not CRA predictive coding, world modeling, language, planning, hardware prediction, or v1.8 by itself.",
            "- Tier 5.12c is host-side visible predictive-context evidence; Tier 5.12d is the compact-regression promotion gate that freezes bounded v1.8.",
            "- Tier 5.12d is controlled software compact-regression/promotion evidence; it is not hidden-regime inference, full world modeling, language, planning, hardware prediction, hardware scaling, native on-chip learning, compositionality, or external-baseline superiority.",
            "- Tier 5.13c is baseline-frozen internal host-side composition/routing evidence; v1.9 freezes it only after a fresh full compact regression pass, and it is not hardware/on-chip routing, language, planning, AGI, or external-baseline superiority.",
            "- Tier 5.14 is noncanonical working-memory/context-binding diagnostic evidence over frozen v1.9; it supports host-side context/cue and delayed module-state binding, but it is not hardware/on-chip working memory, language, planning, AGI, external-baseline superiority, or a v2.0 freeze by itself.",
            "- Tier 5.15 is noncanonical software temporal-code diagnostic evidence; it shows timing codes can carry task information under time-shuffle/rate-only controls, but it is not hardware/on-chip temporal coding, neuron-model robustness, hard-switch temporal superiority, or a v2.0 freeze.",
            "- Tier 5.16 is noncanonical NEST neuron-parameter sensitivity evidence; it shows the current CRA NEST path remains functional across the tested LIF threshold/tau/refractory/capacitance/synaptic-tau band with zero fallback/failure counters and audited propagation, but it is not hardware/custom-C/on-chip neuron evidence, adaptive-Izhikevich evidence, or a v2.0 freeze.",
            "- Tier 5.17 is failed noncanonical pre-reward representation diagnostic evidence; it proves the no-label/no-reward exposure harness works, but the strict scaffold is not promoted because probe, sham-separation, and sample-efficiency gates did not all pass.",
            "- Tier 5.17b is passed noncanonical failure-analysis evidence; it classifies the 5.17 failure and routes the next repair to intrinsic predictive / MI-style preexposure, but it does not promote reward-free representation learning or a v2.0 freeze.",
            "- Tier 5.17c is failed noncanonical intrinsic predictive preexposure evidence; it preserves zero-label/zero-reward/zero-dopamine exposure and shows partial gains, but target-shuffled, wrong-domain, STDP-only, and best non-oracle controls are not cleanly separated.",
            "- Tier 5.17d is passed bounded noncanonical predictive-binding evidence; it repairs the 5.17c sham-separation failure on cross-modal and reentry binding tasks, but it is not general unsupervised concept learning, hardware/on-chip representation evidence, full world modeling, language, planning, AGI, or a v2.0 freeze.",
            "- Tier 5.17e is baseline-frozen host-side predictive-binding compact-regression evidence; it freezes v2.0 only after v1.8 compact regression, v1.9 composition/routing, Tier 5.14 working-memory/context binding, and Tier 5.17d predictive-binding guardrails all pass.",
            "- Tier 5.18 is passed noncanonical self-evaluation/metacognitive-monitoring diagnostic evidence; it supports operational pre-feedback reliability monitoring and confidence-gated adaptation over frozen v2.0, but it is not consciousness, self-awareness, hardware evidence, AGI, or a v2.1 freeze.",
            "- Tier 5.18c is baseline-frozen host-side self-evaluation compact-regression evidence; it freezes v2.1 only after the full v2.0 compact gate and Tier 5.18 guardrail both pass, and it is not consciousness, self-awareness, hardware evidence, AGI, language, planning, or external-baseline superiority.",
            "- Tier 5.9c is failed noncanonical macro-eligibility recheck evidence; the v2.1 guardrail stayed green but the macro residual still failed trace-ablation specificity, so macro eligibility remains parked and is not hardware/custom-C ready.",
            "- Tier 5.19c is baseline-frozen host-side software fading-memory temporal-state evidence; it freezes v2.2 only after a full NEST compact regression gate and destructive temporal shams pass, and it is not bounded nonlinear recurrence, hardware evidence, native on-chip temporal dynamics, universal benchmark superiority, language, planning, AGI, or ASI.",
            "- Tier 4.30-readiness is a lifecycle-native engineering audit; it selects a static-pool path layered on the native mechanism bridge, not a lifecycle implementation or hardware claim.",
            "- Tier 4.30 is a lifecycle-native static-pool contract; it defines commands, readback, event semantics, gates, and failure classes, but it is not runtime implementation or hardware evidence.",
            "- Tier 4.30a is a deterministic local lifecycle reference with active-mask, lineage, event-count, checksum, and sham-control outputs; it is not runtime C or hardware evidence.",
            "- Tier 4.30b is local source/runtime host evidence that the lifecycle static-pool surface matches the 4.30a checksums and preserves existing runtime tests; it is not hardware evidence, task-effect evidence, multi-core lifecycle migration, or a baseline freeze.",
            "- Tier 4.30b-hw is single-core lifecycle hardware smoke evidence after corrected ingest; it proves compact lifecycle metadata readback and reference parity on a real board, not task benefit, multi-core lifecycle migration, speedup, multi-chip scaling, or a lifecycle baseline freeze.",
            "- Tier 4.30c is local multi-core lifecycle split contract/reference evidence; it defines the five-core role split and MCPL/multicast lifecycle messages, but it is not C runtime implementation or EBRAINS hardware evidence.",
            "- Tier 4.30d is local source/runtime host evidence for the five-core lifecycle split; it proves the dedicated lifecycle_core profile, stubs/counters, ownership guards, and local C tests, not EBRAINS hardware execution.",
            "- Tier 4.30e is multi-core lifecycle hardware smoke evidence; it proves the five-profile lifecycle runtime surface builds/loads/executes on one real SpiNNaker board with ownership guards, duplicate/stale rejection, and canonical/boundary lifecycle parity, but it is not lifecycle task-benefit evidence, lifecycle sham-control success, speedup, multi-chip scaling, v2.2 temporal migration, or a lifecycle baseline freeze.",
            "- Tier 4.30f is lifecycle sham-control hardware subset evidence; it proves enabled and five predeclared lifecycle controls separate on real SpiNNaker, but it is not lifecycle task-benefit evidence, full Tier 6.3 hardware, speedup, multi-chip scaling, v2.2 temporal migration, or a lifecycle baseline freeze by itself.",
            "- Tier 4.30g-hw is lifecycle task-benefit/resource bridge hardware evidence; it proves a bounded host-ferried lifecycle gate opens for enabled mode and closes for five controls with returned resource accounting, but it is not autonomous lifecycle-to-learning MCPL, speedup, multi-chip scaling, dynamic population creation, v2.2 temporal migration, or full organism autonomy.",
            "- Tier 4.32h is a local native-scale evidence closeout that freezes `CRA_NATIVE_SCALE_BASELINE_v0.5` over 4.32a-replicated, 4.32d, 4.32e, and 4.32g. It is a substrate baseline only, not speedup evidence, benchmark usefulness evidence, true two-partition learning, lifecycle scaling, multi-shard learning, language, planning, AGI, or ASI.",
            "- Tier 4.20a is a passed hardware-transfer readiness audit; it classifies v2.1 mechanisms by chunked-host readiness versus future custom-runtime/on-chip blockers, but it is not SpiNNaker hardware evidence or v2.1 hardware transfer.",
            "- Tier 4.20b is passed one-seed v2.1 chunked-host bridge/transport hardware evidence; it returned real pyNN.spiNNaker execution, zero fallback, zero sim.run/readback failures, and nonzero spike readback, but it is not repeatability evidence or full native/on-chip v2.1 mechanism execution.",
            "- Tier 6.1 is controlled software lifecycle/self-scaling evidence with clean lineage and hard-switch advantage regimes; it is not full adult turnover, sham-control proof, hardware lifecycle, or external-baseline superiority.",
            "- Tier 6.3 is controlled software lifecycle sham-control evidence; replay/shuffle controls are audit artifacts and it is not hardware lifecycle, full adult turnover, or external-baseline superiority.",
            "- Tier 6.4 is controlled software circuit-motif causality evidence; the motif-diverse graph is seeded for the suite, motif-label shuffle is not causal by itself, and it is not hardware motif execution, custom-C/on-chip learning, compositionality, or world-model evidence.",
            "- Tiers 4.13, 4.14, 4.15, 4.16a, 4.16b, and 4.18a are not full hardware scaling evidence.",
            "- Frozen baselines are intentionally historical and may contain older evidence counts.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    checks: list[Check] = []
    checks.append(check_required_files(REQUIRED_SOURCE_DOCS, "source documentation"))
    checks.append(check_required_files(REQUIRED_BASELINE_FILES, "baseline"))
    checks.append(check_generated_clutter())
    registry_check, registry = check_registry()
    checks.append(registry_check)
    if registry:
        checks.append(check_latest_manifests(registry))
        checks.append(check_paper_table(registry))
    else:
        checks.append(Check("latest manifest pointers match canonical registry", False, "registry missing"))
        checks.append(Check("paper-facing results table matches registry", False, "registry missing"))
    checks.append(check_frozen_baselines())
    checks.append(check_stale_doc_claims())

    status = "pass" if all(c.passed for c in checks if c.severity == "error") else "fail"
    payload = {
        "generated_at_utc": utc_now(),
        "status": status,
        "checks": [c.as_dict() for c in checks],
        "registry_summary": {
            "registry_status": registry.get("registry_status") if registry else None,
            "evidence_count": registry.get("evidence_count") if registry else None,
            "expanded_test_entry_count": registry.get("expanded_test_entry_count") if registry else None,
        },
    }
    write_json(JSON_PATH, payload)
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOC_PATH.write_text(build_report(checks, registry), encoding="utf-8")
    print(json.dumps({"status": status, "markdown": str(DOC_PATH), "json": str(JSON_PATH)}, indent=2))
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
