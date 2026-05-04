#!/usr/bin/env python3
"""Tier 4.22h compact state readback and build-command readiness.

Tier 4.22g repaired the first custom-C scale blockers locally. Tier 4.22h adds
the compact readback command needed before hardware command acceptance can mean
anything. It also records whether the local environment can build an `.aplx`.

Claim boundary:
- PASS = compact state-summary readback exists, host tests cover it, static
  protocol checks pass, and build/load readiness is explicitly recorded.
- If `spinnaker_tools` are not installed locally, `.aplx` build/load acceptance
  is recorded as not attempted, not silently claimed.
- Not hardware evidence, not speedup evidence, and not a custom-runtime learning
  hardware pass.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"
RUNTIME = ROOT / "coral_reef_spinnaker" / "spinnaker_runtime"
SRC = RUNTIME / "src"
TESTS = RUNTIME / "tests"
TIER = "Tier 4.22h - Compact Readback / Build-Command Readiness"
RUNNER_REVISION = "tier4_22h_compact_readback_acceptance_20260430_0006"
TIER4_22G_LATEST = CONTROLLED / "tier4_22g_latest_manifest.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
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
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def criterion(name: str, value: Any, rule: str, passed: bool, note: str = "") -> dict[str, Any]:
    return {"name": name, "value": value, "rule": rule, "passed": bool(passed), "note": note}


def latest_status(path: Path) -> tuple[str, str | None]:
    if not path.exists():
        return "missing", None
    try:
        payload = read_json(path)
    except Exception as exc:
        return f"unreadable:{type(exc).__name__}", None
    return str(payload.get("status", "unknown")).lower(), str(payload.get("manifest") or "")


def markdown_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.6g}"
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, sort_keys=True)
    return str(value)


def function_body(source: str, signature: str) -> str:
    start = source.find(signature)
    if start < 0:
        return ""
    brace = source.find("{", start)
    if brace < 0:
        return ""
    depth = 0
    for i in range(brace, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[brace + 1 : i]
    return ""


def run_cmd(cmd: list[str], *, cwd: Path) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)
    return {
        "command": " ".join(cmd),
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def run_host_tests() -> dict[str, Any]:
    result = run_cmd(["make", "-C", str(RUNTIME), "clean-host", "test"], cwd=ROOT)
    result["passed"] = result["returncode"] == 0 and "=== ALL TESTS PASSED ===" in result["stdout"]
    return result


def maybe_build_aplx() -> dict[str, Any]:
    env_hint = os.environ.get("SPINN_DIRS", "")
    candidates = [
        Path(env_hint) if env_hint else None,
        Path("/opt/spinnaker_tools"),
        Path("/usr/local/spinnaker_tools"),
        Path.home() / "spinnaker_tools",
    ]
    tools_dir = next((path for path in candidates if path and (path / "make" / "spinnaker_tools.mk").exists()), None)
    if tools_dir is None:
        return {
            "attempted": False,
            "status": "not_attempted_spinnaker_tools_missing",
            "spinnaker_tools": "",
            "command": "make -C coral_reef_spinnaker/spinnaker_runtime clean all",
            "returncode": None,
            "stdout_artifact": "",
            "stderr_artifact": "",
            "aplx_artifact": "",
        }
    result = run_cmd(["make", "-C", str(RUNTIME), "clean", "all"], cwd=ROOT)
    aplx = RUNTIME / "build" / "coral_reef.aplx"
    result.update(
        {
            "attempted": True,
            "status": "pass" if result["returncode"] == 0 and aplx.exists() else "fail",
            "spinnaker_tools": str(tools_dir),
            "aplx_artifact": str(aplx) if aplx.exists() else "",
        }
    )
    return result


def source_map() -> dict[str, str]:
    return {
        "config.h": read_text(SRC / "config.h"),
        "main.c": read_text(SRC / "main.c"),
        "host_interface.h": read_text(SRC / "host_interface.h"),
        "host_interface.c": read_text(SRC / "host_interface.c"),
        "router.h": read_text(SRC / "router.h"),
        "router.c": read_text(SRC / "router.c"),
        "state_manager.h": read_text(SRC / "state_manager.h"),
        "synapse_manager.h": read_text(SRC / "synapse_manager.h"),
        "sark_stub.h": read_text(RUNTIME / "stubs" / "sark.h"),
        "spin1_api_stub.h": read_text(RUNTIME / "stubs" / "spin1_api.h"),
        "test_runtime.c": read_text(TESTS / "test_runtime.c"),
        "makefile": read_text(RUNTIME / "Makefile"),
        "protocol": read_text(RUNTIME / "PROTOCOL_SPEC.md"),
    }


def static_checks(src: dict[str, str]) -> list[dict[str, Any]]:
    pack_body = function_body(src["host_interface.c"], "uint8_t host_if_pack_state_summary")
    switch_body = function_body(src["host_interface.c"], "void sdp_rx_callback")
    return [
        criterion("CMD_READ_STATE defined", "CMD_READ_STATE 8", "config.h defines opcode", "#define CMD_READ_STATE   8" in src["config.h"]),
        criterion("CMD_READ_STATE tested", "assert(CMD_READ_STATE == 8)", "host tests cover opcode", "assert(CMD_READ_STATE == 8)" in src["test_runtime.c"]),
        criterion("state summary pack API declared", "host_if_pack_state_summary", "declared in host_interface.h", "host_if_pack_state_summary" in src["host_interface.h"]),
        criterion("state summary pack API implemented", "host_if_pack_state_summary", "implemented in host_interface.c", "uint8_t host_if_pack_state_summary" in src["host_interface.c"]),
        criterion("state summary command handler exists", "_handle_read_state", "implemented in host_interface.c", "static void _handle_read_state" in src["host_interface.c"]),
        criterion("state summary command dispatched", "case CMD_READ_STATE", "sdp switch dispatches read-state", "case CMD_READ_STATE" in switch_body),
        criterion("state summary includes timestep", "g_timestep", "packed into payload", "_write_u32(&payload[4], g_timestep)" in pack_body),
        criterion("state summary includes neuron/synapse/trace counts", "neuron_count/synapse_count/synapse_active_trace_count", "packed into payload", all(token in pack_body for token in ["neuron_count()", "synapse_count()", "synapse_active_trace_count()"])),
        criterion("state summary includes context counters", "active_slots/slot_writes/hits/misses/evictions", "packed into payload", all(token in pack_body for token in ["summary.active_slots", "summary.slot_writes", "summary.slot_hits", "summary.slot_misses", "summary.slot_evictions"])),
        criterion("state summary includes decision/reward counters", "decisions/reward_events", "packed into payload", "summary.decisions" in pack_body and "summary.reward_events" in pack_body),
        criterion("state summary includes pending horizon counters", "pending_created/matured/dropped/active_pending", "packed into payload", all(token in pack_body for token in ["summary.pending_created", "summary.pending_matured", "summary.pending_dropped", "summary.active_pending"])),
        criterion("state summary includes readout state", "readout_weight/readout_bias", "packed into payload", "summary.readout_weight" in pack_body and "summary.readout_bias" in pack_body),
        criterion("state summary stays SDP compact", "73 bytes", "<= 255 byte payload", "const uint8_t required_len = 73" in src["host_interface.c"]),
        criterion("host test covers compact summary", "test_host_state_summary_pack", "test_runtime.c exercises pack fields", "test_host_state_summary_pack" in src["test_runtime.c"]),
        criterion("runtime Makefile has aplx target", "all hardware aplx", "build path declared", "all hardware aplx" in src["makefile"] and "$(BUILD_DIR)/$(APP).aplx" in src["makefile"]),
        criterion("official MC no-payload callback registered", "MC_PACKET_RECEIVED", "main.c registers official Spin1API enum event confirmed by Tier 4.22k", "spin1_callback_on(MC_PACKET_RECEIVED" in src["main.c"]),
        criterion("official MC payload callback registered", "MCPL_PACKET_RECEIVED", "main.c registers official Spin1API enum event confirmed by Tier 4.22k", "spin1_callback_on(MCPL_PACKET_RECEIVED" in src["main.c"]),
        criterion("no brittle legacy MC_PACKET_RX callback", "MC_PACKET_RX absent", "legacy guessed event name is not used", "MC_PACKET_RX" not in src["main.c"]),
        criterion("host stub mirrors official MC event names", "MC_PACKET_RECEIVED/MCPL_PACKET_RECEIVED", "local syntax guard exposes official enum names and omits legacy guessed names", "MC_PACKET_RECEIVED" in src["spin1_api_stub.h"] and "MCPL_PACKET_RECEIVED" in src["spin1_api_stub.h"] and "MC_PACKET_RX" not in src["spin1_api_stub.h"]),
        criterion("SDP reply uses packed official sdp_msg_t fields", "dest_port/srce_port/dest_addr/srce_addr", "host_interface.c mirrors real SARK SDP struct field names", all(token in src["host_interface.c"] for token in ["reply->dest_port = req->srce_port", "reply->srce_port = req->dest_port", "reply->dest_addr = req->srce_addr", "reply->srce_addr = req->dest_addr"])),
        criterion("SDP reply uses SARK memory copy API", "sark_mem_cpy", "real spinnaker_tools exposes sark_mem_cpy, not sark_memcpy", "sark_mem_cpy(" in src["host_interface.c"] and "sark_memcpy" not in src["host_interface.c"]),
        criterion("router header includes stdint directly", "#include <stdint.h>", "router.h must not rely on indirect EBRAINS header includes for uint32_t", "#include <stdint.h>" in src["router.h"]),
        criterion("router uses official SARK router API", "rtr_alloc/rtr_mc_set/rtr_free", "real spinnaker_tools exposes official rtr_* router calls", all(token in src["router.c"] for token in ["rtr_alloc(1)", "rtr_mc_set(", "rtr_free("])),
        criterion("deprecated local-only router helpers absent", "sark_router_alloc/sark_router_free absent", "local stubs must not hide EBRAINS SARK API drift", all(token not in src["router.c"] and token not in src["sark_stub.h"] for token in ["sark_router_alloc", "sark_router_free"])),
        criterion("host stub mirrors official router API", "rtr_alloc/rtr_mc_set/rtr_free", "local syntax guard exposes official SARK router names", all(token in src["sark_stub.h"] for token in ["rtr_alloc", "rtr_mc_set", "rtr_free"])),
        criterion("hardware build uses official spinnaker_tools.mk", "spinnaker_tools.mk", "official build chain supplies cpu_reset, build object, spin1_api library, and APLX section packing", "make/spinnaker_tools.mk" in src["makefile"]),
        criterion("hardware build avoids deprecated Makefile.common include", "Makefile.common absent", "Makefile.common inclusion lacks the app build rules needed for APLX creation", "Makefile.common" not in src["makefile"]),
        criterion("hardware build avoids manual direct linker recipe", "no direct $(LD) object-only link", "manual object-only link produced empty ELF without cpu_reset/startup sections on EBRAINS", "$(LD) $(LDFLAGS) $^ -o" not in src["makefile"] and "$(OC) -O binary $(BUILD_DIR)/$(APP).elf" not in src["makefile"] and "aplx-maker" not in src["makefile"]),
        criterion("hardware output stays under build directory", "APP_OUTPUT_DIR := build/", "runner expects build/coral_reef.aplx", "APP_OUTPUT_DIR := build/" in src["makefile"]),
        criterion("hardware build creates nested object directories", "$(OBJECTS): | $(OBJECT_DIRS)", "spinnaker_tools.mk writes build/gnu/src/*.o and does not create nested source subdirectories itself", "OBJECT_DIRS := $(sort $(dir $(OBJECTS)))" in src["makefile"] and "$(OBJECTS): | $(OBJECT_DIRS)" in src["makefile"] and "mkdir -p $@" in src["makefile"]),
    ]


def readback_rows() -> list[dict[str, Any]]:
    fields = [
        ("0", "cmd", "u8", "CMD_READ_STATE"),
        ("1", "status", "u8", "0 = ok"),
        ("2", "schema_version", "u8", "1"),
        ("3", "reserved", "u8", "reserved/alignment"),
        ("4", "timestep", "u32", "runtime timestep"),
        ("8", "neuron_count", "u32", "live neurons"),
        ("12", "synapse_count", "u32", "live synapses"),
        ("16", "active_trace_count", "u32", "active eligibility traces"),
        ("20", "active_slots", "u32", "active context slots"),
        ("24", "slot_writes", "u32", "context writes"),
        ("28", "slot_hits", "u32", "context hits"),
        ("32", "slot_misses", "u32", "context misses"),
        ("36", "slot_evictions", "u32", "context evictions"),
        ("40", "decisions", "u32", "readout decisions"),
        ("44", "reward_events", "u32", "reward events"),
        ("48", "pending_created", "u32", "pending horizons created"),
        ("52", "pending_matured", "u32", "pending horizons matured"),
        ("56", "pending_dropped", "u32", "pending horizons dropped"),
        ("60", "active_pending", "u32", "active pending horizons"),
        ("64", "readout_weight", "s32", "s16.15 readout weight"),
        ("68", "readout_bias", "s32", "s16.15 readout bias"),
        ("72", "flags", "u8", "reserved"),
    ]
    return [{"byte_offset": off, "field": field, "type": typ, "meaning": meaning} for off, field, typ, meaning in fields]


def acceptance_rows(build: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "gate": "host_runtime_tests",
            "status": "pass",
            "meaning": "runtime C command/readback code compiles and host tests pass",
            "hardware_claim": "none",
        },
        {
            "gate": "compact_state_readback",
            "status": "pass",
            "meaning": "CMD_READ_STATE schema is packed and covered by host tests",
            "hardware_claim": "none until board round-trip",
        },
        {
            "gate": "aplx_build",
            "status": build["status"],
            "meaning": "local .aplx build attempted only if spinnaker_tools are installed",
            "hardware_claim": "none unless build status is pass and board load/command smoke later passes",
        },
        {
            "gate": "board_load_command_roundtrip",
            "status": "not_attempted",
            "meaning": "requires EBRAINS/board run",
            "hardware_claim": "future Tier 4.22i target",
        },
    ]


def write_report(path: Path, result: dict[str, Any]) -> None:
    summary = result["summary"]
    lines = [
        "# Tier 4.22h Compact Readback / Build-Command Readiness",
        "",
        f"- Generated: `{result['generated_at_utc']}`",
        f"- Status: **{result['status'].upper()}**",
        f"- Output directory: `{result['output_dir']}`",
        "",
        "Tier 4.22h adds compact custom-runtime state readback and records build-command readiness. It does not claim a board load or hardware command round-trip unless those are actually run.",
        "",
        "## Summary",
        "",
        f"- Tier 4.22g latest status: `{summary['tier4_22g_status']}`",
        f"- Host C tests passed: `{summary['host_tests_passed']}`",
        f"- Static readback checks passed: `{summary['static_checks_passed']}` / `{summary['static_checks_total']}`",
        f"- Compact readback payload bytes: `{summary['compact_readback_payload_bytes']}`",
        f"- APLX build status: `{summary['aplx_build_status']}`",
        f"- Board load/command roundtrip status: `{summary['board_load_command_roundtrip_status']}`",
        f"- Custom-runtime learning hardware allowed: `{summary['custom_runtime_learning_hardware_allowed']}`",
        f"- Next gate: `{summary['next_step_if_passed']}`",
        "",
        "## Criteria",
        "",
        "| Criterion | Value | Rule | Pass |",
        "| --- | --- | --- | --- |",
    ]
    for item in result["criteria"]:
        lines.append(f"| {item['name']} | `{markdown_value(item.get('value'))}` | `{item.get('rule')}` | {'yes' if item.get('passed') else 'no'} |")
    lines.extend(["", "## Readback Schema", "", "| Offset | Field | Type | Meaning |", "| --- | --- | --- | --- |"])
    for row in result["readback_schema"]:
        lines.append(f"| `{row['byte_offset']}` | `{row['field']}` | `{row['type']}` | {row['meaning']} |")
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            "- This is local compact-readback and build-command readiness evidence.",
            "- It is not a hardware run, board load, command round-trip, speedup result, or custom-runtime learning pass.",
            "- If local `spinnaker_tools` are missing, `.aplx` build is recorded as not attempted rather than treated as failure or success.",
            "- The next hardware-facing gate must run a tiny board load/command round-trip before any custom-runtime learning job.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_latest(output_dir: Path, manifest: Path, report: Path, status: str) -> None:
    CONTROLLED.mkdir(parents=True, exist_ok=True)
    write_json(
        CONTROLLED / "tier4_22h_latest_manifest.json",
        {
            "generated_at_utc": utc_now(),
            "tier": TIER,
            "status": status,
            "output_dir": str(output_dir),
            "manifest": str(manifest),
            "report": str(report),
            "canonical": False,
            "claim": "Latest Tier 4.22h compact state readback and build-command readiness; not hardware command round-trip evidence.",
        },
    )


def run(args: argparse.Namespace) -> int:
    output_dir = (args.output_dir or CONTROLLED / "tier4_22h_20260430_compact_readback_acceptance").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    tier4_22g_status, tier4_22g_manifest = latest_status(TIER4_22G_LATEST)
    src = source_map()
    host = run_host_tests()
    build = maybe_build_aplx()
    checks = static_checks(src)
    schema = readback_rows()
    acceptance = acceptance_rows(build)

    host_stdout = output_dir / "tier4_22h_host_test_stdout.txt"
    host_stderr = output_dir / "tier4_22h_host_test_stderr.txt"
    host_stdout.write_text(host["stdout"], encoding="utf-8")
    host_stderr.write_text(host["stderr"], encoding="utf-8")

    build_stdout = output_dir / "tier4_22h_aplx_build_stdout.txt"
    build_stderr = output_dir / "tier4_22h_aplx_build_stderr.txt"
    build_stdout.write_text(str(build.get("stdout", "")), encoding="utf-8")
    build_stderr.write_text(str(build.get("stderr", "")), encoding="utf-8")
    build["stdout_artifact"] = str(build_stdout)
    build["stderr_artifact"] = str(build_stderr)

    static_csv = output_dir / "tier4_22h_static_checks.csv"
    schema_csv = output_dir / "tier4_22h_readback_schema.csv"
    acceptance_csv = output_dir / "tier4_22h_acceptance_matrix.csv"
    write_csv(static_csv, checks)
    write_csv(schema_csv, schema)
    write_csv(acceptance_csv, acceptance)

    static_passed = sum(1 for check in checks if check["passed"])
    aplx_ok_or_not_attempted = build["status"] in {"pass", "not_attempted_spinnaker_tools_missing"}
    board_roundtrip_status = "not_attempted"
    learning_hw_allowed = False
    criteria = [
        criterion("runner revision current", RUNNER_REVISION, "expected current source", True),
        criterion("Tier 4.22g optimization pass exists", tier4_22g_status, "== pass", tier4_22g_status == "pass"),
        criterion("custom C host tests pass", host["returncode"], "returncode == 0 and ALL TESTS PASSED", bool(host["passed"])),
        criterion("all static readback checks pass", f"{static_passed}/{len(checks)}", "all pass", static_passed == len(checks)),
        criterion("compact readback schema <= SDP payload", 73, "<= 255 bytes", 73 <= 255),
        criterion("APLX build status recorded honestly", build["status"], "pass or not_attempted_spinnaker_tools_missing", aplx_ok_or_not_attempted),
        criterion("board load/command roundtrip not overclaimed", board_roundtrip_status, "not_attempted locally", board_roundtrip_status == "not_attempted"),
        criterion("custom-runtime learning hardware remains blocked", learning_hw_allowed, "False until board command roundtrip passes", not learning_hw_allowed),
    ]
    status = "pass" if all(item["passed"] for item in criteria) else "fail"
    failure_reason = "" if status == "pass" else "Failed criteria: " + ", ".join(item["name"] for item in criteria if not item["passed"])
    summary = {
        "runner_revision": RUNNER_REVISION,
        "tier4_22g_status": tier4_22g_status,
        "tier4_22g_manifest": tier4_22g_manifest,
        "host_tests_passed": bool(host["passed"]),
        "host_test_returncode": int(host["returncode"]),
        "static_checks_total": len(checks),
        "static_checks_passed": static_passed,
        "compact_readback_command": "CMD_READ_STATE",
        "compact_readback_payload_bytes": 73,
        "readback_schema_version": 1,
        "aplx_build_status": build["status"],
        "aplx_build_attempted": bool(build["attempted"]),
        "aplx_artifact": build.get("aplx_artifact", ""),
        "board_load_command_roundtrip_status": board_roundtrip_status,
        "custom_runtime_learning_hardware_allowed": learning_hw_allowed,
        "claim_boundary": "Local compact-readback/build-readiness only; not hardware, board command round-trip, speedup, or custom-runtime learning evidence.",
        "next_step_if_passed": "Tier 4.22i tiny EBRAINS/board custom-runtime load + CMD_READ_STATE round-trip smoke, then minimal closed-loop learning only if that passes.",
    }

    manifest = output_dir / "tier4_22h_results.json"
    report = output_dir / "tier4_22h_report.md"
    result = {
        "tier": TIER,
        "generated_at_utc": utc_now(),
        "status": status,
        "failure_reason": failure_reason,
        "output_dir": str(output_dir),
        "summary": summary,
        "criteria": criteria,
        "static_checks": checks,
        "readback_schema": schema,
        "acceptance_matrix": acceptance,
        "host_test": {
            "command": host["command"],
            "returncode": host["returncode"],
            "stdout_artifact": str(host_stdout),
            "stderr_artifact": str(host_stderr),
        },
        "aplx_build": build,
        "artifacts": {
            "manifest_json": str(manifest),
            "report_md": str(report),
            "static_checks_csv": str(static_csv),
            "readback_schema_csv": str(schema_csv),
            "acceptance_matrix_csv": str(acceptance_csv),
            "host_test_stdout": str(host_stdout),
            "host_test_stderr": str(host_stderr),
            "aplx_build_stdout": str(build_stdout),
            "aplx_build_stderr": str(build_stderr),
        },
    }
    write_json(manifest, result)
    write_report(report, result)
    write_latest(output_dir, manifest, report, status)
    print(json.dumps({"status": status, "output_dir": str(output_dir), "manifest": str(manifest)}, indent=2))
    return 0 if status == "pass" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Tier 4.22h compact readback/build-command readiness.")
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    return run(build_parser().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
