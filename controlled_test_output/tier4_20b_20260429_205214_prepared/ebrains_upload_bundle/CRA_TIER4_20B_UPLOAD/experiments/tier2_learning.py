#!/usr/bin/env python3
"""Run Tier 2 controlled learning-proof tests for the CRA organism.

Tier 2 asks for positive evidence:

4. Fixed-pattern task: learn a causal next-symbol mapping.
5. Delayed reward task: assign credit to cue-time predictions after a delay.
6. Nonstationary switch task: adapt after the rule changes.

The harness stops on first failure when ``--stop-on-fail`` is used and writes a
CSV/JSON/Markdown/PNG evidence bundle like the Tier 1 harness.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import sys
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
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

from coral_reef_spinnaker import MockSimulator, Organism, ReefConfig


EPS = 1e-12
DEFAULT_AMPLITUDE = 0.01
DEFAULT_STEPS = 180
DEFAULT_DT_SECONDS = 0.05
DEFAULT_MAX_POLYPS = 8


@dataclass
class TestResult:
    name: str
    status: str
    summary: dict[str, Any]
    criteria: list[dict[str, Any]]
    artifacts: dict[str, str]
    failure_reason: str = ""

    @property
    def passed(self) -> bool:
        return self.status == "pass"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "summary": self.summary,
            "criteria": self.criteria,
            "artifacts": self.artifacts,
            "failure_reason": self.failure_reason,
        }


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def strict_sign(value: float, eps: float = EPS) -> int:
    if value > eps:
        return 1
    if value < -eps:
        return -1
    return 0


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        f = float(value)
        return None if math.isnan(f) or math.isinf(f) else f
    if isinstance(value, np.ndarray):
        return [json_safe(v) for v in value.tolist()]
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(json_safe(payload), indent=2, sort_keys=True),
        encoding="utf-8",
    )


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
            writer.writerow({k: json_safe(v) for k, v in row.items()})


def criterion(
    name: str,
    value: Any,
    op: str,
    threshold: Any,
    passed: bool,
    note: str = "",
) -> dict[str, Any]:
    return {
        "name": name,
        "value": value,
        "operator": op,
        "threshold": threshold,
        "passed": bool(passed),
        "note": note,
    }


def pass_fail(criteria: list[dict[str, Any]]) -> tuple[str, str]:
    failed = [c for c in criteria if not c["passed"]]
    if not failed:
        return "pass", ""
    return "fail", "Failed criteria: " + ", ".join(c["name"] for c in failed)


def safe_corr(x_values: list[float], y_values: list[float]) -> float | None:
    x = np.asarray(x_values, dtype=float)
    y = np.asarray(y_values, dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    x = x[mask]
    y = y[mask]
    if x.size < 3 or y.size < 3:
        return None
    if float(np.std(x)) <= EPS or float(np.std(y)) <= EPS:
        return None
    return float(np.corrcoef(x, y)[0, 1])


def markdown_value(value: Any) -> str:
    if value is None:
        return "None"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def load_backend(name: str):
    if name == "mock":
        return MockSimulator, "MockSimulator"
    if name == "nest":
        import pyNN.nest as sim

        return sim, "NEST"
    if name == "brian2":
        import pyNN.brian2 as sim

        return sim, "Brian2"
    raise ValueError(f"Unsupported backend: {name}")


def setup_backend(sim, backend_name: str) -> None:
    if backend_name == "Brian2":
        configure_brian2_compatibility()
    try:
        sim.end()
    except Exception:
        pass
    if backend_name == "MockSimulator":
        sim.setup(timestep=1.0)
    else:
        sim.setup(timestep=1.0)


def configure_brian2_compatibility() -> None:
    """Use Brian2's pure-Python runtime path when binary extensions mismatch.

    Some local Python environments have Brian2's optional Cython spike queue
    compiled against a different NumPy ABI. Brian2 only catches ImportError for
    that optional extension, but the ABI mismatch raises ValueError. Backend
    parity should test CRA behavior, not fail on an optional acceleration path,
    so we force NumPy codegen and make the spike queue fallback catch any
    extension-loading failure.
    """
    try:
        import brian2
        from brian2.devices.device import RuntimeDevice
        from brian2.synapses.spikequeue import SpikeQueue as PythonSpikeQueue
        from pyNN.brian2.standardmodels import cells as brian2_cells
        from pyNN.brian2.standardmodels import receptors as brian2_receptors
    except Exception:
        return

    try:
        brian2.prefs.codegen.target = "numpy"
    except Exception:
        pass

    try:
        # PyNN 0.12.4 + Brian2 2.6.0 can emit an ``int(not_refractory)``
        # expression that Brian2's NumPy renderer rejects as unsupported Call
        # syntax. CRA does not depend on refractory-period fidelity for these
        # controlled parity tasks, so use the same current-based LIF equation
        # without Brian2's refractory multiplier.
        brian2_cells.leaky_iaf = brian2.Equations(
            """
            dv/dt = (v_rest-v)/tau_m + (i_syn + i_offset + i_inj)/c_m : volt
            tau_m                   : second
            c_m                     : farad
            v_rest                  : volt
            i_offset                : amp
            i_inj                   : amp
            """
        )
        brian2_cells.IF_curr_exp.eqs = (
            brian2_cells.leaky_iaf
            + brian2_receptors.current_based_exponential_synapses
        )
    except Exception:
        pass

    if getattr(RuntimeDevice, "_cra_spike_queue_fallback", False):
        return

    def spike_queue(self, source_start, source_end):
        try:
            from brian2.synapses.cythonspikequeue import SpikeQueue
        except Exception:
            SpikeQueue = PythonSpikeQueue
        return SpikeQueue(source_start=source_start, source_end=source_end)

    RuntimeDevice.spike_queue = spike_queue
    RuntimeDevice._cra_spike_queue_fallback = True


def end_backend(sim) -> None:
    try:
        sim.end()
    except Exception:
        pass


def make_config(
    *,
    seed: int,
    steps: int,
    max_polyps: int,
    horizon: int,
    readout_lr: float,
    delayed_readout_lr: float,
    fixed_population: bool,
) -> ReefConfig:
    cfg = ReefConfig.default()
    cfg.seed = int(seed)
    cfg.lifecycle.max_population_from_memory = False
    cfg.lifecycle.max_population_hard = int(max_polyps)
    cfg.lifecycle.enable_reproduction = not fixed_population
    if fixed_population:
        cfg.lifecycle.enable_apoptosis = False
    cfg.measurement.stream_history_maxlen = max(steps + 16, 128)
    cfg.spinnaker.sync_interval_steps = 0
    cfg.spinnaker.runtime_ms_per_step = 1000.0
    cfg.learning.evaluation_horizon_bars = int(horizon)
    cfg.learning.readout_learning_rate = float(readout_lr)
    cfg.learning.delayed_readout_learning_rate = float(delayed_readout_lr)
    return cfg


def alive_readout_weights(organism: Organism) -> list[float]:
    if organism.polyp_population is None:
        return []
    return [
        float(getattr(p, "predictive_readout_weight", 0.0))
        for p in organism.polyp_population.states
        if getattr(p, "is_alive", False)
    ]


def run_organism_case(
    *,
    name: str,
    seed: int,
    sensory: np.ndarray,
    target: np.ndarray,
    evaluation_target: np.ndarray,
    evaluation_mask: np.ndarray,
    horizon: int,
    args: argparse.Namespace,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not (
        sensory.shape == target.shape == evaluation_target.shape == evaluation_mask.shape
    ):
        raise ValueError("sensory, target, evaluation_target, and mask shapes must match")

    random.seed(seed)
    np.random.seed(seed)
    sim, backend_name = load_backend(args.backend)
    setup_backend(sim, backend_name)

    cfg = make_config(
        seed=seed,
        steps=int(target.size),
        max_polyps=args.max_polyps,
        horizon=horizon,
        readout_lr=args.readout_lr,
        delayed_readout_lr=args.delayed_readout_lr,
        fixed_population=args.fixed_population,
    )
    organism = Organism(cfg, sim)
    rows: list[dict[str, Any]] = []
    task_window: deque[float] = deque(maxlen=horizon)
    started = time.perf_counter()

    try:
        organism.initialize(stream_keys=["controlled"])
        for step, (sensory_value, target_value, eval_value, eval_enabled) in enumerate(
            zip(sensory, target, evaluation_target, evaluation_mask)
        ):
            task_window.append(float(target_value))
            task_signal = float(np.sum(list(task_window)))

            metrics = organism.train_step(
                market_return_1m=float(target_value),
                dt_seconds=args.dt_seconds,
                sensory_return_1m=float(sensory_value),
            )

            prediction = float(metrics.colony_prediction)
            eval_sign = strict_sign(float(eval_value))
            pred_sign = strict_sign(prediction)
            weights = alive_readout_weights(organism)
            learning_status = (
                organism.learning_manager.get_summary()
                if organism.learning_manager is not None
                else {}
            )
            row = metrics.to_dict()
            row.update(
                {
                    "test_name": name,
                    "backend": backend_name,
                    "seed": seed,
                    "step": step,
                    "sensory_return_1m": float(sensory_value),
                    "target_return_1m": float(target_value),
                    "task_signal_horizon": task_signal,
                    "target_signal_horizon": float(eval_value),
                    "target_signal_sign": eval_sign,
                    "target_signal_nonzero": bool(eval_enabled and eval_sign != 0),
                    "prediction_sign": pred_sign,
                    "strict_direction_correct": bool(
                        eval_enabled and pred_sign != 0 and pred_sign == eval_sign
                    ),
                    "mean_readout_weight": float(np.mean(weights)) if weights else 0.0,
                    "min_readout_weight": float(np.min(weights)) if weights else 0.0,
                    "max_readout_weight": float(np.max(weights)) if weights else 0.0,
                    "mean_abs_readout_weight": float(np.mean(np.abs(weights)))
                    if weights
                    else 0.0,
                    "pending_horizons": int(learning_status.get("pending_horizons", 0)),
                    "matured_horizons": int(learning_status.get("matured_horizons", 0)),
                }
            )
            rows.append(row)
    finally:
        organism.shutdown()
        end_backend(sim)

    return rows, {
        "backend": backend_name,
        "seed": seed,
        "steps": int(target.size),
        "runtime_seconds": time.perf_counter() - started,
        "horizon": horizon,
        "config": cfg.to_dict(),
    }


def window_accuracy(rows: list[dict[str, Any]], start: int, end: int) -> float | None:
    window = [
        r
        for r in rows[max(0, start) : min(len(rows), end)]
        if bool(r.get("target_signal_nonzero", False))
    ]
    if not window:
        return None
    return float(np.mean([bool(r["strict_direction_correct"]) for r in window]))


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {}

    steps = len(rows)
    eval_rows = [r for r in rows if bool(r.get("target_signal_nonzero", False))]
    tail_start = int(steps * 0.75)
    tail_rows = [
        r
        for r in rows[tail_start:]
        if bool(r.get("target_signal_nonzero", False))
    ]
    early_rows = [
        r
        for r in rows[: max(1, int(steps * 0.20))]
        if bool(r.get("target_signal_nonzero", False))
    ]

    def arr(key: str, source: list[dict[str, Any]] = rows) -> np.ndarray:
        return np.asarray([float(r.get(key, 0.0)) for r in source], dtype=float)

    def accuracy(source: list[dict[str, Any]]) -> float | None:
        if not source:
            return None
        return float(np.mean([bool(r["strict_direction_correct"]) for r in source]))

    pred_eval = [float(r["colony_prediction"]) for r in eval_rows]
    target_eval = [float(r["target_signal_horizon"]) for r in eval_rows]
    pred_tail = [float(r["colony_prediction"]) for r in tail_rows]
    target_tail = [float(r["target_signal_horizon"]) for r in tail_rows]

    return {
        "steps": steps,
        "evaluation_count": len(eval_rows),
        "early_accuracy": accuracy(early_rows),
        "tail_accuracy": accuracy(tail_rows),
        "all_accuracy": accuracy(eval_rows),
        "accuracy_improvement": (
            None
            if accuracy(early_rows) is None or accuracy(tail_rows) is None
            else accuracy(tail_rows) - accuracy(early_rows)
        ),
        "prediction_target_corr": safe_corr(pred_eval, target_eval),
        "tail_prediction_target_corr": safe_corr(pred_tail, target_tail),
        "final_capital": float(arr("capital")[-1]),
        "capital_delta": float(arr("capital")[-1] - arr("capital")[0]),
        "max_abs_dopamine": float(np.max(np.abs(arr("raw_dopamine")))),
        "mean_abs_dopamine": float(np.mean(np.abs(arr("raw_dopamine")))),
        "final_accuracy_ema": float(arr("mean_directional_accuracy_ema")[-1]),
        "tail_accuracy_ema": float(
            np.mean(arr("mean_directional_accuracy_ema", rows[tail_start:]))
        ),
        "final_n_alive": int(arr("n_alive")[-1]),
        "max_n_alive": int(np.max(arr("n_alive"))),
        "total_births": int(np.sum(arr("births_this_step"))),
        "total_deaths": int(np.sum(arr("deaths_this_step"))),
        "final_mean_readout_weight": float(arr("mean_readout_weight")[-1]),
        "final_mean_abs_readout_weight": float(arr("mean_abs_readout_weight")[-1]),
        "final_matured_horizons": int(arr("matured_horizons")[-1]),
        "max_matured_horizons": int(np.max(arr("matured_horizons"))),
    }


def plot_case(rows: list[dict[str, Any]], path: Path, title: str, switch_step: int | None = None) -> None:
    if plt is None:
        return
    steps = np.asarray([int(r["step"]) for r in rows], dtype=int)

    def values(key: str) -> np.ndarray:
        return np.asarray([float(r.get(key, 0.0)) for r in rows], dtype=float)

    fig, axes = plt.subplots(5, 1, figsize=(12, 12), sharex=True)
    fig.suptitle(title, fontsize=14, fontweight="bold")

    axes[0].plot(steps, values("sensory_return_1m"), label="sensory cue", lw=1.2)
    axes[0].plot(steps, values("target_return_1m"), label="current reward/target", lw=1.0, alpha=0.8)
    axes[0].set_ylabel("signal")
    axes[0].legend(loc="upper right")
    axes[0].grid(alpha=0.2)

    axes[1].plot(steps, values("colony_prediction"), label="prediction", lw=1.2)
    axes[1].plot(steps, values("target_signal_horizon"), label="evaluation target", lw=1.0, alpha=0.85)
    axes[1].axhline(0.0, color="black", lw=0.8, alpha=0.5)
    axes[1].set_ylabel("prediction")
    axes[1].legend(loc="upper right")
    axes[1].grid(alpha=0.2)

    axes[2].plot(steps, values("raw_dopamine"), label="raw dopamine", color="#c23b22", lw=1.0)
    axes[2].axhline(0.0, color="black", lw=0.8, alpha=0.5)
    axes[2].set_ylabel("dopamine")
    axes[2].legend(loc="upper right")
    axes[2].grid(alpha=0.2)

    axes[3].plot(steps, values("mean_readout_weight"), label="mean readout weight", color="#2f855a", lw=1.2)
    axes[3].axhline(0.0, color="black", lw=0.8, alpha=0.5)
    axes[3].set_ylabel("weight")
    axes[3].legend(loc="upper right")
    axes[3].grid(alpha=0.2)

    axes[4].plot(steps, values("mean_directional_accuracy_ema"), label="accuracy EMA", color="#2b6cb0", lw=1.1)
    axes[4].plot(steps, values("matured_horizons") / max(1.0, np.max(values("matured_horizons"))), label="matured horizons scaled", color="#805ad5", lw=1.0)
    axes[4].set_ylabel("summary")
    axes[4].set_xlabel("step")
    axes[4].legend(loc="upper right")
    axes[4].grid(alpha=0.2)

    if switch_step is not None:
        for ax in axes:
            ax.axvline(switch_step, color="#d69e2e", lw=1.0, linestyle="--", alpha=0.8)

    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(path, dpi=160)
    plt.close(fig)


def alternating_signs(steps: int) -> np.ndarray:
    return np.asarray([1.0 if i % 2 == 0 else -1.0 for i in range(steps)])


def fixed_pattern_task(steps: int, amplitude: float) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    signs = alternating_signs(steps)
    target = amplitude * signs
    sensory = np.concatenate([[0.0], target[:-1]])
    evaluation_target = target.copy()
    evaluation_mask = np.ones(steps, dtype=bool)
    evaluation_mask[0] = False
    return sensory, target, evaluation_target, evaluation_mask


def delayed_reward_task(
    *,
    steps: int,
    amplitude: float,
    delay: int,
    period: int,
    seed: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    sensory = np.zeros(steps, dtype=float)
    target = np.zeros(steps, dtype=float)
    evaluation_target = np.zeros(steps, dtype=float)
    evaluation_mask = np.zeros(steps, dtype=bool)

    trial_starts = list(range(0, steps - delay, period))
    signs = np.array([1.0, -1.0] * ((len(trial_starts) + 1) // 2))[: len(trial_starts)]
    rng.shuffle(signs)

    for start, cue_sign in zip(trial_starts, signs):
        reward_sign = -cue_sign
        sensory[start] = amplitude * cue_sign
        target[start + delay] = amplitude * reward_sign
        evaluation_target[start] = amplitude * reward_sign
        evaluation_mask[start] = True

    return sensory, target, evaluation_target, evaluation_mask


def nonstationary_switch_task(steps: int, amplitude: float) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, int]:
    signs = alternating_signs(steps)
    sensory = amplitude * signs
    switch_step = steps // 2
    target = sensory.copy()
    target[switch_step:] *= -1.0
    evaluation_target = target.copy()
    evaluation_mask = np.ones(steps, dtype=bool)
    return sensory, target, evaluation_target, evaluation_mask, switch_step


def run_fixed_pattern(args: argparse.Namespace, output_dir: Path) -> TestResult:
    sensory, target, evaluation_target, evaluation_mask = fixed_pattern_task(
        args.steps,
        args.amplitude,
    )
    rows, metadata = run_organism_case(
        name="fixed_pattern",
        seed=args.base_seed,
        sensory=sensory,
        target=target,
        evaluation_target=evaluation_target,
        evaluation_mask=evaluation_mask,
        horizon=1,
        args=args,
    )
    csv_path = output_dir / "fixed_pattern_timeseries.csv"
    plot_path = output_dir / "fixed_pattern_timeseries.png"
    write_csv(csv_path, rows)
    plot_case(rows, plot_path, "Tier 2.4 Fixed-Pattern Causal Task")

    summary = summarize_rows(rows)
    summary.update(metadata)
    tail_corr = summary["tail_prediction_target_corr"]
    criteria = [
        criterion(
            "tail strict accuracy",
            summary["tail_accuracy"],
            ">=",
            args.fixed_tail_accuracy_threshold,
            summary["tail_accuracy"] is not None
            and summary["tail_accuracy"] >= args.fixed_tail_accuracy_threshold,
        ),
        criterion(
            "tail prediction/target correlation",
            tail_corr,
            ">=",
            args.fixed_corr_threshold,
            tail_corr is not None and tail_corr >= args.fixed_corr_threshold,
        ),
        criterion(
            "learned inverse readout weight",
            summary["final_mean_readout_weight"],
            "<=",
            -0.05,
            summary["final_mean_readout_weight"] <= -0.05,
            "Previous symbol predicts the opposite next symbol.",
        ),
    ]
    status, failure_reason = pass_fail(criteria)
    return TestResult(
        name="fixed_pattern",
        status=status,
        summary=summary,
        criteria=criteria,
        artifacts={
            "timeseries_csv": str(csv_path),
            "plot_png": str(plot_path) if plot_path.exists() else "",
        },
        failure_reason=failure_reason,
    )


def run_delayed_reward(args: argparse.Namespace, output_dir: Path) -> TestResult:
    period = max(args.delay + 2, args.delayed_period)
    sensory, target, evaluation_target, evaluation_mask = delayed_reward_task(
        steps=args.steps,
        amplitude=args.amplitude,
        delay=args.delay,
        period=period,
        seed=args.base_seed,
    )
    rows, metadata = run_organism_case(
        name="delayed_reward",
        seed=args.base_seed,
        sensory=sensory,
        target=target,
        evaluation_target=evaluation_target,
        evaluation_mask=evaluation_mask,
        horizon=args.delay,
        args=args,
    )
    csv_path = output_dir / "delayed_reward_timeseries.csv"
    plot_path = output_dir / "delayed_reward_timeseries.png"
    write_csv(csv_path, rows)
    plot_case(rows, plot_path, "Tier 2.5 Delayed Reward Task")

    summary = summarize_rows(rows)
    summary.update(metadata)
    summary["delay"] = args.delay
    summary["trial_period"] = period
    tail_corr = summary["tail_prediction_target_corr"]
    criteria = [
        criterion(
            "tail cue-time strict accuracy",
            summary["tail_accuracy"],
            ">=",
            args.delayed_tail_accuracy_threshold,
            summary["tail_accuracy"] is not None
            and summary["tail_accuracy"] >= args.delayed_tail_accuracy_threshold,
        ),
        criterion(
            "matured delayed horizons",
            summary["final_matured_horizons"],
            ">=",
            1,
            summary["final_matured_horizons"] >= 1,
        ),
        criterion(
            "delayed inverse readout weight",
            summary["final_mean_readout_weight"],
            "<=",
            -0.05,
            summary["final_mean_readout_weight"] <= -0.05,
        ),
        criterion(
            "tail prediction/target correlation",
            tail_corr,
            ">=",
            args.delayed_corr_threshold,
            tail_corr is not None and tail_corr >= args.delayed_corr_threshold,
        ),
    ]
    status, failure_reason = pass_fail(criteria)
    return TestResult(
        name="delayed_reward",
        status=status,
        summary=summary,
        criteria=criteria,
        artifacts={
            "timeseries_csv": str(csv_path),
            "plot_png": str(plot_path) if plot_path.exists() else "",
        },
        failure_reason=failure_reason,
    )


def first_recovery_step(
    rows: list[dict[str, Any]],
    *,
    switch_step: int,
    window: int,
    threshold: float,
) -> int | None:
    for start in range(switch_step, len(rows) - window + 1):
        acc = window_accuracy(rows, start, start + window)
        if acc is not None and acc >= threshold:
            return start - switch_step
    return None


def run_nonstationary_switch(args: argparse.Namespace, output_dir: Path) -> TestResult:
    sensory, target, evaluation_target, evaluation_mask, switch_step = nonstationary_switch_task(
        args.steps,
        args.amplitude,
    )
    rows, metadata = run_organism_case(
        name="nonstationary_switch",
        seed=args.base_seed,
        sensory=sensory,
        target=target,
        evaluation_target=evaluation_target,
        evaluation_mask=evaluation_mask,
        horizon=1,
        args=args,
    )
    csv_path = output_dir / "nonstationary_switch_timeseries.csv"
    plot_path = output_dir / "nonstationary_switch_timeseries.png"
    write_csv(csv_path, rows)
    plot_case(
        rows,
        plot_path,
        "Tier 2.6 Nonstationary Switch Task",
        switch_step=switch_step,
    )

    pre_acc = window_accuracy(
        rows,
        max(0, switch_step - args.switch_eval_window),
        switch_step,
    )
    immediate_post_acc = window_accuracy(
        rows,
        switch_step,
        min(len(rows), switch_step + args.switch_eval_window),
    )
    final_post_acc = window_accuracy(
        rows,
        max(switch_step, len(rows) - args.switch_eval_window),
        len(rows),
    )
    recovery = first_recovery_step(
        rows,
        switch_step=switch_step,
        window=args.switch_recovery_window,
        threshold=args.switch_recovery_accuracy_threshold,
    )

    summary = summarize_rows(rows)
    summary.update(metadata)
    summary.update(
        {
            "switch_step": switch_step,
            "pre_switch_accuracy": pre_acc,
            "immediate_post_switch_accuracy": immediate_post_acc,
            "final_post_switch_accuracy": final_post_acc,
            "recovery_steps": recovery,
        }
    )

    criteria = [
        criterion(
            "pre-switch accuracy",
            pre_acc,
            ">=",
            args.switch_pre_accuracy_threshold,
            pre_acc is not None and pre_acc >= args.switch_pre_accuracy_threshold,
        ),
        criterion(
            "post-switch disruption",
            immediate_post_acc,
            "<=",
            args.switch_disruption_threshold,
            immediate_post_acc is not None
            and immediate_post_acc <= args.switch_disruption_threshold,
        ),
        criterion(
            "final post-switch accuracy",
            final_post_acc,
            ">=",
            args.switch_final_accuracy_threshold,
            final_post_acc is not None
            and final_post_acc >= args.switch_final_accuracy_threshold,
        ),
        criterion(
            "recovery time",
            recovery,
            "<=",
            args.switch_max_recovery_steps,
            recovery is not None and recovery <= args.switch_max_recovery_steps,
        ),
        criterion(
            "final inverse readout weight",
            summary["final_mean_readout_weight"],
            "<=",
            0.0,
            summary["final_mean_readout_weight"] <= 0.0,
        ),
    ]
    status, failure_reason = pass_fail(criteria)
    return TestResult(
        name="nonstationary_switch",
        status=status,
        summary=summary,
        criteria=criteria,
        artifacts={
            "timeseries_csv": str(csv_path),
            "plot_png": str(plot_path) if plot_path.exists() else "",
        },
        failure_reason=failure_reason,
    )


def summary_rows(results: list[TestResult]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for result in results:
        row = {
            "test_name": result.name,
            "status": result.status,
            "failure_reason": result.failure_reason,
        }
        row.update(result.summary)
        rows.append(row)
    return rows


def write_report(
    *,
    path: Path,
    results: list[TestResult],
    manifest_path: Path,
    summary_csv_path: Path,
    output_dir: Path,
    stopped_after: str | None,
    args: argparse.Namespace,
) -> None:
    overall = "PASS" if results and all(r.passed for r in results) else "FAIL"
    if stopped_after:
        overall = "STOPPED"

    lines = [
        "# Tier 2 Controlled Learning Findings",
        "",
        f"- Generated: `{utc_now()}`",
        f"- Backend: `{args.backend}`",
        f"- Overall status: **{overall}**",
        f"- Steps per run: `{args.steps}`",
        f"- Base seed: `{args.base_seed}`",
        f"- Fixed population: `{args.fixed_population}`",
        f"- Output directory: `{output_dir}`",
        "",
        "Tier 2 is a positive-control tier. These tests check whether the organism can learn causal cue/outcome structure, delayed consequence, and a switched rule after Tier 1 ruled out obvious fake learning.",
        "",
        "## Artifact Index",
        "",
        f"- JSON manifest: `{manifest_path.name}`",
        f"- Summary CSV: `{summary_csv_path.name}`",
    ]
    if MATPLOTLIB_ERROR:
        lines.append(f"- Plotting unavailable: `{MATPLOTLIB_ERROR}`")
    lines.extend(
        [
            "",
            "## Summary",
            "",
            "| Test | Status | Key metric | Notes |",
            "| --- | --- | --- | --- |",
        ]
    )

    for result in results:
        if result.name == "fixed_pattern":
            key = (
                f"tail_acc={markdown_value(result.summary.get('tail_accuracy'))}, "
                f"weight={markdown_value(result.summary.get('final_mean_readout_weight'))}"
            )
        elif result.name == "delayed_reward":
            key = (
                f"tail_cue_acc={markdown_value(result.summary.get('tail_accuracy'))}, "
                f"matured={markdown_value(result.summary.get('final_matured_horizons'))}"
            )
        elif result.name == "nonstationary_switch":
            key = (
                f"pre={markdown_value(result.summary.get('pre_switch_accuracy'))}, "
                f"post_final={markdown_value(result.summary.get('final_post_switch_accuracy'))}, "
                f"recovery={markdown_value(result.summary.get('recovery_steps'))}"
            )
        else:
            key = ""
        lines.append(
            f"| `{result.name}` | **{result.status.upper()}** | {key} | {result.failure_reason or 'criteria satisfied'} |"
        )
    lines.append("")

    for result in results:
        lines.extend(
            [
                f"## {result.name}",
                "",
                f"Status: **{result.status.upper()}**",
                "",
                "Criteria:",
                "",
                "| Criterion | Value | Rule | Pass |",
                "| --- | ---: | --- | --- |",
            ]
        )
        for item in result.criteria:
            lines.append(
                "| "
                f"{item['name']} | "
                f"{markdown_value(item['value'])} | "
                f"{item['operator']} {markdown_value(item['threshold'])} | "
                f"{'yes' if item['passed'] else 'no'} |"
            )
        lines.append("")
        lines.append("Artifacts:")
        lines.append("")
        for label, artifact in result.artifacts.items():
            if artifact:
                artifact_path = Path(artifact)
                lines.append(f"- `{label}`: `{artifact_path.name}`")
                if artifact_path.suffix.lower() == ".png":
                    lines.append("")
                    lines.append(f"![{result.name} plot]({artifact_path.name})")
                    lines.append("")
        lines.append("")

    if stopped_after:
        lines.extend(
            [
                "## Stop Condition",
                "",
                f"Execution stopped after `{stopped_after}` because `--stop-on-fail` was enabled.",
                "",
            ]
        )

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def resolve_tests(selected: list[str]) -> list[str]:
    order = ["fixed_pattern", "delayed_reward", "nonstationary_switch"]
    aliases = {
        "all": "all",
        "fixed": "fixed_pattern",
        "fixed_pattern": "fixed_pattern",
        "delayed": "delayed_reward",
        "delayed_reward": "delayed_reward",
        "switch": "nonstationary_switch",
        "nonstationary": "nonstationary_switch",
        "nonstationary_switch": "nonstationary_switch",
    }
    normalized = [aliases[item] for item in selected]
    if "all" in normalized:
        return order
    wanted = set(normalized)
    return [name for name in order if name in wanted]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run Tier 2 CRA learning-proof controls and export findings.",
    )
    parser.add_argument(
        "--tests",
        nargs="+",
        default=["all"],
        choices=[
            "all",
            "fixed",
            "fixed_pattern",
            "delayed",
            "delayed_reward",
            "switch",
            "nonstationary",
            "nonstationary_switch",
        ],
    )
    parser.add_argument("--backend", choices=["nest", "brian2", "mock"], default="nest")
    parser.add_argument("--steps", type=int, default=DEFAULT_STEPS)
    parser.add_argument("--base-seed", type=int, default=42)
    parser.add_argument("--amplitude", type=float, default=DEFAULT_AMPLITUDE)
    parser.add_argument("--max-polyps", type=int, default=DEFAULT_MAX_POLYPS)
    parser.add_argument("--dt-seconds", type=float, default=DEFAULT_DT_SECONDS)
    parser.add_argument("--readout-lr", type=float, default=0.10)
    parser.add_argument("--delayed-readout-lr", type=float, default=0.05)
    parser.add_argument("--fixed-population", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--stop-on-fail", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=None)

    parser.add_argument("--delay", type=int, default=5)
    parser.add_argument("--delayed-period", type=int, default=8)

    parser.add_argument("--fixed-tail-accuracy-threshold", type=float, default=0.80)
    parser.add_argument("--fixed-corr-threshold", type=float, default=0.70)
    parser.add_argument("--delayed-tail-accuracy-threshold", type=float, default=0.65)
    parser.add_argument("--delayed-corr-threshold", type=float, default=0.50)
    parser.add_argument("--switch-eval-window", type=int, default=24)
    parser.add_argument("--switch-recovery-window", type=int, default=12)
    parser.add_argument("--switch-recovery-accuracy-threshold", type=float, default=0.70)
    parser.add_argument("--switch-pre-accuracy-threshold", type=float, default=0.80)
    parser.add_argument("--switch-disruption-threshold", type=float, default=0.90)
    parser.add_argument("--switch-final-accuracy-threshold", type=float, default=0.80)
    parser.add_argument("--switch-max-recovery-steps", type=int, default=60)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.steps <= 0:
        parser.error("--steps must be positive")
    if args.delay <= 0:
        parser.error("--delay must be positive")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = args.output_dir or (ROOT / "controlled_test_output" / f"tier2_{timestamp}")
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    selected_tests = resolve_tests(args.tests)
    runners = {
        "fixed_pattern": run_fixed_pattern,
        "delayed_reward": run_delayed_reward,
        "nonstationary_switch": run_nonstationary_switch,
    }
    results: list[TestResult] = []
    stopped_after: str | None = None

    for test_name in selected_tests:
        print(f"[tier2] running {test_name} on {args.backend}...", flush=True)
        result = runners[test_name](args, output_dir)
        results.append(result)
        print(
            f"[tier2] {test_name}: {result.status.upper()}",
            result.failure_reason,
            flush=True,
        )
        if args.stop_on_fail and not result.passed:
            stopped_after = test_name
            break

    summary_csv_path = output_dir / "tier2_summary.csv"
    manifest_path = output_dir / "tier2_results.json"
    report_path = output_dir / "tier2_report.md"
    write_csv(summary_csv_path, summary_rows(results))

    manifest = {
        "generated_at_utc": utc_now(),
        "tier": "Tier 2 - learning proof tests",
        "backend": args.backend,
        "command": " ".join(sys.argv),
        "output_dir": str(output_dir),
        "selected_tests": selected_tests,
        "stopped_after": stopped_after,
        "thresholds": {
            "fixed_tail_accuracy_threshold": args.fixed_tail_accuracy_threshold,
            "fixed_corr_threshold": args.fixed_corr_threshold,
            "delayed_tail_accuracy_threshold": args.delayed_tail_accuracy_threshold,
            "delayed_corr_threshold": args.delayed_corr_threshold,
            "switch_pre_accuracy_threshold": args.switch_pre_accuracy_threshold,
            "switch_disruption_threshold": args.switch_disruption_threshold,
            "switch_final_accuracy_threshold": args.switch_final_accuracy_threshold,
            "switch_max_recovery_steps": args.switch_max_recovery_steps,
        },
        "results": [r.to_dict() for r in results],
        "artifacts": {
            "summary_csv": str(summary_csv_path),
            "report_md": str(report_path),
        },
    }
    write_json(manifest_path, manifest)
    write_report(
        path=report_path,
        results=results,
        manifest_path=manifest_path,
        summary_csv_path=summary_csv_path,
        output_dir=output_dir,
        stopped_after=stopped_after,
        args=args,
    )

    latest_path = ROOT / "controlled_test_output" / "tier2_latest_manifest.json"
    write_json(
        latest_path,
        {
            "generated_at_utc": utc_now(),
            "manifest": str(manifest_path),
            "report": str(report_path),
            "status": "pass" if results and all(r.passed for r in results) else "fail",
            "stopped_after": stopped_after,
        },
    )

    if stopped_after:
        return 1
    return 0 if results and all(r.passed for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
