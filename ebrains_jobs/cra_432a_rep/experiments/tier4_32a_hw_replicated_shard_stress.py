#!/usr/bin/env python3
"""Tier 4.32a-hw-replicated single-chip replicated-shard MCPL stress.

This hardware-facing gate follows Tier 4.32a-hw and Tier 4.32a-r1. It runs the
replicated 8/12/16-core single-chip stress points that were blocked until the
MCPL lookup protocol carried shard-aware value/meta replies.

Claim boundary:
- prepare means a source-only EBRAINS upload folder and command are ready.
- run-hardware is evidence only for the executed single-chip replicated-shard
  stress, with real target acquisition, profile builds/loads, shard-aware MCPL
  lookup parity, compact per-core readback, and zero stale/duplicate/timeout
  counters.
- This is not multi-chip evidence, not speedup evidence, not static reef
  partitioning, not benchmark superiority evidence, and not a native-scale
  baseline freeze.
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
from experiments.tier4_22x_compact_v2_bridge_decoupled_smoke import (  # noqa: E402
    CONTEXT_KEY_IDS,
    MEMORY_KEY_IDS,
    ROUTE_KEY_IDS,
    TASK_SEQUENCE,
)

CONTROLLED = ROOT / "controlled_test_output"
RUNTIME = ROOT / "coral_reef_spinnaker" / "spinnaker_runtime"
TIER_NAME = "Tier 4.32a-hw-replicated - Replicated-Shard MCPL-First EBRAINS Scale Stress"
RUNNER_REVISION = "tier4_32a_hw_replicated_shard_stress_20260507_0001"
DEFAULT_PREPARE_OUTPUT = CONTROLLED / "tier4_32a_hw_replicated_20260507_prepared"
DEFAULT_RUN_OUTPUT = CONTROLLED / f"tier4_32a_hw_replicated_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_run_hardware"
DEFAULT_INGEST_OUTPUT = CONTROLLED / "tier4_32a_hw_replicated_ingested"
LATEST_MANIFEST = CONTROLLED / "tier4_32a_hw_replicated_latest_manifest.json"
UPLOAD_PACKAGE_NAME = "cra_432a_rep"
STABLE_EBRAINS_UPLOAD = ROOT / "ebrains_jobs" / UPLOAD_PACKAGE_NAME

TIER4_32A_RESULTS = CONTROLLED / "tier4_32a_20260506_single_chip_scale_stress" / "tier4_32a_results.json"
TIER4_32A_R1_RESULTS = CONTROLLED / "tier4_32a_r1_20260506_mcpl_lookup_repair" / "tier4_32a_r1_results.json"
TIER4_32A_HW_RESULTS = CONTROLLED / "tier4_32a_hw_20260507_hardware_pass_ingested" / "tier4_32a_hw_results.json"

LOOKUPS_PER_EVENT = 3
PROFILES = [
    ("context", "context_core"),
    ("route", "route_core"),
    ("memory", "memory_core"),
    ("learning", "learning_core"),
]

POINTS = [
    {"point_id": "point_08c_dual_shard", "shards": 2, "event_count": 192, "cores": 8},
    {"point_id": "point_12c_triple_shard", "shards": 3, "event_count": 384, "cores": 12},
    {"point_id": "point_16c_quad_shard", "shards": 4, "event_count": 512, "cores": 16},
]

CLAIM_BOUNDARY = (
    "Tier 4.32a-hw-replicated is a single-chip replicated-shard EBRAINS hardware "
    "stress over the repaired Tier 4.32a-r1 MCPL value/meta protocol. It is not "
    "multi-chip evidence, not speedup evidence, not static reef partitioning, "
    "not benchmark superiority evidence, and not a native-scale baseline freeze."
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
    (output_dir / "tier4_32a_hw_replicated_prepare_source_checks_stdout.txt").write_text(result["stdout"], encoding="utf-8")
    (output_dir / "tier4_32a_hw_replicated_prepare_source_checks_stderr.txt").write_text(result["stderr"], encoding="utf-8")
    return result


def py_compile_scripts(output_dir: Path) -> dict[str, Any]:
    scripts = [
        "experiments/tier4_32a_hw_replicated_shard_stress.py",
        "experiments/tier4_32a_hw_single_shard_scale_stress.py",
        "experiments/tier4_28a_four_core_mcpl_repeatability.py",
        "experiments/tier4_22i_custom_runtime_roundtrip.py",
    ]
    result = run_cmd([sys.executable, "-m", "py_compile", *scripts])
    result["status"] = "pass" if result["returncode"] == 0 else "fail"
    (output_dir / "tier4_32a_hw_replicated_py_compile_stdout.txt").write_text(result["stdout"], encoding="utf-8")
    (output_dir / "tier4_32a_hw_replicated_py_compile_stderr.txt").write_text(result["stderr"], encoding="utf-8")
    return result


def build_aplx_for_profile_shard(profile: str, shard_id: int, output_dir: Path) -> dict[str, Any]:
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
    env["MCPL_SHARD_ID"] = str(int(shard_id))

    base_aplx = RUNTIME / "build" / "coral_reef.aplx"
    if base_aplx.exists():
        base_aplx.unlink()
    result = run_cmd(["make", "-C", str(RUNTIME), "clean", "all"], env=env)
    stdout_path = output_dir / f"tier4_32a_hw_replicated_build_s{shard_id}_{profile}_stdout.txt"
    stderr_path = output_dir / f"tier4_32a_hw_replicated_build_s{shard_id}_{profile}_stderr.txt"
    stdout_path.write_text(result.get("stdout", ""), encoding="utf-8")
    stderr_path.write_text(result.get("stderr", ""), encoding="utf-8")

    profile_aplx = output_dir / f"coral_reef_s{shard_id}_{profile}.aplx"
    if base_aplx.exists():
        if profile_aplx.exists():
            profile_aplx.unlink()
        shutil.copy2(base_aplx, profile_aplx)

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
            "shard_id": int(shard_id),
            "runtime_profile": profile,
            "spinnaker_tools": tools,
            "aplx_artifact": str(profile_aplx),
            "aplx_exists": profile_aplx.exists(),
            "size_text": size_text,
            "status": "pass" if result.get("returncode") == 0 and profile_aplx.exists() else "fail",
        }
    )
    return result


def shard_core_map(shard_id: int) -> dict[str, int]:
    base_core = 1 + int(shard_id) * 4
    return {"context": base_core, "route": base_core + 1, "memory": base_core + 2, "learning": base_core + 3}


def shard_app_id(shard_id: int, role_index: int) -> int:
    return 1 + int(shard_id) * 4 + int(role_index)


def tiled_schedule(count: int, delay_steps: int = 2) -> list[dict[str, Any]]:
    schedule: list[dict[str, Any]] = []
    for index in range(int(count)):
        event = TASK_SEQUENCE[index % len(TASK_SEQUENCE)]
        schedule.append(
            {
                "timestep": index + 1,
                "context_key": int(event.get("bridge_context_key_id", 0)),
                "route_key": int(event.get("bridge_route_key_id", 0)),
                "memory_key": int(event.get("bridge_memory_key_id", 0)),
                "cue": float(event.get("bridge_visible_cue", 0.0)),
                "target": float(event.get("target", 0.0)),
                "delay": int(delay_steps),
            }
        )
    return schedule


def load_all_profiles(hostname: str, args: argparse.Namespace, target: dict[str, Any], builds: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    tx = target.get("_transceiver")
    loads: dict[str, dict[str, Any]] = {}
    for shard in range(4):
        cores = shard_core_map(shard)
        for role_index, (role, _profile) in enumerate(PROFILES):
            key = f"s{shard}_{role}"
            build = builds.get(key, {})
            if build.get("status") != "pass":
                loads[key] = {"status": "not_attempted", "reason": "build_failed"}
                continue
            loads[key] = base.load_application_spinnman(
                hostname,
                Path(build["aplx_artifact"]),
                x=int(args.dest_x),
                y=int(args.dest_y),
                p=int(cores[role]),
                app_id=shard_app_id(shard, role_index),
                delay=float(args.startup_delay_seconds),
                transceiver=tx,
            )
    return loads


def write_state_slots(ctrl: Any, args: argparse.Namespace, role: str, core: int) -> list[dict[str, Any]]:
    writes: list[dict[str, Any]] = []
    if role == "context":
        for key, key_id in CONTEXT_KEY_IDS.items():
            value, confidence = t28a.REGIME_VALUES.get(key, (0.0, 1.0))
            ok = ctrl.write_context(key_id, value, confidence, args.dest_x, args.dest_y, core)
            writes.append({"key": key, "slot": key_id, "success": ok.get("success") is True})
    elif role == "route":
        for key, key_id in ROUTE_KEY_IDS.items():
            value, confidence = t28a.REGIME_VALUES.get(key, (0.0, 1.0))
            ok = ctrl.write_route_slot(key_id, value, confidence, args.dest_x, args.dest_y, core)
            writes.append({"key": key, "slot": key_id, "success": ok.get("success") is True})
    elif role == "memory":
        for key, key_id in MEMORY_KEY_IDS.items():
            value, confidence = t28a.REGIME_VALUES.get(key, (0.0, 1.0))
            ok = ctrl.write_memory_slot(key_id, value, confidence, args.dest_x, args.dest_y, core)
            writes.append({"key": key, "slot": key_id, "success": ok.get("success") is True})
    return writes


def run_replicated_point(hostname: str, args: argparse.Namespace, point: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    from coral_reef_spinnaker.python_host.colony_controller import ColonyController

    point_id = str(point["point_id"])
    shards = int(point["shards"])
    event_count = int(point["event_count"])
    events_per_shard = event_count // shards
    point_dir = output_dir / point_id
    point_dir.mkdir(parents=True, exist_ok=True)
    ctrl = ColonyController(hostname, port=int(args.port), timeout=float(args.timeout_seconds))
    shard_results: dict[str, Any] = {}
    hardware_exception: dict[str, Any] | None = None
    waited = 0.0
    try:
        resets: dict[str, Any] = {}
        state_writes: dict[str, list[dict[str, Any]]] = {}
        schedule_uploads: dict[str, list[dict[str, Any]]] = {}
        run_cmds: dict[str, dict[str, Any]] = {}
        pauses: dict[str, dict[str, Any]] = {}
        finals: dict[str, dict[str, Any]] = {}

        for shard in range(shards):
            cores = shard_core_map(shard)
            for role, core in cores.items():
                resets[f"s{shard}_{role}"] = ctrl.reset(args.dest_x, args.dest_y, core)
                time.sleep(float(args.command_delay_seconds))

        for shard in range(shards):
            cores = shard_core_map(shard)
            for role in ("context", "route", "memory"):
                state_writes[f"s{shard}_{role}"] = write_state_slots(ctrl, args, role, cores[role])
                time.sleep(float(args.command_delay_seconds))

        schedule = tiled_schedule(events_per_shard)
        for shard in range(shards):
            uploads: list[dict[str, Any]] = []
            learning_core = shard_core_map(shard)["learning"]
            for index, entry in enumerate(schedule):
                ok = ctrl.write_schedule_entry(
                    index=index,
                    timestep=entry["timestep"],
                    context_key=entry["context_key"],
                    route_key=entry["route_key"],
                    memory_key=entry["memory_key"],
                    cue=entry["cue"],
                    target=entry["target"],
                    delay=entry["delay"],
                    dest_x=args.dest_x,
                    dest_y=args.dest_y,
                    dest_cpu=learning_core,
                )
                uploads.append({"index": index, "success": ok.get("success") is True})
                if index % 16 == 15:
                    time.sleep(float(args.command_delay_seconds))
            schedule_uploads[f"s{shard}_learning"] = uploads

        for shard in range(shards):
            cores = shard_core_map(shard)
            for role in ("context", "route", "memory"):
                run = ctrl.run_continuous(float(args.learning_rate), 0, args.dest_x, args.dest_y, cores[role])
                run_cmds[f"s{shard}_{role}"] = {"success": run.get("success") is True, "raw": run}
            learning_run = ctrl.run_continuous(float(args.learning_rate), events_per_shard, args.dest_x, args.dest_y, cores["learning"])
            run_cmds[f"s{shard}_learning"] = {"success": learning_run.get("success") is True, "raw": learning_run}
            time.sleep(float(args.command_delay_seconds))

        max_wait = float(args.max_wait_seconds)
        poll_interval = float(args.poll_interval_seconds)
        while waited < max_wait:
            time.sleep(poll_interval)
            waited += poll_interval
            complete = True
            for shard in range(shards):
                learning_core = shard_core_map(shard)["learning"]
                state = ctrl.read_state(args.dest_x, args.dest_y, learning_core)
                finals[f"s{shard}_learning_poll"] = state
                if not (
                    state.get("success") is True
                    and state.get("pending_matured") == events_per_shard
                    and state.get("active_pending") == 0
                ):
                    complete = False
            if complete:
                break

        for shard in range(shards):
            cores = shard_core_map(shard)
            for role, core in cores.items():
                pause = ctrl.pause(args.dest_x, args.dest_y, core)
                pauses[f"s{shard}_{role}"] = {"success": pause.get("success") is True, "raw": pause}
                time.sleep(float(args.command_delay_seconds))

        for shard in range(shards):
            cores = shard_core_map(shard)
            shard_final: dict[str, Any] = {}
            for role, core in cores.items():
                final = ctrl.read_state(args.dest_x, args.dest_y, core)
                shard_final[role] = final
                finals[f"s{shard}_{role}"] = final
            shard_results[f"s{shard}"] = {
                "cores": cores,
                "events_per_shard": events_per_shard,
                "expected_lookup_count": events_per_shard * LOOKUPS_PER_EVENT,
                "final_state": shard_final,
            }

        result = {
            "point_id": point_id,
            "status": "completed",
            "shards": shards,
            "event_count": event_count,
            "events_per_shard": events_per_shard,
            "expected_lookup_count_per_shard": events_per_shard * LOOKUPS_PER_EVENT,
            "reset": resets,
            "state_writes": state_writes,
            "schedule_uploads": schedule_uploads,
            "run_continuous": run_cmds,
            "pause": pauses,
            "finals_flat": finals,
            "shards_detail": shard_results,
            "waited_seconds": waited,
        }
    except Exception as exc:
        hardware_exception = {"exception_type": type(exc).__name__, "exception": str(exc), "traceback": traceback.format_exc()}
        result = {"point_id": point_id, "status": "fail", "hardware_exception": hardware_exception}
    finally:
        try:
            ctrl.close()
        except Exception:
            pass

    criteria = point_criteria(result, hardware_exception)
    status = "pass" if all(item["passed"] for item in criteria) else "fail"
    result.update({"criteria": criteria, "status": status, "hardware_exception": hardware_exception})
    write_json(point_dir / f"tier4_32a_hw_replicated_{point_id}_result.json", result)
    write_csv(point_dir / f"tier4_32a_hw_replicated_{point_id}_summary.csv", criteria)
    return result


def point_criteria(point_result: dict[str, Any], hardware_exception: dict[str, Any] | None) -> list[dict[str, Any]]:
    point_id = str(point_result.get("point_id", "unknown"))
    shards = int(point_result.get("shards") or 0)
    events_per_shard = int(point_result.get("events_per_shard") or 0)
    expected_lookup = int(point_result.get("expected_lookup_count_per_shard") or 0)
    criteria = [
        criterion(f"{point_id} no hardware exception", hardware_exception is None, "== True", hardware_exception is None),
        criterion(f"{point_id} completed", point_result.get("status"), "completed before criteria", point_result.get("status") in {"completed", "pass"}),
        criterion(f"{point_id} shard count", shards, ">= 2", shards >= 2),
        criterion(f"{point_id} events per shard within schedule buffer", events_per_shard, "<= 512", 0 < events_per_shard <= 512),
    ]
    resets = point_result.get("reset", {}) if isinstance(point_result, dict) else {}
    writes = point_result.get("state_writes", {}) if isinstance(point_result, dict) else {}
    uploads = point_result.get("schedule_uploads", {}) if isinstance(point_result, dict) else {}
    runs = point_result.get("run_continuous", {}) if isinstance(point_result, dict) else {}
    pauses = point_result.get("pause", {}) if isinstance(point_result, dict) else {}

    criteria.extend(
        [
            criterion(f"{point_id} all resets succeeded", resets, "all == True", bool(resets) and all(v is True or v.get("success") is True if isinstance(v, dict) else v is True for v in resets.values())),
            criterion(f"{point_id} all state writes succeeded", writes, "all success", bool(writes) and all(item.get("success") is True for group in writes.values() for item in group)),
            criterion(f"{point_id} all schedule uploads succeeded", uploads, "all success", bool(uploads) and all(item.get("success") is True for group in uploads.values() for item in group)),
            criterion(f"{point_id} all run_continuous succeeded", runs, "all success", bool(runs) and all(item.get("success") is True for item in runs.values())),
            criterion(f"{point_id} all pause commands succeeded", pauses, "all success", bool(pauses) and all(item.get("success") is True for item in pauses.values())),
        ]
    )

    aggregate_lookup_requests = 0
    aggregate_lookup_replies = 0
    aggregate_stale = 0
    aggregate_duplicate = 0
    aggregate_timeouts = 0
    aggregate_pending = 0
    shard_details = point_result.get("shards_detail", {}) if isinstance(point_result, dict) else {}
    for shard_key, shard in shard_details.items():
        final = shard.get("final_state", {}) if isinstance(shard, dict) else {}
        learning = final.get("learning", {}) if isinstance(final, dict) else {}
        aggregate_lookup_requests += int(learning.get("lookup_requests") or 0)
        aggregate_lookup_replies += int(learning.get("lookup_replies") or 0)
        aggregate_stale += int(learning.get("stale_replies") or 0)
        aggregate_duplicate += int(learning.get("duplicate_replies") or 0)
        aggregate_timeouts += int(learning.get("timeouts") or 0)
        aggregate_pending += int(learning.get("active_pending") or 0)
        criteria.extend(
            [
                criterion(f"{point_id} {shard_key} context read success", final.get("context", {}).get("success"), "== True", final.get("context", {}).get("success") is True),
                criterion(f"{point_id} {shard_key} route read success", final.get("route", {}).get("success"), "== True", final.get("route", {}).get("success") is True),
                criterion(f"{point_id} {shard_key} memory read success", final.get("memory", {}).get("success"), "== True", final.get("memory", {}).get("success") is True),
                criterion(f"{point_id} {shard_key} learning read success", learning.get("success"), "== True", learning.get("success") is True),
                criterion(f"{point_id} {shard_key} pending_created", learning.get("pending_created"), f"== {events_per_shard}", learning.get("pending_created") == events_per_shard),
                criterion(f"{point_id} {shard_key} pending_matured", learning.get("pending_matured"), f"== {events_per_shard}", learning.get("pending_matured") == events_per_shard),
                criterion(f"{point_id} {shard_key} active_pending", learning.get("active_pending"), "== 0", learning.get("active_pending") == 0),
                criterion(f"{point_id} {shard_key} lookup_requests", learning.get("lookup_requests"), f"== {expected_lookup}", learning.get("lookup_requests") == expected_lookup),
                criterion(f"{point_id} {shard_key} lookup_replies", learning.get("lookup_replies"), f"== {expected_lookup}", learning.get("lookup_replies") == expected_lookup),
                criterion(f"{point_id} {shard_key} stale_replies", learning.get("stale_replies"), "== 0", learning.get("stale_replies") == 0),
                criterion(f"{point_id} {shard_key} duplicate_replies", learning.get("duplicate_replies"), "== 0", learning.get("duplicate_replies") == 0),
                criterion(f"{point_id} {shard_key} timeouts", learning.get("timeouts"), "== 0", learning.get("timeouts") == 0),
                criterion(f"{point_id} {shard_key} schema_version", learning.get("schema_version"), "== 2", learning.get("schema_version") == 2),
                criterion(f"{point_id} {shard_key} readback compact", learning.get("payload_len"), ">= 105", int(learning.get("payload_len") or 0) >= 105),
            ]
        )

    criteria.extend(
        [
            criterion(f"{point_id} aggregate lookup_requests", aggregate_lookup_requests, f"== {shards * expected_lookup}", aggregate_lookup_requests == shards * expected_lookup),
            criterion(f"{point_id} aggregate lookup_replies", aggregate_lookup_replies, f"== {shards * expected_lookup}", aggregate_lookup_replies == shards * expected_lookup),
            criterion(f"{point_id} aggregate active_pending", aggregate_pending, "== 0", aggregate_pending == 0),
            criterion(f"{point_id} aggregate stale_replies", aggregate_stale, "== 0", aggregate_stale == 0),
            criterion(f"{point_id} aggregate duplicate_replies", aggregate_duplicate, "== 0", aggregate_duplicate == 0),
            criterion(f"{point_id} aggregate timeouts", aggregate_timeouts, "== 0", aggregate_timeouts == 0),
        ]
    )
    return criteria


def prepare_bundle(output_dir: Path) -> tuple[Path, str, dict[str, str]]:
    bundle_root = output_dir / "ebrains_upload_bundle"
    if bundle_root.exists():
        shutil.rmtree(bundle_root)
    bundle = bundle_root / UPLOAD_PACKAGE_NAME
    (bundle / "experiments").mkdir(parents=True, exist_ok=True)
    (bundle / "experiments" / "__init__.py").write_text("# experiments package\n", encoding="utf-8")
    (bundle / "coral_reef_spinnaker" / "python_host").mkdir(parents=True, exist_ok=True)

    scripts = [
        "tier4_32a_hw_replicated_shard_stress.py",
        "tier4_32a_hw_single_shard_scale_stress.py",
        "tier4_32a_single_chip_scale_stress.py",
        "tier4_32a_r1_mcpl_lookup_repair.py",
        "tier4_28a_four_core_mcpl_repeatability.py",
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
        f"{UPLOAD_PACKAGE_NAME}/experiments/tier4_32a_hw_replicated_shard_stress.py "
        "--mode run-hardware --output-dir tier4_32a_replicated_job_output"
    )
    readme = bundle / "README_TIER4_32A_REPLICATED_JOB.md"
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
        "This job runs the predeclared replicated-shard single-chip stress points only:\n\n"
        "- `point_08c_dual_shard`: 2 shards, 8 cores, 192 total task events.\n"
        "- `point_12c_triple_shard`: 3 shards, 12 cores, 384 total task events.\n"
        "- `point_16c_quad_shard`: 4 shards, 16 cores, 512 total task events.\n\n"
        "Each shard has independent context/route/memory/learning cores, shard-specific MCPL keys, and compact per-core readback.\n\n"
        "## Pass Boundary\n\n"
        "PASS requires real target acquisition, 16 shard-specific profile builds/loads, per-shard pending/lookup parity, zero stale/duplicate/timeout counters, returned point artifacts, and zero synthetic fallback.\n\n"
        "## Nonclaims\n\n"
        f"{CLAIM_BOUNDARY}\n",
        encoding="utf-8",
    )
    metadata = {
        "tier": TIER_NAME,
        "runner_revision": RUNNER_REVISION,
        "upload_package": UPLOAD_PACKAGE_NAME,
        "prepared_at_utc": utc_now(),
        "runner": "experiments/tier4_32a_hw_replicated_shard_stress.py",
        "job_command": command,
        "scope": [point["point_id"] for point in POINTS],
        "core_map": {f"shard_{shard}": shard_core_map(shard) for shard in range(4)},
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
    result_path = output_dir / "tier4_32a_hw_replicated_results.json"
    report_path = output_dir / "tier4_32a_hw_replicated_report.md"
    summary_path = output_dir / "tier4_32a_hw_replicated_summary.csv"
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
                    "expected_job_command": f"{UPLOAD_PACKAGE_NAME}/experiments/tier4_32a_hw_replicated_shard_stress.py --mode run-hardware --output-dir tier4_32a_replicated_job_output",
                },
                indent=2,
            )
        )
        return 1
    output_dir.mkdir(parents=True, exist_ok=True)
    tier4_32a_status = prerequisite_status(TIER4_32A_RESULTS)
    tier4_32a_r1_status = prerequisite_status(TIER4_32A_R1_RESULTS)
    tier4_32a_hw_status = prerequisite_status(TIER4_32A_HW_RESULTS)
    source_checks = run_prepare_source_checks(output_dir)
    py_compile = py_compile_scripts(output_dir)
    bundle, command, bundle_artifacts = prepare_bundle(output_dir)
    bundle_config = (bundle / "coral_reef_spinnaker" / "spinnaker_runtime" / "src" / "config.h").read_text(encoding="utf-8")
    bundle_makefile = (bundle / "coral_reef_spinnaker" / "spinnaker_runtime" / "Makefile").read_text(encoding="utf-8")
    bundle_state = (bundle / "coral_reef_spinnaker" / "spinnaker_runtime" / "src" / "state_manager.c").read_text(encoding="utf-8")
    criteria = [
        criterion("Tier 4.32a prerequisite passed", tier4_32a_status, "== pass", tier4_32a_status == "pass"),
        criterion("Tier 4.32a-r1 protocol repair passed", tier4_32a_r1_status, "== pass", tier4_32a_r1_status == "pass"),
        criterion("Tier 4.32a-hw single-shard hardware pass ingested", tier4_32a_hw_status, "== pass", tier4_32a_hw_status == "pass"),
        criterion("MCPL replicated source checks pass", source_checks.get("status"), "== pass", source_checks.get("status") == "pass"),
        criterion("runner and dependencies py_compile", py_compile.get("status"), "== pass", py_compile.get("status") == "pass"),
        criterion("upload bundle created", str(bundle), "exists", bundle.exists()),
        criterion("stable upload folder created", str(STABLE_EBRAINS_UPLOAD), "exists", STABLE_EBRAINS_UPLOAD.exists()),
        criterion("run-hardware command emitted", command, "contains --mode run-hardware", "--mode run-hardware" in command),
        criterion("bundle includes MCPL_SHARD_ID build flag", "MCPL_SHARD_ID", "present", "MCPL_SHARD_ID" in bundle_makefile),
        criterion("bundle includes shard-aware MCPL key", "MAKE_MCPL_KEY_SHARD", "present", "MAKE_MCPL_KEY_SHARD" in bundle_config),
        criterion("bundle includes value/meta MCPL replies", "MCPL_MSG_LOOKUP_REPLY_META", "present", "MCPL_MSG_LOOKUP_REPLY_META" in bundle_config),
        criterion("bundle drops wrong-shard requests", "shard_id != (CRA_MCPL_SHARD_ID", "present", "shard_id != (CRA_MCPL_SHARD_ID" in bundle_state),
        criterion("multi-chip remains nonclaim", "single_chip_only", "== single_chip_only", True),
        criterion("native-scale baseline freeze remains blocked", "not_authorized", "== not_authorized", True),
    ]
    status = "prepared" if all(item["passed"] for item in criteria) else "blocked"
    result = {
        "tier": "4.32a-hw-replicated",
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
            "scope": [point["point_id"] for point in POINTS],
            "core_map": {f"shard_{shard}": shard_core_map(shard) for shard in range(4)},
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
    write_json(output_dir / "tier4_32a_hw_replicated_environment.json", env_report)
    source_checks = run_prepare_source_checks(output_dir)
    main_syntax = base.run_main_syntax_check(output_dir)
    builds: dict[str, dict[str, Any]] = {}
    for shard in range(4):
        for role, profile in PROFILES:
            builds[f"s{shard}_{role}"] = build_aplx_for_profile_shard(profile, shard, output_dir)
            write_json(output_dir / f"tier4_32a_hw_replicated_s{shard}_{role}_build.json", builds[f"s{shard}_{role}"])

    target = base.acquire_hardware_target(args)
    hostname = str(target.get("hostname") or target.get("target_ipaddress") or "")
    write_json(output_dir / "tier4_32a_hw_replicated_target_acquisition.json", base.public_target_acquisition(target))
    loads: dict[str, dict[str, Any]] = {f"s{shard}_{role}": {"status": "not_attempted"} for shard in range(4) for role, _profile in PROFILES}
    points: dict[str, dict[str, Any]] = {point["point_id"]: {"status": "not_attempted"} for point in POINTS}
    hardware_exception: dict[str, Any] | None = None
    target_cleanup: dict[str, Any] = {"status": "not_attempted"}
    try:
        if target.get("status") == "pass" and hostname and all(build.get("status") == "pass" for build in builds.values()):
            loads = load_all_profiles(hostname, args, target, builds)
            for key, load in loads.items():
                write_json(output_dir / f"tier4_32a_hw_replicated_{key}_load.json", load)
            if all(load.get("status") == "pass" for load in loads.values()):
                for point in POINTS:
                    points[point["point_id"]] = run_replicated_point(hostname, args, point, output_dir)
    except Exception as exc:
        hardware_exception = {"exception_type": type(exc).__name__, "exception": str(exc), "traceback": traceback.format_exc()}
    finally:
        target_cleanup = base.release_hardware_target(target)
        write_json(output_dir / "tier4_32a_hw_replicated_target_acquisition.json", base.public_target_acquisition({**target, "cleanup": target_cleanup}))
        for key, load in loads.items():
            write_json(output_dir / f"tier4_32a_hw_replicated_{key}_load.json", load)

    criteria = [
        criterion("runner revision current", RUNNER_REVISION, "expected", True),
        criterion("synthetic fallback zero", 0, "== 0", True),
        criterion("source checks pass", source_checks.get("status"), "== pass", source_checks.get("status") == "pass"),
        criterion("main syntax check pass", main_syntax.get("status"), "== pass", main_syntax.get("status") == "pass"),
        criterion("hardware target acquired", base.public_target_acquisition(target), "status == pass", target.get("status") == "pass"),
        criterion("all 16 shard-specific profile builds pass", {k: v.get("status") for k, v in builds.items()}, "all == pass", bool(builds) and all(v.get("status") == "pass" for v in builds.values())),
        criterion("all 16 profile loads pass", {k: v.get("status") for k, v in loads.items()}, "all == pass", bool(loads) and all(v.get("status") == "pass" for v in loads.values())),
        criterion("no top-level hardware exception", hardware_exception is None, "== True", hardware_exception is None),
    ]
    for point in POINTS:
        point_result = points.get(point["point_id"], {})
        criteria.append(criterion(f"{point['point_id']} status pass", point_result.get("status"), "== pass", point_result.get("status") == "pass"))
        criteria.extend(point_result.get("criteria", []))
    criteria.extend(
        [
            criterion("static reef partitioning not attempted", "not_attempted", "== not_attempted", True),
            criterion("multi-chip not attempted", "not_attempted", "== not_attempted", True),
            criterion("native-scale baseline freeze not authorized", "not_authorized", "== not_authorized", True),
        ]
    )
    status = "pass" if all(item["passed"] for item in criteria) else "fail"
    result = {
        "tier": "4.32a-hw-replicated",
        "tier_name": TIER_NAME,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "mode": "run-hardware",
        "status": status,
        "failure_reason": "" if status == "pass" else "Failed criteria: " + ", ".join(item["name"] for item in criteria if not item["passed"]),
        "output_dir": str(output_dir),
        "runtime_seconds": time.perf_counter() - started,
        "summary": {
            "point08_status": points.get("point_08c_dual_shard", {}).get("status"),
            "point12_status": points.get("point_12c_triple_shard", {}).get("status"),
            "point16_status": points.get("point_16c_quad_shard", {}).get("status"),
            "single_chip_replicated_shard_only": True,
            "multi_chip_attempted": False,
            "static_reef_partitioning_attempted": False,
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
        "points": points,
        "hardware_exception": hardware_exception,
        "criteria": criteria,
        "final_decision": {
            "status": status,
            "tier4_32b_static_reef_partitioning": "authorized_next" if status == "pass" else "blocked_until_replicated_stress_passes",
            "multi_chip_scaling": "still_blocked_until_static_partitioning_and_resource_envelope",
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
        matches = sorted(ingest_dir.rglob("tier4_32a_hw_replicated_results.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        candidate = matches[0] if matches else None
    if candidate is None or not candidate.exists():
        result = {
            "tier": "4.32a-hw-replicated-ingest",
            "tier_name": TIER_NAME,
            "runner_revision": RUNNER_REVISION,
            "generated_at_utc": utc_now(),
            "mode": "ingest",
            "status": "fail",
            "failure_reason": f"tier4_32a_hw_replicated_results.json not found in {ingest_dir}",
            "criteria": [criterion("hardware results json exists", str(ingest_dir), "contains tier4_32a_hw_replicated_results.json", False)],
            "claim_boundary": "Failed ingest only; not hardware evidence.",
        }
        return finalize(output_dir, result)
    hardware = read_json(candidate)
    returned = copy_returned_artifacts(ingest_dir, output_dir, candidate)
    criteria = [
        criterion("hardware results json exists", str(candidate), "exists", True),
        criterion("hardware mode was run-hardware", hardware.get("mode"), "== run-hardware", hardware.get("mode") == "run-hardware"),
        criterion("raw hardware status pass", hardware.get("status"), "== pass", hardware.get("status") == "pass"),
        criterion("point08 pass", hardware.get("summary", {}).get("point08_status"), "== pass", hardware.get("summary", {}).get("point08_status") == "pass"),
        criterion("point12 pass", hardware.get("summary", {}).get("point12_status"), "== pass", hardware.get("summary", {}).get("point12_status") == "pass"),
        criterion("point16 pass", hardware.get("summary", {}).get("point16_status"), "== pass", hardware.get("summary", {}).get("point16_status") == "pass"),
        criterion("returned artifacts preserved", len(returned), ">= 1", len(returned) >= 1),
        criterion("single-chip replicated-shard only", hardware.get("summary", {}).get("single_chip_replicated_shard_only"), "== True", hardware.get("summary", {}).get("single_chip_replicated_shard_only") is True),
        criterion("synthetic fallback zero", hardware.get("summary", {}).get("synthetic_fallback_used"), "== False", hardware.get("summary", {}).get("synthetic_fallback_used") is False),
    ]
    status = "pass" if all(item["passed"] for item in criteria) else "fail"
    result = {
        "tier": "4.32a-hw-replicated-ingest",
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
            "point08_status": hardware.get("summary", {}).get("point08_status"),
            "point12_status": hardware.get("summary", {}).get("point12_status"),
            "point16_status": hardware.get("summary", {}).get("point16_status"),
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
        lines.append("Upload the stable `cra_432a_rep` folder to EBRAINS and run the emitted JobManager command.")
    elif result.get("status") == "pass":
        lines.append("Ingest returned artifacts before authorizing Tier 4.32b static reef partitioning/resource mapping.")
    else:
        lines.append("Classify failed criteria before rerunning or scaling.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=TIER_NAME)
    parser.add_argument("--mode", choices=["prepare", "run-hardware", "ingest"], default="prepare")
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--ingest-dir", type=Path, default=None)
    parser.add_argument("--hardware-results", type=Path, default=None)
    parser.add_argument("--dest-x", type=int, default=0)
    parser.add_argument("--dest-y", type=int, default=0)
    parser.add_argument("--port", type=int, default=17893)
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    parser.add_argument("--startup-delay-seconds", type=float, default=1.0)
    parser.add_argument("--command-delay-seconds", type=float, default=0.01)
    parser.add_argument("--poll-interval-seconds", type=float, default=0.10)
    parser.add_argument("--max-wait-seconds", type=float, default=30.0)
    parser.add_argument("--learning-rate", type=float, default=0.25)
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
            "tier": "4.32a-hw-replicated",
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
