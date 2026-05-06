#!/usr/bin/env python3
"""Tier 4.30f lifecycle sham-control hardware subset.

Tier 4.30e proved that the five-profile lifecycle runtime can execute canonical
lifecycle schedules on real SpiNNaker hardware. Tier 4.30f asks the next
reviewer-defense question: do compact lifecycle sham controls produce the
expected separations on the lifecycle core, rather than merely toggling a flag?

Claim boundary:
- PREPARED means only the EBRAINS upload bundle and command are ready.
- PASS in run-hardware means the selected sham-control subset executed on a
  real SpiNNaker target with five profile builds/loads, compact readback,
  expected enabled/control separations, and zero synthetic fallback.
- This is not lifecycle task-benefit evidence, not full Tier 6.3 hardware,
  not speedup evidence, not multi-chip scaling, and not a lifecycle baseline
  freeze.
"""

from __future__ import annotations

import argparse
import csv
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


ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"
RUNTIME = ROOT / "coral_reef_spinnaker" / "spinnaker_runtime"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments import tier4_22i_custom_runtime_roundtrip as base  # noqa: E402
from experiments.tier4_30a_static_pool_lifecycle_reference import (  # noqa: E402
    LifecycleEvent,
    generate_schedule,
    run_schedule,
)
from experiments.tier4_30b_lifecycle_hardware_smoke import lifecycle_event_payload  # noqa: E402


TIER = "Tier 4.30f - Lifecycle Sham-Control Hardware Subset"
RUNNER_REVISION = "tier4_30f_lifecycle_sham_hardware_subset_20260505_0001"
UPLOAD_PACKAGE_NAME = "cra_430f"
STABLE_EBRAINS_UPLOAD = ROOT / "ebrains_jobs" / UPLOAD_PACKAGE_NAME
DEFAULT_PREPARE_OUTPUT = CONTROLLED / "tier4_30f_hw_20260505_prepared"
DEFAULT_RUN_OUTPUT = CONTROLLED / f"tier4_30f_hw_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_run_hardware"

FP_ONE = 1 << 15
SCENARIO_NAME = "canonical_32"
SCENARIO_EVENT_COUNT = 32

CORE_ROLES: dict[str, dict[str, Any]] = {
    "context": {"profile": "context_core", "profile_id": 4, "core": 4, "app_id": 1},
    "route": {"profile": "route_core", "profile_id": 5, "core": 5, "app_id": 2},
    "memory": {"profile": "memory_core", "profile_id": 6, "core": 6, "app_id": 3},
    "learning": {"profile": "learning_core", "profile_id": 3, "core": 7, "app_id": 4},
    "lifecycle": {"profile": "lifecycle_core", "profile_id": 7, "core": 8, "app_id": 5},
}

SHAM_MODE_IDS = {
    "enabled": 0,
    "fixed_static_pool_control": 1,
    "random_event_replay_control": 2,
    "active_mask_shuffle_control": 3,
    "no_trophic_pressure_control": 5,
    "no_dopamine_or_plasticity_control": 6,
}

SHAM_MODE_ORDER = [
    "enabled",
    "fixed_static_pool_control",
    "random_event_replay_control",
    "active_mask_shuffle_control",
    "no_trophic_pressure_control",
    "no_dopamine_or_plasticity_control",
]

SEPARATION_FIELDS = {
    "fixed_static_pool_control": "active_mask_bits",
    "random_event_replay_control": "lineage_checksum",
    "active_mask_shuffle_control": "active_mask_bits",
    "no_trophic_pressure_control": "trophic_checksum",
    "no_dopamine_or_plasticity_control": "trophic_checksum",
}


# ---------------------------------------------------------------------------
# Small IO helpers
# ---------------------------------------------------------------------------


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    return value


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    keys: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def criterion(name: str, value: Any, rule: str, passed: bool, note: str = "") -> dict[str, Any]:
    return {"name": name, "value": json_safe(value), "rule": rule, "passed": bool(passed), "note": note}


def run_cmd(command: list[str], *, cwd: Path = ROOT, env: dict[str, str] | None = None) -> dict[str, Any]:
    completed = subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True, check=False)
    return {
        "command": " ".join(command),
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


# ---------------------------------------------------------------------------
# References and expected hardware summaries
# ---------------------------------------------------------------------------


def _schedule_for_mode(schedule: list[LifecycleEvent], mode: str) -> list[LifecycleEvent]:
    if mode != "random_event_replay_control":
        return list(schedule)
    events = list(schedule)
    rng = random.Random(4242)
    rng.shuffle(events)
    return [
        LifecycleEvent(
            event_index=index,
            event_type=event.event_type,
            target_slot=event.target_slot,
            parent_slot=event.parent_slot,
            child_slot=event.child_slot,
            trophic_delta_raw=event.trophic_delta_raw,
            reward_raw=event.reward_raw,
        )
        for index, event in enumerate(events)
    ]


def _accepted_rows(state: Any, event_type: str | None = None) -> list[dict[str, Any]]:
    rows = [row for row in state.rows if int(row.get("accepted", 0)) == 1]
    if event_type is not None:
        rows = [row for row in rows if row.get("event_type") == event_type]
    return rows


def control_reference(mode: str, event_count: int = SCENARIO_EVENT_COUNT) -> dict[str, Any]:
    schedule = generate_schedule(event_count)
    state = run_schedule(f"tier4_30f_{mode}", schedule, mode=mode)
    summary = state.summary()
    accepted_count = summary["event_count"] - summary["invalid_event_count"]
    expected = {
        "schema_version": 1,
        "sham_mode": SHAM_MODE_IDS[mode],
        "pool_size": 8,
        "founder_count": 2,
        "active_count": summary["active_count"],
        "inactive_count": summary["inactive_count"],
        "active_mask_bits": summary["active_mask_bits"],
        "attempted_event_count": summary["attempted_event_count"],
        "lifecycle_event_count": accepted_count,
        "cleavage_count": summary["cleavage_count"],
        "adult_birth_count": summary["birth_count"],
        "death_count": summary["death_count"],
        "maturity_count": len(_accepted_rows(state, "maturity_handoff")),
        "trophic_update_count": len(_accepted_rows(state, "trophic_update")),
        "invalid_event_count": summary["invalid_event_count"],
        "lineage_checksum": summary["lineage_checksum"],
        "trophic_checksum": summary["trophic_checksum"],
        "payload_len": 68,
    }
    return {
        "mode": mode,
        "event_count": event_count,
        "schedule": _schedule_for_mode(schedule, mode),
        "reference_summary": summary,
        "expected": expected,
    }


def all_references() -> dict[str, dict[str, Any]]:
    return {mode: control_reference(mode) for mode in SHAM_MODE_ORDER}


def sham_scenario_criteria(mode: str, observed: dict[str, Any], expected: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        criterion(f"{mode} lifecycle readback success", observed.get("success"), "== True", observed.get("success") is True),
        criterion(f"{mode} schema version", observed.get("schema_version"), f"== {expected['schema_version']}", observed.get("schema_version") == expected["schema_version"]),
        criterion(f"{mode} sham mode readback", observed.get("sham_mode"), f"== {expected['sham_mode']}", observed.get("sham_mode") == expected["sham_mode"]),
        criterion(f"{mode} pool size", observed.get("pool_size"), f"== {expected['pool_size']}", observed.get("pool_size") == expected["pool_size"]),
        criterion(f"{mode} founder count", observed.get("founder_count"), f"== {expected['founder_count']}", observed.get("founder_count") == expected["founder_count"]),
        criterion(f"{mode} active count", observed.get("active_count"), f"== {expected['active_count']}", observed.get("active_count") == expected["active_count"]),
        criterion(f"{mode} inactive count", observed.get("inactive_count"), f"== {expected['inactive_count']}", observed.get("inactive_count") == expected["inactive_count"]),
        criterion(f"{mode} active mask bits", observed.get("active_mask_bits"), f"== {expected['active_mask_bits']}", observed.get("active_mask_bits") == expected["active_mask_bits"]),
        criterion(f"{mode} attempted event count", observed.get("attempted_event_count"), f"== {expected['attempted_event_count']}", observed.get("attempted_event_count") == expected["attempted_event_count"]),
        criterion(f"{mode} lifecycle accepted event count", observed.get("lifecycle_event_count"), f"== {expected['lifecycle_event_count']}", observed.get("lifecycle_event_count") == expected["lifecycle_event_count"]),
        criterion(f"{mode} cleavage count", observed.get("cleavage_count"), f"== {expected['cleavage_count']}", observed.get("cleavage_count") == expected["cleavage_count"]),
        criterion(f"{mode} adult birth count", observed.get("adult_birth_count"), f"== {expected['adult_birth_count']}", observed.get("adult_birth_count") == expected["adult_birth_count"]),
        criterion(f"{mode} death count", observed.get("death_count"), f"== {expected['death_count']}", observed.get("death_count") == expected["death_count"]),
        criterion(f"{mode} maturity count", observed.get("maturity_count"), f"== {expected['maturity_count']}", observed.get("maturity_count") == expected["maturity_count"]),
        criterion(f"{mode} trophic update count", observed.get("trophic_update_count"), f"== {expected['trophic_update_count']}", observed.get("trophic_update_count") == expected["trophic_update_count"]),
        criterion(f"{mode} invalid event count", observed.get("invalid_event_count"), f"== {expected['invalid_event_count']}", observed.get("invalid_event_count") == expected["invalid_event_count"]),
        criterion(f"{mode} lineage checksum", observed.get("lineage_checksum"), f"== {expected['lineage_checksum']}", observed.get("lineage_checksum") == expected["lineage_checksum"]),
        criterion(f"{mode} trophic checksum", observed.get("trophic_checksum"), f"== {expected['trophic_checksum']}", observed.get("trophic_checksum") == expected["trophic_checksum"]),
        criterion(f"{mode} compact lifecycle payload length", observed.get("payload_len"), "== 68", observed.get("payload_len") == 68),
    ]


def separation_criteria(finals: dict[str, dict[str, Any]], references: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    enabled = finals.get("enabled", {})
    enabled_expected = references["enabled"]["expected"]
    rows: list[dict[str, Any]] = []
    for mode, field in SEPARATION_FIELDS.items():
        observed_value = finals.get(mode, {}).get(field)
        enabled_value = enabled.get(field)
        rows.append(
            criterion(
                f"{mode} separates {field} from enabled",
                {"control": observed_value, "enabled": enabled_value},
                "control != enabled",
                observed_value != enabled_value,
            )
        )
    rows.append(
        criterion(
            "fixed-pool suppresses mask mutation counters",
            {
                "cleavage": finals.get("fixed_static_pool_control", {}).get("cleavage_count"),
                "adult_birth": finals.get("fixed_static_pool_control", {}).get("adult_birth_count"),
                "death": finals.get("fixed_static_pool_control", {}).get("death_count"),
            },
            "all == 0",
            finals.get("fixed_static_pool_control", {}).get("cleavage_count") == 0
            and finals.get("fixed_static_pool_control", {}).get("adult_birth_count") == 0
            and finals.get("fixed_static_pool_control", {}).get("death_count") == 0,
        )
    )
    rows.append(
        criterion(
            "enabled control remains canonical",
            {field: enabled.get(field) for field in ["active_mask_bits", "lineage_checksum", "trophic_checksum"]},
            "matches enabled reference",
            enabled.get("active_mask_bits") == enabled_expected["active_mask_bits"]
            and enabled.get("lineage_checksum") == enabled_expected["lineage_checksum"]
            and enabled.get("trophic_checksum") == enabled_expected["trophic_checksum"],
        )
    )
    return rows


# ---------------------------------------------------------------------------
# Build/package helpers
# ---------------------------------------------------------------------------


def clean_copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)

    def ignore(_dir: str, names: list[str]) -> set[str]:
        return {
            name
            for name in names
            if name in {"__pycache__", ".pytest_cache", "build", "test_runtime", "test_lifecycle", "test_lifecycle_split"}
            or (name.startswith("test_") and "." not in name)
            or name.endswith((".pyc", ".o"))
        }

    shutil.copytree(src, dst, ignore=ignore)


def run_lifecycle_sham_host_tests(output_dir: Path) -> dict[str, Any]:
    result = run_cmd(
        [
            "make",
            "-C",
            str(RUNTIME),
            "clean-host",
            "test-lifecycle",
            "test-lifecycle-split",
            "test-profiles",
        ]
    )
    result["status"] = "pass" if result["returncode"] == 0 else "fail"
    (output_dir / "tier4_30f_host_tests_stdout.txt").write_text(result.get("stdout", ""), encoding="utf-8")
    (output_dir / "tier4_30f_host_tests_stderr.txt").write_text(result.get("stderr", ""), encoding="utf-8")
    return result


def build_aplx_for_profile(profile: str, output_dir: Path) -> dict[str, Any]:
    env = os.environ.copy()
    tools = base.detect_spinnaker_tools()
    fallback = Path("/tmp/spinnaker_tools")
    if not tools and fallback.exists():
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
    result = run_cmd(["make", "-C", str(RUNTIME), "clean", "all"], env=env)
    (output_dir / f"tier4_30f_build_{profile}_stdout.txt").write_text(result.get("stdout", ""), encoding="utf-8")
    (output_dir / f"tier4_30f_build_{profile}_stderr.txt").write_text(result.get("stderr", ""), encoding="utf-8")

    aplx = RUNTIME / "build" / "coral_reef.aplx"
    profile_aplx = output_dir / f"coral_reef_{profile}.aplx"
    if aplx.exists():
        if profile_aplx.exists():
            profile_aplx.unlink()
        shutil.copy2(aplx, profile_aplx)

    size_text = 0
    elf = RUNTIME / "build" / "gnu" / "coral_reef.elf"
    if elf.exists():
        size_bin = str(arm_toolchain / "arm-none-eabi-size") if arm_toolchain.exists() else "arm-none-eabi-size"
        size = run_cmd([size_bin, str(elf)])
        result["size_stdout"] = size.get("stdout", "")
        result["size_stderr"] = size.get("stderr", "")
        if size.get("returncode") == 0:
            for line in size.get("stdout", "").splitlines():
                if "coral_reef.elf" not in line:
                    continue
                parts = line.strip().split()
                if len(parts) >= 4:
                    try:
                        size_text = int(parts[0]) + int(parts[1])
                    except ValueError:
                        size_text = 0

    result.update(
        {
            "profile": profile,
            "runtime_profile": profile,
            "spinnaker_tools": tools,
            "aplx_artifact": str(profile_aplx),
            "aplx_exists": profile_aplx.exists(),
            "size_text": size_text,
        }
    )
    result["status"] = "pass" if result["returncode"] == 0 and profile_aplx.exists() else "fail"
    return result


def prepare_bundle(output_dir: Path) -> tuple[Path, str, dict[str, str]]:
    bundle = output_dir / "ebrains_upload_bundle" / UPLOAD_PACKAGE_NAME
    if bundle.exists():
        shutil.rmtree(bundle)
    (bundle / "experiments").mkdir(parents=True, exist_ok=True)
    (bundle / "coral_reef_spinnaker" / "python_host").mkdir(parents=True, exist_ok=True)

    scripts = [
        "tier4_30f_lifecycle_sham_hardware_subset.py",
        "tier4_30e_multicore_lifecycle_hardware_smoke.py",
        "tier4_30b_lifecycle_hardware_smoke.py",
        "tier4_30a_static_pool_lifecycle_reference.py",
        "tier4_22i_custom_runtime_roundtrip.py",
    ]
    for script in scripts:
        target = bundle / "experiments" / script
        shutil.copy2(ROOT / "experiments" / script, target)
        os.chmod(target, 0o755)

    shutil.copy2(ROOT / "coral_reef_spinnaker" / "__init__.py", bundle / "coral_reef_spinnaker" / "__init__.py")
    shutil.copy2(
        ROOT / "coral_reef_spinnaker" / "python_host" / "colony_controller.py",
        bundle / "coral_reef_spinnaker" / "python_host" / "colony_controller.py",
    )
    clean_copy_tree(RUNTIME, bundle / "coral_reef_spinnaker" / "spinnaker_runtime")

    command = f"{UPLOAD_PACKAGE_NAME}/experiments/tier4_30f_lifecycle_sham_hardware_subset.py --mode run-hardware --output-dir tier4_30f_hw_job_output"
    readme = bundle / "README_TIER4_30F_HW_JOB.md"
    readme.write_text(
        "# Tier 4.30f EBRAINS Lifecycle Sham-Control Hardware Subset\n\n"
        f"Upload the `{UPLOAD_PACKAGE_NAME}` folder itself so the JobManager path starts with `{UPLOAD_PACKAGE_NAME}/`. Do not upload `controlled_test_output`.\n\n"
        "Purpose: build/load the same five custom runtime profiles as 4.30e, then run a compact lifecycle sham-control subset on the lifecycle core: enabled, fixed-pool, random event replay, active-mask shuffle, no trophic pressure, and no dopamine/plasticity.\n\n"
        "Run command:\n\n"
        f"```text\n{command}\n```\n\n"
        "Paste the command directly into the EBRAINS JobManager command field. Do not wrap it in `bash`, `cd`, or `python3`.\n\n"
        "PASS is a sham-control hardware subset only: real target acquisition, five profile builds/loads, compact lifecycle readback, expected enabled/control separations, and zero synthetic fallback. It is not lifecycle task-benefit evidence, not full Tier 6.3 hardware, not speedup, not multi-chip scaling, and not a lifecycle baseline freeze.\n",
        encoding="utf-8",
    )
    metadata = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "upload_package": UPLOAD_PACKAGE_NAME,
        "prepared_at_utc": utc_now(),
        "runner": "experiments/tier4_30f_lifecycle_sham_hardware_subset.py",
        "job_command": command,
        "core_roles": CORE_ROLES,
        "sham_modes": SHAM_MODE_ORDER,
        "claim_boundary": "Prepared source bundle only. Hardware evidence requires returned run-hardware artifacts from EBRAINS/SpiNNaker.",
    }
    write_json(bundle / "metadata.json", metadata)

    STABLE_EBRAINS_UPLOAD.parent.mkdir(parents=True, exist_ok=True)
    if STABLE_EBRAINS_UPLOAD.exists():
        shutil.rmtree(STABLE_EBRAINS_UPLOAD)
    shutil.copytree(bundle, STABLE_EBRAINS_UPLOAD)
    return bundle, command, {"upload_bundle": str(bundle), "stable_upload_folder": str(STABLE_EBRAINS_UPLOAD), "job_readme": str(readme)}


# ---------------------------------------------------------------------------
# Hardware loop
# ---------------------------------------------------------------------------


def _read_profile_states(ctrls: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    return {
        role: ctrl.read_state(args.dest_x, args.dest_y, CORE_ROLES[role]["core"])
        for role, ctrl in ctrls.items()
    }


def _non_lifecycle_guard_probe(ctrls: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    return {
        role: ctrl.lifecycle_read_state(args.dest_x, args.dest_y, CORE_ROLES[role]["core"])
        for role, ctrl in ctrls.items()
        if role != "lifecycle"
    }


def _run_sham_mode(lifecycle_ctrl: Any, args: argparse.Namespace, mode: str, reference: dict[str, Any]) -> dict[str, Any]:
    p = CORE_ROLES["lifecycle"]["core"]
    reset = lifecycle_ctrl.reset(args.dest_x, args.dest_y, p)
    time.sleep(float(args.command_delay_seconds))
    init = lifecycle_ctrl.lifecycle_init(
        pool_size=8,
        founder_count=2,
        seed=int(args.seed),
        trophic_seed_raw=FP_ONE,
        generation_seed=0,
        dest_x=args.dest_x,
        dest_y=args.dest_y,
        dest_cpu=p,
    )
    sham = lifecycle_ctrl.lifecycle_sham_mode(
        SHAM_MODE_IDS[mode],
        dest_x=args.dest_x,
        dest_y=args.dest_y,
        dest_cpu=p,
    )
    event_rows: list[dict[str, Any]] = []
    for event in reference["schedule"]:
        payload = lifecycle_event_payload(event)
        observed = lifecycle_ctrl.lifecycle_event(
            **payload,
            dest_x=args.dest_x,
            dest_y=args.dest_y,
            dest_cpu=p,
        )
        event_rows.append(
            {
                **payload,
                "event_name": event.event_type,
                "success": observed.get("success") is True,
                "status": observed.get("status"),
                "observed_event_count": observed.get("lifecycle_event_count"),
                "observed_invalid_event_count": observed.get("invalid_event_count"),
                "observed_active_mask_bits": observed.get("active_mask_bits"),
            }
        )
    final = lifecycle_ctrl.lifecycle_read_state(args.dest_x, args.dest_y, p)
    expected = reference["expected"]
    success_count = sum(1 for row in event_rows if row["success"])
    failure_count = len(event_rows) - success_count
    criteria = [
        criterion(f"{mode} reset acknowledged", reset, "== True", reset is True),
        criterion(f"{mode} lifecycle init succeeded", init.get("success"), "== True", init.get("success") is True),
        criterion(f"{mode} sham mode command succeeded", sham.get("success"), "== True", sham.get("success") is True),
        criterion(f"{mode} sham mode command readback", sham.get("sham_mode"), f"== {expected['sham_mode']}", sham.get("sham_mode") == expected["sham_mode"]),
        criterion(f"{mode} successful event command count", success_count, f"== {expected['lifecycle_event_count']}", success_count == expected["lifecycle_event_count"]),
        criterion(f"{mode} failed event command count", failure_count, f"== {expected['invalid_event_count']}", failure_count == expected["invalid_event_count"]),
        *sham_scenario_criteria(mode, final, expected),
    ]
    return {
        "status": "pass" if all(item["passed"] for item in criteria) else "fail",
        "mode": mode,
        "criteria": criteria,
        "reset": reset,
        "init": init,
        "sham": sham,
        "events": event_rows,
        "final": final,
        "expected": expected,
    }


def lifecycle_sham_hardware_loop(hostname: str, args: argparse.Namespace, references: dict[str, dict[str, Any]]) -> dict[str, Any]:
    from coral_reef_spinnaker.python_host.colony_controller import ColonyController

    started = time.perf_counter()
    ctrls = {
        role: ColonyController(hostname, port=int(args.port), timeout=float(args.timeout_seconds))
        for role in CORE_ROLES
    }
    try:
        resets = {
            role: ctrl.reset(args.dest_x, args.dest_y, CORE_ROLES[role]["core"])
            for role, ctrl in ctrls.items()
        }
        time.sleep(0.1)
        profile_reads = _read_profile_states(ctrls, args)
        non_lifecycle_guards = _non_lifecycle_guard_probe(ctrls, args)
        modes = {
            mode: _run_sham_mode(ctrls["lifecycle"], args, mode, reference)
            for mode, reference in references.items()
        }
        final_profile_reads = _read_profile_states(ctrls, args)
        finals = {mode: item.get("final", {}) for mode, item in modes.items()}
        separations = separation_criteria(finals, references)
        status = "pass" if (
            all(resets.values())
            and all(read.get("success") is True for read in profile_reads.values())
            and all(read.get("profile_id") == CORE_ROLES[role]["profile_id"] for role, read in profile_reads.items())
            and all(probe.get("success") is False for probe in non_lifecycle_guards.values())
            and all(item.get("status") == "pass" for item in modes.values())
            and all(item["passed"] for item in separations)
            and all(read.get("success") is True for read in final_profile_reads.values())
        ) else "fail"
        return {
            "status": status,
            "hostname": hostname,
            "runtime_seconds": time.perf_counter() - started,
            "core_roles": CORE_ROLES,
            "resets": resets,
            "profile_reads": profile_reads,
            "non_lifecycle_guard_probe": non_lifecycle_guards,
            "modes": modes,
            "separation_criteria": separations,
            "final_profile_reads": final_profile_reads,
        }
    except Exception as exc:
        return {
            "status": "fail",
            "hostname": hostname,
            "runtime_seconds": time.perf_counter() - started,
            "exception_type": type(exc).__name__,
            "exception": str(exc),
            "traceback": traceback.format_exc(),
        }
    finally:
        for ctrl in ctrls.values():
            ctrl.close()


# ---------------------------------------------------------------------------
# Reports and modes
# ---------------------------------------------------------------------------


def write_report(path: Path, result: dict[str, Any]) -> None:
    summary = result.get("summary", {})
    lines = [
        "# Tier 4.30f Lifecycle Sham-Control Hardware Subset",
        "",
        f"- Generated: `{result.get('generated_at_utc')}`",
        f"- Mode: `{result.get('mode')}`",
        f"- Status: **{str(result.get('status', 'unknown')).upper()}**",
        f"- Upload package: `{summary.get('upload_package', UPLOAD_PACKAGE_NAME)}`",
        "",
        "## Claim Boundary",
        "",
        result.get("claim_boundary", ""),
        "",
        "## Summary",
        "",
    ]
    for key in [
        "hardware_target_configured",
        "spinnaker_hostname",
        "profile_builds_passed",
        "profile_loads_passed",
        "task_status",
        "raw_remote_status",
        "corrected_ingest_status",
        "job_command",
    ]:
        if key in summary:
            lines.append(f"- {key}: `{summary[key]}`")
    lines.extend(["", "## Criteria", "", "| Criterion | Value | Rule | Pass |", "| --- | --- | --- | --- |"])
    for item in result.get("criteria", []):
        value = json.dumps(json_safe(item.get("value")), sort_keys=True)
        if len(value) > 140:
            value = value[:137] + "..."
        lines.append(f"| {item.get('name')} | `{value}` | {item.get('rule')} | {'yes' if item.get('passed') else 'no'} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def finalize(output_dir: Path, result: dict[str, Any]) -> int:
    result_path = output_dir / "tier4_30f_hw_results.json"
    report_path = output_dir / "tier4_30f_hw_report.md"
    result.setdefault("artifacts", {})
    result["artifacts"].update({"results_json": str(result_path), "report_md": str(report_path)})
    write_json(result_path, result)
    write_report(report_path, result)
    write_json(CONTROLLED / "tier4_30f_hw_latest_manifest.json", result)
    print(json.dumps({"status": result.get("status"), "output_dir": str(output_dir), "results": str(result_path)}, indent=2))
    return 0 if str(result.get("status", "")).lower() in {"pass", "prepared"} else 1


def mode_prepare(args: argparse.Namespace, output_dir: Path) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    references = all_references()
    host_tests = run_lifecycle_sham_host_tests(output_dir)
    main_syntax = base.run_main_syntax_check(output_dir)
    bundle, command, bundle_artifacts = prepare_bundle(output_dir)
    enabled = references["enabled"]["expected"]
    separation_precheck = separation_criteria({mode: ref["expected"] for mode, ref in references.items()}, references)
    criteria = [
        criterion("reference sham modes generated", list(references), f"== {SHAM_MODE_ORDER}", list(references) == SHAM_MODE_ORDER),
        criterion("enabled reference remains canonical_32", enabled, "active_mask=63, lineage=105428, trophic=466851", enabled["active_mask_bits"] == 63 and enabled["lineage_checksum"] == 105428 and enabled["trophic_checksum"] == 466851),
        criterion("local reference controls separate", [item["passed"] for item in separation_precheck], "all True", all(item["passed"] for item in separation_precheck)),
        criterion("lifecycle sham host tests pass", host_tests.get("status"), "== pass", host_tests.get("status") == "pass"),
        criterion("main.c host syntax check pass", main_syntax.get("status"), "== pass", main_syntax.get("status") == "pass"),
        criterion("upload bundle created", str(bundle), "exists", bundle.exists()),
        criterion("stable upload folder created", str(STABLE_EBRAINS_UPLOAD), "exists", STABLE_EBRAINS_UPLOAD.exists()),
        criterion("run-hardware command emitted", command, "contains --mode run-hardware", "--mode run-hardware" in command),
    ]
    status = "prepared" if all(item["passed"] for item in criteria) else "blocked"
    result = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "mode": "prepare",
        "status": status,
        "output_dir": str(output_dir),
        "summary": {
            "upload_package": UPLOAD_PACKAGE_NAME,
            "upload_bundle": str(bundle),
            "stable_upload_folder": str(STABLE_EBRAINS_UPLOAD),
            "job_command": command,
            "what_i_need_from_user": f"Upload `{UPLOAD_PACKAGE_NAME}` to EBRAINS/JobManager and run the emitted command.",
            "claim_boundary": "Prepared source bundle only; no hardware evidence until returned run-hardware artifacts pass.",
        },
        "criteria": criteria,
        "references": {mode: {"expected": ref["expected"], "event_count": ref["event_count"]} for mode, ref in references.items()},
        "host_tests": host_tests,
        "main_syntax_check": main_syntax,
        "bundle_artifacts": bundle_artifacts,
        "core_roles": CORE_ROLES,
        "claim_boundary": "Prepared source bundle only; no hardware evidence until returned run-hardware artifacts pass.",
    }
    return finalize(output_dir, result)


def mode_run_hardware(args: argparse.Namespace, output_dir: Path) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    references = all_references()
    env_report = base.environment_report()
    host_tests = run_lifecycle_sham_host_tests(output_dir)
    main_syntax = base.run_main_syntax_check(output_dir)
    builds = {role: build_aplx_for_profile(spec["profile"], output_dir) for role, spec in CORE_ROLES.items()}

    target: dict[str, Any] = {"status": "not_attempted", "reason": "blocked_before_target_acquisition"}
    target_cleanup: dict[str, Any] = {"status": "not_attempted"}
    loads: dict[str, dict[str, Any]] = {role: {"status": "not_attempted"} for role in CORE_ROLES}
    task: dict[str, Any] = {"status": "not_attempted", "reason": "blocked_before_lifecycle_sham_loop"}
    hostname = ""
    hardware_exception: dict[str, Any] | None = None

    try:
        if all(build.get("status") == "pass" for build in builds.values()):
            target = base.acquire_hardware_target(args)
            hostname = str(target.get("hostname") or target.get("target_ipaddress") or "")
            tx = target.get("_transceiver")
            if target.get("status") == "pass" and hostname and not args.skip_load:
                for role, spec in CORE_ROLES.items():
                    loads[role] = base.load_application_spinnman(
                        hostname,
                        Path(builds[role]["aplx_artifact"]),
                        x=int(args.dest_x),
                        y=int(args.dest_y),
                        p=int(spec["core"]),
                        app_id=int(spec["app_id"]),
                        delay=float(args.startup_delay_seconds),
                        transceiver=tx,
                    )
            elif args.skip_load:
                loads = {role: {"status": "skipped", "reason": "--skip-load set"} for role in CORE_ROLES}
            if target.get("status") == "pass" and hostname and all(load.get("status") in {"pass", "skipped"} for load in loads.values()):
                task = lifecycle_sham_hardware_loop(hostname, args, references)
    except Exception as exc:
        hardware_exception = {"exception_type": type(exc).__name__, "exception": str(exc), "traceback": traceback.format_exc()}
        task = {"status": "fail", **hardware_exception}
    finally:
        target_cleanup = base.release_hardware_target(target)

    write_json(output_dir / "tier4_30f_hw_environment.json", env_report)
    write_json(output_dir / "tier4_30f_hw_target_acquisition.json", base.public_target_acquisition({**target, "cleanup": target_cleanup}))
    for role, build in builds.items():
        write_json(output_dir / f"tier4_30f_hw_{role}_build.json", build)
    for role, load in loads.items():
        write_json(output_dir / f"tier4_30f_hw_{role}_load.json", load)
    write_json(output_dir / "tier4_30f_hw_task_result.json", task)
    for mode, item in task.get("modes", {}).items() if isinstance(task, dict) else []:
        write_csv(output_dir / f"tier4_30f_hw_{mode}_events.csv", item.get("events", []))

    mode_checks: list[dict[str, Any]] = []
    for item in task.get("modes", {}).values() if isinstance(task, dict) else []:
        mode_checks.extend(item.get("criteria", []))
    separation_checks = task.get("separation_criteria", []) if isinstance(task, dict) else []
    profile_reads = task.get("profile_reads", {}) if isinstance(task, dict) else {}
    final_profile_reads = task.get("final_profile_reads", {}) if isinstance(task, dict) else {}
    non_lifecycle_guards = task.get("non_lifecycle_guard_probe", {}) if isinstance(task, dict) else {}

    profile_criteria: list[dict[str, Any]] = []
    for role, spec in CORE_ROLES.items():
        read = profile_reads.get(role, {})
        final_read = final_profile_reads.get(role, {})
        profile_criteria.extend(
            [
                criterion(f"{role} profile read success", read.get("success"), "== True", read.get("success") is True),
                criterion(f"{role} profile id", read.get("profile_id"), f"== {spec['profile_id']}", read.get("profile_id") == spec["profile_id"]),
                criterion(f"{role} final profile read success", final_read.get("success"), "== True", final_read.get("success") is True),
            ]
        )
    guard_criteria = [
        criterion(f"{role} rejects direct lifecycle read", probe.get("success"), "== False", probe.get("success") is False)
        for role, probe in non_lifecycle_guards.items()
    ]

    criteria = [
        criterion("runner revision current", RUNNER_REVISION, "expected current source", True),
        criterion("lifecycle sham host tests pass", host_tests.get("status"), "== pass", host_tests.get("status") == "pass"),
        criterion("main.c host syntax check pass", main_syntax.get("status"), "== pass", main_syntax.get("status") == "pass"),
        criterion("all five profile builds pass", {role: build.get("status") for role, build in builds.items()}, "all == pass", all(build.get("status") == "pass" for build in builds.values())),
        criterion("hardware target acquired", base.public_target_acquisition(target), "status == pass and hostname acquired", target.get("status") == "pass" and bool(hostname)),
        criterion("all five profile loads pass", {role: load.get("status") for role, load in loads.items()}, "all == pass", all(load.get("status") == "pass" for load in loads.values())),
        criterion("lifecycle sham-control task pass", task.get("status"), "== pass", task.get("status") == "pass"),
        *profile_criteria,
        *guard_criteria,
        *mode_checks,
        *separation_checks,
        criterion("no unhandled hardware exception", hardware_exception is None, "== True", hardware_exception is None),
        criterion("synthetic fallback zero", 0, "== 0", True),
    ]
    status = "pass" if all(item["passed"] for item in criteria) else "fail"
    result = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "mode": "run-hardware",
        "status": status,
        "failure_reason": "" if status == "pass" else "Failed criteria: " + ", ".join(item["name"] for item in criteria if not item["passed"]),
        "output_dir": str(output_dir),
        "summary": {
            "upload_package": UPLOAD_PACKAGE_NAME,
            "hardware_target_configured": target.get("status") == "pass" and bool(hostname),
            "spinnaker_hostname": hostname,
            "profile_builds_passed": all(build.get("status") == "pass" for build in builds.values()),
            "profile_loads_passed": all(load.get("status") == "pass" for load in loads.values()),
            "task_status": task.get("status"),
            "sham_modes": SHAM_MODE_ORDER,
            "claim_boundary": "Lifecycle sham-control hardware subset only; not lifecycle task benefit, not full Tier 6.3 hardware, not speedup, not multi-chip scaling, and not a lifecycle baseline freeze.",
            "next_step_if_passed": "Ingest returned artifacts, then decide whether 4.30g should run a fuller lifecycle task-benefit/control bridge or move to the next native lifecycle integration gate.",
        },
        "criteria": criteria,
        "references": {mode: {"expected": ref["expected"], "event_count": ref["event_count"]} for mode, ref in references.items()},
        "environment": env_report,
        "host_tests": host_tests,
        "main_syntax_check": main_syntax,
        "builds": builds,
        "target_acquisition": base.public_target_acquisition(target),
        "target_cleanup": target_cleanup,
        "loads": loads,
        "task": task,
        "hardware_exception": hardware_exception,
        "core_roles": CORE_ROLES,
        "claim_boundary": "Lifecycle sham-control hardware subset only; not lifecycle task benefit, not full Tier 6.3 hardware, not speedup, not multi-chip scaling, and not a lifecycle baseline freeze.",
    }
    return finalize(output_dir, result)


def copy_returned_artifacts(ingest_dir: Path, output_dir: Path, *, anchor: Path | None = None) -> list[str]:
    if not ingest_dir.exists():
        return []
    returned_dir = output_dir / "returned_artifacts"
    returned_dir.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    anchor_mtime = anchor.stat().st_mtime if anchor and anchor.exists() else None
    for path in sorted(ingest_dir.iterdir()):
        if not path.is_file():
            continue
        if anchor_mtime is not None and abs(path.stat().st_mtime - anchor_mtime) > 900:
            continue
        if path.suffix in {".o", ".elf", ".aplx"}:
            continue
        name = path.name
        if (
            name.startswith("tier4_30f")
            or name.startswith("main ")
            or name.startswith("state_manager ")
            or name.startswith("host_interface ")
            or name.startswith("reports")
            or name in {"finished", "global_provenance.sqlite3"}
        ):
            dest = returned_dir / name
            shutil.copy2(path, dest)
            copied.append(str(dest))
    return copied


def mode_ingest(args: argparse.Namespace, output_dir: Path) -> int:
    ingest_dir = Path(args.ingest_dir or output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    candidate = Path(args.hardware_results) if args.hardware_results else ingest_dir / "tier4_30f_hw_results.json"
    if not candidate.exists():
        matches = sorted(ingest_dir.glob("**/tier4_30f_hw_results.json"))
        if matches:
            candidate = matches[-1]
    if not candidate.exists():
        result = {
            "tier": TIER,
            "runner_revision": RUNNER_REVISION,
            "generated_at_utc": utc_now(),
            "mode": "ingest",
            "status": "fail",
            "failure_reason": f"tier4_30f_hw_results.json not found in {ingest_dir}",
            "criteria": [criterion("hardware results json exists", str(candidate), "exists", False)],
            "claim_boundary": "Failed ingest only; not hardware evidence.",
        }
        return finalize(output_dir, result)
    returned_artifacts = copy_returned_artifacts(ingest_dir, output_dir, anchor=candidate)
    hardware = read_json(candidate)
    criteria = [
        criterion("hardware results json exists", str(candidate), "exists", True),
        criterion("hardware mode was run-hardware", hardware.get("mode"), "== run-hardware", hardware.get("mode") == "run-hardware"),
        criterion("hardware status pass", hardware.get("status"), "== pass", hardware.get("status") == "pass"),
        criterion("runner revision current", hardware.get("runner_revision"), f"== {RUNNER_REVISION}", hardware.get("runner_revision") == RUNNER_REVISION),
        criterion("returned artifacts preserved", len(returned_artifacts), "> 0", len(returned_artifacts) > 0),
    ]
    status = "pass" if all(item["passed"] for item in criteria) else "fail"
    result = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "mode": "ingest",
        "status": status,
        "failure_reason": "" if status == "pass" else "Failed criteria: " + ", ".join(item["name"] for item in criteria if not item["passed"]),
        "output_dir": str(output_dir),
        "criteria": criteria,
        "raw_remote_status": hardware.get("status"),
        "returned_artifacts": returned_artifacts,
        "hardware_results": hardware,
        "summary": {
            "raw_remote_status": hardware.get("status"),
            "corrected_ingest_status": status,
            "hardware_target_configured": hardware.get("summary", {}).get("hardware_target_configured"),
            "spinnaker_hostname": hardware.get("summary", {}).get("spinnaker_hostname"),
            "profile_builds_passed": hardware.get("summary", {}).get("profile_builds_passed"),
            "profile_loads_passed": hardware.get("summary", {}).get("profile_loads_passed"),
            "task_status": hardware.get("summary", {}).get("task_status"),
            "sham_modes": hardware.get("summary", {}).get("sham_modes"),
        },
        "claim_boundary": "Ingest confirms returned EBRAINS run-hardware artifacts only; no new claim beyond Tier 4.30f lifecycle sham-control hardware subset.",
    }
    return finalize(output_dir, result)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=TIER)
    parser.add_argument("--mode", choices=["prepare", "run-hardware", "ingest"], default="prepare")
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--ingest-dir", type=Path, default=None)
    parser.add_argument("--hardware-results", type=Path, default=None)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--dest-x", type=int, default=0)
    parser.add_argument("--dest-y", type=int, default=0)
    parser.add_argument("--port", type=int, default=17893)
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    parser.add_argument("--startup-delay-seconds", type=float, default=2.0)
    parser.add_argument("--command-delay-seconds", type=float, default=0.03)
    parser.add_argument("--target-acquisition", choices=["auto", "hostname", "spynnaker-probe"], default="auto")
    parser.add_argument("--spinnaker-hostname", default="")
    parser.add_argument("--target-probe-run-ms", type=float, default=1.0)
    parser.add_argument("--target-probe-timestep-ms", type=float, default=1.0)
    parser.add_argument("--target-probe-population-size", type=int, default=1)
    parser.add_argument("--dest-cpu", type=int, default=4, help="Used only by the target-acquisition probe; Tier 4.30f loads fixed cores 4-8.")
    parser.add_argument("--auto-dest-cpu", dest="auto_dest_cpu", action="store_true", default=True)
    parser.add_argument("--no-auto-dest-cpu", dest="auto_dest_cpu", action="store_false")
    parser.add_argument("--skip-load", action="store_true", help="Debug only; canonical hardware evidence requires normal load.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.output_dir is None:
        args.output_dir = DEFAULT_PREPARE_OUTPUT if args.mode == "prepare" else DEFAULT_RUN_OUTPUT
    if args.mode == "prepare":
        return mode_prepare(args, args.output_dir)
    if args.mode == "run-hardware":
        return mode_run_hardware(args, args.output_dir)
    if args.mode == "ingest":
        return mode_ingest(args, args.output_dir)
    raise AssertionError(f"unsupported mode: {args.mode}")


if __name__ == "__main__":
    raise SystemExit(main())
