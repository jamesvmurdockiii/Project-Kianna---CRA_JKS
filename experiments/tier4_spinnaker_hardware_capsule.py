#!/usr/bin/env python3
"""Prepare or run the Tier 4.13 SpiNNaker hardware capsule.

Tier 4.13 is intentionally separate from Tier 4.12:

- Tier 4.12: local backend parity, NEST <-> Brian2, plus sPyNNaker readiness.
- Tier 4.13: real SpiNNaker hardware capsule, normally executed through an
  EBRAINS/JobManager allocation.

This harness has three modes:

``prepare``
    Build a reproducible capsule directory with config, JobManager run
    instructions, local environment facts, and a report. This does not claim a
    hardware result.

``run-hardware``
    Run the minimal fixed-pattern CRA task using ``pyNN.spiNNaker``. By default
    this refuses to run if the local sPyNNaker config looks like a virtual board
    rather than real hardware.

``ingest``
    Ingest a completed hardware run manifest from a JobManager result directory
    and write a local comparison/report bundle.
"""

from __future__ import annotations

import argparse
import configparser
import csv
import json
import math
import os
import platform
import random
import shutil
import sys
import time
import traceback
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
from coral_reef_spinnaker.spinnaker_compat import (  # noqa: E402
    apply_spinnaker_numpy2_compat_patches,
)
from tier2_learning import (  # noqa: E402
    DEFAULT_AMPLITUDE,
    DEFAULT_DT_SECONDS,
    criterion,
    fixed_pattern_task,
    json_safe,
    markdown_value,
    pass_fail,
    plot_case,
    strict_sign,
    summarize_rows,
    write_csv,
    write_json,
    utc_now,
)
from tier4_scaling import alive_readout_weights, alive_trophic_health  # noqa: E402


NONE_LIKE = {"", "none", "null", "false", "0"}


class BackendFallbackError(RuntimeError):
    """Raised when the hardware run detects a backend fallback."""

    def __init__(self, step: int, diagnostics: dict[str, Any]) -> None:
        self.step = int(step)
        self.diagnostics = diagnostics
        stage = diagnostics.get("last_backend_failure_stage") or "unknown"
        exc_type = diagnostics.get("last_backend_exception_type") or "unknown"
        detail = diagnostics.get("last_sim_run_error") or exc_type
        counters = (
            f"sim_run_failures={diagnostics.get('sim_run_failures')}, "
            f"summary_read_failures={diagnostics.get('summary_read_failures')}, "
            f"synthetic_fallbacks={diagnostics.get('synthetic_fallbacks')}"
        )
        inner_traceback = diagnostics.get("last_backend_traceback") or ""
        message = (
            f"backend fallback detected at step {step}: "
            f"stage={stage}, exception={exc_type}, {counters}, error={detail}"
        )
        if inner_traceback:
            message += f"\n\nInner backend traceback:\n{inner_traceback}"
        super().__init__(message)


def read_spynnaker_config() -> dict[str, Any]:
    path = Path.home() / ".spynnaker.cfg"
    info: dict[str, Any] = {
        "path": str(path),
        "exists": path.exists(),
        "machineName": None,
        "version": None,
        "spalloc_server": None,
        "remote_spinnaker_url": None,
        "spalloc_port": None,
        "spalloc_user": None,
        "spalloc_group": None,
        "virtual_board": None,
        "width": None,
        "height": None,
        "mode": None,
    }
    if not path.exists():
        return info

    parser = configparser.ConfigParser()
    parser.read(path)
    if parser.has_section("Machine"):
        machine = parser["Machine"]
        for key in [
            "machineName",
            "version",
            "spalloc_server",
            "remote_spinnaker_url",
            "spalloc_port",
            "spalloc_user",
            "spalloc_group",
            "virtual_board",
            "width",
            "height",
        ]:
            info[key] = machine.get(key, fallback=None)
    if parser.has_section("Mode"):
        info["mode"] = parser["Mode"].get("mode", fallback=None)
    return info


def clean_config_value(value: Any) -> str:
    return "" if value is None else str(value).strip()


def truthy(value: Any) -> bool:
    return clean_config_value(value).lower() in {"1", "true", "yes", "on"}


def has_real_hardware_target(config_info: dict[str, Any], hostname: str | None) -> bool:
    if hostname:
        return True
    virtual_board = config_info.get("virtual_board")
    if virtual_board is not None and truthy(virtual_board):
        return False
    machine_name = clean_config_value(config_info.get("machineName"))
    spalloc_server = clean_config_value(config_info.get("spalloc_server"))
    remote_spinnaker_url = clean_config_value(config_info.get("remote_spinnaker_url"))
    return (
        machine_name.lower() not in NONE_LIKE
        or spalloc_server.lower() not in NONE_LIKE
        or remote_spinnaker_url.lower() not in NONE_LIKE
        or clean_config_value(os.environ.get("SPINNAKER_MACHINE")).lower() not in NONE_LIKE
        or clean_config_value(os.environ.get("SPALLOC_SERVER")).lower() not in NONE_LIKE
        or clean_config_value(os.environ.get("REMOTE_SPINNAKER_URL")).lower() not in NONE_LIKE
    )


def module_status(name: str) -> dict[str, Any]:
    try:
        module = __import__(name, fromlist=["*"])
        return {
            "name": name,
            "ok": True,
            "version": getattr(module, "__version__", None),
            "path": getattr(module, "__file__", None),
            "error": "",
        }
    except Exception as exc:
        return {
            "name": name,
            "ok": False,
            "version": None,
            "path": None,
            "error": f"{type(exc).__name__}: {exc}",
        }


def collect_environment(args: argparse.Namespace) -> dict[str, Any]:
    config_info = read_spynnaker_config()
    return {
        "generated_at_utc": utc_now(),
        "hostname": platform.node(),
        "platform": platform.platform(),
        "python": sys.version,
        "jobmanager_cli": shutil.which("jobmanager"),
        "spalloc_cli": shutil.which("spalloc"),
        "ybug_cli": shutil.which("ybug"),
        "env_flags": {
            key: bool(os.environ.get(key))
            for key in [
                "JOB_ID",
                "SLURM_JOB_ID",
                "EBRAINS_JOB_ID",
                "SPINNAKER_MACHINE",
                "SPALLOC_SERVER",
                "REMOTE_SPINNAKER_URL",
            ]
        },
        "spynnaker_config": config_info,
        "hardware_target_configured": has_real_hardware_target(
            config_info,
            args.spinnaker_hostname,
        ),
        "modules": [
            module_status("pyNN.spiNNaker"),
            module_status("spynnaker.pyNN"),
            module_status("spalloc_client"),
            module_status("spinnman"),
            module_status("spinn_front_end_common"),
        ],
    }


def collect_recent_spinnaker_reports(
    output_dir: Path,
    started_epoch: float,
    *,
    max_reports: int = 4,
) -> dict[str, str]:
    """Copy recent sPyNNaker report directories into the run artifacts."""
    roots: list[Path] = []
    for root in [ROOT / "reports", Path.cwd() / "reports"]:
        resolved = root.resolve()
        if resolved not in roots and resolved.exists():
            roots.append(resolved)

    candidates: list[Path] = []
    for root in roots:
        for child in root.iterdir():
            if not child.is_dir():
                continue
            try:
                if child.stat().st_mtime >= started_epoch - 2.0:
                    candidates.append(child)
            except OSError:
                continue

    if not candidates:
        return {}

    candidates = sorted(set(candidates), key=lambda p: p.stat().st_mtime)[-max_reports:]
    dest_root = output_dir / "spinnaker_reports"
    dest_root.mkdir(parents=True, exist_ok=True)
    artifacts: dict[str, str] = {}
    for index, source in enumerate(candidates, start=1):
        dest = dest_root / source.name
        try:
            shutil.copytree(source, dest, dirs_exist_ok=True)
        except Exception as exc:
            marker = dest_root / f"{source.name}_copy_error.txt"
            marker.write_text(f"{type(exc).__name__}: {exc}\n", encoding="utf-8")
            artifacts[f"spinnaker_report_{index}_copy_error"] = str(marker)
            continue
        artifacts[f"spinnaker_report_{index}"] = str(dest)
    return artifacts


def latest_tier4_12_manifest() -> dict[str, Any]:
    latest = ROOT / "controlled_test_output" / "tier4_12_latest_manifest.json"
    if not latest.exists():
        return {}
    try:
        pointer = json.loads(latest.read_text(encoding="utf-8"))
        manifest_path = Path(pointer.get("manifest", ""))
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            return {
                "pointer": pointer,
                "manifest_path": str(manifest_path),
                "output_dir": manifest.get("output_dir"),
                "results": manifest.get("results", []),
            }
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}
    return {}


def make_hardware_config(
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


def run_spinnaker_seed(
    *,
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

    sensory, target, evaluation_target, evaluation_mask = fixed_pattern_task(
        args.steps,
        args.amplitude,
    )
    cfg = make_hardware_config(
        seed=seed,
        steps=int(target.size),
        population_size=args.population_size,
        args=args,
    )
    organism: Organism | None = Organism(cfg, sim, setup_kwargs=setup_kwargs)
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
            diagnostics = organism.backend_diagnostics()
            if args.stop_on_backend_fallback and (
                int(diagnostics.get("sim_run_failures", 0)) > 0
                or int(diagnostics.get("summary_read_failures", 0)) > 0
                or int(diagnostics.get("synthetic_fallbacks", 0)) > 0
            ):
                raise BackendFallbackError(step, diagnostics)

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
                    "test_name": "tier4_13_spinnaker_hardware_capsule",
                    "backend": "pyNN.spiNNaker",
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
            "backend": "pyNN.spiNNaker",
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
    summary["spinnman_numpy2_compat"] = compat_status
    return rows, summary


def safe_mean(values: list[Any]) -> float | None:
    clean: list[float] = []
    for value in values:
        if value is None:
            continue
        try:
            f = float(value)
        except Exception:
            continue
        if math.isfinite(f):
            clean.append(f)
    return None if not clean else float(np.mean(clean))


def safe_std(values: list[Any]) -> float | None:
    clean: list[float] = []
    for value in values:
        if value is None:
            continue
        try:
            f = float(value)
        except Exception:
            continue
        if math.isfinite(f):
            clean.append(f)
    if not clean:
        return None
    return 0.0 if len(clean) < 2 else float(np.std(clean, ddof=1))


def aggregate_summaries(summaries: list[dict[str, Any]]) -> dict[str, Any]:
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
    ]
    aggregate: dict[str, Any] = {
        "runs": len(summaries),
        "seeds": [s.get("seed") for s in summaries],
        "backend": "pyNN.spiNNaker",
    }
    for key in keys:
        values = [s.get(key) for s in summaries]
        aggregate[f"{key}_mean"] = safe_mean(values)
        aggregate[f"{key}_std"] = safe_std(values)
    aggregate["sim_run_failures_sum"] = int(
        sum(int(s.get("sim_run_failures", 0)) for s in summaries)
    )
    aggregate["summary_read_failures_sum"] = int(
        sum(int(s.get("summary_read_failures", 0)) for s in summaries)
    )
    aggregate["synthetic_fallbacks_sum"] = int(
        sum(int(s.get("synthetic_fallbacks", 0)) for s in summaries)
    )
    aggregate["total_births_sum"] = int(sum(int(s.get("total_births", 0)) for s in summaries))
    aggregate["total_deaths_sum"] = int(sum(int(s.get("total_deaths", 0)) for s in summaries))
    return aggregate


def hardware_criteria(aggregate: dict[str, Any], args: argparse.Namespace) -> list[dict[str, Any]]:
    return [
        criterion(
            "sim.run has no failures",
            aggregate["sim_run_failures_sum"],
            "==",
            0,
            aggregate["sim_run_failures_sum"] == 0,
        ),
        criterion(
            "summary read has no failures",
            aggregate["summary_read_failures_sum"],
            "==",
            0,
            aggregate["summary_read_failures_sum"] == 0,
        ),
        criterion(
            "no synthetic fallback",
            aggregate["synthetic_fallbacks_sum"],
            "==",
            0,
            aggregate["synthetic_fallbacks_sum"] == 0,
        ),
        criterion(
            "real spike readback is active",
            aggregate["total_step_spikes_mean"],
            ">",
            0,
            aggregate["total_step_spikes_mean"] is not None
            and aggregate["total_step_spikes_mean"] > 0,
        ),
        criterion(
            "fixed population has no births/deaths",
            {
                "births": aggregate["total_births_sum"],
                "deaths": aggregate["total_deaths_sum"],
            },
            "==",
            {"births": 0, "deaths": 0},
            aggregate["total_births_sum"] == 0 and aggregate["total_deaths_sum"] == 0,
        ),
        criterion(
            "no extinction/collapse",
            aggregate["final_n_alive_mean"],
            "==",
            args.population_size,
            aggregate["final_n_alive_mean"] == args.population_size,
        ),
        criterion(
            "overall strict accuracy",
            aggregate["all_accuracy_mean"],
            ">=",
            args.all_accuracy_threshold,
            aggregate["all_accuracy_mean"] is not None
            and aggregate["all_accuracy_mean"] >= args.all_accuracy_threshold,
        ),
        criterion(
            "tail strict accuracy",
            aggregate["tail_accuracy_mean"],
            ">=",
            args.tail_accuracy_threshold,
            aggregate["tail_accuracy_mean"] is not None
            and aggregate["tail_accuracy_mean"] >= args.tail_accuracy_threshold,
        ),
        criterion(
            "tail prediction/target correlation",
            aggregate["tail_prediction_target_corr_mean"],
            ">=",
            args.corr_threshold,
            aggregate["tail_prediction_target_corr_mean"] is not None
            and aggregate["tail_prediction_target_corr_mean"] >= args.corr_threshold,
        ),
    ]


def plot_hardware_summary(aggregate: dict[str, Any], output_path: Path) -> None:
    if plt is None:
        return
    labels = [
        "overall\naccuracy",
        "tail\naccuracy",
        "tail\ncorr",
        "fallbacks",
    ]
    values = [
        aggregate.get("all_accuracy_mean") or 0.0,
        aggregate.get("tail_accuracy_mean") or 0.0,
        aggregate.get("tail_prediction_target_corr_mean") or 0.0,
        aggregate.get("synthetic_fallbacks_sum") or 0.0,
    ]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(np.arange(len(labels)), values, color=["#1f6feb", "#2f855a", "#8250df", "#9a6700"])
    ax.set_xticks(np.arange(len(labels)))
    ax.set_xticklabels(labels)
    ax.set_title("Tier 4.13 SpiNNaker Hardware Capsule")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def write_jobmanager_capsule(output_dir: Path, args: argparse.Namespace) -> dict[str, str]:
    capsule_dir = output_dir / "jobmanager_capsule"
    capsule_dir.mkdir(parents=True, exist_ok=True)
    config_path = capsule_dir / "capsule_config.json"
    command_path = capsule_dir / "run_tier4_13_on_jobmanager.sh"
    readme_path = capsule_dir / "README_JOBMANAGER.md"
    expected_path = capsule_dir / "expected_outputs.json"

    config_payload = {
        "tier": "Tier 4.13 SpiNNaker Hardware Capsule",
        "task": "fixed_pattern",
        "steps": args.steps,
        "seed": args.base_seed,
        "population_size": args.population_size,
        "amplitude": args.amplitude,
        "dt_seconds": args.dt_seconds,
        "timestep_ms": args.timestep_ms,
        "thresholds": {
            "all_accuracy_threshold": args.all_accuracy_threshold,
            "tail_accuracy_threshold": args.tail_accuracy_threshold,
            "corr_threshold": args.corr_threshold,
        },
        "claim_boundary": (
            "Capsule prep is not a hardware pass. A pass requires run-hardware "
            "mode on a real SpiNNaker target with zero backend fallbacks."
        ),
    }
    write_json(config_path, config_payload)

    command_path.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                "",
                "# Run from the repository root inside the EBRAINS/JobManager job.",
                "# The job environment should provide real SpiNNaker access via",
                "# ~/.spynnaker.cfg, spalloc, or the platform's generated config.",
                "OUT_DIR=${1:-tier4_13_job_output}",
                "python3 experiments/tier4_spinnaker_hardware_capsule.py \\",
                "  --mode run-hardware \\",
                "  --require-real-hardware \\",
                "  --stop-on-fail \\",
                "  --output-dir \"$OUT_DIR\"",
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
                    "tier4_13_report.md",
                    "tier4_13_results.json",
                    "tier4_13_summary.csv",
                    "spinnaker_hardware_seed<seed>_timeseries.csv",
                    "spinnaker_hardware_seed<seed>_timeseries.png",
                    "hardware_capsule_summary.png",
                ],
                "failure_debug_artifacts": [
                    "seed_<seed>_failure_traceback.txt",
                    "seed_<seed>_backend_diagnostics.json",
                    "seed_<seed>_inner_backend_traceback.txt",
                    "spinnaker_reports/<report_timestamp>/",
                ],
                "pass_requires": [
                    "hardware_run_attempted=true",
                    "hardware_target_configured=true",
                    "sim_run_failures_sum=0",
                    "summary_read_failures_sum=0",
                    "synthetic_fallbacks_sum=0",
                    "real spike readback > 0",
                    "accuracy/correlation above thresholds",
                ],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    readme_path.write_text(
        "\n".join(
            [
                "# Tier 4.13 SpiNNaker Hardware Capsule",
                "",
                "This capsule is meant to run inside an EBRAINS/JobManager job with real SpiNNaker access.",
                "",
                "## Run",
                "",
                "From the repository root inside the job:",
                "",
                "```bash",
                "bash controlled_test_output/<tier4_13_run>/jobmanager_capsule/run_tier4_13_on_jobmanager.sh",
                "```",
                "",
                "Or run the harness directly:",
                "",
                "```bash",
                "python3 experiments/tier4_spinnaker_hardware_capsule.py --mode run-hardware --require-real-hardware --stop-on-fail",
                "```",
                "",
                "## Claim Boundary",
                "",
                "A prepared capsule is not a hardware result. The hardware claim only exists if `run-hardware` completes on a real target with zero synthetic fallbacks, zero `sim.run` failures, and zero summary-read failures.",
                "",
                "## Hardware Note",
                "",
                "The sPyNNaker dopamine/neuromodulation projection is sharded across multiple dopamine source neurons. This avoids the 255-synapse-per-source-row cap that appears when one dopamine source fans out to all 256 target atoms in the N=8 capsule.",
                "",
                "The runner also applies narrow NumPy 2 compatibility shims for sPyNNaker/spinnman 7.4.x neuromodulation synapse flags, hardware byte buffers, and host-side memory-upload checksums. This does not change the CRA model or pass criteria; it only prevents valid 32-bit SpiNNaker words from failing scalar uint8 casts during upload/readback bookkeeping.",
                "",
                "On failure, the capsule exports `seed_<seed>_failure_traceback.txt`, `seed_<seed>_backend_diagnostics.json`, `seed_<seed>_inner_backend_traceback.txt`, and recent `reports/` directories so the next hardware blocker has a full stack/provenance trail.",
                "",
                "## Expected Claim If It Passes",
                "",
                "`CRA minimal learning capsule executes on real SpiNNaker hardware and preserves expected fixed-pattern behavior.`",
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
        "# Tier 4.13 SpiNNaker Hardware Capsule Findings",
        "",
        f"- Generated: `{utc_now()}`",
        f"- Mode: `{mode}`",
        f"- Status: **{status.upper()}**",
        f"- Output directory: `{output_dir}`",
        "",
        "Tier 4.13 is separate from Tier 4.12. It is the hardware capsule step: a minimal fixed-pattern CRA task intended to run on real SpiNNaker hardware through EBRAINS/JobManager.",
        "",
        "## Claim Boundary",
        "",
        "- `PREPARED` means the capsule package exists locally; it is not a hardware pass.",
        "- `PASS` requires a real `pyNN.spiNNaker` run with zero synthetic fallback, zero `sim.run` failures, zero summary-read failures, real spike readback, and learning metrics above threshold.",
        "- SpiNNaker virtual-board or setup-only results must not be described as hardware learning.",
        "",
        "## Summary",
        "",
    ]
    for key in [
        "hardware_run_attempted",
        "hardware_target_configured",
        "all_accuracy_mean",
        "tail_accuracy_mean",
        "tail_prediction_target_corr_mean",
        "synthetic_fallbacks_sum",
        "sim_run_failures_sum",
        "summary_read_failures_sum",
        "jobmanager_cli",
        "failure_step",
        "capsule_dir",
    ]:
        if key in summary:
            lines.append(f"- {key}: `{markdown_value(summary.get(key))}`")
    if failure_reason:
        lines.extend(["", f"Failure: {failure_reason}", ""])
    failure_diagnostics = summary.get("failure_diagnostics") or {}
    if isinstance(failure_diagnostics, dict) and failure_diagnostics:
        lines.extend(["", "## Failure Diagnostics", ""])
        for key in [
            "backend",
            "last_backend_failure_stage",
            "last_backend_exception_type",
            "last_sim_run_error",
        ]:
            if key in failure_diagnostics:
                lines.append(f"- {key}: `{markdown_value(failure_diagnostics.get(key))}`")

    if criteria:
        lines.extend(
            [
                "",
                "## Criteria",
                "",
                "| Criterion | Value | Rule | Pass |",
                "| --- | --- | --- | --- |",
            ]
        )
        for item in criteria:
            lines.append(
                "| "
                f"{item['name']} | "
                f"{markdown_value(item['value'])} | "
                f"{item['operator']} {markdown_value(item['threshold'])} | "
                f"{'yes' if item['passed'] else 'no'} |"
            )

    lines.extend(["", "## Artifacts", ""])
    for label, artifact in artifacts.items():
        lines.append(f"- `{label}`: `{artifact}`")
    if artifacts.get("hardware_summary_png"):
        lines.extend(["", "![hardware_capsule_summary](hardware_capsule_summary.png)", ""])

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def prepare_capsule(args: argparse.Namespace, output_dir: Path) -> int:
    env = collect_environment(args)
    capsule_artifacts = write_jobmanager_capsule(output_dir, args)
    reference = latest_tier4_12_manifest()
    summary = {
        "mode": "prepare",
        "hardware_run_attempted": False,
        "hardware_target_configured": env.get("hardware_target_configured"),
        "jobmanager_cli": env.get("jobmanager_cli"),
        "capsule_dir": capsule_artifacts["capsule_dir"],
    }
    criteria = [
        criterion(
            "sPyNNaker imports locally",
            next((m.get("ok") for m in env["modules"] if m["name"] == "pyNN.spiNNaker"), False),
            "==",
            True,
            bool(next((m.get("ok") for m in env["modules"] if m["name"] == "pyNN.spiNNaker"), False)),
        ),
        criterion(
            "capsule package generated",
            Path(capsule_artifacts["jobmanager_run_script"]).exists(),
            "==",
            True,
            Path(capsule_artifacts["jobmanager_run_script"]).exists(),
        ),
    ]
    write_json(output_dir / "local_environment.json", env)
    write_json(output_dir / "tier4_13_reference_tier4_12.json", reference)

    manifest = {
        "generated_at_utc": utc_now(),
        "tier": "Tier 4.13 - SpiNNaker Hardware Capsule",
        "mode": "prepare",
        "status": "prepared",
        "output_dir": str(output_dir),
        "summary": summary,
        "criteria": criteria,
        "artifacts": capsule_artifacts,
        "environment": env,
        "tier4_12_reference": reference,
    }
    manifest_path = output_dir / "tier4_13_results.json"
    report_path = output_dir / "tier4_13_report.md"
    summary_csv_path = output_dir / "tier4_13_summary.csv"
    write_json(manifest_path, manifest)
    write_summary_csv(summary_csv_path, [summary])
    write_report(
        path=report_path,
        mode="prepare",
        status="prepared",
        output_dir=output_dir,
        criteria=criteria,
        artifacts={
            "manifest_json": str(manifest_path),
            "summary_csv": str(summary_csv_path),
            **capsule_artifacts,
        },
        summary=summary,
    )
    write_latest(output_dir, report_path, manifest_path, "prepared")
    return 0


def run_hardware(args: argparse.Namespace, output_dir: Path) -> int:
    run_started_epoch = time.time()
    env = collect_environment(args)
    env["spinnman_numpy2_compat"] = apply_spinnaker_numpy2_compat_patches()
    hardware_target_configured = bool(env.get("hardware_target_configured"))
    if args.require_real_hardware and not hardware_target_configured:
        failure = (
            "No real SpiNNaker target is configured locally. "
            "Refusing to run a virtual-board result as Tier 4.13 hardware."
        )
        summary = {
            "mode": "run-hardware",
            "hardware_run_attempted": False,
            "hardware_target_configured": False,
            "jobmanager_cli": env.get("jobmanager_cli"),
        }
        criteria = [
            criterion(
                "real SpiNNaker target configured",
                hardware_target_configured,
                "==",
                True,
                False,
            )
        ]
        manifest_path = output_dir / "tier4_13_results.json"
        report_path = output_dir / "tier4_13_report.md"
        summary_csv_path = output_dir / "tier4_13_summary.csv"
        write_json(
            manifest_path,
            {
                "generated_at_utc": utc_now(),
                "tier": "Tier 4.13 - SpiNNaker Hardware Capsule",
                "mode": "run-hardware",
                "status": "blocked",
                "failure_reason": failure,
                "summary": summary,
                "criteria": criteria,
                "environment": env,
            },
        )
        write_summary_csv(summary_csv_path, [summary])
        write_report(
            path=report_path,
            mode="run-hardware",
            status="blocked",
            output_dir=output_dir,
            criteria=criteria,
            artifacts={
                "manifest_json": str(manifest_path),
                "summary_csv": str(summary_csv_path),
            },
            summary=summary,
            failure_reason=failure,
        )
        write_latest(output_dir, report_path, manifest_path, "blocked")
        return 1

    summaries: list[dict[str, Any]] = []
    artifacts: dict[str, str] = {}
    failure_reason = ""
    failure_traceback = ""
    failure_diagnostics: dict[str, Any] = {}
    failure_step: int | None = None
    hardware_run_attempted = False
    for seed in [args.base_seed]:
        try:
            hardware_run_attempted = True
            rows, summary = run_spinnaker_seed(seed=seed, args=args)
        except Exception as exc:
            failure_reason = f"seed {seed} raised {type(exc).__name__}: {exc}"
            failure_traceback = traceback.format_exc()
            failure_diagnostics = getattr(exc, "diagnostics", {}) or {}
            failure_step = getattr(exc, "step", None)
            traceback_path = output_dir / f"seed_{seed}_failure_traceback.txt"
            traceback_path.write_text(failure_traceback, encoding="utf-8")
            artifacts[f"seed_{seed}_failure_traceback"] = str(traceback_path)
            if failure_diagnostics:
                diagnostics_path = output_dir / f"seed_{seed}_backend_diagnostics.json"
                write_json(diagnostics_path, failure_diagnostics)
                artifacts[f"seed_{seed}_backend_diagnostics"] = str(diagnostics_path)
                inner_traceback = str(
                    failure_diagnostics.get("last_backend_traceback", "")
                )
                if inner_traceback:
                    inner_path = output_dir / f"seed_{seed}_inner_backend_traceback.txt"
                    inner_path.write_text(inner_traceback, encoding="utf-8")
                    artifacts[f"seed_{seed}_inner_backend_traceback"] = str(inner_path)
            break
        csv_path = output_dir / f"spinnaker_hardware_seed{seed}_timeseries.csv"
        png_path = output_dir / f"spinnaker_hardware_seed{seed}_timeseries.png"
        write_csv(csv_path, rows)
        plot_case(rows, png_path, f"Tier 4.13 SpiNNaker hardware seed {seed}")
        artifacts[f"seed_{seed}_timeseries_csv"] = str(csv_path)
        if png_path.exists():
            artifacts[f"seed_{seed}_timeseries_png"] = str(png_path)
        summaries.append(summary)

    aggregate = aggregate_summaries(summaries)
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
    criteria = hardware_criteria(aggregate, args) if summaries else []
    status, criteria_failure = pass_fail(criteria) if criteria else ("fail", failure_reason)
    if criteria_failure:
        failure_reason = criteria_failure

    summary_png = output_dir / "hardware_capsule_summary.png"
    if summaries:
        plot_hardware_summary(aggregate, summary_png)
        if summary_png.exists():
            artifacts["hardware_summary_png"] = str(summary_png)
    artifacts.update(collect_recent_spinnaker_reports(output_dir, run_started_epoch))
    if failure_traceback:
        aggregate["failure_traceback"] = failure_traceback

    manifest_path = output_dir / "tier4_13_results.json"
    report_path = output_dir / "tier4_13_report.md"
    summary_csv_path = output_dir / "tier4_13_summary.csv"
    write_json(
        manifest_path,
        {
            "generated_at_utc": utc_now(),
            "tier": "Tier 4.13 - SpiNNaker Hardware Capsule",
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
    write_summary_csv(summary_csv_path, [aggregate])
    write_report(
        path=report_path,
        mode="run-hardware",
        status=status,
        output_dir=output_dir,
        criteria=criteria,
        artifacts={
            "manifest_json": str(manifest_path),
            "summary_csv": str(summary_csv_path),
            **artifacts,
        },
        summary=aggregate,
        failure_reason=failure_reason,
    )
    write_latest(output_dir, report_path, manifest_path, status)
    return 0 if status == "pass" else 1


def ingest_results(args: argparse.Namespace, output_dir: Path) -> int:
    if args.ingest_dir is None:
        raise SystemExit("--ingest-dir is required in ingest mode")
    ingest_dir = args.ingest_dir.resolve()
    candidates = [
        ingest_dir / "tier4_13_results.json",
        ingest_dir / "hardware_capsule_results.json",
    ]
    source = next((p for p in candidates if p.exists()), None)
    if source is None:
        raise SystemExit(f"No Tier 4.13 result JSON found in {ingest_dir}")
    data = json.loads(source.read_text(encoding="utf-8"))
    summary = dict(data.get("summary", {}))
    criteria = list(data.get("criteria", []))
    status = str(data.get("status", "unknown"))
    summary.update(
        {
            "mode": "ingest",
            "ingested_from": str(source),
            "hardware_run_attempted": summary.get("hardware_run_attempted"),
        }
    )
    manifest_path = output_dir / "tier4_13_results.json"
    report_path = output_dir / "tier4_13_report.md"
    summary_csv_path = output_dir / "tier4_13_summary.csv"
    write_json(
        manifest_path,
        {
            "generated_at_utc": utc_now(),
            "tier": "Tier 4.13 - SpiNNaker Hardware Capsule",
            "mode": "ingest",
            "status": status,
            "ingested_from": str(source),
            "summary": summary,
            "criteria": criteria,
            "source_manifest": data,
        },
    )
    write_summary_csv(summary_csv_path, [summary])
    write_report(
        path=report_path,
        mode="ingest",
        status=status,
        output_dir=output_dir,
        criteria=criteria,
        artifacts={
            "manifest_json": str(manifest_path),
            "summary_csv": str(summary_csv_path),
            "ingested_source": str(source),
        },
        summary=summary,
        failure_reason=str(data.get("failure_reason", "")),
    )
    write_latest(output_dir, report_path, manifest_path, status)
    return 0 if status == "pass" else 1


def write_latest(output_dir: Path, report_path: Path, manifest_path: Path, status: str) -> None:
    latest_path = ROOT / "controlled_test_output" / "tier4_13_latest_manifest.json"
    write_json(
        latest_path,
        {
            "generated_at_utc": utc_now(),
            "manifest": str(manifest_path),
            "report": str(report_path),
            "output_dir": str(output_dir),
            "status": status,
        },
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepare, run, or ingest the Tier 4.13 SpiNNaker hardware capsule.",
    )
    parser.add_argument(
        "--mode",
        choices=["prepare", "run-hardware", "ingest"],
        default="prepare",
    )
    parser.add_argument("--steps", type=int, default=120)
    parser.add_argument("--base-seed", type=int, default=42)
    parser.add_argument("--population-size", type=int, default=8)
    parser.add_argument("--amplitude", type=float, default=DEFAULT_AMPLITUDE)
    parser.add_argument("--dt-seconds", type=float, default=DEFAULT_DT_SECONDS)
    parser.add_argument("--timestep-ms", type=float, default=1.0)
    parser.add_argument("--readout-lr", type=float, default=0.10)
    parser.add_argument("--delayed-readout-lr", type=float, default=0.05)
    parser.add_argument("--all-accuracy-threshold", type=float, default=0.65)
    parser.add_argument("--tail-accuracy-threshold", type=float, default=0.75)
    parser.add_argument("--corr-threshold", type=float, default=0.60)
    parser.add_argument("--spinnaker-hostname", default=None)
    parser.add_argument(
        "--require-real-hardware",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument(
        "--stop-on-backend-fallback",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
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
    output_dir = args.output_dir or (
        ROOT / "controlled_test_output" / f"tier4_13_{timestamp}"
    )
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
