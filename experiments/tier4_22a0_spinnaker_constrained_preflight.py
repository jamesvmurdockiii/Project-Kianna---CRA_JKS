#!/usr/bin/env python3
"""Tier 4.22a0 SpiNNaker-constrained local preflight.

This is the cheap gate before more EBRAINS hardware time. It does not make a
new hardware/science claim. It checks that the proven chunked-host bridge and
keyed-memory bridge are still expressed in a SpiNNaker-compatible subset before
Tier 4.22b+ custom/hybrid runtime work begins:

- local constrained PyNN/NEST scheduled-input + binned-readback smoke,
- static PyNN/sPyNNaker feature compliance for the current bridge path,
- bounded SpiNNaker resource estimates using the repo constraint checker,
- optional sPyNNaker feature/tiny-smoke checks when a target context is present,
- host-side custom C runtime unit tests.

Claim boundary:
- PASS reduces hardware-transfer risk; it is not real hardware evidence.
- PASS does not prove custom C, native/on-chip learning, continuous execution,
  or speedup.
- Real hardware claims still require returned pyNN.spiNNaker artifacts with
  zero fallback, zero sim.run/readback failures, and nonzero real spike readback.
"""

from __future__ import annotations

import argparse
import csv
import importlib
import json
import math
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"
TIER = "Tier 4.22a0 - SpiNNaker-Constrained Local Preflight"
RUNNER_REVISION = "tier4_22a0_spinnaker_constrained_preflight_20260430_0000"
TIER4_22A_LATEST = CONTROLLED / "tier4_22a_latest_manifest.json"
TIER4_20C_LATEST = CONTROLLED / "tier4_20c_latest_manifest.json"
TIER4_21A_LATEST = CONTROLLED / "tier4_21a_latest_manifest.json"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from coral_reef_spinnaker.runtime_modes import make_runtime_plan  # noqa: E402
from coral_reef_spinnaker.spinnaker_constraints import (  # noqa: E402
    SpiNNakerConstraintChecker,
    quantize_weight_for_hardware,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    return value


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    keys: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                keys.append(key)
                seen.add(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def criterion(name: str, value: Any, rule: str, passed: bool, note: str = "") -> dict[str, Any]:
    return {"name": name, "value": value, "rule": rule, "passed": bool(passed), "note": note}


def markdown_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.6g}"
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(json_safe(value), sort_keys=True)
    return "" if value is None else str(value)


def latest_status(path: Path) -> tuple[str, str | None]:
    if not path.exists():
        return "missing", None
    try:
        payload = read_json(path)
    except Exception as exc:
        return f"unreadable:{type(exc).__name__}", None
    manifest = payload.get("manifest")
    return str(payload.get("status", "unknown")).lower(), str(manifest) if manifest else None


def compressed_schedule(currents: np.ndarray, dt_ms: float) -> tuple[list[float], list[float]]:
    times: list[float] = []
    amplitudes: list[float] = []
    last: float | None = None
    for step, amp in enumerate(currents):
        value = float(amp)
        if last is None or not math.isclose(value, last, abs_tol=1e-12):
            times.append(float(step) * dt_ms)
            amplitudes.append(value)
            last = value
    if not times or times[0] != 0.0:
        times.insert(0, 0.0)
        amplitudes.insert(0, 0.0)
    return times, amplitudes


def bin_spike_trains(spike_trains: Any, *, steps: int, dt_ms: float) -> np.ndarray:
    bins = np.zeros(int(steps), dtype=int)
    for train in spike_trains:
        for t in train:
            step = int(float(t) // dt_ms)
            if 0 <= step < steps:
                bins[step] += 1
    return bins


def run_constrained_nest_probe(args: argparse.Namespace) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Run a tiny hardware-legal PyNN/NEST scheduled-input probe."""

    started = time.perf_counter()
    rows: list[dict[str, Any]] = []
    try:
        import pyNN.nest as sim
    except Exception as exc:  # pragma: no cover - environment dependent
        return (
            {
                "status": "fail",
                "error": f"{type(exc).__name__}: {exc}",
                "runtime_seconds": time.perf_counter() - started,
            },
            rows,
        )

    dt_ms = float(args.timestep_ms)
    steps = int(args.steps)
    pop_size = int(args.population_size)
    currents = np.zeros(steps, dtype=float)
    for step in range(steps):
        phase = step % int(args.input_period_steps)
        if phase in {2, 3, 4, 5, 6, 7, 8}:
            currents[step] = float(args.input_amplitude)
        elif phase in {13, 14, 15}:
            currents[step] = float(args.input_amplitude) * 0.55
    times, amplitudes = compressed_schedule(currents, dt_ms)

    sim_run_failures = 0
    readback_failures = 0
    setup_ok = False
    spike_bins = np.zeros(steps, dtype=int)
    total_spikes = 0
    nonzero_bins = 0
    try:
        sim.setup(timestep=dt_ms, min_delay=dt_ms, max_delay=max(dt_ms, 8.0 * dt_ms))
        setup_ok = True
        cell = sim.IF_curr_exp(
            i_offset=0.0,
            tau_m=20.0,
            v_rest=-65.0,
            v_reset=-70.0,
            v_thresh=-55.0,
            tau_refrac=2.0,
            tau_syn_E=5.0,
            tau_syn_I=5.0,
            cm=0.25,
        )
        pop = sim.Population(pop_size, cell, label="tier4_22a0_constrained_nest_probe")
        pop.record("spikes")
        source = sim.StepCurrentSource(times=times, amplitudes=amplitudes)
        pop.inject(source)
        try:
            sim.run(float(steps) * dt_ms)
        except Exception:
            sim_run_failures += 1
            raise
        try:
            data = pop.get_data("spikes", clear=False)
            spike_bins = bin_spike_trains(data.segments[0].spiketrains, steps=steps, dt_ms=dt_ms)
            total_spikes = int(spike_bins.sum())
            nonzero_bins = int(np.count_nonzero(spike_bins))
        except Exception:
            readback_failures += 1
            raise
    except Exception as exc:
        status = "fail"
        error = f"{type(exc).__name__}: {exc}"
    else:
        status = "pass"
        error = ""
    finally:
        try:
            sim.end()
        except Exception:
            pass

    for step in range(steps):
        rows.append(
            {
                "step": step,
                "current": float(currents[step]),
                "spike_count": int(spike_bins[step]),
                "bin_active": bool(spike_bins[step] > 0),
            }
        )
    summary = {
        "status": status,
        "error": error,
        "backend": "pyNN.nest",
        "setup_ok": setup_ok,
        "population_size": pop_size,
        "steps": steps,
        "timestep_ms": dt_ms,
        "scheduled_input_mode": "StepCurrentSource",
        "scheduled_current_changes": len(times),
        "sim_run_calls": 1,
        "sim_run_failures": sim_run_failures,
        "readback_failures": readback_failures,
        "total_spikes": total_spikes,
        "nonzero_spike_bins": nonzero_bins,
        "max_bin_spikes": int(spike_bins.max()) if len(spike_bins) else 0,
        "mean_bin_spikes": float(np.mean(spike_bins)) if len(spike_bins) else 0.0,
        "runtime_seconds": time.perf_counter() - started,
        "claim_boundary": "Local constrained NEST smoke only; not SpiNNaker hardware evidence.",
    }
    return summary, rows


def module_import_rows() -> list[dict[str, Any]]:
    modules = ["nest", "pyNN", "pyNN.nest", "pyNN.spiNNaker"]
    rows: list[dict[str, Any]] = []
    for module in modules:
        started = time.perf_counter()
        try:
            imported = importlib.import_module(module)
            status = "pass"
            error = ""
            version = str(getattr(imported, "__version__", ""))
            if module == "nest" and not version and hasattr(imported, "version"):
                try:
                    version = str(imported.version())
                except Exception:
                    version = ""
        except Exception as exc:  # pragma: no cover - environment dependent
            status = "fail"
            error = f"{type(exc).__name__}: {exc}"
            version = ""
        rows.append(
            {
                "module": module,
                "status": status,
                "version": version,
                "error": error,
                "runtime_seconds": time.perf_counter() - started,
            }
        )
    return rows


def spynnaker_feature_check() -> dict[str, Any]:
    required = [
        "IF_curr_exp",
        "StepCurrentSource",
        "Population",
        "Projection",
        "StaticSynapse",
        "FromListConnector",
        "OneToOneConnector",
    ]
    try:
        sim = importlib.import_module("pyNN.spiNNaker")
    except Exception as exc:  # pragma: no cover - environment dependent
        return {"status": "fail", "error": f"{type(exc).__name__}: {exc}", "required": required, "available": []}
    available = [name for name in required if hasattr(sim, name)]
    missing = [name for name in required if name not in available]
    return {
        "status": "pass" if not missing else "fail",
        "error": "" if not missing else "Missing: " + ", ".join(missing),
        "required": required,
        "available": available,
        "missing": missing,
        "claim_boundary": "Feature import only by default; no hardware allocation or science run is attempted.",
    }


def run_optional_spynnaker_smoke(args: argparse.Namespace) -> dict[str, Any]:
    if not args.run_spynnaker_smoke:
        return {"status": "skipped", "reason": "--run-spynnaker-smoke not requested"}
    started = time.perf_counter()
    try:
        import pyNN.spiNNaker as sim
        setup_kwargs: dict[str, Any] = {"timestep": float(args.timestep_ms)}
        if args.spinnaker_hostname:
            setup_kwargs["spinnaker_hostname"] = str(args.spinnaker_hostname)
        sim.setup(**setup_kwargs)
        pop = sim.Population(1, sim.IF_curr_exp(i_offset=0.8, tau_m=20.0, v_thresh=-55.0), label="tier4_22a0_tiny_smoke")
        pop.record("spikes")
        sim.run(2.0 * float(args.timestep_ms))
        data = pop.get_data("spikes", clear=False)
        spike_count = sum(len(train) for train in data.segments[0].spiketrains)
    except Exception as exc:  # pragma: no cover - requires hardware context
        status = "fail"
        error = f"{type(exc).__name__}: {exc}"
        spike_count = 0
    else:
        status = "pass"
        error = ""
    finally:
        try:
            sim.end()  # type: ignore[name-defined]
        except Exception:
            pass
    return {
        "status": status,
        "error": error,
        "spike_count": int(spike_count),
        "runtime_seconds": time.perf_counter() - started,
        "claim_boundary": "Tiny sPyNNaker smoke only; not a CRA learning result.",
    }


def extract_function_source(path: Path, function_name: str) -> str:
    text = path.read_text(encoding="utf-8")
    needle = f"def {function_name}"
    start = text.find(needle)
    if start < 0:
        return ""
    next_def = text.find("\ndef ", start + len(needle))
    if next_def < 0:
        return text[start:]
    return text[start:next_def]


def static_compliance_rows() -> list[dict[str, Any]]:
    bridge_path = ROOT / "experiments" / "tier4_harder_spinnaker_capsule.py"
    keyed_path = ROOT / "experiments" / "tier4_21a_keyed_context_memory_bridge.py"
    contract_path = ROOT / "experiments" / "tier4_22a_custom_runtime_contract.py"
    bridge_source = extract_function_source(bridge_path, "run_chunked_spinnaker_task_seed")
    keyed_source = keyed_path.read_text(encoding="utf-8") if keyed_path.exists() else ""
    contract_source = contract_path.read_text(encoding="utf-8") if contract_path.exists() else ""

    checks = [
        {
            "scope": "tier4_16_chunked_bridge_function",
            "path": str(bridge_path),
            "check": "uses pyNN.spiNNaker in direct runner",
            "value": "pyNN.spiNNaker" in bridge_source,
            "rule": "required",
        },
        {
            "scope": "tier4_16_chunked_bridge_function",
            "path": str(bridge_path),
            "check": "uses IF_curr_exp",
            "value": "sim.IF_curr_exp" in bridge_source,
            "rule": "required hardware-supported cell model",
        },
        {
            "scope": "tier4_16_chunked_bridge_function",
            "path": str(bridge_path),
            "check": "uses StepCurrentSource scheduled input",
            "value": "sim.StepCurrentSource" in bridge_source,
            "rule": "required bridge input primitive",
        },
        {
            "scope": "tier4_16_chunked_bridge_function",
            "path": str(bridge_path),
            "check": "uses Population",
            "value": "sim.Population" in bridge_source,
            "rule": "required hardware population primitive",
        },
        {
            "scope": "tier4_16_chunked_bridge_function",
            "path": str(bridge_path),
            "check": "reads spikes through get_data",
            "value": "get_data(\"spikes\"" in bridge_source,
            "rule": "required binned readback path",
        },
        {
            "scope": "tier4_16_chunked_bridge_function",
            "path": str(bridge_path),
            "check": "does not create PyNN Projection in chunk bridge",
            "value": "sim.Projection" not in bridge_source,
            "rule": "no dynamic graph/projection mutation in bridge loop",
        },
        {
            "scope": "tier4_16_chunked_bridge_function",
            "path": str(bridge_path),
            "check": "does not use STDPMechanism in bridge runner",
            "value": "STDPMechanism" not in bridge_source,
            "rule": "host replay bridge must not imply unsupported native plasticity",
        },
        {
            "scope": "tier4_21a_keyed_bridge_source",
            "path": str(keyed_path),
            "check": "keyed memory bridge has explicit variants",
            "value": all(token in keyed_source for token in ["keyed_context_memory", "slot_reset_ablation", "slot_shuffle_ablation", "wrong_key_ablation"]),
            "rule": "candidate and shams must stay explicit",
        },
        {
            "scope": "tier4_21a_keyed_bridge_source",
            "path": str(keyed_path),
            "check": "keyed memory is bounded by configured slot count",
            "value": "context_memory_slot_count" in keyed_source and "max_context_memory_slot_count" in keyed_source,
            "rule": "bounded-state telemetry required",
        },
        {
            "scope": "tier4_22a_contract_source",
            "path": str(contract_path),
            "check": "contract declares constrained-NEST/sPyNNaker preflight",
            "value": "constrained-NEST" in contract_source and "sPyNNaker" in contract_source,
            "rule": "Tier 4.22a0 must stay in roadmap/contract",
        },
    ]
    rows: list[dict[str, Any]] = []
    for item in checks:
        passed = bool(item.pop("value"))
        rows.append({**item, "status": "pass" if passed else "fail", "passed": passed})
    return rows


def runtime_host_test(output_dir: Path, enabled: bool) -> dict[str, Any]:
    if not enabled:
        return {"status": "skipped", "reason": "--no-runtime-host-test"}
    started = utc_now()
    proc = subprocess.run(
        ["make", "test"],
        cwd=ROOT / "coral_reef_spinnaker" / "spinnaker_runtime",
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout_path = output_dir / "spinnaker_runtime_host_test_stdout.log"
    stderr_path = output_dir / "spinnaker_runtime_host_test_stderr.log"
    stdout_path.write_text(proc.stdout, encoding="utf-8")
    stderr_path.write_text(proc.stderr, encoding="utf-8")
    return {
        "status": "pass" if proc.returncode == 0 else "fail",
        "started_at_utc": started,
        "return_code": int(proc.returncode),
        "stdout_log": str(stdout_path),
        "stderr_log": str(stderr_path),
        "claim_boundary": "Host C runtime unit tests only; not hardware .aplx evidence.",
    }


def resource_rows(args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    checker = SpiNNakerConstraintChecker(num_chips=int(args.num_chips))
    population_size = int(args.population_size)
    slot_count = int(args.context_memory_slot_count)
    # The current chunked bridge has no recurrent PyNN Projection. Use a small
    # all-to-all planning row as a conservative custom-runtime budget probe.
    planned_connections = population_size * population_size
    checker.check_population(population_size, label="tier4_22a0_population")
    checker.check_projection(planned_connections, src_label="planned_local_pool", dst_label="planned_local_pool")
    checker.check_routing_entries(max(1, population_size), chip_id=0)
    summary = checker.summary()
    rows = [
        {
            "item": "population_neurons",
            "current": population_size,
            "limit": checker.max_neurons_per_core * max(1, int(args.num_chips)) * 17,
            "status": "pass" if summary["n_errors"] == 0 else "fail",
            "note": "N=8 bridge population should map far below one-chip limits.",
        },
        {
            "item": "planned_all_to_all_connections_budget_probe",
            "current": planned_connections,
            "limit": checker.sdram_per_core // 4,
            "status": "pass" if summary["n_errors"] == 0 else "fail",
            "note": "Conservative planning row; current bridge uses StepCurrentSource, not recurrent Projection.",
        },
        {
            "item": "keyed_context_slots",
            "current": slot_count,
            "limit": int(args.max_context_memory_slots_allowed),
            "status": "pass" if slot_count <= int(args.max_context_memory_slots_allowed) else "fail",
            "note": "Dynamic dict semantics must remain bounded before chip/hybrid state work.",
        },
    ]
    for weight in [-1.2, -1.0, -0.12345, 0.0, 0.12345, 0.999999, 1.2]:
        rows.append(
            {
                "item": "fixed_point_weight_quantization_probe",
                "current": weight,
                "limit": "[-1.0, 1.0)",
                "quantized": quantize_weight_for_hardware(weight),
                "status": "pass",
                "note": "Records the fixed-point clipping/rounding contract used for future runtime parity.",
            }
        )
    return rows, summary


def build_result(args: argparse.Namespace, output_dir: Path) -> dict[str, Any]:
    status420c, manifest420c = latest_status(TIER4_20C_LATEST)
    status421a, manifest421a = latest_status(TIER4_21A_LATEST)
    status422a, manifest422a = latest_status(TIER4_22A_LATEST)
    imports = module_import_rows()
    feature_check = spynnaker_feature_check()
    spynnaker_smoke = run_optional_spynnaker_smoke(args)
    static_rows = static_compliance_rows()
    resource, resource_summary = resource_rows(args)
    nest_summary, nest_rows = run_constrained_nest_probe(args)
    runtime_test = runtime_host_test(output_dir, not args.no_runtime_host_test)

    import_status = {row["module"]: row["status"] for row in imports}
    static_failures = [row for row in static_rows if not row["passed"]]
    resource_failures = [row for row in resource if row["status"] == "fail"]
    smoke_required = bool(args.require_spynnaker_smoke)
    smoke_ok = spynnaker_smoke["status"] == "pass" or (spynnaker_smoke["status"] == "skipped" and not smoke_required)

    runtime_plan = make_runtime_plan(
        runtime_mode="chunked",
        learning_location="host",
        chunk_size_steps=int(args.reference_chunk_size_steps),
        total_steps=int(args.reference_total_steps),
        dt_seconds=float(args.reference_dt_seconds),
    )
    continuous_plan = make_runtime_plan(
        runtime_mode="continuous",
        learning_location="on_chip",
        chunk_size_steps=int(args.reference_total_steps),
        total_steps=int(args.reference_total_steps),
        dt_seconds=float(args.reference_dt_seconds),
    )

    criteria = [
        criterion("runner revision current", RUNNER_REVISION, "expected current source", True),
        criterion("Tier 4.20c reference pass exists", status420c, "== pass", status420c == "pass", "Reference chunked-host bridge repeat."),
        criterion("Tier 4.21a reference pass exists", status421a, "== pass", status421a == "pass", "Reference keyed-memory bridge pass."),
        criterion("Tier 4.22a contract pass exists", status422a, "== pass", status422a == "pass", "Engineering contract must exist before this preflight."),
        criterion("NEST imports locally", import_status.get("nest"), "== pass", import_status.get("nest") == "pass"),
        criterion("pyNN.nest imports locally", import_status.get("pyNN.nest"), "== pass", import_status.get("pyNN.nest") == "pass"),
        criterion("pyNN.spiNNaker imports locally", import_status.get("pyNN.spiNNaker"), "== pass", import_status.get("pyNN.spiNNaker") == "pass"),
        criterion("sPyNNaker exposes required PyNN primitives", feature_check.get("status"), "== pass", feature_check.get("status") == "pass"),
        criterion("optional sPyNNaker tiny smoke satisfied if required", spynnaker_smoke.get("status"), "pass OR skipped when not required", smoke_ok),
        criterion("constrained NEST StepCurrentSource probe passed", nest_summary.get("status"), "== pass", nest_summary.get("status") == "pass"),
        criterion("constrained NEST produced nonzero spikes", nest_summary.get("total_spikes"), "> 0", int(nest_summary.get("total_spikes") or 0) > 0),
        criterion("constrained NEST sim/readback failures zero", {"sim": nest_summary.get("sim_run_failures"), "readback": nest_summary.get("readback_failures")}, "all == 0", int(nest_summary.get("sim_run_failures") or 0) == 0 and int(nest_summary.get("readback_failures") or 0) == 0),
        criterion("static PyNN bridge compliance passed", len(static_failures), "== 0 failed checks", len(static_failures) == 0),
        criterion("resource budget checks passed", len(resource_failures), "== 0 failed rows", len(resource_failures) == 0),
        criterion("custom runtime host tests passed", runtime_test.get("status"), "== pass", runtime_test.get("status") == "pass"),
        criterion("chunked reference remains implemented", runtime_plan.implemented, "True", runtime_plan.implemented is True),
        criterion("continuous/on-chip remains future until proven", continuous_plan.implemented, "False", continuous_plan.implemented is False),
    ]
    failed = [item["name"] for item in criteria if not item["passed"]]
    status = "pass" if not failed else "fail"
    summary = {
        "runner_revision": RUNNER_REVISION,
        "claim_boundary": "Local constrained preflight only; not real hardware evidence, not custom C evidence, not continuous/on-chip execution, and not speedup evidence.",
        "tier4_20c_status": status420c,
        "tier4_20c_manifest": manifest420c,
        "tier4_21a_status": status421a,
        "tier4_21a_manifest": manifest421a,
        "tier4_22a_status": status422a,
        "tier4_22a_manifest": manifest422a,
        "nest_status": nest_summary.get("status"),
        "nest_total_spikes": nest_summary.get("total_spikes"),
        "nest_nonzero_spike_bins": nest_summary.get("nonzero_spike_bins"),
        "spynnaker_feature_status": feature_check.get("status"),
        "spynnaker_smoke_status": spynnaker_smoke.get("status"),
        "static_compliance_failed_checks": len(static_failures),
        "resource_failed_rows": len(resource_failures),
        "runtime_host_test_status": runtime_test.get("status"),
        "reference_chunked_sim_run_calls": runtime_plan.sim_run_calls,
        "continuous_target_sim_run_calls": continuous_plan.sim_run_calls,
        "next_step_if_passed": "Tier 4.22b continuous no-learning scaffold: scheduled input, compact readback, no learning claim.",
        "next_step_if_failed": "Fix local constrained/mapping issue before spending EBRAINS hardware time.",
    }
    return {
        "tier": TIER,
        "generated_at_utc": utc_now(),
        "status": status,
        "failure_reason": "" if status == "pass" else "Failed criteria: " + ", ".join(failed),
        "output_dir": str(output_dir),
        "summary": summary,
        "criteria": criteria,
        "imports": imports,
        "spynnaker_feature_check": feature_check,
        "spynnaker_smoke": spynnaker_smoke,
        "constrained_nest_summary": nest_summary,
        "static_compliance": static_rows,
        "resource_budget": resource,
        "resource_checker_summary": resource_summary,
        "runtime_host_test": runtime_test,
        "artifacts": {},
    }, nest_rows


def write_report(path: Path, result: dict[str, Any]) -> None:
    summary = result["summary"]
    lines = [
        "# Tier 4.22a0 SpiNNaker-Constrained Local Preflight",
        "",
        f"- Generated: `{result['generated_at_utc']}`",
        f"- Status: **{result['status'].upper()}**",
        f"- Output directory: `{result['output_dir']}`",
        "",
        "Tier 4.22a0 is a local pre-hardware gate. It reduces transfer risk before more EBRAINS time, but it is not real SpiNNaker evidence.",
        "",
        "## Claim Boundary",
        "",
        "- `PASS` means constrained NEST, static PyNN/sPyNNaker feature compliance, bounded resource checks, and host runtime tests passed locally.",
        "- This is not custom C, native/on-chip CRA, continuous execution, or speedup evidence.",
        "- Real hardware claims still require returned pyNN.spiNNaker artifacts with zero fallback/failures and nonzero real spike readback.",
        "",
        "## Summary",
        "",
        f"- Tier 4.20c reference status: `{summary.get('tier4_20c_status')}`",
        f"- Tier 4.21a reference status: `{summary.get('tier4_21a_status')}`",
        f"- Tier 4.22a contract status: `{summary.get('tier4_22a_status')}`",
        f"- NEST probe status: `{summary.get('nest_status')}`",
        f"- NEST total spikes: `{markdown_value(summary.get('nest_total_spikes'))}`",
        f"- sPyNNaker feature status: `{summary.get('spynnaker_feature_status')}`",
        f"- sPyNNaker tiny smoke status: `{summary.get('spynnaker_smoke_status')}`",
        f"- Static compliance failed checks: `{summary.get('static_compliance_failed_checks')}`",
        f"- Resource failed rows: `{summary.get('resource_failed_rows')}`",
        f"- Runtime host test status: `{summary.get('runtime_host_test_status')}`",
        "",
        "## Criteria",
        "",
        "| Criterion | Value | Rule | Pass |",
        "| --- | --- | --- | --- |",
    ]
    for item in result["criteria"]:
        lines.append(f"| {item['name']} | `{markdown_value(item['value'])}` | `{item['rule']}` | {'yes' if item['passed'] else 'no'} |")
    lines.extend(
        [
            "",
            "## Static Compliance",
            "",
            "| Scope | Check | Rule | Pass |",
            "| --- | --- | --- | --- |",
        ]
    )
    for row in result["static_compliance"]:
        lines.append(f"| {row['scope']} | {row['check']} | {row['rule']} | {'yes' if row['passed'] else 'no'} |")
    lines.extend(
        [
            "",
            "## Resource Budget",
            "",
            "| Item | Current | Limit | Status | Note |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for row in result["resource_budget"]:
        lines.append(f"| {row['item']} | `{markdown_value(row.get('current'))}` | `{markdown_value(row.get('limit'))}` | `{row['status']}` | {row.get('note', '')} |")
    lines.extend(
        [
            "",
            "## Next Step",
            "",
            f"- If pass: {summary['next_step_if_passed']}",
            f"- If fail: {summary['next_step_if_failed']}",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_latest(output_dir: Path, manifest: Path, report: Path, status: str) -> None:
    write_json(
        CONTROLLED / "tier4_22a0_latest_manifest.json",
        {
            "generated_at_utc": utc_now(),
            "tier": TIER,
            "status": status,
            "output_dir": str(output_dir),
            "manifest": str(manifest),
            "report": str(report),
            "canonical": False,
            "claim": "Latest Tier 4.22a0 constrained local preflight; not real hardware evidence.",
        },
    )


def run(args: argparse.Namespace) -> int:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = (args.output_dir or CONTROLLED / f"tier4_22a0_{stamp}_spinnaker_constrained_preflight").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    result, nest_rows = build_result(args, output_dir)

    manifest = output_dir / "tier4_22a0_results.json"
    report = output_dir / "tier4_22a0_report.md"
    imports_csv = output_dir / "tier4_22a0_imports.csv"
    static_csv = output_dir / "tier4_22a0_static_compliance.csv"
    nest_csv = output_dir / "tier4_22a0_constrained_nest_timeseries.csv"
    resource_csv = output_dir / "tier4_22a0_resource_budget.csv"
    result["artifacts"] = {
        "manifest_json": str(manifest),
        "report_md": str(report),
        "imports_csv": str(imports_csv),
        "static_compliance_csv": str(static_csv),
        "constrained_nest_timeseries_csv": str(nest_csv),
        "resource_budget_csv": str(resource_csv),
        "runtime_host_test_stdout": result["runtime_host_test"].get("stdout_log"),
        "runtime_host_test_stderr": result["runtime_host_test"].get("stderr_log"),
    }
    write_csv(imports_csv, result["imports"])
    write_csv(static_csv, result["static_compliance"])
    write_csv(nest_csv, nest_rows)
    write_csv(resource_csv, result["resource_budget"])
    write_json(manifest, result)
    write_report(report, result)
    write_latest(output_dir, manifest, report, result["status"])
    print(json.dumps({"status": result["status"], "output_dir": str(output_dir), "manifest": str(manifest), "report": str(report)}, indent=2))
    return 0 if result["status"] == "pass" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Tier 4.22a0 SpiNNaker-constrained local preflight.")
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--steps", type=int, default=120)
    parser.add_argument("--population-size", type=int, default=8)
    parser.add_argument("--timestep-ms", type=float, default=1.0)
    parser.add_argument("--input-amplitude", type=float, default=0.85)
    parser.add_argument("--input-period-steps", type=int, default=20)
    parser.add_argument("--num-chips", type=int, default=1)
    parser.add_argument("--context-memory-slot-count", type=int, default=4)
    parser.add_argument("--max-context-memory-slots-allowed", type=int, default=16)
    parser.add_argument("--reference-total-steps", type=int, default=1200)
    parser.add_argument("--reference-chunk-size-steps", type=int, default=50)
    parser.add_argument("--reference-dt-seconds", type=float, default=1.0)
    parser.add_argument("--run-spynnaker-smoke", action="store_true", help="Attempt a tiny pyNN.spiNNaker run in the current target context.")
    parser.add_argument("--require-spynnaker-smoke", action="store_true", help="Fail if --run-spynnaker-smoke is skipped or fails.")
    parser.add_argument("--spinnaker-hostname", default="")
    parser.add_argument("--no-runtime-host-test", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    return run(build_parser().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
