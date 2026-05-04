#!/usr/bin/env python3
"""Tier 4.21a keyed context-memory hardware bridge probe.

Tier 4.20c proved that the v2.1 chunked-host bridge repeats across three real
SpiNNaker seeds, but it deliberately did not activate the v2 host-side keyed
memory mechanism. Tier 4.21a is the first targeted v2 mechanism bridge probe:
it tests whether the Tier 5.10g keyed context-memory path can be represented in
the chunked hardware transport by scheduling a causal host-side memory-transformed
input stream, reading real spikes, and replaying the existing host learner.

Claim boundary:
- Prepared output is not hardware evidence.
- A local-bridge PASS is a source/logic preflight only.
- A run-hardware PASS means the keyed context-memory *bridge adapter* executed
  through real pyNN.spiNNaker with spike readback; it is not native/on-chip
  memory, not custom C, and not continuous execution.
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
import time
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from coral_reef_spinnaker.runtime_modes import chunk_ranges  # noqa: E402
from coral_reef_spinnaker.spinnaker_compat import apply_spinnaker_numpy2_compat_patches  # noqa: E402
from experiments import tier4_20b_v2_1_hardware_probe as bridge  # noqa: E402
from tier2_learning import markdown_value, pass_fail, plot_case, strict_sign, write_csv, write_json  # noqa: E402
from tier4_harder_spinnaker_capsule import (  # noqa: E402
    ChunkedHostReplay,
    bin_spiketrains,
    compressed_current_schedule,
    task_horizon,
)
from tier4_scaling import mean, min_value, stdev  # noqa: E402
from tier5_external_baselines import TaskStream, summarize_rows  # noqa: E402
from tier5_keyed_context_memory import (  # noqa: E402
    build_parser as build_tier5_10g_parser,
    build_tasks,
    context_memory_key_for_step,
)

TIER = "Tier 4.21a - Keyed Context-Memory Hardware Bridge Probe"
RUNNER_REVISION = "tier4_21a_keyed_memory_bridge_20260430_0000"
TIER4_20C_LATEST = CONTROLLED / "tier4_20c_latest_manifest.json"
DEFAULT_TASKS = "context_reentry_interference"
DEFAULT_VARIANTS = "keyed_context_memory,slot_reset_ablation,slot_shuffle_ablation,wrong_key_ablation"
DEFAULT_SEEDS = "42"
DEFAULT_STEPS = 720
DEFAULT_CHUNK_SIZE = 50
DEFAULT_POPULATION_SIZE = 8
DEFAULT_DELAYED_LR = 0.20
ALLOWED_TASKS = {"intervening_contexts", "overlapping_contexts", "context_reentry_interference"}
ALLOWED_VARIANTS = {
    "keyed_context_memory": "candidate",
    "slot_reset_ablation": "memory_ablation",
    "slot_shuffle_ablation": "memory_ablation",
    "wrong_key_ablation": "memory_ablation",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def criterion(name: str, value: Any, rule: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "value": value, "rule": rule, "passed": bool(passed)}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_csv(value: str) -> list[str]:
    items = [item.strip() for item in str(value).split(",") if item.strip()]
    if not items:
        raise argparse.ArgumentTypeError("at least one item is required")
    return items


def parse_tasks(value: str) -> list[str]:
    tasks = parse_csv(value)
    unknown = [task for task in tasks if task not in ALLOWED_TASKS]
    if unknown:
        raise argparse.ArgumentTypeError(f"unknown Tier 4.21a task(s): {', '.join(unknown)}")
    return tasks


def parse_variants(value: str) -> list[str]:
    variants = parse_csv(value)
    unknown = [variant for variant in variants if variant not in ALLOWED_VARIANTS]
    if unknown:
        raise argparse.ArgumentTypeError(f"unknown Tier 4.21a variant(s): {', '.join(unknown)}")
    if "keyed_context_memory" not in variants:
        raise argparse.ArgumentTypeError("Tier 4.21a requires keyed_context_memory")
    return variants


def parse_seeds(value: str) -> list[int]:
    try:
        return [int(item) for item in parse_csv(value)]
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def latest_420c_status() -> tuple[str, str | None]:
    if not TIER4_20C_LATEST.exists():
        return "missing", None
    try:
        payload = read_json(TIER4_20C_LATEST)
    except Exception:
        return "unreadable", None
    return str(payload.get("status", "unknown")).lower(), str(payload.get("manifest") or "")


def task_args_for(args: argparse.Namespace, task_name: str) -> argparse.Namespace:
    task_args = build_tier5_10g_parser().parse_args([])
    task_args.tasks = task_name
    task_args.steps = int(args.steps)
    task_args.amplitude = float(args.amplitude)
    task_args.task_seed = int(args.task_seed)
    task_args.capacity_period = int(args.capacity_period)
    task_args.capacity_decision_gap = int(args.capacity_decision_gap)
    task_args.interfering_contexts = int(args.interfering_contexts)
    task_args.interference_spacing = int(args.interference_spacing)
    task_args.interfering_context_scale = float(args.interfering_context_scale)
    task_args.overlap_period = int(args.overlap_period)
    task_args.overlap_context_gap = int(args.overlap_context_gap)
    task_args.overlap_first_decision_gap = int(args.overlap_first_decision_gap)
    task_args.overlap_second_decision_gap = int(args.overlap_second_decision_gap)
    task_args.reentry_phase_len = int(args.reentry_phase_len)
    task_args.reentry_decision_stride = int(args.reentry_decision_stride)
    task_args.reentry_interference_probability = float(args.reentry_interference_probability)
    task_args.distractor_density = float(args.distractor_density)
    task_args.distractor_scale = float(args.distractor_scale)
    return task_args


def build_memory_task(task_name: str, *, seed: int, args: argparse.Namespace):
    built = build_tasks(task_args_for(args, task_name), seed=int(args.task_seed) + int(seed))
    if len(built) != 1:
        raise RuntimeError(f"expected one memory task for {task_name}, got {len(built)}")
    return built[0]


def _touch(order: list[str], key: str) -> None:
    if key in order:
        order.remove(key)
    order.append(key)


def _write_slot(slots: dict[str, int], order: list[str], key: str, sign: int, max_slots: int) -> None:
    if key not in slots and len(slots) >= max_slots and order:
        evicted = order.pop(0)
        slots.pop(evicted, None)
    slots[key] = int(sign)
    _touch(order, key)


def _read_slot(slots: dict[str, int], order: list[str], key: str, fallback: int) -> int:
    if key in slots:
        _touch(order, key)
        return int(slots[key])
    return int(fallback)


def _alternate_slot(slots: dict[str, int], order: list[str], key: str, fallback: int) -> int:
    for candidate in reversed(order):
        if candidate != key and candidate in slots:
            return int(slots[candidate])
    return int(-fallback if fallback else -1)


def transform_for_variant(memory_task: Any, *, variant: str, amplitude: float, slot_count: int) -> tuple[TaskStream, list[dict[str, Any]], dict[str, Any]]:
    stream = memory_task.stream
    transformed = np.asarray(stream.sensory, dtype=float).copy()
    slots: dict[str, int] = {}
    order: list[str] = []
    global_context = 1
    updates = 0
    feature_active_steps = 0
    max_slots_seen = 0
    events: list[dict[str, Any]] = []
    max_slots = max(1, int(slot_count))
    for step in range(stream.steps):
        raw = float(stream.sensory[step])
        event = str(memory_task.event_type[step])
        key = context_memory_key_for_step(memory_task, step)
        raw_sign = strict_sign(raw)
        source = "raw"
        cue_sign = 0
        context = int(global_context)
        if event == "context" and raw_sign != 0:
            global_context = int(raw_sign)
            context = int(global_context)
            _write_slot(slots, order, key, int(raw_sign), max_slots)
            updates += 1
            source = "context_update"
        elif event == "decision" and raw_sign != 0:
            cue_sign = int(raw_sign)
            keyed = _read_slot(slots, order, key, int(global_context))
            if variant == "keyed_context_memory":
                context = keyed
                transformed[step] = float(amplitude * context * cue_sign)
                source = "bridge_keyed_context"
            elif variant == "slot_reset_ablation":
                context = 1
                transformed[step] = float(amplitude * cue_sign)
                source = "bridge_slot_reset_no_context"
            elif variant in {"slot_shuffle_ablation", "wrong_key_ablation"}:
                context = _alternate_slot(slots, order, key, keyed)
                transformed[step] = float(amplitude * context * cue_sign)
                source = "bridge_wrong_or_shuffled_slot"
            else:
                transformed[step] = raw
                source = "raw"
            feature_active_steps += int(source != "raw")
        max_slots_seen = max(max_slots_seen, len(slots))
        events.append(
            {
                "step": int(step),
                "event_type": event,
                "phase": str(memory_task.phase[step]),
                "trial_id": int(memory_task.trial_id[step]),
                "context_memory_key": key,
                "raw_sensory": raw,
                "transformed_sensory": float(transformed[step]),
                "context_memory_value": int(context),
                "visible_cue_sign": int(cue_sign),
                "context_memory_updates": int(updates),
                "context_memory_slot_count": int(len(slots)),
                "feature_active": bool(source not in {"raw", "context_update"}),
                "feature_source": source,
            }
        )
    transformed_stream = replace(stream, sensory=transformed)
    summary = {
        "feature_active_steps": int(feature_active_steps),
        "context_memory_updates": int(updates),
        "max_context_memory_slot_count": int(max_slots_seen),
        "slot_count_configured": int(slot_count),
    }
    return transformed_stream, events, summary


def scheduled_currents_from_sensory(sensory: np.ndarray, args: argparse.Namespace) -> np.ndarray:
    unit = np.zeros(len(sensory), dtype=float)
    if abs(float(args.amplitude)) > 0.0:
        unit = np.asarray(sensory, dtype=float) / float(args.amplitude)
    currents = float(args.base_current_na) + float(args.cue_current_gain_na) * unit
    return np.clip(currents, float(args.min_current_na), None)


def run_bridge_task_seed_variant(
    *,
    task_name: str,
    seed: int,
    variant: str,
    args: argparse.Namespace,
    hardware: bool,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    memory_task = build_memory_task(task_name, seed=seed, args=args)
    transformed_stream, memory_events, memory_summary = transform_for_variant(
        memory_task,
        variant=variant,
        amplitude=float(args.amplitude),
        slot_count=int(args.context_memory_slot_count),
    )
    replay = ChunkedHostReplay(
        lr=float(args.delayed_readout_lr),
        amplitude=float(args.amplitude),
        population_size=int(args.population_size),
    )
    rows: list[dict[str, Any]] = []
    diagnostics = {
        "sim_run_failures": 0,
        "summary_read_failures": 0,
        "synthetic_fallbacks": 0,
        "scheduled_input_failures": 0,
        "spike_readback_failures": 0,
    }
    spike_bins = np.zeros(transformed_stream.steps, dtype=int)
    calls = 0
    started = time.perf_counter()
    sim = None
    pop = None
    dt_ms = float(args.dt_seconds) * 1000.0
    currents = scheduled_currents_from_sensory(transformed_stream.sensory, args)
    try:
        if hardware:
            compat_status = apply_spinnaker_numpy2_compat_patches()
            import pyNN.spiNNaker as sim  # type: ignore

            setup_kwargs: dict[str, Any] = {"timestep": args.timestep_ms}
            if args.spinnaker_hostname:
                setup_kwargs["spinnaker_hostname"] = args.spinnaker_hostname
            sim.setup(**setup_kwargs)
            if not hasattr(sim, "StepCurrentSource"):
                diagnostics["scheduled_input_failures"] = 1
                raise RuntimeError("pyNN.spiNNaker does not expose StepCurrentSource")
            cell = sim.IF_curr_exp(i_offset=0.0, tau_m=20.0, v_rest=-65.0, v_reset=-70.0, v_thresh=-55.0, tau_refrac=2.0, cm=0.25)
            pop = sim.Population(int(args.population_size), cell, label=f"tier4_21a_{task_name}_{variant}_seed{seed}")
            pop.record("spikes")
            times, amplitudes = compressed_current_schedule(currents, dt_ms)
            pop.inject(sim.StepCurrentSource(times=times, amplitudes=amplitudes))
        else:
            compat_status = {"hardware": False, "mode": "local_bridge_sim"}

        for start, stop in chunk_ranges(transformed_stream.steps, int(args.chunk_size_steps)):
            if hardware:
                try:
                    sim.run(float(stop - start) * dt_ms)  # type: ignore[union-attr]
                    calls += 1
                except Exception:
                    diagnostics["sim_run_failures"] += 1
                    raise
                try:
                    data = pop.get_data("spikes", clear=False)  # type: ignore[union-attr]
                    spike_bins = bin_spiketrains(data.segments[0].spiketrains, steps=transformed_stream.steps, dt_ms=dt_ms)
                except Exception:
                    diagnostics["summary_read_failures"] += 1
                    diagnostics["spike_readback_failures"] += 1
                    raise
            else:
                calls += 1
                local_scale = np.abs(np.asarray(transformed_stream.sensory[start:stop], dtype=float)) / max(abs(float(args.amplitude)), 1e-12)
                spike_bins[start:stop] = np.maximum(0, np.rint(local_scale * int(args.population_size) * 10.0)).astype(int)
            for step in range(start, stop):
                row = replay.step(task=transformed_stream, step=step, spike_count=int(spike_bins[step]))
                mem = memory_events[step]
                eval_sign = strict_sign(float(transformed_stream.evaluation_target[step]))
                pred_sign = strict_sign(float(row.get("colony_prediction", 0.0)))
                row.update(
                    {
                        "tier": TIER,
                        "task": task_name,
                        "variant": variant,
                        "variant_group": ALLOWED_VARIANTS[variant],
                        "model": variant,
                        "model_family": "CRA_bridge",
                        "backend": "pyNN.spiNNaker" if hardware else "local_bridge_sim",
                        "backend_path": "keyed_memory_scheduler_stepcurrent_chunked_host_replay" if hardware else "keyed_memory_scheduler_local_host_replay",
                        "seed": int(seed),
                        "runtime_mode": "chunked",
                        "learning_location": "host",
                        "chunk_size_steps": int(args.chunk_size_steps),
                        "sim_run_calls": int(calls),
                        "event_type": mem["event_type"],
                        "phase": mem["phase"],
                        "trial_id": mem["trial_id"],
                        "context_memory_key": mem["context_memory_key"],
                        "raw_sensory_return_1m": mem["raw_sensory"],
                        "sensory_return_1m": mem["transformed_sensory"],
                        "context_memory_value": mem["context_memory_value"],
                        "context_memory_visible_cue_sign": mem["visible_cue_sign"],
                        "context_memory_updates": mem["context_memory_updates"],
                        "context_memory_slot_count": mem["context_memory_slot_count"],
                        "context_memory_feature_active": mem["feature_active"],
                        "context_memory_feature_source": mem["feature_source"],
                        "target_signal_sign": eval_sign,
                        "prediction_sign": pred_sign,
                        "strict_direction_correct": bool(transformed_stream.evaluation_mask[step] and pred_sign != 0 and pred_sign == eval_sign),
                        "sim_run_failures": int(diagnostics["sim_run_failures"]),
                        "summary_read_failures": int(diagnostics["summary_read_failures"]),
                        "synthetic_fallbacks": int(diagnostics["synthetic_fallbacks"]),
                    }
                )
                rows.append(row)
    finally:
        if hardware and sim is not None:
            try:
                sim.end()
            except Exception:
                pass
    summary = summarize_rows(rows)
    step_spikes = [float(r.get("step_spike_count", 0.0)) for r in rows]
    summary.update(
        {
            "task": task_name,
            "variant": variant,
            "variant_group": ALLOWED_VARIANTS[variant],
            "backend": "pyNN.spiNNaker" if hardware else "local_bridge_sim",
            "backend_path": "keyed_memory_scheduler_stepcurrent_chunked_host_replay" if hardware else "keyed_memory_scheduler_local_host_replay",
            "seed": int(seed),
            "steps": int(transformed_stream.steps),
            "population_size": int(args.population_size),
            "runtime_mode": "chunked",
            "learning_location": "host",
            "chunk_size_steps": int(args.chunk_size_steps),
            "sim_run_calls": int(calls),
            "runtime_seconds": time.perf_counter() - started,
            "total_step_spikes": int(sum(step_spikes)),
            "mean_step_spikes": float(np.mean(step_spikes)) if step_spikes else 0.0,
            "scheduled_current_changes": len(compressed_current_schedule(currents, dt_ms)[0]),
            "scheduled_current_min": float(np.min(currents)) if len(currents) else None,
            "scheduled_current_max": float(np.max(currents)) if len(currents) else None,
            "task_metadata": transformed_stream.metadata,
            "spinnman_numpy2_compat": compat_status,
            **memory_summary,
            **diagnostics,
        }
    )
    return rows, summary


def aggregate_summaries(summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    keys = [
        "all_accuracy",
        "tail_accuracy",
        "prediction_target_corr",
        "tail_prediction_target_corr",
        "runtime_seconds",
        "evaluation_count",
        "feature_active_steps",
        "context_memory_updates",
        "max_context_memory_slot_count",
        "total_step_spikes",
        "mean_step_spikes",
        "sim_run_failures",
        "summary_read_failures",
        "synthetic_fallbacks",
    ]
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for summary in summaries:
        grouped.setdefault((str(summary["task"]), str(summary["variant"])), []).append(summary)
    rows: list[dict[str, Any]] = []
    for (task, variant), group in sorted(grouped.items()):
        row: dict[str, Any] = {
            "task": task,
            "variant": variant,
            "variant_group": group[0].get("variant_group"),
            "runs": len(group),
            "seeds": [item.get("seed") for item in group],
            "backend": group[0].get("backend"),
            "backend_path": group[0].get("backend_path"),
        }
        for key in keys:
            vals = [item.get(key) for item in group]
            row[f"{key}_mean"] = mean(vals)
            row[f"{key}_std"] = stdev(vals)
            row[f"{key}_min"] = min_value(vals)
            valid = [float(v) for v in vals if v is not None]
            row[f"{key}_max"] = max(valid) if valid else None
            row[f"{key}_sum"] = float(sum(valid)) if valid else None
        rows.append(row)
    return rows


def build_comparisons(aggregates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by = {(row["task"], row["variant"]): row for row in aggregates}
    rows: list[dict[str, Any]] = []
    for task in sorted({row["task"] for row in aggregates}):
        candidate = by.get((task, "keyed_context_memory"), {})
        controls = [row for row in aggregates if row["task"] == task and row.get("variant_group") == "memory_ablation"]
        best = max(controls, key=lambda r: float(r.get("all_accuracy_mean") or 0.0), default={})
        rows.append(
            {
                "task": task,
                "keyed_all_accuracy": candidate.get("all_accuracy_mean"),
                "keyed_tail_accuracy": candidate.get("tail_accuracy_mean"),
                "keyed_context_memory_updates": candidate.get("context_memory_updates_max"),
                "keyed_feature_active_steps": candidate.get("feature_active_steps_sum"),
                "keyed_max_slots": candidate.get("max_context_memory_slot_count_max"),
                "best_ablation": best.get("variant"),
                "best_ablation_all_accuracy": best.get("all_accuracy_mean"),
                "keyed_delta_vs_best_ablation": float(candidate.get("all_accuracy_mean") or 0.0) - float(best.get("all_accuracy_mean") or 0.0),
                "keyed_tail_delta_vs_best_ablation": float(candidate.get("tail_accuracy_mean") or 0.0) - float(best.get("tail_accuracy_mean") or 0.0),
            }
        )
    return rows


def evaluate(*, args: argparse.Namespace, mode: str, summaries: list[dict[str, Any]], aggregates: list[dict[str, Any]], comparisons: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    c_status, c_manifest = latest_420c_status()
    expected_runs = len(args.tasks) * len(args.seeds) * len(args.variants)
    sim_failures = int(sum(int(s.get("sim_run_failures", 0) or 0) for s in summaries))
    read_failures = int(sum(int(s.get("summary_read_failures", 0) or 0) for s in summaries))
    fallback = int(sum(int(s.get("synthetic_fallbacks", 0) or 0) for s in summaries))
    min_spikes = min([float(s.get("total_step_spikes") or 0.0) for s in summaries], default=0.0)
    keyed_rows = [row for row in aggregates if row["variant"] == "keyed_context_memory"]
    keyed_updates = sum(float(row.get("context_memory_updates_max") or 0.0) for row in keyed_rows)
    keyed_features = sum(float(row.get("feature_active_steps_sum") or 0.0) for row in keyed_rows)
    keyed_slots = max([float(row.get("max_context_memory_slot_count_max") or 0.0) for row in keyed_rows], default=0.0)
    edges = [float(row.get("keyed_delta_vs_best_ablation") or 0.0) for row in comparisons]
    criteria = [
        criterion("all requested task/seed/variant runs completed", len(summaries), f"== {expected_runs}", len(summaries) == expected_runs),
        criterion("sim.run failures zero", sim_failures, "== 0", sim_failures == 0),
        criterion("summary/readback failures zero", read_failures, "== 0", read_failures == 0),
        criterion("synthetic fallback zero", fallback, "== 0", fallback == 0),
        criterion("keyed memory updates observed", keyed_updates, "> 0", keyed_updates > 0),
        criterion("keyed memory feature active at decisions", keyed_features, "> 0", keyed_features > 0),
        criterion("keyed memory retains more than one slot", keyed_slots, ">= 2", keyed_slots >= 2),
        criterion("keyed candidate not worse than best memory ablation", min(edges) if edges else None, ">= min edge", bool(edges) and min(edges) >= float(args.min_keyed_edge_vs_ablation)),
    ]
    if mode == "run-hardware":
        criteria.append(criterion("real spike readback nonzero", min_spikes, "> 0", min_spikes > 0.0))
    summary = {
        "baseline": "v2.1",
        "runner_revision": RUNNER_REVISION,
        "tasks": args.tasks,
        "seeds": args.seeds,
        "variants": args.variants,
        "steps": args.steps,
        "population_size": args.population_size,
        "runtime_mode": "chunked",
        "learning_location": "host",
        "chunk_size_steps": args.chunk_size_steps,
        "context_memory_slot_count": args.context_memory_slot_count,
        "hardware_run_attempted": mode == "run-hardware",
        "runs": len(summaries),
        "expected_runs": expected_runs,
        "sim_run_failures_sum": sim_failures,
        "summary_read_failures_sum": read_failures,
        "synthetic_fallbacks_sum": fallback,
        "total_step_spikes_min": min_spikes,
        "keyed_context_memory_updates_sum": keyed_updates,
        "keyed_feature_active_steps_sum": keyed_features,
        "keyed_max_context_memory_slots": keyed_slots,
        "claim_boundary": "Targeted keyed context-memory bridge probe only; host-side scheduler plus chunked PyNN readback, not native/on-chip memory.",
        "comparisons": comparisons,
        "aggregates": aggregates,
    }
    return criteria, summary


def write_summary_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    bridge.write_csv(path, rows)


def write_report(path: Path, result: dict[str, Any]) -> None:
    summary = result["summary"]
    lines = [
        "# Tier 4.21a Keyed Context-Memory Hardware Bridge Probe",
        "",
        f"- Generated: `{result['generated_at_utc']}`",
        f"- Mode: `{result['mode']}`",
        f"- Status: **{result['status'].upper()}**",
        f"- Output directory: `{result['output_dir']}`",
        "",
        "Tier 4.21a is a targeted v2 mechanism bridge probe for keyed context memory. It tests the host-side keyed-memory scheduler through the chunked PyNN/SpiNNaker transport path.",
        "",
        "## Claim Boundary",
        "",
        "- `PREPARED` is not hardware evidence.",
        "- `LOCAL-BRIDGE` is source/logic preflight only.",
        "- `RUN-HARDWARE` with `PASS` is keyed-memory bridge evidence, not native/on-chip memory, custom C, continuous execution, language, planning, or AGI.",
        "",
        "## Summary",
        "",
    ]
    for key in [
        "baseline",
        "runner_revision",
        "tasks",
        "seeds",
        "variants",
        "steps",
        "population_size",
        "chunk_size_steps",
        "context_memory_slot_count",
        "hardware_run_attempted",
        "runs",
        "expected_runs",
        "sim_run_failures_sum",
        "summary_read_failures_sum",
        "synthetic_fallbacks_sum",
        "total_step_spikes_min",
        "keyed_context_memory_updates_sum",
        "keyed_feature_active_steps_sum",
        "keyed_max_context_memory_slots",
    ]:
        if key in summary:
            lines.append(f"- {key}: `{markdown_value(summary[key])}`")
    lines.extend(["", "## Task Comparisons", "", "| Task | Keyed all | Keyed tail | Best ablation | Ablation all | Delta all | Delta tail | Updates | Active steps | Slots |", "| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |"])
    for row in summary.get("comparisons", []):
        lines.append(
            "| "
            f"{row['task']} | {markdown_value(row.get('keyed_all_accuracy'))} | {markdown_value(row.get('keyed_tail_accuracy'))} | "
            f"`{row.get('best_ablation')}` | {markdown_value(row.get('best_ablation_all_accuracy'))} | "
            f"{markdown_value(row.get('keyed_delta_vs_best_ablation'))} | {markdown_value(row.get('keyed_tail_delta_vs_best_ablation'))} | "
            f"{markdown_value(row.get('keyed_context_memory_updates'))} | {markdown_value(row.get('keyed_feature_active_steps'))} | {markdown_value(row.get('keyed_max_slots'))} |"
        )
    lines.extend(["", "## Criteria", "", "| Criterion | Value | Rule | Pass |", "| --- | --- | --- | --- |"])
    for item in result.get("criteria", []):
        lines.append(f"| {item['name']} | `{markdown_value(item['value'])}` | `{item['rule']}` | {'yes' if item['passed'] else 'no'} |")
    if result.get("failure_reason"):
        lines.extend(["", f"Failure: {result['failure_reason']}"])
    lines.extend(["", "## Artifacts", ""])
    for name, artifact in sorted(result.get("artifacts", {}).items()):
        lines.append(f"- `{name}`: `{artifact}`")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_latest(output_dir: Path, manifest: Path, report: Path, status: str) -> None:
    payload = {
        "generated_at_utc": utc_now(),
        "tier": TIER,
        "status": status,
        "output_dir": str(output_dir),
        "manifest": str(manifest),
        "report": str(report),
        "canonical": False,
        "claim": "Latest Tier 4.21a keyed-memory bridge probe; pass is bridge evidence, not native/on-chip memory.",
    }
    bridge.write_json(CONTROLLED / "tier4_21a_latest_manifest.json", payload)


def finalize(output_dir: Path, result: dict[str, Any]) -> int:
    manifest = output_dir / "tier4_21a_results.json"
    report = output_dir / "tier4_21a_report.md"
    summary_csv = output_dir / "tier4_21a_summary.csv"
    comparisons_csv = output_dir / "tier4_21a_comparisons.csv"
    result.setdefault("artifacts", {})["manifest_json"] = str(manifest)
    result["artifacts"]["report_md"] = str(report)
    result["artifacts"]["summary_csv"] = str(summary_csv)
    result["artifacts"]["comparisons_csv"] = str(comparisons_csv)
    bridge.write_json(manifest, result)
    write_report(report, result)
    write_summary_csv(summary_csv, result.get("summary", {}).get("aggregates", []))
    write_summary_csv(comparisons_csv, result.get("summary", {}).get("comparisons", []))
    bridge.write_json(manifest, result)
    write_latest(output_dir, manifest, report, result["status"])
    print(json.dumps({"status": result["status"], "output_dir": str(output_dir), "manifest": str(manifest), "report": str(report)}, indent=2))
    return 0 if result["status"] in {"pass", "prepared"} else 1


def write_capsule(output_dir: Path, args: argparse.Namespace) -> dict[str, str]:
    capsule = output_dir / "jobmanager_capsule"
    capsule.mkdir(parents=True, exist_ok=True)
    command = (
        "cra_421a/experiments/tier4_21a_keyed_context_memory_bridge.py --mode run-hardware "
        f"--tasks {','.join(args.tasks)} --variants {','.join(args.variants)} --seeds {','.join(str(s) for s in args.seeds)} "
        f"--steps {args.steps} --population-size {args.population_size} --chunk-size-steps {args.chunk_size_steps} "
        f"--delayed-readout-lr {args.delayed_readout_lr} --context-memory-slot-count {args.context_memory_slot_count} "
        "--no-require-real-hardware --output-dir tier4_21a_job_output"
    )
    config = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "baseline": "v2.1",
        "tasks": args.tasks,
        "variants": args.variants,
        "seeds": args.seeds,
        "steps": args.steps,
        "population_size": args.population_size,
        "runtime_mode": "chunked",
        "learning_location": "host",
        "chunk_size_steps": args.chunk_size_steps,
        "context_memory_slot_count": args.context_memory_slot_count,
        "direct_jobmanager_command": command,
        "claim_boundary": "Targeted keyed context-memory bridge adapter; not native/on-chip memory.",
    }
    bridge.write_json(capsule / "capsule_config.json", config)
    bridge.write_json(capsule / "expected_outputs.json", {"required": ["tier4_21a_results.json", "tier4_21a_report.md", "tier4_21a_summary.csv", "spinnaker_hardware_<task>_<variant>_seed<seed>_timeseries.csv"], "pass_requires": ["keyed memory updates observed", "keyed memory feature active", "zero fallback/failures", "real spike readback in run-hardware"]})
    (capsule / "README_JOBMANAGER.md").write_text(
        "# Tier 4.21a Keyed Context-Memory Bridge\n\n"
        "Upload only `experiments/` and `coral_reef_spinnaker/` under a fresh `cra_421a/` folder.\n\n"
        "Run this in the EBRAINS JobManager command-line field:\n\n"
        f"```text\n{command}\n```\n\n"
        "Do not upload `controlled_test_output/`, `baselines/`, reports, or downloads.\n",
        encoding="utf-8",
    )
    return {"capsule_dir": str(capsule), "capsule_config_json": str(capsule / "capsule_config.json"), "expected_outputs_json": str(capsule / "expected_outputs.json"), "jobmanager_readme": str(capsule / "README_JOBMANAGER.md")}


def preflight_criteria(args: argparse.Namespace, mode: str) -> list[dict[str, Any]]:
    source_layout = bridge.ensure_source_layout()
    c_status, c_manifest = latest_420c_status()
    prereq_ok = c_status == "pass" or mode == "run-hardware"
    return [
        criterion("Tier 4.21a runner revision", RUNNER_REVISION, "expected current source", True),
        criterion("source package import path available", source_layout, "coral_reef_spinnaker exists", bool(source_layout.get("canonical_package_exists"))),
        criterion("Tier 4.20c bridge repeat prerequisite", {"status": c_status, "manifest": c_manifest, "mode": mode}, "status == pass locally OR fresh run-hardware", prereq_ok),
        criterion("keyed context-memory included", args.variants, "contains keyed_context_memory", "keyed_context_memory" in args.variants),
        criterion("memory ablation included", args.variants, "contains at least one ablation", any(ALLOWED_VARIANTS[v] == "memory_ablation" for v in args.variants)),
        criterion("runtime mode is chunked", "chunked", "fixed", True),
        criterion("learning location is host", "host", "fixed", True),
        criterion("context memory slot count supports keyed binding", args.context_memory_slot_count, ">= 2", int(args.context_memory_slot_count) >= 2),
    ]


def run_matrix(args: argparse.Namespace, output_dir: Path, *, hardware: bool) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, str]]:
    all_rows: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    artifacts: dict[str, str] = {}
    for task in args.tasks:
        for seed in args.seeds:
            for variant in args.variants:
                rows, summary = run_bridge_task_seed_variant(task_name=task, seed=seed, variant=variant, args=args, hardware=hardware)
                csv_path = output_dir / f"spinnaker_hardware_{task}_{variant}_seed{seed}_timeseries.csv"
                write_csv(csv_path, rows)
                artifacts[f"{task}_{variant}_seed{seed}_timeseries_csv"] = str(csv_path)
                if rows:
                    png_path = output_dir / f"spinnaker_hardware_{task}_{variant}_seed{seed}_timeseries.png"
                    plot_case(rows, png_path, f"Tier 4.21a {task} {variant} seed {seed}")
                    if png_path.exists():
                        artifacts[f"{task}_{variant}_seed{seed}_timeseries_png"] = str(png_path)
                all_rows.extend(rows)
                summaries.append(summary)
    return all_rows, summaries, artifacts


def run_prepare(args: argparse.Namespace, output_dir: Path) -> int:
    criteria = preflight_criteria(args, "prepare")
    status, failure = pass_fail(criteria)
    status = "prepared" if status == "pass" else "fail"
    artifacts = write_capsule(output_dir, args)
    result = {
        "tier": TIER,
        "generated_at_utc": utc_now(),
        "mode": "prepare",
        "status": status,
        "failure_reason": failure,
        "output_dir": str(output_dir),
        "summary": {
            "baseline": "v2.1",
            "runner_revision": RUNNER_REVISION,
            "tasks": args.tasks,
            "variants": args.variants,
            "seeds": args.seeds,
            "steps": args.steps,
            "population_size": args.population_size,
            "chunk_size_steps": args.chunk_size_steps,
            "context_memory_slot_count": args.context_memory_slot_count,
            "hardware_run_attempted": False,
        },
        "criteria": criteria,
        "artifacts": artifacts,
    }
    return finalize(output_dir, result)


def run_bridge(args: argparse.Namespace, output_dir: Path, *, hardware: bool) -> int:
    mode = "run-hardware" if hardware else "local-bridge"
    started = time.perf_counter()
    criteria = preflight_criteria(args, mode)
    artifacts: dict[str, str] = {}
    try:
        _, summaries, run_artifacts = run_matrix(args, output_dir, hardware=hardware)
        artifacts.update(run_artifacts)
        aggregates = aggregate_summaries(summaries)
        comparisons = build_comparisons(aggregates)
        eval_criteria, summary = evaluate(args=args, mode=mode, summaries=summaries, aggregates=aggregates, comparisons=comparisons)
        criteria.extend(eval_criteria)
        status, failure = pass_fail(criteria)
    except Exception as exc:
        trace = output_dir / "tier4_21a_failure_traceback.txt"
        import traceback

        trace.write_text(traceback.format_exc(), encoding="utf-8")
        artifacts["failure_traceback"] = str(trace)
        summaries = []
        aggregates = []
        comparisons = []
        summary = {
            "baseline": "v2.1",
            "runner_revision": RUNNER_REVISION,
            "tasks": args.tasks,
            "variants": args.variants,
            "seeds": args.seeds,
            "hardware_run_attempted": hardware,
            "exception": f"{type(exc).__name__}: {exc}",
        }
        status = "fail"
        failure = f"raised {type(exc).__name__}: {exc}"
    summary["runtime_seconds"] = time.perf_counter() - started
    result = {"tier": TIER, "generated_at_utc": utc_now(), "mode": mode, "status": status, "failure_reason": failure, "output_dir": str(output_dir), "summary": summary, "criteria": criteria, "artifacts": artifacts}
    return finalize(output_dir, result)


def ingest(args: argparse.Namespace, output_dir: Path) -> int:
    if args.ingest_dir is None:
        raise SystemExit("--ingest-dir is required for ingest mode")
    source = args.ingest_dir.resolve()
    manifest = source / "tier4_21a_results.json"
    if not manifest.exists():
        raise SystemExit(f"No tier4_21a_results.json found in {source}")
    status = str(read_json(manifest).get("status", "unknown")).lower()
    if output_dir.exists() and output_dir != source:
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for pattern in ["tier4_21a_*", "spinnaker_hardware_*", "reports.zip", "global_provenance*.sqlite3", "finished*"]:
        for path in source.glob(pattern):
            if path.is_file():
                shutil.copy2(path, output_dir / path.name)
    result = read_json(manifest)
    result["mode"] = "ingest"
    result.setdefault("summary", {})["ingested_from"] = str(source)
    result["output_dir"] = str(output_dir)
    return finalize(output_dir, result)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Tier 4.21a keyed context-memory hardware bridge probe.")
    parser.add_argument("--mode", choices=["prepare", "local-bridge", "run-hardware", "ingest"], default="prepare")
    parser.add_argument("--tasks", type=parse_tasks, default=parse_tasks(DEFAULT_TASKS))
    parser.add_argument("--variants", type=parse_variants, default=parse_variants(DEFAULT_VARIANTS))
    parser.add_argument("--seeds", type=parse_seeds, default=parse_seeds(DEFAULT_SEEDS))
    parser.add_argument("--steps", type=int, default=DEFAULT_STEPS)
    parser.add_argument("--task-seed", type=int, default=5100)
    parser.add_argument("--population-size", type=int, default=DEFAULT_POPULATION_SIZE)
    parser.add_argument("--chunk-size-steps", type=int, default=DEFAULT_CHUNK_SIZE)
    parser.add_argument("--context-memory-slot-count", type=int, default=4)
    parser.add_argument("--delayed-readout-lr", type=float, default=DEFAULT_DELAYED_LR)
    parser.add_argument("--amplitude", type=float, default=0.01)
    parser.add_argument("--dt-seconds", type=float, default=1.0)
    parser.add_argument("--timestep-ms", type=float, default=1.0)
    parser.add_argument("--base-current-na", type=float, default=0.72)
    parser.add_argument("--cue-current-gain-na", type=float, default=0.55)
    parser.add_argument("--min-current-na", type=float, default=0.02)
    parser.add_argument("--spinnaker-hostname", default=None)
    parser.add_argument("--require-real-hardware", dest="require_real_hardware", action="store_true", default=True)
    parser.add_argument("--no-require-real-hardware", dest="require_real_hardware", action="store_false")
    parser.add_argument("--min-keyed-edge-vs-ablation", type=float, default=0.0)
    parser.add_argument("--capacity-period", type=int, default=120)
    parser.add_argument("--capacity-decision-gap", type=int, default=72)
    parser.add_argument("--interfering-contexts", type=int, default=2)
    parser.add_argument("--interference-spacing", type=int, default=24)
    parser.add_argument("--interfering-context-scale", type=float, default=0.50)
    parser.add_argument("--overlap-period", type=int, default=120)
    parser.add_argument("--overlap-context-gap", type=int, default=36)
    parser.add_argument("--overlap-first-decision-gap", type=int, default=72)
    parser.add_argument("--overlap-second-decision-gap", type=int, default=96)
    parser.add_argument("--reentry-phase-len", type=int, default=180)
    parser.add_argument("--reentry-decision-stride", type=int, default=24)
    parser.add_argument("--reentry-interference-probability", type=float, default=0.70)
    parser.add_argument("--distractor-density", type=float, default=0.55)
    parser.add_argument("--distractor-scale", type=float, default=0.35)
    parser.add_argument("--ingest-dir", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = {"prepare": "prepared", "local-bridge": "local_bridge", "run-hardware": "run_hardware", "ingest": "ingested"}[args.mode]
    output_dir = (args.output_dir or (CONTROLLED / f"tier4_21a_{stamp}_{suffix}")).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if args.mode == "prepare":
        return run_prepare(args, output_dir)
    if args.mode == "local-bridge":
        return run_bridge(args, output_dir, hardware=False)
    if args.mode == "run-hardware":
        return run_bridge(args, output_dir, hardware=True)
    return ingest(args, output_dir)


if __name__ == "__main__":
    raise SystemExit(main())
