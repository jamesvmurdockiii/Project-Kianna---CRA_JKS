#!/usr/bin/env python3
"""Tier 4.32c inter-chip feasibility contract.

This is a local contract gate after Tier 4.32b. It does not run SpiNNaker
hardware and does not claim multi-chip scaling. Its job is to make the first
cross-chip smoke target explicit enough that a later EBRAINS package cannot
silently overclaim:

* which board/chip/shard/role fields identify ownership;
* which MCPL/multicast key bits are already source-backed;
* which fields are *not* in the MCPL key and must be carried by placement and
  readback metadata;
* which compact counters prove cross-chip delivery is clean; and
* what exact smallest cross-chip smoke is allowed next.
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

TIER = "Tier 4.32c - Inter-Chip Feasibility Contract"
RUNNER_REVISION = "tier4_32c_interchip_feasibility_contract_20260507_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier4_32c_20260507_interchip_feasibility_contract"
LATEST_MANIFEST = CONTROLLED / "tier4_32c_latest_manifest.json"

TIER4_32B = (
    CONTROLLED
    / "tier4_32b_20260507_static_reef_partition_smoke"
    / "tier4_32b_results.json"
)

CONSERVATIVE_APP_CORES_PER_CHIP = 16
FIRST_SMOKE_CHIPS = 2
FIRST_SMOKE_PARTITIONS = 2
FIRST_SMOKE_CORES = 8
FIRST_SMOKE_EVENTS_PER_PARTITION = 32
LOOKUP_TYPES_PER_EVENT = 3

CLAIM_BOUNDARY = (
    "Tier 4.32c is a local inter-chip feasibility contract over the measured "
    "single-chip static partition map. It is not a SpiNNaker hardware run, not "
    "multi-chip execution evidence, not speedup evidence, not learning-scale "
    "evidence, not benchmark superiority, and not a native-scale baseline "
    "freeze."
)


@dataclass(frozen=True)
class Criterion:
    name: str
    value: Any
    rule: str
    passed: bool
    note: str = ""


@dataclass(frozen=True)
class SourceCheck:
    file: str
    token: str
    present: bool
    purpose: str


@dataclass(frozen=True)
class IdentityField:
    field: str
    location: str
    type_or_bits: str
    owner: str
    purpose: str
    required_for_4_32d: bool
    failure_if_missing: str


@dataclass(frozen=True)
class PlacementRow:
    smoke_target: str
    board_id: str
    chip_x: int
    chip_y: int
    partition_id: str
    shard_id: int
    polyp_slots: str
    context_core: int
    route_core: int
    memory_core: int
    learning_core: int
    expected_events: int
    expected_lookups: int
    ownership_rule: str


@dataclass(frozen=True)
class MessagePath:
    path_id: str
    source_partition: str
    source_chip: str
    source_core_role: str
    destination_partition: str
    destination_chip: str
    destination_core_role: str
    transport: str
    key_fields: str
    metadata_fields: str
    expected_messages: int
    ack_or_readback: str
    failure_if: str


@dataclass(frozen=True)
class ReadbackField:
    field: str
    producer: str
    scope: str
    required: bool
    expected_rule: str
    why: str


@dataclass(frozen=True)
class FailureClass:
    failure_class: str
    detection_rule: str
    required_response: str
    blocks: str


@dataclass(frozen=True)
class NextGate:
    gate: str
    decision: str
    question: str
    prerequisites: str
    pass_boundary: str
    fail_boundary: str
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
    keys: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json_safe(row.get(key, "")) for key in keys})


def criterion(name: str, value: Any, rule: str, passed: bool, note: str = "") -> Criterion:
    return Criterion(name=name, value=value, rule=rule, passed=bool(passed), note=note)


def parse_define_int(path: Path, name: str) -> int:
    pattern = re.compile(rf"^\s*#define\s+{re.escape(name)}\s+(0x[0-9A-Fa-f]+|[0-9]+)\b")
    for line in path.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if match:
            return int(match.group(1), 0)
    raise ValueError(f"missing #define {name} in {path}")


def source_check(path: Path, token: str, purpose: str) -> SourceCheck:
    text = path.read_text(encoding="utf-8")
    return SourceCheck(file=rel(path), token=token, present=token in text, purpose=purpose)


def runtime_limits() -> dict[str, int]:
    config_h = RUNTIME_SRC / "config.h"
    return {
        "max_lifecycle_slots": parse_define_int(config_h, "MAX_LIFECYCLE_SLOTS"),
        "max_schedule_entries": parse_define_int(config_h, "MAX_SCHEDULE_ENTRIES"),
        "mcpl_key_shard_mask": parse_define_int(config_h, "MCPL_KEY_SHARD_MASK"),
    }


def source_checks() -> list[SourceCheck]:
    config_h = RUNTIME_SRC / "config.h"
    state_h = RUNTIME_SRC / "state_manager.h"
    state_c = RUNTIME_SRC / "state_manager.c"
    return [
        source_check(config_h, "MAKE_MCPL_KEY_SHARD", "MCPL lookup key can carry shard identity."),
        source_check(config_h, "EXTRACT_MCPL_SHARD_ID", "Receivers can decode shard identity from keys."),
        source_check(config_h, "MCPL_MSG_LOOKUP_REQUEST", "Lookup request message type is source-declared."),
        source_check(config_h, "MCPL_MSG_LOOKUP_REPLY_VALUE", "Lookup value reply packet is source-declared."),
        source_check(config_h, "MCPL_MSG_LOOKUP_REPLY_META", "Lookup metadata reply packet is source-declared."),
        source_check(state_h, "cra_state_lookup_send_shard", "Lookup send path accepts explicit shard id."),
        source_check(state_h, "cra_state_lookup_get_result_shard", "Lookup readback path accepts explicit shard id."),
        source_check(state_c, "g_lookup_entries[i].shard_id", "Pending lookup entries store shard identity."),
        source_check(state_c, "CRA_MCPL_SHARD_ID", "Runtime images can be compiled with a static shard id."),
    ]


def identity_fields() -> list[IdentityField]:
    return [
        IdentityField(
            field="logical_board_id",
            location="host manifest and returned compact readback",
            type_or_bits="string/integer metadata; not packed into MCPL key",
            owner="host placement manifest",
            purpose="distinguish physical board allocation if EBRAINS exposes more than one board",
            required_for_4_32d=True,
            failure_if_missing="returned artifacts cannot prove which board executed each partition",
        ),
        IdentityField(
            field="chip_x",
            location="host placement manifest and per-core readback",
            type_or_bits="integer chip coordinate metadata; not packed into MCPL key",
            owner="host placement manifest plus SpiNNaker placement/readback",
            purpose="identify the source/destination chip for cross-chip routing",
            required_for_4_32d=True,
            failure_if_missing="same-core-id replies from different chips become ambiguous",
        ),
        IdentityField(
            field="chip_y",
            location="host placement manifest and per-core readback",
            type_or_bits="integer chip coordinate metadata; not packed into MCPL key",
            owner="host placement manifest plus SpiNNaker placement/readback",
            purpose="identify the source/destination chip for cross-chip routing",
            required_for_4_32d=True,
            failure_if_missing="same-core-id replies from different chips become ambiguous",
        ),
        IdentityField(
            field="p_core",
            location="per-core profile/readback",
            type_or_bits="integer processor id metadata",
            owner="runtime profile and host loader",
            purpose="bind context/route/memory/learning role to a physical core",
            required_for_4_32d=True,
            failure_if_missing="role ownership cannot be reconstructed",
        ),
        IdentityField(
            field="role",
            location="profile name and compact readback",
            type_or_bits="context|route|memory|learning",
            owner="runtime profile",
            purpose="preserve single-writer state ownership across chips",
            required_for_4_32d=True,
            failure_if_missing="readback payload cannot be interpreted safely",
        ),
        IdentityField(
            field="partition_id",
            location="host manifest, compact readback, and evidence tables",
            type_or_bits="reef_partition_N",
            owner="Tier 4.32b static map",
            purpose="bind static polyp slots to a mechanism partition",
            required_for_4_32d=True,
            failure_if_missing="cross-chip message cannot be traced to a semantic reef partition",
        ),
        IdentityField(
            field="shard_id",
            location="MCPL key bits plus readback",
            type_or_bits="0..MCPL_KEY_SHARD_MASK",
            owner="runtime key contract",
            purpose="separate lookup traffic from different static partitions",
            required_for_4_32d=True,
            failure_if_missing="identical seq/type messages can cross-talk across partitions",
        ),
        IdentityField(
            field="seq_id",
            location="MCPL key bits and pending lookup table",
            type_or_bits="bounded sequence field",
            owner="learning/lookup sender",
            purpose="pair value/meta replies with the correct lookup request",
            required_for_4_32d=True,
            failure_if_missing="stale/duplicate replies cannot be classified",
        ),
    ]


def first_smoke_placement() -> list[PlacementRow]:
    return [
        PlacementRow(
            smoke_target="point_2chip_2partition_lookup_smoke",
            board_id="allocated_board_0",
            chip_x=0,
            chip_y=0,
            partition_id="reef_partition_0",
            shard_id=0,
            polyp_slots="0,1",
            context_core=1,
            route_core=2,
            memory_core=3,
            learning_core=4,
            expected_events=FIRST_SMOKE_EVENTS_PER_PARTITION,
            expected_lookups=FIRST_SMOKE_EVENTS_PER_PARTITION * LOOKUP_TYPES_PER_EVENT,
            ownership_rule="source partition; local self-lookups plus remote lookup probes to reef_partition_1",
        ),
        PlacementRow(
            smoke_target="point_2chip_2partition_lookup_smoke",
            board_id="allocated_board_0",
            chip_x=1,
            chip_y=0,
            partition_id="reef_partition_1",
            shard_id=1,
            polyp_slots="2,3",
            context_core=1,
            route_core=2,
            memory_core=3,
            learning_core=4,
            expected_events=FIRST_SMOKE_EVENTS_PER_PARTITION,
            expected_lookups=FIRST_SMOKE_EVENTS_PER_PARTITION * LOOKUP_TYPES_PER_EVENT,
            ownership_rule="remote partition; must produce distinguishable chip/partition readback",
        ),
    ]


def message_paths() -> list[MessagePath]:
    expected = FIRST_SMOKE_EVENTS_PER_PARTITION * LOOKUP_TYPES_PER_EVENT
    return [
        MessagePath(
            path_id="local_partition0_self_lookup",
            source_partition="reef_partition_0",
            source_chip="(0,0)",
            source_core_role="learning_core",
            destination_partition="reef_partition_0",
            destination_chip="(0,0)",
            destination_core_role="context/route/memory cores",
            transport="MCPL/multicast lookup request plus value/meta reply",
            key_fields="app_id,msg_type,lookup_type,shard_id=0,seq_id",
            metadata_fields="board_id,chip_x,chip_y,p_core,role,partition_id in readback",
            expected_messages=expected,
            ack_or_readback="request_count == reply_value_count == reply_meta_count == expected",
            failure_if="local parity regresses before cross-chip comparison",
        ),
        MessagePath(
            path_id="remote_partition0_to_partition1_lookup_probe",
            source_partition="reef_partition_0",
            source_chip="(0,0)",
            source_core_role="learning_core",
            destination_partition="reef_partition_1",
            destination_chip="(1,0)",
            destination_core_role="context/route/memory cores",
            transport="MCPL/multicast lookup request routed across chip boundary plus value/meta reply",
            key_fields="app_id,msg_type,lookup_type,shard_id=1,seq_id",
            metadata_fields="board_id,source_chip,destination_chip,p_core,role,partition_id in readback",
            expected_messages=expected,
            ack_or_readback="remote request_count == reply_value_count == reply_meta_count == expected",
            failure_if="remote parity fails, replies are stale/duplicate, or readback cannot prove destination chip",
        ),
        MessagePath(
            path_id="remote_partition1_to_partition0_lookup_probe",
            source_partition="reef_partition_1",
            source_chip="(1,0)",
            source_core_role="learning_core",
            destination_partition="reef_partition_0",
            destination_chip="(0,0)",
            destination_core_role="context/route/memory cores",
            transport="MCPL/multicast lookup request routed across chip boundary plus value/meta reply",
            key_fields="app_id,msg_type,lookup_type,shard_id=0,seq_id",
            metadata_fields="board_id,source_chip,destination_chip,p_core,role,partition_id in readback",
            expected_messages=expected,
            ack_or_readback="remote request_count == reply_value_count == reply_meta_count == expected",
            failure_if="bidirectional route asymmetry or stale replies",
        ),
    ]


def readback_fields() -> list[ReadbackField]:
    return [
        ReadbackField("runner_revision", "host", "artifact", True, f"== {RUNNER_REVISION} or later 4.32d runner", "bind evidence to runner contract"),
        ReadbackField("board_id", "host/placement", "per run and per partition", True, "non-empty", "disambiguate allocation"),
        ReadbackField("chip_x", "host/placement/runtime readback", "per core", True, "matches placement table", "prove cross-chip source/destination identity"),
        ReadbackField("chip_y", "host/placement/runtime readback", "per core", True, "matches placement table", "prove cross-chip source/destination identity"),
        ReadbackField("p_core", "runtime readback", "per core", True, "matches role map", "reconstruct ownership"),
        ReadbackField("role", "runtime readback", "per core", True, "context/route/memory/learning", "decode payload safely"),
        ReadbackField("partition_id", "host/runtime readback", "per core and aggregate", True, "reef_partition_0/1 for 4.32d", "bind state to reef partition"),
        ReadbackField("shard_id", "runtime readback", "per lookup and aggregate", True, "0 or 1 for 4.32d", "prove shard-aware routing"),
        ReadbackField("lookup_requests", "learning/runtime", "per path", True, "== expected_messages", "prove request schedule consumed"),
        ReadbackField("reply_value_packets", "runtime", "per path", True, "== expected_messages", "prove value packet returned"),
        ReadbackField("reply_meta_packets", "runtime", "per path", True, "== expected_messages", "prove confidence/hit/status packet returned"),
        ReadbackField("stale_replies", "runtime", "per path and aggregate", True, "== 0", "classify stale lookup failures"),
        ReadbackField("duplicate_replies", "runtime", "per path and aggregate", True, "== 0", "classify duplicate lookup failures"),
        ReadbackField("timeouts", "runtime", "per path and aggregate", True, "== 0", "classify delivery failure"),
        ReadbackField("route_mismatch_count", "runtime or host ingest", "per path", True, "== 0", "catch wrong-chip or wrong-partition replies"),
        ReadbackField("payload_len", "runtime readback", "per core", True, "<= compact readback contract", "prevent readback bloat"),
    ]


def failure_classes() -> list[FailureClass]:
    return [
        FailureClass("target_or_machine_allocation", "pyNN.spiNNaker target or board/chip placement unavailable", "preserve prepared artifacts; do not mark hardware fail", "4.32d hardware evidence"),
        FailureClass("placement_ambiguity", "returned artifacts lack board/chip/core/role/partition fields", "repair placement/readback before rerun", "all multi-chip claims"),
        FailureClass("router_table_or_multicast_path", "local parity passes but remote path parity fails", "inspect routing table construction and key masks", "4.32d and 4.32e"),
        FailureClass("cross_chip_key_collision", "wrong shard, wrong partition, stale reply, or duplicate reply appears", "repair key/seq/shard contract before rerun", "learning scale"),
        FailureClass("metadata_value_split", "value packets return without matching metadata packets", "repair value/meta pair handling", "confidence-gated learning"),
        FailureClass("readback_bloat", "payload length expands beyond compact readback contract", "reduce readback before larger runs", "speed/resource claims"),
        FailureClass("environment_or_runner", "command/path/import failure before target execution", "repair package/runbook; preserve failure as noncanonical", "hardware evidence"),
        FailureClass("overclaim_boundary", "report claims speedup, benchmark superiority, or baseline freeze", "correct docs and rerun audit before commit", "paper readiness"),
    ]


def next_gates() -> list[NextGate]:
    return [
        NextGate(
            gate="Tier 4.32d",
            decision="authorize_after_4_32c_pass",
            question="Can the smallest two-chip, two-partition MCPL lookup smoke execute with reconstructable readback?",
            prerequisites="4.32c contract pass, source package QA, explicit placement table, compact readback schema.",
            pass_boundary="Hardware run returns zero stale/duplicate/timeout/route-mismatch counters and complete board/chip/partition readback for local and remote lookup paths.",
            fail_boundary="Classify as allocation, placement, routing, key collision, value/meta split, readback, or environment before rerun.",
            claim_boundary="first cross-chip communication/readback smoke only; not learning scale or speedup",
        ),
        NextGate(
            gate="Tier 4.32e",
            decision="blocked_until_4_32d_passes",
            question="Can a tiny cross-chip native learning micro-task preserve parity after communication is proven?",
            prerequisites="4.32d hardware smoke pass plus local fixed-point learning reference.",
            pass_boundary="Tiny delayed-credit or reentry micro-task matches local reference within tolerance with zero synthetic fallback.",
            fail_boundary="Do not run larger tasks or benchmarks; classify cross-chip learning/timing/readback failure.",
            claim_boundary="tiny multi-chip learning evidence only",
        ),
        NextGate(
            gate="CRA_NATIVE_SCALE_BASELINE_v0.5",
            decision="not_authorized",
            question="Is the native runtime stable enough to freeze as the scale baseline?",
            prerequisites="4.32b, 4.32c, 4.32d, and 4.32e all pass with clean resource/readback accounting.",
            pass_boundary="Freeze only if static partition, first cross-chip communication, and first cross-chip learning are clean.",
            fail_boundary="Publish measured single-chip/static partition limits honestly and keep v0.4 as latest native lifecycle baseline.",
            claim_boundary="baseline freeze decision is separate from this contract",
        ),
    ]


def load_tier4_32b() -> dict[str, Any]:
    return read_json(TIER4_32B)


def evaluate(
    *,
    tier4_32b: dict[str, Any],
    limits: dict[str, int],
    checks: list[SourceCheck],
    identities: list[IdentityField],
    placements: list[PlacementRow],
    paths: list[MessagePath],
    readbacks: list[ReadbackField],
    failures: list[FailureClass],
    gates: list[NextGate],
) -> tuple[list[Criterion], dict[str, Any]]:
    final = tier4_32b.get("final_decision", {})
    canonical_layout = str(final.get("canonical_static_layout") or "")
    max_shard = max(row.shard_id for row in placements)
    total_cores = len(placements) * 4
    expected_remote_paths = [path for path in paths if path.source_chip != path.destination_chip]
    required_identity_fields = [row.field for row in identities if row.required_for_4_32d]
    required_readback_fields = [row.field for row in readbacks if row.required]
    source_missing = [row.token for row in checks if not row.present]

    criteria = [
        criterion("Tier 4.32b prerequisite passed", tier4_32b.get("status"), "== pass", tier4_32b.get("status") == "pass"),
        criterion("4.32b canonical layout is quad mechanism map", canonical_layout, "== quad_mechanism_partition_v0", canonical_layout == "quad_mechanism_partition_v0"),
        criterion("4.32b authorized 4.32c", final.get("tier4_32c"), "== authorized_next_contract", final.get("tier4_32c") == "authorized_next_contract"),
        criterion("source supports shard-aware MCPL lookup", source_missing, "empty", not source_missing),
        criterion("first smoke uses two chips", FIRST_SMOKE_CHIPS, "== 2", FIRST_SMOKE_CHIPS == 2),
        criterion("first smoke uses two static partitions", FIRST_SMOKE_PARTITIONS, "== 2", len(placements) == FIRST_SMOKE_PARTITIONS),
        criterion("first smoke stays within one-chip-per-partition core envelope", total_cores, "<= 2 * 16", total_cores <= FIRST_SMOKE_CHIPS * CONSERVATIVE_APP_CORES_PER_CHIP),
        criterion("first smoke shard ids fit MCPL mask", max_shard, f"<= {limits['mcpl_key_shard_mask']}", max_shard <= limits["mcpl_key_shard_mask"]),
        criterion("events per partition fit schedule limit", FIRST_SMOKE_EVENTS_PER_PARTITION, f"<= {limits['max_schedule_entries']}", FIRST_SMOKE_EVENTS_PER_PARTITION <= limits["max_schedule_entries"]),
        criterion("identity fields include board/chip/core/role/partition/shard/seq", required_identity_fields, "contains required fields", {"logical_board_id", "chip_x", "chip_y", "p_core", "role", "partition_id", "shard_id", "seq_id"}.issubset(set(required_identity_fields))),
        criterion("readback fields include delivery counters", required_readback_fields, "contains stale/duplicate/timeouts/route_mismatch", {"stale_replies", "duplicate_replies", "timeouts", "route_mismatch_count"}.issubset(set(required_readback_fields))),
        criterion("contract includes bidirectional remote paths", len(expected_remote_paths), ">= 2", len(expected_remote_paths) >= 2),
        criterion("remote paths use different source and destination chips", [path.path_id for path in expected_remote_paths], "source_chip != destination_chip", all(path.source_chip != path.destination_chip for path in expected_remote_paths)),
        criterion("message paths preserve value/meta distinction", [path.path_id for path in paths if "value/meta" in path.transport or "value/meta" in path.ack_or_readback], "all paths", all("value/meta" in path.transport or "value/meta" in path.ack_or_readback for path in paths)),
        criterion("failure classes include placement ambiguity", [row.failure_class for row in failures], "contains placement_ambiguity", any(row.failure_class == "placement_ambiguity" for row in failures)),
        criterion("failure classes include cross-chip key collision", [row.failure_class for row in failures], "contains cross_chip_key_collision", any(row.failure_class == "cross_chip_key_collision" for row in failures)),
        criterion("next gate is 4.32d hardware smoke", gates[0].gate, "== Tier 4.32d", gates[0].gate == "Tier 4.32d"),
        criterion("4.32e remains blocked", gates[1].decision, "== blocked_until_4_32d_passes", gates[1].decision == "blocked_until_4_32d_passes"),
        criterion("native scale baseline freeze remains blocked", gates[2].decision, "== not_authorized", gates[2].decision == "not_authorized"),
    ]

    summary = {
        "canonical_layout": canonical_layout,
        "first_smoke_target": "point_2chip_2partition_lookup_smoke",
        "first_smoke_chips": FIRST_SMOKE_CHIPS,
        "first_smoke_partitions": FIRST_SMOKE_PARTITIONS,
        "first_smoke_total_cores": total_cores,
        "first_smoke_events_per_partition": FIRST_SMOKE_EVENTS_PER_PARTITION,
        "first_smoke_expected_lookups_per_partition": FIRST_SMOKE_EVENTS_PER_PARTITION * LOOKUP_TYPES_PER_EVENT,
        "required_identity_fields": required_identity_fields,
        "required_readback_fields": required_readback_fields,
        "remote_path_count": len(expected_remote_paths),
        "recommended_next_step": "Tier 4.32d first two-chip/two-partition MCPL lookup smoke package, only after source/package QA.",
        "claim_boundary": CLAIM_BOUNDARY,
    }
    return criteria, summary


def write_report(
    path: Path,
    *,
    generated_at: str,
    output_dir: Path,
    status: str,
    criteria: list[Criterion],
    summary: dict[str, Any],
    identities: list[IdentityField],
    placements: list[PlacementRow],
    paths: list[MessagePath],
    readbacks: list[ReadbackField],
    failures: list[FailureClass],
    gates: list[NextGate],
) -> None:
    lines = [
        "# Tier 4.32c Inter-Chip Feasibility Contract",
        "",
        f"- Generated: `{generated_at}`",
        f"- Runner revision: `{RUNNER_REVISION}`",
        f"- Status: **{status.upper()}**",
        f"- Criteria: `{sum(c.passed for c in criteria)}/{len(criteria)}`",
        f"- Output directory: `{output_dir}`",
        "",
        "## Claim Boundary",
        "",
        CLAIM_BOUNDARY,
        "",
        "## Contract Summary",
        "",
        f"- First smoke target: `{summary['first_smoke_target']}`",
        f"- Chips: `{summary['first_smoke_chips']}`",
        f"- Static partitions: `{summary['first_smoke_partitions']}`",
        f"- Total cores: `{summary['first_smoke_total_cores']}`",
        f"- Events per partition: `{summary['first_smoke_events_per_partition']}`",
        f"- Expected lookups per partition: `{summary['first_smoke_expected_lookups_per_partition']}`",
        f"- Remote paths: `{summary['remote_path_count']}`",
        f"- Recommended next step: {summary['recommended_next_step']}",
        "",
        "## Identity Contract",
        "",
        "| Field | Location | Type/Bits | Owner | Required | Failure If Missing |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in identities:
        lines.append(
            f"| `{row.field}` | {row.location} | {row.type_or_bits} | {row.owner} | "
            f"{'yes' if row.required_for_4_32d else 'no'} | {row.failure_if_missing} |"
        )

    lines.extend(
        [
            "",
            "## First Cross-Chip Smoke Placement",
            "",
            "| Target | Board | Chip | Partition | Shard | Slots | Cores C/R/M/L | Events | Lookups | Rule |",
            "| --- | --- | --- | --- | ---: | --- | --- | ---: | ---: | --- |",
        ]
    )
    for row in placements:
        lines.append(
            f"| `{row.smoke_target}` | `{row.board_id}` | `({row.chip_x},{row.chip_y})` | "
            f"`{row.partition_id}` | {row.shard_id} | `{row.polyp_slots}` | "
            f"`{row.context_core}/{row.route_core}/{row.memory_core}/{row.learning_core}` | "
            f"{row.expected_events} | {row.expected_lookups} | {row.ownership_rule} |"
        )

    lines.extend(
        [
            "",
            "## Message Paths",
            "",
            "| Path | Source | Destination | Transport | Key Fields | Expected | Failure If |",
            "| --- | --- | --- | --- | --- | ---: | --- |",
        ]
    )
    for row in paths:
        lines.append(
            f"| `{row.path_id}` | `{row.source_partition}` `{row.source_chip}` {row.source_core_role} | "
            f"`{row.destination_partition}` `{row.destination_chip}` {row.destination_core_role} | "
            f"{row.transport} | `{row.key_fields}` | {row.expected_messages} | {row.failure_if} |"
        )

    lines.extend(
        [
            "",
            "## Required Readback",
            "",
            "| Field | Producer | Scope | Rule | Why |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for row in readbacks:
        lines.append(f"| `{row.field}` | {row.producer} | {row.scope} | `{row.expected_rule}` | {row.why} |")

    lines.extend(
        [
            "",
            "## Failure Classes",
            "",
            "| Failure | Detection | Required Response | Blocks |",
            "| --- | --- | --- | --- |",
        ]
    )
    for row in failures:
        lines.append(f"| `{row.failure_class}` | {row.detection_rule} | {row.required_response} | {row.blocks} |")

    lines.extend(
        [
            "",
            "## Next Gates",
            "",
            "| Gate | Decision | Question | Claim Boundary |",
            "| --- | --- | --- | --- |",
        ]
    )
    for row in gates:
        lines.append(f"| `{row.gate}` | `{row.decision}` | {row.question} | {row.claim_boundary} |")

    lines.extend(
        [
            "",
            "## Criteria",
            "",
            "| Criterion | Value | Rule | Pass |",
            "| --- | --- | --- | --- |",
        ]
    )
    for row in criteria:
        value = json.dumps(json_safe(row.value), sort_keys=True) if not isinstance(row.value, str) else row.value
        lines.append(f"| {row.name} | `{value}` | {row.rule} | {'yes' if row.passed else 'no'} |")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(output_dir: Path) -> dict[str, Any]:
    generated_at = utc_now()
    output_dir.mkdir(parents=True, exist_ok=True)

    tier4_32b = load_tier4_32b()
    limits = runtime_limits()
    checks = source_checks()
    identities = identity_fields()
    placements = first_smoke_placement()
    paths = message_paths()
    readbacks = readback_fields()
    failures = failure_classes()
    gates = next_gates()
    criteria, summary = evaluate(
        tier4_32b=tier4_32b,
        limits=limits,
        checks=checks,
        identities=identities,
        placements=placements,
        paths=paths,
        readbacks=readbacks,
        failures=failures,
        gates=gates,
    )

    status = "pass" if all(row.passed for row in criteria) else "fail"
    artifacts = {
        "results_json": output_dir / "tier4_32c_results.json",
        "report_md": output_dir / "tier4_32c_report.md",
        "criteria_csv": output_dir / "tier4_32c_criteria.csv",
        "source_checks_csv": output_dir / "tier4_32c_source_checks.csv",
        "identity_contract_csv": output_dir / "tier4_32c_identity_contract.csv",
        "placement_contract_csv": output_dir / "tier4_32c_placement_contract.csv",
        "message_paths_csv": output_dir / "tier4_32c_message_paths.csv",
        "readback_contract_csv": output_dir / "tier4_32c_readback_contract.csv",
        "failure_classes_csv": output_dir / "tier4_32c_failure_classes.csv",
        "next_gate_plan_csv": output_dir / "tier4_32c_next_gate_plan.csv",
    }

    result = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": generated_at,
        "status": status,
        "criteria_passed": sum(row.passed for row in criteria),
        "criteria_total": len(criteria),
        "output_dir": str(output_dir),
        "summary": summary,
        "claim_boundary": CLAIM_BOUNDARY,
        "runtime_limits": limits,
        "source_checks": checks,
        "identity_contract": identities,
        "placement_contract": placements,
        "message_paths": paths,
        "readback_contract": readbacks,
        "failure_classes": failures,
        "next_gates": gates,
        "criteria": criteria,
        "artifacts": artifacts,
    }

    write_json(artifacts["results_json"], result)
    write_csv(artifacts["criteria_csv"], [asdict(row) for row in criteria])
    write_csv(artifacts["source_checks_csv"], [asdict(row) for row in checks])
    write_csv(artifacts["identity_contract_csv"], [asdict(row) for row in identities])
    write_csv(artifacts["placement_contract_csv"], [asdict(row) for row in placements])
    write_csv(artifacts["message_paths_csv"], [asdict(row) for row in paths])
    write_csv(artifacts["readback_contract_csv"], [asdict(row) for row in readbacks])
    write_csv(artifacts["failure_classes_csv"], [asdict(row) for row in failures])
    write_csv(artifacts["next_gate_plan_csv"], [asdict(row) for row in gates])
    write_report(
        artifacts["report_md"],
        generated_at=generated_at,
        output_dir=output_dir,
        status=status,
        criteria=criteria,
        summary=summary,
        identities=identities,
        placements=placements,
        paths=paths,
        readbacks=readbacks,
        failures=failures,
        gates=gates,
    )

    latest = {
        "claim": "Latest Tier 4.32c inter-chip feasibility contract.",
        "generated_at_utc": generated_at,
        "manifest": str(artifacts["results_json"]),
        "status": status,
        "tier": TIER,
    }
    write_json(LATEST_MANIFEST, latest)

    return result


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
                "recommended_next_step": result["summary"]["recommended_next_step"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    if result["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
