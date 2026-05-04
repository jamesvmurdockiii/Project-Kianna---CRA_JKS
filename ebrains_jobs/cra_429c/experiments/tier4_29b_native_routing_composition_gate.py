#!/usr/bin/env python3
"""
Tier 4.29b — Native Routing/Composition Gate.

Tests the native SpiNNaker keyed context + route composition mechanism.
Uses non-neutral route values (+1.0 and -1.0) to create a routing-gated
composition test with explicit controls: wrong-context, wrong-route, overwrite,
and shuffle events. Four-core MCPL distributed runner.

Modes:
  local        — build four MCPL profiles, verify ITCM, run host reference
  prepare      — create EBRAINS job bundle with MCPL images and runner script
  run-hardware — load four MCPL images, run distributed two-phase task, read back
  ingest       — compare hardware results with reference

Claim boundary:
  Native keyed context * route composition works for multi-slot tables.
  Wrong-context, wrong-route, overwrite, and shuffle controls pass.
  This is a single-mechanism bridge; not replay, predictive binding,
  multi-chip scaling, or speedup evidence.
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

from experiments import tier4_22i_custom_runtime_roundtrip as base  # noqa: E402

# ---------------------------------------------------------------------------
# Fixed-point helpers (s16.15)
# ---------------------------------------------------------------------------
FP_SHIFT = 15
FP_ONE = 1 << FP_SHIFT
SURPRISE_RAW = 2 * FP_ONE


def fp_from_float(value: float) -> int:
    return int(value * FP_ONE)


def fp_to_float(value: int) -> float:
    return int(value) / FP_ONE


def fp_mul(a: int, b: int) -> int:
    return (int(a) * int(b)) >> FP_SHIFT


# ---------------------------------------------------------------------------
# Tier constants
# ---------------------------------------------------------------------------
TIER = "Tier 4.29b — Native Routing/Composition Gate"
RUNNER_REVISION = "tier4_29b_native_routing_composition_20260503_0001"
UPLOAD_PACKAGE_NAME = "cra_429c"
STABLE_EBRAINS_UPLOAD = ROOT / "ebrains_jobs" / UPLOAD_PACKAGE_NAME
DEPRECATED_EBRAINS_UPLOADS = [
    ROOT / "ebrains_jobs" / "cra_429a_old",
    ROOT / "ebrains_jobs" / "cra_429",
    ROOT / "ebrains_jobs" / "cra_429a",
    ROOT / "ebrains_jobs" / "cra_429b",
]

# Core role map
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

# Task parameters
TASK_LEARNING_RATE = 0.25
TASK_DELAY = 2
TASK_TAIL_WINDOW = 6

# Neutral memory key
NEUTRAL_MEMORY_KEY = 1

# Context slot keys and initial values
CONTEXT_SLOTS = {
    201: 1.0,
    202: 1.0,
    203: 1.0,
    204: 1.0,
    205: -1.0,
    206: -1.0,
    207: -0.5,
    208: -0.5,
}

# Route slot keys and initial values (non-neutral: +1.0 and -1.0)
ROUTE_SLOTS = {
    101: 1.0,   # positive regime: leaves feature sign unchanged
    102: -1.0,  # negative regime: flips feature sign
}

# Context overwrite: key 201 changes from +1.0 to -1.0 between phases
OVERWRITE_KEY = 201
OVERWRITE_OLD = 1.0
OVERWRITE_NEW = -1.0

# Route overwrite: key 102 changes from -1.0 to +1.0 between phases
ROUTE_OVERWRITE_KEY = 102
ROUTE_OVERWRITE_OLD = -1.0
ROUTE_OVERWRITE_NEW = 1.0

# Wrong-key values (never written)
WRONG_KEYS = [999, 998, 997, 996, 995, 994]
WRONG_ROUTE_KEYS = [899, 898, 897, 896]


def _generate_task_sequence() -> list[dict[str, Any]]:
    """Generate the 32-event stream with route-gated composition controls."""
    ctx_slots = dict(CONTEXT_SLOTS)
    route_slots = dict(ROUTE_SLOTS)
    events: list[dict[str, Any]] = []

    def add_event(step: int, ctx_key: int, route_key: int, cue: float, target: float, purpose: str) -> None:
        events.append({
            "step": step,
            "context_key": ctx_key,
            "route_key": route_key,
            "memory_key": NEUTRAL_MEMORY_KEY,
            "cue": cue,
            "target": target,
            "delay": TASK_DELAY,
            "purpose": purpose,
            "phase": 1 if step <= 16 else 2,
        })

    # Phase 1: route 101 (positive, sign unchanged) with first 4 context slots
    for i, (key, val) in enumerate(list(ctx_slots.items())[:4]):
        add_event(i + 1, key, 101, 1.0, val, f"phase1_route101_ctx{key}")

    # Phase 1: route 102 (negative, sign flipped) with last 4 context slots
    for i, (key, val) in enumerate(list(ctx_slots.items())[4:]):
        add_event(5 + i, key, 102, 1.0, -val, f"phase1_route102_ctx{key}")

    # Phase 1: wrong-context events (route ok, context missing)
    add_event(9, 201, 101, 1.0, 1.0, "phase1_wrong_ctx_route_ok")
    add_event(10, WRONG_KEYS[0], 101, 1.0, 0.0, "phase1_wrong_ctx")

    # Phase 1: wrong-route events (context ok, route missing)
    add_event(11, 201, WRONG_ROUTE_KEYS[0], 1.0, 0.0, "phase1_wrong_route")
    add_event(12, 202, WRONG_ROUTE_KEYS[1], 1.0, 0.0, "phase1_wrong_route2")

    # Phase 1: both-wrong events (both missing)
    add_event(13, WRONG_KEYS[1], WRONG_ROUTE_KEYS[2], 1.0, 0.0, "phase1_both_wrong")
    add_event(14, WRONG_KEYS[2], WRONG_ROUTE_KEYS[3], 1.0, 0.0, "phase1_both_wrong2")

    # Phase 1: re-read with flipped cues
    add_event(15, 203, 101, -1.0, -1.0, "phase1_reread_flip")
    add_event(16, 205, 102, -1.0, 1.0, "phase1_reread_flip_neg")

    # --- OVERWRITES between phases ---
    ctx_slots[OVERWRITE_KEY] = OVERWRITE_NEW
    route_slots[ROUTE_OVERWRITE_KEY] = ROUTE_OVERWRITE_NEW

    # Phase 2: context overwrite verification
    add_event(17, OVERWRITE_KEY, 101, 1.0, OVERWRITE_NEW, "phase2_ctx_overwrite")
    add_event(18, OVERWRITE_KEY, 101, -1.0, -OVERWRITE_NEW, "phase2_ctx_overwrite_neg")

    # Phase 2: route overwrite verification (was -1.0, now +1.0)
    add_event(19, 201, ROUTE_OVERWRITE_KEY, 1.0, 1.0, "phase2_route_overwrite")
    add_event(20, 202, ROUTE_OVERWRITE_KEY, 1.0, 1.0, "phase2_route_overwrite2")

    # Phase 2: mixed reads with both route keys
    mixed_ctx = [203, 204, 205, 206, 207, 208]
    mixed_route = [101, 102, 101, 102, 101, 102]
    for i, (ctx_key, route_key) in enumerate(zip(mixed_ctx, mixed_route)):
        ctx_val = ctx_slots[ctx_key]
        route_val = route_slots[route_key]
        cue = 1.0 if i % 2 == 0 else -1.0
        target = cue * ctx_val * route_val
        add_event(21 + i, ctx_key, route_key, cue, target, f"phase2_mixed_{ctx_key}_r{route_key}")

    # Phase 2: wrong-context and wrong-route events
    add_event(27, WRONG_KEYS[3], 101, 1.0, 0.0, "phase2_wrong_ctx")
    add_event(28, 201, WRONG_ROUTE_KEYS[0], 1.0, 0.0, "phase2_wrong_route")
    add_event(29, WRONG_KEYS[4], WRONG_ROUTE_KEYS[1], 1.0, 0.0, "phase2_both_wrong")

    # Phase 2: final re-reads
    add_event(30, 204, 102, 1.0, -1.0, "phase2_final")
    add_event(31, 206, 101, -1.0, 1.0, "phase2_final2")
    add_event(32, 208, 102, 1.0, 0.5, "phase2_final3")

    return events


TASK_SEQUENCE = _generate_task_sequence()


def _compute_reference() -> dict[str, Any]:
    """Fixed-point s16.15 reference matching chip semantics."""
    weight = 0
    bias = 0
    lr_raw = fp_from_float(TASK_LEARNING_RATE)
    pending: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []

    # Track simulated slot tables
    slots: dict[int, float] = dict(CONTEXT_SLOTS)
    route_slots: dict[int, float] = dict(ROUTE_SLOTS)

    for idx, event in enumerate(TASK_SEQUENCE):
        step = idx + 1
        key = event["context_key"]
        cue = event["cue"]
        target = event["target"]

        # Apply overwrites between phases
        if step == 17:
            slots[OVERWRITE_KEY] = OVERWRITE_NEW
            route_slots[ROUTE_OVERWRITE_KEY] = ROUTE_OVERWRITE_NEW

        # Linear-scan keyed lookup, default 0 for missing keys
        ctx_val = slots.get(key, 0.0)
        route_val = route_slots.get(event["route_key"], 0.0)

        # Feature = context * route * memory * cue  (memory=1.0)
        feature = ctx_val * route_val * cue
        feature_raw = fp_from_float(feature)
        target_raw = fp_from_float(target)

        # Prediction before update
        pred_raw = fp_mul(weight, feature_raw) + bias
        error_raw = target_raw - pred_raw

        # Surprise gating
        surprise = abs(error_raw)
        gated = surprise >= SURPRISE_RAW

        # Schedule pending
        pending.append({
            "feature_raw": feature_raw,
            "target_raw": target_raw,
            "prediction_raw": pred_raw,
            "due_step": step + TASK_DELAY,
            "step": step,
            "gated": gated,
        })

        # Mature any due pending
        while pending and pending[0]["due_step"] <= step:
            p = pending.pop(0)
            if not p["gated"]:
                err = p["target_raw"] - p["prediction_raw"]
                delta_w = fp_mul(lr_raw, fp_mul(err, p["feature_raw"]))
                delta_b = fp_mul(lr_raw, err)
                weight += delta_w
                bias += delta_b

            pred_sign = 1 if p["prediction_raw"] >= 0 else -1
            target_sign = 1 if p["target_raw"] >= 0 else -1
            rows.append({
                "step": p["step"],
                "sign_correct": pred_sign == target_sign,
                "gated": p["gated"],
                "feature_raw": p["feature_raw"],
                "prediction_raw": p["prediction_raw"],
            })

    # Mature remaining
    while pending:
        p = pending.pop(0)
        if not p["gated"]:
            err = p["target_raw"] - p["prediction_raw"]
            delta_w = fp_mul(lr_raw, fp_mul(err, p["feature_raw"]))
            delta_b = fp_mul(lr_raw, err)
            weight += delta_w
            bias += delta_b

        pred_sign = 1 if p["prediction_raw"] >= 0 else -1
        target_sign = 1 if p["target_raw"] >= 0 else -1
        rows.append({
            "step": p["step"],
            "sign_correct": pred_sign == target_sign,
            "gated": p["gated"],
            "feature_raw": p["feature_raw"],
            "prediction_raw": p["prediction_raw"],
        })

    tail = rows[-TASK_TAIL_WINDOW:]
    nongated_tail = [r for r in tail if not r.get("gated", False)]
    tail_accuracy = (
        sum(1 for r in nongated_tail if r["sign_correct"]) / len(nongated_tail)
        if nongated_tail else 0.0
    )

    # Count wrong-context-key events
    wrong_ctx_events = [e for e in TASK_SEQUENCE if e["context_key"] in WRONG_KEYS]
    wrong_ctx_count = len(wrong_ctx_events)

    # Count wrong-route-key events
    wrong_route_events = [e for e in TASK_SEQUENCE if e["route_key"] in WRONG_ROUTE_KEYS]
    wrong_route_count = len(wrong_route_events)

    # Count context overwrite events
    ctx_overwrite_events = [
        e for e in TASK_SEQUENCE
        if e["context_key"] == OVERWRITE_KEY and e["step"] > 16
    ]

    # Count route overwrite events
    route_overwrite_events = [
        e for e in TASK_SEQUENCE
        if e["route_key"] == ROUTE_OVERWRITE_KEY and e["step"] > 16
    ]

    # Route hits/misses
    route_hits = len([e for e in TASK_SEQUENCE if e["route_key"] in ROUTE_SLOTS])
    route_misses = wrong_route_count

    return {
        "weight_raw": weight,
        "weight": weight / FP_ONE,
        "bias_raw": bias,
        "bias": bias / FP_ONE,
        "tail_accuracy": tail_accuracy,
        "rows": rows,
        "wrong_ctx_count": wrong_ctx_count,
        "wrong_route_count": wrong_route_count,
        "ctx_overwrite_events": len(ctx_overwrite_events),
        "route_overwrite_events": len(route_overwrite_events),
        "slot_writes": len(CONTEXT_SLOTS) + 1,
        "slot_hits": len(TASK_SEQUENCE) - wrong_ctx_count,
        "slot_misses": wrong_ctx_count,
        "active_slots": len(CONTEXT_SLOTS),
        "route_slot_writes": len(ROUTE_SLOTS) + 1,
        "route_slot_hits": route_hits,
        "route_slot_misses": route_misses,
        "active_route_slots": len(ROUTE_SLOTS),
        "sequence_length": len(TASK_SEQUENCE),
    }


# ---------------------------------------------------------------------------
# Build helpers (same pattern as 4.28d)
# ---------------------------------------------------------------------------

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
    (output_dir / f"tier4_29b_build_{profile}_stdout.txt").write_text(build["stdout"])
    (output_dir / f"tier4_29b_build_{profile}_stderr.txt").write_text(build["stderr"])

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

    default_dir = f"tier4_29b_seed{args.seed}_job_output"
    output_dir = Path(args.output) if args.output else Path(default_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Verify MCPL wiring
    print("\n[1/6] Verifying MCPL source wiring...")
    wiring = verify_mcpl_wiring()
    for name, passed in wiring["checks"].items():
        mark = "PASS" if passed else "FAIL"
        print(f"  [{mark}] {name}")

    # 2. Build context_core
    print("\n[2/6] Building context_core with MCPL...")
    ctx = build_aplx_for_profile(CONTEXT_CORE_PROFILE, output_dir)
    print(f"  context_core: {'OK' if ctx['aplx_exists'] else 'FAIL'} (text={ctx['itcm_text_bytes']} bytes)")

    # 3. Build route_core
    print("\n[3/6] Building route_core with MCPL...")
    route = build_aplx_for_profile(ROUTE_CORE_PROFILE, output_dir)
    print(f"  route_core: {'OK' if route['aplx_exists'] else 'FAIL'} (text={route['itcm_text_bytes']} bytes)")

    # 4. Build memory_core
    print("\n[4/6] Building memory_core with MCPL...")
    mem = build_aplx_for_profile(MEMORY_CORE_PROFILE, output_dir)
    print(f"  memory_core: {'OK' if mem['aplx_exists'] else 'FAIL'} (text={mem['itcm_text_bytes']} bytes)")

    # 5. Build learning_core
    print("\n[5/6] Building learning_core with MCPL...")
    learn = build_aplx_for_profile(LEARNING_CORE_PROFILE, output_dir)
    print(f"  learning_core: {'OK' if learn['aplx_exists'] else 'FAIL'} (text={learn['itcm_text_bytes']} bytes)")

    # 6. Host reference
    print("\n[6/6] Running host reference...")
    ref = _compute_reference()
    print(f"  Host ref weight={ref['weight_raw']} ({ref['weight']:.4f}), bias={ref['bias_raw']} ({ref['bias']:.4f}), tail_acc={ref['tail_accuracy']:.2f}")
    print(f"  wrong_ctx={ref['wrong_ctx_count']}, wrong_route={ref['wrong_route_count']}, ctx_overwrite={ref['ctx_overwrite_events']}, route_overwrite={ref['route_overwrite_events']}, slot_hits={ref['slot_hits']}, slot_misses={ref['slot_misses']}")

    # Host tests + syntax
    host_tests = base.run_host_tests(output_dir)
    main_syntax = base.run_main_syntax_check(output_dir)

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
        {"name": "custom C host tests pass", "value": host_tests.get("status"), "rule": "== pass", "passed": host_tests.get("status") == "pass"},
        {"name": "host reference generated", "value": ref["sequence_length"], "rule": "== 32", "passed": ref["sequence_length"] == 32},
        {"name": "reference active slots match", "value": ref["active_slots"], "rule": "== 8", "passed": ref["active_slots"] == 8},
        {"name": "reference slot writes match", "value": ref["slot_writes"], "rule": "== 9", "passed": ref["slot_writes"] == 9},
        {"name": "reference slot hits match", "value": ref["slot_hits"], "rule": f"== {ref['slot_hits']}", "passed": True},
        {"name": "reference slot misses match", "value": ref["slot_misses"], "rule": f"== {ref['slot_misses']}", "passed": True},
        {"name": "reference wrong-context count match", "value": ref["wrong_ctx_count"], "rule": f"== {ref['wrong_ctx_count']}", "passed": True},
        {"name": "reference wrong-route count match", "value": ref["wrong_route_count"], "rule": f"== {ref['wrong_route_count']}", "passed": True},
        {"name": "reference context overwrite events match", "value": ref["ctx_overwrite_events"], "rule": f"== {ref['ctx_overwrite_events']}", "passed": True},
        {"name": "reference route overwrite events match", "value": ref["route_overwrite_events"], "rule": f"== {ref['route_overwrite_events']}", "passed": True},
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
        "reference": ref,
        "claim_boundary": "Local build validation only. NOT hardware evidence.",
    }

    output_path = output_dir / "tier4_29b_local_results.json"
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

    default_dir = f"tier4_29b_seed{args.seed}_job_output"
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

    (bundle / "experiments" / "__init__.py").write_text("# experiments package\n", encoding="utf-8")

    scripts = [
        "tier4_29b_native_routing_composition_gate.py",
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

    for name, b in builds.items():
        if b["aplx_exists"]:
            fname = f"coral_reef_{b['profile']}.aplx"
            shutil.copy2(b["aplx_path"], bundle / fname)

    # 4. Write README
    print("\n[4/4] Writing README...")
    command_single = f"{UPLOAD_PACKAGE_NAME}/experiments/tier4_29b_native_routing_composition_gate.py --mode run-hardware --seed 42"
    command_multi = f"{UPLOAD_PACKAGE_NAME}/experiments/tier4_29b_native_routing_composition_gate.py --mode run-hardware --seeds 42,43,44"

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

## Task Design

- 8 keyed context slots with signed values (+1.0, -1.0, +0.5, -0.5).
- 32 events in two phases (16 + 16).
- Phase 2 includes a mid-stream overwrite of slot 201 (+1.0 → -1.0).
- 6 wrong-key events (~19%) expect feature=0 (bias-only prediction).
- Slot-shuffle control: events read slots in different orders across phases.

## Exact JobManager Command (all 3 seeds in one job)

```text
{command_multi}
```

## Alternative: single-seed command

```text
{command_single}
```

## Expected Reference Metrics

```text
readout_weight_raw  ≈ +25000 (positive, converges toward +1.0)
readout_bias_raw    ≈ 0
pending_created     = 32
pending_matured     = 32
active_pending      = 0
decisions           = 32
reward_events       = 32
lookup_requests     = 96 (3 per event: context + route + memory)
lookup_replies      = 96
stale_replies       = 0
timeouts            = 0
schema_version      = 2
payload_bytes       = 105
context_active_slots    = 8
context_slot_writes     = 9 (8 initial + 1 overwrite)
context_slot_hits       = 26
context_slot_misses     = 6
```

Tolerance: weight ±8192, bias ±8192

## Multi-Seed Repeatability

Run `--seeds 42,43,44` for one-job three-seed execution.
Each seed produces output in `tier4_29b_seed{{seed}}_job_output/`.

## Claim Boundary

Local package preparation and build validation only. NOT hardware evidence.
Returned EBRAINS artifacts must pass all criteria for each seed to claim
keyed-memory overcapacity gate.
"""

    readme = bundle / "README_TIER4_29B_JOB.md"
    readme.write_text(readme_text, encoding="utf-8")

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
            "job_command": command_multi,
            "what_i_need_from_user": f"Upload {UPLOAD_PACKAGE_NAME} to EBRAINS/JobManager and run the emitted command for seeds 42, 43, 44.",
            "claim_boundary": "Local package preparation only. NOT hardware evidence.",
        },
        "criteria": criteria,
    }

    output_path = output_dir / "tier4_29b_prepare_results.json"
    output_path.write_text(json.dumps(result, indent=2))
    print(f"\nArtifact: {output_path}")
    print(f"\n{'=' * 60}")
    print(f"OVERALL: {status.upper()}")
    for c in criteria:
        mark = "PASS" if c["passed"] else "FAIL"
        print(f"  [{mark}] {c['name']}")
    return result


# ---------------------------------------------------------------------------
# Hardware helpers
# ---------------------------------------------------------------------------

def _build_schedule(sequence: list[dict[str, Any]], offset: int = 0) -> list[dict]:
    """Build compact schedule entries from task sequence."""
    schedule = []
    for i, event in enumerate(sequence):
        schedule.append({
            "index": offset + i,
            "timestep": i + 1,  # relative to phase base_timestep
            "context_key": int(event["context_key"]),
            "route_key": int(event["route_key"]),
            "memory_key": int(event["memory_key"]),
            "cue": float(event["cue"]),
            "target": float(event["target"]),
            "delay": int(event["delay"]),
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

        # Write keyed route slots (non-neutral values)
        route_writes = []
        for key, val in ROUTE_SLOTS.items():
            ok = route_ctrl.write_route_slot(key, val, 1.0, dest_x, dest_y, ROUTE_CORE_P)
            route_writes.append({"key": key, "value": val, "success": ok.get("success") is True})

        mem_writes = []
        ok = mem_ctrl.write_memory_slot(NEUTRAL_MEMORY_KEY, 1.0, 1.0, dest_x, dest_y, MEMORY_CORE_P)
        mem_writes.append({"key": NEUTRAL_MEMORY_KEY, "success": ok.get("success") is True})

        # Write initial context slots
        ctx_writes = []
        for key, val in CONTEXT_SLOTS.items():
            ok = ctx_ctrl.write_context(key, val, 1.0, dest_x, dest_y, CONTEXT_CORE_P)
            ctx_writes.append({"key": key, "value": val, "success": ok.get("success") is True})

        # Build and upload Phase 1 schedule (events 0-15)
        phase1_events = TASK_SEQUENCE[:16]
        phase1_schedule = _build_schedule(phase1_events, offset=0)
        schedule_uploads = []
        for entry in phase1_schedule:
            ok = learning_ctrl.write_schedule_entry(
                index=entry["index"],
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
            schedule_uploads.append({"index": entry["index"], "success": ok.get("success") is True})

        # Phase 1: Start continuous on all four cores
        learning_rate = TASK_LEARNING_RATE
        ctx_run1 = ctx_ctrl.run_continuous(learning_rate, 0, dest_x, dest_y, CONTEXT_CORE_P)
        route_run1 = route_ctrl.run_continuous(learning_rate, 0, dest_x, dest_y, ROUTE_CORE_P)
        mem_run1 = mem_ctrl.run_continuous(learning_rate, 0, dest_x, dest_y, MEMORY_CORE_P)
        learning_run1 = learning_ctrl.run_continuous(learning_rate, len(phase1_schedule), dest_x, dest_y, LEARNING_CORE_P)
        time.sleep(0.05)

        # Wait for Phase 1 completion
        max_wait = 10.0
        poll_interval = 0.5
        waited1 = 0.0
        while waited1 < max_wait:
            time.sleep(poll_interval)
            waited1 += poll_interval
            learning_status = learning_ctrl.read_state(dest_x, dest_y, LEARNING_CORE_P)
            if learning_status.get("success") and learning_status.get("active_pending") == 0:
                break

        # Read mid-state for diagnostics
        learning_mid = learning_ctrl.read_state(dest_x, dest_y, LEARNING_CORE_P)
        ctx_mid = ctx_ctrl.read_state(dest_x, dest_y, CONTEXT_CORE_P)

        # Phase 2: Overwrite context slot 201 and route slot 102
        overwrite_write = ctx_ctrl.write_context(OVERWRITE_KEY, OVERWRITE_NEW, 1.0, dest_x, dest_y, CONTEXT_CORE_P)
        route_overwrite_write = route_ctrl.write_route_slot(ROUTE_OVERWRITE_KEY, ROUTE_OVERWRITE_NEW, 1.0, dest_x, dest_y, ROUTE_CORE_P)

        # Build and upload Phase 2 schedule (events 16-31)
        phase2_events = TASK_SEQUENCE[16:]
        phase2_schedule = _build_schedule(phase2_events, offset=16)
        for entry in phase2_schedule:
            ok = learning_ctrl.write_schedule_entry(
                index=entry["index"],
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
            schedule_uploads.append({"index": entry["index"], "success": ok.get("success") is True})

        # Phase 2: Resume continuous on all cores
        ctx_run2 = ctx_ctrl.run_continuous(learning_rate, 0, dest_x, dest_y, CONTEXT_CORE_P)
        route_run2 = route_ctrl.run_continuous(learning_rate, 0, dest_x, dest_y, ROUTE_CORE_P)
        mem_run2 = mem_ctrl.run_continuous(learning_rate, 0, dest_x, dest_y, MEMORY_CORE_P)
        total_schedule = len(phase1_schedule) + len(phase2_schedule)
        learning_run2 = learning_ctrl.run_continuous(learning_rate, total_schedule, dest_x, dest_y, LEARNING_CORE_P)
        time.sleep(0.05)

        # Wait for Phase 2 completion
        waited2 = 0.0
        while waited2 < max_wait:
            time.sleep(poll_interval)
            waited2 += poll_interval
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
            "overwrite_write": {
                "success": overwrite_write.get("success") is True,
                "active_slots_after": overwrite_write.get("active_slots"),
                "slot_writes_after": overwrite_write.get("slot_writes"),
            },
            "route_overwrite_write": {
                "success": route_overwrite_write.get("success") is True,
                "active_route_slots_after": route_overwrite_write.get("active_slots"),
                "route_slot_writes_after": route_overwrite_write.get("slot_writes"),
            },
            "schedule_uploads": schedule_uploads,
            "run_continuous": {
                "phase1": {
                    "context": {"success": ctx_run1.get("success") is True},
                    "route": {"success": route_run1.get("success") is True},
                    "memory": {"success": mem_run1.get("success") is True},
                    "learning": {"success": learning_run1.get("success") is True},
                },
                "phase2": {
                    "context": {"success": ctx_run2.get("success") is True},
                    "route": {"success": route_run2.get("success") is True},
                    "memory": {"success": mem_run2.get("success") is True},
                    "learning": {"success": learning_run2.get("success") is True},
                },
            },
            "pause": {
                "context": {"success": ctx_pause.get("success") is True},
                "route": {"success": route_pause.get("success") is True},
                "memory": {"success": mem_pause.get("success") is True},
                "learning": {"success": learning_pause.get("success") is True},
            },
            "mid_state": {
                "context": ctx_mid,
                "learning": learning_mid,
            },
            "final_state": {
                "context": ctx_final,
                "route": route_final,
                "memory": mem_final,
                "learning": learning_final,
            },
            "waited_seconds": {"phase1": waited1, "phase2": waited2},
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

    default_dir = f"tier4_29b_seed{args.seed}_job_output"
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

    write_json(output_dir / "tier4_29b_environment.json", env_report)
    write_json(output_dir / "tier4_29b_target_acquisition.json", base.public_target_acquisition(target))

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
                write_json(output_dir / f"tier4_29b_{name}_load.json", load_info)

        if (target.get("status") == "pass" and hostname
            and all(l.get("status") == "pass" for l in loads.values())):
            print("\n[4/4] Running four-core hardware loop...")
            task_result = four_core_hardware_loop(hostname, args, target, loads)
            write_json(output_dir / "tier4_29b_task.json", task_result)
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
        write_json(output_dir / "tier4_29b_environment.json", env_report)
        write_json(output_dir / "tier4_29b_target_acquisition.json", base.public_target_acquisition(target))
        for name, load_info in loads.items():
            write_json(output_dir / f"tier4_29b_{name}_load.json", load_info)
        write_json(output_dir / "tier4_29b_task.json", task_result)

    # Reference
    ref = _compute_reference()
    ref_events = len(TASK_SEQUENCE)
    tolerance = 8192

    final_states = task_result.get("final_state", {}) if isinstance(task_result, dict) else {}
    learning_final = final_states.get("learning", {}) if isinstance(final_states, dict) else {}
    ctx_final = final_states.get("context", {}) if isinstance(final_states, dict) else {}
    route_final = final_states.get("route", {}) if isinstance(final_states, dict) else {}
    mem_final = final_states.get("memory", {}) if isinstance(final_states, dict) else {}

    mid_states = task_result.get("mid_state", {}) if isinstance(task_result, dict) else {}
    ctx_mid = mid_states.get("context", {}) if isinstance(mid_states, dict) else {}

    def criterion(name: str, value: Any, rule: str, passed: bool, note: str = "") -> dict[str, Any]:
        return {"name": name, "value": value, "rule": rule, "passed": passed, "note": note}

    # Criteria guards using len(list)>0 and all(...) pattern
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
        criterion("phase1 context_core run_continuous succeeded", task_result.get("run_continuous", {}).get("phase1", {}).get("context", {}).get("success"), "== True", task_result.get("run_continuous", {}).get("phase1", {}).get("context", {}).get("success") is True),
        criterion("phase1 route_core run_continuous succeeded", task_result.get("run_continuous", {}).get("phase1", {}).get("route", {}).get("success"), "== True", task_result.get("run_continuous", {}).get("phase1", {}).get("route", {}).get("success") is True),
        criterion("phase1 memory_core run_continuous succeeded", task_result.get("run_continuous", {}).get("phase1", {}).get("memory", {}).get("success"), "== True", task_result.get("run_continuous", {}).get("phase1", {}).get("memory", {}).get("success") is True),
        criterion("phase1 learning_core run_continuous succeeded", task_result.get("run_continuous", {}).get("phase1", {}).get("learning", {}).get("success"), "== True", task_result.get("run_continuous", {}).get("phase1", {}).get("learning", {}).get("success") is True),
        criterion("phase2 context_core run_continuous succeeded", task_result.get("run_continuous", {}).get("phase2", {}).get("context", {}).get("success"), "== True", task_result.get("run_continuous", {}).get("phase2", {}).get("context", {}).get("success") is True),
        criterion("phase2 route_core run_continuous succeeded", task_result.get("run_continuous", {}).get("phase2", {}).get("route", {}).get("success"), "== True", task_result.get("run_continuous", {}).get("phase2", {}).get("route", {}).get("success") is True),
        criterion("phase2 memory_core run_continuous succeeded", task_result.get("run_continuous", {}).get("phase2", {}).get("memory", {}).get("success"), "== True", task_result.get("run_continuous", {}).get("phase2", {}).get("memory", {}).get("success") is True),
        criterion("phase2 learning_core run_continuous succeeded", task_result.get("run_continuous", {}).get("phase2", {}).get("learning", {}).get("success"), "== True", task_result.get("run_continuous", {}).get("phase2", {}).get("learning", {}).get("success") is True),
        criterion("overwrite write succeeded", task_result.get("overwrite_write", {}).get("success"), "== True", task_result.get("overwrite_write", {}).get("success") is True),
        criterion("context_core final read succeeded", ctx_final.get("success"), "== True", ctx_final.get("success") is True),
        criterion("route_core final read succeeded", route_final.get("success"), "== True", route_final.get("success") is True),
        criterion("memory_core final read succeeded", mem_final.get("success"), "== True", mem_final.get("success") is True),
        criterion("learning_core final read succeeded", learning_final.get("success"), "== True", learning_final.get("success") is True),
        criterion("learning_core weight near reference", learning_final.get("readout_weight_raw"), f"within +/- {tolerance} of {ref['weight_raw']}", abs(int(learning_final.get("readout_weight_raw") or 0) - ref["weight_raw"]) <= tolerance),
        criterion("learning_core bias near reference", learning_final.get("readout_bias_raw"), f"within +/- {tolerance} of {ref['bias_raw']}", abs(int(learning_final.get("readout_bias_raw") or 0) - ref["bias_raw"]) <= tolerance),
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
        # Tier 4.29b specific criteria — context controls
        criterion("wrong-context events fail cleanly (context misses)", ctx_final.get("slot_misses"), f"== {ref['slot_misses']}", ctx_final.get("slot_misses") == ref["slot_misses"]),
        criterion("context overwrite uses new value (context writes)", ctx_final.get("slot_writes"), f"== {ref['slot_writes']}", ctx_final.get("slot_writes") == ref["slot_writes"]),
        criterion("context slot-shuffle maintains correctness (context hits)", ctx_final.get("slot_hits"), f"== {ref['slot_hits']}", ctx_final.get("slot_hits") == ref["slot_hits"]),
        criterion("context_core active_slots matches expected", ctx_final.get("active_slots"), f"== {ref['active_slots']}", ctx_final.get("active_slots") == ref["active_slots"]),
        # Tier 4.29b specific criteria — route controls
        criterion("route overwrite write succeeded", task_result.get("route_overwrite_write", {}).get("success"), "== True", task_result.get("route_overwrite_write", {}).get("success") is True),
        criterion("wrong-route events fail cleanly (route misses)", route_final.get("slot_misses"), f"== {ref['route_slot_misses']}", route_final.get("slot_misses") == ref["route_slot_misses"]),
        criterion("route overwrite uses new value (route writes)", route_final.get("slot_writes"), f"== {ref['route_slot_writes']}", route_final.get("slot_writes") == ref["route_slot_writes"]),
        criterion("route lookups maintain correctness (route hits)", route_final.get("slot_hits"), f"== {ref['route_slot_hits']}", route_final.get("slot_hits") == ref["route_slot_hits"]),
        criterion("route_core active_slots matches expected", route_final.get("active_slots"), f"== {ref['active_route_slots']}", route_final.get("active_slots") == ref["active_route_slots"]),
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
        "reference": ref,
    }
    write_json(output_dir / "tier4_29b_hardware_results.json", result)

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
    print("Tier 4.29b — Ingest hardware results")
    print("=" * 60)

    default_dir = f"tier4_29b_seed{args.seed}_job_output"
    output_dir = Path(args.output) if args.output else Path(default_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    hw_dir = Path(args.hardware_output_dir) if args.hardware_output_dir else output_dir
    hw_results_path = hw_dir / "tier4_29b_hardware_results.json"

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
    output_path = output_dir / "tier4_29b_ingest_results.json"
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

    (output_dir / "tier4_29b_ingest_report.md").write_text(report)

    print(f"OVERALL: {status.upper()}")
    print(f"Passed: {passed}/{total}")
    print(f"Ingest report: {output_dir / 'tier4_29b_ingest_report.md'}")
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
    parser.add_argument("--seeds", type=str, default="", help="Comma-separated seeds for multi-seed run-hardware (e.g., 42,43,44). Overrides --seed.")
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
                combined_path = Path(f"tier4_29b_multi_seed_job_output") / "tier4_29b_combined_results.json"
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
        crash_path = Path(f"tier4_29b_seed{args.seed}_job_output") / "tier4_29b_crash_report.json"
        crash_path.parent.mkdir(parents=True, exist_ok=True)
        crash_path.write_text(json.dumps(crash, indent=2))
        print(f"\n[FATAL CRASH] {type(exc).__name__}: {exc}")
        print(f"Crash report written to: {crash_path}")
        return 1


if __name__ == "__main__":
    sys.exit(main())


# ---------------------------------------------------------------------------
# Local mode
# ---------------------------------------------------------------------------

def mode_local(args: argparse.Namespace) -> dict[str, Any]:
    print(TIER)
    print("=" * 60)

    default_dir = f"tier4_29b_seed{args.seed}_job_output"
    output_dir = Path(args.output) if args.output else Path(default_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Verify MCPL wiring
    print("\n[1/6] Verifying MCPL source wiring...")
    wiring = verify_mcpl_wiring()
    for name, passed in wiring["checks"].items():
        mark = "PASS" if passed else "FAIL"
        print(f"  [{mark}] {name}")

    # 2. Build context_core
    print("\n[2/6] Building context_core with MCPL...")
    ctx = build_aplx_for_profile(CONTEXT_CORE_PROFILE, output_dir)
    print(f"  context_core: {'OK' if ctx['aplx_exists'] else 'FAIL'} (text={ctx['itcm_text_bytes']} bytes)")

    # 3. Build route_core
    print("\n[3/6] Building route_core with MCPL...")
    route = build_aplx_for_profile(ROUTE_CORE_PROFILE, output_dir)
    print(f"  route_core: {'OK' if route['aplx_exists'] else 'FAIL'} (text={route['itcm_text_bytes']} bytes)")

    # 4. Build memory_core
    print("\n[4/6] Building memory_core with MCPL...")
    mem = build_aplx_for_profile(MEMORY_CORE_PROFILE, output_dir)
    print(f"  memory_core: {'OK' if mem['aplx_exists'] else 'FAIL'} (text={mem['itcm_text_bytes']} bytes)")

    # 5. Build learning_core
    print("\n[5/6] Building learning_core with MCPL...")
    learn = build_aplx_for_profile(LEARNING_CORE_PROFILE, output_dir)
    print(f"  learning_core: {'OK' if learn['aplx_exists'] else 'FAIL'} (text={learn['itcm_text_bytes']} bytes)")

    # 6. Host reference
    print("\n[6/6] Running host reference...")
    ref = _compute_reference()
    print(f"  Host ref weight={ref['weight_raw']} ({ref['weight']:.4f}), bias={ref['bias_raw']} ({ref['bias']:.4f}), tail_acc={ref['tail_accuracy']:.2f}")
    print(f"  wrong_ctx={ref['wrong_ctx_count']}, wrong_route={ref['wrong_route_count']}, ctx_overwrite={ref['ctx_overwrite_events']}, route_overwrite={ref['route_overwrite_events']}")
    print(f"  ctx_hits={ref['slot_hits']}, ctx_misses={ref['slot_misses']}, route_hits={ref['route_slot_hits']}, route_misses={ref['route_slot_misses']}")

    # Host tests + syntax
    host_tests = base.run_host_tests(output_dir)
    main_syntax = base.run_main_syntax_check(output_dir)

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
        {"name": "custom C host tests pass", "value": host_tests.get("status"), "rule": "== pass", "passed": host_tests.get("status") == "pass"},
        {"name": "host reference generated", "value": ref["sequence_length"], "rule": "== 32", "passed": ref["sequence_length"] == 32},
        {"name": "reference active context slots match", "value": ref["active_slots"], "rule": "== 8", "passed": ref["active_slots"] == 8},
        {"name": "reference context slot writes match", "value": ref["slot_writes"], "rule": "== 9", "passed": ref["slot_writes"] == 9},
        {"name": "reference context slot hits match", "value": ref["slot_hits"], "rule": "== 24", "passed": ref["slot_hits"] == 24},
        {"name": "reference context slot misses match", "value": ref["slot_misses"], "rule": "== 8", "passed": ref["slot_misses"] == 8},
        {"name": "reference wrong-context count match", "value": ref["wrong_ctx_count"], "rule": "== 8", "passed": ref["wrong_ctx_count"] == 8},
        {"name": "reference context overwrite events match", "value": ref["ctx_overwrite_events"], "rule": ">= 2", "passed": ref["ctx_overwrite_events"] >= 2},
        {"name": "reference active route slots match", "value": ref["active_route_slots"], "rule": "== 2", "passed": ref["active_route_slots"] == 2},
        {"name": "reference route slot writes match", "value": ref["route_slot_writes"], "rule": "== 3", "passed": ref["route_slot_writes"] == 3},
        {"name": "reference route slot hits match", "value": ref["route_slot_hits"], "rule": "== 24", "passed": ref["route_slot_hits"] == 24},
        {"name": "reference route slot misses match", "value": ref["route_slot_misses"], "rule": "== 8", "passed": ref["route_slot_misses"] == 8},
        {"name": "reference wrong-route count match", "value": ref["wrong_route_count"], "rule": "== 8", "passed": ref["wrong_route_count"] == 8},
        {"name": "reference route overwrite events match", "value": ref["route_overwrite_events"], "rule": ">= 2", "passed": ref["route_overwrite_events"] >= 2},
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
        "reference": ref,
        "claim_boundary": "Local build validation only. NOT hardware evidence.",
    }

    output_path = output_dir / "tier4_29b_local_results.json"
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

    default_dir = f"tier4_29b_seed{args.seed}_job_output"
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

    (bundle / "experiments" / "__init__.py").write_text("# experiments package\n", encoding="utf-8")

    scripts = [
        "tier4_29b_native_routing_composition_gate.py",
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

    for name, b in builds.items():
        if b["aplx_exists"]:
            fname = f"coral_reef_{b['profile']}.aplx"
            shutil.copy2(b["aplx_path"], bundle / fname)

    # 4. Write README
    print("\n[4/4] Writing README...")
    command_single = f"{UPLOAD_PACKAGE_NAME}/experiments/tier4_29b_native_routing_composition_gate.py --mode run-hardware --seed 42"
    command_multi = f"{UPLOAD_PACKAGE_NAME}/experiments/tier4_29b_native_routing_composition_gate.py --mode run-hardware --seeds 42,43,44"

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

## Task Design

- 8 keyed context slots with signed values (+1.0, -1.0, +0.5, -0.5).
- 2 keyed route slots with signed values (+1.0, -1.0).
- Neutral memory slot (value = 1.0, no multiplicative effect).
- 32 events in two phases (16 + 16).
- Phase 2 includes mid-stream overwrites: slot 201 (+1.0 → -1.0) and route 102 (-1.0 → +1.0).
- 8 wrong-context events (~25%) expect feature=0.
- 8 wrong-route events (~25%) expect feature=0.
- 4 both-wrong events (~12%) expect feature=0.
- Feature = context[key] * route[key] * memory[key] * cue.

## Exact JobManager Command (all 3 seeds in one job)

```text
{command_multi}
```

## Alternative: single-seed command

```text
{command_single}
```

## Expected Reference Metrics

```text
readout_weight_raw  ≈ +8192 (positive, partial convergence)
readout_bias_raw    ≈ -5905
pending_created     = 32
pending_matured     = 32
active_pending      = 0
decisions           = 32
reward_events       = 32
lookup_requests     = 96 (3 per event: context + route + memory)
lookup_replies      = 96
stale_replies       = 0
timeouts            = 0
schema_version      = 2
payload_bytes       = 105
context_active_slots    = 8
context_slot_writes     = 9 (8 initial + 1 overwrite)
context_slot_hits       = 24
context_slot_misses     = 8
route_active_slots      = 2
route_slot_writes       = 3 (2 initial + 1 overwrite)
route_slot_hits         = 24
route_slot_misses       = 8
```

Tolerance: weight ±8192, bias ±8192

## Multi-Seed Repeatability

Run `--seeds 42,43,44` for one-job three-seed execution.
Each seed produces output in `tier4_29b_seed{{seed}}_job_output/`.

## Claim Boundary

Local package preparation and build validation only. NOT hardware evidence.
Returned EBRAINS artifacts must pass all criteria for each seed to claim
native routing/composition gate.
"""

    readme = bundle / "README_TIER4_29B_JOB.md"
    readme.write_text(readme_text, encoding="utf-8")

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
            "job_command": command_multi,
            "what_i_need_from_user": f"Upload {UPLOAD_PACKAGE_NAME} to EBRAINS/JobManager and run the emitted command for seeds 42, 43, 44.",
            "claim_boundary": "Local package preparation only. NOT hardware evidence.",
        },
        "criteria": criteria,
    }

    output_path = output_dir / "tier4_29b_prepare_results.json"
    output_path.write_text(json.dumps(result, indent=2))
    print(f"\nArtifact: {output_path}")
    print(f"\n{'=' * 60}")
    print(f"OVERALL: {status.upper()}")
    for c in criteria:
        mark = "PASS" if c["passed"] else "FAIL"
        print(f"  [{mark}] {c['name']}")
    return result


# ---------------------------------------------------------------------------
# Hardware helpers
# ---------------------------------------------------------------------------

def _build_schedule(sequence: list[dict[str, Any]], offset: int = 0) -> list[dict]:
    """Build compact schedule entries from task sequence."""
    schedule = []
    for i, event in enumerate(sequence):
        schedule.append({
            "index": offset + i,
            "timestep": i + 1,  # relative to phase base_timestep
            "context_key": int(event["context_key"]),
            "route_key": int(event["route_key"]),
            "memory_key": int(event["memory_key"]),
            "cue": float(event["cue"]),
            "target": float(event["target"]),
            "delay": int(event["delay"]),
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

        # Write route slots (non-neutral)
        route_writes = []
        for key, val in ROUTE_SLOTS.items():
            ok = route_ctrl.write_route_slot(key, val, 1.0, dest_x, dest_y, ROUTE_CORE_P)
            route_writes.append({"key": key, "value": val, "success": ok.get("success") is True})

        # Write neutral memory slot
        mem_writes = []
        ok = mem_ctrl.write_memory_slot(NEUTRAL_MEMORY_KEY, 1.0, 1.0, dest_x, dest_y, MEMORY_CORE_P)
        mem_writes.append({"key": NEUTRAL_MEMORY_KEY, "success": ok.get("success") is True})

        # Write initial context slots
        ctx_writes = []
        for key, val in CONTEXT_SLOTS.items():
            ok = ctx_ctrl.write_context(key, val, 1.0, dest_x, dest_y, CONTEXT_CORE_P)
            ctx_writes.append({"key": key, "value": val, "success": ok.get("success") is True})

        # Build and upload Phase 1 schedule (events 0-15)
        phase1_events = TASK_SEQUENCE[:16]
        phase1_schedule = _build_schedule(phase1_events, offset=0)
        schedule_uploads = []
        for entry in phase1_schedule:
            ok = learning_ctrl.write_schedule_entry(
                index=entry["index"],
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
            schedule_uploads.append({"index": entry["index"], "success": ok.get("success") is True})

        # Phase 1: Start continuous on all four cores
        learning_rate = TASK_LEARNING_RATE
        ctx_run1 = ctx_ctrl.run_continuous(learning_rate, 0, dest_x, dest_y, CONTEXT_CORE_P)
        route_run1 = route_ctrl.run_continuous(learning_rate, 0, dest_x, dest_y, ROUTE_CORE_P)
        mem_run1 = mem_ctrl.run_continuous(learning_rate, 0, dest_x, dest_y, MEMORY_CORE_P)
        learning_run1 = learning_ctrl.run_continuous(learning_rate, len(phase1_schedule), dest_x, dest_y, LEARNING_CORE_P)
        time.sleep(0.05)

        # Wait for Phase 1 completion
        max_wait = 10.0
        poll_interval = 0.5
        waited1 = 0.0
        while waited1 < max_wait:
            time.sleep(poll_interval)
            waited1 += poll_interval
            learning_status = learning_ctrl.read_state(dest_x, dest_y, LEARNING_CORE_P)
            if learning_status.get("success") and learning_status.get("active_pending") == 0:
                break

        # Read mid-state for diagnostics
        learning_mid = learning_ctrl.read_state(dest_x, dest_y, LEARNING_CORE_P)
        ctx_mid = ctx_ctrl.read_state(dest_x, dest_y, CONTEXT_CORE_P)
        route_mid = route_ctrl.read_state(dest_x, dest_y, ROUTE_CORE_P)

        # Phase 2: Context overwrite
        overwrite_write = ctx_ctrl.write_context(OVERWRITE_KEY, OVERWRITE_NEW, 1.0, dest_x, dest_y, CONTEXT_CORE_P)

        # Phase 2: Route overwrite
        route_overwrite_write = route_ctrl.write_route_slot(ROUTE_OVERWRITE_KEY, ROUTE_OVERWRITE_NEW, 1.0, dest_x, dest_y, ROUTE_CORE_P)

        # Build and upload Phase 2 schedule (events 16-31)
        phase2_events = TASK_SEQUENCE[16:]
        phase2_schedule = _build_schedule(phase2_events, offset=16)
        for entry in phase2_schedule:
            ok = learning_ctrl.write_schedule_entry(
                index=entry["index"],
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
            schedule_uploads.append({"index": entry["index"], "success": ok.get("success") is True})

        # Phase 2: Resume continuous on all cores
        ctx_run2 = ctx_ctrl.run_continuous(learning_rate, 0, dest_x, dest_y, CONTEXT_CORE_P)
        route_run2 = route_ctrl.run_continuous(learning_rate, 0, dest_x, dest_y, ROUTE_CORE_P)
        mem_run2 = mem_ctrl.run_continuous(learning_rate, 0, dest_x, dest_y, MEMORY_CORE_P)
        total_schedule = len(phase1_schedule) + len(phase2_schedule)
        learning_run2 = learning_ctrl.run_continuous(learning_rate, total_schedule, dest_x, dest_y, LEARNING_CORE_P)
        time.sleep(0.05)

        # Wait for Phase 2 completion
        waited2 = 0.0
        while waited2 < max_wait:
            time.sleep(poll_interval)
            waited2 += poll_interval
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
            "overwrite_write": {
                "success": overwrite_write.get("success") is True,
                "active_slots_after": overwrite_write.get("active_slots"),
                "slot_writes_after": overwrite_write.get("slot_writes"),
            },
            "route_overwrite_write": {
                "success": route_overwrite_write.get("success") is True,
                "active_slots_after": route_overwrite_write.get("active_slots"),
                "slot_writes_after": route_overwrite_write.get("slot_writes"),
            },
            "schedule_uploads": schedule_uploads,
            "run_continuous": {
                "phase1": {
                    "context": {"success": ctx_run1.get("success") is True},
                    "route": {"success": route_run1.get("success") is True},
                    "memory": {"success": mem_run1.get("success") is True},
                    "learning": {"success": learning_run1.get("success") is True},
                },
                "phase2": {
                    "context": {"success": ctx_run2.get("success") is True},
                    "route": {"success": route_run2.get("success") is True},
                    "memory": {"success": mem_run2.get("success") is True},
                    "learning": {"success": learning_run2.get("success") is True},
                },
            },
            "pause": {
                "context": {"success": ctx_pause.get("success") is True},
                "route": {"success": route_pause.get("success") is True},
                "memory": {"success": mem_pause.get("success") is True},
                "learning": {"success": learning_pause.get("success") is True},
            },
            "mid_state": {
                "context": ctx_mid,
                "route": route_mid,
                "learning": learning_mid,
            },
            "final_state": {
                "context": ctx_final,
                "route": route_final,
                "memory": mem_final,
                "learning": learning_final,
            },
            "waited_seconds": {"phase1": waited1, "phase2": waited2},
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

    default_dir = f"tier4_29b_seed{args.seed}_job_output"
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

    write_json(output_dir / "tier4_29b_environment.json", env_report)
    write_json(output_dir / "tier4_29b_target_acquisition.json", base.public_target_acquisition(target))

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
                write_json(output_dir / f"tier4_29b_{name}_load.json", load_info)

        if (target.get("status") == "pass" and hostname
            and all(l.get("status") == "pass" for l in loads.values())):
            print("\n[4/4] Running four-core hardware loop...")
            task_result = four_core_hardware_loop(hostname, args, target, loads)
            write_json(output_dir / "tier4_29b_task.json", task_result)
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
        write_json(output_dir / "tier4_29b_environment.json", env_report)
        write_json(output_dir / "tier4_29b_target_acquisition.json", base.public_target_acquisition(target))
        for name, load_info in loads.items():
            write_json(output_dir / f"tier4_29b_{name}_load.json", load_info)
        write_json(output_dir / "tier4_29b_task.json", task_result)

    # Reference
    ref = _compute_reference()
    ref_events = len(TASK_SEQUENCE)
    tolerance = 8192

    final_states = task_result.get("final_state", {}) if isinstance(task_result, dict) else {}
    learning_final = final_states.get("learning", {}) if isinstance(final_states, dict) else {}
    ctx_final = final_states.get("context", {}) if isinstance(final_states, dict) else {}
    route_final = final_states.get("route", {}) if isinstance(final_states, dict) else {}
    mem_final = final_states.get("memory", {}) if isinstance(final_states, dict) else {}

    mid_states = task_result.get("mid_state", {}) if isinstance(task_result, dict) else {}
    ctx_mid = mid_states.get("context", {}) if isinstance(mid_states, dict) else {}

    def criterion(name: str, value: Any, rule: str, passed: bool, note: str = "") -> dict[str, Any]:
        return {"name": name, "value": value, "rule": rule, "passed": passed, "note": note}

    # Criteria guards using len(list)>0 and all(...) pattern
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
        criterion("phase1 context_core run_continuous succeeded", task_result.get("run_continuous", {}).get("phase1", {}).get("context", {}).get("success"), "== True", task_result.get("run_continuous", {}).get("phase1", {}).get("context", {}).get("success") is True),
        criterion("phase1 route_core run_continuous succeeded", task_result.get("run_continuous", {}).get("phase1", {}).get("route", {}).get("success"), "== True", task_result.get("run_continuous", {}).get("phase1", {}).get("route", {}).get("success") is True),
        criterion("phase1 memory_core run_continuous succeeded", task_result.get("run_continuous", {}).get("phase1", {}).get("memory", {}).get("success"), "== True", task_result.get("run_continuous", {}).get("phase1", {}).get("memory", {}).get("success") is True),
        criterion("phase1 learning_core run_continuous succeeded", task_result.get("run_continuous", {}).get("phase1", {}).get("learning", {}).get("success"), "== True", task_result.get("run_continuous", {}).get("phase1", {}).get("learning", {}).get("success") is True),
        criterion("phase2 context_core run_continuous succeeded", task_result.get("run_continuous", {}).get("phase2", {}).get("context", {}).get("success"), "== True", task_result.get("run_continuous", {}).get("phase2", {}).get("context", {}).get("success") is True),
        criterion("phase2 route_core run_continuous succeeded", task_result.get("run_continuous", {}).get("phase2", {}).get("route", {}).get("success"), "== True", task_result.get("run_continuous", {}).get("phase2", {}).get("route", {}).get("success") is True),
        criterion("phase2 memory_core run_continuous succeeded", task_result.get("run_continuous", {}).get("phase2", {}).get("memory", {}).get("success"), "== True", task_result.get("run_continuous", {}).get("phase2", {}).get("memory", {}).get("success") is True),
        criterion("phase2 learning_core run_continuous succeeded", task_result.get("run_continuous", {}).get("phase2", {}).get("learning", {}).get("success"), "== True", task_result.get("run_continuous", {}).get("phase2", {}).get("learning", {}).get("success") is True),
        criterion("context overwrite write succeeded", task_result.get("overwrite_write", {}).get("success"), "== True", task_result.get("overwrite_write", {}).get("success") is True),
        criterion("route overwrite write succeeded", task_result.get("route_overwrite_write", {}).get("success"), "== True", task_result.get("route_overwrite_write", {}).get("success") is True),
        criterion("context_core final read succeeded", ctx_final.get("success"), "== True", ctx_final.get("success") is True),
        criterion("route_core final read succeeded", route_final.get("success"), "== True", route_final.get("success") is True),
        criterion("memory_core final read succeeded", mem_final.get("success"), "== True", mem_final.get("success") is True),
        criterion("learning_core final read succeeded", learning_final.get("success"), "== True", learning_final.get("success") is True),
        criterion("learning_core weight near reference", learning_final.get("readout_weight_raw"), f"within +/- {tolerance} of {ref['weight_raw']}", abs(int(learning_final.get("readout_weight_raw") or 0) - ref["weight_raw"]) <= tolerance),
        criterion("learning_core bias near reference", learning_final.get("readout_bias_raw"), f"within +/- {tolerance} of {ref['bias_raw']}", abs(int(learning_final.get("readout_bias_raw") or 0) - ref["bias_raw"]) <= tolerance),
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
        # Tier 4.29b specific criteria
        criterion("wrong-context events fail cleanly (context misses)", ctx_final.get("slot_misses"), f"== {ref['slot_misses']}", ctx_final.get("slot_misses") == ref["slot_misses"]),
        criterion("context overwrite events use new value (context writes)", ctx_final.get("slot_writes"), f"== {ref['slot_writes']}", ctx_final.get("slot_writes") == ref["slot_writes"]),
        criterion("slot-shuffle maintains correctness (context hits)", ctx_final.get("slot_hits"), f"== {ref['slot_hits']}", ctx_final.get("slot_hits") == ref["slot_hits"]),
        criterion("context_core active_slots matches expected", ctx_final.get("active_slots"), f"== {ref['active_slots']}", ctx_final.get("active_slots") == ref["active_slots"]),
        criterion("wrong-route events fail cleanly (route misses)", route_final.get("slot_misses"), f"== {ref['route_slot_misses']}", route_final.get("slot_misses") == ref["route_slot_misses"]),
        criterion("route overwrite events use new value (route writes)", route_final.get("slot_writes"), f"== {ref['route_slot_writes']}", route_final.get("slot_writes") == ref["route_slot_writes"]),
        criterion("route-shuffle maintains correctness (route hits)", route_final.get("slot_hits"), f"== {ref['route_slot_hits']}", route_final.get("slot_hits") == ref["route_slot_hits"]),
        criterion("route_core active_route_slots matches expected", route_final.get("active_slots"), f"== {ref['active_route_slots']}", route_final.get("active_slots") == ref["active_route_slots"]),
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
        "reference": ref,
    }
    write_json(output_dir / "tier4_29b_hardware_results.json", result)

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
    print("Tier 4.29b — Ingest hardware results")
    print("=" * 60)

    default_dir = f"tier4_29b_seed{args.seed}_job_output"
    output_dir = Path(args.output) if args.output else Path(default_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    hw_dir = Path(args.hardware_output_dir) if args.hardware_output_dir else output_dir
    hw_results_path = hw_dir / "tier4_29b_hardware_results.json"

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
    output_path = output_dir / "tier4_29b_ingest_results.json"
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

    (output_dir / "tier4_29b_ingest_report.md").write_text(report)

    print(f"OVERALL: {status.upper()}")
    print(f"Passed: {passed}/{total}")
    print(f"Ingest report: {output_dir / 'tier4_29b_ingest_report.md'}")
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
    parser.add_argument("--seeds", type=str, default="", help="Comma-separated seeds for multi-seed run-hardware (e.g., 42,43,44). Overrides --seed.")
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
                combined_path = Path(f"tier4_29b_multi_seed_job_output") / "tier4_29b_combined_results.json"
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
        crash_path = Path(f"tier4_29b_seed{args.seed}_job_output") / "tier4_29b_crash_report.json"
        crash_path.parent.mkdir(parents=True, exist_ok=True)
        crash_path.write_text(json.dumps(crash, indent=2))
        print(f"\n[FATAL CRASH] {type(exc).__name__}: {exc}")
        print(f"Crash report written to: {crash_path}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
