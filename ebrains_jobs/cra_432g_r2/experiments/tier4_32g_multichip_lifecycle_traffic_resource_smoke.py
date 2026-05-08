#!/usr/bin/env python3
"""Tier 4.32g two-chip lifecycle traffic/resource hardware smoke.

This gate follows Tier 4.32g-r0. It packages and runs the smallest hardware
smoke that can prove lifecycle traffic crosses a chip boundary with compact
runtime counters:

  source chip: learning_core emits lifecycle event/trophic MCPL requests
  remote chip: lifecycle_core receives requests and broadcasts active-mask sync
  shard: 0
  traffic: trophic request + death event request + active-mask/lineage sync

Claim boundary:
- prepare means a source-only EBRAINS upload folder and exact JobManager command
  are ready; it is not hardware evidence.
- run-hardware is evidence only if returned artifacts show real target
  acquisition, profile builds/loads on two chips, lifecycle request emission,
  lifecycle-core receipt/mutation, active-mask sync receipt on the source core,
  compact readback counters, zero synthetic fallback, and zero stale/duplicate/
  missing-ack counters.
- This is not lifecycle scaling, not benchmark evidence, not speedup evidence,
  not multi-shard learning, not true partitioned organism ecology, and not a
  native-scale baseline freeze.
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

CONTROLLED = ROOT / "controlled_test_output"
RUNTIME = ROOT / "coral_reef_spinnaker" / "spinnaker_runtime"
TIER_NAME = "Tier 4.32g - Two-Chip Lifecycle Traffic/Resource Hardware Smoke"
RUNNER_REVISION = "tier4_32g_multichip_lifecycle_traffic_resource_smoke_20260508_0003"
DEFAULT_PREPARE_OUTPUT = CONTROLLED / "tier4_32g_20260508_r2_prepared"
DEFAULT_RUN_OUTPUT = CONTROLLED / f"tier4_32g_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_run_hardware"
DEFAULT_INGEST_OUTPUT = CONTROLLED / "tier4_32g_ingested"
LATEST_MANIFEST = CONTROLLED / "tier4_32g_latest_manifest.json"
INGEST_ARTIFACT_MTIME_WINDOW_SECONDS = 15 * 60
UPLOAD_PACKAGE_NAME = "cra_432g_r2"
STABLE_EBRAINS_UPLOAD = ROOT / "ebrains_jobs" / UPLOAD_PACKAGE_NAME

TIER4_32E_RESULTS = CONTROLLED / "tier4_32e_20260507_hardware_pass_ingested" / "tier4_32e_results.json"
TIER4_32F_RESULTS = CONTROLLED / "tier4_32f_20260507_multichip_resource_lifecycle_decision" / "tier4_32f_results.json"
TIER4_32G_R0_RESULTS = CONTROLLED / "tier4_32g_r0_20260507_lifecycle_route_source_audit" / "tier4_32g_r0_results.json"

FP_SHIFT = 15
FP_ONE = 1 << FP_SHIFT
SHARD_ID = 0
SOURCE_CHIP = {"x": 0, "y": 0}
REMOTE_CHIP = {"x": 1, "y": 0}
REQUEST_LINK_ROUTE = "ROUTE_E"
SYNC_LINK_ROUTE = "ROUTE_W"
POOL_SIZE = 8
FOUNDER_COUNT = 2
SEED = 42
TROPHIC_TARGET_SLOT = 0
TROPHIC_DELTA_RAW = FP_ONE // 8
DEATH_EVENT_INDEX = 1
DEATH_TARGET_SLOT = 1
EXPECTED_SOURCE_ACTIVE_MASK = 1

CORE_ROLES = {
    "learning": {"chip": "source", "profile": "learning_core", "core": 7, "app_id": 4, "link": "request_east"},
    "lifecycle": {"chip": "remote", "profile": "lifecycle_core", "core": 4, "app_id": 5, "link": "sync_west"},
}

CLAIM_BOUNDARY = (
    "Tier 4.32g is a two-chip lifecycle traffic/resource smoke. It proves only that the named "
    "source-chip learning core can emit lifecycle event/trophic MCPL requests to a remote-chip "
    "lifecycle core and receive the resulting active-mask/lineage sync through compact readback "
    "counters. It is not lifecycle scaling, not benchmark evidence, not speedup evidence, not "
    "multi-shard learning, not true partitioned ecology, and not a native-scale baseline freeze."
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


def control_ack_success(value: Any) -> bool:
    """Return True for either legacy bool ACKs or structured reply ACKs."""
    if isinstance(value, bool):
        return value is True
    if isinstance(value, dict):
        return value.get("success") is True
    return False


def prerequisite_status(path: Path) -> str:
    if not path.exists():
        return "missing"
    try:
        return str(read_json(path).get("status", "unknown")).lower()
    except Exception as exc:  # pragma: no cover - defensive artifact parsing
        return f"unreadable:{type(exc).__name__}"


def run_cmd(cmd: list[str], *, cwd: Path = ROOT, env: dict[str, str] | None = None) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=True, check=False)
    return {"command": " ".join(cmd), "returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}


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
        "test_mcpl_interchip_route_learning",
        "test_mcpl_interchip_route_context",
        "test_mcpl_lifecycle_interchip_route_learning",
        "test_mcpl_lifecycle_interchip_route_lifecycle",
        "test_mcpl_lifecycle_receive_learning",
        "test_mcpl_lifecycle_receive_lifecycle",
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
        "test-mcpl-lifecycle-receive-contract",
        "test-mcpl-lifecycle-interchip-route-contract",
        "test-lifecycle-split",
        "test-profiles",
    ]
    result = run_cmd(cmd)
    result["status"] = "pass" if result["returncode"] == 0 else "fail"
    (output_dir / "tier4_32g_prepare_source_checks_stdout.txt").write_text(result.get("stdout", ""), encoding="utf-8")
    (output_dir / "tier4_32g_prepare_source_checks_stderr.txt").write_text(result.get("stderr", ""), encoding="utf-8")
    return result


def py_compile_scripts(output_dir: Path) -> dict[str, Any]:
    scripts = [
        "experiments/tier4_32g_multichip_lifecycle_traffic_resource_smoke.py",
        "experiments/tier4_22i_custom_runtime_roundtrip.py",
    ]
    result = run_cmd([sys.executable, "-m", "py_compile", *scripts])
    result["status"] = "pass" if result["returncode"] == 0 else "fail"
    (output_dir / "tier4_32g_py_compile_stdout.txt").write_text(result.get("stdout", ""), encoding="utf-8")
    (output_dir / "tier4_32g_py_compile_stderr.txt").write_text(result.get("stderr", ""), encoding="utf-8")
    return result


def build_aplx_for_role(role: str, output_dir: Path) -> dict[str, Any]:
    spec = CORE_ROLES[role]
    profile = str(spec["profile"])
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
    env["MCPL_SHARD_ID"] = str(SHARD_ID)
    if role == "learning":
        env["MCPL_INTERCHIP_LIFECYCLE_REQUEST_LINK_ROUTE"] = REQUEST_LINK_ROUTE
    elif role == "lifecycle":
        env["MCPL_INTERCHIP_LIFECYCLE_SYNC_LINK_ROUTE"] = SYNC_LINK_ROUTE

    base_aplx = RUNTIME / "build" / "coral_reef.aplx"
    if base_aplx.exists():
        base_aplx.unlink()
    result = run_cmd(["make", "-C", str(RUNTIME), "clean", "all"], env=env)
    (output_dir / f"tier4_32g_build_{role}_{profile}_stdout.txt").write_text(result.get("stdout", ""), encoding="utf-8")
    (output_dir / f"tier4_32g_build_{role}_{profile}_stderr.txt").write_text(result.get("stderr", ""), encoding="utf-8")

    aplx_artifact = output_dir / f"coral_reef_4_32g_{role}_{profile}.aplx"
    if base_aplx.exists():
        if aplx_artifact.exists():
            aplx_artifact.unlink()
        shutil.copy2(base_aplx, aplx_artifact)

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
            "role": role,
            "profile": profile,
            "runtime_profile": profile,
            "shard_id": SHARD_ID,
            "spinnaker_tools": tools,
            "request_link_route": REQUEST_LINK_ROUTE if role == "learning" else "",
            "sync_link_route": SYNC_LINK_ROUTE if role == "lifecycle" else "",
            "aplx_artifact": str(aplx_artifact),
            "aplx_exists": aplx_artifact.exists(),
            "size_text": size_text,
            "status": "pass" if result.get("returncode") == 0 and aplx_artifact.exists() else "fail",
        }
    )
    return result


def load_profiles(hostname: str, args: argparse.Namespace, target: dict[str, Any], builds: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    loads: dict[str, dict[str, Any]] = {}
    tx = target.get("_transceiver")
    for role, spec in CORE_ROLES.items():
        build = builds.get(role, {})
        if build.get("status") != "pass":
            loads[role] = {"status": "not_attempted", "reason": "build_failed"}
            continue
        chip = SOURCE_CHIP if spec["chip"] == "source" else REMOTE_CHIP
        loads[role] = base.load_application_spinnman(
            hostname,
            Path(build["aplx_artifact"]),
            x=int(chip["x"]),
            y=int(chip["y"]),
            p=int(spec["core"]),
            app_id=int(spec["app_id"]),
            delay=float(args.startup_delay_seconds),
            transceiver=tx,
        )
    return loads


def run_lifecycle_traffic_smoke(hostname: str, args: argparse.Namespace, output_dir: Path) -> dict[str, Any]:
    from coral_reef_spinnaker.python_host.colony_controller import ColonyController

    source_x = int(args.source_x)
    source_y = int(args.source_y)
    remote_x = int(args.remote_x)
    remote_y = int(args.remote_y)
    learning_core = int(CORE_ROLES["learning"]["core"])
    lifecycle_core = int(CORE_ROLES["lifecycle"]["core"])
    ctrl = ColonyController(hostname, port=int(args.port), timeout=float(args.timeout_seconds))
    hardware_exception: dict[str, Any] | None = None
    try:
        resets = {
            "learning": ctrl.reset(source_x, source_y, learning_core),
            "lifecycle": ctrl.reset(remote_x, remote_y, lifecycle_core),
        }
        time.sleep(float(args.command_delay_seconds))
        init = ctrl.lifecycle_init(
            pool_size=POOL_SIZE,
            founder_count=FOUNDER_COUNT,
            seed=SEED,
            trophic_seed_raw=FP_ONE,
            generation_seed=0,
            dest_x=remote_x,
            dest_y=remote_y,
            dest_cpu=lifecycle_core,
        )
        time.sleep(float(args.command_delay_seconds))
        trophic_emit = ctrl.send_lifecycle_trophic_request(
            target_slot=TROPHIC_TARGET_SLOT,
            trophic_delta_raw=TROPHIC_DELTA_RAW,
            dest_x=source_x,
            dest_y=source_y,
            dest_cpu=learning_core,
        )
        time.sleep(float(args.command_delay_seconds))
        death_emit = ctrl.send_lifecycle_event_request(
            event_index=DEATH_EVENT_INDEX,
            event_type=4,  # LIFECYCLE_EVENT_DEATH in config.h
            target_slot=DEATH_TARGET_SLOT,
            dest_x=source_x,
            dest_y=source_y,
            dest_cpu=learning_core,
        )
        time.sleep(float(args.sync_wait_seconds))
        final_state = {
            "learning": ctrl.read_state(source_x, source_y, learning_core),
            "lifecycle_runtime": ctrl.read_state(remote_x, remote_y, lifecycle_core),
            "lifecycle_summary": ctrl.lifecycle_read_state(remote_x, remote_y, lifecycle_core),
        }
        pauses = {
            "learning": ctrl.pause(source_x, source_y, learning_core),
            "lifecycle": ctrl.pause(remote_x, remote_y, lifecycle_core),
        }
        task = {
            "status": "completed",
            "source_chip": {"x": source_x, "y": source_y},
            "remote_chip": {"x": remote_x, "y": remote_y},
            "core_roles": CORE_ROLES,
            "reset": resets,
            "lifecycle_init": init,
            "trophic_emit": trophic_emit,
            "death_emit": death_emit,
            "final_state": final_state,
            "pause": pauses,
        }
    except Exception as exc:
        hardware_exception = {"exception_type": type(exc).__name__, "exception": str(exc), "traceback": traceback.format_exc()}
        task = {"status": "fail", "hardware_exception": hardware_exception}
    finally:
        try:
            ctrl.close()
        except Exception:
            pass

    task["hardware_exception"] = hardware_exception
    task["criteria"] = smoke_criteria(task, hardware_exception)
    task["status"] = "pass" if all(item["passed"] for item in task["criteria"]) else "fail"
    write_json(output_dir / "tier4_32g_task_result.json", task)
    write_csv(output_dir / "tier4_32g_task_summary.csv", task["criteria"])
    return task


def smoke_criteria(task: dict[str, Any], hardware_exception: dict[str, Any] | None) -> list[dict[str, Any]]:
    final_state = task.get("final_state", {}) if isinstance(task, dict) else {}
    learning = final_state.get("learning", {}) if isinstance(final_state, dict) else {}
    lifecycle_runtime = final_state.get("lifecycle_runtime", {}) if isinstance(final_state, dict) else {}
    lifecycle_summary = final_state.get("lifecycle_summary", {}) if isinstance(final_state, dict) else {}
    resets = task.get("reset", {}) if isinstance(task, dict) else {}
    pauses = task.get("pause", {}) if isinstance(task, dict) else {}
    return [
        criterion("no hardware exception", hardware_exception is None, "== True", hardware_exception is None),
        criterion("task completed", task.get("status"), "completed/pass", task.get("status") in {"completed", "pass"}),
        criterion("source chip placement", task.get("source_chip"), f"== {SOURCE_CHIP}", task.get("source_chip") == SOURCE_CHIP),
        criterion("remote chip placement", task.get("remote_chip"), f"== {REMOTE_CHIP}", task.get("remote_chip") == REMOTE_CHIP),
        criterion("all resets succeeded", resets, "all success", bool(resets) and all(control_ack_success(v) for v in resets.values())),
        criterion("lifecycle init succeeded", task.get("lifecycle_init", {}).get("success"), "== True", task.get("lifecycle_init", {}).get("success") is True),
        criterion("trophic request emitted", task.get("trophic_emit", {}).get("success"), "== True", task.get("trophic_emit", {}).get("success") is True),
        criterion("death event emitted", task.get("death_emit", {}).get("success"), "== True", task.get("death_emit", {}).get("success") is True),
        criterion("learning read success", learning.get("success"), "== True", learning.get("success") is True),
        criterion("lifecycle runtime read success", lifecycle_runtime.get("success"), "== True", lifecycle_runtime.get("success") is True),
        criterion("lifecycle summary read success", lifecycle_summary.get("success"), "== True", lifecycle_summary.get("success") is True),
        criterion("source event request counter", learning.get("lifecycle_event_requests_sent"), "== 1", learning.get("lifecycle_event_requests_sent") == 1),
        criterion("source trophic request counter", learning.get("lifecycle_trophic_requests_sent"), "== 1", learning.get("lifecycle_trophic_requests_sent") == 1),
        criterion("source received one mask sync", learning.get("lifecycle_mask_syncs_received"), "== 1", learning.get("lifecycle_mask_syncs_received") == 1),
        criterion("source saw expected active mask", learning.get("lifecycle_last_seen_active_mask_bits"), f"== {EXPECTED_SOURCE_ACTIVE_MASK}", learning.get("lifecycle_last_seen_active_mask_bits") == EXPECTED_SOURCE_ACTIVE_MASK),
        criterion("source saw lifecycle event count", learning.get("lifecycle_last_seen_event_count"), ">= 2", int(learning.get("lifecycle_last_seen_event_count") or 0) >= 2),
        criterion("source lineage checksum present", learning.get("lifecycle_last_seen_lineage_checksum"), "> 0", int(learning.get("lifecycle_last_seen_lineage_checksum") or 0) > 0),
        criterion("lifecycle accepted trophic+death", lifecycle_runtime.get("lifecycle_event_acks_received"), "== 2", lifecycle_runtime.get("lifecycle_event_acks_received") == 2),
        criterion("lifecycle sent one mask sync", lifecycle_runtime.get("lifecycle_mask_syncs_sent"), "== 1", lifecycle_runtime.get("lifecycle_mask_syncs_sent") == 1),
        criterion("lifecycle duplicate events zero", lifecycle_runtime.get("lifecycle_duplicate_events"), "== 0", lifecycle_runtime.get("lifecycle_duplicate_events") == 0),
        criterion("lifecycle stale events zero", lifecycle_runtime.get("lifecycle_stale_events"), "== 0", lifecycle_runtime.get("lifecycle_stale_events") == 0),
        criterion("lifecycle missing acks zero", lifecycle_runtime.get("lifecycle_missing_acks"), "== 0", lifecycle_runtime.get("lifecycle_missing_acks") == 0),
        criterion("lifecycle active mask mutated", lifecycle_summary.get("active_mask_bits"), f"== {EXPECTED_SOURCE_ACTIVE_MASK}", lifecycle_summary.get("active_mask_bits") == EXPECTED_SOURCE_ACTIVE_MASK),
        criterion("lifecycle active count", lifecycle_summary.get("active_count"), "== 1", lifecycle_summary.get("active_count") == 1),
        criterion("lifecycle death count", lifecycle_summary.get("death_count"), "== 1", lifecycle_summary.get("death_count") == 1),
        criterion("lifecycle trophic update count", lifecycle_summary.get("trophic_update_count"), "== 1", lifecycle_summary.get("trophic_update_count") == 1),
        criterion("lifecycle invalid events zero", lifecycle_summary.get("invalid_event_count"), "== 0", lifecycle_summary.get("invalid_event_count") == 0),
        criterion("all pause commands succeeded", pauses, "all success", bool(pauses) and all(control_ack_success(v) for v in pauses.values())),
        criterion("learning payload includes lifecycle counters", learning.get("payload_len"), ">= 149", int(learning.get("payload_len") or 0) >= 149),
        criterion("lifecycle runtime payload includes lifecycle counters", lifecycle_runtime.get("payload_len"), ">= 149", int(lifecycle_runtime.get("payload_len") or 0) >= 149),
    ]


def top_level_criteria(
    source_checks: dict[str, Any],
    main_syntax: dict[str, Any],
    target: dict[str, Any],
    builds: dict[str, dict[str, Any]],
    loads: dict[str, dict[str, Any]],
    task: dict[str, Any],
    hardware_exception: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    return [
        criterion("runner revision current", RUNNER_REVISION, "expected", True),
        criterion("synthetic fallback zero", 0, "== 0", True),
        criterion("source checks pass", source_checks.get("status"), "== pass", source_checks.get("status") == "pass"),
        criterion("main syntax check pass", main_syntax.get("status"), "== pass", main_syntax.get("status") == "pass"),
        criterion("hardware target acquired", base.public_target_acquisition(target), "status == pass", target.get("status") == "pass"),
        criterion("both role builds pass", {k: v.get("status") for k, v in builds.items()}, "all == pass", bool(builds) and all(v.get("status") == "pass" for v in builds.values())),
        criterion("both role loads pass", {k: v.get("status") for k, v in loads.items()}, "all == pass", bool(loads) and all(v.get("status") == "pass" for v in loads.values())),
        criterion("no top-level hardware exception", hardware_exception is None, "== True", hardware_exception is None),
        criterion("lifecycle traffic smoke status pass", task.get("status"), "== pass", task.get("status") == "pass"),
        *task.get("criteria", []),
        criterion("lifecycle scaling not claimed", "not_claimed", "== not_claimed", True),
        criterion("native-scale baseline freeze not authorized", "not_authorized", "== not_authorized", True),
    ]


def prepare_bundle(output_dir: Path) -> tuple[Path, str, dict[str, str]]:
    bundle_root = output_dir / "ebrains_upload_bundle"
    if bundle_root.exists():
        shutil.rmtree(bundle_root)
    bundle = bundle_root / UPLOAD_PACKAGE_NAME
    (bundle / "experiments").mkdir(parents=True, exist_ok=True)
    (bundle / "experiments" / "__init__.py").write_text("# experiments package\n", encoding="utf-8")
    (bundle / "coral_reef_spinnaker" / "python_host").mkdir(parents=True, exist_ok=True)

    scripts = [
        "tier4_32g_multichip_lifecycle_traffic_resource_smoke.py",
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
        f"{UPLOAD_PACKAGE_NAME}/experiments/tier4_32g_multichip_lifecycle_traffic_resource_smoke.py "
        "--mode run-hardware --output-dir tier4_32g_job_output"
    )
    readme = bundle / "README_TIER4_32G_JOB.md"
    readme.write_text(
        f"# {TIER_NAME}\n\n"
        f"Upload the `{UPLOAD_PACKAGE_NAME}` folder itself so the JobManager path starts with `{UPLOAD_PACKAGE_NAME}/`. "
        "Do not upload `controlled_test_output`, the full repo, Downloads, or compiled host-test binaries.\n\n"
        "## Exact JobManager Command\n\n"
        "```text\n"
        f"{command}\n"
        "```\n\n"
        "Paste the command directly into the EBRAINS JobManager command field. Do not wrap it in `bash`, `cd`, or `python3`.\n\n"
        "## Placement Assumption\n\n"
        f"- Source/learning chip: `({SOURCE_CHIP['x']},{SOURCE_CHIP['y']})`, learning core `{CORE_ROLES['learning']['core']}`.\n"
        f"- Remote/lifecycle chip: `({REMOTE_CHIP['x']},{REMOTE_CHIP['y']})`, lifecycle core `{CORE_ROLES['lifecycle']['core']}`.\n"
        f"- Source lifecycle requests route east using `{REQUEST_LINK_ROUTE}`; lifecycle mask sync routes west using `{SYNC_LINK_ROUTE}`.\n"
        "- This is shard `0` only and sends one trophic request plus one death event request.\n\n"
        "## Pass Boundary\n\n"
        "PASS requires real target acquisition, profile builds/loads on both chips, lifecycle init, source event/trophic emission, "
        "remote lifecycle receipt/mutation, source active-mask sync receipt, compact lifecycle traffic counters, zero stale/duplicate/missing-ack counters, and zero synthetic fallback.\n\n"
        "## Nonclaims\n\n"
        f"{CLAIM_BOUNDARY}\n",
        encoding="utf-8",
    )
    metadata = {
        "tier": TIER_NAME,
        "runner_revision": RUNNER_REVISION,
        "upload_package": UPLOAD_PACKAGE_NAME,
        "prepared_at_utc": utc_now(),
        "runner": "experiments/tier4_32g_multichip_lifecycle_traffic_resource_smoke.py",
        "job_command": command,
        "source_chip": SOURCE_CHIP,
        "remote_chip": REMOTE_CHIP,
        "core_roles": CORE_ROLES,
        "traffic_contract": {
            "trophic_target_slot": TROPHIC_TARGET_SLOT,
            "trophic_delta_raw": TROPHIC_DELTA_RAW,
            "death_event_index": DEATH_EVENT_INDEX,
            "death_target_slot": DEATH_TARGET_SLOT,
            "expected_source_active_mask": EXPECTED_SOURCE_ACTIVE_MASK,
        },
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
    result_path = output_dir / "tier4_32g_results.json"
    report_path = output_dir / "tier4_32g_report.md"
    summary_path = output_dir / "tier4_32g_summary.csv"
    result["artifacts"].update({"results_json": str(result_path), "report_md": str(report_path), "summary_csv": str(summary_path)})
    write_json(result_path, result)
    write_report(report_path, result)
    write_csv(summary_path, result.get("criteria", []))
    write_json(LATEST_MANIFEST, result)
    print(json.dumps({"status": result.get("status"), "output_dir": str(output_dir), "results": str(result_path)}, indent=2))
    return 0 if str(result.get("status", "")).lower() in {"pass", "prepared"} else 1


def mode_prepare(args: argparse.Namespace, output_dir: Path) -> int:
    if ROOT.name == UPLOAD_PACKAGE_NAME and (ROOT / "metadata.json").exists():
        print(json.dumps({"status": "blocked", "reason": "Run prepare only from the full repo root; run run-hardware from the upload package."}, indent=2))
        return 1
    output_dir.mkdir(parents=True, exist_ok=True)
    tier4_32e_status = prerequisite_status(TIER4_32E_RESULTS)
    tier4_32f_status = prerequisite_status(TIER4_32F_RESULTS)
    tier4_32g_r0_status = prerequisite_status(TIER4_32G_R0_RESULTS)
    source_checks = run_prepare_source_checks(output_dir)
    py_compile = py_compile_scripts(output_dir)
    bundle, command, bundle_artifacts = prepare_bundle(output_dir)
    bundle_makefile = (bundle / "coral_reef_spinnaker" / "spinnaker_runtime" / "Makefile").read_text(encoding="utf-8")
    bundle_state = (bundle / "coral_reef_spinnaker" / "spinnaker_runtime" / "src" / "state_manager.c").read_text(encoding="utf-8")
    bundle_host = (bundle / "coral_reef_spinnaker" / "spinnaker_runtime" / "src" / "host_interface.c").read_text(encoding="utf-8")
    bundle_pyhost = (bundle / "coral_reef_spinnaker" / "python_host" / "colony_controller.py").read_text(encoding="utf-8")
    criteria = [
        criterion("Tier 4.32e hardware prerequisite passed", tier4_32e_status, "== pass", tier4_32e_status == "pass"),
        criterion("Tier 4.32f decision prerequisite passed", tier4_32f_status, "== pass", tier4_32f_status == "pass"),
        criterion("Tier 4.32g-r0 source prerequisite passed", tier4_32g_r0_status, "== pass", tier4_32g_r0_status == "pass"),
        criterion("lifecycle source checks pass", source_checks.get("status"), "== pass", source_checks.get("status") == "pass"),
        criterion("runner and dependencies py_compile", py_compile.get("status"), "== pass", py_compile.get("status") == "pass"),
        criterion("upload bundle created", str(bundle), "exists", bundle.exists()),
        criterion("stable upload folder created", str(STABLE_EBRAINS_UPLOAD), "exists", STABLE_EBRAINS_UPLOAD.exists()),
        criterion("run-hardware command emitted", command, "contains --mode run-hardware", "--mode run-hardware" in command),
        criterion("bundle Makefile exposes lifecycle request route", "MCPL_INTERCHIP_LIFECYCLE_REQUEST_LINK_ROUTE", "present", "MCPL_INTERCHIP_LIFECYCLE_REQUEST_LINK_ROUTE" in bundle_makefile),
        criterion("bundle Makefile exposes lifecycle sync route", "MCPL_INTERCHIP_LIFECYCLE_SYNC_LINK_ROUTE", "present", "MCPL_INTERCHIP_LIFECYCLE_SYNC_LINK_ROUTE" in bundle_makefile),
        criterion("bundle dispatches lifecycle receive packets", "MCPL_MSG_LIFECYCLE_EVENT_REQUEST", "present in receive", "MCPL_MSG_LIFECYCLE_EVENT_REQUEST" in bundle_state and "MCPL_MSG_LIFECYCLE_ACTIVE_MASK_SYNC" in bundle_state),
        criterion("bundle learning host emits lifecycle requests", "_handle_lifecycle_event_request_emit", "present", "_handle_lifecycle_event_request_emit" in bundle_host),
        criterion("bundle Python host has request helpers", "send_lifecycle_event_request", "present", "send_lifecycle_event_request" in bundle_pyhost and "send_lifecycle_trophic_request" in bundle_pyhost),
        criterion("bundle readback exposes lifecycle counters", "lifecycle_event_requests_sent", "present", "lifecycle_event_requests_sent" in bundle_pyhost and "lifecycle_mask_syncs_received" in bundle_pyhost),
        criterion("lifecycle scaling remains unclaimed", "not_claimed", "== not_claimed", True),
        criterion("native-scale baseline freeze remains blocked", "not_authorized", "== not_authorized", True),
    ]
    status = "prepared" if all(item["passed"] for item in criteria) else "blocked"
    result = {
        "tier": "4.32g",
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
            "what_i_need_from_user": f"Upload the {UPLOAD_PACKAGE_NAME} folder to EBRAINS/JobManager and run the emitted command.",
            "source_chip": SOURCE_CHIP,
            "remote_chip": REMOTE_CHIP,
            "core_roles": CORE_ROLES,
            "claim_boundary": "Prepared source bundle only; no hardware evidence until returned run-hardware artifacts pass.",
        },
        "criteria": criteria,
        "source_checks": source_checks,
        "py_compile": py_compile,
        "bundle_artifacts": bundle_artifacts,
        "claim_boundary": "Prepared source bundle only; no hardware evidence until returned run-hardware artifacts pass.",
    }
    return finalize(output_dir, result)


def mode_run_hardware(args: argparse.Namespace, output_dir: Path) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    env_report = base.environment_report()
    write_json(output_dir / "tier4_32g_environment.json", env_report)
    source_checks = run_prepare_source_checks(output_dir)
    main_syntax = base.run_main_syntax_check(output_dir)
    builds = {role: build_aplx_for_role(role, output_dir) for role in CORE_ROLES}
    for role, build in builds.items():
        write_json(output_dir / f"tier4_32g_{role}_build.json", build)

    target = base.acquire_hardware_target(args)
    hostname = str(target.get("hostname") or target.get("target_ipaddress") or "")
    write_json(output_dir / "tier4_32g_target_acquisition.json", base.public_target_acquisition(target))
    loads = {role: {"status": "not_attempted"} for role in CORE_ROLES}
    task: dict[str, Any] = {"status": "not_attempted"}
    hardware_exception: dict[str, Any] | None = None
    target_cleanup: dict[str, Any] = {"status": "not_attempted"}
    try:
        if target.get("status") == "pass" and hostname and all(build.get("status") == "pass" for build in builds.values()):
            loads = load_profiles(hostname, args, target, builds)
            for role, load in loads.items():
                write_json(output_dir / f"tier4_32g_{role}_load.json", load)
            if all(load.get("status") == "pass" for load in loads.values()):
                task = run_lifecycle_traffic_smoke(hostname, args, output_dir)
    except Exception as exc:
        hardware_exception = {"exception_type": type(exc).__name__, "exception": str(exc), "traceback": traceback.format_exc()}
    finally:
        target_cleanup = base.release_hardware_target(target)
        write_json(output_dir / "tier4_32g_target_acquisition.json", base.public_target_acquisition({**target, "cleanup": target_cleanup}))
        for role, load in loads.items():
            write_json(output_dir / f"tier4_32g_{role}_load.json", load)
        write_json(output_dir / "tier4_32g_task_result.json", task)

    criteria = top_level_criteria(source_checks, main_syntax, target, builds, loads, task, hardware_exception)
    status = "pass" if all(item["passed"] for item in criteria) else "fail"
    result = {
        "tier": "4.32g",
        "tier_name": TIER_NAME,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "mode": "run-hardware",
        "status": status,
        "failure_reason": "" if status == "pass" else "Failed criteria: " + ", ".join(item["name"] for item in criteria if not item["passed"]),
        "output_dir": str(output_dir),
        "runtime_seconds": time.perf_counter() - started,
        "summary": {
            "source_chip": SOURCE_CHIP,
            "remote_chip": REMOTE_CHIP,
            "core_roles": CORE_ROLES,
            "lifecycle_traffic_status": task.get("status"),
            "synthetic_fallback_used": False,
            "claim_boundary": CLAIM_BOUNDARY,
        },
        "environment": env_report,
        "source_checks": source_checks,
        "main_syntax": main_syntax,
        "target": base.public_target_acquisition(target),
        "target_cleanup": target_cleanup,
        "builds": builds,
        "loads": loads,
        "task": task,
        "hardware_exception": hardware_exception,
        "criteria": criteria,
        "final_decision": {
            "status": status,
            "next_gate": "ingest_returned_artifacts_before_authorizing_4_32h" if status == "pass" else "classify_failed_criteria_before_rerun",
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
    anchor_mtime = anchor.stat().st_mtime if anchor.exists() else None
    for path in sorted(search_root.rglob("*")):
        if not path.is_file():
            continue
        if anchor_mtime is not None and abs(path.stat().st_mtime - anchor_mtime) > INGEST_ARTIFACT_MTIME_WINDOW_SECONDS:
            continue
        rel = path.relative_to(search_root)
        dst = returned_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dst)
        copied.append(str(dst))
    return copied


def summarize_hardware_traffic_path(hardware: dict[str, Any]) -> dict[str, Any]:
    """Expose the mechanism path even when a later cleanup criterion fails."""
    task = hardware.get("task", {}) if isinstance(hardware, dict) else {}
    final_state = task.get("final_state", {}) if isinstance(task, dict) else {}
    learning = final_state.get("learning", {}) if isinstance(final_state, dict) else {}
    lifecycle_runtime = final_state.get("lifecycle_runtime", {}) if isinstance(final_state, dict) else {}
    lifecycle_summary = final_state.get("lifecycle_summary", {}) if isinstance(final_state, dict) else {}
    reset = task.get("reset", {}) if isinstance(task, dict) else {}
    pause = task.get("pause", {}) if isinstance(task, dict) else {}
    checks = {
        "source_event_request_counter": learning.get("lifecycle_event_requests_sent") == 1,
        "source_trophic_request_counter": learning.get("lifecycle_trophic_requests_sent") == 1,
        "source_mask_sync_received": learning.get("lifecycle_mask_syncs_received") == 1,
        "source_expected_active_mask_seen": learning.get("lifecycle_last_seen_active_mask_bits") == EXPECTED_SOURCE_ACTIVE_MASK,
        "source_lifecycle_event_count_seen": int(learning.get("lifecycle_last_seen_event_count") or 0) >= 2,
        "lifecycle_accepted_trophic_and_death": lifecycle_runtime.get("lifecycle_event_acks_received") == 2,
        "lifecycle_sent_mask_sync": lifecycle_runtime.get("lifecycle_mask_syncs_sent") == 1,
        "lifecycle_duplicate_zero": lifecycle_runtime.get("lifecycle_duplicate_events") == 0,
        "lifecycle_stale_zero": lifecycle_runtime.get("lifecycle_stale_events") == 0,
        "lifecycle_missing_ack_zero": lifecycle_runtime.get("lifecycle_missing_acks") == 0,
        "lifecycle_active_mask_mutated": lifecycle_summary.get("active_mask_bits") == EXPECTED_SOURCE_ACTIVE_MASK,
        "lifecycle_active_count_expected": lifecycle_summary.get("active_count") == 1,
        "lifecycle_death_count_expected": lifecycle_summary.get("death_count") == 1,
        "lifecycle_trophic_update_count_expected": lifecycle_summary.get("trophic_update_count") == 1,
        "lifecycle_invalid_events_zero": lifecycle_summary.get("invalid_event_count") == 0,
    }
    failure_classes: list[str] = []
    reset_success = isinstance(reset, dict) and bool(reset) and all(control_ack_success(v) for v in reset.values())
    pause_success = isinstance(pause, dict) and bool(pause) and all(control_ack_success(v) for v in pause.values())
    if isinstance(reset, dict) and reset and not reset_success:
        failure_classes.append("reset_control_or_criteria")
    if isinstance(pause, dict) and pause and not pause_success:
        failure_classes.append("pause_control_surface")
    return {
        "traffic_counter_core_pass": bool(checks) and all(checks.values()),
        "checks": checks,
        "failure_classes": failure_classes,
    }


def mode_ingest(args: argparse.Namespace, output_dir: Path) -> int:
    ingest_dir = args.ingest_dir or Path.home() / "Downloads"
    output_dir.mkdir(parents=True, exist_ok=True)
    candidate = args.hardware_results if args.hardware_results else None
    if candidate is None:
        matches = sorted(ingest_dir.rglob("tier4_32g_results.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        candidate = matches[0] if matches else None
    if candidate is None or not candidate.exists():
        result = {
            "tier": "4.32g-ingest",
            "tier_name": TIER_NAME,
            "runner_revision": RUNNER_REVISION,
            "generated_at_utc": utc_now(),
            "mode": "ingest",
            "status": "fail",
            "failure_reason": f"tier4_32g_results.json not found in {ingest_dir}",
            "criteria": [criterion("hardware results json exists", str(ingest_dir), "contains tier4_32g_results.json", False)],
            "claim_boundary": "Failed ingest only; not hardware evidence.",
        }
        return finalize(output_dir, result)
    hardware = read_json(candidate)
    returned = copy_returned_artifacts(ingest_dir, output_dir, candidate)
    traffic_path = summarize_hardware_traffic_path(hardware)
    criteria = [
        criterion("hardware results json exists", str(candidate), "exists", True),
        criterion("hardware mode was run-hardware", hardware.get("mode"), "== run-hardware", hardware.get("mode") == "run-hardware"),
        criterion("raw hardware status pass", hardware.get("status"), "== pass", hardware.get("status") == "pass"),
        criterion("lifecycle traffic smoke pass", hardware.get("summary", {}).get("lifecycle_traffic_status"), "== pass", hardware.get("summary", {}).get("lifecycle_traffic_status") == "pass"),
        criterion("traffic counters internally passed", traffic_path.get("traffic_counter_core_pass"), "== True", traffic_path.get("traffic_counter_core_pass") is True),
        criterion("returned artifacts preserved", len(returned), ">= 1", len(returned) >= 1),
        criterion("synthetic fallback zero", hardware.get("summary", {}).get("synthetic_fallback_used"), "== False", hardware.get("summary", {}).get("synthetic_fallback_used") is False),
    ]
    status = "pass" if all(item["passed"] for item in criteria) else "fail"
    result = {
        "tier": "4.32g-ingest",
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
            "hardware_runner_revision": hardware.get("runner_revision"),
            "ingest_runner_revision": RUNNER_REVISION,
            "stale_package_detected": hardware.get("runner_revision") != RUNNER_REVISION,
            "lifecycle_traffic_status": hardware.get("summary", {}).get("lifecycle_traffic_status"),
            "traffic_counter_core_pass": traffic_path.get("traffic_counter_core_pass"),
            "traffic_failure_classes": traffic_path.get("failure_classes"),
            "returned_artifact_count": len(returned),
        },
        "traffic_path_summary": traffic_path,
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
        lines.append(f"Upload the stable `{UPLOAD_PACKAGE_NAME}` folder to EBRAINS and run the emitted JobManager command.")
    elif result.get("status") == "pass":
        lines.append("Ingest returned artifacts before authorizing the next multi-chip native-runtime gate.")
    else:
        lines.append("Classify failed criteria before rerunning or scaling.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=TIER_NAME)
    parser.add_argument("--mode", choices=["prepare", "run-hardware", "ingest"], default="prepare")
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--ingest-dir", type=Path, default=None)
    parser.add_argument("--hardware-results", type=Path, default=None)
    parser.add_argument("--source-x", type=int, default=SOURCE_CHIP["x"])
    parser.add_argument("--source-y", type=int, default=SOURCE_CHIP["y"])
    parser.add_argument("--remote-x", type=int, default=REMOTE_CHIP["x"])
    parser.add_argument("--remote-y", type=int, default=REMOTE_CHIP["y"])
    parser.add_argument("--dest-x", type=int, default=SOURCE_CHIP["x"])
    parser.add_argument("--dest-y", type=int, default=SOURCE_CHIP["y"])
    parser.add_argument("--dest-cpu", type=int, default=CORE_ROLES["learning"]["core"])
    parser.add_argument("--port", type=int, default=17893)
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    parser.add_argument("--startup-delay-seconds", type=float, default=1.0)
    parser.add_argument("--command-delay-seconds", type=float, default=0.05)
    parser.add_argument("--sync-wait-seconds", type=float, default=0.35)
    parser.add_argument("--target-acquisition", choices=["auto", "hostname", "spynnaker-probe"], default="auto")
    parser.add_argument("--spinnaker-hostname", default="")
    parser.add_argument("--target-probe-run-ms", type=float, default=1.0)
    parser.add_argument("--target-probe-timestep-ms", type=float, default=1.0)
    parser.add_argument("--target-probe-population-size", type=int, default=1)
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
    args.dest_x = int(args.source_x)
    args.dest_y = int(args.source_y)
    args.dest_cpu = int(CORE_ROLES["learning"]["core"])
    try:
        if args.mode == "prepare":
            return mode_prepare(args, args.output_dir)
        if args.mode == "run-hardware":
            return mode_run_hardware(args, args.output_dir)
        if args.mode == "ingest":
            return mode_ingest(args, args.output_dir)
        raise ValueError(f"Unsupported mode {args.mode}")
    except Exception as exc:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        crash = {
            "tier": "4.32g",
            "tier_name": TIER_NAME,
            "runner_revision": RUNNER_REVISION,
            "generated_at_utc": utc_now(),
            "mode": getattr(args, "mode", "unknown"),
            "status": "fail",
            "exception_type": type(exc).__name__,
            "exception": str(exc),
            "traceback": traceback.format_exc(),
            "claim_boundary": "Crash artifact only; not hardware evidence.",
        }
        write_json(args.output_dir / "tier4_32g_crash.json", crash)
        write_json(args.output_dir / "tier4_32g_results.json", crash)
        print(json.dumps({"status": "fail", "exception_type": type(exc).__name__, "exception": str(exc)}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
