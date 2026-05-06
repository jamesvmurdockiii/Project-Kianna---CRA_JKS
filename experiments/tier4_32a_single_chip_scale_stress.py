#!/usr/bin/env python3
"""Tier 4.32a single-chip multi-core scale-stress preflight.

This tier turns the Tier 4.32 resource model into a concrete single-chip scale
stress contract. It deliberately stays local: no SpiNNaker hardware is run here
and no speedup or multi-chip claim is made. The purpose is to predeclare the
core-count, schedule, slot, lookup, MCPL-byte, readback, and profile-headroom
envelope that the next EBRAINS hardware stress package must measure.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"

TIER = "Tier 4.32a - Single-Chip Multi-Core Scale-Stress Preflight"
RUNNER_REVISION = "tier4_32a_single_chip_scale_stress_20260506_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier4_32a_20260506_single_chip_scale_stress"
LATEST_MANIFEST = CONTROLLED / "tier4_32a_latest_manifest.json"

TIER4_32 = CONTROLLED / "tier4_32_20260506_mapping_resource_model" / "tier4_32_results.json"

CONSERVATIVE_APP_CORES_PER_CHIP = 16
LOOKUP_TYPES_PER_EVENT = 3
MCPL_MESSAGES_PER_LOOKUP = 2
MCPL_BYTES_PER_LOOKUP_ROUND_TRIP = 16
SDP_BYTES_PER_LOOKUP_ROUND_TRIP = 54
STANDARD_PAYLOAD_BYTES = 105
LIFECYCLE_PAYLOAD_BYTES = 68
TEMPORAL_PAYLOAD_BYTES = 48


@dataclass(frozen=True)
class Criterion:
    name: str
    value: Any
    rule: str
    passed: bool
    note: str = ""


@dataclass(frozen=True)
class ScalePoint:
    point_id: str
    purpose: str
    status: str
    total_cores: int
    shards: int
    context_cores: int
    route_cores: int
    memory_cores: int
    learning_cores: int
    lifecycle_cores: int
    temporal_state_enabled: bool
    event_count: int
    schedule_entries_per_learning_core: int
    context_slots_per_context_core: int
    route_slots_per_route_core: int
    memory_slots_per_memory_core: int
    lifecycle_slots_per_lifecycle_core: int
    max_pending_horizons: int
    lookup_replies_in_flight: int
    lookup_requests_total: int
    lookup_replies_total: int
    mcpl_messages_total: int
    mcpl_payload_bytes_total: int
    sdp_payload_bytes_if_fallback_total: int
    compact_readback_bytes_per_snapshot: int
    projected_failure_class: str
    claim_boundary: str


@dataclass(frozen=True)
class ProfileAllocation:
    point_id: str
    profile: str
    copies: int
    text_bytes_per_core: int
    dtcm_estimate_bytes_per_core: int
    itcm_headroom_bytes_per_core: int
    dtcm_headroom_bytes_per_core: int
    allocation_status: str
    note: str


@dataclass(frozen=True)
class FailureClass:
    failure_class: str
    preflight_status: str
    detection_rule: str
    hardware_measurement_required: str
    next_gate: str


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
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json_safe(row.get(key, "")) for key in keys})


def criterion(name: str, value: Any, rule: str, passed: bool, note: str = "") -> Criterion:
    return Criterion(name=name, value=value, rule=rule, passed=bool(passed), note=note)


def profile_map(tier4_32: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["profile"]: row for row in tier4_32["profile_budgets"]}


def scale_points(limits: dict[str, int]) -> list[ScalePoint]:
    plans = [
        {
            "point_id": "point_04c_reference",
            "purpose": "Measured four-core family reference carried forward from 4.28e.",
            "shards": 1,
            "event_count": 48,
            "lifecycle": 0,
            "temporal": False,
        },
        {
            "point_id": "point_05c_lifecycle",
            "purpose": "Five-profile lifecycle bridge envelope carried forward from 4.30g.",
            "shards": 1,
            "event_count": 96,
            "lifecycle": 1,
            "temporal": False,
        },
        {
            "point_id": "point_08c_dual_shard",
            "purpose": "First replicated context/route/memory/learning shard stress point.",
            "shards": 2,
            "event_count": 192,
            "lifecycle": 0,
            "temporal": True,
        },
        {
            "point_id": "point_12c_triple_shard",
            "purpose": "Intermediate replicated shard stress point before full single-chip pressure.",
            "shards": 3,
            "event_count": 384,
            "lifecycle": 0,
            "temporal": True,
        },
        {
            "point_id": "point_16c_quad_shard",
            "purpose": "Conservative full single-chip application-core pressure point.",
            "shards": 4,
            "event_count": 512,
            "lifecycle": 0,
            "temporal": True,
        },
    ]

    rows: list[ScalePoint] = []
    for plan in plans:
        shards = int(plan["shards"])
        event_count = int(plan["event_count"])
        lifecycle_cores = int(plan["lifecycle"])
        context_cores = shards
        route_cores = shards
        memory_cores = shards
        learning_cores = shards
        total_cores = context_cores + route_cores + memory_cores + learning_cores + lifecycle_cores
        schedule_per_learning = math.ceil(event_count / learning_cores)
        context_slots = math.ceil(event_count / context_cores)
        route_slots = min(limits["max_route_slots"], 4)
        memory_slots = min(limits["max_memory_slots"], 4)
        lifecycle_slots = limits["max_lifecycle_slots"] if lifecycle_cores else 0
        pending = min(10 * shards, limits["max_lookup_replies"])
        lookup_requests = event_count * LOOKUP_TYPES_PER_EVENT
        lookup_replies = lookup_requests
        mcpl_messages = lookup_requests * MCPL_MESSAGES_PER_LOOKUP
        mcpl_bytes = lookup_requests * MCPL_BYTES_PER_LOOKUP_ROUND_TRIP
        sdp_bytes = lookup_requests * SDP_BYTES_PER_LOOKUP_ROUND_TRIP
        readback = (
            total_cores * STANDARD_PAYLOAD_BYTES
            + lifecycle_cores * LIFECYCLE_PAYLOAD_BYTES
            + (TEMPORAL_PAYLOAD_BYTES if plan["temporal"] else 0)
        )

        projected_failure = "none_projected_preflight"
        if total_cores > CONSERVATIVE_APP_CORES_PER_CHIP:
            projected_failure = "core_budget_exceeded"
        elif schedule_per_learning > limits["max_schedule_entries"]:
            projected_failure = "schedule_length_overflow"
        elif context_slots > limits["max_context_slots"]:
            projected_failure = "context_slot_overflow"
        elif pending > limits["max_lookup_replies"]:
            projected_failure = "lookup_reply_window_overflow"

        rows.append(
            ScalePoint(
                point_id=str(plan["point_id"]),
                purpose=str(plan["purpose"]),
                status="eligible_for_hardware_stress" if projected_failure == "none_projected_preflight" else "blocked",
                total_cores=total_cores,
                shards=shards,
                context_cores=context_cores,
                route_cores=route_cores,
                memory_cores=memory_cores,
                learning_cores=learning_cores,
                lifecycle_cores=lifecycle_cores,
                temporal_state_enabled=bool(plan["temporal"]),
                event_count=event_count,
                schedule_entries_per_learning_core=schedule_per_learning,
                context_slots_per_context_core=context_slots,
                route_slots_per_route_core=route_slots,
                memory_slots_per_memory_core=memory_slots,
                lifecycle_slots_per_lifecycle_core=lifecycle_slots,
                max_pending_horizons=pending,
                lookup_replies_in_flight=pending,
                lookup_requests_total=lookup_requests,
                lookup_replies_total=lookup_replies,
                mcpl_messages_total=mcpl_messages,
                mcpl_payload_bytes_total=mcpl_bytes,
                sdp_payload_bytes_if_fallback_total=sdp_bytes,
                compact_readback_bytes_per_snapshot=readback,
                projected_failure_class=projected_failure,
                claim_boundary="preflight projection only; must be measured on EBRAINS before scaling claims",
            )
        )
    return rows


def profile_allocations(points: list[ScalePoint], profiles: dict[str, dict[str, Any]]) -> list[ProfileAllocation]:
    rows: list[ProfileAllocation] = []
    profile_names = ["context_core", "route_core", "memory_core", "learning_core", "lifecycle_core"]
    for point in points:
        copies = {
            "context_core": point.context_cores,
            "route_core": point.route_cores,
            "memory_core": point.memory_cores,
            "learning_core": point.learning_cores,
            "lifecycle_core": point.lifecycle_cores,
        }
        for profile in profile_names:
            if copies[profile] == 0:
                continue
            budget = profiles[profile]
            ok = budget["itcm_headroom_bytes"] > 0 and budget["dtcm_headroom_bytes"] > 0
            rows.append(
                ProfileAllocation(
                    point_id=point.point_id,
                    profile=profile,
                    copies=int(copies[profile]),
                    text_bytes_per_core=int(budget["text_bytes"]),
                    dtcm_estimate_bytes_per_core=int(budget["dtcm_estimate_bytes"]),
                    itcm_headroom_bytes_per_core=int(budget["itcm_headroom_bytes"]),
                    dtcm_headroom_bytes_per_core=int(budget["dtcm_headroom_bytes"]),
                    allocation_status="profile_headroom_positive" if ok else "profile_headroom_blocked",
                    note="Replicated profiles keep per-core ITCM/DTCM headroom; aggregate chip pressure must be measured in hardware.",
                )
            )
    return rows


def failure_classes() -> list[FailureClass]:
    return [
        FailureClass(
            "schedule_length_overflow",
            "bounded_by_preflight",
            "schedule_entries_per_learning_core <= MAX_SCHEDULE_ENTRIES",
            "hardware run must return accepted schedule count and reject overflow cleanly",
            "Tier 4.32a-hw",
        ),
        FailureClass(
            "context_slot_exhaustion",
            "bounded_by_preflight",
            "context_slots_per_context_core <= MAX_CONTEXT_SLOTS",
            "hardware run must report context slot high-water mark",
            "Tier 4.32a-hw",
        ),
        FailureClass(
            "route_memory_slot_exhaustion",
            "bounded_by_preflight",
            "route/memory slots per core <= source limits",
            "hardware run must report route/memory slot high-water marks",
            "Tier 4.32a-hw",
        ),
        FailureClass(
            "pending_horizon_or_lookup_reply_overflow",
            "bounded_by_preflight",
            "max pending and in-flight replies <= min(MAX_PENDING_HORIZONS, MAX_LOOKUP_REPLIES)",
            "hardware run must report pending high-water mark, lookup replies, and overflow counters",
            "Tier 4.32a-hw",
        ),
        FailureClass(
            "mcpl_delivery_integrity_failure",
            "not_measured_by_preflight",
            "preflight can only declare MCPL-first message counts",
            "hardware run must return request/reply parity, stale, duplicate, timeout, and drop counters",
            "Tier 4.32a-hw",
        ),
        FailureClass(
            "compact_readback_growth",
            "projected_by_preflight",
            "compact_readback_bytes_per_snapshot is projected for each point",
            "hardware run must return per-core payload lengths and cumulative readback bytes",
            "Tier 4.32a-hw",
        ),
        FailureClass(
            "profile_itcm_dtcm_exhaustion",
            "bounded_by_returned_profile_sizes",
            "all replicated profile copies use profiles with positive per-core headroom",
            "any new profile build must return size/headroom before promotion",
            "Tier 4.32a-hw",
        ),
        FailureClass(
            "multi_chip_routing_failure",
            "out_of_scope",
            "single-chip only",
            "must be handled by a separate inter-chip contract before first multi-chip smoke",
            "Tier 4.32c",
        ),
    ]


def next_gates() -> list[NextGate]:
    return [
        NextGate(
            gate="Tier 4.32a-hw",
            decision="authorize if this preflight passes",
            question="Do the predeclared 4/5/8/12/16-core single-chip stress points execute with MCPL-first integrity and compact readback?",
            prerequisites="Use the 4.32a preflight scale-point table; no SDP core-to-core fallback unless documented as a control.",
            pass_boundary="zero stale/duplicate/timeout/drop counters, lookup request/reply parity, compact readback returned, profile builds returned, and no schedule/slot overflow.",
            fail_boundary="localize to schedule, slot, MCPL delivery, readback, profile, or EBRAINS environment class before adding more mechanics.",
            claim_boundary="single-chip hardware stress only; not multi-chip, not speedup, not baseline freeze.",
        ),
        NextGate(
            gate="Tier 4.32b",
            decision="blocked until 4.32a-hw passes",
            question="Can static reef partitioning map groups/modules/polyps to the measured single-chip runtime envelope?",
            prerequisites="4.32a-hw pass with measured resource envelope.",
            pass_boundary="static partition smoke preserves ownership, compact readback, and measured failure counters.",
            fail_boundary="publish measured single-chip runtime boundary; do not proceed to multi-chip.",
            claim_boundary="static partition smoke only; not one-polyp-per-chip and not organism-scale proof.",
        ),
        NextGate(
            gate="CRA_NATIVE_SCALE_BASELINE_v0.5",
            decision="not authorized",
            question="Is native scaling stable enough to freeze as a paper baseline?",
            prerequisites="4.32a-hw, 4.32b, first inter-chip feasibility, and first multi-chip smoke must pass.",
            pass_boundary="freeze only after single-chip and first multi-chip evidence are clean.",
            fail_boundary="keep v0.4 as latest native baseline and publish limits honestly.",
            claim_boundary="not considered by this preflight.",
        ),
    ]


def build_results() -> dict[str, Any]:
    tier4_32 = read_json(TIER4_32)
    limits = {key: int(value) for key, value in tier4_32["runtime_limits"].items()}
    profiles = profile_map(tier4_32)
    points = scale_points(limits)
    allocations = profile_allocations(points, profiles)
    failures = failure_classes()
    gates = next_gates()

    all_points_eligible = all(point.status == "eligible_for_hardware_stress" for point in points)
    all_points_single_chip = all(point.total_cores <= CONSERVATIVE_APP_CORES_PER_CHIP for point in points)
    max_schedule = max(point.schedule_entries_per_learning_core for point in points)
    max_context_slots = max(point.context_slots_per_context_core for point in points)
    max_pending = max(point.max_pending_horizons for point in points)
    mcpl_smaller_all = all(point.mcpl_payload_bytes_total < point.sdp_payload_bytes_if_fallback_total for point in points)
    profile_ok = all(row.allocation_status == "profile_headroom_positive" for row in allocations)
    point_ids = [point.point_id for point in points]

    criteria = [
        criterion("Tier 4.32 prerequisite passed", tier4_32["status"], "== pass", tier4_32["status"] == "pass"),
        criterion("Tier 4.32 authorized 4.32a", tier4_32["final_decision"].get("tier4_32a"), "== authorized_next", tier4_32["final_decision"].get("tier4_32a") == "authorized_next"),
        criterion("no native scale baseline freeze inherited", tier4_32["final_decision"].get("native_scale_baseline_freeze"), "== not_authorized", tier4_32["final_decision"].get("native_scale_baseline_freeze") == "not_authorized"),
        criterion("MCPL-first policy inherited", tier4_32["final_decision"].get("mcpl_policy"), "contains mcpl_first", "mcpl_first" in tier4_32["final_decision"].get("mcpl_policy", "")),
        criterion("five ordered scale points declared", point_ids, "== 4/5/8/12/16 core points", point_ids == ["point_04c_reference", "point_05c_lifecycle", "point_08c_dual_shard", "point_12c_triple_shard", "point_16c_quad_shard"]),
        criterion("scale points remain within conservative single-chip app-core budget", max(point.total_cores for point in points), f"<= {CONSERVATIVE_APP_CORES_PER_CHIP}", all_points_single_chip),
        criterion("scale points are eligible for hardware stress", [point.status for point in points], "all eligible", all_points_eligible),
        criterion("schedule pressure within current source limit", max_schedule, f"<= {limits['max_schedule_entries']}", max_schedule <= limits["max_schedule_entries"]),
        criterion("context slot pressure within current source limit", max_context_slots, f"<= {limits['max_context_slots']}", max_context_slots <= limits["max_context_slots"]),
        criterion("route slot pressure within current source limit", max(point.route_slots_per_route_core for point in points), f"<= {limits['max_route_slots']}", max(point.route_slots_per_route_core for point in points) <= limits["max_route_slots"]),
        criterion("memory slot pressure within current source limit", max(point.memory_slots_per_memory_core for point in points), f"<= {limits['max_memory_slots']}", max(point.memory_slots_per_memory_core for point in points) <= limits["max_memory_slots"]),
        criterion("lifecycle slot pressure within current source limit", max(point.lifecycle_slots_per_lifecycle_core for point in points), f"<= {limits['max_lifecycle_slots']}", max(point.lifecycle_slots_per_lifecycle_core for point in points) <= limits["max_lifecycle_slots"]),
        criterion("pending/reply pressure within lookup reply window", max_pending, f"<= {limits['max_lookup_replies']}", max_pending <= limits["max_lookup_replies"]),
        criterion("MCPL projected bytes cheaper than SDP fallback for every point", [round(point.mcpl_payload_bytes_total / point.sdp_payload_bytes_if_fallback_total, 6) for point in points], "< 1.0 each", mcpl_smaller_all),
        criterion("profile allocation headroom positive", len(allocations), "all profile allocations positive", profile_ok),
        criterion("failure classes cover hardware-only measurements", [row.failure_class for row in failures], ">= 8 classes", len(failures) >= 8 and any(row.preflight_status == "not_measured_by_preflight" for row in failures)),
        criterion("next gate is hardware stress, not 4.32b jump", gates[0].gate, "== Tier 4.32a-hw", gates[0].gate == "Tier 4.32a-hw"),
        criterion("baseline freeze remains blocked", gates[-1].decision, "== not authorized", gates[-1].decision == "not authorized"),
    ]
    failed = [item for item in criteria if not item.passed]
    status = "pass" if not failed else "fail"

    final_decision = {
        "status": status,
        "tier4_32a_hw": "authorized_next" if status == "pass" else "blocked_until_4_32a_preflight_repairs",
        "tier4_32b": "blocked_until_4_32a_hw_passes",
        "tier4_32c": "blocked_until_4_32b_passes",
        "tier4_32d": "blocked_until_4_32c_passes",
        "tier4_32e": "blocked_until_4_32d_passes",
        "native_scale_baseline_freeze": "not_authorized",
        "claim_boundary": "local single-chip scale-stress preflight only",
    }

    return {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "status": status,
        "criteria_passed": len(criteria) - len(failed),
        "criteria_total": len(criteria),
        "criteria": criteria,
        "failed_criteria": failed,
        "tier4_32_source": rel(TIER4_32),
        "runtime_limits": limits,
        "scale_points": points,
        "profile_allocations": allocations,
        "failure_classes": failures,
        "next_gate_plan": gates,
        "final_decision": final_decision,
        "recommended_next_step": (
            "Prepare and run Tier 4.32a-hw EBRAINS single-chip MCPL-first scale stress."
            if status == "pass"
            else "Repair failed Tier 4.32a preflight criteria before hardware stress."
        ),
        "claim_boundary": (
            "Tier 4.32a is a local scale-stress preflight over the Tier 4.32 resource model. "
            "It is not a SpiNNaker hardware run, not a speedup claim, not a multi-chip claim, "
            "not a static reef partition proof, not benchmark/superiority evidence, and not a "
            "native-scale baseline freeze."
        ),
    }


def write_report(path: Path, results: dict[str, Any]) -> None:
    lines = [
        "# Tier 4.32a Single-Chip Multi-Core Scale-Stress Preflight",
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
            "## Scale Points",
            "",
            "| Point | Status | Cores | Shards | Events | Schedule/Core | Context Slots/Core | Pending | MCPL Bytes | SDP Bytes If Fallback | Readback/Snapshot | Failure Class |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for row in results["scale_points"]:
        lines.append(
            f"| `{row['point_id']}` | `{row['status']}` | {row['total_cores']} | {row['shards']} | "
            f"{row['event_count']} | {row['schedule_entries_per_learning_core']} | "
            f"{row['context_slots_per_context_core']} | {row['max_pending_horizons']} | "
            f"{row['mcpl_payload_bytes_total']} | {row['sdp_payload_bytes_if_fallback_total']} | "
            f"{row['compact_readback_bytes_per_snapshot']} | `{row['projected_failure_class']}` |"
        )

    lines.extend(
        [
            "",
            "## Profile Allocation",
            "",
            "| Point | Profile | Copies | Text/Core | DTCM/Core | ITCM Headroom/Core | DTCM Headroom/Core | Status |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for row in results["profile_allocations"]:
        lines.append(
            f"| `{row['point_id']}` | `{row['profile']}` | {row['copies']} | {row['text_bytes_per_core']} | "
            f"{row['dtcm_estimate_bytes_per_core']} | {row['itcm_headroom_bytes_per_core']} | "
            f"{row['dtcm_headroom_bytes_per_core']} | `{row['allocation_status']}` |"
        )

    lines.extend(["", "## Failure Classes", "", "| Failure Class | Preflight Status | Detection Rule | Hardware Measurement Required | Next Gate |", "| --- | --- | --- | --- | --- |"])
    for row in results["failure_classes"]:
        lines.append(
            f"| `{row['failure_class']}` | `{row['preflight_status']}` | {row['detection_rule']} | {row['hardware_measurement_required']} | `{row['next_gate']}` |"
        )

    lines.extend(["", "## Next Gate Plan", "", "| Gate | Decision | Question | Prerequisites | Pass Boundary | Fail Boundary | Claim Boundary |", "| --- | --- | --- | --- | --- | --- | --- |"])
    for row in results["next_gate_plan"]:
        lines.append(
            f"| `{row['gate']}` | `{row['decision']}` | {row['question']} | {row['prerequisites']} | {row['pass_boundary']} | {row['fail_boundary']} | {row['claim_boundary']} |"
        )

    lines.extend(["", "## Criteria", "", "| Criterion | Value | Rule | Pass | Note |", "| --- | --- | --- | --- | --- |"])
    for item in results["criteria"]:
        lines.append(f"| {item['name']} | `{item['value']}` | `{item['rule']}` | {'yes' if item['passed'] else 'no'} | {item.get('note', '')} |")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    results = build_results()
    results["output_dir"] = str(output_dir)
    safe = json_safe(results)

    write_json(output_dir / "tier4_32a_results.json", safe)
    write_report(output_dir / "tier4_32a_report.md", safe)
    write_csv(output_dir / "tier4_32a_scale_points.csv", safe["scale_points"])
    write_csv(output_dir / "tier4_32a_profile_allocation.csv", safe["profile_allocations"])
    write_csv(output_dir / "tier4_32a_failure_classes.csv", safe["failure_classes"])
    write_csv(output_dir / "tier4_32a_next_gate_plan.csv", safe["next_gate_plan"])
    write_csv(output_dir / "tier4_32a_criteria.csv", safe["criteria"])
    write_json(
        LATEST_MANIFEST,
        {
            "tier": TIER,
            "runner_revision": RUNNER_REVISION,
            "generated_at_utc": results["generated_at_utc"],
            "status": results["status"],
            "manifest": str(output_dir / "tier4_32a_results.json"),
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
                "output_dir": str(args.output_dir),
                "recommended_next_step": results["recommended_next_step"],
            },
            indent=2,
        )
    )
    return 0 if results["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
