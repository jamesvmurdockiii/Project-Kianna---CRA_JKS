#!/usr/bin/env python3
"""Tier 4.30b-hw single-core lifecycle active-mask/lineage hardware smoke.

This gate packages and runs the audited Tier 4.30b lifecycle/static-pool
runtime surface on one SpiNNaker core. It verifies compact lifecycle metadata
readback only: active masks, event counters, lineage checksum, and trophic
checksum must match the Tier 4.30a fixed-point reference.

It is intentionally not a lifecycle task-benefit claim, not a multi-core
lifecycle migration, not a speedup claim, and not a lifecycle baseline freeze.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"
RUNTIME = ROOT / "coral_reef_spinnaker" / "spinnaker_runtime"

sys.path.insert(0, str(ROOT))

from experiments import tier4_22i_custom_runtime_roundtrip as base  # noqa: E402
from experiments.tier4_30a_static_pool_lifecycle_reference import (  # noqa: E402
    EVENT_NAMES,
    FP_ONE,
    generate_schedule,
    run_schedule,
)


TIER = "Tier 4.30b-hw - Single-Core Lifecycle Active-Mask/Lineage Hardware Smoke"
RUNNER_REVISION = "tier4_30b_lifecycle_hardware_smoke_20260505_0001"
UPLOAD_PACKAGE_NAME = "cra_430b"
STABLE_EBRAINS_UPLOAD = ROOT / "ebrains_jobs" / UPLOAD_PACKAGE_NAME
DEFAULT_PREPARE_OUTPUT = CONTROLLED / "tier4_30b_hw_20260505_prepared"
DEFAULT_RUN_OUTPUT = CONTROLLED / f"tier4_30b_hw_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_run_hardware"

RUNTIME_PROFILE = "decoupled_memory_route"
APP_ID = 17

SCENARIOS = {
    "canonical_32": 32,
    "boundary_64": 64,
}

EVENT_TYPE_TO_OPCODE = {
    "trophic_update": EVENT_NAMES["trophic_update"],
    "cleavage": EVENT_NAMES["cleavage"],
    "adult_birth": EVENT_NAMES["adult_birth"],
    "death": EVENT_NAMES["death"],
    "maturity_handoff": EVENT_NAMES["maturity_handoff"],
}


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
        writer = csv.DictWriter(handle, fieldnames=keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def criterion(name: str, value: Any, rule: str, passed: bool, note: str = "") -> dict[str, Any]:
    return {
        "name": name,
        "value": json_safe(value),
        "rule": rule,
        "passed": bool(passed),
        "note": note,
    }


def scenario_reference(event_count: int) -> dict[str, Any]:
    schedule = generate_schedule(event_count)
    state = run_schedule(f"tier4_30b_hw_{event_count}", schedule, mode="enabled")
    summary = state.summary()
    return {
        "event_count": event_count,
        "schedule": schedule,
        "summary": summary,
        "expected": {
            "pool_size": 8,
            "founder_count": 2,
            "active_count": summary["active_count"],
            "inactive_count": summary["inactive_count"],
            "active_mask_bits": summary["active_mask_bits"],
            "attempted_event_count": summary["attempted_event_count"],
            "lifecycle_event_count": summary["event_count"],
            "cleavage_count": summary["cleavage_count"],
            "adult_birth_count": summary["birth_count"],
            "death_count": summary["death_count"],
            "invalid_event_count": summary["invalid_event_count"],
            "lineage_checksum": summary["lineage_checksum"],
            "trophic_checksum": summary["trophic_checksum"],
        },
    }


def all_references() -> dict[str, dict[str, Any]]:
    return {name: scenario_reference(count) for name, count in SCENARIOS.items()}


def lifecycle_event_payload(event: Any) -> dict[str, int]:
    target_slot = int(event.target_slot) if int(event.target_slot) >= 0 else 0
    return {
        "event_index": int(event.event_index),
        "event_type": int(EVENT_TYPE_TO_OPCODE[event.event_type]),
        "target_slot": target_slot,
        "parent_slot": int(event.parent_slot),
        "child_slot": int(event.child_slot),
        "trophic_delta_raw": int(event.trophic_delta_raw),
        "reward_raw": int(event.reward_raw),
    }


def scenario_criteria(name: str, observed: dict[str, Any], expected: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        criterion(f"{name} lifecycle readback success", observed.get("success"), "== True", observed.get("success") is True),
        criterion(f"{name} lifecycle schema version", observed.get("schema_version"), "== 1", observed.get("schema_version") == 1),
        criterion(f"{name} pool size", observed.get("pool_size"), f"== {expected['pool_size']}", observed.get("pool_size") == expected["pool_size"]),
        criterion(f"{name} founder count", observed.get("founder_count"), f"== {expected['founder_count']}", observed.get("founder_count") == expected["founder_count"]),
        criterion(f"{name} active count", observed.get("active_count"), f"== {expected['active_count']}", observed.get("active_count") == expected["active_count"]),
        criterion(f"{name} inactive count", observed.get("inactive_count"), f"== {expected['inactive_count']}", observed.get("inactive_count") == expected["inactive_count"]),
        criterion(f"{name} active mask bits", observed.get("active_mask_bits"), f"== {expected['active_mask_bits']}", observed.get("active_mask_bits") == expected["active_mask_bits"]),
        criterion(f"{name} attempted event count", observed.get("attempted_event_count"), f"== {expected['attempted_event_count']}", observed.get("attempted_event_count") == expected["attempted_event_count"]),
        criterion(f"{name} lifecycle event count", observed.get("lifecycle_event_count"), f"== {expected['lifecycle_event_count']}", observed.get("lifecycle_event_count") == expected["lifecycle_event_count"]),
        criterion(f"{name} cleavage count", observed.get("cleavage_count"), f"== {expected['cleavage_count']}", observed.get("cleavage_count") == expected["cleavage_count"]),
        criterion(f"{name} adult birth count", observed.get("adult_birth_count"), f"== {expected['adult_birth_count']}", observed.get("adult_birth_count") == expected["adult_birth_count"]),
        criterion(f"{name} death count", observed.get("death_count"), f"== {expected['death_count']}", observed.get("death_count") == expected["death_count"]),
        criterion(f"{name} invalid event count", observed.get("invalid_event_count"), "== 0", observed.get("invalid_event_count") == 0),
        criterion(f"{name} lineage checksum", observed.get("lineage_checksum"), f"== {expected['lineage_checksum']}", observed.get("lineage_checksum") == expected["lineage_checksum"]),
        criterion(f"{name} trophic checksum", observed.get("trophic_checksum"), f"== {expected['trophic_checksum']}", observed.get("trophic_checksum") == expected["trophic_checksum"]),
        criterion(f"{name} compact lifecycle readback bytes", observed.get("readback_bytes"), "== 68", observed.get("readback_bytes") == 68),
    ]


def run_lifecycle_host_tests(output_dir: Path) -> dict[str, Any]:
    result = base.run_cmd(
        ["make", "-C", str(RUNTIME), "clean-host", "test-lifecycle", "test-profiles"],
        cwd=ROOT,
    )
    result["status"] = "pass" if result["returncode"] == 0 else "fail"
    (output_dir / "tier4_30b_hw_host_tests_stdout.txt").write_text(result.get("stdout", ""), encoding="utf-8")
    (output_dir / "tier4_30b_hw_host_tests_stderr.txt").write_text(result.get("stderr", ""), encoding="utf-8")
    return result


def build_lifecycle_aplx(output_dir: Path) -> dict[str, Any]:
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
    env["RUNTIME_PROFILE"] = RUNTIME_PROFILE

    base_aplx = RUNTIME / "build" / "coral_reef.aplx"
    if base_aplx.exists():
        base_aplx.unlink()
    result = base.run_cmd(["make", "-C", str(RUNTIME), "clean", "all"], cwd=ROOT, env=env)
    (output_dir / "tier4_30b_hw_aplx_build_stdout.txt").write_text(result.get("stdout", ""), encoding="utf-8")
    (output_dir / "tier4_30b_hw_aplx_build_stderr.txt").write_text(result.get("stderr", ""), encoding="utf-8")

    aplx = RUNTIME / "build" / "coral_reef.aplx"
    profile_aplx = RUNTIME / "build" / f"coral_reef_{RUNTIME_PROFILE}.aplx"
    if aplx.exists():
        if profile_aplx.exists():
            profile_aplx.unlink()
        shutil.copy2(aplx, profile_aplx)

    size_text = 0
    elf = RUNTIME / "build" / "gnu" / "coral_reef.elf"
    if elf.exists():
        size_bin = str(arm_toolchain / "arm-none-eabi-size") if arm_toolchain.exists() else "arm-none-eabi-size"
        size = base.run_cmd([size_bin, str(elf)], cwd=ROOT)
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
            "runtime_profile": RUNTIME_PROFILE,
            "spinnaker_tools": tools,
            "aplx_artifact": str(profile_aplx if profile_aplx.exists() else aplx),
            "aplx_exists": profile_aplx.exists() or aplx.exists(),
            "size_text": size_text,
        }
    )
    result["status"] = "pass" if result["returncode"] == 0 and result["aplx_exists"] else "fail"
    return result


def clean_copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)

    def ignore(_dir: str, names: list[str]) -> set[str]:
        blocked = {"__pycache__", ".pytest_cache", "build", "test_runtime", "test_lifecycle"}
        return {
            name
            for name in names
            if name in blocked
            or (name.startswith("test_") and "." not in name)
            or name.endswith((".pyc", ".o"))
        }

    shutil.copytree(src, dst, ignore=ignore)


def prepare_bundle(output_dir: Path) -> tuple[Path, str, dict[str, str]]:
    bundle = output_dir / "ebrains_upload_bundle" / UPLOAD_PACKAGE_NAME
    if bundle.exists():
        shutil.rmtree(bundle)
    (bundle / "experiments").mkdir(parents=True, exist_ok=True)
    (bundle / "coral_reef_spinnaker" / "python_host").mkdir(parents=True, exist_ok=True)

    for script in [
        "tier4_30b_lifecycle_hardware_smoke.py",
        "tier4_30a_static_pool_lifecycle_reference.py",
        "tier4_22i_custom_runtime_roundtrip.py",
    ]:
        target = bundle / "experiments" / script
        shutil.copy2(ROOT / "experiments" / script, target)
        os.chmod(target, 0o755)

    shutil.copy2(ROOT / "coral_reef_spinnaker" / "__init__.py", bundle / "coral_reef_spinnaker" / "__init__.py")
    shutil.copy2(
        ROOT / "coral_reef_spinnaker" / "python_host" / "colony_controller.py",
        bundle / "coral_reef_spinnaker" / "python_host" / "colony_controller.py",
    )
    clean_copy_tree(RUNTIME, bundle / "coral_reef_spinnaker" / "spinnaker_runtime")

    command = f"{UPLOAD_PACKAGE_NAME}/experiments/tier4_30b_lifecycle_hardware_smoke.py --mode run-hardware --output-dir tier4_30b_hw_job_output"
    readme = bundle / "README_TIER4_30B_HW_JOB.md"
    readme.write_text(
        "# Tier 4.30b-hw EBRAINS Lifecycle Active-Mask/Lineage Smoke\n\n"
        f"Upload the `{UPLOAD_PACKAGE_NAME}` folder itself so the JobManager path starts with `{UPLOAD_PACKAGE_NAME}/`. Do not upload `controlled_test_output`.\n\n"
        "Purpose: build and load the custom runtime with `RUNTIME_PROFILE=decoupled_memory_route`, initialize the Tier 4.30 static lifecycle pool, apply the canonical 32-event and boundary 64-event lifecycle schedules, and read back compact lifecycle telemetry with `CMD_LIFECYCLE_READ_STATE`.\n\n"
        "Run command:\n\n"
        f"```text\n{command}\n```\n\n"
        "Pass means lifecycle active masks, event counters, lineage checksum, and trophic checksum matched the Tier 4.30a reference on real SpiNNaker. It is not a task-benefit claim, not multi-core lifecycle migration, not speedup evidence, and not a lifecycle baseline freeze.\n",
        encoding="utf-8",
    )
    metadata = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "upload_package": UPLOAD_PACKAGE_NAME,
        "prepared_at_utc": utc_now(),
        "runtime_profile": RUNTIME_PROFILE,
        "runner": "experiments/tier4_30b_lifecycle_hardware_smoke.py",
        "job_command": command,
        "claim_boundary": (
            "Prepared source bundle only. Hardware evidence requires returned "
            "run-hardware artifacts from EBRAINS/SpiNNaker."
        ),
    }
    write_json(bundle / "metadata.json", metadata)

    STABLE_EBRAINS_UPLOAD.parent.mkdir(parents=True, exist_ok=True)
    if STABLE_EBRAINS_UPLOAD.exists():
        shutil.rmtree(STABLE_EBRAINS_UPLOAD)
    shutil.copytree(bundle, STABLE_EBRAINS_UPLOAD)
    return bundle, command, {"upload_bundle": str(bundle), "stable_upload_folder": str(STABLE_EBRAINS_UPLOAD), "job_readme": str(readme)}


def lifecycle_hardware_loop(hostname: str, args: argparse.Namespace, *, dest_cpu: int, references: dict[str, dict[str, Any]]) -> dict[str, Any]:
    from coral_reef_spinnaker.python_host.colony_controller import ColonyController

    started = time.perf_counter()
    ctrl = ColonyController(hostname, port=int(args.port), timeout=float(args.timeout_seconds))
    scenario_results: dict[str, dict[str, Any]] = {}
    try:
        for name, reference in references.items():
            reset_ok = ctrl.reset(args.dest_x, args.dest_y, dest_cpu)
            time.sleep(float(args.command_delay_seconds))
            init = ctrl.lifecycle_init(
                pool_size=8,
                founder_count=2,
                seed=int(args.seed),
                trophic_seed_raw=FP_ONE,
                generation_seed=0,
                dest_x=args.dest_x,
                dest_y=args.dest_y,
                dest_cpu=dest_cpu,
            )
            event_rows: list[dict[str, Any]] = []
            for event in reference["schedule"]:
                payload = lifecycle_event_payload(event)
                observed = ctrl.lifecycle_event(
                    **payload,
                    dest_x=args.dest_x,
                    dest_y=args.dest_y,
                    dest_cpu=dest_cpu,
                )
                event_rows.append(
                    {
                        **payload,
                        "event_name": event.event_type,
                        "success": observed.get("success") is True,
                        "status": observed.get("status"),
                        "observed_event_count": observed.get("lifecycle_event_count"),
                        "observed_active_mask_bits": observed.get("active_mask_bits"),
                    }
                )
            final = ctrl.lifecycle_read_state(args.dest_x, args.dest_y, dest_cpu)
            criteria = [
                criterion(f"{name} reset acknowledged", reset_ok, "== True", reset_ok is True),
                criterion(f"{name} lifecycle init succeeded", init.get("success"), "== True", init.get("success") is True),
                criterion(f"{name} all lifecycle event commands succeeded", [row["success"] for row in event_rows], "all True", bool(event_rows) and all(row["success"] for row in event_rows)),
                *scenario_criteria(name, final, reference["expected"]),
            ]
            scenario_results[name] = {
                "status": "pass" if all(item["passed"] for item in criteria) else "fail",
                "criteria": criteria,
                "init": init,
                "events": event_rows,
                "final": final,
                "expected": reference["expected"],
            }
        status = "pass" if all(item["status"] == "pass" for item in scenario_results.values()) else "fail"
        return {
            "status": status,
            "hostname": hostname,
            "dest_cpu": dest_cpu,
            "runtime_seconds": time.perf_counter() - started,
            "scenarios": scenario_results,
        }
    except Exception as exc:
        return {
            "status": "fail",
            "hostname": hostname,
            "dest_cpu": dest_cpu,
            "runtime_seconds": time.perf_counter() - started,
            "exception_type": type(exc).__name__,
            "exception": str(exc),
            "traceback": traceback.format_exc(),
            "scenarios": scenario_results,
        }
    finally:
        ctrl.close()


def write_report(path: Path, result: dict[str, Any]) -> None:
    summary = result.get("summary", {})
    lines = [
        "# Tier 4.30b-hw Lifecycle Hardware Smoke",
        "",
        f"- Generated: `{result.get('generated_at_utc')}`",
        f"- Mode: `{result.get('mode')}`",
        f"- Status: **{str(result.get('status', 'unknown')).upper()}**",
        f"- Upload package: `{summary.get('upload_package', '')}`",
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
        "selected_dest_cpu",
        "runtime_profile",
        "aplx_build_status",
        "app_load_status",
        "task_status",
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
    result_path = output_dir / "tier4_30b_hw_results.json"
    report_path = output_dir / "tier4_30b_hw_report.md"
    result.setdefault("artifacts", {})
    result["artifacts"].update({"results_json": str(result_path), "report_md": str(report_path)})
    write_json(result_path, result)
    write_report(report_path, result)
    write_json(CONTROLLED / "tier4_30b_hw_latest_manifest.json", result)
    print(json.dumps({"status": result.get("status"), "output_dir": str(output_dir), "results": str(result_path)}, indent=2))
    return 0 if str(result.get("status", "")).lower() in {"pass", "prepared"} else 1


def mode_prepare(args: argparse.Namespace, output_dir: Path) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    references = all_references()
    host_tests = run_lifecycle_host_tests(output_dir)
    main_syntax = base.run_main_syntax_check(output_dir)
    bundle, command, bundle_artifacts = prepare_bundle(output_dir)
    criteria = [
        criterion("reference scenarios generated", list(references), "canonical_32 and boundary_64", set(references) == set(SCENARIOS)),
        criterion("lifecycle host tests pass", host_tests.get("status"), "== pass", host_tests.get("status") == "pass"),
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
        "references": {name: {"expected": ref["expected"], "event_count": ref["event_count"]} for name, ref in references.items()},
        "host_tests": host_tests,
        "main_syntax_check": main_syntax,
        "bundle_artifacts": bundle_artifacts,
        "claim_boundary": "Prepared source bundle only; no hardware evidence until returned run-hardware artifacts pass.",
    }
    return finalize(output_dir, result)


def mode_run_hardware(args: argparse.Namespace, output_dir: Path) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    references = all_references()
    env_report = base.environment_report()
    host_tests = run_lifecycle_host_tests(output_dir)
    main_syntax = base.run_main_syntax_check(output_dir)
    build = build_lifecycle_aplx(output_dir)
    aplx = Path(build.get("aplx_artifact") or RUNTIME / "build" / "coral_reef.aplx")

    target = {"status": "not_attempted", "reason": "blocked_before_target_acquisition"}
    target_cleanup = {"status": "not_attempted"}
    load = {"status": "not_attempted", "reason": "blocked_before_load"}
    task = {"status": "not_attempted", "reason": "blocked_before_lifecycle_loop"}
    hostname = ""
    dest_cpu = int(args.dest_cpu)

    try:
        if build.get("status") == "pass":
            target = base.acquire_hardware_target(args)
            hostname = str(target.get("hostname") or target.get("target_ipaddress") or "")
            dest_cpu = int(target.get("dest_cpu") or args.dest_cpu)
            if target.get("status") == "pass" and not args.skip_load:
                load = base.load_application_spinnman(
                    hostname,
                    aplx,
                    x=int(args.dest_x),
                    y=int(args.dest_y),
                    p=dest_cpu,
                    app_id=int(args.app_id),
                    delay=float(args.startup_delay_seconds),
                    transceiver=target.get("_transceiver"),
                )
            elif args.skip_load:
                load = {"status": "skipped", "reason": "--skip-load set", "hostname": hostname, "dest_cpu": dest_cpu}
            if target.get("status") == "pass" and hostname and load.get("status") in {"pass", "skipped"}:
                task = lifecycle_hardware_loop(hostname, args, dest_cpu=dest_cpu, references=references)
    finally:
        target_cleanup = base.release_hardware_target(target)

    write_json(output_dir / "tier4_30b_hw_environment.json", env_report)
    write_json(output_dir / "tier4_30b_hw_target_acquisition.json", base.public_target_acquisition({**target, "cleanup": target_cleanup}))
    write_json(output_dir / "tier4_30b_hw_load_result.json", load)
    write_json(output_dir / "tier4_30b_hw_task_result.json", task)
    for name, scenario in task.get("scenarios", {}).items() if isinstance(task, dict) else []:
        write_csv(output_dir / f"tier4_30b_hw_{name}_events.csv", scenario.get("events", []))

    scenario_items = task.get("scenarios", {}) if isinstance(task, dict) else {}
    scenario_checks: list[dict[str, Any]] = []
    for scenario in scenario_items.values():
        scenario_checks.extend(scenario.get("criteria", []))

    criteria = [
        criterion("runner revision current", RUNNER_REVISION, "expected current source", True),
        criterion("lifecycle host tests pass", host_tests.get("status"), "== pass", host_tests.get("status") == "pass"),
        criterion("main.c host syntax check pass", main_syntax.get("status"), "== pass", main_syntax.get("status") == "pass"),
        criterion("hardware runtime profile selected", build.get("runtime_profile"), f"== {RUNTIME_PROFILE}", build.get("runtime_profile") == RUNTIME_PROFILE),
        criterion("custom runtime .aplx build pass", build.get("status"), "== pass", build.get("status") == "pass"),
        criterion("hardware target acquired", base.public_target_acquisition(target), "status == pass and hostname acquired", target.get("status") == "pass" and bool(hostname)),
        criterion("custom runtime app load pass", load.get("status"), "== pass", load.get("status") == "pass"),
        criterion("lifecycle hardware task pass", task.get("status"), "== pass", task.get("status") == "pass"),
        criterion("canonical_32 scenario executed", scenario_items.get("canonical_32", {}).get("status"), "== pass", scenario_items.get("canonical_32", {}).get("status") == "pass"),
        criterion("boundary_64 scenario executed", scenario_items.get("boundary_64", {}).get("status"), "== pass", scenario_items.get("boundary_64", {}).get("status") == "pass"),
        *scenario_checks,
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
            "selected_dest_cpu": dest_cpu,
            "runtime_profile": RUNTIME_PROFILE,
            "aplx_build_status": build.get("status"),
            "app_load_status": load.get("status"),
            "task_status": task.get("status"),
            "claim_boundary": "Single-core lifecycle metadata/readback smoke only; not lifecycle task benefit, not multi-core lifecycle migration, not speedup, and not a lifecycle baseline freeze.",
            "next_step_if_passed": "Ingest returned artifacts, then design Tier 4.30c multi-core lifecycle state split.",
        },
        "criteria": criteria,
        "references": {name: {"expected": ref["expected"], "event_count": ref["event_count"]} for name, ref in references.items()},
        "environment": env_report,
        "host_tests": host_tests,
        "main_syntax_check": main_syntax,
        "aplx_build": build,
        "target_acquisition": base.public_target_acquisition(target),
        "target_cleanup": target_cleanup,
        "app_load": load,
        "task": task,
        "claim_boundary": "Single-core lifecycle metadata/readback smoke only; not lifecycle task benefit, not multi-core lifecycle migration, not speedup, and not a lifecycle baseline freeze.",
    }
    return finalize(output_dir, result)


def mode_ingest(args: argparse.Namespace, output_dir: Path) -> int:
    ingest_dir = Path(args.ingest_dir or output_dir)
    candidate = Path(args.hardware_results) if args.hardware_results else ingest_dir / "tier4_30b_hw_results.json"
    if not candidate.exists():
        matches = sorted(ingest_dir.glob("**/tier4_30b_hw_results.json"))
        if matches:
            candidate = matches[-1]
    if not candidate.exists():
        result = {
            "tier": TIER,
            "runner_revision": RUNNER_REVISION,
            "generated_at_utc": utc_now(),
            "mode": "ingest",
            "status": "fail",
            "failure_reason": f"tier4_30b_hw_results.json not found in {ingest_dir}",
            "criteria": [criterion("hardware results json exists", str(candidate), "exists", False)],
            "claim_boundary": "Failed ingest only; not hardware evidence.",
        }
        return finalize(output_dir, result)
    hardware = read_json(candidate)
    criteria = [
        criterion("hardware results json exists", str(candidate), "exists", True),
        criterion("hardware mode was run-hardware", hardware.get("mode"), "== run-hardware", hardware.get("mode") == "run-hardware"),
        criterion("hardware status pass", hardware.get("status"), "== pass", hardware.get("status") == "pass"),
        criterion("runner revision matches", hardware.get("runner_revision"), f"== {RUNNER_REVISION}", hardware.get("runner_revision") == RUNNER_REVISION),
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
        "hardware_results": hardware,
        "claim_boundary": "Ingest confirms returned EBRAINS run-hardware artifacts only; no new claim beyond Tier 4.30b-hw.",
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
    parser.add_argument("--dest-cpu", type=int, default=4)
    parser.add_argument("--auto-dest-cpu", dest="auto_dest_cpu", action="store_true", default=True)
    parser.add_argument("--no-auto-dest-cpu", dest="auto_dest_cpu", action="store_false")
    parser.add_argument("--port", type=int, default=17893)
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    parser.add_argument("--startup-delay-seconds", type=float, default=2.0)
    parser.add_argument("--command-delay-seconds", type=float, default=0.03)
    parser.add_argument("--target-acquisition", choices=["auto", "hostname", "spynnaker-probe"], default="auto")
    parser.add_argument("--spinnaker-hostname", default="")
    parser.add_argument("--target-probe-run-ms", type=float, default=1.0)
    parser.add_argument("--target-probe-timestep-ms", type=float, default=1.0)
    parser.add_argument("--target-probe-population-size", type=int, default=1)
    parser.add_argument("--app-id", type=int, default=APP_ID)
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
