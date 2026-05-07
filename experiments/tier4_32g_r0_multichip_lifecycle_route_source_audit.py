#!/usr/bin/env python3
"""Tier 4.32g-r0 multi-chip lifecycle route/source repair audit.

This is a local source/runtime QA gate after Tier 4.32f. It does not package or
run EBRAINS hardware. It proves the missing lifecycle MCPL route source support
that 4.32f identified before authorizing a bounded two-chip lifecycle
traffic/resource hardware smoke.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"
RUNTIME = ROOT / "coral_reef_spinnaker" / "spinnaker_runtime"
RUNTIME_SRC = RUNTIME / "src"
RUNTIME_TESTS = RUNTIME / "tests"

TIER = "Tier 4.32g-r0 - Multi-Chip Lifecycle Route/Source Repair Audit"
RUNNER_REVISION = "tier4_32g_r0_lifecycle_route_source_audit_20260507_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier4_32g_r0_20260507_lifecycle_route_source_audit"
LATEST_MANIFEST = CONTROLLED / "tier4_32g_r0_latest_manifest.json"

TIER4_32F = CONTROLLED / "tier4_32f_20260507_multichip_resource_lifecycle_decision" / "tier4_32f_results.json"
TIER4_32E = CONTROLLED / "tier4_32e_20260507_hardware_pass_ingested" / "tier4_32e_results.json"

CLAIM_BOUNDARY = (
    "Tier 4.32g-r0 is local source/route QA only. It source-proves lifecycle "
    "event/trophic/mask-sync inter-chip MCPL route support before a hardware "
    "package. It is not SpiNNaker hardware evidence, not lifecycle scaling, "
    "not speedup evidence, not benchmark superiority, not true two-partition "
    "learning, not multi-shard learning, and not a native-scale baseline freeze."
)


@dataclass(frozen=True)
class Criterion:
    name: str
    value: Any
    rule: str
    passed: bool
    note: str = ""


@dataclass(frozen=True)
class SourceFinding:
    finding_id: str
    file: str
    token: str
    present: bool
    purpose: str


@dataclass(frozen=True)
class RouteContract:
    route_id: str
    profile: str
    key: str
    mask: str
    route: str
    purpose: str
    required_for_4_32g: bool


@dataclass(frozen=True)
class TestCommand:
    command_id: str
    command: str
    returncode: int
    stdout_file: str
    stderr_file: str
    passed: bool
    purpose: str


@dataclass(frozen=True)
class NextGate:
    gate: str
    decision: str
    question: str
    prerequisites: str
    pass_case: str
    fail_case: str
    claim_boundary: str


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "__dataclass_fields__"):
        return json_safe(asdict(value))
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    return value


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json_safe(row.get(key, "")) for key in keys})


def criterion(name: str, value: Any, rule: str, passed: bool, note: str = "") -> Criterion:
    return Criterion(name=name, value=value, rule=rule, passed=bool(passed), note=note)


def source_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def source_findings() -> list[SourceFinding]:
    config_h = RUNTIME_SRC / "config.h"
    state_c = RUNTIME_SRC / "state_manager.c"
    state_h = RUNTIME_SRC / "state_manager.h"
    runtime_make = RUNTIME / "Makefile"
    test_c = RUNTIME_TESTS / "test_mcpl_lifecycle_interchip_route_contract.c"
    rows = [
        ("event_msg_type", config_h, "MCPL_MSG_LIFECYCLE_EVENT_REQUEST", "Lifecycle event request message type exists."),
        ("trophic_msg_type", config_h, "MCPL_MSG_LIFECYCLE_TROPHIC_UPDATE", "Lifecycle trophic update message type exists."),
        ("sync_msg_type", config_h, "MCPL_MSG_LIFECYCLE_ACTIVE_MASK_SYNC", "Lifecycle active-mask/lineage sync message type exists."),
        ("request_route_macro", state_c, "CRA_MCPL_INTERCHIP_LIFECYCLE_REQUEST_LINK_ROUTE", "Learning/source core can install outbound lifecycle request link routes."),
        ("sync_route_macro", state_c, "CRA_MCPL_INTERCHIP_LIFECYCLE_SYNC_LINK_ROUTE", "Lifecycle core can install outbound active-mask sync link routes."),
        ("event_route_install", state_c, "MCPL_MSG_LIFECYCLE_EVENT_REQUEST, 0, 0", "Route install code references lifecycle event request keys."),
        ("trophic_route_install", state_c, "MCPL_MSG_LIFECYCLE_TROPHIC_UPDATE, 0, 0", "Route install code references lifecycle trophic update keys."),
        ("sync_route_install", state_c, "MCPL_MSG_LIFECYCLE_ACTIVE_MASK_SYNC, 0, 0", "Route install code references active-mask sync keys."),
        ("duplicate_counter", state_h, "lifecycle_duplicate_events", "Duplicate lifecycle events are counted."),
        ("stale_counter", state_h, "lifecycle_stale_events", "Stale lifecycle events are counted."),
        ("missing_ack_counter", state_h, "lifecycle_missing_acks", "Missing lifecycle acks are counted."),
        ("route_contract_test", test_c, "Tier 4.32g-r0 lifecycle MCPL inter-chip route contract tests", "Local C route contract test exists."),
        ("make_target", runtime_make, "test-mcpl-lifecycle-interchip-route-contract", "Runtime Makefile exposes the lifecycle route contract test."),
    ]
    return [
        SourceFinding(
            finding_id=finding_id,
            file=rel(path),
            token=token,
            present=path.exists() and token in source_text(path),
            purpose=purpose,
        )
        for finding_id, path, token, purpose in rows
    ]


def route_contract() -> list[RouteContract]:
    mask = "0xFFF0F000 (match app/msg/shard; ignore lifecycle subtype and seq)"
    return [
        RouteContract(
            "learning_local_mask_sync_consumer",
            "learning_core",
            "MAKE_MCPL_KEY(APP_ID, MCPL_MSG_LIFECYCLE_ACTIVE_MASK_SYNC, 0, 0)",
            mask,
            "MC_CORE_ROUTE(learning_core)",
            "learning/consumer core receives lifecycle active-mask and lineage sync packets",
            True,
        ),
        RouteContract(
            "learning_outbound_lifecycle_event",
            "learning_core",
            "MAKE_MCPL_KEY(APP_ID, MCPL_MSG_LIFECYCLE_EVENT_REQUEST, 0, 0)",
            mask,
            "CRA_MCPL_INTERCHIP_LIFECYCLE_REQUEST_LINK_ROUTE",
            "event requests leave source chip over explicit link route",
            True,
        ),
        RouteContract(
            "learning_outbound_lifecycle_trophic",
            "learning_core",
            "MAKE_MCPL_KEY(APP_ID, MCPL_MSG_LIFECYCLE_TROPHIC_UPDATE, 0, 0)",
            mask,
            "CRA_MCPL_INTERCHIP_LIFECYCLE_REQUEST_LINK_ROUTE",
            "trophic update requests leave source chip over explicit link route",
            True,
        ),
        RouteContract(
            "lifecycle_local_event_request",
            "lifecycle_core",
            "MAKE_MCPL_KEY(APP_ID, MCPL_MSG_LIFECYCLE_EVENT_REQUEST, 0, 0)",
            mask,
            "MC_CORE_ROUTE(lifecycle_core)",
            "destination lifecycle core receives event requests locally",
            True,
        ),
        RouteContract(
            "lifecycle_local_trophic_request",
            "lifecycle_core",
            "MAKE_MCPL_KEY(APP_ID, MCPL_MSG_LIFECYCLE_TROPHIC_UPDATE, 0, 0)",
            mask,
            "MC_CORE_ROUTE(lifecycle_core)",
            "destination lifecycle core receives trophic requests locally",
            True,
        ),
        RouteContract(
            "lifecycle_outbound_mask_sync",
            "lifecycle_core",
            "MAKE_MCPL_KEY(APP_ID, MCPL_MSG_LIFECYCLE_ACTIVE_MASK_SYNC, 0, 0)",
            mask,
            "CRA_MCPL_INTERCHIP_LIFECYCLE_SYNC_LINK_ROUTE",
            "active-mask/lineage sync leaves lifecycle chip over explicit link route",
            True,
        ),
    ]


def run_command(command_id: str, args: list[str], output_dir: Path, purpose: str) -> TestCommand:
    completed = subprocess.run(args, cwd=ROOT, text=True, capture_output=True, check=False)
    stdout_path = output_dir / f"tier4_32g_r0_{command_id}_stdout.txt"
    stderr_path = output_dir / f"tier4_32g_r0_{command_id}_stderr.txt"
    stdout_path.write_text(completed.stdout, encoding="utf-8")
    stderr_path.write_text(completed.stderr, encoding="utf-8")
    return TestCommand(
        command_id=command_id,
        command=" ".join(args),
        returncode=completed.returncode,
        stdout_file=rel(stdout_path),
        stderr_file=rel(stderr_path),
        passed=completed.returncode == 0,
        purpose=purpose,
    )


def test_commands(output_dir: Path) -> list[TestCommand]:
    return [
        run_command(
            "lifecycle_interchip_route_contract",
            ["make", "-C", "coral_reef_spinnaker/spinnaker_runtime", "test-mcpl-lifecycle-interchip-route-contract"],
            output_dir,
            "Prove learning/lifecycle profile lifecycle inter-chip route entries locally.",
        ),
        run_command(
            "lookup_interchip_route_regression",
            ["make", "-C", "coral_reef_spinnaker/spinnaker_runtime", "test-mcpl-interchip-route-contract"],
            output_dir,
            "Ensure the existing 4.32d-r1 lookup route repair still passes.",
        ),
        run_command(
            "lifecycle_split_regression",
            ["make", "-C", "coral_reef_spinnaker/spinnaker_runtime", "test-lifecycle-split"],
            output_dir,
            "Ensure lifecycle duplicate/stale/mask-sync bookkeeping still passes.",
        ),
    ]


def next_gates() -> list[NextGate]:
    return [
        NextGate(
            gate="Tier 4.32g - Two-Chip Lifecycle Traffic/Resource Hardware Smoke",
            decision="authorized_next_prepare",
            question="Can lifecycle event/trophic/mask-sync traffic cross the chip boundary with compact resource counters?",
            prerequisites="4.32g-r0 source/route audit pass, explicit board/chip/core/role placement, compact readback schema, and bounded lifecycle schedule.",
            pass_case="Canonical lifecycle traffic and at least one control return expected event/sync counters, zero stale/duplicate/missing-ack counters, compact payload, zero fallback, and preserved returned artifacts.",
            fail_case="Classify as route, key, ack, readback, source/package, allocation, or lifecycle semantic failure before rerun.",
            claim_boundary="two-chip lifecycle traffic/resource smoke only; not full lifecycle scaling",
        ),
        NextGate(
            gate="Tier 4.32h - True Partition Semantics Contract",
            decision="blocked_until_4_32g_hardware_result",
            question="What origin/target shard semantics are required before true two-partition cross-chip learning?",
            prerequisites="4.32g hardware lifecycle/resource result or explicit parking decision.",
            pass_case="Defines origin/target shard identity and authorizes true two-partition local reference/repair work.",
            fail_case="Keep claims to single-shard split-role hardware evidence.",
            claim_boundary="contract only; no hardware claim",
        ),
    ]


def evaluate(output_dir: Path) -> dict[str, Any]:
    tier4_32f = read_json(TIER4_32F)
    tier4_32e = read_json(TIER4_32E)
    findings = source_findings()
    routes = route_contract()
    commands = test_commands(output_dir)
    gates = next_gates()
    missing = [row.finding_id for row in findings if not row.present]
    failed_commands = [row.command_id for row in commands if not row.passed]
    criteria = [
        criterion("Tier 4.32f prerequisite passed", tier4_32f.get("status"), "== pass", tier4_32f.get("status") == "pass"),
        criterion("4.32f authorized 4.32g-r0 next", tier4_32f.get("summary", {}).get("selected_next_gate"), "== tier4_32g_r0_multichip_lifecycle_route_source_repair_audit", tier4_32f.get("summary", {}).get("selected_next_gate") == "tier4_32g_r0_multichip_lifecycle_route_source_repair_audit"),
        criterion("Tier 4.32e hardware learning prerequisite passed", tier4_32e.get("status"), "== pass", tier4_32e.get("status") == "pass"),
        criterion("source lifecycle route findings present", missing, "empty", not missing),
        criterion("route contract covers six required lifecycle paths", len(routes), "== 6", len(routes) == 6),
        criterion("learning core has outbound event route", [row.route_id for row in routes], "contains learning_outbound_lifecycle_event", any(row.route_id == "learning_outbound_lifecycle_event" for row in routes)),
        criterion("learning core has outbound trophic route", [row.route_id for row in routes], "contains learning_outbound_lifecycle_trophic", any(row.route_id == "learning_outbound_lifecycle_trophic" for row in routes)),
        criterion("learning core has local mask-sync consumer route", [row.route_id for row in routes], "contains learning_local_mask_sync_consumer", any(row.route_id == "learning_local_mask_sync_consumer" for row in routes)),
        criterion("lifecycle core has local event route", [row.route_id for row in routes], "contains lifecycle_local_event_request", any(row.route_id == "lifecycle_local_event_request" for row in routes)),
        criterion("lifecycle core has local trophic route", [row.route_id for row in routes], "contains lifecycle_local_trophic_request", any(row.route_id == "lifecycle_local_trophic_request" for row in routes)),
        criterion("lifecycle core has outbound mask-sync route", [row.route_id for row in routes], "contains lifecycle_outbound_mask_sync", any(row.route_id == "lifecycle_outbound_mask_sync" for row in routes)),
        criterion("local test commands passed", failed_commands, "empty", not failed_commands),
        criterion("4.32g hardware prepare authorized", gates[0].decision, "== authorized_next_prepare", gates[0].decision == "authorized_next_prepare"),
        criterion("true partition semantics still blocked", gates[1].decision, "== blocked_until_4_32g_hardware_result", gates[1].decision == "blocked_until_4_32g_hardware_result"),
    ]
    status = "pass" if all(row.passed for row in criteria) else "fail"
    return {
        "status": status,
        "criteria": criteria,
        "source_findings": findings,
        "route_contract": routes,
        "test_commands": commands,
        "next_gates": gates,
        "summary": {
            "source_findings_missing": missing,
            "failed_commands": failed_commands,
            "route_contract_paths": len(routes),
            "selected_next_gate": "tier4_32g_two_chip_lifecycle_traffic_resource_hardware_smoke",
            "hardware_package_status": "authorized_next_prepare" if status == "pass" else "blocked",
            "claim_boundary": CLAIM_BOUNDARY,
        },
        "final_decision": {
            "status": status,
            "tier4_32g_hardware_prepare": "authorized_next" if status == "pass" else "blocked",
            "tier4_32h_true_partition_semantics": "blocked_until_4_32g_hardware_result",
            "speedup_claims": "not_authorized",
            "benchmark_claims": "not_authorized",
            "native_scale_baseline_freeze": "not_authorized",
            "claim_boundary": CLAIM_BOUNDARY,
        },
    }


def write_report(path: Path, payload: dict[str, Any], output_dir: Path) -> None:
    lines = [
        "# Tier 4.32g-r0 Multi-Chip Lifecycle Route/Source Repair Audit",
        "",
        f"- Generated: `{payload['generated_at_utc']}`",
        f"- Runner revision: `{RUNNER_REVISION}`",
        f"- Status: **{payload['status'].upper()}**",
        f"- Criteria: `{payload['criteria_passed']}/{payload['criteria_total']}`",
        f"- Output directory: `{output_dir}`",
        "",
        "## Claim Boundary",
        "",
        CLAIM_BOUNDARY,
        "",
        "## Decision",
        "",
        f"- 4.32g hardware prepare: `{payload['final_decision']['tier4_32g_hardware_prepare']}`",
        f"- Next gate: `{payload['summary']['selected_next_gate']}`",
        f"- True partition semantics: `{payload['final_decision']['tier4_32h_true_partition_semantics']}`",
        f"- Native scale baseline freeze: `{payload['final_decision']['native_scale_baseline_freeze']}`",
        "",
        "## Route Contract",
        "",
        "| Route | Profile | Key | Mask | Route | Purpose |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in payload["route_contract"]:
        lines.append(f"| `{row['route_id']}` | `{row['profile']}` | `{row['key']}` | `{row['mask']}` | `{row['route']}` | {row['purpose']} |")
    lines.extend(["", "## Source Findings", "", "| Finding | File | Token | Present | Purpose |", "| --- | --- | --- | --- | --- |"])
    for row in payload["source_findings"]:
        lines.append(f"| `{row['finding_id']}` | `{row['file']}` | `{row['token']}` | {'yes' if row['present'] else 'no'} | {row['purpose']} |")
    lines.extend(["", "## Local Test Commands", "", "| Command | Return | Pass | Purpose | Logs |", "| --- | ---: | --- | --- | --- |"])
    for row in payload["test_commands"]:
        logs = f"`{row['stdout_file']}`, `{row['stderr_file']}`"
        lines.append(f"| `{row['command']}` | {row['returncode']} | {'yes' if row['passed'] else 'no'} | {row['purpose']} | {logs} |")
    lines.extend(["", "## Next Gates", "", "| Gate | Decision | Question | Boundary |", "| --- | --- | --- | --- |"])
    for row in payload["next_gates"]:
        lines.append(f"| `{row['gate']}` | `{row['decision']}` | {row['question']} | {row['claim_boundary']} |")
    lines.extend(["", "## Criteria", "", "| Criterion | Value | Rule | Pass |", "| --- | --- | --- | --- |"])
    for row in payload["criteria"]:
        value = row["value"] if isinstance(row["value"], str) else json.dumps(json_safe(row["value"]), sort_keys=True)
        lines.append(f"| {row['name']} | `{value}` | {row['rule']} | {'yes' if row['passed'] else 'no'} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(output_dir: Path) -> dict[str, Any]:
    generated_at = utc_now()
    output_dir.mkdir(parents=True, exist_ok=True)
    evaluated = evaluate(output_dir)
    criteria = evaluated["criteria"]
    artifacts = {
        "results_json": output_dir / "tier4_32g_r0_results.json",
        "report_md": output_dir / "tier4_32g_r0_report.md",
        "criteria_csv": output_dir / "tier4_32g_r0_criteria.csv",
        "source_findings_csv": output_dir / "tier4_32g_r0_source_findings.csv",
        "route_contract_csv": output_dir / "tier4_32g_r0_route_contract.csv",
        "test_commands_csv": output_dir / "tier4_32g_r0_test_commands.csv",
        "next_gates_csv": output_dir / "tier4_32g_r0_next_gates.csv",
    }
    payload = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": generated_at,
        "status": evaluated["status"],
        "criteria_passed": sum(row.passed for row in criteria),
        "criteria_total": len(criteria),
        "output_dir": str(output_dir),
        "claim_boundary": CLAIM_BOUNDARY,
        "summary": evaluated["summary"],
        "final_decision": evaluated["final_decision"],
        "source_findings": evaluated["source_findings"],
        "route_contract": evaluated["route_contract"],
        "test_commands": evaluated["test_commands"],
        "next_gates": evaluated["next_gates"],
        "criteria": criteria,
        "artifacts": artifacts,
    }
    write_json(artifacts["results_json"], payload)
    write_csv(artifacts["criteria_csv"], [asdict(row) for row in criteria])
    write_csv(artifacts["source_findings_csv"], [asdict(row) for row in evaluated["source_findings"]])
    write_csv(artifacts["route_contract_csv"], [asdict(row) for row in evaluated["route_contract"]])
    write_csv(artifacts["test_commands_csv"], [asdict(row) for row in evaluated["test_commands"]])
    write_csv(artifacts["next_gates_csv"], [asdict(row) for row in evaluated["next_gates"]])
    write_report(artifacts["report_md"], json_safe(payload), output_dir)
    write_json(
        LATEST_MANIFEST,
        {
            "claim": "Latest Tier 4.32g-r0 multi-chip lifecycle route/source repair audit.",
            "generated_at_utc": generated_at,
            "manifest": str(artifacts["results_json"]),
            "status": evaluated["status"],
            "tier": TIER,
        },
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=TIER)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    result = run(args.output_dir)
    print(
        json.dumps(
            {
                "status": result["status"],
                "criteria": f"{result['criteria_passed']}/{result['criteria_total']}",
                "results": str(result["artifacts"]["results_json"]),
                "selected_next_gate": result["summary"]["selected_next_gate"],
                "hardware_package_status": result["summary"]["hardware_package_status"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    if result["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
