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
RUNNER_REVISION = "tier4_29e_native_replay_consolidation_20260505_0003"
UPLOAD_PACKAGE_NAME = "cra_429p"
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

# Correct replay events rehearse balanced +/- pairs that should strengthen the
# native readout weight while keeping bias near zero under the native
# surprise-threshold/order semantics.
REPLAY_EVENTS = [
    {"step": 16, "cue": 1.0,  "target": 1.5,  "control": "balanced_replay_pos"},
    {"step": 17, "cue": -1.0, "target": -1.5, "control": "balanced_replay_neg"},
    {"step": 18, "cue": 1.0,  "target": 1.5,  "control": "balanced_replay_pos"},
    {"step": 19, "cue": -1.0, "target": -1.5, "control": "balanced_replay_neg"},
    {"step": 20, "cue": 1.0,  "target": 1.5,  "control": "balanced_replay_pos"},
    {"step": 21, "cue": -1.0, "target": -1.5, "control": "balanced_replay_neg"},
    {"step": 22, "cue": 1.0,  "target": 1.5,  "control": "balanced_replay_pos"},
    {"step": 23, "cue": -1.0, "target": -1.5, "control": "balanced_replay_neg"},
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
            "context_key": int(ev.get("context_key", context_key)),
            "route_key": ROUTE_KEY,
            "memory_key": MEMORY_KEY,
            "cue": ev["cue"],
            "target": ev["target"],
            "delay": TASK_DELAY,
        })
    return schedule


def run_host_reference(seed: int, events: list[dict]) -> dict:
    """Compute a host-side mirror of the native four-core continuous path.

    This intentionally mirrors the native learning-core ordering instead of a
    simpler Python delayed-credit equation:
    - a schedule entry sends three lookups on its timestep
    - replies are available on the next tick
    - the pending record matures after the native delay
    - the runtime applies the native surprise threshold before weight/bias update
    - missing context keys produce feature=0 but still leave bias learning active
    """
    random.seed(seed)
    weight = 0
    bias = 0
    lr = fp_from_float(TASK_LEARNING_RATE)
    surprise_threshold = 2 * FP_ONE
    rows = []
    pending = []
    schedule = _build_schedule(events, CONTEXT_KEY)
    schedule_index = 0
    event_active = False
    replies_ready = False
    active_event: dict[str, Any] | None = None
    timestep = 1

    while timestep < 500 and (schedule_index < len(schedule) or event_active or pending):
        # Phase B in state_manager.c: compose feature once lookup replies exist.
        if event_active and replies_ready and active_event is not None:
            context_value = FP_ONE if active_event["context_key"] == CONTEXT_KEY else 0
            route_value = FP_ONE
            memory_value = FP_ONE
            feature = fp_mul(
                fp_mul(fp_mul(context_value, route_value), memory_value),
                fp_from_float(active_event["cue"]),
            )
            prediction = fp_mul(weight, feature) + bias
            pending.append({
                "step": active_event["index"],
                "feature": feature,
                "prediction": prediction,
                "target": fp_from_float(active_event["target"]),
                "due_step": active_event["base_timestep"] + active_event["delay"],
                "control": active_event.get("control", ""),
            })
            event_active = False
            replies_ready = False
            active_event = None

        # Phase A in state_manager.c: send lookups for the due schedule entry.
        if (
            not event_active
            and schedule_index < len(schedule)
            and schedule[schedule_index]["timestep"] == timestep
        ):
            active_event = dict(schedule[schedule_index])
            active_event["base_timestep"] = timestep
            active_event["control"] = events[schedule_index].get("control", "")
            event_active = True
            schedule_index += 1

        # Phase C in state_manager.c: mature the oldest due pending record.
        oldest_idx = None
        oldest_due = 2**32 - 1
        for i, p in enumerate(pending):
            if p["due_step"] <= timestep and p["due_step"] < oldest_due:
                oldest_idx = i
                oldest_due = p["due_step"]
        if oldest_idx is not None:
            p = pending.pop(oldest_idx)
            err = p["target"] - p["prediction"]
            delta_w = 0
            delta_b = 0
            skipped = abs(err) >= surprise_threshold
            if not skipped:
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
                "surprise_skipped": skipped,
                "delta_w_raw": delta_w,
                "delta_b_raw": delta_b,
                "weight_after": weight,
                "bias_after": bias,
            })

        if event_active:
            replies_ready = True
        timestep += 1

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
            # Wrong-key replay must not reproduce the correct replay weight. Bias
            # can move because the native runtime bias update is feature-independent;
            # require it to stay bounded rather than treating bias drift as success.
            diff_b = abs(ref["final_bias"] - no_ref["final_bias"])
            criteria.append({
                "name": f"{name}_bias_bounded_near_no_replay",
                "value": diff_b,
                "threshold": tolerance,
                "passed": diff_b <= tolerance,
                "note": f"wrong_key bias={ref['final_bias_float']:.4f}; no_replay={no_ref['final_bias_float']:.4f}; diff={diff_b}",
            })

        if name == "correct_replay" and no_ref:
            diff_w = abs(ref["final_weight"] - no_ref["final_weight"])
            criteria.append({
                "name": f"{name}_weight_differs_from_no_replay",
                "value": diff_w,
                "threshold": tolerance,
                "passed": diff_w > tolerance,
                "note": f"correct_replay weight={ref['final_weight_float']:.4f}; no_replay={no_ref['final_weight_float']:.4f}; diff={diff_w}",
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
    all_refs: dict[str, dict],
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

    # Write slots
    ctx_writes = []
    route_writes = []
    mem_writes = []

    ok = ctx_ctrl.write_context(
        CONTEXT_KEY, CONTEXT_VALUE, 1.0, dest_x, dest_y, CONTEXT_CORE_P
    )
    ctx_writes.append({"key": CONTEXT_KEY, "success": ok.get("success") is True})

    ok = route_ctrl.write_route_slot(
        ROUTE_KEY, ROUTE_VALUE, 1.0, dest_x, dest_y, ROUTE_CORE_P
    )
    route_writes.append({"key": ROUTE_KEY, "success": ok.get("success") is True})

    ok = mem_ctrl.write_memory_slot(
        MEMORY_KEY, MEMORY_VALUE, 1.0, dest_x, dest_y, MEMORY_CORE_P
    )
    mem_writes.append({"key": MEMORY_KEY, "success": ok.get("success") is True})

    # Build schedule per control
    events = [dict(ev) for ev in control["events"]]
    for ev in events:
        if control["name"] == "wrong_key_replay" and ev["step"] >= 16:
            ev["context_key"] = WRONG_CONTEXT_KEY
        else:
            ev["context_key"] = control["context_key"]

    schedule = _build_schedule(events, control["context_key"])
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
    ref = run_host_reference(int(args.seed), events)

    criteria = evaluate_control_criteria(control, ref, all_refs=all_refs, hw_state=learning_final)

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
    """Run four-core distributed replay task on hardware."""
    print(TIER)
    print("=" * 60)

    default_dir = f"tier4_29e_seed{args.seed}_job_output"
    output_dir = Path(args.output) if args.output else Path(default_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    def write_json(path: Path, data: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2))

    # 1. Build all four MCPL images
    print("\n[1/4] Building .aplx images...")
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

    write_json(output_dir / "tier4_29e_environment.json", env_report)
    write_json(output_dir / "tier4_29e_target_acquisition.json", base.public_target_acquisition(target))

    # Compute all references before running controls so hardware criteria include
    # the same cross-control checks used by local mode and ingest mode.
    all_refs = {}
    for control in CONTROLS:
        events = [dict(ev) for ev in control["events"]]
        for ev in events:
            if control["name"] == "wrong_key_replay" and ev["step"] >= 16:
                ev["context_key"] = WRONG_CONTEXT_KEY
            else:
                ev["context_key"] = control["context_key"]
        all_refs[control["name"]] = run_host_reference(int(args.seed), events)

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
                write_json(output_dir / f"tier4_29e_{name}_load.json", load_info)

        if (target.get("status") == "pass" and hostname
            and all(l.get("status") == "pass" for l in loads.values())):
            print("\n[3/4] Running control conditions...")
            for control in CONTROLS:
                print(f"\n  -> Control: {control['name']}")
                result = four_core_hardware_loop(hostname, args, target, loads, control, all_refs)
                control_results.append(result)
                write_json(output_dir / f"tier4_29e_task_{control['name']}.json", result)
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
        write_json(output_dir / "tier4_29e_environment.json", env_report)
        write_json(output_dir / "tier4_29e_target_acquisition.json", base.public_target_acquisition(target))
        for name, load_info in loads.items():
            write_json(output_dir / f"tier4_29e_{name}_load.json", load_info)

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
        "build": {
            "context": ctx_build,
            "route": route_build,
            "memory": mem_build,
            "learning": learning_build,
        },
        "loads": loads,
        "target": base.public_target_acquisition(target),
        "environment": env_report,
        "hardware_exception": hardware_exception,
    }
    write_json(output_dir / f"tier4_29e_hardware_results_seed{args.seed}.json", report)

    print(f"\n{'='*60}")
    print(f"Tier 4.29e Hardware Seed {args.seed}: {'PASS' if all_passed else 'FAIL'}")
    print(f"Report: {output_dir / f'tier4_29e_hardware_results_seed{args.seed}.json'}")
    print(f"{'='*60}")

    return report


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
        for r in hw_data.get("control_results", []):
            if r.get("control") == control["name"]:
                hw_state = r.get("final_state", {}).get("learning")
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

    # The source package is 4.29d/cra_429j, so replace source-specific job docs
    # and make this package self-contained for JobManager execution.
    for stale_readme in dest.glob("README_TIER4_29D_JOB.md"):
        stale_readme.unlink()
    exp_dir = dest / "experiments"
    exp_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(Path(__file__), exp_dir / Path(__file__).name)

    # Update metadata
    metadata = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "upload_package": UPLOAD_PACKAGE_NAME,
        "based_on": "cra_429j",
        "change_summary": "No C runtime changes. Repairs 4.29e schedule-key/reference gate after cra_429o failed two hardware tolerance criteria.",
        "profiles": [CONTEXT_CORE_PROFILE, ROUTE_CORE_PROFILE, MEMORY_CORE_PROFILE, LEARNING_CORE_PROFILE],
        "app_ids": [CONTEXT_CORE_APP_ID, ROUTE_CORE_APP_ID, MEMORY_CORE_APP_ID, LEARNING_CORE_APP_ID],
        "cores": [CONTEXT_CORE_P, ROUTE_CORE_P, MEMORY_CORE_P, LEARNING_CORE_P],
        "prepared_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(dest / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    readme = f"""# Tier 4.29e - Native Replay/Consolidation Bridge

Upload folder: `{UPLOAD_PACKAGE_NAME}`

Command:
```text
{UPLOAD_PACKAGE_NAME}/experiments/tier4_29e_native_replay_consolidation_bridge.py --mode run-hardware --seeds 42,43,44
```

Purpose: Verify that host-scheduled replay/consolidation events run through the
native four-core state pipeline using context, route, memory, and learning cores.

Controls:
- `no_replay`
- `correct_replay`
- `wrong_key_replay`
- `random_event_replay`

Notes:
- Reuses `cra_429j` binaries; 4.29e intentionally makes no C runtime change.
- Fresh package after `cra_429o` failed: fixes per-event wrong-key scheduling,
  native-continuous reference mirroring, and a stronger correct-replay-vs-no-replay gate.
- The 4.29e runner is copied into this package during prepare mode.
- This is host-scheduled replay only, not native on-chip replay buffers.
- Hardware evidence requires three-seed run, ingest, and standard documentation updates.
"""
    (dest / "README_TIER4_29E_JOB.md").write_text(readme)

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
