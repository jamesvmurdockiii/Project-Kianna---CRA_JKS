#!/usr/bin/env python3
"""Tier 4.32f multi-chip resource/lifecycle decision contract.

Tier 4.32e proved the smallest two-chip, single-shard learning-bearing MCPL
micro-task. This gate deliberately does not package another EBRAINS hardware
run. It decides the next scalable multi-chip target and records what must be
source-proven before spending hardware time again.

Decision boundary: lifecycle traffic is the right next direction, because CRA's
organism claim depends on lifecycle/self-scaling moving across the same native
multi-chip substrate as lookup/learning. However, current source only proves
inter-chip route entries for lookup request/reply packets, not lifecycle
event/trophic/mask-sync packets. Therefore 4.32f authorizes a local 4.32g-r0
lifecycle route/source repair audit before any 4.32g hardware package.
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

TIER = "Tier 4.32f - Multi-Chip Resource/Lifecycle Decision Contract"
RUNNER_REVISION = "tier4_32f_multichip_resource_lifecycle_decision_20260507_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier4_32f_20260507_multichip_resource_lifecycle_decision"
LATEST_MANIFEST = CONTROLLED / "tier4_32f_latest_manifest.json"

TIER4_30G = CONTROLLED / "tier4_30g_hw_20260505_hardware_pass_ingested" / "tier4_30g_hw_results.json"
TIER4_32B = CONTROLLED / "tier4_32b_20260507_static_reef_partition_smoke" / "tier4_32b_results.json"
TIER4_32D = CONTROLLED / "tier4_32d_20260507_hardware_pass_ingested" / "tier4_32d_results.json"
TIER4_32E = CONTROLLED / "tier4_32e_20260507_hardware_pass_ingested" / "tier4_32e_results.json"
TIER4_32E_TASK = (
    CONTROLLED
    / "tier4_32e_20260507_hardware_pass_ingested"
    / "returned_artifacts"
    / "tier4_32e_task_result.json"
)

CLAIM_BOUNDARY = (
    "Tier 4.32f is a local decision/contract gate after the first two-chip "
    "learning-bearing hardware micro-task. It does not run SpiNNaker hardware, "
    "does not claim speedup, does not claim benchmark superiority, does not "
    "claim true two-partition learning, does not claim lifecycle scaling, does "
    "not claim multi-shard learning, and does not freeze a native-scale baseline."
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
    check_id: str
    file: str
    token: str
    present: bool
    implication: str


@dataclass(frozen=True)
class CandidateDirection:
    direction: str
    decision: str
    reason: str
    required_before_hardware: str
    claim_boundary: str


@dataclass(frozen=True)
class NextGate:
    gate: str
    status: str
    question: str
    hypothesis: str
    null_hypothesis: str
    mechanism_under_test: str
    required_work: str
    pass_case: str
    fail_case: str
    expected_artifacts: str
    claim_boundary: str


@dataclass(frozen=True)
class RequiredReadback:
    field: str
    producer: str
    required_for: str
    expected_rule: str
    why: str


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


def parse_define_int(path: Path, name: str) -> int:
    pattern = re.compile(rf"^\s*#define\s+{re.escape(name)}\s+(0x[0-9A-Fa-f]+|[0-9]+)\b")
    for line in path.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if match:
            return int(match.group(1), 0)
    raise ValueError(f"missing #define {name} in {path}")


def source_has(path: Path, token: str) -> bool:
    return token in path.read_text(encoding="utf-8")


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
    checks = [
        ("lifecycle_event_msg_type", config_h, "MCPL_MSG_LIFECYCLE_EVENT_REQUEST", "Lifecycle event request packet type exists."),
        ("lifecycle_trophic_msg_type", config_h, "MCPL_MSG_LIFECYCLE_TROPHIC_UPDATE", "Lifecycle trophic update packet type exists."),
        ("lifecycle_mask_sync_msg_type", config_h, "MCPL_MSG_LIFECYCLE_ACTIVE_MASK_SYNC", "Lifecycle active-mask sync packet type exists."),
        ("lifecycle_event_sender", state_h, "cra_lifecycle_send_event_request_stub", "Lifecycle event request sender is declared."),
        ("lifecycle_trophic_sender", state_h, "cra_lifecycle_send_trophic_update_stub", "Lifecycle trophic update sender is declared."),
        ("lifecycle_event_handler", state_h, "cra_lifecycle_handle_event_request", "Lifecycle event receiver/handler is declared."),
        ("lifecycle_trophic_handler", state_h, "cra_lifecycle_handle_trophic_request", "Lifecycle trophic receiver/handler is declared."),
        ("lifecycle_mask_receiver", state_h, "cra_lifecycle_receive_active_mask_sync", "Lifecycle mask-sync receiver is declared."),
        ("lifecycle_duplicate_counter", state_h, "lifecycle_duplicate_events", "Duplicate lifecycle events are counted."),
        ("lifecycle_stale_counter", state_h, "lifecycle_stale_events", "Stale lifecycle events are counted."),
        ("lifecycle_missing_ack_counter", state_h, "lifecycle_missing_acks", "Missing lifecycle acks are counted."),
        ("lookup_interchip_request_route", state_c, "CRA_MCPL_INTERCHIP_REQUEST_LINK_ROUTE", "Lookup route repair has explicit source-chip request-link routing."),
        ("lookup_interchip_reply_route", state_c, "CRA_MCPL_INTERCHIP_REPLY_LINK_ROUTE", "Lookup route repair has explicit state-chip reply-link routing."),
    ]
    return [
        SourceCheck(check_id=check_id, file=rel(path), token=token, present=source_has(path, token), implication=implication)
        for check_id, path, token, implication in checks
    ]


def lifecycle_interchip_routes_source_proven() -> bool:
    """Return whether source currently installs explicit lifecycle inter-chip routes.

    We intentionally look for route-install code, not merely lifecycle packet
    senders. Lookup inter-chip routing was repaired by installing explicit link
    routes. The lifecycle packets need the same source-proven route treatment
    before a reviewer-defensible two-chip lifecycle hardware smoke.
    """
    state_c = (RUNTIME_SRC / "state_manager.c").read_text(encoding="utf-8")
    has_lifecycle_msgs = all(
        token in state_c
        for token in (
            "MCPL_MSG_LIFECYCLE_EVENT_REQUEST",
            "MCPL_MSG_LIFECYCLE_TROPHIC_UPDATE",
            "MCPL_MSG_LIFECYCLE_ACTIVE_MASK_SYNC",
        )
    )
    has_lifecycle_route_macro = "CRA_MCPL_INTERCHIP_LIFECYCLE" in state_c
    has_route_install_near_lifecycle = bool(
        re.search(r"_mcpl_install_route\([^;]+MCPL_MSG_LIFECYCLE", state_c, flags=re.DOTALL)
    )
    return has_lifecycle_msgs and (has_lifecycle_route_macro or has_route_install_near_lifecycle)


def learning_case_summaries(task: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case in task.get("cases", []):
        learning = (case.get("final_state") or {}).get("learning") or {}
        rows.append(
            {
                "case_label": case.get("case_label"),
                "case_kind": case.get("case_kind"),
                "event_count": case.get("event_count"),
                "expected_lookup_count": case.get("expected_lookup_count"),
                "lookup_requests": learning.get("lookup_requests"),
                "lookup_replies": learning.get("lookup_replies"),
                "stale_replies": learning.get("stale_replies"),
                "duplicate_replies": learning.get("duplicate_replies"),
                "timeouts": learning.get("timeouts"),
                "pending_created": learning.get("pending_created"),
                "pending_matured": learning.get("pending_matured"),
                "active_pending": learning.get("active_pending"),
                "readout_weight_raw": learning.get("readout_weight_raw"),
                "readout_bias_raw": learning.get("readout_bias_raw"),
                "payload_len": learning.get("payload_len"),
            }
        )
    return rows


def candidate_directions(lifecycle_routes_ready: bool) -> list[CandidateDirection]:
    lifecycle_decision = "selected_but_requires_4_32g_r0_source_repair"
    lifecycle_requirement = (
        "Add/prove explicit inter-chip lifecycle route entries and lifecycle "
        "readback counters before EBRAINS hardware."
    )
    if lifecycle_routes_ready:
        lifecycle_decision = "selected_and_source_routes_ready_for_package"
        lifecycle_requirement = "Prepare the bounded 4.32g hardware package with lifecycle traffic/resource counters."
    return [
        CandidateDirection(
            direction="multi_chip_lifecycle_traffic",
            decision=lifecycle_decision,
            reason="The organism/self-scaling claim needs lifecycle traffic to move across chips after lookup/learning already passed.",
            required_before_hardware=lifecycle_requirement,
            claim_boundary="Lifecycle traffic/resource smoke only; not full lifecycle scaling or autonomous growth.",
        ),
        CandidateDirection(
            direction="resource_timing_characterization",
            decision="include_inside_lifecycle_smoke_not_standalone_next",
            reason="Resource/timing counters are necessary, but a timing-only run would not advance the organism-scale mechanism path.",
            required_before_hardware="Predeclare payload length, message count, stale/duplicate/timeout counters, wall/runtime fields, and per-role compact readback.",
            claim_boundary="Engineering measurement only, not speedup.",
        ),
        CandidateDirection(
            direction="true_two_partition_cross_chip_learning",
            decision="blocked",
            reason="Current evidence still uses one shard field and one source/remote partition; origin/target shard semantics are not defined.",
            required_before_hardware="Define origin shard, target shard, role ownership, and cross-partition credit semantics before attempting this.",
            claim_boundary="No true two-partition learning claim.",
        ),
        CandidateDirection(
            direction="benchmarks_or_speedup",
            decision="blocked",
            reason="Benchmark/speedup claims require stable native scale mechanics and fair software baselines first.",
            required_before_hardware="Complete native scale/lifecycle gates and freeze a justified native-scale baseline.",
            claim_boundary="No benchmark or speedup claim from 4.32f.",
        ),
        CandidateDirection(
            direction="CRA_NATIVE_SCALE_BASELINE_v0_5",
            decision="not_authorized",
            reason="4.32e is a major pass but still tiny and single-shard; lifecycle/resource and multi-shard semantics remain open.",
            required_before_hardware="At minimum, pass a contract-backed lifecycle/resource gate and decide true partition semantics.",
            claim_boundary="No native-scale baseline freeze.",
        ),
    ]


def required_readback_fields() -> list[RequiredReadback]:
    return [
        RequiredReadback("board_id", "host/placement", "all later multi-chip tiers", "non-empty and preserved in returned artifacts", "tie evidence to EBRAINS allocation"),
        RequiredReadback("chip_x/chip_y/p_core/role", "host/runtime", "all role cores", "matches placement table", "reconstruct ownership"),
        RequiredReadback("partition_id/shard_id", "host/runtime/MCPL key", "all lifecycle and lookup messages", "matches selected static reef partition", "prevent cross-talk"),
        RequiredReadback("lifecycle_event_requests_sent", "source/runtime", "4.32g-r0 and 4.32g", "> 0 for lifecycle smoke", "prove event traffic was emitted"),
        RequiredReadback("lifecycle_trophic_requests_sent", "source/runtime", "4.32g-r0 and 4.32g", "> 0 when trophic updates are scheduled", "prove trophic traffic was emitted"),
        RequiredReadback("lifecycle_event_acks_received", "source/runtime", "4.32g-r0 and 4.32g", "== expected lifecycle mutating events", "prove event requests were accepted"),
        RequiredReadback("lifecycle_mask_syncs_sent", "lifecycle core", "4.32g-r0 and 4.32g", "> 0 after active-mask mutation", "prove mask sync broadcast"),
        RequiredReadback("lifecycle_mask_syncs_received", "learning/consumer core", "4.32g-r0 and 4.32g", "== expected sync packets", "prove consumer saw mask sync"),
        RequiredReadback("lifecycle_duplicate_events", "lifecycle core", "4.32g-r0 and 4.32g", "== 0 in canonical case; >0 in duplicate-control if used", "classify duplicate failures"),
        RequiredReadback("lifecycle_stale_events", "lifecycle core", "4.32g-r0 and 4.32g", "== 0 in canonical case; >0 in stale-control if used", "classify stale failures"),
        RequiredReadback("lifecycle_missing_acks", "source/runtime", "4.32g-r0 and 4.32g", "== 0", "catch lost lifecycle packets"),
        RequiredReadback("payload_len", "all compact readbacks", "all later hardware tiers", "within compact schema limit", "avoid readback bloat"),
    ]


def next_gates(lifecycle_routes_ready: bool) -> list[NextGate]:
    hardware_status = "blocked_until_4_32g_r0_passes"
    required_work = (
        "Audit/repair source support for explicit inter-chip lifecycle routes for "
        "event request, trophic update, active-mask sync, and any ack/readback "
        "path. Add local host tests before packaging."
    )
    if lifecycle_routes_ready:
        hardware_status = "authorized_after_contract_review"
        required_work = "Prepare bounded 4.32g hardware package with lifecycle/resource counters."
    return [
        NextGate(
            gate="Tier 4.32g-r0 - Multi-Chip Lifecycle Route/Source Repair Audit",
            status="authorized_next",
            question="Can lifecycle MCPL event/trophic/mask-sync traffic be made chip/shard explicit enough for a two-chip lifecycle smoke?",
            hypothesis="The runtime can source-prove explicit lifecycle routes and counters analogous to the lookup route repair that enabled 4.32d/e.",
            null_hypothesis="Lifecycle packets exist but cannot be routed/read back across chips without ambiguity or missing counters.",
            mechanism_under_test="lifecycle MCPL message routing, duplicate/stale/missing-ack counters, active-mask sync, lineage checksum visibility",
            required_work=required_work,
            pass_case="All lifecycle route/source checks pass locally and the 4.32g hardware package is authorized.",
            fail_case="Do not package EBRAINS; repair route/key/readback/counter semantics first.",
            expected_artifacts="tier4_32g_r0_results.json, report, criteria CSV, source findings CSV, route contract CSV, test command logs",
            claim_boundary="Local source/route audit only; not hardware lifecycle scaling.",
        ),
        NextGate(
            gate="Tier 4.32g - Two-Chip Lifecycle Traffic/Resource Hardware Smoke",
            status=hardware_status,
            question="Can lifecycle event/trophic/mask-sync traffic cross the chip boundary with compact resource counters?",
            hypothesis="A bounded two-chip single-shard lifecycle traffic smoke preserves event acceptance, active-mask sync, lineage checksum, and zero stale/duplicate/missing-ack counters.",
            null_hypothesis="Lifecycle traffic fails, cannot be reconstructed, or bloats readback before scale.",
            mechanism_under_test="native lifecycle MCPL traffic across chips with resource/timing/readback accounting",
            required_work="Only prepare after 4.32g-r0 passes.",
            pass_case="Canonical lifecycle events and at least one control return exact counters, compact payload, and zero fallback.",
            fail_case="Classify as route, key, ack, readback, source/package, allocation, or lifecycle semantics failure.",
            expected_artifacts="tier4_32g_results.json, task result JSON, per-case summaries, target acquisition, build/load logs, reports zip",
            claim_boundary="Two-chip lifecycle traffic/resource smoke only; not full lifecycle scaling.",
        ),
        NextGate(
            gate="Tier 4.32h - True Partition Semantics Contract",
            status="blocked_until_lifecycle_resource_gate",
            question="What origin/target shard semantics are required before true two-partition cross-chip learning?",
            hypothesis="Origin/target shard identity can be defined without breaking the existing single-shard MCPL path.",
            null_hypothesis="The current key/readback contract is insufficient for true two-partition learning.",
            mechanism_under_test="origin shard, target shard, partition role ownership, cross-partition credit assignment",
            required_work="Define after lifecycle/resource traffic is either passed or explicitly parked.",
            pass_case="Authorizes a true two-partition local reference/repair tier.",
            fail_case="Keep claims to single-shard split-role hardware evidence.",
            expected_artifacts="contract results, identity table, message path table, failure class table",
            claim_boundary="Contract only; no hardware claim.",
        ),
    ]


def evaluate() -> dict[str, Any]:
    tier4_30g = read_json(TIER4_30G)
    tier4_32b = read_json(TIER4_32B)
    tier4_32d = read_json(TIER4_32D)
    tier4_32e = read_json(TIER4_32E)
    tier4_32e_task = read_json(TIER4_32E_TASK)
    limits = runtime_limits()
    checks = source_checks()
    lifecycle_routes_ready = lifecycle_interchip_routes_source_proven()
    directions = candidate_directions(lifecycle_routes_ready)
    readback = required_readback_fields()
    gates = next_gates(lifecycle_routes_ready)
    cases = learning_case_summaries(tier4_32e_task)
    all_cases_pass = tier4_32e_task.get("status") == "pass" and len(cases) == 2
    lookup_cases_clean = all(
        row.get("lookup_requests") == row.get("lookup_replies") == row.get("expected_lookup_count")
        and row.get("stale_replies") == 0
        and row.get("duplicate_replies") == 0
        and row.get("timeouts") == 0
        for row in cases
    )
    enabled = next((row for row in cases if row.get("case_label") == "enabled_lr_0_25"), {})
    no_learning = next((row for row in cases if row.get("case_label") == "no_learning_lr_0_00"), {})
    source_missing = [row.check_id for row in checks if not row.present]
    required_tokens_exist = not source_missing
    criteria = [
        criterion("Tier 4.30g lifecycle native baseline evidence passed", tier4_30g.get("status"), "== pass", tier4_30g.get("status") == "pass"),
        criterion("Tier 4.32b static partition map passed", tier4_32b.get("status"), "== pass", tier4_32b.get("status") == "pass"),
        criterion("Tier 4.32d two-chip lookup smoke passed", tier4_32d.get("status"), "== pass", tier4_32d.get("status") == "pass"),
        criterion("Tier 4.32e two-chip learning micro-task passed", tier4_32e.get("status"), "== pass", tier4_32e.get("status") == "pass"),
        criterion("Tier 4.32e raw remote status passed", tier4_32e.get("summary", {}).get("raw_remote_status"), "== pass", tier4_32e.get("summary", {}).get("raw_remote_status") == "pass"),
        criterion("Tier 4.32e preserved returned artifacts", tier4_32e.get("summary", {}).get("returned_artifact_count"), ">= 40", (tier4_32e.get("summary", {}).get("returned_artifact_count") or 0) >= 40),
        criterion("Tier 4.32e task result passed", tier4_32e_task.get("status"), "== pass", tier4_32e_task.get("status") == "pass"),
        criterion("Tier 4.32e contains enabled and no-learning cases", [row.get("case_label") for row in cases], "contains enabled_lr_0_25 and no_learning_lr_0_00", all_cases_pass),
        criterion("Tier 4.32e lookup cases clean", lookup_cases_clean, "all requests==replies and zero stale/duplicate/timeouts", lookup_cases_clean),
        criterion("enabled learning moved readout", enabled.get("readout_weight_raw"), "== 32768", enabled.get("readout_weight_raw") == 32768),
        criterion("no-learning control stayed zero", no_learning.get("readout_weight_raw"), "== 0", no_learning.get("readout_weight_raw") == 0),
        criterion("runtime lifecycle source primitives exist", source_missing, "empty", required_tokens_exist),
        criterion("lifecycle inter-chip route gap classified", lifecycle_routes_ready, "False is acceptable only if next hardware is blocked", lifecycle_routes_ready is False, "Current source lacks explicit lifecycle inter-chip route installs; 4.32g-r0 is required."),
        criterion("next direction selects lifecycle traffic", directions[0].direction, "== multi_chip_lifecycle_traffic", directions[0].direction == "multi_chip_lifecycle_traffic"),
        criterion("next direction blocks immediate lifecycle hardware", gates[1].status, "== blocked_until_4_32g_r0_passes", gates[1].status == "blocked_until_4_32g_r0_passes"),
        criterion("true two-partition learning remains blocked", directions[2].decision, "== blocked", directions[2].decision == "blocked"),
        criterion("speedup and benchmarks remain blocked", directions[3].decision, "== blocked", directions[3].decision == "blocked"),
        criterion("native scale baseline freeze not authorized", directions[4].decision, "== not_authorized", directions[4].decision == "not_authorized"),
        criterion("4.32g-r0 authorized next", gates[0].status, "== authorized_next", gates[0].status == "authorized_next"),
        criterion("lifecycle readback requires duplicate/stale/missing-ack counters", [row.field for row in readback], "contains lifecycle_duplicate_events/lifecycle_stale_events/lifecycle_missing_acks", {"lifecycle_duplicate_events", "lifecycle_stale_events", "lifecycle_missing_acks"}.issubset({row.field for row in readback})),
        criterion("compact payload remains required", [row.field for row in readback], "contains payload_len", any(row.field == "payload_len" for row in readback)),
        criterion("lifecycle pool fits current static native pool", limits["max_lifecycle_slots"], ">= 8", limits["max_lifecycle_slots"] >= 8),
    ]
    status = "pass" if all(row.passed for row in criteria) else "fail"
    final_decision = {
        "status": status,
        "selected_next_gate": "tier4_32g_r0_multichip_lifecycle_route_source_repair_audit",
        "tier4_32g_hardware": "blocked_until_4_32g_r0_passes",
        "lifecycle_interchip_routes_source_proven": lifecycle_routes_ready,
        "true_two_partition_learning": "blocked_until_origin_target_shard_semantics",
        "speedup_claims": "not_authorized",
        "benchmark_claims": "not_authorized",
        "native_scale_baseline_freeze": "not_authorized",
        "claim_boundary": CLAIM_BOUNDARY,
    }
    summary = {
        "tier4_32e_learning_microtask_status": tier4_32e.get("status"),
        "tier4_32e_raw_remote_status": tier4_32e.get("summary", {}).get("raw_remote_status"),
        "tier4_32e_returned_artifact_count": tier4_32e.get("summary", {}).get("returned_artifact_count"),
        "lifecycle_interchip_routes_source_proven": lifecycle_routes_ready,
        "selected_direction": "multi_chip_lifecycle_traffic_with_resource_counters",
        "selected_next_gate": final_decision["selected_next_gate"],
        "hardware_package_status": final_decision["tier4_32g_hardware"],
        "why_not_true_partition_yet": "origin/target shard semantics remain undefined",
        "why_not_benchmark_yet": "native scale/lifecycle mechanics are not stable enough for benchmark/speedup claims",
    }
    return {
        "status": status,
        "criteria": criteria,
        "summary": summary,
        "final_decision": final_decision,
        "runtime_limits": limits,
        "source_checks": checks,
        "learning_case_summaries": cases,
        "candidate_directions": directions,
        "required_readback": readback,
        "next_gates": gates,
    }


def write_report(path: Path, payload: dict[str, Any], output_dir: Path) -> None:
    lines = [
        "# Tier 4.32f Multi-Chip Resource/Lifecycle Decision Contract",
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
        f"- Selected direction: `{payload['summary']['selected_direction']}`",
        f"- Selected next gate: `{payload['summary']['selected_next_gate']}`",
        f"- Hardware package status: `{payload['summary']['hardware_package_status']}`",
        f"- Lifecycle inter-chip routes source-proven now: `{payload['summary']['lifecycle_interchip_routes_source_proven']}`",
        f"- True partition learning: `{payload['final_decision']['true_two_partition_learning']}`",
        f"- Native scale baseline freeze: `{payload['final_decision']['native_scale_baseline_freeze']}`",
        "",
        "## Why",
        "",
        "Tier 4.32d proved two-chip communication/readback. Tier 4.32e proved a",
        "tiny two-chip learning-bearing micro-task with enabled-vs-no-learning",
        "separation. The next organism-scale question is lifecycle traffic across",
        "chips, but lifecycle inter-chip route entries are not source-proven yet.",
        "So 4.32f authorizes a local 4.32g-r0 source/route repair audit and blocks",
        "the 4.32g hardware package until that audit passes.",
        "",
        "## 4.32e Learning Case Summary",
        "",
        "| Case | Kind | Events | Lookups | Stale | Duplicate | Timeouts | Pending | Readout | Payload |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: |",
    ]
    for row in payload["learning_case_summaries"]:
        pending = f"{row['pending_created']}/{row['pending_matured']}/{row['active_pending']}"
        readout = f"{row['readout_weight_raw']}/{row['readout_bias_raw']}"
        lines.append(
            f"| `{row['case_label']}` | `{row['case_kind']}` | {row['event_count']} | "
            f"{row['lookup_requests']}/{row['lookup_replies']} | {row['stale_replies']} | "
            f"{row['duplicate_replies']} | {row['timeouts']} | `{pending}` | `{readout}` | {row['payload_len']} |"
        )
    lines.extend(["", "## Candidate Directions", "", "| Direction | Decision | Reason | Required Before Hardware | Boundary |", "| --- | --- | --- | --- | --- |"])
    for row in payload["candidate_directions"]:
        lines.append(f"| `{row['direction']}` | `{row['decision']}` | {row['reason']} | {row['required_before_hardware']} | {row['claim_boundary']} |")
    lines.extend(["", "## Next Gates", "", "| Gate | Status | Question | Pass | Fail |", "| --- | --- | --- | --- | --- |"])
    for row in payload["next_gates"]:
        lines.append(f"| `{row['gate']}` | `{row['status']}` | {row['question']} | {row['pass_case']} | {row['fail_case']} |")
    lines.extend(["", "## Required Readback For Next Hardware Work", "", "| Field | Producer | Required For | Rule | Why |", "| --- | --- | --- | --- | --- |"])
    for row in payload["required_readback"]:
        lines.append(f"| `{row['field']}` | {row['producer']} | {row['required_for']} | `{row['expected_rule']}` | {row['why']} |")
    lines.extend(["", "## Source Checks", "", "| Check | File | Token | Present | Implication |", "| --- | --- | --- | --- | --- |"])
    for row in payload["source_checks"]:
        lines.append(f"| `{row['check_id']}` | `{row['file']}` | `{row['token']}` | {'yes' if row['present'] else 'no'} | {row['implication']} |")
    lines.extend(["", "## Criteria", "", "| Criterion | Value | Rule | Pass | Note |", "| --- | --- | --- | --- | --- |"])
    for row in payload["criteria"]:
        value = row["value"] if isinstance(row["value"], str) else json.dumps(json_safe(row["value"]), sort_keys=True)
        lines.append(f"| {row['name']} | `{value}` | {row['rule']} | {'yes' if row['passed'] else 'no'} | {row['note']} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(output_dir: Path) -> dict[str, Any]:
    generated_at = utc_now()
    output_dir.mkdir(parents=True, exist_ok=True)
    evaluated = evaluate()
    criteria = evaluated["criteria"]
    status = evaluated["status"]
    artifacts = {
        "results_json": output_dir / "tier4_32f_results.json",
        "report_md": output_dir / "tier4_32f_report.md",
        "criteria_csv": output_dir / "tier4_32f_criteria.csv",
        "source_checks_csv": output_dir / "tier4_32f_source_checks.csv",
        "learning_cases_csv": output_dir / "tier4_32f_learning_cases.csv",
        "candidate_directions_csv": output_dir / "tier4_32f_candidate_directions.csv",
        "required_readback_csv": output_dir / "tier4_32f_required_readback.csv",
        "next_gates_csv": output_dir / "tier4_32f_next_gates.csv",
    }
    payload = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": generated_at,
        "status": status,
        "criteria_passed": sum(row.passed for row in criteria),
        "criteria_total": len(criteria),
        "output_dir": str(output_dir),
        "claim_boundary": CLAIM_BOUNDARY,
        "summary": evaluated["summary"],
        "final_decision": evaluated["final_decision"],
        "runtime_limits": evaluated["runtime_limits"],
        "source_checks": evaluated["source_checks"],
        "learning_case_summaries": evaluated["learning_case_summaries"],
        "candidate_directions": evaluated["candidate_directions"],
        "required_readback": evaluated["required_readback"],
        "next_gates": evaluated["next_gates"],
        "criteria": criteria,
        "artifacts": artifacts,
    }
    write_json(artifacts["results_json"], payload)
    write_csv(artifacts["criteria_csv"], [asdict(row) for row in criteria])
    write_csv(artifacts["source_checks_csv"], [asdict(row) for row in evaluated["source_checks"]])
    write_csv(artifacts["learning_cases_csv"], evaluated["learning_case_summaries"])
    write_csv(artifacts["candidate_directions_csv"], [asdict(row) for row in evaluated["candidate_directions"]])
    write_csv(artifacts["required_readback_csv"], [asdict(row) for row in evaluated["required_readback"]])
    write_csv(artifacts["next_gates_csv"], [asdict(row) for row in evaluated["next_gates"]])
    write_report(artifacts["report_md"], json_safe(payload), output_dir)
    write_json(
        LATEST_MANIFEST,
        {
            "claim": "Latest Tier 4.32f multi-chip resource/lifecycle decision contract.",
            "generated_at_utc": generated_at,
            "manifest": str(artifacts["results_json"]),
            "status": status,
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
