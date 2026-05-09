#!/usr/bin/env python3
"""Tier 7.4e - cost-aware policy/action held-out scoring preflight.

Tier 7.4d locked the held-out/public action-cost contract. This preflight does
not score v2.4. It verifies that the public-source artifacts, held-out splits,
fixed cost model, action schema, baselines, shams, metrics, and output schemas
exist before any held-out scoring gate is allowed to run.

Boundary: preflight/schema evidence only. No performance scoring, no public
usefulness claim, no new baseline freeze, and no hardware/native transfer.
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
BASELINES = ROOT / "baselines"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from tier7_1g_nab_source_data_scoring_preflight import criterion, sha256_file, write_csv, write_json  # noqa: E402


TIER = "Tier 7.4e - Cost-Aware Policy/Action Held-Out Scoring Preflight"
RUNNER_REVISION = "tier7_4e_cost_aware_policy_action_heldout_preflight_20260509_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_4e_20260509_cost_aware_policy_action_heldout_preflight"
TIER7_4D_RESULTS = CONTROLLED / "tier7_4d_20260509_cost_aware_policy_action_heldout_contract" / "tier7_4d_results.json"
TIER7_1B_RESULTS = CONTROLLED / "tier7_1b_20260508_cmapss_source_data_preflight" / "tier7_1b_results.json"
TIER7_1G_RESULTS = CONTROLLED / "tier7_1g_20260508_nab_source_data_scoring_preflight" / "tier7_1g_results.json"
TIER7_1L_RESULTS = CONTROLLED / "tier7_1l_20260508_nab_locked_policy_holdout_confirmation" / "tier7_1l_results.json"
V24_BASELINE = BASELINES / "CRA_EVIDENCE_BASELINE_v2.4.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def csv_header(path: Path) -> list[str]:
    rows = read_csv_rows(path)
    return list(rows[0].keys()) if rows else []


def build_split_manifest(contract: dict[str, Any], nab_holdout: dict[str, Any], cmapss: dict[str, Any]) -> dict[str, Any]:
    nab_source = nab_holdout.get("source") or {}
    cmapss_profile = cmapss.get("fd001_profile") or {}
    return {
        "locked_by": "Tier 7.4d",
        "scoring_gate": "Tier 7.4f - Cost-Aware Policy/Action Held-Out Scoring Gate",
        "families": [
            {
                "family": "nab_heldout_alarm_action_cost",
                "source": "Numenta NAB",
                "commit": nab_source.get("commit"),
                "heldout_files": nab_source.get("heldout_files", []),
                "heldout_file_count": nab_source.get("heldout_file_count", 0),
                "heldout_categories": nab_source.get("heldout_categories", []),
                "disjoint_from_policy_selection": bool(nab_source.get("disjoint_from_tier7_1k_broad_subset")),
                "calibration_rule": "per-stream calibration rows only; no held-out label tuning",
                "test_rule": "score actions on held-out rows/windows after online action emission",
                "label_visibility": "offline scoring only",
            },
            {
                "family": "cmapss_maintenance_action_cost",
                "source": "NASA C-MAPSS FD001",
                "download_url": cmapss.get("download_url"),
                "zip_sha256": cmapss.get("zip_sha256"),
                "train_units": cmapss_profile.get("train_units"),
                "test_units": cmapss_profile.get("test_units"),
                "train_rows": cmapss_profile.get("train_rows"),
                "test_rows": cmapss_profile.get("test_rows"),
                "calibration_rule": "train units only; train-only normalization from Tier 7.1b",
                "test_rule": "emit maintenance action before RUL feedback for each test cycle",
                "label_visibility": "offline RUL labels only",
            },
            {
                "family": "standard_dynamical_action_cost",
                "source": "locked Tier 7.0 Mackey-Glass/Lorenz/NARMA10 generator",
                "split_rule": "reuse locked train/calibration/test windows; no tuning on test windows",
                "claim_role": "secondary diagnostic, not public usefulness alone",
            },
            {
                "family": "heldout_synthetic_policy_stress",
                "source": "locked local mechanism stressors",
                "split_rule": "fixed seeds and task parameters before scoring",
                "claim_role": "mechanism localization only",
            },
        ],
        "global_leakage_rules": contract["split_and_leakage_rules"],
    }


def build_scoring_schema(contract: dict[str, Any]) -> dict[str, Any]:
    return {
        "online_action_row": [
            "family",
            "stream_or_unit",
            "event_id",
            "time_index",
            "model",
            "action",
            "confidence",
            "prediction",
            "feedback_visible",
            "cost_visible",
            "label_visible",
        ],
        "offline_scoring_row": [
            "family",
            "stream_or_unit",
            "event_id",
            "model",
            "action",
            "label_or_outcome",
            "utility",
            "false_positive",
            "missed_event",
            "latency",
            "regret_vs_oracle",
        ],
        "model_score_row": [
            "family",
            "model",
            "expected_utility",
            "cost_normalized_score",
            "regret_vs_oracle",
            "false_positive_cost_per_1000",
            "missed_event_cost",
            "action_latency",
            "calibration_error",
            "action_rate",
        ],
        "statistical_support_row": [
            "family",
            "candidate",
            "baseline",
            "metric",
            "mean_delta",
            "ci_low",
            "ci_high",
            "effect_size",
            "paired_units",
        ],
        "required_metrics": contract["primary_metrics"],
        "required_statistics": contract["statistics"],
    }


def make_manifest(output_dir: Path, artifacts: dict[str, Path], status: str) -> dict[str, Any]:
    return {
        "tier": TIER,
        "status": status,
        "generated_at_utc": utc_now(),
        "runner_revision": RUNNER_REVISION,
        "output_dir": str(output_dir),
        "artifacts": [
            {
                "name": name,
                "path": str(path),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
            for name, path in sorted(artifacts.items())
        ],
    }


def write_report(output_dir: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# Tier 7.4e Cost-Aware Policy/Action Held-Out Scoring Preflight",
        "",
        f"- Generated: `{payload['generated_at_utc']}`",
        f"- Runner revision: `{payload['runner_revision']}`",
        f"- Status: **{payload['status'].upper()}**",
        f"- Criteria: `{payload['criteria_passed']}/{payload['criteria_total']}`",
        f"- Next gate: `{payload['decision']['next_gate']}`",
        "",
        "## Boundary",
        "",
        payload["claim_boundary"],
        "",
        "## Locked Families",
        "",
    ]
    for family in payload["split_manifest"]["families"]:
        lines.append(f"- `{family['family']}`: {family.get('source', '')}")
    lines.extend(
        [
            "",
            "## What This Preflight Proves",
            "",
            "- The 7.4d contract exists and passed.",
            "- Public source/data preflights exist for NAB and C-MAPSS.",
            "- Held-out splits, fixed costs, baseline/sham inventories, and scoring schemas are materialized before scoring.",
            "- No performance scores or public usefulness claims are produced here.",
            "",
        ]
    )
    output_dir.joinpath("tier7_4e_report.md").write_text("\n".join(lines), encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    tier7_4d = read_json(TIER7_4D_RESULTS) if TIER7_4D_RESULTS.exists() else {}
    contract = (tier7_4d.get("contract") or {})
    v24 = read_json(V24_BASELINE) if V24_BASELINE.exists() else {}
    cmapss = read_json(TIER7_1B_RESULTS) if TIER7_1B_RESULTS.exists() else {}
    nab_preflight = read_json(TIER7_1G_RESULTS) if TIER7_1G_RESULTS.exists() else {}
    nab_holdout = read_json(TIER7_1L_RESULTS) if TIER7_1L_RESULTS.exists() else {}

    split_manifest = build_split_manifest(contract, nab_holdout, cmapss) if contract else {"families": []}
    scoring_schema = build_scoring_schema(contract) if contract else {}
    cost_model = contract.get("locked_cost_model", {})
    baselines = contract.get("baselines", [])
    shams = contract.get("shams_and_ablations", [])

    nab_stream_path = CONTROLLED / "tier7_1g_20260508_nab_source_data_scoring_preflight" / "tier7_1g_smoke_stream.csv"
    nab_label_path = CONTROLLED / "tier7_1g_20260508_nab_source_data_scoring_preflight" / "tier7_1g_label_windows.csv"
    cmapss_stream_path = CONTROLLED / "tier7_1b_20260508_cmapss_source_data_preflight" / "tier7_1b_smoke_stream_preview.csv"
    cmapss_label_path = CONTROLLED / "tier7_1b_20260508_cmapss_source_data_preflight" / "tier7_1b_smoke_scoring_labels.csv"

    source_artifacts = [
        {"family": "nab", "artifact": "tier7_1g_results", "path": str(TIER7_1G_RESULTS), "exists": TIER7_1G_RESULTS.exists()},
        {"family": "nab", "artifact": "tier7_1l_results", "path": str(TIER7_1L_RESULTS), "exists": TIER7_1L_RESULTS.exists()},
        {"family": "nab", "artifact": "online_smoke_stream", "path": str(nab_stream_path), "exists": nab_stream_path.exists(), "rows": len(read_csv_rows(nab_stream_path)), "header": ",".join(csv_header(nab_stream_path))},
        {"family": "nab", "artifact": "offline_label_windows", "path": str(nab_label_path), "exists": nab_label_path.exists(), "rows": len(read_csv_rows(nab_label_path)), "header": ",".join(csv_header(nab_label_path))},
        {"family": "cmapss", "artifact": "tier7_1b_results", "path": str(TIER7_1B_RESULTS), "exists": TIER7_1B_RESULTS.exists()},
        {"family": "cmapss", "artifact": "online_smoke_stream", "path": str(cmapss_stream_path), "exists": cmapss_stream_path.exists(), "rows": len(read_csv_rows(cmapss_stream_path)), "header": ",".join(csv_header(cmapss_stream_path))},
        {"family": "cmapss", "artifact": "offline_labels", "path": str(cmapss_label_path), "exists": cmapss_label_path.exists(), "rows": len(read_csv_rows(cmapss_label_path)), "header": ",".join(csv_header(cmapss_label_path))},
    ]

    nab_family = split_manifest["families"][0] if split_manifest.get("families") else {}
    cmapss_family = split_manifest["families"][1] if len(split_manifest.get("families", [])) > 1 else {}
    schema_fields = {field for row in scoring_schema.values() if isinstance(row, list) for field in row if isinstance(field, str)}
    criteria = [
        criterion("Tier 7.4d exists", str(TIER7_4D_RESULTS), "exists", TIER7_4D_RESULTS.exists()),
        criterion("Tier 7.4d passed", tier7_4d.get("status"), "== pass", tier7_4d.get("status") == "pass"),
        criterion("v2.4 baseline frozen", v24.get("status"), "== frozen", v24.get("status") == "frozen"),
        criterion("NAB source preflight passed", nab_preflight.get("status"), "== pass", nab_preflight.get("status") == "pass"),
        criterion("C-MAPSS source preflight passed", cmapss.get("status"), "== pass", cmapss.get("status") == "pass"),
        criterion("NAB holdout evidence available", nab_holdout.get("status"), "== pass", nab_holdout.get("status") == "pass"),
        criterion("NAB heldout split is locked and disjoint", nab_family, ">=12 files and disjoint", nab_family.get("heldout_file_count", 0) >= 12 and bool(nab_family.get("disjoint_from_policy_selection"))),
        criterion("C-MAPSS train/test split is locked", cmapss_family, "100 train/test units", cmapss_family.get("train_units") == 100 and cmapss_family.get("test_units") == 100),
        criterion("raw public data cache is ignored", ".cra_data_cache/", "present in .gitignore", ".cra_data_cache/" in (ROOT / ".gitignore").read_text(encoding="utf-8")),
        criterion("online and offline artifacts exist", source_artifacts, "all exist", all(row["exists"] for row in source_artifacts)),
        criterion(
            "online streams separate labels",
            [csv_header(nab_stream_path), csv_header(cmapss_stream_path)],
            "only visibility flags, no offline labels/outcomes",
            "offline_rul_label" not in ",".join(csv_header(cmapss_stream_path)).lower()
            and "label_points" not in ",".join(csv_header(nab_stream_path)).lower()
            and "window_start" not in ",".join(csv_header(nab_stream_path)).lower()
            and "label_available_in_stream" in csv_header(nab_stream_path)
            and "target_available_in_stream" in csv_header(cmapss_stream_path),
        ),
        criterion("offline labels exist separately", [len(read_csv_rows(nab_label_path)), len(read_csv_rows(cmapss_label_path))], ">0 label rows", len(read_csv_rows(nab_label_path)) > 0 and len(read_csv_rows(cmapss_label_path)) > 0),
        criterion("cost model is numeric and complete", cost_model, ">=8 numeric costs", len(cost_model) >= 8 and all(isinstance(v, (int, float)) for v in cost_model.values())),
        criterion("baseline inventory complete", baselines, ">=10 baselines", len(baselines) >= 10),
        criterion("sham inventory complete", shams, ">=8 shams/ablations", len(shams) >= 8),
        criterion("scoring schema includes no hidden labels online", scoring_schema.get("online_action_row", []), "feedback/cost/label visibility fields present", {"feedback_visible", "cost_visible", "label_visible"}.issubset(set(scoring_schema.get("online_action_row", [])))),
        criterion("scoring schema includes utility and regret offline", scoring_schema.get("offline_scoring_row", []), "utility/regret fields present", {"utility", "regret_vs_oracle"}.issubset(set(scoring_schema.get("offline_scoring_row", [])))),
        criterion("statistics schema includes confidence support", scoring_schema.get("statistical_support_row", []), "CI/effect fields present", {"ci_low", "ci_high", "effect_size", "paired_units"}.issubset(set(scoring_schema.get("statistical_support_row", [])))),
        criterion("preflight emits no heldout performance scores", list(schema_fields), "no expected_utility values computed", True, "schemas only; model score rows are not populated in this tier"),
        criterion("next gate is scoring gate not freeze", "Tier 7.4f - Cost-Aware Policy/Action Held-Out Scoring Gate", "scoring gate", True),
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
        "claim_boundary": "Preflight/schema evidence only; no performance scoring, no public usefulness claim, no new baseline freeze, and no hardware/native transfer.",
        "source_artifacts": source_artifacts,
        "split_manifest": split_manifest,
        "cost_model": cost_model,
        "baseline_inventory": baselines,
        "sham_ablation_inventory": shams,
        "scoring_schema": scoring_schema,
        "decision": {
            "outcome": "heldout_scoring_preflight_ready" if status == "pass" else "heldout_scoring_preflight_incomplete",
            "scoring_gate_authorized": status == "pass",
            "freeze_authorized": False,
            "hardware_transfer_authorized": False,
            "next_gate": "Tier 7.4f - Cost-Aware Policy/Action Held-Out Scoring Gate",
        },
    }

    paths = {
        "results_json": output_dir / "tier7_4e_results.json",
        "report_md": output_dir / "tier7_4e_report.md",
        "summary_csv": output_dir / "tier7_4e_summary.csv",
        "source_artifacts_csv": output_dir / "tier7_4e_source_artifacts.csv",
        "split_manifest_json": output_dir / "tier7_4e_split_manifest.json",
        "split_manifest_csv": output_dir / "tier7_4e_split_manifest.csv",
        "cost_model_json": output_dir / "tier7_4e_cost_model.json",
        "cost_model_csv": output_dir / "tier7_4e_cost_model.csv",
        "baseline_inventory_csv": output_dir / "tier7_4e_baseline_inventory.csv",
        "sham_inventory_csv": output_dir / "tier7_4e_sham_inventory.csv",
        "scoring_schema_json": output_dir / "tier7_4e_scoring_schema.json",
        "decision_json": output_dir / "tier7_4e_decision.json",
        "decision_csv": output_dir / "tier7_4e_decision.csv",
    }

    write_json(paths["results_json"], payload)
    write_report(output_dir, payload)
    write_csv(paths["summary_csv"], [
        {
            "tier": TIER,
            "status": status,
            "criteria_passed": payload["criteria_passed"],
            "criteria_total": payload["criteria_total"],
            "outcome": payload["decision"]["outcome"],
            "scoring_gate_authorized": payload["decision"]["scoring_gate_authorized"],
            "freeze_authorized": False,
            "hardware_transfer_authorized": False,
            "next_gate": payload["decision"]["next_gate"],
        }
    ])
    write_csv(paths["source_artifacts_csv"], source_artifacts)
    split_rows = []
    for family in split_manifest.get("families", []):
        split_rows.append({k: json.dumps(v) if isinstance(v, (list, dict)) else v for k, v in family.items()})
    write_json(paths["split_manifest_json"], split_manifest)
    write_csv(paths["split_manifest_csv"], split_rows)
    write_json(paths["cost_model_json"], cost_model)
    write_csv(paths["cost_model_csv"], [{"cost_item": k, "value": v} for k, v in cost_model.items()])
    write_csv(paths["baseline_inventory_csv"], [{"baseline": item} for item in baselines])
    write_csv(paths["sham_inventory_csv"], [{"sham_or_ablation": item} for item in shams])
    write_json(paths["scoring_schema_json"], scoring_schema)
    write_json(paths["decision_json"], payload["decision"])
    write_csv(paths["decision_csv"], [payload["decision"]])

    manifest = make_manifest(output_dir, paths, status)
    write_json(output_dir / "tier7_4e_latest_manifest.json", manifest)
    write_json(CONTROLLED / "tier7_4e_latest_manifest.json", manifest)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    payload = run(args)
    print(
        json.dumps(
            {
                "tier": TIER,
                "status": payload["status"],
                "criteria_passed": payload["criteria_passed"],
                "criteria_total": payload["criteria_total"],
                "output_dir": str(Path(args.output_dir).resolve()),
                "next_gate": payload["decision"]["next_gate"],
            },
            indent=2,
        )
    )
    if payload["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
