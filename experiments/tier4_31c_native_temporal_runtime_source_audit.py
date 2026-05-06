#!/usr/bin/env python3
"""Tier 4.31c native temporal-substrate runtime source audit/local C host test.

This gate implements and verifies only the source/local-test layer for the
Tier 4.31b fixed-point temporal subset. It is deliberately not an EBRAINS
package and not hardware evidence. PASS means the custom runtime now owns the
seven causal EMA traces, exposes compact readback, and has local C tests for
init/update/readback/sham behavior before any temporal hardware smoke.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"
RUNTIME = ROOT / "coral_reef_spinnaker" / "spinnaker_runtime"

TIER = "Tier 4.31c - Native Temporal-Substrate Runtime Source Audit"
RUNNER_REVISION = "tier4_31c_native_temporal_runtime_source_audit_20260506_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier4_31c_20260506_native_temporal_runtime_source_audit"

TIER4_31A_RESULTS = CONTROLLED / "tier4_31a_20260506_native_temporal_substrate_readiness" / "tier4_31a_results.json"
TIER4_31B_RESULTS = CONTROLLED / "tier4_31b_20260506_native_temporal_fixed_point_reference" / "tier4_31b_results.json"

EXPECTED_DECAY = [19874, 25519, 28917, 30782, 31759, 32259, 32512]
EXPECTED_ALPHA = [12893, 7248, 3850, 1985, 1008, 508, 255]
EXPECTED_COMMANDS = {
    "CMD_TEMPORAL_INIT": 39,
    "CMD_TEMPORAL_UPDATE": 40,
    "CMD_TEMPORAL_READ_STATE": 41,
    "CMD_TEMPORAL_SHAM_MODE": 42,
}


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
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
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


def parse_cmd_values(config_text: str) -> dict[str, int]:
    values: dict[str, int] = {}
    for match in re.finditer(r"^#define\s+(CMD_[A-Z0-9_]+)\s+(\d+)\b", config_text, flags=re.MULTILINE):
        values[match.group(1)] = int(match.group(2))
    return values


def build_results() -> dict[str, Any]:
    tier4_31a = load_json(TIER4_31A_RESULTS)
    tier4_31b = load_json(TIER4_31B_RESULTS)

    config_h = RUNTIME / "src" / "config.h"
    state_h = RUNTIME / "src" / "state_manager.h"
    state_c = RUNTIME / "src" / "state_manager.c"
    host_h = RUNTIME / "src" / "host_interface.h"
    host_c = RUNTIME / "src" / "host_interface.c"
    makefile = RUNTIME / "Makefile"
    test_runtime = RUNTIME / "tests" / "test_runtime.c"
    test_profiles = RUNTIME / "tests" / "test_profiles.c"
    test_temporal = RUNTIME / "tests" / "test_temporal_state.c"

    config_text = config_h.read_text(encoding="utf-8")
    state_text = state_c.read_text(encoding="utf-8")
    host_text = host_c.read_text(encoding="utf-8")
    cmd_values = parse_cmd_values(config_text)
    reverse: dict[int, list[str]] = {}
    for name, value in cmd_values.items():
        reverse.setdefault(value, []).append(name)
    collisions = {str(value): names for value, names in reverse.items() if len(names) > 1}

    checks = [
        source_check(config_h, "CMD_TEMPORAL_INIT            39", "temporal init command code"),
        source_check(config_h, "CMD_TEMPORAL_UPDATE          40", "temporal update command code"),
        source_check(config_h, "CMD_TEMPORAL_READ_STATE      41", "temporal readback command code"),
        source_check(config_h, "CMD_TEMPORAL_SHAM_MODE       42", "temporal sham command code"),
        source_check(config_h, "TEMPORAL_TRACE_BOUND         FP_FROM_FLOAT(2.0f)", "Tier 4.31b selected trace range"),
        source_check(config_h, "TEMPORAL_TIMESCALE_CHECKSUM  1811900589U", "tau/alpha checksum"),
        source_check(state_h, "cra_temporal_summary_t", "versioned temporal summary struct"),
        source_check(state_h, "cra_temporal_update", "temporal update API"),
        source_check(state_h, "cra_temporal_get_trace", "local host trace parity API"),
        source_check(state_c, "g_temporal_decay_raw", "decay table owned by C runtime"),
        source_check(state_c, "g_temporal_alpha_raw", "alpha table owned by C runtime"),
        source_check(state_c, "FP_MUL(g_temporal_decay_raw[i], g_temporal_traces[i])", "fixed-point EMA decay equation"),
        source_check(state_c, "FP_MUL(g_temporal_alpha_raw[i], x)", "fixed-point EMA input equation"),
        source_check(state_c, "TEMPORAL_SHAM_ZERO_STATE", "zero-state sham behavior"),
        source_check(state_c, "TEMPORAL_SHAM_FROZEN_STATE", "frozen-state sham behavior"),
        source_check(host_h, "host_if_pack_temporal_summary", "compact temporal readback declaration"),
        source_check(host_c, "CRA_RUNTIME_PROFILE_TEMPORAL_HOST_SURFACE", "temporal host-surface ownership guard"),
        source_check(host_c, "case CMD_TEMPORAL_READ_STATE", "temporal readback dispatch"),
        source_check(host_c, "const uint8_t required_len = 48;", "compact temporal payload length"),
        source_check(makefile, "test-temporal-state", "local temporal C host test target"),
        source_check(test_runtime, "CMD_TEMPORAL_SHAM_MODE == 42", "full runtime command constant test"),
        source_check(test_profiles, "CMD_TEMPORAL_READ_STATE", "profile ownership guard tests"),
        source_check(test_temporal, "temporal fixed-point mirror updates", "4.31c direct fixed-point parity test"),
        source_check(test_temporal, "temporal compact host readback", "4.31c compact readback test"),
    ]

    commands = [
        run_command(["make", "-C", str(RUNTIME.relative_to(ROOT)), "test-temporal-state"]),
        run_command(["make", "-C", str(RUNTIME.relative_to(ROOT)), "test-profiles"]),
        run_command(["make", "-C", str(RUNTIME.relative_to(ROOT)), "test"]),
        run_command(["make", "-C", str(RUNTIME.relative_to(ROOT)), "test-lifecycle"]),
        run_command(["make", "-C", str(RUNTIME.relative_to(ROOT)), "test-lifecycle-split"]),
    ]
    command_passes = {item["command"][-1]: item["returncode"] == 0 for item in commands}
    command_log = "\n\n".join(
        "COMMAND: "
        + " ".join(item["command"])
        + f"\nRETURNCODE: {item['returncode']}\nSTDOUT:\n{item['stdout']}\nSTDERR:\n{item['stderr']}"
        for item in commands
    )

    decay_match = all(f"TEMPORAL_DECAY_RAW_{idx}         {value}" in config_text for idx, value in enumerate(EXPECTED_DECAY))
    alpha_match = all(f"TEMPORAL_ALPHA_RAW_{idx}         {value}" in config_text for idx, value in enumerate(EXPECTED_ALPHA))
    expected_commands_match = all(cmd_values.get(name) == value for name, value in EXPECTED_COMMANDS.items())

    criteria = [
        criterion("Tier 4.31a readiness passed", tier4_31a.get("status"), "== pass", tier4_31a.get("status") == "pass"),
        criterion("Tier 4.31a criteria complete", f"{tier4_31a.get('criteria_passed')}/{tier4_31a.get('criteria_total')}", "== 24/24", tier4_31a.get("criteria_passed") == tier4_31a.get("criteria_total") == 24),
        criterion("Tier 4.31b fixed-point reference passed", tier4_31b.get("status"), "== pass", tier4_31b.get("status") == "pass"),
        criterion("Tier 4.31b criteria complete", f"{tier4_31b.get('criteria_passed')}/{tier4_31b.get('criteria_total')}", "== 16/16", tier4_31b.get("criteria_passed") == tier4_31b.get("criteria_total") == 16),
        criterion("temporal command codes match contract", {name: cmd_values.get(name) for name in EXPECTED_COMMANDS}, "39,40,41,42", expected_commands_match),
        criterion("command code collision scan", collisions, "no duplicate CMD_* numeric values", not collisions),
        criterion("fixed-point timescale table matches 4.31b", {"decay": EXPECTED_DECAY, "alpha": EXPECTED_ALPHA}, "all raw constants present", decay_match and alpha_match),
        criterion("selected trace range remains +/-2", "TEMPORAL_TRACE_BOUND", "== FP_FROM_FLOAT(2.0f)", "TEMPORAL_TRACE_BOUND         FP_FROM_FLOAT(2.0f)" in config_text),
        criterion("source surface tokens present", [asdict(item) for item in checks], "all source checks present", all(item.present for item in checks)),
        criterion("EMA update is C-owned", "g_temporal_traces + alpha/decay + FP_MUL", "state_manager.c owns update equation", "g_temporal_traces" in state_text and "g_temporal_alpha_raw" in state_text and "FP_MUL(g_temporal_decay_raw[i], g_temporal_traces[i])" in state_text),
        criterion("compact temporal readback length", "required_len = 48", "host_if_pack_temporal_summary uses 48 bytes", "const uint8_t required_len = 48;" in host_text),
        criterion("temporal host surface is ownership guarded", "CRA_RUNTIME_PROFILE_TEMPORAL_HOST_SURFACE", "learning/full/decoupled only", "CRA_RUNTIME_PROFILE_TEMPORAL_HOST_SURFACE" in host_text and "!defined(CRA_RUNTIME_PROFILE_LIFECYCLE_CORE)" in host_text),
        criterion("runtime test-temporal-state passed", command_passes.get("test-temporal-state"), "returncode == 0", command_passes.get("test-temporal-state", False)),
        criterion("runtime test-profiles passed", command_passes.get("test-profiles"), "returncode == 0", command_passes.get("test-profiles", False)),
        criterion("runtime test passed", command_passes.get("test"), "returncode == 0", command_passes.get("test", False)),
        criterion("lifecycle tests preserved", {"test-lifecycle": command_passes.get("test-lifecycle"), "test-lifecycle-split": command_passes.get("test-lifecycle-split")}, "both returncode == 0", command_passes.get("test-lifecycle", False) and command_passes.get("test-lifecycle-split", False)),
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
        "command_values": cmd_values,
        "command_collisions": collisions,
        "source_contract": {
            "temporal_trace_count": 7,
            "temporal_trace_bound_raw": 65536,
            "temporal_input_bound_raw": 98304,
            "temporal_timescale_checksum": 1811900589,
            "compact_readback_len": 48,
            "owner_profile": "learning_core plus monolithic/decoupled local surfaces",
            "non_owner_profiles": ["context_core", "route_core", "memory_core", "lifecycle_core"],
            "sham_modes": ["enabled", "zero_state", "frozen_state", "reset_each_update"],
        },
        "claim_boundary": (
            "Tier 4.31c is local source/runtime host evidence only. It proves the "
            "custom C runtime owns the seven-EMA fixed-point temporal subset from "
            "Tier 4.31b with compact readback and behavior-backed shams. It is not "
            "EBRAINS hardware evidence, not speedup, not nonlinear recurrence, not "
            "native replay/sleep, not native macro eligibility, and not benchmark superiority."
        ),
        "next_step": (
            "Tier 4.31d native temporal-substrate hardware smoke: prepare and run a "
            "one-board/one-seed compact hardware probe only after this local source "
            "audit remains green."
        ),
    }


def write_report(path: Path, results: dict[str, Any]) -> None:
    lines = [
        "# Tier 4.31c Native Temporal-Substrate Runtime Source Audit",
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
        "## Source Contract",
        "",
        "```json",
        json.dumps(json_safe(results["source_contract"]), indent=2, sort_keys=True),
        "```",
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
    for item in results["source_checks"]:
        lines.append(f"| `{item.file}` | `{item.token}` | {'yes' if item.present else 'no'} | {item.purpose} |")
    lines.extend(["", "## Next Step", "", results["next_step"], ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    results = build_results()
    serializable = results | {
        "output_dir": str(output_dir),
        "artifacts": {
            "results_json": str(output_dir / "tier4_31c_results.json"),
            "report_md": str(output_dir / "tier4_31c_report.md"),
            "source_checks_csv": str(output_dir / "tier4_31c_source_checks.csv"),
            "summary_csv": str(output_dir / "tier4_31c_summary.csv"),
            "command_log": str(output_dir / "tier4_31c_command_log.txt"),
        },
    }
    write_json(output_dir / "tier4_31c_results.json", serializable)
    write_report(output_dir / "tier4_31c_report.md", results)
    write_csv(output_dir / "tier4_31c_source_checks.csv", [asdict(item) for item in results["source_checks"]])
    write_csv(output_dir / "tier4_31c_summary.csv", [asdict(item) for item in results["criteria"]])
    (output_dir / "tier4_31c_command_log.txt").write_text(results["command_log"], encoding="utf-8")
    write_json(CONTROLLED / "tier4_31c_latest_manifest.json", serializable)
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
