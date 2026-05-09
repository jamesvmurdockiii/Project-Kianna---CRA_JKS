#!/usr/bin/env python3
"""Tier 7.7g - Lorenz state-capacity / NARMA memory-depth contract.

Tier 7.7f produced a valid repaired long-run scoreboard and classified the
result as Mackey-only localized. This contract predeclares the next diagnostic:
separate capacity/state-interface limitations from deeper architectural
limitations before adding more CRA mechanisms.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"

TIER = "Tier 7.7g - Lorenz State-Capacity / NARMA Memory-Depth Diagnostic Contract"
RUNNER_REVISION = "tier7_7g_lorenz_capacity_narma_memory_contract_20260509_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_7g_20260509_lorenz_capacity_narma_memory_contract"
PREREQ_77F = CONTROLLED / "tier7_7f_20260509_repaired_finite_stream_long_run_scoreboard" / "tier7_7f_results.json"
PREREQ_77E = CONTROLLED / "tier7_7e_20260509_finite_stream_repair_preflight" / "tier7_7e_results.json"
NEXT_GATE = "Tier 7.7h - Lorenz Capacity / NARMA Memory-Depth Scoring Gate"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = []
        for row in rows:
            for key in row:
                if key not in fieldnames:
                    fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json_safe(row.get(key, "")) for key in fieldnames})


def sha256_file(path: Path) -> str | None:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def criterion(name: str, value: Any, rule: str, passed: bool, details: str = "") -> dict[str, Any]:
    return {
        "name": name,
        "criterion": name,
        "value": json_safe(value),
        "operator": rule,
        "rule": rule,
        "passed": bool(passed),
        "pass": bool(passed),
        "note": details,
        "details": details,
    }


def capacity_matrix_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for units in [16, 32, 64, 128]:
        rows.append(
            {
                "variant": f"cra_v2_5_temporal_state_{units}",
                "family": "CRA temporal-state capacity sweep",
                "temporal_hidden_units": units,
                "meta_features": "locked v2.5 causal meta-state adapter",
                "readout_rule": "locked online readout from 7.7b/7.7f; no retune",
                "required": True,
            }
        )
        rows.append(
            {
                "variant": f"esn_train_prefix_ridge_{units}",
                "family": "matched-capacity ESN reference",
                "temporal_hidden_units": units,
                "meta_features": "none",
                "readout_rule": "train-prefix ridge baseline",
                "required": True,
            }
        )
        rows.append(
            {
                "variant": f"random_reservoir_online_{units}",
                "family": "matched-capacity random reservoir control",
                "temporal_hidden_units": units,
                "meta_features": "none",
                "readout_rule": "locked online readout/control",
                "required": True,
            }
        )
    rows.extend(
        [
            {
                "variant": "lag_ridge_reference",
                "family": "simple lag/readout baseline",
                "temporal_hidden_units": 0,
                "meta_features": "none",
                "readout_rule": "train-prefix ridge",
                "required": True,
            },
            {
                "variant": "online_lms_reference",
                "family": "simple online linear baseline",
                "temporal_hidden_units": 0,
                "meta_features": "none",
                "readout_rule": "online LMS",
                "required": True,
            },
        ]
    )
    return rows


def task_rows() -> list[dict[str, Any]]:
    return [
        {
            "task": "lorenz",
            "role": "primary state-geometry reconstruction diagnostic",
            "lengths": "8000,16000,32000",
            "primary_metric": "test_mse and ESN-gap closure by capacity",
            "why": "7.7f showed Lorenz is flat/weak while ESN dominates.",
        },
        {
            "task": "narma10",
            "role": "primary nonlinear memory-depth diagnostic",
            "lengths": "8000,16000,32000",
            "primary_metric": "test_mse, tail_mse, and memory-depth improvement by capacity",
            "why": "7.7f repaired finite streams but NARMA stayed near-flat.",
            "stream_policy": "repaired_narma10_reduced_input_u02 from 7.7e",
        },
        {
            "task": "mackey_glass",
            "role": "positive-control / no-regression anchor",
            "lengths": "8000,16000,32000",
            "primary_metric": "ensure Mackey signal does not collapse under capacity sweep",
            "why": "Mackey is the localized positive signal from 7.7b/7.7f.",
        },
    ]


def diagnostic_question_rows() -> list[dict[str, Any]]:
    return [
        {
            "question_id": "lorenz_capacity_closure",
            "question": "Does increasing CRA temporal-state capacity materially close the Lorenz gap toward matched-capacity ESN/reservoir references?",
            "evidence_required": "capacity curve over 16/32/64/128 units, paired seeds, tail MSE, and ESN-gap closure",
        },
        {
            "question_id": "narma_memory_depth_closure",
            "question": "Does increasing CRA temporal-state capacity improve repaired NARMA10 memory-depth performance beyond v2.5-16?",
            "evidence_required": "capacity curve, repaired-stream manifest, lag/depth controls, and tail stability",
        },
        {
            "question_id": "capacity_vs_architecture",
            "question": "If capacity increases do not help, does the result justify a structural mechanism rather than more units?",
            "evidence_required": "flat CRA curve despite matched-capacity sweep and separated shams",
        },
        {
            "question_id": "external_capacity_fairness",
            "question": "Do ESN/reservoir baselines remain stronger at comparable state counts, or is the comparison unfairly capacity-skewed?",
            "evidence_required": "matched-capacity baseline table with disclosed units and feature counts",
        },
        {
            "question_id": "mackey_anchor_regression",
            "question": "Does any higher-capacity variant preserve the Mackey signal, or does capacity damage the only confirmed standardized gain?",
            "evidence_required": "Mackey ratios and shams across capacity levels",
        },
    ]


def sham_rows() -> list[dict[str, Any]]:
    return [
        {"sham": "state_reset_by_capacity", "purpose": "reset temporal state periodically to verify state persistence matters"},
        {"sham": "permuted_recurrence_by_capacity", "purpose": "preserve input projection but scramble recurrent wiring"},
        {"sham": "target_shuffle_by_capacity", "purpose": "break input-target relation"},
        {"sham": "time_shuffle_by_capacity", "purpose": "destroy temporal order"},
        {"sham": "prediction_disabled_meta", "purpose": "remove predictive v2.5 meta columns"},
        {"sham": "memory_disabled_meta", "purpose": "remove slow-memory bridge columns"},
        {"sham": "same_feature_budget_audit", "purpose": "record feature counts so capacity claims are not hidden parameter-budget claims"},
    ]


def pass_fail_rows() -> list[dict[str, Any]]:
    return [
        {
            "kind": "capacity_limited_closing",
            "rule": "Higher-capacity CRA improves Lorenz or repaired NARMA by >=25% versus 16-unit v2.5 and closes >=30% of the gap to matched-capacity ESN/reservoir with shams separated.",
            "claim_allowed": "capacity/state-interface limitation is supported; next step may tune capacity or design larger state interface before adding mechanisms",
        },
        {
            "kind": "capacity_helps_but_baseline_gap_persists",
            "rule": "Higher-capacity CRA improves materially versus 16-unit v2.5 but ESN/reservoir remains substantially better.",
            "claim_allowed": "capacity matters, but broad usefulness remains blocked; design targeted state-interface repair or mechanism only after this evidence",
        },
        {
            "kind": "architecture_limited_flat",
            "rule": "CRA remains flat across 16/32/64/128 while matched-capacity ESN/reservoir remains much stronger.",
            "claim_allowed": "more capacity alone is unlikely to solve Lorenz/NARMA; move to a predeclared structural mechanism gate",
        },
        {
            "kind": "overfit_or_sham_blocked",
            "rule": "Train metrics improve while test/tail fails, or shams match candidate performance.",
            "claim_allowed": "no capacity or mechanism promotion; repair leakage/overfit/task design first",
        },
        {
            "kind": "mackey_regression",
            "rule": "Capacity variants damage the confirmed Mackey signal without improving Lorenz/NARMA.",
            "claim_allowed": "do not promote larger capacity; preserve v2.5 localized claim only",
        },
    ]


def expected_artifact_rows() -> list[dict[str, Any]]:
    return [
        {"artifact": "tier7_7h_results.json", "purpose": "capacity diagnostic scoring result and classification"},
        {"artifact": "tier7_7h_report.md", "purpose": "human-readable result"},
        {"artifact": "tier7_7h_summary.csv", "purpose": "criteria summary"},
        {"artifact": "tier7_7h_capacity_scoreboard.csv", "purpose": "per-task/per-capacity/per-model metrics"},
        {"artifact": "tier7_7h_capacity_curves.csv", "purpose": "capacity scaling curves and gap closure"},
        {"artifact": "tier7_7h_matched_capacity_baselines.csv", "purpose": "matched ESN/reservoir/reference table"},
        {"artifact": "tier7_7h_sham_controls.csv", "purpose": "capacity-specific shams/ablations"},
        {"artifact": "tier7_7h_repaired_stream_manifest.json", "purpose": "NARMA repaired-stream proof"},
        {"artifact": "tier7_7h_claim_boundary.md", "purpose": "allowed claims and nonclaims"},
    ]


def build_contract() -> dict[str, Any]:
    return {
        "question": "Are the remaining Lorenz and repaired-NARMA gaps capacity/state-interface limited, or do they remain flat under matched-capacity sweeps?",
        "hypothesis": "If the 7.7f failure is mainly capacity/state-interface limited, increasing CRA temporal-state capacity toward ESN parity should materially improve Lorenz and/or repaired NARMA while preserving the Mackey anchor and separating shams.",
        "null_hypothesis": "Increasing CRA temporal-state capacity does not materially improve Lorenz or repaired NARMA, or apparent gains are explained by shams/overfit rather than usable state geometry or memory depth.",
        "mechanism_under_test": "capacity/state-interface diagnostic only; no new CRA mechanism, no baseline freeze, no hardware/native transfer",
        "tasks": task_rows(),
        "seeds": [42, 43, 44],
        "lengths": [8000, 16000, 32000],
        "capacity_matrix": capacity_matrix_rows(),
        "diagnostic_questions": diagnostic_question_rows(),
        "shams": sham_rows(),
        "metrics": [
            "test_mse",
            "test_nmse",
            "tail_mse",
            "test_corr",
            "capacity_curve_slope",
            "best_capacity_vs_v2_5_16_ratio",
            "gap_closure_to_matched_esn",
            "feature_count",
            "train_test_gap",
            "paired_seed_delta",
        ],
        "pass_fail_criteria": pass_fail_rows(),
        "expected_artifacts": expected_artifact_rows(),
        "leakage_rules": [
            "use repaired NARMA U(0,0.2) stream from Tier 7.7e only",
            "same seeds/tasks/splits across candidate, shams, and baselines",
            "disclose feature counts and hidden units for every capacity variant",
            "do not tune readout learning rates inside this gate",
            "do not add mechanisms inside this gate",
            "prediction emitted before online update for online models",
            "normalization fit on train prefix only",
        ],
        "nonclaims": [
            "not a new baseline freeze",
            "not a mechanism promotion",
            "not broad public usefulness",
            "not hardware/native transfer",
            "not evidence of external-baseline superiority unless the scoring gate shows it",
            "not language, broad reasoning, AGI, or ASI evidence",
        ],
        "next_gate": NEXT_GATE,
    }


def write_report(output_dir: Path, payload: dict[str, Any]) -> None:
    c = payload["contract"]
    lines = [
        "# Tier 7.7g Lorenz State-Capacity / NARMA Memory-Depth Contract",
        "",
        f"- Generated: `{payload['generated_at_utc']}`",
        f"- Status: **{payload['status'].upper()}**",
        f"- Criteria: `{payload['criteria_passed']}/{payload['criteria_total']}`",
        f"- Outcome: `{payload['classification']['outcome']}`",
        "",
        "## Question",
        "",
        c["question"],
        "",
        "## Capacity Matrix",
        "",
        "| Variant | Family | Units | Required |",
        "| --- | --- | ---: | --- |",
    ]
    for row in c["capacity_matrix"]:
        lines.append(f"| `{row['variant']}` | {row['family']} | {row['temporal_hidden_units']} | {row['required']} |")
    lines.extend(["", "## Diagnostic Questions", ""])
    for row in c["diagnostic_questions"]:
        lines.append(f"- `{row['question_id']}`: {row['question']}")
    lines.extend(["", "## Pass/Fail Classes", ""])
    for row in c["pass_fail_criteria"]:
        lines.append(f"- `{row['kind']}`: {row['rule']}")
    lines.extend(["", "## Nonclaims", ""])
    for item in c["nonclaims"]:
        lines.append(f"- {item}")
    lines.append("")
    (output_dir / "tier7_7g_report.md").write_text("\n".join(lines), encoding="utf-8")


def run(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    prereq_77f = read_json(PREREQ_77F)
    prereq_77e = read_json(PREREQ_77E)
    contract = build_contract()
    capacity_units = sorted({int(row["temporal_hidden_units"]) for row in contract["capacity_matrix"] if int(row["temporal_hidden_units"]) > 0})
    criteria = [
        criterion("Tier 7.7f prerequisite exists", str(PREREQ_77F), "exists and pass", PREREQ_77F.exists() and prereq_77f.get("status") == "pass"),
        criterion("Tier 7.7f outcome requires capacity diagnostic", (prereq_77f.get("classification") or {}).get("outcome"), "== mackey_only_localized", (prereq_77f.get("classification") or {}).get("outcome") == "mackey_only_localized"),
        criterion("Tier 7.7e repaired stream prerequisite exists", str(PREREQ_77E), "exists and pass", PREREQ_77E.exists() and prereq_77e.get("status") == "pass"),
        criterion("repaired NARMA stream locked", (prereq_77e.get("classification") or {}).get("selected_generator"), "== narma10_reduced_input_u02", (prereq_77e.get("classification") or {}).get("selected_generator") == "narma10_reduced_input_u02"),
        criterion("capacity sweep includes 16/32/64/128", capacity_units, "== [16,32,64,128]", capacity_units == [16, 32, 64, 128]),
        criterion("tasks include Lorenz/NARMA/Mackey", [row["task"] for row in contract["tasks"]], "contains lorenz,narma10,mackey", {row["task"] for row in contract["tasks"]} == {"lorenz", "narma10", "mackey_glass"}),
        criterion("lengths locked", contract["lengths"], "== [8000,16000,32000]", contract["lengths"] == [8000, 16000, 32000]),
        criterion("seeds locked", contract["seeds"], "== [42,43,44]", contract["seeds"] == [42, 43, 44]),
        criterion("matched-capacity baselines included", [row["variant"] for row in contract["capacity_matrix"]], "contains ESN and reservoir at every capacity", all(any(row["variant"] == f"esn_train_prefix_ridge_{units}" for row in contract["capacity_matrix"]) and any(row["variant"] == f"random_reservoir_online_{units}" for row in contract["capacity_matrix"]) for units in [16, 32, 64, 128])),
        criterion("shams locked", len(contract["shams"]), ">= 6", len(contract["shams"]) >= 6),
        criterion("pass/fail classes locked", len(contract["pass_fail_criteria"]), ">= 5", len(contract["pass_fail_criteria"]) >= 5),
        criterion("expected artifacts locked", len(contract["expected_artifacts"]), ">= 8", len(contract["expected_artifacts"]) >= 8),
        criterion("contract does not score", False, "must remain false", True),
        criterion("no mechanism promotion", False, "must remain false", True),
        criterion("hardware/native transfer blocked", False, "must remain false", True),
    ]
    passed = sum(1 for item in criteria if item["passed"])
    status = "pass" if passed == len(criteria) else "fail"
    payload = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "status": status,
        "criteria": criteria,
        "criteria_passed": passed,
        "criteria_total": len(criteria),
        "output_dir": str(output_dir),
        "prerequisites": {
            "tier7_7f_results": str(PREREQ_77F),
            "tier7_7f_status": prereq_77f.get("status"),
            "tier7_7f_outcome": (prereq_77f.get("classification") or {}).get("outcome"),
            "tier7_7f_sha256": sha256_file(PREREQ_77F),
            "tier7_7e_results": str(PREREQ_77E),
            "tier7_7e_status": prereq_77e.get("status"),
            "tier7_7e_selected_generator": (prereq_77e.get("classification") or {}).get("selected_generator"),
            "tier7_7e_sha256": sha256_file(PREREQ_77E),
        },
        "contract": contract,
        "classification": {
            "outcome": "lorenz_capacity_narma_memory_contract_locked",
            "scoring_authorized": status == "pass",
            "next_gate": NEXT_GATE,
            "baseline_freeze_authorized": False,
            "hardware_transfer_authorized": False,
            "mechanism_promotion_authorized": False,
        },
        "claim_boundary": "Tier 7.7g is a contract/pre-registration gate only. It performs no scoring, promotes no mechanism, freezes no baseline, claims no public usefulness, and authorizes no hardware/native transfer.",
    }
    write_json(output_dir / "tier7_7g_results.json", payload)
    write_json(output_dir / "tier7_7g_capacity_contract.json", contract)
    write_csv(output_dir / "tier7_7g_summary.csv", criteria)
    write_csv(output_dir / "tier7_7g_task_matrix.csv", contract["tasks"])
    write_csv(output_dir / "tier7_7g_capacity_matrix.csv", contract["capacity_matrix"])
    write_csv(output_dir / "tier7_7g_diagnostic_questions.csv", contract["diagnostic_questions"])
    write_csv(output_dir / "tier7_7g_shams.csv", contract["shams"])
    write_csv(output_dir / "tier7_7g_pass_fail_criteria.csv", contract["pass_fail_criteria"])
    write_csv(output_dir / "tier7_7g_expected_artifacts.csv", contract["expected_artifacts"])
    (output_dir / "tier7_7g_claim_boundary.md").write_text(payload["claim_boundary"] + "\n", encoding="utf-8")
    write_report(output_dir, payload)
    manifest = {
        "tier": TIER,
        "status": status,
        "generated_at_utc": payload["generated_at_utc"],
        "output_dir": str(output_dir),
        "results_json": str(output_dir / "tier7_7g_results.json"),
        "report_md": str(output_dir / "tier7_7g_report.md"),
        "summary_csv": str(output_dir / "tier7_7g_summary.csv"),
        "classification_outcome": payload["classification"]["outcome"],
    }
    write_json(output_dir / "tier7_7g_latest_manifest.json", manifest)
    write_json(CONTROLLED / "tier7_7g_latest_manifest.json", manifest)
    return payload


def main() -> int:
    payload = run()
    print(json.dumps(json_safe({"status": payload["status"], "classification": payload["classification"]}), indent=2, sort_keys=True))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
