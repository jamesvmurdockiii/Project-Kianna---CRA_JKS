#!/usr/bin/env python3
"""Tier 7.1d - C-MAPSS failure analysis / adapter repair.

Tier 7.1c was an honest negative result for the compact scalar PCA1 C-MAPSS
adapter. This gate does not add a new CRA mechanism and does not try to tune
until something wins. It localizes the failure by testing whether the gap comes
from scalar compression, readout policy, RUL target policy, unit-reset policy,
or the lack of a multichannel CRA adapter interface.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from tier5_19b_temporal_substrate_gate import temporal_features_variant  # noqa: E402
from tier7_0c_continuous_readout_repair import shuffled_rows  # noqa: E402
from tier7_1c_cmapss_fd001_scoring_gate import (  # noqa: E402
    CmapssTask,
    aggregate,
    criterion,
    lag_features_by_unit,
    load_task,
    make_manifest,
    read_json,
    score_model,
    temporal_by_unit,
    train_prefix_lms,
    train_prefix_ridge,
    write_csv,
    write_json,
)


TIER = "Tier 7.1d - C-MAPSS Failure Analysis / Adapter Repair"
RUNNER_REVISION = "tier7_1d_cmapss_failure_analysis_adapter_repair_20260508_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_1d_20260508_cmapss_failure_analysis_adapter_repair"
TIER7_1B_RESULTS = CONTROLLED / "tier7_1b_20260508_cmapss_source_data_preflight" / "tier7_1b_results.json"
TIER7_1C_RESULTS = CONTROLLED / "tier7_1c_20260508_cmapss_fd001_scoring_gate" / "tier7_1c_results.json"

SCALAR_V23_LMS_UNCAPPED = "scalar_pca1_v2_3_lms_uncapped"
SCALAR_V23_RIDGE_UNCAPPED = "scalar_pca1_v2_3_ridge_uncapped"
AGE_UNCAPPED = "age_ridge_uncapped"
AGE_CAPPED = "age_ridge_capped125"
RAW_MULTI_RIDGE_CAPPED = "raw_multichannel_ridge_capped125"
LAG_MULTI_RIDGE_CAPPED = "lag_multichannel_ridge_capped125"
SCALAR_V22_RIDGE_CAPPED = "scalar_pca1_v2_2_ridge_capped125"
SCALAR_V23_LMS_CAPPED = "scalar_pca1_v2_3_lms_capped125"
SCALAR_V23_RIDGE_CAPPED = "scalar_pca1_v2_3_ridge_capped125"
MULTI_V23_LMS_CAPPED = "multichannel_v2_3_lms_capped125"
MULTI_V23_RIDGE_CAPPED = "multichannel_v2_3_ridge_capped125"
MULTI_V23_SHUFFLED_CAPPED = "multichannel_v2_3_shuffled_state_capped125"
MULTI_V23_NO_UPDATE_CAPPED = "multichannel_v2_3_no_update_capped125"
SCALAR_V23_CONTINUOUS_PROBE = "scalar_pca1_v2_3_no_unit_reset_probe_capped125"

REQUIRED_MODELS = [
    SCALAR_V23_LMS_UNCAPPED,
    SCALAR_V23_RIDGE_UNCAPPED,
    AGE_UNCAPPED,
    AGE_CAPPED,
    RAW_MULTI_RIDGE_CAPPED,
    LAG_MULTI_RIDGE_CAPPED,
    SCALAR_V22_RIDGE_CAPPED,
    SCALAR_V23_LMS_CAPPED,
    SCALAR_V23_RIDGE_CAPPED,
    MULTI_V23_LMS_CAPPED,
    MULTI_V23_RIDGE_CAPPED,
    MULTI_V23_SHUFFLED_CAPPED,
    MULTI_V23_NO_UPDATE_CAPPED,
    SCALAR_V23_CONTINUOUS_PROBE,
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def capped_task(task: CmapssTask, cap: float) -> CmapssTask:
    raw = np.minimum(task.target_raw, float(cap))
    train_raw = raw[: task.train_end]
    mu = float(np.mean(train_raw))
    sd = float(np.std(train_raw))
    if sd < 1e-9:
        sd = 1.0
    profile = dict(task.fd001_profile)
    profile["raw_rul_policy"] = f"RUL capped at {float(cap):g} for failure-analysis target-policy probe"
    profile["target_mu_train_only"] = mu
    profile["target_sd_train_only"] = sd
    return replace(task, target_raw=raw, target_norm=(raw - mu) / sd, target_mu=mu, target_sd=sd, fd001_profile=profile)


def selected_channels(task: CmapssTask, target_norm: np.ndarray, max_channels: int) -> tuple[list[int], list[dict[str, Any]]]:
    train_x = task.features_raw[: task.train_end]
    train_y = target_norm[: task.train_end]
    rows: list[dict[str, Any]] = []
    for idx in range(train_x.shape[1]):
        col = train_x[:, idx]
        if float(np.std(col)) < 1e-12 or float(np.std(train_y)) < 1e-12:
            corr = 0.0
        else:
            corr = float(np.corrcoef(col, train_y)[0, 1])
        rows.append({"channel_index": idx, "feature_column": idx + 3, "train_corr_to_target_norm": corr, "abs_corr": abs(corr)})
    ranked = sorted(rows, key=lambda r: (-float(r["abs_corr"]), int(r["channel_index"])))
    chosen = ranked[: max(1, min(int(max_channels), task.features_raw.shape[1]))]
    return [int(r["channel_index"]) for r in chosen], chosen


def bias_plus(x: np.ndarray) -> np.ndarray:
    return np.column_stack([np.ones(x.shape[0]), x])


def multichannel_lag_features(task: CmapssTask, channels: list[int], history: int) -> np.ndarray:
    pieces = [np.ones((len(task.target_raw), 1), dtype=float)]
    for channel in channels:
        pseudo = replace(task, observed=task.features_raw[:, channel])
        pieces.append(lag_features_by_unit(pseudo, history)[:, 1:])
    return np.hstack(pieces)


def multichannel_temporal_features(task: CmapssTask, channels: list[int], *, seed: int, args: argparse.Namespace, mode: str) -> np.ndarray:
    pieces = [np.ones((len(task.target_raw), 1), dtype=float)]
    for channel in channels:
        pseudo = replace(task, observed=task.features_raw[:, channel])
        pieces.append(temporal_by_unit(pseudo, seed=seed + channel * 101, args=args, mode=mode)[:, 1:])
    return np.hstack(pieces)


def continuous_scalar_temporal_probe(task: CmapssTask, *, seed: int, args: argparse.Namespace) -> np.ndarray:
    bundle = temporal_features_variant(
        task.observed,
        seed=seed,
        train_end=task.train_end,
        timescales=[float(x) for x in args.temporal_timescales.split(",") if x.strip()],
        hidden_units=args.temporal_hidden_units,
        recurrent_scale=args.temporal_recurrent_scale,
        input_scale=args.temporal_input_scale,
        hidden_decay=args.temporal_hidden_decay,
        mode="full",
        reset_interval=0,
        recurrent_seed_offset=0,
    )
    return bundle.features


def age_features(task: CmapssTask) -> np.ndarray:
    cycle = task.cycles.astype(float)
    mu = float(np.mean(cycle[: task.train_end]))
    sd = float(np.std(cycle[: task.train_end])) or 1.0
    z = (cycle - mu) / sd
    return np.column_stack([np.ones(len(z)), z, z * z])


def run_model(
    task: CmapssTask,
    *,
    model: str,
    seed: int,
    features: np.ndarray,
    readout: str,
    args: argparse.Namespace,
    diagnostics: dict[str, Any],
    update_enabled: bool = True,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if readout == "ridge":
        pred_norm, diag = train_prefix_ridge(features, task.target_norm, task.train_end, args.ridge)
    elif readout == "lms":
        pred_norm, diag = train_prefix_lms(
            features,
            task.target_norm,
            train_end=task.train_end,
            lr=args.readout_lr,
            decay=args.readout_decay,
            weight_clip=args.weight_clip,
            output_clip=args.output_clip,
            update_enabled=update_enabled,
        )
    else:
        raise ValueError(f"unknown readout {readout}")
    row, units = score_model(task, model, seed, pred_norm, {**diag, **diagnostics})
    return row, units


def run_seed(task_uncapped: CmapssTask, task_capped: CmapssTask, seed: int, args: argparse.Namespace, channels: list[int]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    per_unit: list[dict[str, Any]] = []

    scalar_v23_uncapped = temporal_by_unit(task_uncapped, seed=seed, args=args, mode="full")
    scalar_v22_capped = temporal_by_unit(task_capped, seed=seed, args=args, mode="fading_only")
    scalar_v23_capped = temporal_by_unit(task_capped, seed=seed, args=args, mode="full")
    multi_v23 = multichannel_temporal_features(task_capped, channels, seed=seed, args=args, mode="full")
    shuffled_multi = shuffled_rows(multi_v23, task_capped.train_end, seed)

    specs: list[tuple[CmapssTask, str, np.ndarray, str, bool, dict[str, Any]]] = [
        (task_uncapped, SCALAR_V23_LMS_UNCAPPED, scalar_v23_uncapped, "lms", True, {"factor_probe": "tier7_1c_scalar_reference", "target_policy": "uncapped"}),
        (task_uncapped, SCALAR_V23_RIDGE_UNCAPPED, scalar_v23_uncapped, "ridge", True, {"factor_probe": "readout_policy", "target_policy": "uncapped"}),
        (task_uncapped, AGE_UNCAPPED, age_features(task_uncapped), "ridge", True, {"factor_probe": "age_baseline", "target_policy": "uncapped"}),
        (task_capped, AGE_CAPPED, age_features(task_capped), "ridge", True, {"factor_probe": "target_policy", "target_policy": "capped125"}),
        (task_capped, RAW_MULTI_RIDGE_CAPPED, bias_plus(task_capped.features_raw[:, channels]), "ridge", True, {"factor_probe": "raw_multichannel_baseline", "target_policy": "capped125", "selected_channels": channels}),
        (task_capped, LAG_MULTI_RIDGE_CAPPED, multichannel_lag_features(task_capped, channels, args.history), "ridge", True, {"factor_probe": "multichannel_lag_baseline", "target_policy": "capped125", "selected_channels": channels}),
        (task_capped, SCALAR_V22_RIDGE_CAPPED, scalar_v22_capped, "ridge", True, {"factor_probe": "v2_2_reference", "target_policy": "capped125"}),
        (task_capped, SCALAR_V23_LMS_CAPPED, scalar_v23_capped, "lms", True, {"factor_probe": "target_policy", "target_policy": "capped125"}),
        (task_capped, SCALAR_V23_RIDGE_CAPPED, scalar_v23_capped, "ridge", True, {"factor_probe": "readout_plus_target_policy", "target_policy": "capped125"}),
        (task_capped, MULTI_V23_LMS_CAPPED, multi_v23, "lms", True, {"factor_probe": "multichannel_cra_adapter", "target_policy": "capped125", "selected_channels": channels}),
        (task_capped, MULTI_V23_RIDGE_CAPPED, multi_v23, "ridge", True, {"factor_probe": "multichannel_cra_adapter", "target_policy": "capped125", "selected_channels": channels}),
        (task_capped, MULTI_V23_SHUFFLED_CAPPED, shuffled_multi, "ridge", True, {"sham": "multichannel_v2_3_state_rows_shuffled", "target_policy": "capped125"}),
        (task_capped, MULTI_V23_NO_UPDATE_CAPPED, multi_v23, "lms", False, {"ablation": "multichannel_v2_3_no_readout_updates", "target_policy": "capped125"}),
        (
            task_capped,
            SCALAR_V23_CONTINUOUS_PROBE,
            continuous_scalar_temporal_probe(task_capped, seed=seed + 5000, args=args),
            "ridge",
            True,
            {"factor_probe": "unit_reset_policy", "promotable": False, "target_policy": "capped125"},
        ),
    ]
    for probe_task, model, features, readout, update_enabled, diagnostics in specs:
        row, units = run_model(
            probe_task,
            model=model,
            seed=seed,
            features=features,
            readout=readout,
            args=args,
            diagnostics=diagnostics,
            update_enabled=update_enabled,
        )
        rows.append(row)
        per_unit.extend(units)

    return rows, per_unit, {
        "seed": seed,
        "selected_channel_count": len(channels),
        "selected_channels": channels,
        "diagnostic_boundary": "failure localization only; not a promoted mechanism",
    }


def rmse(summary: dict[str, dict[str, Any]], model: str) -> float:
    return float(summary[model]["test_rmse_mean"])


def classify(summary_rows: list[dict[str, Any]], args: argparse.Namespace) -> dict[str, Any]:
    by_model = {str(r["model"]): r for r in summary_rows}
    promotable_models = [m for m in by_model if m != SCALAR_V23_CONTINUOUS_PROBE]
    best_promotable = min((by_model[m] for m in promotable_models), key=lambda r: float(r["test_rmse_mean"]))
    best_baseline = min(
        (by_model[m] for m in [AGE_CAPPED, RAW_MULTI_RIDGE_CAPPED, LAG_MULTI_RIDGE_CAPPED]),
        key=lambda r: float(r["test_rmse_mean"]),
    )
    readout_delta = rmse(by_model, SCALAR_V23_LMS_UNCAPPED) - rmse(by_model, SCALAR_V23_RIDGE_UNCAPPED)
    target_delta = rmse(by_model, SCALAR_V23_LMS_UNCAPPED) - rmse(by_model, SCALAR_V23_LMS_CAPPED)
    scalar_to_multi_delta = rmse(by_model, SCALAR_V23_RIDGE_CAPPED) - rmse(by_model, MULTI_V23_RIDGE_CAPPED)
    multi_sham_delta = rmse(by_model, MULTI_V23_SHUFFLED_CAPPED) - rmse(by_model, MULTI_V23_RIDGE_CAPPED)
    v23_multi_beats_baseline = rmse(by_model, MULTI_V23_RIDGE_CAPPED) < float(best_baseline["test_rmse_mean"])
    v23_multi_beats_scalar = scalar_to_multi_delta > args.min_repair_delta
    sham_separated = multi_sham_delta > args.min_repair_delta
    if v23_multi_beats_baseline and sham_separated:
        outcome = "multichannel_cra_adapter_candidate_signal"
    elif v23_multi_beats_scalar and sham_separated:
        outcome = "compact_failure_localized_to_scalar_adapter_but_not_public_win"
    elif readout_delta > args.min_repair_delta or target_delta > args.min_repair_delta:
        outcome = "compact_failure_partly_readout_or_target_policy"
    else:
        outcome = "compact_failure_not_repaired_by_diagnostic_adapters"
    return {
        "outcome": outcome,
        "best_promotable_model": best_promotable["model"],
        "best_promotable_rmse": best_promotable["test_rmse_mean"],
        "best_public_baseline": best_baseline["model"],
        "best_public_baseline_rmse": best_baseline["test_rmse_mean"],
        "scalar_v2_3_lms_uncapped_rmse": rmse(by_model, SCALAR_V23_LMS_UNCAPPED),
        "scalar_v2_3_ridge_uncapped_rmse": rmse(by_model, SCALAR_V23_RIDGE_UNCAPPED),
        "scalar_v2_3_lms_capped_rmse": rmse(by_model, SCALAR_V23_LMS_CAPPED),
        "scalar_v2_3_ridge_capped_rmse": rmse(by_model, SCALAR_V23_RIDGE_CAPPED),
        "multichannel_v2_3_ridge_capped_rmse": rmse(by_model, MULTI_V23_RIDGE_CAPPED),
        "multichannel_v2_3_shuffled_capped_rmse": rmse(by_model, MULTI_V23_SHUFFLED_CAPPED),
        "readout_repair_delta_rmse": readout_delta,
        "target_policy_delta_rmse": target_delta,
        "scalar_to_multichannel_delta_rmse": scalar_to_multi_delta,
        "multichannel_sham_separation_delta_rmse": multi_sham_delta,
        "multichannel_beats_best_public_baseline": v23_multi_beats_baseline,
        "multichannel_beats_scalar": v23_multi_beats_scalar,
        "multichannel_sham_separated": sham_separated,
        "freeze_authorized": False,
        "hardware_transfer_authorized": False,
    }


def factor_rows(classification: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "factor": "readout_policy",
            "delta_rmse_positive_is_better": classification["readout_repair_delta_rmse"],
            "interpretation": "ridge readout improves scalar v2.3 uncapped" if classification["readout_repair_delta_rmse"] > 0 else "no scalar readout-policy repair",
        },
        {
            "factor": "target_policy",
            "delta_rmse_positive_is_better": classification["target_policy_delta_rmse"],
            "interpretation": "capped RUL improves scalar v2.3 LMS" if classification["target_policy_delta_rmse"] > 0 else "no scalar target-policy repair",
        },
        {
            "factor": "multichannel_adapter",
            "delta_rmse_positive_is_better": classification["scalar_to_multichannel_delta_rmse"],
            "interpretation": "multichannel CRA adapter improves over scalar" if classification["multichannel_beats_scalar"] else "multichannel adapter did not clear scalar repair threshold",
        },
        {
            "factor": "sham_specificity",
            "delta_rmse_positive_is_better": classification["multichannel_sham_separation_delta_rmse"],
            "interpretation": "multichannel state is sham-separated" if classification["multichannel_sham_separated"] else "multichannel state not sham-separated enough",
        },
    ]


def write_report(output_dir: Path, payload: dict[str, Any]) -> None:
    c = payload["classification"]
    lines = [
        "# Tier 7.1d C-MAPSS Failure Analysis / Adapter Repair",
        "",
        f"- Generated: `{payload['generated_at_utc']}`",
        f"- Runner revision: `{payload['runner_revision']}`",
        f"- Status: **{payload['status'].upper()}**",
        f"- Criteria: `{payload['criteria_passed']}/{payload['criteria_total']}`",
        f"- Outcome: `{c['outcome']}`",
        "",
        "## Key Metrics",
        "",
        f"- Best promotable model: `{c['best_promotable_model']}` RMSE `{c['best_promotable_rmse']}`",
        f"- Best public baseline: `{c['best_public_baseline']}` RMSE `{c['best_public_baseline_rmse']}`",
        f"- Scalar v2.3 LMS uncapped RMSE: `{c['scalar_v2_3_lms_uncapped_rmse']}`",
        f"- Scalar v2.3 ridge uncapped RMSE: `{c['scalar_v2_3_ridge_uncapped_rmse']}`",
        f"- Scalar v2.3 LMS capped RMSE: `{c['scalar_v2_3_lms_capped_rmse']}`",
        f"- Multichannel v2.3 ridge capped RMSE: `{c['multichannel_v2_3_ridge_capped_rmse']}`",
        f"- Multichannel sham separation delta RMSE: `{c['multichannel_sham_separation_delta_rmse']}`",
        "",
        "## Boundary",
        "",
        payload["claim_boundary"],
        "",
        "## Next Step",
        "",
        payload["next_step"],
        "",
    ]
    output_dir.joinpath("tier7_1d_report.md").write_text("\n".join(lines), encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    task_uncapped = load_task(args)
    task_capped = capped_task(task_uncapped, args.rul_cap)
    channels, channel_rows = selected_channels(task_capped, task_capped.target_norm, args.max_channels)
    seeds = [int(x) for x in args.seeds.split(",") if x.strip()]
    rows: list[dict[str, Any]] = []
    per_unit: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    for seed in seeds:
        seed_rows, seed_units, seed_diag = run_seed(task_uncapped, task_capped, seed, args, channels)
        rows.extend(seed_rows)
        per_unit.extend(seed_units)
        diagnostics.append(seed_diag)
    summary = aggregate(rows)
    classification = classify(summary, args)
    preflight = read_json(TIER7_1B_RESULTS) if TIER7_1B_RESULTS.exists() else {}
    scoring = read_json(TIER7_1C_RESULTS) if TIER7_1C_RESULTS.exists() else {}
    models = {str(r["model"]) for r in rows}
    criteria = [
        criterion("Tier 7.1b preflight exists", TIER7_1B_RESULTS, "exists", TIER7_1B_RESULTS.exists()),
        criterion("Tier 7.1b preflight passed", preflight.get("status"), "== pass", preflight.get("status") == "pass"),
        criterion("Tier 7.1c scoring exists", TIER7_1C_RESULTS, "exists", TIER7_1C_RESULTS.exists()),
        criterion("Tier 7.1c outcome was negative", scoring.get("classification", {}).get("outcome"), "== v2_3_no_public_adapter_advantage", scoring.get("classification", {}).get("outcome") == "v2_3_no_public_adapter_advantage"),
        criterion("all diagnostic models ran", sorted(models), "contains required models", all(m in models for m in REQUIRED_MODELS)),
        criterion("metrics finite", True, "all model RMSE finite", all(math.isfinite(float(r["test_rmse"])) for r in rows)),
        criterion("selected channels bounded", len(channels), f"1..{args.max_channels}", 1 <= len(channels) <= args.max_channels),
        criterion("no test readout updates", [r["diagnostics"].get("test_updates") for r in rows], "all 0 or None", all((r["diagnostics"].get("test_updates") in {0, None}) for r in rows)),
        criterion("target policy probe present", [AGE_UNCAPPED, AGE_CAPPED, SCALAR_V23_LMS_CAPPED], "present", all(m in models for m in [AGE_UNCAPPED, AGE_CAPPED, SCALAR_V23_LMS_CAPPED])),
        criterion("readout policy probe present", [SCALAR_V23_LMS_UNCAPPED, SCALAR_V23_RIDGE_UNCAPPED], "present", all(m in models for m in [SCALAR_V23_LMS_UNCAPPED, SCALAR_V23_RIDGE_UNCAPPED])),
        criterion("multichannel probe and sham present", [MULTI_V23_RIDGE_CAPPED, MULTI_V23_SHUFFLED_CAPPED], "present", all(m in models for m in [MULTI_V23_RIDGE_CAPPED, MULTI_V23_SHUFFLED_CAPPED])),
        criterion("classification computed", classification["outcome"], "non-empty", bool(classification["outcome"])),
        criterion("no baseline freeze authorized", classification["freeze_authorized"], "== false", classification["freeze_authorized"] is False),
        criterion("no hardware transfer authorized", classification["hardware_transfer_authorized"], "== false", classification["hardware_transfer_authorized"] is False),
    ]
    status = "pass" if all(c["passed"] for c in criteria) else "fail"
    factors = factor_rows(classification)
    payload = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "status": status,
        "criteria": criteria,
        "criteria_passed": sum(1 for c in criteria if c["passed"]),
        "criteria_total": len(criteria),
        "failed_criteria": [c for c in criteria if not c["passed"]],
        "classification": classification,
        "fd001_profile": task_capped.fd001_profile,
        "seeds": seeds,
        "selected_channels": channel_rows,
        "model_summary": summary,
        "factor_analysis": factors,
        "seed_diagnostics": diagnostics,
        "output_dir": str(output_dir),
        "claim_boundary": (
            "Tier 7.1d is software failure analysis / adapter repair only. It is "
            "not a full C-MAPSS benchmark, not a new CRA mechanism, not a "
            "baseline freeze, not hardware/native transfer, and not AGI/ASI "
            "evidence. Continuous no-reset probes are diagnostic only and are "
            "not promotable C-MAPSS claims."
        ),
        "next_step": (
            "Use the localized factor result to define the next locked gate. If "
            "multichannel CRA state is sham-separated but still loses to fair "
            "baselines, design a stricter multichannel adapter/fairness gate. If "
            "no adapter factor repairs the gap, stop C-MAPSS promotion and move "
            "to the next predeclared public benchmark family or planned general "
            "mechanism without native transfer."
        ),
    }
    paths = {
        "results_json": output_dir / "tier7_1d_results.json",
        "report_md": output_dir / "tier7_1d_report.md",
        "summary_csv": output_dir / "tier7_1d_summary.csv",
        "model_metrics_csv": output_dir / "tier7_1d_model_metrics.csv",
        "model_summary_csv": output_dir / "tier7_1d_model_summary.csv",
        "per_unit_metrics_csv": output_dir / "tier7_1d_per_unit_metrics.csv",
        "factor_analysis_csv": output_dir / "tier7_1d_factor_analysis.csv",
        "selected_channels_csv": output_dir / "tier7_1d_selected_channels.csv",
    }
    write_json(paths["results_json"], payload)
    write_csv(paths["summary_csv"], [{"criterion": c["name"], "passed": c["passed"], "value": c["value"], "rule": c["rule"]} for c in criteria])
    write_csv(paths["model_metrics_csv"], rows)
    write_csv(paths["model_summary_csv"], summary)
    write_csv(paths["per_unit_metrics_csv"], per_unit)
    write_csv(paths["factor_analysis_csv"], factors)
    write_csv(paths["selected_channels_csv"], channel_rows)
    write_report(output_dir, payload)
    manifest = make_manifest(output_dir, paths, status)
    write_json(output_dir / "tier7_1d_latest_manifest.json", manifest)
    write_json(CONTROLLED / "tier7_1d_latest_manifest.json", manifest)
    return payload


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    p.add_argument("--data-cache", default=str(CONTROLLED.parent / ".cra_data_cache" / "nasa_cmapss"))
    p.add_argument("--url", default="https://data.nasa.gov/docs/legacy/CMAPSSData.zip")
    p.add_argument("--timeout", type=int, default=60)
    p.add_argument("--seeds", default="42,43,44")
    p.add_argument("--rul-cap", type=float, default=125.0)
    p.add_argument("--max-channels", type=int, default=12)
    p.add_argument("--history", type=int, default=12)
    p.add_argument("--ridge", type=float, default=1e-3)
    p.add_argument("--readout-lr", type=float, default=0.10)
    p.add_argument("--readout-decay", type=float, default=0.0005)
    p.add_argument("--weight-clip", type=float, default=25.0)
    p.add_argument("--output-clip", type=float, default=6.0)
    p.add_argument("--temporal-timescales", default="2,4,8,16,32,64,128")
    p.add_argument("--temporal-hidden-units", type=int, default=16)
    p.add_argument("--temporal-recurrent-scale", type=float, default=0.65)
    p.add_argument("--temporal-input-scale", type=float, default=0.35)
    p.add_argument("--temporal-hidden-decay", type=float, default=0.82)
    p.add_argument("--state-reset-interval", type=int, default=12)
    p.add_argument("--min-repair-delta", type=float, default=1.0)
    return p.parse_args()


def main() -> None:
    payload = run(parse_args())
    print(
        json.dumps(
            {
                "status": payload["status"],
                "criteria": f"{payload['criteria_passed']}/{payload['criteria_total']}",
                "outcome": payload["classification"]["outcome"],
                "best_promotable_model": payload["classification"]["best_promotable_model"],
                "best_promotable_rmse": payload["classification"]["best_promotable_rmse"],
                "output_dir": payload["output_dir"],
            },
            indent=2,
        )
    )
    if payload["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
