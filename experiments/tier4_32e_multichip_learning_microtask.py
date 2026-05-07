#!/usr/bin/env python3
"""Tier 4.32e multi-chip learning micro-task.

This gate follows the Tier 4.32d hardware pass. It packages and runs the
smallest learning-bearing hardware task over the repaired cross-chip MCPL
lookup path:

  source chip: learning_core
  remote chip: context_core, route_core, memory_core
  shard: 0
  schedule: 32 events, 96 lookup requests/replies per case
  cases: enabled learning and no-learning control

Claim boundary:
- prepare means a source-only EBRAINS upload folder and exact JobManager command
  are ready; it is not hardware evidence.
- run-hardware is hardware evidence only if returned artifacts show real target
  acquisition, profile builds/loads on two chips, successful state writes,
  lookup request/reply parity, zero stale/duplicate/timeout counters, compact
  readback, enabled readout movement, no-learning immobility, and zero synthetic
  fallback.
- This is not speedup evidence, not benchmark evidence, not true two-partition
  learning, not lifecycle scaling, and not a native-scale baseline freeze.
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
TIER_NAME = "Tier 4.32e - Multi-Chip Learning Micro-Task"
RUNNER_REVISION = "tier4_32e_multichip_learning_microtask_20260507_0001"
DEFAULT_PREPARE_OUTPUT = CONTROLLED / "tier4_32e_20260507_prepared"
DEFAULT_RUN_OUTPUT = CONTROLLED / f"tier4_32e_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_run_hardware"
DEFAULT_INGEST_OUTPUT = CONTROLLED / "tier4_32e_ingested"
LATEST_MANIFEST = CONTROLLED / "tier4_32e_latest_manifest.json"
INGEST_ARTIFACT_MTIME_WINDOW_SECONDS = 15 * 60
UPLOAD_PACKAGE_NAME = "cra_432e"
STABLE_EBRAINS_UPLOAD = ROOT / "ebrains_jobs" / UPLOAD_PACKAGE_NAME

TIER4_32C_RESULTS = CONTROLLED / "tier4_32c_20260507_interchip_feasibility_contract" / "tier4_32c_results.json"
TIER4_32D_RESULTS = CONTROLLED / "tier4_32d_20260507_hardware_pass_ingested" / "tier4_32d_results.json"
TIER4_32D_R0_RESULTS = CONTROLLED / "tier4_32d_r0_20260507_interchip_route_source_audit" / "tier4_32d_r0_results.json"
TIER4_32D_R1_RESULTS = CONTROLLED / "tier4_32d_r1_20260507_interchip_route_repair_local_qa" / "tier4_32d_r1_results.json"

LOOKUPS_PER_EVENT = 3
EVENT_COUNT = 32
EXPECTED_LOOKUPS = EVENT_COUNT * LOOKUPS_PER_EVENT
FP_SHIFT = 15
FP_ONE = 1 << FP_SHIFT
SURPRISE_THRESHOLD_RAW = 2 * FP_ONE
SHARD_ID = 0
SOURCE_CHIP = {"x": 0, "y": 0}
REMOTE_CHIP = {"x": 1, "y": 0}
REQUEST_LINK_ROUTE = "ROUTE_E"
REPLY_LINK_ROUTE = "ROUTE_W"
LEARNING_CASES = [
    {"label": "enabled_lr_0_25", "learning_rate": 0.25, "kind": "enabled"},
    {"label": "no_learning_lr_0_00", "learning_rate": 0.0, "kind": "no_learning"},
]

CORE_ROLES = {
    "context": {"chip": "remote", "profile": "context_core", "core": 4, "app_id": 1, "link": "reply_west"},
    "route": {"chip": "remote", "profile": "route_core", "core": 5, "app_id": 2, "link": "reply_west"},
    "memory": {"chip": "remote", "profile": "memory_core", "core": 6, "app_id": 3, "link": "reply_west"},
    "learning": {"chip": "source", "profile": "learning_core", "core": 7, "app_id": 4, "link": "request_east"},
}

CLAIM_BOUNDARY = (
    "Tier 4.32e is a two-chip split-role single-shard learning micro-task over the MCPL "
    "lookup path. It proves only that the named source-chip learning core can retrieve "
    "remote context/route/memory state from the remote chip and update its readout on a "
    "32-event deterministic task while a no-learning control stays immobile. It is not "
    "speedup evidence, not benchmark evidence, not true two-partition learning, not "
    "lifecycle scaling, not multi-shard learning, and not a native-scale baseline freeze."
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
        "test_mcpl_interchip_route_learning",
        "test_mcpl_interchip_route_context",
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
        "test-mcpl-interchip-route-contract",
        "test-mcpl-lookup-contract",
        "test-four-core-mcpl-local",
        "test-four-core-48event",
    ]
    result = run_cmd(cmd)
    result["status"] = "pass" if result["returncode"] == 0 else "fail"
    (output_dir / "tier4_32e_prepare_source_checks_stdout.txt").write_text(result.get("stdout", ""), encoding="utf-8")
    (output_dir / "tier4_32e_prepare_source_checks_stderr.txt").write_text(result.get("stderr", ""), encoding="utf-8")
    return result


def py_compile_scripts(output_dir: Path) -> dict[str, Any]:
    scripts = [
        "experiments/tier4_32e_multichip_learning_microtask.py",
        "experiments/tier4_28a_four_core_mcpl_repeatability.py",
        "experiments/tier4_22i_custom_runtime_roundtrip.py",
        "experiments/tier4_22x_compact_v2_bridge_decoupled_smoke.py",
    ]
    result = run_cmd([sys.executable, "-m", "py_compile", *scripts])
    result["status"] = "pass" if result["returncode"] == 0 else "fail"
    (output_dir / "tier4_32e_py_compile_stdout.txt").write_text(result.get("stdout", ""), encoding="utf-8")
    (output_dir / "tier4_32e_py_compile_stderr.txt").write_text(result.get("stderr", ""), encoding="utf-8")
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
        env["MCPL_INTERCHIP_REQUEST_LINK_ROUTE"] = REQUEST_LINK_ROUTE
    else:
        env["MCPL_INTERCHIP_REPLY_LINK_ROUTE"] = REPLY_LINK_ROUTE

    base_aplx = RUNTIME / "build" / "coral_reef.aplx"
    if base_aplx.exists():
        base_aplx.unlink()
    result = run_cmd(["make", "-C", str(RUNTIME), "clean", "all"], env=env)
    stdout_path = output_dir / f"tier4_32e_build_{role}_{profile}_stdout.txt"
    stderr_path = output_dir / f"tier4_32e_build_{role}_{profile}_stderr.txt"
    stdout_path.write_text(result.get("stdout", ""), encoding="utf-8")
    stderr_path.write_text(result.get("stderr", ""), encoding="utf-8")

    aplx_artifact = output_dir / f"coral_reef_4_32e_{role}_{profile}.aplx"
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
            "reply_link_route": REPLY_LINK_ROUTE if role != "learning" else "",
            "aplx_artifact": str(aplx_artifact),
            "aplx_exists": aplx_artifact.exists(),
            "size_text": size_text,
            "status": "pass" if result.get("returncode") == 0 and aplx_artifact.exists() else "fail",
        }
    )
    return result


def build_schedule(count: int = EVENT_COUNT, delay_steps: int = 2) -> list[dict[str, Any]]:
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


def fp_from_float(value: float) -> int:
    return int(float(value) * FP_ONE)


def fp_mul(left: int, right: int) -> int:
    return int((int(left) * int(right)) >> FP_SHIFT)


def slot_value_maps() -> dict[str, dict[int, tuple[int, int]]]:
    maps: dict[str, dict[int, tuple[int, int]]] = {"context": {}, "route": {}, "memory": {}}
    for name, key_id in CONTEXT_KEY_IDS.items():
        value, confidence = t28a.REGIME_VALUES.get(name, (0.0, 1.0))
        maps["context"][int(key_id)] = (fp_from_float(value), fp_from_float(confidence))
    for name, key_id in ROUTE_KEY_IDS.items():
        value, confidence = t28a.REGIME_VALUES.get(name, (0.0, 1.0))
        maps["route"][int(key_id)] = (fp_from_float(value), fp_from_float(confidence))
    for name, key_id in MEMORY_KEY_IDS.items():
        value, confidence = t28a.REGIME_VALUES.get(name, (0.0, 1.0))
        maps["memory"][int(key_id)] = (fp_from_float(value), fp_from_float(confidence))
    return maps


def reference_learning_trace(learning_rate: float, count: int = EVENT_COUNT) -> dict[str, Any]:
    """Mirror the learning-core tick order for the deterministic micro-task.

    The hardware core sends lookups on one tick, composes/schedules the event
    once replies are available, then matures at most the oldest due pending
    horizon. This reference keeps the pass criteria tied to the runtime
    contract rather than to a hand-waved final weight.
    """
    schedule = build_schedule(count)
    maps = slot_value_maps()
    learning_rate_raw = fp_from_float(learning_rate)
    weight = 0
    bias = 0
    schedule_index = 0
    active_event: tuple[dict[str, Any], int] | None = None
    pending: list[dict[str, int]] = []
    decisions = 0
    reward_events = 0
    trace: list[dict[str, Any]] = []
    final_timestep = 0

    for timestep in range(1, 500):
        if active_event is not None:
            entry, event_base_timestep = active_event
            context_value, context_confidence = maps["context"][int(entry["context_key"])]
            route_value, route_confidence = maps["route"][int(entry["route_key"])]
            memory_value, memory_confidence = maps["memory"][int(entry["memory_key"])]
            cue = fp_from_float(float(entry["cue"]))
            target = fp_from_float(float(entry["target"]))
            feature = fp_mul(fp_mul(fp_mul(context_value, route_value), memory_value), cue)
            prediction = fp_mul(weight, feature) + bias
            composite_confidence = fp_mul(fp_mul(context_confidence, route_confidence), memory_confidence)
            decisions += 1
            pending.append(
                {
                    "due": event_base_timestep + int(entry["delay"]),
                    "feature": feature,
                    "prediction": prediction,
                    "target": target,
                    "confidence": composite_confidence,
                }
            )
            trace.append(
                {
                    "timestep": timestep,
                    "event": decisions,
                    "feature_raw": feature,
                    "target_raw": target,
                    "prediction_raw": prediction,
                    "due": event_base_timestep + int(entry["delay"]),
                }
            )
            active_event = None

        if active_event is None and schedule_index < count:
            entry = schedule[schedule_index]
            if int(entry["timestep"]) == timestep:
                active_event = (entry, timestep)
                schedule_index += 1

        due_pending = [item for item in pending if item["due"] <= timestep]
        if due_pending:
            oldest = min(due_pending, key=lambda item: item["due"])
            pending.remove(oldest)
            effective_lr = fp_mul(learning_rate_raw, oldest["confidence"])
            error = oldest["target"] - oldest["prediction"]
            if abs(error) < SURPRISE_THRESHOLD_RAW:
                weight += fp_mul(effective_lr, fp_mul(error, oldest["feature"]))
                bias += fp_mul(effective_lr, error)
            reward_events += 1

        if schedule_index >= count and active_event is None and not pending:
            final_timestep = timestep
            break

    return {
        "learning_rate": learning_rate,
        "learning_rate_raw": learning_rate_raw,
        "event_count": count,
        "decisions": decisions,
        "reward_events": reward_events,
        "pending_created": decisions,
        "pending_matured": reward_events,
        "active_pending": len(pending),
        "readout_weight_raw": weight,
        "readout_bias_raw": bias,
        "readout_weight": weight / FP_ONE,
        "readout_bias": bias / FP_ONE,
        "final_timestep": final_timestep,
        "trace_preview": trace[:8],
    }


def write_state_slots(ctrl: Any, args: argparse.Namespace, role: str, core: int) -> list[dict[str, Any]]:
    writes: list[dict[str, Any]] = []
    remote_x = int(args.remote_x)
    remote_y = int(args.remote_y)
    if role == "context":
        for key, key_id in CONTEXT_KEY_IDS.items():
            value, confidence = t28a.REGIME_VALUES.get(key, (0.0, 1.0))
            ok = ctrl.write_context(key_id, value, confidence, remote_x, remote_y, core)
            writes.append({"key": key, "slot": key_id, "success": ok.get("success") is True})
    elif role == "route":
        for key, key_id in ROUTE_KEY_IDS.items():
            value, confidence = t28a.REGIME_VALUES.get(key, (0.0, 1.0))
            ok = ctrl.write_route_slot(key_id, value, confidence, remote_x, remote_y, core)
            writes.append({"key": key, "slot": key_id, "success": ok.get("success") is True})
    elif role == "memory":
        for key, key_id in MEMORY_KEY_IDS.items():
            value, confidence = t28a.REGIME_VALUES.get(key, (0.0, 1.0))
            ok = ctrl.write_memory_slot(key_id, value, confidence, remote_x, remote_y, core)
            writes.append({"key": key, "slot": key_id, "success": ok.get("success") is True})
    return writes


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


def run_learning_case(ctrl: Any, args: argparse.Namespace, case: dict[str, Any]) -> dict[str, Any]:
    source_x = int(args.source_x)
    source_y = int(args.source_y)
    remote_x = int(args.remote_x)
    remote_y = int(args.remote_y)
    label = str(case["label"])
    learning_rate = float(case["learning_rate"])
    reference = reference_learning_trace(learning_rate, EVENT_COUNT)
    result: dict[str, Any]
    hardware_exception: dict[str, Any] | None = None
    waited = 0.0
    try:
        resets: dict[str, Any] = {}
        state_writes: dict[str, list[dict[str, Any]]] = {}
        schedule_uploads: list[dict[str, Any]] = []
        run_cmds: dict[str, dict[str, Any]] = {}
        pauses: dict[str, dict[str, Any]] = {}

        for role, spec in CORE_ROLES.items():
            chip = (source_x, source_y) if spec["chip"] == "source" else (remote_x, remote_y)
            resets[role] = ctrl.reset(chip[0], chip[1], int(spec["core"]))
            time.sleep(float(args.command_delay_seconds))

        for role in ("context", "route", "memory"):
            state_writes[role] = write_state_slots(ctrl, args, role, int(CORE_ROLES[role]["core"]))
            time.sleep(float(args.command_delay_seconds))

        schedule = build_schedule(EVENT_COUNT)
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
                dest_x=source_x,
                dest_y=source_y,
                dest_cpu=int(CORE_ROLES["learning"]["core"]),
            )
            schedule_uploads.append({"index": index, "success": ok.get("success") is True})
            if index % 16 == 15:
                time.sleep(float(args.command_delay_seconds))

        for role in ("context", "route", "memory"):
            run = ctrl.run_continuous(learning_rate, 0, remote_x, remote_y, int(CORE_ROLES[role]["core"]))
            run_cmds[role] = {"success": run.get("success") is True, "raw": run}
            time.sleep(float(args.command_delay_seconds))
        run = ctrl.run_continuous(learning_rate, EVENT_COUNT, source_x, source_y, int(CORE_ROLES["learning"]["core"]))
        run_cmds["learning"] = {"success": run.get("success") is True, "raw": run}

        max_wait = float(args.max_wait_seconds)
        poll_interval = float(args.poll_interval_seconds)
        learning_core = int(CORE_ROLES["learning"]["core"])
        poll_reads: list[dict[str, Any]] = []
        while waited < max_wait:
            time.sleep(poll_interval)
            waited += poll_interval
            state = ctrl.read_state(source_x, source_y, learning_core)
            poll_reads.append(state)
            if (
                state.get("success") is True
                and state.get("pending_matured") == EVENT_COUNT
                and state.get("active_pending") == 0
                and state.get("lookup_replies") == EXPECTED_LOOKUPS
            ):
                break

        for role, spec in CORE_ROLES.items():
            chip = (source_x, source_y) if spec["chip"] == "source" else (remote_x, remote_y)
            pause = ctrl.pause(chip[0], chip[1], int(spec["core"]))
            pauses[role] = {"success": pause.get("success") is True, "raw": pause}
            time.sleep(float(args.command_delay_seconds))

        final_state = {
            "context": ctrl.read_state(remote_x, remote_y, int(CORE_ROLES["context"]["core"])),
            "route": ctrl.read_state(remote_x, remote_y, int(CORE_ROLES["route"]["core"])),
            "memory": ctrl.read_state(remote_x, remote_y, int(CORE_ROLES["memory"]["core"])),
            "learning": ctrl.read_state(source_x, source_y, int(CORE_ROLES["learning"]["core"])),
        }
        result = {
            "status": "completed",
            "case_label": label,
            "case_kind": str(case["kind"]),
            "learning_rate": learning_rate,
            "learning_reference": reference,
            "source_chip": {"x": source_x, "y": source_y},
            "remote_chip": {"x": remote_x, "y": remote_y},
            "event_count": EVENT_COUNT,
            "expected_lookup_count": EXPECTED_LOOKUPS,
            "reset": resets,
            "state_writes": state_writes,
            "schedule_uploads": schedule_uploads,
            "run_continuous": run_cmds,
            "poll_reads": poll_reads,
            "pause": pauses,
            "final_state": final_state,
            "waited_seconds": waited,
        }
    except Exception as exc:
        hardware_exception = {"exception_type": type(exc).__name__, "exception": str(exc), "traceback": traceback.format_exc()}
        result = {"status": "fail", "hardware_exception": hardware_exception}
    finally:
        pass

    result["hardware_exception"] = hardware_exception
    criteria = case_criteria(result, hardware_exception)
    result["criteria"] = criteria
    result["status"] = "pass" if all(item["passed"] for item in criteria) else "fail"
    return result


def run_multichip_learning_microtask(hostname: str, args: argparse.Namespace, output_dir: Path) -> dict[str, Any]:
    from coral_reef_spinnaker.python_host.colony_controller import ColonyController

    ctrl = ColonyController(hostname, port=int(args.port), timeout=float(args.timeout_seconds))
    started = time.perf_counter()
    hardware_exception: dict[str, Any] | None = None
    cases: list[dict[str, Any]] = []
    try:
        for case in LEARNING_CASES:
            case_result = run_learning_case(ctrl, args, case)
            cases.append(case_result)
            write_json(output_dir / f"tier4_32e_case_{case['label']}.json", case_result)
            write_csv(output_dir / f"tier4_32e_case_{case['label']}_summary.csv", case_result.get("criteria", []))
            time.sleep(float(args.command_delay_seconds))
    except Exception as exc:
        hardware_exception = {"exception_type": type(exc).__name__, "exception": str(exc), "traceback": traceback.format_exc()}
    finally:
        try:
            ctrl.close()
        except Exception:
            pass

    criteria = task_criteria(cases, hardware_exception)
    result = {
        "status": "pass" if all(item["passed"] for item in criteria) else "fail",
        "case_count": len(cases),
        "cases": cases,
        "hardware_exception": hardware_exception,
        "source_chip": SOURCE_CHIP,
        "remote_chip": REMOTE_CHIP,
        "event_count_per_case": EVENT_COUNT,
        "expected_lookup_count_per_case": EXPECTED_LOOKUPS,
        "learning_cases": LEARNING_CASES,
        "reference_cases": {case["label"]: reference_learning_trace(float(case["learning_rate"]), EVENT_COUNT) for case in LEARNING_CASES},
        "runtime_seconds": time.perf_counter() - started,
        "criteria": criteria,
    }
    write_json(output_dir / "tier4_32e_task_result.json", result)
    write_csv(output_dir / "tier4_32e_task_summary.csv", criteria)
    return result


def case_criteria(task: dict[str, Any], hardware_exception: dict[str, Any] | None) -> list[dict[str, Any]]:
    final_state = task.get("final_state", {}) if isinstance(task, dict) else {}
    learning = final_state.get("learning", {}) if isinstance(final_state, dict) else {}
    context = final_state.get("context", {}) if isinstance(final_state, dict) else {}
    route = final_state.get("route", {}) if isinstance(final_state, dict) else {}
    memory = final_state.get("memory", {}) if isinstance(final_state, dict) else {}
    resets = task.get("reset", {}) if isinstance(task, dict) else {}
    writes = task.get("state_writes", {}) if isinstance(task, dict) else {}
    uploads = task.get("schedule_uploads", []) if isinstance(task, dict) else []
    runs = task.get("run_continuous", {}) if isinstance(task, dict) else {}
    pauses = task.get("pause", {}) if isinstance(task, dict) else {}
    reference = task.get("learning_reference", {}) if isinstance(task, dict) else {}
    kind = str(task.get("case_kind", ""))
    enabled = kind == "enabled"
    no_learning = kind == "no_learning"
    return [
        criterion("no hardware exception", hardware_exception is None, "== True", hardware_exception is None),
        criterion("task completed", task.get("status"), "completed/pass", task.get("status") in {"completed", "pass"}),
        criterion("case label present", task.get("case_label"), "non-empty", bool(task.get("case_label"))),
        criterion("case kind valid", kind, "enabled|no_learning", kind in {"enabled", "no_learning"}),
        criterion("reference computed", reference, "contains final readout", "readout_weight_raw" in reference and "readout_bias_raw" in reference),
        criterion("source chip placement", task.get("source_chip"), f"== {SOURCE_CHIP}", task.get("source_chip") == SOURCE_CHIP),
        criterion("remote chip placement", task.get("remote_chip"), f"== {REMOTE_CHIP}", task.get("remote_chip") == REMOTE_CHIP),
        criterion("all resets succeeded", resets, "all success", bool(resets) and all(v is True or (isinstance(v, dict) and v.get("success") is True) for v in resets.values())),
        criterion("all state writes succeeded", writes, "all success", bool(writes) and all(item.get("success") is True for group in writes.values() for item in group)),
        criterion("all schedule uploads succeeded", uploads, "all success", bool(uploads) and all(item.get("success") is True for item in uploads)),
        criterion("all run_continuous succeeded", runs, "all success", bool(runs) and all(item.get("success") is True for item in runs.values())),
        criterion("all pause commands succeeded", pauses, "all success", bool(pauses) and all(item.get("success") is True for item in pauses.values())),
        criterion("context read success", context.get("success"), "== True", context.get("success") is True),
        criterion("route read success", route.get("success"), "== True", route.get("success") is True),
        criterion("memory read success", memory.get("success"), "== True", memory.get("success") is True),
        criterion("learning read success", learning.get("success"), "== True", learning.get("success") is True),
        criterion("decisions", learning.get("decisions"), f"== {EVENT_COUNT}", learning.get("decisions") == EVENT_COUNT),
        criterion("reward_events", learning.get("reward_events"), f"== {EVENT_COUNT}", learning.get("reward_events") == EVENT_COUNT),
        criterion("pending_created", learning.get("pending_created"), f"== {EVENT_COUNT}", learning.get("pending_created") == EVENT_COUNT),
        criterion("pending_matured", learning.get("pending_matured"), f"== {EVENT_COUNT}", learning.get("pending_matured") == EVENT_COUNT),
        criterion("active_pending cleared", learning.get("active_pending"), "== 0", learning.get("active_pending") == 0),
        criterion("lookup_requests", learning.get("lookup_requests"), f"== {EXPECTED_LOOKUPS}", learning.get("lookup_requests") == EXPECTED_LOOKUPS),
        criterion("lookup_replies", learning.get("lookup_replies"), f"== {EXPECTED_LOOKUPS}", learning.get("lookup_replies") == EXPECTED_LOOKUPS),
        criterion("stale_replies zero", learning.get("stale_replies"), "== 0", learning.get("stale_replies") == 0),
        criterion("duplicate_replies zero", learning.get("duplicate_replies"), "== 0", learning.get("duplicate_replies") == 0),
        criterion("timeouts zero", learning.get("timeouts"), "== 0", learning.get("timeouts") == 0),
        criterion("readout weight matches reference", learning.get("readout_weight_raw"), f"== {reference.get('readout_weight_raw')}", learning.get("readout_weight_raw") == reference.get("readout_weight_raw")),
        criterion("readout bias matches reference", learning.get("readout_bias_raw"), f"== {reference.get('readout_bias_raw')}", learning.get("readout_bias_raw") == reference.get("readout_bias_raw")),
        criterion("enabled learning moves readout", learning.get("readout_weight_raw"), "> 0 when enabled", (not enabled) or int(learning.get("readout_weight_raw") or 0) > 0),
        criterion("no-learning keeps weight zero", learning.get("readout_weight_raw"), "== 0 when no_learning", (not no_learning) or learning.get("readout_weight_raw") == 0),
        criterion("no-learning keeps bias zero", learning.get("readout_bias_raw"), "== 0 when no_learning", (not no_learning) or learning.get("readout_bias_raw") == 0),
        criterion("learning payload compact", learning.get("payload_len"), ">= 105", int(learning.get("payload_len") or 0) >= 105),
    ]


def task_criteria(cases: list[dict[str, Any]], hardware_exception: dict[str, Any] | None) -> list[dict[str, Any]]:
    case_by_label = {str(case.get("case_label")): case for case in cases}
    enabled = case_by_label.get("enabled_lr_0_25", {})
    no_learning = case_by_label.get("no_learning_lr_0_00", {})
    enabled_learning = enabled.get("final_state", {}).get("learning", {}) if isinstance(enabled, dict) else {}
    no_learning_state = no_learning.get("final_state", {}).get("learning", {}) if isinstance(no_learning, dict) else {}
    criteria = [
        criterion("no top-level hardware exception", hardware_exception is None, "== True", hardware_exception is None),
        criterion("both learning cases returned", len(cases), f"== {len(LEARNING_CASES)}", len(cases) == len(LEARNING_CASES)),
        criterion("enabled case present", "enabled_lr_0_25" in case_by_label, "present", "enabled_lr_0_25" in case_by_label),
        criterion("no-learning case present", "no_learning_lr_0_00" in case_by_label, "present", "no_learning_lr_0_00" in case_by_label),
        criterion("all cases pass", {case.get("case_label"): case.get("status") for case in cases}, "all == pass", bool(cases) and all(case.get("status") == "pass" for case in cases)),
        criterion(
            "enabled readout exceeds no-learning control",
            {
                "enabled": enabled_learning.get("readout_weight_raw"),
                "no_learning": no_learning_state.get("readout_weight_raw"),
            },
            "enabled > no_learning",
            int(enabled_learning.get("readout_weight_raw") or 0) > int(no_learning_state.get("readout_weight_raw") or 0),
        ),
        criterion(
            "both cases used identical lookup budget",
            {
                "enabled": enabled_learning.get("lookup_replies"),
                "no_learning": no_learning_state.get("lookup_replies"),
            },
            f"both == {EXPECTED_LOOKUPS}",
            enabled_learning.get("lookup_replies") == EXPECTED_LOOKUPS and no_learning_state.get("lookup_replies") == EXPECTED_LOOKUPS,
        ),
        criterion("true two-partition learning not attempted", "not_attempted", "== not_attempted", True),
        criterion("native-scale baseline freeze not authorized", "not_authorized", "== not_authorized", True),
    ]
    for case in cases:
        for item in case.get("criteria", []):
            item = dict(item)
            item["name"] = f"{case.get('case_label')} :: {item.get('name')}"
            criteria.append(item)
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
        "tier4_32e_multichip_learning_microtask.py",
        "tier4_28a_four_core_mcpl_repeatability.py",
        "tier4_22i_custom_runtime_roundtrip.py",
        "tier4_22x_compact_v2_bridge_decoupled_smoke.py",
        "tier4_22l_custom_runtime_learning_parity.py",
        "tier4_22j_minimal_custom_runtime_learning.py",
        "tier4_23a_continuous_local_reference.py",
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
        f"{UPLOAD_PACKAGE_NAME}/experiments/tier4_32e_multichip_learning_microtask.py "
        "--mode run-hardware --output-dir tier4_32e_job_output"
    )
    readme = bundle / "README_TIER4_32E_JOB.md"
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
        f"- Remote/state chip: `({REMOTE_CHIP['x']},{REMOTE_CHIP['y']})`, context/route/memory cores `4/5/6`.\n"
        f"- Source requests route east using `{REQUEST_LINK_ROUTE}`; remote replies route west using `{REPLY_LINK_ROUTE}`.\n"
        "- This is shard `0` only and uses 32 schedule events per case.\n"
        "- It runs two cases: enabled learning at LR `0.25` and a no-learning LR `0.0` control.\n\n"
        "## Pass Boundary\n\n"
        "PASS requires real target acquisition, profile builds/loads on both chips, state writes on the remote chip, "
        "schedule upload on the source chip, 96 lookup requests and 96 lookup replies per case on the learning core, "
        "zero stale/duplicate/timeout counters, compact readback, enabled readout movement matching reference, "
        "no-learning readout immobility, and zero synthetic fallback.\n\n"
        "## Nonclaims\n\n"
        f"{CLAIM_BOUNDARY}\n",
        encoding="utf-8",
    )
    metadata = {
        "tier": TIER_NAME,
        "runner_revision": RUNNER_REVISION,
        "upload_package": UPLOAD_PACKAGE_NAME,
        "prepared_at_utc": utc_now(),
        "runner": "experiments/tier4_32e_multichip_learning_microtask.py",
        "job_command": command,
        "source_chip": SOURCE_CHIP,
        "remote_chip": REMOTE_CHIP,
        "core_roles": CORE_ROLES,
        "event_count": EVENT_COUNT,
        "expected_lookups": EXPECTED_LOOKUPS,
        "learning_cases": LEARNING_CASES,
        "reference_cases": {case["label"]: reference_learning_trace(float(case["learning_rate"]), EVENT_COUNT) for case in LEARNING_CASES},
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
    result_path = output_dir / "tier4_32e_results.json"
    report_path = output_dir / "tier4_32e_report.md"
    summary_path = output_dir / "tier4_32e_summary.csv"
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
                    "expected_job_command": f"{UPLOAD_PACKAGE_NAME}/experiments/tier4_32e_multichip_learning_microtask.py --mode run-hardware --output-dir tier4_32e_job_output",
                },
                indent=2,
            )
        )
        return 1
    output_dir.mkdir(parents=True, exist_ok=True)
    tier4_32c_status = prerequisite_status(TIER4_32C_RESULTS)
    tier4_32d_status = prerequisite_status(TIER4_32D_RESULTS)
    tier4_32d_r0_status = prerequisite_status(TIER4_32D_R0_RESULTS)
    tier4_32d_r1_status = prerequisite_status(TIER4_32D_R1_RESULTS)
    source_checks = run_prepare_source_checks(output_dir)
    py_compile = py_compile_scripts(output_dir)
    bundle, command, bundle_artifacts = prepare_bundle(output_dir)
    bundle_makefile = (bundle / "coral_reef_spinnaker" / "spinnaker_runtime" / "Makefile").read_text(encoding="utf-8")
    bundle_state = (bundle / "coral_reef_spinnaker" / "spinnaker_runtime" / "src" / "state_manager.c").read_text(encoding="utf-8")
    criteria = [
        criterion("Tier 4.32c inter-chip contract passed", tier4_32c_status, "== pass", tier4_32c_status == "pass"),
        criterion("Tier 4.32d hardware pass ingested", tier4_32d_status, "== pass", tier4_32d_status == "pass"),
        criterion("Tier 4.32d-r0 route audit passed", tier4_32d_r0_status, "== pass", tier4_32d_r0_status == "pass"),
        criterion("Tier 4.32d-r1 route repair/local QA passed", tier4_32d_r1_status, "== pass", tier4_32d_r1_status == "pass"),
        criterion("inter-chip route source checks pass", source_checks.get("status"), "== pass", source_checks.get("status") == "pass"),
        criterion("runner and dependencies py_compile", py_compile.get("status"), "== pass", py_compile.get("status") == "pass"),
        criterion("upload bundle created", str(bundle), "exists", bundle.exists()),
        criterion("stable upload folder created", str(STABLE_EBRAINS_UPLOAD), "exists", STABLE_EBRAINS_UPLOAD.exists()),
        criterion("run-hardware command emitted", command, "contains --mode run-hardware", "--mode run-hardware" in command),
        criterion("bundle Makefile exposes request link route", "MCPL_INTERCHIP_REQUEST_LINK_ROUTE", "present", "MCPL_INTERCHIP_REQUEST_LINK_ROUTE" in bundle_makefile),
        criterion("bundle Makefile exposes reply link route", "MCPL_INTERCHIP_REPLY_LINK_ROUTE", "present", "MCPL_INTERCHIP_REPLY_LINK_ROUTE" in bundle_makefile),
        criterion("bundle installs outbound request route", "CRA_MCPL_INTERCHIP_REQUEST_LINK_ROUTE", "present", "CRA_MCPL_INTERCHIP_REQUEST_LINK_ROUTE" in bundle_state),
        criterion("bundle installs outbound reply route", "CRA_MCPL_INTERCHIP_REPLY_LINK_ROUTE", "present", "CRA_MCPL_INTERCHIP_REPLY_LINK_ROUTE" in bundle_state),
        criterion("reference enabled learning moves readout", reference_learning_trace(0.25, EVENT_COUNT)["readout_weight_raw"], "> 0", reference_learning_trace(0.25, EVENT_COUNT)["readout_weight_raw"] > 0),
        criterion("reference no-learning control stays fixed", reference_learning_trace(0.0, EVENT_COUNT)["readout_weight_raw"], "== 0", reference_learning_trace(0.0, EVENT_COUNT)["readout_weight_raw"] == 0),
        criterion("multi-chip learning micro-task only", {"source": SOURCE_CHIP, "remote": REMOTE_CHIP}, "predeclared", True),
        criterion("true two-partition learning remains blocked", "blocked", "== blocked", True),
        criterion("native-scale baseline freeze remains blocked", "not_authorized", "== not_authorized", True),
    ]
    status = "prepared" if all(item["passed"] for item in criteria) else "blocked"
    result = {
        "tier": "4.32e",
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
            "source_chip": SOURCE_CHIP,
            "remote_chip": REMOTE_CHIP,
            "event_count": EVENT_COUNT,
            "expected_lookups": EXPECTED_LOOKUPS,
            "learning_cases": LEARNING_CASES,
            "reference_cases": {case["label"]: reference_learning_trace(float(case["learning_rate"]), EVENT_COUNT) for case in LEARNING_CASES},
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
    write_json(output_dir / "tier4_32e_environment.json", env_report)
    source_checks = run_prepare_source_checks(output_dir)
    main_syntax = base.run_main_syntax_check(output_dir)
    builds = {role: build_aplx_for_role(role, output_dir) for role in CORE_ROLES}
    for role, build in builds.items():
        write_json(output_dir / f"tier4_32e_{role}_build.json", build)

    target = base.acquire_hardware_target(args)
    hostname = str(target.get("hostname") or target.get("target_ipaddress") or "")
    write_json(output_dir / "tier4_32e_target_acquisition.json", base.public_target_acquisition(target))
    loads = {role: {"status": "not_attempted"} for role in CORE_ROLES}
    task: dict[str, Any] = {"status": "not_attempted"}
    hardware_exception: dict[str, Any] | None = None
    target_cleanup: dict[str, Any] = {"status": "not_attempted"}
    try:
        if target.get("status") == "pass" and hostname and all(build.get("status") == "pass" for build in builds.values()):
            loads = load_profiles(hostname, args, target, builds)
            for role, load in loads.items():
                write_json(output_dir / f"tier4_32e_{role}_load.json", load)
            if all(load.get("status") == "pass" for load in loads.values()):
                task = run_multichip_learning_microtask(hostname, args, output_dir)
    except Exception as exc:
        hardware_exception = {"exception_type": type(exc).__name__, "exception": str(exc), "traceback": traceback.format_exc()}
    finally:
        target_cleanup = base.release_hardware_target(target)
        write_json(output_dir / "tier4_32e_target_acquisition.json", base.public_target_acquisition({**target, "cleanup": target_cleanup}))
        for role, load in loads.items():
            write_json(output_dir / f"tier4_32e_{role}_load.json", load)
        write_json(output_dir / "tier4_32e_task_result.json", task)

    criteria = [
        criterion("runner revision current", RUNNER_REVISION, "expected", True),
        criterion("synthetic fallback zero", 0, "== 0", True),
        criterion("source checks pass", source_checks.get("status"), "== pass", source_checks.get("status") == "pass"),
        criterion("main syntax check pass", main_syntax.get("status"), "== pass", main_syntax.get("status") == "pass"),
        criterion("hardware target acquired", base.public_target_acquisition(target), "status == pass", target.get("status") == "pass"),
        criterion("all four role builds pass", {k: v.get("status") for k, v in builds.items()}, "all == pass", bool(builds) and all(v.get("status") == "pass" for v in builds.values())),
        criterion("all four role loads pass", {k: v.get("status") for k, v in loads.items()}, "all == pass", bool(loads) and all(v.get("status") == "pass" for v in loads.values())),
        criterion("no top-level hardware exception", hardware_exception is None, "== True", hardware_exception is None),
        criterion("multi-chip learning micro-task status pass", task.get("status"), "== pass", task.get("status") == "pass"),
        *task.get("criteria", []),
        criterion("true two-partition learning not attempted", "not_attempted", "== not_attempted", True),
        criterion("native-scale baseline freeze not authorized", "not_authorized", "== not_authorized", True),
    ]
    status = "pass" if all(item["passed"] for item in criteria) else "fail"
    result = {
        "tier": "4.32e",
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
            "event_count": EVENT_COUNT,
            "expected_lookups": EXPECTED_LOOKUPS,
            "learning_microtask_status": task.get("status"),
            "learning_cases": LEARNING_CASES,
            "reference_cases": {case["label"]: reference_learning_trace(float(case["learning_rate"]), EVENT_COUNT) for case in LEARNING_CASES},
            "synthetic_fallback_used": False,
            "true_two_partition_learning_attempted": False,
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
            "tier4_32f_multi_chip_lifecycle_or_resource_gate": "authorized_next" if status == "pass" else "blocked_until_4_32e_hardware_passes",
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
        if anchor_mtime is not None:
            age_delta = abs(path.stat().st_mtime - anchor_mtime)
            if age_delta > INGEST_ARTIFACT_MTIME_WINDOW_SECONDS:
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
        matches = sorted(ingest_dir.rglob("tier4_32e_results.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        candidate = matches[0] if matches else None
    if candidate is None or not candidate.exists():
        result = {
            "tier": "4.32e-ingest",
            "tier_name": TIER_NAME,
            "runner_revision": RUNNER_REVISION,
            "generated_at_utc": utc_now(),
            "mode": "ingest",
            "status": "fail",
            "failure_reason": f"tier4_32e_results.json not found in {ingest_dir}",
            "criteria": [criterion("hardware results json exists", str(ingest_dir), "contains tier4_32e_results.json", False)],
            "claim_boundary": "Failed ingest only; not hardware evidence.",
        }
        return finalize(output_dir, result)
    hardware = read_json(candidate)
    returned = copy_returned_artifacts(ingest_dir, output_dir, candidate)
    criteria = [
        criterion("hardware results json exists", str(candidate), "exists", True),
        criterion("hardware mode was run-hardware", hardware.get("mode"), "== run-hardware", hardware.get("mode") == "run-hardware"),
        criterion("raw hardware status pass", hardware.get("status"), "== pass", hardware.get("status") == "pass"),
        criterion("learning microtask pass", hardware.get("summary", {}).get("learning_microtask_status"), "== pass", hardware.get("summary", {}).get("learning_microtask_status") == "pass"),
        criterion("enabled case present", "enabled_lr_0_25" in {case.get("case_label") for case in hardware.get("task", {}).get("cases", [])}, "present", "enabled_lr_0_25" in {case.get("case_label") for case in hardware.get("task", {}).get("cases", [])}),
        criterion("no-learning case present", "no_learning_lr_0_00" in {case.get("case_label") for case in hardware.get("task", {}).get("cases", [])}, "present", "no_learning_lr_0_00" in {case.get("case_label") for case in hardware.get("task", {}).get("cases", [])}),
        criterion("returned artifacts preserved", len(returned), ">= 1", len(returned) >= 1),
        criterion("true two-partition learning not attempted", hardware.get("summary", {}).get("true_two_partition_learning_attempted"), "== False", hardware.get("summary", {}).get("true_two_partition_learning_attempted") is False),
        criterion("synthetic fallback zero", hardware.get("summary", {}).get("synthetic_fallback_used"), "== False", hardware.get("summary", {}).get("synthetic_fallback_used") is False),
    ]
    status = "pass" if all(item["passed"] for item in criteria) else "fail"
    result = {
        "tier": "4.32e-ingest",
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
            "learning_microtask_status": hardware.get("summary", {}).get("learning_microtask_status"),
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
        lines.append("Upload the stable `cra_432e` folder to EBRAINS and run the emitted JobManager command.")
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
    # Compatibility with shared target-acquisition helpers.
    parser.add_argument("--dest-x", type=int, default=SOURCE_CHIP["x"])
    parser.add_argument("--dest-y", type=int, default=SOURCE_CHIP["y"])
    parser.add_argument("--dest-cpu", type=int, default=CORE_ROLES["learning"]["core"])
    parser.add_argument("--port", type=int, default=17893)
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    parser.add_argument("--startup-delay-seconds", type=float, default=1.0)
    parser.add_argument("--command-delay-seconds", type=float, default=0.02)
    parser.add_argument("--poll-interval-seconds", type=float, default=0.10)
    parser.add_argument("--max-wait-seconds", type=float, default=20.0)
    parser.add_argument("--learning-rate", type=float, default=0.25)
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
    # Keep compatibility fields aligned for shared target acquisition helpers.
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
            "tier": "4.32e",
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
        write_json(args.output_dir / "tier4_32e_crash.json", crash)
        write_json(args.output_dir / "tier4_32e_results.json", crash)
        print(json.dumps({"status": "fail", "exception_type": type(exc).__name__, "exception": str(exc)}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
