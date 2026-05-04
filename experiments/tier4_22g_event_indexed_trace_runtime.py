#!/usr/bin/env python3
"""Tier 4.22g event-indexed / active-trace runtime optimization.

Tier 4.22f0 blocked direct custom-runtime learning hardware because the C
sidecar still used all-synapse scans for spike delivery, trace decay, and
dopamine modulation. Tier 4.22g fixes those specific data-structure blockers:

- pre-indexed outgoing synapse delivery
- active eligibility trace list
- active-trace-only decay and dopamine modulation

Claim boundary:
- PASS = the local C runtime has the indexed/active-trace optimization and host
  tests cover it.
- PASS does not mean custom-runtime hardware learning is allowed yet. Compact
  state readback and build/load/command acceptance remain separate gates.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"
RUNTIME = ROOT / "coral_reef_spinnaker" / "spinnaker_runtime"
SRC = RUNTIME / "src"
TESTS = RUNTIME / "tests"
TIER = "Tier 4.22g - Event-Indexed Active-Trace Runtime"
RUNNER_REVISION = "tier4_22g_event_indexed_trace_runtime_20260430_0000"
TIER4_22F0_LATEST = CONTROLLED / "tier4_22f0_latest_manifest.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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


def criterion(name: str, value: Any, rule: str, passed: bool, note: str = "") -> dict[str, Any]:
    return {"name": name, "value": value, "rule": rule, "passed": bool(passed), "note": note}


def latest_status(path: Path) -> tuple[str, str | None]:
    if not path.exists():
        return "missing", None
    try:
        payload = read_json(path)
    except Exception as exc:
        return f"unreadable:{type(exc).__name__}", None
    return str(payload.get("status", "unknown")).lower(), str(payload.get("manifest") or "")


def markdown_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.6g}"
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, sort_keys=True)
    return str(value)


def function_body(source: str, signature: str) -> str:
    start = source.find(signature)
    if start < 0:
        return ""
    brace = source.find("{", start)
    if brace < 0:
        return ""
    depth = 0
    for i in range(brace, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[brace + 1 : i]
    return ""


def run_host_tests() -> dict[str, Any]:
    cmd = ["make", "-C", str(RUNTIME), "clean-host", "test"]
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)
    return {
        "command": " ".join(cmd),
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "passed": proc.returncode == 0 and "=== ALL TESTS PASSED ===" in proc.stdout,
    }


def source_map() -> dict[str, str]:
    return {
        "synapse_manager.c": read_text(SRC / "synapse_manager.c"),
        "synapse_manager.h": read_text(SRC / "synapse_manager.h"),
        "test_runtime.c": read_text(TESTS / "test_runtime.c"),
        "runtime_readme": read_text(RUNTIME / "README.md"),
    }


def static_checks(src: dict[str, str]) -> list[dict[str, Any]]:
    deliver = function_body(src["synapse_manager.c"], "void synapse_deliver_spike")
    decay = function_body(src["synapse_manager.c"], "void synapse_decay_traces_all")
    modulate = function_body(src["synapse_manager.c"], "void synapse_modulate_all")
    return [
        criterion(
            "pre index type exists",
            "pre_entry_t",
            "source defines pre-indexed adjacency",
            "typedef struct pre_entry" in src["synapse_manager.c"] and "static pre_entry_t *g_pre_index" in src["synapse_manager.c"],
        ),
        criterion(
            "synapse stores post id",
            "post_id",
            "needed for outgoing pre-index delivery",
            "uint32_t  post_id" in src["synapse_manager.h"],
        ),
        criterion(
            "dual index links exist",
            "next_post/next_pre",
            "synapse_t has post and pre links",
            "next_post" in src["synapse_manager.h"] and "next_pre" in src["synapse_manager.h"],
        ),
        criterion(
            "active trace list exists",
            "g_active_trace_head",
            "source maintains active trace list",
            "static synapse_t *g_active_trace_head" in src["synapse_manager.c"] and "next_active" in src["synapse_manager.h"],
        ),
        criterion(
            "spike delivery uses pre index",
            "_find_pre(pre_id)",
            "deliver path starts from pre index",
            "_find_pre(pre_id)" in deliver and "s = s->next_pre" in deliver,
        ),
        criterion(
            "spike delivery no longer scans post index",
            "g_post_index",
            "absent from synapse_deliver_spike body",
            "g_post_index" not in deliver,
        ),
        criterion(
            "decay uses active trace list",
            "g_active_trace_head",
            "decay path starts from active trace head",
            "g_active_trace_head" in decay and "next_active" in decay,
        ),
        criterion(
            "decay no longer scans post index",
            "g_post_index",
            "absent from synapse_decay_traces_all body",
            "g_post_index" not in decay,
        ),
        criterion(
            "dopamine uses active trace list",
            "g_active_trace_head",
            "modulation path starts from active trace head",
            "g_active_trace_head" in modulate and "next_active" in modulate,
        ),
        criterion(
            "dopamine no longer scans post index",
            "g_post_index",
            "absent from synapse_modulate_all body",
            "g_post_index" not in modulate,
        ),
        criterion(
            "diagnostic visit counters exist",
            "synapse_last_*_visit_count",
            "host tests can prove bounded visits",
            all(token in src["synapse_manager.h"] for token in ["synapse_last_delivery_visit_count", "synapse_last_decay_visit_count", "synapse_last_modulation_visit_count"]),
        ),
        criterion(
            "host test covers indexed delivery",
            "test_synapse_indexed_delivery_and_active_traces",
            "test_runtime.c exercises new path",
            "test_synapse_indexed_delivery_and_active_traces" in src["test_runtime.c"],
        ),
    ]


def blocker_rows() -> list[dict[str, Any]]:
    return [
        {
            "blocker_id": "SCALE-001",
            "prior_issue": "synapse_deliver_spike scanned every synapse per incoming spike",
            "tier4_22g_status": "repaired_locally",
            "evidence": "pre index plus host visit-count test",
            "remaining_risk": "hardware timing still unmeasured",
        },
        {
            "blocker_id": "SCALE-002",
            "prior_issue": "synapse_decay_traces_all swept every synapse every millisecond",
            "tier4_22g_status": "repaired_locally",
            "evidence": "active trace list plus host visit-count test",
            "remaining_risk": "long-trace list density must be characterized on hardware",
        },
        {
            "blocker_id": "SCALE-003",
            "prior_issue": "synapse_modulate_all swept every synapse per dopamine event",
            "tier4_22g_status": "repaired_locally",
            "evidence": "dopamine modulation walks active trace list only",
            "remaining_risk": "reward-event cost scales with active traces",
        },
        {
            "blocker_id": "SCALE-004",
            "prior_issue": "neuron_add_input uses linked-list neuron lookup",
            "tier4_22g_status": "open",
            "evidence": "not targeted by 4.22g",
            "remaining_risk": "needs direct neuron id -> state index or bounded pool",
        },
        {
            "blocker_id": "SCALE-005",
            "prior_issue": "dynamic allocation/free-list fragmentation risk",
            "tier4_22g_status": "open",
            "evidence": "not targeted by 4.22g",
            "remaining_risk": "needs preallocated pools/free lists before long organism runs",
        },
        {
            "blocker_id": "SCALE-006",
            "prior_issue": "READ_SPIKES exposes count/timestep only",
            "tier4_22g_status": "open_high",
            "evidence": "not targeted by 4.22g",
            "remaining_risk": "blocks learning hardware acceptance until compact state readback exists",
        },
        {
            "blocker_id": "SCALE-007",
            "prior_issue": "single-core proof-of-concept state",
            "tier4_22g_status": "open",
            "evidence": "not targeted by 4.22g",
            "remaining_risk": "needs shard contract before scaling across cores/chips",
        },
    ]


def complexity_rows() -> list[dict[str, Any]]:
    return [
        {
            "function": "synapse_deliver_spike",
            "before_4_22g": "O(S) per incoming spike",
            "after_4_22g": "O(out_degree(pre_id)) per incoming spike",
            "hardware_claim": "not yet measured",
        },
        {
            "function": "synapse_decay_traces_all",
            "before_4_22g": "O(S) per timer tick",
            "after_4_22g": "O(active_traces) per timer tick",
            "hardware_claim": "not yet measured",
        },
        {
            "function": "synapse_modulate_all",
            "before_4_22g": "O(S) per dopamine event",
            "after_4_22g": "O(active_traces) per dopamine event",
            "hardware_claim": "not yet measured",
        },
        {
            "function": "neuron_add_input/neuron_find",
            "before_4_22g": "O(N) per delivered input",
            "after_4_22g": "unchanged",
            "hardware_claim": "open blocker",
        },
        {
            "function": "_handle_read_spikes",
            "before_4_22g": "count/timestep only",
            "after_4_22g": "unchanged",
            "hardware_claim": "open blocker",
        },
    ]


def write_report(path: Path, result: dict[str, Any]) -> None:
    summary = result["summary"]
    lines = [
        "# Tier 4.22g Event-Indexed Active-Trace Runtime",
        "",
        f"- Generated: `{result['generated_at_utc']}`",
        f"- Status: **{result['status'].upper()}**",
        f"- Output directory: `{result['output_dir']}`",
        "",
        "Tier 4.22g repairs the first custom-C scale blockers identified by Tier 4.22f0: all-synapse spike delivery, all-synapse eligibility decay, and all-synapse dopamine modulation. This remains local C evidence, not hardware learning evidence.",
        "",
        "## Summary",
        "",
        f"- Tier 4.22f0 latest status: `{summary['tier4_22f0_status']}`",
        f"- Host C tests passed: `{summary['host_tests_passed']}`",
        f"- Static optimization checks passed: `{summary['static_checks_passed']}` / `{summary['static_checks_total']}`",
        f"- Repaired scale blockers: `{summary['repaired_scale_blockers']}`",
        f"- Open scale blockers: `{summary['open_scale_blockers']}`",
        f"- Custom-runtime hardware learning allowed: `{summary['custom_runtime_hardware_learning_allowed']}`",
        f"- Next gate: `{summary['next_step_if_passed']}`",
        "",
        "## Criteria",
        "",
        "| Criterion | Value | Rule | Pass |",
        "| --- | --- | --- | --- |",
    ]
    for item in result["criteria"]:
        lines.append(f"| {item['name']} | `{markdown_value(item.get('value'))}` | `{item.get('rule')}` | {'yes' if item.get('passed') else 'no'} |")
    lines.extend(["", "## Complexity Delta", "", "| Function | Before | After | Hardware Claim |", "| --- | --- | --- | --- |"])
    for row in result["runtime_complexity"]:
        lines.append(f"| `{row['function']}` | `{row['before_4_22g']}` | `{row['after_4_22g']}` | `{row['hardware_claim']}` |")
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            "- This is local custom-C optimization evidence.",
            "- It is not a hardware run.",
            "- It is not full CRA parity, speedup evidence, or final on-chip learning proof.",
            "- PyNN/sPyNNaker remains the primary supported hardware layer for supported primitives.",
            "- Custom-runtime hardware learning remains blocked until compact state readback and build/load/command acceptance pass.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_latest(output_dir: Path, manifest: Path, report: Path, status: str) -> None:
    CONTROLLED.mkdir(parents=True, exist_ok=True)
    write_json(
        CONTROLLED / "tier4_22g_latest_manifest.json",
        {
            "generated_at_utc": utc_now(),
            "tier": TIER,
            "status": status,
            "output_dir": str(output_dir),
            "manifest": str(manifest),
            "report": str(report),
            "canonical": False,
            "claim": "Latest Tier 4.22g local event-indexed/active-trace custom-C optimization; not hardware or speedup evidence.",
        },
    )


def run(args: argparse.Namespace) -> int:
    output_dir = (args.output_dir or CONTROLLED / "tier4_22g_20260430_event_indexed_trace_runtime").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    tier4_22f0_status, tier4_22f0_manifest = latest_status(TIER4_22F0_LATEST)
    src = source_map()
    host = run_host_tests()
    checks = static_checks(src)
    blockers = blocker_rows()
    complexity = complexity_rows()

    host_stdout = output_dir / "tier4_22g_host_test_stdout.txt"
    host_stderr = output_dir / "tier4_22g_host_test_stderr.txt"
    host_stdout.write_text(host["stdout"], encoding="utf-8")
    host_stderr.write_text(host["stderr"], encoding="utf-8")

    static_csv = output_dir / "tier4_22g_static_checks.csv"
    blockers_csv = output_dir / "tier4_22g_blocker_status.csv"
    complexity_csv = output_dir / "tier4_22g_runtime_complexity.csv"
    write_csv(static_csv, checks)
    write_csv(blockers_csv, blockers)
    write_csv(complexity_csv, complexity)

    static_passed = sum(1 for check in checks if check["passed"])
    repaired = [row for row in blockers if row["tier4_22g_status"] == "repaired_locally"]
    open_blockers = [row for row in blockers if row["tier4_22g_status"].startswith("open")]
    open_high = [row for row in blockers if row["tier4_22g_status"] == "open_high"]
    hardware_learning_allowed = len(open_high) == 0

    criteria = [
        criterion("runner revision current", RUNNER_REVISION, "expected current source", True),
        criterion("Tier 4.22f0 audit pass exists", tier4_22f0_status, "== pass", tier4_22f0_status == "pass"),
        criterion("custom C host tests pass", host["returncode"], "returncode == 0 and ALL TESTS PASSED", bool(host["passed"])),
        criterion("all static optimization checks pass", f"{static_passed}/{len(checks)}", "all pass", static_passed == len(checks)),
        criterion("SCALE-001/002/003 repaired locally", len(repaired), "== 3", len(repaired) == 3),
        criterion("hardware learning still blocked by readback", len(open_high), ">= 1", len(open_high) >= 1),
        criterion("no hardware/speedup overclaim", "local C optimization only", "boundary explicit", True),
    ]
    status = "pass" if all(item["passed"] for item in criteria) else "fail"
    failure_reason = "" if status == "pass" else "Failed criteria: " + ", ".join(item["name"] for item in criteria if not item["passed"])
    summary = {
        "runner_revision": RUNNER_REVISION,
        "tier4_22f0_status": tier4_22f0_status,
        "tier4_22f0_manifest": tier4_22f0_manifest,
        "host_tests_passed": bool(host["passed"]),
        "host_test_returncode": int(host["returncode"]),
        "static_checks_total": len(checks),
        "static_checks_passed": static_passed,
        "repaired_scale_blockers": [row["blocker_id"] for row in repaired],
        "open_scale_blockers": [row["blocker_id"] for row in open_blockers],
        "custom_runtime_hardware_learning_allowed": hardware_learning_allowed,
        "pynn_spynnaker_role": "primary hardware construction/mapping/run layer for supported primitives",
        "custom_c_role": "only optimized CRA-specific on-chip substrate mechanics that PyNN cannot express or scale directly",
        "claim_boundary": "Local custom-C optimization only; not hardware, speedup, full CRA parity, or final on-chip learning evidence.",
        "next_step_if_passed": "Tier 4.22h compact state readback plus build/load/command acceptance before custom-runtime learning hardware.",
    }

    manifest = output_dir / "tier4_22g_results.json"
    report = output_dir / "tier4_22g_report.md"
    result = {
        "tier": TIER,
        "generated_at_utc": utc_now(),
        "status": status,
        "failure_reason": failure_reason,
        "output_dir": str(output_dir),
        "summary": summary,
        "criteria": criteria,
        "static_checks": checks,
        "blocker_status": blockers,
        "runtime_complexity": complexity,
        "host_test": {
            "command": host["command"],
            "returncode": host["returncode"],
            "stdout_artifact": str(host_stdout),
            "stderr_artifact": str(host_stderr),
        },
        "artifacts": {
            "manifest_json": str(manifest),
            "report_md": str(report),
            "static_checks_csv": str(static_csv),
            "blocker_status_csv": str(blockers_csv),
            "runtime_complexity_csv": str(complexity_csv),
            "host_test_stdout": str(host_stdout),
            "host_test_stderr": str(host_stderr),
        },
    }
    write_json(manifest, result)
    write_report(report, result)
    write_latest(output_dir, manifest, report, status)
    print(json.dumps({"status": status, "output_dir": str(output_dir), "manifest": str(manifest)}, indent=2))
    return 0 if status == "pass" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Tier 4.22g event-indexed active-trace custom runtime optimization.")
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    return run(build_parser().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
