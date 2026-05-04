#!/usr/bin/env python3
"""Tier 4.16 harder SpiNNaker hardware capsule.

Tier 4.16 is intentionally separate from Tier 4.13 and Tier 4.15:

- Tier 4.13: one minimal fixed-pattern hardware pass.
- Tier 4.15: repeat the same minimal fixed-pattern capsule across seeds.
- Tier 4.16: test whether the confirmed Tier 5.4 delayed-credit setting
  (`delayed_lr_0_20`) survives harder task structure on real SpiNNaker.

The tier is split into two parts:

``4.16a``
    `delayed_cue` hardware capsule.

``4.16b``
    `hard_noisy_switching` hardware capsule.

A prepared capsule is not evidence. A pass requires real `pyNN.spiNNaker`, zero
synthetic fallback, zero `sim.run` failures, zero summary-read failures, real
spike readback, and task metrics above the predeclared thresholds.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import shutil
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

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

from coral_reef_spinnaker import Organism, ReefConfig  # noqa: E402
from coral_reef_spinnaker.runtime_modes import (  # noqa: E402
    LEARNING_LOCATIONS,
    RUNTIME_MODES,
    chunk_ranges,
    make_runtime_plan,
)
from coral_reef_spinnaker.spinnaker_compat import apply_spinnaker_numpy2_compat_patches  # noqa: E402
from tier2_learning import (  # noqa: E402
    DEFAULT_AMPLITUDE,
    DEFAULT_DT_SECONDS,
    criterion,
    json_safe,
    markdown_value,
    pass_fail,
    plot_case,
    strict_sign,
    write_csv,
    write_json,
    utc_now,
)
from tier4_scaling import alive_readout_weights, alive_trophic_health  # noqa: E402
from tier4_spinnaker_hardware_capsule import (  # noqa: E402
    BackendFallbackError,
    collect_environment,
    collect_recent_spinnaker_reports,
    safe_mean,
    safe_std,
    truthy,
)
from tier5_external_baselines import (  # noqa: E402
    TaskStream,
    delayed_cue_task,
    hard_noisy_switching_task,
    summarize_rows,
)

TIER = "Tier 4.16 - Harder SpiNNaker Hardware Capsule"
DEFAULT_TASKS = "delayed_cue,hard_noisy_switching"
DEFAULT_SEEDS = "42,43,44"
DEFAULT_STEPS = 120
DEFAULT_DELAYED_LR = 0.20
DEFAULT_HARD_PERIOD = 7
DEFAULT_HARD_MIN_DELAY = 3
DEFAULT_HARD_MAX_DELAY = 5
DEFAULT_HARD_NOISE_PROB = 0.20
DEFAULT_HARD_SENSORY_NOISE_FRACTION = 0.25
DEFAULT_HARD_MIN_SWITCH_INTERVAL = 32
DEFAULT_HARD_MAX_SWITCH_INTERVAL = 48
DEFAULT_HARD_TAIL_THRESHOLD = 0.50

TASK_PARTS = {
    "delayed_cue": "4.16a",
    "hard_noisy_switching": "4.16b",
}


def parse_csv_list(value: str) -> list[str]:
    items = [item.strip() for item in value.split(",") if item.strip()]
    if not items:
        raise argparse.ArgumentTypeError("at least one item is required")
    return items


def parse_seeds(value: str) -> list[int]:
    try:
        return [int(item) for item in parse_csv_list(value)]
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def parse_tasks(value: str) -> list[str]:
    tasks = parse_csv_list(value)
    unknown = [task for task in tasks if task not in TASK_PARTS]
    if unknown:
        raise argparse.ArgumentTypeError(f"unknown Tier 4.16 task(s): {', '.join(unknown)}")
    return tasks


def clean_float(value: Any) -> float | None:
    try:
        f = float(value)
    except Exception:
        return None
    return f if math.isfinite(f) else None


def build_task(task_name: str, *, seed: int, args: argparse.Namespace) -> TaskStream:
    if task_name == "delayed_cue":
        return delayed_cue_task(steps=args.steps, amplitude=args.amplitude, seed=seed, args=args)
    if task_name == "hard_noisy_switching":
        return hard_noisy_switching_task(steps=args.steps, amplitude=args.amplitude, seed=seed, args=args)
    raise ValueError(f"unknown task: {task_name}")


def task_horizon(task: TaskStream) -> int:
    due = np.asarray(task.feedback_due_step, dtype=int)
    offsets = due - np.arange(task.steps, dtype=int)
    valid = offsets[due >= 0]
    return int(max(1, int(np.max(valid)))) if valid.size else 1


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


class ChunkedHostReplay:
    """Host-side CRA-like delayed-credit replay for chunked hardware readback.

    This bridge is intentionally still host-side, but it should mirror the
    full CRA local readout path closely enough that chunked hardware probes do
    not test a different learner. The replay therefore uses the same sensory
    feature scale, initial local readout weight, every-step horizon ledger, and
    signed reward-gated readout update rule as ``LearningManager``.
    """

    def __init__(
        self,
        *,
        lr: float,
        amplitude: float,
        population_size: int,
        readout_lr: float = 0.10,
        feature_gain: float = 30.0,
        initial_weight: float = 0.25,
        weight_decay: float = 0.001,
        weight_clip: float = 20.0,
        negative_surprise_multiplier: float = 3.0,
        seed_output_scale: float = 0.1,
        dopamine_gain: float = 10000.0,
    ) -> None:
        self.delayed_lr = float(lr)
        self.readout_lr = float(readout_lr)
        self.amplitude = float(amplitude)
        self.population_size = max(1, int(population_size))
        self.feature_gain = float(feature_gain)
        self.initial_weight = float(initial_weight)
        self.weight_decay = float(weight_decay)
        self.weight_clip = float(weight_clip)
        self.negative_surprise_multiplier = float(negative_surprise_multiplier)
        self.seed_output_scale = float(seed_output_scale)
        self.dopamine_gain = float(dopamine_gain)
        self.weight = float(initial_weight)
        self.bias = 0.0
        self.pending: list[dict[str, Any]] = []
        self.matured_count = 0
        self.horizon_bars: int | None = None

    @staticmethod
    def _sign(value: float) -> int:
        return 1 if value > 0.0 else -1 if value < 0.0 else 0

    def _feature(self, sensory: float) -> float:
        return float(sensory) * self.feature_gain

    def _predict(self, feature: float) -> float:
        return float(math.tanh(self.weight * float(feature) + self.bias))

    def _apply_readout_update(
        self,
        *,
        prediction: float,
        feature: float,
        reinforcement_sign: int,
        learning_rate: float,
        dopamine_gate: float = 1.0,
    ) -> None:
        if dopamine_gate <= 0.0:
            return
        feature_sign = self._sign(float(feature))
        if feature_sign == 0 or reinforcement_sign == 0:
            return
        pred_sign = self._sign(float(prediction))
        if pred_sign == 0:
            pred_sign = feature_sign
        effective_lr = float(learning_rate) * float(dopamine_gate)
        if reinforcement_sign < 0:
            effective_lr *= self.negative_surprise_multiplier
        delta = effective_lr * float(reinforcement_sign) * float(pred_sign) * float(feature_sign)
        self.weight = (1.0 - self.weight_decay) * self.weight + delta
        self.weight = float(np.clip(self.weight, -self.weight_clip, self.weight_clip))

    def _advance_horizons(self, *, actual_return: float, step: int) -> int:
        if self.horizon_bars is None:
            raise RuntimeError("horizon_bars must be set before replay")
        matured_now = 0
        still_pending: list[dict[str, Any]] = []
        for record in self.pending:
            record["future_returns"].append(float(actual_return))
            bars_elapsed = int(step) - int(record["created_step"])
            if bars_elapsed < self.horizon_bars:
                still_pending.append(record)
                continue
            horizon_returns = record["future_returns"][: self.horizon_bars]
            cumulative_return = float(sum(horizon_returns))
            pred_sign = self._sign(float(record["prediction_at_cue"]))
            return_sign = self._sign(cumulative_return)
            reinforcement_sign = pred_sign * return_sign if pred_sign and return_sign else 0
            self._apply_readout_update(
                prediction=float(record["prediction_at_cue"]),
                feature=float(record["feature"]),
                reinforcement_sign=reinforcement_sign,
                learning_rate=self.delayed_lr,
                dopamine_gate=1.0,
            )
            self.matured_count += 1
            matured_now += 1
        self.pending = still_pending
        return matured_now

    def step(self, *, task: TaskStream, step: int, spike_count: int) -> dict[str, Any]:
        sensory = float(task.sensory[step])
        if self.horizon_bars is None:
            self.horizon_bars = task_horizon(task)
        feature = self._feature(sensory)
        spike_scale = min(2.0, max(0.0, float(spike_count) / float(self.population_size)))
        prediction = self._predict(feature)
        eval_sign = strict_sign(float(task.evaluation_target[step]))
        pred_sign = strict_sign(prediction)
        target_nonzero = bool(task.evaluation_mask[step] and eval_sign != 0)
        correct = bool(target_nonzero and pred_sign != 0 and pred_sign == eval_sign)
        actual_return = float(task.current_target[step])
        raw_dopamine = float(
            math.tanh(prediction * actual_return * self.seed_output_scale * self.dopamine_gain)
        )

        target_sign = self._sign(actual_return)
        if target_sign != 0:
            direction_correct = bool(pred_sign != 0 and pred_sign == target_sign)
            self._apply_readout_update(
                prediction=prediction,
                feature=feature,
                reinforcement_sign=1 if direction_correct else -1,
                learning_rate=self.readout_lr,
                dopamine_gate=abs(raw_dopamine),
            )

        # Match LearningManager ordering: immediate consequence learning runs
        # before matured delayed horizons, then the current prediction is added
        # to the pending ledger so it never sees its own current bar.
        matured_now = self._advance_horizons(actual_return=actual_return, step=step)
        self.pending.append(
            {
                "created_step": int(step),
                "due_step": int(task.feedback_due_step[step]),
                "feature": float(feature),
                "prediction_at_cue": prediction,
                "future_returns": [],
                "spike_scale": float(spike_scale),
            }
        )

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
            "mean_readout_weight": float(self.weight),
            "raw_dopamine": raw_dopamine,
            "matured_horizons": int(self.matured_count),
            "matured_horizons_this_step": int(matured_now),
            "pending_horizons": int(len(self.pending)),
            "n_alive": int(self.population_size),
            "births_this_step": 0,
            "deaths_this_step": 0,
        }


def make_hardware_config(*, seed: int, task: TaskStream, args: argparse.Namespace) -> ReefConfig:
    cfg = ReefConfig.default()
    cfg.seed = int(seed)
    cfg.lifecycle.initial_population = int(args.population_size)
    cfg.lifecycle.max_population_from_memory = False
    cfg.lifecycle.max_population_hard = int(args.population_size)
    cfg.lifecycle.enable_reproduction = False
    cfg.lifecycle.enable_apoptosis = False
    cfg.lifecycle.enable_structural_plasticity = True
    cfg.measurement.stream_history_maxlen = max(task.steps + 16, 128)
    cfg.spinnaker.sync_interval_steps = 0
    cfg.spinnaker.runtime_ms_per_step = float(args.dt_seconds) * 1000.0
    cfg.spinnaker.runtime_mode = str(args.runtime_mode)
    cfg.spinnaker.learning_location = str(args.learning_location)
    cfg.spinnaker.chunk_size_steps = int(args.chunk_size_steps)
    cfg.learning.evaluation_horizon_bars = task_horizon(task)
    cfg.learning.readout_learning_rate = float(args.readout_lr)
    cfg.learning.delayed_readout_learning_rate = float(args.delayed_readout_lr)
    return cfg


def run_spinnaker_task_seed(
    *,
    task_name: str,
    seed: int,
    args: argparse.Namespace,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    random.seed(seed)
    np.random.seed(seed)
    compat_status = apply_spinnaker_numpy2_compat_patches()

    import pyNN.spiNNaker as sim

    setup_kwargs: dict[str, Any] = {"timestep": args.timestep_ms}
    if args.spinnaker_hostname:
        setup_kwargs["spinnaker_hostname"] = args.spinnaker_hostname
    sim.setup(**setup_kwargs)

    task = build_task(task_name, seed=seed, args=args)
    cfg = make_hardware_config(seed=seed, task=task, args=args)
    organism: Organism | None = Organism(cfg, sim, setup_kwargs=setup_kwargs)
    rows: list[dict[str, Any]] = []
    diagnostics: dict[str, Any] = {}
    started = time.perf_counter()

    try:
        organism.initialize(stream_keys=[task.domain])
        for step in range(task.steps):
            sensory_value = float(task.sensory[step])
            target_value = float(task.current_target[step])
            metrics = organism.train_step(
                market_return_1m=target_value,
                dt_seconds=args.dt_seconds,
                sensory_return_1m=sensory_value,
            )
            diagnostics = organism.backend_diagnostics()
            if args.stop_on_backend_fallback and (
                int(diagnostics.get("sim_run_failures", 0)) > 0
                or int(diagnostics.get("summary_read_failures", 0)) > 0
                or int(diagnostics.get("synthetic_fallbacks", 0)) > 0
            ):
                raise BackendFallbackError(step, diagnostics)

            prediction = float(metrics.colony_prediction)
            eval_sign = strict_sign(float(task.evaluation_target[step]))
            pred_sign = strict_sign(prediction)
            weights = alive_readout_weights(organism)
            trophic = alive_trophic_health(organism)
            learning_status = (
                organism.learning_manager.get_summary()
                if organism.learning_manager is not None
                else {}
            )
            latest_spikes = organism.spike_buffer[-1] if organism.spike_buffer else {}
            row = metrics.to_dict()
            row.update(
                {
                    "tier": TIER,
                    "tier_part": TASK_PARTS[task.name],
                    "test_name": f"tier4_16_{task.name}",
                    "task": task.name,
                    "task_display_name": task.display_name,
                    "task_domain": task.domain,
                    "backend": "pyNN.spiNNaker",
                    "seed": int(seed),
                    "step": int(step),
                    "sensory_return_1m": sensory_value,
                    "target_return_1m": target_value,
                    "target_signal_horizon": float(task.evaluation_target[step]),
                    "target_signal_sign": eval_sign,
                    "target_signal_nonzero": bool(task.evaluation_mask[step] and eval_sign != 0),
                    "prediction_sign": pred_sign,
                    "strict_direction_correct": bool(
                        task.evaluation_mask[step]
                        and pred_sign != 0
                        and pred_sign == eval_sign
                    ),
                    "feedback_due_step": int(task.feedback_due_step[step]),
                    "configured_horizon_bars": int(cfg.learning.evaluation_horizon_bars),
                    "configured_readout_lr": float(cfg.learning.readout_learning_rate),
                    "configured_delayed_readout_lr": float(cfg.learning.delayed_readout_learning_rate),
                    "mean_readout_weight": float(np.mean(weights)) if weights else 0.0,
                    "min_readout_weight": float(np.min(weights)) if weights else 0.0,
                    "max_readout_weight": float(np.max(weights)) if weights else 0.0,
                    "mean_abs_readout_weight": float(np.mean(np.abs(weights))) if weights else 0.0,
                    "mean_trophic_health": float(np.mean(trophic)) if trophic else 0.0,
                    "min_trophic_health": float(np.min(trophic)) if trophic else 0.0,
                    "max_trophic_health": float(np.max(trophic)) if trophic else 0.0,
                    "pending_horizons": int(learning_status.get("pending_horizons", 0)),
                    "matured_horizons": int(learning_status.get("matured_horizons", 0)),
                    "step_spike_count": int(sum(int(v) for v in latest_spikes.values())),
                    "sim_run_failures": int(diagnostics.get("sim_run_failures", 0)),
                    "summary_read_failures": int(diagnostics.get("summary_read_failures", 0)),
                    "synthetic_fallbacks": int(diagnostics.get("synthetic_fallbacks", 0)),
                }
            )
            rows.append(row)
        diagnostics = organism.backend_diagnostics()
    finally:
        if organism is not None:
            if not diagnostics:
                diagnostics = organism.backend_diagnostics()
            organism.shutdown()
        try:
            sim.end()
        except Exception:
            pass

    summary = summarize_rows(rows)
    step_spikes = [float(r.get("step_spike_count", 0.0)) for r in rows]
    summary.update(
        {
            "tier_part": TASK_PARTS[task.name],
            "task": task.name,
            "task_display_name": task.display_name,
            "task_metadata": task.metadata,
            "backend": "pyNN.spiNNaker",
            "seed": int(seed),
            "steps": int(task.steps),
            "population_size": int(args.population_size),
            "runtime_seconds": time.perf_counter() - started,
            "total_step_spikes": int(sum(step_spikes)),
            "mean_step_spikes": float(np.mean(step_spikes)) if step_spikes else 0.0,
            "config": cfg.to_dict(),
        }
    )
    summary.update(diagnostics)
    summary["spinnman_numpy2_compat"] = compat_status
    return rows, summary


def run_chunked_spinnaker_task_seed(
    *,
    task_name: str,
    seed: int,
    args: argparse.Namespace,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Run a chunked direct-PyNN hardware capsule with host replay.

    This is intentionally narrower than the full ``Organism.train_step`` path:
    it is the Tier 4.17b-proven batching bridge for the repaired Tier 4.16a
    hardware probe. It schedules task input inside each chunk, bins real spike
    readback back to CRA step resolution, and replays delayed-credit learning on
    the host from those bins.
    """

    random.seed(seed)
    np.random.seed(seed)
    compat_status = apply_spinnaker_numpy2_compat_patches()

    import pyNN.spiNNaker as sim

    setup_kwargs: dict[str, Any] = {"timestep": args.timestep_ms}
    if args.spinnaker_hostname:
        setup_kwargs["spinnaker_hostname"] = args.spinnaker_hostname
    sim.setup(**setup_kwargs)

    task = build_task(task_name, seed=seed, args=args)
    currents = scheduled_currents(task, args)
    dt_ms = float(args.dt_seconds) * 1000.0
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
    started = time.perf_counter()
    calls = 0
    spike_bins = np.zeros(task.steps, dtype=int)

    try:
        if not hasattr(sim, "StepCurrentSource"):
            diagnostics["scheduled_input_failures"] = 1
            raise RuntimeError("pyNN.spiNNaker does not expose StepCurrentSource")
        cell = sim.IF_curr_exp(
            i_offset=0.0,
            tau_m=20.0,
            v_rest=-65.0,
            v_reset=-70.0,
            v_thresh=-55.0,
            tau_refrac=2.0,
            cm=0.25,
        )
        pop = sim.Population(
            int(args.population_size),
            cell,
            label=f"tier4_16_{task_name}_chunked_seed{seed}",
        )
        pop.record("spikes")
        times, amplitudes = compressed_current_schedule(currents, dt_ms)
        source = sim.StepCurrentSource(times=times, amplitudes=amplitudes)
        pop.inject(source)

        for start, stop in chunk_ranges(task.steps, int(args.chunk_size_steps)):
            try:
                sim.run(float(stop - start) * dt_ms)
                calls += 1
            except Exception:
                diagnostics["sim_run_failures"] += 1
                raise
            try:
                data = pop.get_data("spikes", clear=False)
                spiketrains = data.segments[0].spiketrains
                spike_bins = bin_spiketrains(spiketrains, steps=task.steps, dt_ms=dt_ms)
            except Exception:
                diagnostics["summary_read_failures"] += 1
                diagnostics["spike_readback_failures"] += 1
                raise
            for step in range(start, stop):
                row = replay.step(task=task, step=step, spike_count=int(spike_bins[step]))
                row.update(
                    {
                        "tier": TIER,
                        "tier_part": TASK_PARTS[task.name],
                        "test_name": f"tier4_16_{task.name}",
                        "task": task.name,
                        "task_display_name": task.display_name,
                        "task_domain": task.domain,
                        "backend": "pyNN.spiNNaker",
                        "backend_path": "direct_pynn_stepcurrent_chunked_host_replay",
                        "seed": int(seed),
                        "runtime_mode": "chunked",
                        "learning_location": "host",
                        "chunk_size_steps": int(args.chunk_size_steps),
                        "sim_run_calls": int(calls),
                        "configured_horizon_bars": int(task_horizon(task)),
                        "configured_readout_lr": float(args.readout_lr),
                        "configured_delayed_readout_lr": float(args.delayed_readout_lr),
                        "mean_trophic_health": 1.0,
                        "min_trophic_health": 1.0,
                        "max_trophic_health": 1.0,
                        "sim_run_failures": int(diagnostics["sim_run_failures"]),
                        "summary_read_failures": int(diagnostics["summary_read_failures"]),
                        "synthetic_fallbacks": int(diagnostics["synthetic_fallbacks"]),
                    }
                )
                rows.append(row)
    finally:
        try:
            sim.end()
        except Exception:
            pass

    summary = summarize_rows(rows)
    step_spikes = [float(r.get("step_spike_count", 0.0)) for r in rows]
    summary.update(
        {
            "tier_part": TASK_PARTS[task.name],
            "task": task.name,
            "task_display_name": task.display_name,
            "task_metadata": task.metadata,
            "backend": "pyNN.spiNNaker",
            "backend_path": "direct_pynn_stepcurrent_chunked_host_replay",
            "seed": int(seed),
            "steps": int(task.steps),
            "population_size": int(args.population_size),
            "runtime_mode": "chunked",
            "learning_location": "host",
            "chunk_size_steps": int(args.chunk_size_steps),
            "sim_run_calls": int(calls),
            "call_reduction_factor": (
                float(task.steps) / float(calls) if calls else None
            ),
            "runtime_seconds": time.perf_counter() - started,
            "total_step_spikes": int(sum(step_spikes)),
            "mean_step_spikes": float(np.mean(step_spikes)) if step_spikes else 0.0,
            "scheduled_input_mode": "StepCurrentSource",
            "binned_readback": True,
            "host_replay": True,
            "final_n_alive": int(args.population_size),
            "total_births": 0,
            "total_deaths": 0,
            "final_mean_readout_weight": float(rows[-1]["host_replay_weight"]) if rows else 0.0,
            "scheduled_current_changes": len(compressed_current_schedule(currents, dt_ms)[0]),
            "scheduled_current_min": float(np.min(currents)),
            "scheduled_current_max": float(np.max(currents)),
        }
    )
    summary.update(diagnostics)
    summary["spinnman_numpy2_compat"] = compat_status
    return rows, summary


def summarize_task(task_name: str, summaries: list[dict[str, Any]]) -> dict[str, Any]:
    task_rows = [s for s in summaries if s.get("task") == task_name]
    keys = [
        "all_accuracy",
        "tail_accuracy",
        "prediction_target_corr",
        "tail_prediction_target_corr",
        "final_n_alive",
        "total_births",
        "total_deaths",
        "final_mean_readout_weight",
        "runtime_seconds",
        "total_step_spikes",
        "mean_step_spikes",
        "sim_run_failures",
        "summary_read_failures",
        "synthetic_fallbacks",
        "evaluation_count",
        "max_abs_dopamine",
        "mean_abs_dopamine",
    ]
    out: dict[str, Any] = {
        "task": task_name,
        "tier_part": TASK_PARTS[task_name],
        "runs": len(task_rows),
        "seeds": [s.get("seed") for s in task_rows],
    }
    for key in keys:
        values = [s.get(key) for s in task_rows]
        out[f"{key}_mean"] = safe_mean(values)
        out[f"{key}_std"] = safe_std(values)
        numeric = [clean_float(v) for v in values]
        numeric = [v for v in numeric if v is not None]
        out[f"{key}_min"] = min(numeric) if numeric else None
        out[f"{key}_max"] = max(numeric) if numeric else None
    out["sim_run_failures_sum"] = int(sum(int(s.get("sim_run_failures", 0)) for s in task_rows))
    out["summary_read_failures_sum"] = int(sum(int(s.get("summary_read_failures", 0)) for s in task_rows))
    out["synthetic_fallbacks_sum"] = int(sum(int(s.get("synthetic_fallbacks", 0)) for s in task_rows))
    out["total_births_sum"] = int(sum(int(s.get("total_births", 0)) for s in task_rows))
    out["total_deaths_sum"] = int(sum(int(s.get("total_deaths", 0)) for s in task_rows))
    return out


def aggregate_summaries(summaries: list[dict[str, Any]], tasks: list[str], seeds: list[int]) -> dict[str, Any]:
    task_summaries = [summarize_task(task, summaries) for task in tasks]
    return {
        "backend": "pyNN.spiNNaker",
        "runs": len(summaries),
        "tasks": tasks,
        "seeds": seeds,
        "task_summaries": task_summaries,
        "sim_run_failures_sum": int(sum(int(s.get("sim_run_failures", 0)) for s in summaries)),
        "summary_read_failures_sum": int(sum(int(s.get("summary_read_failures", 0)) for s in summaries)),
        "synthetic_fallbacks_sum": int(sum(int(s.get("synthetic_fallbacks", 0)) for s in summaries)),
        "total_births_sum": int(sum(int(s.get("total_births", 0)) for s in summaries)),
        "total_deaths_sum": int(sum(int(s.get("total_deaths", 0)) for s in summaries)),
        "total_step_spikes_min": safe_mean([min([s.get("total_step_spikes", 0) for s in summaries])] if summaries else []),
        "total_step_spikes_mean": safe_mean([s.get("total_step_spikes") for s in summaries]),
        "runtime_seconds_mean": safe_mean([s.get("runtime_seconds") for s in summaries]),
    }


def criteria_for_run(aggregate: dict[str, Any], args: argparse.Namespace) -> list[dict[str, Any]]:
    tasks = list(aggregate.get("tasks") or [])
    expected_runs = len(tasks) * len(args.seeds)
    by_task = {row["task"]: row for row in aggregate.get("task_summaries", [])}
    delayed = by_task.get("delayed_cue", {})
    hard = by_task.get("hard_noisy_switching", {})
    criteria = [
        criterion("all requested task/seed hardware runs completed", aggregate.get("runs"), "==", expected_runs, int(aggregate.get("runs", 0)) == expected_runs),
        criterion("sim.run failures sum", aggregate.get("sim_run_failures_sum"), "==", 0, int(aggregate.get("sim_run_failures_sum", 0)) == 0),
        criterion("summary read failures sum", aggregate.get("summary_read_failures_sum"), "==", 0, int(aggregate.get("summary_read_failures_sum", 0)) == 0),
        criterion("synthetic fallback sum", aggregate.get("synthetic_fallbacks_sum"), "==", 0, int(aggregate.get("synthetic_fallbacks_sum", 0)) == 0),
        criterion("real spike readback in every run", aggregate.get("total_step_spikes_min"), ">", 0, (clean_float(aggregate.get("total_step_spikes_min")) or 0.0) > 0.0),
        criterion("fixed population has no births/deaths", {"births": aggregate.get("total_births_sum"), "deaths": aggregate.get("total_deaths_sum")}, "==", {"births": 0, "deaths": 0}, int(aggregate.get("total_births_sum", 0)) == 0 and int(aggregate.get("total_deaths_sum", 0)) == 0),
    ]
    if "delayed_cue" in tasks:
        criteria.append(
            criterion(
                "4.16a delayed_cue tail accuracy",
                delayed.get("tail_accuracy_min"),
                ">=",
                args.delayed_tail_threshold,
                (clean_float(delayed.get("tail_accuracy_min")) or 0.0) >= args.delayed_tail_threshold,
            )
        )
    if "hard_noisy_switching" in tasks:
        criteria.append(
            criterion(
                "4.16b hard_noisy_switching tail accuracy",
                hard.get("tail_accuracy_min"),
                ">=",
                args.hard_tail_threshold,
                (clean_float(hard.get("tail_accuracy_min")) or 0.0) >= args.hard_tail_threshold,
            )
        )
        criteria.append(
            criterion(
                "4.16b hard_noisy_switching tail correlation is finite",
                hard.get("tail_prediction_target_corr_mean"),
                "is finite",
                True,
                clean_float(hard.get("tail_prediction_target_corr_mean")) is not None,
            )
        )
    criteria.append(
        criterion(
            "confirmed delayed-credit setting used",
            args.delayed_readout_lr,
            "==",
            DEFAULT_DELAYED_LR,
            abs(float(args.delayed_readout_lr) - DEFAULT_DELAYED_LR) < 1e-12,
        )
    )
    return criteria


def plot_summary(task_summaries: list[dict[str, Any]], output_path: Path) -> None:
    if plt is None or not task_summaries:
        return
    labels = [row["task"].replace("_", "\n") for row in task_summaries]
    tail = [row.get("tail_accuracy_mean") or 0.0 for row in task_summaries]
    corr = [row.get("tail_prediction_target_corr_mean") or 0.0 for row in task_summaries]
    spikes = [row.get("total_step_spikes_mean") or 0.0 for row in task_summaries]
    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    axes[0].bar(labels, tail, color="#1f6feb")
    axes[0].set_title("Tail accuracy")
    axes[0].set_ylim(0, 1.05)
    axes[1].bar(labels, corr, color="#2f855a")
    axes[1].set_title("Tail correlation")
    axes[1].axhline(0, color="black", lw=0.8)
    axes[2].bar(labels, spikes, color="#8250df")
    axes[2].set_title("Mean spike readback")
    for ax in axes:
        ax.grid(axis="y", alpha=0.25)
    fig.suptitle(TIER)
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def write_summary_csv(path: Path, rows: list[dict[str, Any]]) -> None:
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
            writer.writerow({k: json_safe(v) for k, v in row.items()})


def write_jobmanager_capsule(output_dir: Path, args: argparse.Namespace) -> dict[str, str]:
    capsule_dir = output_dir / "jobmanager_capsule"
    capsule_dir.mkdir(parents=True, exist_ok=True)
    config_path = capsule_dir / "capsule_config.json"
    command_path = capsule_dir / "run_tier4_16_on_jobmanager.sh"
    readme_path = capsule_dir / "README_JOBMANAGER.md"
    expected_path = capsule_dir / "expected_outputs.json"

    command = [
        "python3 experiments/tier4_harder_spinnaker_capsule.py",
        "--mode run-hardware",
        "--require-real-hardware",
        "--stop-on-fail",
        f"--tasks {','.join(args.tasks)}",
        f"--seeds {','.join(str(s) for s in args.seeds)}",
        f"--steps {args.steps}",
        f"--population-size {args.population_size}",
        f"--delayed-readout-lr {args.delayed_readout_lr}",
        f"--readout-lr {args.readout_lr}",
        f"--runtime-mode {args.runtime_mode}",
        f"--learning-location {args.learning_location}",
        f"--chunk-size-steps {args.chunk_size_steps}",
        "--output-dir \"$OUT_DIR\"",
    ]
    config_payload = {
        "tier": TIER,
        "tasks": args.tasks,
        "parts": {task: TASK_PARTS[task] for task in args.tasks},
        "seeds": args.seeds,
        "steps": args.steps,
        "population_size": args.population_size,
        "delayed_readout_lr": args.delayed_readout_lr,
        "readout_lr": args.readout_lr,
        "runtime_mode": args.runtime_mode,
        "learning_location": args.learning_location,
        "chunk_size_steps": args.chunk_size_steps,
        "scheduled_input_mode": "StepCurrentSource" if args.runtime_mode == "chunked" else None,
        "binned_readback": bool(args.runtime_mode == "chunked"),
        "host_replay": bool(args.runtime_mode == "chunked" and args.learning_location == "host"),
        "claim_boundary": "Prepared capsule is not hardware evidence. PASS requires real pyNN.spiNNaker execution with zero fallback/failures and real spike readback.",
    }
    write_json(config_path, config_payload)
    command_path.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                "",
                "# Run from the repository root inside EBRAINS/JobManager with real SpiNNaker access.",
                "OUT_DIR=${1:-tier4_16_job_output}",
                " \\\n  ".join(command),
                "",
            ]
        ),
        encoding="utf-8",
    )
    command_path.chmod(0o755)
    expected_path.write_text(
        json.dumps(
            {
                "required": [
                    "tier4_16_results.json",
                    "tier4_16_report.md",
                    "tier4_16_summary.csv",
                    "tier4_16_task_summary.csv",
                    "tier4_16_hardware_summary.png",
                    "spinnaker_hardware_<task>_seed<seed>_timeseries.csv",
                    "spinnaker_hardware_<task>_seed<seed>_timeseries.png",
                ],
                "pass_requires": [
                    "hardware_run_attempted=true",
                    "sim_run_failures_sum=0",
                    "summary_read_failures_sum=0",
                    "synthetic_fallbacks_sum=0",
                    "real spike readback > 0 in every run",
                    "delayed_readout_lr=0.20",
                    "for chunked mode: scheduled input, binned readback, and host replay enabled",
                    "task metrics above thresholds",
                ],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    part_lines = [f"- {TASK_PARTS[task]}: `{task}`" for task in args.tasks]
    readme_path.write_text(
        "\n".join(
            [
                "# Tier 4.16 Harder SpiNNaker Hardware Capsule",
                "",
                "This capsule tests whether the Tier 5.4 confirmed delayed-credit setting survives on real SpiNNaker hardware.",
                "",
                "Chunked mode uses scheduled input, per-step binned spike readback, and host-side delayed-credit replay. It is still not continuous/on-chip learning.",
                "",
                "## Run",
                "",
                "```bash",
                "bash controlled_test_output/<tier4_16_prepared_run>/jobmanager_capsule/run_tier4_16_on_jobmanager.sh /tmp/tier4_16_job_output",
                "```",
                "",
                "## Claim Boundary",
                "",
                "A prepared capsule is not a hardware pass. A pass requires real `pyNN.spiNNaker`, zero fallback, zero `sim.run` failures, zero summary-read failures, real spike readback, and task metrics above threshold.",
                "",
                "This is not a superiority claim and not hardware population scaling.",
                "",
                "## Parts",
                "",
                *part_lines,
                "",
            ]
        ),
        encoding="utf-8",
    )
    return {
        "capsule_dir": str(capsule_dir),
        "capsule_config_json": str(config_path),
        "jobmanager_run_script": str(command_path),
        "jobmanager_readme": str(readme_path),
        "expected_outputs_json": str(expected_path),
    }


def write_report(
    *,
    path: Path,
    mode: str,
    status: str,
    output_dir: Path,
    criteria: list[dict[str, Any]],
    artifacts: dict[str, str],
    summary: dict[str, Any],
    failure_reason: str = "",
) -> None:
    lines = [
        "# Tier 4.16 Harder SpiNNaker Hardware Capsule Findings",
        "",
        f"- Generated: `{utc_now()}`",
        f"- Mode: `{mode}`",
        f"- Status: **{status.upper()}**",
        f"- Output directory: `{output_dir}`",
        "",
        "Tier 4.16 tests whether the Tier 5.4 confirmed delayed-credit setting survives on real SpiNNaker hardware.",
        "",
        "## Claim Boundary",
        "",
        "- `PREPARED` means the JobManager capsule exists locally; it is not hardware evidence.",
        "- `PASS` requires real `pyNN.spiNNaker`, zero synthetic fallback, zero `sim.run` failures, zero summary-read failures, real spike readback, and task metrics above threshold.",
        "- This is not full hardware scaling and not a superiority claim over external baselines.",
        "",
        "## Summary",
        "",
    ]
    for key in [
        "hardware_run_attempted",
        "hardware_target_configured",
        "backend",
        "tasks",
        "seeds",
        "runs",
        "runtime_mode",
        "learning_location",
        "chunk_size_steps",
        "total_step_spikes_min",
        "total_step_spikes_mean",
        "sim_run_failures_sum",
        "summary_read_failures_sum",
        "synthetic_fallbacks_sum",
        "runtime_seconds_mean",
        "capsule_dir",
        "jobmanager_cli",
        "failure_step",
    ]:
        if key in summary:
            lines.append(f"- {key}: `{markdown_value(summary.get(key))}`")
    if failure_reason:
        lines.extend(["", f"Failure: {failure_reason}", ""])
    task_summaries = summary.get("task_summaries") or []
    if task_summaries:
        lines.extend([
            "",
            "## Task Summary",
            "",
            "| Part | Task | Runs | Tail Acc Mean | Tail Acc Min | Tail Corr Mean | Spike Min | Runtime Mean |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ])
        for row in task_summaries:
            lines.append(
                "| "
                f"{row.get('tier_part')} | `{row.get('task')}` | {markdown_value(row.get('runs'))} | "
                f"{markdown_value(row.get('tail_accuracy_mean'))} | {markdown_value(row.get('tail_accuracy_min'))} | "
                f"{markdown_value(row.get('tail_prediction_target_corr_mean'))} | {markdown_value(row.get('total_step_spikes_min'))} | "
                f"{markdown_value(row.get('runtime_seconds_mean'))} |"
            )
    if criteria:
        lines.extend([
            "",
            "## Criteria",
            "",
            "| Criterion | Value | Rule | Pass |",
            "| --- | --- | --- | --- |",
        ])
        for item in criteria:
            lines.append(
                "| "
                f"{item['name']} | {markdown_value(item['value'])} | "
                f"{item['operator']} {markdown_value(item['threshold'])} | "
                f"{'yes' if item['passed'] else 'no'} |"
            )
    lines.extend(["", "## Artifacts", ""])
    for label, artifact in artifacts.items():
        lines.append(f"- `{label}`: `{artifact}`")
    if artifacts.get("hardware_summary_png"):
        lines.extend(["", "![tier4_16_hardware_summary](tier4_16_hardware_summary.png)", ""])
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_latest(output_dir: Path, report_path: Path, manifest_path: Path, status: str) -> None:
    latest_dir = ROOT / "controlled_test_output"
    latest_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        latest_dir / "tier4_16_latest_manifest.json",
        {
            "generated_at_utc": utc_now(),
            "manifest": str(manifest_path),
            "report": str(report_path),
            "output_dir": str(output_dir),
            "status": status,
            "canonical": False,
            "claim": "Latest Tier 4.16 harder SpiNNaker hardware capsule; promote only after real hardware review.",
        },
    )


def prepare_capsule(args: argparse.Namespace, output_dir: Path) -> int:
    env = collect_environment(args)
    capsule_artifacts = write_jobmanager_capsule(output_dir, args)
    summary = {
        "mode": "prepare",
        "backend": "pyNN.spiNNaker",
        "hardware_run_attempted": False,
        "hardware_target_configured": bool(env.get("hardware_target_configured")),
        "jobmanager_cli": env.get("jobmanager_cli"),
        "tasks": args.tasks,
        "seeds": args.seeds,
        "steps": args.steps,
        "population_size": args.population_size,
        "delayed_readout_lr": args.delayed_readout_lr,
        "runtime_mode": args.runtime_mode,
        "learning_location": args.learning_location,
        "chunk_size_steps": args.chunk_size_steps,
        "capsule_dir": capsule_artifacts.get("capsule_dir"),
    }
    criteria = [
        criterion("capsule directory exists", capsule_artifacts.get("capsule_dir"), "exists", True, Path(capsule_artifacts["capsule_dir"]).exists()),
        criterion("confirmed delayed-credit setting selected", args.delayed_readout_lr, "==", DEFAULT_DELAYED_LR, abs(float(args.delayed_readout_lr) - DEFAULT_DELAYED_LR) < 1e-12),
        criterion("4.16a delayed_cue included", "delayed_cue" in args.tasks, "==", True, "delayed_cue" in args.tasks),
        criterion("runtime plan is implemented", make_runtime_plan(runtime_mode=args.runtime_mode, learning_location=args.learning_location, chunk_size_steps=args.chunk_size_steps, total_steps=args.steps, dt_seconds=args.dt_seconds).implementation_stage, "implemented", True, make_runtime_plan(runtime_mode=args.runtime_mode, learning_location=args.learning_location, chunk_size_steps=args.chunk_size_steps, total_steps=args.steps, dt_seconds=args.dt_seconds).implemented),
    ]
    if len(args.tasks) > 1:
        criteria.append(criterion("4.16b hard_noisy_switching included", "hard_noisy_switching" in args.tasks, "==", True, "hard_noisy_switching" in args.tasks))
    status, failure = pass_fail(criteria)
    status = "prepared" if status == "pass" else "fail"
    manifest_path = output_dir / "tier4_16_results.json"
    report_path = output_dir / "tier4_16_report.md"
    summary_csv_path = output_dir / "tier4_16_summary.csv"
    write_json(
        manifest_path,
        {
            "generated_at_utc": utc_now(),
            "tier": TIER,
            "mode": "prepare",
            "status": status,
            "failure_reason": failure,
            "summary": summary,
            "criteria": criteria,
            "environment": env,
            "artifacts": capsule_artifacts,
        },
    )
    write_summary_csv(summary_csv_path, [summary])
    write_report(
        path=report_path,
        mode="prepare",
        status=status,
        output_dir=output_dir,
        criteria=criteria,
        artifacts={"manifest_json": str(manifest_path), "summary_csv": str(summary_csv_path), **capsule_artifacts},
        summary=summary,
        failure_reason=failure,
    )
    write_latest(output_dir, report_path, manifest_path, status)
    return 0 if status == "prepared" else 1


def run_hardware(args: argparse.Namespace, output_dir: Path) -> int:
    run_started_epoch = time.time()
    env = collect_environment(args)
    env["spinnman_numpy2_compat"] = apply_spinnaker_numpy2_compat_patches()
    hardware_target_configured = bool(env.get("hardware_target_configured"))
    runtime_plan = make_runtime_plan(
        runtime_mode=args.runtime_mode,
        learning_location=args.learning_location,
        chunk_size_steps=args.chunk_size_steps,
        total_steps=args.steps,
        dt_seconds=args.dt_seconds,
    )
    if not runtime_plan.implemented:
        failure = (
            "Requested runtime plan is not implemented for Tier 4.16 hardware: "
            f"{runtime_plan.implementation_stage}; blockers={list(runtime_plan.blockers)}. "
            "Choose step+host or chunked+host for this runner; hybrid, on-chip, "
            "and continuous modes remain future custom-runtime work."
        )
        summary = {
            "mode": "run-hardware",
            "backend": "pyNN.spiNNaker",
            "hardware_run_attempted": False,
            "hardware_target_configured": hardware_target_configured,
            "jobmanager_cli": env.get("jobmanager_cli"),
            "tasks": args.tasks,
            "seeds": args.seeds,
            "runtime_mode": args.runtime_mode,
            "learning_location": args.learning_location,
            "chunk_size_steps": args.chunk_size_steps,
            "runtime_plan": runtime_plan.__dict__,
        }
        criteria = [
            criterion(
                "requested runtime plan implemented",
                runtime_plan.implementation_stage,
                "==",
                "current_step_host_loop",
                False,
            )
        ]
        manifest_path = output_dir / "tier4_16_results.json"
        report_path = output_dir / "tier4_16_report.md"
        summary_csv_path = output_dir / "tier4_16_summary.csv"
        write_json(manifest_path, {"generated_at_utc": utc_now(), "tier": TIER, "mode": "run-hardware", "status": "blocked", "failure_reason": failure, "summary": summary, "criteria": criteria, "environment": env})
        write_summary_csv(summary_csv_path, [summary])
        write_report(path=report_path, mode="run-hardware", status="blocked", output_dir=output_dir, criteria=criteria, artifacts={"manifest_json": str(manifest_path), "summary_csv": str(summary_csv_path)}, summary=summary, failure_reason=failure)
        write_latest(output_dir, report_path, manifest_path, "blocked")
        return 1
    virtual_board_requested = truthy((env.get("spynnaker_config") or {}).get("virtual_board"))
    if args.require_real_hardware and not hardware_target_configured:
        env["hardware_target_detection_note"] = (
            "No explicit Machine target was visible to the local detector "
            "(machineName/version/spalloc_server/remote_spinnaker_url/env flags "
            "were absent). This is advisory only: prior EBRAINS/JobManager runs "
            "may still provide a usable target at runtime, so hardware evidence "
            "is decided by the actual pyNN.spiNNaker run, fallback count, readback "
            "failures, and nonzero real spike readback."
        )
    if args.require_real_hardware and virtual_board_requested:
        failure = "sPyNNaker is configured for virtual_board=True. Refusing to run virtual-board output as Tier 4.16 hardware."
        summary = {
            "mode": "run-hardware",
            "backend": "pyNN.spiNNaker",
            "hardware_run_attempted": False,
            "hardware_target_configured": False,
            "jobmanager_cli": env.get("jobmanager_cli"),
            "tasks": args.tasks,
            "seeds": args.seeds,
        }
        criteria = [criterion("real SpiNNaker target configured", {"hardware_target_configured": hardware_target_configured, "virtual_board": True}, "==", {"virtual_board": False}, False)]
        manifest_path = output_dir / "tier4_16_results.json"
        report_path = output_dir / "tier4_16_report.md"
        summary_csv_path = output_dir / "tier4_16_summary.csv"
        write_json(manifest_path, {"generated_at_utc": utc_now(), "tier": TIER, "mode": "run-hardware", "status": "blocked", "failure_reason": failure, "summary": summary, "criteria": criteria, "environment": env})
        write_summary_csv(summary_csv_path, [summary])
        write_report(path=report_path, mode="run-hardware", status="blocked", output_dir=output_dir, criteria=criteria, artifacts={"manifest_json": str(manifest_path), "summary_csv": str(summary_csv_path)}, summary=summary, failure_reason=failure)
        write_latest(output_dir, report_path, manifest_path, "blocked")
        return 1

    summaries: list[dict[str, Any]] = []
    artifacts: dict[str, str] = {}
    failure_reason = ""
    failure_traceback = ""
    failure_diagnostics: dict[str, Any] = {}
    failure_step: int | None = None
    hardware_run_attempted = False

    for task_name in args.tasks:
        for seed in args.seeds:
            try:
                hardware_run_attempted = True
                if args.runtime_mode == "chunked" and args.learning_location == "host":
                    rows, summary = run_chunked_spinnaker_task_seed(task_name=task_name, seed=seed, args=args)
                else:
                    rows, summary = run_spinnaker_task_seed(task_name=task_name, seed=seed, args=args)
            except Exception as exc:
                failure_reason = f"task {task_name} seed {seed} raised {type(exc).__name__}: {exc}"
                failure_traceback = traceback.format_exc()
                failure_diagnostics = getattr(exc, "diagnostics", {}) or {}
                failure_step = getattr(exc, "step", None)
                trace_path = output_dir / f"{task_name}_seed_{seed}_failure_traceback.txt"
                trace_path.write_text(failure_traceback, encoding="utf-8")
                artifacts[f"{task_name}_seed_{seed}_failure_traceback"] = str(trace_path)
                if failure_diagnostics:
                    diag_path = output_dir / f"{task_name}_seed_{seed}_backend_diagnostics.json"
                    write_json(diag_path, failure_diagnostics)
                    artifacts[f"{task_name}_seed_{seed}_backend_diagnostics"] = str(diag_path)
                    inner_traceback = str(failure_diagnostics.get("last_backend_traceback", ""))
                    if inner_traceback:
                        inner_path = output_dir / f"{task_name}_seed_{seed}_inner_backend_traceback.txt"
                        inner_path.write_text(inner_traceback, encoding="utf-8")
                        artifacts[f"{task_name}_seed_{seed}_inner_backend_traceback"] = str(inner_path)
                if args.stop_on_fail:
                    break
                continue
            csv_path = output_dir / f"spinnaker_hardware_{task_name}_seed{seed}_timeseries.csv"
            png_path = output_dir / f"spinnaker_hardware_{task_name}_seed{seed}_timeseries.png"
            write_csv(csv_path, rows)
            switch_step = None
            task_meta = summary.get("task_metadata", {})
            if isinstance(task_meta, dict) and task_meta.get("switch_steps"):
                switch_steps = task_meta.get("switch_steps") or []
                switch_step = int(switch_steps[1]) if len(switch_steps) > 1 else None
            plot_case(rows, png_path, f"Tier 4.16 {task_name} hardware seed {seed}", switch_step=switch_step)
            artifacts[f"{task_name}_seed_{seed}_timeseries_csv"] = str(csv_path)
            if png_path.exists():
                artifacts[f"{task_name}_seed_{seed}_timeseries_png"] = str(png_path)
            summaries.append(summary)
        if failure_reason and args.stop_on_fail:
            break

    aggregate = aggregate_summaries(summaries, args.tasks, args.seeds)
    aggregate.update(
        {
            "mode": "run-hardware",
            "hardware_run_attempted": hardware_run_attempted,
            "hardware_target_configured": hardware_target_configured,
            "jobmanager_cli": env.get("jobmanager_cli"),
            "failure_reason": failure_reason,
            "failure_step": failure_step,
            "failure_diagnostics": failure_diagnostics,
        }
    )
    criteria = criteria_for_run(aggregate, args) if summaries else []
    status, criteria_failure = pass_fail(criteria) if criteria else ("fail", failure_reason)
    if criteria_failure:
        failure_reason = criteria_failure
    summary_png = output_dir / "tier4_16_hardware_summary.png"
    if summaries:
        plot_summary(aggregate.get("task_summaries", []), summary_png)
        if summary_png.exists():
            artifacts["hardware_summary_png"] = str(summary_png)
    artifacts.update(collect_recent_spinnaker_reports(output_dir, run_started_epoch))
    if failure_traceback:
        aggregate["failure_traceback"] = failure_traceback

    manifest_path = output_dir / "tier4_16_results.json"
    report_path = output_dir / "tier4_16_report.md"
    summary_csv_path = output_dir / "tier4_16_summary.csv"
    task_summary_path = output_dir / "tier4_16_task_summary.csv"
    write_json(
        manifest_path,
        {
            "generated_at_utc": utc_now(),
            "tier": TIER,
            "mode": "run-hardware",
            "status": status,
            "failure_reason": failure_reason,
            "summary": aggregate,
            "criteria": criteria,
            "seed_summaries": summaries,
            "artifacts": artifacts,
            "environment": env,
        },
    )
    write_summary_csv(summary_csv_path, summaries)
    write_summary_csv(task_summary_path, aggregate.get("task_summaries", []))
    write_report(path=report_path, mode="run-hardware", status=status, output_dir=output_dir, criteria=criteria, artifacts={"manifest_json": str(manifest_path), "summary_csv": str(summary_csv_path), "task_summary_csv": str(task_summary_path), **artifacts}, summary=aggregate, failure_reason=failure_reason)
    write_latest(output_dir, report_path, manifest_path, status)
    return 0 if status == "pass" else 1


def ingest_results(args: argparse.Namespace, output_dir: Path) -> int:
    if args.ingest_dir is None:
        raise SystemExit("--ingest-dir is required in ingest mode")
    ingest_dir = args.ingest_dir.resolve()
    source = ingest_dir / "tier4_16_results.json"
    if not source.exists():
        raise SystemExit(f"No Tier 4.16 result JSON found in {ingest_dir}")
    data = json.loads(source.read_text(encoding="utf-8"))
    summary = dict(data.get("summary", {}))
    summary.update({"mode": "ingest", "ingested_from": str(source)})
    criteria = list(data.get("criteria", []))
    status = str(data.get("status", "unknown"))
    artifacts: dict[str, str] = {"ingested_source": str(source)}
    for name in [
        "tier4_16_summary.csv",
        "tier4_16_task_summary.csv",
        "tier4_16_hardware_summary.png",
    ]:
        src = ingest_dir / name
        if src.exists():
            dest = output_dir / name
            shutil.copy2(src, dest)
            artifacts[name] = str(dest)
    for pattern in [
        "spinnaker_hardware_*_timeseries.csv",
        "spinnaker_hardware_*_timeseries.png",
    ]:
        for src in sorted(ingest_dir.glob(pattern)):
            dest = output_dir / src.name
            shutil.copy2(src, dest)
            artifacts[src.name] = str(dest)
    raw_dir = output_dir / "raw_hardware_artifacts"
    raw_copied = False
    for src_name, dest_name in [
        ("reports.zip", "reports.zip"),
        ("global_provenance.sqlite3", "global_provenance.sqlite3"),
        ("finished", "finished"),
        ("tier4_16_latest_manifest.json", "tier4_16_latest_manifest.json"),
        ("tier4_16_report.md", "source_tier4_16_report.md"),
    ]:
        src = ingest_dir / src_name
        if src.exists():
            raw_dir.mkdir(parents=True, exist_ok=True)
            dest = raw_dir / dest_name
            shutil.copy2(src, dest)
            artifacts[f"raw_{dest_name}"] = str(dest)
            raw_copied = True
    if raw_copied:
        artifacts["raw_hardware_artifacts_dir"] = str(raw_dir)
    manifest_path = output_dir / "tier4_16_results.json"
    report_path = output_dir / "tier4_16_report.md"
    summary_csv_path = output_dir / "tier4_16_summary.csv"
    if not summary_csv_path.exists():
        write_summary_csv(summary_csv_path, data.get("seed_summaries", []))
    write_json(
        manifest_path,
        {
            "generated_at_utc": utc_now(),
            "tier": TIER,
            "mode": "ingest",
            "status": status,
            "ingested_from": str(source),
            "summary": summary,
            "criteria": criteria,
            "source_manifest": data,
            "artifacts": artifacts,
        },
    )
    write_report(path=report_path, mode="ingest", status=status, output_dir=output_dir, criteria=criteria, artifacts={"manifest_json": str(manifest_path), "summary_csv": str(summary_csv_path), **artifacts}, summary=summary, failure_reason=str(data.get("failure_reason", "")))
    write_latest(output_dir, report_path, manifest_path, status)
    return 0 if status == "pass" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare, run, or ingest Tier 4.16 harder SpiNNaker hardware capsule.")
    parser.add_argument("--mode", choices=["prepare", "run-hardware", "ingest"], default="prepare")
    parser.add_argument("--tasks", type=parse_tasks, default=parse_tasks(DEFAULT_TASKS))
    parser.add_argument("--seeds", type=parse_seeds, default=parse_seeds(DEFAULT_SEEDS))
    parser.add_argument("--steps", type=int, default=DEFAULT_STEPS)
    parser.add_argument("--population-size", type=int, default=8)
    parser.add_argument("--amplitude", type=float, default=DEFAULT_AMPLITUDE)
    parser.add_argument("--dt-seconds", type=float, default=DEFAULT_DT_SECONDS)
    parser.add_argument("--timestep-ms", type=float, default=1.0)
    parser.add_argument("--readout-lr", type=float, default=0.10)
    parser.add_argument("--delayed-readout-lr", type=float, default=DEFAULT_DELAYED_LR)
    parser.add_argument("--base-current-na", type=float, default=1.4)
    parser.add_argument("--cue-current-gain-na", type=float, default=0.2)
    parser.add_argument("--min-current-na", type=float, default=0.0)
    parser.add_argument("--delayed-tail-threshold", type=float, default=0.85)
    parser.add_argument("--hard-tail-threshold", type=float, default=DEFAULT_HARD_TAIL_THRESHOLD)
    parser.add_argument("--delay", type=int, default=5)
    parser.add_argument("--period", type=int, default=8)
    parser.add_argument("--min-delay", type=int, default=DEFAULT_HARD_MIN_DELAY)
    parser.add_argument("--max-delay", type=int, default=DEFAULT_HARD_MAX_DELAY)
    parser.add_argument("--hard-period", type=int, default=DEFAULT_HARD_PERIOD)
    parser.add_argument("--noise-prob", type=float, default=DEFAULT_HARD_NOISE_PROB)
    parser.add_argument("--sensory-noise-fraction", type=float, default=DEFAULT_HARD_SENSORY_NOISE_FRACTION)
    parser.add_argument("--runtime-mode", choices=RUNTIME_MODES, default="step")
    parser.add_argument("--learning-location", choices=LEARNING_LOCATIONS, default="host")
    parser.add_argument("--chunk-size-steps", type=int, default=1)
    parser.add_argument("--min-switch-interval", type=int, default=DEFAULT_HARD_MIN_SWITCH_INTERVAL)
    parser.add_argument("--max-switch-interval", type=int, default=DEFAULT_HARD_MAX_SWITCH_INTERVAL)
    parser.add_argument("--spinnaker-hostname", default=None)
    parser.add_argument("--require-real-hardware", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--stop-on-backend-fallback", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--stop-on-fail", action="store_true")
    parser.add_argument("--ingest-dir", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.steps <= 0:
        parser.error("--steps must be positive")
    if args.population_size <= 0:
        parser.error("--population-size must be positive")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = "prepared" if args.mode == "prepare" else args.mode.replace("-", "_")
    output_dir = args.output_dir or (ROOT / "controlled_test_output" / f"tier4_16_{timestamp}_{suffix}")
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.mode == "prepare":
        return prepare_capsule(args, output_dir)
    if args.mode == "run-hardware":
        return run_hardware(args, output_dir)
    if args.mode == "ingest":
        return ingest_results(args, output_dir)
    raise AssertionError(args.mode)


if __name__ == "__main__":
    raise SystemExit(main())
