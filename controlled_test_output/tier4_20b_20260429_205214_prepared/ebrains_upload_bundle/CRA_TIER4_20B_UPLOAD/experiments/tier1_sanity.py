#!/usr/bin/env python3
"""Run Tier 1 controlled sanity tests for the CRA organism.

Tier 1 is intentionally falsification-oriented:

1. Zero-signal test: no usable input and no target.
2. Shuffled-label test: input sequence is decoupled from target labels.
3. Random-seed repeat: repeat the shuffled-label control across many seeds.

The script writes a complete evidence bundle:

- per-step CSV files
- per-seed summary CSV
- tier summary CSV
- JSON manifest
- Markdown findings report
- PNG plots when matplotlib is available
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
from typing import Any, Iterable

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
DEFAULT_AMPLITUDE = 0.002
DEFAULT_MAX_POLYPS = 16
DEFAULT_STEPS = 200
DEFAULT_SEEDS = 20
DEFAULT_DT_SECONDS = 1.0
WARMUP_FRACTION = 0.25


@dataclass
class TestResult:
    """Compact result for a Tier 1 test."""

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
    """Convert numpy/path objects into JSON-safe values."""
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


def safe_corr(x_values: Iterable[float], y_values: Iterable[float]) -> float | None:
    x = np.asarray(list(x_values), dtype=float)
    y = np.asarray(list(y_values), dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    x = x[mask]
    y = y[mask]
    if x.size < 3 or y.size < 3:
        return None
    if float(np.std(x)) <= EPS or float(np.std(y)) <= EPS:
        return None
    return float(np.corrcoef(x, y)[0, 1])


def make_config(
    seed: int,
    steps: int,
    max_polyps: int,
    *,
    readout_lr: float = 0.10,
    delayed_readout_lr: float = 0.05,
) -> ReefConfig:
    cfg = ReefConfig.default()
    cfg.seed = int(seed)
    cfg.lifecycle.max_population_from_memory = False
    cfg.lifecycle.max_population_hard = int(max_polyps)
    cfg.measurement.stream_history_maxlen = max(steps + 16, 128)
    cfg.spinnaker.sync_interval_steps = 0
    cfg.spinnaker.runtime_ms_per_step = 1000.0
    cfg.learning.evaluation_horizon_bars = 5
    cfg.learning.readout_learning_rate = float(readout_lr)
    cfg.learning.delayed_readout_learning_rate = float(delayed_readout_lr)
    return cfg


def run_organism_case(
    *,
    name: str,
    seed: int,
    sensory: np.ndarray,
    target: np.ndarray,
    max_polyps: int,
    dt_seconds: float,
    readout_lr: float = 0.10,
    delayed_readout_lr: float = 0.05,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Run one controlled input/target sequence through the organism."""
    if sensory.shape != target.shape:
        raise ValueError("sensory and target arrays must have the same shape")

    random.seed(seed)
    np.random.seed(seed)
    MockSimulator.end()
    MockSimulator.setup(timestep=1.0)

    cfg = make_config(
        seed=seed,
        steps=int(target.size),
        max_polyps=max_polyps,
        readout_lr=readout_lr,
        delayed_readout_lr=delayed_readout_lr,
    )
    organism = Organism(cfg, MockSimulator)
    rows: list[dict[str, Any]] = []
    target_window: deque[float] = deque(maxlen=cfg.learning.evaluation_horizon_bars)
    started = time.perf_counter()

    try:
        organism.initialize(stream_keys=["controlled"])
        for step, (sensory_value, target_value) in enumerate(zip(sensory, target)):
            target_window.append(float(target_value))
            target_signal = float(np.sum(list(target_window)))

            metrics = organism.train_step(
                market_return_1m=float(target_value),
                dt_seconds=dt_seconds,
                sensory_return_1m=float(sensory_value),
            )

            row = metrics.to_dict()
            prediction = float(row.get("colony_prediction", 0.0))
            target_sign = strict_sign(target_signal)
            pred_sign = strict_sign(prediction)
            row.update(
                {
                    "test_name": name,
                    "seed": seed,
                    "step": step,
                    "sensory_return_1m": float(sensory_value),
                    "target_return_1m": float(target_value),
                    "target_signal_horizon": target_signal,
                    "prediction_sign": pred_sign,
                    "target_signal_sign": target_sign,
                    "target_signal_nonzero": target_sign != 0,
                    "strict_direction_correct": (
                        pred_sign != 0 and pred_sign == target_sign
                    ),
                }
            )
            rows.append(row)
    finally:
        organism.shutdown()
        MockSimulator.end()

    runtime = time.perf_counter() - started
    metadata = {
        "config": cfg.to_dict(),
        "backend": "MockSimulator",
        "seed": seed,
        "steps": int(target.size),
        "runtime_seconds": runtime,
        "dt_seconds": dt_seconds,
        "max_polyps": max_polyps,
    }
    return rows, metadata


def summarize_rows(
    rows: list[dict[str, Any]],
    *,
    warmup_steps: int | None = None,
) -> dict[str, Any]:
    if not rows:
        return {}

    steps = len(rows)
    warmup = warmup_steps if warmup_steps is not None else int(steps * WARMUP_FRACTION)
    warmup = max(0, min(warmup, max(0, steps - 1)))
    tail = rows[warmup:]

    def arr(key: str, source: list[dict[str, Any]] = rows) -> np.ndarray:
        return np.asarray([float(r.get(key, 0.0)) for r in source], dtype=float)

    def bool_arr(key: str, source: list[dict[str, Any]] = rows) -> np.ndarray:
        return np.asarray([bool(r.get(key, False)) for r in source], dtype=bool)

    target_nonzero_tail = bool_arr("target_signal_nonzero", tail)
    correct_tail = bool_arr("strict_direction_correct", tail)
    if np.any(target_nonzero_tail):
        strict_accuracy_tail = float(np.mean(correct_tail[target_nonzero_tail]))
    else:
        strict_accuracy_tail = None

    target_nonzero_all = bool_arr("target_signal_nonzero", rows)
    correct_all = bool_arr("strict_direction_correct", rows)
    if np.any(target_nonzero_all):
        strict_accuracy_all = float(np.mean(correct_all[target_nonzero_all]))
    else:
        strict_accuracy_all = None

    predictions_tail = arr("colony_prediction", tail)
    target_signal_tail = arr("target_signal_horizon", tail)
    dopamine_all = arr("raw_dopamine")
    prediction_all = arr("colony_prediction")
    target_signal_all = arr("target_signal_horizon")
    capital_all = arr("capital")
    accuracy_all = arr("mean_directional_accuracy_ema")
    n_alive_all = arr("n_alive")
    births_all = arr("births_this_step")
    deaths_all = arr("deaths_this_step")

    return {
        "steps": steps,
        "warmup_steps": warmup,
        "tail_steps": len(tail),
        "final_capital": float(capital_all[-1]),
        "capital_delta": float(capital_all[-1] - capital_all[0]),
        "max_abs_dopamine": float(np.max(np.abs(dopamine_all))),
        "mean_abs_dopamine": float(np.mean(np.abs(dopamine_all))),
        "final_accuracy_ema": float(accuracy_all[-1]),
        "tail_accuracy_ema": float(np.mean(arr("mean_directional_accuracy_ema", tail))),
        "strict_accuracy_all_nonzero_targets": strict_accuracy_all,
        "strict_accuracy_tail_nonzero_targets": strict_accuracy_tail,
        "nonzero_target_count_tail": int(np.sum(target_nonzero_tail)),
        "mean_abs_prediction": float(np.mean(np.abs(prediction_all))),
        "tail_mean_abs_prediction": float(np.mean(np.abs(predictions_tail))),
        "max_abs_prediction": float(np.max(np.abs(prediction_all))),
        "prediction_target_corr": safe_corr(prediction_all, target_signal_all),
        "tail_prediction_target_corr": safe_corr(predictions_tail, target_signal_tail),
        "final_n_alive": int(n_alive_all[-1]),
        "max_n_alive": int(np.max(n_alive_all)),
        "total_births": int(np.sum(births_all)),
        "total_deaths": int(np.sum(deaths_all)),
    }


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
    names = ", ".join(c["name"] for c in failed)
    return "fail", f"Failed criteria: {names}"


def balanced_signs(steps: int, rng: np.random.Generator) -> np.ndarray:
    signs = np.array([1, -1] * ((steps + 1) // 2), dtype=float)[:steps]
    rng.shuffle(signs)
    return signs


def make_zero_signal(steps: int) -> tuple[np.ndarray, np.ndarray]:
    zeros = np.zeros(steps, dtype=float)
    return zeros.copy(), zeros.copy()


def make_shuffled_label(
    *,
    steps: int,
    seed: int,
    amplitude: float,
) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    sensory_signs = balanced_signs(steps, rng)
    target_signs = sensory_signs.copy()

    # Use an independent permutation so the target marginal distribution is
    # identical to sensory, but the time-aligned labels are broken.
    perm_rng = np.random.default_rng(seed + 10_000)
    perm_rng.shuffle(target_signs)

    sensory = amplitude * sensory_signs
    target = amplitude * target_signs
    return sensory.astype(float), target.astype(float)


def plot_case_timeseries(
    *,
    rows: list[dict[str, Any]],
    path: Path,
    title: str,
) -> str | None:
    if plt is None:
        return None

    steps = np.asarray([int(r["step"]) for r in rows], dtype=int)

    def values(key: str) -> np.ndarray:
        return np.asarray([float(r.get(key, 0.0)) for r in rows], dtype=float)

    fig, axes = plt.subplots(4, 1, figsize=(12, 10), sharex=True)
    fig.suptitle(title, fontsize=14, fontweight="bold")

    axes[0].plot(steps, values("sensory_return_1m"), label="sensory input", lw=1.3)
    axes[0].plot(steps, values("target_return_1m"), label="target return", lw=1.0, alpha=0.75)
    axes[0].set_ylabel("1-step return")
    axes[0].legend(loc="upper right")
    axes[0].grid(alpha=0.2)

    axes[1].plot(steps, values("colony_prediction"), label="colony prediction", lw=1.2)
    axes[1].plot(steps, values("target_signal_horizon"), label="horizon target", lw=1.0, alpha=0.8)
    axes[1].axhline(0.0, color="black", lw=0.8, alpha=0.5)
    axes[1].set_ylabel("prediction / target")
    axes[1].legend(loc="upper right")
    axes[1].grid(alpha=0.2)

    axes[2].plot(steps, values("raw_dopamine"), label="raw dopamine", color="#c23b22", lw=1.0)
    axes[2].axhline(0.0, color="black", lw=0.8, alpha=0.5)
    axes[2].set_ylabel("dopamine")
    axes[2].legend(loc="upper right")
    axes[2].grid(alpha=0.2)

    axes[3].plot(steps, values("mean_directional_accuracy_ema"), label="accuracy EMA", color="#2b6cb0", lw=1.1)
    axes[3].plot(steps, values("capital") - 1.0, label="capital delta", color="#2f855a", lw=1.1)
    axes[3].plot(steps, values("n_alive") / max(1.0, np.max(values("n_alive"))), label="alive polyps scaled", color="#805ad5", lw=1.0, alpha=0.8)
    axes[3].axhline(0.5, color="#2b6cb0", lw=0.8, alpha=0.35, linestyle="--")
    axes[3].set_ylabel("summary")
    axes[3].set_xlabel("step")
    axes[3].legend(loc="upper right")
    axes[3].grid(alpha=0.2)

    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return str(path)


def plot_seed_repeat(
    *,
    seed_rows: list[dict[str, Any]],
    path: Path,
    accuracy_threshold: float,
    corr_threshold: float,
) -> str | None:
    if plt is None:
        return None
    seeds = np.asarray([int(r["seed"]) for r in seed_rows], dtype=int)
    acc = np.asarray(
        [float(r.get("strict_accuracy_tail_nonzero_targets", 0.0)) for r in seed_rows],
        dtype=float,
    )
    corr_values = np.asarray(
        [
            0.0
            if r.get("tail_prediction_target_corr") is None
            else float(r.get("tail_prediction_target_corr"))
            for r in seed_rows
        ],
        dtype=float,
    )

    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    fig.suptitle("Tier 1 Random-Seed Repeat Control", fontsize=14, fontweight="bold")

    axes[0].bar(seeds, acc, color="#2b6cb0", alpha=0.8)
    axes[0].axhline(0.5, color="black", lw=0.9, linestyle="--", label="chance")
    axes[0].axhline(accuracy_threshold, color="#c23b22", lw=1.0, linestyle="--", label="warning threshold")
    axes[0].set_ylabel("tail strict accuracy")
    axes[0].legend(loc="upper right")
    axes[0].grid(axis="y", alpha=0.2)

    axes[1].bar(seeds, corr_values, color="#2f855a", alpha=0.8)
    axes[1].axhline(corr_threshold, color="#c23b22", lw=1.0, linestyle="--")
    axes[1].axhline(-corr_threshold, color="#c23b22", lw=1.0, linestyle="--")
    axes[1].axhline(0.0, color="black", lw=0.9)
    axes[1].set_ylabel("tail prediction/target corr")
    axes[1].set_xlabel("seed")
    axes[1].grid(axis="y", alpha=0.2)

    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return str(path)


def run_zero_signal(args: argparse.Namespace, output_dir: Path) -> TestResult:
    sensory, target = make_zero_signal(args.steps)
    rows, metadata = run_organism_case(
        name="zero_signal",
        seed=args.base_seed,
        sensory=sensory,
        target=target,
        max_polyps=args.max_polyps,
        dt_seconds=args.dt_seconds,
        readout_lr=args.readout_lr,
        delayed_readout_lr=args.delayed_readout_lr,
    )

    csv_path = output_dir / "zero_signal_timeseries.csv"
    plot_path = output_dir / "zero_signal_timeseries.png"
    write_csv(csv_path, rows)
    plot_case_timeseries(
        rows=rows,
        path=plot_path,
        title="Tier 1.1 Zero-Signal Test",
    )

    summary = summarize_rows(rows)
    summary.update(
        {
            "backend": metadata["backend"],
            "seed": metadata["seed"],
            "runtime_seconds": metadata["runtime_seconds"],
        }
    )

    corr = summary["prediction_target_corr"]
    criteria = [
        criterion(
            "zero target stayed zero",
            summary["nonzero_target_count_tail"],
            "==",
            0,
            summary["nonzero_target_count_tail"] == 0,
        ),
        criterion(
            "max absolute dopamine",
            summary["max_abs_dopamine"],
            "<=",
            1e-9,
            summary["max_abs_dopamine"] <= 1e-9,
        ),
        criterion(
            "capital absolute delta",
            abs(summary["capital_delta"]),
            "<=",
            1e-9,
            abs(summary["capital_delta"]) <= 1e-9,
        ),
        criterion(
            "tail accuracy EMA",
            summary["tail_accuracy_ema"],
            "<=",
            0.51,
            summary["tail_accuracy_ema"] <= 0.51,
            "Zero/zero must not count as learned directional success.",
        ),
        criterion(
            "prediction/target correlation",
            corr,
            "is None or abs <= ",
            1e-9,
            corr is None or abs(corr) <= 1e-9,
        ),
    ]
    status, failure_reason = pass_fail(criteria)
    return TestResult(
        name="zero_signal",
        status=status,
        summary=summary,
        criteria=criteria,
        artifacts={
            "timeseries_csv": str(csv_path),
            "plot_png": str(plot_path) if plot_path.exists() else "",
        },
        failure_reason=failure_reason,
    )


def run_shuffled_label(args: argparse.Namespace, output_dir: Path) -> TestResult:
    sensory, target = make_shuffled_label(
        steps=args.steps,
        seed=args.base_seed,
        amplitude=args.amplitude,
    )
    rows, metadata = run_organism_case(
        name="shuffled_label",
        seed=args.base_seed,
        sensory=sensory,
        target=target,
        max_polyps=args.max_polyps,
        dt_seconds=args.dt_seconds,
        readout_lr=args.readout_lr,
        delayed_readout_lr=args.delayed_readout_lr,
    )

    csv_path = output_dir / "shuffled_label_timeseries.csv"
    plot_path = output_dir / "shuffled_label_timeseries.png"
    write_csv(csv_path, rows)
    plot_case_timeseries(
        rows=rows,
        path=plot_path,
        title="Tier 1.2 Shuffled-Label Test",
    )

    summary = summarize_rows(rows)
    summary.update(
        {
            "backend": metadata["backend"],
            "seed": metadata["seed"],
            "runtime_seconds": metadata["runtime_seconds"],
            "amplitude": args.amplitude,
        }
    )

    acc = summary["strict_accuracy_tail_nonzero_targets"]
    corr = summary["tail_prediction_target_corr"]
    corr_abs = None if corr is None else abs(corr)
    criteria = [
        criterion(
            "tail strict accuracy on nonzero targets",
            acc,
            "<=",
            args.single_run_accuracy_threshold,
            acc is not None and acc <= args.single_run_accuracy_threshold,
        ),
        criterion(
            "tail prediction/target abs correlation",
            corr_abs,
            "is None or <=",
            args.single_run_corr_threshold,
            corr_abs is None or corr_abs <= args.single_run_corr_threshold,
        ),
        criterion(
            "capital absolute delta",
            abs(summary["capital_delta"]),
            "<=",
            args.single_run_capital_threshold,
            abs(summary["capital_delta"]) <= args.single_run_capital_threshold,
        ),
    ]
    status, failure_reason = pass_fail(criteria)
    return TestResult(
        name="shuffled_label",
        status=status,
        summary=summary,
        criteria=criteria,
        artifacts={
            "timeseries_csv": str(csv_path),
            "plot_png": str(plot_path) if plot_path.exists() else "",
        },
        failure_reason=failure_reason,
    )


def run_seed_repeat(args: argparse.Namespace, output_dir: Path) -> TestResult:
    seed_summaries: list[dict[str, Any]] = []
    all_case_metadata: list[dict[str, Any]] = []

    for offset in range(args.seeds):
        seed = args.base_seed + offset
        sensory, target = make_shuffled_label(
            steps=args.steps,
            seed=seed,
            amplitude=args.amplitude,
        )
        rows, metadata = run_organism_case(
            name="seed_repeat_shuffled_label",
            seed=seed,
            sensory=sensory,
            target=target,
            max_polyps=args.max_polyps,
            dt_seconds=args.dt_seconds,
            readout_lr=args.readout_lr,
            delayed_readout_lr=args.delayed_readout_lr,
        )
        summary = summarize_rows(rows)
        summary.update(
            {
                "seed": seed,
                "runtime_seconds": metadata["runtime_seconds"],
                "backend": metadata["backend"],
            }
        )
        seed_summaries.append(summary)
        all_case_metadata.append(metadata)

        if args.export_seed_timeseries:
            write_csv(output_dir / f"seed_repeat_seed_{seed}_timeseries.csv", rows)

    csv_path = output_dir / "seed_repeat_summary.csv"
    plot_path = output_dir / "seed_repeat_summary.png"
    write_csv(csv_path, seed_summaries)
    plot_seed_repeat(
        seed_rows=seed_summaries,
        path=plot_path,
        accuracy_threshold=args.single_run_accuracy_threshold,
        corr_threshold=args.single_run_corr_threshold,
    )

    accuracies = np.asarray(
        [
            float(s["strict_accuracy_tail_nonzero_targets"])
            for s in seed_summaries
            if s["strict_accuracy_tail_nonzero_targets"] is not None
        ],
        dtype=float,
    )
    corr_abs_values = np.asarray(
        [
            abs(float(s["tail_prediction_target_corr"]))
            for s in seed_summaries
            if s["tail_prediction_target_corr"] is not None
        ],
        dtype=float,
    )
    high_seed_count = int(np.sum(accuracies > args.single_run_accuracy_threshold))
    high_seed_fraction = float(high_seed_count / max(1, len(accuracies)))
    mean_abs_corr = (
        float(np.mean(corr_abs_values)) if corr_abs_values.size > 0 else None
    )

    summary = {
        "backend": "MockSimulator",
        "n_seeds": args.seeds,
        "steps_per_seed": args.steps,
        "base_seed": args.base_seed,
        "mean_tail_strict_accuracy": float(np.mean(accuracies)),
        "median_tail_strict_accuracy": float(np.median(accuracies)),
        "min_tail_strict_accuracy": float(np.min(accuracies)),
        "max_tail_strict_accuracy": float(np.max(accuracies)),
        "std_tail_strict_accuracy": float(np.std(accuracies, ddof=1))
        if accuracies.size > 1
        else 0.0,
        "high_seed_count": high_seed_count,
        "high_seed_fraction": high_seed_fraction,
        "mean_abs_tail_prediction_target_corr": mean_abs_corr,
        "max_abs_tail_prediction_target_corr": float(np.max(corr_abs_values))
        if corr_abs_values.size > 0
        else None,
        "total_runtime_seconds": float(
            sum(m["runtime_seconds"] for m in all_case_metadata)
        ),
    }

    criteria = [
        criterion(
            "mean tail strict accuracy",
            summary["mean_tail_strict_accuracy"],
            "<=",
            args.repeat_mean_accuracy_threshold,
            summary["mean_tail_strict_accuracy"]
            <= args.repeat_mean_accuracy_threshold,
        ),
        criterion(
            "high-accuracy seed fraction",
            summary["high_seed_fraction"],
            "<=",
            args.repeat_high_seed_fraction_threshold,
            summary["high_seed_fraction"]
            <= args.repeat_high_seed_fraction_threshold,
            f"High seed means > {args.single_run_accuracy_threshold:.3f}.",
        ),
        criterion(
            "mean absolute tail prediction/target correlation",
            summary["mean_abs_tail_prediction_target_corr"],
            "<=",
            args.repeat_mean_abs_corr_threshold,
            mean_abs_corr is not None
            and mean_abs_corr <= args.repeat_mean_abs_corr_threshold,
        ),
    ]
    status, failure_reason = pass_fail(criteria)
    return TestResult(
        name="seed_repeat",
        status=status,
        summary=summary,
        criteria=criteria,
        artifacts={
            "seed_summary_csv": str(csv_path),
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


def markdown_value(value: Any) -> str:
    if value is None:
        return "None"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


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
    lines: list[str] = []
    overall = "PASS" if results and all(r.passed for r in results) else "FAIL"
    if stopped_after:
        overall = "STOPPED"

    lines.extend(
        [
            "# Tier 1 Controlled Sanity Findings",
            "",
            f"- Generated: `{utc_now()}`",
            "- Backend: `MockSimulator`",
            f"- Overall status: **{overall}**",
            f"- Steps per run: `{args.steps}`",
            f"- Seed repeat count: `{args.seeds}`",
            f"- Base seed: `{args.base_seed}`",
            f"- Output directory: `{output_dir}`",
            "",
            "Tier 1 is a negative-control tier. Passing it does not prove learning; "
            "it proves the organism does not appear to learn when useful signal is absent or labels are broken.",
            "",
            "## Artifact Index",
            "",
            f"- JSON manifest: `{manifest_path.name}`",
            f"- Summary CSV: `{summary_csv_path.name}`",
        ]
    )
    if MATPLOTLIB_ERROR:
        lines.append(f"- Plotting unavailable: `{MATPLOTLIB_ERROR}`")
    lines.append("")

    lines.extend(
        [
            "## Summary",
            "",
            "| Test | Status | Key metric | Notes |",
            "| --- | --- | --- | --- |",
        ]
    )
    for result in results:
        if result.name == "zero_signal":
            key_metric = (
                "max_abs_dopamine="
                f"{markdown_value(result.summary.get('max_abs_dopamine'))}, "
                "capital_delta="
                f"{markdown_value(result.summary.get('capital_delta'))}"
            )
        elif result.name == "shuffled_label":
            key_metric = (
                "tail_strict_acc="
                f"{markdown_value(result.summary.get('strict_accuracy_tail_nonzero_targets'))}, "
                "tail_corr="
                f"{markdown_value(result.summary.get('tail_prediction_target_corr'))}"
            )
        elif result.name == "seed_repeat":
            key_metric = (
                "mean_tail_strict_acc="
                f"{markdown_value(result.summary.get('mean_tail_strict_accuracy'))}, "
                "high_seed_fraction="
                f"{markdown_value(result.summary.get('high_seed_fraction'))}"
            )
        else:
            key_metric = ""
        notes = result.failure_reason or "criteria satisfied"
        lines.append(f"| `{result.name}` | **{result.status.upper()}** | {key_metric} | {notes} |")
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
            rule = f"{item['operator']} {markdown_value(item['threshold'])}"
            lines.append(
                "| "
                f"{item['name']} | "
                f"{markdown_value(item['value'])} | "
                f"{rule} | "
                f"{'yes' if item['passed'] else 'no'} |"
            )
        lines.append("")
        if result.artifacts:
            lines.append("Artifacts:")
            lines.append("")
            for label, artifact in result.artifacts.items():
                if artifact:
                    artifact_path = Path(artifact)
                    rel = artifact_path.name
                    lines.append(f"- `{label}`: `{rel}`")
                    if artifact_path.suffix.lower() == ".png":
                        lines.append("")
                        lines.append(f"![{result.name} plot]({rel})")
                        lines.append("")
            lines.append("")

    if stopped_after:
        lines.extend(
            [
                "## Stop Condition",
                "",
                f"Execution stopped after `{stopped_after}` because `--stop-on-fail` was enabled.",
                "Debug the failed test before proceeding to later Tier 1 or Tier 2 tests.",
                "",
            ]
        )

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def resolve_tests(selected: list[str]) -> list[str]:
    order = ["zero_signal", "shuffled_label", "seed_repeat"]
    aliases = {
        "zero": "zero_signal",
        "zero_signal": "zero_signal",
        "shuffled": "shuffled_label",
        "shuffled_label": "shuffled_label",
        "seed": "seed_repeat",
        "seeds": "seed_repeat",
        "seed_repeat": "seed_repeat",
        "all": "all",
    }
    normalized = [aliases[item] for item in selected]
    if "all" in normalized:
        return order
    wanted = set(normalized)
    return [name for name in order if name in wanted]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run Tier 1 CRA sanity controls and export findings.",
    )
    parser.add_argument(
        "--tests",
        nargs="+",
        default=["all"],
        choices=[
            "all",
            "zero",
            "zero_signal",
            "shuffled",
            "shuffled_label",
            "seed",
            "seeds",
            "seed_repeat",
        ],
    )
    parser.add_argument("--steps", type=int, default=DEFAULT_STEPS)
    parser.add_argument("--seeds", type=int, default=DEFAULT_SEEDS)
    parser.add_argument("--base-seed", type=int, default=42)
    parser.add_argument("--amplitude", type=float, default=DEFAULT_AMPLITUDE)
    parser.add_argument("--max-polyps", type=int, default=DEFAULT_MAX_POLYPS)
    parser.add_argument("--dt-seconds", type=float, default=DEFAULT_DT_SECONDS)
    parser.add_argument("--readout-lr", type=float, default=0.10)
    parser.add_argument("--delayed-readout-lr", type=float, default=0.05)
    parser.add_argument("--stop-on-fail", action="store_true")
    parser.add_argument("--export-seed-timeseries", action="store_true")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Defaults to controlled_test_output/tier1_<timestamp>.",
    )
    parser.add_argument(
        "--single-run-accuracy-threshold",
        type=float,
        default=0.60,
    )
    parser.add_argument(
        "--single-run-corr-threshold",
        type=float,
        default=0.25,
    )
    parser.add_argument(
        "--single-run-capital-threshold",
        type=float,
        default=0.05,
    )
    parser.add_argument(
        "--repeat-mean-accuracy-threshold",
        type=float,
        default=0.56,
    )
    parser.add_argument(
        "--repeat-high-seed-fraction-threshold",
        type=float,
        default=0.20,
    )
    parser.add_argument(
        "--repeat-mean-abs-corr-threshold",
        type=float,
        default=0.20,
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.steps <= 0:
        parser.error("--steps must be positive")
    if args.seeds <= 0:
        parser.error("--seeds must be positive")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = args.output_dir or (ROOT / "controlled_test_output" / f"tier1_{timestamp}")
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    selected_tests = resolve_tests(args.tests)
    runners = {
        "zero_signal": run_zero_signal,
        "shuffled_label": run_shuffled_label,
        "seed_repeat": run_seed_repeat,
    }
    results: list[TestResult] = []
    stopped_after: str | None = None

    for test_name in selected_tests:
        print(f"[tier1] running {test_name}...", flush=True)
        result = runners[test_name](args, output_dir)
        results.append(result)
        print(
            f"[tier1] {test_name}: {result.status.upper()}",
            result.failure_reason,
            flush=True,
        )
        if args.stop_on_fail and not result.passed:
            stopped_after = test_name
            break

    summary_csv_path = output_dir / "tier1_summary.csv"
    manifest_path = output_dir / "tier1_results.json"
    report_path = output_dir / "tier1_report.md"

    write_csv(summary_csv_path, summary_rows(results))
    manifest = {
        "generated_at_utc": utc_now(),
        "tier": "Tier 1 - sanity tests",
        "backend": "MockSimulator",
        "command": " ".join(sys.argv),
        "output_dir": str(output_dir),
        "selected_tests": selected_tests,
        "stopped_after": stopped_after,
        "thresholds": {
            "readout_lr": args.readout_lr,
            "delayed_readout_lr": args.delayed_readout_lr,
            "single_run_accuracy_threshold": args.single_run_accuracy_threshold,
            "single_run_corr_threshold": args.single_run_corr_threshold,
            "single_run_capital_threshold": args.single_run_capital_threshold,
            "repeat_mean_accuracy_threshold": args.repeat_mean_accuracy_threshold,
            "repeat_high_seed_fraction_threshold": args.repeat_high_seed_fraction_threshold,
            "repeat_mean_abs_corr_threshold": args.repeat_mean_abs_corr_threshold,
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

    latest_path = ROOT / "controlled_test_output" / "tier1_latest_manifest.json"
    latest_path.parent.mkdir(parents=True, exist_ok=True)
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
