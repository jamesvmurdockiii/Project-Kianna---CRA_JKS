#!/usr/bin/env python3
"""Tier 7.1j - NAB failure/localization analysis.

Tier 7.1i broadened NAB scoring and found that v2.3 beat v2.2 plus shams, but
simple rolling z-score won the aggregate. This tier is a diagnostic gate, not a
new mechanism. It separates threshold policy, false-positive penalty, category
mix, stream localization, and sham separation so the next decision is grounded
before adding mechanisms or transferring anything to hardware.

Boundary: software failure analysis only. It does not freeze a baseline and does
not authorize hardware/native transfer.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections import defaultdict
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

from tier7_1g_nab_source_data_scoring_preflight import (  # noqa: E402
    DATA_CACHE,
    PINNED_NAB_COMMIT,
    criterion,
    sha256_file,
    write_csv,
    write_json,
)
from tier7_1h_compact_nab_scoring_gate import (  # noqa: E402
    EWMA,
    NO_UPDATE,
    RESERVOIR,
    ROLLING_MAD,
    ROLLING_Z,
    SHUFFLED,
    SHUFFLED_TARGET,
    V22,
    V23,
    calibration_threshold,
    detector_scores,
    primary_score,
    score_stream,
)
from tier7_1i_nab_fairness_confirmation import (  # noqa: E402
    BROAD_NAB_DATA_FILES,
    load_broad_streams,
)


TIER = "Tier 7.1j - NAB Failure/Localization Analysis"
RUNNER_REVISION = "tier7_1j_nab_failure_localization_20260508_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_1j_20260508_nab_failure_localization"
TIER7_1I_RESULTS = CONTROLLED / "tier7_1i_20260508_nab_fairness_confirmation" / "tier7_1i_results.json"

KEY_MODELS = [ROLLING_Z, RESERVOIR, EWMA, ROLLING_MAD, V22, V23, SHUFFLED, SHUFFLED_TARGET, NO_UPDATE]
THRESHOLD_QUANTILES = [0.99, 0.995, 0.999]
FP_PENALTIES = [0.0, 0.001, 0.002, 0.005, 0.01]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def adjusted_primary(row: dict[str, Any], fp_penalty: float) -> float:
    return (
        float(row["event_f1"])
        + 0.05 * float(row["window_recall"])
        + 0.05 * float(row["nab_style_score_normalized"])
        - float(fp_penalty) * float(row["fp_per_1000_non_anomaly_points"])
    )


def summarize_policy(rows: list[dict[str, Any]], fp_penalty: float) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for model in sorted({str(row["model"]) for row in rows}):
        subset = [row for row in rows if row["model"] == model]
        scores = [adjusted_primary(row, fp_penalty) for row in subset]
        out.append(
            {
                "threshold_quantile": subset[0]["threshold_quantile"],
                "fp_penalty": float(fp_penalty),
                "model": model,
                "runs": len(subset),
                "primary_score_mean": float(np.mean(scores)),
                "primary_score_median": float(np.median(scores)),
                "event_f1_mean": float(np.mean([float(row["event_f1"]) for row in subset])),
                "window_recall_mean": float(np.mean([float(row["window_recall"]) for row in subset])),
                "nab_style_score_mean": float(np.mean([float(row["nab_style_score_normalized"]) for row in subset])),
                "fp_per_1000_mean": float(np.mean([float(row["fp_per_1000_non_anomaly_points"]) for row in subset])),
                "false_positive_events_mean": float(np.mean([float(row["false_positive_events"]) for row in subset])),
            }
        )
    ranked = sorted(out, key=lambda row: (-float(row["primary_score_mean"]), -float(row["event_f1_mean"]), float(row["fp_per_1000_mean"]), str(row["model"])))
    rank = {row["model"]: idx + 1 for idx, row in enumerate(ranked)}
    for row in out:
        row["rank_by_primary_score"] = rank[row["model"]]
    return sorted(out, key=lambda row: (int(row["rank_by_primary_score"]), str(row["model"])))


def group_policy_summary(rows: list[dict[str, Any]], group_key: str, threshold_quantile: float, fp_penalty: float) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row[group_key])].append(row)
    out: list[dict[str, Any]] = []
    for group, subset in sorted(grouped.items()):
        for summary in summarize_policy(subset, fp_penalty):
            out.append({group_key: group, **summary, "threshold_quantile": threshold_quantile, "fp_penalty": fp_penalty})
    return out


def run_policy_matrix(args: argparse.Namespace) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    streams, source, _downloads = load_broad_streams(args)
    seeds = [int(item) for item in args.seeds.split(",") if item.strip()]
    score_cache: dict[tuple[int, str, str], np.ndarray] = {}
    policy_rows: list[dict[str, Any]] = []
    thresholds: list[dict[str, Any]] = []
    for seed in seeds:
        for stream in streams:
            for model in KEY_MODELS:
                scores, _pred, _diag = detector_scores(stream, model, seed, args)
                score_cache[(seed, stream.file, model)] = scores
                for quantile in THRESHOLD_QUANTILES:
                    threshold, threshold_meta = calibration_threshold(scores, stream.calibration_n, quantile)
                    metrics = score_stream(stream, model, seed, scores, threshold, threshold_meta)
                    metrics["threshold_quantile"] = float(quantile)
                    metrics["threshold_label_used"] = bool(threshold_meta.get("label_used", False))
                    policy_rows.append(metrics)
                    thresholds.append(
                        {
                            "model": model,
                            "seed": seed,
                            "file": stream.file,
                            "threshold_quantile": quantile,
                            "threshold": threshold,
                            **threshold_meta,
                        }
                    )
    policy_summary: list[dict[str, Any]] = []
    category_summary: list[dict[str, Any]] = []
    stream_summary: list[dict[str, Any]] = []
    for quantile in THRESHOLD_QUANTILES:
        quantile_rows = [row for row in policy_rows if float(row["threshold_quantile"]) == quantile]
        for fp_penalty in FP_PENALTIES:
            policy_summary.extend(summarize_policy(quantile_rows, fp_penalty))
            category_summary.extend(group_policy_summary(quantile_rows, "category", quantile, fp_penalty))
            stream_summary.extend(group_policy_summary(quantile_rows, "file", quantile, fp_penalty))
    return policy_rows, policy_summary, thresholds, {
        "source": source,
        "stream_profile": [
            {
                "file": s.file,
                "category": s.category,
                "rows": len(s.values_raw),
                "windows": len(s.windows),
                "label_points": int(np.sum(s.labels)),
                "calibration_rows": s.calibration_n,
                "raw_chronological": s.raw_chronological,
            }
            for s in streams
        ],
        "category_summary": category_summary,
        "stream_summary": stream_summary,
    }


def best_rows(policy_summary: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best: list[dict[str, Any]] = []
    keys = sorted({(float(row["threshold_quantile"]), float(row["fp_penalty"])) for row in policy_summary})
    for threshold_quantile, fp_penalty in keys:
        subset = [
            row
            for row in policy_summary
            if float(row["threshold_quantile"]) == threshold_quantile and float(row["fp_penalty"]) == fp_penalty
        ]
        best.append(min(subset, key=lambda row: int(row["rank_by_primary_score"])))
    return best


def diagnose(
    policy_summary: list[dict[str, Any]],
    category_summary: list[dict[str, Any]],
    stream_summary: list[dict[str, Any]],
) -> dict[str, Any]:
    default_subset = [
        row
        for row in policy_summary
        if abs(float(row["threshold_quantile"]) - 0.995) < 1e-12 and abs(float(row["fp_penalty"]) - 0.002) < 1e-12
    ]
    default_best = min(default_subset, key=lambda row: int(row["rank_by_primary_score"]))
    default_by_model = {row["model"]: row for row in default_subset}
    grid_best = best_rows(policy_summary)
    v23_grid_wins = [row for row in grid_best if row["model"] == V23]
    v23_best_rank = min(int(row["rank_by_primary_score"]) for row in policy_summary if row["model"] == V23)
    v23_beats_zscore_cells = 0
    total_cells = 0
    for threshold_quantile, fp_penalty in sorted({(float(row["threshold_quantile"]), float(row["fp_penalty"])) for row in policy_summary}):
        by_model = {
            row["model"]: row
            for row in policy_summary
            if float(row["threshold_quantile"]) == threshold_quantile and float(row["fp_penalty"]) == fp_penalty
        }
        total_cells += 1
        if float(by_model[V23]["primary_score_mean"]) > float(by_model[ROLLING_Z]["primary_score_mean"]):
            v23_beats_zscore_cells += 1
    default_category = [
        row
        for row in category_summary
        if abs(float(row["threshold_quantile"]) - 0.995) < 1e-12 and abs(float(row["fp_penalty"]) - 0.002) < 1e-12
    ]
    default_stream = [
        row
        for row in stream_summary
        if abs(float(row["threshold_quantile"]) - 0.995) < 1e-12 and abs(float(row["fp_penalty"]) - 0.002) < 1e-12
    ]
    category_wins = sorted(
        row["category"]
        for row in default_category
        if row["model"] == V23 and int(row["rank_by_primary_score"]) == 1
    )
    stream_wins = sorted(
        row["file"]
        for row in default_stream
        if row["model"] == V23 and int(row["rank_by_primary_score"]) == 1
    )
    v23_vs_components = {
        "event_f1_delta_vs_rolling_zscore": float(default_by_model[V23]["event_f1_mean"]) - float(default_by_model[ROLLING_Z]["event_f1_mean"]),
        "window_recall_delta_vs_rolling_zscore": float(default_by_model[V23]["window_recall_mean"]) - float(default_by_model[ROLLING_Z]["window_recall_mean"]),
        "nab_style_delta_vs_rolling_zscore": float(default_by_model[V23]["nab_style_score_mean"]) - float(default_by_model[ROLLING_Z]["nab_style_score_mean"]),
        "fp_per_1000_delta_vs_rolling_zscore": float(default_by_model[V23]["fp_per_1000_mean"]) - float(default_by_model[ROLLING_Z]["fp_per_1000_mean"]),
    }
    if v23_grid_wins:
        failure_class = "threshold_or_fp_penalty_sensitive"
    elif category_wins or stream_wins:
        failure_class = "localized_stream_family_signal_not_aggregate"
    elif v23_beats_zscore_cells > 0:
        failure_class = "weak_policy_sensitive_signal"
    else:
        failure_class = "simple_residual_baseline_dominates_broader_nab"
    return {
        "failure_class": failure_class,
        "default_best_model": default_best["model"],
        "default_best_primary_score": default_best["primary_score_mean"],
        "v2_3_default_rank": default_by_model[V23]["rank_by_primary_score"],
        "v2_3_default_primary_score": default_by_model[V23]["primary_score_mean"],
        "rolling_zscore_default_primary_score": default_by_model[ROLLING_Z]["primary_score_mean"],
        "v2_3_best_rank_any_policy": v23_best_rank,
        "v2_3_policy_grid_wins": len(v23_grid_wins),
        "v2_3_beats_zscore_cells": v23_beats_zscore_cells,
        "policy_cells": total_cells,
        "v2_3_category_wins_default_policy": category_wins,
        "v2_3_stream_wins_default_policy": stream_wins,
        "component_deltas_vs_rolling_zscore": v23_vs_components,
        "freeze_authorized": False,
        "hardware_transfer_authorized": False,
    }


def make_manifest(output_dir: Path, artifacts: dict[str, Path], status: str) -> dict[str, Any]:
    return {
        "tier": TIER,
        "status": status,
        "generated_at_utc": utc_now(),
        "runner_revision": RUNNER_REVISION,
        "output_dir": output_dir,
        "artifacts": [
            {"name": name, "path": path, "sha256": sha256_file(path), "bytes": path.stat().st_size}
            for name, path in sorted(artifacts.items())
        ],
    }


def write_report(output_dir: Path, payload: dict[str, Any]) -> None:
    d = payload["diagnosis"]
    lines = [
        "# Tier 7.1j NAB Failure/Localization Analysis",
        "",
        f"- Generated: `{payload['generated_at_utc']}`",
        f"- Runner revision: `{payload['runner_revision']}`",
        f"- Status: **{payload['status'].upper()}**",
        f"- Criteria: `{payload['criteria_passed']}/{payload['criteria_total']}`",
        f"- Failure class: `{d['failure_class']}`",
        "",
        "## Key Findings",
        "",
        f"- Default best model: `{d['default_best_model']}` score `{d['default_best_primary_score']}`",
        f"- v2.3 default rank: `{d['v2_3_default_rank']}` score `{d['v2_3_default_primary_score']}`",
        f"- v2.3 policy-grid wins: `{d['v2_3_policy_grid_wins']}` / `{d['policy_cells']}`",
        f"- v2.3 beats rolling z-score cells: `{d['v2_3_beats_zscore_cells']}` / `{d['policy_cells']}`",
        f"- v2.3 default category wins: `{d['v2_3_category_wins_default_policy']}`",
        f"- v2.3 default stream wins: `{d['v2_3_stream_wins_default_policy']}`",
        f"- Component deltas vs rolling z-score: `{d['component_deltas_vs_rolling_zscore']}`",
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
    output_dir.joinpath("tier7_1j_report.md").write_text("\n".join(lines), encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    prior = read_json(TIER7_1I_RESULTS) if TIER7_1I_RESULTS.exists() else {}
    policy_rows, policy_summary, thresholds, extra = run_policy_matrix(args)
    category_summary = extra["category_summary"]
    stream_summary = extra["stream_summary"]
    diagnosis = diagnose(policy_summary, category_summary, stream_summary)
    threshold_label_used = [row["label_used"] for row in thresholds]
    criteria = [
        criterion("Tier 7.1i exists", TIER7_1I_RESULTS, "exists", TIER7_1I_RESULTS.exists()),
        criterion("Tier 7.1i passed", prior.get("status"), "== pass", prior.get("status") == "pass"),
        criterion("key models present", sorted({row["model"] for row in policy_rows}), "contains key models", all(model in {row["model"] for row in policy_rows} for model in KEY_MODELS)),
        criterion("threshold policies tested", THRESHOLD_QUANTILES, ">= 3 policies", len(THRESHOLD_QUANTILES) >= 3),
        criterion("false-positive penalties tested", FP_PENALTIES, ">= 4 penalties", len(FP_PENALTIES) >= 4),
        criterion("broader NAB subset retained", len(BROAD_NAB_DATA_FILES), ">= 20 streams", len(BROAD_NAB_DATA_FILES) >= 20),
        criterion("thresholds label-free", threshold_label_used, "all false", all(not bool(x) for x in threshold_label_used)),
        criterion("policy metrics finite", True, "all finite", all(math.isfinite(adjusted_primary(row, 0.002)) for row in policy_rows)),
        criterion("diagnosis computed", diagnosis["failure_class"], "non-empty", bool(diagnosis["failure_class"])),
        criterion("localization computed", diagnosis["v2_3_stream_wins_default_policy"], "list present", isinstance(diagnosis["v2_3_stream_wins_default_policy"], list)),
        criterion("no freeze authorized", diagnosis["freeze_authorized"], "== false", diagnosis["freeze_authorized"] is False),
        criterion("no hardware transfer authorized", diagnosis["hardware_transfer_authorized"], "== false", diagnosis["hardware_transfer_authorized"] is False),
    ]
    status = "pass" if all(c["passed"] for c in criteria) else "fail"
    payload = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "status": status,
        "criteria": criteria,
        "criteria_passed": sum(1 for c in criteria if c["passed"]),
        "criteria_total": len(criteria),
        "failed_criteria": [c for c in criteria if not c["passed"]],
        "diagnosis": diagnosis,
        "source": extra["source"],
        "stream_profile": extra["stream_profile"],
        "threshold_quantiles": THRESHOLD_QUANTILES,
        "fp_penalties": FP_PENALTIES,
        "key_models": KEY_MODELS,
        "output_dir": str(output_dir),
        "claim_boundary": (
            "Tier 7.1j is software failure/localization analysis over the Tier "
            "7.1i broader NAB subset. It is not public usefulness proof, not a "
            "promoted mechanism, not a baseline freeze, not hardware/native "
            "transfer, and not AGI/ASI evidence."
        ),
        "next_step": (
            "If the failure localizes to scoring/threshold policy, repair the "
            "adapter/readout contract before mechanisms. If simple residual "
            "baselines dominate across policy variants, narrow the NAB claim or "
            "return to planned general mechanisms only with a predeclared failure "
            "hypothesis."
        ),
    }
    paths = {
        "results_json": output_dir / "tier7_1j_results.json",
        "report_md": output_dir / "tier7_1j_report.md",
        "summary_csv": output_dir / "tier7_1j_summary.csv",
        "policy_metrics_csv": output_dir / "tier7_1j_policy_metrics.csv",
        "policy_summary_csv": output_dir / "tier7_1j_policy_summary.csv",
        "category_summary_csv": output_dir / "tier7_1j_category_summary.csv",
        "stream_summary_csv": output_dir / "tier7_1j_stream_summary.csv",
        "thresholds_csv": output_dir / "tier7_1j_thresholds.csv",
        "diagnosis_csv": output_dir / "tier7_1j_diagnosis.csv",
        "contract_json": output_dir / "tier7_1j_failure_analysis_contract.json",
    }
    write_json(paths["results_json"], payload)
    write_csv(paths["summary_csv"], [{"criterion": c["name"], "passed": c["passed"], "value": c["value"], "rule": c["rule"]} for c in criteria])
    write_csv(paths["policy_metrics_csv"], policy_rows)
    write_csv(paths["policy_summary_csv"], policy_summary)
    write_csv(paths["category_summary_csv"], category_summary)
    write_csv(paths["stream_summary_csv"], stream_summary)
    write_csv(paths["thresholds_csv"], thresholds)
    write_csv(paths["diagnosis_csv"], [diagnosis])
    write_json(
        paths["contract_json"],
        {
            "prior_gate": str(TIER7_1I_RESULTS),
            "source_commit": PINNED_NAB_COMMIT,
            "selected_files": BROAD_NAB_DATA_FILES,
            "key_models": KEY_MODELS,
            "threshold_quantiles": THRESHOLD_QUANTILES,
            "fp_penalties": FP_PENALTIES,
            "question": "Why does rolling z-score win the broader NAB aggregate while v2.3 remains sham-separated and localized?",
            "nonclaims": [
                "not public usefulness proof",
                "not a promoted mechanism",
                "not a baseline freeze",
                "not hardware/native transfer",
                "not AGI/ASI evidence",
            ],
        },
    )
    write_report(output_dir, payload)
    manifest = make_manifest(output_dir, paths, status)
    write_json(output_dir / "tier7_1j_latest_manifest.json", manifest)
    write_json(CONTROLLED / "tier7_1j_latest_manifest.json", manifest)
    return payload


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    p.add_argument("--data-cache", default=str(DATA_CACHE))
    p.add_argument("--commit", default=PINNED_NAB_COMMIT)
    p.add_argument("--timeout", type=int, default=60)
    p.add_argument("--seeds", default="42,43,44")
    p.add_argument("--calibration-fraction", type=float, default=0.05)
    p.add_argument("--history", type=int, default=12)
    p.add_argument("--rolling-window", type=int, default=96)
    p.add_argument("--ewma-alpha", type=float, default=0.025)
    p.add_argument("--ridge", type=float, default=1e-3)
    p.add_argument("--readout-lr", type=float, default=0.05)
    p.add_argument("--readout-decay", type=float, default=0.0005)
    p.add_argument("--weight-clip", type=float, default=25.0)
    p.add_argument("--temporal-timescales", default="2,4,8,16,32,64,128")
    p.add_argument("--temporal-hidden-units", type=int, default=16)
    p.add_argument("--temporal-recurrent-scale", type=float, default=0.65)
    p.add_argument("--temporal-input-scale", type=float, default=0.35)
    p.add_argument("--temporal-hidden-decay", type=float, default=0.82)
    p.add_argument("--reservoir-units", type=int, default=32)
    p.add_argument("--reservoir-spectral-radius", type=float, default=0.9)
    p.add_argument("--reservoir-input-scale", type=float, default=0.5)
    p.add_argument("--esn-units", type=int, default=48)
    p.add_argument("--esn-spectral-radius", type=float, default=0.95)
    return p.parse_args()


def main() -> None:
    payload = run(parse_args())
    print(
        json.dumps(
            {
                "status": payload["status"],
                "criteria": f"{payload['criteria_passed']}/{payload['criteria_total']}",
                "failure_class": payload["diagnosis"]["failure_class"],
                "default_best_model": payload["diagnosis"]["default_best_model"],
                "v2_3_default_rank": payload["diagnosis"]["v2_3_default_rank"],
                "output_dir": payload["output_dir"],
            },
            indent=2,
        )
    )
    if payload["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
