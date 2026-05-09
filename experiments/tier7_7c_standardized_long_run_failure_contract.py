#!/usr/bin/env python3
"""Tier 7.7c - standardized long-run / failure-localization contract.

This is a contract-only gate after Tier 7.7b. It does not run the long-run
scoreboard. It locks the length sweep, diagnostics, controls, pass/fail classes,
and nonclaims needed to answer why v2.5 improved Mackey-Glass but did not improve
Lorenz/NARMA10 or beat strong external baselines.
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
BASELINES = ROOT / "baselines"

TIER = "Tier 7.7c - Standardized Long-Run / Failure-Localization Contract"
RUNNER_REVISION = "tier7_7c_standardized_long_run_failure_contract_20260509_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_7c_20260509_standardized_long_run_failure_contract"

PREREQ_77B = CONTROLLED / "tier7_7b_20260509_v2_5_standardized_scoreboard_scoring_gate" / "tier7_7b_results.json"
PREREQ_77A = CONTROLLED / "tier7_7a_20260509_v2_5_standardized_scoreboard_contract" / "tier7_7a_results.json"
V25_BASELINE = BASELINES / "CRA_EVIDENCE_BASELINE_v2.5.json"
NEXT_GATE = "Tier 7.7d - Standardized Long-Run / Failure-Localization Scoring Gate"


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


def sha256_file(path: Path) -> str:
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


def length_matrix_rows() -> list[dict[str, Any]]:
    return [
        {
            "length": 8000,
            "role": "anchor",
            "claim_use": "reproduce Tier 7.7b locked score inside the long-run scoring output",
            "required": True,
        },
        {
            "length": 16000,
            "role": "long_run_primary",
            "claim_use": "test whether v2.5 signal persists after twice the locked 7.7b exposure",
            "required": True,
        },
        {
            "length": 32000,
            "role": "long_run_primary",
            "claim_use": "test whether v2.5 signal grows, plateaus, or collapses over longer exposure",
            "required": True,
        },
        {
            "length": 50000,
            "role": "optional_runtime_diagnostic",
            "claim_use": "optional stress only if finite/runtime budget permits; cannot replace required lengths",
            "required": False,
        },
    ]


def diagnostic_question_rows() -> list[dict[str, Any]]:
    return [
        {
            "question_id": "mackey_signal_persistence",
            "question": "Does the Mackey-Glass improvement persist or grow as the stream length increases?",
            "primary_metrics": "per-seed test_mse, tail_mse, v2.3/v2.5 ratio by length",
            "failure_interpretation": "short-run delayed scalar recurrence benefit only",
        },
        {
            "question_id": "lorenz_state_reconstruction_gap",
            "question": "Is Lorenz flat because the current one-dimensional causal interface lacks enough state reconstruction?",
            "primary_metrics": "Lorenz v2.5-vs-v2.3 delta, ESN gap, state-disabled and prediction-disabled controls",
            "failure_interpretation": "requires richer state reconstruction or multichannel/state-space interface before mechanism layering",
        },
        {
            "question_id": "narma_memory_depth_gap",
            "question": "Is NARMA10 flat because the current memory/readout path lacks sufficient nonlinear memory depth?",
            "primary_metrics": "NARMA10 v2.5-vs-v2.3 delta, lag-depth diagnostics, memory/prediction-disabled controls",
            "failure_interpretation": "requires targeted memory-depth/readout repair rather than more high-level planning mechanics",
        },
        {
            "question_id": "external_baseline_gap",
            "question": "Do ESN/online-linear/ridge baselines win because of richer state, stronger readout, or simple linear fit advantages?",
            "primary_metrics": "rank, geomean_mse, train_mse/test_mse gap, tail_mse, parameter/disclosed feature budget",
            "failure_interpretation": "CRA remains below standard sequence baselines on this suite; broad usefulness claim stays blocked",
        },
        {
            "question_id": "sham_specificity",
            "question": "Do target/time/state/planning shams stay separated at longer lengths?",
            "primary_metrics": "target-shuffle margin, time-shuffle margin, planning-disabled margin, state-disabled margin",
            "failure_interpretation": "apparent long-run improvement is not causally specific enough for promotion",
        },
    ]


def model_rows() -> list[dict[str, Any]]:
    return [
        {"model": "cra_v2_5_scoreboard_candidate", "role": "candidate", "required": True},
        {"model": "cra_v2_3_generic_recurrent_reference", "role": "previous CRA reference", "required": True},
        {"model": "cra_v2_4_policy_reference_no_planning", "role": "policy/action previous reference", "required": True},
        {"model": "persistence", "role": "simple causal baseline", "required": True},
        {"model": "online_lms", "role": "online linear baseline", "required": True},
        {"model": "ridge_lag", "role": "train-prefix linear lag baseline", "required": True},
        {"model": "lag_only_online_lms_control", "role": "same causal lag budget control", "required": True},
        {"model": "fixed_random_reservoir_online_control", "role": "random reservoir control", "required": True},
        {"model": "fixed_esn_train_prefix_ridge_baseline", "role": "strong reservoir baseline", "required": True},
        {"model": "small_gru", "role": "optional reviewer-defense baseline if dependency/runtime budget is locked", "required": False},
    ]


def sham_rows() -> list[dict[str, Any]]:
    return [
        {"sham": "target_shuffle_control", "purpose": "break input-target relation"},
        {"sham": "time_shuffle_control", "purpose": "destroy temporal order"},
        {"sham": "planning_disabled_v2_3_equivalent", "purpose": "remove v2.5 planning/subgoal meta-state"},
        {"sham": "state_disabled", "purpose": "remove recurrent/fading state"},
        {"sham": "memory_disabled", "purpose": "remove slow-memory bridge columns"},
        {"sham": "prediction_disabled", "purpose": "remove predictive extrapolation columns"},
        {"sham": "self_evaluation_disabled", "purpose": "remove reliability/uncertainty columns"},
        {"sham": "composition_routing_disabled", "purpose": "remove route/composition interactions"},
        {"sham": "future_label_leak_guard", "purpose": "audit causal ordering and future-label absence"},
    ]


def pass_fail_rows() -> list[dict[str, Any]]:
    return [
        {
            "kind": "long_run_confirmed",
            "rule": "v2.5 improves v2.3 aggregate by >=10% at both 16000 and 32000 with paired support, while at least 2/3 tasks or tail metrics improve and shams stay separated",
            "claim_allowed": "long-run standardized progress versus v2.3; still not external-baseline superiority unless baselines are beaten",
        },
        {
            "kind": "mackey_only_localized",
            "rule": "Mackey-Glass remains improved but Lorenz/NARMA10 stay flat or worse",
            "claim_allowed": "localized delayed scalar recurrence signal only",
        },
        {
            "kind": "baseline_gap_persists",
            "rule": "v2.5 improves v2.3 but ESN/online-linear/ridge remain materially better on aggregate",
            "claim_allowed": "progress versus older CRA only; no broad usefulness or baseline-competitive claim",
        },
        {
            "kind": "signal_collapses",
            "rule": "7.7b aggregate improvement disappears at 16000 or 32000, or shams match the candidate",
            "claim_allowed": "no long-run usefulness upgrade; route to measured failure repair",
        },
        {
            "kind": "stop_or_narrow",
            "rule": "v2.5 fails to improve v2.3 at longer lengths and standard baselines dominate all required lengths",
            "claim_allowed": "narrow paper to architecture/evidence/hardware substrate unless a future predeclared mechanism changes the scoreboard",
        },
    ]


def expected_artifact_rows() -> list[dict[str, Any]]:
    return [
        {"artifact": "tier7_7d_results.json", "purpose": "long-run scoring result and classification"},
        {"artifact": "tier7_7d_summary.csv", "purpose": "criteria summary"},
        {"artifact": "tier7_7d_report.md", "purpose": "human-readable result"},
        {"artifact": "tier7_7d_length_scoreboard.csv", "purpose": "per-length/per-task/per-model metrics"},
        {"artifact": "tier7_7d_length_aggregate.csv", "purpose": "aggregate geomean/rank table by length"},
        {"artifact": "tier7_7d_failure_decomposition.csv", "purpose": "diagnostic answer table"},
        {"artifact": "tier7_7d_sham_controls.csv", "purpose": "long-run sham/ablation separation"},
        {"artifact": "tier7_7d_leakage_audit.json", "purpose": "finite-stream and causal-order audit"},
        {"artifact": "tier7_7d_claim_boundary.md", "purpose": "allowed claims and nonclaims"},
        {"artifact": "tier7_7d_latest_manifest.json", "purpose": "registry pointer if promoted canonical"},
    ]


def build_contract() -> dict[str, Any]:
    return {
        "question": "Does the Tier 7.7b v2.5 standardized progress signal persist under longer streams, and what explains the Lorenz/NARMA10 plus external-baseline gap?",
        "hypothesis": "If v2.5 captures useful general temporal structure, its aggregate advantage versus v2.3 should persist or grow at 16000 and 32000 steps without sham matching, and failure decomposition should show which mechanisms help which task family.",
        "null_hypothesis": "The 7.7b gain is a Mackey-Glass-local short-run effect; Lorenz/NARMA10 and strong standard baselines remain better, or shams explain the apparent gain.",
        "tasks": ["mackey_glass", "lorenz", "narma10"],
        "horizon": 8,
        "seeds": [42, 43, 44],
        "split": "chronological train 65%, test 35%, tail = final quartile of test suffix",
        "length_matrix": length_matrix_rows(),
        "diagnostic_questions": diagnostic_question_rows(),
        "models": model_rows(),
        "shams": sham_rows(),
        "metrics": [
            "test_mse",
            "test_nmse",
            "tail_mse",
            "test_corr",
            "all_three_geomean_mse",
            "paired_seed_delta",
            "bootstrap_or_paired_ci",
            "rank_vs_external_baselines",
            "train_mse_vs_test_mse_gap",
            "runtime_seconds",
        ],
        "pass_fail_criteria": pass_fail_rows(),
        "expected_artifacts": expected_artifact_rows(),
        "leakage_rules": [
            "same causal observed stream only; no future target or test-label access",
            "prediction emitted before online update",
            "normalization fit on train prefix only",
            "same seeds/tasks/splits for candidate and baselines",
            "optional 50000-step run cannot replace required 8000/16000/32000 lengths",
            "do not add or tune mechanisms inside the scoring gate",
        ],
        "nonclaims": [
            "not a new score by itself",
            "not a new baseline freeze",
            "not hardware/native evidence",
            "not a mechanism implementation",
            "not external-baseline superiority unless 7.7d shows it",
            "not language, broad reasoning, AGI, or ASI evidence",
        ],
        "next_gate": NEXT_GATE,
    }


def write_report(output_dir: Path, payload: dict[str, Any]) -> None:
    c = payload["contract"]
    lines = [
        "# Tier 7.7c Standardized Long-Run / Failure-Localization Contract",
        "",
        f"- Generated: `{payload['generated_at_utc']}`",
        f"- Status: **{payload['status'].upper()}**",
        f"- Criteria: `{payload['criteria_passed']}/{payload['criteria_total']}`",
        "",
        "## Question",
        "",
        c["question"],
        "",
        "## Locked Lengths",
        "",
        "| Length | Role | Required | Claim Use |",
        "| ---: | --- | --- | --- |",
    ]
    for row in c["length_matrix"]:
        lines.append(f"| {row['length']} | {row['role']} | {row['required']} | {row['claim_use']} |")
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
    (output_dir / "tier7_7c_report.md").write_text("\n".join(lines), encoding="utf-8")


def run(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    prereq_77b = read_json(PREREQ_77B)
    prereq_77a = read_json(PREREQ_77A)
    contract = build_contract()
    prerequisites = {
        "tier7_7b_results": str(PREREQ_77B),
        "tier7_7b_status": prereq_77b.get("status"),
        "tier7_7b_outcome": (prereq_77b.get("classification") or {}).get("outcome"),
        "tier7_7b_sha256": sha256_file(PREREQ_77B) if PREREQ_77B.exists() else None,
        "tier7_7a_results": str(PREREQ_77A),
        "tier7_7a_status": prereq_77a.get("status"),
        "tier7_7a_sha256": sha256_file(PREREQ_77A) if PREREQ_77A.exists() else None,
        "v2_5_baseline": str(V25_BASELINE),
        "v2_5_baseline_sha256": sha256_file(V25_BASELINE) if V25_BASELINE.exists() else None,
    }
    criteria = [
        criterion("Tier 7.7b prerequisite exists", str(PREREQ_77B), "exists", PREREQ_77B.exists()),
        criterion("Tier 7.7b prerequisite passed", prereq_77b.get("status"), "== pass", prereq_77b.get("status") == "pass"),
        criterion("Tier 7.7b outcome requires localization", (prereq_77b.get("classification") or {}).get("outcome"), "in standardized_progress/localized/baseline-gap outcomes", (prereq_77b.get("classification") or {}).get("outcome") in {"standardized_progress_pass", "localized_pass", "baseline_gap_persists"}),
        criterion("Tier 7.7a contract exists", str(PREREQ_77A), "exists and pass", PREREQ_77A.exists() and prereq_77a.get("status") == "pass"),
        criterion("v2.5 baseline exists", str(V25_BASELINE), "exists", V25_BASELINE.exists()),
        criterion("required lengths locked", [row["length"] for row in contract["length_matrix"] if row["required"]], "== [8000, 16000, 32000]", [row["length"] for row in contract["length_matrix"] if row["required"]] == [8000, 16000, 32000]),
        criterion("standard tasks locked", contract["tasks"], "== Mackey/Lorenz/NARMA", contract["tasks"] == ["mackey_glass", "lorenz", "narma10"]),
        criterion("same seeds locked", contract["seeds"], "== [42,43,44]", contract["seeds"] == [42, 43, 44]),
        criterion("diagnostic questions locked", len(contract["diagnostic_questions"]), ">= 5", len(contract["diagnostic_questions"]) >= 5),
        criterion("model matrix includes candidate/reference/baselines", [row["model"] for row in contract["models"]], "contains v2.5/v2.3/ESN/ridge/online", {"cra_v2_5_scoreboard_candidate", "cra_v2_3_generic_recurrent_reference", "fixed_esn_train_prefix_ridge_baseline", "ridge_lag", "online_lms"}.issubset({row["model"] for row in contract["models"]})),
        criterion("shams locked", len(contract["shams"]), ">= 8", len(contract["shams"]) >= 8),
        criterion("pass/fail classes locked", len(contract["pass_fail_criteria"]), ">= 5", len(contract["pass_fail_criteria"]) >= 5),
        criterion("expected artifacts locked", len(contract["expected_artifacts"]), ">= 8", len(contract["expected_artifacts"]) >= 8),
        criterion("contract does not score", False, "must remain false", True),
        criterion("hardware/native transfer blocked", "blocked", "blocked", True),
    ]
    passed = sum(1 for item in criteria if item["passed"])
    payload = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "status": "pass" if passed == len(criteria) else "fail",
        "criteria": criteria,
        "criteria_passed": passed,
        "criteria_total": len(criteria),
        "output_dir": str(output_dir),
        "prerequisites": prerequisites,
        "contract": contract,
        "classification": {
            "outcome": "standardized_long_run_failure_contract_locked",
            "scoring_authorized": True,
            "next_gate": NEXT_GATE,
            "baseline_freeze_authorized": False,
            "hardware_transfer_authorized": False,
            "public_usefulness_authorized": False,
        },
        "claim_boundary": "Tier 7.7c is a contract/pre-registration gate only. It performs no long-run scoring, freezes no baseline, claims no public usefulness, and authorizes no hardware/native transfer.",
    }
    write_json(output_dir / "tier7_7c_results.json", payload)
    write_json(output_dir / "tier7_7c_long_run_contract.json", contract)
    write_csv(output_dir / "tier7_7c_summary.csv", criteria)
    write_csv(output_dir / "tier7_7c_length_matrix.csv", contract["length_matrix"])
    write_csv(output_dir / "tier7_7c_diagnostic_questions.csv", contract["diagnostic_questions"])
    write_csv(output_dir / "tier7_7c_models.csv", contract["models"])
    write_csv(output_dir / "tier7_7c_shams.csv", contract["shams"])
    write_csv(output_dir / "tier7_7c_pass_fail_criteria.csv", contract["pass_fail_criteria"])
    write_csv(output_dir / "tier7_7c_expected_artifacts.csv", contract["expected_artifacts"])
    (output_dir / "tier7_7c_claim_boundary.md").write_text(payload["claim_boundary"] + "\n", encoding="utf-8")
    write_report(output_dir, payload)
    manifest = {
        "tier": TIER,
        "status": payload["status"],
        "generated_at_utc": payload["generated_at_utc"],
        "output_dir": str(output_dir),
        "results_json": str(output_dir / "tier7_7c_results.json"),
        "report_md": str(output_dir / "tier7_7c_report.md"),
        "summary_csv": str(output_dir / "tier7_7c_summary.csv"),
        "contract_json": str(output_dir / "tier7_7c_long_run_contract.json"),
    }
    write_json(output_dir / "tier7_7c_latest_manifest.json", manifest)
    write_json(CONTROLLED / "tier7_7c_latest_manifest.json", manifest)
    return payload


def main() -> int:
    payload = run()
    print(json.dumps(json_safe({"status": payload["status"], "classification": payload["classification"]}), indent=2, sort_keys=True))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
