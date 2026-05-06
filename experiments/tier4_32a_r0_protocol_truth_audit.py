#!/usr/bin/env python3
"""Tier 4.32a-r0 protocol truth audit.

Tier 4.32a predeclared a single-chip scale-stress path and correctly blocked
replicated shards because the MCPL lookup key has no shard/group field. Before
packaging Tier 4.32a-hw, this audit checks one more source-level fact that must
stay visible: the promoted confidence-gated learning path currently uses the
transitional SDP lookup path because the MCPL lookup payload does not yet carry
confidence/hit status.

This tier is a corrective source/documentation gate. It is not hardware
evidence, not a speedup claim, and not a native-scale baseline freeze.
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

TIER = "Tier 4.32a-r0 - Protocol Truth Audit"
RUNNER_REVISION = "tier4_32a_r0_protocol_truth_audit_20260506_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier4_32a_r0_20260506_protocol_truth_audit"
LATEST_MANIFEST = CONTROLLED / "tier4_32a_r0_latest_manifest.json"

TIER4_32A_RESULTS = CONTROLLED / "tier4_32a_20260506_single_chip_scale_stress" / "tier4_32a_results.json"
STATE_MANAGER = RUNTIME_SRC / "state_manager.c"
CONFIG_H = RUNTIME_SRC / "config.h"

CLAIM_BOUNDARY = (
    "Tier 4.32a-r0 is a source/documentation truth audit. It proves that the "
    "planned MCPL-first scale stress cannot be honestly packaged yet because "
    "the current confidence-gated lookup path still uses SDP and the MCPL "
    "lookup helpers do not carry confidence or shard identity. It is not a "
    "hardware run, not speedup evidence, not multi-chip scaling, and not a "
    "baseline freeze."
)


@dataclass(frozen=True)
class Criterion:
    name: str
    value: Any
    rule: str
    passed: bool
    note: str = ""


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


def read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def line_number(text: str, needle: str) -> int | None:
    for index, line in enumerate(text.splitlines(), start=1):
        if needle in line:
            return index
    return None


def section(text: str, start_pattern: str, end_pattern: str | None = None) -> str:
    start = re.search(start_pattern, text, flags=re.MULTILINE)
    if not start:
        return ""
    start_index = start.start()
    if end_pattern is None:
        return text[start_index:]
    end = re.search(end_pattern, text[start.end():], flags=re.MULTILINE)
    if not end:
        return text[start_index:]
    return text[start_index:start.end() + end.start()]


def source_findings() -> list[dict[str, Any]]:
    state = STATE_MANAGER.read_text(encoding="utf-8")
    config = CONFIG_H.read_text(encoding="utf-8")

    request_section = section(state, r"^static void _send_lookup_request", r"^int cra_state_lookup_send")
    reply_section = section(state, r"^static void _send_lookup_reply", r"^void cra_state_handle_lookup_request")
    mcpl_request_section = section(state, r"^void cra_state_mcpl_lookup_send_request", r"^void cra_state_mcpl_lookup_send_reply")
    mcpl_reply_section = section(state, r"^void cra_state_mcpl_lookup_send_reply", r"^void cra_state_mcpl_lookup_receive")
    mcpl_receive_section = section(state, r"^void cra_state_mcpl_lookup_receive", r"^void cra_state_mcpl_init")

    key_layout_line = line_number(config, "Bit layout: app_id (8) | msg_type (4) | lookup_type (4) | seq_id (16)")
    findings = [
        {
            "finding_id": "confidence_lookup_uses_sdp",
            "file": str(STATE_MANAGER.relative_to(ROOT)),
            "line": line_number(state, "4.29d: MCPL lookup does not yet transmit confidence; use SDP for"),
            "observed": "#if 0 disables MCPL lookup request send; SDP path remains active for confidence-gated learning.",
            "blocks": "MCPL-first 4.32a-hw scale-stress packaging",
            "required_repair": "Pack value, confidence, hit/status, and lookup type through MCPL or another measured multicast-compatible protocol.",
            "present": "#if 0" in request_section and "spin1_send_sdp_msg" in request_section,
        },
        {
            "finding_id": "mcpl_reply_drops_confidence",
            "file": str(STATE_MANAGER.relative_to(ROOT)),
            "line": line_number(state, "(void)confidence; // reserved for future payload packing"),
            "observed": "MCPL reply helper discards confidence.",
            "blocks": "confidence-gated learning over MCPL",
            "required_repair": "Define and test a confidence-bearing MCPL reply payload/packet sequence.",
            "present": "(void)confidence" in mcpl_reply_section,
        },
        {
            "finding_id": "mcpl_receive_hardcodes_confidence",
            "file": str(STATE_MANAGER.relative_to(ROOT)),
            "line": line_number(state, "cra_state_lookup_receive(seq_id, value, FP_ONE, 1);"),
            "observed": "MCPL receive path hardcodes confidence=FP_ONE and hit=1.",
            "blocks": "self-evaluation/confidence-gated v2.1 transfer over MCPL",
            "required_repair": "Decode confidence/hit/status in MCPL receive and preserve 4.29d zero/half-confidence controls.",
            "present": "cra_state_lookup_receive(seq_id, value, FP_ONE, 1);" in mcpl_receive_section,
        },
        {
            "finding_id": "mcpl_key_lacks_shard_identity",
            "file": str(CONFIG_H.relative_to(ROOT)),
            "line": key_layout_line,
            "observed": "MCPL key layout has app_id, msg_type, lookup_type, and seq_id, but no shard/group field.",
            "blocks": "replicated 8/12/16-core shard stress and multi-chip routing",
            "required_repair": "Add shard/group identity or equivalent directed-routing semantics with local cross-talk tests.",
            "present": "shard" not in config.lower().split("bit layout:", 1)[-1].split("#define EXTRACT_MCPL_MSG_TYPE", 1)[0],
        },
        {
            "finding_id": "mcpl_dest_core_reserved",
            "file": str(STATE_MANAGER.relative_to(ROOT)),
            "line": line_number(state, "(void)dest_core;  // reserved for future routing-table-directed sends"),
            "observed": "MCPL send helpers reserve/ignore dest_core.",
            "blocks": "directed replicated-shard lookup routing",
            "required_repair": "Either use shard-aware key/routing masks or implement measured directed-core routing semantics.",
            "present": "(void)dest_core;" in mcpl_request_section and "(void)dest_core;" in mcpl_reply_section,
        },
    ]
    return findings


def build_results() -> dict[str, Any]:
    tier4_32a = read_json(TIER4_32A_RESULTS)
    findings = source_findings()
    finding_map = {row["finding_id"]: row for row in findings}

    required_findings_present = all(row["present"] for row in findings)
    criteria = [
        criterion("Tier 4.32a prerequisite passed", tier4_32a.get("status"), "== pass", tier4_32a.get("status") == "pass"),
        criterion("confidence lookup SDP fallback found", finding_map["confidence_lookup_uses_sdp"]["present"], "== True", finding_map["confidence_lookup_uses_sdp"]["present"]),
        criterion("MCPL reply drops confidence found", finding_map["mcpl_reply_drops_confidence"]["present"], "== True", finding_map["mcpl_reply_drops_confidence"]["present"]),
        criterion("MCPL receive hardcodes confidence found", finding_map["mcpl_receive_hardcodes_confidence"]["present"], "== True", finding_map["mcpl_receive_hardcodes_confidence"]["present"]),
        criterion("MCPL key lacks shard identity found", finding_map["mcpl_key_lacks_shard_identity"]["present"], "== True", finding_map["mcpl_key_lacks_shard_identity"]["present"]),
        criterion("MCPL dest_core reserved/ignored found", finding_map["mcpl_dest_core_reserved"]["present"], "== True", finding_map["mcpl_dest_core_reserved"]["present"]),
        criterion("all protocol blockers classified", len(findings), "== 5", len(findings) == 5 and required_findings_present),
        criterion("MCPL-first 4.32a-hw package blocked", "blocked", "== blocked", True),
        criterion("Tier 4.32a-r1 protocol repair required next", "required_next", "== required_next", True),
        criterion("native scale baseline freeze remains blocked", "not_authorized", "== not_authorized", True),
    ]

    final_decision = {
        "status": "pass" if all(item.passed for item in criteria) else "fail",
        "tier4_32a_hw_mcpl_first": "blocked_until_4_32a_r1_protocol_repair",
        "tier4_32a_sdp_debug_hw": "allowed_only_if_relabelled_transitional_sdp_debug_not_scale_evidence",
        "tier4_32a_r1": "required_next",
        "tier4_32a_hw_replicated": "blocked_until_confidence_and_shard_aware_mcpl_passes",
        "tier4_32b": "blocked_until_confidence_and_shard_aware_4_32a_hardware_stress_passes",
        "native_scale_baseline_freeze": "not_authorized",
        "claim_boundary": CLAIM_BOUNDARY,
    }

    return {
        "tier": "4.32a-r0",
        "tier_name": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "status": final_decision["status"],
        "claim_boundary": CLAIM_BOUNDARY,
        "criteria": [asdict(item) for item in criteria],
        "criteria_passed": sum(1 for item in criteria if item.passed),
        "criteria_total": len(criteria),
        "failed_criteria": [item.name for item in criteria if not item.passed],
        "source_findings": findings,
        "final_decision": final_decision,
        "required_next_gate": {
            "tier": "Tier 4.32a-r1",
            "name": "Confidence-bearing shard-aware MCPL lookup repair",
            "required_repairs": [
                "MCPL reply payload/sequence carries value, confidence, hit/status, and lookup type.",
                "MCPL receive path no longer hardcodes confidence=FP_ONE.",
                "4.29d full/zero/zero-context/half-confidence controls pass over the repaired path.",
                "MCPL key/routing carries shard/group identity or equivalent directed semantics.",
                "Local C tests prove two independent shards can issue identical lookup types and sequence ranges without cross-talk.",
            ],
            "blocked_until_passes": [
                "MCPL-first Tier 4.32a-hw hardware scale stress",
                "replicated 8/12/16-core hardware stress",
                "Tier 4.32b static reef partitioning",
                "multi-chip scaling",
                "CRA_NATIVE_SCALE_BASELINE_v0.5",
            ],
        },
    }


def write_report(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Tier 4.32a-r0 Protocol Truth Audit",
        "",
        f"- Generated: `{result['generated_at_utc']}`",
        f"- Status: **{result['status'].upper()}**",
        f"- Runner revision: `{result['runner_revision']}`",
        "",
        "## Claim Boundary",
        "",
        result["claim_boundary"],
        "",
        "## Summary",
        "",
        "- The planned MCPL-first 4.32a-hw package is blocked until Tier 4.32a-r1 repairs confidence-bearing and shard-aware MCPL lookup.",
        "- A transitional SDP debug run may still be useful, but it must be labelled as SDP debug evidence, not MCPL-first scale evidence.",
        "- No native-scale baseline freeze is authorized.",
        "",
        "## Criteria",
        "",
        "| Criterion | Value | Rule | Pass |",
        "| --- | --- | --- | --- |",
    ]
    for item in result["criteria"]:
        lines.append(f"| {item['name']} | `{item['value']}` | {item['rule']} | {'yes' if item['passed'] else 'no'} |")
    lines.extend(["", "## Source Findings", "", "| Finding | File | Line | Blocks |", "| --- | --- | --- | --- |"])
    for item in result["source_findings"]:
        lines.append(f"| `{item['finding_id']}` | `{item['file']}` | `{item.get('line')}` | {item['blocks']} |")
    lines.extend(["", "## Final Decision", ""])
    for key, value in result["final_decision"].items():
        if key != "claim_boundary":
            lines.append(f"- `{key}`: `{value}`")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=TIER)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    result = build_results()

    results_path = output_dir / "tier4_32a_r0_results.json"
    report_path = output_dir / "tier4_32a_r0_report.md"
    criteria_path = output_dir / "tier4_32a_r0_criteria.csv"
    findings_path = output_dir / "tier4_32a_r0_source_findings.csv"
    decision_path = output_dir / "tier4_32a_r0_final_decision.json"

    result["artifacts"] = {
        "results_json": str(results_path),
        "report_md": str(report_path),
        "criteria_csv": str(criteria_path),
        "source_findings_csv": str(findings_path),
        "final_decision_json": str(decision_path),
    }

    write_json(results_path, result)
    write_report(report_path, result)
    write_csv(criteria_path, result["criteria"])
    write_csv(findings_path, result["source_findings"])
    write_json(decision_path, result["final_decision"])
    write_json(LATEST_MANIFEST, result)
    print(json.dumps({"status": result["status"], "output_dir": str(output_dir), "results": str(results_path)}, indent=2))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
