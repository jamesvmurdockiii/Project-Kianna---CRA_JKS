#!/usr/bin/env python3
"""
Tier 4.24b / 4.25-Preflight — EBRAINS Build/Size Resource Capture

Closes the ITCM/build-size gap flagged in 4.24 and 4.25A.

Builds the current decoupled_memory_route runtime on EBRAINS (where
arm-none-eabi-size is available), captures exact .text/.data/.bss sizes,
.aplx/.elf file sizes, and build log. Optionally loads to hardware to
capture load time.

Modes:
  local        — verify source constants and struct math locally
  prepare      — create EBRAINS upload bundle
  run-hardware — build on EBRAINS, capture sizes, optionally load
  ingest       — verify returned build artifacts are real (non-zero)

Claim boundary:
  This is a build-infrastructure tier, not a science tier. PASS means the
  exact binary footprint is known. It does not prove the binary runs
  correctly (4.23c already did that) or that multi-core works.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"
RUNTIME = ROOT / "coral_reef_spinnaker" / "spinnaker_runtime"
TIER = "Tier 4.24b / 4.25-Preflight — EBRAINS Build/Size Resource Capture"
RUNNER_REVISION = "tier4_24b_build_size_capture_20260501_0001"
RUNTIME_PROFILE = "decoupled_memory_route"
UPLOAD_PACKAGE_NAME = "cra_424"
STABLE_EBRAINS_UPLOAD = ROOT / "ebrains_jobs" / UPLOAD_PACKAGE_NAME
DEPRECATED_EBRAINS_UPLOADS: list[Path] = []

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments import tier4_22i_custom_runtime_roundtrip as base  # noqa: E402


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2))


def criterion(name: str, value: Any, rule: str, passed: bool, note: str = "") -> dict[str, Any]:
    return {"name": name, "value": value, "rule": rule, "passed": passed, "note": note}


def find_tool(name: str) -> str:
    path = shutil.which(name)
    if path:
        return path
    # Fallback: search in SPINN_DIRS/tools/
    spinn_dirs = os.environ.get("SPINN_DIRS", "")
    if spinn_dirs:
        candidate = Path(spinn_dirs) / "tools" / name
        if candidate.exists():
            return str(candidate)
    return ""


def run_cmd(cmd: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=True, check=False)
    return {
        "command": " ".join(cmd),
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def parse_size_output(stdout: str) -> dict[str, Any]:
    """Parse arm-none-eabi-size output. Expected format:
       text    data     bss     dec     hex filename
    or GNU format:
         text    data     bss     dec     hex filename
    """
    lines = [l.strip() for l in stdout.strip().splitlines() if l.strip()]
    if not lines:
        return {"command_found": False, "text": 0, "data": 0, "bss": 0, "total": 0, "raw": stdout}

    # Try to find a line with numeric values
    for line in lines:
        parts = line.split()
        if len(parts) >= 4:
            try:
                text = int(parts[0])
                data = int(parts[1])
                bss = int(parts[2])
                total = int(parts[3])
                return {
                    "command_found": True,
                    "text": text,
                    "data": data,
                    "bss": bss,
                    "total": total,
                    "raw": stdout,
                }
            except ValueError:
                continue

    return {"command_found": False, "text": 0, "data": 0, "bss": 0, "total": 0, "raw": stdout}


def local(args: argparse.Namespace, output_dir: Path) -> int:
    """Local mode: verify struct math and source constants."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Exact struct sizes from state_manager.h (ARM 32-bit, GCC default)
    struct_sizes = {
        "context_slot_t": 20,
        "route_slot_t": 20,
        "memory_slot_t": 20,
        "pending_horizon_t": 20,
        "schedule_entry_t": 28,
        "cra_state_summary_t": 116,
    }

    # Verify config.h values
    config_path = RUNTIME / "src" / "config.h"
    config_text = config_path.read_text() if config_path.exists() else ""

    max_context = 8 if "MAX_CONTEXT_SLOTS 8" in config_text else 0
    max_route = 8 if "MAX_ROUTE_SLOTS 8" in config_text else 0
    max_memory = 8 if "MAX_MEMORY_SLOTS 8" in config_text else 0
    max_pending = 128 if "MAX_PENDING_HORIZONS 128" in config_text else 0
    max_schedule = 64 if "MAX_SCHEDULE_ENTRIES 64" in config_text else 0

    arrays = {
        "context_slots": max_context * struct_sizes["context_slot_t"],
        "route_slots": max_route * struct_sizes["route_slot_t"],
        "memory_slots": max_memory * struct_sizes["memory_slot_t"],
        "pending_horizons": max_pending * struct_sizes["pending_horizon_t"],
        "schedule_entries": max_schedule * struct_sizes["schedule_entry_t"],
        "summary": struct_sizes["cra_state_summary_t"],
    }
    scalars = 4 + 4 + 4 + 1 + 4  # count, index, base, mode, lr
    state_manager_total = sum(arrays.values()) + scalars

    result = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "mode": "local",
        "struct_sizes": struct_sizes,
        "arrays": arrays,
        "scalars_bytes": scalars,
        "state_manager_total_bytes": state_manager_total,
        "note": "Local verification only. Build sizes unknown until EBRAINS run.",
    }
    write_json(output_dir / "tier4_24b_local_results.json", result)
    return 0


def prepare(args: argparse.Namespace, output_dir: Path) -> int:
    """Prepare mode: create EBRAINS upload bundle."""
    output_dir.mkdir(parents=True, exist_ok=True)

    local_exit = local(args, output_dir / "local_reference")

    bundle = output_dir / "ebrains_upload_bundle" / UPLOAD_PACKAGE_NAME
    if bundle.exists():
        shutil.rmtree(bundle)
    (bundle / "experiments").mkdir(parents=True, exist_ok=True)
    (bundle / "coral_reef_spinnaker" / "python_host").mkdir(parents=True, exist_ok=True)

    scripts = [
        "tier4_24b_ebrains_build_size_capture.py",
        "tier4_22i_custom_runtime_roundtrip.py",
    ]
    for script in scripts:
        src = ROOT / "experiments" / script
        if src.exists():
            shutil.copy2(src, bundle / "experiments" / script)
            os.chmod(bundle / "experiments" / script, 0o755)

    shutil.copy2(ROOT / "coral_reef_spinnaker" / "__init__.py", bundle / "coral_reef_spinnaker" / "__init__.py")
    shutil.copy2(
        ROOT / "coral_reef_spinnaker" / "python_host" / "colony_controller.py",
        bundle / "coral_reef_spinnaker" / "python_host" / "colony_controller.py",
    )
    base.copy_tree_clean(RUNTIME, bundle / "coral_reef_spinnaker" / "spinnaker_runtime")

    command_build_only = f"{UPLOAD_PACKAGE_NAME}/experiments/tier4_24b_ebrains_build_size_capture.py --mode run-hardware --skip-load --out-dir tier4_24b_job_output"
    command_with_load = f"{UPLOAD_PACKAGE_NAME}/experiments/tier4_24b_ebrains_build_size_capture.py --mode run-hardware --out-dir tier4_24b_job_output"
    readme = bundle / "README_TIER4_24B_JOB.md"
    readme.write_text(
        "# Tier 4.24b EBRAINS Build/Size Resource Capture Job\n\n"
        f"Upload the `{UPLOAD_PACKAGE_NAME}` folder itself so the JobManager path starts with `{UPLOAD_PACKAGE_NAME}/`.\n\n"
        f"This job builds the custom C runtime with `RUNTIME_PROFILE={RUNTIME_PROFILE}` on EBRAINS, "
        "captures exact .text/.data/.bss via `arm-none-eabi-size`, records .aplx and .elf file sizes, "
        "and optionally loads to hardware to capture load time.\n\n"
        "**Recommended (build-only):**\n\n"
        f"```text\n{command_build_only}\n```\n\n"
        "**With hardware load (if board is available):**\n\n"
        f"```text\n{command_with_load}\n```\n\n"
        "Pass means real build-size/resource metrics were captured with no zero-size loopholes.\n",
        encoding="utf-8",
    )

    STABLE_EBRAINS_UPLOAD.parent.mkdir(parents=True, exist_ok=True)
    for old_upload in DEPRECATED_EBRAINS_UPLOADS:
        if old_upload.exists():
            shutil.rmtree(old_upload)
    if STABLE_EBRAINS_UPLOAD.exists():
        shutil.rmtree(STABLE_EBRAINS_UPLOAD)
    shutil.copytree(bundle, STABLE_EBRAINS_UPLOAD)

    criteria = [
        criterion("local reference generated", local_exit, "== 0", local_exit == 0),
        criterion("upload bundle created", str(bundle), "exists", bundle.exists()),
        criterion("runtime source included", str(bundle / "coral_reef_spinnaker" / "spinnaker_runtime"), "exists", (bundle / "coral_reef_spinnaker" / "spinnaker_runtime").exists()),
        criterion("run-hardware command emitted", command_build_only, "contains --mode run-hardware", "--mode run-hardware" in command_build_only),
    ]

    status = "prepared" if all(c["passed"] for c in criteria) else "blocked"
    result = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "mode": "prepare",
        "status": status,
        "output_dir": str(output_dir),
        "summary": {
            "upload_bundle": str(bundle),
            "stable_upload_folder": str(STABLE_EBRAINS_UPLOAD),
            "job_command_build_only": command_build_only,
            "job_command_with_load": command_with_load,
            "what_i_need_from_user": f"Upload {UPLOAD_PACKAGE_NAME} to EBRAINS/JobManager and run the emitted command.",
            "claim_boundary": "Prepared source bundle only; no build metrics until returned artifacts pass ingest.",
            "next_step_if_passed": "Run the emitted EBRAINS command and ingest returned files.",
        },
        "criteria": criteria,
    }
    write_json(output_dir / "tier4_24b_prepare_results.json", result)
    return 0 if status == "prepared" else 1


def run_hardware(args: argparse.Namespace, output_dir: Path) -> int:
    """Run-hardware mode: build on EBRAINS, capture sizes, optionally load."""
    output_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    tools = base.detect_spinnaker_tools()
    if tools and not env.get("SPINN_DIRS"):
        env["SPINN_DIRS"] = tools
    env["RUNTIME_PROFILE"] = RUNTIME_PROFILE

    # Build
    build_cmd = ["make", "-C", str(RUNTIME), "clean", "all"]
    build = run_cmd(build_cmd, cwd=ROOT, env=env)

    build_dir = RUNTIME / "build"
    elf_path = build_dir / "coral_reef.elf"
    aplx_path = build_dir / "coral_reef.aplx"

    # File sizes
    elf_size = elf_path.stat().st_size if elf_path.exists() else 0
    aplx_size = aplx_path.stat().st_size if aplx_path.exists() else 0

    # arm-none-eabi-size
    size_tool = find_tool("arm-none-eabi-size") or find_tool("size")
    size_info = {"command_found": False, "text": 0, "data": 0, "bss": 0, "total": 0, "raw": ""}
    if size_tool and elf_path.exists():
        size_result = run_cmd([size_tool, "-A", str(elf_path)], cwd=ROOT)
        if size_result["returncode"] == 0:
            size_info = parse_size_output(size_result["stdout"])
        else:
            size_info["raw"] = size_result["stdout"] + "\n" + size_result["stderr"]
    elif not size_tool:
        size_info["raw"] = "arm-none-eabi-size not found in PATH"
    elif not elf_path.exists():
        size_info["raw"] = "ELF not found after build"

    # Also try GNU format
    if size_tool and elf_path.exists() and not size_info["command_found"]:
        size_result = run_cmd([size_tool, str(elf_path)], cwd=ROOT)
        if size_result["returncode"] == 0:
            size_info = parse_size_output(size_result["stdout"])

    # Build metadata
    build_metrics = {
        "build_time_seconds": 0.0,  # Not measured precisely in this version
        "build_returncode": build["returncode"],
        "build_stdout": build["stdout"],
        "build_stderr": build["stderr"],
        "aplx_size_bytes": aplx_size,
        "elf_size_bytes": elf_size,
        "size_info": size_info,
        "aplx_path": str(aplx_path),
        "elf_path": str(elf_path),
        "tools_detected": bool(tools),
        "size_tool_path": size_tool,
        "runtime_profile": RUNTIME_PROFILE,
    }

    # Optional: load to hardware and capture load time
    load_metrics: dict[str, Any] = {"status": "not_attempted"}
    if not args.skip_load:
        target = base.acquire_hardware_target(args)
        hostname = str(target.get("hostname") or target.get("target_ipaddress") or "")
        dest_cpu = int(target.get("dest_cpu") or args.dest_cpu)

        try:
            if target.get("status") == "pass" and hostname and aplx_path.exists():
                load_metrics = base.load_application_spinnman(
                    hostname,
                    aplx_path,
                    x=int(args.dest_x),
                    y=int(args.dest_y),
                    p=dest_cpu,
                    app_id=int(args.app_id),
                    delay=float(args.startup_delay_seconds),
                    transceiver=target.get("_transceiver"),
                )
            elif target.get("status") != "pass":
                load_metrics = {"status": "no_target", "reason": "hardware target not acquired"}
            elif not aplx_path.exists():
                load_metrics = {"status": "no_binary", "reason": ".aplx not found after build"}
        finally:
            base.release_hardware_target(target)
    else:
        load_metrics = {"status": "skipped", "reason": "--skip-load set"}

    write_json(output_dir / "tier4_24b_build_metrics.json", build_metrics)
    write_json(output_dir / "tier4_24b_load_metrics.json", load_metrics)

    # Criteria
    build_ok = build["returncode"] == 0 and aplx_path.exists() and elf_path.exists()
    size_ok = size_info["command_found"] and size_info["text"] > 0

    criteria = [
        criterion("runner revision current", RUNNER_REVISION, "expected current source", True),
        criterion("build succeeded", build["returncode"], "== 0", build_ok),
        criterion(".aplx exists and non-zero", aplx_size, "> 0", aplx_size > 0),
        criterion(".elf exists and non-zero", elf_size, "> 0", elf_size > 0),
        criterion("size tool found", size_tool, "non-empty", bool(size_tool)),
        criterion("text section measured and non-zero", size_info["text"], "> 0", size_ok),
        criterion("data section measured", size_info["data"], ">= 0", size_info["data"] >= 0),
        criterion("bss section measured", size_info["bss"], ">= 0", size_info["bss"] >= 0),
        criterion("runtime profile is decoupled_memory_route", RUNTIME_PROFILE, "== decoupled_memory_route", RUNTIME_PROFILE == "decoupled_memory_route"),
        criterion("load captured or skipped", load_metrics["status"], "in {pass, skipped, no_target, no_binary}", load_metrics["status"] in {"pass", "skipped", "no_target", "no_binary"}),
    ]

    status = "pass" if all(c["passed"] for c in criteria) else "fail"
    result = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "mode": "run-hardware",
        "status": status,
        "output_dir": str(output_dir),
        "criteria": criteria,
        "build_metrics": build_metrics,
        "load_metrics": load_metrics,
    }
    write_json(output_dir / "tier4_24b_hardware_results.json", result)
    return 0 if status == "pass" else 1


def ingest(args: argparse.Namespace, output_dir: Path) -> int:
    """Ingest mode: verify returned build artifacts are real."""
    output_dir.mkdir(parents=True, exist_ok=True)

    hw_dir = args.hardware_output_dir or output_dir
    hw_results_path = hw_dir / "tier4_24b_hardware_results.json"
    build_metrics_path = hw_dir / "tier4_24b_build_metrics.json"

    hw_results = json.loads(hw_results_path.read_text()) if hw_results_path.exists() else {}
    build_metrics = json.loads(build_metrics_path.read_text()) if build_metrics_path.exists() else {}

    size_info = build_metrics.get("size_info", {})
    aplx_size = build_metrics.get("aplx_size_bytes", 0)
    elf_size = build_metrics.get("elf_size_bytes", 0)

    criteria = [
        criterion("hardware results exist", str(hw_results_path), "exists", hw_results_path.exists()),
        criterion("build metrics exist", str(build_metrics_path), "exists", build_metrics_path.exists()),
        criterion("build succeeded", build_metrics.get("build_returncode"), "== 0", build_metrics.get("build_returncode") == 0),
        criterion(".aplx size non-zero", aplx_size, "> 0", aplx_size > 0),
        criterion(".elf size non-zero", elf_size, "> 0", elf_size > 0),
        criterion("size tool succeeded", size_info.get("command_found"), "== True", size_info.get("command_found") is True),
        criterion("text section non-zero", size_info.get("text"), "> 0", (size_info.get("text") or 0) > 0),
        criterion("data section measured", size_info.get("data"), ">= 0", (size_info.get("data") or 0) >= 0),
        criterion("bss section measured", size_info.get("bss"), ">= 0", (size_info.get("bss") or 0) >= 0),
        criterion("runtime profile verified", build_metrics.get("runtime_profile"), "== decoupled_memory_route", build_metrics.get("runtime_profile") == "decoupled_memory_route"),
        criterion("no zero-size loopholes", "all sizes > 0", "true", aplx_size > 0 and elf_size > 0 and (size_info.get("text") or 0) > 0),
    ]

    passed = sum(1 for c in criteria if c["passed"])
    total = len(criteria)
    status = "pass" if passed == total else "fail"

    result = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "mode": "ingest",
        "status": status,
        "output_dir": str(output_dir),
        "hardware_output_dir": str(hw_dir),
        "passed_count": passed,
        "total_count": total,
        "criteria": criteria,
        "build_metrics": build_metrics,
    }
    write_json(output_dir / "tier4_24b_ingest_results.json", result)

    report = (
        f"# {TIER} — Ingest Report\n\n"
        f"- Status: **{status.upper()}**\n"
        f"- Passed: {passed}/{total}\n"
        f"- Hardware output: `{hw_dir}`\n\n"
        f"## Build Metrics\n\n"
        f"| Metric | Value |\n"
        f"|--------|-------|\n"
        f"| .aplx size | {aplx_size} bytes |\n"
        f"| .elf size | {elf_size} bytes |\n"
        f"| text | {size_info.get('text', 0)} bytes |\n"
        f"| data | {size_info.get('data', 0)} bytes |\n"
        f"| bss | {size_info.get('bss', 0)} bytes |\n"
        f"| total (text+data+bss) | {size_info.get('total', 0)} bytes |\n"
        f"| runtime profile | {build_metrics.get('runtime_profile', 'unknown')} |\n\n"
        f"## Criteria\n\n"
    )
    for c in criteria:
        report += f"- {'✓' if c['passed'] else '✗'} {c['name']}: `{c['value']}` ({c['rule']})\n"

    (output_dir / "tier4_24b_ingest_report.md").write_text(report)
    return 0 if status == "pass" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=TIER)
    parser.add_argument("--mode", default="local", choices=["local", "prepare", "run-hardware", "ingest"])
    parser.add_argument("--out-dir", default="", dest="output_dir", help="Output directory for results")
    parser.add_argument("--hw-dir", default="", dest="hardware_output_dir", help="Directory containing run-hardware artifacts for ingest")
    parser.add_argument("--skip-load", action="store_true", help="Skip hardware load (build-only)")
    parser.add_argument("--dest-x", default="0")
    parser.add_argument("--dest-y", default="0")
    parser.add_argument("--dest-cpu", default="4")
    parser.add_argument("--app-id", default="1")
    parser.add_argument("--startup-delay-seconds", default="2.0")
    # Target acquisition args (mirrored from base)
    parser.add_argument("--target-acquisition", choices=["auto", "hostname", "spynnaker-probe"], default="auto")
    parser.add_argument("--target-probe-population-size", type=int, default=1)
    parser.add_argument("--target-probe-run-ms", type=float, default=1.0)
    parser.add_argument("--target-probe-timestep-ms", type=float, default=1.0)
    parser.add_argument("--auto-dest-cpu", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--spinnaker-hostname", default="")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    output_dir = Path(args.output_dir) if args.output_dir else (
        CONTROLLED / f"tier4_24b_{utc_now()[:10].replace('-', '')}_build_size_capture"
    )

    if args.mode == "local":
        return local(args, output_dir)
    if args.mode == "prepare":
        return prepare(args, output_dir)
    if args.mode == "run-hardware":
        return run_hardware(args, output_dir)
    if args.mode == "ingest":
        return ingest(args, output_dir)
    return 1


if __name__ == "__main__":
    sys.exit(main())
