#!/usr/bin/env python3
"""Tier 4.32d-r1 inter-chip MCPL route repair/local QA.

This gate repairs the source blocker found by Tier 4.32d-r0. It proves locally
that the custom runtime can install explicit chip-link route entries for the
first two-chip split-role single-shard MCPL lookup smoke:

* learning chip: outbound lookup-request routes to an inter-chip link
* state chip: local request delivery plus outbound reply routes to a return link

The gate does not prepare or run an EBRAINS package. It only authorizes the
next hardware-smoke packaging step if source, route contracts, and regression
tests are clean.
"""
from __future__ import annotations

import csv
import json
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"
RUNTIME = ROOT / "coral_reef_spinnaker" / "spinnaker_runtime"
RUNTIME_SRC = RUNTIME / "src"
RUNTIME_TESTS = RUNTIME / "tests"
EBRAINS = ROOT / "ebrains_jobs"

TIER = "Tier 4.32d-r1 - Inter-Chip MCPL Route Repair Local QA"
RUNNER_REVISION = "tier4_32d_r1_interchip_route_repair_local_qa_20260507_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier4_32d_r1_20260507_interchip_route_repair_local_qa"
LATEST_MANIFEST = CONTROLLED / "tier4_32d_r1_latest_manifest.json"
TIER4_32D_R0_RESULTS = CONTROLLED / "tier4_32d_r0_20260507_interchip_route_source_audit" / "tier4_32d_r0_results.json"

CLAIM_BOUNDARY = (
    "Tier 4.32d-r1 is local source/runtime QA for explicit inter-chip MCPL "
    "route entries. It is not a SpiNNaker hardware run, not an EBRAINS package, "
    "not multi-chip execution evidence, not learning-scale evidence, not "
    "speedup evidence, not benchmark superiority, and not a native-scale "
    "baseline freeze."
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


def run_command(args: list[str], cwd: Path) -> dict[str, Any]:
    proc = subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=False)
    return {
        "command": " ".join(args),
        "cwd": str(cwd),
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def source_findings(state_text: str, make_text: str, stub_text: str) -> list[SourceFinding]:
    return [
        SourceFinding(
            "request_link_macro_present",
            rel(RUNTIME_SRC / "state_manager.c"),
            str("CRA_MCPL_INTERCHIP_REQUEST_LINK_ROUTE" in state_text),
            "Learning-core builds can install outbound request routes to an explicit chip link.",
            "keep",
        ),
        SourceFinding(
            "reply_link_macro_present",
            rel(RUNTIME_SRC / "state_manager.c"),
            str("CRA_MCPL_INTERCHIP_REPLY_LINK_ROUTE" in state_text),
            "State-core builds can install outbound reply routes to an explicit chip link.",
            "keep",
        ),
        SourceFinding(
            "learning_request_routes_specific",
            rel(RUNTIME_SRC / "state_manager.c"),
            "LOOKUP_TYPE_CONTEXT/ROUTE/MEMORY request routes installed under request-link macro",
            "Source-chip learning profile can route all three lookup request types off chip.",
            "keep",
        ),
        SourceFinding(
            "state_reply_routes_specific",
            rel(RUNTIME_SRC / "state_manager.c"),
            "VALUE/META reply routes installed per state profile lookup type under reply-link macro",
            "Remote state profiles avoid broad duplicate reply routes while returning value/meta packets.",
            "keep",
        ),
        SourceFinding(
            "route_stub_captures_rtr_mc_set",
            rel(RUNTIME / "stubs" / "sark.h"),
            str("g_test_rtr_routes" in stub_text and "rtr_mc_set" in stub_text),
            "Host tests can inspect programmed key/mask/route entries instead of trusting comments.",
            "keep",
        ),
        SourceFinding(
            "make_target_present",
            rel(RUNTIME / "Makefile"),
            str("test-mcpl-interchip-route-contract" in make_text),
            "The route contract is callable by CI/local validation.",
            "keep",
        ),
    ]


def write_report(path: Path, result: dict[str, Any]) -> None:
    summary = result["summary"]
    lines = [
        "# Tier 4.32d-r1 Inter-Chip MCPL Route Repair Local QA",
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
        "## Result",
        "",
        f"- Tier 4.32d-r0 prerequisite: `{summary['tier4_32d_r0_status']}`",
        f"- Route contract test: `{summary['route_contract_returncode']}`",
        f"- Existing MCPL lookup regression: `{summary['lookup_contract_returncode']}`",
        f"- Existing four-core MCPL regression: `{summary['four_core_mcpl_returncode']}`",
        f"- EBRAINS package authorized next: `{summary['ebrains_package_authorized_next']}`",
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
        "## Criteria",
        "",
        "| Criterion | Value | Rule | Pass | Note |",
        "| --- | --- | --- | --- | --- |",
    ])
    for item in result["criteria"]:
        lines.append(f"| {item['name']} | `{item['value']}` | {item['rule']} | {'yes' if item['passed'] else 'no'} | {item.get('note', '')} |")
    lines.extend([
        "",
        "## Test Commands",
        "",
    ])
    for item in result["test_commands"]:
        lines.append(f"- `{item['command']}` -> `{item['returncode']}`")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    state_text = (RUNTIME_SRC / "state_manager.c").read_text(encoding="utf-8")
    make_text = (RUNTIME / "Makefile").read_text(encoding="utf-8")
    stub_text = (RUNTIME / "stubs" / "sark.h").read_text(encoding="utf-8")
    test_text = (RUNTIME_TESTS / "test_mcpl_interchip_route_contract.c").read_text(encoding="utf-8")
    tier4_32d_r0 = read_json(TIER4_32D_R0_RESULTS) if TIER4_32D_R0_RESULTS.exists() else {}
    tier4_32d_r0_status = str(tier4_32d_r0.get("status", "missing")).lower()

    commands = [
        run_command(["make", "test-mcpl-interchip-route-contract"], RUNTIME),
        run_command(["make", "test-mcpl-lookup-contract"], RUNTIME),
        run_command(["make", "test-four-core-mcpl-local"], RUNTIME),
    ]

    route_cmd, lookup_cmd, four_core_cmd = commands
    for index, item in enumerate(commands, start=1):
        (output_dir / f"tier4_32d_r1_test_command_{index}.stdout.txt").write_text(item["stdout"], encoding="utf-8")
        (output_dir / f"tier4_32d_r1_test_command_{index}.stderr.txt").write_text(item["stderr"], encoding="utf-8")

    findings = [asdict(item) for item in source_findings(state_text, make_text, stub_text)]
    upload_folder_exists = (EBRAINS / "cra_432d").exists()
    source_has_request_link = "CRA_MCPL_INTERCHIP_REQUEST_LINK_ROUTE" in state_text
    source_has_reply_link = "CRA_MCPL_INTERCHIP_REPLY_LINK_ROUTE" in state_text
    source_has_request_types = all(token in state_text for token in [
        "MCPL_MSG_LOOKUP_REQUEST, LOOKUP_TYPE_CONTEXT",
        "MCPL_MSG_LOOKUP_REQUEST, LOOKUP_TYPE_ROUTE",
        "MCPL_MSG_LOOKUP_REQUEST, LOOKUP_TYPE_MEMORY",
    ])
    source_has_reply_types = all(token in state_text for token in [
        "MCPL_MSG_LOOKUP_REPLY_VALUE, lookup_type",
        "MCPL_MSG_LOOKUP_REPLY_META, lookup_type",
    ])
    test_asserts_learning = "learning core installs outbound request link routes" in test_text
    test_asserts_state = "state core installs local request route plus outbound reply link routes" in test_text

    criteria = [
        criterion("Tier 4.32d-r0 prerequisite passed", tier4_32d_r0_status, "== pass", tier4_32d_r0_status == "pass"),
        criterion("source has request link-route macro", source_has_request_link, "== true", source_has_request_link),
        criterion("source has reply link-route macro", source_has_reply_link, "== true", source_has_reply_link),
        criterion("learning source installs all three request lookup routes", source_has_request_types, "== true", source_has_request_types),
        criterion("state source installs value/meta reply routes", source_has_reply_types, "== true", source_has_reply_types),
        criterion("route stub records rtr_mc_set key/mask/route", "g_test_rtr_routes" in stub_text, "== true", "g_test_rtr_routes" in stub_text),
        criterion("Makefile exposes inter-chip route contract target", "test-mcpl-interchip-route-contract" in make_text, "== true", "test-mcpl-interchip-route-contract" in make_text),
        criterion("route contract tests learning and state sides", test_asserts_learning and test_asserts_state, "== true", test_asserts_learning and test_asserts_state),
        criterion("inter-chip route contract test passes", route_cmd["returncode"], "== 0", route_cmd["returncode"] == 0),
        criterion("existing MCPL lookup contract still passes", lookup_cmd["returncode"], "== 0", lookup_cmd["returncode"] == 0),
        criterion("existing four-core MCPL local regression still passes", four_core_cmd["returncode"], "== 0", four_core_cmd["returncode"] == 0),
        criterion("4.32d upload folder not prepared by local QA", str(EBRAINS / "cra_432d"), "must not exist", not upload_folder_exists),
        criterion("next hardware smoke is authorized only after this local pass", "Tier 4.32d", "authorized_next_if_all_pass", True),
        criterion("no baseline freeze authorized", "blocked", "== blocked", True),
    ]
    passed = sum(1 for item in criteria if item.passed)
    status = "pass" if passed == len(criteria) else "fail"
    package_authorized = status == "pass" and not upload_folder_exists
    summary = {
        "tier4_32d_r0_status": tier4_32d_r0_status,
        "route_contract_returncode": route_cmd["returncode"],
        "lookup_contract_returncode": lookup_cmd["returncode"],
        "four_core_mcpl_returncode": four_core_cmd["returncode"],
        "ebrains_package_authorized_next": package_authorized,
        "decision": "authorize_4_32d_package_next" if package_authorized else "keep_4_32d_package_blocked",
        "recommended_next_step": "Tier 4.32d two-chip split-role single-shard MCPL lookup hardware smoke package/run." if package_authorized else "Repair route source/local tests before any EBRAINS package.",
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
        "test_commands": commands,
        "artifacts": {},
    }
    result_path = output_dir / "tier4_32d_r1_results.json"
    report_path = output_dir / "tier4_32d_r1_report.md"
    criteria_path = output_dir / "tier4_32d_r1_criteria.csv"
    findings_path = output_dir / "tier4_32d_r1_source_findings.csv"
    commands_path = output_dir / "tier4_32d_r1_test_commands.csv"
    result["artifacts"] = {
        "results_json": str(result_path),
        "report_md": str(report_path),
        "criteria_csv": str(criteria_path),
        "source_findings_csv": str(findings_path),
        "test_commands_csv": str(commands_path),
        "route_contract_stdout": str(output_dir / "tier4_32d_r1_test_command_1.stdout.txt"),
        "lookup_contract_stdout": str(output_dir / "tier4_32d_r1_test_command_2.stdout.txt"),
        "four_core_mcpl_stdout": str(output_dir / "tier4_32d_r1_test_command_3.stdout.txt"),
    }
    write_json(result_path, result)
    write_report(report_path, result)
    write_csv(criteria_path, result["criteria"])
    write_csv(findings_path, result["source_findings"])
    write_csv(commands_path, result["test_commands"])
    write_json(LATEST_MANIFEST, {
        "tier": TIER,
        "status": status,
        "generated_at_utc": result["generated_at_utc"],
        "manifest": str(result_path),
        "claim": "Latest Tier 4.32d-r1 inter-chip MCPL route repair/local QA.",
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
