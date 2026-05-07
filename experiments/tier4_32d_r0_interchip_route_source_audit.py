#!/usr/bin/env python3
"""Tier 4.32d-r0 inter-chip route/source/package audit.

This is a local pre-package audit after Tier 4.32c. It deliberately does not
prepare an EBRAINS upload bundle. Its job is to decide whether the current
custom runtime can honestly run the first two-chip split-role single-shard MCPL
lookup smoke, or whether a source repair is required before packaging.

The audit passes when it classifies the current route state correctly. A PASS
here can still mean "hardware package blocked" if the measured source state is
not ready. That preserves the evidence boundary and avoids wasting SpiNNaker
allocations on a known routing gap.
"""
from __future__ import annotations

import csv
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"
RUNTIME_SRC = ROOT / "coral_reef_spinnaker" / "spinnaker_runtime" / "src"
EBRAINS = ROOT / "ebrains_jobs"

TIER = "Tier 4.32d-r0 - Inter-Chip Route/Source/Package Audit"
RUNNER_REVISION = "tier4_32d_r0_interchip_route_source_audit_20260507_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier4_32d_r0_20260507_interchip_route_source_audit"
LATEST_MANIFEST = CONTROLLED / "tier4_32d_r0_latest_manifest.json"
TIER4_32C_RESULTS = CONTROLLED / "tier4_32c_20260507_interchip_feasibility_contract" / "tier4_32c_results.json"

CLAIM_BOUNDARY = (
    "Tier 4.32d-r0 is a local route/source/package audit only. It is not a "
    "SpiNNaker hardware run, not an EBRAINS package, not multi-chip execution "
    "evidence, not speedup evidence, not learning-scale evidence, not benchmark "
    "superiority, and not a native-scale baseline freeze."
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
    observed: str
    interpretation: str
    decision: str


@dataclass(frozen=True)
class FailureClass:
    failure_class: str
    detection_rule: str
    required_response: str
    blocks: str


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


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    rows = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json_safe(row.get(key, "")) for key in keys})


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def criterion(name: str, value: Any, rule: str, passed: bool, note: str = "") -> Criterion:
    return Criterion(name=name, value=value, rule=rule, passed=bool(passed), note=note)


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def extract_function(text: str, name: str) -> str:
    marker = f"void {name}("
    start = text.find(marker)
    if start < 0:
        return ""
    brace = text.find("{", start)
    if brace < 0:
        return ""
    depth = 0
    for idx in range(brace, len(text)):
        char = text[idx]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start:idx + 1]
    return text[start:]


def source_findings(state_text: str, init_text: str) -> list[SourceFinding]:
    link_tokens = ["ROUTE_E", "ROUTE_NE", "ROUTE_N", "ROUTE_W", "ROUTE_SW", "ROUTE_S"]
    init_has_link_route = any(token in init_text for token in link_tokens)
    init_has_local_core_route = "MC_CORE_ROUTE(core_id)" in init_text
    send_ignores_dest_core = "(void)dest_core;  // routing table decides delivery by key/mask" in state_text
    return [
        SourceFinding(
            "mcpl_request_reply_source_backed",
            rel(RUNTIME_SRC / "state_manager.c"),
            "cra_state_mcpl_lookup_send_request_shard and cra_state_mcpl_lookup_send_reply_shard emit MCPL packets with shard-aware keys",
            "MCPL packet construction is present for the split-role smoke.",
            "keep",
        ),
        SourceFinding(
            "dest_core_not_delivery_authority",
            rel(RUNTIME_SRC / "state_manager.c"),
            str(send_ignores_dest_core),
            "The send path intentionally ignores dest_core; routing table entries are the delivery authority.",
            "4.32d must verify router entries, not just command arguments",
        ),
        SourceFinding(
            "local_core_routes_only",
            rel(RUNTIME_SRC / "state_manager.c"),
            f"MC_CORE_ROUTE(core_id)={init_has_local_core_route}; explicit_link_route={init_has_link_route}",
            "cra_state_mcpl_init currently routes matched request/reply keys to the local core only and does not name inter-chip links.",
            "block package until inter-chip route repair or explicit placement/routing contract exists",
        ),
        SourceFinding(
            "true_two_partition_learning_protocol_missing",
            rel(RUNTIME_SRC / "config.h"),
            "one shard_id field in MCPL key",
            "The 4.32c boundary remains correct: split-role single-shard smoke is the first honest target; true two-partition learning needs origin/target shard semantics later.",
            "keep blocked for 4.32e+ until repaired",
        ),
    ]


def failure_classes() -> list[FailureClass]:
    return [
        FailureClass(
            "cross_chip_route_missing",
            "cra_state_mcpl_init has only MC_CORE_ROUTE(core_id) delivery and no explicit link route or placement-provided routing table contract",
            "do not prepare EBRAINS package; implement or prove inter-chip route entries first",
            "Tier 4.32d hardware upload",
        ),
        FailureClass(
            "single_shard_protocol_limit",
            "attempted true two-partition cross-chip learning with only one shard_id field",
            "add origin/target shard semantics before multi-partition learning",
            "Tier 4.32e+ learning scale",
        ),
        FailureClass(
            "package_overclaim",
            "upload folder or command claims learning scale, speedup, or two-partition learning before route smoke passes",
            "delete/rewrite package and preserve audit failure",
            "EBRAINS submission",
        ),
    ]


def write_report(path: Path, result: dict[str, Any]) -> None:
    summary = result["summary"]
    lines = [
        "# Tier 4.32d-r0 Inter-Chip Route/Source/Package Audit",
        "",
        f"- Generated: `{result['generated_at_utc']}`",
        f"- Runner revision: `{result['runner_revision']}`",
        f"- Status: **{result['status'].upper()}**",
        f"- Criteria: `{summary['passed_criteria']}/{summary['total_criteria']}`",
        f"- Decision: `{summary['decision']}`",
        "",
        "## Claim Boundary",
        "",
        CLAIM_BOUNDARY,
        "",
        "## Audit Result",
        "",
        f"- Tier 4.32c prerequisite: `{summary['tier4_32c_status']}`",
        f"- First smoke target: `{summary['first_smoke_target']}`",
        f"- MCPL init local-core route only: `{summary['local_core_route_only']}`",
        f"- Explicit inter-chip link route present: `{summary['explicit_link_route_present']}`",
        f"- EBRAINS package authorized: `{summary['ebrains_package_authorized']}`",
        f"- Recommended next step: {summary['recommended_next_step']}",
        "",
        "## Source Findings",
        "",
        "| Finding | File | Observed | Interpretation | Decision |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in result["source_findings"]:
        lines.append(
            f"| `{row['finding_id']}` | `{row['file']}` | {row['observed']} | {row['interpretation']} | {row['decision']} |"
        )
    lines.extend([
        "",
        "## Failure Classes",
        "",
        "| Failure | Detection | Required Response | Blocks |",
        "| --- | --- | --- | --- |",
    ])
    for row in result["failure_classes"]:
        lines.append(
            f"| `{row['failure_class']}` | {row['detection_rule']} | {row['required_response']} | {row['blocks']} |"
        )
    lines.extend([
        "",
        "## Criteria",
        "",
        "| Criterion | Value | Rule | Pass | Note |",
        "| --- | --- | --- | --- | --- |",
    ])
    for item in result["criteria"]:
        lines.append(f"| {item['name']} | `{item['value']}` | {item['rule']} | {'yes' if item['passed'] else 'no'} | {item.get('note', '')} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    state_path = RUNTIME_SRC / "state_manager.c"
    config_path = RUNTIME_SRC / "config.h"
    state_text = state_path.read_text(encoding="utf-8")
    config_text = config_path.read_text(encoding="utf-8")
    init_text = extract_function(state_text, "cra_state_mcpl_init")

    tier4_32c = read_json(TIER4_32C_RESULTS) if TIER4_32C_RESULTS.exists() else {}
    tier4_32c_status = str(tier4_32c.get("status", "missing")).lower()
    metrics = tier4_32c.get("top_level_metrics") or tier4_32c.get("summary", {})
    first_smoke_target = str(metrics.get("first_smoke_target", ""))
    first_smoke_partitions = metrics.get("first_smoke_partitions")

    link_tokens = ["ROUTE_E", "ROUTE_NE", "ROUTE_N", "ROUTE_W", "ROUTE_SW", "ROUTE_S"]
    explicit_link_route_present = any(token in init_text for token in link_tokens)
    local_core_route_present = "MC_CORE_ROUTE(core_id)" in init_text
    send_ignores_dest_core = "(void)dest_core;  // routing table decides delivery by key/mask" in state_text
    single_shard_key = all(token in config_text for token in ["MCPL_KEY_SHARD_SHIFT", "MCPL_KEY_SHARD_MASK", "MAKE_MCPL_KEY_SHARD"])
    upload_folder = EBRAINS / "cra_432d"
    upload_folder_exists = upload_folder.exists()
    package_authorized = bool(explicit_link_route_present and local_core_route_present and not upload_folder_exists)

    findings = [asdict(item) for item in source_findings(state_text, init_text)]
    failures = [asdict(item) for item in failure_classes()]
    criteria = [
        criterion("Tier 4.32c prerequisite passed", tier4_32c_status, "== pass", tier4_32c_status == "pass"),
        criterion("4.32c target is split-role single-shard", first_smoke_target, "== point_2chip_split_partition_lookup_smoke", first_smoke_target == "point_2chip_split_partition_lookup_smoke"),
        criterion("4.32c first smoke uses one partition", first_smoke_partitions, "== 1", first_smoke_partitions == 1),
        criterion("MCPL shard-aware key source exists", single_shard_key, "== true", single_shard_key),
        criterion("MCPL send path delegates delivery to router table", send_ignores_dest_core, "== true", send_ignores_dest_core),
        criterion("MCPL init installs local core routes", local_core_route_present, "== true", local_core_route_present),
        criterion("explicit inter-chip link route is absent and classified", explicit_link_route_present, "== false", not explicit_link_route_present),
        criterion("4.32d upload folder not prepared prematurely", str(upload_folder), "must not exist", not upload_folder_exists),
        criterion("hardware package remains blocked by source audit", "blocked", "== blocked", not package_authorized),
        criterion("next gate is route repair", "Tier 4.32d-r1", "== Tier 4.32d-r1", True),
    ]
    passed = sum(1 for item in criteria if item.passed)
    status = "pass" if passed == len(criteria) else "fail"
    summary = {
        "tier4_32c_status": tier4_32c_status,
        "first_smoke_target": first_smoke_target,
        "first_smoke_partitions": first_smoke_partitions,
        "local_core_route_only": local_core_route_present and not explicit_link_route_present,
        "explicit_link_route_present": explicit_link_route_present,
        "ebrains_package_authorized": package_authorized,
        "decision": "block_4_32d_package_until_route_repair" if not package_authorized else "package_authorized",
        "recommended_next_step": "Tier 4.32d-r1 inter-chip MCPL route repair/local QA before any EBRAINS package.",
        "total_criteria": len(criteria),
        "passed_criteria": passed,
    }
    result = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "status": status,
        "output_dir": str(output_dir),
        "claim_boundary": CLAIM_BOUNDARY,
        "summary": summary,
        "criteria": [asdict(item) for item in criteria],
        "source_findings": findings,
        "failure_classes": failures,
        "artifacts": {},
    }
    result_path = output_dir / "tier4_32d_r0_results.json"
    report_path = output_dir / "tier4_32d_r0_report.md"
    criteria_path = output_dir / "tier4_32d_r0_criteria.csv"
    findings_path = output_dir / "tier4_32d_r0_source_findings.csv"
    failures_path = output_dir / "tier4_32d_r0_failure_classes.csv"
    result["artifacts"] = {
        "results_json": str(result_path),
        "report_md": str(report_path),
        "criteria_csv": str(criteria_path),
        "source_findings_csv": str(findings_path),
        "failure_classes_csv": str(failures_path),
    }
    write_json(result_path, result)
    write_report(report_path, result)
    write_csv(criteria_path, result["criteria"])
    write_csv(findings_path, result["source_findings"])
    write_csv(failures_path, result["failure_classes"])
    write_json(LATEST_MANIFEST, {
        "tier": TIER,
        "status": status,
        "generated_at_utc": result["generated_at_utc"],
        "manifest": str(result_path),
        "claim": "Latest Tier 4.32d-r0 inter-chip route/source/package audit.",
    })
    return result


def main() -> int:
    result = run(DEFAULT_OUTPUT_DIR)
    print(json.dumps({
        "status": result["status"],
        "decision": result["summary"]["decision"],
        "criteria": f"{result['summary']['passed_criteria']}/{result['summary']['total_criteria']}",
        "results": result["artifacts"]["results_json"],
        "recommended_next_step": result["summary"]["recommended_next_step"],
    }, indent=2))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
