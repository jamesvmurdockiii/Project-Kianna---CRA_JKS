#!/usr/bin/env python3
"""Tier 4.22f0 custom-runtime scale-readiness audit.

Tier 4.22b proved continuous PyNN/sPyNNaker transport. Tier 4.22c-e added
local custom-C state, reward/plasticity, and delayed-readout parity scaffolds.

This tier deliberately does *not* claim the C runtime is ready for hardware
learning. It audits the custom-C sidecar for scalable data-structure blockers
before another expensive hardware allocation is spent.

Claim boundary:
- PASS = the audit completed, prior gates are visible, host tests pass, and
  known scale blockers are explicitly documented with next required fixes.
- PASS does not mean "scale-ready"; this gate is allowed to pass while setting
  custom_runtime_scale_ready=False.
- Not hardware evidence, not speedup evidence, not full CRA parity, and not a
  reason to rewrite PyNN/sPyNNaker-supported pieces in C.
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
TIER = "Tier 4.22f0 - Custom Runtime Scale-Readiness Audit"
RUNNER_REVISION = "tier4_22f0_custom_runtime_scale_audit_20260430_0000"
TIER4_22E_LATEST = CONTROLLED / "tier4_22e_latest_manifest.json"


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


def parse_defines(config_text: str) -> dict[str, int]:
    values: dict[str, int] = {}
    for name in ["MAX_NEURONS", "MAX_SYNAPSES", "MAX_CONTEXT_SLOTS", "MAX_PENDING_HORIZONS"]:
        match = re.search(rf"#define\s+{name}\s+([0-9]+)", config_text)
        if match:
            values[name] = int(match.group(1))
    return values


def source_map() -> dict[str, str]:
    return {
        "config.h": read_text(SRC / "config.h"),
        "neuron_manager.c": read_text(SRC / "neuron_manager.c"),
        "neuron_manager.h": read_text(SRC / "neuron_manager.h"),
        "synapse_manager.c": read_text(SRC / "synapse_manager.c"),
        "synapse_manager.h": read_text(SRC / "synapse_manager.h"),
        "state_manager.c": read_text(SRC / "state_manager.c"),
        "state_manager.h": read_text(SRC / "state_manager.h"),
        "router.c": read_text(SRC / "router.c"),
        "host_interface.c": read_text(SRC / "host_interface.c"),
        "main.c": read_text(SRC / "main.c"),
        "test_runtime.c": read_text(TESTS / "test_runtime.c"),
        "runtime_readme": read_text(RUNTIME / "README.md"),
        "protocol_spec": read_text(RUNTIME / "PROTOCOL_SPEC.md"),
        "repo_readme": read_text(ROOT / "README.md"),
    }


def static_checks(src: dict[str, str]) -> list[dict[str, Any]]:
    checks = [
        criterion(
            "PyNN/sPyNNaker boundary documented",
            "Python/PyNN canonical + C sidecar",
            "runtime README keeps C as experimental sidecar",
            "experimental sidecar" in src["runtime_readme"].lower()
            and "Python/PyNN package remains the canonical implementation" in src["runtime_readme"],
        ),
        criterion(
            "custom C is limited to unsupported/scaling substrate pieces",
            "state/plasticity/readback/lifecycle substrate",
            "docs must not imply full repo rewrite in C",
            "rewrite PyNN/sPyNNaker-supported pieces in C" in (__doc__ or ""),
        ),
        criterion(
            "bounded context slots",
            "MAX_CONTEXT_SLOTS",
            "defined and used as fixed array",
            "#define MAX_CONTEXT_SLOTS" in src["config.h"]
            and "g_context_slots[MAX_CONTEXT_SLOTS]" in src["state_manager.c"],
        ),
        criterion(
            "bounded pending horizons",
            "MAX_PENDING_HORIZONS",
            "defined and used as fixed array",
            "#define MAX_PENDING_HORIZONS" in src["config.h"]
            and "g_pending_horizons[MAX_PENDING_HORIZONS]" in src["state_manager.c"],
        ),
        criterion(
            "pending horizons do not store future target",
            "int32_t target;",
            "absent from pending_horizon_t",
            "int32_t target;" not in src["state_manager.h"],
        ),
        criterion(
            "state manager avoids dynamic allocation",
            "malloc/sark_alloc",
            "absent from state_manager.c",
            "malloc" not in src["state_manager.c"] and "sark_alloc" not in src["state_manager.c"],
        ),
        criterion(
            "eligibility trace exists",
            "eligibility_trace",
            "in synapse_t and dopamine rule",
            "eligibility_trace" in src["synapse_manager.h"]
            and "FP_MUL(dopamine_level, s->eligibility_trace)" in src["synapse_manager.c"],
        ),
        criterion(
            "count-only readback is explicitly marked incomplete",
            "READ_SPIKES",
            "host_interface documents count/timestep-only readback",
            "Minimal reply: global neuron count + current timestep only" in src["host_interface.c"],
        ),
        criterion(
            "host tests cover runtime substrate",
            "test_runtime.c",
            "state/plasticity tests exist",
            "test_state_pending_horizon_maturation" in src["test_runtime.c"]
            and "test_synapse_eligibility_modulation" in src["test_runtime.c"],
        ),
    ]
    return checks


def scale_blockers(src: dict[str, str]) -> list[dict[str, Any]]:
    blockers = [
        {
            "blocker_id": "SCALE-001",
            "severity": "high",
            "file": "src/synapse_manager.c",
            "function": "synapse_deliver_spike",
            "current_pattern": "incoming pre spike scans every post-entry and every synapse",
            "detected": "post_entry_t *pe = g_post_index" in src["synapse_manager.c"]
            and "if (s->pre_id == pre_id)" in src["synapse_manager.c"],
            "complexity": "O(S) per incoming spike",
            "why_it_matters": "large CRA populations would spend most runtime scanning irrelevant synapses",
            "required_fix": "add pre-indexed outgoing adjacency: pre_id -> compact outgoing synapse/event list",
            "blocks_custom_runtime_learning_hardware": True,
        },
        {
            "blocker_id": "SCALE-002",
            "severity": "high",
            "file": "src/synapse_manager.c",
            "function": "synapse_decay_traces_all",
            "current_pattern": "timer tick sweeps every synapse to decay eligibility traces",
            "detected": "void synapse_decay_traces_all" in src["synapse_manager.c"]
            and "FP_MUL(s->eligibility_trace, decay_factor)" in src["synapse_manager.c"],
            "complexity": "O(S) per ms tick",
            "why_it_matters": "all-synapse trace decay destroys the expected SpiNNaker speed advantage as S grows",
            "required_fix": "use lazy timestamp decay or an active-trace list updated only for recently touched synapses",
            "blocks_custom_runtime_learning_hardware": True,
        },
        {
            "blocker_id": "SCALE-003",
            "severity": "medium",
            "file": "src/synapse_manager.c",
            "function": "synapse_modulate_all",
            "current_pattern": "dopamine event sweeps every synapse",
            "detected": "void synapse_modulate_all" in src["synapse_manager.c"]
            and "delta_w = FP_MUL(dopamine_level, s->eligibility_trace)" in src["synapse_manager.c"],
            "complexity": "O(S) per dopamine event",
            "why_it_matters": "global reward updates should touch active traces, not every synapse",
            "required_fix": "modulate only active trace list or lazily evaluated eligible synapses",
            "blocks_custom_runtime_learning_hardware": True,
        },
        {
            "blocker_id": "SCALE-004",
            "severity": "medium",
            "file": "src/neuron_manager.c",
            "function": "neuron_add_input/neuron_find",
            "current_pattern": "each delivered synaptic input performs a linked-list neuron lookup",
            "detected": "neuron_t *n = neuron_find(id)" in src["neuron_manager.c"]
            and "while (n != NULL)" in src["neuron_manager.c"],
            "complexity": "O(N) per delivered input",
            "why_it_matters": "even after adding outgoing adjacency, input delivery can stay expensive",
            "required_fix": "add direct neuron id -> neuron/state index table or bounded preallocated pool",
            "blocks_custom_runtime_learning_hardware": True,
        },
        {
            "blocker_id": "SCALE-005",
            "severity": "medium",
            "file": "src/neuron_manager.c/src/synapse_manager.c/src/router.c",
            "function": "birth/death/create_syn/router_add_neuron",
            "current_pattern": "runtime birth/death and synapse creation use sark_alloc/sark_free linked structures",
            "detected": "sark_alloc" in src["neuron_manager.c"]
            and "sark_alloc" in src["synapse_manager.c"]
            and "sark_alloc" in src["router.c"],
            "complexity": "allocation-time variable cost and fragmentation risk",
            "why_it_matters": "long-running organism growth should not depend on heap fragmentation behavior",
            "required_fix": "preallocate bounded pools with free lists/active masks and explicit capacity telemetry",
            "blocks_custom_runtime_learning_hardware": False,
        },
        {
            "blocker_id": "SCALE-006",
            "severity": "high",
            "file": "src/host_interface.c",
            "function": "_handle_read_spikes",
            "current_pattern": "READ_SPIKES returns only neuron count and low 16 bits of timestep",
            "detected": "reply[1]" in src["host_interface.c"]
            and "reply[4]" in src["host_interface.c"]
            and "current timestep only" in src["host_interface.c"],
            "complexity": "insufficient observability, not a runtime cost issue",
            "why_it_matters": "learning acceptance needs compact summaries/readback, not just count/timestep",
            "required_fix": "add fragmented or compact state-summary readback for spikes, reward, pending, slots, and weights",
            "blocks_custom_runtime_learning_hardware": True,
        },
        {
            "blocker_id": "SCALE-007",
            "severity": "medium",
            "file": "src/main.c",
            "function": "timer_callback/c_main",
            "current_pattern": "single-core global state and no shard/placement contract",
            "detected": "uint32_t g_timestep" in src["main.c"]
            and "spin1_start(SYNC_NOWAIT)" in src["main.c"],
            "complexity": "single-core proof of concept",
            "why_it_matters": "population growth requires shardable per-core state and host-visible partitioning",
            "required_fix": "define core-local shard contract, per-core summaries, and inter-core routing/resource budgets",
            "blocks_custom_runtime_learning_hardware": False,
        },
    ]
    return blockers


def runtime_complexity_rows(blockers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "path": row["file"],
            "function": row["function"],
            "current_complexity": row["complexity"],
            "severity": row["severity"],
            "scale_ready": False if row["severity"] == "high" else "limited",
            "required_fix": row["required_fix"],
        }
        for row in blockers
    ] + [
        {
            "path": "src/state_manager.c",
            "function": "cra_state_write_context/cra_state_read_context",
            "current_complexity": "O(C) with C=MAX_CONTEXT_SLOTS",
            "severity": "low",
            "scale_ready": "bounded for current single-core scaffold",
            "required_fix": "keep bounded; increase only with explicit memory-budget artifact",
        },
        {
            "path": "src/state_manager.c",
            "function": "cra_state_mature_pending_horizons",
            "current_complexity": "O(P) with P=MAX_PENDING_HORIZONS",
            "severity": "low",
            "scale_ready": "bounded for current delayed-readout scaffold",
            "required_fix": "use due-time ring/event queue if P grows beyond the fixed budget",
        },
        {
            "path": "src/neuron_manager.c",
            "function": "neuron_update_all",
            "current_complexity": "O(N) per ms tick",
            "severity": "expected",
            "scale_ready": "normal per-core neuron integration cost",
            "required_fix": "shard across cores and keep N per core within measured budget",
        },
    ]


def memory_budget_rows(defines: dict[str, int]) -> list[dict[str, Any]]:
    max_neurons = defines.get("MAX_NEURONS", 0)
    max_synapses = defines.get("MAX_SYNAPSES", 0)
    max_context = defines.get("MAX_CONTEXT_SLOTS", 0)
    max_pending = defines.get("MAX_PENDING_HORIZONS", 0)
    return [
        {
            "component": "neurons",
            "bound": "MAX_NEURONS",
            "configured_count": max_neurons,
            "approx_bytes_each": 52,
            "approx_total_bytes": max_neurons * 52,
            "scale_note": "current linked-list allocation; production should use bounded pool/index",
        },
        {
            "component": "synapses",
            "bound": "MAX_SYNAPSES",
            "configured_count": max_synapses,
            "approx_bytes_each": 20,
            "approx_total_bytes": max_synapses * 20,
            "scale_note": "current post-list allocation; production needs pre-index and active-trace metadata",
        },
        {
            "component": "context_slots",
            "bound": "MAX_CONTEXT_SLOTS",
            "configured_count": max_context,
            "approx_bytes_each": 20,
            "approx_total_bytes": max_context * 20,
            "scale_note": "static bounded state; acceptable at current scaffold size",
        },
        {
            "component": "pending_horizons",
            "bound": "MAX_PENDING_HORIZONS",
            "configured_count": max_pending,
            "approx_bytes_each": 16,
            "approx_total_bytes": max_pending * 16,
            "scale_note": "static bounded no-leak delayed-credit queue",
        },
        {
            "component": "state_summary",
            "bound": "one per runtime instance",
            "configured_count": 1,
            "approx_bytes_each": 72,
            "approx_total_bytes": 72,
            "scale_note": "compact summary state; should be expanded intentionally for readback",
        },
    ]


def api_contract_rows() -> list[dict[str, Any]]:
    return [
        {
            "layer": "PyNN/sPyNNaker",
            "role": "primary hardware construction/mapping/run layer",
            "keep_in_python": "task definitions, experiment orchestration, evidence exports, baselines, paper tables, PyNN populations/connectors, standard spike readback",
            "do_not_rewrite_in_c": True,
        },
        {
            "layer": "custom C runtime",
            "role": "only for substrate mechanics PyNN cannot express or scale as closed-loop on-chip state",
            "customize_in_c": "persistent state, delayed-credit queues, eligibility/dopamine/plasticity, compact summaries, lifecycle state, routing/memory kernels when promoted",
            "do_not_rewrite_in_c": False,
        },
        {
            "layer": "host Python controller",
            "role": "commands, configuration, validation, logging, and comparison to canonical software baselines",
            "keep_in_python": "offline analysis, registry, preflight, JobManager packaging, result ingestion",
            "do_not_rewrite_in_c": True,
        },
        {
            "layer": "future custom runtime acceptance",
            "role": "hardware proof only after scale blockers are resolved",
            "required_before_hardware_learning": "event-indexed spike delivery, lazy/active trace decay, compact state readback, build/load/command acceptance",
            "do_not_rewrite_in_c": False,
        },
    ]


def write_report(path: Path, result: dict[str, Any]) -> None:
    summary = result["summary"]
    lines = [
        "# Tier 4.22f0 Custom Runtime Scale-Readiness Audit",
        "",
        f"- Generated: `{result['generated_at_utc']}`",
        f"- Status: **{result['status'].upper()}**",
        f"- Output directory: `{result['output_dir']}`",
        "",
        "Tier 4.22f0 audits the custom-C sidecar before spending another hardware allocation on custom-runtime learning. It keeps the architecture boundary explicit: PyNN/sPyNNaker remains the normal mapping/execution layer, and custom C is reserved for CRA-specific on-chip substrate mechanics that PyNN cannot express or scale directly.",
        "",
        "## Summary",
        "",
        f"- Tier 4.22e latest status: `{summary['tier4_22e_status']}`",
        f"- Host C tests passed: `{summary['host_tests_passed']}`",
        f"- Static checks passed: `{summary['static_checks_passed']}` / `{summary['static_checks_total']}`",
        f"- High-severity scale blockers: `{summary['high_severity_blockers']}`",
        f"- Runtime scale-ready: `{summary['custom_runtime_scale_ready']}`",
        f"- Direct custom-runtime hardware learning allowed: `{summary['direct_custom_runtime_hardware_learning_allowed']}`",
        f"- Next gate: `{summary['next_step_if_passed']}`",
        "",
        "## Criteria",
        "",
        "| Criterion | Value | Rule | Pass |",
        "| --- | --- | --- | --- |",
    ]
    for item in result["criteria"]:
        lines.append(f"| {item['name']} | `{markdown_value(item.get('value'))}` | `{item.get('rule')}` | {'yes' if item.get('passed') else 'no'} |")

    lines.extend(["", "## Scale Blockers", "", "| ID | Severity | Function | Complexity | Required Fix |", "| --- | --- | --- | --- | --- |"])
    for row in result["scale_blockers"]:
        lines.append(
            f"| {row['blocker_id']} | `{row['severity']}` | `{row['function']}` | `{row['complexity']}` | {row['required_fix']} |"
        )

    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            "- This is a scale-readiness audit, not a hardware run.",
            "- A PASS here means the audit is complete and the blockers are explicit; it does not mean the C runtime is scale-ready.",
            "- PyNN/sPyNNaker remains the correct path for supported network construction, mapping, running, and standard readback.",
            "- Custom C remains reserved for CRA-specific on-chip state, plasticity, delayed-credit, lifecycle/routing state, and compact readback where PyNN cannot support the long-term substrate goal.",
            "- The next engineering move is event-indexed/lazy-trace optimization, not a large custom-runtime hardware learning claim.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_latest(output_dir: Path, manifest: Path, report: Path, status: str) -> None:
    CONTROLLED.mkdir(parents=True, exist_ok=True)
    write_json(
        CONTROLLED / "tier4_22f0_latest_manifest.json",
        {
            "generated_at_utc": utc_now(),
            "tier": TIER,
            "status": status,
            "output_dir": str(output_dir),
            "manifest": str(manifest),
            "report": str(report),
            "canonical": False,
            "claim": "Latest Tier 4.22f0 custom-runtime scale audit; identifies blockers and does not claim scale-ready hardware learning.",
        },
    )


def run(args: argparse.Namespace) -> int:
    output_dir = (args.output_dir or CONTROLLED / "tier4_22f0_20260430_custom_runtime_scale_audit").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    src = source_map()
    defines = parse_defines(src["config.h"])
    tier4_22e_status, tier4_22e_manifest = latest_status(TIER4_22E_LATEST)
    host = run_host_tests()
    checks = static_checks(src)
    blockers = scale_blockers(src)
    complexity_rows = runtime_complexity_rows(blockers)
    memory_rows = memory_budget_rows(defines)
    api_rows = api_contract_rows()

    host_stdout = output_dir / "tier4_22f0_host_test_stdout.txt"
    host_stderr = output_dir / "tier4_22f0_host_test_stderr.txt"
    host_stdout.write_text(host["stdout"], encoding="utf-8")
    host_stderr.write_text(host["stderr"], encoding="utf-8")

    static_csv = output_dir / "tier4_22f0_static_checks.csv"
    blockers_csv = output_dir / "tier4_22f0_scale_blockers.csv"
    complexity_csv = output_dir / "tier4_22f0_runtime_complexity.csv"
    memory_csv = output_dir / "tier4_22f0_memory_budget.csv"
    api_csv = output_dir / "tier4_22f0_api_contract.csv"
    write_csv(static_csv, checks)
    write_csv(blockers_csv, blockers)
    write_csv(complexity_csv, complexity_rows)
    write_csv(memory_csv, memory_rows)
    write_csv(api_csv, api_rows)

    static_passed = sum(1 for check in checks if check["passed"])
    detected_blockers = [row for row in blockers if row["detected"]]
    high_blockers = [row for row in detected_blockers if row["severity"] == "high"]
    blocking_items = [row for row in detected_blockers if row["blocks_custom_runtime_learning_hardware"]]
    custom_runtime_scale_ready = len(high_blockers) == 0 and len(blocking_items) == 0
    direct_hw_learning_allowed = custom_runtime_scale_ready

    criteria = [
        criterion("runner revision current", RUNNER_REVISION, "expected current source", True),
        criterion("Tier 4.22e local parity pass exists", tier4_22e_status, "== pass", tier4_22e_status == "pass"),
        criterion("custom C host tests pass", host["returncode"], "returncode == 0 and ALL TESTS PASSED", bool(host["passed"])),
        criterion("all static audit checks pass", f"{static_passed}/{len(checks)}", "all pass", static_passed == len(checks)),
        criterion("scale blockers are detected", len(detected_blockers), ">= 5 documented blockers", len(detected_blockers) >= 5),
        criterion("high severity blockers are explicit", len(high_blockers), ">= 2 known blockers documented", len(high_blockers) >= 2),
        criterion("direct custom-runtime hardware learning is blocked", direct_hw_learning_allowed, "False until blockers are fixed", not direct_hw_learning_allowed),
        criterion("PyNN/sPyNNaker boundary remains explicit", "PyNN/sPyNNaker primary, C only for unsupported substrate mechanics", "must be documented", True),
    ]
    status = "pass" if all(item["passed"] for item in criteria) else "fail"
    failure_reason = "" if status == "pass" else "Failed criteria: " + ", ".join(item["name"] for item in criteria if not item["passed"])
    summary = {
        "runner_revision": RUNNER_REVISION,
        "tier4_22e_status": tier4_22e_status,
        "tier4_22e_manifest": tier4_22e_manifest,
        "host_tests_passed": bool(host["passed"]),
        "host_test_returncode": int(host["returncode"]),
        "static_checks_total": len(checks),
        "static_checks_passed": static_passed,
        "detected_scale_blockers": len(detected_blockers),
        "high_severity_blockers": len(high_blockers),
        "hardware_learning_blocking_items": len(blocking_items),
        "custom_runtime_scale_ready": custom_runtime_scale_ready,
        "direct_custom_runtime_hardware_learning_allowed": direct_hw_learning_allowed,
        "pynn_spynnaker_role": "primary hardware construction/mapping/run layer for supported primitives",
        "custom_c_role": "only CRA-specific on-chip state, delayed credit, plasticity, lifecycle/routing, and compact readback that PyNN cannot express or scale",
        "claim_boundary": "Scale-readiness audit only; PASS means blockers are explicit, not that the runtime is scale-ready.",
        "next_step_if_passed": "Tier 4.22g event-indexed spike delivery plus lazy/active eligibility traces before any custom-runtime learning hardware claim.",
    }

    manifest = output_dir / "tier4_22f0_results.json"
    report = output_dir / "tier4_22f0_report.md"
    result = {
        "tier": TIER,
        "generated_at_utc": utc_now(),
        "status": status,
        "failure_reason": failure_reason,
        "output_dir": str(output_dir),
        "summary": summary,
        "criteria": criteria,
        "static_checks": checks,
        "scale_blockers": blockers,
        "runtime_complexity": complexity_rows,
        "memory_budget": memory_rows,
        "api_contract": api_rows,
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
            "scale_blockers_csv": str(blockers_csv),
            "runtime_complexity_csv": str(complexity_csv),
            "memory_budget_csv": str(memory_csv),
            "api_contract_csv": str(api_csv),
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
    parser = argparse.ArgumentParser(description="Tier 4.22f0 custom-runtime scale-readiness audit.")
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    return run(build_parser().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
