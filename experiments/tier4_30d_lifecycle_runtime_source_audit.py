#!/usr/bin/env python3
"""Tier 4.30d multi-core lifecycle runtime source audit/local C host test.

This gate implements and verifies only the source/local-test layer for the
Tier 4.30c split. It is deliberately not an EBRAINS package and not hardware
evidence. PASS means the custom runtime now has a dedicated lifecycle_core
profile, lifecycle inter-core stubs/counters, active-mask sync bookkeeping, and
local C tests that enforce lifecycle ownership before the next hardware smoke.
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

TIER = "Tier 4.30d - Multi-Core Lifecycle Runtime Source Audit"
RUNNER_REVISION = "tier4_30d_lifecycle_runtime_source_audit_20260505_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier4_30d_20260505_lifecycle_runtime_source_audit"

TIER4_30B_RESULTS = CONTROLLED / "tier4_30b_20260505_lifecycle_source_audit" / "tier4_30b_results.json"
TIER4_30B_HW_RESULTS = CONTROLLED / "tier4_30b_hw_20260505_hardware_pass_ingested" / "tier4_30b_hw_results.json"
TIER4_30C_RESULTS = CONTROLLED / "tier4_30c_20260505_multicore_lifecycle_split" / "tier4_30c_results.json"


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
        writer = csv.DictWriter(handle, fieldnames=keys, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def criterion(name: str, value: Any, rule: str, passed: bool, note: str = "") -> Criterion:
    return Criterion(name=name, value=value, rule=rule, passed=bool(passed), note=note)


def run_command(command: list[str]) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def source_check(path: Path, token: str, purpose: str) -> SourceCheck:
    return SourceCheck(
        file=str(path.relative_to(ROOT)),
        token=token,
        present=token in path.read_text(encoding="utf-8"),
        purpose=purpose,
    )


def build_results() -> dict[str, Any]:
    tier4_30b = load_json(TIER4_30B_RESULTS)
    tier4_30b_hw = load_json(TIER4_30B_HW_RESULTS)
    tier4_30c = load_json(TIER4_30C_RESULTS)

    config_h = RUNTIME / "src" / "config.h"
    state_h = RUNTIME / "src" / "state_manager.h"
    state_c = RUNTIME / "src" / "state_manager.c"
    host_c = RUNTIME / "src" / "host_interface.c"
    makefile = RUNTIME / "Makefile"
    test_profiles = RUNTIME / "tests" / "test_profiles.c"
    test_lifecycle_split = RUNTIME / "tests" / "test_lifecycle_split.c"
    spin_stub_h = RUNTIME / "stubs" / "spin1_api.h"

    checks = [
        source_check(config_h, "PROFILE_LIFECYCLE_CORE", "dedicated lifecycle_core profile id"),
        source_check(config_h, "MCPL_MSG_LIFECYCLE_EVENT_REQUEST", "event request MCPL message id"),
        source_check(config_h, "MCPL_MSG_LIFECYCLE_TROPHIC_UPDATE", "trophic update MCPL message id"),
        source_check(config_h, "MCPL_MSG_LIFECYCLE_ACTIVE_MASK_SYNC", "active-mask sync MCPL message id"),
        source_check(config_h, "MCPL_LIFECYCLE_SYNC_LINEAGE", "lineage checksum sync subtype"),
        source_check(makefile, "RUNTIME_PROFILE),lifecycle_core", "hardware/local build profile"),
        source_check(makefile, "test-lifecycle-split", "local split host test target"),
        source_check(state_h, "cra_lifecycle_handle_event_request", "lifecycle-core event request API"),
        source_check(state_h, "cra_lifecycle_receive_active_mask_sync", "consumer active-mask sync API"),
        source_check(state_h, "lifecycle_duplicate_events", "duplicate event counter"),
        source_check(state_h, "lifecycle_stale_events", "stale event counter"),
        source_check(state_h, "lifecycle_missing_acks", "missing-ack counter"),
        source_check(state_c, "cra_lifecycle_send_event_request_stub", "learning-side event request stub"),
        source_check(state_c, "cra_lifecycle_send_trophic_update_stub", "learning-side trophic request stub"),
        source_check(state_c, "spin1_send_mc_packet", "MCPL/multicast-target send surface"),
        source_check(state_c, "_lifecycle_broadcast_active_mask_sync", "active-mask sync broadcast stub"),
        source_check(state_c, "_lifecycle_reject_duplicate_or_stale", "duplicate/stale failure guard"),
        source_check(host_c, "CRA_RUNTIME_PROFILE_LIFECYCLE_HOST_SURFACE", "direct lifecycle host surface guard"),
        source_check(host_c, "!defined(CRA_RUNTIME_PROFILE_LIFECYCLE_CORE)", "decoupled catch-all excludes lifecycle_core"),
        source_check(test_profiles, "CMD_LIFECYCLE_INIT", "non-lifecycle profile ownership guard test"),
        source_check(test_lifecycle_split, "active-mask/count/lineage sync send/receive bookkeeping", "4.30d split host test"),
        source_check(spin_stub_h, "g_test_last_mc_key", "host-side MCPL packet inspection"),
        source_check(spin_stub_h, "g_test_mc_packet_count", "host-side multi-packet MCPL inspection"),
    ]

    commands = [
        run_command(["make", "-C", str(RUNTIME.relative_to(ROOT)), "test-lifecycle"]),
        run_command(["make", "-C", str(RUNTIME.relative_to(ROOT)), "test-lifecycle-split"]),
        run_command(["make", "-C", str(RUNTIME.relative_to(ROOT)), "test-profiles"]),
        run_command(["make", "-C", str(RUNTIME.relative_to(ROOT)), "test"]),
    ]
    command_passes = {item["command"][-1]: item["returncode"] == 0 for item in commands}
    command_log = "\n\n".join(
        "COMMAND: "
        + " ".join(item["command"])
        + f"\nRETURNCODE: {item['returncode']}\nSTDOUT:\n{item['stdout']}\nSTDERR:\n{item['stderr']}"
        for item in commands
    )

    criteria = [
        criterion("Tier 4.30b source audit passed", tier4_30b.get("status"), "== pass", tier4_30b.get("status") == "pass"),
        criterion("Tier 4.30b-hw corrected ingest passed", tier4_30b_hw.get("status"), "== pass", tier4_30b_hw.get("status") == "pass"),
        criterion("Tier 4.30c split contract passed", tier4_30c.get("status"), "== pass", tier4_30c.get("status") == "pass"),
        criterion(
            "Tier 4.30c split criteria complete",
            f"{tier4_30c.get('criteria_passed')}/{tier4_30c.get('criteria_total')}",
            "== 22/22",
            tier4_30c.get("criteria_passed") == tier4_30c.get("criteria_total") == 22,
        ),
        criterion("source surface tokens present", [asdict(item) for item in checks], "all source checks present", all(item.present for item in checks)),
        criterion("runtime test-lifecycle passed", command_passes.get("test-lifecycle"), "returncode == 0", command_passes.get("test-lifecycle", False)),
        criterion("runtime test-lifecycle-split passed", command_passes.get("test-lifecycle-split"), "returncode == 0", command_passes.get("test-lifecycle-split", False)),
        criterion("runtime test-profiles passed", command_passes.get("test-profiles"), "returncode == 0", command_passes.get("test-profiles", False)),
        criterion("runtime test passed", command_passes.get("test"), "returncode == 0", command_passes.get("test", False)),
        criterion("dedicated lifecycle_core profile id", "PROFILE_LIFECYCLE_CORE=7", "declared and locally tested", any(item.token == "PROFILE_LIFECYCLE_CORE" and item.present for item in checks)),
        criterion("non-lifecycle profiles reject direct lifecycle writes", "test_profiles", "CMD_LIFECYCLE_INIT/READ_STATE NAK outside lifecycle_core", "CMD_LIFECYCLE_INIT" in test_profiles.read_text(encoding="utf-8")),
        criterion("active-mask sync uses MCPL/multicast-target stub", "spin1_send_mc_packet mask+lineage packets", "present in lifecycle sync path", "_lifecycle_broadcast_active_mask_sync" in state_c.read_text(encoding="utf-8") and "MCPL_LIFECYCLE_SYNC_LINEAGE" in state_c.read_text(encoding="utf-8") and "spin1_send_mc_packet" in state_c.read_text(encoding="utf-8")),
        criterion("payload length rule preserved", "host_if_pack_lifecycle_summary required_len = 68", "compact payload_len=68 unchanged", "const uint8_t required_len = 68;" in host_c.read_text(encoding="utf-8")),
        criterion("no EBRAINS package generated", "local-source-audit", "mode is local only", True),
    ]
    failed = [item for item in criteria if not item.passed]

    return {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "status": "pass" if not failed else "fail",
        "mode": "local-source-audit",
        "criteria_passed": len(criteria) - len(failed),
        "criteria_total": len(criteria),
        "criteria": criteria,
        "failed_criteria": failed,
        "source_checks": checks,
        "command_results": commands,
        "command_log": command_log,
        "source_inputs": {
            "tier4_30b_results": str(TIER4_30B_RESULTS),
            "tier4_30b_hw_results": str(TIER4_30B_HW_RESULTS),
            "tier4_30c_results": str(TIER4_30C_RESULTS),
            "config_h": str(config_h),
            "state_manager_h": str(state_h),
            "state_manager_c": str(state_c),
            "host_interface_c": str(host_c),
            "runtime_makefile": str(makefile),
            "test_lifecycle_split_c": str(test_lifecycle_split),
        },
        "claim_boundary": (
            "Tier 4.30d is local source/runtime host evidence only. It proves a "
            "dedicated lifecycle_core profile, lifecycle inter-core stubs/counters, "
            "active-mask/count/lineage sync bookkeeping, and local ownership guards "
            "against the Tier 4.30c contract. It is not EBRAINS hardware evidence, "
            "not task-benefit evidence, not speedup, not multi-chip scaling, not "
            "v2.2 temporal migration, and not a lifecycle baseline freeze."
        ),
        "next_step": (
            "Tier 4.30e multi-core lifecycle hardware smoke package/run: package the "
            "4.30d runtime source surface and prove real SpiNNaker execution/readback "
            "before any lifecycle sham-control hardware subset."
        ),
    }


def write_report(path: Path, results: dict[str, Any]) -> None:
    safe_checks = [asdict(item) for item in results["source_checks"]]
    lines = [
        "# Tier 4.30d Multi-Core Lifecycle Runtime Source Audit",
        "",
        f"- Generated: `{results['generated_at_utc']}`",
        f"- Runner revision: `{results['runner_revision']}`",
        f"- Mode: `{results['mode']}`",
        f"- Status: **{results['status'].upper()}**",
        f"- Criteria: `{results['criteria_passed']}/{results['criteria_total']}`",
        "",
        "## Claim Boundary",
        "",
        results["claim_boundary"],
        "",
        "## Criteria",
        "",
        "| Criterion | Value | Rule | Pass | Note |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in results["criteria"]:
        value = json.dumps(json_safe(item.value), sort_keys=True)
        if len(value) > 140:
            value = value[:137] + "..."
        lines.append(f"| {item.name} | `{value}` | {item.rule} | {'yes' if item.passed else 'no'} | {item.note} |")
    lines.extend(
        [
            "",
            "## Source Checks",
            "",
            "| File | Token | Present | Purpose |",
            "| --- | --- | --- | --- |",
        ]
    )
    for item in safe_checks:
        lines.append(f"| `{item['file']}` | `{item['token']}` | {'yes' if item['present'] else 'no'} | {item['purpose']} |")
    lines.extend(["", "## Next Step", "", results["next_step"], ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    results = build_results()
    serializable = results | {
        "output_dir": str(output_dir),
        "artifacts": {
            "results_json": str(output_dir / "tier4_30d_results.json"),
            "report_md": str(output_dir / "tier4_30d_report.md"),
            "source_checks_csv": str(output_dir / "tier4_30d_source_checks.csv"),
            "command_log": str(output_dir / "tier4_30d_command_log.txt"),
        },
    }
    write_json(output_dir / "tier4_30d_results.json", serializable)
    write_report(output_dir / "tier4_30d_report.md", results)
    write_csv(output_dir / "tier4_30d_source_checks.csv", [asdict(item) for item in results["source_checks"]])
    (output_dir / "tier4_30d_command_log.txt").write_text(results["command_log"], encoding="utf-8")
    write_json(CONTROLLED / "tier4_30d_latest_manifest.json", serializable)
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
