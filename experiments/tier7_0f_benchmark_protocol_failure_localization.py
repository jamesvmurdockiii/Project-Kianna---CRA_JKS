#!/usr/bin/env python3
"""Tier 7.0f - Benchmark Protocol Repair / Public Failure Localization.

Tier 7.0e showed two things:

1. v2.2 improves materially over raw CRA v2.1 on the short/medium public
   standard dynamical suite.
2. v2.2 is still not competitive with the strongest standard sequence baseline,
   and the 10k NARMA10 run is blocked by a non-finite seed-44 stream.

This tier does not tune CRA and does not add a mechanism. It repairs the
benchmark protocol boundary and localizes what the public scoreboard currently
means.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
import time
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

from tier5_19a_temporal_substrate_reference import criterion, json_safe, write_json  # noqa: E402
from tier7_0_standard_dynamical_benchmarks import build_task, parse_csv, parse_seeds  # noqa: E402


TIER = "Tier 7.0f - Benchmark Protocol Repair / Public Failure Localization"
RUNNER_REVISION = "tier7_0f_benchmark_protocol_failure_localization_20260508_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_0f_20260508_benchmark_protocol_failure_localization"
DEFAULT_LENGTHS = "720,2000,4000,8000,10000,20000,50000"
DEFAULT_SEEDS = "42,43,44"
DEFAULT_SEED_SCAN = "42:80"
CALIBRATION_DIR = CONTROLLED / "tier7_0e_20260508_length_calibration"
LONG_SCOREBOARD_DIR = CONTROLLED / "tier7_0e_20260508_length_10000_scoreboard"
V22 = "fading_memory_only_ablation"
RAW = "raw_cra_v2_1_online"
ESN = "fixed_esn_train_prefix_ridge_baseline"
LAG = "lag_only_online_lms_control"
RESERVOIR = "fixed_random_reservoir_online_control"
PUBLIC_MODELS = {V22, RAW, ESN, LAG, RESERVOIR}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def parse_lengths(raw: str) -> list[int]:
    return sorted(dict.fromkeys(int(item) for item in parse_csv(raw)))


def parse_seed_scan(raw: str) -> list[int]:
    if ":" in raw:
        start, end = raw.split(":", 1)
        return list(range(int(start), int(end) + 1))
    return [int(item) for item in parse_csv(raw)]


def write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def safe_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or abs(denominator) < 1e-12:
        return None
    return numerator / denominator


def finite_check(task_name: str, length: int, seed: int, horizon: int) -> dict[str, Any]:
    task = build_task(task_name, length, seed, horizon)
    observed = np.asarray(task.observed, dtype=float)
    target = np.asarray(task.target, dtype=float)
    observed_finite = bool(np.isfinite(observed).all())
    target_finite = bool(np.isfinite(target).all())
    finite_target = target[np.isfinite(target)]
    return {
        "task": task_name,
        "length": int(length),
        "seed": int(seed),
        "observed_finite": observed_finite,
        "target_finite": target_finite,
        "observed_nonfinite_count": int(np.size(observed) - np.count_nonzero(np.isfinite(observed))),
        "target_nonfinite_count": int(np.size(target) - np.count_nonzero(np.isfinite(target))),
        "target_min": None if finite_target.size == 0 else float(np.min(finite_target)),
        "target_max": None if finite_target.size == 0 else float(np.max(finite_target)),
        "status": "pass" if observed_finite and target_finite else "fail",
    }


def scan_narma(lengths: list[int], primary_seeds: list[int], seed_pool: list[int], horizon: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for length in lengths:
        for seed in primary_seeds:
            rows.append({**finite_check("narma10", length, seed, horizon), "scan_scope": "primary_seed_set"})
    replacement_by_length: dict[int, list[int]] = {}
    for length in lengths:
        finite_seeds = []
        for seed in seed_pool:
            check = finite_check("narma10", length, seed, horizon)
            if check["status"] == "pass":
                finite_seeds.append(seed)
            if len(finite_seeds) >= len(primary_seeds):
                break
        replacement_by_length[int(length)] = finite_seeds
    all_primary_finite_lengths = [
        length
        for length in lengths
        if all(row["status"] == "pass" for row in rows if row["length"] == length and row["scan_scope"] == "primary_seed_set")
    ]
    invalid_primary = [row for row in rows if row["status"] != "pass"]
    policy = {
        "primary_seeds": primary_seeds,
        "seed_pool": [min(seed_pool), max(seed_pool)] if seed_pool else [],
        "largest_original_seed_finite_length": max(all_primary_finite_lengths) if all_primary_finite_lengths else None,
        "invalid_primary_streams": invalid_primary,
        "replacement_finite_seeds_by_length": replacement_by_length,
        "recommended_immediate_rerun": {
            "policy": "same_seed_max_finite_length",
            "length": max(all_primary_finite_lengths) if all_primary_finite_lengths else None,
            "seeds": primary_seeds,
            "reason": "preserves original seeds while avoiding invalid NARMA streams",
        },
        "optional_sensitivity_rerun": {
            "policy": "predeclared_finite_seed_replacement",
            "length": 10000,
            "seeds": replacement_by_length.get(10000, []),
            "reason": "keeps standard NARMA formula but replaces invalid streams through a model-independent finite pre-scan",
        },
    }
    return rows, policy


def load_7_0e(calibration_dir: Path, long_dir: Path) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "calibration_results_path": str(calibration_dir / "tier7_0e_results.json"),
        "calibration_summary_path": str(calibration_dir / "tier7_0e_summary.csv"),
        "calibration_model_aggregate_path": str(calibration_dir / "tier7_0e_model_aggregate.csv"),
        "long_results_path": str(long_dir / "tier7_0e_results.json"),
    }
    payload["calibration_results"] = json.loads((calibration_dir / "tier7_0e_results.json").read_text(encoding="utf-8"))
    payload["calibration_summary"] = read_csv(calibration_dir / "tier7_0e_summary.csv")
    payload["calibration_model_aggregate"] = read_csv(calibration_dir / "tier7_0e_model_aggregate.csv")
    payload["long_results"] = json.loads((long_dir / "tier7_0e_results.json").read_text(encoding="utf-8"))
    return payload


def localize_gap(loaded: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    summary = [
        row
        for row in loaded["calibration_summary"]
        if row.get("model") in PUBLIC_MODELS and row.get("status") == "pass"
    ]
    rows: list[dict[str, Any]] = []
    for length in sorted({int(row["length"]) for row in summary}):
        for task in sorted({row["task"] for row in summary if int(row["length"]) == length}):
            by_model = {row["model"]: row for row in summary if int(row["length"]) == length and row["task"] == task}
            candidate = safe_float(by_model.get(V22, {}).get("mse_mean"))
            raw = safe_float(by_model.get(RAW, {}).get("mse_mean"))
            esn = safe_float(by_model.get(ESN, {}).get("mse_mean"))
            lag = safe_float(by_model.get(LAG, {}).get("mse_mean"))
            reservoir = safe_float(by_model.get(RESERVOIR, {}).get("mse_mean"))
            candidates = [
                (model, safe_float(row.get("mse_mean")))
                for model, row in by_model.items()
                if safe_float(row.get("mse_mean")) is not None
            ]
            candidates.sort(key=lambda item: float(item[1]))
            rank = {model: idx + 1 for idx, (model, _) in enumerate(candidates)}
            rows.append(
                {
                    "length": int(length),
                    "task": task,
                    "candidate_mse": candidate,
                    "candidate_rank": rank.get(V22),
                    "best_model": candidates[0][0] if candidates else None,
                    "best_mse": candidates[0][1] if candidates else None,
                    "candidate_divided_by_esn": ratio(candidate, esn),
                    "candidate_divided_by_lag": ratio(candidate, lag),
                    "candidate_divided_by_reservoir": ratio(candidate, reservoir),
                    "raw_divided_by_candidate": ratio(raw, candidate),
                    "candidate_corr": safe_float(by_model.get(V22, {}).get("test_corr_mean")),
                    "esn_corr": safe_float(by_model.get(ESN, {}).get("test_corr_mean")),
                    "lag_corr": safe_float(by_model.get(LAG, {}).get("test_corr_mean")),
                    "interpretation": task_interpretation(task, candidate, esn, lag, reservoir),
                }
            )
    aggregate = loaded["calibration_results"]["classification"]
    by_length = {int(k): v for k, v in aggregate.get("by_length", {}).items()}
    diagnosis = {
        "length_alone_supported": bool(
            aggregate.get("candidate_improvement_first_to_last") is not None
            and float(aggregate["candidate_improvement_first_to_last"]) >= 1.25
        ),
        "candidate_improvement_first_to_last": aggregate.get("candidate_improvement_first_to_last"),
        "best_baseline_improvement_first_to_last": aggregate.get("best_baseline_improvement_first_to_last"),
        "v2_2_improved_over_raw": bool(aggregate.get("any_improves_vs_raw_v2_1")),
        "v2_2_competitive_with_best_baseline": bool(aggregate.get("any_competitive_with_best_baseline")),
        "aggregate_by_length": by_length,
        "localized_failure_class": [
            "not explained by raw CRA inability: v2.2 improves raw v2.1",
            "not solved by more exposure at 720->2000: candidate geomean worsened while ESN remains ahead",
            "Mackey-Glass and Lorenz still favor ESN/offline train-prefix readout",
            "NARMA10 favors explicit lag memory over v2.2 fading memory",
            "10k public aggregate blocked by invalid NARMA stream, not interpretable as model evidence",
        ],
        "next_protocol": "repair finite NARMA policy, then rerun largest valid same-seed public scoreboard before adding mechanisms",
    }
    return rows, diagnosis


def task_interpretation(task: str, candidate: float | None, esn: float | None, lag: float | None, reservoir: float | None) -> str:
    if candidate is None:
        return "candidate missing"
    beats = {
        "esn": esn is not None and candidate < esn,
        "lag": lag is not None and candidate < lag,
        "reservoir": reservoir is not None and candidate < reservoir,
    }
    if task == "narma10" and beats["esn"] and beats["reservoir"] and not beats["lag"]:
        return "candidate has useful nonlinear-memory signal but explicit lag memory still wins"
    if beats["lag"] and beats["reservoir"] and not beats["esn"]:
        return "candidate beats simple online controls but ESN/offline train-prefix readout still wins"
    if not any(beats.values()):
        return "candidate trails all public baselines"
    return "mixed task-specific result"


def classify(narma_policy: dict[str, Any], diagnosis: dict[str, Any]) -> dict[str, Any]:
    invalid_10k = any(
        row.get("length") == 10000 and row.get("status") != "pass"
        for row in narma_policy.get("invalid_primary_streams", [])
    )
    if invalid_10k:
        outcome = "benchmark_protocol_blocker_confirmed"
    else:
        outcome = "benchmark_protocol_valid"
    if diagnosis["v2_2_competitive_with_best_baseline"]:
        next_step = "run ablations and compact regression before any claim upgrade"
    elif diagnosis["v2_2_improved_over_raw"]:
        next_step = "repair long benchmark protocol, rerun largest valid public scoreboard, then diagnose readout/interface or add one planned general mechanism"
    else:
        next_step = "stop blaming length and narrow or redesign the continuous benchmark interface"
    return {
        "outcome": outcome,
        "next_step": next_step,
        "claim": "benchmark protocol and failure localization evidence",
        "nonclaims": [
            "not a CRA performance improvement",
            "not a new mechanism",
            "not a baseline freeze",
            "not hardware evidence",
            "not public benchmark superiority",
            "not AGI/ASI evidence",
        ],
    }


def write_report(output_dir: Path, payload: dict[str, Any]) -> None:
    c = payload["classification"]
    diagnosis = payload["gap_diagnosis"]
    policy = payload["narma_policy"]
    lines = [
        "# Tier 7.0f Benchmark Protocol Repair / Public Failure Localization",
        "",
        f"- Generated: `{payload['generated_at_utc']}`",
        f"- Status: **{payload['status'].upper()}**",
        f"- Criteria: `{payload['criteria_passed']}/{payload['criteria_total']}`",
        f"- Outcome: `{c['outcome']}`",
        f"- Next step: {c['next_step']}",
        "",
        "## What This Proves",
        "",
        "Tier 7.0f proves the benchmark protocol/failure boundary, not a new CRA capability.",
        "",
        "## NARMA10 Finite-Stream Policy",
        "",
        f"- Largest original-seed finite length: `{policy['largest_original_seed_finite_length']}`",
        f"- Recommended immediate rerun: `{policy['recommended_immediate_rerun']}`",
        f"- Optional 10k finite-seed sensitivity: `{policy['optional_sensitivity_rerun']}`",
        f"- Invalid primary streams: `{len(policy['invalid_primary_streams'])}`",
        "",
        "## Gap Diagnosis",
        "",
        f"- v2.2 improved over raw v2.1: `{diagnosis['v2_2_improved_over_raw']}`",
        f"- v2.2 competitive with best baseline: `{diagnosis['v2_2_competitive_with_best_baseline']}`",
        f"- Length-alone support at 720->2000: `{diagnosis['length_alone_supported']}`",
        f"- Candidate improvement first-to-last: `{diagnosis['candidate_improvement_first_to_last']}`",
        "",
        "Failure classes:",
        "",
    ]
    for item in diagnosis["localized_failure_class"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Nonclaims", ""])
    for item in c["nonclaims"]:
        lines.append(f"- {item}")
    lines.append("")
    (output_dir / "tier7_0f_report.md").write_text("\n".join(lines), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=TIER)
    parser.add_argument("--lengths", default=DEFAULT_LENGTHS)
    parser.add_argument("--seeds", default=DEFAULT_SEEDS)
    parser.add_argument("--seed-count", type=int, default=None)
    parser.add_argument("--base-seed", type=int, default=42)
    parser.add_argument("--seed-scan", default=DEFAULT_SEED_SCAN)
    parser.add_argument("--horizon", type=int, default=8)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--calibration-dir", type=Path, default=CALIBRATION_DIR)
    parser.add_argument("--long-scoreboard-dir", type=Path, default=LONG_SCOREBOARD_DIR)
    return parser


def run(args: argparse.Namespace) -> dict[str, Any]:
    started = time.perf_counter()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    lengths = parse_lengths(args.lengths)
    seeds = parse_seeds(args)
    seed_pool = parse_seed_scan(args.seed_scan)
    narma_rows, narma_policy = scan_narma(lengths, seeds, seed_pool, args.horizon)
    loaded = load_7_0e(args.calibration_dir.resolve(), args.long_scoreboard_dir.resolve())
    gap_rows, gap_diagnosis = localize_gap(loaded)
    classification = classify(narma_policy, gap_diagnosis)
    criteria = [
        criterion("7.0e calibration loaded", str(args.calibration_dir), "manifest present", bool(loaded.get("calibration_results"))),
        criterion("7.0e long scoreboard loaded", str(args.long_scoreboard_dir), "manifest present", bool(loaded.get("long_results"))),
        criterion("NARMA finite scan completed", len(narma_rows), ">= lengths * primary seeds", len(narma_rows) >= len(lengths) * len(seeds)),
        criterion("10k invalid stream reproduced", narma_policy["invalid_primary_streams"], "contains length 10000 invalid primary stream", any(row.get("length") == 10000 for row in narma_policy["invalid_primary_streams"])),
        criterion("same-seed finite fallback exists", narma_policy["largest_original_seed_finite_length"], ">= 2000", (narma_policy["largest_original_seed_finite_length"] or 0) >= 2000),
        criterion("10k replacement finite seeds exist", narma_policy["optional_sensitivity_rerun"]["seeds"], f">= {len(seeds)} seeds", len(narma_policy["optional_sensitivity_rerun"]["seeds"]) >= len(seeds)),
        criterion("gap localization rows produced", len(gap_rows), ">= 6", len(gap_rows) >= 6),
        criterion("no baseline freeze authorized", False, "must remain false", True),
    ]
    status = "pass" if all(item["passed"] for item in criteria) else "fail"
    payload = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "status": status,
        "criteria": criteria,
        "criteria_passed": sum(1 for item in criteria if item["passed"]),
        "criteria_total": len(criteria),
        "output_dir": str(output_dir),
        "lengths": lengths,
        "seeds": seeds,
        "seed_scan": args.seed_scan,
        "narma_policy": narma_policy,
        "gap_diagnosis": gap_diagnosis,
        "gap_rows": gap_rows,
        "classification": classification,
        "runtime_seconds": time.perf_counter() - started,
        "claim_boundary": (
            "Tier 7.0f is benchmark-protocol and failure-localization evidence only. "
            "It does not improve CRA, add a mechanism, freeze a baseline, or authorize "
            "hardware transfer."
        ),
    }
    write_json(output_dir / "tier7_0f_results.json", payload)
    write_json(
        output_dir / "tier7_0f_fairness_contract.json",
        {
            "tier": TIER,
            "standard_tasks": ["mackey_glass", "lorenz", "narma10"],
            "finite_stream_policy": "invalid generated observed/target streams cannot be scored as model evidence",
            "recommended_rerun": narma_policy["recommended_immediate_rerun"],
            "optional_sensitivity": narma_policy["optional_sensitivity_rerun"],
            "custom_task_policy": "custom diagnostics may localize failure but cannot replace the public scoreboard",
        },
    )
    write_rows(output_dir / "tier7_0f_narma_scan.csv", narma_rows)
    write_rows(output_dir / "tier7_0f_gap_table.csv", gap_rows)
    write_rows(
        output_dir / "tier7_0f_summary.csv",
        [
            {
                "status": status,
                "outcome": classification["outcome"],
                "largest_original_seed_finite_length": narma_policy["largest_original_seed_finite_length"],
                "v2_2_improved_over_raw": gap_diagnosis["v2_2_improved_over_raw"],
                "v2_2_competitive_with_best_baseline": gap_diagnosis["v2_2_competitive_with_best_baseline"],
                "length_alone_supported": gap_diagnosis["length_alone_supported"],
                "next_step": classification["next_step"],
            }
        ],
    )
    write_report(output_dir, payload)
    write_json(
        CONTROLLED / "tier7_0f_latest_manifest.json",
        {
            "tier": TIER,
            "runner_revision": RUNNER_REVISION,
            "generated_at_utc": payload["generated_at_utc"],
            "status": status,
            "manifest": str(output_dir / "tier7_0f_results.json"),
            "output_dir": str(output_dir),
        },
    )
    return payload


def main() -> None:
    result = run(build_parser().parse_args())
    print(
        json.dumps(
            {
                "tier": TIER,
                "status": result["status"],
                "criteria": f"{result['criteria_passed']}/{result['criteria_total']}",
                "outcome": result["classification"]["outcome"],
                "next_step": result["classification"]["next_step"],
                "output_dir": result["output_dir"],
            },
            indent=2,
        )
    )
    if result["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
