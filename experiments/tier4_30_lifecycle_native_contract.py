#!/usr/bin/env python3
"""Tier 4.30 lifecycle-native contract.

This tier is a contract gate, not runtime implementation and not hardware
evidence. It converts the Tier 4.30-readiness audit into a precise static-pool
lifecycle/self-scaling specification before any C runtime edits are allowed.

The contract exists to keep the native lifecycle path reviewer-defensible:

- no dynamic PyNN population creation mid-run
- no legacy malloc/free neuron birth/death as the lifecycle proof
- no hidden host-side lifecycle decisions without readback
- no unscoped v2.2 temporal-state migration
- no EBRAINS package before local parity and source audit
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"
RUNTIME_SRC = ROOT / "coral_reef_spinnaker" / "spinnaker_runtime" / "src"

TIER = "Tier 4.30 - Lifecycle-Native Static-Pool Contract"
RUNNER_REVISION = "tier4_30_lifecycle_native_contract_20260505_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier4_30_20260505_lifecycle_native_contract"
READINESS_RESULTS = (
    CONTROLLED
    / "tier4_30_readiness_20260505_lifecycle_native_audit"
    / "tier4_30_readiness_results.json"
)


@dataclass(frozen=True)
class Criterion:
    name: str
    value: Any
    rule: str
    passed: bool
    note: str = ""


@dataclass(frozen=True)
class CommandSpec:
    command: str
    owner: str
    phase: str
    payload_fields: str
    deterministic_rule: str
    required_ack: str
    forbidden_behavior: str


@dataclass(frozen=True)
class ReadbackSpec:
    field: str
    type: str
    owner: str
    when_read: str
    purpose: str
    pass_rule: str


@dataclass(frozen=True)
class EventSpec:
    event_type: str
    trigger_inputs: str
    state_updates: str
    required_invariants: str
    sham_control: str


@dataclass(frozen=True)
class GateSpec:
    gate: str
    mode: str
    scope: str
    pass_criteria: str
    fail_criteria: str
    artifacts: str


@dataclass(frozen=True)
class FailureClass:
    failure_class: str
    meaning: str
    required_response: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


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
                seen.add(key)
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_define_int(header_text: str, name: str) -> int | None:
    match = re.search(rf"^\s*#define\s+{re.escape(name)}\s+([0-9]+)\b", header_text, re.MULTILINE)
    return int(match.group(1)) if match else None


def criterion(name: str, value: Any, rule: str, passed: bool, note: str = "") -> Criterion:
    return Criterion(name=name, value=value, rule=rule, passed=bool(passed), note=note)


def command_specs() -> list[CommandSpec]:
    return [
        CommandSpec(
            command="CMD_LIFECYCLE_INIT",
            owner="host -> lifecycle core",
            phase="setup before run",
            payload_fields="pool_size, founder_count, seed, trophic_seed_raw, generation_seed",
            deterministic_rule="initial active slots are 0..founder_count-1; all other slots inactive",
            required_ack="pool_size, active_count, inactive_count, lineage_checksum",
            forbidden_behavior="no dynamic allocation, no graph rebuild, no implicit extra founders",
        ),
        CommandSpec(
            command="CMD_LIFECYCLE_EVENT",
            owner="host/reference -> lifecycle core",
            phase="local reference and first hardware smoke",
            payload_fields="event_index, event_type, parent_slot, target_slot, child_slot, trophic_delta_raw, reward_raw",
            deterministic_rule="event is applied only if invariants hold; invalid events increment invalid_event_count",
            required_ack="event_index, last_event_type, event_count, active_mask_checksum",
            forbidden_behavior="no silent overwrite of active child slot, no lineage mutation without event telemetry",
        ),
        CommandSpec(
            command="CMD_LIFECYCLE_TROPHIC_UPDATE",
            owner="learning core -> lifecycle core",
            phase="after lifecycle smoke, before task-effect claims",
            payload_fields="slot_id, reward_raw, activity_raw, prediction_error_raw, decay_raw",
            deterministic_rule="trophic_health, cyclin_d, and bax update in fixed-point with explicit clipping",
            required_ack="slot_id, trophic_health_raw, cyclin_d_raw, bax_raw",
            forbidden_behavior="no float-only host trophic decision in hardware claim",
        ),
        CommandSpec(
            command="CMD_LIFECYCLE_READ_STATE",
            owner="host <- lifecycle core",
            phase="debug, ingest, and paper audit",
            payload_fields="read_scope, start_slot, slot_count, schema_version",
            deterministic_rule="readback schema is stable and versioned; compact summary always available",
            required_ack="schema_version, pool_summary, per-slot compact rows or declared truncation",
            forbidden_behavior="no paper claim from unversioned or partial lifecycle state",
        ),
        CommandSpec(
            command="CMD_LIFECYCLE_SHAM_MODE",
            owner="host -> lifecycle core",
            phase="sham-control runs",
            payload_fields="control_mode, event_budget, shuffle_seed, disable_trophic, disable_plasticity",
            deterministic_rule="control perturbation is seeded and reproduced exactly by local reference",
            required_ack="control_mode, shuffle_seed, event_budget, sham_counter",
            forbidden_behavior="no post-hoc relabeling of failed lifecycle runs as controls",
        ),
    ]


def readback_specs() -> list[ReadbackSpec]:
    rows = [
        ("schema_version", "uint16", "host_interface", "every read", "detect stale parser/report mismatch", "matches contract version"),
        ("pool_size", "uint16", "lifecycle_core", "every read", "prove fixed capacity", "equals declared static pool"),
        ("active_count", "uint16", "lifecycle_core", "every read", "prove mask state", "matches popcount(active_mask)"),
        ("inactive_count", "uint16", "lifecycle_core", "every read", "capacity accounting", "active + inactive == pool_size"),
        ("active_mask_bits", "uint32", "lifecycle_core", "every read", "compact active/inactive proof", "matches reference bitmask"),
        ("lineage_checksum", "uint32", "lifecycle_core", "every read", "compact lineage integrity", "matches local reference"),
        ("trophic_checksum", "int32", "lifecycle_core", "every read", "compact trophic integrity", "within fixed-point tolerance"),
        ("event_count", "uint32", "lifecycle_core", "every read", "event accounting", "matches accepted events"),
        ("cleavage_count", "uint32", "lifecycle_core", "every read", "reproduction accounting", "matches reference"),
        ("birth_count", "uint32", "lifecycle_core", "every read", "adult birth accounting", "matches reference"),
        ("death_count", "uint32", "lifecycle_core", "every read", "death accounting", "matches reference"),
        ("invalid_event_count", "uint32", "lifecycle_core", "every read", "invariant failure accounting", "zero in canonical pass"),
        ("slot_id", "uint16", "lifecycle_core", "debug/full read", "stable static-pool index", "0 <= slot_id < pool_size"),
        ("active_mask", "uint8", "lifecycle_core", "debug/full read", "per-slot active flag", "matches reference"),
        ("polyp_id", "uint32", "lifecycle_core", "debug/full read", "auditable identity", "stable unless slot is reassigned by accepted event"),
        ("lineage_id", "uint32", "lifecycle_core", "debug/full read", "lineage audit", "matches reference lineage tree"),
        ("parent_slot", "int16", "lifecycle_core", "debug/full read", "birth provenance", "-1 for founders or valid parent slot"),
        ("generation", "uint16", "lifecycle_core", "debug/full read", "lifecycle depth", "increments only on accepted child event"),
        ("age_steps", "uint32", "lifecycle_core", "debug/full read", "maturity gates", "monotonic while active"),
        ("trophic_health_raw", "s16.15", "lifecycle_core", "debug/full read", "survival/reproduction pressure", "clipped and matches fixed-point reference"),
        ("cyclin_d_raw", "s16.15", "lifecycle_core", "debug/full read", "reproduction gate", "clipped and matches fixed-point reference"),
        ("bax_raw", "s16.15", "lifecycle_core", "debug/full read", "death gate", "clipped and matches fixed-point reference"),
        ("last_event_type", "uint8", "lifecycle_core", "debug/full read", "event audit", "matches final accepted event for slot"),
    ]
    return [
        ReadbackSpec(
            field=field,
            type=type_,
            owner=owner,
            when_read=when_read,
            purpose=purpose,
            pass_rule=pass_rule,
        )
        for field, type_, owner, when_read, purpose, pass_rule in rows
    ]


def event_specs() -> list[EventSpec]:
    return [
        EventSpec(
            event_type="trophic_update",
            trigger_inputs="slot activity/reward/error summary",
            state_updates="trophic_health, cyclin_d, bax, age_steps",
            required_invariants="slot active; fixed-point values clipped; no lineage mutation",
            sham_control="no_trophic_pressure_control",
        ),
        EventSpec(
            event_type="cleavage",
            trigger_inputs="parent active, inactive child slot available, cyclin gate passes",
            state_updates="child active, child parent_slot, child generation, child lineage_id, cleavage_count",
            required_invariants="parent remains active; child was inactive; event increments exactly once",
            sham_control="random_event_replay_control",
        ),
        EventSpec(
            event_type="adult_birth",
            trigger_inputs="adult parent active, inactive child slot available, trophic and maturity gates pass",
            state_updates="child active, child lineage_id/parent/generation, birth_count",
            required_invariants="adult gate explicit; no dynamic allocation; no hidden extra capacity",
            sham_control="fixed_static_pool_control",
        ),
        EventSpec(
            event_type="death",
            trigger_inputs="active slot, bax/death gate passes or explicit reference event",
            state_updates="slot inactive, death_count, final lineage telemetry preserved",
            required_invariants="active_count decreases by one; lineage remains readable after death",
            sham_control="active_mask_shuffle_control",
        ),
        EventSpec(
            event_type="maturity_handoff",
            trigger_inputs="age threshold or trophic threshold reached",
            state_updates="last_event_type, maturity marker encoded through cyclin/trophic state",
            required_invariants="no active-mask change unless paired with accepted birth/cleavage/death",
            sham_control="lineage_id_shuffle_control",
        ),
    ]


def gate_specs() -> list[GateSpec]:
    return [
        GateSpec(
            gate="Tier 4.30 contract",
            mode="local engineering",
            scope="command/readback schema and invariant specification",
            pass_criteria="all readiness inputs pass; command/readback/event/gate/failure schemas complete",
            fail_criteria="ambiguous ownership, missing shams, dynamic allocation dependency, or unscoped v2.2 migration",
            artifacts="results JSON, report MD, command/readback/event/gate/failure CSVs",
        ),
        GateSpec(
            gate="Tier 4.30a local static-pool reference",
            mode="local deterministic reference",
            scope="8-slot pool, 2 founders, 32-64 lifecycle events, no hardware",
            pass_criteria="exact active mask/lineage/event/checksum parity and all controls precomputed",
            fail_criteria="any nondeterminism, hidden capacity growth, invalid events in canonical pass",
            artifacts="local reference JSON, per-event CSV, final state CSV, control summaries",
        ),
        GateSpec(
            gate="Tier 4.30b single-core hardware smoke",
            mode="EBRAINS/SpiNNaker",
            scope="active-mask and lineage telemetry only, one seed first",
            pass_criteria="real hardware, zero fallback, compact readback matches local reference within fixed-point tolerance",
            fail_criteria="readback schema mismatch, stale state, dynamic allocation, timeout, or lineage checksum mismatch",
            artifacts="hardware results JSON, report MD, board/core info, compact readback, ingest report",
        ),
        GateSpec(
            gate="Tier 4.30c multi-core lifecycle split",
            mode="EBRAINS/SpiNNaker",
            scope="lifecycle state split from learning/context/route/memory cores",
            pass_criteria="no stale replies, no mask corruption, local parity preserved across cores",
            fail_criteria="cross-core stale reply, timeout, corrupted lineage, or unmatched event count",
            artifacts="core map, message counters, compact readback, local/hardware diff",
        ),
        GateSpec(
            gate="Tier 4.30d lifecycle sham-control subset",
            mode="local then hardware subset",
            scope="fixed pool, random events, mask shuffle, lineage shuffle, no trophic, no dopamine/plasticity",
            pass_criteria="lifecycle-enabled path separates from shams on a predeclared lifecycle-pressure task",
            fail_criteria="shams match lifecycle, no task effect, or lineage telemetry is decorative",
            artifacts="control matrix CSV, effect sizes, per-seed rows, failure classification",
        ),
    ]


def failure_classes() -> list[FailureClass]:
    return [
        FailureClass(
            "contract_gap",
            "A command, field, control, artifact, or claim boundary is not specified.",
            "Do not implement runtime code; repair the contract first.",
        ),
        FailureClass(
            "dynamic_allocation_dependency",
            "The proposed lifecycle proof depends on dynamic graph creation or malloc/free neuron birth/death.",
            "Reject as noncanonical for Tier 4.30; redesign as static pool/mask.",
        ),
        FailureClass(
            "local_reference_mismatch",
            "C/local candidate does not match the deterministic Python reference.",
            "Debug locally; no EBRAINS upload.",
        ),
        FailureClass(
            "readback_schema_mismatch",
            "Hardware emits a state schema the ingest/parser cannot verify.",
            "Stop and repair schema/versioning; no scientific claim.",
        ),
        FailureClass(
            "lineage_or_mask_corruption",
            "Active mask, lineage checksum, parent links, or event counters diverge.",
            "Classify as lifecycle-state failure and debug before controls.",
        ),
        FailureClass(
            "sham_explains_effect",
            "Fixed capacity, random events, shuffled masks, shuffled lineage, or no-trophic controls match the enabled path.",
            "Do not promote lifecycle-native baseline; narrow organism claim or redesign mechanism.",
        ),
        FailureClass(
            "unsupported_claim_jump",
            "A report claims lifecycle superiority, multi-chip scaling, speedup, or native v2.2 temporal state from this contract.",
            "Reject report wording and correct source-of-truth docs.",
        ),
    ]


def build_contract() -> dict[str, Any]:
    readiness = load_json(READINESS_RESULTS)
    config_h = read_text(RUNTIME_SRC / "config.h")
    state_h = read_text(RUNTIME_SRC / "state_manager.h")
    neuron_c = read_text(RUNTIME_SRC / "neuron_manager.c")

    constants = {
        name: parse_define_int(config_h, name)
        for name in (
            "MAX_NEURONS",
            "MAX_CONTEXT_SLOTS",
            "MAX_ROUTE_SLOTS",
            "MAX_MEMORY_SLOTS",
            "MAX_PENDING_HORIZONS",
            "MAX_SCHEDULE_ENTRIES",
        )
    }
    command_rows = command_specs()
    readback_rows = readback_specs()
    event_rows = event_specs()
    gate_rows = gate_specs()
    failure_rows = failure_classes()

    has_static_capacity = (constants["MAX_NEURONS"] or 0) >= 8 and (constants["MAX_SCHEDULE_ENTRIES"] or 0) >= 64
    has_legacy_dynamic_birth_death = "neuron_birth" in neuron_c and "sark_alloc" in neuron_c and "neuron_death" in neuron_c
    has_existing_lifecycle_surface = any(
        token in state_h
        for token in ("lineage_id", "trophic_health", "active_mask", "cyclin_d", "bax")
    )
    readiness_decision = readiness.get("layering_decision", {}).get("decision", "")

    contract = {
        "pool": {
            "pool_size": 8,
            "founder_count": 2,
            "max_events_for_first_reference": 64,
            "capacity_model": "fixed compile-time pool; lifecycle events activate, silence, or reassign slots",
            "first_task_scope": "state mechanics only; task-effect claims begin only after local and hardware state parity",
        },
        "layering": {
            "base_native_line": "CRA_NATIVE_MECHANISM_BRIDGE_v0.3",
            "software_reference_line": "v2.2",
            "software_reference_rule": "v2.2 informs future comparisons but is not migrated into hardware lifecycle in Tier 4.30.",
            "forbidden": [
                "dynamic PyNN population creation mid-run",
                "legacy SDRAM malloc/free neuron_birth/neuron_death as lifecycle proof",
                "host-only lifecycle decisions without readback",
                "unscoped native v2.2 fading-memory migration",
                "multi-chip or speedup claims",
            ],
        },
        "local_reference": {
            "language": "Python deterministic reference first; C fixed-point parity second",
            "event_count": "32 canonical events plus optional 64-event boundary smoke",
            "tolerance": "exact for integer/mask/lineage/event counters; <=1 raw unit for fixed-point summaries unless predeclared otherwise",
            "seed_rule": "seed 42 for first local reference; seeds 42/43/44 only after deterministic seed-42 pass",
        },
        "hardware_package_rule": {
            "allowed_after": "contract pass, local reference pass, source audit pass, generated package contains source only",
            "first_hardware_seed": 42,
            "first_hardware_scope": "single-core active-mask and lineage telemetry smoke",
            "ingest_required": True,
        },
    }

    criteria = [
        criterion("readiness audit passed", readiness.get("status"), "== pass", readiness.get("status") == "pass"),
        criterion("readiness audit criteria complete", f"{readiness.get('criteria_passed')}/{readiness.get('criteria_total')}", "== 16/16", readiness.get("criteria_passed") == readiness.get("criteria_total") == 16),
        criterion("layering decision imported", readiness_decision, "uses native mechanism bridge with v2.2 software reference only", "native_mechanism_bridge_v0_3" in readiness_decision and "v2_2_as_software_reference_only" in readiness_decision),
        criterion("static runtime capacity sufficient for first reference", constants, "MAX_NEURONS>=8 and schedule>=64", has_static_capacity),
        criterion("legacy dynamic birth/death excluded", has_legacy_dynamic_birth_death, "identified and excluded", has_legacy_dynamic_birth_death, "The legacy path exists but is explicitly not the Tier 4.30 proof."),
        criterion("lifecycle surface not already silently present", has_existing_lifecycle_surface, "== false before implementation", not has_existing_lifecycle_surface),
        criterion("command schema declared", len(command_rows), ">= 5 commands", len(command_rows) >= 5),
        criterion("readback schema declared", len(readback_rows), ">= 20 fields", len(readback_rows) >= 20),
        criterion("event semantics declared", len(event_rows), ">= 5 lifecycle event types", len(event_rows) >= 5),
        criterion("gate sequence declared", len(gate_rows), ">= 5 gates", len(gate_rows) >= 5),
        criterion("failure classes declared", len(failure_rows), ">= 6 classes", len(failure_rows) >= 6),
        criterion("static-pool contract declares bounded pool", contract["pool"]["pool_size"], "== 8 with 2 founders", contract["pool"]["pool_size"] == 8 and contract["pool"]["founder_count"] == 2),
        criterion("local reference required before hardware", contract["hardware_package_rule"]["allowed_after"], "mentions contract/local/source audit before package", all(token in contract["hardware_package_rule"]["allowed_after"] for token in ("contract pass", "local reference pass", "source audit pass"))),
        criterion("claim boundary forbids unsupported jumps", contract["layering"]["forbidden"], ">= 5 forbidden behaviors", len(contract["layering"]["forbidden"]) >= 5),
    ]
    failed = [item for item in criteria if not item.passed]

    return {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "status": "pass" if not failed else "fail",
        "mode": "local-contract",
        "criteria_passed": len(criteria) - len(failed),
        "criteria_total": len(criteria),
        "criteria": criteria,
        "failed_criteria": failed,
        "source_inputs": {
            "readiness_results": str(READINESS_RESULTS),
            "runtime_config": str(RUNTIME_SRC / "config.h"),
            "runtime_state_header": str(RUNTIME_SRC / "state_manager.h"),
            "legacy_neuron_manager": str(RUNTIME_SRC / "neuron_manager.c"),
        },
        "contract": contract,
        "command_schema": command_rows,
        "readback_schema": readback_rows,
        "event_semantics": event_rows,
        "gate_sequence": gate_rows,
        "failure_classes": failure_rows,
        "next_step": "Tier 4.30a local static-pool lifecycle reference",
        "claim_boundary": (
            "Tier 4.30 is a local engineering contract. It does not implement "
            "the C runtime lifecycle surface, does not run hardware, does not "
            "prove lifecycle/self-scaling, does not freeze a lifecycle baseline, "
            "does not migrate v2.2 temporal state, and does not claim speedup or "
            "multi-chip scaling."
        ),
    }


def write_report(path: Path, results: dict[str, Any]) -> None:
    safe = json_safe(results)
    lines = [
        "# Tier 4.30 Lifecycle-Native Static-Pool Contract",
        "",
        f"- Generated: `{safe['generated_at_utc']}`",
        f"- Runner revision: `{safe['runner_revision']}`",
        f"- Status: **{safe['status'].upper()}**",
        f"- Criteria: `{safe['criteria_passed']}/{safe['criteria_total']}`",
        "",
        "## Claim Boundary",
        "",
        safe["claim_boundary"],
        "",
        "## Contract Decision",
        "",
        f"- Base native line: `{safe['contract']['layering']['base_native_line']}`",
        f"- Software reference line: `{safe['contract']['layering']['software_reference_line']}`",
        f"- Pool size: `{safe['contract']['pool']['pool_size']}`",
        f"- Founder count: `{safe['contract']['pool']['founder_count']}`",
        f"- Capacity model: {safe['contract']['pool']['capacity_model']}",
        "",
        "Forbidden for Tier 4.30:",
        "",
        *[f"- {item}" for item in safe["contract"]["layering"]["forbidden"]],
        "",
        "## Command Schema",
        "",
        "| Command | Owner | Phase | Payload Fields | Deterministic Rule | Required Ack | Forbidden Behavior |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in safe["command_schema"]:
        lines.append(
            f"| `{row['command']}` | {row['owner']} | {row['phase']} | {row['payload_fields']} | {row['deterministic_rule']} | {row['required_ack']} | {row['forbidden_behavior']} |"
        )
    lines.extend(
        [
            "",
            "## Readback Schema",
            "",
            "| Field | Type | Owner | When Read | Purpose | Pass Rule |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in safe["readback_schema"]:
        lines.append(
            f"| `{row['field']}` | `{row['type']}` | {row['owner']} | {row['when_read']} | {row['purpose']} | {row['pass_rule']} |"
        )
    lines.extend(
        [
            "",
            "## Event Semantics",
            "",
            "| Event | Trigger Inputs | State Updates | Required Invariants | Sham Control |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for row in safe["event_semantics"]:
        lines.append(
            f"| `{row['event_type']}` | {row['trigger_inputs']} | {row['state_updates']} | {row['required_invariants']} | `{row['sham_control']}` |"
        )
    lines.extend(["", "## Gate Sequence", ""])
    for index, row in enumerate(safe["gate_sequence"], start=1):
        lines.append(f"{index}. **{row['gate']}** ({row['mode']}): {row['scope']}")
        lines.append(f"   Pass: {row['pass_criteria']}")
        lines.append(f"   Fail: {row['fail_criteria']}")
        lines.append(f"   Artifacts: {row['artifacts']}")
    lines.extend(
        [
            "",
            "## Failure Classes",
            "",
            "| Failure Class | Meaning | Required Response |",
            "| --- | --- | --- |",
        ]
    )
    for row in safe["failure_classes"]:
        lines.append(f"| `{row['failure_class']}` | {row['meaning']} | {row['required_response']} |")
    lines.extend(
        [
            "",
            "## Criteria",
            "",
            "| Criterion | Value | Rule | Pass | Note |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for row in safe["criteria"]:
        lines.append(
            f"| {row['name']} | `{row['value']}` | `{row['rule']}` | {'yes' if row['passed'] else 'no'} | {row.get('note', '')} |"
        )
    lines.extend(["", "## Next Step", "", safe["next_step"], ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    results = build_contract()
    results["output_dir"] = str(output_dir)

    write_json(output_dir / "tier4_30_contract_results.json", results)
    write_report(output_dir / "tier4_30_contract_report.md", results)
    write_csv(output_dir / "tier4_30_command_schema.csv", [asdict(row) for row in command_specs()])
    write_csv(output_dir / "tier4_30_readback_schema.csv", [asdict(row) for row in readback_specs()])
    write_csv(output_dir / "tier4_30_event_semantics.csv", [asdict(row) for row in event_specs()])
    write_csv(output_dir / "tier4_30_gate_sequence.csv", [asdict(row) for row in gate_specs()])
    write_csv(output_dir / "tier4_30_failure_classes.csv", [asdict(row) for row in failure_classes()])
    write_json(
        CONTROLLED / "tier4_30_latest_manifest.json",
        {
            "tier": TIER,
            "runner_revision": RUNNER_REVISION,
            "generated_at_utc": results["generated_at_utc"],
            "status": results["status"],
            "manifest": str(output_dir / "tier4_30_contract_results.json"),
            "output_dir": str(output_dir),
        },
    )
    return results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=TIER)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    results = run(args)
    print(
        json.dumps(
            {
                "tier": TIER,
                "status": results["status"],
                "criteria": f"{results['criteria_passed']}/{results['criteria_total']}",
                "output_dir": results["output_dir"],
                "next": results["next_step"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if results["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
