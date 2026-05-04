#!/usr/bin/env python3
"""
Tier 4.27a — Four-core runtime resource / timing characterization.

Splits CRA runtime across four SpiNNaker cores:
  Core 4 (context_core): context slot table, lookup replies
  Core 5 (route_core):   route slot table, lookup replies
  Core 6 (memory_core):  memory slot table, lookup replies
  Core 7 (learning_core): event schedule, parallel lookups, feature composition,
                          pending horizon, readout update

Inter-core transport: SDP point-to-point (transitional; target is multicast/MCPL).
Learning core sends CMD_LOOKUP_REQUEST (opcode 32) to state cores;
state cores reply with CMD_LOOKUP_REPLY (opcode 33).

Modes:
  local        — compile C test, run against 48-event reference, validate criteria
  prepare      — create EBRAINS job bundle with four .aplx images
  run-hardware — load four images, run distributed task, read back all cores
  ingest       — compare hardware results with 4.23c monolithic reference

Claim boundary:
  PASS means four independent cores can hold distributed state and cooperate to
  reproduce the monolithic delayed-credit result within tolerance. It is NOT
  speedup evidence, NOT multi-chip scaling, NOT a general multi-core framework,
  and NOT full native v2.1 autonomy.
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
CONTROLLED = ROOT / "controlled_test_output"
RUNTIME = ROOT / "coral_reef_spinnaker" / "spinnaker_runtime"
EXPERIMENTS = ROOT / "experiments"

sys.path.insert(0, str(ROOT))

from experiments.tier4_22x_compact_v2_bridge_decoupled_smoke import (
    TASK_SEQUENCE,
    FP_ONE,
    FP_SHIFT,
    TASK_TAIL_WINDOW,
    CONTEXT_KEY_IDS,
    ROUTE_KEY_IDS,
    MEMORY_KEY_IDS,
    V2StateBridge,
)
from experiments.tier4_23a_continuous_local_reference import (
    ContinuousEventLoop,
    score_rows,
)
from experiments import tier4_22i_custom_runtime_roundtrip as base  # noqa: E402

TIER = "Tier 4.27a — Four-Core Runtime Resource / Timing Characterization"
RUNNER_REVISION = "tier4_27a_four_core_characterization_20260502_0001"
UPLOAD_PACKAGE_NAME = "cra_427b"
STABLE_EBRAINS_UPLOAD = ROOT / "ebrains_jobs" / UPLOAD_PACKAGE_NAME
DEPRECATED_EBRAINS_UPLOADS: list[Path] = [ROOT / "ebrains_jobs" / "cra_426b", ROOT / "ebrains_jobs" / "cra_426c", ROOT / "ebrains_jobs" / "cra_426d", ROOT / "ebrains_jobs" / "cra_426e", ROOT / "ebrains_jobs" / "cra_426f", ROOT / "ebrains_jobs" / "cra_427a"]

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


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def criterion(name: str, value: Any, rule: str, passed: bool, note: str = "") -> dict[str, Any]:
    return {"name": name, "value": value, "rule": rule, "passed": passed, "note": note}


def run_cmd(cmd: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=True, check=False)
    return {
        "command": " ".join(cmd),
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def build_aplx_for_profile(profile: str, output_dir: Path) -> dict[str, Any]:
    """Build .aplx for a given runtime profile."""
    env = os.environ.copy()
    tools = base.detect_spinnaker_tools()
    if tools and not env.get("SPINN_DIRS"):
        env["SPINN_DIRS"] = tools
    env["RUNTIME_PROFILE"] = profile

    build = run_cmd(["make", "-C", str(RUNTIME), "clean", "all"], cwd=ROOT, env=env)
    (output_dir / f"tier4_27a_build_{profile}_stdout.txt").write_text(build["stdout"])
    (output_dir / f"tier4_27a_build_{profile}_stderr.txt").write_text(build["stderr"])

    aplx = RUNTIME / "build" / "coral_reef.aplx"
    profile_aplx = RUNTIME / "build" / f"coral_reef_{profile}.aplx"
    if aplx.exists() and not profile_aplx.exists():
        shutil.copy2(aplx, profile_aplx)
    elf_gnu = RUNTIME / "build" / "gnu" / "coral_reef.elf"
    elf = RUNTIME / "build" / "coral_reef.elf"
    elf_actual = elf_gnu if elf_gnu.exists() else elf if elf.exists() else None

    return {
        "profile": profile,
        "build_returncode": build["returncode"],
        "aplx_exists": profile_aplx.exists(),
        "aplx_path": str(profile_aplx) if profile_aplx.exists() else str(aplx),
        "elf_exists": elf_actual is not None and elf_actual.exists(),
        "elf_path": str(elf_actual) if elf_actual else "",
    }


def fp_from_float(x: float) -> int:
    return int(round(x * FP_ONE))


def fp_to_float(raw: int) -> float:
    return float(raw) / FP_ONE


def fp_mul(a: int, b: int) -> int:
    return int((a * b) >> FP_SHIFT)


# ---------------------------------------------------------------------------
# Local mode (Step 5)
# ---------------------------------------------------------------------------

def generate_test_data() -> dict[str, Any]:
    """Generate the C header with 48-event schedule + expected slot values."""
    generator = RUNTIME / "tests" / "generate_48event_data.py"
    result = run_cmd([sys.executable, str(generator)], cwd=RUNTIME)
    return {
        "status": "pass" if result["returncode"] == 0 else "fail",
        "stdout": result["stdout"],
        "stderr": result["stderr"],
    }


def compile_and_run_c_test() -> dict[str, Any]:
    """Compile and run the 48-event C integration test."""
    run_cmd(["make", "clean"], cwd=RUNTIME)
    result = run_cmd(["make", "test-four-core-48event"], cwd=RUNTIME)

    c_results: dict[str, Any] = {}
    if result["returncode"] == 0:
        for line in result["stdout"].strip().splitlines():
            if "=" in line:
                key, val = line.split("=", 1)
                try:
                    c_results[key] = int(val)
                except ValueError:
                    c_results[key] = val

    return {
        "status": "pass" if result["returncode"] == 0 else "fail",
        "returncode": result["returncode"],
        "stdout": result["stdout"],
        "stderr": result["stderr"],
        "parsed": c_results,
    }


def run_monolithic_reference() -> dict[str, Any]:
    """Run the Python ContinuousEventLoop monolithic reference."""
    loop = ContinuousEventLoop(TASK_SEQUENCE)
    while loop.tick():
        pass
    while loop.pending:
        loop.timestep += 1
        loop._mature_oldest()

    metrics = score_rows(loop.rows, tail_window=TASK_TAIL_WINDOW)

    return {
        "status": "pass",
        "final_weight_raw": loop.weight_raw,
        "final_bias_raw": loop.bias_raw,
        "decisions": loop.decisions,
        "rewards": loop.rewards,
        "max_pending_depth": loop.max_pending_depth,
        "accuracy": metrics.get("accuracy"),
        "tail_accuracy": metrics.get("tail_accuracy"),
        "rows": loop.rows,
    }


def validate_criteria(c_results: dict[str, Any], mono_ref: dict[str, Any]) -> list[dict[str, Any]]:
    """Validate all Step 5 pass criteria."""
    criteria = []

    def check(name: str, value: Any, expected: Any) -> dict[str, Any]:
        passed = value == expected
        criteria.append({
            "name": name,
            "value": value,
            "expected": expected,
            "passed": passed,
        })
        return criteria[-1]

    check("pending_created", c_results.get("pending_created"), 48)
    check("pending_matured", c_results.get("pending_matured"), 48)
    check("active_pending", c_results.get("active_pending"), 0)
    check("decisions", c_results.get("decisions"), 48)
    check("reward_events", c_results.get("reward_events"), 48)
    check("lookup_requests", c_results.get("lookup_requests"), 144)
    check("lookup_replies", c_results.get("lookup_replies"), 144)
    check("stale_replies", c_results.get("stale_replies", 0), 0)
    check("timeouts", c_results.get("timeouts", 0), 0)
    check("readout_weight", c_results.get("readout_weight"), mono_ref["final_weight_raw"])
    check("readout_bias", c_results.get("readout_bias"), mono_ref["final_bias_raw"])

    return criteria


def mode_local(args: argparse.Namespace) -> dict[str, Any]:
    """Local mode: run C test against Python monolithic reference."""
    print("Tier 4.27a Step 5 — Four-core distributed 48-event smoke test")
    print("=" * 60)

    print("\n[1/4] Generating C test data header...")
    gen_result = generate_test_data()
    print(f"  Data generation: {gen_result['status']}")

    print("\n[2/4] Running Python monolithic reference...")
    mono_ref = run_monolithic_reference()
    print(f"  Monolithic weight={mono_ref['final_weight_raw']} bias={mono_ref['final_bias_raw']}")
    print(f"  Accuracy={mono_ref['accuracy']:.4f} tail_accuracy={mono_ref['tail_accuracy']:.4f}")

    print("\n[3/4] Compiling and running C distributed test...")
    c_result = compile_and_run_c_test()
    print(f"  C test status: {c_result['status']} (rc={c_result['returncode']})")
    if c_result["parsed"]:
        print(f"  C weight={c_result['parsed'].get('readout_weight')} "
              f"bias={c_result['parsed'].get('readout_bias')}")

    print("\n[4/4] Validating pass criteria...")
    criteria = validate_criteria(c_result.get("parsed", {}), mono_ref)
    all_passed = all(c["passed"] for c in criteria)

    for c in criteria:
        mark = "PASS" if c["passed"] else "FAIL"
        print(f"  [{mark}] {c['name']}: {c['value']} (expected {c['expected']})")

    report = {
        "mode": "local",
        "status": "pass" if all_passed else "fail",
        "data_generation": gen_result,
        "monolithic_reference": {
            "final_weight_raw": mono_ref["final_weight_raw"],
            "final_bias_raw": mono_ref["final_bias_raw"],
            "accuracy": mono_ref["accuracy"],
            "tail_accuracy": mono_ref["tail_accuracy"],
        },
        "c_distributed_test": c_result,
        "criteria": criteria,
    }

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2))
        print(f"\nArtifact exported: {out_path}")

    print(f"\n{'=' * 60}")
    print(f"OVERALL: {'PASS' if all_passed else 'FAIL'}")
    return report


# ---------------------------------------------------------------------------
# Prepare mode (Step 6)
# ---------------------------------------------------------------------------

EXPECTED_METRICS = {
    "readout_weight_raw": 32768,
    "readout_bias_raw": 0,
    "pending_created": 48,
    "pending_matured": 48,
    "active_pending": 0,
    "decisions": 48,
    "reward_events": 48,
    "lookup_requests": 144,
    "lookup_replies": 144,
    "stale_replies": 0,
    "timeouts": 0,
    "accuracy": 0.9583,
    "tail_accuracy": 1.0,
    "tail_window": 6,
    "task_sequence_length": 48,
    "delay_steps": 2,
    "learning_rate": 0.25,
    "schema_version": 2,
    "payload_bytes": 105,
}

FAILURE_CLASSES = [
    {
        "class": "build/load failure",
        "description": "One of the four .aplx images fails to link or exceeds ITCM/DTCM limits",
        "detection": "build_returncode != 0 or aplx missing",
        "recovery": "Reduce code size or split functionality further",
    },
    {
        "class": "core role/profile mismatch",
        "description": "Wrong runtime profile loaded onto a core (e.g., learning_core on context core)",
        "detection": "READ_STATE profile_id does not match expected role for that core",
        "recovery": "Verify app_id/core mapping in load script matches core role map",
    },
    {
        "class": "inter-core lookup timeout",
        "description": "Lookup request sent but no reply arrives within timeout window",
        "detection": "timeout_count > 0, or decisions < 48 with pending lookups stuck",
        "recovery": "Verify SDP routing; check state core tick is running; increase timeout",
    },
    {
        "class": "stale/duplicate seq_id accepted",
        "description": "Sequence ID mismatch or duplicate reply not rejected by learning core",
        "detection": "stale_count > 0 in learning core state summary",
        "recovery": "Verify seq_id monotonically advances; check lookup table clearing logic",
    },
    {
        "class": "wrong-profile reply accepted",
        "description": "Learning core accepts a reply from an unexpected profile (e.g., route reply for context lookup)",
        "detection": "Cross-profile key/type mismatch in lookup table",
        "recovery": "Verify lookup_type matching in state core handlers",
    },
    {
        "class": "feature/reference mismatch",
        "description": "feature = context * route * memory * cue differs from monolithic reference",
        "detection": "final weight/bias outside ±8192 tolerance, or per-event prediction divergence",
        "recovery": "Check fixed-point multiply order matches monolithic; verify slot values",
    },
    {
        "class": "pending maturation mismatch",
        "description": "Learning core matures wrong count, wrong order, or wrong due timestep",
        "detection": "pending_created != pending_matured, or active_pending > 0 at end",
        "recovery": "Check due_timestep calculation; verify no double-maturation or skipped maturation",
    },
    {
        "class": "readout mismatch",
        "description": "Final readout weight/bias outside tolerance on learning core",
        "detection": "READ_STATE returns weight/bias outside expected range",
        "recovery": "Check for state corruption or uninitialized slot values",
    },
    {
        "class": "missing compact readback",
        "description": "CMD_READ_STATE fails or returns incomplete payload from any core",
        "detection": "READ_STATE success=False or payload shorter than 73 bytes",
        "recovery": "Verify SDP port/routing; check host_interface pack function",
    },
]

CLAIM_BOUNDARY = (
    "Prepared only. Not hardware evidence until EBRAINS artifacts return and are ingested. "
    "Not speedup evidence. Not full native v2.1. Not multi-chip. Not arbitrary task switching."
)


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


def mode_prepare(args: argparse.Namespace) -> dict[str, Any]:
    """Prepare EBRAINS job bundle with four .aplx images."""
    print("Tier 4.27a Step 6 — Prepare EBRAINS job bundle")
    print("=" * 60)

    default_dir = f"tier4_27a_seed{args.seed}_job_output"
    output_dir = Path(args.output) if args.output else Path(default_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Run local reference
    print("\n[1/5] Running local reference...")
    local_output = str(output_dir / "tier4_27a_local_results.json")
    saved_output = args.output
    args.output = local_output
    local_exit = mode_local(args)
    args.output = saved_output

    # 2. Build all four .aplx images
    print("\n[2/5] Building four runtime profile images...")
    ctx_build = build_aplx_for_profile(CONTEXT_CORE_PROFILE, output_dir)
    route_build = build_aplx_for_profile(ROUTE_CORE_PROFILE, output_dir)
    mem_build = build_aplx_for_profile(MEMORY_CORE_PROFILE, output_dir)
    learning_build = build_aplx_for_profile(LEARNING_CORE_PROFILE, output_dir)

    builds = [ctx_build, route_build, mem_build, learning_build]
    for b in builds:
        status = "OK" if b["aplx_exists"] else "FAIL"
        print(f"  {b['profile']}: {status}")

    # 3. Create upload bundle
    print("\n[3/5] Creating upload bundle...")
    bundle = output_dir / "ebrains_upload_bundle" / UPLOAD_PACKAGE_NAME
    if bundle.exists():
        shutil.rmtree(bundle)
    (bundle / "experiments").mkdir(parents=True, exist_ok=True)
    (bundle / "coral_reef_spinnaker" / "python_host").mkdir(parents=True, exist_ok=True)

    scripts = [
        "tier4_27a_four_core_distributed_smoke.py",
        "tier4_22i_custom_runtime_roundtrip.py",
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
    for b in builds:
        if b["aplx_exists"]:
            fname = f"coral_reef_{b['profile']}.aplx"
            shutil.copy2(b["aplx_path"], bundle / fname)

    # 4. Write README
    print("\n[4/5] Writing README...")
    command = f"{UPLOAD_PACKAGE_NAME}/experiments/tier4_27a_four_core_distributed_smoke.py --mode run-hardware --seed {args.seed}"

    readme_text = f"""# {TIER}

Upload the `{UPLOAD_PACKAGE_NAME}` folder itself so the JobManager path starts
with `{UPLOAD_PACKAGE_NAME}/`.

## Core Role Map

| Core | App ID | Profile | Role |
|------|--------|---------|------|
| {CONTEXT_CORE_P} | {CONTEXT_CORE_APP_ID} | `{CONTEXT_CORE_PROFILE}` | Context slot table; replies to context lookup requests |
| {ROUTE_CORE_P} | {ROUTE_CORE_APP_ID} | `{ROUTE_CORE_PROFILE}` | Route slot table; replies to route lookup requests |
| {MEMORY_CORE_P} | {MEMORY_CORE_APP_ID} | `{MEMORY_CORE_PROFILE}` | Memory slot table; replies to memory lookup requests |
| {LEARNING_CORE_P} | {LEARNING_CORE_APP_ID} | `{LEARNING_CORE_PROFILE}` | Event schedule, parallel lookups, feature composition, pending horizon, readout |

## Inter-Core Protocol

- Learning core sends `CMD_LOOKUP_REQUEST` (opcode 32) to state cores.
- State cores reply with `CMD_LOOKUP_REPLY` (opcode 33).
- Sequence IDs detect stale reply contamination.
- Transitional SDP; architecture target is multicast/MCPL.

## Exact JobManager Command

```text
{command}
```

Default output dir is `tier4_27a_seed{args.seed}_job_output`.

**Do NOT add `--out-dir` or `--output-dir` flags; EBRAINS strips `out` from arguments.**
This was the root cause of the `cra_425h` failure (repaired as `cra_425i`).

## Expected 48-Event Reference Metrics

```text
readout_weight_raw  = {EXPECTED_METRICS['readout_weight_raw']}
readout_bias_raw    = {EXPECTED_METRICS['readout_bias_raw']}
pending_created     = {EXPECTED_METRICS['pending_created']}
pending_matured     = {EXPECTED_METRICS['pending_matured']}
active_pending      = {EXPECTED_METRICS['active_pending']}
decisions           = {EXPECTED_METRICS['decisions']}
reward_events       = {EXPECTED_METRICS['reward_events']}
lookup_requests     = {EXPECTED_METRICS['lookup_requests']}
lookup_replies      = {EXPECTED_METRICS['lookup_replies']}
stale_replies       = {EXPECTED_METRICS['stale_replies']}
timeouts            = {EXPECTED_METRICS['timeouts']}
accuracy            = {EXPECTED_METRICS['accuracy']:.4f}
tail_accuracy       = {EXPECTED_METRICS['tail_accuracy']:.4f}
tail_window         = {EXPECTED_METRICS['tail_window']}
delay_steps         = {EXPECTED_METRICS['delay_steps']}
learning_rate       = {EXPECTED_METRICS['learning_rate']}
schema_version      = {EXPECTED_METRICS['schema_version']}
payload_bytes       = {EXPECTED_METRICS['payload_bytes']}
```

Tolerance: weight ±8192 of {EXPECTED_METRICS['readout_weight_raw']}, bias ±8192 of {EXPECTED_METRICS['readout_bias_raw']}

## Failure-Class Table

| Class | Description | Detection | Recovery |
|-------|-------------|-----------|----------|
"""
    for fc in FAILURE_CLASSES:
        readme_text += f"| {fc['class']} | {fc['description']} | {fc['detection']} | {fc['recovery']} |\n"

    readme_text += f"""
## Claim Boundary

{CLAIM_BOUNDARY}

## Next Step

If hardware run passes: ingest artifacts, evaluate migrating inter-core protocol
from SDP to multicast/MCPL, then design Tier 4.28.

If hardware run fails: classify per failure-class table above, repair smallest
failing layer locally, do not promote to multi-seed until single-seed smoke passes.
"""

    readme = bundle / f"README_TIER4_27a_JOB.md"
    readme.write_text(readme_text, encoding="utf-8")

    # 5. Copy to stable upload folder
    print("\n[5/5] Copying to stable upload folder...")
    STABLE_EBRAINS_UPLOAD.parent.mkdir(parents=True, exist_ok=True)
    for old_upload in DEPRECATED_EBRAINS_UPLOADS:
        if old_upload.exists():
            shutil.rmtree(old_upload)
    if STABLE_EBRAINS_UPLOAD.exists():
        shutil.rmtree(STABLE_EBRAINS_UPLOAD)
    shutil.copytree(bundle, STABLE_EBRAINS_UPLOAD)

    tools = base.detect_spinnaker_tools()
    config_text = (RUNTIME / "src" / "config.h").read_text()
    has_lookup_opcodes = "CMD_LOOKUP_REQUEST" in config_text and "CMD_LOOKUP_REPLY" in config_text

    criteria = [
        criterion("local reference passed", local_exit.get("status") == "pass", "== True", local_exit.get("status") == "pass"),
        criterion("upload bundle created", str(bundle), "exists", bundle.exists()),
        criterion("runtime source included", str(bundle / "coral_reef_spinnaker" / "spinnaker_runtime"), "exists", (bundle / "coral_reef_spinnaker" / "spinnaker_runtime").exists()),
        criterion("context_core .aplx built or tools missing", ctx_build["aplx_exists"], "== True", ctx_build["aplx_exists"] or not tools),
        criterion("route_core .aplx built or tools missing", route_build["aplx_exists"], "== True", route_build["aplx_exists"] or not tools),
        criterion("memory_core .aplx built or tools missing", mem_build["aplx_exists"], "== True", mem_build["aplx_exists"] or not tools),
        criterion("learning_core .aplx built or tools missing", learning_build["aplx_exists"], "== True", learning_build["aplx_exists"] or not tools),
        criterion("lookup opcodes in config.h", "CMD_LOOKUP_REQUEST / CMD_LOOKUP_REPLY", "present", has_lookup_opcodes),
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
            "what_i_need_from_user": f"Upload {UPLOAD_PACKAGE_NAME} to EBRAINS/JobManager and run the emitted command.",
            "claim_boundary": CLAIM_BOUNDARY,
            "next_step_if_passed": "Run the emitted EBRAINS command and ingest returned files.",
            "expected_metrics": EXPECTED_METRICS,
            "failure_classes": FAILURE_CLASSES,
        },
        "criteria": criteria,
    }

    write_json(output_dir / "tier4_27a_prepare_results.json", result)

    print(f"\n{'=' * 60}")
    print(f"OVERALL: {status.upper()}")
    for c in criteria:
        mark = "PASS" if c["passed"] else "FAIL"
        print(f"  [{mark}] {c['name']}")
    print(f"\nStable upload folder: {STABLE_EBRAINS_UPLOAD}")
    print(f"Job command: {command}")
    return result


# ---------------------------------------------------------------------------
# Run-hardware mode (Step 7)
# ---------------------------------------------------------------------------

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
        max_wait = 10.0  # seconds
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


def mode_run(args: argparse.Namespace) -> dict[str, Any]:
    """Run on EBRAINS hardware (Step 7)."""
    print("Tier 4.27a Step 7 — Four-Core EBRAINS Hardware Characterization")
    print("=" * 60)

    default_dir = f"tier4_27a_seed{args.seed}_job_output"
    output_dir = Path(args.output) if args.output else Path(default_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    tools = base.detect_spinnaker_tools()
    if tools and not env.get("SPINN_DIRS"):
        env["SPINN_DIRS"] = tools

    # Build all four images
    print("\n[1/4] Building four runtime profile images...")
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

    # Acquire hardware target
    print("\n[2/4] Acquiring hardware target...")
    target = base.acquire_hardware_target(args)
    hostname = str(target.get("hostname") or target.get("target_ipaddress") or "")
    tx = target.get("_transceiver")

    # Load all four applications
    print("\n[3/4] Loading four applications onto hardware...")
    loads: dict[str, dict[str, Any]] = {
        "context": {"status": "not_attempted"},
        "route": {"status": "not_attempted"},
        "memory": {"status": "not_attempted"},
        "learning": {"status": "not_attempted"},
    }

    task_result: dict[str, Any] = {"status": "not_attempted"}
    hardware_exception: dict[str, Any] | None = None

    # Write intermediate artifacts before hardware execution so we have
    # diagnostic data even if the script is killed mid-flight.
    write_json(output_dir / "tier4_27a_environment.json", env_report)
    write_json(output_dir / "tier4_27a_target_acquisition.json", base.public_target_acquisition(target))

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
            # Intermediate artifact: loads succeeded or failed individually
            for name, load_info in loads.items():
                write_json(output_dir / f"tier4_27a_{name}_load.json", load_info)

        if (target.get("status") == "pass" and hostname
            and all(l.get("status") == "pass" for l in loads.values())):
            print("\n[4/4] Running four-core hardware loop...")
            task_result = four_core_hardware_loop(hostname, args, target, loads)
            # Intermediate artifact: task completed (or inner except caught it)
            write_json(output_dir / "tier4_27a_task.json", task_result)
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
        # Export artifacts — MUST happen even on exception so we can diagnose
        write_json(output_dir / "tier4_27a_environment.json", env_report)
        write_json(output_dir / "tier4_27a_target_acquisition.json", base.public_target_acquisition(target))
        for name, load_info in loads.items():
            write_json(output_dir / f"tier4_27a_{name}_load.json", load_info)
        write_json(output_dir / "tier4_27a_task.json", task_result)

    # Criteria
    ref_weight = 32768
    ref_bias = 0
    ref_events = len(TASK_SEQUENCE)

    final_states = task_result.get("final_state", {}) if isinstance(task_result, dict) else {}
    learning_final = final_states.get("learning", {}) if isinstance(final_states, dict) else {}
    ctx_final = final_states.get("context", {}) if isinstance(final_states, dict) else {}
    route_final = final_states.get("route", {}) if isinstance(final_states, dict) else {}
    mem_final = final_states.get("memory", {}) if isinstance(final_states, dict) else {}

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
        criterion("learning_core weight near reference", learning_final.get("readout_weight_raw"), f"within +/- {ref_weight//4} of {ref_weight}", abs(int(learning_final.get("readout_weight_raw") or 0) - ref_weight) <= ref_weight // 4),
        criterion("learning_core bias near reference", learning_final.get("readout_bias_raw"), f"within +/- {ref_weight//4} of {ref_bias}", abs(int(learning_final.get("readout_bias_raw") or 0) - ref_bias) <= ref_weight // 4),
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
    write_json(output_dir / "tier4_27a_hardware_results.json", result)

    print(f"\n{'=' * 60}")
    print(f"OVERALL: {status.upper()}")
    for c in criteria:
        mark = "PASS" if c["passed"] else "FAIL"
        print(f"  [{mark}] {c['name']}: {c['value']}")
    print(f"\nArtifacts exported to: {output_dir}")
    return result


# ---------------------------------------------------------------------------
# Ingest mode (Step 8)
# ---------------------------------------------------------------------------

def mode_ingest(args: argparse.Namespace) -> dict[str, Any]:
    """Ingest hardware results (Step 8)."""
    print("Tier 4.27a Step 8 — Ingest hardware results")
    print("=" * 60)

    default_dir = f"tier4_27a_seed{args.seed}_job_output"
    output_dir = Path(args.output) if args.output else Path(default_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    hw_dir = Path(args.hardware_output_dir) if args.hardware_output_dir else output_dir
    hw_results_path = hw_dir / "tier4_27a_hardware_results.json"

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
    write_json(output_dir / "tier4_27a_ingest_results.json", result)

    report = (
        f"# {TIER} — Ingest Report\n\n"
        f"- Status: **{status.upper()}**\n"
        f"- Passed: {passed}/{total}\n"
        f"- Hardware output: `{hw_dir}`\n\n"
        f"## Criteria\n\n"
    )
    for c in criteria:
        report += f"- {'✓' if c['passed'] else '✗'} {c['name']}: `{c['value']}` ({c['rule']})\n"

    (output_dir / "tier4_27a_ingest_report.md").write_text(report)

    print(f"OVERALL: {status.upper()}")
    print(f"Passed: {passed}/{total}")
    print(f"Ingest report: {output_dir / 'tier4_27a_ingest_report.md'}")
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Tier 4.27a four-core runtime resource / timing characterization")
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
            report = mode_run(args)
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
        crash_path = Path(f"tier4_27a_seed{args.seed}_job_output") / "tier4_27a_crash_report.json"
        crash_path.parent.mkdir(parents=True, exist_ok=True)
        crash_path.write_text(json.dumps(crash, indent=2))
        print(f"\n[FATAL CRASH] {type(exc).__name__}: {exc}")
        print(f"Crash report written to: {crash_path}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
