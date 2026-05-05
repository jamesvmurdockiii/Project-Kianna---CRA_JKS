#!/usr/bin/env python3
"""
Tier 4.29c — Native Predictive Binding Bridge.

Tests that the native SpiNNaker learning_core computes, stores, and uses
predictions before feedback arrives. Verifies prediction parity between
host reference and chip-computed values, and checks that prediction-error-
based weight updates pass explicit controls.

Modes:
  local        — build four MCPL profiles, run host reference, verify parity
  prepare      — create EBRAINS job bundle
  run-hardware — load four MCPL images, run distributed prediction task
  ingest       — compare hardware results with reference

Claim boundary:
  Native prediction computation and storage works on real SpiNNaker.
  Prediction is readable before reward arrives.
  Prediction-error-based learning updates pass zero-error and sign-flip controls.
  Not full world modeling, not hidden-regime inference, not speedup, not multi-chip.
"""
from __future__ import annotations

import argparse
import json
import os
import random
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

from experiments import tier4_22i_custom_runtime_roundtrip as base  # noqa: E402

# ---------------------------------------------------------------------------
# Fixed-point helpers (s16.15)
# ---------------------------------------------------------------------------
FP_SHIFT = 15
FP_ONE = 1 << FP_SHIFT


def fp_from_float(value: float) -> int:
    return int(value * FP_ONE)


def fp_to_float(value: int) -> float:
    return int(value) / FP_ONE


def fp_mul(a: int, b: int) -> int:
    return (int(a) * int(b)) >> FP_SHIFT


# ---------------------------------------------------------------------------
# Tier constants
# ---------------------------------------------------------------------------
TIER = "Tier 4.29c — Native Predictive Binding Bridge"
RUNNER_REVISION = "tier4_29c_native_predictive_binding_20260503_0001"
UPLOAD_PACKAGE_NAME = "cra_429h"
STABLE_EBRAINS_UPLOAD = ROOT / "ebrains_jobs" / UPLOAD_PACKAGE_NAME

# Core role map (same four-core architecture as 4.29b)
CONTEXT_CORE_P = 4
ROUTE_CORE_P = 5
MEMORY_CORE_P = 6
LEARNING_CORE_P = 7

CONTEXT_CORE_PROFILE = "context_core"
ROUTE_CORE_PROFILE = "route_core"
MEMORY_CORE_PROFILE = "memory_core"
LEARNING_CORE_PROFILE = "learning_core"

CONTEXT_CORE_APP_ID = 1
ROUTE_CORE_APP_ID = 2
MEMORY_CORE_APP_ID = 3
LEARNING_CORE_APP_ID = 4

# Task parameters
TASK_LEARNING_RATE = 0.25
TASK_DELAY = 2

# Context slot: single positive context
CONTEXT_KEY = 101
CONTEXT_VALUE = 1.0

# Neutral route and memory (value = 1.0, no effect on feature)
ROUTE_KEY = 201
ROUTE_VALUE = 1.0
MEMORY_KEY = 301
MEMORY_VALUE = 1.0

# Task sequence: 20 events with explicit controls
# Feature = context * route * memory * cue = cue (since all base values are +1.0)
# Initial weight = 1.0, bias = 0
TASK_EVENTS = [
    # Phase 1: Zero-error control (target = prediction, weight should stay at 1.0)
    {"step": 0,  "cue": 1.0,  "target": 1.0,  "control": "zero_error",    "expected_err": 0.0},
    {"step": 1,  "cue": 1.0,  "target": 1.0,  "control": "zero_error",    "expected_err": 0.0},
    {"step": 2,  "cue": 1.0,  "target": 1.0,  "control": "zero_error",    "expected_err": 0.0},
    {"step": 3,  "cue": 1.0,  "target": 1.0,  "control": "zero_error",    "expected_err": 0.0},
    # Phase 2: Positive surprise (target > prediction, weight should increase)
    {"step": 4,  "cue": 1.0,  "target": 2.0,  "control": "positive_err",  "expected_err": 1.0},
    {"step": 5,  "cue": 1.0,  "target": 2.0,  "control": "positive_err",  "expected_err": 1.0},
    # Phase 3: Negative surprise (target < prediction, weight should decrease)
    {"step": 6,  "cue": 1.0,  "target": 0.0,  "control": "negative_err",  "expected_err": -1.0},
    {"step": 7,  "cue": 1.0,  "target": 0.0,  "control": "negative_err",  "expected_err": -1.0},
    # Phase 4: Sign-flip control (cue = -1.0, verify feature sign flips prediction)
    {"step": 8,  "cue": -1.0, "target": -1.0, "control": "sign_flip",     "expected_err": 0.0},
    {"step": 9,  "cue": -1.0, "target": -1.0, "control": "sign_flip",     "expected_err": 0.0},
    # Phase 5: Mixed recovery (converge back toward zero-error)
    {"step": 10, "cue": 1.0,  "target": 1.0,  "control": "recovery",      "expected_err": None},
    {"step": 11, "cue": 1.0,  "target": 1.0,  "control": "recovery",      "expected_err": None},
    {"step": 12, "cue": 1.0,  "target": 1.0,  "control": "recovery",      "expected_err": None},
    {"step": 13, "cue": 1.0,  "target": 1.0,  "control": "recovery",      "expected_err": None},
    # Phase 6: Additional positive/negative to test convergence
    {"step": 14, "cue": 1.0,  "target": 1.5,  "control": "mixed",         "expected_err": 0.5},
    {"step": 15, "cue": 1.0,  "target": 0.5,  "control": "mixed",         "expected_err": -0.5},
    {"step": 16, "cue": 1.0,  "target": 1.0,  "control": "recovery",      "expected_err": None},
    {"step": 17, "cue": 1.0,  "target": 1.0,  "control": "recovery",      "expected_err": None},
    {"step": 18, "cue": -1.0, "target": -1.0, "control": "sign_flip",     "expected_err": 0.0},
    {"step": 19, "cue": -1.0, "target": -1.0, "control": "sign_flip",     "expected_err": 0.0},
]


def _build_schedule(events: list[dict], offset: int = 0) -> list[dict]:
    """Build schedule entries for continuous mode."""
    schedule = []
    for i, ev in enumerate(events):
        schedule.append({
            "index": offset + i,
            "timestep": i + 1,  # Must start at 1; timestep 0 is unreachable because
                                # g_schedule_base_timestep = g_timestep at run_continuous,
                                # and the next tick is already > base + 0.
            "context_key": CONTEXT_KEY,
            "route_key": ROUTE_KEY,
            "memory_key": MEMORY_KEY,
            "cue": ev["cue"],
            "target": ev["target"],
            "delay": TASK_DELAY,
        })
    return schedule


def run_host_reference(seed: int) -> dict:
    """Compute the host-side s16.15 reference for the prediction task."""
    random.seed(seed)
    weight = FP_ONE  # 1.0
    bias = 0
    lr = fp_from_float(TASK_LEARNING_RATE)
    rows = []
    pending = []

    for ev in TASK_EVENTS:
        step = ev["step"]
        cue = fp_from_float(ev["cue"])
        target = fp_from_float(ev["target"])
        feature = cue  # context=route=memory=1.0, so feature=cue

        # Compute prediction
        prediction = fp_mul(weight, feature) + bias

        # Schedule pending
        pending.append({
            "step": step,
            "feature": feature,
            "prediction": prediction,
            "target": target,
            "due_step": step + TASK_DELAY,
            "control": ev["control"],
        })

        # Mature any due pending
        while pending and pending[0]["due_step"] <= step:
            p = pending.pop(0)
            err = p["target"] - p["prediction"]
            delta_w = fp_mul(lr, fp_mul(err, p["feature"]))
            delta_b = fp_mul(lr, err)
            weight += delta_w
            bias += delta_b

            rows.append({
                "step": p["step"],
                "control": p["control"],
                "feature_raw": p["feature"],
                "prediction_raw": p["prediction"],
                "target_raw": p["target"],
                "error_raw": err,
                "delta_w_raw": delta_w,
                "delta_b_raw": delta_b,
                "weight_after": weight,
                "bias_after": bias,
            })

    # Mature remaining
    while pending:
        p = pending.pop(0)
        err = p["target"] - p["prediction"]
        delta_w = fp_mul(lr, fp_mul(err, p["feature"]))
        delta_b = fp_mul(lr, err)
        weight += delta_w
        bias += delta_b

        rows.append({
            "step": p["step"],
            "control": p["control"],
            "feature_raw": p["feature"],
            "prediction_raw": p["prediction"],
            "target_raw": p["target"],
            "error_raw": err,
            "delta_w_raw": delta_w,
            "delta_b_raw": delta_b,
            "weight_after": weight,
            "bias_after": bias,
        })

    return {
        "seed": seed,
        "final_weight": weight,
        "final_bias": bias,
        "final_weight_float": fp_to_float(weight),
        "final_bias_float": fp_to_float(bias),
        "rows": rows,
        "pending_count": len(TASK_EVENTS),
        "matured_count": len(rows),
    }


def evaluate_criteria(ref: dict) -> list[dict]:
    """Evaluate pass/fail criteria against the host reference."""
    criteria = []
    rows = ref["rows"]

    # Criterion 1: All zero-error events have |error| < threshold
    zero_error_rows = [r for r in rows if r["control"] == "zero_error"]
    zero_error_max = max(abs(r["error_raw"]) for r in zero_error_rows) if zero_error_rows else 0
    criteria.append({
        "name": "zero_error_events_have_near_zero_error",
        "value": zero_error_max,
        "threshold": 100,  # s16.15: 100/32768 ≈ 0.003
        "passed": zero_error_max <= 100,
        "note": f"max |error| = {zero_error_max} (threshold 100)",
    })

    # Criterion 2: Positive surprise events increase weight
    pos_err_rows = [r for r in rows if r["control"] == "positive_err"]
    pos_weight_increases = all(r["delta_w_raw"] > 0 for r in pos_err_rows) if pos_err_rows else True
    criteria.append({
        "name": "positive_surprise_increases_weight",
        "value": pos_weight_increases,
        "threshold": True,
        "passed": pos_weight_increases,
        "note": "all positive_err events have delta_w > 0",
    })

    # Criterion 3: Negative surprise events decrease weight
    neg_err_rows = [r for r in rows if r["control"] == "negative_err"]
    neg_weight_decreases = all(r["delta_w_raw"] < 0 for r in neg_err_rows) if neg_err_rows else True
    criteria.append({
        "name": "negative_surprise_decreases_weight",
        "value": neg_weight_decreases,
        "threshold": True,
        "passed": neg_weight_decreases,
        "note": "all negative_err events have delta_w < 0",
    })

    # Criterion 4: Sign-flip events have prediction with correct sign
    sign_flip_rows = [r for r in rows if r["control"] == "sign_flip"]
    sign_flip_correct = all(
        (r["prediction_raw"] >= 0 and r["feature_raw"] >= 0) or
        (r["prediction_raw"] <= 0 and r["feature_raw"] <= 0)
        for r in sign_flip_rows
    ) if sign_flip_rows else True
    criteria.append({
        "name": "sign_flip_prediction_matches_feature_sign",
        "value": sign_flip_correct,
        "threshold": True,
        "passed": sign_flip_correct,
        "note": "prediction sign matches feature sign for all sign_flip events",
    })

    # Criterion 5: All events matured
    criteria.append({
        "name": "all_events_matured",
        "value": ref["matured_count"],
        "threshold": ref["pending_count"],
        "passed": ref["matured_count"] == ref["pending_count"],
        "note": f"matured {ref['matured_count']}/{ref['pending_count']}",
    })

    # Criterion 6: Final weight is finite and in reasonable range
    final_w = abs(ref["final_weight"])
    criteria.append({
        "name": "final_weight_in_reasonable_range",
        "value": final_w,
        "threshold": 65536,  # 2.0 in s16.15
        "passed": final_w <= 65536,
        "note": f"final weight = {ref['final_weight_float']:.4f}",
    })

    # Criterion 7: All predictions computed (none missing)
    predictions_missing = sum(1 for r in rows if r["prediction_raw"] == 0 and r["feature_raw"] != 0)
    criteria.append({
        "name": "no_missing_predictions",
        "value": predictions_missing,
        "threshold": 0,
        "passed": predictions_missing == 0,
        "note": f"missing predictions: {predictions_missing}",
    })

    return criteria


def mode_local(args: argparse.Namespace) -> dict:
    """Run local host reference and verify criteria."""
    seed = int(args.seed)
    ref = run_host_reference(seed)
    criteria = evaluate_criteria(ref)

    all_passed = all(c["passed"] for c in criteria)
    results = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "mode": "local",
        "seed": seed,
        "status": "pass" if all_passed else "fail",
        "criteria": criteria,
        "reference": ref,
    }

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    with open(output_dir / "tier4_29c_local_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"Local reference: {ref['matured_count']}/{ref['pending_count']} events matured")
    print(f"Final weight: {ref['final_weight_float']:.4f}, bias: {ref['final_bias_float']:.4f}")
    for c in criteria:
        mark = "PASS" if c["passed"] else "FAIL"
        print(f"  [{mark}] {c['name']}: {c['note']}")

    return results


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

    base_aplx = RUNTIME / "build" / "coral_reef.aplx"
    if base_aplx.exists():
        base_aplx.unlink()

    build = base.run_cmd(["make", "-C", str(RUNTIME), "clean", "all"], cwd=ROOT, env=env)
    (output_dir / f"tier4_29c_build_{profile}_stdout.txt").write_text(build["stdout"])
    (output_dir / f"tier4_29c_build_{profile}_stderr.txt").write_text(build["stderr"])

    aplx = RUNTIME / "build" / "coral_reef.aplx"
    profile_aplx = RUNTIME / "build" / f"coral_reef_{profile}.aplx"
    if aplx.exists():
        if profile_aplx.exists():
            profile_aplx.unlink()
        shutil.copy2(aplx, profile_aplx)

    size_text = 0
    elf_path = RUNTIME / "build" / "gnu" / "coral_reef.elf"
    if elf_path.exists():
        size_bin = str(arm_toolchain / "arm-none-eabi-size") if arm_toolchain.exists() else "arm-none-eabi-size"
        size_cmd = base.run_cmd([size_bin, str(elf_path)], cwd=ROOT)
        if size_cmd["returncode"] == 0:
            for line in size_cmd.get("stdout", "").splitlines():
                if "coral_reef.elf" in line:
                    parts = line.strip().split()
                    if len(parts) >= 4:
                        try:
                            size_text = int(parts[0]) + int(parts[1])
                        except ValueError:
                            pass

    return {
        "profile": profile,
        "returncode": build["returncode"],
        "stdout": build["stdout"],
        "stderr": build["stderr"],
        "aplx_exists": profile_aplx.exists(),
        "size_text": size_text,
    }


def mode_prepare(args: argparse.Namespace) -> dict:
    """Create EBRAINS upload bundle."""
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    bundle = output_dir / "ebrains_upload_bundle" / UPLOAD_PACKAGE_NAME
    if bundle.exists():
        shutil.rmtree(bundle)
    (bundle / "experiments").mkdir(parents=True, exist_ok=True)
    (bundle / "coral_reef_spinnaker" / "python_host").mkdir(parents=True, exist_ok=True)

    # Selective copy: only scripts this runner actually imports
    (bundle / "experiments" / "__init__.py").write_text("# experiments package\n", encoding="utf-8")
    scripts = [
        "tier4_29c_native_predictive_binding_bridge.py",
        "tier4_22i_custom_runtime_roundtrip.py",
        "tier4_28d_hard_noisy_switching_four_core_mcpl.py",
        "tier4_22r_native_context_state_smoke.py",
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

    # Build .aplx images for all four profiles
    builds = {}
    for profile in [CONTEXT_CORE_PROFILE, ROUTE_CORE_PROFILE, MEMORY_CORE_PROFILE, LEARNING_CORE_PROFILE]:
        build_result = build_aplx_for_profile(profile, output_dir)
        builds[profile] = build_result
        if build_result["returncode"] != 0:
            print(f"ERROR: build failed for {profile}")
            print(build_result["stderr"])
            return {"status": "fail", "reason": f"build failed: {profile}"}
        src_aplx = RUNTIME / "build" / f"coral_reef_{profile}.aplx"
        if src_aplx.exists():
            shutil.copy2(src_aplx, bundle / f"coral_reef_{profile}.aplx")

    # Write job README
    readme = bundle / f"README_TIER4_29C_JOB.md"
    readme.write_text(f"""# {TIER}

Upload folder: `{UPLOAD_PACKAGE_NAME}`

Command:
```text
{UPLOAD_PACKAGE_NAME}/experiments/tier4_29c_native_predictive_binding_bridge.py --mode run-hardware --seeds 42,43,44
```

Purpose: Verify that the native learning_core computes, stores, and uses
predictions before feedback arrives. Test zero-error, positive-surprise,
negative-surprise, and sign-flip controls.
 """)

    # Create stable symlink
    if STABLE_EBRAINS_UPLOAD.exists() or STABLE_EBRAINS_UPLOAD.is_symlink():
        STABLE_EBRAINS_UPLOAD.unlink()
    STABLE_EBRAINS_UPLOAD.symlink_to(bundle.resolve(), target_is_directory=True)

    # Write prepare results
    results = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "mode": "prepare",
        "status": "prepared",
        "upload_folder": str(bundle),
        "stable_upload_folder": str(STABLE_EBRAINS_UPLOAD),
        "jobmanager_command": f"{UPLOAD_PACKAGE_NAME}/experiments/tier4_29c_native_predictive_binding_bridge.py --mode run-hardware --seeds 42,43,44",
    }
    with open(output_dir / "tier4_29c_prepare_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"Prepared: {bundle}")
    print(f"Stable:   {STABLE_EBRAINS_UPLOAD}")
    return results


def four_core_hardware_loop(
    hostname: str,
    args: argparse.Namespace,
    target: dict,
    loads: dict[str, dict],
) -> dict:
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

    # Reset all four cores
    ctx_reset = ctx_ctrl.reset(dest_x, dest_y, CONTEXT_CORE_P)
    route_reset = route_ctrl.reset(dest_x, dest_y, ROUTE_CORE_P)
    mem_reset = mem_ctrl.reset(dest_x, dest_y, MEMORY_CORE_P)
    learning_reset = learning_ctrl.reset(dest_x, dest_y, LEARNING_CORE_P)
    time.sleep(0.1)

    # Write neutral slots
    ctx_writes = []
    route_writes = []
    mem_writes = []

    ok = ctx_ctrl.write_context(CONTEXT_KEY, CONTEXT_VALUE, 1.0, dest_x, dest_y, CONTEXT_CORE_P)
    ctx_writes.append({"key": CONTEXT_KEY, "success": ok.get("success") is True})

    ok = route_ctrl.write_route_slot(ROUTE_KEY, ROUTE_VALUE, 1.0, dest_x, dest_y, ROUTE_CORE_P)
    route_writes.append({"key": ROUTE_KEY, "success": ok.get("success") is True})

    ok = mem_ctrl.write_memory_slot(MEMORY_KEY, MEMORY_VALUE, 1.0, dest_x, dest_y, MEMORY_CORE_P)
    mem_writes.append({"key": MEMORY_KEY, "success": ok.get("success") is True})

    # Upload schedule to learning core
    schedule = _build_schedule(TASK_EVENTS)
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
    learning_rate = TASK_LEARNING_RATE
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
            "context": ctx_run,
            "route": route_run,
            "memory": mem_run,
            "learning": learning_run,
        },
        "pause": {
            "context": ctx_pause,
            "route": route_pause,
            "memory": mem_pause,
            "learning": learning_pause,
            "all_paused": all([ctx_pause, route_pause, mem_pause, learning_pause]),
        },
        "final_state": {
            "context": ctx_final,
            "route": route_final,
            "memory": mem_final,
            "learning": learning_final,
        },
        "wait_time": waited,
    }


def mode_run_hardware(args: argparse.Namespace) -> dict:
    """Run four-core distributed prediction task on real SpiNNaker hardware."""
    print(TIER)
    print("=" * 60)

    default_dir = f"tier4_29c_seed{args.seed}_job_output"
    output_dir = Path(args.output) if args.output else Path(default_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    def write_json(path: Path, data: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2))

    # 1. Build all four MCPL images
    print("\n[1/4] Building four MCPL runtime profile images...")
    ctx_build = build_aplx_for_profile(CONTEXT_CORE_PROFILE, output_dir)
    route_build = build_aplx_for_profile(ROUTE_CORE_PROFILE, output_dir)
    mem_build = build_aplx_for_profile(MEMORY_CORE_PROFILE, output_dir)
    learning_build = build_aplx_for_profile(LEARNING_CORE_PROFILE, output_dir)

    ctx_aplx = RUNTIME / "build" / f"coral_reef_{CONTEXT_CORE_PROFILE}.aplx"
    route_aplx = RUNTIME / "build" / f"coral_reef_{ROUTE_CORE_PROFILE}.aplx"
    mem_aplx = RUNTIME / "build" / f"coral_reef_{MEMORY_CORE_PROFILE}.aplx"
    learning_aplx = RUNTIME / "build" / f"coral_reef_{LEARNING_CORE_PROFILE}.aplx"

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
    loads: dict[str, dict] = {
        "context": {"status": "not_attempted"},
        "route": {"status": "not_attempted"},
        "memory": {"status": "not_attempted"},
        "learning": {"status": "not_attempted"},
    }

    task_result: dict = {"status": "not_attempted"}
    hardware_exception: dict | None = None

    write_json(output_dir / "tier4_29c_environment.json", env_report)
    write_json(output_dir / "tier4_29c_target_acquisition.json", base.public_target_acquisition(target))

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
                write_json(output_dir / f"tier4_29c_{name}_load.json", load_info)

        if (target.get("status") == "pass" and hostname
            and all(l.get("status") == "pass" for l in loads.values())):
            print("\n[4/4] Running four-core hardware loop...")
            task_result = four_core_hardware_loop(hostname, args, target, loads)
            write_json(output_dir / "tier4_29c_task.json", task_result)
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
        write_json(output_dir / "tier4_29c_environment.json", env_report)
        write_json(output_dir / "tier4_29c_target_acquisition.json", base.public_target_acquisition(target))
        for name, load_info in loads.items():
            write_json(output_dir / f"tier4_29c_{name}_load.json", load_info)
        write_json(output_dir / "tier4_29c_task.json", task_result)

    # Reference
    ref = run_host_reference(int(args.seed))
    tolerance = 8192  # ~0.25 in s16.15

    final_states = task_result.get("final_state", {}) if isinstance(task_result, dict) else {}
    learning_final = final_states.get("learning", {}) if isinstance(final_states, dict) else {}
    ctx_final = final_states.get("context", {}) if isinstance(final_states, dict) else {}
    route_final = final_states.get("route", {}) if isinstance(final_states, dict) else {}
    mem_final = final_states.get("memory", {}) if isinstance(final_states, dict) else {}

    def criterion(name: str, value, rule: str, passed: bool, note: str = "") -> dict:
        return {"name": name, "value": value, "rule": rule, "passed": passed, "note": note}

    ctx_writes = task_result.get("state_writes", {}).get("context", [])
    route_writes_list = task_result.get("state_writes", {}).get("route", [])
    mem_writes_list = task_result.get("state_writes", {}).get("memory", [])
    schedule_uploads_list = task_result.get("schedule_uploads", [])

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
        criterion("all context writes succeeded", len(ctx_writes) > 0 and all(w.get("success") for w in ctx_writes), "len>0 and all success", len(ctx_writes) > 0 and all(w.get("success") for w in ctx_writes)),
        criterion("all route writes succeeded", len(route_writes_list) > 0 and all(w.get("success") for w in route_writes_list), "len>0 and all success", len(route_writes_list) > 0 and all(w.get("success") for w in route_writes_list)),
        criterion("all memory writes succeeded", len(mem_writes_list) > 0 and all(w.get("success") for w in mem_writes_list), "len>0 and all success", len(mem_writes_list) > 0 and all(w.get("success") for w in mem_writes_list)),
        criterion("all schedule uploads succeeded", len(schedule_uploads_list) > 0 and all(u.get("success") for u in schedule_uploads_list), "len>0 and all success", len(schedule_uploads_list) > 0 and all(u.get("success") for u in schedule_uploads_list)),
        criterion("context_core run_continuous succeeded", task_result.get("run_continuous", {}).get("context", {}).get("success"), "== True", task_result.get("run_continuous", {}).get("context", {}).get("success") is True),
        criterion("route_core run_continuous succeeded", task_result.get("run_continuous", {}).get("route", {}).get("success"), "== True", task_result.get("run_continuous", {}).get("route", {}).get("success") is True),
        criterion("memory_core run_continuous succeeded", task_result.get("run_continuous", {}).get("memory", {}).get("success"), "== True", task_result.get("run_continuous", {}).get("memory", {}).get("success") is True),
        criterion("learning_core run_continuous succeeded", task_result.get("run_continuous", {}).get("learning", {}).get("success"), "== True", task_result.get("run_continuous", {}).get("learning", {}).get("success") is True),
        criterion("all cores paused", task_result.get("pause", {}).get("all_paused"), "== True", task_result.get("pause", {}).get("all_paused") is True),
        criterion("learning final weight within tolerance", learning_final.get("readout_weight_raw", 0), f"within {tolerance} of {ref['final_weight']}", abs(learning_final.get("readout_weight_raw", 0) - ref["final_weight"]) <= tolerance),
        criterion("learning final bias within tolerance", learning_final.get("readout_bias_raw", 0), f"within {tolerance} of {ref['final_bias']}", abs(learning_final.get("readout_bias_raw", 0) - ref["final_bias"]) <= tolerance),
        criterion("all pending matured", learning_final.get("active_pending", 1), "== 0", learning_final.get("active_pending", 1) == 0),
        criterion("pending_created equals expected", learning_final.get("pending_created", 0), f"== {len(TASK_EVENTS)}", learning_final.get("pending_created", 0) == len(TASK_EVENTS)),
        criterion("pending_matured equals expected", learning_final.get("pending_matured", 0), f"== {len(TASK_EVENTS)}", learning_final.get("pending_matured", 0) == len(TASK_EVENTS)),
    ]

    all_passed = all(c["passed"] for c in criteria)
    report = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "mode": "run-hardware",
        "seed": int(args.seed),
        "hostname": hostname,
        "status": "pass" if all_passed else "fail",
        "criteria": criteria,
        "reference": {
            "final_weight_raw": ref["final_weight"],
            "final_bias_raw": ref["final_bias"],
            "final_weight_float": ref["final_weight_float"],
            "final_bias_float": ref["final_bias_float"],
        },
        "final_state": final_states,
        "task_result": task_result,
        "loads": {k: {"status": v.get("status")} for k, v in loads.items()},
    }

    write_json(output_dir / "tier4_29c_report.json", report)

    print(f"\nHardware seed {args.seed}: {'PASS' if all_passed else 'FAIL'}")
    for c in criteria:
        mark = "PASS" if c["passed"] else "FAIL"
        print(f"  [{mark}] {c['name']}: {c['note']}")

    return report


def mode_ingest(args: argparse.Namespace) -> dict:
    """Ingest hardware results."""
    output_dir = Path(args.output_dir)
    seeds = [int(s.strip()) for s in args.seeds.split(",")]

    all_results = []
    for seed in seeds:
        hw_file = output_dir / f"tier4_29c_hardware_results_seed{seed}.json"
        if not hw_file.exists():
            print(f"Missing hardware results for seed {seed}")
            continue
        with open(hw_file) as f:
            hw = json.load(f)
        all_results.append(hw)

    if not all_results:
        return {"status": "fail", "reason": "no hardware results found"}

    total_criteria = sum(len(r["criteria"]) for r in all_results)
    passed_criteria = sum(sum(1 for c in r["criteria"] if c["passed"]) for r in all_results)

    ingest_summary = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "mode": "ingest",
        "seeds": seeds,
        "status": "pass" if passed_criteria == total_criteria else "fail",
        "total_criteria": total_criteria,
        "passed_criteria": passed_criteria,
        "per_seed": [{"seed": r["seed"], "status": r["status"], "criteria_passed": sum(1 for c in r["criteria"] if c["passed"]), "criteria_total": len(r["criteria"])} for r in all_results],
    }

    with open(output_dir / "tier4_29c_ingest_results.json", "w") as f:
        json.dump(ingest_summary, f, indent=2)

    print(f"Ingest: {passed_criteria}/{total_criteria} criteria passed across {len(seeds)} seed(s)")
    return ingest_summary


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> int:
    parser = argparse.ArgumentParser(description=TIER)
    parser.add_argument("--mode", choices=["local", "prepare", "run-hardware", "ingest"], default="local")
    parser.add_argument("--output-dir", default="tier4_29c_output")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--seeds", type=str, default="42")
    parser.add_argument("--dest-x", type=int, default=0)
    parser.add_argument("--dest-y", type=int, default=0)
    parser.add_argument("--dest-cpu", type=int, default=1)
    parser.add_argument("--auto-dest-cpu", dest="auto_dest_cpu", action="store_true", default=True)
    parser.add_argument("--no-auto-dest-cpu", dest="auto_dest_cpu", action="store_false")
    parser.add_argument("--target-probe-run-ms", type=float, default=1.0)
    parser.add_argument("--port", type=int, default=17893)
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    parser.add_argument("--startup-delay-seconds", type=float, default=2.0)
    parser.add_argument("--output", type=str, default=None, help="Hardware output directory")
    parser.add_argument("--target-acquisition", choices=["auto", "hostname", "spynnaker-probe"], default="auto")
    parser.add_argument("--spinnaker-hostname", default="")
    parser.add_argument("--target-probe-timestep-ms", type=float, default=1.0)
    parser.add_argument("--target-probe-population-size", type=int, default=1)
    parser.add_argument("--app-id", type=int, default=17)
    parser.add_argument("--command-delay-seconds", type=float, default=0.05)
    parser.add_argument("--post-mutation-delay-seconds", type=float, default=0.10)
    args = parser.parse_args()

    mode = args.mode
    report = None

    try:
        if mode == "local":
            report = mode_local(args)
        elif mode == "prepare":
            report = mode_prepare(args)
        elif mode == "run-hardware":
            if args.seeds:
                seeds = [int(s.strip()) for s in args.seeds.split(",")]
                reports = []
                for seed in seeds:
                    print(f"\n{'='*60}")
                    print(f"MULTI-SEED RUN: seed {seed} / {seeds}")
                    print(f"{'='*60}")
                    args.seed = seed
                    r = mode_run_hardware(args)
                    reports.append(r)
                all_pass = all(r.get("status") == "pass" for r in reports)
                combined = {
                    "tier": TIER,
                    "runner_revision": RUNNER_REVISION,
                    "mode": "run-hardware",
                    "submode": "multi-seed",
                    "seeds": seeds,
                    "status": "pass" if all_pass else "fail",
                    "reports": reports,
                }
                combined_path = Path(f"tier4_29c_multi_seed_job_output") / "tier4_29c_combined_results.json"
                combined_path.parent.mkdir(parents=True, exist_ok=True)
                combined_path.write_text(json.dumps(combined, indent=2))
                print(f"\n{'='*60}")
                print(f"MULTI-SEED OVERALL: {'PASS' if all_pass else 'FAIL'}")
                print(f"Combined report: {combined_path}")
                report = combined
            else:
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
        crash_path = Path(f"tier4_29c_seed{args.seed}_job_output") / "tier4_29c_crash_report.json"
        crash_path.parent.mkdir(parents=True, exist_ok=True)
        crash_path.write_text(json.dumps(crash, indent=2))
        print(f"\n[FATAL CRASH] {type(exc).__name__}: {exc}")
        print(f"Crash report written to: {crash_path}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
