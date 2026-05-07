#!/usr/bin/env python3
"""Tier 4.32b static reef partition smoke/resource mapping.

This tier is a local engineering gate after the Tier 4.32a-hw-replicated
single-chip hardware pass. It does not run SpiNNaker hardware and it does not
claim speedup, multi-chip scaling, or a new learning result.

The goal is narrower and reviewer-facing:

* map CRA reef groups/modules/polyps onto the measured replicated-shard
  single-chip envelope;
* define which core owns which state;
* prove the static map fits source/runtime limits and measured hardware
  counters;
* make the next inter-chip contract gate explicit.
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

TIER = "Tier 4.32b - Static Reef Partition Smoke/Resource Mapping"
RUNNER_REVISION = "tier4_32b_static_reef_partition_smoke_20260507_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier4_32b_20260507_static_reef_partition_smoke"
LATEST_MANIFEST = CONTROLLED / "tier4_32b_latest_manifest.json"

TIER4_32 = CONTROLLED / "tier4_32_20260506_mapping_resource_model" / "tier4_32_results.json"
TIER4_32A = CONTROLLED / "tier4_32a_20260506_single_chip_scale_stress" / "tier4_32a_results.json"
TIER4_32A_R1 = CONTROLLED / "tier4_32a_r1_20260506_mcpl_lookup_repair" / "tier4_32a_r1_results.json"
TIER4_32A_REPLICATED_INGEST = (
    CONTROLLED
    / "tier4_32a_hw_replicated_20260507_hardware_pass_ingested"
    / "tier4_32a_hw_replicated_results.json"
)
TIER4_32A_REPLICATED_RAW = (
    CONTROLLED
    / "tier4_32a_hw_replicated_20260507_hardware_pass_ingested"
    / "returned_artifacts"
    / "tier4_32a_hw_replicated_results.json"
)

CONSERVATIVE_APP_CORES_PER_CHIP = 16
POLYP_POOL_SLOTS = 8
LOOKUP_TYPES_PER_EVENT = 3
CANONICAL_POINT_ID = "point_16c_quad_shard"

CLAIM_BOUNDARY = (
    "Tier 4.32b is local static reef partition/resource evidence over the "
    "measured single-chip replicated-shard envelope. It is not a new "
    "SpiNNaker hardware run, not speedup evidence, not one-polyp-one-chip "
    "evidence, not multi-chip evidence, not benchmark superiority, and not a "
    "native-scale baseline freeze."
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
class ReplicatedEnvelopeRow:
    point_id: str
    status: str
    shards: int
    total_cores: int
    total_events: int
    events_per_shard: int
    expected_lookup_count_per_shard: int
    max_stale_replies: int
    max_duplicate_replies: int
    max_timeouts: int
    max_payload_len: int
    max_learning_readback_bytes: int
    interpretation: str


@dataclass(frozen=True)
class PartitionRow:
    partition_id: str
    shard_id: int
    semantic_group: str
    polyp_slots: str
    context_core: int
    route_core: int
    memory_core: int
    learning_core: int
    module_roles: str
    event_count: int
    expected_lookup_count: int
    measured_lookup_requests: int
    measured_lookup_replies: int
    payload_bytes_per_core: int
    ownership_status: str
    claim_boundary: str


@dataclass(frozen=True)
class CandidateLayout:
    layout_id: str
    total_cores: int
    reef_partitions: int
    lifecycle_cores: int
    polyp_slots: int
    status: str
    decision: str
    evidence_basis: str
    blocker: str


@dataclass(frozen=True)
class OwnershipInvariant:
    invariant_id: str
    owner: str
    owned_state: str
    forbidden_writers: str
    proof_source: str
    failure_if: str


@dataclass(frozen=True)
class FailureClass:
    failure_class: str
    status: str
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


def status_of(payload: dict[str, Any]) -> str:
    return str(payload.get("status") or payload.get("registry_status") or "unknown").lower()


def runtime_limits() -> dict[str, int]:
    config_h = RUNTIME_SRC / "config.h"
    state_h = RUNTIME_SRC / "state_manager.h"
    return {
        "max_context_slots": parse_define_int(config_h, "MAX_CONTEXT_SLOTS"),
        "max_route_slots": parse_define_int(config_h, "MAX_ROUTE_SLOTS"),
        "max_memory_slots": parse_define_int(config_h, "MAX_MEMORY_SLOTS"),
        "max_pending_horizons": parse_define_int(config_h, "MAX_PENDING_HORIZONS"),
        "max_lifecycle_slots": parse_define_int(config_h, "MAX_LIFECYCLE_SLOTS"),
        "max_schedule_entries": parse_define_int(config_h, "MAX_SCHEDULE_ENTRIES"),
        "max_lookup_replies": parse_define_int(state_h, "MAX_LOOKUP_REPLIES"),
        "mcpl_key_shard_mask": parse_define_int(config_h, "MCPL_KEY_SHARD_MASK"),
    }


def source_checks() -> list[SourceCheck]:
    config_h = RUNTIME_SRC / "config.h"
    state_h = RUNTIME_SRC / "state_manager.h"
    state_c = RUNTIME_SRC / "state_manager.c"
    return [
        source_check(config_h, "MCPL_KEY_SHARD_SHIFT", "MCPL keys reserve shard identity bits."),
        source_check(config_h, "MCPL_KEY_SHARD_MASK", "Shard id mask is source-declared."),
        source_check(config_h, "MAKE_MCPL_KEY_SHARD", "Static partitions can map to explicit shard ids."),
        source_check(config_h, "EXTRACT_MCPL_SHARD_ID", "Receivers can decode partition/shard identity."),
        source_check(config_h, "MAX_LIFECYCLE_SLOTS", "Static polyp/lifecycle pool limit is source-declared."),
        source_check(state_h, "cra_state_lookup_send_shard", "Lookup table tracks shard-specific pending entries."),
        source_check(state_h, "cra_state_lookup_get_result_shard", "Shard-specific lookup readback is testable."),
        source_check(state_c, "g_lookup_entries[i].shard_id", "Lookup entries store shard identity."),
        source_check(state_c, "CRA_MCPL_SHARD_ID", "Runtime images can be compiled per static shard."),
    ]


def point_criteria_pass_count(point: dict[str, Any]) -> tuple[int, int]:
    criteria = point.get("criteria") or []
    return sum(1 for item in criteria if item.get("passed")), len(criteria)


def role_final(point: dict[str, Any], shard_id: int, role: str) -> dict[str, Any]:
    return point["shards_detail"][f"s{shard_id}"]["final_state"][role]


def envelope_rows(raw: dict[str, Any]) -> list[ReplicatedEnvelopeRow]:
    rows: list[ReplicatedEnvelopeRow] = []
    for point_id, point in raw["points"].items():
        shards = int(point["shards"])
        max_stale = 0
        max_dup = 0
        max_timeouts = 0
        max_payload = 0
        max_learning_readback = 0
        for shard_id in range(shards):
            learning = role_final(point, shard_id, "learning")
            max_stale = max(max_stale, int(learning.get("stale_replies", 0)))
            max_dup = max(max_dup, int(learning.get("duplicate_replies", 0)))
            max_timeouts = max(max_timeouts, int(learning.get("timeouts", 0)))
            max_payload = max(max_payload, *(int(role_final(point, shard_id, role).get("payload_len", 0)) for role in ["context", "route", "memory", "learning"]))
            max_learning_readback = max(max_learning_readback, int(learning.get("readback_bytes", 0)))
        rows.append(
            ReplicatedEnvelopeRow(
                point_id=point_id,
                status=str(point["status"]),
                shards=shards,
                total_cores=shards * 4,
                total_events=int(point["event_count"]),
                events_per_shard=int(point["events_per_shard"]),
                expected_lookup_count_per_shard=int(point["expected_lookup_count_per_shard"]),
                max_stale_replies=max_stale,
                max_duplicate_replies=max_dup,
                max_timeouts=max_timeouts,
                max_payload_len=max_payload,
                max_learning_readback_bytes=max_learning_readback,
                interpretation="Measured single-chip replicated context/route/memory/learning shard envelope.",
            )
        )
    return rows


def partition_rows(raw: dict[str, Any]) -> list[PartitionRow]:
    point = raw["points"][CANONICAL_POINT_ID]
    rows: list[PartitionRow] = []
    for shard_id in range(int(point["shards"])):
        detail = point["shards_detail"][f"s{shard_id}"]
        cores = detail["cores"]
        learning = role_final(point, shard_id, "learning")
        polyp_slots = [shard_id * 2, shard_id * 2 + 1]
        rows.append(
            PartitionRow(
                partition_id=f"reef_partition_{shard_id}",
                shard_id=shard_id,
                semantic_group=f"static_reef_quadrant_{shard_id}",
                polyp_slots=",".join(str(slot) for slot in polyp_slots),
                context_core=int(cores["context"]),
                route_core=int(cores["route"]),
                memory_core=int(cores["memory"]),
                learning_core=int(cores["learning"]),
                module_roles="context,route,memory,learning",
                event_count=int(point["events_per_shard"]),
                expected_lookup_count=int(point["expected_lookup_count_per_shard"]),
                measured_lookup_requests=int(learning.get("lookup_requests", -1)),
                measured_lookup_replies=int(learning.get("lookup_replies", -1)),
                payload_bytes_per_core=max(
                    int(role_final(point, shard_id, role).get("payload_len", 0))
                    for role in ["context", "route", "memory", "learning"]
                ),
                ownership_status="single_writer_per_module_family",
                claim_boundary="static semantic map over measured replicated shard; not dynamic population growth",
            )
        )
    return rows


def candidate_layouts() -> list[CandidateLayout]:
    return [
        CandidateLayout(
            layout_id="quad_mechanism_partition_v0",
            total_cores=16,
            reef_partitions=4,
            lifecycle_cores=0,
            polyp_slots=8,
            status="eligible_static_mapping_reference",
            decision="canonical_4_32b_static_map",
            evidence_basis="Tier 4.32a-hw-replicated point_16c_quad_shard hardware pass.",
            blocker="dedicated lifecycle core is not included in this exact 16-core envelope",
        ),
        CandidateLayout(
            layout_id="triple_partition_plus_lifecycle_v0",
            total_cores=13,
            reef_partitions=3,
            lifecycle_cores=1,
            polyp_slots=8,
            status="eligible_for_future_local_contract",
            decision="reserve_as_lifecycle_including_single_chip_layout",
            evidence_basis="Tier 4.32a point12 measured replicated shards plus Tier 4.30g lifecycle core evidence, but not yet run as one combined hardware layout.",
            blocker="combined 12-core plus lifecycle layout has not been hardware-smoked as a single package",
        ),
        CandidateLayout(
            layout_id="quad_partition_plus_dedicated_lifecycle_v0",
            total_cores=17,
            reef_partitions=4,
            lifecycle_cores=1,
            polyp_slots=8,
            status="blocked_on_single_chip_budget",
            decision="requires multi-chip or distributed lifecycle ownership",
            evidence_basis="16-core replicated shard pass plus lifecycle-core requirement exceeds conservative 16 application-core envelope.",
            blocker="17 cores exceeds conservative single-chip app-core budget",
        ),
        CandidateLayout(
            layout_id="one_polyp_one_chip",
            total_cores=8,
            reef_partitions=8,
            lifecycle_cores=0,
            polyp_slots=8,
            status="rejected_claim",
            decision="do_not_use_as_claim",
            evidence_basis="No evidence maps one polyp to one chip; current evidence maps groups of polyp slots to shard/core groups.",
            blocker="conceptual mapping is unsupported by current runtime/evidence",
        ),
    ]


def ownership_invariants() -> list[OwnershipInvariant]:
    return [
        OwnershipInvariant(
            "single_context_owner",
            "context_core within each reef partition",
            "context slots and context lookup replies for that shard id",
            "route_core,memory_core,learning_core,lifecycle_core,host after setup",
            "point16 per-shard context readback plus shard-aware MCPL key",
            "context slot writes or replies are observed from a non-owner shard/core",
        ),
        OwnershipInvariant(
            "single_route_owner",
            "route_core within each reef partition",
            "route slots and route lookup replies for that shard id",
            "context_core,memory_core,learning_core,lifecycle_core,host after setup",
            "point16 per-shard route readback plus shard-aware MCPL key",
            "route lookup replies cross shard or duplicate for one pending lookup",
        ),
        OwnershipInvariant(
            "single_memory_owner",
            "memory_core within each reef partition",
            "memory slots and memory lookup replies for that shard id",
            "context_core,route_core,learning_core,lifecycle_core,host after setup",
            "point16 per-shard memory readback plus shard-aware MCPL key",
            "memory lookup replies cross shard or duplicate for one pending lookup",
        ),
        OwnershipInvariant(
            "single_learning_owner",
            "learning_core within each reef partition",
            "pending horizons, reward maturation, readout update, lookup request accounting",
            "context_core,route_core,memory_core,lifecycle_core",
            "point16 learning pending/reply parity and final readout state",
            "pending horizon mutates outside the owning learning core",
        ),
        OwnershipInvariant(
            "static_polyp_slot_owner",
            "reef partition assigned by slot // 2",
            "two static polyp/lifecycle slots per reef partition",
            "other reef partitions",
            "4.30 static lifecycle pool size plus 4.32a-hw-replicated shard ids",
            "one polyp slot appears in more than one partition or no partition",
        ),
        OwnershipInvariant(
            "lifecycle_boundary_explicit",
            "host-ferried or future lifecycle owner",
            "birth/death/trophic mutation until a combined lifecycle partition is measured",
            "context,route,memory,learning replicated shard cores",
            "CRA_LIFECYCLE_NATIVE_BASELINE_v0.4 boundary and 4.32b candidate-layout table",
            "4.32b is described as autonomous lifecycle-to-learning MCPL",
        ),
    ]


def failure_classes() -> list[FailureClass]:
    return [
        FailureClass(
            "static_partition_overlap",
            "bounded_by_4_32b",
            "core ids and polyp slots must be unique across partitions",
            "repair partition map before 4.32c",
            "inter-chip contract",
        ),
        FailureClass(
            "shard_key_exhaustion",
            "bounded_by_4_32b",
            "max shard id must be <= MCPL_KEY_SHARD_MASK",
            "increase key width or reduce static partitions",
            "inter-chip contract",
        ),
        FailureClass(
            "lookup_parity_regression",
            "measured_clean_in_4_32a_hw_replicated",
            "per-partition lookup requests must equal replies",
            "do not proceed to 4.32c; repair MCPL routing/readback",
            "multi-chip smoke",
        ),
        FailureClass(
            "lifecycle_core_budget_overflow",
            "detected_by_candidate_layouts",
            "quad partition plus dedicated lifecycle requires 17 cores",
            "choose distributed lifecycle ownership or move lifecycle owner to another chip",
            "native-scale baseline freeze",
        ),
        FailureClass(
            "one_polyp_one_chip_overclaim",
            "rejected_by_4_32b",
            "current evidence maps polyp slots to partition groups, not one polyp to one chip",
            "keep docs/claims at group/module/slot mapping level",
            "paper claim boundary",
        ),
        FailureClass(
            "static_readback_ambiguity",
            "bounded_by_4_32b",
            "readback must include partition/shard/core role enough to reconstruct ownership",
            "add partition id fields before hardware packaging",
            "inter-chip contract",
        ),
        FailureClass(
            "multi_chip_route_ambiguity",
            "out_of_scope_until_4_32c",
            "board/chip id is not represented in current single-chip partition map",
            "define board/chip/routing key fields in 4.32c before first multi-chip smoke",
            "4.32d hardware smoke",
        ),
    ]


def next_gates() -> list[NextGate]:
    return [
        NextGate(
            gate="Tier 4.32c",
            decision="authorize_next_if_4_32b_passes",
            question="What exact inter-chip routing/readback contract carries static reef partitions beyond one chip?",
            prerequisites="4.32b static partition map, unique shard/core/polyp ownership, and preserved 4.32a-hw-replicated counters.",
            pass_boundary="Contract declares board/chip/shard key fields, message path, readback fields, failure counters, and smallest cross-chip smoke target.",
            fail_boundary="If board/chip identity or readback ownership is ambiguous, do not prepare a multi-chip job.",
            claim_boundary="contract evidence only; not hardware execution and not multi-chip learning",
        ),
        NextGate(
            gate="Tier 4.32d",
            decision="blocked_until_4_32c_passes",
            question="Can the smallest cross-chip static-partition message/readback smoke execute cleanly?",
            prerequisites="4.32c inter-chip contract and source/package QA.",
            pass_boundary="Real hardware run returns zero stale/duplicate/timeout/drop counters and reconstructable partition ownership.",
            fail_boundary="Classify as target/load/routing/readback/schema/environment before rerun.",
            claim_boundary="first multi-chip smoke only; not speedup and not learning scale",
        ),
        NextGate(
            gate="Tier 4.32e",
            decision="blocked_until_4_32d_passes",
            question="Can a tiny cross-chip learning micro-task preserve the native loop?",
            prerequisites="4.32d cross-chip communication smoke.",
            pass_boundary="Cross-chip learning micro-task matches fixed-point/local reference within predeclared tolerance.",
            fail_boundary="Do not run larger tasks or benchmarks until the micro-task is stable.",
            claim_boundary="tiny multi-chip learning evidence only",
        ),
        NextGate(
            gate="native scale baseline freeze",
            decision="not_authorized",
            question="Is the native runtime stable enough to freeze as a scale baseline?",
            prerequisites="4.32b static partition, 4.32c contract, 4.32d smoke, and 4.32e micro-learning all pass.",
            pass_boundary="Freeze only after static partition and first multi-chip evidence are clean.",
            fail_boundary="Keep CRA_LIFECYCLE_NATIVE_BASELINE_v0.4 as latest native baseline and publish limits honestly.",
            claim_boundary="baseline decision is separate from this local mapping tier",
        ),
    ]


def build_results() -> dict[str, Any]:
    tier4_32 = read_json(TIER4_32)
    tier4_32a = read_json(TIER4_32A)
    tier4_32a_r1 = read_json(TIER4_32A_R1)
    ingest = read_json(TIER4_32A_REPLICATED_INGEST)
    raw = read_json(TIER4_32A_REPLICATED_RAW)

    limits = runtime_limits()
    checks = source_checks()
    envelope = envelope_rows(raw)
    partitions = partition_rows(raw)
    layouts = candidate_layouts()
    invariants = ownership_invariants()
    failures = failure_classes()
    gates = next_gates()

    canonical = raw["points"][CANONICAL_POINT_ID]
    canonical_pass, canonical_total = point_criteria_pass_count(canonical)
    all_cores: list[int] = []
    all_polyp_slots: list[int] = []
    for row in partitions:
        all_cores.extend([row.context_core, row.route_core, row.memory_core, row.learning_core])
        all_polyp_slots.extend(int(slot) for slot in row.polyp_slots.split(","))

    lookup_parity = all(row.measured_lookup_requests == row.measured_lookup_replies == row.expected_lookup_count for row in partitions)
    max_shard_id = max(row.shard_id for row in partitions)
    shard_mask = int(limits["mcpl_key_shard_mask"])
    point_statuses = {point_id: point["status"] for point_id, point in raw["points"].items()}
    source_ok = all(check.present for check in checks)
    canonical_layout = next(row for row in layouts if row.layout_id == "quad_mechanism_partition_v0")
    blocked_lifecycle_layout = next(row for row in layouts if row.layout_id == "quad_partition_plus_dedicated_lifecycle_v0")

    criteria = [
        criterion("Tier 4.32 prerequisite passed", status_of(tier4_32), "== pass", status_of(tier4_32) == "pass"),
        criterion("Tier 4.32a preflight passed", status_of(tier4_32a), "== pass", status_of(tier4_32a) == "pass"),
        criterion("Tier 4.32a-r1 MCPL repair passed", status_of(tier4_32a_r1), "== pass", status_of(tier4_32a_r1) == "pass"),
        criterion("Tier 4.32a-hw-replicated ingest passed", status_of(ingest), "== pass", status_of(ingest) == "pass"),
        criterion("raw replicated hardware pass", raw.get("status"), "== pass", raw.get("status") == "pass"),
        criterion("raw final decision authorized 4.32b", raw.get("final_decision", {}).get("tier4_32b_static_reef_partitioning"), "== authorized_next", raw.get("final_decision", {}).get("tier4_32b_static_reef_partitioning") == "authorized_next"),
        criterion("replicated stress points all passed", point_statuses, "point08/12/16 all pass", all(value == "pass" for value in point_statuses.values())),
        criterion("canonical point16 criteria all passed", f"{canonical_pass}/{canonical_total}", "all pass", canonical_pass == canonical_total and canonical_total > 0),
        criterion("canonical point has four reef partitions", len(partitions), "== 4", len(partitions) == 4),
        criterion("canonical point uses conservative 16 app-core envelope", canonical_layout.total_cores, f"<= {CONSERVATIVE_APP_CORES_PER_CHIP}", canonical_layout.total_cores <= CONSERVATIVE_APP_CORES_PER_CHIP),
        criterion("partition core ownership unique", sorted(all_cores), "16 unique cores", len(all_cores) == len(set(all_cores)) == 16),
        criterion("partition polyp slots cover static pool exactly", sorted(all_polyp_slots), f"== 0..{POLYP_POOL_SLOTS - 1}", sorted(all_polyp_slots) == list(range(POLYP_POOL_SLOTS))),
        criterion("polyp slots fit lifecycle source limit", POLYP_POOL_SLOTS, "<= MAX_LIFECYCLE_SLOTS", POLYP_POOL_SLOTS <= limits["max_lifecycle_slots"]),
        criterion("shard ids fit MCPL key mask", max_shard_id, f"<= {shard_mask}", max_shard_id <= shard_mask),
        criterion("source tokens support shard-aware partitioning", [asdict(check) for check in checks], "all present", source_ok),
        criterion("lookup parity holds for every partition", {row.partition_id: f"{row.measured_lookup_requests}/{row.measured_lookup_replies}" for row in partitions}, "requests == replies == expected", lookup_parity),
        criterion("no stale/duplicate/timeouts in replicated envelope", [(row.point_id, row.max_stale_replies, row.max_duplicate_replies, row.max_timeouts) for row in envelope], "all zero", all(row.max_stale_replies == row.max_duplicate_replies == row.max_timeouts == 0 for row in envelope)),
        criterion("event schedule per partition within source limit", max(row.event_count for row in partitions), "<= MAX_SCHEDULE_ENTRIES", max(row.event_count for row in partitions) <= limits["max_schedule_entries"]),
        criterion("lookup count per partition matches three lookup types per event", {row.partition_id: row.expected_lookup_count for row in partitions}, "event_count * 3", all(row.expected_lookup_count == row.event_count * LOOKUP_TYPES_PER_EVENT for row in partitions)),
        criterion("dedicated lifecycle plus quad partition correctly blocked", blocked_lifecycle_layout.total_cores, f"> {CONSERVATIVE_APP_CORES_PER_CHIP}", blocked_lifecycle_layout.status == "blocked_on_single_chip_budget" and blocked_lifecycle_layout.total_cores > CONSERVATIVE_APP_CORES_PER_CHIP),
        criterion("one-polyp-one-chip claim rejected", next(row for row in layouts if row.layout_id == "one_polyp_one_chip").status, "== rejected_claim", next(row for row in layouts if row.layout_id == "one_polyp_one_chip").status == "rejected_claim"),
        criterion("ownership invariants cover lifecycle boundary", [row.invariant_id for row in invariants], "contains lifecycle_boundary_explicit", any(row.invariant_id == "lifecycle_boundary_explicit" for row in invariants)),
        criterion("failure classes include multi-chip ambiguity", [row.failure_class for row in failures], "contains multi_chip_route_ambiguity", any(row.failure_class == "multi_chip_route_ambiguity" for row in failures)),
        criterion("next gate is 4.32c contract, not hardware jump", gates[0].gate, "== Tier 4.32c", gates[0].gate == "Tier 4.32c" and gates[0].decision == "authorize_next_if_4_32b_passes"),
        criterion("native scale baseline freeze remains blocked", gates[-1].decision, "== not_authorized", gates[-1].decision == "not_authorized"),
    ]
    failed = [item for item in criteria if not item.passed]
    status = "pass" if not failed else "fail"

    final_decision = {
        "status": status,
        "canonical_static_layout": canonical_layout.layout_id,
        "tier4_32c": "authorized_next_contract" if status == "pass" else "blocked_until_static_partition_repairs",
        "tier4_32d": "blocked_until_4_32c_passes",
        "tier4_32e": "blocked_until_4_32d_passes",
        "multi_chip_scaling": "blocked_until_4_32c_contract_and_4_32d_smoke",
        "speedup_claims": "not_authorized",
        "native_scale_baseline_freeze": "not_authorized",
        "claim_boundary": "local static reef partition mapping only",
    }

    return {
        "tier": "4.32b",
        "tier_name": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "status": status,
        "criteria_passed": len(criteria) - len(failed),
        "criteria_total": len(criteria),
        "criteria": criteria,
        "failed_criteria": failed,
        "source_checks": checks,
        "runtime_limits": limits,
        "evidence_inputs": {
            "tier4_32": rel(TIER4_32),
            "tier4_32a": rel(TIER4_32A),
            "tier4_32a_r1": rel(TIER4_32A_R1),
            "tier4_32a_hw_replicated_ingest": rel(TIER4_32A_REPLICATED_INGEST),
            "tier4_32a_hw_replicated_raw": rel(TIER4_32A_REPLICATED_RAW),
        },
        "replicated_envelope": envelope,
        "partition_map": partitions,
        "candidate_layouts": layouts,
        "ownership_invariants": invariants,
        "failure_classes": failures,
        "next_gate_plan": gates,
        "final_decision": final_decision,
        "recommended_next_step": (
            "Tier 4.32c inter-chip feasibility contract: define board/chip/shard key fields, readback ownership, and first cross-chip smoke target."
            if status == "pass"
            else "Repair Tier 4.32b static partition ownership/resource failures before inter-chip contract work."
        ),
        "claim_boundary": CLAIM_BOUNDARY,
    }


def write_report(path: Path, results: dict[str, Any]) -> None:
    lines = [
        "# Tier 4.32b Static Reef Partition Smoke/Resource Mapping",
        "",
        f"- Generated: `{results['generated_at_utc']}`",
        f"- Runner revision: `{results['runner_revision']}`",
        f"- Status: **{results['status'].upper()}**",
        f"- Criteria: `{results['criteria_passed']}/{results['criteria_total']}`",
        f"- Recommended next step: {results['recommended_next_step']}",
        "",
        "## Claim Boundary",
        "",
        results["claim_boundary"],
        "",
        "## Final Decision",
        "",
    ]
    for key, value in results["final_decision"].items():
        lines.append(f"- `{key}`: `{value}`")

    lines.extend(
        [
            "",
            "## Canonical Static Partition Map",
            "",
            "| Partition | Shard | Polyp Slots | Context | Route | Memory | Learning | Events | Lookups | Status |",
            "| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for row in results["partition_map"]:
        lines.append(
            f"| `{row['partition_id']}` | {row['shard_id']} | `{row['polyp_slots']}` | "
            f"{row['context_core']} | {row['route_core']} | {row['memory_core']} | "
            f"{row['learning_core']} | {row['event_count']} | {row['expected_lookup_count']} | "
            f"`{row['ownership_status']}` |"
        )

    lines.extend(
        [
            "",
            "## Candidate Layouts",
            "",
            "| Layout | Cores | Partitions | Lifecycle Cores | Slots | Status | Decision | Blocker |",
            "| --- | ---: | ---: | ---: | ---: | --- | --- | --- |",
        ]
    )
    for row in results["candidate_layouts"]:
        lines.append(
            f"| `{row['layout_id']}` | {row['total_cores']} | {row['reef_partitions']} | "
            f"{row['lifecycle_cores']} | {row['polyp_slots']} | `{row['status']}` | "
            f"{row['decision']} | {row['blocker']} |"
        )

    lines.extend(
        [
            "",
            "## Replicated Hardware Envelope",
            "",
            "| Point | Status | Shards | Cores | Events | Events/Shard | Lookups/Shard | Stale/Dup/Timeout |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for row in results["replicated_envelope"]:
        lines.append(
            f"| `{row['point_id']}` | `{row['status']}` | {row['shards']} | {row['total_cores']} | "
            f"{row['total_events']} | {row['events_per_shard']} | {row['expected_lookup_count_per_shard']} | "
            f"{row['max_stale_replies']}/{row['max_duplicate_replies']}/{row['max_timeouts']} |"
        )

    lines.extend(
        [
            "",
            "## Criteria",
            "",
            "| Criterion | Value | Rule | Pass |",
            "| --- | --- | --- | --- |",
        ]
    )
    for item in results["criteria"]:
        value = json.dumps(item["value"], sort_keys=True) if isinstance(item["value"], (dict, list)) else item["value"]
        lines.append(f"| {item['name']} | `{value}` | {item['rule']} | {'yes' if item['passed'] else 'no'} |")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_outputs(results: dict[str, Any], output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "results_json": output_dir / "tier4_32b_results.json",
        "report_md": output_dir / "tier4_32b_report.md",
        "criteria_csv": output_dir / "tier4_32b_criteria.csv",
        "source_checks_csv": output_dir / "tier4_32b_source_checks.csv",
        "replicated_envelope_csv": output_dir / "tier4_32b_replicated_envelope.csv",
        "partition_map_csv": output_dir / "tier4_32b_partition_map.csv",
        "candidate_layouts_csv": output_dir / "tier4_32b_candidate_layouts.csv",
        "ownership_invariants_csv": output_dir / "tier4_32b_ownership_invariants.csv",
        "failure_classes_csv": output_dir / "tier4_32b_failure_classes.csv",
        "next_gate_plan_csv": output_dir / "tier4_32b_next_gate_plan.csv",
    }
    payload = {**results, "output_dir": str(output_dir), "artifacts": {key: str(value) for key, value in artifacts.items()}}
    write_json(artifacts["results_json"], payload)
    write_csv(artifacts["criteria_csv"], [asdict(item) for item in results["criteria"]])
    write_csv(artifacts["source_checks_csv"], [asdict(item) for item in results["source_checks"]])
    write_csv(artifacts["replicated_envelope_csv"], [asdict(item) for item in results["replicated_envelope"]])
    write_csv(artifacts["partition_map_csv"], [asdict(item) for item in results["partition_map"]])
    write_csv(artifacts["candidate_layouts_csv"], [asdict(item) for item in results["candidate_layouts"]])
    write_csv(artifacts["ownership_invariants_csv"], [asdict(item) for item in results["ownership_invariants"]])
    write_csv(artifacts["failure_classes_csv"], [asdict(item) for item in results["failure_classes"]])
    write_csv(artifacts["next_gate_plan_csv"], [asdict(item) for item in results["next_gate_plan"]])
    write_report(artifacts["report_md"], json_safe(payload))
    write_json(LATEST_MANIFEST, payload)
    return {key: str(value) for key, value in artifacts.items()}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=TIER)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    results = build_results()
    artifacts = write_outputs(results, args.output_dir)
    print(
        json.dumps(
            {
                "status": results["status"],
                "criteria": f"{results['criteria_passed']}/{results['criteria_total']}",
                "output_dir": str(args.output_dir),
                "results": artifacts["results_json"],
                "recommended_next_step": results["recommended_next_step"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if results["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
