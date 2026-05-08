#!/usr/bin/env python3
"""Tier 7.1i - NAB fairness/statistical confirmation or failure localization.

Tier 7.1h produced a partial compact NAB signal: v2.3 beat v2.2 and all three
v2.3 shams, but did not beat the strongest external reservoir baseline. This
tier broadens the predeclared NAB subset while preserving label separation,
online scoring, and the same baseline family. The gate answers whether the
compact signal survives, collapses, or localizes to specific stream families.

Boundary: software confirmation/localization only. It does not freeze a
baseline and does not authorize hardware/native transfer by itself.
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
    cache_path,
    criterion,
    download_if_needed,
    download_source_set,
    load_cached_json,
    raw_url,
    sha256_file,
    write_csv,
    write_json,
)
from tier7_1h_compact_nab_scoring_gate import (  # noqa: E402
    CRA_MODELS,
    EXTERNAL_BASELINES,
    NO_UPDATE,
    REQUIRED_MODELS,
    SHUFFLED,
    SHUFFLED_TARGET,
    V22,
    V23,
    aggregate_metrics,
    classify,
    load_stream,
    paired_bootstrap,
    primary_score,
    run_model_stream,
)


TIER = "Tier 7.1i - NAB Fairness/Statistical Confirmation"
RUNNER_REVISION = "tier7_1i_nab_fairness_confirmation_20260508_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_1i_20260508_nab_fairness_confirmation"
TIER7_1G_RESULTS = CONTROLLED / "tier7_1g_20260508_nab_source_data_scoring_preflight" / "tier7_1g_results.json"
TIER7_1H_RESULTS = CONTROLLED / "tier7_1h_20260508_compact_nab_scoring_gate" / "tier7_1h_results.json"

BROAD_NAB_DATA_FILES = [
    "artificialWithAnomaly/art_daily_flatmiddle.csv",
    "artificialWithAnomaly/art_daily_jumpsdown.csv",
    "artificialWithAnomaly/art_daily_jumpsup.csv",
    "artificialWithAnomaly/art_load_balancer_spikes.csv",
    "realAWSCloudwatch/ec2_cpu_utilization_24ae8d.csv",
    "realAWSCloudwatch/ec2_cpu_utilization_5f5533.csv",
    "realAWSCloudwatch/ec2_disk_write_bytes_c0d644.csv",
    "realAWSCloudwatch/grok_asg_anomaly.csv",
    "realAWSCloudwatch/rds_cpu_utilization_e47b3b.csv",
    "realAdExchange/exchange-2_cpm_results.csv",
    "realAdExchange/exchange-4_cpm_results.csv",
    "realKnownCause/ambient_temperature_system_failure.csv",
    "realKnownCause/cpu_utilization_asg_misconfiguration.csv",
    "realKnownCause/ec2_request_latency_system_failure.csv",
    "realKnownCause/machine_temperature_system_failure.csv",
    "realKnownCause/nyc_taxi.csv",
    "realTraffic/TravelTime_387.csv",
    "realTraffic/speed_7578.csv",
    "realTweets/Twitter_volume_AAPL.csv",
    "realTweets/Twitter_volume_GOOG.csv",
]


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


def ensure_broad_source_set(cache_root: Path, commit: str, timeout: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    download_source_set(cache_root, commit, timeout=timeout)
    required_paths = [f"data/{path}" for path in BROAD_NAB_DATA_FILES]
    for repo_path in required_paths:
        url = raw_url(commit, repo_path)
        dst = cache_path(cache_root, commit, repo_path)
        info = download_if_needed(url, dst, timeout=timeout)
        rows.append(
            {
                "repo_path": repo_path,
                "source_url": url,
                "local_cache_path": str(dst),
                "downloaded": bool(info["downloaded"]),
                "bytes": dst.stat().st_size,
                "sha256": sha256_file(dst),
            }
        )
    return rows


def load_broad_streams(args: argparse.Namespace) -> tuple[list[Any], dict[str, Any], list[dict[str, Any]]]:
    cache_root = Path(args.data_cache).resolve()
    commit = args.commit.strip() or PINNED_NAB_COMMIT
    downloads = ensure_broad_source_set(cache_root, commit, timeout=args.timeout)
    windows_by_file = load_cached_json(cache_root, commit, "labels/combined_windows.json")
    streams = [
        load_stream(file_id, cache_root, commit, windows_by_file, args.calibration_fraction)
        for file_id in BROAD_NAB_DATA_FILES
    ]
    source = {
        "commit": commit,
        "cache_root": str(cache_root),
        "selected_files": BROAD_NAB_DATA_FILES,
        "selected_file_count": len(BROAD_NAB_DATA_FILES),
        "selected_categories": sorted({path.split("/", 1)[0] for path in BROAD_NAB_DATA_FILES}),
        "source_manifest_sha256": {
            path: sha256_file(cache_path(cache_root, commit, path))
            for path in ["labels/combined_windows.json", "config/profiles.json", "config/thresholds.json", "nab/scorer.py"]
        },
    }
    return streams, source, downloads


def summarize_by_group(rows: list[dict[str, Any]], group_key: str) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row[group_key])].append(row)
    out: list[dict[str, Any]] = []
    for group, subset in sorted(grouped.items()):
        model_rows = aggregate_metrics(subset)
        for row in model_rows:
            out.append({group_key: group, **row})
    return out


def localization_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    category_rows = summarize_by_group(rows, "category")
    stream_rows = summarize_by_group(rows, "file")
    by_category_model = {(row["category"], row["model"]): row for row in category_rows}
    by_stream_model = {(row["file"], row["model"]): row for row in stream_rows}
    categories = sorted({str(row["category"]) for row in rows})
    streams = sorted({str(row["file"]) for row in rows})
    category_wins: list[str] = []
    category_beats_v22: list[str] = []
    stream_wins: list[str] = []
    stream_beats_v22: list[str] = []
    for category in categories:
        subset = [row for row in category_rows if row["category"] == category]
        best = min(subset, key=lambda row: int(row["rank_by_primary_score"]))
        if best["model"] == V23:
            category_wins.append(category)
        v23 = by_category_model[(category, V23)]
        v22 = by_category_model[(category, V22)]
        if float(v23["primary_score_mean"]) > float(v22["primary_score_mean"]):
            category_beats_v22.append(category)
    for stream in streams:
        subset = [row for row in stream_rows if row["file"] == stream]
        best = min(subset, key=lambda row: int(row["rank_by_primary_score"]))
        if best["model"] == V23:
            stream_wins.append(stream)
        v23 = by_stream_model[(stream, V23)]
        v22 = by_stream_model[(stream, V22)]
        if float(v23["primary_score_mean"]) > float(v22["primary_score_mean"]):
            stream_beats_v22.append(stream)
    return {
        "category_summary": category_rows,
        "stream_summary": stream_rows,
        "category_count": len(categories),
        "stream_count": len(streams),
        "v2_3_category_wins": category_wins,
        "v2_3_category_beats_v2_2": category_beats_v22,
        "v2_3_stream_wins": stream_wins,
        "v2_3_stream_beats_v2_2": stream_beats_v22,
    }


def classify_confirmation(
    overall_classification: dict[str, Any],
    localization: dict[str, Any],
    args: argparse.Namespace,
) -> dict[str, Any]:
    bootstrap = overall_classification["bootstrap_vs_best_external"]
    ci_low = bootstrap.get("ci_low")
    confirmed = (
        overall_classification["best_model"] == V23
        and overall_classification["v2_3_sham_separations"] >= args.min_sham_separations
        and ci_low is not None
        and float(ci_low) > 0.0
    )
    partial = (
        bool(overall_classification["v2_3_beats_v2_2"])
        and overall_classification["v2_3_sham_separations"] >= args.min_sham_separations
    )
    localized = bool(localization["v2_3_category_wins"] or localization["v2_3_stream_wins"])
    if confirmed:
        outcome = "v2_3_broader_nab_signal_confirmed"
    elif partial and localized:
        outcome = "v2_3_nab_signal_localized_not_confirmed"
    elif partial:
        outcome = "v2_3_broader_nab_partial_signal_not_confirmed"
    else:
        outcome = "v2_3_compact_nab_signal_collapsed"
    return {
        **overall_classification,
        "outcome": outcome,
        "broader_confirmation_authorized": bool(confirmed),
        "localized_signal": bool(localized),
        "v2_3_category_wins": localization["v2_3_category_wins"],
        "v2_3_category_beats_v2_2": localization["v2_3_category_beats_v2_2"],
        "v2_3_stream_wins": localization["v2_3_stream_wins"],
        "v2_3_stream_beats_v2_2": localization["v2_3_stream_beats_v2_2"],
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
    c = payload["classification"]
    b = c["bootstrap_vs_best_external"]
    lines = [
        "# Tier 7.1i NAB Fairness/Statistical Confirmation",
        "",
        f"- Generated: `{payload['generated_at_utc']}`",
        f"- Runner revision: `{payload['runner_revision']}`",
        f"- Status: **{payload['status'].upper()}**",
        f"- Criteria: `{payload['criteria_passed']}/{payload['criteria_total']}`",
        f"- Outcome: `{c['outcome']}`",
        "",
        "## Key Metrics",
        "",
        f"- Streams: `{payload['source']['selected_file_count']}`",
        f"- Categories: `{len(payload['source']['selected_categories'])}`",
        f"- Best model: `{c['best_model']}` primary score `{c['best_model_primary_score']}`",
        f"- Best external baseline: `{c['best_external_baseline']}` primary score `{c['best_external_primary_score']}`",
        f"- v2.3 rank: `{c['v2_3_rank']}`",
        f"- v2.3 primary score: `{c['v2_3_primary_score']}`",
        f"- v2.2 primary score: `{c['v2_2_primary_score']}`",
        f"- v2.3 sham separations: `{c['v2_3_sham_separations']}`",
        f"- Bootstrap mean delta vs best external: `{b['mean_delta']}`",
        f"- Bootstrap 95% CI: `[{b['ci_low']}, {b['ci_high']}]`",
        f"- v2.3 category wins: `{c['v2_3_category_wins']}`",
        f"- v2.3 stream wins: `{c['v2_3_stream_wins']}`",
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
    output_dir.joinpath("tier7_1i_report.md").write_text("\n".join(lines), encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    preflight = read_json(TIER7_1G_RESULTS) if TIER7_1G_RESULTS.exists() else {}
    compact = read_json(TIER7_1H_RESULTS) if TIER7_1H_RESULTS.exists() else {}
    streams, source, downloads = load_broad_streams(args)
    seeds = [int(item) for item in args.seeds.split(",") if item.strip()]
    rows: list[dict[str, Any]] = []
    thresholds: list[dict[str, Any]] = []
    preview: list[dict[str, Any]] = []
    for seed in seeds:
        for stream in streams:
            for model in REQUIRED_MODELS:
                metrics, threshold_row, preview_rows = run_model_stream(stream, model, seed, args)
                rows.append(metrics)
                thresholds.append(threshold_row)
                preview.extend(preview_rows)

    summary = aggregate_metrics(rows)
    best_external = min((row for row in summary if row["model"] in EXTERNAL_BASELINES), key=lambda row: int(row["rank_by_primary_score"]))
    bootstrap = paired_bootstrap(rows, V23, str(best_external["model"]), seed=43, n=args.bootstrap_samples)
    compact_classification = classify(summary, rows, bootstrap, args)
    localization = localization_summary(rows)
    classification = classify_confirmation(compact_classification, localization, args)
    models = {str(row["model"]) for row in rows}
    threshold_label_used = [row["label_used"] for row in thresholds]
    preview_has_label_columns = any(
        key.lower() in {"label", "labels", "is_anomaly", "anomaly", "anomaly_window"}
        for row in preview
        for key in row
    )
    categories = sorted({stream.category for stream in streams})
    criteria = [
        criterion("Tier 7.1g preflight exists", TIER7_1G_RESULTS, "exists", TIER7_1G_RESULTS.exists()),
        criterion("Tier 7.1g preflight passed", preflight.get("status"), "== pass", preflight.get("status") == "pass"),
        criterion("Tier 7.1h compact scoring exists", TIER7_1H_RESULTS, "exists", TIER7_1H_RESULTS.exists()),
        criterion("Tier 7.1h compact scoring passed", compact.get("status"), "== pass", compact.get("status") == "pass"),
        criterion("NAB source commit matches preflight", source["commit"], "matches Tier 7.1g", source["commit"] == preflight.get("source", {}).get("selected_commit")),
        criterion("broader subset expands compact subset", len(streams), "> 5 streams", len(streams) > 5),
        criterion("broader subset covers categories", categories, ">= 5 categories", len(categories) >= 5),
        criterion("selected streams have anomaly windows", [len(s.windows) for s in streams], "all > 0", all(len(s.windows) > 0 for s in streams)),
        criterion("all required models ran", sorted(models), "contains required models", all(model in models for model in REQUIRED_MODELS)),
        criterion("external baselines present", sorted(EXTERNAL_BASELINES), "all present", all(model in models for model in EXTERNAL_BASELINES)),
        criterion("v2.3 shams present", [SHUFFLED, SHUFFLED_TARGET, NO_UPDATE], "all present", all(model in models for model in [SHUFFLED, SHUFFLED_TARGET, NO_UPDATE])),
        criterion("metrics finite", True, "all primary/event metrics finite", all(math.isfinite(primary_score(row)) and math.isfinite(float(row["event_f1"])) for row in rows)),
        criterion("thresholds label-free", threshold_label_used, "all false", all(not bool(x) for x in threshold_label_used)),
        criterion("score preview label-free", preview_has_label_columns, "== false", not preview_has_label_columns),
        criterion("bootstrap comparison computed", bootstrap.get("paired_units"), ">= 30 paired units", int(bootstrap.get("paired_units") or 0) >= 30),
        criterion("localization computed", classification["outcome"], "non-empty outcome", bool(classification["outcome"])),
        criterion("no baseline freeze authorized", classification["freeze_authorized"], "== false", classification["freeze_authorized"] is False),
        criterion("no hardware transfer authorized", classification["hardware_transfer_authorized"], "== false", classification["hardware_transfer_authorized"] is False),
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
        "classification": classification,
        "source": source,
        "download_manifest": downloads,
        "seeds": seeds,
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
        "model_summary": summary,
        "category_summary": localization["category_summary"],
        "stream_summary": localization["stream_summary"],
        "output_dir": str(output_dir),
        "claim_boundary": (
            "Tier 7.1i is broader NAB software confirmation/localization using "
            "label-separated online anomaly scores. It is not a full NAB benchmark "
            "claim by itself, not public usefulness proof unless confirmed by the "
            "predeclared statistical gate, not a baseline freeze, not hardware/native "
            "transfer, and not AGI/ASI evidence."
        ),
        "next_step": (
            "If v2.3 confirms on the broader subset, design the next holdout/public "
            "adapter gate before any transfer. If the signal localizes or collapses, "
            "debug the localized stream families or narrow the public usefulness claim "
            "before adding mechanisms."
        ),
    }
    paths = {
        "results_json": output_dir / "tier7_1i_results.json",
        "report_md": output_dir / "tier7_1i_report.md",
        "summary_csv": output_dir / "tier7_1i_summary.csv",
        "model_metrics_csv": output_dir / "tier7_1i_model_metrics.csv",
        "model_summary_csv": output_dir / "tier7_1i_model_summary.csv",
        "category_summary_csv": output_dir / "tier7_1i_category_summary.csv",
        "stream_summary_csv": output_dir / "tier7_1i_stream_summary.csv",
        "thresholds_csv": output_dir / "tier7_1i_thresholds.csv",
        "score_preview_csv": output_dir / "tier7_1i_score_preview.csv",
        "bootstrap_csv": output_dir / "tier7_1i_bootstrap.csv",
        "source_manifest_csv": output_dir / "tier7_1i_source_manifest.csv",
        "scoring_contract_json": output_dir / "tier7_1i_scoring_contract.json",
    }
    write_json(paths["results_json"], payload)
    write_csv(paths["summary_csv"], [{"criterion": c["name"], "passed": c["passed"], "value": c["value"], "rule": c["rule"]} for c in criteria])
    write_csv(paths["model_metrics_csv"], rows)
    write_csv(paths["model_summary_csv"], summary)
    write_csv(paths["category_summary_csv"], localization["category_summary"])
    write_csv(paths["stream_summary_csv"], localization["stream_summary"])
    write_csv(paths["thresholds_csv"], thresholds)
    write_csv(paths["score_preview_csv"], preview)
    write_csv(paths["bootstrap_csv"], [bootstrap])
    write_csv(paths["source_manifest_csv"], downloads)
    write_json(
        paths["scoring_contract_json"],
        {
            "source_preflight": str(TIER7_1G_RESULTS),
            "compact_prior": str(TIER7_1H_RESULTS),
            "source_commit": source["commit"],
            "selected_files": BROAD_NAB_DATA_FILES,
            "models": REQUIRED_MODELS,
            "external_baselines": EXTERNAL_BASELINES,
            "cra_models": CRA_MODELS,
            "threshold_policy": "per-stream calibration-prefix quantile, no labels",
            "primary_metric": "primary_score_mean = event_f1 + 0.05*window_recall + 0.05*nab_style_score - 0.002*fp_per_1000",
            "confirmation_rule": "v2.3 must be best overall, sham-separated, and bootstrap CI low > 0 versus best external baseline",
            "localization_rule": "if not confirmed, report category/stream wins and v2.2 separations without claiming public usefulness",
            "label_policy": "labels/windows are offline scoring only and are not present in score preview rows",
            "nonclaims": [
                "not a full NAB benchmark claim by itself",
                "not public usefulness proof unless statistical confirmation passes",
                "not a baseline freeze",
                "not hardware/native transfer",
                "not AGI/ASI evidence",
            ],
        },
    )
    write_report(output_dir, payload)
    manifest = make_manifest(output_dir, paths, status)
    write_json(output_dir / "tier7_1i_latest_manifest.json", manifest)
    write_json(CONTROLLED / "tier7_1i_latest_manifest.json", manifest)
    return payload


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    p.add_argument("--data-cache", default=str(DATA_CACHE))
    p.add_argument("--commit", default=PINNED_NAB_COMMIT)
    p.add_argument("--timeout", type=int, default=60)
    p.add_argument("--seeds", default="42,43,44")
    p.add_argument("--calibration-fraction", type=float, default=0.05)
    p.add_argument("--threshold-quantile", type=float, default=0.995)
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
    p.add_argument("--bootstrap-samples", type=int, default=2000)
    p.add_argument("--min-sham-separations", type=int, default=2)
    p.add_argument("--preview-rows-per-stream", type=int, default=10)
    return p.parse_args()


def main() -> None:
    payload = run(parse_args())
    print(
        json.dumps(
            {
                "status": payload["status"],
                "criteria": f"{payload['criteria_passed']}/{payload['criteria_total']}",
                "outcome": payload["classification"]["outcome"],
                "best_model": payload["classification"]["best_model"],
                "v2_3_rank": payload["classification"]["v2_3_rank"],
                "stream_count": payload["source"]["selected_file_count"],
                "output_dir": payload["output_dir"],
            },
            indent=2,
        )
    )
    if payload["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
