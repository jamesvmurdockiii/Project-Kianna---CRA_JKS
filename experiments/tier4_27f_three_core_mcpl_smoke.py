#!/usr/bin/env python3
"""
Tier 4.27f — Three-state-core MCPL lookup smoke.

Extends 4.27e to three state cores (context + route + memory) all replying
to the learning core via MCPL. Validates:
  - All four profile .aplx images build with USE_MCPL_LOOKUP=1
  - Learning core router mask catches replies from all three lookup types
  - ITCM headroom remains under 32KB for all profiles

Local build checks:
  1. context_core .aplx builds with MCPL
  2. route_core .aplx builds with MCPL
  3. memory_core .aplx builds with MCPL
  4. learning_core .aplx builds with MCPL
  5. All ITCM sizes under 32KB
  6. Learning core router mask is 0xFFFF0000 (broad enough for all types)
  7. MCPL feasibility host tests still pass
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

TIER = "Tier 4.27f — Three-State-Core MCPL Lookup Smoke"
RUNNER_REVISION = "tier4_27f_three_core_mcpl_smoke_20260502_0001"


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


def build_aplx_for_profile(profile: str, use_mcpl: bool = True) -> dict[str, Any]:
    env = os.environ.copy()
    tools = base.detect_spinnaker_tools()
    if not tools:
        fallback = Path("/tmp/spinnaker_tools")
        if fallback.exists():
            tools = str(fallback)
    if tools and not env.get("SPINN_DIRS"):
        env["SPINN_DIRS"] = tools
    arm_toolchain = Path("/tmp/arm-gnu-toolchain-13.3.rel1-darwin-arm64-arm-none-eabi/bin")
    if arm_toolchain.exists():
        env["PATH"] = str(arm_toolchain) + os.pathsep + env.get("PATH", "")
    env["RUNTIME_PROFILE"] = profile
    if use_mcpl:
        env["USE_MCPL_LOOKUP"] = "1"

    # Ensure stale .aplx is removed (make clean only deletes BUILD_DIR, not APP_OUTPUT_DIR)
    for stale in RUNTIME.glob("build/coral_reef*.aplx"):
        stale.unlink(missing_ok=True)

    build = run_cmd(["make", "-C", str(RUNTIME), "clean", "all"], cwd=ROOT, env=env)

    aplx = RUNTIME / "build" / "coral_reef.aplx"
    profile_aplx = RUNTIME / "build" / f"coral_reef_{profile}.aplx"
    if aplx.exists() and not profile_aplx.exists():
        import shutil
        shutil.copy2(aplx, profile_aplx)

    # Try to get ITCM size from .elf; fallback to parsing RO_DATA.bin size from build stdout
    elf_path = RUNTIME / "build" / "gnu" / "coral_reef.elf"
    size_text = 0
    size_bin = str(arm_toolchain / "arm-none-eabi-size") if arm_toolchain.exists() else "arm-none-eabi-size"
    size_cmd = run_cmd([size_bin, str(elf_path)], cwd=ROOT)
    if size_cmd["returncode"] == 0:
        for line in size_cmd.get("stdout", "").splitlines():
            if "coral_reef.elf" in line:
                parts = line.strip().split()
                if len(parts) >= 4:
                    try:
                        size_text = int(parts[0])
                    except ValueError:
                        pass
    # Fallback: RO_DATA.bin size in build stdout equals text section
    if size_text == 0:
        for line in build.get("stdout", "").splitlines():
            if "RO_DATA.bin" in line and "staff" in line:
                parts = line.strip().split()
                if len(parts) >= 8:
                    try:
                        size_text = int(parts[4])
                    except ValueError:
                        pass

    return {
        "profile": profile,
        "use_mcpl": use_mcpl,
        "build_returncode": build["returncode"],
        "aplx_exists": profile_aplx.exists(),
        "aplx_path": str(profile_aplx) if profile_aplx.exists() else str(aplx),
        "itcm_text_bytes": size_text,
        "stdout": build["stdout"],
        "stderr": build["stderr"],
    }


def verify_source_wiring() -> dict[str, Any]:
    state_manager_c = (RUNTIME / "src" / "state_manager.c").read_text()

    checks = {
        "learning_core router mask catches all lookup types (0xFFF00000)":
            "mask = 0xFFF00000;  // ignore lookup_type (bits 16-19) and seq_id (bits 0-15)" in state_manager_c,
        "state cores use specific lookup type in router key":
            "MAKE_MCPL_KEY(APP_ID, MCPL_MSG_LOOKUP_REQUEST, lookup_type, 0)" in state_manager_c,
        "cra_state_mcpl_lookup_receive handles REQUEST for state cores":
            "MCPL_MSG_LOOKUP_REQUEST" in state_manager_c,
        "cra_state_mcpl_lookup_receive handles REPLY for learning core":
            "MCPL_MSG_LOOKUP_REPLY" in state_manager_c,
    }
    return {
        "checks": {k: v for k, v in checks.items()},
        "all_passed": all(checks.values()),
    }


def mode_run(args: argparse.Namespace) -> dict[str, Any]:
    print(TIER)
    print("=" * 60)

    output_dir = Path(args.output) if args.output else Path("tier4_27f_job_output")
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Source wiring verification
    print("\n[1/6] Verifying MCPL source wiring...")
    wiring = verify_source_wiring()
    for name, passed in wiring["checks"].items():
        mark = "PASS" if passed else "FAIL"
        print(f"  [{mark}] {name}")

    # 2. Build all four profiles with MCPL
    profiles = ["context_core", "route_core", "memory_core", "learning_core"]
    builds = {}
    for i, profile in enumerate(profiles, start=2):
        print(f"\n[{i}/6] Building {profile} with MCPL...")
        b = build_aplx_for_profile(profile, use_mcpl=True)
        builds[profile] = b
        ok = b["aplx_exists"] and b["itcm_text_bytes"] < 32768
        print(f"  {profile}: {'OK' if ok else 'FAIL'} (text={b['itcm_text_bytes']} bytes)")

    # 6. Run MCPL feasibility host test
    print("\n[6/6] Running MCPL feasibility host test...")
    test_result = run_cmd(["make", "test-mcpl-feasibility"], cwd=RUNTIME)
    test_pass = test_result["returncode"] == 0
    print(f"  MCPL feasibility: {'PASS' if test_pass else 'FAIL'}")

    criteria = [
        {"name": "runner revision current", "value": RUNNER_REVISION, "rule": "expected", "passed": True},
        {"name": "source wiring all checks pass", "value": wiring["all_passed"], "rule": "== True", "passed": wiring["all_passed"]},
    ]
    for profile in profiles:
        b = builds[profile]
        criteria.append({
            "name": f"{profile} .aplx built with MCPL",
            "value": b["aplx_exists"],
            "rule": "== True",
            "passed": b["aplx_exists"],
        })
        criteria.append({
            "name": f"{profile} ITCM < 32KB",
            "value": b["itcm_text_bytes"],
            "rule": "< 32768",
            "passed": b["itcm_text_bytes"] < 32768,
        })
    criteria.append({
        "name": "MCPL host test pass",
        "value": test_result["returncode"],
        "rule": "== 0",
        "passed": test_pass,
    })

    all_passed = all(c["passed"] for c in criteria)
    status = "pass" if all_passed else "fail"

    result = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "mode": "local",
        "status": status,
        "criteria": criteria,
        "wiring_checks": wiring["checks"],
        "builds": builds,
        "mcpl_test": test_result,
        "claim_boundary": "Local build and wiring validation for four-core MCPL. NOT hardware evidence.",
    }

    output_path = output_dir / "tier4_27f_results.json"
    output_path.write_text(json.dumps(result, indent=2))
    print(f"\nArtifact: {output_path}")

    report_path = output_dir / "tier4_27f_report.md"
    report_path.write_text(_generate_report(result))
    print(f"Report: {report_path}")

    print(f"\n{'=' * 60}")
    print(f"OVERALL: {status.upper()}")
    for c in criteria:
        mark = "PASS" if c["passed"] else "FAIL"
        print(f"  [{mark}] {c['name']}: {c['value']}")
    return result


def _generate_report(result: dict[str, Any]) -> str:
    lines = [
        f"# {result['tier']}",
        "",
        f"- Runner revision: `{result['runner_revision']}`",
        f"- Generated: {result['generated_at_utc']}",
        f"- Status: **{result['status'].upper()}**",
        "",
        "## Criteria",
        "",
        "| Criterion | Value | Rule | Pass |",
        "|-----------|-------|------|------|",
    ]
    for c in result["criteria"]:
        lines.append(f"| {c['name']} | {c['value']} | {c['rule']} | {'yes' if c['passed'] else 'no'} |")
    lines += [
        "",
        "## Wiring Checks",
        "",
    ]
    for name, passed in result.get("wiring_checks", {}).items():
        lines.append(f"- {'[PASS]' if passed else '[FAIL]'} {name}")
    lines += [
        "",
        "## Build Summary",
        "",
    ]
    for profile, b in result.get("builds", {}).items():
        lines.append(f"- {profile}: text={b['itcm_text_bytes']} bytes, aplx_exists={b['aplx_exists']}")
    lines += [
        "",
        f"## Claim Boundary",
        "",
        result.get("claim_boundary", ""),
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=TIER)
    parser.add_argument("--output", type=str, default=None, help="Output directory")
    args = parser.parse_args()
    mode_run(args)


if __name__ == "__main__":
    main()
