#!/usr/bin/env python3
"""Tier 4.22k Spin1API event-symbol discovery for EBRAINS custom runtime work.

Tier 4.22i failed before board execution because the EBRAINS build image did not
expose the multicast callback macro names we expected. This tier is intentionally
small and diagnostic: inspect the exact SpiNNaker toolchain/header set inside the
EBRAINS JobManager environment and compile a probe matrix for candidate callback
symbols.

Claim boundary:
- PREPARED means the source-only EBRAINS job folder is ready.
- PASS in run-hardware means the EBRAINS image exposed inspectable Spin1API
  headers, baseline TIMER/SDP callback probes compiled, and at least one real
  multicast receive callback event macro compiled.
- This is not board execution, not app loading, not learning, and not speedup
  evidence. It is the gate that decides whether custom-runtime spike receive can
  be implemented through the available Spin1API headers or whether we must use a
  different documented receive path before continuing custom-runtime learning.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"
TIER = "Tier 4.22k - Spin1API Event-Symbol Discovery"
RUNNER_REVISION = "tier4_22k_spin1api_event_discovery_20260430_0001"
DEFAULT_OUTPUT = CONTROLLED / "tier4_22k_20260430_spin1api_event_discovery_prepared"
UPLOAD_PACKAGE_NAME = "cra_422k"
STABLE_EBRAINS_UPLOAD = ROOT / "ebrains_jobs" / UPLOAD_PACKAGE_NAME
OFFICIAL_SPIN1API_SOURCE = "https://github.com/SpiNNakerManchester/spinnaker_tools/blob/master/include/spin1_api.h"
OFFICIAL_SPINNAKER_SOURCE = "https://github.com/SpiNNakerManchester/spinnaker_tools/blob/master/include/spinnaker.h"

HEADER_PATTERNS = [
    "spin1_callback_on",
    "NUM_EVENTS",
    "MC_PACKET",
    "MCPL",
    "FR_PACKET",
    "SDP_PACKET_RX",
    "TIMER_TICK",
    "USER_EVENT",
    "CC_MC_INT",
    "WITH_PAYLOAD",
]

PROBE_EVENTS = [
    {"macro": "TIMER_TICK", "kind": "baseline_timer", "real_mc_event": False},
    {"macro": "SDP_PACKET_RX", "kind": "baseline_sdp", "real_mc_event": False},
    {"macro": "MC_PACKET_RECEIVED", "kind": "official_mc_no_payload", "real_mc_event": True},
    {"macro": "MCPL_PACKET_RECEIVED", "kind": "official_mc_payload", "real_mc_event": True},
    {"macro": "MC_PACKET_RX", "kind": "legacy_or_local_guess", "real_mc_event": True},
    {"macro": "MCPL_PACKET_RX", "kind": "legacy_or_local_guess", "real_mc_event": True},
    {"macro": "FR_PACKET_RECEIVED", "kind": "official_fixed_route", "real_mc_event": False},
    {"macro": "FRPL_PACKET_RECEIVED", "kind": "official_fixed_route_payload", "real_mc_event": False},
    {"macro": "USER_EVENT", "kind": "baseline_user_event", "real_mc_event": False},
    {"macro": "CC_MC_INT", "kind": "interrupt_constant_not_api_event", "real_mc_event": False},
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def criterion(name: str, value: Any, rule: str, passed: bool, note: str = "") -> dict[str, Any]:
    return {"name": name, "value": value, "rule": rule, "passed": bool(passed), "note": note}


def markdown_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.6g}"
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, sort_keys=True)
    return str(value)


def find_tool(name: str) -> str:
    return shutil.which(name) or ""


def run_cmd(cmd: list[str], *, cwd: Path, timeout: float = 30.0) -> dict[str, Any]:
    try:
        proc = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False, timeout=timeout)
        return {
            "command": " ".join(cmd),
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": " ".join(cmd),
            "returncode": None,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "timed_out": True,
        }


def module_status(name: str) -> dict[str, Any]:
    try:
        module = __import__(name)
        return {"name": name, "available": True, "path": getattr(module, "__file__", "")}
    except Exception as exc:
        return {"name": name, "available": False, "error": f"{type(exc).__name__}: {exc}"}


def split_env_paths(value: str) -> list[Path]:
    if not value:
        return []
    pieces = re.split(r"[:;,]", value)
    return [Path(piece).expanduser() for piece in pieces if piece.strip()]


def candidate_tool_roots() -> list[Path]:
    candidates: list[Path] = []
    for key in ["SPINN_DIRS", "SPINNAKER_TOOLS", "SPINNTOOLS", "SPINN_PATH"]:
        candidates.extend(split_env_paths(os.environ.get(key, "")))
    candidates.extend(
        [
            Path("/opt/spinnaker_tools"),
            Path("/usr/local/spinnaker_tools"),
            Path.home() / "spinnaker_tools",
            Path.home() / "spinnaker" / "spinnaker_tools",
            Path("/home/jovyan/spinnaker/spinnaker_tools"),
            Path("/home/jovyan/spinnaker_tools"),
        ]
    )
    unique: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        resolved = str(path)
        if resolved not in seen:
            unique.append(path)
            seen.add(resolved)
    return unique


def detect_include_dirs() -> list[Path]:
    include_dirs: list[Path] = []
    for root in candidate_tool_roots():
        for candidate in [root / "include", root / "spin1_api", root]:
            if (candidate / "spin1_api.h").exists() or (candidate / "sark.h").exists():
                include_dirs.append(candidate)
    for key in ["C_INCLUDE_PATH", "CPATH"]:
        for path in split_env_paths(os.environ.get(key, "")):
            if (path / "spin1_api.h").exists() or (path / "sark.h").exists():
                include_dirs.append(path)
    unique: list[Path] = []
    seen: set[str] = set()
    for path in include_dirs:
        resolved = str(path.resolve()) if path.exists() else str(path)
        if resolved not in seen:
            unique.append(path)
            seen.add(resolved)
    return unique


def environment_report() -> dict[str, Any]:
    return {
        "cwd": str(Path.cwd()),
        "root": str(ROOT),
        "python": sys.executable,
        "python_version": sys.version,
        "runner_revision": RUNNER_REVISION,
        "env": {
            key: os.environ.get(key, "")
            for key in [
                "SPINN_DIRS",
                "SPINNAKER_TOOLS",
                "SPINNTOOLS",
                "SPINN_PATH",
                "C_INCLUDE_PATH",
                "CPATH",
                "PATH",
            ]
        },
        "candidate_tool_roots": [str(path) for path in candidate_tool_roots()],
        "include_dirs": [str(path) for path in detect_include_dirs()],
        "tools": {name: find_tool(name) for name in ["arm-none-eabi-gcc", "arm-none-eabi-cpp", "gcc", "cc", "make", "ybug"]},
        "modules": [module_status(name) for name in ["spinnman", "spinn_machine", "spinn_utilities"]],
        "official_reference_sources": {
            "spin1_api_h": OFFICIAL_SPIN1API_SOURCE,
            "spinnaker_h": OFFICIAL_SPINNAKER_SOURCE,
            "expected_current_mc_event_symbols": ["MC_PACKET_RECEIVED", "MCPL_PACKET_RECEIVED"],
        },
    }


def header_files(include_dirs: list[Path]) -> list[Path]:
    files: list[Path] = []
    seen: set[str] = set()
    for include_dir in include_dirs:
        if not include_dir.exists():
            continue
        for path in include_dir.rglob("*.h"):
            try:
                resolved = str(path.resolve())
            except OSError:
                resolved = str(path)
            if resolved not in seen:
                files.append(path)
                seen.add(resolved)
    return files


def collect_header_inventory(include_dirs: list[Path]) -> tuple[list[dict[str, Any]], str]:
    rows: list[dict[str, Any]] = []
    symbol_lines: list[str] = []
    pattern_re = re.compile("|".join(re.escape(pattern) for pattern in HEADER_PATTERNS))
    for path in header_files(include_dirs):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception as exc:
            rows.append({"path": str(path), "line": "", "symbol": "", "text": "", "error": f"{type(exc).__name__}: {exc}"})
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            matches = [pattern for pattern in HEADER_PATTERNS if pattern in line]
            if not matches:
                continue
            clean = line.strip()
            for match in matches:
                rows.append({"path": str(path), "line": line_number, "symbol": match, "text": clean, "error": ""})
            symbol_lines.append(f"{path}:{line_number}: {clean}")
    return rows, "\n".join(symbol_lines) + ("\n" if symbol_lines else "")


def choose_compiler() -> tuple[str, list[str]]:
    arm = find_tool("arm-none-eabi-gcc")
    if arm:
        return arm, ["-mthumb-interwork", "-march=armv5te"]
    gcc = find_tool("gcc")
    if gcc:
        return gcc, []
    cc = find_tool("cc") or "cc"
    return cc, []


def probe_source(event_macro: str) -> str:
    return f"""
#include <sark.h>
#include <spinnaker.h>
#include <spin1_api.h>

static void cra_probe_callback(uint arg0, uint arg1) {{
    (void)arg0;
    (void)arg1;
}}

void c_main(void) {{
    spin1_callback_on({event_macro}, cra_probe_callback, 0);
}}
""".lstrip()


def classify_probe(returncode: Any, stderr: str) -> str:
    if returncode == 0:
        return "compile_pass"
    lower = stderr.lower()
    if "undeclared" in lower or "not declared" in lower or "undefined" in lower:
        return "symbol_missing_or_undeclared"
    if "no such file" in lower or "cannot find" in lower or "not found" in lower:
        return "include_or_toolchain_missing"
    if "unrecognized" in lower or "bad value" in lower:
        return "compiler_flag_incompatible"
    return "compile_fail_other"


def compile_probe_matrix(output_dir: Path, include_dirs: list[Path]) -> tuple[list[dict[str, Any]], str, str]:
    compiler, compiler_flags = choose_compiler()
    rows: list[dict[str, Any]] = []
    stdout_chunks: list[str] = []
    stderr_chunks: list[str] = []
    with tempfile.TemporaryDirectory(prefix="cra_422k_probe_") as tmp_name:
        tmp = Path(tmp_name)
        for event in PROBE_EVENTS:
            macro = event["macro"]
            source = tmp / f"probe_{macro}.c"
            obj = tmp / f"probe_{macro}.o"
            source.write_text(probe_source(macro), encoding="utf-8")
            cmd = [compiler, "-std=gnu99", "-ffreestanding", *compiler_flags]
            for include_dir in include_dirs:
                cmd.extend(["-I", str(include_dir)])
            cmd.extend(["-c", str(source), "-o", str(obj)])
            result = run_cmd(cmd, cwd=tmp, timeout=20.0)
            status = classify_probe(result.get("returncode"), str(result.get("stderr", "")))
            rows.append(
                {
                    "macro": macro,
                    "kind": event["kind"],
                    "real_mc_event_candidate": event["real_mc_event"],
                    "compiler": compiler,
                    "returncode": result.get("returncode"),
                    "status": status,
                    "compiled": status == "compile_pass",
                    "command": result.get("command", ""),
                    "stderr_excerpt": str(result.get("stderr", ""))[-1000:],
                }
            )
            stdout_chunks.append(f"===== {macro} =====\n{result.get('stdout', '')}\n")
            stderr_chunks.append(f"===== {macro} =====\n{result.get('stderr', '')}\n")
    return rows, "\n".join(stdout_chunks), "\n".join(stderr_chunks)


def prepare_bundle(output_dir: Path) -> tuple[Path, str, dict[str, str]]:
    bundle = output_dir / "ebrains_upload_bundle" / UPLOAD_PACKAGE_NAME
    if bundle.exists():
        shutil.rmtree(bundle)
    (bundle / "experiments").mkdir(parents=True, exist_ok=True)
    script = bundle / "experiments" / "tier4_22k_spin1api_event_discovery.py"
    shutil.copy2(ROOT / "experiments" / "tier4_22k_spin1api_event_discovery.py", script)
    os.chmod(script, 0o755)
    command = f"{UPLOAD_PACKAGE_NAME}/experiments/tier4_22k_spin1api_event_discovery.py --mode run-hardware --output-dir tier4_22k_job_output"
    readme = bundle / "README_TIER4_22K_JOB.md"
    readme.write_text(
        "# Tier 4.22k EBRAINS Spin1API Event-Symbol Discovery\n\n"
        f"Upload the `{UPLOAD_PACKAGE_NAME}` folder itself so the JobManager path starts with `{UPLOAD_PACKAGE_NAME}/`.\n\n"
        "Do not upload `controlled_test_output/`, repo history, downloaded reports, or compiled binaries.\n\n"
        "Run command:\n\n"
        f"```text\n{command}\n```\n\n"
        "Download every `tier4_22k*` file after it finishes. This job does not need a board hostname; it inspects and compiles against the EBRAINS build image headers.\n",
        encoding="utf-8",
    )
    STABLE_EBRAINS_UPLOAD.parent.mkdir(parents=True, exist_ok=True)
    if STABLE_EBRAINS_UPLOAD.exists():
        shutil.rmtree(STABLE_EBRAINS_UPLOAD)
    shutil.copytree(bundle, STABLE_EBRAINS_UPLOAD)
    return bundle, command, {"upload_bundle": str(bundle), "stable_upload_folder": str(STABLE_EBRAINS_UPLOAD), "job_readme": str(readme)}


def write_report(path: Path, result: dict[str, Any]) -> None:
    summary = result.get("summary", {})
    lines = [
        "# Tier 4.22k Spin1API Event-Symbol Discovery",
        "",
        f"- Generated: `{result.get('generated_at_utc', utc_now())}`",
        f"- Mode: `{result.get('mode', summary.get('mode', 'unknown'))}`",
        f"- Status: **{str(result.get('status', 'unknown')).upper()}**",
        f"- Output directory: `{result.get('output_dir', path.parent)}`",
        "",
        "Tier 4.22k inspects the EBRAINS Spin1API build image and compiles a callback-symbol probe matrix. It exists because Tier 4.22i reached the raw custom-runtime layer and failed before board execution on callback event-symbol mismatch.",
        "",
        "## Claim Boundary",
        "",
        "- This is build-image/toolchain discovery evidence only.",
        "- It is not a board load, not a command round-trip, not learning, not speedup, and not hardware transfer of a mechanism.",
        "- If no real multicast receive event macro compiles, custom-runtime learning hardware is blocked until the receive path is repaired with documented Spin1API/SCAMP semantics.",
        "",
        "## Summary",
        "",
    ]
    for key in [
        "include_dirs_found",
        "header_inventory_rows",
        "compiler",
        "baseline_timer_compiles",
        "baseline_sdp_compiles",
        "mc_receive_event_macros_compiling",
        "custom_runtime_learning_hardware_allowed_next",
        "next_step_if_passed",
        "next_step_if_failed",
    ]:
        if key in summary:
            lines.append(f"- {key}: `{markdown_value(summary[key])}`")
    lines.extend(["", "## Criteria", "", "| Criterion | Value | Rule | Pass | Note |", "| --- | --- | --- | --- | --- |"])
    for item in result.get("criteria", []):
        lines.append(
            f"| {item['name']} | `{markdown_value(item.get('value'))}` | `{item.get('rule')}` | {'yes' if item.get('passed') else 'no'} | {item.get('note', '')} |"
        )
    artifacts = result.get("artifacts", {})
    if artifacts:
        lines.extend(["", "## Artifacts", ""])
        for key, value in artifacts.items():
            lines.append(f"- `{key}`: `{value}`")
    lines.extend(
        [
            "",
            "## Official Reference Checked",
            "",
            f"- Official `spin1_api.h`: `{OFFICIAL_SPIN1API_SOURCE}`",
            f"- Official `spinnaker.h`: `{OFFICIAL_SPINNAKER_SOURCE}`",
            "- Current official source exposes `MC_PACKET_RECEIVED` and `MCPL_PACKET_RECEIVED`; this tier checks whether the EBRAINS image exposes the same symbols.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_latest(output_dir: Path, manifest: Path, report: Path, status: str, mode: str) -> None:
    CONTROLLED.mkdir(parents=True, exist_ok=True)
    write_json(
        CONTROLLED / "tier4_22k_latest_manifest.json",
        {
            "generated_at_utc": utc_now(),
            "tier": TIER,
            "status": status,
            "mode": mode,
            "output_dir": str(output_dir),
            "manifest": str(manifest),
            "report": str(report),
            "canonical": False,
            "claim": "Latest Tier 4.22k Spin1API event-symbol discovery; not board or learning evidence.",
        },
    )


def finalize(output_dir: Path, result: dict[str, Any]) -> int:
    manifest = output_dir / "tier4_22k_results.json"
    report = output_dir / "tier4_22k_report.md"
    result.setdefault("artifacts", {})
    result["artifacts"].update({"manifest_json": str(manifest), "report_md": str(report)})
    write_json(manifest, result)
    write_report(report, result)
    write_latest(output_dir, manifest, report, str(result.get("status", "unknown")), str(result.get("mode", "unknown")))
    print(json.dumps({"status": result.get("status"), "output_dir": str(output_dir), "manifest": str(manifest), "report": str(report)}, indent=2))
    return 0 if str(result.get("status", "")).lower() in {"pass", "prepared"} else 1


def prepare(args: argparse.Namespace, output_dir: Path) -> int:
    bundle, command, artifacts = prepare_bundle(output_dir)
    criteria = [
        criterion("runner revision current", RUNNER_REVISION, "expected current source", True),
        criterion("upload bundle created", str(bundle), "exists", bundle.exists()),
        criterion("discovery runner included", str(bundle / "experiments" / "tier4_22k_spin1api_event_discovery.py"), "exists", (bundle / "experiments" / "tier4_22k_spin1api_event_discovery.py").exists()),
        criterion("run-hardware command emitted", command, "contains --mode run-hardware", "--mode run-hardware" in command),
        criterion("stable upload folder refreshed", str(STABLE_EBRAINS_UPLOAD), "exists", STABLE_EBRAINS_UPLOAD.exists()),
    ]
    status = "prepared" if all(item["passed"] for item in criteria) else "blocked"
    result = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "mode": "prepare",
        "status": status,
        "failure_reason": "" if status == "prepared" else "Failed criteria: " + ", ".join(item["name"] for item in criteria if not item["passed"]),
        "output_dir": str(output_dir),
        "summary": {
            "mode": "prepare",
            "jobmanager_command": command,
            "upload_folder": str(STABLE_EBRAINS_UPLOAD),
            "what_i_need_from_user": f"Upload {STABLE_EBRAINS_UPLOAD} to EBRAINS/JobManager and run the emitted command; download every tier4_22k* file.",
            "claim_boundary": "Prepared source-only discovery package; no hardware/build-image evidence until EBRAINS returns run-hardware artifacts.",
            "next_step_if_passed": "Run the emitted EBRAINS command and ingest returned Tier 4.22k files.",
        },
        "criteria": criteria,
        "artifacts": artifacts,
    }
    return finalize(output_dir, result)


def run_hardware(args: argparse.Namespace, output_dir: Path) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    env_report = environment_report()
    include_dirs = detect_include_dirs()
    inventory, symbols = collect_header_inventory(include_dirs)
    probe_rows, probe_stdout, probe_stderr = compile_probe_matrix(output_dir, include_dirs)

    env_path = output_dir / "tier4_22k_environment.json"
    inventory_csv = output_dir / "tier4_22k_header_inventory.csv"
    symbols_txt = output_dir / "tier4_22k_spin1api_symbols.txt"
    probe_csv = output_dir / "tier4_22k_probe_matrix.csv"
    probe_stdout_path = output_dir / "tier4_22k_probe_build_stdout.txt"
    probe_stderr_path = output_dir / "tier4_22k_probe_build_stderr.txt"
    write_json(env_path, env_report)
    write_csv(inventory_csv, inventory)
    symbols_txt.write_text(symbols, encoding="utf-8")
    write_csv(probe_csv, probe_rows)
    probe_stdout_path.write_text(probe_stdout, encoding="utf-8")
    probe_stderr_path.write_text(probe_stderr, encoding="utf-8")

    compiled = {row["macro"] for row in probe_rows if row.get("compiled")}
    mc_compiled = [row["macro"] for row in probe_rows if row.get("real_mc_event_candidate") and row.get("compiled")]
    compiler, _flags = choose_compiler()
    baseline_timer = "TIMER_TICK" in compiled
    baseline_sdp = "SDP_PACKET_RX" in compiled
    spin1_callback_rows = [row for row in inventory if row.get("symbol") == "spin1_callback_on"]
    expected_symbols_in_headers = [symbol for symbol in ["MC_PACKET_RECEIVED", "MCPL_PACKET_RECEIVED"] if any(row.get("symbol") in {"MC_PACKET", "MCPL"} and symbol in str(row.get("text", "")) for row in inventory)]

    criteria = [
        criterion("runner revision current", RUNNER_REVISION, "expected current source", True),
        criterion("include dirs found", len(include_dirs), ">= 1", len(include_dirs) >= 1),
        criterion("spin1_callback_on found in headers", len(spin1_callback_rows), ">= 1", len(spin1_callback_rows) >= 1),
        criterion("TIMER_TICK callback probe compiles", baseline_timer, "True", baseline_timer),
        criterion("SDP_PACKET_RX callback probe compiles", baseline_sdp, "True", baseline_sdp),
        criterion("official MC receive symbol visible in header inventory", expected_symbols_in_headers, "contains MC_PACKET_RECEIVED or MCPL_PACKET_RECEIVED", bool(expected_symbols_in_headers)),
        criterion("real MC receive event callback probe compiles", mc_compiled, "at least one real MC receive candidate compiles", bool(mc_compiled)),
    ]
    status = "pass" if all(item["passed"] for item in criteria) else "fail"
    result = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "mode": "run-hardware",
        "status": status,
        "failure_reason": "" if status == "pass" else "Failed criteria: " + ", ".join(item["name"] for item in criteria if not item["passed"]),
        "output_dir": str(output_dir),
        "summary": {
            "mode": "run-hardware",
            "include_dirs_found": [str(path) for path in include_dirs],
            "header_inventory_rows": len(inventory),
            "compiler": compiler,
            "baseline_timer_compiles": baseline_timer,
            "baseline_sdp_compiles": baseline_sdp,
            "official_symbols_seen_in_headers": expected_symbols_in_headers,
            "mc_receive_event_macros_compiling": mc_compiled,
            "custom_runtime_learning_hardware_allowed_next": status == "pass",
            "claim_boundary": "Build-image/header discovery only; not board load or learning evidence.",
            "next_step_if_passed": "Patch the custom runtime to use the compiling MC receive event macro, regenerate Tier 4.22i, then rerun board load/CMD_READ_STATE smoke.",
            "next_step_if_failed": "Do not run custom-runtime learning. Inspect tier4_22k_header_inventory.csv and pick a documented alternate receive path or toolchain include fix first.",
        },
        "criteria": criteria,
        "environment": env_report,
        "probe_matrix": probe_rows,
        "artifacts": {
            "environment_json": str(env_path),
            "header_inventory_csv": str(inventory_csv),
            "spin1api_symbols_txt": str(symbols_txt),
            "probe_matrix_csv": str(probe_csv),
            "probe_build_stdout": str(probe_stdout_path),
            "probe_build_stderr": str(probe_stderr_path),
        },
    }
    return finalize(output_dir, result)


def ingest(args: argparse.Namespace, output_dir: Path) -> int:
    if args.ingest_dir is None:
        raise SystemExit("--ingest-dir is required in ingest mode")
    source = args.ingest_dir.resolve()
    if not source.exists():
        raise SystemExit(f"ingest dir does not exist: {source}")
    output_dir.mkdir(parents=True, exist_ok=True)
    ingest_items = [item for item in source.iterdir() if item.name.startswith("tier4_22k")]
    if not ingest_items:
        raise SystemExit(f"no tier4_22k artifacts found in ingest dir: {source}")
    for item in ingest_items:
        target = output_dir / item.name
        if item.is_dir():
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(item, target)
        else:
            shutil.copy2(item, target)
    manifest = output_dir / "tier4_22k_results.json"
    if not manifest.exists():
        raise SystemExit(f"missing tier4_22k_results.json in ingested files: {source}")
    data = read_json(manifest)
    data["mode"] = data.get("mode", "ingest")
    data["output_dir"] = str(output_dir)
    report = output_dir / "tier4_22k_report.md"
    if not report.exists():
        write_report(report, data)
    write_latest(output_dir, manifest, report, str(data.get("status", "unknown")), "ingest")
    print(json.dumps({"status": data.get("status"), "output_dir": str(output_dir), "manifest": str(manifest)}, indent=2))
    return 0 if str(data.get("status", "")).lower() in {"pass", "prepared"} else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Tier 4.22k Spin1API event-symbol discovery.")
    parser.add_argument("--mode", choices=["prepare", "run-hardware", "ingest"], default="prepare")
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--ingest-dir", type=Path, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    default = DEFAULT_OUTPUT if args.mode == "prepare" else CONTROLLED / f"tier4_22k_{stamp}_{args.mode.replace('-', '_')}"
    output_dir = (args.output_dir or default).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if args.mode == "prepare":
        return prepare(args, output_dir)
    if args.mode == "run-hardware":
        return run_hardware(args, output_dir)
    if args.mode == "ingest":
        return ingest(args, output_dir)
    raise AssertionError(args.mode)


if __name__ == "__main__":
    raise SystemExit(main())
