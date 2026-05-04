#!/usr/bin/env python3
"""Run Tier 4.12 backend-parity tests for the CRA organism.

Tier 4.12 asks whether the same controlled learning behavior survives backend
movement. This harness starts with a small but strict parity ladder:

1. NEST fixed-pattern baseline.
2. Brian2 same task/config/seeds.
3. SpiNNaker PyNN import/setup/factory readiness prep.

The NEST and Brian2 runs must learn the same fixed-pattern task and must not
use synthetic spike fallback. The SpiNNaker step is intentionally a prep smoke:
it verifies that the PyNN modules, setup path, backend factory, and neuromorphic
capabilities are available locally, but it does not claim a hardware run.
"""

from __future__ import annotations

import argparse
import importlib
import math
import random
import sys
import time
from collections import deque
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
from coral_reef_spinnaker.backend_factory import get_backend_factory  # noqa: E402
from tier2_learning import (  # noqa: E402
    DEFAULT_AMPLITUDE,
    DEFAULT_DT_SECONDS,
    criterion,
    fixed_pattern_task,
    json_safe,
    load_backend,
    markdown_value,
    pass_fail,
    plot_case,
    setup_backend,
    strict_sign,
    summarize_rows,
    write_csv,
    write_json,
    utc_now,
    end_backend,
)
from tier4_scaling import (  # noqa: E402
    TestResult,
    alive_readout_weights,
    alive_trophic_health,
    mean,
    seeds_from_args,
    stdev,
)


def make_config(
    *,
    seed: int,
    steps: int,
    population_size: int,
    args: argparse.Namespace,
) -> ReefConfig:
    cfg = ReefConfig.default()
    cfg.seed = int(seed)
    cfg.lifecycle.initial_population = int(population_size)
    cfg.lifecycle.max_population_from_memory = False
    cfg.lifecycle.max_population_hard = int(population_size)
    cfg.lifecycle.enable_reproduction = False
    cfg.lifecycle.enable_apoptosis = False
    cfg.lifecycle.enable_structural_plasticity = True
    cfg.measurement.stream_history_maxlen = max(steps + 16, 128)
    cfg.spinnaker.sync_interval_steps = 0
    cfg.spinnaker.runtime_ms_per_step = float(args.dt_seconds) * 1000.0
    cfg.learning.evaluation_horizon_bars = 1
    cfg.learning.readout_learning_rate = float(args.readout_lr)
    cfg.learning.delayed_readout_learning_rate = float(args.delayed_readout_lr)
    return cfg


def run_backend_seed(
    *,
    backend_key: str,
    seed: int,
    args: argparse.Namespace,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    random.seed(seed)
    np.random.seed(seed)
    sensory, target, evaluation_target, evaluation_mask = fixed_pattern_task(
        args.steps,
        args.amplitude,
    )

    sim, backend_name = load_backend(backend_key)
    setup_backend(sim, backend_name)
    cfg = make_config(
        seed=seed,
        steps=int(target.size),
        population_size=args.population_size,
        args=args,
    )
    organism: Organism | None = Organism(cfg, sim)
    diagnostics: dict[str, Any] = {}
    rows: list[dict[str, Any]] = []
    task_window: deque[float] = deque(maxlen=1)
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
                    "test_name": "backend_parity_fixed_pattern",
                    "backend_key": backend_key,
                    "backend": backend_name,
                    "seed": int(seed),
                    "step": int(step),
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
                    "mean_trophic_health": float(np.mean(trophic)) if trophic else 0.0,
                    "min_trophic_health": float(np.min(trophic)) if trophic else 0.0,
                    "max_trophic_health": float(np.max(trophic)) if trophic else 0.0,
                    "pending_horizons": int(learning_status.get("pending_horizons", 0)),
                    "matured_horizons": int(learning_status.get("matured_horizons", 0)),
                    "step_spike_count": int(sum(int(v) for v in latest_spikes.values())),
                }
            )
            rows.append(row)
        diagnostics = organism.backend_diagnostics()
    finally:
        if organism is not None:
            if not diagnostics:
                diagnostics = organism.backend_diagnostics()
            organism.shutdown()
        end_backend(sim)

    summary = summarize_rows(rows)
    step_spikes = [float(r.get("step_spike_count", 0.0)) for r in rows]
    summary.update(
        {
            "backend_key": backend_key,
            "backend": backend_name,
            "seed": int(seed),
            "steps": int(target.size),
            "population_size": int(args.population_size),
            "runtime_seconds": time.perf_counter() - started,
            "total_step_spikes": int(sum(step_spikes)),
            "mean_step_spikes": float(np.mean(step_spikes)) if step_spikes else 0.0,
            "config": cfg.to_dict(),
        }
    )
    summary.update(diagnostics)
    return rows, summary


def aggregate_backend(backend_key: str, summaries: list[dict[str, Any]]) -> dict[str, Any]:
    keys = [
        "tail_accuracy",
        "all_accuracy",
        "early_accuracy",
        "accuracy_improvement",
        "prediction_target_corr",
        "tail_prediction_target_corr",
        "max_abs_dopamine",
        "mean_abs_dopamine",
        "final_accuracy_ema",
        "tail_accuracy_ema",
        "final_n_alive",
        "max_n_alive",
        "total_births",
        "total_deaths",
        "final_mean_readout_weight",
        "final_mean_abs_readout_weight",
        "final_matured_horizons",
        "max_matured_horizons",
        "runtime_seconds",
        "total_step_spikes",
        "mean_step_spikes",
    ]
    agg: dict[str, Any] = {
        "backend_key": backend_key,
        "backend": summaries[0].get("backend") if summaries else backend_key,
        "runs": len(summaries),
        "seeds": [s.get("seed") for s in summaries],
    }
    for key in keys:
        values = [s.get(key) for s in summaries]
        agg[f"{key}_mean"] = mean(values)
        agg[f"{key}_std"] = stdev(values)
    agg["sim_run_failures_sum"] = int(
        sum(int(s.get("sim_run_failures", 0)) for s in summaries)
    )
    agg["summary_read_failures_sum"] = int(
        sum(int(s.get("summary_read_failures", 0)) for s in summaries)
    )
    agg["synthetic_fallbacks_sum"] = int(
        sum(int(s.get("synthetic_fallbacks", 0)) for s in summaries)
    )
    agg["last_sim_run_errors"] = [
        s.get("last_sim_run_error", "") for s in summaries if s.get("last_sim_run_error")
    ]
    agg["total_births_sum"] = int(sum(int(s.get("total_births", 0)) for s in summaries))
    agg["total_deaths_sum"] = int(sum(int(s.get("total_deaths", 0)) for s in summaries))
    return agg


def backend_criteria(agg: dict[str, Any], args: argparse.Namespace) -> list[dict[str, Any]]:
    return [
        criterion(
            "backend sim.run has no failures",
            agg["sim_run_failures_sum"],
            "==",
            0,
            agg["sim_run_failures_sum"] == 0,
        ),
        criterion(
            "backend summary read has no failures",
            agg["summary_read_failures_sum"],
            "==",
            0,
            agg["summary_read_failures_sum"] == 0,
        ),
        criterion(
            "no synthetic spike fallback",
            agg["synthetic_fallbacks_sum"],
            "==",
            0,
            agg["synthetic_fallbacks_sum"] == 0,
        ),
        criterion(
            "real spike readback is active",
            agg["total_step_spikes_mean"],
            ">",
            0,
            agg["total_step_spikes_mean"] is not None
            and agg["total_step_spikes_mean"] > 0,
        ),
        criterion(
            "fixed population has no births/deaths",
            {"births": agg["total_births_sum"], "deaths": agg["total_deaths_sum"]},
            "==",
            {"births": 0, "deaths": 0},
            agg["total_births_sum"] == 0 and agg["total_deaths_sum"] == 0,
        ),
        criterion(
            "no extinction/collapse",
            agg["final_n_alive_mean"],
            "==",
            args.population_size,
            agg["final_n_alive_mean"] == args.population_size,
        ),
        criterion(
            "overall strict accuracy",
            agg["all_accuracy_mean"],
            ">=",
            args.all_accuracy_threshold,
            agg["all_accuracy_mean"] is not None
            and agg["all_accuracy_mean"] >= args.all_accuracy_threshold,
        ),
        criterion(
            "tail strict accuracy",
            agg["tail_accuracy_mean"],
            ">=",
            args.tail_accuracy_threshold,
            agg["tail_accuracy_mean"] is not None
            and agg["tail_accuracy_mean"] >= args.tail_accuracy_threshold,
        ),
        criterion(
            "tail prediction/target correlation",
            agg["tail_prediction_target_corr_mean"],
            ">=",
            args.corr_threshold,
            agg["tail_prediction_target_corr_mean"] is not None
            and agg["tail_prediction_target_corr_mean"] >= args.corr_threshold,
        ),
        criterion(
            "inverse readout weight learned",
            agg["final_mean_readout_weight_mean"],
            "<=",
            args.max_final_readout_weight,
            agg["final_mean_readout_weight_mean"] is not None
            and agg["final_mean_readout_weight_mean"] <= args.max_final_readout_weight,
            "Previous symbol should predict the opposite next symbol.",
        ),
    ]


def run_backend_case(
    *,
    backend_key: str,
    args: argparse.Namespace,
    output_dir: Path,
) -> TestResult:
    print(
        f"[tier4.12] {backend_key}: running {len(seeds_from_args(args))} seeds...",
        flush=True,
    )
    summaries: list[dict[str, Any]] = []
    artifacts: dict[str, str] = {}
    for seed in seeds_from_args(args):
        try:
            rows, summary = run_backend_seed(backend_key=backend_key, seed=seed, args=args)
        except Exception as exc:
            failure = f"{backend_key} seed {seed} raised {type(exc).__name__}: {exc}"
            result = TestResult(
                name=f"{backend_key}_fixed_pattern",
                status="fail",
                summary={
                    "aggregate": {
                        "backend_key": backend_key,
                        "backend": backend_key,
                        "runs": len(summaries),
                    },
                    "seed_summaries": summaries,
                    "exception": repr(exc),
                },
                criteria=[
                    criterion(
                        "backend execution",
                        failure,
                        "no exception",
                        "",
                        False,
                    )
                ],
                artifacts=artifacts,
                failure_reason=failure,
            )
            print(f"[tier4.12] {backend_key}: FAIL {failure}", flush=True)
            return result

        csv_path = output_dir / f"{backend_key}_fixed_pattern_seed{seed}_timeseries.csv"
        png_path = output_dir / f"{backend_key}_fixed_pattern_seed{seed}_timeseries.png"
        write_csv(csv_path, rows)
        plot_case(rows, png_path, f"Tier 4.12 {backend_key} fixed-pattern seed {seed}")
        artifacts[f"seed_{seed}_timeseries_csv"] = str(csv_path)
        if png_path.exists():
            artifacts[f"seed_{seed}_timeseries_png"] = str(png_path)
        summaries.append(summary)

    aggregate = aggregate_backend(backend_key, summaries)
    criteria = backend_criteria(aggregate, args)
    status, failure_reason = pass_fail(criteria)
    result = TestResult(
        name=f"{backend_key}_fixed_pattern",
        status=status,
        summary={
            "aggregate": aggregate,
            "seed_summaries": summaries,
        },
        criteria=criteria,
        artifacts=artifacts,
        failure_reason=failure_reason,
    )
    print(f"[tier4.12] {backend_key}: {status.upper()} {failure_reason}", flush=True)
    return result


def value_delta(a: Any, b: Any) -> float | None:
    if a is None or b is None:
        return None
    try:
        af = float(a)
        bf = float(b)
    except Exception:
        return None
    if not math.isfinite(af) or not math.isfinite(bf):
        return None
    return abs(af - bf)


def run_parity_comparison(
    *,
    results: list[TestResult],
    args: argparse.Namespace,
) -> TestResult:
    by_key = {
        r.summary.get("aggregate", {}).get("backend_key"): r
        for r in results
        if "aggregate" in r.summary
    }
    nest = by_key.get("nest")
    brian2 = by_key.get("brian2")
    summary: dict[str, Any] = {
        "nest_present": nest is not None,
        "brian2_present": brian2 is not None,
    }
    criteria: list[dict[str, Any]] = [
        criterion("NEST case exists", summary["nest_present"], "==", True, nest is not None),
        criterion("Brian2 case exists", summary["brian2_present"], "==", True, brian2 is not None),
    ]
    if nest is None or brian2 is None:
        status, failure_reason = pass_fail(criteria)
        return TestResult(
            name="nest_brian2_parity",
            status=status,
            summary=summary,
            criteria=criteria,
            artifacts={},
            failure_reason=failure_reason,
        )

    n_agg = nest.summary["aggregate"]
    b_agg = brian2.summary["aggregate"]
    all_delta = value_delta(n_agg.get("all_accuracy_mean"), b_agg.get("all_accuracy_mean"))
    tail_delta = value_delta(n_agg.get("tail_accuracy_mean"), b_agg.get("tail_accuracy_mean"))
    corr_delta = value_delta(
        n_agg.get("tail_prediction_target_corr_mean"),
        b_agg.get("tail_prediction_target_corr_mean"),
    )
    runtime_ratio = None
    if (
        n_agg.get("runtime_seconds_mean") is not None
        and b_agg.get("runtime_seconds_mean") is not None
        and float(n_agg["runtime_seconds_mean"]) > 0.0
    ):
        runtime_ratio = float(b_agg["runtime_seconds_mean"]) / float(
            n_agg["runtime_seconds_mean"]
        )

    summary.update(
        {
            "nest_status": nest.status,
            "brian2_status": brian2.status,
            "nest_all_accuracy_mean": n_agg.get("all_accuracy_mean"),
            "brian2_all_accuracy_mean": b_agg.get("all_accuracy_mean"),
            "all_accuracy_delta": all_delta,
            "nest_tail_accuracy_mean": n_agg.get("tail_accuracy_mean"),
            "brian2_tail_accuracy_mean": b_agg.get("tail_accuracy_mean"),
            "tail_accuracy_delta": tail_delta,
            "nest_tail_corr_mean": n_agg.get("tail_prediction_target_corr_mean"),
            "brian2_tail_corr_mean": b_agg.get("tail_prediction_target_corr_mean"),
            "tail_corr_delta": corr_delta,
            "brian2_to_nest_runtime_ratio": runtime_ratio,
        }
    )
    criteria.extend(
        [
            criterion(
                "NEST backend case passes",
                nest.status,
                "==",
                "pass",
                nest.passed,
            ),
            criterion(
                "Brian2 backend case passes",
                brian2.status,
                "==",
                "pass",
                brian2.passed,
            ),
            criterion(
                "overall accuracy parity delta",
                all_delta,
                "<=",
                args.max_all_accuracy_delta,
                all_delta is not None and all_delta <= args.max_all_accuracy_delta,
            ),
            criterion(
                "tail accuracy parity delta",
                tail_delta,
                "<=",
                args.max_tail_accuracy_delta,
                tail_delta is not None and tail_delta <= args.max_tail_accuracy_delta,
            ),
            criterion(
                "tail correlation parity delta",
                corr_delta,
                "<=",
                args.max_corr_delta,
                corr_delta is not None and corr_delta <= args.max_corr_delta,
            ),
        ]
    )
    status, failure_reason = pass_fail(criteria)
    print(f"[tier4.12] nest_brian2_parity: {status.upper()} {failure_reason}", flush=True)
    return TestResult(
        name="nest_brian2_parity",
        status=status,
        summary=summary,
        criteria=criteria,
        artifacts={},
        failure_reason=failure_reason,
    )


def import_spinnaker_module(module_name: str) -> dict[str, Any]:
    info: dict[str, Any] = {
        "module_name": module_name,
        "import_ok": False,
        "setup_ok": None,
        "end_ok": None,
        "version": None,
        "error": "",
    }
    try:
        module = importlib.import_module(module_name)
        info["import_ok"] = True
        info["version"] = getattr(module, "__version__", None)
        info["module_repr"] = repr(module)
        info["module"] = module
    except Exception as exc:
        info["error"] = f"{type(exc).__name__}: {exc}"
    return info


def run_spinnaker_prep(args: argparse.Namespace) -> TestResult:
    print("[tier4.12] spinnaker_pynn_prep: checking local PyNN readiness...", flush=True)
    module_infos = [
        import_spinnaker_module("pyNN.spiNNaker"),
        import_spinnaker_module("spynnaker.pyNN"),
    ]

    canonical = module_infos[0]
    setup_error = ""
    if canonical.get("import_ok") and args.spinnaker_setup_smoke:
        module = canonical["module"]
        try:
            module.setup(timestep=args.spinnaker_timestep)
            canonical["setup_ok"] = True
        except Exception as exc:
            canonical["setup_ok"] = False
            setup_error = f"{type(exc).__name__}: {exc}"
        finally:
            try:
                module.end()
                canonical["end_ok"] = True
            except Exception as exc:
                canonical["end_ok"] = False
                if not setup_error:
                    setup_error = f"end {type(exc).__name__}: {exc}"

    factory_summary: dict[str, Any] = {
        "factory_backend": None,
        "supports_live_spike_packet_gathering": None,
        "supports_dynamic_projections": None,
        "supports_runtime_weight_update": None,
        "uses_fixed_point": None,
        "supports_native_dopamine_stdp": None,
        "factory_error": "",
    }
    if canonical.get("import_ok"):
        try:
            factory = get_backend_factory(canonical["module"])
            factory_summary.update(
                {
                    "factory_backend": getattr(factory, "backend_name", None),
                    "supports_live_spike_packet_gathering": bool(
                        factory.supports_live_spike_packet_gathering()
                    ),
                    "supports_dynamic_projections": bool(
                        factory.supports_dynamic_projections()
                    ),
                    "supports_runtime_weight_update": bool(
                        factory.supports_runtime_weight_update()
                    ),
                    "uses_fixed_point": bool(factory.uses_fixed_point()),
                    "supports_native_dopamine_stdp": bool(
                        factory.supports_native_dopamine_stdp()
                    ),
                }
            )
        except Exception as exc:
            factory_summary["factory_error"] = f"{type(exc).__name__}: {exc}"

    sanitized_module_infos = []
    for info in module_infos:
        clean = {k: v for k, v in info.items() if k != "module"}
        sanitized_module_infos.append(clean)

    summary = {
        "spinnaker_prep_kind": "import/setup/factory readiness only",
        "hardware_run_attempted": False,
        "sim_run_attempted": False,
        "canonical_module": "pyNN.spiNNaker",
        "setup_smoke_requested": bool(args.spinnaker_setup_smoke),
        "module_infos": sanitized_module_infos,
        "setup_error": setup_error,
    }
    summary.update(factory_summary)

    alias_info = module_infos[1]
    criteria = [
        criterion(
            "pyNN.spiNNaker imports",
            canonical.get("import_ok"),
            "==",
            True,
            bool(canonical.get("import_ok")),
        ),
        criterion(
            "spynnaker.pyNN alias imports",
            alias_info.get("import_ok"),
            "==",
            True,
            bool(alias_info.get("import_ok")),
        ),
        criterion(
            "pyNN.spiNNaker setup/end smoke",
            {
                "setup_ok": canonical.get("setup_ok"),
                "end_ok": canonical.get("end_ok"),
            },
            "==",
            {"setup_ok": True, "end_ok": True},
            (
                not args.spinnaker_setup_smoke
                or (
                    canonical.get("setup_ok") is True
                    and canonical.get("end_ok") is True
                )
            ),
            "No hardware sim.run is attempted in this prep smoke.",
        ),
        criterion(
            "BackendFactory maps to sPyNNaker",
            factory_summary["factory_backend"],
            "==",
            "sPyNNaker",
            factory_summary["factory_backend"] == "sPyNNaker",
        ),
        criterion(
            "factory exposes live spike packet support",
            factory_summary["supports_live_spike_packet_gathering"],
            "==",
            True,
            factory_summary["supports_live_spike_packet_gathering"] is True,
        ),
        criterion(
            "factory marks dynamic projections unsupported",
            factory_summary["supports_dynamic_projections"],
            "==",
            False,
            factory_summary["supports_dynamic_projections"] is False,
            "This is expected for sPyNNaker; topology should be pre-allocated.",
        ),
        criterion(
            "factory marks fixed-point backend",
            factory_summary["uses_fixed_point"],
            "==",
            True,
            factory_summary["uses_fixed_point"] is True,
        ),
        criterion(
            "native neuromodulation STDP path available",
            factory_summary["supports_native_dopamine_stdp"],
            "==",
            True,
            factory_summary["supports_native_dopamine_stdp"] is True,
        ),
    ]
    status, failure_reason = pass_fail(criteria)
    print(f"[tier4.12] spinnaker_pynn_prep: {status.upper()} {failure_reason}", flush=True)
    return TestResult(
        name="spinnaker_pynn_prep",
        status=status,
        summary=summary,
        criteria=criteria,
        artifacts={},
        failure_reason=failure_reason,
    )


def plot_backend_summary(results: list[TestResult], path: Path) -> None:
    if plt is None:
        return
    backend_results = [
        r for r in results if "aggregate" in r.summary and r.name.endswith("_fixed_pattern")
    ]
    if not backend_results:
        return
    labels = [r.summary["aggregate"]["backend_key"] for r in backend_results]
    x = np.arange(len(labels))

    def values(key: str) -> np.ndarray:
        return np.asarray(
            [
                0.0
                if r.summary["aggregate"].get(key) is None
                else float(r.summary["aggregate"].get(key))
                for r in backend_results
            ],
            dtype=float,
        )

    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle("Tier 4.12 Backend Parity", fontsize=14, fontweight="bold")
    panels = [
        (axes[0, 0], values("all_accuracy_mean"), "overall accuracy", (0.0, 1.0)),
        (axes[0, 1], values("tail_accuracy_mean"), "tail accuracy", (0.0, 1.0)),
        (
            axes[1, 0],
            values("tail_prediction_target_corr_mean"),
            "tail prediction/target corr",
            (-1.0, 1.0),
        ),
        (axes[1, 1], values("runtime_seconds_mean"), "mean runtime seconds", None),
    ]
    colors = ["#1f6feb", "#2f855a", "#8250df", "#9a6700"]
    for (ax, panel_values, ylabel, ylim), color in zip(panels, colors):
        ax.bar(x, panel_values, color=color, alpha=0.82)
        ax.set_xticks(x)
        ax.set_xticklabels(labels)
        ax.set_ylabel(ylabel)
        if ylim is not None:
            ax.set_ylim(*ylim)
        ax.grid(axis="y", alpha=0.25)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(path, dpi=160)
    plt.close(fig)


def summary_rows(results: list[TestResult]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for result in results:
        row = {
            "test_name": result.name,
            "status": result.status,
            "failure_reason": result.failure_reason,
        }
        if "aggregate" in result.summary:
            agg = result.summary["aggregate"]
            row.update(
                {
                    "backend_key": agg.get("backend_key"),
                    "backend": agg.get("backend"),
                    "runs": agg.get("runs"),
                    "seeds": agg.get("seeds"),
                    "all_accuracy_mean": agg.get("all_accuracy_mean"),
                    "tail_accuracy_mean": agg.get("tail_accuracy_mean"),
                    "tail_prediction_target_corr_mean": agg.get(
                        "tail_prediction_target_corr_mean"
                    ),
                    "final_mean_readout_weight_mean": agg.get(
                        "final_mean_readout_weight_mean"
                    ),
                    "total_step_spikes_mean": agg.get("total_step_spikes_mean"),
                    "sim_run_failures_sum": agg.get("sim_run_failures_sum"),
                    "summary_read_failures_sum": agg.get("summary_read_failures_sum"),
                    "synthetic_fallbacks_sum": agg.get("synthetic_fallbacks_sum"),
                    "runtime_seconds_mean": agg.get("runtime_seconds_mean"),
                }
            )
        else:
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
        "# Tier 4.12 Backend Parity Findings",
        "",
        f"- Generated: `{utc_now()}`",
        f"- Overall status: **{overall}**",
        f"- Backends: `{', '.join(parse_backend_list(args.backends))}`",
        f"- Population size: `{args.population_size}` fixed polyps",
        f"- Seeds: `{', '.join(str(s) for s in seeds_from_args(args))}`",
        f"- Steps per run: `{args.steps}`",
        f"- Output directory: `{output_dir}`",
        "",
        "Tier 4.12 checks whether the fixed-pattern learning result survives movement from NEST to Brian2, while rejecting any synthetic spike fallback. The SpiNNaker item is a readiness prep smoke only; no hardware `sim.run()` is claimed here.",
        "",
        "## Artifact Index",
        "",
        f"- JSON manifest: `{manifest_path.name}`",
        f"- Summary CSV: `{summary_csv_path.name}`",
        "- Summary plot: `backend_parity_summary.png`",
    ]
    if MATPLOTLIB_ERROR:
        lines.append(f"- Plotting unavailable: `{MATPLOTLIB_ERROR}`")

    lines.extend(
        [
            "",
            "## Summary",
            "",
            "| Test | Status | Key metric | Diagnostics |",
            "| --- | --- | --- | --- |",
        ]
    )
    for result in results:
        if "aggregate" in result.summary:
            agg = result.summary["aggregate"]
            key = (
                f"all={markdown_value(agg.get('all_accuracy_mean'))}, "
                f"tail={markdown_value(agg.get('tail_accuracy_mean'))}, "
                f"corr={markdown_value(agg.get('tail_prediction_target_corr_mean'))}"
            )
            diag = (
                f"fallbacks={agg.get('synthetic_fallbacks_sum')}, "
                f"sim_fail={agg.get('sim_run_failures_sum')}, "
                f"read_fail={agg.get('summary_read_failures_sum')}"
            )
        elif result.name == "nest_brian2_parity":
            key = (
                f"tail_delta={markdown_value(result.summary.get('tail_accuracy_delta'))}, "
                f"corr_delta={markdown_value(result.summary.get('tail_corr_delta'))}"
            )
            diag = (
                f"runtime_ratio={markdown_value(result.summary.get('brian2_to_nest_runtime_ratio'))}"
            )
        elif result.name == "spinnaker_pynn_prep":
            key = (
                f"factory={markdown_value(result.summary.get('factory_backend'))}, "
                f"setup={markdown_value(result.summary.get('module_infos', [{}])[0].get('setup_ok'))}"
            )
            diag = "hardware_run_attempted=False"
        else:
            key = ""
            diag = ""
        lines.append(
            f"| `{result.name}` | **{result.status.upper()}** | {key} | {diag} |"
        )

    lines.extend(["", "## Criteria", ""])
    for result in results:
        lines.extend([f"### {result.name}", ""])
        lines.extend(["| Criterion | Value | Rule | Pass |", "| --- | --- | --- | --- |"])
        for item in result.criteria:
            lines.append(
                "| "
                f"{item['name']} | "
                f"{markdown_value(item['value'])} | "
                f"{item['operator']} {markdown_value(item['threshold'])} | "
                f"{'yes' if item['passed'] else 'no'} |"
            )
        if result.failure_reason:
            lines.extend(["", f"Failure: {result.failure_reason}"])
        lines.append("")

    lines.extend(
        [
            "## Interpretation",
            "",
            "- NEST is the baseline backend for this stage.",
            "- Brian2 must pass the same learning thresholds and stay within bounded NEST/Brian2 parity deltas.",
            "- `synthetic_fallbacks`, `sim_run_failures`, and `summary_read_failures` must remain zero for the real backend cases.",
            "- SpiNNaker PyNN readiness is not a hardware result; it verifies local module/setup/factory readiness before a later controlled `sim.run()` or board run.",
            "",
            "## Plots",
            "",
            "![backend_parity_summary](backend_parity_summary.png)",
            "",
        ]
    )
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


def parse_backend_list(value: str) -> list[str]:
    allowed = {"nest", "brian2", "mock"}
    backends = [item.strip().lower() for item in value.split(",") if item.strip()]
    invalid = [item for item in backends if item not in allowed]
    if invalid:
        raise ValueError(f"Unsupported backend(s): {', '.join(invalid)}")
    if not backends:
        raise ValueError("At least one backend is required")
    return backends


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Tier 4.12 CRA backend-parity tests.")
    parser.add_argument("--backends", default="nest,brian2")
    parser.add_argument("--steps", type=int, default=120)
    parser.add_argument("--base-seed", type=int, default=42)
    parser.add_argument("--seed-count", type=int, default=3)
    parser.add_argument("--population-size", type=int, default=8)
    parser.add_argument("--amplitude", type=float, default=DEFAULT_AMPLITUDE)
    parser.add_argument("--dt-seconds", type=float, default=DEFAULT_DT_SECONDS)
    parser.add_argument("--readout-lr", type=float, default=0.10)
    parser.add_argument("--delayed-readout-lr", type=float, default=0.05)
    parser.add_argument("--stop-on-fail", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=None)

    parser.add_argument("--all-accuracy-threshold", type=float, default=0.65)
    parser.add_argument("--tail-accuracy-threshold", type=float, default=0.75)
    parser.add_argument("--corr-threshold", type=float, default=0.60)
    parser.add_argument("--max-final-readout-weight", type=float, default=-0.05)
    parser.add_argument("--max-all-accuracy-delta", type=float, default=0.25)
    parser.add_argument("--max-tail-accuracy-delta", type=float, default=0.25)
    parser.add_argument("--max-corr-delta", type=float, default=0.50)

    parser.add_argument(
        "--spinnaker-prep",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument(
        "--spinnaker-setup-smoke",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument("--spinnaker-timestep", type=float, default=1.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.steps <= 0:
        parser.error("--steps must be positive")
    if args.seed_count <= 0:
        parser.error("--seed-count must be positive")
    if args.population_size <= 0:
        parser.error("--population-size must be positive")
    try:
        backend_keys = parse_backend_list(args.backends)
    except ValueError as exc:
        parser.error(str(exc))

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = args.output_dir or (
        ROOT / "controlled_test_output" / f"tier4_12_{timestamp}"
    )
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    results: list[TestResult] = []
    stopped_after: str | None = None

    for backend_key in backend_keys:
        result = run_backend_case(backend_key=backend_key, args=args, output_dir=output_dir)
        results.append(result)
        if args.stop_on_fail and not result.passed:
            stopped_after = result.name
            break

    if stopped_after is None and {"nest", "brian2"}.issubset(set(backend_keys)):
        parity = run_parity_comparison(results=results, args=args)
        results.append(parity)
        if args.stop_on_fail and not parity.passed:
            stopped_after = parity.name

    if stopped_after is None and args.spinnaker_prep:
        prep = run_spinnaker_prep(args)
        results.append(prep)
        if args.stop_on_fail and not prep.passed:
            stopped_after = prep.name

    summary_plot = output_dir / "backend_parity_summary.png"
    plot_backend_summary(results, summary_plot)
    summary_csv_path = output_dir / "tier4_12_summary.csv"
    manifest_path = output_dir / "tier4_12_results.json"
    report_path = output_dir / "tier4_12_report.md"
    write_csv(summary_csv_path, summary_rows(results))

    manifest = {
        "generated_at_utc": utc_now(),
        "tier": "Tier 4.12 - backend parity",
        "command": " ".join(sys.argv),
        "output_dir": str(output_dir),
        "backend_keys": backend_keys,
        "stopped_after": stopped_after,
        "thresholds": {
            "all_accuracy_threshold": args.all_accuracy_threshold,
            "tail_accuracy_threshold": args.tail_accuracy_threshold,
            "corr_threshold": args.corr_threshold,
            "max_final_readout_weight": args.max_final_readout_weight,
            "max_all_accuracy_delta": args.max_all_accuracy_delta,
            "max_tail_accuracy_delta": args.max_tail_accuracy_delta,
            "max_corr_delta": args.max_corr_delta,
        },
        "results": [r.to_dict() for r in results],
        "artifacts": {
            "summary_csv": str(summary_csv_path),
            "report_md": str(report_path),
            "summary_plot_png": str(summary_plot) if summary_plot.exists() else "",
        },
    }
    write_json(manifest_path, json_safe(manifest))
    write_report(
        path=report_path,
        results=results,
        manifest_path=manifest_path,
        summary_csv_path=summary_csv_path,
        output_dir=output_dir,
        stopped_after=stopped_after,
        args=args,
    )

    latest_path = ROOT / "controlled_test_output" / "tier4_12_latest_manifest.json"
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
