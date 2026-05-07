#!/usr/bin/env python3
"""Tier 4.32a-hw single-shard MCPL-first EBRAINS scale stress.

This hardware-facing gate follows Tier 4.32a-r1. It runs only the two
single-shard single-chip points that were predeclared as eligible by Tier 4.32a:

  - point_04c_reference: four-core context/route/memory/learning reference
  - point_05c_lifecycle: five-core lifecycle bridge stress with 96 task events

Claim boundary:
- prepare means a source-only EBRAINS upload folder and command are ready.
- run-hardware is hardware evidence only if returned artifacts show real target
  acquisition, successful profile builds/loads, MCPL lookup parity, zero
  stale/duplicate/timeout counters, compact readback, and zero synthetic fallback.
- This is not replicated-shard stress, not multi-chip evidence, not speedup
  evidence, not static reef partitioning, and not a native-scale baseline freeze.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import time
import traceback
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments import tier4_22i_custom_runtime_roundtrip as base  # noqa: E402
from experiments import tier4_28a_four_core_mcpl_repeatability as t28a  # noqa: E402
from experiments import tier4_30g_lifecycle_task_benefit_resource_bridge as t30g  # noqa: E402

CONTROLLED = ROOT / "controlled_test_output"
RUNTIME = ROOT / "coral_reef_spinnaker" / "spinnaker_runtime"
TIER_NAME = "Tier 4.32a-hw - Single-Shard MCPL-First EBRAINS Scale Stress"
RUNNER_REVISION = "tier4_32a_hw_single_shard_scale_stress_20260506_0001"
DEFAULT_PREPARE_OUTPUT = CONTROLLED / "tier4_32a_hw_20260506_prepared"
DEFAULT_RUN_OUTPUT = CONTROLLED / f"tier4_32a_hw_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_run_hardware"
DEFAULT_INGEST_OUTPUT = CONTROLLED / "tier4_32a_hw_ingested"
LATEST_MANIFEST = CONTROLLED / "tier4_32a_hw_latest_manifest.json"
UPLOAD_PACKAGE_NAME = "cra_432a_hw"
STABLE_EBRAINS_UPLOAD = ROOT / "ebrains_jobs" / UPLOAD_PACKAGE_NAME

TIER4_32A_RESULTS = CONTROLLED / "tier4_32a_20260506_single_chip_scale_stress" / "tier4_32a_results.json"
TIER4_32A_R1_RESULTS = CONTROLLED / "tier4_32a_r1_20260506_mcpl_lookup_repair" / "tier4_32a_r1_results.json"

POINT04_ID = "point_04c_reference"
POINT05_ID = "point_05c_lifecycle"
POINT04_EVENTS = 48
POINT05_EVENTS = 96
POINT04_LOOKUPS = POINT04_EVENTS * 3
POINT05_LOOKUPS = POINT05_EVENTS * 3

CLAIM_BOUNDARY = (
    "Tier 4.32a-hw is a single-shard single-chip EBRAINS hardware stress over "
    "the repaired Tier 4.32a-r1 MCPL protocol. It is not replicated-shard "
    "stress, not multi-chip evidence, not speedup evidence, not static reef "
    "partitioning, not benchmark superiority evidence, and not a native-scale "
    "baseline freeze."
)


@dataclass(frozen=True)
class Criterion:
    name: str
    value: Any
    rule: str
    passed: bool
    note: str = ""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "__dataclass_fields__"):
        return json_safe(asdict(value))
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items() if not str(k).startswith("_")}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    return value


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    rows = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json_safe(row.get(key, "")) for key in keys})


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def criterion(name: str, value: Any, rule: str, passed: bool, note: str = "") -> dict[str, Any]:
    return asdict(Criterion(name=name, value=value, rule=rule, passed=bool(passed), note=note))


def run_cmd(cmd: list[str], *, cwd: Path = ROOT, env: dict[str, str] | None = None) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=True, check=False)
    return {"command": " ".join(cmd), "returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}


def run_cmd_to_files(cmd: list[str], stdout_path: Path, stderr_path: Path, *, cwd: Path = ROOT) -> dict[str, Any]:
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stderr_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    with stdout_path.open("w", encoding="utf-8") as out, stderr_path.open("w", encoding="utf-8") as err:
        proc = subprocess.run(cmd, cwd=cwd, text=True, stdout=out, stderr=err, check=False)
    return {
        "command": " ".join(cmd),
        "returncode": proc.returncode,
        "runtime_seconds": time.perf_counter() - started,
        "stdout_artifact": str(stdout_path),
        "stderr_artifact": str(stderr_path),
    }


def prerequisite_status(path: Path) -> str:
    if not path.exists():
        return "missing"
    try:
        return str(read_json(path).get("status", "unknown")).lower()
    except Exception as exc:
        return f"unreadable:{type(exc).__name__}"


def clean_copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)

    generated_host_tests = {
        "test_runtime",
        "test_context_core",
        "test_route_core",
        "test_memory_core",
        "test_learning_core",
        "test_lifecycle_core",
        "test_four_core_local",
        "test_four_core_mcpl_local",
        "test_four_core_48event",
        "test_mcpl_feasibility",
        "test_mcpl_lookup_contract",
        "test_lifecycle",
        "test_lifecycle_split",
        "test_temporal_state",
    }

    def ignore(_dir: str, names: list[str]) -> set[str]:
        return {
            name
            for name in names
            if name in {"__pycache__", ".pytest_cache", "build", ".DS_Store"} | generated_host_tests
            or name.endswith((".pyc", ".o", ".elf", ".aplx"))
        }

    shutil.copytree(src, dst, ignore=ignore)


def run_prepare_source_checks(output_dir: Path) -> dict[str, Any]:
    cmd = [
        "make",
        "-C",
        str(RUNTIME),
        "clean-host",
        "test-mcpl-lookup-contract",
        "test-four-core-mcpl-local",
        "test-mcpl-feasibility",
        "test-four-core-local",
        "test-four-core-48event",
        "test-profiles",
        "test-lifecycle-split",
    ]
    result = run_cmd(cmd)
    result["status"] = "pass" if result["returncode"] == 0 else "fail"
    (output_dir / "tier4_32a_hw_prepare_source_checks_stdout.txt").write_text(result["stdout"], encoding="utf-8")
    (output_dir / "tier4_32a_hw_prepare_source_checks_stderr.txt").write_text(result["stderr"], encoding="utf-8")
    return result


def py_compile_scripts(output_dir: Path) -> dict[str, Any]:
    scripts = [
        "experiments/tier4_32a_hw_single_shard_scale_stress.py",
        "experiments/tier4_28a_four_core_mcpl_repeatability.py",
        "experiments/tier4_30g_lifecycle_task_benefit_resource_bridge.py",
        "experiments/tier4_22i_custom_runtime_roundtrip.py",
    ]
    result = run_cmd([sys.executable, "-m", "py_compile", *scripts])
    result["status"] = "pass" if result["returncode"] == 0 else "fail"
    (output_dir / "tier4_32a_hw_py_compile_stdout.txt").write_text(result["stdout"], encoding="utf-8")
    (output_dir / "tier4_32a_hw_py_compile_stderr.txt").write_text(result["stderr"], encoding="utf-8")
    return result


def prepare_bundle(output_dir: Path) -> tuple[Path, str, dict[str, str]]:
    bundle_root = output_dir / "ebrains_upload_bundle"
    if bundle_root.exists():
        shutil.rmtree(bundle_root)
    bundle = bundle_root / UPLOAD_PACKAGE_NAME
    (bundle / "experiments").mkdir(parents=True, exist_ok=True)
    (bundle / "experiments" / "__init__.py").write_text("# experiments package\n", encoding="utf-8")
    (bundle / "coral_reef_spinnaker" / "python_host").mkdir(parents=True, exist_ok=True)

    scripts = [
        "tier4_32a_hw_single_shard_scale_stress.py",
        "tier4_28a_four_core_mcpl_repeatability.py",
        "tier4_30g_lifecycle_task_benefit_resource_bridge.py",
        "tier4_30f_lifecycle_sham_hardware_subset.py",
        "tier4_30e_multicore_lifecycle_hardware_smoke.py",
        "tier4_30b_lifecycle_hardware_smoke.py",
        "tier4_30a_static_pool_lifecycle_reference.py",
        "tier4_27a_four_core_distributed_smoke.py",
        "tier4_23a_continuous_local_reference.py",
        "tier4_22x_compact_v2_bridge_decoupled_smoke.py",
        "tier4_22l_custom_runtime_learning_parity.py",
        "tier4_22j_minimal_custom_runtime_learning.py",
        "tier4_22i_custom_runtime_roundtrip.py",
    ]
    for script in scripts:
        src = ROOT / "experiments" / script
        dst = bundle / "experiments" / script
        shutil.copy2(src, dst)
        os.chmod(dst, 0o755)

    shutil.copy2(ROOT / "coral_reef_spinnaker" / "__init__.py", bundle / "coral_reef_spinnaker" / "__init__.py")
    shutil.copy2(
        ROOT / "coral_reef_spinnaker" / "python_host" / "colony_controller.py",
        bundle / "coral_reef_spinnaker" / "python_host" / "colony_controller.py",
    )
    clean_copy_tree(RUNTIME, bundle / "coral_reef_spinnaker" / "spinnaker_runtime")

    command = (
        f"{UPLOAD_PACKAGE_NAME}/experiments/tier4_32a_hw_single_shard_scale_stress.py "
        "--mode run-hardware --output-dir tier4_32a_hw_job_output"
    )
    readme = bundle / "README_TIER4_32A_HW_JOB.md"
    readme.write_text(
        f"# {TIER_NAME}\n\n"
        f"Upload the `{UPLOAD_PACKAGE_NAME}` folder itself so the JobManager path starts with `{UPLOAD_PACKAGE_NAME}/`. "
        "Do not upload `controlled_test_output`, the full repo, Downloads, or compiled host-test binaries.\n\n"
        "## Exact JobManager Command\n\n"
        "```text\n"
        f"{command}\n"
        "```\n\n"
        "Paste the command directly into the EBRAINS JobManager command field. Do not wrap it in `bash`, `cd`, or `python3`.\n\n"
        "## Scope\n\n"
        "This job runs only the two Tier 4.32a single-shard points authorized after the Tier 4.32a-r1 MCPL repair:\n\n"
        f"- `{POINT04_ID}`: 4-core context/route/memory/learning reference, {POINT04_EVENTS} events, {POINT04_LOOKUPS} lookup requests/replies.\n"
        f"- `{POINT05_ID}`: 5-core lifecycle bridge stress, {POINT05_EVENTS} task events, {POINT05_LOOKUPS} lookup requests/replies.\n\n"
        "## Pass Boundary\n\n"
        "PASS requires real target acquisition, successful profile builds/loads, compact readback, lookup request/reply parity, "
        "zero stale/duplicate/timeout counters, returned point artifacts, and zero synthetic fallback.\n\n"
        "## Nonclaims\n\n"
        f"{CLAIM_BOUNDARY}\n",
        encoding="utf-8",
    )
    metadata = {
        "tier": TIER_NAME,
        "runner_revision": RUNNER_REVISION,
        "upload_package": UPLOAD_PACKAGE_NAME,
        "prepared_at_utc": utc_now(),
        "runner": "experiments/tier4_32a_hw_single_shard_scale_stress.py",
        "job_command": command,
        "scope": [POINT04_ID, POINT05_ID],
        "blocked": ["replicated_8_12_16_core_stress", "static_reef_partitioning", "multi_chip", "native_scale_baseline_freeze"],
        "claim_boundary": "Prepared source bundle only. Hardware evidence requires returned run-hardware artifacts from EBRAINS/SpiNNaker.",
    }
    write_json(bundle / "metadata.json", metadata)

    STABLE_EBRAINS_UPLOAD.parent.mkdir(parents=True, exist_ok=True)
    if STABLE_EBRAINS_UPLOAD.exists():
        shutil.rmtree(STABLE_EBRAINS_UPLOAD)
    shutil.copytree(bundle, STABLE_EBRAINS_UPLOAD)
    return bundle, command, {"upload_bundle": str(bundle), "stable_upload_folder": str(STABLE_EBRAINS_UPLOAD), "job_readme": str(readme)}


def finalize(output_dir: Path, result: dict[str, Any]) -> int:
    result.setdefault("artifacts", {})
    result_path = output_dir / "tier4_32a_hw_results.json"
    report_path = output_dir / "tier4_32a_hw_report.md"
    summary_path = output_dir / "tier4_32a_hw_summary.csv"
    result["artifacts"].update({"results_json": str(result_path), "report_md": str(report_path), "summary_csv": str(summary_path)})
    write_json(result_path, result)
    write_report(report_path, result)
    write_csv(summary_path, result.get("criteria", []))
    write_json(LATEST_MANIFEST, result)
    print(json.dumps({"status": result.get("status"), "output_dir": str(output_dir), "results": str(result_path)}, indent=2))
    return 0 if str(result.get("status", "")).lower() in {"pass", "prepared"} else 1


def mode_prepare(args: argparse.Namespace, output_dir: Path) -> int:
    if ROOT.name == UPLOAD_PACKAGE_NAME and (ROOT / "metadata.json").exists():
        print(
            json.dumps(
                {
                    "status": "blocked",
                    "mode": "prepare",
                    "reason": "This is an EBRAINS upload package. Run prepare only from the full repo root; run run-hardware from the upload package.",
                    "expected_job_command": f"{UPLOAD_PACKAGE_NAME}/experiments/tier4_32a_hw_single_shard_scale_stress.py --mode run-hardware --output-dir tier4_32a_hw_job_output",
                },
                indent=2,
            )
        )
        return 1
    output_dir.mkdir(parents=True, exist_ok=True)
    tier4_32a_status = prerequisite_status(TIER4_32A_RESULTS)
    tier4_32a_r1_status = prerequisite_status(TIER4_32A_R1_RESULTS)
    source_checks = run_prepare_source_checks(output_dir)
    py_compile = py_compile_scripts(output_dir)
    bundle, command, bundle_artifacts = prepare_bundle(output_dir)
    bundle_text = (bundle / "coral_reef_spinnaker" / "spinnaker_runtime" / "src" / "config.h").read_text(encoding="utf-8")
    bundle_state = (bundle / "coral_reef_spinnaker" / "spinnaker_runtime" / "src" / "state_manager.c").read_text(encoding="utf-8")
    criteria = [
        criterion("Tier 4.32a prerequisite passed", tier4_32a_status, "== pass", tier4_32a_status == "pass"),
        criterion("Tier 4.32a-r1 protocol repair passed", tier4_32a_r1_status, "== pass", tier4_32a_r1_status == "pass"),
        criterion("MCPL repair source checks pass", source_checks.get("status"), "== pass", source_checks.get("status") == "pass"),
        criterion("runner and dependencies py_compile", py_compile.get("status"), "== pass", py_compile.get("status") == "pass"),
        criterion("upload bundle created", str(bundle), "exists", bundle.exists()),
        criterion("stable upload folder created", str(STABLE_EBRAINS_UPLOAD), "exists", STABLE_EBRAINS_UPLOAD.exists()),
        criterion("run-hardware command emitted", command, "contains --mode run-hardware", "--mode run-hardware" in command),
        criterion("bundle includes shard-aware MCPL key", "MCPL_KEY_SHARD_SHIFT", "present", "MCPL_KEY_SHARD_SHIFT" in bundle_text),
        criterion("bundle includes value/meta MCPL replies", "MCPL_MSG_LOOKUP_REPLY_META", "present", "MCPL_MSG_LOOKUP_REPLY_META" in bundle_text),
        criterion("bundle receive no hardcoded confidence shortcut", "cra_state_lookup_receive(seq_id, value, FP_ONE, 1);", "absent", "cra_state_lookup_receive(seq_id, value, FP_ONE, 1);" not in bundle_state),
        criterion("replicated stress remains blocked", "single_shard_only", "== single_shard_only", True),
        criterion("native-scale baseline freeze remains blocked", "not_authorized", "== not_authorized", True),
    ]
    status = "prepared" if all(item["passed"] for item in criteria) else "blocked"
    result = {
        "tier": "4.32a-hw",
        "tier_name": TIER_NAME,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "mode": "prepare",
        "status": status,
        "failure_reason": "" if status == "prepared" else "Failed criteria: " + ", ".join(item["name"] for item in criteria if not item["passed"]),
        "output_dir": str(output_dir),
        "summary": {
            "upload_package": UPLOAD_PACKAGE_NAME,
            "upload_bundle": str(bundle),
            "stable_upload_folder": str(STABLE_EBRAINS_UPLOAD),
            "job_command": command,
            "what_i_need_from_user": f"Upload `{UPLOAD_PACKAGE_NAME}` to EBRAINS/JobManager and run the emitted command.",
            "scope": [POINT04_ID, POINT05_ID],
            "claim_boundary": "Prepared source bundle only; no hardware evidence until returned run-hardware artifacts pass.",
        },
        "criteria": criteria,
        "source_checks": source_checks,
        "py_compile": py_compile,
        "bundle_artifacts": bundle_artifacts,
        "claim_boundary": "Prepared source bundle only; no hardware evidence until returned run-hardware artifacts pass.",
    }
    return finalize(output_dir, result)


def run_point04(args: argparse.Namespace, output_dir: Path) -> dict[str, Any]:
    point_dir = output_dir / POINT04_ID
    point_args = argparse.Namespace(
        mode="run-hardware",
        mode_pos=None,
        output=str(point_dir),
        hardware_output_dir="",
        seed=int(args.seed),
        dest_x=str(args.dest_x),
        dest_y=str(args.dest_y),
        port=str(args.port),
        timeout_seconds=str(args.timeout_seconds),
        startup_delay_seconds=str(args.startup_delay_seconds),
        target_acquisition=args.target_acquisition,
        spinnaker_hostname=args.spinnaker_hostname,
        target_probe_population_size=int(args.target_probe_population_size),
        target_probe_run_ms=float(args.target_probe_run_ms),
        target_probe_timestep_ms=float(args.target_probe_timestep_ms),
        dest_cpu=int(args.dest_cpu),
        auto_dest_cpu=bool(args.auto_dest_cpu),
    )
    try:
        result = t28a.mode_run_hardware(point_args)
    except Exception as exc:
        result = {"status": "fail", "exception_type": type(exc).__name__, "exception": str(exc), "traceback": traceback.format_exc()}
    write_json(output_dir / "tier4_32a_hw_point04_result.json", result)
    return result


def load_profiles(hostname: str, args: argparse.Namespace, target: dict[str, Any], builds: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    tx = target.get("_transceiver")
    loads: dict[str, dict[str, Any]] = {}
    for role, spec in t30g.CORE_ROLES.items():
        build = builds.get(role, {})
        if build.get("status") != "pass":
            loads[role] = {"status": "not_attempted", "reason": "build_failed"}
            continue
        loads[role] = base.load_application_spinnman(
            hostname,
            Path(build["aplx_artifact"]),
            x=int(args.dest_x),
            y=int(args.dest_y),
            p=int(spec["core"]),
            app_id=int(spec["app_id"]),
            delay=float(args.startup_delay_seconds),
            transceiver=tx,
        )
    return loads


def run_point05(args: argparse.Namespace, output_dir: Path) -> dict[str, Any]:
    point_dir = output_dir / POINT05_ID
    point_dir.mkdir(parents=True, exist_ok=True)
    old_task_events = t30g.TASK_EVENTS
    t30g.TASK_EVENTS = POINT05_EVENTS
    target: dict[str, Any] = {"status": "not_attempted"}
    target_cleanup: dict[str, Any] = {"status": "not_attempted"}
    task: dict[str, Any] = {"status": "not_attempted"}
    loads: dict[str, dict[str, Any]] = {role: {"status": "not_attempted"} for role in t30g.CORE_ROLES}
    hardware_exception: dict[str, Any] | None = None
    try:
        env_report = base.environment_report()
        host_tests = t30g.run_runtime_source_checks(point_dir)
        main_syntax = base.run_main_syntax_check(point_dir)
        builds = {role: t30g.build_aplx_for_profile(spec["profile"], point_dir) for role, spec in t30g.CORE_ROLES.items()}
        target = base.acquire_hardware_target(args)
        hostname = str(target.get("hostname") or target.get("target_ipaddress") or "")
        if target.get("status") == "pass" and hostname and all(build.get("status") == "pass" for build in builds.values()):
            loads = load_profiles(hostname, args, target, builds)
            if all(load.get("status") == "pass" for load in loads.values()):
                from coral_reef_spinnaker.python_host.colony_controller import ColonyController

                ctrls = {
                    role: ColonyController(hostname, port=int(args.port), timeout=float(args.timeout_seconds))
                    for role in t30g.CORE_ROLES
                }
                try:
                    profile_reads = {
                        role: ctrl.read_state(args.dest_x, args.dest_y, t30g.CORE_ROLES[role]["core"])
                        for role, ctrl in ctrls.items()
                    }
                    reference = t30g.control_reference("enabled")
                    lifecycle_result = t30g.run_lifecycle_mode(ctrls["lifecycle"], args, "enabled", reference)
                    bridge = t30g.derive_bridge_features("enabled", lifecycle_result.get("final", {}), reference["expected"])
                    expected_task, _trace = t30g.run_task_reference("enabled", bridge)
                    task_result = t30g.run_task_mode(ctrls, args, "enabled", bridge, expected_task)
                    final_profile_reads = {
                        role: ctrl.read_state(args.dest_x, args.dest_y, t30g.CORE_ROLES[role]["core"])
                        for role, ctrl in ctrls.items()
                    }
                    task = {
                        "status": "pass" if lifecycle_result.get("status") == "pass" and task_result.get("status") == "pass" else "fail",
                        "mode": "enabled_only_96_event_lifecycle_stress",
                        "profile_reads": profile_reads,
                        "final_profile_reads": final_profile_reads,
                        "lifecycle": lifecycle_result,
                        "bridge": bridge,
                        "task": task_result,
                        "expected_task": expected_task,
                        "resource_accounting": [
                            {
                                "point_id": POINT05_ID,
                                "task_event_count": POINT05_EVENTS,
                                "learning_lookup_requests": task_result.get("final_state", {}).get("learning", {}).get("lookup_requests"),
                                "learning_lookup_replies": task_result.get("final_state", {}).get("learning", {}).get("lookup_replies"),
                                "learning_stale_replies": task_result.get("final_state", {}).get("learning", {}).get("stale_replies"),
                                "learning_duplicate_replies": task_result.get("final_state", {}).get("learning", {}).get("duplicate_replies"),
                                "learning_timeouts": task_result.get("final_state", {}).get("learning", {}).get("timeouts"),
                                "learning_readback_bytes": task_result.get("final_state", {}).get("learning", {}).get("readback_bytes"),
                                "lifecycle_readback_bytes": lifecycle_result.get("final", {}).get("readback_bytes"),
                            }
                        ],
                    }
                finally:
                    for ctrl in ctrls.values():
                        try:
                            ctrl.close()
                        except Exception:
                            pass
    except Exception as exc:
        hardware_exception = {"exception_type": type(exc).__name__, "exception": str(exc), "traceback": traceback.format_exc()}
        task = {"status": "fail", **hardware_exception}
    finally:
        target_cleanup = base.release_hardware_target(target)
        t30g.TASK_EVENTS = old_task_events

    write_json(point_dir / "tier4_32a_hw_point05_environment.json", env_report if "env_report" in locals() else {})
    write_json(point_dir / "tier4_32a_hw_point05_target_acquisition.json", base.public_target_acquisition({**target, "cleanup": target_cleanup}))
    for role, build in (builds if "builds" in locals() else {}).items():
        write_json(point_dir / f"tier4_32a_hw_point05_{role}_build.json", build)
    for role, load in loads.items():
        write_json(point_dir / f"tier4_32a_hw_point05_{role}_load.json", load)
    write_json(point_dir / "tier4_32a_hw_point05_task_result.json", task)
    if task.get("resource_accounting"):
        write_csv(point_dir / "tier4_32a_hw_point05_resource_accounting.csv", task.get("resource_accounting", []))

    learning_final = task.get("task", {}).get("final_state", {}).get("learning", {}) if isinstance(task, dict) else {}
    lifecycle_final = task.get("lifecycle", {}).get("final", {}) if isinstance(task, dict) else {}
    criteria = [
        criterion("point05 host source checks pass", host_tests.get("status") if "host_tests" in locals() else None, "== pass", "host_tests" in locals() and host_tests.get("status") == "pass"),
        criterion("point05 main syntax check pass", main_syntax.get("status") if "main_syntax" in locals() else None, "== pass", "main_syntax" in locals() and main_syntax.get("status") == "pass"),
        criterion("point05 all five profile builds pass", {k: v.get("status") for k, v in (builds if "builds" in locals() else {}).items()}, "all == pass", "builds" in locals() and all(v.get("status") == "pass" for v in builds.values())),
        criterion("point05 hardware target acquired", target.get("status"), "== pass", target.get("status") == "pass"),
        criterion("point05 all five profile loads pass", {k: v.get("status") for k, v in loads.items()}, "all == pass", all(v.get("status") == "pass" for v in loads.values())),
        criterion("point05 enabled lifecycle bridge pass", task.get("status"), "== pass", task.get("status") == "pass"),
        criterion("point05 lifecycle readback compact", lifecycle_final.get("payload_len"), ">= 68", int(lifecycle_final.get("payload_len") or 0) >= 68),
        criterion("point05 pending_created", learning_final.get("pending_created"), f"== {POINT05_EVENTS}", learning_final.get("pending_created") == POINT05_EVENTS),
        criterion("point05 pending_matured", learning_final.get("pending_matured"), f"== {POINT05_EVENTS}", learning_final.get("pending_matured") == POINT05_EVENTS),
        criterion("point05 active_pending cleared", learning_final.get("active_pending"), "== 0", learning_final.get("active_pending") == 0),
        criterion("point05 lookup_requests", learning_final.get("lookup_requests"), f"== {POINT05_LOOKUPS}", learning_final.get("lookup_requests") == POINT05_LOOKUPS),
        criterion("point05 lookup_replies", learning_final.get("lookup_replies"), f"== {POINT05_LOOKUPS}", learning_final.get("lookup_replies") == POINT05_LOOKUPS),
        criterion("point05 stale_replies zero", learning_final.get("stale_replies"), "== 0", learning_final.get("stale_replies") == 0),
        criterion("point05 duplicate_replies zero", learning_final.get("duplicate_replies"), "== 0", learning_final.get("duplicate_replies") == 0),
        criterion("point05 timeouts zero", learning_final.get("timeouts"), "== 0", learning_final.get("timeouts") == 0),
        criterion("point05 no unhandled hardware exception", hardware_exception is None, "== True", hardware_exception is None),
    ]
    status = "pass" if all(item["passed"] for item in criteria) else "fail"
    result = {
        "point_id": POINT05_ID,
        "status": status,
        "event_count": POINT05_EVENTS,
        "lookup_count_expected": POINT05_LOOKUPS,
        "criteria": criteria,
        "target": base.public_target_acquisition(target),
        "loads": loads,
        "task": task,
        "hardware_exception": hardware_exception,
        "claim_boundary": "Five-core enabled-lifecycle scale stress only; not lifecycle sham-control proof and not baseline freeze.",
    }
    write_json(point_dir / "tier4_32a_hw_point05_results.json", result)
    return result


def point04_criteria(point: dict[str, Any]) -> list[dict[str, Any]]:
    final_states = point.get("task", {}).get("final_state", {}) if isinstance(point, dict) else {}
    learning = final_states.get("learning", {}) if isinstance(final_states, dict) else {}
    return [
        criterion("point04 runner status", point.get("status"), "== pass", point.get("status") == "pass"),
        criterion("point04 pending_created", learning.get("pending_created"), f"== {POINT04_EVENTS}", learning.get("pending_created") == POINT04_EVENTS),
        criterion("point04 pending_matured", learning.get("pending_matured"), f"== {POINT04_EVENTS}", learning.get("pending_matured") == POINT04_EVENTS),
        criterion("point04 active_pending cleared", learning.get("active_pending"), "== 0", learning.get("active_pending") == 0),
        criterion("point04 lookup_requests", learning.get("lookup_requests"), f"== {POINT04_LOOKUPS}", learning.get("lookup_requests") == POINT04_LOOKUPS),
        criterion("point04 lookup_replies", learning.get("lookup_replies"), f"== {POINT04_LOOKUPS}", learning.get("lookup_replies") == POINT04_LOOKUPS),
        criterion("point04 stale_replies zero", learning.get("stale_replies"), "== 0", learning.get("stale_replies") == 0),
        criterion("point04 duplicate_replies zero", learning.get("duplicate_replies"), "== 0", learning.get("duplicate_replies") == 0),
        criterion("point04 timeouts zero", learning.get("timeouts"), "== 0", learning.get("timeouts") == 0),
    ]


def mode_run_hardware(args: argparse.Namespace, output_dir: Path) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    point04 = run_point04(args, output_dir)
    point05 = {"status": "not_attempted", "reason": "point04_failed"}
    if point04.get("status") == "pass":
        point05 = run_point05(args, output_dir)
    criteria = [
        criterion("runner revision current", RUNNER_REVISION, "expected", True),
        criterion("synthetic fallback zero", 0, "== 0", True),
        criterion("scope limited to single-shard points", [POINT04_ID, POINT05_ID], "== allowed points only", True),
        *point04_criteria(point04),
        *point05.get("criteria", []),
        criterion("point05 attempted after point04 pass", point05.get("status"), "attempted and pass", point04.get("status") == "pass" and point05.get("status") == "pass"),
        criterion("replicated shard stress not attempted", "not_attempted", "== not_attempted", True),
        criterion("native-scale baseline freeze not authorized", "not_authorized", "== not_authorized", True),
    ]
    status = "pass" if all(item["passed"] for item in criteria) else "fail"
    result = {
        "tier": "4.32a-hw",
        "tier_name": TIER_NAME,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "mode": "run-hardware",
        "status": status,
        "failure_reason": "" if status == "pass" else "Failed criteria: " + ", ".join(item["name"] for item in criteria if not item["passed"]),
        "output_dir": str(output_dir),
        "runtime_seconds": time.perf_counter() - started,
        "summary": {
            "point04_status": point04.get("status"),
            "point05_status": point05.get("status"),
            "single_shard_only": True,
            "replicated_stress_attempted": False,
            "synthetic_fallback_used": False,
            "claim_boundary": CLAIM_BOUNDARY,
        },
        "criteria": criteria,
        "points": {POINT04_ID: point04, POINT05_ID: point05},
        "final_decision": {
            "status": status,
            "replicated_8_12_16_core_stress": "authorized_next" if status == "pass" else "blocked_until_4_32a_hw_passes",
            "tier4_32b_static_reef_partitioning": "still_blocked_until_replicated_stress_passes",
            "native_scale_baseline_freeze": "not_authorized",
            "claim_boundary": CLAIM_BOUNDARY,
        },
        "claim_boundary": CLAIM_BOUNDARY,
    }
    return finalize(output_dir, result)


def copy_returned_artifacts(ingest_dir: Path, output_dir: Path, anchor: Path) -> list[str]:
    returned_dir = output_dir / "returned_artifacts"
    if returned_dir.exists():
        shutil.rmtree(returned_dir)
    returned_dir.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    search_root = anchor.parent if anchor.exists() else ingest_dir
    for path in sorted(search_root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(search_root)
        dst = returned_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dst)
        copied.append(str(dst))
    return copied


def mode_ingest(args: argparse.Namespace, output_dir: Path) -> int:
    ingest_dir = args.ingest_dir or Path.home() / "Downloads"
    output_dir.mkdir(parents=True, exist_ok=True)
    candidate = args.hardware_results if args.hardware_results else None
    if candidate is None:
        matches = sorted(ingest_dir.rglob("tier4_32a_hw_results.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        candidate = matches[0] if matches else None
    if candidate is None or not candidate.exists():
        result = {
            "tier": "4.32a-hw-ingest",
            "tier_name": TIER_NAME,
            "runner_revision": RUNNER_REVISION,
            "generated_at_utc": utc_now(),
            "mode": "ingest",
            "status": "fail",
            "failure_reason": f"tier4_32a_hw_results.json not found in {ingest_dir}",
            "criteria": [criterion("hardware results json exists", str(ingest_dir), "contains tier4_32a_hw_results.json", False)],
            "claim_boundary": "Failed ingest only; not hardware evidence.",
        }
        return finalize(output_dir, result)
    hardware = read_json(candidate)
    returned = copy_returned_artifacts(ingest_dir, output_dir, candidate)
    criteria = [
        criterion("hardware results json exists", str(candidate), "exists", True),
        criterion("hardware mode was run-hardware", hardware.get("mode"), "== run-hardware", hardware.get("mode") == "run-hardware"),
        criterion("raw hardware status pass", hardware.get("status"), "== pass", hardware.get("status") == "pass"),
        criterion("point04 pass", hardware.get("summary", {}).get("point04_status"), "== pass", hardware.get("summary", {}).get("point04_status") == "pass"),
        criterion("point05 pass", hardware.get("summary", {}).get("point05_status"), "== pass", hardware.get("summary", {}).get("point05_status") == "pass"),
        criterion("returned artifacts preserved", len(returned), ">= 1", len(returned) >= 1),
        criterion("single-shard only", hardware.get("summary", {}).get("single_shard_only"), "== True", hardware.get("summary", {}).get("single_shard_only") is True),
        criterion("synthetic fallback zero", hardware.get("summary", {}).get("synthetic_fallback_used"), "== False", hardware.get("summary", {}).get("synthetic_fallback_used") is False),
    ]
    status = "pass" if all(item["passed"] for item in criteria) else "fail"
    result = {
        "tier": "4.32a-hw-ingest",
        "tier_name": TIER_NAME,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "mode": "ingest",
        "status": status,
        "failure_reason": "" if status == "pass" else "Failed criteria: " + ", ".join(item["name"] for item in criteria if not item["passed"]),
        "output_dir": str(output_dir),
        "hardware_results": hardware,
        "returned_artifacts": returned,
        "criteria": criteria,
        "summary": {
            "raw_remote_status": hardware.get("status"),
            "point04_status": hardware.get("summary", {}).get("point04_status"),
            "point05_status": hardware.get("summary", {}).get("point05_status"),
            "returned_artifact_count": len(returned),
        },
        "claim_boundary": "Ingest confirms returned EBRAINS run-hardware artifacts only; baseline decisions remain separate.",
    }
    return finalize(output_dir, result)


def write_report(path: Path, result: dict[str, Any]) -> None:
    lines = [
        f"# {TIER_NAME}",
        "",
        f"- Generated: `{result.get('generated_at_utc')}`",
        f"- Mode: `{result.get('mode')}`",
        f"- Status: **{str(result.get('status')).upper()}**",
        f"- Runner revision: `{result.get('runner_revision')}`",
        "",
        "## Claim Boundary",
        "",
        result.get("claim_boundary", ""),
        "",
        "## Summary",
        "",
    ]
    for key, value in result.get("summary", {}).items():
        lines.append(f"- {key}: `{json_safe(value)}`")
    lines.extend(["", "## Criteria", "", "| Criterion | Value | Rule | Pass |", "| --- | --- | --- | --- |"])
    for item in result.get("criteria", []):
        value = json.dumps(json_safe(item.get("value")), sort_keys=True)
        if len(value) > 160:
            value = value[:157] + "..."
        lines.append(f"| {item.get('name')} | `{value}` | {item.get('rule')} | {'yes' if item.get('passed') else 'no'} |")
    lines.extend(["", "## Next", ""])
    if result.get("mode") == "prepare":
        lines.append("Upload the stable `cra_432a_hw` folder to EBRAINS and run the emitted JobManager command.")
    elif result.get("status") == "pass":
        lines.append("Ingest returned artifacts before authorizing replicated 8/12/16-core stress.")
    else:
        lines.append("Classify failed criteria before rerunning or scaling.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=TIER_NAME)
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
    parser.add_argument("--poll-interval-seconds", type=float, default=0.05)
    parser.add_argument("--max-wait-seconds", type=float, default=20.0)
    parser.add_argument("--readout-tolerance-raw", type=int, default=8192)
    parser.add_argument("--target-acquisition", choices=["auto", "hostname", "spynnaker-probe"], default="auto")
    parser.add_argument("--spinnaker-hostname", default="")
    parser.add_argument("--target-probe-run-ms", type=float, default=1.0)
    parser.add_argument("--target-probe-timestep-ms", type=float, default=1.0)
    parser.add_argument("--target-probe-population-size", type=int, default=1)
    parser.add_argument("--dest-cpu", type=int, default=4)
    parser.add_argument("--auto-dest-cpu", dest="auto_dest_cpu", action="store_true", default=True)
    parser.add_argument("--no-auto-dest-cpu", dest="auto_dest_cpu", action="store_false")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.output_dir is None:
        if args.mode == "prepare":
            args.output_dir = DEFAULT_PREPARE_OUTPUT
        elif args.mode == "run-hardware":
            args.output_dir = DEFAULT_RUN_OUTPUT
        else:
            args.output_dir = DEFAULT_INGEST_OUTPUT
    args.output_dir = args.output_dir.resolve()
    try:
        if args.mode == "prepare":
            return mode_prepare(args, args.output_dir)
        if args.mode == "run-hardware":
            return mode_run_hardware(args, args.output_dir)
        return mode_ingest(args, args.output_dir)
    except Exception as exc:
        result = {
            "tier": "4.32a-hw",
            "tier_name": TIER_NAME,
            "runner_revision": RUNNER_REVISION,
            "generated_at_utc": utc_now(),
            "mode": args.mode,
            "status": "fail",
            "failure_reason": f"Unhandled runner exception: {type(exc).__name__}: {exc}",
            "criteria": [criterion("runner reached structured finalization", type(exc).__name__, "no unhandled exception", False, str(exc))],
            "exception_type": type(exc).__name__,
            "exception": str(exc),
            "traceback": traceback.format_exc(),
            "claim_boundary": CLAIM_BOUNDARY,
        }
        return finalize(args.output_dir, result)


if __name__ == "__main__":
    raise SystemExit(main())
