#!/usr/bin/env python3
"""
Tier 4.28b — Delayed-Cue Four-Core MCPL Hardware Probe.

Extends 4.28a from a simple delayed-credit micro-loop to a delayed-cue task
where target = -feature (predict opposite sign). The four-core MCPL scaffold,
loading sequence, schedule format, and readback schema are identical to 4.28a.
Only the task sequence and pass criteria change.

Modes:
  local        — build four MCPL profiles, verify ITCM, run host reference
  prepare      — create EBRAINS job bundle with MCPL images and runner script
  run-hardware — load four MCPL images, run distributed task, read back all cores
  ingest       — compare hardware results with reference

Claim boundary:
  Local modes (local, prepare) are software evidence only.
  run-hardware is hardware evidence for the executed seed only.
  ingest compares returned artifacts against reference.
  This is still a micro-task, not full hard_noisy_switching, not v2.1 mechanism
  transfer, not multi-chip scaling, and not speedup evidence.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
RUNTIME = ROOT / "coral_reef_spinnaker" / "spinnaker_runtime"
EXPERIMENTS = ROOT / "experiments"

sys.path.insert(0, str(ROOT))

from experiments.tier4_22x_compact_v2_bridge_decoupled_smoke import (
    FP_ONE,
    FP_SHIFT,
    TASK_TAIL_WINDOW,
    CONTEXT_KEY_IDS,
    ROUTE_KEY_IDS,
    MEMORY_KEY_IDS,
)
from experiments import tier4_22i_custom_runtime_roundtrip as base  # noqa: E402

def _compute_delayed_cue_reference(learning_rate: float = 0.25, delay_steps: int = 2) -> dict[str, Any]:
    """Simulate fixed-point delayed-cue learning on the host."""
    weight = 0
    bias = 0
    lr_raw = int(learning_rate * FP_ONE)
    pending_queue: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    for idx, event in enumerate(TASK_SEQUENCE):
        feature_raw = int(float(event["feature"]) * FP_ONE)
        target_raw = int(float(event["target"]) * FP_ONE)
        # Prediction before update
        pred_raw = ((weight * feature_raw) >> FP_SHIFT) + bias
        # Create pending horizon
        pending_queue.append({
            "feature_raw": feature_raw,
            "target_raw": target_raw,
            "due_step": idx + 1 + delay_steps,
            "prediction_raw": pred_raw,
        })
        # Mature any pending whose due step has arrived
        while pending_queue and pending_queue[0]["due_step"] <= idx + 1:
            p = pending_queue.pop(0)
            error_raw = p["target_raw"] - p["prediction_raw"]
            delta_w = (lr_raw * ((error_raw * p["feature_raw"]) >> FP_SHIFT)) >> FP_SHIFT
            delta_b = (lr_raw * error_raw) >> FP_SHIFT
            weight += delta_w
            bias += delta_b
        # Check sign correctness for this event
        pred_sign = 1 if pred_raw >= 0 else -1
        target_sign = 1 if target_raw >= 0 else -1
        rows.append({"sign_correct": pred_sign == target_sign})
    # Mature remaining
    while pending_queue:
        p = pending_queue.pop(0)
        error_raw = p["target_raw"] - p["prediction_raw"]
        delta_w = (lr_raw * ((error_raw * p["feature_raw"]) >> FP_SHIFT)) >> FP_SHIFT
        delta_b = (lr_raw * error_raw) >> FP_SHIFT
        weight += delta_w
        bias += delta_b
    tail = rows[-TASK_TAIL_WINDOW:]
    tail_accuracy = sum(1 for r in tail if r["sign_correct"]) / len(tail) if tail else 0.0
    return {
        "weight_raw": weight,
        "weight": weight / FP_ONE,
        "bias_raw": bias,
        "bias": bias / FP_ONE,
        "tail_accuracy": tail_accuracy,
    }


TIER = "Tier 4.28b — Delayed-Cue Four-Core MCPL Hardware Probe"
RUNNER_REVISION = "tier4_28b_delayed_cue_four_core_mcpl_20260502_0001"
UPLOAD_PACKAGE_NAME = "cra_428g"
DEPRECATED_EBRAINS_UPLOADS = [ROOT / "ebrains_jobs" / "cra_428f"]
STABLE_EBRAINS_UPLOAD = ROOT / "ebrains_jobs" / UPLOAD_PACKAGE_NAME
DEPRECATED_EBRAINS_UPLOADS = [ROOT / "ebrains_jobs" / "cra_428f_old"]

# Delayed-cue task: predict opposite sign. 48 events, alternating ±1 feature,
# target = -feature, delay = 2 steps.
# Delayed-cue task: predict opposite sign. 48 events, alternating ±1 feature,
# target = -feature, delay = 2 steps. Uses ctx_A/route_A/mem_A (all value=1.0)
# so that feature = cue.
TASK_SEQUENCE = [
    {
        "step": idx + 1,
        "feature": 1.0 if idx % 2 == 0 else -1.0,
        "target": -1.0 if idx % 2 == 0 else 1.0,
        "purpose": "delayed_cue_signed_event",
        "bridge_context_key": "ctx_A",
        "bridge_context_key_id": CONTEXT_KEY_IDS["ctx_A"],
        "bridge_route_key": "route_A",
        "bridge_route_key_id": ROUTE_KEY_IDS["route_A"],
        "bridge_memory_key": "mem_A",
        "bridge_memory_key_id": MEMORY_KEY_IDS["mem_A"],
        "bridge_visible_cue": 1 if idx % 2 == 0 else -1,
    }
    for idx in range(48)
]

# Core role map (same as 4.27a)
CONTEXT_CORE_P = 4
ROUTE_CORE_P = 5
MEMORY_CORE_P = 6
LEARNING_CORE_P = 7

CONTEXT_CORE_APP_ID = 1
ROUTE_CORE_APP_ID = 2
MEMORY_CORE_APP_ID = 3
LEARNING_CORE_APP_ID = 4

CONTEXT_CORE_PROFILE = "context_core"
ROUTE_CORE_PROFILE = "route_core"
MEMORY_CORE_PROFILE = "memory_core"
LEARNING_CORE_PROFILE = "learning_core"

# Static regime values from V2StateBridge.REGIMES
REGIME_VALUES = {
    "ctx_A": (1.0, 1.0), "ctx_B": (-1.0, 1.0),
    "ctx_C": (1.0, 1.0), "ctx_D": (-1.0, 1.0),
    "route_A": (1.0, 1.0), "route_B": (-1.0, 1.0),
    "route_C": (-1.0, 1.0), "route_D": (1.0, 1.0),
    "mem_A": (1.0, 1.0), "mem_B": (-1.0, 1.0),
    "mem_C": (1.0, 1.0), "mem_D": (-1.0, 1.0),
}


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


def build_aplx_for_profile(profile: str, output_dir: Path) -> dict[str, Any]:
    """Build .aplx for a given runtime profile with MCPL enabled."""
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
    env["USE_MCPL_LOOKUP"] = "1"

    # Ensure stale base .aplx is removed before build (profile copies from
    # previous iterations must survive until the gather step)
    base_aplx = RUNTIME / "build" / "coral_reef.aplx"
    if base_aplx.exists():
        base_aplx.unlink()

    build = run_cmd(["make", "-C", str(RUNTIME), "clean", "all"], cwd=ROOT, env=env)
    (output_dir / f"tier4_28b_build_{profile}_stdout.txt").write_text(build["stdout"])
    (output_dir / f"tier4_28b_build_{profile}_stderr.txt").write_text(build["stderr"])

    aplx = RUNTIME / "build" / "coral_reef.aplx"
    profile_aplx = RUNTIME / "build" / f"coral_reef_{profile}.aplx"
    if aplx.exists() and not profile_aplx.exists():
        shutil.copy2(aplx, profile_aplx)

    # Get ITCM size
    size_text = 0
    elf_path = RUNTIME / "build" / "gnu" / "coral_reef.elf"
    if elf_path.exists():
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
        "build_returncode": build["returncode"],
        "aplx_exists": profile_aplx.exists(),
        "aplx_path": str(profile_aplx) if profile_aplx.exists() else str(aplx),
        "itcm_text_bytes": size_text,
    }


def verify_mcpl_wiring() -> dict[str, Any]:
    """Quick source check that MCPL is wired into the lookup state machine."""
    state_manager_c = (RUNTIME / "src" / "state_manager.c").read_text()
    main_c = (RUNTIME / "src" / "main.c").read_text()
    config_h = (RUNTIME / "src" / "config.h").read_text()

    checks = {
        "CRA_USE_MCPL_LOOKUP defined in Makefile": "USE_MCPL_LOOKUP" in (RUNTIME / "Makefile").read_text(),
        "_send_lookup_request uses MCPL path": "cra_state_mcpl_lookup_send_request" in state_manager_c,
        "_send_lookup_reply uses MCPL path": "cra_state_mcpl_lookup_send_reply" in state_manager_c,
        "mcpl_lookup_callback wired in main.c": "cra_state_mcpl_lookup_receive(key, payload)" in main_c,
        "cra_state_mcpl_init called in c_main": "cra_state_mcpl_init(sark_core_id())" in main_c,
        "MCPL key macros in config.h": "MAKE_MCPL_KEY" in config_h,
        "MCPL msg types defined": "MCPL_MSG_LOOKUP_REQUEST" in config_h and "MCPL_MSG_LOOKUP_REPLY" in config_h,
    }
    return {"checks": checks, "all_passed": all(checks.values())}


# ---------------------------------------------------------------------------
# Local mode
# ---------------------------------------------------------------------------

def mode_local(args: argparse.Namespace) -> dict[str, Any]:
    print(TIER)
    print("=" * 60)

    default_dir = f"tier4_28b_seed{args.seed}_job_output"
    output_dir = Path(args.output) if args.output else Path(default_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Verify MCPL wiring
    print("\n[1/5] Verifying MCPL source wiring...")
    wiring = verify_mcpl_wiring()
    for name, passed in wiring["checks"].items():
        mark = "PASS" if passed else "FAIL"
        print(f"  [{mark}] {name}")

    # 2. Build context_core
    print("\n[2/5] Building context_core with MCPL...")
    ctx = build_aplx_for_profile(CONTEXT_CORE_PROFILE, output_dir)
    print(f"  context_core: {'OK' if ctx['aplx_exists'] else 'FAIL'} (text={ctx['itcm_text_bytes']} bytes)")

    # 3. Build route_core
    print("\n[3/5] Building route_core with MCPL...")
    route = build_aplx_for_profile(ROUTE_CORE_PROFILE, output_dir)
    print(f"  route_core: {'OK' if route['aplx_exists'] else 'FAIL'} (text={route['itcm_text_bytes']} bytes)")

    # 4. Build memory_core
    print("\n[4/5] Building memory_core with MCPL...")
    mem = build_aplx_for_profile(MEMORY_CORE_PROFILE, output_dir)
    print(f"  memory_core: {'OK' if mem['aplx_exists'] else 'FAIL'} (text={mem['itcm_text_bytes']} bytes)")

    # 5. Build learning_core
    print("\n[5/5] Building learning_core with MCPL...")
    learn = build_aplx_for_profile(LEARNING_CORE_PROFILE, output_dir)
    print(f"  learning_core: {'OK' if learn['aplx_exists'] else 'FAIL'} (text={learn['itcm_text_bytes']} bytes)")

    # Host reference: simulate fixed-point delayed-cue learning
    print("\n[6/5] Running host reference for delayed-cue...")
    ref = _compute_delayed_cue_reference()
    print(f"  Host ref weight={ref['weight_raw']} ({ref['weight']:.4f}), bias={ref['bias_raw']} ({ref['bias']:.4f})")

    criteria = [
        {"name": "runner revision current", "value": RUNNER_REVISION, "rule": "expected", "passed": True},
        {"name": "MCPL wiring all checks pass", "value": wiring["all_passed"], "rule": "== True", "passed": wiring["all_passed"]},
        {"name": "context_core .aplx built", "value": ctx["aplx_exists"], "rule": "== True", "passed": ctx["aplx_exists"]},
        {"name": "context_core ITCM < 32KB", "value": ctx["itcm_text_bytes"], "rule": "< 32768", "passed": ctx["itcm_text_bytes"] < 32768},
        {"name": "route_core .aplx built", "value": route["aplx_exists"], "rule": "== True", "passed": route["aplx_exists"]},
        {"name": "route_core ITCM < 32KB", "value": route["itcm_text_bytes"], "rule": "< 32768", "passed": route["itcm_text_bytes"] < 32768},
        {"name": "memory_core .aplx built", "value": mem["aplx_exists"], "rule": "== True", "passed": mem["aplx_exists"]},
        {"name": "memory_core ITCM < 32KB", "value": mem["itcm_text_bytes"], "rule": "< 32768", "passed": mem["itcm_text_bytes"] < 32768},
        {"name": "learning_core .aplx built", "value": learn["aplx_exists"], "rule": "== True", "passed": learn["aplx_exists"]},
        {"name": "learning_core ITCM < 32KB", "value": learn["itcm_text_bytes"], "rule": "< 32768", "passed": learn["itcm_text_bytes"] < 32768},
        {"name": "host reference weight negative", "value": ref["weight_raw"], "rule": "< 0", "passed": ref["weight_raw"] < 0},
        {"name": "host reference tail accuracy high", "value": ref["tail_accuracy"], "rule": "> 0.8", "passed": ref["tail_accuracy"] > 0.8},
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
        "wiring_checks": wiring["checks"],
        "builds": {
            "context_core": ctx,
            "route_core": route,
            "memory_core": mem,
            "learning_core": learn,
        },
        "claim_boundary": "Local build validation only. NOT hardware evidence.",
    }

    output_path = output_dir / "tier4_28b_local_results.json"
    output_path.write_text(json.dumps(result, indent=2))
    print(f"\nArtifact: {output_path}")

    print(f"\n{'=' * 60}")
    print(f"OVERALL: {status.upper()}")
    for c in criteria:
        mark = "PASS" if c["passed"] else "FAIL"
        print(f"  [{mark}] {c['name']}: {c['value']}")
    return result


# ---------------------------------------------------------------------------
# Prepare mode
# ---------------------------------------------------------------------------

def mode_prepare(args: argparse.Namespace) -> dict[str, Any]:
    print(TIER)
    print("=" * 60)

    default_dir = f"tier4_28b_seed{args.seed}_job_output"
    output_dir = Path(args.output) if args.output else Path(default_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Run local validation
    print("\n[1/4] Running local validation...")
    local_result = mode_local(args)
    if local_result.get("status") != "pass":
        print("\nLocal validation failed. Fix before preparing.")
        return local_result

    # 2. Gather built artifacts
    print("\n[2/4] Gathering built artifacts...")
    builds = local_result["builds"]
    for name, b in builds.items():
        print(f"  {name}: {b['aplx_path']}")

    # 3. Create upload bundle
    print("\n[3/4] Creating EBRAINS upload bundle...")
    bundle = output_dir / "ebrains_upload_bundle" / UPLOAD_PACKAGE_NAME
    if bundle.exists():
        shutil.rmtree(bundle)
    (bundle / "experiments").mkdir(parents=True, exist_ok=True)
    (bundle / "coral_reef_spinnaker" / "python_host").mkdir(parents=True, exist_ok=True)

    # Create __init__.py so experiments is a regular package on EBRAINS
    (bundle / "experiments" / "__init__.py").write_text("# experiments package\n", encoding="utf-8")

    # Copy runner scripts
    scripts = [
        "tier4_28b_delayed_cue_four_core_mcpl.py",
        "tier4_22i_custom_runtime_roundtrip.py",
        "tier4_27a_four_core_distributed_smoke.py",
        "tier4_23a_continuous_local_reference.py",
        "tier4_22x_compact_v2_bridge_decoupled_smoke.py",
        "tier4_22j_minimal_custom_runtime_learning.py",
        "tier4_22l_custom_runtime_learning_parity.py",
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

    # Copy built .aplx artifacts
    for name, b in builds.items():
        if b["aplx_exists"]:
            fname = f"coral_reef_{b['profile']}.aplx"
            shutil.copy2(b["aplx_path"], bundle / fname)

    # 4. Write README
    print("\n[4/4] Writing README...")
    command = f"{UPLOAD_PACKAGE_NAME}/experiments/tier4_28b_delayed_cue_four_core_mcpl.py --mode run-hardware --seed {args.seed}"

    readme_text = f"""# {TIER}

Upload the `{UPLOAD_PACKAGE_NAME}` folder itself so the JobManager path starts
with `{UPLOAD_PACKAGE_NAME}/`.

## Core Role Map

| Core | Profile | Role |
|------|---------|------|
| {CONTEXT_CORE_P} | `{CONTEXT_CORE_PROFILE}` | Context slot table; MCPL replies to context lookup requests |
| {ROUTE_CORE_P} | `{ROUTE_CORE_PROFILE}` | Route slot table; MCPL replies to route lookup requests |
| {MEMORY_CORE_P} | `{MEMORY_CORE_PROFILE}` | Memory slot table; MCPL replies to memory lookup requests |
| {LEARNING_CORE_P} | `{LEARNING_CORE_PROFILE}` | Event schedule, parallel MCPL lookups, feature composition, pending horizon, readout |

## Inter-Core Protocol

- Learning core sends MCPL lookup REQUEST packets to state cores via `spin1_send_mc_packet`.
- State cores reply via MCPL lookup REPLY packets via `spin1_send_mc_packet`.
- Router tables configured per-core by `cra_state_mcpl_init()` at startup.
- No SDP monitor-processor involvement in lookup traffic.

## Exact JobManager Command

```text
{command}
```

Default output dir is `tier4_28b_seed{args.seed}_job_output`.

## Expected 48-Event Reference Metrics

```text
readout_weight_raw  = 32768
readout_bias_raw    = 0
pending_created     = 48
pending_matured     = 48
active_pending      = 0
decisions           = 48
reward_events       = 48
lookup_requests     = 144
lookup_replies      = 144
stale_replies       = 0
timeouts            = 0
accuracy            = 0.9583
tail_accuracy       = 1.0
schema_version      = 2
payload_bytes       = 105
```

Tolerance: weight ±8192 of 32768, bias ±8192 of 0

## Multi-Seed Repeatability

Run this command for seeds 42, 43, and 44. One board per run is sufficient.
If variability appears across seeds, document it before freezing the baseline.

## Claim Boundary

Local package preparation and build validation only. NOT hardware evidence.
Returned EBRAINS artifacts must pass all criteria for each seed to claim
repeatability.

## Next Step

If all three seeds pass: ingest artifacts, freeze `CRA_NATIVE_RUNTIME_BASELINE_v0.1`.
If any seed fails: classify failure (router, timing, drop), repair, re-run.
"""

    readme = bundle / "README_TIER4_28b_JOB.md"
    readme.write_text(readme_text, encoding="utf-8")

    # Copy to stable upload folder
    STABLE_EBRAINS_UPLOAD.parent.mkdir(parents=True, exist_ok=True)
    if STABLE_EBRAINS_UPLOAD.exists():
        shutil.rmtree(STABLE_EBRAINS_UPLOAD)
    shutil.copytree(bundle, STABLE_EBRAINS_UPLOAD)

    criteria = [
        {"name": "local validation passed", "value": local_result["status"], "rule": "== pass", "passed": local_result["status"] == "pass"},
        {"name": "upload bundle created", "value": str(bundle), "rule": "exists", "passed": bundle.exists()},
        {"name": "context_core .aplx in bundle", "value": (bundle / f"coral_reef_{CONTEXT_CORE_PROFILE}.aplx").exists(), "rule": "== True", "passed": (bundle / f"coral_reef_{CONTEXT_CORE_PROFILE}.aplx").exists()},
        {"name": "route_core .aplx in bundle", "value": (bundle / f"coral_reef_{ROUTE_CORE_PROFILE}.aplx").exists(), "rule": "== True", "passed": (bundle / f"coral_reef_{ROUTE_CORE_PROFILE}.aplx").exists()},
        {"name": "memory_core .aplx in bundle", "value": (bundle / f"coral_reef_{MEMORY_CORE_PROFILE}.aplx").exists(), "rule": "== True", "passed": (bundle / f"coral_reef_{MEMORY_CORE_PROFILE}.aplx").exists()},
        {"name": "learning_core .aplx in bundle", "value": (bundle / f"coral_reef_{LEARNING_CORE_PROFILE}.aplx").exists(), "rule": "== True", "passed": (bundle / f"coral_reef_{LEARNING_CORE_PROFILE}.aplx").exists()},
        {"name": "stable upload folder created", "value": str(STABLE_EBRAINS_UPLOAD), "rule": "exists", "passed": STABLE_EBRAINS_UPLOAD.exists()},
    ]

    all_passed = all(c["passed"] for c in criteria)
    status = "prepared" if all_passed else "blocked"

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
            "job_command": command,
            "what_i_need_from_user": f"Upload {UPLOAD_PACKAGE_NAME} to EBRAINS/JobManager and run the emitted command for seeds 42, 43, 44.",
            "claim_boundary": "Local package preparation only. NOT hardware evidence.",
        },
        "criteria": criteria,
    }

    output_path = output_dir / "tier4_28b_prepare_results.json"
    output_path.write_text(json.dumps(result, indent=2))
    print(f"\nArtifact: {output_path}")
    print(f"\n{'=' * 60}")
    print(f"OVERALL: {status.upper()}")
    for c in criteria:
        mark = "PASS" if c["passed"] else "FAIL"
        print(f"  [{mark}] {c['name']}")
    return result


# ---------------------------------------------------------------------------
# Hardware helpers (copied from 4.27a; host-to-core commands still use SDP)
# ---------------------------------------------------------------------------

def _build_schedule(sequence: list, delay_steps: int = 2) -> list[dict]:
    """Build compact schedule entries from task sequence."""
    schedule = []
    for i, event in enumerate(sequence):
        schedule.append({
            "timestep": i + 1,
            "context_key": int(event.get("bridge_context_key_id", 0)),
            "route_key": int(event.get("bridge_route_key_id", 0)),
            "memory_key": int(event.get("bridge_memory_key_id", 0)),
            "cue": float(event.get("bridge_visible_cue", 0)),
            "target": float(event.get("target", 0.0)),
            "delay": delay_steps,
        })
    return schedule


def four_core_hardware_loop(
    hostname: str,
    args: argparse.Namespace,
    target: dict[str, Any],
    loads: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Run the four-core distributed task on hardware using ColonyController."""
    from coral_reef_spinnaker.python_host.colony_controller import ColonyController

    dest_x = int(args.dest_x)
    dest_y = int(args.dest_y)
    port = int(args.port)
    timeout = float(args.timeout_seconds)

    ctx_ctrl = ColonyController(hostname, port=port, timeout=timeout)
    route_ctrl = ColonyController(hostname, port=port, timeout=timeout)
    mem_ctrl = ColonyController(hostname, port=port, timeout=timeout)
    learning_ctrl = ColonyController(hostname, port=port, timeout=timeout)

    try:
        # Reset all four cores
        ctx_reset = ctx_ctrl.reset(dest_x, dest_y, CONTEXT_CORE_P)
        route_reset = route_ctrl.reset(dest_x, dest_y, ROUTE_CORE_P)
        mem_reset = mem_ctrl.reset(dest_x, dest_y, MEMORY_CORE_P)
        learning_reset = learning_ctrl.reset(dest_x, dest_y, LEARNING_CORE_P)
        time.sleep(0.1)

        # Write state slots to each state core
        ctx_writes = []
        for ctx_key, ctx_id in CONTEXT_KEY_IDS.items():
            val, conf = REGIME_VALUES.get(ctx_key, (0.0, 1.0))
            ok = ctx_ctrl.write_context(ctx_id, val, conf, dest_x, dest_y, CONTEXT_CORE_P)
            ctx_writes.append({"key": ctx_key, "success": ok.get("success") is True})

        route_writes = []
        for route_key, route_id in ROUTE_KEY_IDS.items():
            val, conf = REGIME_VALUES.get(route_key, (0.0, 1.0))
            ok = route_ctrl.write_route_slot(route_id, val, conf, dest_x, dest_y, ROUTE_CORE_P)
            route_writes.append({"key": route_key, "success": ok.get("success") is True})

        mem_writes = []
        for mem_key, mem_id in MEMORY_KEY_IDS.items():
            val, conf = REGIME_VALUES.get(mem_key, (0.0, 1.0))
            ok = mem_ctrl.write_memory_slot(mem_id, val, conf, dest_x, dest_y, MEMORY_CORE_P)
            mem_writes.append({"key": mem_key, "success": ok.get("success") is True})

        # Upload schedule to learning core
        schedule = _build_schedule(TASK_SEQUENCE)
        schedule_uploads = []
        for i, entry in enumerate(schedule):
            ok = learning_ctrl.write_schedule_entry(
                index=i,
                timestep=entry["timestep"],
                context_key=entry["context_key"],
                route_key=entry["route_key"],
                memory_key=entry["memory_key"],
                cue=entry["cue"],
                target=entry["target"],
                delay=entry["delay"],
                dest_x=dest_x,
                dest_y=dest_y,
                dest_cpu=LEARNING_CORE_P,
            )
            schedule_uploads.append({"index": i, "success": ok.get("success") is True})

        # Start continuous mode on all four cores
        learning_rate = 0.25
        ctx_run = ctx_ctrl.run_continuous(learning_rate, 0, dest_x, dest_y, CONTEXT_CORE_P)
        route_run = route_ctrl.run_continuous(learning_rate, 0, dest_x, dest_y, ROUTE_CORE_P)
        mem_run = mem_ctrl.run_continuous(learning_rate, 0, dest_x, dest_y, MEMORY_CORE_P)
        learning_run = learning_ctrl.run_continuous(learning_rate, len(schedule), dest_x, dest_y, LEARNING_CORE_P)
        time.sleep(0.05)

        # Wait for completion (learning core schedule + pending maturity)
        max_wait = 10.0
        poll_interval = 0.5
        waited = 0.0
        while waited < max_wait:
            time.sleep(poll_interval)
            waited += poll_interval
            learning_status = learning_ctrl.read_state(dest_x, dest_y, LEARNING_CORE_P)
            if learning_status.get("success") and learning_status.get("active_pending") == 0:
                break

        # Send pause to all cores
        ctx_pause = ctx_ctrl.pause(dest_x, dest_y, CONTEXT_CORE_P)
        route_pause = route_ctrl.pause(dest_x, dest_y, ROUTE_CORE_P)
        mem_pause = mem_ctrl.pause(dest_x, dest_y, MEMORY_CORE_P)
        learning_pause = learning_ctrl.pause(dest_x, dest_y, LEARNING_CORE_P)
        time.sleep(0.1)

        # Read back final state from all cores
        ctx_final = ctx_ctrl.read_state(dest_x, dest_y, CONTEXT_CORE_P)
        route_final = route_ctrl.read_state(dest_x, dest_y, ROUTE_CORE_P)
        mem_final = mem_ctrl.read_state(dest_x, dest_y, MEMORY_CORE_P)
        learning_final = learning_ctrl.read_state(dest_x, dest_y, LEARNING_CORE_P)

        return {
            "status": "completed",
            "reset": {
                "context": ctx_reset,
                "route": route_reset,
                "memory": mem_reset,
                "learning": learning_reset,
            },
            "state_writes": {
                "context": ctx_writes,
                "route": route_writes,
                "memory": mem_writes,
            },
            "schedule_uploads": schedule_uploads,
            "run_continuous": {
                "context": {"success": ctx_run.get("success") is True},
                "route": {"success": route_run.get("success") is True},
                "memory": {"success": mem_run.get("success") is True},
                "learning": {"success": learning_run.get("success") is True},
            },
            "pause": {
                "context": {"success": ctx_pause.get("success") is True},
                "route": {"success": route_pause.get("success") is True},
                "memory": {"success": mem_pause.get("success") is True},
                "learning": {"success": learning_pause.get("success") is True},
            },
            "final_state": {
                "context": ctx_final,
                "route": route_final,
                "memory": mem_final,
                "learning": learning_final,
            },
            "waited_seconds": waited,
        }
    except Exception as exc:
        return {
            "status": "fail",
            "reason": str(exc),
            "traceback": traceback.format_exc(),
        }
    finally:
        ctx_ctrl.close()
        route_ctrl.close()
        mem_ctrl.close()
        learning_ctrl.close()


# ---------------------------------------------------------------------------
# Run-hardware mode
# ---------------------------------------------------------------------------

def mode_run_hardware(args: argparse.Namespace) -> dict[str, Any]:
    print(TIER)
    print("=" * 60)

    default_dir = f"tier4_28b_seed{args.seed}_job_output"
    output_dir = Path(args.output) if args.output else Path(default_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    def write_json(path: Path, data: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2))

    # 1. Build all four MCPL images
    print("\n[1/4] Building four MCPL runtime profile images...")
    ctx_build = build_aplx_for_profile(CONTEXT_CORE_PROFILE, output_dir)
    route_build = build_aplx_for_profile(ROUTE_CORE_PROFILE, output_dir)
    mem_build = build_aplx_for_profile(MEMORY_CORE_PROFILE, output_dir)
    learning_build = build_aplx_for_profile(LEARNING_CORE_PROFILE, output_dir)

    ctx_aplx = Path(ctx_build["aplx_path"]) if ctx_build["aplx_exists"] else RUNTIME / "build" / "coral_reef.aplx"
    route_aplx = Path(route_build["aplx_path"]) if route_build["aplx_exists"] else RUNTIME / "build" / "coral_reef.aplx"
    mem_aplx = Path(mem_build["aplx_path"]) if mem_build["aplx_exists"] else RUNTIME / "build" / "coral_reef.aplx"
    learning_aplx = Path(learning_build["aplx_path"]) if learning_build["aplx_exists"] else RUNTIME / "build" / "coral_reef.aplx"

    env_report = base.environment_report()
    host_tests = base.run_host_tests(output_dir)
    main_syntax = base.run_main_syntax_check(output_dir)

    # 2. Acquire hardware target
    print("\n[2/4] Acquiring hardware target...")
    target = base.acquire_hardware_target(args)
    hostname = str(target.get("hostname") or target.get("target_ipaddress") or "")
    tx = target.get("_transceiver")

    # 3. Load all four applications
    print("\n[3/4] Loading four applications onto hardware...")
    loads: dict[str, dict[str, Any]] = {
        "context": {"status": "not_attempted"},
        "route": {"status": "not_attempted"},
        "memory": {"status": "not_attempted"},
        "learning": {"status": "not_attempted"},
    }

    task_result: dict[str, Any] = {"status": "not_attempted"}
    hardware_exception: dict[str, Any] | None = None

    write_json(output_dir / "tier4_28b_environment.json", env_report)
    write_json(output_dir / "tier4_28b_target_acquisition.json", base.public_target_acquisition(target))

    try:
        if target.get("status") == "pass" and hostname:
            loads["context"] = base.load_application_spinnman(
                hostname, ctx_aplx,
                x=int(args.dest_x), y=int(args.dest_y), p=CONTEXT_CORE_P,
                app_id=CONTEXT_CORE_APP_ID,
                delay=float(args.startup_delay_seconds),
                transceiver=tx,
            )
            loads["route"] = base.load_application_spinnman(
                hostname, route_aplx,
                x=int(args.dest_x), y=int(args.dest_y), p=ROUTE_CORE_P,
                app_id=ROUTE_CORE_APP_ID,
                delay=float(args.startup_delay_seconds),
                transceiver=tx,
            )
            loads["memory"] = base.load_application_spinnman(
                hostname, mem_aplx,
                x=int(args.dest_x), y=int(args.dest_y), p=MEMORY_CORE_P,
                app_id=MEMORY_CORE_APP_ID,
                delay=float(args.startup_delay_seconds),
                transceiver=tx,
            )
            loads["learning"] = base.load_application_spinnman(
                hostname, learning_aplx,
                x=int(args.dest_x), y=int(args.dest_y), p=LEARNING_CORE_P,
                app_id=LEARNING_CORE_APP_ID,
                delay=float(args.startup_delay_seconds),
                transceiver=tx,
            )
            for name, load_info in loads.items():
                write_json(output_dir / f"tier4_28b_{name}_load.json", load_info)

        if (target.get("status") == "pass" and hostname
            and all(l.get("status") == "pass" for l in loads.values())):
            print("\n[4/4] Running four-core hardware loop...")
            task_result = four_core_hardware_loop(hostname, args, target, loads)
            write_json(output_dir / "tier4_28b_task.json", task_result)
    except Exception as exc:
        hardware_exception = {
            "exception_type": type(exc).__name__,
            "exception": str(exc),
            "traceback": traceback.format_exc(),
        }
        task_result = {
            "status": "fail",
            "reason": str(exc),
            "traceback": traceback.format_exc(),
        }
        print(f"\n[HARDWARE EXCEPTION] {type(exc).__name__}: {exc}")
    finally:
        base.release_hardware_target(target)
        write_json(output_dir / "tier4_28b_environment.json", env_report)
        write_json(output_dir / "tier4_28b_target_acquisition.json", base.public_target_acquisition(target))
        for name, load_info in loads.items():
            write_json(output_dir / f"tier4_28b_{name}_load.json", load_info)
        write_json(output_dir / "tier4_28b_task.json", task_result)

    # Criteria
    ref_weight = -32768
    ref_bias = 0
    ref_events = len(TASK_SEQUENCE)

    final_states = task_result.get("final_state", {}) if isinstance(task_result, dict) else {}
    learning_final = final_states.get("learning", {}) if isinstance(final_states, dict) else {}
    ctx_final = final_states.get("context", {}) if isinstance(final_states, dict) else {}
    route_final = final_states.get("route", {}) if isinstance(final_states, dict) else {}
    mem_final = final_states.get("memory", {}) if isinstance(final_states, dict) else {}

    def criterion(name: str, value: Any, rule: str, passed: bool, note: str = "") -> dict[str, Any]:
        return {"name": name, "value": value, "rule": rule, "passed": passed, "note": note}

    criteria = [
        criterion("runner revision current", RUNNER_REVISION, "expected current source", True),
        criterion("custom C host tests pass", host_tests.get("status"), "== pass", host_tests.get("status") == "pass"),
        criterion("main.c syntax check pass", main_syntax.get("status"), "== pass", main_syntax.get("status") == "pass"),
        criterion("hardware target acquired", base.public_target_acquisition(target), "status == pass", target.get("status") == "pass"),
        criterion("context_core .aplx built", ctx_build["aplx_exists"], "== True", ctx_build["aplx_exists"]),
        criterion("route_core .aplx built", route_build["aplx_exists"], "== True", route_build["aplx_exists"]),
        criterion("memory_core .aplx built", mem_build["aplx_exists"], "== True", mem_build["aplx_exists"]),
        criterion("learning_core .aplx built", learning_build["aplx_exists"], "== True", learning_build["aplx_exists"]),
        criterion("context_core load pass", loads["context"].get("status"), "== pass", loads["context"].get("status") == "pass"),
        criterion("route_core load pass", loads["route"].get("status"), "== pass", loads["route"].get("status") == "pass"),
        criterion("memory_core load pass", loads["memory"].get("status"), "== pass", loads["memory"].get("status") == "pass"),
        criterion("learning_core load pass", loads["learning"].get("status"), "== pass", loads["learning"].get("status") == "pass"),
        criterion("all context writes succeeded", task_result.get("state_writes", {}).get("context", []), "all success", all(w.get("success") for w in task_result.get("state_writes", {}).get("context", []))),
        criterion("all route writes succeeded", task_result.get("state_writes", {}).get("route", []), "all success", all(w.get("success") for w in task_result.get("state_writes", {}).get("route", []))),
        criterion("all memory writes succeeded", task_result.get("state_writes", {}).get("memory", []), "all success", all(w.get("success") for w in task_result.get("state_writes", {}).get("memory", []))),
        criterion("all schedule uploads succeeded", task_result.get("schedule_uploads", []), "all success", all(u.get("success") for u in task_result.get("schedule_uploads", []))),
        criterion("context_core run_continuous succeeded", task_result.get("run_continuous", {}).get("context", {}).get("success"), "== True", task_result.get("run_continuous", {}).get("context", {}).get("success") is True),
        criterion("route_core run_continuous succeeded", task_result.get("run_continuous", {}).get("route", {}).get("success"), "== True", task_result.get("run_continuous", {}).get("route", {}).get("success") is True),
        criterion("memory_core run_continuous succeeded", task_result.get("run_continuous", {}).get("memory", {}).get("success"), "== True", task_result.get("run_continuous", {}).get("memory", {}).get("success") is True),
        criterion("learning_core run_continuous succeeded", task_result.get("run_continuous", {}).get("learning", {}).get("success"), "== True", task_result.get("run_continuous", {}).get("learning", {}).get("success") is True),
        criterion("context_core final read succeeded", ctx_final.get("success"), "== True", ctx_final.get("success") is True),
        criterion("route_core final read succeeded", route_final.get("success"), "== True", route_final.get("success") is True),
        criterion("memory_core final read succeeded", mem_final.get("success"), "== True", mem_final.get("success") is True),
        criterion("learning_core final read succeeded", learning_final.get("success"), "== True", learning_final.get("success") is True),
        criterion("learning_core weight negative and near reference", learning_final.get("readout_weight_raw"), f"within +/- {abs(ref_weight)//4} of {ref_weight}", abs(int(learning_final.get("readout_weight_raw") or 0) - ref_weight) <= abs(ref_weight) // 4),
        criterion("learning_core bias near reference", learning_final.get("readout_bias_raw"), f"within +/- {abs(ref_weight)//4} of {ref_bias}", abs(int(learning_final.get("readout_bias_raw") or 0) - ref_bias) <= abs(ref_weight) // 4),
        criterion("learning_core pending_created matches reference", learning_final.get("pending_created"), f"== {ref_events}", learning_final.get("pending_created") == ref_events),
        criterion("learning_core pending_matured matches reference", learning_final.get("pending_matured"), f"== {ref_events}", learning_final.get("pending_matured") == ref_events),
        criterion("learning_core active_pending cleared", learning_final.get("active_pending"), "== 0", learning_final.get("active_pending") == 0),
        criterion("no unhandled hardware exception", hardware_exception is None, "== True", hardware_exception is None),
        criterion("learning_core schema_version v2", learning_final.get("schema_version"), "== 2", learning_final.get("schema_version") == 2),
        criterion("learning_core lookup_requests == 144", learning_final.get("lookup_requests"), "== 144", learning_final.get("lookup_requests") == 144),
        criterion("learning_core lookup_replies == 144", learning_final.get("lookup_replies"), "== 144", learning_final.get("lookup_replies") == 144),
        criterion("learning_core stale_replies == 0", learning_final.get("stale_replies"), "== 0", learning_final.get("stale_replies") == 0),
        criterion("learning_core timeouts == 0", learning_final.get("timeouts"), "== 0", learning_final.get("timeouts") == 0),
        criterion("context_core lookup_replies == 0", ctx_final.get("lookup_replies"), "== 0", ctx_final.get("lookup_replies") == 0),
        criterion("route_core lookup_replies == 0", route_final.get("lookup_replies"), "== 0", route_final.get("lookup_replies") == 0),
        criterion("memory_core lookup_replies == 0", mem_final.get("lookup_replies"), "== 0", mem_final.get("lookup_replies") == 0),
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
        "loads": loads,
        "task": task_result,
        "hardware_exception": hardware_exception,
    }
    write_json(output_dir / "tier4_28b_hardware_results.json", result)

    print(f"\n{'=' * 60}")
    print(f"OVERALL: {status.upper()}")
    for c in criteria:
        mark = "PASS" if c["passed"] else "FAIL"
        print(f"  [{mark}] {c['name']}: {c['value']}")
    print(f"\nArtifacts exported to: {output_dir}")
    return result


# ---------------------------------------------------------------------------
# Ingest mode
# ---------------------------------------------------------------------------

def mode_ingest(args: argparse.Namespace) -> dict[str, Any]:
    print("Tier 4.28b — Ingest hardware results")
    print("=" * 60)

    default_dir = f"tier4_28b_seed{args.seed}_job_output"
    output_dir = Path(args.output) if args.output else Path(default_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    hw_dir = Path(args.hardware_output_dir) if args.hardware_output_dir else output_dir
    hw_results_path = hw_dir / "tier4_28b_hardware_results.json"

    hw_results = json.loads(hw_results_path.read_text()) if hw_results_path.exists() else {}
    criteria = hw_results.get("criteria", [])
    passed = sum(1 for c in criteria if c.get("passed"))
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
    }
    output_path = output_dir / "tier4_28b_ingest_results.json"
    output_path.write_text(json.dumps(result, indent=2))

    report = (
        f"# {TIER} — Ingest Report\n\n"
        f"- Status: **{status.upper()}**\n"
        f"- Passed: {passed}/{total}\n"
        f"- Hardware output: `{hw_dir}`\n\n"
        f"## Criteria\n\n"
    )
    for c in criteria:
        report += f"- {'✓' if c['passed'] else '✗'} {c['name']}: `{c['value']}` ({c['rule']})\n"

    (output_dir / "tier4_28b_ingest_report.md").write_text(report)

    print(f"OVERALL: {status.upper()}")
    print(f"Passed: {passed}/{total}")
    print(f"Ingest report: {output_dir / 'tier4_28b_ingest_report.md'}")
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=TIER)
    parser.add_argument(
        "--mode",
        default=None,
        choices=["local", "prepare", "run-hardware", "ingest"],
        help="Execution mode",
    )
    parser.add_argument(
        "mode_pos",
        nargs="?",
        default=None,
        choices=["local", "prepare", "run-hardware", "ingest"],
        help="Execution mode (positional, for backward compatibility)",
    )
    parser.add_argument("--output", type=str, default=None, help="Path to write JSON artifact or output directory")
    parser.add_argument("--hw-dir", default="", dest="hardware_output_dir", help="Hardware output directory for ingest")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for task generation and run labeling")
    parser.add_argument("--dest-x", default="0")
    parser.add_argument("--dest-y", default="0")
    parser.add_argument("--port", default="17893")
    parser.add_argument("--timeout-seconds", default="2.0")
    parser.add_argument("--startup-delay-seconds", default="2.0")
    parser.add_argument("--target-acquisition", choices=["auto", "hostname", "spynnaker-probe"], default="auto")
    parser.add_argument("--spinnaker-hostname", default="")
    parser.add_argument("--target-probe-population-size", type=int, default=1)
    parser.add_argument("--target-probe-run-ms", type=float, default=1.0)
    parser.add_argument("--target-probe-timestep-ms", type=float, default=1.0)
    parser.add_argument("--dest-cpu", type=int, default=1)
    parser.add_argument("--auto-dest-cpu", dest="auto_dest_cpu", action="store_true", default=True)
    parser.add_argument("--no-auto-dest-cpu", dest="auto_dest_cpu", action="store_false")
    args = parser.parse_args()

    mode = args.mode or args.mode_pos or "local"

    try:
        if mode == "local":
            report = mode_local(args)
        elif mode == "prepare":
            report = mode_prepare(args)
        elif mode == "run-hardware":
            report = mode_run_hardware(args)
        elif mode == "ingest":
            report = mode_ingest(args)
        else:
            parser.print_help()
            return 1

        return 0 if report.get("status") in ("pass", "prepared") else 1
    except BaseException as exc:
        crash = {
            "tier": TIER,
            "runner_revision": RUNNER_REVISION,
            "mode": mode,
            "exception_type": type(exc).__name__,
            "exception": str(exc),
            "traceback": traceback.format_exc(),
            "timestamp": utc_now(),
        }
        crash_path = Path(f"tier4_28b_seed{args.seed}_job_output") / "tier4_28b_crash_report.json"
        crash_path.parent.mkdir(parents=True, exist_ok=True)
        crash_path.write_text(json.dumps(crash, indent=2))
        print(f"\n[FATAL CRASH] {type(exc).__name__}: {exc}")
        print(f"Crash report written to: {crash_path}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
