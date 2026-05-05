#!/usr/bin/env python3
"""Tier 4.30c multi-core lifecycle state-split contract/local reference.

This gate is deliberately local-only. It defines the smallest reviewer-defensible
multi-core lifecycle split before any C runtime migration or EBRAINS upload:

- the lifecycle core is the sole writer of lifecycle slot state;
- learning may request trophic/lifecycle events but must not mutate slots;
- context/route/memory cores consume active-mask snapshots but do not own them;
- host traffic is setup/readback only; inter-core lifecycle traffic is the
  scalable path that later maps to MCPL/multicast.

PASS means the split contract and local split reference reproduce the existing
Tier 4.30a canonical/boundary lifecycle summaries and build directly on the
ingested Tier 4.30b-hw single-core hardware smoke. It is not C implementation,
not hardware evidence, not task-benefit evidence, not speedup, and not a
lifecycle baseline freeze.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"

sys.path.insert(0, str(ROOT))

TIER = "Tier 4.30c - Multi-Core Lifecycle State Split Contract/Reference"
RUNNER_REVISION = "tier4_30c_multicore_lifecycle_split_20260505_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier4_30c_20260505_multicore_lifecycle_split"

TIER4_30A_RESULTS = (
    CONTROLLED
    / "tier4_30a_20260505_static_pool_lifecycle_reference"
    / "tier4_30a_results.json"
)
TIER4_30B_RESULTS = (
    CONTROLLED
    / "tier4_30b_20260505_lifecycle_source_audit"
    / "tier4_30b_results.json"
)
TIER4_30B_HW_RESULTS = (
    CONTROLLED
    / "tier4_30b_hw_20260505_hardware_pass_ingested"
    / "tier4_30b_hw_results.json"
)

from experiments.tier4_30a_static_pool_lifecycle_reference import (  # noqa: E402
    CONTROL_MODES,
    EVENT_NAMES,
    LifecycleEvent,
    LifecycleReference,
    generate_schedule,
    run_schedule,
)


@dataclass(frozen=True)
class Criterion:
    name: str
    value: Any
    rule: str
    passed: bool
    note: str = ""


@dataclass(frozen=True)
class CoreRole:
    role: str
    proposed_p_core: int
    owner: str
    owns_state: str
    accepts: str
    emits: str
    forbidden: str


@dataclass(frozen=True)
class MessageSpec:
    message: str
    transport: str
    source: str
    destination: str
    payload_fields: str
    deterministic_rule: str
    ack_or_readback: str
    failure_if: str


@dataclass(frozen=True)
class FailureClass:
    failure_class: str
    detection: str
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


def criterion(name: str, value: Any, rule: str, passed: bool, note: str = "") -> Criterion:
    return Criterion(name=name, value=value, rule=rule, passed=bool(passed), note=note)


def core_roles() -> list[CoreRole]:
    return [
        CoreRole(
            role="context_core",
            proposed_p_core=4,
            owner="native context mechanism bridge",
            owns_state="context slots and context confidence",
            accepts="active-mask snapshot for optional future context gating",
            emits="context lookup replies",
            forbidden="must not mutate lifecycle slots, lineage, trophic state, or active masks",
        ),
        CoreRole(
            role="route_core",
            proposed_p_core=5,
            owner="native route/composition mechanism bridge",
            owns_state="route slots and route confidence",
            accepts="active-mask snapshot for optional future route gating",
            emits="route lookup replies",
            forbidden="must not mutate lifecycle slots, lineage, trophic state, or active masks",
        ),
        CoreRole(
            role="memory_core",
            proposed_p_core=6,
            owner="native keyed-memory/replay mechanism bridge",
            owns_state="memory slots, replay/consolidation keys, memory confidence",
            accepts="active-mask snapshot for optional future memory-slot gating",
            emits="memory lookup replies",
            forbidden="must not mutate lifecycle slots, lineage, trophic state, or active masks",
        ),
        CoreRole(
            role="learning_core",
            proposed_p_core=7,
            owner="native delayed-credit/readout mechanism bridge",
            owns_state="pending horizons, readout weight/bias, confidence-gated reward updates",
            accepts="lifecycle event ack, active-mask snapshot, compact lifecycle summary",
            emits="trophic update request, lifecycle event request, lifecycle read request",
            forbidden="must not directly write lifecycle slot state or fabricate lineage",
        ),
        CoreRole(
            role="lifecycle_core",
            proposed_p_core=8,
            owner="Tier 4.30 static-pool lifecycle surface",
            owns_state="fixed slot pool, active masks, lineage IDs, trophic health, event counters, sham mode",
            accepts="init, trophic/event requests, sham mode, readback request",
            emits="event ack, active-mask sync, compact summary, optional full-slot rows",
            forbidden="must not run task readout learning or rewrite context/route/memory tables",
        ),
    ]


def message_specs() -> list[MessageSpec]:
    return [
        MessageSpec(
            message="LIFE_INIT_CONTROL",
            transport="host SDP control",
            source="host",
            destination="lifecycle_core",
            payload_fields="pool_size, founder_count, seed, trophic_seed_raw, generation_seed",
            deterministic_rule="initialize exactly the Tier 4.30a static pool",
            ack_or_readback="compact lifecycle summary with payload_len=68",
            failure_if="wrong pool size, nonzero invalid events, missing compact summary",
        ),
        MessageSpec(
            message="LIFE_EVENT_REQUEST",
            transport="inter-core event packet; MCPL/multicast target, SDP permitted only in local transitional tests",
            source="learning_core",
            destination="lifecycle_core",
            payload_fields="event_index, event_type, target_slot, parent_slot, child_slot, trophic_delta_raw, reward_raw",
            deterministic_rule="lifecycle_core applies event once if invariants hold",
            ack_or_readback="event_count, active_mask_bits, lineage_checksum, trophic_checksum",
            failure_if="duplicate event, stale event, invalid event hidden, or checksum mismatch",
        ),
        MessageSpec(
            message="LIFE_TROPHIC_UPDATE",
            transport="inter-core event packet; MCPL/multicast target",
            source="learning_core",
            destination="lifecycle_core",
            payload_fields="slot_id, trophic_delta_raw, reward_raw, confidence_raw, source_timestep",
            deterministic_rule="trophic update changes trophic/cyclin/bax only; no lineage mutation",
            ack_or_readback="slot status and compact trophic checksum",
            failure_if="inactive slot silently accepted or lineage changes on trophic-only event",
        ),
        MessageSpec(
            message="LIFE_ACTIVE_MASK_SYNC",
            transport="inter-core broadcast; MCPL/multicast target",
            source="lifecycle_core",
            destination="context_core, route_core, memory_core, learning_core",
            payload_fields="event_count, active_mask_bits, active_count, lineage_checksum",
            deterministic_rule="emitted after every accepted mask-mutating event and after init",
            ack_or_readback="receiving cores expose last_seen_lifecycle_event_count in later source audits",
            failure_if="consumer sees stale active mask after cleavage, birth, or death",
        ),
        MessageSpec(
            message="LIFE_SUMMARY_READBACK",
            transport="host SDP readback",
            source="host",
            destination="lifecycle_core",
            payload_fields="read_scope, start_slot, slot_count, schema_version",
            deterministic_rule="readback is versioned; compact schema-v1 length is payload_len=68",
            ack_or_readback="compact summary, optional full-slot rows in later tiers",
            failure_if="unversioned readback, cumulative byte counter used as payload-size proof",
        ),
    ]


def failure_classes() -> list[FailureClass]:
    return [
        FailureClass("duplicate_event", "same event_index accepted twice", "event replay/transport defect", "fail gate; add dedup counter before hardware"),
        FailureClass("stale_event", "event_index lower than lifecycle event counter", "out-of-order lifecycle mutation risk", "fail gate; add stale counter/readback"),
        FailureClass("missing_ack", "learning_core request has no lifecycle ack", "inter-core timeout or routing failure", "fail gate; no inferred success"),
        FailureClass("mask_desync", "consumer active mask differs from lifecycle_core", "distributed state corruption", "fail gate; require active-mask sync readback"),
        FailureClass("checksum_mismatch", "lineage/trophic checksum differs from reference", "lifecycle state corruption", "fail gate; inspect event trace"),
        FailureClass("invalid_event_hidden", "invalid event not counted", "invariant audit broken", "fail gate; invalid_event_count must be explicit"),
        FailureClass("wrong_owner_write", "non-lifecycle core writes slot fields", "architecture boundary violation", "fail gate; reject implementation"),
        FailureClass("payload_schema_drift", "payload_len/schema version mismatch", "host/runtime parser drift", "fail gate; update protocol/tests before EBRAINS"),
    ]


def summary_subset(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "pool_size": summary["pool_size"],
        "founder_count": summary["founder_count"],
        "active_count": summary["active_count"],
        "inactive_count": summary["inactive_count"],
        "active_mask_bits": summary["active_mask_bits"],
        "attempted_event_count": summary["attempted_event_count"],
        "event_count": summary["event_count"],
        "cleavage_count": summary["cleavage_count"],
        "birth_count": summary["birth_count"],
        "death_count": summary["death_count"],
        "invalid_event_count": summary["invalid_event_count"],
        "lineage_checksum": summary["lineage_checksum"],
        "trophic_checksum": summary["trophic_checksum"],
    }


def artifact_expected_summary(tier4_30a: dict[str, Any], scenario: str) -> dict[str, Any]:
    for row in tier4_30a["scenarios"]:
        if row["scenario"] == scenario:
            enabled = row["summary_by_mode"]["enabled"]
            return summary_subset(enabled)
    raise KeyError(f"missing scenario in Tier 4.30a artifact: {scenario}")


def local_expected_summary(scenario: str, event_count: int) -> dict[str, Any]:
    state = run_schedule(scenario, generate_schedule(event_count), mode="enabled")
    return summary_subset(state.summary())


class MultiCoreLifecycleSplitReference:
    def __init__(self, scenario: str, schedule: list[LifecycleEvent]) -> None:
        self.scenario = scenario
        self.schedule = list(schedule)
        self.lifecycle = LifecycleReference(mode="enabled")
        self.rows: list[dict[str, Any]] = []
        self.ack_count = 0
        self.mask_sync_count = 1  # init broadcasts the initial active mask
        self.consumer_masks = {
            "context_core": self.lifecycle.active_mask_bits(),
            "route_core": self.lifecycle.active_mask_bits(),
            "memory_core": self.lifecycle.active_mask_bits(),
            "learning_core": self.lifecycle.active_mask_bits(),
        }
        self._emit_row(
            stage="init",
            event=LifecycleEvent(-1, "trophic_update", target_slot=0),
            before_mask=0,
            after_mask=self.lifecycle.active_mask_bits(),
            accepted=True,
            message="LIFE_INIT_CONTROL",
        )

    def _broadcast_mask(self, event_index: int) -> None:
        mask = self.lifecycle.active_mask_bits()
        for core in self.consumer_masks:
            self.consumer_masks[core] = mask
        self.mask_sync_count += 1
        self.rows.append(
            {
                "scenario": self.scenario,
                "stage": "active_mask_sync",
                "message": "LIFE_ACTIVE_MASK_SYNC",
                "event_index": event_index,
                "active_mask_bits": mask,
                "active_count": len(self.lifecycle.active_slots()),
                "lineage_checksum": self.lifecycle.lineage_checksum(),
                "transport": "inter-core broadcast target",
                "source_core": "lifecycle_core",
                "destination_core": "context_core,route_core,memory_core,learning_core",
            }
        )

    def _emit_row(
        self,
        *,
        stage: str,
        event: LifecycleEvent,
        before_mask: int,
        after_mask: int,
        accepted: bool,
        message: str,
    ) -> None:
        summary = self.lifecycle.summary()
        self.rows.append(
            {
                "scenario": self.scenario,
                "stage": stage,
                "message": message,
                "event_index": event.event_index,
                "event_type": event.event_type,
                "target_slot": event.target_slot,
                "parent_slot": event.parent_slot,
                "child_slot": event.child_slot,
                "before_active_mask_bits": before_mask,
                "after_active_mask_bits": after_mask,
                "accepted": int(accepted),
                "active_count": summary["active_count"],
                "inactive_count": summary["inactive_count"],
                "event_count": summary["event_count"],
                "lineage_checksum": summary["lineage_checksum"],
                "trophic_checksum": summary["trophic_checksum"],
                "transport": "inter-core event target" if stage == "event" else "host control/readback",
                "source_core": "learning_core" if stage == "event" else "host",
                "destination_core": "lifecycle_core",
            }
        )

    def run(self) -> dict[str, Any]:
        for event in self.schedule:
            before_mask = self.lifecycle.active_mask_bits()
            before_event_count = self.lifecycle.summary()["event_count"]
            self.lifecycle.apply(self.scenario, event)
            after_mask = self.lifecycle.active_mask_bits()
            after_event_count = self.lifecycle.summary()["event_count"]
            accepted = after_event_count == before_event_count + 1
            self.ack_count += int(accepted)
            self._emit_row(
                stage="event",
                event=event,
                before_mask=before_mask,
                after_mask=after_mask,
                accepted=accepted,
                message="LIFE_EVENT_REQUEST",
            )
            if after_mask != before_mask:
                self._broadcast_mask(event.event_index)
        final = summary_subset(self.lifecycle.summary())
        return {
            "scenario": self.scenario,
            "event_count": len(self.schedule),
            "ack_count": self.ack_count,
            "mask_sync_count": self.mask_sync_count,
            "consumer_masks": dict(self.consumer_masks),
            "consumer_masks_match": all(mask == final["active_mask_bits"] for mask in self.consumer_masks.values()),
            "summary": final,
            "rows": self.rows,
        }


def build_results() -> dict[str, Any]:
    tier4_30a = load_json(TIER4_30A_RESULTS)
    tier4_30b = load_json(TIER4_30B_RESULTS)
    tier4_30b_hw = load_json(TIER4_30B_HW_RESULTS)

    roles = core_roles()
    messages = message_specs()
    failures = failure_classes()
    scenario_counts = {"canonical_32": 32, "boundary_64": 64}
    scenario_results: list[dict[str, Any]] = []
    trace_rows: list[dict[str, Any]] = []

    for scenario, count in scenario_counts.items():
        reference = MultiCoreLifecycleSplitReference(scenario, generate_schedule(count)).run()
        reference["artifact_expected"] = artifact_expected_summary(tier4_30a, scenario)
        reference["local_expected"] = local_expected_summary(scenario, count)
        reference["matches_artifact_expected"] = reference["summary"] == reference["artifact_expected"]
        reference["matches_local_expected"] = reference["summary"] == reference["local_expected"]
        trace_rows.extend(reference.pop("rows"))
        scenario_results.append(reference)

    owner_count = {}
    for role in roles:
        for field in [
            "fixed slot pool",
            "active masks",
            "lineage IDs",
            "trophic health",
            "event counters",
            "sham mode",
        ]:
            if field in role.owns_state:
                owner_count[field] = owner_count.get(field, 0) + 1

    criteria = [
        criterion("Tier 4.30a reference passed", tier4_30a.get("status"), "== pass", tier4_30a.get("status") == "pass"),
        criterion("Tier 4.30b source audit passed", tier4_30b.get("status"), "== pass", tier4_30b.get("status") == "pass"),
        criterion("Tier 4.30b-hw corrected ingest passed", tier4_30b_hw.get("status"), "== pass", tier4_30b_hw.get("status") == "pass"),
        criterion(
            "Tier 4.30b-hw raw remote failure preserved",
            tier4_30b_hw.get("raw_remote_status"),
            "== fail with correction",
            tier4_30b_hw.get("raw_remote_status") == "fail"
            and tier4_30b_hw.get("false_fail_correction", {}).get("applied") is True,
        ),
        criterion("five-core role map declared", [role.role for role in roles], "includes lifecycle core plus 4.29 bridge cores", len(roles) == 5 and any(role.role == "lifecycle_core" for role in roles)),
        criterion("lifecycle fields single-owned", owner_count, "all lifecycle fields owned once", all(value == 1 for value in owner_count.values()) and len(owner_count) == 6),
        criterion("learning core cannot write lifecycle slots", [role.forbidden for role in roles if role.role == "learning_core"], "forbidden direct slot writes", "must not directly write lifecycle slot state" in next(role.forbidden for role in roles if role.role == "learning_core")),
        criterion("host limited to control/readback", [msg.message for msg in messages if msg.source == "host"], "host only init/readback", {msg.message for msg in messages if msg.source == "host"} == {"LIFE_INIT_CONTROL", "LIFE_SUMMARY_READBACK"}),
        criterion("inter-core lifecycle messages declared", [msg.message for msg in messages if "inter-core" in msg.transport], "event, trophic, mask sync present", {"LIFE_EVENT_REQUEST", "LIFE_TROPHIC_UPDATE", "LIFE_ACTIVE_MASK_SYNC"}.issubset({msg.message for msg in messages if "inter-core" in msg.transport})),
        criterion("MCPL/multicast target explicit", [msg.transport for msg in messages], "inter-core transport names MCPL/multicast target", all("MCPL/multicast target" in msg.transport for msg in messages if "inter-core" in msg.transport)),
        criterion("canonical split matches artifact reference", next(s for s in scenario_results if s["scenario"] == "canonical_32")["matches_artifact_expected"], "== true", next(s for s in scenario_results if s["scenario"] == "canonical_32")["matches_artifact_expected"]),
        criterion("boundary split matches artifact reference", next(s for s in scenario_results if s["scenario"] == "boundary_64")["matches_artifact_expected"], "== true", next(s for s in scenario_results if s["scenario"] == "boundary_64")["matches_artifact_expected"]),
        criterion("canonical split matches regenerated reference", next(s for s in scenario_results if s["scenario"] == "canonical_32")["matches_local_expected"], "== true", next(s for s in scenario_results if s["scenario"] == "canonical_32")["matches_local_expected"]),
        criterion("boundary split matches regenerated reference", next(s for s in scenario_results if s["scenario"] == "boundary_64")["matches_local_expected"], "== true", next(s for s in scenario_results if s["scenario"] == "boundary_64")["matches_local_expected"]),
        criterion("canonical event ack count", next(s for s in scenario_results if s["scenario"] == "canonical_32")["ack_count"], "== 32", next(s for s in scenario_results if s["scenario"] == "canonical_32")["ack_count"] == 32),
        criterion("boundary event ack count", next(s for s in scenario_results if s["scenario"] == "boundary_64")["ack_count"], "== 64", next(s for s in scenario_results if s["scenario"] == "boundary_64")["ack_count"] == 64),
        criterion("canonical consumers receive final active mask", next(s for s in scenario_results if s["scenario"] == "canonical_32")["consumer_masks_match"], "== true", next(s for s in scenario_results if s["scenario"] == "canonical_32")["consumer_masks_match"]),
        criterion("boundary consumers receive final active mask", next(s for s in scenario_results if s["scenario"] == "boundary_64")["consumer_masks_match"], "== true", next(s for s in scenario_results if s["scenario"] == "boundary_64")["consumer_masks_match"]),
        criterion("payload length requirement explicit", "payload_len=68", "not cumulative readback_bytes", any("payload_len=68" in msg.ack_or_readback for msg in messages)),
        criterion("failure classes cover distributed lifecycle risks", [item.failure_class for item in failures], ">= 8 classes", len(failures) >= 8),
        criterion("no EBRAINS package generated", "local-contract-reference", "mode is local only", True),
        criterion("claim boundary excludes hardware/task/speedup/baseline", "bounded local contract", "explicit exclusions", True),
    ]
    failed = [item for item in criteria if not item.passed]

    return {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "status": "pass" if not failed else "fail",
        "mode": "local-contract-reference",
        "criteria_passed": len(criteria) - len(failed),
        "criteria_total": len(criteria),
        "criteria": criteria,
        "failed_criteria": failed,
        "core_roles": roles,
        "message_specs": messages,
        "failure_classes": failures,
        "scenarios": scenario_results,
        "trace_rows": trace_rows,
        "source_inputs": {
            "tier4_30a_results": str(TIER4_30A_RESULTS),
            "tier4_30b_results": str(TIER4_30B_RESULTS),
            "tier4_30b_hw_results": str(TIER4_30B_HW_RESULTS),
        },
        "claim_boundary": (
            "Tier 4.30c is a local multi-core lifecycle split contract/reference. "
            "It proves ownership, message semantics, failure classes, and deterministic "
            "split-reference parity against Tier 4.30a plus the ingested 4.30b-hw smoke. "
            "It is not C implementation, not hardware evidence, not task-benefit evidence, "
            "not multi-chip scaling, not speedup, not v2.2 temporal migration, and not a "
            "lifecycle baseline freeze."
        ),
        "next_step": (
            "Tier 4.30d multi-core lifecycle runtime source audit/local C host test: "
            "implement the lifecycle-core profile and inter-core message/readback stubs "
            "against this contract before any EBRAINS package."
        ),
    }


def scenario_summary_rows(results: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for scenario in results["scenarios"]:
        row = {
            "scenario": scenario["scenario"],
            "event_count": scenario["event_count"],
            "ack_count": scenario["ack_count"],
            "mask_sync_count": scenario["mask_sync_count"],
            "consumer_masks_match": scenario["consumer_masks_match"],
            "matches_artifact_expected": scenario["matches_artifact_expected"],
            "matches_local_expected": scenario["matches_local_expected"],
        }
        row.update({f"summary_{key}": value for key, value in scenario["summary"].items()})
        rows.append(row)
    return rows


def write_report(path: Path, results: dict[str, Any]) -> None:
    safe = json_safe({key: value for key, value in results.items() if key != "trace_rows"})
    lines = [
        "# Tier 4.30c Multi-Core Lifecycle State Split",
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
        "## Core Ownership Contract",
        "",
        "| Role | Proposed core | Owns | Accepts | Emits | Forbidden |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for role in safe["core_roles"]:
        lines.append(
            f"| `{role['role']}` | `{role['proposed_p_core']}` | {role['owns_state']} | {role['accepts']} | {role['emits']} | {role['forbidden']} |"
        )
    lines.extend([
        "",
        "## Message Contract",
        "",
        "| Message | Transport | Source | Destination | Payload | Ack/Readback | Failure If |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ])
    for msg in safe["message_specs"]:
        lines.append(
            f"| `{msg['message']}` | {msg['transport']} | `{msg['source']}` | `{msg['destination']}` | {msg['payload_fields']} | {msg['ack_or_readback']} | {msg['failure_if']} |"
        )
    lines.extend(["", "## Scenario Results", "", "| Scenario | Events | Acks | Mask Syncs | Final Mask | Lineage | Trophic | Match |", "| --- | --- | --- | --- | --- | --- | --- | --- |"])
    for scenario in safe["scenarios"]:
        summary = scenario["summary"]
        match = scenario["matches_artifact_expected"] and scenario["matches_local_expected"] and scenario["consumer_masks_match"]
        lines.append(
            f"| `{scenario['scenario']}` | `{scenario['event_count']}` | `{scenario['ack_count']}` | `{scenario['mask_sync_count']}` | `{summary['active_mask_bits']}` | `{summary['lineage_checksum']}` | `{summary['trophic_checksum']}` | `{match}` |"
        )
    lines.extend(["", "## Failure Classes", "", "| Failure | Detection | Meaning | Required Response |", "| --- | --- | --- | --- |"])
    for item in safe["failure_classes"]:
        lines.append(
            f"| `{item['failure_class']}` | {item['detection']} | {item['meaning']} | {item['required_response']} |"
        )
    lines.extend(["", "## Criteria", "", "| Criterion | Value | Rule | Pass | Note |", "| --- | --- | --- | --- | --- |"])
    for item in safe["criteria"]:
        value = json.dumps(item["value"], sort_keys=True)
        if len(value) > 140:
            value = value[:137] + "..."
        lines.append(
            f"| {item['name']} | `{value}` | {item['rule']} | {'yes' if item['passed'] else 'no'} | {item.get('note', '')} |"
        )
    lines.extend(["", "## Next Step", "", safe["next_step"], ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    results = build_results()
    serializable = {key: value for key, value in results.items() if key != "trace_rows"}
    serializable["output_dir"] = str(output_dir)

    write_json(output_dir / "tier4_30c_results.json", serializable)
    write_report(output_dir / "tier4_30c_report.md", results | {"output_dir": str(output_dir)})
    write_csv(output_dir / "tier4_30c_core_roles.csv", [asdict(role) for role in results["core_roles"]])
    write_csv(output_dir / "tier4_30c_message_contract.csv", [asdict(msg) for msg in results["message_specs"]])
    write_csv(output_dir / "tier4_30c_failure_classes.csv", [asdict(item) for item in results["failure_classes"]])
    write_csv(output_dir / "tier4_30c_scenario_summary.csv", scenario_summary_rows(results))
    write_csv(output_dir / "tier4_30c_split_trace.csv", results["trace_rows"])
    write_json(
        CONTROLLED / "tier4_30c_latest_manifest.json",
        {
            "tier": TIER,
            "runner_revision": RUNNER_REVISION,
            "generated_at_utc": serializable["generated_at_utc"],
            "status": serializable["status"],
            "manifest": str(output_dir / "tier4_30c_results.json"),
            "output_dir": str(output_dir),
        },
    )
    return serializable


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
