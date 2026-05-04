#!/usr/bin/env python3
"""Tier 4.17b step-vs-chunked parity.

This tier is a local runtime parity diagnostic, not a hardware learning claim.
It tests the mechanics required before a repaired long SpiNNaker run:

1. scheduled input inside each chunk via PyNN ``StepCurrentSource``
2. spike readback binned back to the original CRA step grid
3. host-side delayed-credit replay from those bins
4. comparison against a step-mode reference that uses one ``sim.run`` per CRA bin

The first task is intentionally narrow: delayed_cue, 120 steps, seed 42.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except Exception as exc:  # pragma: no cover - optional plotting dependency
    plt = None
    MATPLOTLIB_ERROR = str(exc)
else:
    MATPLOTLIB_ERROR = None

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from coral_reef_spinnaker.runtime_modes import chunk_ranges, make_runtime_plan  # noqa: E402
from tier2_learning import (  # noqa: E402
    DEFAULT_AMPLITUDE,
    DEFAULT_DT_SECONDS,
    criterion,
    end_backend,
    load_backend,
    markdown_value,
    pass_fail,
    safe_corr,
    setup_backend,
    strict_sign,
)
from tier5_external_baselines import TaskStream, delayed_cue_task, summarize_rows  # noqa: E402


TIER = "Tier 4.17b - Step vs Chunked Parity"
OUTPUT_ROOT = ROOT / "controlled_test_output"
DEFAULT_BACKENDS = "nest,brian2"
DEFAULT_CHUNK_SIZES = "5,10,25,50"


@dataclass
class BackendRun:
    backend_key: str
    backend: str
    seed: int
    chunk_size_steps: int
    sim_run_calls: int
    spike_bins: np.ndarray
    rows: list[dict[str, Any]]
    summary: dict[str, Any]
    runtime_seconds: float
    diagnostics: dict[str, Any]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def parse_csv_list(value: str) -> list[str]:
    items = [item.strip() for item in value.split(",") if item.strip()]
    if not items:
        raise argparse.ArgumentTypeError("at least one item is required")
    return items


def parse_int_list(value: str) -> list[int]:
    try:
        items = [int(item) for item in parse_csv_list(value)]
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc
    if any(item < 1 for item in items):
        raise argparse.ArgumentTypeError("chunk sizes must be >= 1")
    return items


def json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, np.ndarray):
        return [json_safe(v) for v in value.tolist()]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        f = float(value)
        return None if not math.isfinite(f) else f
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json_safe(value) for key, value in row.items()})


def build_task(seed: int, args: argparse.Namespace) -> TaskStream:
    return delayed_cue_task(steps=args.steps, amplitude=args.amplitude, seed=seed, args=args)


def scheduled_currents(task: TaskStream, args: argparse.Namespace) -> np.ndarray:
    sensory_unit = np.zeros(task.steps, dtype=float)
    if abs(float(args.amplitude)) > 0.0:
        sensory_unit = np.asarray(task.sensory, dtype=float) / float(args.amplitude)
    currents = float(args.base_current_na) + float(args.cue_current_gain_na) * sensory_unit
    return np.clip(currents, float(args.min_current_na), None)


def compressed_current_schedule(currents: np.ndarray, dt_ms: float) -> tuple[list[float], list[float]]:
    times: list[float] = []
    amplitudes: list[float] = []
    last: float | None = None
    for step, current in enumerate(currents):
        value = float(current)
        if step == 0 or last is None or abs(value - last) > 1e-12:
            times.append(float(step) * dt_ms)
            amplitudes.append(value)
            last = value
    return times, amplitudes


def bin_spiketrains(spiketrains: list[Any], *, steps: int, dt_ms: float) -> np.ndarray:
    bins = np.zeros(steps, dtype=int)
    for train in spiketrains:
        times = np.asarray(train, dtype=float)
        for step in range(steps):
            start = float(step) * dt_ms
            stop = float(step + 1) * dt_ms
            if step == steps - 1:
                mask = (times >= start) & (times <= stop)
            else:
                mask = (times >= start) & (times < stop)
            bins[step] += int(np.sum(mask))
    return bins


class DelayedCreditReplay:
    """Tiny host-side delayed-credit replay used only for runtime parity."""

    def __init__(self, *, lr: float, amplitude: float) -> None:
        self.lr = float(lr)
        self.amplitude = float(amplitude)
        self.weight = 0.0
        self.bias = 0.0
        self.pending: list[dict[str, Any]] = []
        self.matured_count = 0

    def step(
        self,
        *,
        task: TaskStream,
        step: int,
        spike_count: int,
        mean_spike_count: float,
    ) -> dict[str, Any]:
        sensory = float(task.sensory[step])
        feature = sensory / self.amplitude if abs(self.amplitude) > 0.0 else 0.0
        spike_scale = 0.0 if mean_spike_count <= 0.0 else float(spike_count) / mean_spike_count
        score = self.weight * feature + self.bias
        prediction = float(math.tanh(score))
        eval_sign = strict_sign(float(task.evaluation_target[step]))
        pred_sign = strict_sign(prediction)
        target_nonzero = bool(task.evaluation_mask[step] and eval_sign != 0)
        correct = bool(target_nonzero and pred_sign != 0 and pred_sign == eval_sign)

        if target_nonzero:
            self.pending.append(
                {
                    "created_step": int(step),
                    "due_step": int(task.feedback_due_step[step]),
                    "feature": float(feature),
                    "label": int(eval_sign),
                    "prediction_at_cue": prediction,
                    "spike_scale": float(spike_scale),
                }
            )

        matured_now = 0
        for record in list(self.pending):
            if int(record["due_step"]) != int(step):
                continue
            effective_lr = self.lr * (0.5 + 0.5 * float(record["spike_scale"]))
            # Label is delayed; feature is the original cue-time signed input.
            self.weight += effective_lr * int(record["label"]) * float(record["feature"])
            self.pending.remove(record)
            self.matured_count += 1
            matured_now += 1

        return {
            "step": int(step),
            "sensory_return_1m": sensory,
            "target_return_1m": float(task.current_target[step]),
            "target_signal_horizon": float(task.evaluation_target[step]),
            "target_signal_sign": eval_sign,
            "target_signal_nonzero": target_nonzero,
            "feedback_due_step": int(task.feedback_due_step[step]),
            "colony_prediction": prediction,
            "prediction_sign": pred_sign,
            "strict_direction_correct": correct,
            "step_spike_count": int(spike_count),
            "spike_scale": float(spike_scale),
            "host_replay_weight": float(self.weight),
            "host_replay_bias": float(self.bias),
            "matured_horizons": int(self.matured_count),
            "matured_horizons_this_step": int(matured_now),
            "pending_horizons": int(len(self.pending)),
        }


def replay_host_learning(
    *,
    task: TaskStream,
    spike_bins: np.ndarray,
    args: argparse.Namespace,
    backend_key: str,
    backend: str,
    seed: int,
    chunk_size_steps: int,
    sim_run_calls: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    mean_spikes = float(np.mean(spike_bins)) if spike_bins.size else 0.0
    replay = DelayedCreditReplay(lr=args.host_replay_lr, amplitude=args.amplitude)
    rows: list[dict[str, Any]] = []
    for step in range(task.steps):
        row = replay.step(
            task=task,
            step=step,
            spike_count=int(spike_bins[step]),
            mean_spike_count=mean_spikes,
        )
        row.update(
            {
                "tier": TIER,
                "task": task.name,
                "backend_key": backend_key,
                "backend": backend,
                "seed": int(seed),
                "runtime_mode": "step" if chunk_size_steps == 1 else "chunked",
                "learning_location": "host",
                "chunk_size_steps": int(chunk_size_steps),
                "sim_run_calls": int(sim_run_calls),
            }
        )
        rows.append(row)
    summary = summarize_rows(rows)
    summary.update(
        {
            "tier": TIER,
            "task": task.name,
            "backend_key": backend_key,
            "backend": backend,
            "seed": int(seed),
            "runtime_mode": "step" if chunk_size_steps == 1 else "chunked",
            "learning_location": "host",
            "chunk_size_steps": int(chunk_size_steps),
            "sim_run_calls": int(sim_run_calls),
            "total_step_spikes": int(np.sum(spike_bins)),
            "mean_step_spikes": float(np.mean(spike_bins)) if spike_bins.size else 0.0,
            "max_step_spikes": int(np.max(spike_bins)) if spike_bins.size else 0,
            "min_step_spikes": int(np.min(spike_bins)) if spike_bins.size else 0,
            "final_host_replay_weight": float(rows[-1]["host_replay_weight"]) if rows else 0.0,
            "scheduled_input_mode": "StepCurrentSource",
            "binned_readback": True,
            "synthetic_fallbacks": 0,
            "sim_run_failures": 0,
            "summary_read_failures": 0,
        }
    )
    return rows, summary


def run_backend_mode(
    *,
    backend_key: str,
    seed: int,
    chunk_size_steps: int,
    args: argparse.Namespace,
) -> BackendRun:
    task = build_task(seed, args)
    currents = scheduled_currents(task, args)
    dt_ms = float(args.dt_seconds) * 1000.0
    sim, backend_name = load_backend(backend_key)
    setup_backend(sim, backend_name)
    started = time.perf_counter()
    diagnostics = {
        "synthetic_fallbacks": 0,
        "sim_run_failures": 0,
        "summary_read_failures": 0,
        "scheduled_input_failures": 0,
        "spike_readback_failures": 0,
    }
    try:
        if not hasattr(sim, "StepCurrentSource"):
            raise RuntimeError(f"{backend_name} does not expose StepCurrentSource")
        cell = sim.IF_curr_exp(
            i_offset=0.0,
            tau_m=20.0,
            v_rest=-65.0,
            v_reset=-70.0,
            v_thresh=-55.0,
            tau_refrac=2.0,
            cm=0.25,
        )
        pop = sim.Population(int(args.probe_neurons), cell, label=f"tier4_17b_{backend_key}_{chunk_size_steps}")
        pop.record("spikes")
        times, amplitudes = compressed_current_schedule(currents, dt_ms)
        source = sim.StepCurrentSource(times=times, amplitudes=amplitudes)
        pop.inject(source)
        calls = 0
        for start, stop in chunk_ranges(task.steps, int(chunk_size_steps)):
            sim.run(float(stop - start) * dt_ms)
            calls += 1
        try:
            data = pop.get_data("spikes", clear=False)
            spiketrains = data.segments[0].spiketrains
            spike_bins = bin_spiketrains(spiketrains, steps=task.steps, dt_ms=dt_ms)
        except Exception:
            diagnostics["summary_read_failures"] = 1
            diagnostics["spike_readback_failures"] = 1
            raise
    except Exception:
        diagnostics["sim_run_failures"] = 1
        raise
    finally:
        try:
            end_backend(sim)
        except Exception:
            pass

    rows, summary = replay_host_learning(
        task=task,
        spike_bins=spike_bins,
        args=args,
        backend_key=backend_key,
        backend=backend_name,
        seed=seed,
        chunk_size_steps=chunk_size_steps,
        sim_run_calls=calls,
    )
    runtime_seconds = time.perf_counter() - started
    summary.update(
        {
            "runtime_seconds": runtime_seconds,
            "scheduled_current_changes": len(compressed_current_schedule(currents, dt_ms)[0]),
            "scheduled_current_min": float(np.min(currents)),
            "scheduled_current_max": float(np.max(currents)),
        }
    )
    summary.update(diagnostics)
    return BackendRun(
        backend_key=backend_key,
        backend=backend_name,
        seed=seed,
        chunk_size_steps=chunk_size_steps,
        sim_run_calls=calls,
        spike_bins=spike_bins,
        rows=rows,
        summary=summary,
        runtime_seconds=runtime_seconds,
        diagnostics=diagnostics,
    )


def finite_float(value: Any) -> float | None:
    try:
        f = float(value)
    except Exception:
        return None
    return f if math.isfinite(f) else None


def metric_or_default(value: Any, default: float) -> float:
    f = finite_float(value)
    return default if f is None else f


def compare_to_reference(reference: BackendRun, candidate: BackendRun) -> dict[str, Any]:
    ref_rows = reference.rows
    cand_rows = candidate.rows
    ref_pred = np.asarray([float(r.get("colony_prediction", 0.0) or 0.0) for r in ref_rows], dtype=float)
    cand_pred = np.asarray([float(r.get("colony_prediction", 0.0) or 0.0) for r in cand_rows], dtype=float)
    ref_target = [float(r.get("target_signal_horizon", 0.0) or 0.0) for r in ref_rows]
    cand_target = [float(r.get("target_signal_horizon", 0.0) or 0.0) for r in cand_rows]
    spike_delta = np.asarray(candidate.spike_bins, dtype=float) - np.asarray(reference.spike_bins, dtype=float)
    pred_delta = cand_pred - ref_pred
    ref_summary = reference.summary
    cand_summary = candidate.summary
    return {
        "backend_key": candidate.backend_key,
        "backend": candidate.backend,
        "seed": candidate.seed,
        "task": "delayed_cue",
        "reference_runtime_mode": reference.summary.get("runtime_mode"),
        "runtime_mode": candidate.summary.get("runtime_mode"),
        "learning_location": candidate.summary.get("learning_location"),
        "chunk_size_steps": candidate.chunk_size_steps,
        "reference_sim_run_calls": reference.sim_run_calls,
        "sim_run_calls": candidate.sim_run_calls,
        "call_reduction_factor": (
            float(reference.sim_run_calls) / float(candidate.sim_run_calls)
            if candidate.sim_run_calls
            else None
        ),
        "same_evaluation_targets": ref_target == cand_target,
        "all_accuracy_reference": ref_summary.get("all_accuracy"),
        "all_accuracy_candidate": cand_summary.get("all_accuracy"),
        "all_accuracy_abs_delta": abs(float(cand_summary.get("all_accuracy") or 0.0) - float(ref_summary.get("all_accuracy") or 0.0)),
        "tail_accuracy_reference": ref_summary.get("tail_accuracy"),
        "tail_accuracy_candidate": cand_summary.get("tail_accuracy"),
        "tail_accuracy_abs_delta": abs(float(cand_summary.get("tail_accuracy") or 0.0) - float(ref_summary.get("tail_accuracy") or 0.0)),
        "prediction_corr_with_reference": safe_corr(ref_pred.tolist(), cand_pred.tolist()),
        "max_abs_prediction_delta": float(np.max(np.abs(pred_delta))) if pred_delta.size else 0.0,
        "total_spikes_reference": int(np.sum(reference.spike_bins)),
        "total_spikes_candidate": int(np.sum(candidate.spike_bins)),
        "total_spike_abs_delta": int(abs(int(np.sum(candidate.spike_bins)) - int(np.sum(reference.spike_bins)))),
        "max_step_spike_abs_delta": int(np.max(np.abs(spike_delta))) if spike_delta.size else 0,
        "spike_bin_corr_with_reference": safe_corr(reference.spike_bins.astype(float).tolist(), candidate.spike_bins.astype(float).tolist()),
        "zero_fallback": int(candidate.summary.get("synthetic_fallbacks", 0)) == 0,
        "zero_failures": (
            int(candidate.summary.get("sim_run_failures", 0)) == 0
            and int(candidate.summary.get("summary_read_failures", 0)) == 0
        ),
    }


def aggregate_comparisons(comparisons: list[dict[str, Any]], expected: int) -> dict[str, Any]:
    def vals(key: str) -> list[float]:
        out: list[float] = []
        for row in comparisons:
            value = finite_float(row.get(key))
            if value is not None:
                out.append(value)
        return out

    return {
        "tier": TIER,
        "status_boundary": "local runtime parity diagnostic; not hardware evidence",
        "expected_comparisons": expected,
        "observed_comparisons": len(comparisons),
        "same_evaluation_targets_all": all(bool(row.get("same_evaluation_targets")) for row in comparisons),
        "zero_fallback_all": all(bool(row.get("zero_fallback")) for row in comparisons),
        "zero_failures_all": all(bool(row.get("zero_failures")) for row in comparisons),
        "max_tail_accuracy_abs_delta": max(vals("tail_accuracy_abs_delta")) if comparisons else None,
        "max_all_accuracy_abs_delta": max(vals("all_accuracy_abs_delta")) if comparisons else None,
        "max_abs_prediction_delta": max(vals("max_abs_prediction_delta")) if comparisons else None,
        "max_step_spike_abs_delta": max(vals("max_step_spike_abs_delta")) if comparisons else None,
        "min_spike_bin_corr": min(vals("spike_bin_corr_with_reference")) if comparisons else None,
        "min_prediction_corr": min(vals("prediction_corr_with_reference")) if comparisons else None,
        "min_call_reduction_factor": min(vals("call_reduction_factor")) if comparisons else None,
        "max_call_reduction_factor": max(vals("call_reduction_factor")) if comparisons else None,
    }


def build_criteria(aggregate: dict[str, Any], args: argparse.Namespace) -> list[dict[str, Any]]:
    return [
        criterion("all backend/chunk comparisons completed", aggregate.get("observed_comparisons"), "==", aggregate.get("expected_comparisons"), aggregate.get("observed_comparisons") == aggregate.get("expected_comparisons")),
        criterion("zero synthetic fallback", aggregate.get("zero_fallback_all"), "==", True, bool(aggregate.get("zero_fallback_all"))),
        criterion("zero backend/readback failures", aggregate.get("zero_failures_all"), "==", True, bool(aggregate.get("zero_failures_all"))),
        criterion("same evaluation targets", aggregate.get("same_evaluation_targets_all"), "==", True, bool(aggregate.get("same_evaluation_targets_all"))),
        criterion("tail accuracy parity", aggregate.get("max_tail_accuracy_abs_delta"), "<=", args.max_accuracy_delta, metric_or_default(aggregate.get("max_tail_accuracy_abs_delta"), 999.0) <= args.max_accuracy_delta),
        criterion("all accuracy parity", aggregate.get("max_all_accuracy_abs_delta"), "<=", args.max_accuracy_delta, metric_or_default(aggregate.get("max_all_accuracy_abs_delta"), 999.0) <= args.max_accuracy_delta),
        criterion("prediction replay parity", aggregate.get("max_abs_prediction_delta"), "<=", args.max_prediction_delta, metric_or_default(aggregate.get("max_abs_prediction_delta"), 999.0) <= args.max_prediction_delta),
        criterion("per-bin spike readback parity", aggregate.get("max_step_spike_abs_delta"), "<=", args.max_step_spike_delta, metric_or_default(aggregate.get("max_step_spike_abs_delta"), 999.0) <= args.max_step_spike_delta),
        criterion("spike-bin correlation parity", aggregate.get("min_spike_bin_corr"), ">=", args.min_spike_corr, metric_or_default(aggregate.get("min_spike_bin_corr"), -999.0) >= args.min_spike_corr),
        criterion("chunking reduces sim.run calls", aggregate.get("min_call_reduction_factor"), ">", 1.0, metric_or_default(aggregate.get("min_call_reduction_factor"), 0.0) > 1.0),
        criterion("no continuous/on-chip claim", aggregate.get("status_boundary"), "contains", "not hardware evidence", "not hardware evidence" in str(aggregate.get("status_boundary", ""))),
    ]


def plot_parity(comparisons: list[dict[str, Any]], output_path: Path) -> None:
    if plt is None or not comparisons:
        return
    labels = [f"{row['backend_key']}\\n{row['chunk_size_steps']}" for row in comparisons]
    spike_delta = [float(row.get("max_step_spike_abs_delta") or 0.0) for row in comparisons]
    pred_delta = [float(row.get("max_abs_prediction_delta") or 0.0) for row in comparisons]
    reduction = [float(row.get("call_reduction_factor") or 0.0) for row in comparisons]
    fig, axes = plt.subplots(1, 3, figsize=(13, 4))
    axes[0].bar(labels, spike_delta, color="#1f6feb")
    axes[0].set_title("Max per-bin spike delta")
    axes[1].bar(labels, pred_delta, color="#2f855a")
    axes[1].set_title("Max prediction delta")
    axes[2].bar(labels, reduction, color="#8250df")
    axes[2].set_title("sim.run reduction")
    for ax in axes:
        ax.grid(axis="y", alpha=0.25)
        ax.tick_params(axis="x", labelrotation=45)
    fig.suptitle(TIER)
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def write_report(
    *,
    path: Path,
    output_dir: Path,
    status: str,
    failure_reason: str,
    aggregate: dict[str, Any],
    comparisons: list[dict[str, Any]],
    criteria: list[dict[str, Any]],
    artifacts: dict[str, str],
) -> None:
    lines = [
        "# Tier 4.17b Step vs Chunked Parity",
        "",
        f"- Generated: `{utc_now()}`",
        f"- Status: **{status.upper()}**",
        f"- Output directory: `{output_dir}`",
        "",
        "Tier 4.17b is a local runtime parity diagnostic. It is not SpiNNaker",
        "hardware evidence and not a continuous/on-chip learning claim.",
        "",
        "## Claim Boundary",
        "",
        "- The step reference uses scheduled PyNN input but still runs one `sim.run` per original CRA step.",
        "- Chunked runs use the same scheduled input source, fewer `sim.run` calls, binned spike readback, and host-side delayed-credit replay.",
        "- Passing this tier authorizes implementing the same mechanics in the hardware capsule path; it does not by itself promote Tier 4.16.",
        "",
    ]
    if failure_reason:
        lines.extend(["## Failure", "", failure_reason, ""])
    lines.extend(
        [
            "## Aggregate",
            "",
            f"- expected comparisons: `{aggregate.get('expected_comparisons')}`",
            f"- observed comparisons: `{aggregate.get('observed_comparisons')}`",
            f"- max tail accuracy delta: `{markdown_value(aggregate.get('max_tail_accuracy_abs_delta'))}`",
            f"- max prediction delta: `{markdown_value(aggregate.get('max_abs_prediction_delta'))}`",
            f"- max step spike delta: `{markdown_value(aggregate.get('max_step_spike_abs_delta'))}`",
            f"- min spike-bin correlation: `{markdown_value(aggregate.get('min_spike_bin_corr'))}`",
            f"- sim.run reduction range: `{markdown_value(aggregate.get('min_call_reduction_factor'))}` to `{markdown_value(aggregate.get('max_call_reduction_factor'))}`",
            "",
            "## Comparisons",
            "",
            "| Backend | Chunk | Calls | Reduction | Tail Delta | Prediction Delta | Spike Delta | Spike Corr |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in comparisons:
        lines.append(
            "| "
            f"`{row['backend_key']}` | {row['chunk_size_steps']} | {row['sim_run_calls']} | "
            f"{markdown_value(row.get('call_reduction_factor'))} | "
            f"{markdown_value(row.get('tail_accuracy_abs_delta'))} | "
            f"{markdown_value(row.get('max_abs_prediction_delta'))} | "
            f"{markdown_value(row.get('max_step_spike_abs_delta'))} | "
            f"{markdown_value(row.get('spike_bin_corr_with_reference'))} |"
        )
    lines.extend(["", "## Criteria", "", "| Criterion | Value | Rule | Pass |", "| --- | --- | --- | --- |"])
    for item in criteria:
        lines.append(
            f"| {item['name']} | {markdown_value(item['value'])} | {item['operator']} {markdown_value(item['threshold'])} | {'yes' if item['passed'] else 'no'} |"
        )
    lines.extend(
        [
            "",
            "## Next Order",
            "",
            "1. Keep this local parity bundle as the gate for the Tier 4.16 chunked runner.",
            "2. Repaired Tier 4.16a delayed_cue, 1200-step chunked hardware has passed across seeds `42,43,44`.",
            "3. Run Tier 4.16b hard_noisy_switching with the same chunked bridge.",
            "",
            "## Artifacts",
            "",
        ]
    )
    for key, value in artifacts.items():
        lines.append(f"- `{key}`: `{value}`")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Tier 4.17b step-vs-chunked local parity.")
    parser.add_argument("--backends", default=DEFAULT_BACKENDS)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--steps", type=int, default=120)
    parser.add_argument("--chunk-sizes", type=parse_int_list, default=parse_int_list(DEFAULT_CHUNK_SIZES))
    parser.add_argument("--amplitude", type=float, default=DEFAULT_AMPLITUDE)
    parser.add_argument("--dt-seconds", type=float, default=DEFAULT_DT_SECONDS)
    parser.add_argument("--delay", type=int, default=5)
    parser.add_argument("--period", type=int, default=8)
    parser.add_argument("--probe-neurons", type=int, default=4)
    parser.add_argument("--base-current-na", type=float, default=1.4)
    parser.add_argument("--cue-current-gain-na", type=float, default=0.2)
    parser.add_argument("--min-current-na", type=float, default=0.0)
    parser.add_argument("--host-replay-lr", type=float, default=0.20)
    parser.add_argument("--max-accuracy-delta", type=float, default=1e-12)
    parser.add_argument("--max-prediction-delta", type=float, default=1e-12)
    parser.add_argument("--max-step-spike-delta", type=int, default=0)
    parser.add_argument("--min-spike-corr", type=float, default=0.999999)
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    output_dir = args.output_dir or OUTPUT_ROOT / f"tier4_17b_{timestamp}_step_chunk_parity"
    output_dir.mkdir(parents=True, exist_ok=True)
    backends = parse_csv_list(args.backends)
    chunk_sizes = [int(size) for size in args.chunk_sizes if int(size) > 1]

    all_rows: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    comparisons: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for backend_key in backends:
        try:
            reference = run_backend_mode(
                backend_key=backend_key,
                seed=args.seed,
                chunk_size_steps=1,
                args=args,
            )
            all_rows.extend(reference.rows)
            summaries.append(reference.summary)
        except Exception as exc:
            failures.append({"backend_key": backend_key, "chunk_size_steps": 1, "error_type": type(exc).__name__, "error": str(exc)})
            continue

        for chunk_size in chunk_sizes:
            plan = make_runtime_plan(
                runtime_mode="chunked",
                learning_location="host",
                chunk_size_steps=chunk_size,
                total_steps=args.steps,
                dt_seconds=args.dt_seconds,
            )
            if not plan.implemented or plan.runtime_mode != "chunked" or plan.learning_location != "host":
                failures.append(
                    {
                        "backend_key": backend_key,
                        "chunk_size_steps": chunk_size,
                        "error_type": "RuntimePlanError",
                        "error": f"unexpected chunked-host plan {plan.__dict__}",
                    }
                )
                continue
            try:
                candidate = run_backend_mode(
                    backend_key=backend_key,
                    seed=args.seed,
                    chunk_size_steps=chunk_size,
                    args=args,
                )
                all_rows.extend(candidate.rows)
                summaries.append(candidate.summary)
                comparisons.append(compare_to_reference(reference, candidate))
            except Exception as exc:
                failures.append({"backend_key": backend_key, "chunk_size_steps": chunk_size, "error_type": type(exc).__name__, "error": str(exc)})

    aggregate = aggregate_comparisons(comparisons, expected=len(backends) * len(chunk_sizes))
    aggregate["failures"] = failures
    aggregate["backend_keys"] = backends
    aggregate["seed"] = int(args.seed)
    aggregate["chunk_sizes"] = chunk_sizes
    criteria = build_criteria(aggregate, args)
    criteria.insert(1, criterion("no execution exceptions", len(failures), "==", 0, len(failures) == 0))
    status, failure_reason = pass_fail(criteria)

    summary_csv = output_dir / "tier4_17b_summary.csv"
    comparison_csv = output_dir / "tier4_17b_comparisons.csv"
    timeseries_csv = output_dir / "tier4_17b_timeseries.csv"
    failures_csv = output_dir / "tier4_17b_failures.csv"
    report_md = output_dir / "tier4_17b_report.md"
    manifest_json = output_dir / "tier4_17b_results.json"
    plot_png = output_dir / "tier4_17b_parity.png"
    write_csv(summary_csv, summaries)
    write_csv(comparison_csv, comparisons)
    write_csv(timeseries_csv, all_rows)
    if failures:
        write_csv(failures_csv, failures)
    plot_parity(comparisons, plot_png)
    artifacts = {
        "summary_csv": str(summary_csv),
        "comparison_csv": str(comparison_csv),
        "timeseries_csv": str(timeseries_csv),
        "manifest_json": str(manifest_json),
        "report_md": str(report_md),
    }
    if failures:
        artifacts["failures_csv"] = str(failures_csv)
    if plot_png.exists():
        artifacts["parity_png"] = str(plot_png)
    write_json(
        manifest_json,
        {
            "generated_at_utc": utc_now(),
            "tier": TIER,
            "status": status,
            "failure_reason": failure_reason,
            "summary": aggregate,
            "criteria": criteria,
            "comparisons": comparisons,
            "run_summaries": summaries,
            "artifacts": artifacts,
            "config": {
                "backends": backends,
                "seed": args.seed,
                "steps": args.steps,
                "task": "delayed_cue",
                "chunk_sizes": chunk_sizes,
                "dt_seconds": args.dt_seconds,
                "learning_location": "host",
                "scheduled_input": "PyNN StepCurrentSource",
                "binned_readback": True,
                "host_replay_lr": args.host_replay_lr,
            },
            "matplotlib_error": MATPLOTLIB_ERROR,
        },
    )
    write_report(
        path=report_md,
        output_dir=output_dir,
        status=status,
        failure_reason=failure_reason,
        aggregate=aggregate,
        comparisons=comparisons,
        criteria=criteria,
        artifacts=artifacts,
    )
    write_json(
        OUTPUT_ROOT / "tier4_17b_latest_manifest.json",
        {
            "generated_at_utc": utc_now(),
            "manifest": str(manifest_json),
            "report": str(report_md),
            "summary_csv": str(summary_csv),
            "comparison_csv": str(comparison_csv),
            "output_dir": str(output_dir),
            "status": status,
            "canonical": False,
            "claim": "Tier 4.17b local step-vs-chunked parity diagnostic; not hardware evidence.",
        },
    )
    print(json.dumps({"status": status, "output_dir": str(output_dir)}, indent=2))
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
