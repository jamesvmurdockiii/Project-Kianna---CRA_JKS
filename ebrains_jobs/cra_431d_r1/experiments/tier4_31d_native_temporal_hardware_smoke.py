#!/usr/bin/env python3
"""Tier 4.31d native temporal-substrate hardware smoke.

This gate is intentionally small. Tier 4.31c proved the C source/runtime owns
seven fixed-point EMA temporal traces locally. Tier 4.31d asks whether that same
C-owned temporal state can be built, loaded, updated, and read back on one real
SpiNNaker board with enabled and destructive temporal controls.

Claim boundary:
- PREPARED means the source-only EBRAINS folder and command are ready.
- PASS in run-hardware means a real SpiNNaker target was acquired, the runtime
  image built/loaded, temporal command codes 39-42 round-tripped, compact
  payload_len=48 readbacks matched the fixed-point reference, and zero synthetic
  fallback was used.
- This is a one-board smoke only. It is not speedup, benchmark superiority,
  multi-chip scaling, nonlinear recurrence, native replay/sleep, or full v2.2
  hardware transfer evidence.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
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
TIER_NAME = "Tier 4.31d - Native Temporal-Substrate Hardware Smoke"
RUNNER_REVISION = "tier4_31d_native_temporal_hardware_smoke_20260506_0003"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier4_31d_hw_20260506_prepared"
DEFAULT_RUN_OUTPUT = CONTROLLED / f"tier4_31d_hw_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_run_hardware"
DEFAULT_INGEST_OUTPUT = CONTROLLED / "tier4_31d_hw_ingested"
LATEST_MANIFEST = CONTROLLED / "tier4_31d_hw_latest_manifest.json"
TIER431C_RESULTS = CONTROLLED / "tier4_31c_20260506_native_temporal_runtime_source_audit" / "tier4_31c_results.json"
UPLOAD_PACKAGE_NAME = "cra_431d_r1"
STABLE_EBRAINS_UPLOAD = ROOT / "ebrains_jobs" / UPLOAD_PACKAGE_NAME

FP_SHIFT = 15
FP_ONE = 1 << FP_SHIFT
TEMPORAL_TRACE_COUNT = 7
TEMPORAL_TIMESCALE_CHECKSUM = 1811900589
TEMPORAL_TRACE_BOUND = 2 * FP_ONE
TEMPORAL_INPUT_BOUND = 3 * FP_ONE
TEMPORAL_NOVELTY_BOUND = 5 * FP_ONE
TEMPORAL_DECAY_RAW = [19874, 25519, 28917, 30782, 31759, 32259, 32512]
TEMPORAL_ALPHA_RAW = [12893, 7248, 3850, 1985, 1008, 508, 255]
TEMPORAL_SHAM_ENABLED = 0
TEMPORAL_SHAM_ZERO_STATE = 1
TEMPORAL_SHAM_FROZEN_STATE = 2
TEMPORAL_SHAM_RESET_EACH_UPDATE = 3
COMMAND_DELAY_SECONDS = 0.025

CLAIM_BOUNDARY = (
    "Tier 4.31d is a one-board native temporal-state hardware smoke. It proves "
    "build/load/command/readback of the C-owned seven-EMA temporal subset only; "
    "it does not prove speedup, benchmark superiority, multi-chip scaling, "
    "nonlinear recurrence, replay/sleep, or full v2.2 hardware transfer."
)

CANONICAL_INPUTS_RAW = [
    int(round(v * FP_ONE))
    for v in [0.25, -0.50, 0.75, 1.00, -0.25, 0.50, -0.75, 0.125,
              0.875, -1.25, 0.375, 0.0, 0.625, -0.875, 0.25, -0.125]
]
FROZEN_SEED_RAW = int(round(0.625 * FP_ONE))


@dataclass
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
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_safe(v) for v in value]
    if isinstance(value, tuple):
        return [json_safe(v) for v in value]
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    return value


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    rows = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = []
        for row in rows:
            for key in row:
                if key not in fieldnames:
                    fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json_safe(row.get(key, "")) for key in fieldnames})


def run_cmd(cmd: list[str], *, env: dict[str, str] | None = None, timeout: float | None = None) -> dict[str, Any]:
    try:
        proc = subprocess.run(cmd, cwd=ROOT, env=env, text=True, capture_output=True, check=False, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        return {
            "command": " ".join(cmd),
            "returncode": None,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "timeout_seconds": timeout,
            "timed_out": True,
        }
    return {"command": " ".join(cmd), "returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}


def run_cmd_to_files(
    cmd: list[str],
    *,
    stdout_path: Path,
    stderr_path: Path,
    env: dict[str, str] | None = None,
    timeout: float | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stderr_path.parent.mkdir(parents=True, exist_ok=True)
    with stdout_path.open("w", encoding="utf-8") as out, stderr_path.open("w", encoding="utf-8") as err:
        try:
            proc = subprocess.run(cmd, cwd=ROOT, env=env, text=True, stdout=out, stderr=err, check=False, timeout=timeout)
            return {
                "command": " ".join(cmd),
                "returncode": proc.returncode,
                "runtime_seconds": time.perf_counter() - started,
                "stdout_artifact": str(stdout_path),
                "stderr_artifact": str(stderr_path),
                "timed_out": False,
            }
        except subprocess.TimeoutExpired:
            err.write(f"\nTIMEOUT after {timeout} seconds\n")
            return {
                "command": " ".join(cmd),
                "returncode": None,
                "runtime_seconds": time.perf_counter() - started,
                "stdout_artifact": str(stdout_path),
                "stderr_artifact": str(stderr_path),
                "timeout_seconds": timeout,
                "timed_out": True,
            }


def criterion(name: str, value: Any, rule: str, passed: bool, note: str = "") -> dict[str, Any]:
    return asdict(Criterion(name=name, value=value, rule=rule, passed=bool(passed), note=note))


def fp_to_float(value: int) -> float:
    return float(value) / float(FP_ONE)


def fp_mul(a: int, b: int) -> int:
    return int((int(a) * int(b)) >> FP_SHIFT)


def clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, int(value)))


class TemporalMirror:
    """Python mirror of the Tier 4.31c C temporal-state update equations."""

    def __init__(self) -> None:
        self.init()

    def init(self) -> None:
        self.traces = [0 for _ in range(TEMPORAL_TRACE_COUNT)]
        self.schema_version = 1
        self.trace_count = TEMPORAL_TRACE_COUNT
        self.sham_mode = TEMPORAL_SHAM_ENABLED
        self.timescale_checksum = TEMPORAL_TIMESCALE_CHECKSUM
        self.update_count = 0
        self.saturation_count = 0
        self.reset_count = 0
        self.input_clip_count = 0
        self.trace_checksum = 0
        self.latest_input_raw = 0
        self.latest_novelty_raw = 0
        self.trace_abs_sum_raw = 0

    def clear_traces_only(self) -> None:
        self.traces = [0 for _ in range(TEMPORAL_TRACE_COUNT)]
        self.recompute_abs_sum()

    def set_sham(self, mode: int) -> None:
        self.sham_mode = int(mode)
        if mode in {TEMPORAL_SHAM_ZERO_STATE, TEMPORAL_SHAM_RESET_EACH_UPDATE}:
            self.clear_traces_only()
            self.trace_checksum = 0
            self.latest_novelty_raw = 0
            self.reset_count += 1

    def recompute_abs_sum(self) -> None:
        self.trace_abs_sum_raw = sum(abs(int(v)) for v in self.traces)

    def accumulate_checksum(self) -> None:
        weighted_sum = sum((i + 1) * int(v) for i, v in enumerate(self.traces))
        self.trace_checksum = ((self.trace_checksum * 2654435761) + (weighted_sum & 0xFFFFFFFF)) & 0xFFFFFFFF

    def update(self, input_raw: int) -> None:
        x = int(input_raw)
        slowest_before = int(self.traces[-1])
        if x > TEMPORAL_INPUT_BOUND:
            x = TEMPORAL_INPUT_BOUND
            self.input_clip_count += 1
        elif x < -TEMPORAL_INPUT_BOUND:
            x = -TEMPORAL_INPUT_BOUND
            self.input_clip_count += 1

        self.update_count += 1
        self.latest_input_raw = x
        self.latest_novelty_raw = clamp(x - slowest_before, -TEMPORAL_NOVELTY_BOUND, TEMPORAL_NOVELTY_BOUND)

        if self.sham_mode == TEMPORAL_SHAM_ZERO_STATE:
            self.clear_traces_only()
            self.latest_novelty_raw = 0
            self.accumulate_checksum()
            return

        if self.sham_mode == TEMPORAL_SHAM_RESET_EACH_UPDATE:
            self.clear_traces_only()
            self.reset_count += 1

        if self.sham_mode != TEMPORAL_SHAM_FROZEN_STATE:
            next_traces: list[int] = []
            for decay, alpha, trace in zip(TEMPORAL_DECAY_RAW, TEMPORAL_ALPHA_RAW, self.traces):
                candidate = fp_mul(decay, trace) + fp_mul(alpha, x)
                clipped = clamp(candidate, -TEMPORAL_TRACE_BOUND, TEMPORAL_TRACE_BOUND)
                if clipped != candidate:
                    self.saturation_count += 1
                next_traces.append(clipped)
            self.traces = next_traces

        self.recompute_abs_sum()
        self.accumulate_checksum()

    def summary(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "trace_count": self.trace_count,
            "sham_mode": self.sham_mode,
            "timescale_checksum": self.timescale_checksum,
            "update_count": self.update_count,
            "saturation_count": self.saturation_count,
            "reset_count": self.reset_count,
            "input_clip_count": self.input_clip_count,
            "trace_checksum": self.trace_checksum,
            "trace_abs_sum_raw": self.trace_abs_sum_raw,
            "trace_abs_sum": fp_to_float(self.trace_abs_sum_raw),
            "latest_input_raw": self.latest_input_raw,
            "latest_input": fp_to_float(self.latest_input_raw),
            "latest_novelty_raw": self.latest_novelty_raw,
            "latest_novelty": fp_to_float(self.latest_novelty_raw),
        }


def expected_scenarios(inputs_raw: list[int]) -> dict[str, dict[str, Any]]:
    scenarios: dict[str, dict[str, Any]] = {}

    enabled = TemporalMirror()
    for raw in inputs_raw:
        enabled.update(raw)
    scenarios["enabled"] = enabled.summary()

    zero = TemporalMirror()
    zero.set_sham(TEMPORAL_SHAM_ZERO_STATE)
    for raw in inputs_raw:
        zero.update(raw)
    scenarios["zero_state"] = zero.summary()

    frozen = TemporalMirror()
    frozen.update(FROZEN_SEED_RAW)
    frozen.set_sham(TEMPORAL_SHAM_FROZEN_STATE)
    for raw in inputs_raw:
        frozen.update(raw)
    scenarios["frozen_state"] = frozen.summary()

    reset = TemporalMirror()
    reset.set_sham(TEMPORAL_SHAM_RESET_EACH_UPDATE)
    for raw in inputs_raw:
        reset.update(raw)
    scenarios["reset_each_update"] = reset.summary()

    return scenarios


def compare_summary(name: str, observed: dict[str, Any], expected: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    fields = [
        "schema_version",
        "trace_count",
        "sham_mode",
        "timescale_checksum",
        "update_count",
        "saturation_count",
        "reset_count",
        "input_clip_count",
        "trace_checksum",
        "trace_abs_sum_raw",
        "latest_input_raw",
        "latest_novelty_raw",
    ]
    rows: list[dict[str, Any]] = []
    criteria: list[dict[str, Any]] = []
    for field in fields:
        obs = observed.get(field)
        exp = expected.get(field)
        match = obs == exp
        rows.append({"scenario": name, "field": field, "observed": obs, "expected": exp, "match": int(match)})
        criteria.append(criterion(f"{name} {field} matches reference", obs, f"== {exp}", match))
    rb = int(observed.get("readback_bytes") or 0)
    criteria.append(criterion(f"{name} compact readback bytes monotonic", rb, ">= 48 and multiple of 48", rb >= 48 and rb % 48 == 0))
    return rows, criteria


def py_compile_runner(output_dir: Path) -> dict[str, Any]:
    result = run_cmd([sys.executable, "-m", "py_compile", str(Path(__file__).relative_to(ROOT))])
    result["status"] = "pass" if result["returncode"] == 0 else "fail"
    (output_dir / "tier4_31d_py_compile_stdout.txt").write_text(result["stdout"], encoding="utf-8")
    (output_dir / "tier4_31d_py_compile_stderr.txt").write_text(result["stderr"], encoding="utf-8")
    return result


def run_runtime_checks(output_dir: Path) -> dict[str, Any]:
    commands = {
        "test_temporal_state": ["make", "-C", str(RUNTIME.relative_to(ROOT)), "clean-host", "test-temporal-state"],
        "test_profiles": ["make", "-C", str(RUNTIME.relative_to(ROOT)), "test-profiles"],
    }
    results: dict[str, Any] = {}
    for name, cmd in commands.items():
        item = run_cmd(cmd)
        item["status"] = "pass" if item["returncode"] == 0 else "fail"
        (output_dir / f"tier4_31d_{name}_stdout.txt").write_text(item["stdout"], encoding="utf-8")
        (output_dir / f"tier4_31d_{name}_stderr.txt").write_text(item["stderr"], encoding="utf-8")
        results[name] = item
    results["status"] = "pass" if all(item.get("status") == "pass" for item in results.values() if isinstance(item, dict)) else "fail"
    return results


def write_milestone(output_dir: Path, phase: str, status: str, extra: dict[str, Any] | None = None) -> None:
    write_json(output_dir / "tier4_31d_hw_milestone.json", {
        "tier": "4.31d-hw",
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "phase": phase,
        "status": status,
        "extra": extra or {},
    })


def build_aplx(output_dir: Path, args: argparse.Namespace) -> dict[str, Any]:
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
    env["RUNTIME_PROFILE"] = "learning_core"
    env["USE_MCPL_LOOKUP"] = "0"

    base_aplx = RUNTIME / "build" / "coral_reef.aplx"
    if base_aplx.exists():
        base_aplx.unlink()
    write_milestone(output_dir, "aplx_build", "started", {"runtime_profile": "learning_core"})
    stdout_path = output_dir / "tier4_31d_aplx_build_stdout.txt"
    stderr_path = output_dir / "tier4_31d_aplx_build_stderr.txt"
    result = run_cmd_to_files(
        ["make", "-C", str(RUNTIME), "clean", "all"],
        env=env,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        timeout=float(args.build_timeout_seconds),
    )

    profile_aplx = output_dir / "coral_reef_learning_core_temporal.aplx"
    if base_aplx.exists():
        if profile_aplx.exists():
            profile_aplx.unlink()
        shutil.copy2(base_aplx, profile_aplx)
    result.update({
        "runtime_profile": "learning_core",
        "spinnaker_tools": tools,
        "aplx_artifact": str(profile_aplx),
        "aplx_exists": profile_aplx.exists(),
        "base_elf_exists": (RUNTIME / "build" / "gnu" / "coral_reef.elf").exists(),
        "base_aplx_exists": base_aplx.exists(),
    })
    if result.get("timed_out"):
        result["status"] = "timeout"
    else:
        result["status"] = "pass" if result.get("returncode") == 0 and profile_aplx.exists() else "fail"
    write_milestone(output_dir, "aplx_build", result["status"], {
        "returncode": result.get("returncode"),
        "aplx_exists": profile_aplx.exists(),
        "base_elf_exists": result.get("base_elf_exists"),
        "base_aplx_exists": result.get("base_aplx_exists"),
    })
    return result


def clean_copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)

    def ignore(_dir: str, names: list[str]) -> set[str]:
        generated_host_tests = {
            "test_runtime",
            "test_context_core",
            "test_route_core",
            "test_memory_core",
            "test_learning_core",
            "test_lifecycle_core",
            "test_four_core_local",
            "test_four_core_48event",
            "test_mcpl_feasibility",
            "test_lifecycle",
            "test_lifecycle_split",
            "test_temporal_state",
        }
        ignored = {"__pycache__", ".pytest_cache", "build"} | generated_host_tests
        return {name for name in names if name in ignored or name.endswith((".pyc", ".o", ".aplx", ".elf"))}

    shutil.copytree(src, dst, ignore=ignore)


def prepare_bundle(output_dir: Path) -> tuple[Path, str, dict[str, str]]:
    bundle_root = output_dir / "ebrains_upload_bundle"
    if bundle_root.exists():
        shutil.rmtree(bundle_root)
    bundle = bundle_root / UPLOAD_PACKAGE_NAME
    (bundle / "experiments").mkdir(parents=True, exist_ok=True)
    (bundle / "coral_reef_spinnaker" / "python_host").mkdir(parents=True, exist_ok=True)

    for runner in [
        "tier4_31d_native_temporal_hardware_smoke.py",
        "tier4_22i_custom_runtime_roundtrip.py",
    ]:
        src = ROOT / "experiments" / runner
        dst = bundle / "experiments" / runner
        shutil.copy2(src, dst)
        os.chmod(dst, 0o755)
    shutil.copy2(ROOT / "coral_reef_spinnaker" / "__init__.py", bundle / "coral_reef_spinnaker" / "__init__.py")
    shutil.copy2(
        ROOT / "coral_reef_spinnaker" / "python_host" / "colony_controller.py",
        bundle / "coral_reef_spinnaker" / "python_host" / "colony_controller.py",
    )
    clean_copy_tree(RUNTIME, bundle / "coral_reef_spinnaker" / "spinnaker_runtime")

    command = f"{UPLOAD_PACKAGE_NAME}/experiments/tier4_31d_native_temporal_hardware_smoke.py --mode run-hardware --output-dir tier4_31d_hw_job_output"
    readme = bundle / "README_TIER4_31D_HW_JOB.md"
    readme.write_text(
        "# Tier 4.31d EBRAINS Native Temporal-Substrate Hardware Smoke\n\n"
        f"Upload the `{UPLOAD_PACKAGE_NAME}` folder itself so the JobManager path starts with `{UPLOAD_PACKAGE_NAME}/`. Do not upload `controlled_test_output`.\n\n"
        "JobManager command:\n\n"
        "```text\n"
        f"{command}\n"
        "```\n\n"
        f"Runner revision: `{RUNNER_REVISION}`.\n\n"
        "Purpose: build/load the learning_core runtime image and exercise C-owned temporal commands 39-42 on one real SpiNNaker board. The runner sends enabled, zero-state, frozen-state, and reset-each-update temporal-control sequences, then compares compact 48-byte readbacks against the fixed-point reference.\n\n"
        "Diagnostic artifacts to download on failure include `tier4_31d_hw_milestone.json`, `tier4_31d_hw_results.json`, `tier4_31d_aplx_build_stdout.txt`, and `tier4_31d_aplx_build_stderr.txt` when present. An ELF or profile stdout by itself is not hardware evidence.\n\n"
        "PASS is hardware execution/readback only: real target acquisition, no fallback, successful build/load, payload_len=48, schema/checksum/counter/reference matches, and destructive controls separated. It is not benchmark performance, speedup, multi-chip scaling, nonlinear recurrence, replay/sleep, or full v2.2 hardware transfer.\n",
        encoding="utf-8",
    )
    metadata = {
        "tier": TIER_NAME,
        "runner_revision": RUNNER_REVISION,
        "upload_package": UPLOAD_PACKAGE_NAME,
        "prepared_at_utc": utc_now(),
        "runner": "experiments/tier4_31d_native_temporal_hardware_smoke.py",
        "job_command": command,
        "claim_boundary": "Prepared source bundle only. Hardware evidence requires returned run-hardware artifacts from EBRAINS/SpiNNaker.",
        "controls": ["enabled", "zero_state", "frozen_state", "reset_each_update"],
        "temporal_payload_len": 48,
    }
    write_json(bundle / "metadata.json", metadata)

    STABLE_EBRAINS_UPLOAD.parent.mkdir(parents=True, exist_ok=True)
    if STABLE_EBRAINS_UPLOAD.exists():
        shutil.rmtree(STABLE_EBRAINS_UPLOAD)
    shutil.copytree(bundle, STABLE_EBRAINS_UPLOAD)
    return bundle, command, {"upload_bundle": str(bundle), "stable_upload_folder": str(STABLE_EBRAINS_UPLOAD), "job_readme": str(readme)}


def run_scenario(ctrl: Any, name: str, mode: int, inputs_raw: list[int], args: argparse.Namespace, *, seed_frozen: bool = False) -> dict[str, Any]:
    dest = {"dest_x": int(args.dest_x), "dest_y": int(args.dest_y), "dest_cpu": int(args.dest_cpu)}
    trace: list[dict[str, Any]] = []
    init = ctrl.temporal_init(**dest)
    trace.append({"scenario": name, "action": "init", **init})
    if not init.get("success"):
        return {"status": "fail", "reason": "temporal_init_failed", "trace": trace, "final": init}
    if seed_frozen:
        seeded = ctrl.temporal_update_raw(FROZEN_SEED_RAW, **dest)
        trace.append({"scenario": name, "action": "seed_update", "input_raw": FROZEN_SEED_RAW, **seeded})
        if not seeded.get("success"):
            return {"status": "fail", "reason": "frozen_seed_update_failed", "trace": trace, "final": seeded}
    if mode != TEMPORAL_SHAM_ENABLED:
        sham = ctrl.temporal_sham_mode(mode, **dest)
        trace.append({"scenario": name, "action": "set_sham", "mode": mode, **sham})
        if not sham.get("success"):
            return {"status": "fail", "reason": "temporal_sham_mode_failed", "trace": trace, "final": sham}
    for index, raw in enumerate(inputs_raw):
        update = ctrl.temporal_update_raw(raw, **dest)
        trace.append({"scenario": name, "action": "update", "index": index, "input_raw": raw, **update})
        if not update.get("success"):
            return {"status": "fail", "reason": "temporal_update_failed", "trace": trace, "final": update}
        time.sleep(float(args.command_delay_seconds))
    final = ctrl.temporal_read_state(**dest)
    trace.append({"scenario": name, "action": "read_state", **final})
    return {"status": "pass" if final.get("success") else "fail", "reason": "", "trace": trace, "final": final}


def temporal_roundtrip(hostname: str, args: argparse.Namespace) -> dict[str, Any]:
    from coral_reef_spinnaker.python_host.colony_controller import ColonyController

    started = time.perf_counter()
    ctrl = ColonyController(hostname, port=int(args.port), timeout=float(args.timeout_seconds))
    scenarios = {
        "enabled": (TEMPORAL_SHAM_ENABLED, False),
        "zero_state": (TEMPORAL_SHAM_ZERO_STATE, False),
        "frozen_state": (TEMPORAL_SHAM_FROZEN_STATE, True),
        "reset_each_update": (TEMPORAL_SHAM_RESET_EACH_UPDATE, False),
    }
    results: dict[str, Any] = {}
    try:
        for name, (mode, seed_frozen) in scenarios.items():
            results[name] = run_scenario(ctrl, name, mode, CANONICAL_INPUTS_RAW, args, seed_frozen=seed_frozen)
        return {"status": "pass" if all(r.get("status") == "pass" for r in results.values()) else "fail", "runtime_seconds": time.perf_counter() - started, "scenarios": results}
    except Exception as exc:
        return {
            "status": "fail",
            "runtime_seconds": time.perf_counter() - started,
            "exception_type": type(exc).__name__,
            "exception": str(exc),
            "traceback": traceback.format_exc(),
            "scenarios": results,
        }


def write_report(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Tier 4.31d Native Temporal-Substrate Hardware Smoke",
        "",
        f"- Generated: `{result.get('generated_at_utc')}`",
        f"- Mode: `{result.get('mode')}`",
        f"- Status: **{str(result.get('status')).upper()}**",
        f"- Runner revision: `{result.get('runner_revision')}`",
        "",
        "## Claim Boundary",
        "",
        f"{result.get('claim_boundary')}",
        "",
        "## Summary",
        "",
    ]
    for key, value in result.get("summary", {}).items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Criteria", "", "| Criterion | Value | Rule | Pass |", "| --- | --- | --- | --- |"])
    for item in result.get("criteria", []):
        lines.append(f"| {item.get('name')} | `{item.get('value')}` | {item.get('rule')} | {'yes' if item.get('passed') else 'no'} |")
    lines.extend(["", "## Artifacts", ""])
    for key, value in result.get("artifacts", {}).items():
        lines.append(f"- `{key}`: `{value}`")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def finalize(output_dir: Path, result: dict[str, Any]) -> int:
    result_path = output_dir / "tier4_31d_hw_results.json"
    report_path = output_dir / "tier4_31d_hw_report.md"
    summary_path = output_dir / "tier4_31d_hw_summary.csv"
    result.setdefault("artifacts", {})
    result["artifacts"].update({"results_json": str(result_path), "report_md": str(report_path), "summary_csv": str(summary_path)})
    write_json(result_path, result)
    write_report(report_path, result)
    write_csv(summary_path, result.get("criteria", []))
    write_json(LATEST_MANIFEST, result)
    print(json.dumps({"status": result.get("status"), "output_dir": str(output_dir), "results": str(result_path)}, indent=2))
    return 0 if str(result.get("status", "")).lower() in {"pass", "prepared"} else 1


def mode_prepare(args: argparse.Namespace, output_dir: Path) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    prereq_status = "missing"
    prereq: dict[str, Any] = {}
    if TIER431C_RESULTS.exists():
        prereq = json.loads(TIER431C_RESULTS.read_text(encoding="utf-8"))
        prereq_status = str(prereq.get("status", "unknown")).lower()
    host_checks = run_runtime_checks(output_dir)
    py_compile = py_compile_runner(output_dir)
    bundle, command, bundle_artifacts = prepare_bundle(output_dir)
    criteria = [
        criterion("Tier 4.31c prerequisite passed", prereq_status, "== pass", prereq_status == "pass"),
        criterion("runtime temporal/profile host checks pass", host_checks.get("status"), "== pass", host_checks.get("status") == "pass"),
        criterion("runner py_compile pass", py_compile.get("returncode"), "== 0", py_compile.get("returncode") == 0),
        criterion("upload bundle created", str(bundle), "exists", bundle.exists()),
        criterion("stable upload folder created", str(STABLE_EBRAINS_UPLOAD), "exists", STABLE_EBRAINS_UPLOAD.exists()),
        criterion("run-hardware command emitted", command, "contains --mode run-hardware", "--mode run-hardware" in command),
        criterion("bundle controller includes temporal parser", "parse_temporal_payload", "present", "parse_temporal_payload" in (bundle / "coral_reef_spinnaker" / "python_host" / "colony_controller.py").read_text(encoding="utf-8")),
    ]
    status = "prepared" if all(item["passed"] for item in criteria) else "blocked"
    result = {
        "tier": "4.31d-hw",
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
            "claim_boundary": "Prepared source bundle only; no hardware evidence until returned run-hardware artifacts pass.",
        },
        "criteria": criteria,
        "host_checks": host_checks,
        "py_compile": py_compile,
        "bundle_artifacts": bundle_artifacts,
        "claim_boundary": "Prepared source bundle only; no hardware evidence until returned run-hardware artifacts pass.",
    }
    return finalize(output_dir, result)


def mode_run_hardware(args: argparse.Namespace, output_dir: Path) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    write_milestone(output_dir, "run_hardware", "started")
    env_report = base.environment_report()
    write_milestone(output_dir, "host_checks", "started")
    host_checks = run_runtime_checks(output_dir)
    write_milestone(output_dir, "host_checks", str(host_checks.get("status", "unknown")))
    py_compile = py_compile_runner(output_dir)
    build = build_aplx(output_dir, args)
    expected = expected_scenarios(CANONICAL_INPUTS_RAW)
    target: dict[str, Any] = {"status": "not_attempted", "reason": "blocked_before_target_acquisition"}
    target_cleanup: dict[str, Any] = {"status": "not_attempted"}
    load: dict[str, Any] = {"status": "not_attempted"}
    roundtrip: dict[str, Any] = {"status": "not_attempted"}
    comparison_rows: list[dict[str, Any]] = []
    scenario_criteria: list[dict[str, Any]] = []

    try:
        if build.get("status") == "pass":
            write_milestone(output_dir, "target_acquisition", "started")
            target = base.acquire_hardware_target(args)
            hostname = str(target.get("hostname") or target.get("target_ipaddress") or "")
            write_milestone(output_dir, "target_acquisition", str(target.get("status", "unknown")), {"method": target.get("method", ""), "hostname": hostname})
            if target.get("status") == "pass" and hostname and not args.skip_load:
                write_milestone(output_dir, "load_application", "started")
                load = base.load_application_spinnman(
                    hostname,
                    Path(build["aplx_artifact"]),
                    x=int(args.dest_x),
                    y=int(args.dest_y),
                    p=int(target.get("dest_cpu") or args.dest_cpu),
                    app_id=int(args.app_id),
                    delay=float(args.startup_delay_seconds),
                    transceiver=target.get("_transceiver"),
                )
                write_milestone(output_dir, "load_application", str(load.get("status", "unknown")))
                args.dest_cpu = int(target.get("dest_cpu") or args.dest_cpu)
            if target.get("status") == "pass" and hostname and (load.get("status") == "pass" or args.skip_load):
                write_milestone(output_dir, "temporal_roundtrip", "started")
                roundtrip = temporal_roundtrip(hostname, args)
                write_milestone(output_dir, "temporal_roundtrip", str(roundtrip.get("status", "unknown")))
                for scenario_name, scenario_result in roundtrip.get("scenarios", {}).items():
                    final = scenario_result.get("final", {}) if isinstance(scenario_result, dict) else {}
                    rows, criteria = compare_summary(scenario_name, final, expected[scenario_name])
                    comparison_rows.extend(rows)
                    scenario_criteria.extend(criteria)
    finally:
        target_cleanup = base.release_hardware_target(target)

    write_json(output_dir / "tier4_31d_hw_environment.json", env_report)
    write_json(output_dir / "tier4_31d_hw_target_acquisition.json", base.public_target_acquisition({**target, "cleanup": target_cleanup}))
    write_json(output_dir / "tier4_31d_hw_build.json", build)
    write_json(output_dir / "tier4_31d_hw_load.json", load)
    write_json(output_dir / "tier4_31d_hw_expected.json", expected)
    write_json(output_dir / "tier4_31d_hw_roundtrip.json", roundtrip)
    write_csv(output_dir / "tier4_31d_hw_comparisons.csv", comparison_rows)

    scenario_statuses = {k: v.get("status") for k, v in roundtrip.get("scenarios", {}).items()} if isinstance(roundtrip, dict) else {}
    criteria = [
        criterion("runtime temporal/profile host checks pass", host_checks.get("status"), "== pass", host_checks.get("status") == "pass"),
        criterion("runner py_compile pass", py_compile.get("returncode"), "== 0", py_compile.get("returncode") == 0),
        criterion("learning_core APLX build pass", build.get("status"), "== pass", build.get("status") == "pass"),
        criterion("hardware target configured", target.get("status"), "== pass", target.get("status") == "pass"),
        criterion("hardware load pass", load.get("status"), "== pass", load.get("status") == "pass"),
        criterion("temporal roundtrip pass", roundtrip.get("status"), "== pass", roundtrip.get("status") == "pass"),
        criterion("all four temporal scenarios executed", scenario_statuses, "enabled/zero/frozen/reset all pass", set(scenario_statuses) == {"enabled", "zero_state", "frozen_state", "reset_each_update"} and all(v == "pass" for v in scenario_statuses.values())),
    ] + scenario_criteria
    status = "pass" if all(item["passed"] for item in criteria) else "fail"
    result = {
        "tier": "4.31d-hw",
        "tier_name": TIER_NAME,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "mode": "run-hardware",
        "status": status,
        "failure_reason": "" if status == "pass" else "Failed criteria: " + ", ".join(item["name"] for item in criteria if not item["passed"]),
        "output_dir": str(output_dir),
        "summary": {
            "hardware_target_configured": target.get("status") == "pass",
            "target_method": target.get("method", ""),
            "hostname": target.get("hostname") or target.get("target_ipaddress") or "",
            "dest_x": int(args.dest_x),
            "dest_y": int(args.dest_y),
            "dest_cpu": int(args.dest_cpu),
            "runtime_profile": "learning_core",
            "temporal_payload_len": 48,
            "scenario_statuses": scenario_statuses,
            "synthetic_fallback_used": False,
            "claim_boundary": CLAIM_BOUNDARY,
        },
        "criteria": criteria,
        "host_checks": host_checks,
        "py_compile": py_compile,
        "build": build,
        "target": base.public_target_acquisition({**target, "cleanup": target_cleanup}),
        "load": load,
        "roundtrip": roundtrip,
        "expected": expected,
        "claim_boundary": CLAIM_BOUNDARY,
    }
    write_milestone(output_dir, "finalize", status)
    return finalize(output_dir, result)


def copy_returned_artifacts(ingest_dir: Path, output_dir: Path, anchor: Path) -> list[str]:
    returned_dir = output_dir / "returned_artifacts"
    if returned_dir.exists():
        shutil.rmtree(returned_dir)
    returned_dir.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for path in sorted(ingest_dir.rglob("*")):
        if not path.is_file():
            continue
        try:
            rel = path.relative_to(anchor)
        except ValueError:
            rel = path.relative_to(ingest_dir)
        dst = returned_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dst)
        copied.append(str(dst))
    return copied


def copy_incomplete_returned_artifacts(ingest_dir: Path, output_dir: Path) -> list[str]:
    """Preserve a compact partial return without copying a whole Downloads tree."""
    tier_files = [path for path in ingest_dir.glob("tier4_31d*") if path.is_file()]
    if not tier_files:
        return []
    newest = max(path.stat().st_mtime for path in tier_files)
    window_seconds = 15 * 60
    candidates: list[Path] = []
    patterns = ("tier4_31d*", "coral_reef*.elf", "coral_reef*.aplx", "reports*.zip")
    for pattern in patterns:
        for path in ingest_dir.glob(pattern):
            if not path.is_file():
                continue
            if pattern == "tier4_31d*" or abs(path.stat().st_mtime - newest) <= window_seconds:
                candidates.append(path)

    returned_dir = output_dir / "returned_artifacts"
    if returned_dir.exists():
        shutil.rmtree(returned_dir)
    returned_dir.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for path in sorted(set(candidates)):
        dst = returned_dir / path.name
        shutil.copy2(path, dst)
        copied.append(str(dst))
    return copied


def mode_ingest(args: argparse.Namespace, output_dir: Path) -> int:
    ingest_dir = args.ingest_dir or Path.home() / "Downloads"
    output_dir.mkdir(parents=True, exist_ok=True)
    if args.hardware_results:
        candidate = args.hardware_results
    else:
        candidates = sorted(ingest_dir.rglob("tier4_31d_hw_results.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        candidate = candidates[0] if candidates else None
    if candidate is None or not candidate.exists():
        returned = copy_incomplete_returned_artifacts(ingest_dir, output_dir)
        result = {
            "tier": "4.31d-hw-ingest",
            "runner_revision": RUNNER_REVISION,
            "generated_at_utc": utc_now(),
            "mode": "ingest",
            "status": "fail",
            "failure_reason": "No tier4_31d_hw_results.json found in ingest directory.",
            "output_dir": str(output_dir),
            "summary": {"ingest_dir": str(ingest_dir), "returned_artifact_count": len(returned)},
            "criteria": [
                criterion("hardware results json exists", str(ingest_dir), "contains tier4_31d_hw_results.json", False),
                criterion("partial returned artifacts preserved", len(returned), "> 0 when partial artifacts exist", len(returned) > 0),
            ],
            "returned_artifacts": returned,
            "claim_boundary": "Ingest only preserves returned artifacts; it cannot create hardware evidence without run-hardware results.",
        }
        return finalize(output_dir, result)
    anchor = candidate.parent
    returned = copy_returned_artifacts(ingest_dir, output_dir, anchor)
    hardware = json.loads(candidate.read_text(encoding="utf-8"))
    criteria = [
        criterion("hardware results json exists", str(candidate), "exists", True),
        criterion("hardware mode was run-hardware", hardware.get("mode"), "== run-hardware", hardware.get("mode") == "run-hardware"),
        criterion("hardware status pass", hardware.get("status"), "== pass", hardware.get("status") == "pass"),
        criterion("runner revision current", hardware.get("runner_revision"), f"== {RUNNER_REVISION}", hardware.get("runner_revision") == RUNNER_REVISION),
        criterion("returned artifacts preserved", len(returned), "> 0", len(returned) > 0),
    ]
    status = "pass" if all(item["passed"] for item in criteria) else "fail"
    result = {
        "tier": "4.31d-hw-ingest",
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "mode": "ingest",
        "status": status,
        "failure_reason": "" if status == "pass" else "Failed criteria: " + ", ".join(item["name"] for item in criteria if not item["passed"]),
        "output_dir": str(output_dir),
        "summary": {
            "source_results": str(candidate),
            "returned_artifact_count": len(returned),
            "hardware_status": hardware.get("status"),
            "scenario_statuses": hardware.get("summary", {}).get("scenario_statuses"),
        },
        "criteria": criteria,
        "hardware_results": hardware,
        "returned_artifacts": returned,
        "claim_boundary": "Ingest confirms returned EBRAINS run-hardware artifacts only; baseline decisions remain separate.",
    }
    return finalize(output_dir, result)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["prepare", "run-hardware", "ingest"], default="prepare")
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--ingest-dir", type=Path, default=None)
    parser.add_argument("--hardware-results", type=Path, default=None)
    parser.add_argument("--spinnaker-hostname", default="")
    parser.add_argument("--target-acquisition", choices=["auto", "hostname", "spynnaker-probe"], default="auto")
    parser.add_argument("--target-probe-run-ms", type=float, default=1.0)
    parser.add_argument("--target-probe-timestep-ms", type=float, default=1.0)
    parser.add_argument("--target-probe-population-size", type=int, default=1)
    parser.add_argument("--auto-dest-cpu", dest="auto_dest_cpu", action="store_true", default=True)
    parser.add_argument("--no-auto-dest-cpu", dest="auto_dest_cpu", action="store_false")
    parser.add_argument("--port", type=int, default=17893)
    parser.add_argument("--timeout-seconds", type=float, default=2.0)
    parser.add_argument("--dest-x", type=int, default=0)
    parser.add_argument("--dest-y", type=int, default=0)
    parser.add_argument("--dest-cpu", type=int, default=1)
    parser.add_argument("--app-id", type=int, default=31)
    parser.add_argument("--startup-delay-seconds", type=float, default=1.0)
    parser.add_argument("--command-delay-seconds", type=float, default=COMMAND_DELAY_SECONDS)
    parser.add_argument("--build-timeout-seconds", type=float, default=180.0)
    parser.add_argument("--skip-load", action="store_true", help="Debug only; canonical evidence requires normal load.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.output_dir is None:
        if args.mode == "prepare":
            args.output_dir = DEFAULT_OUTPUT_DIR
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
        if args.mode == "ingest":
            return mode_ingest(args, args.output_dir)
    except Exception as exc:
        if args.mode == "run-hardware":
            result = {
                "tier": "4.31d-hw",
                "tier_name": TIER_NAME,
                "runner_revision": RUNNER_REVISION,
                "generated_at_utc": utc_now(),
                "mode": "run-hardware",
                "status": "fail",
                "failure_reason": f"Unhandled runner exception: {type(exc).__name__}: {exc}",
                "output_dir": str(args.output_dir),
                "summary": {"synthetic_fallback_used": False, "claim_boundary": CLAIM_BOUNDARY},
                "criteria": [criterion("runner reached structured finalization", type(exc).__name__, "no unhandled exception", False, str(exc))],
                "exception_type": type(exc).__name__,
                "exception": str(exc),
                "traceback": traceback.format_exc(),
                "claim_boundary": CLAIM_BOUNDARY,
            }
            write_milestone(args.output_dir, "unhandled_exception", "fail", {"exception_type": type(exc).__name__, "exception": str(exc)})
            return finalize(args.output_dir, result)
        raise
    raise AssertionError(args.mode)


if __name__ == "__main__":
    raise SystemExit(main())
