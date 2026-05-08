#!/usr/bin/env python3
"""Tier 7.1e - C-MAPSS capped-RUL/readout fairness confirmation.

Tier 7.1d found a tiny capped-RUL/ridge signal for the v2.2 scalar state on
FD001. This gate tests whether that signal is statistically meaningful against
the strongest fair baseline, rather than treating a small RMSE difference as a
public usefulness claim.
"""

from __future__ import annotations

import argparse
import csv
import json
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

from tier7_1c_cmapss_fd001_scoring_gate import criterion, read_json, sha256_file, write_csv, write_json  # noqa: E402


TIER = "Tier 7.1e - C-MAPSS Capped-RUL/Readout Fairness Confirmation"
RUNNER_REVISION = "tier7_1e_cmapss_capped_readout_fairness_confirmation_20260508_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_1e_20260508_cmapss_capped_readout_fairness_confirmation"
TIER7_1D_DIR = CONTROLLED / "tier7_1d_20260508_cmapss_failure_analysis_adapter_repair"
TIER7_1D_RESULTS = TIER7_1D_DIR / "tier7_1d_results.json"
TIER7_1D_PER_UNIT = TIER7_1D_DIR / "tier7_1d_per_unit_metrics.csv"
TIER7_1D_SUMMARY = TIER7_1D_DIR / "tier7_1d_model_summary.csv"

CANDIDATE = "scalar_pca1_v2_2_ridge_capped125"
PRIMARY_BASELINE = "lag_multichannel_ridge_capped125"
SECONDARY_BASELINES = [
    "age_ridge_capped125",
    "raw_multichannel_ridge_capped125",
    "scalar_pca1_v2_3_ridge_capped125",
    "multichannel_v2_3_ridge_capped125",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def model_unit_means(rows: list[dict[str, str]], model: str) -> dict[int, dict[str, float]]:
    selected = [r for r in rows if r.get("model") == model]
    out: dict[int, dict[str, float]] = {}
    for unit in sorted({int(r["unit"]) for r in selected}):
        unit_rows = [r for r in selected if int(r["unit"]) == unit]
        out[unit] = {
            "unit": float(unit),
            "rmse": float(np.mean([float(r["rmse"]) for r in unit_rows])),
            "mae": float(np.mean([float(r["mae"]) for r in unit_rows])),
            "test_rows": float(np.mean([float(r["test_rows"]) for r in unit_rows])),
            "seed_count": float(len({int(r["seed"]) for r in unit_rows})),
        }
    return out


def paired_comparison(candidate: dict[int, dict[str, float]], baseline: dict[int, dict[str, float]], baseline_name: str, rng: np.random.Generator, bootstraps: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    units = sorted(set(candidate) & set(baseline))
    candidate_rmse = np.asarray([candidate[u]["rmse"] for u in units], dtype=float)
    baseline_rmse = np.asarray([baseline[u]["rmse"] for u in units], dtype=float)
    delta = baseline_rmse - candidate_rmse
    mean_delta = float(np.mean(delta))
    median_delta = float(np.median(delta))
    sd = float(np.std(delta, ddof=1)) if len(delta) > 1 else 0.0
    effect = None if sd < 1e-12 else mean_delta / sd
    samples = []
    for idx in range(int(bootstraps)):
        choice = rng.integers(0, len(delta), size=len(delta))
        samples.append(float(np.mean(delta[choice])))
    arr = np.asarray(samples, dtype=float)
    ci_low = float(np.percentile(arr, 2.5))
    ci_high = float(np.percentile(arr, 97.5))
    row = {
        "candidate_model": CANDIDATE,
        "baseline_model": baseline_name,
        "unit_count": len(units),
        "candidate_rmse_mean_by_unit": float(np.mean(candidate_rmse)),
        "baseline_rmse_mean_by_unit": float(np.mean(baseline_rmse)),
        "mean_delta_rmse_positive_candidate_better": mean_delta,
        "median_delta_rmse_positive_candidate_better": median_delta,
        "bootstrap_ci95_low": ci_low,
        "bootstrap_ci95_high": ci_high,
        "paired_effect_size_d": effect,
        "candidate_better_units": int(np.sum(delta > 0)),
        "candidate_worse_units": int(np.sum(delta < 0)),
        "candidate_equal_units": int(np.sum(delta == 0)),
    }
    sample_rows = [
        {"baseline_model": baseline_name, "bootstrap_index": idx, "mean_delta_rmse_positive_candidate_better": value}
        for idx, value in enumerate(samples)
    ]
    return row, sample_rows


def classify(primary: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    ci_low = float(primary["bootstrap_ci95_low"])
    mean_delta = float(primary["mean_delta_rmse_positive_candidate_better"])
    effect = primary["paired_effect_size_d"]
    effect_value = 0.0 if effect is None else float(effect)
    confirmed = bool(ci_low > 0.0 and mean_delta >= args.min_mean_delta and effect_value >= args.min_effect_size)
    outcome = "v2_2_capped_signal_confirmed_candidate" if confirmed else "v2_2_capped_signal_not_statistically_confirmed"
    return {
        "outcome": outcome,
        "candidate_model": CANDIDATE,
        "primary_baseline": PRIMARY_BASELINE,
        "primary_mean_delta_rmse_positive_candidate_better": mean_delta,
        "primary_bootstrap_ci95_low": ci_low,
        "primary_bootstrap_ci95_high": float(primary["bootstrap_ci95_high"]),
        "primary_effect_size_d": effect,
        "primary_candidate_better_units": primary["candidate_better_units"],
        "primary_candidate_worse_units": primary["candidate_worse_units"],
        "min_mean_delta": args.min_mean_delta,
        "min_effect_size": args.min_effect_size,
        "confirmed": confirmed,
        "freeze_authorized": False,
        "hardware_transfer_authorized": False,
    }


def write_report(output_dir: Path, payload: dict[str, Any]) -> None:
    c = payload["classification"]
    lines = [
        "# Tier 7.1e C-MAPSS Capped-RUL/Readout Fairness Confirmation",
        "",
        f"- Generated: `{payload['generated_at_utc']}`",
        f"- Runner revision: `{payload['runner_revision']}`",
        f"- Status: **{payload['status'].upper()}**",
        f"- Criteria: `{payload['criteria_passed']}/{payload['criteria_total']}`",
        f"- Outcome: `{c['outcome']}`",
        "",
        "## Primary Comparison",
        "",
        f"- Candidate: `{c['candidate_model']}`",
        f"- Baseline: `{c['primary_baseline']}`",
        f"- Mean delta RMSE, positive means candidate better: `{c['primary_mean_delta_rmse_positive_candidate_better']}`",
        f"- Bootstrap 95% CI: `{c['primary_bootstrap_ci95_low']}` to `{c['primary_bootstrap_ci95_high']}`",
        f"- Effect size d: `{c['primary_effect_size_d']}`",
        f"- Better/worse units: `{c['primary_candidate_better_units']}` / `{c['primary_candidate_worse_units']}`",
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
    output_dir.joinpath("tier7_1e_report.md").write_text("\n".join(lines), encoding="utf-8")


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


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    tier7_1d = read_json(TIER7_1D_RESULTS) if TIER7_1D_RESULTS.exists() else {}
    per_unit_rows = read_csv_rows(TIER7_1D_PER_UNIT) if TIER7_1D_PER_UNIT.exists() else []
    summary_rows = read_csv_rows(TIER7_1D_SUMMARY) if TIER7_1D_SUMMARY.exists() else []
    rng = np.random.default_rng(args.bootstrap_seed)
    candidate = model_unit_means(per_unit_rows, CANDIDATE)
    comparisons: list[dict[str, Any]] = []
    bootstrap_rows: list[dict[str, Any]] = []
    for baseline_name in [PRIMARY_BASELINE] + SECONDARY_BASELINES:
        baseline = model_unit_means(per_unit_rows, baseline_name)
        row, samples = paired_comparison(candidate, baseline, baseline_name, rng, args.bootstraps)
        comparisons.append(row)
        if args.write_bootstrap_samples:
            bootstrap_rows.extend(samples)
    primary = next(r for r in comparisons if r["baseline_model"] == PRIMARY_BASELINE)
    classification = classify(primary, args)
    models = {r.get("model") for r in summary_rows}
    criteria = [
        criterion("Tier 7.1d results exist", TIER7_1D_RESULTS, "exists", TIER7_1D_RESULTS.exists()),
        criterion("Tier 7.1d passed", tier7_1d.get("status"), "== pass", tier7_1d.get("status") == "pass"),
        criterion("Tier 7.1d localized target/readout policy", tier7_1d.get("classification", {}).get("outcome"), "== compact_failure_partly_readout_or_target_policy", tier7_1d.get("classification", {}).get("outcome") == "compact_failure_partly_readout_or_target_policy"),
        criterion("candidate present", CANDIDATE, "in Tier 7.1d per-unit rows", bool(candidate)),
        criterion("primary baseline present", PRIMARY_BASELINE, "in Tier 7.1d per-unit rows", PRIMARY_BASELINE in {r.get("model") for r in per_unit_rows}),
        criterion("candidate unit count", len(candidate), "== 100", len(candidate) == 100),
        criterion("summary models present", sorted(models), "contains candidate and primary baseline", CANDIDATE in models and PRIMARY_BASELINE in models),
        criterion("bootstrap count", args.bootstraps, ">= 1000", args.bootstraps >= 1000),
        criterion("primary comparison computed", primary["baseline_model"], f"== {PRIMARY_BASELINE}", primary["baseline_model"] == PRIMARY_BASELINE),
        criterion("classification computed", classification["outcome"], "non-empty", bool(classification["outcome"])),
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
        "comparisons": comparisons,
        "source_tier7_1d": str(TIER7_1D_RESULTS),
        "output_dir": str(output_dir),
        "claim_boundary": (
            "Tier 7.1e is a statistical/fairness confirmation over Tier 7.1d "
            "per-unit results. It does not rerun or expand C-MAPSS, does not "
            "promote a mechanism, does not freeze a baseline, does not authorize "
            "hardware/native transfer, and does not prove public usefulness."
        ),
        "next_step": (
            "If the candidate is not confirmed, do not keep tuning C-MAPSS. Move "
            "to the next predeclared public benchmark family or a planned general "
            "mechanism with its own evidence contract. If confirmed in a later "
            "expanded gate, require full C-MAPSS FD001-FD004 and stronger "
            "external baselines before any paper usefulness claim."
        ),
    }
    paths = {
        "results_json": output_dir / "tier7_1e_results.json",
        "report_md": output_dir / "tier7_1e_report.md",
        "summary_csv": output_dir / "tier7_1e_summary.csv",
        "paired_comparisons_csv": output_dir / "tier7_1e_paired_comparisons.csv",
    }
    write_json(paths["results_json"], payload)
    write_csv(paths["summary_csv"], [{"criterion": c["name"], "passed": c["passed"], "value": c["value"], "rule": c["rule"]} for c in criteria])
    write_csv(paths["paired_comparisons_csv"], comparisons)
    if args.write_bootstrap_samples:
        paths["bootstrap_samples_csv"] = output_dir / "tier7_1e_bootstrap_samples.csv"
        write_csv(paths["bootstrap_samples_csv"], bootstrap_rows)
    write_report(output_dir, payload)
    manifest = make_manifest(output_dir, paths, status)
    write_json(output_dir / "tier7_1e_latest_manifest.json", manifest)
    write_json(CONTROLLED / "tier7_1e_latest_manifest.json", manifest)
    return payload


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    p.add_argument("--bootstraps", type=int, default=5000)
    p.add_argument("--bootstrap-seed", type=int, default=42)
    p.add_argument("--min-mean-delta", type=float, default=1.0)
    p.add_argument("--min-effect-size", type=float, default=0.2)
    p.add_argument("--write-bootstrap-samples", action="store_true")
    return p.parse_args()


def main() -> None:
    payload = run(parse_args())
    print(
        json.dumps(
            {
                "status": payload["status"],
                "criteria": f"{payload['criteria_passed']}/{payload['criteria_total']}",
                "outcome": payload["classification"]["outcome"],
                "primary_mean_delta": payload["classification"]["primary_mean_delta_rmse_positive_candidate_better"],
                "primary_ci95": [
                    payload["classification"]["primary_bootstrap_ci95_low"],
                    payload["classification"]["primary_bootstrap_ci95_high"],
                ],
                "output_dir": payload["output_dir"],
            },
            indent=2,
        )
    )
    if payload["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
