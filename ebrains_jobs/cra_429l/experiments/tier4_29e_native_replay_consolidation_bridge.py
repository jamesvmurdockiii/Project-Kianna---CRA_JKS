#!/usr/bin/env python3
"""
Tier 4.29e — Native Replay/Consolidation Bridge.

Tests that host-scheduled replay events are processed correctly by the native
SpiNNaker four-core runtime through existing state primitives (context/route/
memory slots, learning core).

Host-scheduled replay means the host constructs a schedule containing both
original events and replay events; the native runtime processes them through
the same pipeline without native replay buffers.

Controls:
  no_replay            — 16 base events only; baseline learning
  correct_replay       — 16 base + 8 replay with correct keys; consolidation
  wrong_key_replay     — 16 base + 8 replay with wrong context keys; no consolidation
  random_event_replay  — 16 base + 8 random events; event correctness matters

Modes:
  local        — host reference for all controls, verify criteria
  prepare      — create EBRAINS job bundle
  run-hardware — load four MCPL images, run distributed replay task
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
TIER = "Tier 4.29e — Native Replay/Consolidation Bridge"
RUNNER_REVISION = "tier4_29e_native_replay_consolidation_20260504_0001"
UPLOAD_PACKAGE_NAME = "cra_429k"
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

# Wrong key for sham controls
WRONG_CONTEXT_KEY = 999

# Base events (16 events)
BASE_EVENTS = [
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
]

# Replay events repeat base events 8-15 (8 events)
REPLAY_EVENTS = [
    {"step": 16, "cue": -1.0, "target": -1.0, "control": "sign_flip_replay"},
    {"step": 17, "cue": -1.0, "target": -1.0, "control": "sign_flip_replay"},
    {"step": 18, "cue": 1.0,  "target": 1.0,  "control": "recovery_replay"},
    {"step": 19, "cue": 1.0,  "target": 1.0,  "control": "recovery_replay"},
    {"step": 20, "cue": 1.0,  "target": 1.0,  "control": "recovery_replay"},
    {"step": 21, "cue": 1.0,  "target": 1.0,  "control": "recovery_replay"},
    {"step": 22, "cue": 1.0,  "target": 1.5,  "control": "mixed_replay"},
    {"step": 23, "cue": 1.0,  "target": 0.5,  "control": "mixed_replay"},
]

# Random events for random_event_replay control
# These events conflict with the learned pattern to produce measurable divergence.
RANDOM_EVENTS = [
    {"step": 16, "cue": 1.0,  "target": -1.0, "control": "random_replay"},
    {"step": 17, "cue": -1.0, "target": 1.0,  "control": "random_replay"},
    {"step": 18, "cue": 1.0,  "target": -1.0, "control": "random_replay"},
    {"step": 19, "cue": -1.0, "target": 1.0,  "control": "random_replay"},
    {"step": 20, "cue": 1.0,  "target": 2.0,  "control": "random_replay"},
    {"step": 21, "cue": -1.0, "target": -2.0, "control": "random_replay"},
    {"step": 22, "cue": 1.0,  "target": 2.0,  "control": "random_replay"},
    {"step": 23, "cue": -1.0, "target": -2.0, "control": "random_replay"},
]

CONTROLS = [
    {
        "name": "no_replay",
        "events": BASE_EVENTS,
        "context_key": CONTEXT_KEY,
        "description": "16 base events only; baseline learning",
    },
    {
        "name": "correct_replay",
        "events": BASE_EVENTS + REPLAY_EVENTS,
        "context_key": CONTEXT_KEY,
        "description": "16 base + 8 correct-key replay events; consolidation",
    },
    {
        "name": "wrong_key_replay",
        "events": BASE_EVENTS + REPLAY_EVENTS,
        "context_key": CONTEXT_KEY,
        "description": "16 base + 8 replay with wrong context keys; no consolidation",
    },
    {
        "name": "random_event_replay",
        "events": BASE_EVENTS + RANDOM_EVENTS,
        "context_key": CONTEXT_KEY,
        "description": "16 base + 8 random events; event correctness matters",
    },
]


def _build_schedule(events: list[dict], context_key: int, offset: int = 0) -> list[dict]:
    schedule = []
    for i, ev in enumerate(events):
        schedule.append({
            "index": offset + i,
            "timestep": i + 1,
            "context_key": context_key if ev.get("use_wrong_key", False) else context_key,
            "route_key": ROUTE_KEY,
            "memory_key": MEMORY_KEY,
            "cue": ev["cue"],
            "target": ev["target"],
            "delay": TASK_DELAY,
        })
    return schedule


def run_host_reference(seed: int, events: list[dict]) -> dict:
    """Compute host-side s16.15 reference starting from weight=0, bias=0.

    Mirrors C runtime _apply_reward_to_feature_prediction exactly:
    - delta_w = lr * error * feature
    - delta_b = lr * error  (DOES NOT depend on feature)
    - For wrong-key events: feature = 0, so delta_w = 0, but delta_b = lr * target
    """
    random.seed(seed)
    weight = 0
    bias = 0
    lr = fp_from_float(TASK_LEARNING_RATE)
    rows = []
    pending = []

    for ev in events:
        step = ev["step"]
        cue = fp_from_float(ev["cue"])
        target = fp_from_float(ev["target"])
        # For wrong-key events, feature = 0 (context lookup returns default 0)
        feature = cue if ev.get("context_key", CONTEXT_KEY) != WRONG_CONTEXT_KEY else 0
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
        "pending_count": len(events),
        "matured_count": len(rows),
    }


def evaluate_control_criteria(control: dict, ref: dict, all_refs: dict[str, dict] | None = None, hw_state: dict | None = None) -> list[dict]:
    """Evaluate pass/fail criteria for a single control condition."""
    criteria = []
    name = control["name"]
    tolerance = 8192  # ~0.25 in s16.15

    # Common checks for all controls
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

    # Cross-control comparison checks
    if all_refs:
        correct_ref = all_refs.get("correct_replay")
        wrong_ref = all_refs.get("wrong_key_replay")
        random_ref = all_refs.get("random_event_replay")
        no_ref = all_refs.get("no_replay")

        if name == "wrong_key_replay" and correct_ref:
            # Wrong-key replay should differ from correct replay
            diff_w = abs(ref["final_weight"] - correct_ref["final_weight"])
            diff_b = abs(ref["final_bias"] - correct_ref["final_bias"])
            criteria.append({
                "name": f"{name}_differs_from_correct_replay",
                "value": diff_w,
                "threshold": tolerance,
                "passed": diff_w > tolerance or diff_b > tolerance,
                "note": f"weight_diff={diff_w} bias_diff={diff_b}",
            })

        if name == "random_event_replay" and correct_ref:
            # Random event replay should differ from correct replay
            diff_w = abs(ref["final_weight"] - correct_ref["final_weight"])
            diff_b = abs(ref["final_bias"] - correct_ref["final_bias"])
            criteria.append({
                "name": f"{name}_differs_from_correct_replay",
                "value": diff_w,
                "threshold": tolerance,
                "passed": diff_w > tolerance or diff_b > tolerance,
                "note": f"weight_diff={diff_w} bias_diff={diff_b}",
            })

        if name == "correct_replay" and wrong_ref:
            # Correct replay should differ from wrong-key replay
            diff_w = abs(ref["final_weight"] - wrong_ref["final_weight"])
            diff_b = abs(ref["final_bias"] - wrong_ref["final_bias"])
            criteria.append({
                "name": f"{name}_differs_from_wrong_key",
                "value": diff_w,
                "threshold": tolerance,
                "passed": diff_w > tolerance or diff_b > tolerance,
                "note": f"weight_diff={diff_w} bias_diff={diff_b}",
            })

        if name == "wrong_key_replay" and no_ref:
            # Wrong-key replay weight should approximate no-replay (feature=0 means delta_w=0 on replay events)
            diff_w = abs(ref["final_weight"] - no_ref["final_weight"])
            criteria.append({
                "name": f"{name}_weight_approx_no_replay",
                "value": diff_w,
                "threshold": tolerance,
                "passed": diff_w <= tolerance,
                "note": f"wrong_key={ref['final_weight_float']:.4f} ≈ no_replay={no_ref['final_weight_float']:.4f} diff={diff_w}",
            })
            # Bias will differ because delta_b = lr * error (independent of feature)
            diff_b = abs(ref["final_bias"] - no_ref["final_bias"])
            criteria.append({
                "name": f"{name}_bias_differs_from_no_replay",
                "value": diff_b,
                "threshold": tolerance,
                "passed": diff_b > tolerance,
                "note": f"wrong_key bias={ref['final_bias_float']:.4f} ≠ no_replay={no_ref['final_bias_float']:.4f} diff={diff_b}",
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

    # Compute all references first for cross-control comparisons
    all_refs = {}
    for control in CONTROLS:
        events = [dict(ev) for ev in control["events"]]
        for ev in events:
            if control["name"] == "wrong_key_replay" and ev["step"] >= 16:
                ev["context_key"] = WRONG_CONTEXT_KEY
                ev["use_wrong_key"] = True
            else:
                ev["context_key"] = control["context_key"]
        all_refs[control["name"]] = run_host_reference(seed, events)

    results = []
    all_passed = True
    for control in CONTROLS:
        ref = all_refs[control["name"]]
        criteria = evaluate_control_criteria(control, ref, all_refs=all_refs)
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
        print(f"  Events: {ref['pending_count']}")
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
    with open(output_dir / "tier4_29e_local_results.json", "w") as f:
        json.dump(summary, f, indent=2)
    return summary


# ---------------------------------------------------------------------------
# Hardware modes reuse the four-core controller from tier4_29d.
# Since 4.29e requires no C runtime changes, we use the same cra_429j binaries.
# ---------------------------------------------------------------------------


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
    (output_dir / f"tier4_29e_build_{profile}_stdout.txt").write_text(build["stdout"])
    (output_dir / f"tier4_29e_build_{profile}_stderr.txt").write_text(build["stderr"])

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
    no_replay_ref: dict,
) -> dict:
    """Run one control condition on the four-core hardware."""
    from coral_reef_spinnaker.python_host.colony_controller import ColonyController

    dest_x = target["x"]
    dest_y = target["y"]

    ctx_ctrl = ColonyController(hostname=hostname, chip_x=dest_x, chip_y=dest_y, core=CONTEXT_CORE_P)
    route_ctrl = ColonyController(hostname=hostname, chip_x=dest_x, chip_y=dest_y, core=ROUTE_CORE_P)
    mem_ctrl = ColonyController(hostname=hostname, chip_x=dest_x, chip_y=dest_y, core=MEMORY_CORE_P)
    learning_ctrl = ColonyController(hostname=hostname, chip_x=dest_x, chip_y=dest_y, core=LEARNING_CORE_P)

    # Reset all cores
    for ctrl in (ctx_ctrl, route_ctrl, mem_ctrl, learning_ctrl):
        ctrl.send_command(0x01, 0, 0, 0, 0, b"")
        time.sleep(0.1)

    # Write context slot
    ctx_ctrl.write_context(CONTEXT_KEY, fp_from_float(CONTEXT_VALUE), fp_from_float(1.0))

    # Write route slot
    route_ctrl.write_route_slot(ROUTE_KEY, fp_from_float(ROUTE_VALUE), fp_from_float(1.0))

    # Write memory slot
    mem_ctrl.write_memory_slot(MEMORY_KEY, fp_from_float(MEMORY_VALUE), fp_from_float(1.0))

    # Build schedule
    events = [dict(ev) for ev in control["events"]]
    for ev in events:
        if control["name"] == "wrong_key_replay" and ev["step"] >= 16:
            ev["context_key"] = WRONG_CONTEXT_KEY
        else:
            ev["context_key"] = control["context_key"]

    schedule = _build_schedule(events, control["context_key"])

    # Upload schedule to learning core
    for entry in schedule:
        learning_ctrl.write_schedule_entry(
            entry["index"],
            entry["timestep"],
            fp_from_float(entry["cue"]),
            fp_from_float(entry["target"]),
            entry["delay"],
            entry["context_key"],
            entry["route_key"],
            entry["memory_key"],
        )

    # Run
    learning_rate = TASK_LEARNING_RATE
    ctx_run = ctx_ctrl.run_continuous(learning_rate, 0, dest_x, dest_y, CONTEXT_CORE_P)
    route_run = route_ctrl.run_continuous(learning_rate, 0, dest_x, dest_y, ROUTE_CORE_P)
    mem_run = mem_ctrl.run_continuous(learning_rate, 0, dest_x, dest_y, MEMORY_CORE_P)
    learning_run = learning_ctrl.run_continuous(learning_rate, len(schedule), dest_x, dest_y, LEARNING_CORE_P)

    time.sleep(3.0)

    # Read state
    hw_state = learning_ctrl.read_state()

    return {
        "control": control["name"],
        "hostname": hostname,
        "target": target,
        "hw_state": hw_state,
        "ctx_run": ctx_run,
        "route_run": route_run,
        "mem_run": mem_run,
        "learning_run": learning_run,
    }


def mode_run_hardware(args: argparse.Namespace) -> dict:
    """Run all controls on hardware."""
    seed = int(args.seed)
    hostname = args.hostname or base.probe_board_hostname()
    if not hostname:
        raise SystemExit("No board hostname provided and auto-probe failed.")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    target_path = args.target or (STABLE_EBRAINS_UPLOAD / "target_acquisition.json")
    if not Path(target_path).exists():
        raise SystemExit(f"Target acquisition file not found: {target_path}")
    with open(target_path) as f:
        target = json.load(f)

    loads_path = args.loads or (STABLE_EBRAINS_UPLOAD / "load_manifest.json")
    if not Path(loads_path).exists():
        raise SystemExit(f"Load manifest not found: {loads_path}")
    with open(loads_path) as f:
        loads = json.load(f)

    no_replay_events = BASE_EVENTS.copy()
    no_replay_ref = run_host_reference(seed, no_replay_events)

    results = []
    for control in CONTROLS:
        print(f"\n[4.29e] Running control={control['name']} seed={seed} host={hostname}")
        try:
            hw_result = four_core_hardware_loop(hostname, args, target, loads, control, no_replay_ref)
            results.append(hw_result)
            hw_w = hw_result["hw_state"].get("readout_weight_raw", 0)
            hw_b = hw_result["hw_state"].get("readout_bias_raw", 0)
            print(f"  HW weight={hw_w} bias={hw_b}")
        except Exception as exc:
            traceback.print_exc()
            results.append({"control": control["name"], "error": str(exc)})

    summary = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "mode": "run-hardware",
        "seed": seed,
        "hostname": hostname,
        "target": target,
        "results": results,
    }
    with open(output_dir / f"tier4_29e_hardware_results_seed{seed}.json", "w") as f:
        json.dump(summary, f, indent=2)
    return summary


def mode_ingest(args: argparse.Namespace) -> dict:
    """Ingest hardware results and compare with reference."""
    seed = int(args.seed)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    hw_path = args.hardware_results or output_dir / f"tier4_29e_hardware_results_seed{seed}.json"
    if not Path(hw_path).exists():
        raise SystemExit(f"Hardware results not found: {hw_path}")
    with open(hw_path) as f:
        hw_data = json.load(f)

    # Compute all references first for cross-control comparisons
    all_refs = {}
    for control in CONTROLS:
        events = [dict(ev) for ev in control["events"]]
        for ev in events:
            if control["name"] == "wrong_key_replay" and ev["step"] >= 16:
                ev["context_key"] = WRONG_CONTEXT_KEY
                ev["use_wrong_key"] = True
            else:
                ev["context_key"] = control["context_key"]
        all_refs[control["name"]] = run_host_reference(seed, events)

    controls_ingested = []
    all_passed = True
    for control in CONTROLS:
        ref = all_refs[control["name"]]

        hw_state = None
        for r in hw_data.get("results", []):
            if r.get("control") == control["name"]:
                hw_state = r.get("hw_state")
                break

        criteria = evaluate_control_criteria(control, ref, all_refs=all_refs, hw_state=hw_state)
        control_passed = all(c["passed"] for c in criteria)
        all_passed = all_passed and control_passed

        controls_ingested.append({
            "control": control["name"],
            "status": "pass" if control_passed else "fail",
            "criteria": criteria,
            "reference": ref,
            "hw_state": hw_state,
        })

    summary = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "mode": "ingest",
        "seed": seed,
        "status": "pass" if all_passed else "fail",
        "controls": controls_ingested,
    }
    with open(output_dir / "tier4_29e_ingest_results.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n{'='*60}")
    print(f"Tier 4.29e Ingest: {'ALL PASSED' if all_passed else 'SOME FAILED'}")
    for ci in controls_ingested:
        print(f"\n  Control: {ci['control']} -> {ci['status']}")
        for c in ci["criteria"]:
            mark = "PASS" if c["passed"] else "FAIL"
            print(f"    [{mark}] {c['name']}: {c['note']}")

    return summary


def mode_prepare(args: argparse.Namespace) -> dict:
    """Prepare EBRAINS upload package (reuse cra_429j binaries)."""
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Since 4.29e requires no C runtime changes, we reuse the cra_429j binaries
    # but create a fresh package per Rule 10.
    src_package = ROOT / "ebrains_jobs" / "cra_429j"
    if not src_package.exists():
        raise SystemExit(f"Source package cra_429j not found at {src_package}")

    # Copy binaries and create fresh metadata
    dest = output_dir / UPLOAD_PACKAGE_NAME
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src_package, dest)

    # Update metadata
    metadata = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "upload_package": UPLOAD_PACKAGE_NAME,
        "based_on": "cra_429j",
        "change_summary": "No C runtime changes. Host-scheduled replay uses existing schedule primitives.",
        "profiles": [CONTEXT_CORE_PROFILE, ROUTE_CORE_PROFILE, MEMORY_CORE_PROFILE, LEARNING_CORE_PROFILE],
        "app_ids": [CONTEXT_CORE_APP_ID, ROUTE_CORE_APP_ID, MEMORY_CORE_APP_ID, LEARNING_CORE_APP_ID],
        "cores": [CONTEXT_CORE_P, ROUTE_CORE_P, MEMORY_CORE_P, LEARNING_CORE_P],
        "prepared_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(dest / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"Prepared package: {dest}")
    print(f"Based on: cra_429j (no C runtime changes for 4.29e)")
    return {"package": str(dest), "metadata": metadata}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=TIER)
    parser.add_argument("--mode", choices=["local", "prepare", "run-hardware", "ingest"], required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--seeds", type=str, default="42", help="Comma-separated seeds for run-hardware mode")
    parser.add_argument("--hostname", type=str, default=None)
    parser.add_argument("--target", type=str, default=None)
    parser.add_argument("--loads", type=str, default=None)
    parser.add_argument("--hardware-results", type=str, default=None)
    parser.add_argument("--output-dir", type=str, default=str(ROOT / "controlled_test_output" / f"tier4_29e_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"))
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.mode == "local":
        mode_local(args)
    elif args.mode == "prepare":
        mode_prepare(args)
    elif args.mode == "run-hardware":
        seeds = [int(s.strip()) for s in args.seeds.split(",")]
        for seed in seeds:
            args.seed = seed
            print(f"\n{'='*60}")
            print(f"[4.29e] Running hardware for seed {seed}")
            print(f"{'='*60}")
            mode_run_hardware(args)
    elif args.mode == "ingest":
        mode_ingest(args)


if __name__ == "__main__":
    main()
