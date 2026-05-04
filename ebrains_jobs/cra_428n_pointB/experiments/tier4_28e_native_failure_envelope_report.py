#!/usr/bin/env python3
"""
Tier 4.28e — Native Failure-Envelope Report.

Systematically stress the four-core MCPL runtime to find where it breaks.
Local sweep predicts breakpoints; hardware probes validate them.

Modes:
  local        — parameter sweep, predict breakpoints, run host reference
  prepare      — create EBRAINS bundles for selected hardware probe points
  run-hardware — load and run one probe-point configuration
  ingest       — compare hardware results with reference

Claim boundary:
  Local modes predict envelope; hardware validates selected points.
  Does not claim full envelope coverage; samples near predicted breakpoints.
  Single-chip only; not multi-chip, not speedup, not v2.1 mechanism transfer.
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

# Hard limits from config.h
MAX_SCHEDULE_ENTRIES = 64
MAX_CONTEXT_SLOTS = 128
MAX_PENDING_HORIZONS = 128
SURPRISE_THRESHOLD = 2.0

TIER = "Tier 4.28e — Native Failure-Envelope Report"
RUNNER_REVISION = "tier4_28e_native_failure_envelope_20260503_0001"
UPLOAD_PACKAGE_NAME = "cra_428n"
STABLE_EBRAINS_UPLOAD = ROOT / "ebrains_jobs" / UPLOAD_PACKAGE_NAME

# Core role map (same as 4.27a/4.28d)
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

    base_aplx = RUNTIME / "build" / "coral_reef.aplx"
    if base_aplx.exists():
        base_aplx.unlink()

    build = run_cmd(["make", "-C", str(RUNTIME), "clean", "all"], cwd=ROOT, env=env)
    (output_dir / f"tier4_28e_build_{profile}_stdout.txt").write_text(build["stdout"])
    (output_dir / f"tier4_28e_build_{profile}_stderr.txt").write_text(build["stderr"])

    aplx = RUNTIME / "build" / "coral_reef.aplx"
    profile_aplx = RUNTIME / "build" / f"coral_reef_{profile}.aplx"
    if aplx.exists() and not profile_aplx.exists():
        shutil.copy2(aplx, profile_aplx)

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


def generate_hard_noisy_switching_sequence(
    *,
    steps: int = 96,
    seed: int = 42,
    amplitude: float = 1.0,
    hard_period: int = 2,
    min_delay: int = 3,
    max_delay: int = 5,
    noise_prob: float = 0.20,
    sensory_noise_fraction: float = 0.25,
    min_switch_interval: int = 32,
    max_switch_interval: int = 48,
) -> list[dict[str, Any]]:
    """Generate hard_noisy_switching schedule with oracle regime context."""
    import random
    rng = random.Random(seed + 41)
    switch_steps = [0]
    cursor = 0
    while cursor < steps:
        cursor += rng.randint(min_switch_interval, max_switch_interval)
        if cursor < steps:
            switch_steps.append(cursor)
    initial_rule = 1.0 if rng.random() < 0.5 else -1.0

    def rule_at(step: int) -> float:
        idx = max(0, len([s for s in switch_steps if s <= step]) - 1)
        return initial_rule * (1.0 if idx % 2 == 0 else -1.0)

    sequence: list[dict[str, Any]] = []
    for start in range(0, steps - max_delay, hard_period):
        cue_sign = 1.0 if rng.random() < 0.5 else -1.0
        delay = rng.randint(min_delay, max_delay)
        regime = rule_at(start)
        label = regime * cue_sign
        is_noisy = rng.random() < noise_prob
        if is_noisy:
            label *= -1.0
        sensory = amplitude * cue_sign + rng.gauss(0.0, sensory_noise_fraction * amplitude)
        target = amplitude * label
        ctx_key_id = 1000 + len(sequence)
        sequence.append({
            "step": len(sequence) + 1,
            "feature": sensory,
            "target": target,
            "purpose": f"hard_noisy_switching_regime{regime:+.0f}_noise{is_noisy}",
            "bridge_context_key": f"ctx_regime_{len(sequence)}",
            "bridge_context_key_id": ctx_key_id,
            "bridge_route_key": "route_A",
            "bridge_route_key_id": ROUTE_KEY_IDS["route_A"],
            "bridge_memory_key": "mem_A",
            "bridge_memory_key_id": MEMORY_KEY_IDS["mem_A"],
            "bridge_visible_cue": int(cue_sign),
            "regime_sign": int(regime),
            "is_noisy": is_noisy,
            "delay": delay,
        })
    return sequence


def simulate_runtime_pressure(sequence: list[dict[str, Any]]) -> dict[str, Any]:
    """Simulate runtime pressure: concurrent pending, schedule fit, slot usage."""
    event_count = len(sequence)
    context_slots_used = len({e["bridge_context_key_id"] for e in sequence})

    # Simulate pending queue to find max concurrent pending
    pending_queue: list[dict[str, Any]] = []
    max_concurrent_pending = 0
    for idx, event in enumerate(sequence):
        due_step = idx + 1 + int(event.get("delay", 2))
        pending_queue.append({"due_step": due_step})
        # Mature any pending whose due step has arrived
        pending_queue = [p for p in pending_queue if p["due_step"] > idx + 1]
        max_concurrent_pending = max(max_concurrent_pending, len(pending_queue))

    # Predicted outcome based on hard limits
    predicted = "pass"
    limit_reason = ""
    if event_count > MAX_SCHEDULE_ENTRIES:
        predicted = "fail"
        limit_reason = f"schedule_overflow ({event_count} > {MAX_SCHEDULE_ENTRIES})"
    elif context_slots_used > MAX_CONTEXT_SLOTS:
        predicted = "fail"
        limit_reason = f"slot_exhaustion ({context_slots_used} > {MAX_CONTEXT_SLOTS})"
    elif max_concurrent_pending > MAX_PENDING_HORIZONS:
        predicted = "fail"
        limit_reason = f"pending_overflow ({max_concurrent_pending} > {MAX_PENDING_HORIZONS})"

    return {
        "event_count": event_count,
        "context_slots_used": context_slots_used,
        "max_concurrent_pending": max_concurrent_pending,
        "predicted": predicted,
        "limit_reason": limit_reason,
    }


def run_host_reference(sequence: list[dict[str, Any]], learning_rate: float = 0.25) -> dict[str, Any]:
    """Fixed-point host simulation with surprise gating.
    Models learning-core profile timing: one-tick MCPL lookup latency means
    pending matures AFTER prediction in the same tick, creating a one-event lag.
    """
    weight = 0
    bias = 0
    lr_raw = int(learning_rate * FP_ONE)
    surprise_raw = int(SURPRISE_THRESHOLD * FP_ONE)
    pending_queue: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    for idx, event in enumerate(sequence):
        cue_sign = float(event.get("bridge_visible_cue", 0))
        regime_sign = float(event.get("regime_sign", 1.0))
        effective_feature = regime_sign * cue_sign
        feature_raw = int(effective_feature * FP_ONE)
        target_raw = int(float(event["target"]) * FP_ONE)
        delay_steps = int(event.get("delay", 2))

        # Phase C: mature ONE oldest pending BEFORE making prediction
        # (pending from event idx-1 matures at timestep idx+1, before event idx's prediction at idx+2)
        matured_idx = -1
        oldest_due = float("inf")
        for i, p in enumerate(pending_queue):
            if p["due_step"] <= idx + 1 and p["due_step"] < oldest_due:
                oldest_due = p["due_step"]
                matured_idx = i
        if matured_idx >= 0:
            p = pending_queue.pop(matured_idx)
            error_raw = p["target_raw"] - p["prediction_raw"]
            if abs(error_raw) >= surprise_raw:
                rows.append({"sign_correct": False, "gated": True})
            else:
                delta_w = (lr_raw * ((error_raw * p["feature_raw"]) >> FP_SHIFT)) >> FP_SHIFT
                delta_b = (lr_raw * error_raw) >> FP_SHIFT
                weight += delta_w
                bias += delta_b
                pred_sign = 1 if p["prediction_raw"] >= 0 else -1
                target_sign = 1 if p["target_raw"] >= 0 else -1
                rows.append({"sign_correct": pred_sign == target_sign, "gated": False})

        # Phase B: make prediction for event idx
        pred_raw = ((weight * feature_raw) >> FP_SHIFT) + bias

        # Schedule pending with due = timestep + delay (timestep = idx+1 for event idx)
        pending_queue.append({
            "feature_raw": feature_raw,
            "target_raw": target_raw,
            "due_step": idx + 1 + delay_steps,
            "prediction_raw": pred_raw,
        })

    # Mature remaining pending
    while pending_queue:
        oldest_idx = -1
        oldest_due = float("inf")
        for i, p in enumerate(pending_queue):
            if p["due_step"] < oldest_due:
                oldest_due = p["due_step"]
                oldest_idx = i
        if oldest_idx >= 0:
            p = pending_queue.pop(oldest_idx)
            error_raw = p["target_raw"] - p["prediction_raw"]
            if abs(error_raw) >= surprise_raw:
                rows.append({"sign_correct": False, "gated": True})
            else:
                delta_w = (lr_raw * ((error_raw * p["feature_raw"]) >> FP_SHIFT)) >> FP_SHIFT
                delta_b = (lr_raw * error_raw) >> FP_SHIFT
                weight += delta_w
                bias += delta_b
                pred_sign = 1 if p["prediction_raw"] >= 0 else -1
                target_sign = 1 if p["target_raw"] >= 0 else -1
                rows.append({"sign_correct": pred_sign == target_sign, "gated": False})

    tail = rows[-TASK_TAIL_WINDOW:] if len(rows) >= TASK_TAIL_WINDOW else rows
    nongated_tail = [r for r in tail if not r.get("gated", False)]
    tail_accuracy = sum(1 for r in nongated_tail if r["sign_correct"]) / len(nongated_tail) if nongated_tail else 0.0
    return {
        "weight_raw": weight,
        "weight": weight / FP_ONE,
        "bias_raw": bias,
        "bias": bias / FP_ONE,
        "tail_accuracy": tail_accuracy,
        "n_events": len(sequence),
        "n_gated": sum(1 for r in rows if r.get("gated", False)),
    }


def _sweep_dimension(name: str, default_params: dict[str, Any], variations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Run sweep over one dimension, keeping others at default."""
    results = []
    for var in variations:
        params = dict(default_params)
        params.update(var)
        seq = generate_hard_noisy_switching_sequence(**params)
        pressure = simulate_runtime_pressure(seq)
        ref = run_host_reference(seq)
        results.append({
            "dimension": name,
            "params": params,
            "pressure": pressure,
            "reference": ref,
        })
    return results


def run_local_sweep(seed: int = 42) -> dict[str, Any]:
    """Run full local parameter sweep."""
    default = {
        "steps": 96,
        "seed": seed,
        "amplitude": 1.0,
        "hard_period": 2,
        "min_delay": 3,
        "max_delay": 5,
        "noise_prob": 0.20,
        "sensory_noise_fraction": 0.25,
        "min_switch_interval": 32,
        "max_switch_interval": 48,
    }

    sweep_results: list[dict[str, Any]] = []

    # 1. Schedule length sweep
    sweep_results.extend(_sweep_dimension("schedule_length", default, [
        {"steps": 32},
        {"steps": 48},
        {"steps": 64},
        {"steps": 80},
        {"steps": 96},
        {"steps": 128},
        {"steps": 160},
        {"steps": 192},
    ]))

    # 2. Delay pressure sweep
    sweep_results.extend(_sweep_dimension("delay_pressure", default, [
        {"min_delay": 1, "max_delay": 1},
        {"min_delay": 1, "max_delay": 2},
        {"min_delay": 2, "max_delay": 3},
        {"min_delay": 3, "max_delay": 5},
        {"min_delay": 5, "max_delay": 7},
        {"min_delay": 7, "max_delay": 10},
    ]))

    # 3. Noise level sweep
    sweep_results.extend(_sweep_dimension("noise_level", default, [
        {"noise_prob": 0.0},
        {"noise_prob": 0.2},
        {"noise_prob": 0.4},
        {"noise_prob": 0.6},
        {"noise_prob": 0.8},
    ]))

    # 4. Switch frequency sweep
    sweep_results.extend(_sweep_dimension("switch_frequency", default, [
        {"min_switch_interval": 8, "max_switch_interval": 12},
        {"min_switch_interval": 16, "max_switch_interval": 24},
        {"min_switch_interval": 32, "max_switch_interval": 48},
        {"min_switch_interval": 48, "max_switch_interval": 64},
        {"min_switch_interval": 64, "max_switch_interval": 80},
    ]))

    # 5. Mixed-stress points
    sweep_results.extend(_sweep_dimension("mixed_stress", default, [
        {"steps": 64, "min_delay": 1, "max_delay": 2, "noise_prob": 0.4},
        {"steps": 96, "min_delay": 1, "max_delay": 2, "noise_prob": 0.4},
        {"steps": 128, "min_delay": 1, "max_delay": 2, "noise_prob": 0.4},
        {"steps": 64, "min_delay": 1, "max_delay": 1, "noise_prob": 0.6},
        {"steps": 96, "min_delay": 1, "max_delay": 1, "noise_prob": 0.6},
        {"steps": 128, "min_delay": 1, "max_delay": 1, "noise_prob": 0.6},
    ]))

    return {
        "default_params": default,
        "sweep_results": sweep_results,
    }


def select_hardware_probe_points(sweep_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Select the most informative hardware probe points from sweep."""
    passing = [r for r in sweep_results if r["pressure"]["predicted"] == "pass"]
    failing = [r for r in sweep_results if r["pressure"]["predicted"] == "fail"]

    # Sort by event count descending among passing
    passing.sort(key=lambda r: r["pressure"]["event_count"], reverse=True)
    # Sort by event count ascending among failing
    failing.sort(key=lambda r: r["pressure"]["event_count"])

    points: list[dict[str, Any]] = []

    # Point A: highest-pressure passing config
    if passing:
        points.append({"label": "A", "description": "highest_pressure_passing", **passing[0]})

    # Point B: first predicted failure
    if failing:
        points.append({"label": "B", "description": "first_predicted_failure", **failing[0]})

    # Point C: a high-event-count, short-delay passing config
    high_event_short_delay = [
        r for r in passing
        if r["pressure"]["event_count"] >= 48
        and r["params"].get("max_delay", 5) <= 3
    ]
    if high_event_short_delay:
        high_event_short_delay.sort(key=lambda r: r["pressure"]["event_count"], reverse=True)
        points.append({"label": "C", "description": "high_event_short_delay", **high_event_short_delay[0]})

    # Point C: high pending pressure (long delays, near schedule limit)
    high_pending = [
        r for r in passing
        if r["pressure"]["event_count"] >= 40
        and r["pressure"]["max_concurrent_pending"] >= 7
    ]
    if high_pending:
        high_pending.sort(key=lambda r: r["pressure"]["max_concurrent_pending"], reverse=True)
        points.append({"label": "C", "description": "high_pending_pressure", **high_pending[0]})

    # Point D: mixed stress with moderate events + noise
    mixed = [r for r in passing if r["dimension"] == "mixed_stress" and r["pressure"]["event_count"] >= 48]
    if mixed:
        mixed.sort(key=lambda r: r["params"].get("noise_prob", 0), reverse=True)
        points.append({"label": "D", "description": "mixed_stress", **mixed[0]})

    # Deduplicate by params tuple
    seen: set[str] = set()
    unique_points = []
    for p in points:
        key = json.dumps(p["params"], sort_keys=True)
        if key not in seen:
            seen.add(key)
            unique_points.append(p)

    return unique_points


# ---------------------------------------------------------------------------
# Modes
# ---------------------------------------------------------------------------

def mode_local(args: argparse.Namespace) -> dict[str, Any]:
    print(TIER)
    print("=" * 60)

    output_dir = Path(args.output) if args.output else Path("tier4_28e_local_output")
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Build all four MCPL images
    print("\n[1/3] Building four MCPL runtime profile images...")
    ctx_build = build_aplx_for_profile(CONTEXT_CORE_PROFILE, output_dir)
    route_build = build_aplx_for_profile(ROUTE_CORE_PROFILE, output_dir)
    mem_build = build_aplx_for_profile(MEMORY_CORE_PROFILE, output_dir)
    learning_build = build_aplx_for_profile(LEARNING_CORE_PROFILE, output_dir)

    build_criteria = [
        {"name": f"{p}_aplx_built", "passed": b["aplx_exists"]}
        for p, b in [("context", ctx_build), ("route", route_build), ("memory", mem_build), ("learning", learning_build)]
    ]
    all_build_pass = all(c["passed"] for c in build_criteria)

    # 2. Run host tests
    print("\n[2/3] Running host tests...")
    host_tests = base.run_host_tests(output_dir)

    # 3. Run local sweep
    print("\n[3/3] Running local parameter sweep...")
    sweep = run_local_sweep(seed=args.seed)
    sweep_results = sweep["sweep_results"]

    # Predicted breakpoints
    predicted_failures = [r for r in sweep_results if r["pressure"]["predicted"] == "fail"]
    predicted_passes = [r for r in sweep_results if r["pressure"]["predicted"] == "pass"]

    # Select hardware probe points
    probe_points = select_hardware_probe_points(sweep_results)

    # Summary table
    print(f"\n{'=' * 60}")
    print("SWEEP SUMMARY")
    print(f"{'=' * 60}")
    print(f"Total configs swept: {len(sweep_results)}")
    print(f"Predicted passes: {len(predicted_passes)}")
    print(f"Predicted failures: {len(predicted_failures)}")
    if predicted_failures:
        print("\nPredicted failure reasons:")
        for r in predicted_failures:
            p = r["pressure"]
            print(f"  {r['dimension']}: {p['limit_reason']} (events={p['event_count']}, pending={p['max_concurrent_pending']}, slots={p['context_slots_used']})")
    print(f"\nSelected hardware probe points: {len(probe_points)}")
    for pp in probe_points:
        p = pp["pressure"]
        print(f"  Point {pp['label']} ({pp['description']}): steps={pp['params']['steps']}, delay=({pp['params']['min_delay']},{pp['params']['max_delay']}), noise={pp['params']['noise_prob']}, events={p['event_count']}, pending={p['max_concurrent_pending']}, predicted={p['predicted']}")

    # Write sweep artifact
    sweep_artifact = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "mode": "local",
        "status": "pass" if all_build_pass and host_tests.get("status") == "pass" else "fail",
        "build_criteria": build_criteria,
        "host_tests": host_tests,
        "sweep": sweep,
        "predicted_failures": predicted_failures,
        "predicted_passes": predicted_passes,
        "probe_points": probe_points,
    }
    sweep_path = output_dir / "tier4_28e_local_sweep.json"
    sweep_path.write_text(json.dumps(sweep_artifact, indent=2, default=str))
    print(f"\nSweep artifact: {sweep_path}")

    # Criteria
    criteria = [
        {"name": "all_aplx_built", "passed": all_build_pass},
        {"name": "host_tests_pass", "passed": host_tests.get("status") == "pass"},
        {"name": "sweep_completed", "passed": len(sweep_results) > 0},
        {"name": "at_least_one_predicted_failure", "passed": len(predicted_failures) > 0},
        {"name": "at_least_one_probe_point_selected", "passed": len(probe_points) > 0},
    ]
    status = "pass" if all(c["passed"] for c in criteria) else "fail"

    result = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "mode": "local",
        "status": status,
        "output_dir": str(output_dir),
        "criteria": criteria,
        "sweep_path": str(sweep_path),
    }
    result_path = output_dir / "tier4_28e_local_results.json"
    result_path.write_text(json.dumps(result, indent=2))
    print(f"\n{'=' * 60}")
    print(f"OVERALL: {status.upper()}")
    for c in criteria:
        mark = "PASS" if c["passed"] else "FAIL"
        print(f"  [{mark}] {c['name']}")
    return result


def mode_prepare(args: argparse.Namespace) -> dict[str, Any]:
    print(TIER)
    print("=" * 60)

    output_dir = Path(args.output) if args.output else Path("tier4_28e_prepare_output")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Must run local sweep first to get probe points
    sweep = run_local_sweep(seed=args.seed)
    probe_points = select_hardware_probe_points(sweep["sweep_results"])

    if not probe_points:
        print("ERROR: No probe points selected. Run local sweep first.")
        return {"status": "blocked", "reason": "no_probe_points"}

    # Build all four images
    print("\n[1/2] Building four MCPL images...")
    ctx_build = build_aplx_for_profile(CONTEXT_CORE_PROFILE, output_dir)
    route_build = build_aplx_for_profile(ROUTE_CORE_PROFILE, output_dir)
    mem_build = build_aplx_for_profile(MEMORY_CORE_PROFILE, output_dir)
    learning_build = build_aplx_for_profile(LEARNING_CORE_PROFILE, output_dir)

    # Create bundle per probe point
    print("\n[2/2] Creating EBRAINS bundles...")
    bundles: list[dict[str, Any]] = []
    for pp in probe_points:
        label = pp["label"]
        params = pp["params"]
        bundle_name = f"{UPLOAD_PACKAGE_NAME}_point{label}"
        bundle = output_dir / bundle_name
        if bundle.exists():
            shutil.rmtree(bundle)
        bundle.mkdir(parents=True)

        # Copy .aplx files
        for build_info in [ctx_build, route_build, mem_build, learning_build]:
            src = Path(build_info["aplx_path"])
            if src.exists():
                shutil.copy2(src, bundle / src.name)

        # Copy experiments package with all dependencies
        (bundle / "experiments").mkdir(exist_ok=True)
        (bundle / "experiments" / "__init__.py").write_text("# experiments package\n", encoding="utf-8")
        scripts = [
            Path(__file__).name,
            "tier4_22i_custom_runtime_roundtrip.py",
            "tier4_22x_compact_v2_bridge_decoupled_smoke.py",
            "tier4_27a_four_core_distributed_smoke.py",
            "tier4_23a_continuous_local_reference.py",
            "tier4_22j_minimal_custom_runtime_learning.py",
            "tier4_22l_custom_runtime_learning_parity.py",
        ]
        for script in scripts:
            src = ROOT / "experiments" / script
            if src.exists():
                shutil.copy2(src, bundle / "experiments" / script)
                os.chmod(bundle / "experiments" / script, 0o755)

        # Copy coral_reef_spinnaker package structure
        (bundle / "coral_reef_spinnaker").mkdir(exist_ok=True)
        (bundle / "coral_reef_spinnaker" / "__init__.py").write_text("", encoding="utf-8")
        (bundle / "coral_reef_spinnaker" / "python_host").mkdir(parents=True, exist_ok=True)
        shutil.copy2(
            ROOT / "coral_reef_spinnaker" / "python_host" / "colony_controller.py",
            bundle / "coral_reef_spinnaker" / "python_host" / "colony_controller.py",
        )
        base.copy_tree_clean(RUNTIME, bundle / "coral_reef_spinnaker" / "spinnaker_runtime")

        # Write params JSON
        params_path = bundle / f"point{label}_params.json"
        params_path.write_text(json.dumps(params, indent=2))

        # Write README
        runner_name = Path(__file__).name
        command = (
            f"{bundle_name}/experiments/{runner_name} "
            f"--mode run-hardware --seed {args.seed} "
            f"--steps {params['steps']} --min-delay {params['min_delay']} --max-delay {params['max_delay']} "
            f"--noise-prob {params['noise_prob']} --min-switch {params['min_switch_interval']} --max-switch {params['max_switch_interval']} "
            f"--output tier4_28e_point{label}_job_output"
        )
        readme_text = f"""# {TIER} — Probe Point {label} Bundle

Parameters:
```json
{json.dumps(params, indent=2)}
```

Predicted: {pp['pressure']['predicted']}
Reason: {pp['pressure']['limit_reason'] or 'N/A'}
Events: {pp['pressure']['event_count']}
Max concurrent pending: {pp['pressure']['max_concurrent_pending']}
Context slots: {pp['pressure']['context_slots_used']}

JobManager command:
```text
{command}
```

Claim boundary: Local package preparation only. NOT hardware evidence.
"""
        (bundle / f"README_TIER4_28E_POINT{label}.md").write_text(readme_text)

        # Stable upload folder
        stable = ROOT / "ebrains_jobs" / bundle_name
        stable.parent.mkdir(parents=True, exist_ok=True)
        if stable.exists():
            shutil.rmtree(stable)
        shutil.copytree(bundle, stable)

        bundles.append({
            "label": label,
            "bundle": str(bundle),
            "stable_upload": str(stable),
            "command": command,
            "params": params,
            "predicted": pp["pressure"]["predicted"],
        })

    # Summary
    all_built = all(b["aplx_exists"] for b in [ctx_build, route_build, mem_build, learning_build])
    criteria = [
        {"name": "all_aplx_built", "passed": all_built},
        {"name": "at_least_one_bundle_created", "passed": len(bundles) > 0},
    ]
    status = "prepared" if all(c["passed"] for c in criteria) else "blocked"

    result = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "mode": "prepare",
        "status": status,
        "output_dir": str(output_dir),
        "bundles": bundles,
        "criteria": criteria,
    }
    result_path = output_dir / "tier4_28e_prepare_results.json"
    result_path.write_text(json.dumps(result, indent=2))
    print(f"\n{'=' * 60}")
    print(f"OVERALL: {status.upper()}")
    for c in criteria:
        mark = "PASS" if c["passed"] else "FAIL"
        print(f"  [{mark}] {c['name']}")
    for b in bundles:
        print(f"\n  Point {b['label']}: {b['stable_upload']}")
        print(f"    Command: {b['command']}")
    return result


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
            "delay": int(event.get("delay", delay_steps)),
        })
    return schedule


def four_core_hardware_loop(
    hostname: str,
    args: argparse.Namespace,
    target: dict[str, Any],
    loads: dict[str, dict[str, Any]],
    sequence: list[dict[str, Any]],
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
        for event in sequence:
            ctx_id = int(event["bridge_context_key_id"])
            val = float(event["regime_sign"])
            ok = ctx_ctrl.write_context(ctx_id, val, 1.0, dest_x, dest_y, CONTEXT_CORE_P)
            ctx_writes.append({"key": event["bridge_context_key"], "success": ok.get("success") is True})

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
        schedule = _build_schedule(sequence)
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

        # Wait for completion
        max_wait = 10.0
        poll_interval = 0.2
        elapsed = 0.0
        learning_final = {}
        while elapsed < max_wait:
            time.sleep(poll_interval)
            elapsed += poll_interval
            learning_final = learning_ctrl.read_state(dest_x, dest_y, LEARNING_CORE_P)
            if learning_final.get("state") == 3:
                break

        # Read all four cores
        ctx_final = ctx_ctrl.read_state(dest_x, dest_y, CONTEXT_CORE_P)
        route_final = route_ctrl.read_state(dest_x, dest_y, ROUTE_CORE_P)
        mem_final = mem_ctrl.read_state(dest_x, dest_y, MEMORY_CORE_P)
        learning_final = learning_ctrl.read_state(dest_x, dest_y, LEARNING_CORE_P)

        return {
            "status": "success",
            "elapsed_wait": elapsed,
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
            "final_state": {
                "context": ctx_final,
                "route": route_final,
                "memory": mem_final,
                "learning": learning_final,
            },
        }
    except Exception as exc:
        return {
            "status": "fail",
            "reason": str(exc),
            "traceback": traceback.format_exc(),
        }


def mode_run_hardware(args: argparse.Namespace) -> dict[str, Any]:
    print(TIER)
    print("=" * 60)

    # Generate sequence from CLI params
    sequence = generate_hard_noisy_switching_sequence(
        steps=args.steps,
        seed=args.seed,
        min_delay=args.min_delay,
        max_delay=args.max_delay,
        noise_prob=args.noise_prob,
        min_switch_interval=args.min_switch,
        max_switch_interval=args.max_switch,
    )
    pressure = simulate_runtime_pressure(sequence)
    ref = run_host_reference(sequence)

    print(f"\nConfiguration: steps={args.steps}, delay=({args.min_delay},{args.max_delay}), noise={args.noise_prob}")
    print(f"Events: {pressure['event_count']}, slots: {pressure['context_slots_used']}, max_pending: {pressure['max_concurrent_pending']}")
    print(f"Predicted: {pressure['predicted']} ({pressure['limit_reason'] or 'within limits'})")
    print(f"Reference: weight={ref['weight_raw']}, bias={ref['bias_raw']}, tail_acc={ref['tail_accuracy']:.2f}")

    default_dir = f"tier4_28e_seed{args.seed}_s{args.steps}_d{args.min_delay}-{args.max_delay}_job_output"
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

    write_json(output_dir / "tier4_28e_environment.json", env_report)
    write_json(output_dir / "tier4_28e_target_acquisition.json", base.public_target_acquisition(target))

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
                write_json(output_dir / f"tier4_28e_{name}_load.json", load_info)

        if (target.get("status") == "pass" and hostname
            and all(l.get("status") == "pass" for l in loads.values())):
            print("\n[4/4] Running four-core hardware loop...")
            task_result = four_core_hardware_loop(hostname, args, target, loads, sequence)
            write_json(output_dir / "tier4_28e_task.json", task_result)
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
        write_json(output_dir / "tier4_28e_environment.json", env_report)
        write_json(output_dir / "tier4_28e_target_acquisition.json", base.public_target_acquisition(target))
        for name, load_info in loads.items():
            write_json(output_dir / f"tier4_28e_{name}_load.json", load_info)
        write_json(output_dir / "tier4_28e_task.json", task_result)

    # Criteria
    ref_weight = ref["weight_raw"]
    ref_bias = ref["bias_raw"]
    ref_events = len(sequence)

    final_states = task_result.get("final_state", {}) if isinstance(task_result, dict) else {}
    learning_final = final_states.get("learning", {}) if isinstance(final_states, dict) else {}
    ctx_final = final_states.get("context", {}) if isinstance(final_states, dict) else {}
    route_final = final_states.get("route", {}) if isinstance(final_states, dict) else {}
    mem_final = final_states.get("memory", {}) if isinstance(final_states, dict) else {}

    def criterion(name: str, value: Any, rule: str, passed: bool, note: str = "") -> dict[str, Any]:
        return {"name": name, "value": value, "rule": rule, "passed": passed, "note": note}

    # Tolerance: ±50% of reference weight/bias to account for MCPL timing jitter
    weight_tol = max(abs(ref_weight) // 2, 8192)
    bias_tol = max(abs(ref_bias) // 2, 8192)

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
        criterion("all context writes succeeded", task_result.get("state_writes", {}).get("context", []), "all success", len(task_result.get("state_writes", {}).get("context", [])) > 0 and all(w.get("success") for w in task_result.get("state_writes", {}).get("context", []))),
        criterion("all route writes succeeded", task_result.get("state_writes", {}).get("route", []), "all success", len(task_result.get("state_writes", {}).get("route", [])) > 0 and all(w.get("success") for w in task_result.get("state_writes", {}).get("route", []))),
        criterion("all memory writes succeeded", task_result.get("state_writes", {}).get("memory", []), "all success", len(task_result.get("state_writes", {}).get("memory", [])) > 0 and all(w.get("success") for w in task_result.get("state_writes", {}).get("memory", []))),
        criterion("all schedule uploads succeeded", task_result.get("schedule_uploads", []), "all success", len(task_result.get("schedule_uploads", [])) > 0 and all(u.get("success") for u in task_result.get("schedule_uploads", []))),
        criterion("context_core run_continuous succeeded", task_result.get("run_continuous", {}).get("context", {}).get("success"), "== True", task_result.get("run_continuous", {}).get("context", {}).get("success") is True),
        criterion("route_core run_continuous succeeded", task_result.get("run_continuous", {}).get("route", {}).get("success"), "== True", task_result.get("run_continuous", {}).get("route", {}).get("success") is True),
        criterion("memory_core run_continuous succeeded", task_result.get("run_continuous", {}).get("memory", {}).get("success"), "== True", task_result.get("run_continuous", {}).get("memory", {}).get("success") is True),
        criterion("learning_core run_continuous succeeded", task_result.get("run_continuous", {}).get("learning", {}).get("success"), "== True", task_result.get("run_continuous", {}).get("learning", {}).get("success") is True),
        criterion("context_core final read succeeded", ctx_final.get("success"), "== True", ctx_final.get("success") is True),
        criterion("route_core final read succeeded", route_final.get("success"), "== True", route_final.get("success") is True),
        criterion("memory_core final read succeeded", mem_final.get("success"), "== True", mem_final.get("success") is True),
        criterion("learning_core final read succeeded", learning_final.get("success"), "== True", learning_final.get("success") is True),
        criterion("learning_core weight near reference", learning_final.get("readout_weight_raw"), f"within +/- {weight_tol} of {ref_weight}", abs(int(learning_final.get("readout_weight_raw") or 0) - ref_weight) <= weight_tol),
        criterion("learning_core bias near reference", learning_final.get("readout_bias_raw"), f"within +/- {bias_tol} of {ref_bias}", abs(int(learning_final.get("readout_bias_raw") or 0) - ref_bias) <= bias_tol),
        criterion("learning_core pending_created matches reference", learning_final.get("pending_created"), f"== {ref_events}", learning_final.get("pending_created") == ref_events),
        criterion("learning_core pending_matured matches reference", learning_final.get("pending_matured"), f"== {ref_events}", learning_final.get("pending_matured") == ref_events),
        criterion("learning_core active_pending cleared", learning_final.get("active_pending"), "== 0", learning_final.get("active_pending") == 0),
        criterion("no unhandled hardware exception", hardware_exception is None, "== True", hardware_exception is None),
        criterion("learning_core schema_version v2", learning_final.get("schema_version"), "== 2", learning_final.get("schema_version") == 2),
        criterion(f"learning_core lookup_requests == {ref_events*3}", learning_final.get("lookup_requests"), f"== {ref_events*3}", learning_final.get("lookup_requests") == ref_events * 3),
        criterion(f"learning_core lookup_replies == {ref_events*3}", learning_final.get("lookup_replies"), f"== {ref_events*3}", learning_final.get("lookup_replies") == ref_events * 3),
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
        "params": {
            "steps": args.steps,
            "seed": args.seed,
            "min_delay": args.min_delay,
            "max_delay": args.max_delay,
            "noise_prob": args.noise_prob,
            "min_switch": args.min_switch,
            "max_switch": args.max_switch,
        },
        "pressure": pressure,
        "reference": ref,
        "criteria": criteria,
        "loads": loads,
        "task": task_result,
        "hardware_exception": hardware_exception,
    }
    write_json(output_dir / "tier4_28e_hardware_results.json", result)

    print(f"\n{'=' * 60}")
    print(f"OVERALL: {status.upper()}")
    for c in criteria:
        mark = "PASS" if c["passed"] else "FAIL"
        print(f"  [{mark}] {c['name']}: {c['value']}")
    print(f"\nArtifacts exported to: {output_dir}")
    return result


def mode_ingest(args: argparse.Namespace) -> dict[str, Any]:
    print("Tier 4.28e — Ingest hardware results")
    print("=" * 60)

    output_dir = Path(args.output) if args.output else Path("tier4_28e_ingest_output")
    output_dir.mkdir(parents=True, exist_ok=True)

    hw_dir = Path(args.hardware_output_dir) if args.hardware_output_dir else output_dir
    hw_results_path = hw_dir / "tier4_28e_hardware_results.json"

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
    output_path = output_dir / "tier4_28e_ingest_results.json"
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

    (output_dir / "tier4_28e_ingest_report.md").write_text(report)

    print(f"OVERALL: {status.upper()}")
    print(f"Passed: {passed}/{total}")
    print(f"Ingest report: {output_dir / 'tier4_28e_ingest_report.md'}")
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

    # Sweep / hardware config params
    parser.add_argument("--steps", type=int, default=96, help="Total steps for task generation")
    parser.add_argument("--min-delay", type=int, default=3, help="Minimum delay steps")
    parser.add_argument("--max-delay", type=int, default=5, help="Maximum delay steps")
    parser.add_argument("--noise-prob", type=float, default=0.20, help="Probability of noisy trial")
    parser.add_argument("--min-switch", type=int, default=32, help="Minimum regime switch interval")
    parser.add_argument("--max-switch", type=int, default=48, help="Maximum regime switch interval")

    # Hardware target params
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
        crash_path = Path(f"tier4_28e_seed{args.seed}_job_output") / "tier4_28e_crash_report.json"
        crash_path.parent.mkdir(parents=True, exist_ok=True)
        crash_path.write_text(json.dumps(crash, indent=2))
        print(f"\n[FATAL CRASH] {type(exc).__name__}: {exc}")
        print(f"Crash report written to: {crash_path}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
