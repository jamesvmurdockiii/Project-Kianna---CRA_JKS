#!/usr/bin/env python3
"""Tier 7.1f - Next public adapter contract / family selection.

C-MAPSS did not produce a confirmed public usefulness signal under the compact
path. This contract selects the next public benchmark family before scoring, so
the repo does not drift into ad-hoc benchmark shopping.
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

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from tier7_1c_cmapss_fd001_scoring_gate import criterion, read_json, sha256_file, write_csv, write_json  # noqa: E402


TIER = "Tier 7.1f - Next Public Adapter Contract / Family Selection"
RUNNER_REVISION = "tier7_1f_next_public_adapter_contract_20260508_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_1f_20260508_next_public_adapter_contract"
TIER7_1E_RESULTS = CONTROLLED / "tier7_1e_20260508_cmapss_capped_readout_fairness_confirmation" / "tier7_1e_results.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_report(output_dir: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# Tier 7.1f Next Public Adapter Contract / Family Selection",
        "",
        f"- Generated: `{payload['generated_at_utc']}`",
        f"- Runner revision: `{payload['runner_revision']}`",
        f"- Status: **{payload['status'].upper()}**",
        f"- Criteria: `{payload['criteria_passed']}/{payload['criteria_total']}`",
        f"- Selected adapter: `{payload['selected_adapter']['adapter_id']}`",
        "",
        "## Why This Adapter",
        "",
        payload["selected_adapter"]["rationale"],
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
    output_dir.joinpath("tier7_1f_report.md").write_text("\n".join(lines), encoding="utf-8")


def write_source_csv(path: Path, sources: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = ["name", "url", "role", "license_or_source_note"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys, lineterminator="\n")
        writer.writeheader()
        writer.writerows([{k: row.get(k, "") for k in keys} for row in sources])


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


def build_contract() -> dict[str, Any]:
    return {
        "adapter_id": "numenta_nab_streaming_anomaly",
        "dataset_family": "Numenta Anomaly Benchmark (NAB)",
        "task_type": "online streaming anomaly detection",
        "rationale": (
            "C-MAPSS behaved like a monotone remaining-useful-life regression problem, "
            "which is not the strongest pressure for CRA's memory/adaptation path. NAB "
            "is a public streaming anomaly benchmark with labeled anomaly windows, "
            "real-time scoring, false-positive pressure, and nonstationary time-series "
            "streams. It better targets online prediction error, surprise, adaptation, "
            "and recovery without moving hardware prematurely."
        ),
        "official_sources": [
            {
                "name": "Numenta NAB GitHub repository",
                "url": "https://github.com/numenta/NAB",
                "role": "official code/data/labels repository",
                "license_or_source_note": "MIT license shown by GitHub repository metadata; repository includes data, labels, scoring tools, and README.",
            },
            {
                "name": "NAB data directory",
                "url": "https://github.com/numenta/NAB/tree/master/data",
                "role": "public time-series data files",
                "license_or_source_note": "Use files from the official repository only; preserve source commit/hash in preflight.",
            },
            {
                "name": "NAB labels directory",
                "url": "https://github.com/numenta/NAB/tree/master/labels",
                "role": "anomaly-window labels and label subsets",
                "license_or_source_note": "Labels are scoring-only; no online detector may read labels before emitting anomaly scores.",
            },
            {
                "name": "Evaluating Real-time Anomaly Detection Algorithms - the Numenta Anomaly Benchmark",
                "url": "https://arxiv.org/abs/1510.03336",
                "role": "original NAB publication / scoring motivation",
                "license_or_source_note": "Use for benchmark/scoring description and citation.",
            },
        ],
        "preprocessing_contract": [
            "download or clone official NAB source only",
            "record source URL, commit or release tag if available, checksum/hash manifest",
            "stream each CSV chronologically",
            "normalize using train/calibration prefix only when a model requires normalization",
            "keep anomaly labels in a separate scoring file",
            "no online model may access future labels, future points, or anomaly windows before scoring",
            "predeclare file subsets before scoring; tiny subsets are smoke only",
        ],
        "metrics": [
            "NAB Standard profile score if scorer integration is practical",
            "NAB reward-low-FP and reward-low-FN scores if scorer integration is practical",
            "event-window precision, recall, and F1",
            "pointwise AUROC / AUPRC as secondary metrics",
            "false positives per 1000 points",
            "detection latency inside anomaly windows",
            "per-file and per-category score tables",
        ],
        "required_baselines": [
            "null/no-alarm detector",
            "random calibrated detector",
            "rolling z-score / Gaussian window detector",
            "EWMA residual detector",
            "rolling median/MAD detector",
            "online AR/ridge predictor residual detector",
            "reservoir/ESN prediction-error detector",
            "CRA v2.2/v2.3 prediction-error or state-surprise detector",
            "CRA shams: shuffled state, no-update, no-memory, wrong-threshold calibration",
            "published NAB scoreboard values as citation/reference only, not direct rerun unless reproduced",
        ],
        "pass_fail_contract": {
            "preflight_pass": [
                "official source is reachable or cached with documented checksum",
                "data and labels parse",
                "chosen file subset is predeclared",
                "scoring labels are separated from online streams",
                "no label leakage in detector rows",
            ],
            "scoring_candidate_pass": [
                "CRA beats or complements the strongest reproduced baseline on predeclared primary metric",
                "effect survives per-file/category analysis",
                "sham controls lose",
                "threshold/calibration protocol is fair",
                "confidence intervals or bootstrap intervals support the result",
            ],
            "fail_or_park": [
                "simple reproduced baselines dominate",
                "CRA only wins one cherry-picked file/category",
                "threshold tuning explains the result",
                "shams match CRA",
                "labels leak into online scoring",
            ],
        },
        "nonclaims": [
            "not a scored NAB result",
            "not public usefulness evidence",
            "not a baseline freeze",
            "not hardware/native transfer",
            "not proof of anomaly-detection superiority",
            "not AGI/ASI evidence",
        ],
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    tier7_1e = read_json(TIER7_1E_RESULTS) if TIER7_1E_RESULTS.exists() else {}
    contract = build_contract()
    criteria = [
        criterion("Tier 7.1e results exist", TIER7_1E_RESULTS, "exists", TIER7_1E_RESULTS.exists()),
        criterion("Tier 7.1e passed", tier7_1e.get("status"), "== pass", tier7_1e.get("status") == "pass"),
        criterion("C-MAPSS signal not confirmed", tier7_1e.get("classification", {}).get("outcome"), "== v2_2_capped_signal_not_statistically_confirmed", tier7_1e.get("classification", {}).get("outcome") == "v2_2_capped_signal_not_statistically_confirmed"),
        criterion("selected adapter declared", contract["adapter_id"], "non-empty", bool(contract["adapter_id"])),
        criterion("official sources declared", len(contract["official_sources"]), ">= 3", len(contract["official_sources"]) >= 3),
        criterion("preprocessing contract declared", len(contract["preprocessing_contract"]), ">= 5", len(contract["preprocessing_contract"]) >= 5),
        criterion("metrics declared", len(contract["metrics"]), ">= 5", len(contract["metrics"]) >= 5),
        criterion("required baselines declared", len(contract["required_baselines"]), ">= 6", len(contract["required_baselines"]) >= 6),
        criterion("pass/fail contract declared", sorted(contract["pass_fail_contract"]), "contains pass/fail", all(k in contract["pass_fail_contract"] for k in ["preflight_pass", "scoring_candidate_pass", "fail_or_park"])),
        criterion("nonclaims include no hardware transfer", contract["nonclaims"], "contains not hardware/native transfer", "not hardware/native transfer" in contract["nonclaims"]),
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
        "selected_adapter": contract,
        "source_tier7_1e": str(TIER7_1E_RESULTS),
        "output_dir": str(output_dir),
        "claim_boundary": (
            "Tier 7.1f is a contract/family-selection gate only. It does not "
            "download NAB, score CRA, compare models, freeze a baseline, authorize "
            "hardware/native transfer, or prove public usefulness."
        ),
        "next_step": (
            "Tier 7.1g NAB source/data/scoring preflight: verify source access, "
            "source hash/commit, file/label parse, label-separated streams, tiny "
            "leakage-safe smoke rows, and scoring-interface feasibility before any "
            "full NAB scoring."
        ),
    }
    paths = {
        "results_json": output_dir / "tier7_1f_results.json",
        "report_md": output_dir / "tier7_1f_report.md",
        "summary_csv": output_dir / "tier7_1f_summary.csv",
        "source_contract_csv": output_dir / "tier7_1f_source_contract.csv",
    }
    write_json(paths["results_json"], payload)
    write_csv(paths["summary_csv"], [{"criterion": c["name"], "passed": c["passed"], "value": c["value"], "rule": c["rule"]} for c in criteria])
    write_source_csv(paths["source_contract_csv"], contract["official_sources"])
    write_report(output_dir, payload)
    manifest = make_manifest(output_dir, paths, status)
    write_json(output_dir / "tier7_1f_latest_manifest.json", manifest)
    write_json(CONTROLLED / "tier7_1f_latest_manifest.json", manifest)
    return payload


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return p.parse_args()


def main() -> None:
    payload = run(parse_args())
    print(
        json.dumps(
            {
                "status": payload["status"],
                "criteria": f"{payload['criteria_passed']}/{payload['criteria_total']}",
                "selected_adapter": payload["selected_adapter"]["adapter_id"],
                "output_dir": payload["output_dir"],
            },
            indent=2,
        )
    )
    if payload["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
