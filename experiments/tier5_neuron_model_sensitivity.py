#!/usr/bin/env python3
"""Tier 5.16 neuron model / parameter sensitivity diagnostic.

Tier 5.16 asks whether CRA's current evidence is brittle to one exact LIF
parameterization. The harness performs two bounded checks:

1. A direct LIF response probe on the selected PyNN backend, showing that the
   parameter variants are real neuron-parameter changes rather than inert labels.
2. A compact CRA task sweep across those variants, recording task metrics,
   backend fallback counters, and parameter propagation evidence.

Claim boundary: this is a reviewer-defense robustness diagnostic. Passing means
current CRA behavior survives a predeclared LIF parameter band on the tested
software backend. It is not a new frozen baseline, not hardware evidence, not a
custom-C/on-chip neuron model, and not a proof that richer neuron models are
unnecessary for future capabilities.
"""

from __future__ import annotations

import argparse
import copy
import csv
import json
import math
import os
import random
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

from coral_reef_spinnaker import Observation, Organism, ReefConfig, SensorControlAdapter  # noqa: E402
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
    write_csv,
    write_json,
)
from tier4_scaling import mean, min_value, seeds_from_args, stdev  # noqa: E402
from tier5_external_baselines import TaskStream, build_tasks, summarize_rows  # noqa: E402

TIER = "Tier 5.16 - Neuron Model / Parameter Sensitivity"
DEFAULT_TASKS = "fixed_pattern,delayed_cue,sensor_control"
DEFAULT_VARIANTS = (
    "default,v_thresh_low,v_thresh_high,tau_m_fast,tau_m_slow,"
    "tau_refrac_short,tau_refrac_long,cm_low,cm_high,tau_syn_fast,tau_syn_slow"
)
EPS = 1e-12


@dataclass(frozen=True)
class VariantSpec:
    name: str
    description: str
    parameters: dict[str, float]
    expected_direction: str
    is_default: bool = False


VARIANT_SPECS: dict[str, VariantSpec] = {
    "default": VariantSpec(
        name="default",
        description="canonical v1.9/v2.0-candidate LIF settings",
        parameters={},
        expected_direction="reference",
        is_default=True,
    ),
    "v_thresh_low": VariantSpec(
        name="v_thresh_low",
        description="lower firing threshold; easier spiking",
        parameters={"v_thresh": -58.0},
        expected_direction="higher excitability",
    ),
    "v_thresh_high": VariantSpec(
        name="v_thresh_high",
        description="higher firing threshold; harder spiking",
        parameters={"v_thresh": -52.0},
        expected_direction="lower excitability",
    ),
    "tau_m_fast": VariantSpec(
        name="tau_m_fast",
        description="shorter membrane time constant",
        parameters={"tau_m": 12.0},
        expected_direction="faster membrane response",
    ),
    "tau_m_slow": VariantSpec(
        name="tau_m_slow",
        description="longer membrane time constant",
        parameters={"tau_m": 32.0},
        expected_direction="slower membrane response",
    ),
    "tau_refrac_short": VariantSpec(
        name="tau_refrac_short",
        description="shorter absolute refractory period",
        parameters={"tau_refrac": 1.0},
        expected_direction="higher max firing rate",
    ),
    "tau_refrac_long": VariantSpec(
        name="tau_refrac_long",
        description="longer absolute refractory period",
        parameters={"tau_refrac": 5.0},
        expected_direction="lower max firing rate",
    ),
    "cm_low": VariantSpec(
        name="cm_low",
        description="lower membrane capacitance",
        parameters={"cm": 0.18},
        expected_direction="higher current sensitivity",
    ),
    "cm_high": VariantSpec(
        name="cm_high",
        description="higher membrane capacitance",
        parameters={"cm": 0.35},
        expected_direction="lower current sensitivity",
    ),
    "tau_syn_fast": VariantSpec(
        name="tau_syn_fast",
        description="faster excitatory/inhibitory synaptic current decay",
        parameters={"tau_syn_e": 2.5, "tau_syn_i": 2.5},
        expected_direction="faster synaptic filtering",
    ),
    "tau_syn_slow": VariantSpec(
        name="tau_syn_slow",
        description="slower excitatory/inhibitory synaptic current decay",
        parameters={"tau_syn_e": 10.0, "tau_syn_i": 10.0},
        expected_direction="slower synaptic filtering",
    ),
}


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


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.ndarray):
        return [json_safe(v) for v in value.tolist()]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        f = float(value)
        return None if math.isnan(f) or math.isinf(f) else f
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def parse_csv_list(raw: str, default: list[str]) -> list[str]:
    values = [item.strip() for chunk in str(raw).split(",") for item in chunk.split() if item.strip()]
    if not values or values == ["all"]:
        return list(default)
    return values


def selected_variants(args: argparse.Namespace) -> list[str]:
    allowed = list(VARIANT_SPECS)
    values = parse_csv_list(args.variants, allowed)
    unknown = sorted(set(values) - set(allowed))
    if unknown:
        raise ValueError(f"Unknown variant(s): {unknown}")
    if "default" not in values:
        values = ["default", *values]
    # Preserve order while dropping duplicates.
    ordered: list[str] = []
    for item in values:
        if item not in ordered:
            ordered.append(item)
    return ordered


def selected_tasks(args: argparse.Namespace) -> list[str]:
    allowed = ["fixed_pattern", "delayed_cue", "sensor_control", "hard_noisy_switching"]
    values = parse_csv_list(args.tasks, allowed)
    unknown = sorted(set(values) - set(allowed))
    if unknown:
        raise ValueError(f"Unknown task(s): {unknown}")
    return values


def apply_variant(cfg: ReefConfig, spec: VariantSpec) -> None:
    for key, value in spec.parameters.items():
        if not hasattr(cfg.network, key):
            raise AttributeError(f"NetworkConfig has no parameter {key!r}")
        setattr(cfg.network, key, float(value))


def make_config(*, seed: int, task: TaskStream, variant: str, args: argparse.Namespace) -> ReefConfig:
    cfg = ReefConfig.default()
    cfg.seed = int(seed)
    cfg.lifecycle.initial_population = int(args.cra_population_size)
    cfg.lifecycle.max_population_from_memory = False
    cfg.lifecycle.max_population_hard = int(args.cra_population_size)
    cfg.lifecycle.enable_reproduction = False
    cfg.lifecycle.enable_apoptosis = False
    cfg.lifecycle.enable_structural_plasticity = True
    cfg.measurement.stream_history_maxlen = max(int(task.steps) + 16, 128)
    cfg.spinnaker.sync_interval_steps = 0
    cfg.spinnaker.runtime_ms_per_step = float(args.runtime_ms_per_step)
    max_horizon = int(max(1, np.max(task.feedback_due_step - np.arange(task.steps)))) if np.any(task.feedback_due_step >= 0) else 1
    cfg.learning.evaluation_horizon_bars = max_horizon
    cfg.learning.readout_learning_rate = float(args.cra_readout_lr)
    cfg.learning.delayed_readout_learning_rate = float(args.cra_delayed_readout_lr)
    apply_variant(cfg, VARIANT_SPECS[variant])
    return cfg


def expected_params_for_variant(variant: str, cfg: ReefConfig) -> dict[str, float]:
    return {
        "tau_m": float(cfg.network.tau_m),
        "v_rest": float(cfg.network.v_rest),
        "v_reset": float(cfg.network.v_reset),
        "v_thresh": float(cfg.network.v_thresh),
        "tau_refrac": float(cfg.network.tau_refrac),
        "tau_syn_E": float(cfg.network.tau_syn_e),
        "tau_syn_I": float(cfg.network.tau_syn_i),
        "cm": float(cfg.network.cm),
    }


def parameter_propagation_rows(
    *,
    variant: str,
    cfg: ReefConfig,
    organism: Organism,
    task: str,
    seed: int,
) -> list[dict[str, Any]]:
    actual = dict(organism.polyp_population.neuron_type.base_params) if organism.polyp_population is not None else {}
    expected = expected_params_for_variant(variant, cfg)
    rows = []
    for key, expected_value in expected.items():
        actual_value = actual.get(key)
        rows.append(
            {
                "task": task,
                "seed": int(seed),
                "variant": variant,
                "parameter": key,
                "expected": expected_value,
                "actual": actual_value,
                "passed": actual_value is not None and abs(float(actual_value) - float(expected_value)) <= 1e-9,
            }
        )
    return rows


def run_cra_variant_case(
    task: TaskStream,
    *,
    variant: str,
    seed: int,
    args: argparse.Namespace,
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    random.seed(seed)
    np.random.seed(seed)
    sim, backend_name = load_backend(args.backend)
    setup_backend(sim, backend_name)
    cfg = make_config(seed=seed, task=task, variant=variant, args=args)
    organism = Organism(cfg, sim, use_default_trading_bridge=(task.domain != "sensor_control"))
    adapter = SensorControlAdapter()
    rows: list[dict[str, Any]] = []
    propagation: list[dict[str, Any]] = []
    started = time.perf_counter()
    backend_diagnostics: dict[str, Any] = {}
    try:
        organism.initialize(stream_keys=[task.domain])
        propagation = parameter_propagation_rows(variant=variant, cfg=cfg, organism=organism, task=task.name, seed=seed)
        bridge_present_after_init = bool(organism.trading_bridge is not None)
        for step in range(task.steps):
            sensory_value = float(task.sensory[step])
            target_value = float(task.current_target[step])
            if task.domain == "sensor_control":
                observation = Observation(
                    stream_id=task.domain,
                    x=np.asarray([sensory_value], dtype=float),
                    target=target_value,
                    metadata={"task": task.name, "step": step, "variant": variant},
                )
                metrics = organism.train_adapter_step(adapter, observation, dt_seconds=args.dt_seconds)
            else:
                metrics = organism.train_step(
                    market_return_1m=target_value,
                    sensory_return_1m=sensory_value,
                    dt_seconds=args.dt_seconds,
                )
            spike_total = 0
            if organism.spike_buffer:
                spike_total = int(sum(int(v) for v in organism.spike_buffer[-1].values()))
            prediction = float(metrics.colony_prediction)
            eval_sign = strict_sign(float(task.evaluation_target[step]))
            pred_sign = strict_sign(prediction)
            row = metrics.to_dict()
            row.update(
                {
                    "task": task.name,
                    "variant": variant,
                    "model": f"cra_{variant}",
                    "model_family": "CRA_parameter_sensitivity",
                    "backend": backend_name,
                    "seed": int(seed),
                    "step": int(step),
                    "sensory_return_1m": sensory_value,
                    "target_return_1m": target_value,
                    "target_signal_horizon": float(task.evaluation_target[step]),
                    "target_signal_sign": eval_sign,
                    "target_signal_nonzero": bool(task.evaluation_mask[step] and eval_sign != 0),
                    "prediction_sign": pred_sign,
                    "strict_direction_correct": bool(task.evaluation_mask[step] and pred_sign != 0 and pred_sign == eval_sign),
                    "feedback_due_step": int(task.feedback_due_step[step]),
                    "backend_spike_total": spike_total,
                    "trading_bridge_present_after_init": bridge_present_after_init,
                    "trading_bridge_present_after_step": bool(organism.trading_bridge is not None),
                }
            )
            rows.append(row)
        backend_diagnostics = organism.backend_diagnostics()
    except Exception as exc:
        backend_diagnostics = organism.backend_diagnostics()
        summary = {
            "task": task.name,
            "variant": variant,
            "seed": int(seed),
            "backend": backend_name,
            "status": "error",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "runtime_seconds": time.perf_counter() - started,
            "backend_diagnostics": backend_diagnostics,
            "config": cfg.to_dict(),
        }
        return rows, summary, propagation
    finally:
        organism.shutdown()
        end_backend(sim)

    summary = summarize_rows(rows)
    spike_totals = [float(r.get("backend_spike_total", 0.0) or 0.0) for r in rows]
    active_rows = [r for r in rows if bool(r.get("target_signal_nonzero", False))]
    summary.update(
        {
            "task": task.name,
            "variant": variant,
            "model": f"cra_{variant}",
            "model_family": "CRA_parameter_sensitivity",
            "backend": backend_name,
            "seed": int(seed),
            "status": "ok",
            "steps": task.steps,
            "runtime_seconds": time.perf_counter() - started,
            "population_size": int(args.cra_population_size),
            "mean_backend_spike_total": mean(spike_totals),
            "max_backend_spike_total": max(spike_totals) if spike_totals else None,
            "active_evaluation_rows": len(active_rows),
            "uses_trading_bridge": task.domain != "sensor_control",
            "trading_bridge_present_after_init": bool(rows[0]["trading_bridge_present_after_init"]) if rows else None,
            "trading_bridge_present_any_step": bool(any(bool(r["trading_bridge_present_after_step"]) for r in rows)),
            "backend_diagnostics": backend_diagnostics,
            "variant_parameters": VARIANT_SPECS[variant].parameters,
            "neuron_params": cfg.neuron_params,
            "config": cfg.to_dict(),
            "task_metadata": task.metadata,
        }
    )
    return rows, summary, propagation


def aggregate_summaries(summaries: list[dict[str, Any]]) -> dict[str, Any]:
    if not summaries:
        return {}
    first = summaries[0]
    keys = [
        "tail_accuracy",
        "all_accuracy",
        "early_accuracy",
        "accuracy_improvement",
        "prediction_target_corr",
        "tail_prediction_target_corr",
        "mean_abs_prediction",
        "mean_backend_spike_total",
        "max_backend_spike_total",
        "runtime_seconds",
        "evaluation_count",
    ]
    out: dict[str, Any] = {
        "task": first.get("task"),
        "variant": first.get("variant"),
        "backend": first.get("backend"),
        "runs": len(summaries),
        "seeds": [int(s.get("seed")) for s in summaries if s.get("seed") is not None],
        "variant_parameters": first.get("variant_parameters", {}),
        "status_count_ok": int(sum(1 for s in summaries if s.get("status") == "ok")),
        "status_count_error": int(sum(1 for s in summaries if s.get("status") != "ok")),
    }
    for key in keys:
        vals = [s.get(key) for s in summaries if s.get(key) is not None]
        out[f"{key}_mean"] = mean(vals)
        out[f"{key}_std"] = stdev(vals)
        out[f"{key}_min"] = min_value(vals)
    for diag_key in ["sim_run_failures", "summary_read_failures", "synthetic_fallbacks"]:
        out[diag_key] = int(sum(int(s.get("backend_diagnostics", {}).get(diag_key, 0) or 0) for s in summaries))
    return out


def build_comparisons(aggregates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    by_task: dict[str, dict[str, dict[str, Any]]] = {}
    for agg in aggregates:
        by_task.setdefault(str(agg.get("task")), {})[str(agg.get("variant"))] = agg
    for task, variants in sorted(by_task.items()):
        default = variants.get("default")
        if default is None:
            continue
        default_tail = float(default.get("tail_accuracy_mean") or 0.0)
        default_corr = default.get("prediction_target_corr_mean")
        default_spikes = default.get("mean_backend_spike_total_mean")
        for variant, agg in sorted(variants.items()):
            if variant == "default":
                continue
            variant_tail = float(agg.get("tail_accuracy_mean") or 0.0)
            variant_corr = agg.get("prediction_target_corr_mean")
            variant_spikes = agg.get("mean_backend_spike_total_mean")
            rows.append(
                {
                    "task": task,
                    "variant": variant,
                    "default_tail_accuracy_mean": default.get("tail_accuracy_mean"),
                    "variant_tail_accuracy_mean": agg.get("tail_accuracy_mean"),
                    "tail_delta_vs_default": variant_tail - default_tail,
                    "default_prediction_target_corr_mean": default_corr,
                    "variant_prediction_target_corr_mean": variant_corr,
                    "corr_delta_vs_default": None if default_corr is None or variant_corr is None else float(variant_corr) - float(default_corr),
                    "default_mean_spike_total": default_spikes,
                    "variant_mean_spike_total": variant_spikes,
                    "spike_delta_vs_default": None if default_spikes is None or variant_spikes is None else float(variant_spikes) - float(default_spikes),
                    "sim_run_failures": agg.get("sim_run_failures"),
                    "summary_read_failures": agg.get("summary_read_failures"),
                    "synthetic_fallbacks": agg.get("synthetic_fallbacks"),
                    "variant_parameters": agg.get("variant_parameters", {}),
                }
            )
    return rows


def run_lif_response_probe(args: argparse.Namespace, variants: list[str]) -> list[dict[str, Any]]:
    if args.skip_response_probe:
        return []
    sim, backend_name = load_backend(args.backend)
    setup_backend(sim, backend_name)
    rows: list[dict[str, Any]] = []
    try:
        currents = [float(x) for x in args.response_probe_currents.split(",") if x.strip()]
        populations = []
        for variant in variants:
            cfg = ReefConfig.default()
            apply_variant(cfg, VARIANT_SPECS[variant])
            params = cfg.neuron_params
            cell = sim.IF_curr_exp(
                tau_m=params["tau_m"],
                v_rest=params["v_rest"],
                v_reset=params["v_reset"],
                v_thresh=params["v_thresh"],
                tau_refrac=params["tau_refrac"],
                tau_syn_E=params["tau_syn_E"],
                tau_syn_I=params["tau_syn_I"],
                cm=params["cm"],
                i_offset=0.0,
            )
            pop = sim.Population(len(currents), cell, label=f"tier5_16_{variant}")
            pop.set(i_offset=currents)
            pop.record("spikes")
            populations.append((variant, cfg, pop, currents))
        sim.run(float(args.response_probe_ms))
        for variant, cfg, pop, currents in populations:
            spiketrains = pop.get_data("spikes", clear=True).segments[-1].spiketrains
            counts = [int(len(st)) for st in spiketrains]
            monotonic = all(counts[i] <= counts[i + 1] for i in range(len(counts) - 1))
            for current, count in zip(currents, counts):
                rows.append(
                    {
                        "backend": backend_name,
                        "variant": variant,
                        "current_nA": current,
                        "runtime_ms": float(args.response_probe_ms),
                        "spike_count": count,
                        "firing_rate_hz": float(count) / float(args.response_probe_ms) * 1000.0,
                        "monotonic_for_variant": monotonic,
                        "variant_parameters": VARIANT_SPECS[variant].parameters,
                        "neuron_params": cfg.neuron_params,
                    }
                )
    finally:
        end_backend(sim)
    return rows


def summary_csv_rows(aggregates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for agg in aggregates:
        rows.append(
            {
                "task": agg.get("task"),
                "variant": agg.get("variant"),
                "backend": agg.get("backend"),
                "runs": agg.get("runs"),
                "tail_accuracy_mean": agg.get("tail_accuracy_mean"),
                "tail_accuracy_std": agg.get("tail_accuracy_std"),
                "all_accuracy_mean": agg.get("all_accuracy_mean"),
                "prediction_target_corr_mean": agg.get("prediction_target_corr_mean"),
                "tail_prediction_target_corr_mean": agg.get("tail_prediction_target_corr_mean"),
                "mean_backend_spike_total_mean": agg.get("mean_backend_spike_total_mean"),
                "max_backend_spike_total_mean": agg.get("max_backend_spike_total_mean"),
                "runtime_seconds_mean": agg.get("runtime_seconds_mean"),
                "sim_run_failures": agg.get("sim_run_failures"),
                "summary_read_failures": agg.get("summary_read_failures"),
                "synthetic_fallbacks": agg.get("synthetic_fallbacks"),
                "variant_parameters": agg.get("variant_parameters"),
            }
        )
    return rows


def plot_robustness(aggregates: list[dict[str, Any]], path: Path) -> None:
    if plt is None or not aggregates:
        return
    variants = [v for v in VARIANT_SPECS if any(a.get("variant") == v for a in aggregates)]
    tasks = sorted({str(a.get("task")) for a in aggregates})
    data = np.full((len(tasks), len(variants)), np.nan, dtype=float)
    for i, task in enumerate(tasks):
        for j, variant in enumerate(variants):
            agg = next((a for a in aggregates if a.get("task") == task and a.get("variant") == variant), None)
            if agg is not None and agg.get("tail_accuracy_mean") is not None:
                data[i, j] = float(agg.get("tail_accuracy_mean"))
    fig, ax = plt.subplots(figsize=(max(12, len(variants) * 0.9), 5.5))
    im = ax.imshow(data, vmin=0.0, vmax=1.0, cmap="viridis")
    ax.set_title("Tier 5.16 CRA Tail Accuracy Across LIF Parameter Variants")
    ax.set_xticks(range(len(variants)))
    ax.set_xticklabels([v.replace("_", "\n") for v in variants], rotation=35, ha="right", fontsize=8)
    ax.set_yticks(range(len(tasks)))
    ax.set_yticklabels([t.replace("_", "\n") for t in tasks])
    for i in range(len(tasks)):
        for j in range(len(variants)):
            value = data[i, j]
            label = "NA" if not np.isfinite(value) else f"{value:.2f}"
            ax.text(j, i, label, ha="center", va="center", color="white" if np.isfinite(value) and value < 0.55 else "black", fontsize=8)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_response_probe(rows: list[dict[str, Any]], path: Path) -> None:
    if plt is None or not rows:
        return
    variants = []
    for row in rows:
        if row["variant"] not in variants:
            variants.append(row["variant"])
    fig, ax = plt.subplots(figsize=(10, 6))
    for variant in variants:
        sub = [r for r in rows if r["variant"] == variant]
        xs = [float(r["current_nA"]) for r in sub]
        ys = [float(r["firing_rate_hz"]) for r in sub]
        ax.plot(xs, ys, marker="o", label=variant)
    ax.set_title("Tier 5.16 LIF Response Probe")
    ax.set_xlabel("i_offset current (nA)")
    ax.set_ylabel("firing rate (Hz)")
    ax.grid(alpha=0.25)
    ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def write_report(
    path: Path,
    result: TestResult,
    aggregates: list[dict[str, Any]],
    comparisons: list[dict[str, Any]],
    response_rows: list[dict[str, Any]],
    args: argparse.Namespace,
    output_dir: Path,
) -> None:
    overall = "PASS" if result.passed else "FAIL"
    lines = [
        "# Tier 5.16 Neuron Model / Parameter Sensitivity Findings",
        "",
        f"- Generated: `{utc_now()}`",
        f"- Status: **{overall}**",
        f"- Backend: `{result.summary.get('backend')}`",
        f"- Seeds: `{', '.join(str(s) for s in seeds_from_args(args))}`",
        f"- Tasks: `{', '.join(selected_tasks(args))}`",
        f"- Variants: `{', '.join(selected_variants(args))}`",
        f"- Output directory: `{output_dir}`",
        "",
        "Tier 5.16 tests whether CRA behavior is brittle to one exact LIF neuron parameterization.",
        "",
        "## Claim Boundary",
        "",
        "- Reviewer-defense robustness diagnostic only; not a new frozen baseline by itself.",
        "- Software backend evidence only; not SpiNNaker hardware or custom-C/on-chip neuron-model evidence.",
        "- Passing means tested CRA behavior survives the predeclared parameter band; it does not prove richer neuron models are unnecessary.",
        "- Synaptic-tau variants are propagation/no-collapse checks here; the direct current response probe primarily audits membrane/refractory excitability.",
        "",
        "## Variant Protocol",
        "",
        "| Variant | Parameters | Expected direction |",
        "| --- | --- | --- |",
    ]
    for name in selected_variants(args):
        spec = VARIANT_SPECS[name]
        lines.append(f"| `{name}` | `{json.dumps(spec.parameters, sort_keys=True)}` | {spec.expected_direction} |")
    lines.extend(
        [
            "",
            "## Aggregate Summary",
            "",
            "| Task | Variant | Tail acc | Overall acc | Corr | Spike total | Runtime s | Failures | Fallbacks |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for agg in aggregates:
        failures = int(agg.get("sim_run_failures") or 0) + int(agg.get("summary_read_failures") or 0)
        lines.append(
            "| "
            f"{agg.get('task')} | `{agg.get('variant')}` | "
            f"{markdown_value(agg.get('tail_accuracy_mean'))} | "
            f"{markdown_value(agg.get('all_accuracy_mean'))} | "
            f"{markdown_value(agg.get('prediction_target_corr_mean'))} | "
            f"{markdown_value(agg.get('mean_backend_spike_total_mean'))} | "
            f"{markdown_value(agg.get('runtime_seconds_mean'))} | "
            f"{failures} | "
            f"{markdown_value(agg.get('synthetic_fallbacks'))} |"
        )
    lines.extend(
        [
            "",
            "## Comparisons Against Default",
            "",
            "| Task | Variant | Tail delta | Corr delta | Spike delta |",
            "| --- | --- | ---: | ---: | ---: |",
        ]
    )
    for row in comparisons:
        lines.append(
            "| "
            f"{row['task']} | `{row['variant']}` | "
            f"{markdown_value(row.get('tail_delta_vs_default'))} | "
            f"{markdown_value(row.get('corr_delta_vs_default'))} | "
            f"{markdown_value(row.get('spike_delta_vs_default'))} |"
        )
    if response_rows:
        lines.extend(
            [
                "",
                "## LIF Response Probe",
                "",
                "| Variant | Current nA | Spikes | Rate Hz | Monotonic |",
                "| --- | ---: | ---: | ---: | --- |",
            ]
        )
        for row in response_rows:
            lines.append(
                "| "
                f"`{row['variant']}` | {markdown_value(row['current_nA'])} | "
                f"{markdown_value(row['spike_count'])} | {markdown_value(row['firing_rate_hz'])} | "
                f"{'yes' if row.get('monotonic_for_variant') else 'no'} |"
            )
    lines.extend(["", "## Criteria", "", "| Criterion | Value | Rule | Pass | Note |", "| --- | --- | --- | --- | --- |"])
    for item in result.criteria:
        lines.append(
            "| "
            f"{item['name']} | "
            f"{markdown_value(item['value'])} | "
            f"{item['operator']} {markdown_value(item['threshold'])} | "
            f"{'yes' if item['passed'] else 'no'} | "
            f"{item.get('note', '')} |"
        )
    if result.failure_reason:
        lines.extend(["", f"Failure: {result.failure_reason}"])
    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            "- `tier5_16_results.json`: machine-readable manifest.",
            "- `tier5_16_summary.csv`: aggregate task/variant metrics.",
            "- `tier5_16_comparisons.csv`: per-variant deltas against default.",
            "- `tier5_16_parameter_propagation.csv`: config-to-neuron-factory propagation audit.",
            "- `tier5_16_lif_response_probe.csv`: direct backend LIF excitability probe.",
            "- `*_timeseries.csv`: per-run step traces.",
            "",
            "## Plots",
            "",
            "![robustness_matrix](tier5_16_robustness_matrix.png)",
            "",
            "![lif_response_probe](tier5_16_lif_response_probe.png)",
            "",
        ]
    )
    if MATPLOTLIB_ERROR:
        lines.append(f"Plotting unavailable: `{MATPLOTLIB_ERROR}`")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def run_tier(args: argparse.Namespace, output_dir: Path) -> TestResult:
    variants = selected_variants(args)
    tasks_arg = ",".join(selected_tasks(args))
    all_artifacts: dict[str, str] = {}
    summaries_by_cell: dict[tuple[str, str], list[dict[str, Any]]] = {}
    propagation_rows: list[dict[str, Any]] = []

    response_rows = run_lif_response_probe(args, variants)
    response_csv = output_dir / "tier5_16_lif_response_probe.csv"
    write_csv(response_csv, response_rows)
    all_artifacts["lif_response_probe_csv"] = str(response_csv)

    task_args = copy.copy(args)
    task_args.tasks = tasks_arg
    for seed in seeds_from_args(args):
        tasks = build_tasks(task_args, seed=args.task_seed + seed)
        for task in tasks:
            for variant in variants:
                print(f"[tier5.16] backend={args.backend} task={task.name} variant={variant} seed={seed}", flush=True)
                rows, summary, run_propagation = run_cra_variant_case(task, variant=variant, seed=seed, args=args)
                propagation_rows.extend(run_propagation)
                csv_path = output_dir / f"{task.name}_{variant}_seed{seed}_timeseries.csv"
                write_csv(csv_path, rows)
                all_artifacts[f"{task.name}_{variant}_seed{seed}_timeseries_csv"] = str(csv_path)
                summaries_by_cell.setdefault((task.name, variant), []).append(summary)
                if args.stop_on_fail and summary.get("status") != "ok":
                    break

    aggregates = [aggregate_summaries(summaries) for _, summaries in sorted(summaries_by_cell.items())]
    comparisons = build_comparisons(aggregates)
    summary_csv = output_dir / "tier5_16_summary.csv"
    comparisons_csv = output_dir / "tier5_16_comparisons.csv"
    propagation_csv = output_dir / "tier5_16_parameter_propagation.csv"
    protocol_json = output_dir / "tier5_16_protocol.json"
    matrix_plot = output_dir / "tier5_16_robustness_matrix.png"
    response_plot = output_dir / "tier5_16_lif_response_probe.png"
    write_csv(summary_csv, summary_csv_rows(aggregates))
    write_csv(comparisons_csv, comparisons)
    write_csv(propagation_csv, propagation_rows)
    write_json(
        protocol_json,
        {
            "generated_at_utc": utc_now(),
            "tier": TIER,
            "claim_boundary": "Software neuron-parameter robustness diagnostic; not hardware/custom-C/on-chip neuron evidence and not a freeze gate by itself.",
            "backend": args.backend,
            "variants": {name: VARIANT_SPECS[name].__dict__ for name in variants},
            "tasks": selected_tasks(args),
            "seeds": seeds_from_args(args),
            "same_task_stream_across_variants": True,
            "same_feedback_due_steps_across_variants": True,
            "prediction_before_feedback": True,
            "parameter_propagation_audited": True,
            "lif_response_probe_currents_nA": [float(x) for x in args.response_probe_currents.split(",") if x.strip()],
        },
    )
    plot_robustness(aggregates, matrix_plot)
    plot_response_probe(response_rows, response_plot)
    all_artifacts.update(
        {
            "summary_csv": str(summary_csv),
            "comparisons_csv": str(comparisons_csv),
            "parameter_propagation_csv": str(propagation_csv),
            "protocol_json": str(protocol_json),
            "robustness_matrix_png": str(matrix_plot),
            "lif_response_probe_png": str(response_plot),
        }
    )

    expected_runs = len(seeds_from_args(args)) * len(selected_tasks(args)) * len(variants)
    observed_runs = int(sum(int(agg.get("runs") or 0) for agg in aggregates))
    run_errors = int(sum(int(agg.get("status_count_error") or 0) for agg in aggregates))
    sim_failures = int(sum(int(agg.get("sim_run_failures") or 0) for agg in aggregates))
    read_failures = int(sum(int(agg.get("summary_read_failures") or 0) for agg in aggregates))
    fallbacks = int(sum(int(agg.get("synthetic_fallbacks") or 0) for agg in aggregates))
    propagation_failures = int(sum(1 for row in propagation_rows if not bool(row.get("passed"))))

    functional_cells = [
        agg for agg in aggregates
        if (agg.get("tail_accuracy_mean") is not None and float(agg.get("tail_accuracy_mean") or 0.0) >= args.min_functional_tail_accuracy)
    ]
    functional_fraction = 0.0 if not aggregates else len(functional_cells) / len(aggregates)
    default_cells = [agg for agg in aggregates if agg.get("variant") == "default"]
    default_min_tail = min([float(agg.get("tail_accuracy_mean") or 0.0) for agg in default_cells], default=0.0)
    collapse_rows = [
        row for row in comparisons
        if (
            (row.get("tail_delta_vs_default") is not None and float(row["tail_delta_vs_default"]) <= -abs(args.max_tail_drop_vs_default))
            or float(row.get("variant_tail_accuracy_mean") or 0.0) < args.collapse_tail_floor
        )
    ]
    monotonic_variants = sorted({row["variant"] for row in response_rows if bool(row.get("monotonic_for_variant"))})
    response_variants = sorted({row["variant"] for row in response_rows})
    response_monotonic_fraction = 1.0 if not response_variants else len(monotonic_variants) / len(response_variants)

    criteria = [
        criterion("expected runs observed", observed_runs, "==", expected_runs, observed_runs == expected_runs),
        criterion("case run errors", run_errors, "==", 0, run_errors == 0),
        criterion("parameter propagation failures", propagation_failures, "==", 0, propagation_failures == 0),
        criterion("sim.run failures", sim_failures, "==", 0, sim_failures == 0),
        criterion("summary read failures", read_failures, "==", 0, read_failures == 0),
        criterion("synthetic fallbacks", fallbacks, "==", 0, fallbacks == 0, "For mock smoke this should still be zero because MockPopulation returns spike data."),
        criterion("default minimum tail accuracy", default_min_tail, ">=", args.min_default_tail_accuracy, default_min_tail >= args.min_default_tail_accuracy),
        criterion("functional cell fraction", functional_fraction, ">=", args.min_functional_cell_fraction, functional_fraction >= args.min_functional_cell_fraction),
        criterion("collapse count", len(collapse_rows), "<=", args.max_collapse_count, len(collapse_rows) <= args.max_collapse_count),
        criterion("response probe monotonic fraction", response_monotonic_fraction, ">=", args.min_response_monotonic_fraction, response_monotonic_fraction >= args.min_response_monotonic_fraction, "Direct current response should be nondecreasing across injected current levels."),
    ]
    status, failure_reason = pass_fail(criteria)
    summary = {
        "tier": TIER,
        "backend": args.backend,
        "tasks": selected_tasks(args),
        "variants": variants,
        "seeds": seeds_from_args(args),
        "expected_runs": expected_runs,
        "observed_runs": observed_runs,
        "aggregate_cells": len(aggregates),
        "functional_cell_count": len(functional_cells),
        "functional_cell_fraction": functional_fraction,
        "default_min_tail_accuracy": default_min_tail,
        "collapse_count": len(collapse_rows),
        "run_errors": run_errors,
        "sim_run_failures": sim_failures,
        "summary_read_failures": read_failures,
        "synthetic_fallbacks": fallbacks,
        "propagation_failures": propagation_failures,
        "response_probe_variants": response_variants,
        "response_probe_monotonic_fraction": response_monotonic_fraction,
        "claim_boundary": "Software neuron-parameter robustness diagnostic; not hardware/custom-C/on-chip neuron evidence and not a freeze gate by itself.",
    }
    result = TestResult(TIER, status, summary, criteria, all_artifacts, failure_reason)
    write_report(output_dir / "tier5_16_report.md", result, aggregates, comparisons, response_rows, args, output_dir)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Tier 5.16 neuron model / parameter sensitivity diagnostics.")
    parser.add_argument("--backend", choices=["nest", "brian2", "mock"], default="nest")
    parser.add_argument("--tasks", default=DEFAULT_TASKS)
    parser.add_argument("--variants", default=DEFAULT_VARIANTS)
    parser.add_argument("--steps", type=int, default=180)
    parser.add_argument("--base-seed", type=int, default=42)
    parser.add_argument("--seed-count", type=int, default=2)
    parser.add_argument("--task-seed", type=int, default=5160)
    parser.add_argument("--amplitude", type=float, default=DEFAULT_AMPLITUDE)
    parser.add_argument("--dt-seconds", type=float, default=DEFAULT_DT_SECONDS)
    parser.add_argument("--runtime-ms-per-step", type=float, default=1000.0)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--stop-on-fail", action="store_true")
    parser.add_argument("--smoke", action="store_true")

    parser.add_argument("--cra-population-size", type=int, default=8)
    parser.add_argument("--cra-readout-lr", type=float, default=0.10)
    parser.add_argument("--cra-delayed-readout-lr", type=float, default=0.20)

    parser.add_argument("--delay", type=int, default=5)
    parser.add_argument("--period", type=int, default=8)
    parser.add_argument("--sensor-delay", type=int, default=3)
    parser.add_argument("--sensor-period", type=int, default=6)
    parser.add_argument("--min-delay", type=int, default=3)
    parser.add_argument("--max-delay", type=int, default=5)
    parser.add_argument("--hard-period", type=int, default=7)
    parser.add_argument("--noise-prob", type=float, default=0.20)
    parser.add_argument("--sensory-noise-fraction", type=float, default=0.25)
    parser.add_argument("--min-switch-interval", type=int, default=32)
    parser.add_argument("--max-switch-interval", type=int, default=48)

    parser.add_argument("--response-probe-ms", type=float, default=250.0)
    parser.add_argument("--response-probe-currents", default="0.0,0.1,0.2,0.4")
    parser.add_argument("--skip-response-probe", action="store_true")

    parser.add_argument("--min-default-tail-accuracy", type=float, default=0.70)
    parser.add_argument("--min-functional-tail-accuracy", type=float, default=0.55)
    parser.add_argument("--min-functional-cell-fraction", type=float, default=0.80)
    parser.add_argument("--max-tail-drop-vs-default", type=float, default=0.35)
    parser.add_argument("--collapse-tail-floor", type=float, default=0.45)
    parser.add_argument("--max-collapse-count", type=int, default=3)
    parser.add_argument("--min-response-monotonic-fraction", type=float, default=1.0)
    return parser


def apply_smoke_defaults(args: argparse.Namespace) -> None:
    if not args.smoke:
        return
    if args.tasks == DEFAULT_TASKS:
        args.tasks = "fixed_pattern,delayed_cue"
    if args.variants == DEFAULT_VARIANTS:
        args.variants = "default,v_thresh_high,tau_m_slow,tau_refrac_long"
    args.steps = min(args.steps, 80)
    args.seed_count = min(args.seed_count, 1)
    args.min_default_tail_accuracy = min(args.min_default_tail_accuracy, 0.50)
    args.min_functional_cell_fraction = min(args.min_functional_cell_fraction, 0.50)
    args.max_collapse_count = max(args.max_collapse_count, 99)
    if args.backend == "mock":
        args.min_response_monotonic_fraction = 0.0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    apply_smoke_defaults(args)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = args.output_dir or (ROOT / "controlled_test_output" / f"tier5_16_{timestamp}")
    output_dir.mkdir(parents=True, exist_ok=True)

    result = run_tier(args, output_dir)
    manifest_path = output_dir / "tier5_16_results.json"
    report_path = output_dir / "tier5_16_report.md"
    manifest = {
        "tier": TIER,
        "generated_at_utc": utc_now(),
        "output_dir": str(output_dir),
        "command": " ".join(sys.argv),
        "summary": result.summary,
        "criteria": result.criteria,
        "status": result.status,
        "failure_reason": result.failure_reason,
        "artifacts": {**result.artifacts, "manifest_json": str(manifest_path), "report_md": str(report_path)},
    }
    write_json(manifest_path, manifest)
    print(json.dumps({"status": result.status, "output_dir": str(output_dir), "summary": result.summary}, indent=2, default=json_safe))
    if args.stop_on_fail and not result.passed:
        return 1
    return 0 if result.passed else 1


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
