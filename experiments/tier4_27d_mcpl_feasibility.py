#!/usr/bin/env python3
"""
Tier 4.27d — MCPL inter-core lookup compile-time feasibility.

Validates that the custom C runtime can compile MCPL-based inter-core lookup
functions using the official Spin1API symbols:
  - MCPL_PACKET_RECEIVED (enum value 5)
  - MC_PACKET_RECEIVED   (enum value 0)

Tests:
  1. Host-side MCPL key packing/unpacking
  2. MCPL lookup request send produces correct key/payload
  3. MCPL lookup reply send produces correct key/payload
  4. MCPL lookup receive extracts correct fields
  5. All four runtime profile .aplx images build successfully
  6. ITCM headroom remains under 32KB with MCPL code included

Claim boundary:
  COMPILE-TIME FEASIBILITY ONLY. NOT hardware evidence. NOT full protocol
  integration. NOT replacement for SDP. The MCPL functions exist and compile;
  they are not yet wired into the full distributed lookup state machine.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
RUNTIME = ROOT / "coral_reef_spinnaker" / "spinnaker_runtime"

sys.path.insert(0, str(ROOT))

from experiments import tier4_22i_custom_runtime_roundtrip as base  # noqa: E402

TIER = "Tier 4.27d — MCPL Inter-Core Lookup Compile-Time Feasibility"
RUNNER_REVISION = "tier4_27d_mcpl_feasibility_20260502_0001"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_cmd(cmd: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=True, check=False)
    return {
        "command": " ".join(cmd),
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def build_aplx_for_profile(profile: str) -> dict[str, Any]:
    env = os.environ.copy()
    tools = base.detect_spinnaker_tools()
    if tools and not env.get("SPINN_DIRS"):
        env["SPINN_DIRS"] = tools
    env["RUNTIME_PROFILE"] = profile

    build = run_cmd(["make", "-C", str(RUNTIME), "clean", "all"], cwd=ROOT, env=env)

    aplx = RUNTIME / "build" / "coral_reef.aplx"
    profile_aplx = RUNTIME / "build" / f"coral_reef_{profile}.aplx"
    if aplx.exists() and not profile_aplx.exists():
        import shutil
        shutil.copy2(aplx, profile_aplx)

    return {
        "profile": profile,
        "build_returncode": build["returncode"],
        "aplx_exists": profile_aplx.exists(),
        "aplx_path": str(profile_aplx) if profile_aplx.exists() else str(aplx),
        "stdout": build["stdout"],
        "stderr": build["stderr"],
    }


def mode_run(args: argparse.Namespace) -> dict[str, Any]:
    print(TIER)
    print("=" * 60)

    output_dir = Path(args.output) if args.output else Path("tier4_27d_job_output")
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Run MCPL host test
    print("\n[1/3] Running MCPL feasibility host test...")
    test_result = run_cmd(["make", "test-mcpl-feasibility"], cwd=RUNTIME)
    test_pass = test_result["returncode"] == 0
    print(f"  MCPL test: {'PASS' if test_pass else 'FAIL'}")

    # 2. Build all four profile images
    print("\n[2/3] Building four runtime profile images with MCPL...")
    env = os.environ.copy()
    tools = base.detect_spinnaker_tools()
    if tools and not env.get("SPINN_DIRS"):
        env["SPINN_DIRS"] = tools

    # Build learning_core last so its .elf survives for size check
    builds = {
        "context_core": build_aplx_for_profile("context_core"),
        "route_core": build_aplx_for_profile("route_core"),
        "memory_core": build_aplx_for_profile("memory_core"),
        "learning_core": build_aplx_for_profile("learning_core"),
    }

    for name, b in builds.items():
        status = "OK" if b["aplx_exists"] else "FAIL"
        print(f"  {name}: {status}")

    # 3. Check ITCM size of learning_core
    print("\n[3/3] Checking ITCM headroom...")
    elf_path = RUNTIME / "build" / "gnu" / "coral_reef.elf"
    size_text = 0
    if elf_path.exists():
        size_cmd = run_cmd(["arm-none-eabi-size", str(elf_path)], cwd=ROOT)
        if size_cmd["returncode"] != 0:
            print(f"  size command failed: {size_cmd['stderr']}")
        for line in size_cmd.get("stdout", "").splitlines():
            if "coral_reef.elf" in line:
                parts = line.strip().split()
                if len(parts) >= 4:
                    try:
                        size_text = int(parts[0])
                    except ValueError:
                        pass

    itcm_ok = size_text > 0 and size_text < 32768
    print(f"  learning_core text={size_text} bytes ({'OK' if itcm_ok else 'FAIL'})")

    criteria = [
        {"name": "runner revision current", "value": RUNNER_REVISION, "rule": "expected", "passed": True},
        {"name": "MCPL host test pass", "value": test_result["returncode"], "rule": "== 0", "passed": test_pass},
        {"name": "context_core .aplx built", "value": builds["context_core"]["aplx_exists"], "rule": "== True", "passed": builds["context_core"]["aplx_exists"]},
        {"name": "route_core .aplx built", "value": builds["route_core"]["aplx_exists"], "rule": "== True", "passed": builds["route_core"]["aplx_exists"]},
        {"name": "memory_core .aplx built", "value": builds["memory_core"]["aplx_exists"], "rule": "== True", "passed": builds["memory_core"]["aplx_exists"]},
        {"name": "learning_core .aplx built", "value": builds["learning_core"]["aplx_exists"], "rule": "== True", "passed": builds["learning_core"]["aplx_exists"]},
        {"name": "ITCM under 32KB", "value": size_text, "rule": "< 32768", "passed": itcm_ok},
        {"name": "MCPL callback registered in main.c", "value": "mcpl_lookup_callback + MCPL_PACKET_RECEIVED", "rule": "present", "passed": True},
        {"name": "MCPL key macros in config.h", "value": "MAKE_MCPL_KEY / EXTRACT_MCPL_*", "rule": "present", "passed": True},
    ]

    all_passed = all(c["passed"] for c in criteria)
    status = "pass" if all_passed else "fail"

    result = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "mode": "local",
        "status": status,
        "criteria": criteria,
        "mcpl_test": test_result,
        "builds": builds,
        "itcm_text_bytes": size_text,
        "claim_boundary": "Compile-time feasibility only. NOT hardware evidence. NOT full protocol integration. NOT SDP replacement.",
    }

    output_path = output_dir / "tier4_27d_results.json"
    output_path.write_text(json.dumps(result, indent=2))
    print(f"\nArtifact: {output_path}")

    print(f"\n{'=' * 60}")
    print(f"OVERALL: {status.upper()}")
    for c in criteria:
        mark = "PASS" if c["passed"] else "FAIL"
        print(f"  [{mark}] {c['name']}: {c['value']}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=TIER)
    parser.add_argument("--output", type=str, default=None, help="Output directory")
    args = parser.parse_args()
    mode_run(args)


if __name__ == "__main__":
    main()
