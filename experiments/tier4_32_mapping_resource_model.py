#!/usr/bin/env python3
"""Tier 4.32 native-runtime mapping/resource model.

This tier is an engineering decision gate over already-measured evidence from
Tiers 4.27-4.31. It does not run SpiNNaker hardware and it does not create a new
science claim. Its job is to make the next scaling decision auditable before we
stress more chips/cores:

* what the measured single-chip native envelope is,
* what resource headroom is visible from returned build profiles,
* what message/readback pressure has actually been observed,
* which failure classes are still unmeasured, and
* which next gate is authorized.
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

TIER = "Tier 4.32 - Native Runtime Mapping/Resource Model"
RUNNER_REVISION = "tier4_32_mapping_resource_model_20260506_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier4_32_20260506_mapping_resource_model"
LATEST_MANIFEST = CONTROLLED / "tier4_32_latest_manifest.json"

TIER4_27G = CONTROLLED / "tier4_27g_20260502_local_pass" / "tier4_27g_results.json"
TIER4_28E_POINT_C = (
    CONTROLLED / "tier4_28e_pointC_20260503_hardware_pass_ingested" / "tier4_28e_hardware_results.json"
)
TIER4_29F = CONTROLLED / "tier4_29f_20260505_native_mechanism_regression" / "tier4_29f_results.json"
TIER4_30G_HW = CONTROLLED / "tier4_30g_hw_20260505_hardware_pass_ingested" / "tier4_30g_hw_results.json"
TIER4_30G_TASK = (
    CONTROLLED / "tier4_30g_hw_20260505_hardware_pass_ingested" / "returned_artifacts" / "tier4_30g_hw_task_result.json"
)
TIER4_30G_RESOURCE_CSV = (
    CONTROLLED
    / "tier4_30g_hw_20260505_hardware_pass_ingested"
    / "returned_artifacts"
    / "tier4_30g_hw_resource_accounting.csv"
)
TIER4_31D_REMOTE = (
    CONTROLLED
    / "tier4_31d_hw_20260506_hardware_pass_ingested"
    / "returned_artifacts"
    / "tier4_31d_hw_results.json"
)
TIER4_31E = CONTROLLED / "tier4_31e_20260506_native_replay_eligibility_decision_closeout" / "tier4_31e_results.json"

BUILD_DIR = CONTROLLED / "tier4_30g_hw_20260505_hardware_pass_ingested" / "returned_artifacts"
BUILD_FILES = {
    "context_core": BUILD_DIR / "tier4_30g_hw_context_build.json",
    "route_core": BUILD_DIR / "tier4_30g_hw_route_build.json",
    "memory_core": BUILD_DIR / "tier4_30g_hw_memory_build.json",
    "learning_core": BUILD_DIR / "tier4_30g_hw_learning_build.json",
    "lifecycle_core": BUILD_DIR / "tier4_30g_hw_lifecycle_build.json",
}

ITCM_BUDGET_BYTES = 32 * 1024
DTCM_BUDGET_BYTES = 64 * 1024


@dataclass(frozen=True)
class Criterion:
    name: str
    value: Any
    rule: str
    passed: bool
    note: str = ""


@dataclass(frozen=True)
class EvidenceInput:
    source_id: str
    path: str
    status: str
    role: str
    extracted_signal: str


@dataclass(frozen=True)
class ProfileBudget:
    profile: str
    source_artifact: str
    status: str
    text_bytes: int
    data_bytes: int
    bss_bytes: int
    dec_bytes: int
    itcm_budget_bytes: int
    dtcm_budget_bytes: int
    itcm_headroom_bytes: int
    dtcm_estimate_bytes: int
    dtcm_headroom_bytes: int
    itcm_headroom_fraction: float
    dtcm_headroom_fraction: float


@dataclass(frozen=True)
class EnvelopeRow:
    category: str
    metric: str
    value: Any
    unit: str
    evidence_source: str
    interpretation: str


@dataclass(frozen=True)
class NextGateRow:
    gate: str
    decision: str
    question: str
    prerequisites: str
    pass_boundary: str
    fail_boundary: str
    claim_boundary: str


@dataclass(frozen=True)
class FailureClassRow:
    failure_class: str
    status: str
    evidence: str
    next_detection_gate: str


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "__dataclass_fields__"):
        return json_safe(asdict(value))
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    return value


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


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


def status_of(payload: dict[str, Any]) -> str:
    return str(payload.get("status") or payload.get("registry_status") or payload.get("baseline_status") or "unknown").lower()


def criterion(name: str, value: Any, rule: str, passed: bool, note: str = "") -> Criterion:
    return Criterion(name=name, value=value, rule=rule, passed=bool(passed), note=note)


def parse_define_int(path: Path, name: str) -> int:
    pattern = re.compile(rf"^\s*#define\s+{re.escape(name)}\s+([0-9]+)\b")
    for line in path.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if match:
            return int(match.group(1))
    raise ValueError(f"missing #define {name} in {path}")


def parse_size_stdout(text: str) -> dict[str, int]:
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 6 and all(part.lstrip("-").isdigit() for part in parts[:4]):
            return {
                "text": int(parts[0]),
                "data": int(parts[1]),
                "bss": int(parts[2]),
                "dec": int(parts[3]),
            }
    raise ValueError(f"could not parse size output: {text!r}")


def int_field(row: dict[str, Any], key: str) -> int:
    return int(float(row[key]))


def float_field(row: dict[str, Any], key: str) -> float:
    return float(row[key])


def profile_budget_rows() -> list[ProfileBudget]:
    rows: list[ProfileBudget] = []
    for profile, path in BUILD_FILES.items():
        data = read_json(path)
        size = parse_size_stdout(str(data.get("size_stdout", "")))
        dtcm_estimate = size["data"] + size["bss"]
        rows.append(
            ProfileBudget(
                profile=profile,
                source_artifact=rel(path),
                status=status_of(data),
                text_bytes=size["text"],
                data_bytes=size["data"],
                bss_bytes=size["bss"],
                dec_bytes=size["dec"],
                itcm_budget_bytes=ITCM_BUDGET_BYTES,
                dtcm_budget_bytes=DTCM_BUDGET_BYTES,
                itcm_headroom_bytes=ITCM_BUDGET_BYTES - size["text"],
                dtcm_estimate_bytes=dtcm_estimate,
                dtcm_headroom_bytes=DTCM_BUDGET_BYTES - dtcm_estimate,
                itcm_headroom_fraction=(ITCM_BUDGET_BYTES - size["text"]) / ITCM_BUDGET_BYTES,
                dtcm_headroom_fraction=(DTCM_BUDGET_BYTES - dtcm_estimate) / DTCM_BUDGET_BYTES,
            )
        )
    return rows


def runtime_limits() -> dict[str, int]:
    config_h = RUNTIME_SRC / "config.h"
    state_manager_h = RUNTIME_SRC / "state_manager.h"
    return {
        "max_context_slots": parse_define_int(config_h, "MAX_CONTEXT_SLOTS"),
        "max_route_slots": parse_define_int(config_h, "MAX_ROUTE_SLOTS"),
        "max_memory_slots": parse_define_int(config_h, "MAX_MEMORY_SLOTS"),
        "max_pending_horizons": parse_define_int(config_h, "MAX_PENDING_HORIZONS"),
        "max_lifecycle_slots": parse_define_int(config_h, "MAX_LIFECYCLE_SLOTS"),
        "max_schedule_entries": parse_define_int(config_h, "MAX_SCHEDULE_ENTRIES"),
        "max_lookup_replies": parse_define_int(state_manager_h, "MAX_LOOKUP_REPLIES"),
    }


def evidence_inputs(
    tier4_27g: dict[str, Any],
    tier4_28e: dict[str, Any],
    tier4_29f: dict[str, Any],
    tier4_30g_hw: dict[str, Any],
    tier4_30g_task: dict[str, Any],
    tier4_31d: dict[str, Any],
    tier4_31e: dict[str, Any],
) -> list[EvidenceInput]:
    return [
        EvidenceInput(
            "tier4_27g_mcpl_vs_sdp_model",
            rel(TIER4_27G),
            status_of(tier4_27g),
            "protocol byte/latency model",
            (
                f"SDP round trip {tier4_27g['sdp_payloads']['round_trip_bytes']} bytes; "
                f"MCPL round trip {tier4_27g['mcpl_payloads']['round_trip_bytes']} bytes; "
                f"48-event MCPL total {tier4_27g['message_counts']['mcpl_total_bytes_48event']} bytes"
            ),
        ),
        EvidenceInput(
            "tier4_28e_pointC_four_core_pressure",
            rel(TIER4_28E_POINT_C),
            status_of(tier4_28e),
            "measured four-core event/slot/lookup pressure",
            (
                f"{tier4_28e['pressure']['event_count']} events; "
                f"context slots {tier4_28e['pressure']['context_slots_used']}; "
                f"max pending {tier4_28e['pressure']['max_concurrent_pending']}; "
                f"learning lookups {tier4_28e['task']['final_state']['learning']['lookup_requests']}"
            ),
        ),
        EvidenceInput(
            "tier4_29f_native_mechanism_regression",
            rel(TIER4_29F),
            status_of(tier4_29f),
            "canonical mechanism-regression prerequisite",
            f"{tier4_29f.get('criteria_passed')}/{tier4_29f.get('criteria_total')} criteria complete",
        ),
        EvidenceInput(
            "tier4_30g_lifecycle_hardware_bridge",
            rel(TIER4_30G_HW),
            status_of(tier4_30g_hw),
            "measured five-core lifecycle bridge",
            (
                f"task status {tier4_30g_hw.get('summary', {}).get('task_status')}; "
                f"profiles {','.join(sorted(tier4_30g_task.get('core_roles', {})))}; "
                f"runtime {tier4_30g_task.get('runtime_seconds'):.6g}s"
            ),
        ),
        EvidenceInput(
            "tier4_31d_native_temporal_hardware_smoke",
            rel(TIER4_31D_REMOTE),
            status_of(tier4_31d),
            "measured temporal compact readback smoke",
            (
                f"payload {tier4_31d.get('summary', {}).get('temporal_payload_len')} bytes; "
                f"board {tier4_31d.get('summary', {}).get('hostname')}; "
                f"scenarios {tier4_31d.get('summary', {}).get('scenario_statuses')}"
            ),
        ),
        EvidenceInput(
            "tier4_31e_decision_closeout",
            rel(TIER4_31E),
            status_of(tier4_31e),
            "replay/eligibility closeout prerequisite",
            f"4.32 decision = {tier4_31e.get('final_decision', {}).get('tier4_32')}",
        ),
    ]


def envelope_rows(
    tier4_27g: dict[str, Any],
    tier4_28e: dict[str, Any],
    tier4_30g_task: dict[str, Any],
    tier4_31d: dict[str, Any],
    limits: dict[str, int],
    budgets: list[ProfileBudget],
) -> list[EnvelopeRow]:
    task_28 = tier4_28e["task"]
    learning_28 = task_28["final_state"]["learning"]
    context_28 = task_28["final_state"]["context"]
    resource_rows = read_csv(TIER4_30G_RESOURCE_CSV)
    enabled_row = next(row for row in resource_rows if row["mode"] == "enabled")
    five_core_roles = tier4_30g_task.get("core_roles", {})
    final_reads = tier4_30g_task.get("final_profile_reads", {})
    max_text = max(row.text_bytes for row in budgets)
    max_dtcm = max(row.dtcm_estimate_bytes for row in budgets)

    rows = [
        EnvelopeRow("protocol", "sdp_round_trip_bytes", tier4_27g["sdp_payloads"]["round_trip_bytes"], "bytes", "tier4_27g", "Transitional SDP lookup round trip byte cost."),
        EnvelopeRow("protocol", "mcpl_round_trip_bytes", tier4_27g["mcpl_payloads"]["round_trip_bytes"], "bytes", "tier4_27g", "Target MCPL lookup round trip byte cost."),
        EnvelopeRow("protocol", "mcpl_byte_reduction_ratio_vs_sdp", round(tier4_27g["mcpl_payloads"]["round_trip_bytes"] / tier4_27g["sdp_payloads"]["round_trip_bytes"], 6), "ratio", "tier4_27g", "MCPL is the scale path; SDP is a transitional/fallback control channel."),
        EnvelopeRow("protocol", "lookup_messages_per_event", tier4_27g["message_counts"]["inter_core_messages_per_event"], "messages/event", "tier4_27g", "Three lookup types times request/reply."),
        EnvelopeRow("protocol", "sdp_total_bytes_48event", tier4_27g["message_counts"]["sdp_total_bytes_48event"], "bytes", "tier4_27g", "Modeled SDP pressure for a 48-event reference."),
        EnvelopeRow("protocol", "mcpl_total_bytes_48event", tier4_27g["message_counts"]["mcpl_total_bytes_48event"], "bytes", "tier4_27g", "Modeled MCPL pressure for a 48-event reference."),
        EnvelopeRow("protocol", "mcpl_router_entries_required", tier4_27g["router_entries"]["mcpl_entries_required"], "router entries", "tier4_27g", "Minimum intra-chip routing entries for context/route/memory request and learning reply paths."),
        EnvelopeRow("four_core_pressure", "tier4_28e_event_count", tier4_28e["pressure"]["event_count"], "events", "tier4_28e_pointC", "Measured four-core pressure event count."),
        EnvelopeRow("four_core_pressure", "tier4_28e_schedule_uploads", len(task_28["schedule_uploads"]), "uploads", "tier4_28e_pointC", "One schedule upload per compact event in this run."),
        EnvelopeRow("four_core_pressure", "tier4_28e_context_slots_used", tier4_28e["pressure"]["context_slots_used"], "slots", "tier4_28e_pointC", "Measured context-slot pressure."),
        EnvelopeRow("four_core_pressure", "tier4_28e_max_pending", tier4_28e["pressure"]["max_concurrent_pending"], "pending horizons", "tier4_28e_pointC", "Measured delayed-credit pending pressure."),
        EnvelopeRow("four_core_pressure", "tier4_28e_lookup_requests", learning_28["lookup_requests"], "requests", "tier4_28e_pointC", "Learning-core lookup requests."),
        EnvelopeRow("four_core_pressure", "tier4_28e_lookup_replies", learning_28["lookup_replies"], "replies", "tier4_28e_pointC", "Learning-core lookup replies."),
        EnvelopeRow("four_core_pressure", "tier4_28e_stale_duplicate_timeout_total", learning_28["stale_replies"] + learning_28["duplicate_replies"] + learning_28["timeouts"], "events", "tier4_28e_pointC", "No stale, duplicate, or timeout events were observed."),
        EnvelopeRow("readback", "standard_payload_len", learning_28["payload_len"], "bytes", "tier4_28e_pointC", "Standard compact state payload in the four-core run."),
        EnvelopeRow("readback", "tier4_28e_learning_readback_bytes", learning_28["readback_bytes"], "bytes", "tier4_28e_pointC", "Measured cumulative learning readback bytes."),
        EnvelopeRow("readback", "tier4_28e_context_readback_bytes", context_28["readback_bytes"], "bytes", "tier4_28e_pointC", "Measured context readback bytes."),
        EnvelopeRow("five_core_lifecycle", "active_profiles", len(five_core_roles), "profiles", "tier4_30g_hw", "Measured five-profile single-chip task bridge."),
        EnvelopeRow("five_core_lifecycle", "enabled_task_schedule_uploads", int_field(enabled_row, "task_schedule_uploads"), "uploads", "tier4_30g_hw", "Lifecycle enabled task schedule length."),
        EnvelopeRow("five_core_lifecycle", "enabled_learning_lookup_requests", int_field(enabled_row, "learning_lookup_requests"), "requests", "tier4_30g_hw", "Lifecycle enabled task lookup pressure."),
        EnvelopeRow("five_core_lifecycle", "enabled_learning_readback_bytes", int_field(enabled_row, "learning_readback_bytes"), "bytes", "tier4_30g_hw", "Lifecycle enabled task learning readback bytes."),
        EnvelopeRow("five_core_lifecycle", "lifecycle_payload_len", int_field(enabled_row, "lifecycle_payload_len"), "bytes", "tier4_30g_hw", "Lifecycle compact payload length."),
        EnvelopeRow("five_core_lifecycle", "lifecycle_readback_bytes", int_field(enabled_row, "lifecycle_readback_bytes"), "bytes", "tier4_30g_hw", "Lifecycle cumulative readback bytes per mode."),
        EnvelopeRow("five_core_lifecycle", "enabled_task_runtime_seconds", float_field(enabled_row, "task_runtime_seconds"), "seconds", "tier4_30g_hw", "Measured lifecycle enabled task roundtrip time."),
        EnvelopeRow("temporal", "temporal_payload_len", tier4_31d["summary"]["temporal_payload_len"], "bytes", "tier4_31d_hw", "Measured native temporal compact payload length."),
        EnvelopeRow("limits", "max_context_slots", limits["max_context_slots"], "slots", "config.h", "Compiled context-slot capacity."),
        EnvelopeRow("limits", "max_route_slots", limits["max_route_slots"], "slots", "config.h", "Compiled route-slot capacity."),
        EnvelopeRow("limits", "max_memory_slots", limits["max_memory_slots"], "slots", "config.h", "Compiled memory-slot capacity."),
        EnvelopeRow("limits", "max_pending_horizons", limits["max_pending_horizons"], "pending horizons", "config.h", "Compiled delayed-credit capacity."),
        EnvelopeRow("limits", "max_lifecycle_slots", limits["max_lifecycle_slots"], "slots", "config.h", "Compiled lifecycle static-pool capacity."),
        EnvelopeRow("limits", "max_schedule_entries", limits["max_schedule_entries"], "schedule entries", "config.h", "Compiled host-supplied schedule capacity."),
        EnvelopeRow("limits", "max_lookup_replies", limits["max_lookup_replies"], "entries", "state_manager.h", "Compiled lookup reply table capacity."),
        EnvelopeRow("profile_budget", "max_profile_text_bytes", max_text, "bytes", "tier4_30g_build_profiles", "Largest measured profile text section."),
        EnvelopeRow("profile_budget", "max_profile_dtcm_estimate_bytes", max_dtcm, "bytes", "tier4_30g_build_profiles", "Largest measured data+bss estimate."),
        EnvelopeRow("profile_budget", "min_itcm_headroom_bytes", min(row.itcm_headroom_bytes for row in budgets), "bytes", "tier4_30g_build_profiles", "Smallest measured ITCM headroom among returned profile builds."),
        EnvelopeRow("profile_budget", "min_dtcm_headroom_bytes", min(row.dtcm_headroom_bytes for row in budgets), "bytes", "tier4_30g_build_profiles", "Smallest measured DTCM estimate headroom among returned profile builds."),
    ]
    for role, read in sorted(final_reads.items()):
        rows.append(
            EnvelopeRow(
                "five_core_final_reads",
                f"{role}_readback_bytes",
                read.get("readback_bytes"),
                "bytes",
                "tier4_30g_hw",
                f"Final compact readback accounting for {role}.",
            )
        )
    return rows


def failure_classes() -> list[FailureClassRow]:
    return [
        FailureClassRow(
            "ITCM overflow",
            "measured historically, not active in 4.30g profiles",
            "4.22w had an unprofiled overflow; 4.30g returned five profiled builds with positive ITCM headroom.",
            "Tier 4.32a profile-size sweep and any new runtime-profile build.",
        ),
        FailureClassRow(
            "DTCM/state-slot exhaustion",
            "not yet stressed to limit",
            "4.28e used 43/128 context slots and 10/128 pending horizons; 4.30g used 1 active lifecycle bridge slot, not lifecycle-pool stress.",
            "Tier 4.32a single-chip scale stress with slot/schedule sweeps.",
        ),
        FailureClassRow(
            "lookup stale/duplicate/timeout",
            "zero observed in measured gates",
            "4.28e and 4.30g returned zero stale replies and zero timeouts under current pressure.",
            "Tier 4.32a and 4.32c must preserve stale/duplicate/timeout counters.",
        ),
        FailureClassRow(
            "SDP overhead bottleneck",
            "architecturally deprecated",
            "4.27g model shows MCPL round-trip bytes are 16 vs SDP 54 and avoids monitor involvement.",
            "Tier 4.32a should stay MCPL-first; SDP remains only fallback/control.",
        ),
        FailureClassRow(
            "readback/provenance blowup",
            "partially measured",
            "4.28e standard readback reached 5460 learning bytes; 4.30g lifecycle readback reached 2380 bytes per mode; temporal compact payload is 48 bytes.",
            "Tier 4.32a compact-readback cadence sweep.",
        ),
        FailureClassRow(
            "multi-chip routing/latency",
            "unmeasured",
            "All current 4.27-4.31 evidence is single-chip/same-board scoped.",
            "Tier 4.32c contract then Tier 4.32d first multi-chip smoke.",
        ),
        FailureClassRow(
            "static reef partition correctness",
            "unmeasured",
            "Current gates split profiles, not reef module/polyps across partitions.",
            "Tier 4.32b static reef partition smoke.",
        ),
        FailureClassRow(
            "benchmark/large-task performance",
            "unmeasured by this tier",
            "4.32 is a resource model, not MackeyGlass/Lorenz/NARMA or external-baseline evidence.",
            "Return to benchmark matrix after native scale gates stabilize.",
        ),
    ]


def next_gate_rows() -> list[NextGateRow]:
    return [
        NextGateRow(
            "Tier 4.32a",
            "authorize next",
            "How far can the current single-chip multi-core runtime be stressed before schedule, slot, readback, or lookup pressure breaks?",
            "4.32 model passes; use MCPL-first runtime profiles and compact readback.",
            "Passes predeclared sweeps with no stale replies, no timeouts, no fallback, positive profile headroom, and documented breakpoints.",
            "Any overflow/timeout/stale reply/readback failure becomes the blocker to repair before static partitioning.",
            "Single-chip scale-stress evidence only; no multi-chip, benchmark, or baseline-freeze claim.",
        ),
        NextGateRow(
            "Tier 4.32b",
            "blocked until 4.32a passes",
            "Can a static reef partition map modules/polyps to runtime profiles without corrupting state ownership?",
            "4.32a pass and a declared partition map.",
            "Static partition smoke preserves state/readout parity and ownership guards.",
            "Partition mismatch, owner leakage, or readback ambiguity blocks multi-chip work.",
            "Static mapping smoke only; not dynamic growth or multi-chip scaling.",
        ),
        NextGateRow(
            "Tier 4.32c",
            "blocked until 4.32b passes",
            "What is the inter-chip MCPL/multicast contract for state, lifecycle, temporal, and learning messages?",
            "4.32b pass and exact key masks/payloads/cadence declared.",
            "Contract defines routing keys, masks, failure counters, placement assumptions, and minimal readback.",
            "Ambiguous key ownership or unmeasured route failure class blocks hardware smoke.",
            "Contract evidence only; not hardware execution.",
        ),
        NextGateRow(
            "Tier 4.32d",
            "blocked until 4.32c passes",
            "Can the smallest cross-chip message/readback smoke execute with zero stale replies and correct ownership?",
            "4.32c contract and EBRAINS package prepared.",
            "One cross-chip message path passes with real board readback and no fallback.",
            "Any routing/load/message/readback failure becomes a repair tier.",
            "First multi-chip smoke only; not learning scale.",
        ),
        NextGateRow(
            "Tier 4.32e",
            "blocked until 4.32d passes",
            "Can a tiny cross-chip learning micro-task preserve the native learning loop?",
            "4.32d pass and compact reference trace.",
            "Cross-chip learning micro-task matches fixed-point reference within predeclared tolerance.",
            "Mismatch or instability blocks larger native benchmarks.",
            "Tiny multi-chip learning evidence only.",
        ),
        NextGateRow(
            "native scale baseline freeze",
            "not authorized",
            "Is the native runtime stable enough to freeze as a scale baseline?",
            "4.32a-e pass with stable resource model and documented failure envelope.",
            "Freeze only after single-chip stress, partition smoke, inter-chip contract, cross-chip smoke, and cross-chip micro-learning are all clean.",
            "Any unresolved scale or routing blocker prevents freeze.",
            "Would be a native-runtime baseline, separate from software v2.x mechanism baselines.",
        ),
    ]


def build_results() -> dict[str, Any]:
    tier4_27g = read_json(TIER4_27G)
    tier4_28e = read_json(TIER4_28E_POINT_C)
    tier4_29f = read_json(TIER4_29F)
    tier4_30g_hw = read_json(TIER4_30G_HW)
    tier4_30g_task = read_json(TIER4_30G_TASK)
    tier4_31d = read_json(TIER4_31D_REMOTE)
    tier4_31e = read_json(TIER4_31E)

    limits = runtime_limits()
    budgets = profile_budget_rows()
    rows = envelope_rows(tier4_27g, tier4_28e, tier4_30g_task, tier4_31d, limits, budgets)
    next_gates = next_gate_rows()
    failures = failure_classes()
    evidence = evidence_inputs(tier4_27g, tier4_28e, tier4_29f, tier4_30g_hw, tier4_30g_task, tier4_31d, tier4_31e)

    learning_28 = tier4_28e["task"]["final_state"]["learning"]
    resource_rows = read_csv(TIER4_30G_RESOURCE_CSV)
    enabled_row = next(row for row in resource_rows if row["mode"] == "enabled")
    required_limits = {
        "max_context_slots": 128,
        "max_route_slots": 8,
        "max_memory_slots": 8,
        "max_pending_horizons": 128,
        "max_lifecycle_slots": 8,
        "max_schedule_entries": 512,
        "max_lookup_replies": 32,
    }
    profile_statuses = {row.profile: row.status for row in budgets}
    all_itcm_ok = all(row.text_bytes < ITCM_BUDGET_BYTES for row in budgets)
    all_dtcm_ok = all(row.dtcm_estimate_bytes < DTCM_BUDGET_BYTES for row in budgets)
    protocol_mcpl_smaller = tier4_27g["mcpl_payloads"]["round_trip_bytes"] < tier4_27g["sdp_payloads"]["round_trip_bytes"]

    criteria = [
        criterion("Tier 4.27g protocol model passed", status_of(tier4_27g), "== pass", status_of(tier4_27g) == "pass"),
        criterion("Tier 4.28e Point C hardware pressure passed", status_of(tier4_28e), "== pass", status_of(tier4_28e) == "pass"),
        criterion("Tier 4.29f mechanism regression passed", f"{tier4_29f.get('criteria_passed')}/{tier4_29f.get('criteria_total')}", "== 113/113", tier4_29f.get("criteria_passed") == tier4_29f.get("criteria_total") == 113),
        criterion("Tier 4.30g hardware lifecycle bridge passed", status_of(tier4_30g_hw), "== pass", status_of(tier4_30g_hw) == "pass"),
        criterion("Tier 4.31d temporal hardware smoke passed", status_of(tier4_31d), "== pass", status_of(tier4_31d) == "pass"),
        criterion("Tier 4.31e authorized 4.32", tier4_31e.get("final_decision", {}).get("tier4_32"), "== authorized_next", tier4_31e.get("final_decision", {}).get("tier4_32") == "authorized_next"),
        criterion("runtime constants parsed", limits, f"== {required_limits}", limits == required_limits),
        criterion("profile build artifacts parsed", profile_statuses, "all pass", all(status == "pass" for status in profile_statuses.values()) and len(profile_statuses) == 5),
        criterion("profile ITCM headroom positive", min(row.itcm_headroom_bytes for row in budgets), "> 0", all_itcm_ok),
        criterion("profile DTCM estimate headroom positive", min(row.dtcm_headroom_bytes for row in budgets), "> 0", all_dtcm_ok),
        criterion("MCPL is byte-cheaper than SDP", f"{tier4_27g['mcpl_payloads']['round_trip_bytes']} < {tier4_27g['sdp_payloads']['round_trip_bytes']}", "true", protocol_mcpl_smaller),
        criterion("4.28e event pressure recorded", tier4_28e["pressure"]["event_count"], ">= 43", tier4_28e["pressure"]["event_count"] >= 43),
        criterion("4.28e context slot pressure below limit", tier4_28e["pressure"]["context_slots_used"], "< MAX_CONTEXT_SLOTS", tier4_28e["pressure"]["context_slots_used"] < limits["max_context_slots"]),
        criterion("4.28e pending pressure below limit", tier4_28e["pressure"]["max_concurrent_pending"], "< MAX_PENDING_HORIZONS", tier4_28e["pressure"]["max_concurrent_pending"] < limits["max_pending_horizons"]),
        criterion("4.28e lookup request/reply parity", f"{learning_28['lookup_requests']}/{learning_28['lookup_replies']}", "equal", learning_28["lookup_requests"] == learning_28["lookup_replies"]),
        criterion("4.28e stale/duplicate/timeouts absent", learning_28["stale_replies"] + learning_28["duplicate_replies"] + learning_28["timeouts"], "== 0", learning_28["stale_replies"] + learning_28["duplicate_replies"] + learning_28["timeouts"] == 0),
        criterion("4.30g lifecycle modes all passed", [row["mode_status"] for row in resource_rows], "all pass", all(row["mode_status"] == "pass" for row in resource_rows) and len(resource_rows) == 6),
        criterion("4.30g lifecycle lookup parity", f"{enabled_row['learning_lookup_requests']}/{enabled_row['learning_lookup_replies']}", "equal", int_field(enabled_row, "learning_lookup_requests") == int_field(enabled_row, "learning_lookup_replies")),
        criterion("4.30g stale/timeouts absent", int_field(enabled_row, "learning_stale_replies") + int_field(enabled_row, "learning_timeouts"), "== 0", int_field(enabled_row, "learning_stale_replies") + int_field(enabled_row, "learning_timeouts") == 0),
        criterion("4.31d temporal payload measured", tier4_31d["summary"]["temporal_payload_len"], "== 48", tier4_31d["summary"]["temporal_payload_len"] == 48),
        criterion("resource envelope rows cover required categories", sorted({row.category for row in rows}), "contains protocol/four_core/readback/five_core/temporal/limits/profile", {"protocol", "four_core_pressure", "readback", "five_core_lifecycle", "temporal", "limits", "profile_budget"}.issubset({row.category for row in rows})),
        criterion("failure classes declared", len(failures), ">= 8", len(failures) >= 8),
        criterion("next gate is 4.32a, not freeze", next_gates[0].gate, "== Tier 4.32a", next_gates[0].gate == "Tier 4.32a" and next_gates[0].decision == "authorize next"),
    ]
    failed = [item for item in criteria if not item.passed]
    status = "pass" if not failed else "fail"

    final_decision = {
        "status": status,
        "tier4_32a": "authorized_next" if status == "pass" else "blocked_until_4_32_repairs",
        "tier4_32b": "blocked_until_4_32a_passes",
        "tier4_32c": "blocked_until_4_32b_passes",
        "tier4_32d": "blocked_until_4_32c_passes",
        "tier4_32e": "blocked_until_4_32d_passes",
        "native_scale_baseline_freeze": "not_authorized",
        "mcpl_policy": "mcpl_first_for_scale_sdp_fallback_control_only",
        "claim_boundary": "local resource/mapping model over measured evidence only",
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
        "evidence_inputs": evidence,
        "runtime_limits": limits,
        "profile_budgets": budgets,
        "resource_envelope": rows,
        "failure_classes": failures,
        "next_gate_plan": next_gates,
        "final_decision": final_decision,
        "recommended_next_step": (
            "Tier 4.32a single-chip multi-core scale stress with MCPL-first messaging and compact readback."
            if status == "pass"
            else "Repair failed Tier 4.32 model criteria before scale stress."
        ),
        "claim_boundary": (
            "Tier 4.32 is a local mapping/resource model over measured Tier 4.27-4.31 evidence. "
            "It is not a new SpiNNaker run, not a speedup claim, not a multi-chip claim, not a "
            "benchmark/superiority claim, not a full organism autonomy claim, and not a baseline freeze."
        ),
    }


def write_report(path: Path, results: dict[str, Any]) -> None:
    lines = [
        "# Tier 4.32 Native Runtime Mapping/Resource Model",
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

    lines.extend(["", "## Evidence Inputs", "", "| Source | Status | Role | Extracted Signal | Path |", "| --- | --- | --- | --- | --- |"])
    for item in results["evidence_inputs"]:
        lines.append(f"| `{item['source_id']}` | `{item['status']}` | {item['role']} | {item['extracted_signal']} | `{item['path']}` |")

    lines.extend(["", "## Profile Budget", "", "| Profile | Text | Data | BSS | ITCM Headroom | DTCM Estimate | DTCM Headroom | Source |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |"])
    for row in results["profile_budgets"]:
        lines.append(
            f"| `{row['profile']}` | {row['text_bytes']} | {row['data_bytes']} | {row['bss_bytes']} | "
            f"{row['itcm_headroom_bytes']} | {row['dtcm_estimate_bytes']} | {row['dtcm_headroom_bytes']} | `{row['source_artifact']}` |"
        )

    lines.extend(["", "## Resource Envelope", "", "| Category | Metric | Value | Unit | Evidence | Interpretation |", "| --- | --- | ---: | --- | --- | --- |"])
    for row in results["resource_envelope"]:
        lines.append(
            f"| `{row['category']}` | `{row['metric']}` | `{row['value']}` | {row['unit']} | `{row['evidence_source']}` | {row['interpretation']} |"
        )

    lines.extend(["", "## Failure Classes", "", "| Failure Class | Status | Evidence | Next Detection Gate |", "| --- | --- | --- | --- |"])
    for row in results["failure_classes"]:
        lines.append(f"| `{row['failure_class']}` | {row['status']} | {row['evidence']} | {row['next_detection_gate']} |")

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

    write_json(output_dir / "tier4_32_results.json", safe)
    write_report(output_dir / "tier4_32_report.md", safe)
    write_csv(output_dir / "tier4_32_evidence_inputs.csv", safe["evidence_inputs"])
    write_csv(output_dir / "tier4_32_profile_budget.csv", safe["profile_budgets"])
    write_csv(output_dir / "tier4_32_resource_envelope.csv", safe["resource_envelope"])
    write_csv(output_dir / "tier4_32_failure_classes.csv", safe["failure_classes"])
    write_csv(output_dir / "tier4_32_next_gate_plan.csv", safe["next_gate_plan"])
    write_csv(output_dir / "tier4_32_criteria.csv", safe["criteria"])
    write_json(
        LATEST_MANIFEST,
        {
            "tier": TIER,
            "runner_revision": RUNNER_REVISION,
            "generated_at_utc": results["generated_at_utc"],
            "status": results["status"],
            "manifest": str(output_dir / "tier4_32_results.json"),
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
                "final_decision": results["final_decision"],
                "next": results["recommended_next_step"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if results["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
