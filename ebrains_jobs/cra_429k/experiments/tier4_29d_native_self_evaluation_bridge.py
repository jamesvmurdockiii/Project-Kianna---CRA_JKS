#!/usr/bin/env python3
"""
Tier 4.29d — Native Self-Evaluation Bridge.

Tests that the native SpiNNaker learning_core modulates plasticity by the
composite confidence of contextual, routing, and memory slots.

Composite confidence = product(context_conf, route_conf, memory_conf) in s16.15.
Effective learning rate = base_lr * composite_confidence.

Controls:
  full_confidence          — all slots confidence=1.0; learning proceeds normally
  zero_confidence          — all slots confidence=0.0; no learning
  zero_context_confidence  — context confidence=0.0, others=1.0; no learning
  half_context_confidence  — context confidence=0.5, others=1.0; reduced learning

Modes:
  local        — host reference for all controls, verify criteria
  prepare      — create EBRAINS job bundle
  run-hardware — load four MCPL images, run distributed self-evaluation task
  ingest       — compare hardware results with reference
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
TIER = "Tier 4.29d — Native Self-Evaluation Bridge"
RUNNER_REVISION = "tier4_29d_native_self_evaluation_20260504_0002"
UPLOAD_PACKAGE_NAME = "cra_429j"
STABLE_EBRAINS_UPLOAD = ROOT / "ebrains_jobs" / UPLOAD_PACKAGE_NAME

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

TASK_LEARNING_RATE = 0.25
TASK_DELAY = 2

CONTEXT_KEY = 101
CONTEXT_VALUE = 1.0
ROUTE_KEY = 201
ROUTE_VALUE = 1.0
MEMORY_KEY = 301
MEMORY_VALUE = 1.0

TASK_EVENTS = [
    {"step": 0,  "cue": 1.0,  "target": 1.0,  "control": "zero_error"},
    {"step": 1,  "cue": 1.0,  "target": 1.0,  "control": "zero_error"},
    {"step": 2,  "cue": 1.0,  "target": 1.0,  "control": "zero_error"},
    {"step": 3,  "cue": 1.0,  "target": 1.0,  "control": "zero_error"},
    {"step": 4,  "cue": 1.0,  "target": 2.0,  "control": "positive_err"},
    {"step": 5,  "cue": 1.0,  "target": 2.0,  "control": "positive_err"},
    {"step": 6,  "cue": 1.0,  "target": 0.0,  "control": "negative_err"},
    {"step": 7,  "cue": 1.0,  "target": 0.0,  "control": "negative_err"},
    {"step": 8,  "cue": -1.0, "target": -1.0, "control": "sign_flip"},
    {"step": 9,  "cue": -1.0, "target": -1.0, "control": "sign_flip"},
    {"step": 10, "cue": 1.0,  "target": 1.0,  "control": "recovery"},
    {"step": 11, "cue": 1.0,  "target": 1.0,  "control": "recovery"},
    {"step": 12, "cue": 1.0,  "target": 1.0,  "control": "recovery"},
    {"step": 13, "cue": 1.0,  "target": 1.0,  "control": "recovery"},
    {"step": 14, "cue": 1.0,  "target": 1.5,  "control": "mixed"},
    {"step": 15, "cue": 1.0,  "target": 0.5,  "control": "mixed"},
    {"step": 16, "cue": 1.0,  "target": 1.0,  "control": "recovery"},
    {"step": 17, "cue": 1.0,  "target": 1.0,  "control": "recovery"},
    {"step": 18, "cue": -1.0, "target": -1.0, "control": "sign_flip"},
    {"step": 19, "cue": -1.0, "target": -1.0, "control": "sign_flip"},
]

CONTROLS = [
    {
        "name": "full_confidence",
        "context_conf": 1.0,
        "route_conf": 1.0,
        "memory_conf": 1.0,
        "description": "All slot confidences = 1.0; full learning rate",
    },
    {
        "name": "zero_confidence",
        "context_conf": 0.0,
        "route_conf": 0.0,
        "memory_conf": 0.0,
        "description": "All slot confidences = 0.0; learning blocked",
    },
    {
        "name": "zero_context_confidence",
        "context_conf": 0.0,
        "route_conf": 1.0,
        "memory_conf": 1.0,
        "description": "Context confidence = 0.0; product = 0; learning blocked",
    },
    {
        "name": "half_context_confidence",
        "context_conf": 0.5,
        "route_conf": 1.0,
        "memory_conf": 1.0,
        "description": "Context confidence = 0.5; product = 0.5; reduced learning",
    },
]


def _build_schedule(events: list[dict], offset: int = 0) -> list[dict]:
    schedule = []
    for i, ev in enumerate(events):
        schedule.append({
            "index": offset + i,
            "timestep": i + 1,
            "context_key": CONTEXT_KEY,
            "route_key": ROUTE_KEY,
            "memory_key": MEMORY_KEY,
            "cue": ev["cue"],
            "target": ev["target"],
            "delay": TASK_DELAY,
        })
    return schedule


def run_host_reference(seed: int, confidences: dict) -> dict:
    """Compute host-side s16.15 reference starting from weight=0, bias=0."""
    random.seed(seed)
    weight = 0
    bias = 0
    lr = fp_from_float(TASK_LEARNING_RATE)
    ctx_conf = fp_from_float(confidences["context_conf"])
    route_conf = fp_from_float(confidences["route_conf"])
    mem_conf = fp_from_float(confidences["memory_conf"])
    composite_confidence = fp_mul(fp_mul(ctx_conf, route_conf), mem_conf)
    effective_lr = fp_mul(lr, composite_confidence)
    rows = []
    pending = []

    for ev in TASK_EVENTS:
        step = ev["step"]
        cue = fp_from_float(ev["cue"])
        target = fp_from_float(ev["target"])
        feature = cue
        prediction = fp_mul(weight, feature) + bias
        pending.append({
            "step": step,
            "feature": feature,
            "prediction": prediction,
            "target": target,
            "due_step": step + TASK_DELAY,
            "control": ev["control"],
        })
        while pending and pending[0]["due_step"] <= step:
            p = pending.pop(0)
            err = p["target"] - p["prediction"]
            delta_w = fp_mul(effective_lr, fp_mul(err, p["feature"]))
            delta_b = fp_mul(effective_lr, err)
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

    while pending:
        p = pending.pop(0)
        err = p["target"] - p["prediction"]
        delta_w = fp_mul(effective_lr, fp_mul(err, p["feature"]))
        delta_b = fp_mul(effective_lr, err)
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
        "confidences": confidences,
        "composite_confidence": fp_to_float(composite_confidence),
        "effective_lr": fp_to_float(effective_lr),
        "final_weight": weight,
        "final_bias": bias,
        "final_weight_float": fp_to_float(weight),
        "final_bias_float": fp_to_float(bias),
        "rows": rows,
        "pending_count": len(TASK_EVENTS),
        "matured_count": len(rows),
    }


def evaluate_control_criteria(control: dict, ref: dict, hw_state: dict | None = None) -> list[dict]:
    """Evaluate pass/fail criteria for a single control condition."""
    criteria = []
    name = control["name"]
    tolerance = 8192  # ~0.25 in s16.15

    if name in ("zero_confidence", "zero_context_confidence"):
        # Exact match: no learning occurred
        criteria.append({
            "name": f"{name}_weight_zero",
            "value": ref["final_weight"],
            "threshold": 0,
            "passed": ref["final_weight"] == 0,
            "note": f"final weight = {ref['final_weight_float']:.4f}",
        })
        criteria.append({
            "name": f"{name}_bias_zero",
            "value": ref["final_bias"],
            "threshold": 0,
            "passed": ref["final_bias"] == 0,
            "note": f"final bias = {ref['final_bias_float']:.4f}",
        })
    elif name == "half_context_confidence":
        # Directional check: magnitude of weight/bias change should be smaller than full-confidence
        full_w = ref.get("_full_ref_weight", 1 << 30)
        full_b = ref.get("_full_ref_bias", 1 << 30)
        criteria.append({
            "name": f"{name}_weight_magnitude_less_than_full",
            "value": abs(ref["final_weight"]),
            "threshold": f"abs(w) < abs(full_ref)={abs(full_w)}",
            "passed": abs(ref["final_weight"]) < abs(full_w),
            "note": f"final weight = {ref['final_weight_float']:.4f} (full={fp_to_float(full_w):.4f})",
        })
        criteria.append({
            "name": f"{name}_bias_magnitude_less_than_full",
            "value": abs(ref["final_bias"]),
            "threshold": f"abs(b) < abs(full_ref)={abs(full_b)}",
            "passed": abs(ref["final_bias"]) < abs(full_b),
            "note": f"final bias = {ref['final_bias_float']:.4f} (full={fp_to_float(full_b):.4f})",
        })
    else:  # full_confidence
        criteria.append({
            "name": f"{name}_weight_finite",
            "value": abs(ref["final_weight"]),
            "threshold": 65536,
            "passed": abs(ref["final_weight"]) <= 65536,
            "note": f"final weight = {ref['final_weight_float']:.4f}",
        })
        criteria.append({
            "name": f"{name}_bias_finite",
            "value": abs(ref["final_bias"]),
            "threshold": 65536,
            "passed": abs(ref["final_bias"]) <= 65536,
            "note": f"final bias = {ref['final_bias_float']:.4f}",
        })

    if hw_state is not None:
        hw_w = hw_state.get("readout_weight_raw", 0)
        hw_b = hw_state.get("readout_bias_raw", 0)
        criteria.append({
            "name": f"{name}_hardware_weight_within_tolerance",
            "value": hw_w,
            "threshold": tolerance,
            "passed": abs(hw_w - ref["final_weight"]) <= tolerance,
            "note": f"hw={hw_w} ref={ref['final_weight']} diff={abs(hw_w - ref['final_weight'])}",
        })
        criteria.append({
            "name": f"{name}_hardware_bias_within_tolerance",
            "value": hw_b,
            "threshold": tolerance,
            "passed": abs(hw_b - ref["final_bias"]) <= tolerance,
            "note": f"hw={hw_b} ref={ref['final_bias']} diff={abs(hw_b - ref['final_bias'])}",
        })

    criteria.append({
        "name": f"{name}_all_events_matured",
        "value": ref["matured_count"],
        "threshold": ref["pending_count"],
        "passed": ref["matured_count"] == ref["pending_count"],
        "note": f"matured {ref['matured_count']}/{ref['pending_count']}",
    })

    return criteria


def mode_local(args: argparse.Namespace) -> dict:
    """Run local host reference for all controls and verify criteria."""
    seed = int(args.seed)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Compute full reference once for directional checks
    full_ref = run_host_reference(seed, {
        "context_conf": 1.0, "route_conf": 1.0, "memory_conf": 1.0,
    })

    results = []
    all_passed = True
    for control in CONTROLS:
        ref = run_host_reference(seed, {
            "context_conf": control["context_conf"],
            "route_conf": control["route_conf"],
            "memory_conf": control["memory_conf"],
        })
        if control["name"] == "half_context_confidence":
            ref["_full_ref_weight"] = full_ref["final_weight"]
            ref["_full_ref_bias"] = full_ref["final_bias"]

        criteria = evaluate_control_criteria(control, ref)
        control_passed = all(c["passed"] for c in criteria)
        all_passed = all_passed and control_passed

        result = {
            "control": control["name"],
            "description": control["description"],
            "status": "pass" if control_passed else "fail",
            "criteria": criteria,
            "reference": ref,
        }
        results.append(result)

        print(f"\nControl: {control['name']}")
        print(f"  Composite confidence: {ref['composite_confidence']:.4f}")
        print(f"  Final weight: {ref['final_weight_float']:.4f}, bias: {ref['final_bias_float']:.4f}")
        for c in criteria:
            mark = "PASS" if c["passed"] else "FAIL"
            print(f"    [{mark}] {c['name']}: {c['note']}")

    summary = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "mode": "local",
        "seed": seed,
        "status": "pass" if all_passed else "fail",
        "controls": results,
    }
    with open(output_dir / "tier4_29d_local_results.json", "w") as f:
        json.dump(summary, f, indent=2)
    return summary


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
    (output_dir / f"tier4_29d_build_{profile}_stdout.txt").write_text(build["stdout"])
    (output_dir / f"tier4_29d_build_{profile}_stderr.txt").write_text(build["stderr"])

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


def four_core_hardware_loop(
    hostname: str,
    args: argparse.Namespace,
    target: dict,
    loads: dict[str, dict],
    control: dict,
    full_ref: dict,
) -> dict:
    """Run one control condition on the four-core hardware."""
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

    # Write slots with control-specific confidence
    ctx_writes = []
    route_writes = []
    mem_writes = []

    ok = ctx_ctrl.write_context(
        CONTEXT_KEY, CONTEXT_VALUE, control["context_conf"], dest_x, dest_y, CONTEXT_CORE_P
    )
    ctx_writes.append({"key": CONTEXT_KEY, "success": ok.get("success") is True})

    ok = route_ctrl.write_route_slot(
        ROUTE_KEY, ROUTE_VALUE, control["route_conf"], dest_x, dest_y, ROUTE_CORE_P
    )
    route_writes.append({"key": ROUTE_KEY, "success": ok.get("success") is True})

    ok = mem_ctrl.write_memory_slot(
        MEMORY_KEY, MEMORY_VALUE, control["memory_conf"], dest_x, dest_y, MEMORY_CORE_P
    )
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

    # Wait for completion
    max_wait = 10.0
    poll_interval = 0.5
    waited = 0.0
    while waited < max_wait:
        time.sleep(poll_interval)
        waited += poll_interval
        learning_status = learning_ctrl.read_state(dest_x, dest_y, LEARNING_CORE_P)
        if learning_status.get("success") and learning_status.get("active_pending") == 0:
            break

    # Pause all cores
    ctx_pause = ctx_ctrl.pause(dest_x, dest_y, CONTEXT_CORE_P)
    route_pause = route_ctrl.pause(dest_x, dest_y, ROUTE_CORE_P)
    mem_pause = mem_ctrl.pause(dest_x, dest_y, MEMORY_CORE_P)
    learning_pause = learning_ctrl.pause(dest_x, dest_y, LEARNING_CORE_P)
    time.sleep(0.1)

    # Read back final state
    ctx_final = ctx_ctrl.read_state(dest_x, dest_y, CONTEXT_CORE_P)
    route_final = route_ctrl.read_state(dest_x, dest_y, ROUTE_CORE_P)
    mem_final = mem_ctrl.read_state(dest_x, dest_y, MEMORY_CORE_P)
    learning_final = learning_ctrl.read_state(dest_x, dest_y, LEARNING_CORE_P)

    # Compute host reference for this control
    ref = run_host_reference(int(args.seed), {
        "context_conf": control["context_conf"],
        "route_conf": control["route_conf"],
        "memory_conf": control["memory_conf"],
    })
    if control["name"] == "half_context_confidence":
        ref["_full_ref_weight"] = full_ref["final_weight"]
        ref["_full_ref_bias"] = full_ref["final_bias"]

    criteria = evaluate_control_criteria(control, ref, learning_final)

    return {
        "status": "completed",
        "control": control["name"],
        "criteria": criteria,
        "reference": {
            "final_weight_raw": ref["final_weight"],
            "final_bias_raw": ref["final_bias"],
            "final_weight_float": ref["final_weight_float"],
            "final_bias_float": ref["final_bias_float"],
        },
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
    """Run four-core distributed self-evaluation task on hardware."""
    print(TIER)
    print("=" * 60)

    default_dir = f"tier4_29d_seed{args.seed}_job_output"
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

    loads: dict[str, dict] = {
        "context": {"status": "not_attempted"},
        "route": {"status": "not_attempted"},
        "memory": {"status": "not_attempted"},
        "learning": {"status": "not_attempted"},
    }

    write_json(output_dir / "tier4_29d_environment.json", env_report)
    write_json(output_dir / "tier4_29d_target_acquisition.json", base.public_target_acquisition(target))

    # Compute full reference for directional checks
    full_ref = run_host_reference(int(args.seed), {
        "context_conf": 1.0, "route_conf": 1.0, "memory_conf": 1.0,
    })

    control_results = []
    hardware_exception = None

    try:
        if target.get("status") == "pass" and hostname:
            # Load applications once
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
                write_json(output_dir / f"tier4_29d_{name}_load.json", load_info)

        if (target.get("status") == "pass" and hostname
            and all(l.get("status") == "pass" for l in loads.values())):
            print("\n[3/4] Running control conditions...")
            for control in CONTROLS:
                print(f"\n  -> Control: {control['name']}")
                result = four_core_hardware_loop(hostname, args, target, loads, control, full_ref)
                control_results.append(result)
                write_json(output_dir / f"tier4_29d_task_{control['name']}.json", result)
                for c in result["criteria"]:
                    mark = "PASS" if c["passed"] else "FAIL"
                    print(f"      [{mark}] {c['name']}: {c['note']}")

    except Exception as exc:
        hardware_exception = {
            "exception_type": type(exc).__name__,
            "exception": str(exc),
            "traceback": traceback.format_exc(),
        }
        print(f"\n[HARDWARE EXCEPTION] {type(exc).__name__}: {exc}")
    finally:
        base.release_hardware_target(target)
        write_json(output_dir / "tier4_29d_environment.json", env_report)
        write_json(output_dir / "tier4_29d_target_acquisition.json", base.public_target_acquisition(target))
        for name, load_info in loads.items():
            write_json(output_dir / f"tier4_29d_{name}_load.json", load_info)

    # Aggregate criteria across controls
    all_criteria = []
    for result in control_results:
        all_criteria.extend(result["criteria"])

    # Add build/load criteria
    all_criteria.insert(0, {"name": "runner revision current", "value": RUNNER_REVISION, "rule": "expected current source", "passed": True, "note": ""})
    all_criteria.insert(1, {"name": "custom C host tests pass", "value": host_tests.get("status"), "rule": "== pass", "passed": host_tests.get("status") == "pass", "note": ""})
    all_criteria.insert(2, {"name": "main.c syntax check pass", "value": main_syntax.get("status"), "rule": "== pass", "passed": main_syntax.get("status") == "pass", "note": ""})
    all_criteria.insert(3, {"name": "hardware target acquired", "value": base.public_target_acquisition(target), "rule": "status == pass", "passed": target.get("status") == "pass", "note": ""})
    all_criteria.insert(4, {"name": "context_core .aplx built", "value": ctx_build["aplx_exists"], "rule": "== True", "passed": ctx_build["aplx_exists"], "note": ""})
    all_criteria.insert(5, {"name": "route_core .aplx built", "value": route_build["aplx_exists"], "rule": "== True", "passed": route_build["aplx_exists"], "note": ""})
    all_criteria.insert(6, {"name": "memory_core .aplx built", "value": mem_build["aplx_exists"], "rule": "== True", "passed": mem_build["aplx_exists"], "note": ""})
    all_criteria.insert(7, {"name": "learning_core .aplx built", "value": learning_build["aplx_exists"], "rule": "== True", "passed": learning_build["aplx_exists"], "note": ""})
    all_criteria.insert(8, {"name": "context_core load pass", "value": loads["context"].get("status"), "rule": "== pass", "passed": loads["context"].get("status") == "pass", "note": ""})
    all_criteria.insert(9, {"name": "route_core load pass", "value": loads["route"].get("status"), "rule": "== pass", "passed": loads["route"].get("status") == "pass", "note": ""})
    all_criteria.insert(10, {"name": "memory_core load pass", "value": loads["memory"].get("status"), "rule": "== pass", "passed": loads["memory"].get("status") == "pass", "note": ""})
    all_criteria.insert(11, {"name": "learning_core load pass", "value": loads["learning"].get("status"), "rule": "== pass", "passed": loads["learning"].get("status") == "pass", "note": ""})

    all_passed = all(c["passed"] for c in all_criteria)
    report = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "mode": "run-hardware",
        "seed": int(args.seed),
        "hostname": hostname,
        "status": "pass" if all_passed else "fail",
        "criteria": all_criteria,
        "control_results": control_results,
        "loads": {k: {"status": v.get("status")} for k, v in loads.items()},
    }
    if hardware_exception:
        report["hardware_exception"] = hardware_exception

    write_json(output_dir / "tier4_29d_report.json", report)

    print(f"\nHardware seed {args.seed}: {'PASS' if all_passed else 'FAIL'}")
    for c in all_criteria:
        mark = "PASS" if c["passed"] else "FAIL"
        print(f"  [{mark}] {c['name']}: {c['note']}")

    return report


def mode_prepare(args: argparse.Namespace) -> dict:
    """Create EBRAINS upload bundle."""
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    bundle = output_dir / "ebrains_upload_bundle" / UPLOAD_PACKAGE_NAME
    if bundle.exists():
        shutil.rmtree(bundle)
    (bundle / "experiments").mkdir(parents=True, exist_ok=True)
    (bundle / "coral_reef_spinnaker" / "python_host").mkdir(parents=True, exist_ok=True)

    (bundle / "experiments" / "__init__.py").write_text("# experiments package\n", encoding="utf-8")
    scripts = [
        "tier4_29d_native_self_evaluation_bridge.py",
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

    readme = bundle / f"README_TIER4_29D_JOB.md"
    readme.write_text(f"""# {TIER}

Upload folder: `{UPLOAD_PACKAGE_NAME}`

Command:
```text
{UPLOAD_PACKAGE_NAME}/experiments/tier4_29d_native_self_evaluation_bridge.py --mode run-hardware --seeds 42,43,44
```

Purpose: Verify that the native learning_core modulates plasticity by the
composite confidence of contextual, routing, and memory slots.
Controls: full confidence, zero confidence, zero-context confidence,
half-context confidence.
""")

    if STABLE_EBRAINS_UPLOAD.exists() or STABLE_EBRAINS_UPLOAD.is_symlink():
        STABLE_EBRAINS_UPLOAD.unlink()
    STABLE_EBRAINS_UPLOAD.symlink_to(bundle.resolve(), target_is_directory=True)

    results = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "mode": "prepare",
        "status": "prepared",
        "upload_folder": str(bundle),
        "stable_upload_folder": str(STABLE_EBRAINS_UPLOAD),
        "jobmanager_command": f"{UPLOAD_PACKAGE_NAME}/experiments/tier4_29d_native_self_evaluation_bridge.py --mode run-hardware --seeds 42,43,44",
    }
    with open(output_dir / "tier4_29d_prepare_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"Prepared: {bundle}")
    print(f"Stable:   {STABLE_EBRAINS_UPLOAD}")
    return results


def mode_ingest(args: argparse.Namespace) -> dict:
    """Ingest hardware results."""
    output_dir = Path(args.output_dir)
    seeds = [int(s.strip()) for s in args.seeds.split(",")]

    all_results = []
    for seed in seeds:
        hw_file = output_dir / f"tier4_29d_report_seed{seed}.json"
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

    with open(output_dir / "tier4_29d_ingest_results.json", "w") as f:
        json.dump(ingest_summary, f, indent=2)

    print(f"Ingest: {passed_criteria}/{total_criteria} criteria passed across {len(seeds)} seed(s)")
    return ingest_summary


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> int:
    parser = argparse.ArgumentParser(description=TIER)
    parser.add_argument("--mode", choices=["local", "prepare", "run-hardware", "ingest"], default="local")
    parser.add_argument("--output-dir", default="tier4_29d_output")
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
                combined_path = Path(f"tier4_29d_multi_seed_job_output") / "tier4_29d_combined_results.json"
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
        crash_path = Path(f"tier4_29d_seed{args.seed}_job_output") / "tier4_29d_crash_report.json"
        crash_path.parent.mkdir(parents=True, exist_ok=True)
        crash_path.write_text(json.dumps(crash, indent=2))
        print(f"\n[FATAL CRASH] {type(exc).__name__}: {exc}")
        print(f"Crash report written to: {crash_path}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
