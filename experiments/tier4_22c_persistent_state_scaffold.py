#!/usr/bin/env python3
"""Tier 4.22c persistent on-chip state scaffold.

This tier moves the runtime path one step closer to the real destination:
full custom/on-chip CRA execution. It does not claim learning yet. It proves the
custom C runtime now has a bounded, static, test-covered state owner for keyed
context slots, readout state, decision counters, and reward counters.

Claim boundary:
- PASS = custom C host tests and static checks show persistent CRA state can be
  owned by the runtime in a chip-friendly, bounded form.
- Not a hardware run, not on-chip learning, not speedup evidence, and not a
  replacement for the later reward/plasticity parity gate.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"
RUNTIME = ROOT / "coral_reef_spinnaker" / "spinnaker_runtime"
SRC = RUNTIME / "src"
TESTS = RUNTIME / "tests"
TIER = "Tier 4.22c - Persistent On-Chip State Scaffold"
RUNNER_REVISION = "tier4_22c_persistent_state_scaffold_20260430_0000"
TIER4_22B_LATEST = CONTROLLED / "tier4_22b_latest_manifest.json"


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


def static_contract_checks() -> list[dict[str, Any]]:
    config = read_text(SRC / "config.h")
    header = read_text(SRC / "state_manager.h")
    source = read_text(SRC / "state_manager.c")
    main = read_text(SRC / "main.c")
    host = read_text(SRC / "host_interface.c")
    makefile = read_text(RUNTIME / "Makefile")
    tests = read_text(TESTS / "test_runtime.c")

    checks = [
        criterion("state_manager header exists", str(SRC / "state_manager.h"), "file exists", (SRC / "state_manager.h").exists()),
        criterion("state_manager source exists", str(SRC / "state_manager.c"), "file exists", (SRC / "state_manager.c").exists()),
        criterion("bounded context slot constant", "MAX_CONTEXT_SLOTS", "defined in config.h", "#define MAX_CONTEXT_SLOTS" in config),
        criterion("bounded pending horizon constant", "MAX_PENDING_HORIZONS", "defined in config.h", "#define MAX_PENDING_HORIZONS" in config),
        criterion("static slot table", "g_context_slots[MAX_CONTEXT_SLOTS]", "static fixed-size array", "static context_slot_t g_context_slots[MAX_CONTEXT_SLOTS]" in source),
        criterion("static pending horizon table", "g_pending_horizons[MAX_PENDING_HORIZONS]", "static fixed-size array", "static pending_horizon_t g_pending_horizons[MAX_PENDING_HORIZONS]" in source),
        criterion("state manager avoids dynamic allocation", "malloc/sark_alloc", "not present in state_manager.c", "malloc" not in source and "sark_alloc" not in source),
        criterion("state init integrated into runtime", "cra_state_init", "called from main.c", "cra_state_init();" in main),
        criterion("state reset integrated into runtime reset", "cra_state_reset", "called from host_interface.c", "cra_state_reset();" in host),
        criterion("state source in runtime build", "src/state_manager.c", "included in Makefile", "src/state_manager.c" in makefile),
        criterion("host tests cover state manager", "state_manager", "test_runtime.c exercises state", "test_state_context_slots" in tests and "test_state_slot_eviction" in tests),
        criterion("summary API exists", "cra_state_get_summary", "declared and implemented", "cra_state_get_summary" in header and "void cra_state_get_summary" in source),
        criterion("reward counter exists", "cra_state_record_reward", "declared and implemented", "cra_state_record_reward" in header and "void cra_state_record_reward" in source),
        criterion("readout state exists", "cra_state_set_readout/cra_state_predict_readout", "declared and implemented", "cra_state_set_readout" in header and "cra_state_predict_readout" in header and "cra_state_predict_readout" in source),
        criterion("bounded pending horizon API exists", "cra_state_schedule_pending_horizon/cra_state_mature_pending_horizons", "declared and implemented", "cra_state_schedule_pending_horizon" in header and "cra_state_mature_pending_horizons" in header and "cra_state_schedule_pending_horizon" in source and "cra_state_mature_pending_horizons" in source),
        criterion("pending horizons do not store future target", "int32_t target;", "absent from pending_horizon_t", "int32_t target;" not in header),
    ]
    return checks


def state_contract_rows() -> list[dict[str, Any]]:
    return [
        {
            "state_component": "keyed_context_slots",
            "runtime_owner": "custom_c_runtime",
            "storage": "static context_slot_t g_context_slots[MAX_CONTEXT_SLOTS]",
            "bound": "MAX_CONTEXT_SLOTS",
            "current_scope": "persistent bounded state scaffold",
            "next_required_gate": "Tier 4.22d reward/plasticity path must use this state causally",
        },
        {
            "state_component": "readout_state",
            "runtime_owner": "custom_c_runtime",
            "storage": "cra_state_summary_t readout_weight/readout_bias/last_feature/last_prediction",
            "bound": "single fixed-point readout summary per runtime instance",
            "current_scope": "persistent state and prediction primitive",
            "next_required_gate": "Tier 4.22d must validate reward-modulated updates against reference",
        },
        {
            "state_component": "decision_reward_counters",
            "runtime_owner": "custom_c_runtime",
            "storage": "cra_state_summary_t decisions/reward_events/last_reward",
            "bound": "uint32 counters and fixed-point reward",
            "current_scope": "auditable summaries for host readback",
            "next_required_gate": "Tier 4.22d must wire reward delivery and plasticity semantics",
        },
        {
            "state_component": "pending_delayed_credit_queue",
            "runtime_owner": "custom_c_runtime",
            "storage": "static pending_horizon_t g_pending_horizons[MAX_PENDING_HORIZONS]",
            "bound": "MAX_PENDING_HORIZONS",
            "current_scope": "bounded delayed-credit prediction queue without future target leakage",
            "next_required_gate": "Tier 4.22e must verify fixed-point delayed-readout parity against a no-leak reference",
        },
        {
            "state_component": "reset_semantics",
            "runtime_owner": "custom_c_runtime",
            "storage": "cra_state_reset clears slots/readout/counters and records reset count",
            "bound": "deterministic reset event",
            "current_scope": "repeatable run hygiene",
            "next_required_gate": "Tier 4.22d and later hardware runs must expose reset provenance",
        },
    ]


def write_report(path: Path, result: dict[str, Any]) -> None:
    summary = result["summary"]
    lines = [
        "# Tier 4.22c Persistent On-Chip State Scaffold",
        "",
        f"- Generated: `{result['generated_at_utc']}`",
        f"- Status: **{result['status'].upper()}**",
        f"- Output directory: `{result['output_dir']}`",
        "",
        "Tier 4.22c is the first concrete custom-C state-ownership step after the continuous transport pass. It does not claim learning yet. It proves the runtime now owns bounded persistent state that later reward/plasticity code can use without a Python-side dictionary or per-step host ledger.",
        "",
        "## North Star",
        "",
        "The project target is full custom/on-chip CRA execution. Hybrid host paths remain transitional diagnostics only. This tier moves state ownership toward that target; Tier 4.22d must move reward/plasticity into the same audited runtime path.",
        "",
        "## Summary",
        "",
        f"- Tier 4.22b latest status: `{summary['tier4_22b_status']}`",
        f"- Host C tests passed: `{summary['host_tests_passed']}`",
        f"- Static contract checks passed: `{summary['static_checks_passed']}` / `{summary['static_checks_total']}`",
        f"- Runtime state owner: `{summary['runtime_state_owner']}`",
        f"- Dynamic allocation in state manager: `{summary['dynamic_allocation_in_state_manager']}`",
        f"- Next gate: `{summary['next_step_if_passed']}`",
        "",
        "## Criteria",
        "",
        "| Criterion | Value | Rule | Pass |",
        "| --- | --- | --- | --- |",
    ]
    for item in result["criteria"]:
        lines.append(f"| {item['name']} | `{markdown_value(item.get('value'))}` | `{item.get('rule')}` | {'yes' if item.get('passed') else 'no'} |")
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            "- This is custom-C persistent-state scaffold evidence.",
            "- It is not a hardware run.",
            "- It is not on-chip learning, reward-modulated plasticity, speedup evidence, or full CRA deployment.",
            "- It is required groundwork for Tier 4.22d reward/plasticity and later full custom runtime work.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_latest(output_dir: Path, manifest: Path, report: Path, status: str) -> None:
    CONTROLLED.mkdir(parents=True, exist_ok=True)
    write_json(
        CONTROLLED / "tier4_22c_latest_manifest.json",
        {
            "generated_at_utc": utc_now(),
            "tier": TIER,
            "status": status,
            "output_dir": str(output_dir),
            "manifest": str(manifest),
            "report": str(report),
            "canonical": False,
            "claim": "Latest Tier 4.22c persistent custom-C state scaffold; not hardware or on-chip learning evidence.",
        },
    )


def run(args: argparse.Namespace) -> int:
    output_dir = (args.output_dir or CONTROLLED / "tier4_22c_20260430_persistent_state_scaffold").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    tier4_22b_status, tier4_22b_manifest = latest_status(TIER4_22B_LATEST)
    host = run_host_tests()
    checks = static_contract_checks()
    contract_rows = state_contract_rows()

    host_stdout = output_dir / "tier4_22c_host_test_stdout.txt"
    host_stderr = output_dir / "tier4_22c_host_test_stderr.txt"
    host_stdout.write_text(host["stdout"], encoding="utf-8")
    host_stderr.write_text(host["stderr"], encoding="utf-8")

    static_csv = output_dir / "tier4_22c_static_compliance.csv"
    contract_csv = output_dir / "tier4_22c_state_contract.csv"
    write_csv(static_csv, checks)
    write_csv(contract_csv, contract_rows)

    static_passed = sum(1 for check in checks if check["passed"])
    criteria = [
        criterion("runner revision current", RUNNER_REVISION, "expected current source", True),
        criterion("Tier 4.22b continuous transport pass exists", tier4_22b_status, "== pass", tier4_22b_status == "pass"),
        criterion("custom C host tests pass", host["returncode"], "returncode == 0 and ALL TESTS PASSED", bool(host["passed"])),
        criterion("all static state checks pass", f"{static_passed}/{len(checks)}", "all pass", static_passed == len(checks)),
        criterion("state manager uses static bounded storage", "MAX_CONTEXT_SLOTS", "bounded fixed-size state", any(check["name"] == "static slot table" and check["passed"] for check in checks)),
        criterion("state manager avoids dynamic allocation", "malloc/sark_alloc absent", "no dynamic allocation in state_manager.c", any(check["name"] == "state manager avoids dynamic allocation" and check["passed"] for check in checks)),
        criterion("full on-chip target explicit", "full custom/on-chip CRA execution", "hybrid is transitional only", True),
    ]
    status = "pass" if all(item["passed"] for item in criteria) else "fail"
    failure_reason = "" if status == "pass" else "Failed criteria: " + ", ".join(item["name"] for item in criteria if not item["passed"])
    summary = {
        "runner_revision": RUNNER_REVISION,
        "tier4_22b_status": tier4_22b_status,
        "tier4_22b_manifest": tier4_22b_manifest,
        "host_tests_passed": bool(host["passed"]),
        "host_test_returncode": int(host["returncode"]),
        "static_checks_total": len(checks),
        "static_checks_passed": static_passed,
        "runtime_state_owner": "custom_c_runtime",
        "runtime_state_storage": "static bounded arrays and fixed-point summary fields",
        "dynamic_allocation_in_state_manager": False,
        "north_star": "full custom/on-chip CRA runtime; hybrid host paths are transitional diagnostics",
        "claim_boundary": "Persistent state scaffold only; not hardware, learning, reward/plasticity, or speedup evidence.",
        "next_step_if_passed": "Tier 4.22d reward/plasticity path: use this persistent C state for dopamine/reward and compare against the chunked reference.",
    }

    manifest = output_dir / "tier4_22c_results.json"
    report = output_dir / "tier4_22c_report.md"
    result = {
        "tier": TIER,
        "generated_at_utc": utc_now(),
        "status": status,
        "failure_reason": failure_reason,
        "output_dir": str(output_dir),
        "summary": summary,
        "criteria": criteria,
        "static_checks": checks,
        "state_contract": contract_rows,
        "host_test": {
            "command": host["command"],
            "returncode": host["returncode"],
            "stdout_artifact": str(host_stdout),
            "stderr_artifact": str(host_stderr),
        },
        "artifacts": {
            "manifest_json": str(manifest),
            "report_md": str(report),
            "static_compliance_csv": str(static_csv),
            "state_contract_csv": str(contract_csv),
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
    parser = argparse.ArgumentParser(description="Tier 4.22c persistent custom-C state scaffold.")
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    return run(build_parser().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
