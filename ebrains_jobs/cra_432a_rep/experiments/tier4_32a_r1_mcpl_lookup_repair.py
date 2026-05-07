#!/usr/bin/env python3
"""Tier 4.32a-r1 confidence-bearing shard-aware MCPL lookup repair.

This local source/runtime gate repairs the blocker found by Tier 4.32a-r0:
MCPL lookup traffic must carry value, confidence, hit/status, lookup type, and
shard identity before MCPL-first hardware scale stress can be packaged.

PASS is local C/runtime evidence only. It is not EBRAINS hardware evidence, not
speedup evidence, not replicated-shard scale proof, and not a baseline freeze.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"
RUNTIME = ROOT / "coral_reef_spinnaker" / "spinnaker_runtime"
SRC = RUNTIME / "src"

TIER = "Tier 4.32a-r1 - Confidence-Bearing Shard-Aware MCPL Lookup Repair"
RUNNER_REVISION = "tier4_32a_r1_mcpl_lookup_repair_20260506_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier4_32a_r1_20260506_mcpl_lookup_repair"
LATEST_MANIFEST = CONTROLLED / "tier4_32a_r1_latest_manifest.json"

TIER4_32A_R0_RESULTS = CONTROLLED / "tier4_32a_r0_20260506_protocol_truth_audit" / "tier4_32a_r0_results.json"

CLAIM_BOUNDARY = (
    "Tier 4.32a-r1 is local source/runtime evidence that the custom runtime now "
    "has a confidence-bearing, shard-aware MCPL lookup path with behavior-backed "
    "confidence controls. It is not EBRAINS hardware evidence, not speedup "
    "evidence, not replicated-shard scale proof, not multi-chip proof, not static "
    "reef partitioning, and not a baseline freeze."
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
        writer = csv.DictWriter(handle, fieldnames=keys, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows([{key: json_safe(row.get(key, "")) for key in keys} for row in rows])


def read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def criterion(name: str, value: Any, rule: str, passed: bool, note: str = "") -> Criterion:
    return Criterion(name=name, value=value, rule=rule, passed=bool(passed), note=note)


def run_command(command: list[str]) -> dict[str, Any]:
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def source_check(path: Path, token: str, purpose: str) -> SourceCheck:
    text = path.read_text(encoding="utf-8")
    return SourceCheck(
        file=str(path.relative_to(ROOT)),
        token=token,
        present=token in text,
        purpose=purpose,
    )


def build_results() -> dict[str, Any]:
    r0 = read_json(TIER4_32A_R0_RESULTS)
    config_h = SRC / "config.h"
    state_h = SRC / "state_manager.h"
    state_c = SRC / "state_manager.c"
    makefile = RUNTIME / "Makefile"
    mcpl_contract_test = RUNTIME / "tests" / "test_mcpl_lookup_contract.c"
    mcpl_four_core_test = RUNTIME / "tests" / "test_four_core_mcpl_local.c"

    checks = [
        source_check(config_h, "shard_id (4) | seq_id (12)", "MCPL key has explicit shard identity"),
        source_check(config_h, "MCPL_MSG_LOOKUP_REPLY_VALUE", "value reply packet type exists"),
        source_check(config_h, "MCPL_MSG_LOOKUP_REPLY_META", "confidence/meta reply packet type exists"),
        source_check(config_h, "PACK_MCPL_LOOKUP_META", "hit/status/confidence packing is centralized"),
        source_check(config_h, "EXTRACT_MCPL_SHARD_ID", "receiver can decode shard identity"),
        source_check(state_h, "cra_state_lookup_send_shard", "learning lookup table can track shard-specific pending entries"),
        source_check(state_h, "cra_state_lookup_get_result_shard", "tests can read shard-specific results without ambiguity"),
        source_check(state_c, "#ifdef CRA_USE_MCPL_LOOKUP", "MCPL path is compile-time selectable instead of #if 0 dead code"),
        source_check(state_c, "cra_state_mcpl_lookup_send_reply_shard", "state core can send value/meta replies with shard identity"),
        source_check(state_c, "_lookup_receive_mcpl_value", "learning core accepts value packet"),
        source_check(state_c, "_lookup_receive_mcpl_meta", "learning core accepts confidence/meta packet"),
        source_check(state_c, "MCPL_MSG_LOOKUP_REPLY_META", "learning core decodes meta reply packet"),
        source_check(state_c, "CRA_MCPL_SHARD_ID", "runtime can compile shard-specific images"),
        source_check(makefile, "MCPL_SHARD_ID ?= 0", "Makefile exposes MCPL shard id for hardware builds"),
        source_check(makefile, "test-mcpl-lookup-contract", "local MCPL protocol contract target exists"),
        source_check(makefile, "test-four-core-mcpl-local", "local MCPL behavior target exists"),
        source_check(mcpl_contract_test, "shard_id prevents identical seq/type cross-talk", "cross-talk regression is tested"),
        source_check(mcpl_contract_test, "wrong-shard packets cannot complete pending lookup", "wrong-shard negative control is tested"),
        source_check(mcpl_four_core_test, "MCPL zero-confidence path blocks learning", "zero-confidence behavior passes through MCPL"),
        source_check(mcpl_four_core_test, "MCPL half-confidence path scales learning", "half-confidence behavior passes through MCPL"),
    ]

    commands = [
        run_command(["make", "-C", str(RUNTIME.relative_to(ROOT)), "test-mcpl-lookup-contract"]),
        run_command(["make", "-C", str(RUNTIME.relative_to(ROOT)), "test-four-core-mcpl-local"]),
        run_command(["make", "-C", str(RUNTIME.relative_to(ROOT)), "test-mcpl-feasibility"]),
        run_command(["make", "-C", str(RUNTIME.relative_to(ROOT)), "test-four-core-local"]),
        run_command(["make", "-C", str(RUNTIME.relative_to(ROOT)), "test-four-core-48event"]),
        run_command(["make", "-C", str(RUNTIME.relative_to(ROOT)), "test-profiles"]),
        run_command(["make", "-C", str(RUNTIME.relative_to(ROOT)), "test-lifecycle-split"]),
    ]
    command_passes = {" ".join(item["command"]): item["returncode"] == 0 for item in commands}
    command_log = "\n\n".join(
        "COMMAND: "
        + " ".join(item["command"])
        + f"\nRETURNCODE: {item['returncode']}\nSTDOUT:\n{item['stdout']}\nSTDERR:\n{item['stderr']}"
        for item in commands
    )

    state_text = state_c.read_text(encoding="utf-8")
    request_dead_code_removed = "#if 0\n    cra_state_mcpl_lookup_send_request" not in state_text
    hardcoded_conf_removed = "cra_state_lookup_receive(seq_id, value, FP_ONE, 1);" not in state_text
    confidence_ignored_removed = "(void)confidence; // reserved for future payload packing" not in state_text

    criteria = [
        criterion("Tier 4.32a-r0 prerequisite passed", r0.get("status"), "== pass", r0.get("status") == "pass"),
        criterion("source protocol tokens present", [asdict(item) for item in checks], "all source checks present", all(item.present for item in checks)),
        criterion("request MCPL dead-code gate removed", request_dead_code_removed, "no #if 0 around MCPL request path", request_dead_code_removed),
        criterion("hardcoded MCPL confidence removed", hardcoded_conf_removed, "no FP_ONE/hit=1 receive shortcut", hardcoded_conf_removed),
        criterion("confidence no longer ignored by reply helper", confidence_ignored_removed, "no reserved/ignored confidence in MCPL reply", confidence_ignored_removed),
        criterion("MCPL lookup contract test passed", command_passes.get(f"make -C {RUNTIME.relative_to(ROOT)} test-mcpl-lookup-contract"), "returncode == 0", command_passes.get(f"make -C {RUNTIME.relative_to(ROOT)} test-mcpl-lookup-contract", False)),
        criterion("MCPL four-core local behavior test passed", command_passes.get(f"make -C {RUNTIME.relative_to(ROOT)} test-four-core-mcpl-local"), "returncode == 0", command_passes.get(f"make -C {RUNTIME.relative_to(ROOT)} test-four-core-mcpl-local", False)),
        criterion("legacy MCPL feasibility test preserved", command_passes.get(f"make -C {RUNTIME.relative_to(ROOT)} test-mcpl-feasibility"), "returncode == 0", command_passes.get(f"make -C {RUNTIME.relative_to(ROOT)} test-mcpl-feasibility", False)),
        criterion("SDP four-core local reference preserved", command_passes.get(f"make -C {RUNTIME.relative_to(ROOT)} test-four-core-local"), "returncode == 0", command_passes.get(f"make -C {RUNTIME.relative_to(ROOT)} test-four-core-local", False)),
        criterion("48-event distributed reference preserved", command_passes.get(f"make -C {RUNTIME.relative_to(ROOT)} test-four-core-48event"), "returncode == 0", command_passes.get(f"make -C {RUNTIME.relative_to(ROOT)} test-four-core-48event", False)),
        criterion("profile ownership tests preserved", command_passes.get(f"make -C {RUNTIME.relative_to(ROOT)} test-profiles"), "returncode == 0", command_passes.get(f"make -C {RUNTIME.relative_to(ROOT)} test-profiles", False)),
        criterion("lifecycle split tests preserved", command_passes.get(f"make -C {RUNTIME.relative_to(ROOT)} test-lifecycle-split"), "returncode == 0", command_passes.get(f"make -C {RUNTIME.relative_to(ROOT)} test-lifecycle-split", False)),
        criterion("no EBRAINS package generated", "local-runtime-repair", "mode is local only", True),
        criterion("hardware scale stress remains separate gate", "4.32a-hw required next", "not hardware evidence", True),
    ]
    failed = [item for item in criteria if not item.passed]

    return {
        "tier": "4.32a-r1",
        "tier_name": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "status": "pass" if not failed else "fail",
        "mode": "local-runtime-repair",
        "criteria_passed": len(criteria) - len(failed),
        "criteria_total": len(criteria),
        "criteria": criteria,
        "failed_criteria": failed,
        "source_checks": checks,
        "command_results": commands,
        "command_log": command_log,
        "claim_boundary": CLAIM_BOUNDARY,
        "final_decision": {
            "status": "pass" if not failed else "fail",
            "tier4_32a_hw_mcpl_first": "authorized_next_single_shard_hardware_stress" if not failed else "blocked",
            "replicated_8_12_16_core_stress": "still_blocked_until_single_shard_hardware_stress_passes",
            "tier4_32b_static_reef_partitioning": "still_blocked_until_4_32a_hw_passes",
            "native_scale_baseline_freeze": "not_authorized",
            "claim_boundary": CLAIM_BOUNDARY,
        },
        "next_step": (
            "Prepare Tier 4.32a-hw as a single-shard MCPL-first EBRAINS hardware "
            "stress using the repaired protocol. Do not run replicated 8/12/16-core "
            "stress or freeze a native scale baseline until the single-shard hardware "
            "stress passes."
        ),
    }


def write_report(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Tier 4.32a-r1 MCPL Lookup Repair",
        "",
        f"- Generated: `{result['generated_at_utc']}`",
        f"- Status: **{result['status'].upper()}**",
        f"- Mode: `{result['mode']}`",
        f"- Runner revision: `{result['runner_revision']}`",
        "",
        "## Claim Boundary",
        "",
        result["claim_boundary"],
        "",
        "## Summary",
        "",
        f"- Criteria: `{result['criteria_passed']}/{result['criteria_total']}`",
        f"- MCPL-first single-shard hardware stress: `{result['final_decision']['tier4_32a_hw_mcpl_first']}`",
        f"- Replicated 8/12/16-core stress: `{result['final_decision']['replicated_8_12_16_core_stress']}`",
        f"- Native scale baseline freeze: `{result['final_decision']['native_scale_baseline_freeze']}`",
        "",
        "## Criteria",
        "",
        "| Criterion | Value | Rule | Pass |",
        "| --- | --- | --- | --- |",
    ]
    for item in result["criteria"]:
        value = item.value
        if isinstance(value, (dict, list, tuple)):
            value = json.dumps(json_safe(value), sort_keys=True)
        lines.append(f"| {item.name} | `{value}` | {item.rule} | {'yes' if item.passed else 'no'} |")
    lines.extend(
        [
            "",
            "## Commands",
            "",
        ]
    )
    for item in result["command_results"]:
        lines.append(f"- `{' '.join(item['command'])}` -> `{item['returncode']}`")
    lines.extend(
        [
            "",
            "## Next Step",
            "",
            result["next_step"],
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_outputs(result: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "results_json": output_dir / "tier4_32a_r1_results.json",
        "report_md": output_dir / "tier4_32a_r1_report.md",
        "criteria_csv": output_dir / "tier4_32a_r1_criteria.csv",
        "source_checks_csv": output_dir / "tier4_32a_r1_source_checks.csv",
        "command_log_txt": output_dir / "tier4_32a_r1_command_log.txt",
        "final_decision_json": output_dir / "tier4_32a_r1_final_decision.json",
    }
    write_json(artifacts["results_json"], result)
    write_report(artifacts["report_md"], result)
    write_csv(artifacts["criteria_csv"], [asdict(item) for item in result["criteria"]])
    write_csv(artifacts["source_checks_csv"], [asdict(item) for item in result["source_checks"]])
    artifacts["command_log_txt"].write_text(result["command_log"], encoding="utf-8")
    write_json(artifacts["final_decision_json"], result["final_decision"])

    manifest = {
        "tier": result["tier"],
        "status": result["status"],
        "generated_at_utc": result["generated_at_utc"],
        "output_dir": str(output_dir),
        "artifacts": artifacts,
        "claim_boundary": result["claim_boundary"],
        "next_step": result["next_step"],
    }
    write_json(output_dir / "tier4_32a_r1_manifest.json", manifest)
    write_json(LATEST_MANIFEST, manifest)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = build_results()
    write_outputs(result, args.output_dir)
    print(json.dumps({"status": result["status"], "output_dir": str(args.output_dir)}, indent=2))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
