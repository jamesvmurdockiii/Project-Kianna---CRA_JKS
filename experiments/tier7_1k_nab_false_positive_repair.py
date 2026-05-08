#!/usr/bin/env python3
"""Tier 7.1k - NAB adapter/readout false-positive repair.

Tier 7.1j localized the broader NAB gap to threshold/false-positive pressure:
v2.3 catches more anomaly windows/events than rolling z-score but pays too much
NAB-style false-positive penalty. This tier tests no-label alarm/readout
policies that can reduce false positives while preserving event/window recall.

Boundary: software adapter/readout repair only. It is not a new CRA mechanism,
not public usefulness proof by itself, not a baseline freeze, and not
hardware/native transfer.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
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
    contiguous_alarm_events,
    detector_scores,
)
from tier7_1i_nab_fairness_confirmation import (  # noqa: E402
    BROAD_NAB_DATA_FILES,
    load_broad_streams,
)


TIER = "Tier 7.1k - NAB Adapter/Readout False-Positive Repair"
RUNNER_REVISION = "tier7_1k_nab_false_positive_repair_20260508_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_1k_20260508_nab_false_positive_repair"
TIER7_1J_RESULTS = CONTROLLED / "tier7_1j_20260508_nab_failure_localization" / "tier7_1j_results.json"

KEY_MODELS = [ROLLING_Z, RESERVOIR, EWMA, ROLLING_MAD, V22, V23, SHUFFLED, SHUFFLED_TARGET, NO_UPDATE]
ALARM_POLICIES = ["raw", "persist2", "persist3", "persist2_cooldown12", "hysteresis_995_990"]


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


def apply_alarm_policy(scores: np.ndarray, high_threshold: float, low_threshold: float, policy: str) -> np.ndarray:
    above = np.asarray(scores > high_threshold, dtype=bool)
    if policy == "raw":
        return above
    if policy == "persist2":
        return above & np.concatenate([[False], above[:-1]])
    if policy == "persist3":
        return above & np.concatenate([[False], above[:-1]]) & np.concatenate([[False, False], above[:-2]])
    if policy == "persist2_cooldown12":
        base = above & np.concatenate([[False], above[:-1]])
        alarms = np.zeros(len(base), dtype=bool)
        cooldown = 0
        for idx, flag in enumerate(base):
            if cooldown > 0:
                cooldown -= 1
                continue
            if flag:
                alarms[idx] = True
                cooldown = 12
        return alarms
    if policy == "hysteresis_995_990":
        alarms = np.zeros(len(scores), dtype=bool)
        active = False
        for idx, score in enumerate(scores):
            if active:
                active = bool(score > low_threshold)
            else:
                active = bool(score > high_threshold)
            alarms[idx] = active
        return alarms
    raise ValueError(f"unknown alarm policy: {policy}")


def score_alarms(stream: Any, model: str, seed: int, scores: np.ndarray, alarms: np.ndarray, policy: str, high_threshold: float, low_threshold: float) -> dict[str, Any]:
    labels = stream.labels
    alarms = np.asarray(alarms, dtype=bool)
    tp = int(np.sum(alarms & labels))
    fp = int(np.sum(alarms & ~labels))
    fn = int(np.sum(~alarms & labels))
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    point_f1 = 2.0 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    events = contiguous_alarm_events(alarms, stream.timestamps, labels)
    false_positive_events = [event for event in events if not event["overlaps_anomaly"]]
    detected_windows = 0
    latency_fraction_rewards: list[float] = []
    latencies_seconds: list[float] = []
    for start, end in stream.windows:
        hit_indices = [idx for idx, ts in enumerate(stream.timestamps) if start <= ts <= end and alarms[idx]]
        if hit_indices:
            detected_windows += 1
            first = hit_indices[0]
            latency = max(0.0, (stream.timestamps[first] - start).total_seconds())
            duration = max(1.0, (end - start).total_seconds())
            latencies_seconds.append(latency)
            latency_fraction_rewards.append(max(0.0, 1.0 - latency / duration))
    window_count = len(stream.windows)
    window_recall = detected_windows / window_count if window_count else 0.0
    event_precision = detected_windows / (detected_windows + len(false_positive_events)) if (detected_windows + len(false_positive_events)) else 0.0
    event_f1 = 2.0 * event_precision * window_recall / (event_precision + window_recall) if (event_precision + window_recall) else 0.0
    non_anomaly_points = max(1, int(np.sum(~labels)))
    fp_per_1000 = 1000.0 * fp / non_anomaly_points
    nab_style_raw = sum(latency_fraction_rewards) - window_count + detected_windows - 0.11 * len(false_positive_events)
    nab_style_normalized = (nab_style_raw + window_count) / max(1e-9, 2.0 * window_count) if window_count else 0.0
    primary = event_f1 + 0.05 * window_recall + 0.05 * nab_style_normalized - 0.002 * fp_per_1000
    return {
        "model": model,
        "seed": int(seed),
        "file": stream.file,
        "category": stream.category,
        "alarm_policy": policy,
        "rows": int(len(scores)),
        "window_count": int(window_count),
        "high_threshold": float(high_threshold),
        "low_threshold": float(low_threshold),
        "alarm_count": int(np.sum(alarms)),
        "tp_points": tp,
        "fp_points": fp,
        "fn_points": fn,
        "point_precision": float(precision),
        "point_recall": float(recall),
        "point_f1": float(point_f1),
        "window_detected": int(detected_windows),
        "window_recall": float(window_recall),
        "false_positive_events": int(len(false_positive_events)),
        "event_precision": float(event_precision),
        "event_f1": float(event_f1),
        "fp_per_1000_non_anomaly_points": float(fp_per_1000),
        "mean_latency_seconds": None if not latencies_seconds else float(np.mean(latencies_seconds)),
        "nab_style_score_raw": float(nab_style_raw),
        "nab_style_score_normalized": float(nab_style_normalized),
        "primary_score": float(primary),
        "threshold_label_used": False,
    }


def summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    keys = sorted({(str(row["alarm_policy"]), str(row["model"])) for row in rows})
    for policy, model in keys:
        subset = [row for row in rows if row["alarm_policy"] == policy and row["model"] == model]
        out.append(
            {
                "alarm_policy": policy,
                "model": model,
                "runs": len(subset),
                "primary_score_mean": float(np.mean([float(row["primary_score"]) for row in subset])),
                "event_f1_mean": float(np.mean([float(row["event_f1"]) for row in subset])),
                "window_recall_mean": float(np.mean([float(row["window_recall"]) for row in subset])),
                "nab_style_score_mean": float(np.mean([float(row["nab_style_score_normalized"]) for row in subset])),
                "fp_per_1000_mean": float(np.mean([float(row["fp_per_1000_non_anomaly_points"]) for row in subset])),
                "false_positive_events_mean": float(np.mean([float(row["false_positive_events"]) for row in subset])),
            }
        )
    for policy in sorted({row["alarm_policy"] for row in out}):
        subset = [row for row in out if row["alarm_policy"] == policy]
        ranked = sorted(subset, key=lambda row: (-float(row["primary_score_mean"]), -float(row["event_f1_mean"]), float(row["fp_per_1000_mean"]), str(row["model"])))
        rank = {row["model"]: idx + 1 for idx, row in enumerate(ranked)}
        for row in subset:
            row["rank_by_primary_score"] = rank[row["model"]]
    return sorted(out, key=lambda row: (str(row["alarm_policy"]), int(row["rank_by_primary_score"]), str(row["model"])))


def summarize_group(rows: list[dict[str, Any]], group_key: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for group in sorted({str(row[group_key]) for row in rows}):
        for row in summarize([row for row in rows if str(row[group_key]) == group]):
            out.append({group_key: group, **row})
    return out


def classify(summary_rows: list[dict[str, Any]], category_rows: list[dict[str, Any]], stream_rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_policy_model = {(row["alarm_policy"], row["model"]): row for row in summary_rows}
    raw_v23 = by_policy_model[("raw", V23)]
    raw_z = by_policy_model[("raw", ROLLING_Z)]
    best_rows = []
    for policy in ALARM_POLICIES:
        subset = [row for row in summary_rows if row["alarm_policy"] == policy]
        best_rows.append(min(subset, key=lambda row: int(row["rank_by_primary_score"])))
    v23_policy_rows = [by_policy_model[(policy, V23)] for policy in ALARM_POLICIES]
    best_v23 = max(v23_policy_rows, key=lambda row: float(row["primary_score_mean"]))
    best_policy = best_v23["alarm_policy"]
    best_policy_z = by_policy_model[(best_policy, ROLLING_Z)]
    best_policy_v22 = by_policy_model[(best_policy, V22)]
    shams = [by_policy_model[(best_policy, SHUFFLED)], by_policy_model[(best_policy, SHUFFLED_TARGET)], by_policy_model[(best_policy, NO_UPDATE)]]
    fp_reduction = float(raw_v23["fp_per_1000_mean"]) - float(best_v23["fp_per_1000_mean"])
    event_f1_loss = float(raw_v23["event_f1_mean"]) - float(best_v23["event_f1_mean"])
    window_recall_loss = float(raw_v23["window_recall_mean"]) - float(best_v23["window_recall_mean"])
    v23_beats_z = float(best_v23["primary_score_mean"]) > float(best_policy_z["primary_score_mean"])
    v23_beats_v22 = float(best_v23["primary_score_mean"]) > float(best_policy_v22["primary_score_mean"])
    sham_separations = sum(float(best_v23["primary_score_mean"]) > float(row["primary_score_mean"]) for row in shams)
    category_wins = sorted(
        row["category"]
        for row in category_rows
        if row["alarm_policy"] == best_policy and row["model"] == V23 and int(row["rank_by_primary_score"]) == 1
    )
    stream_wins = sorted(
        row["file"]
        for row in stream_rows
        if row["alarm_policy"] == best_policy and row["model"] == V23 and int(row["rank_by_primary_score"]) == 1
    )
    if v23_beats_z and v23_beats_v22 and sham_separations >= 2:
        outcome = "v2_3_nab_false_positive_repair_candidate"
    elif fp_reduction > 0 and event_f1_loss <= 0.03 and window_recall_loss <= 0.10:
        outcome = "v2_3_false_positive_reduced_but_not_superior"
    else:
        outcome = "v2_3_alarm_policy_repair_not_sufficient"
    return {
        "outcome": outcome,
        "raw_v2_3_primary_score": raw_v23["primary_score_mean"],
        "raw_v2_3_fp_per_1000": raw_v23["fp_per_1000_mean"],
        "raw_rolling_zscore_primary_score": raw_z["primary_score_mean"],
        "best_v2_3_policy": best_policy,
        "best_v2_3_primary_score": best_v23["primary_score_mean"],
        "best_v2_3_rank": best_v23["rank_by_primary_score"],
        "best_v2_3_fp_per_1000": best_v23["fp_per_1000_mean"],
        "best_policy_rolling_zscore_primary_score": best_policy_z["primary_score_mean"],
        "v2_3_beats_rolling_zscore_under_best_policy": bool(v23_beats_z),
        "v2_3_beats_v2_2_under_best_policy": bool(v23_beats_v22),
        "v2_3_sham_separations_under_best_policy": int(sham_separations),
        "fp_per_1000_reduction_vs_raw": float(fp_reduction),
        "event_f1_loss_vs_raw": float(event_f1_loss),
        "window_recall_loss_vs_raw": float(window_recall_loss),
        "v2_3_policy_wins": [row["alarm_policy"] for row in best_rows if row["model"] == V23],
        "v2_3_category_wins": category_wins,
        "v2_3_stream_wins": stream_wins,
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
    lines = [
        "# Tier 7.1k NAB Adapter/Readout False-Positive Repair",
        "",
        f"- Generated: `{payload['generated_at_utc']}`",
        f"- Runner revision: `{payload['runner_revision']}`",
        f"- Status: **{payload['status'].upper()}**",
        f"- Criteria: `{payload['criteria_passed']}/{payload['criteria_total']}`",
        f"- Outcome: `{c['outcome']}`",
        "",
        "## Key Metrics",
        "",
        f"- Best v2.3 policy: `{c['best_v2_3_policy']}`",
        f"- Best v2.3 primary score: `{c['best_v2_3_primary_score']}`",
        f"- Best v2.3 rank: `{c['best_v2_3_rank']}`",
        f"- Rolling z-score under best v2.3 policy: `{c['best_policy_rolling_zscore_primary_score']}`",
        f"- v2.3 FP/1000 reduction vs raw: `{c['fp_per_1000_reduction_vs_raw']}`",
        f"- v2.3 event-F1 loss vs raw: `{c['event_f1_loss_vs_raw']}`",
        f"- v2.3 window-recall loss vs raw: `{c['window_recall_loss_vs_raw']}`",
        f"- v2.3 sham separations: `{c['v2_3_sham_separations_under_best_policy']}`",
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
    output_dir.joinpath("tier7_1k_report.md").write_text("\n".join(lines), encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    prior = read_json(TIER7_1J_RESULTS) if TIER7_1J_RESULTS.exists() else {}
    streams, source, _downloads = load_broad_streams(args)
    seeds = [int(item) for item in args.seeds.split(",") if item.strip()]
    rows: list[dict[str, Any]] = []
    thresholds: list[dict[str, Any]] = []
    for seed in seeds:
        for stream in streams:
            for model in KEY_MODELS:
                scores, _pred, _diag = detector_scores(stream, model, seed, args)
                high_threshold, high_meta = calibration_threshold(scores, stream.calibration_n, 0.995)
                low_threshold, low_meta = calibration_threshold(scores, stream.calibration_n, 0.990)
                thresholds.append(
                    {
                        "model": model,
                        "seed": seed,
                        "file": stream.file,
                        "high_threshold": high_threshold,
                        "low_threshold": low_threshold,
                        "high_label_used": high_meta.get("label_used", False),
                        "low_label_used": low_meta.get("label_used", False),
                    }
                )
                for policy in ALARM_POLICIES:
                    alarms = apply_alarm_policy(scores, high_threshold, low_threshold, policy)
                    rows.append(score_alarms(stream, model, seed, scores, alarms, policy, high_threshold, low_threshold))
    summary = summarize(rows)
    category_summary = summarize_group(rows, "category")
    stream_summary = summarize_group(rows, "file")
    classification = classify(summary, category_summary, stream_summary)
    threshold_label_used = [row["high_label_used"] or row["low_label_used"] for row in thresholds]
    criteria = [
        criterion("Tier 7.1j exists", TIER7_1J_RESULTS, "exists", TIER7_1J_RESULTS.exists()),
        criterion("Tier 7.1j passed", prior.get("status"), "== pass", prior.get("status") == "pass"),
        criterion("alarm policies tested", ALARM_POLICIES, ">= 5 policies", len(ALARM_POLICIES) >= 5),
        criterion("key models present", sorted({row["model"] for row in rows}), "contains key models", all(model in {row["model"] for row in rows} for model in KEY_MODELS)),
        criterion("thresholds label-free", threshold_label_used, "all false", all(not bool(x) for x in threshold_label_used)),
        criterion("metrics finite", True, "all primary metrics finite", all(math.isfinite(float(row["primary_score"])) for row in rows)),
        criterion("classification computed", classification["outcome"], "non-empty", bool(classification["outcome"])),
        criterion("no freeze authorized", classification["freeze_authorized"], "== false", classification["freeze_authorized"] is False),
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
        "alarm_policies": ALARM_POLICIES,
        "key_models": KEY_MODELS,
        "output_dir": str(output_dir),
        "claim_boundary": (
            "Tier 7.1k is software adapter/readout repair over the Tier 7.1i "
            "broader NAB subset. It is not a new CRA mechanism, not public "
            "usefulness proof by itself, not a baseline freeze, not hardware/"
            "native transfer, and not AGI/ASI evidence."
        ),
        "next_step": (
            "If the repair candidate beats rolling z-score while preserving sham "
            "separation, run fairness confirmation. Otherwise narrow the NAB claim "
            "or return to planned general mechanisms with this false-positive "
            "failure mode as the predeclared target."
        ),
    }
    paths = {
        "results_json": output_dir / "tier7_1k_results.json",
        "report_md": output_dir / "tier7_1k_report.md",
        "summary_csv": output_dir / "tier7_1k_summary.csv",
        "policy_metrics_csv": output_dir / "tier7_1k_policy_metrics.csv",
        "policy_summary_csv": output_dir / "tier7_1k_policy_summary.csv",
        "category_summary_csv": output_dir / "tier7_1k_category_summary.csv",
        "stream_summary_csv": output_dir / "tier7_1k_stream_summary.csv",
        "thresholds_csv": output_dir / "tier7_1k_thresholds.csv",
        "classification_csv": output_dir / "tier7_1k_classification.csv",
        "contract_json": output_dir / "tier7_1k_repair_contract.json",
    }
    write_json(paths["results_json"], payload)
    write_csv(paths["summary_csv"], [{"criterion": c["name"], "passed": c["passed"], "value": c["value"], "rule": c["rule"]} for c in criteria])
    write_csv(paths["policy_metrics_csv"], rows)
    write_csv(paths["policy_summary_csv"], summary)
    write_csv(paths["category_summary_csv"], category_summary)
    write_csv(paths["stream_summary_csv"], stream_summary)
    write_csv(paths["thresholds_csv"], thresholds)
    write_csv(paths["classification_csv"], [classification])
    write_json(
        paths["contract_json"],
        {
            "prior_gate": str(TIER7_1J_RESULTS),
            "source_commit": PINNED_NAB_COMMIT,
            "selected_files": BROAD_NAB_DATA_FILES,
            "alarm_policies": ALARM_POLICIES,
            "key_models": KEY_MODELS,
            "question": "Can no-label alarm/readout policies reduce v2.3 false positives while preserving recall enough to beat rolling z-score?",
            "nonclaims": [
                "not a new CRA mechanism",
                "not public usefulness proof by itself",
                "not a baseline freeze",
                "not hardware/native transfer",
                "not AGI/ASI evidence",
            ],
        },
    )
    write_report(output_dir, payload)
    manifest = make_manifest(output_dir, paths, status)
    write_json(output_dir / "tier7_1k_latest_manifest.json", manifest)
    write_json(CONTROLLED / "tier7_1k_latest_manifest.json", manifest)
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
                "outcome": payload["classification"]["outcome"],
                "best_v2_3_policy": payload["classification"]["best_v2_3_policy"],
                "best_v2_3_rank": payload["classification"]["best_v2_3_rank"],
                "output_dir": payload["output_dir"],
            },
            indent=2,
        )
    )
    if payload["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
