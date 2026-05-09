#!/usr/bin/env python3
"""Tier 7.7k - effective-state-dimensionality repair contract.

Tier 7.7j classified the Lorenz capacity failure as low-rank collapse: larger
nominal recurrent capacity increased state amplitude but did not create enough
independent state dimensions. This contract pre-registers the next repair before
any implementation, tuning, or mechanism promotion.
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

TIER = "Tier 7.7k - Effective-State-Dimensionality Repair Contract"
RUNNER_REVISION = "tier7_7k_effective_state_dimensionality_repair_contract_20260509_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_7k_20260509_effective_state_dimensionality_repair_contract"
PREREQ_77J = CONTROLLED / "tier7_7j_20260509_capacity_sham_separation_scoring_gate" / "tier7_7j_results.json"
NEXT_GATE = "Tier 7.7l - Effective-State-Dimensionality Repair Scoring Gate"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
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
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def criterion(name: str, value: Any, rule: str, passed: bool, details: str = "") -> dict[str, Any]:
    return {
        "name": name,
        "criterion": name,
        "value": json_safe(value),
        "operator": rule,
        "rule": rule,
        "passed": bool(passed),
        "pass": bool(passed),
        "details": details,
        "note": details,
    }


def mechanism_rows() -> list[dict[str, Any]]:
    return [
        {
            "mechanism": "partitioned_driver_diverse_recurrent_state",
            "role": "primary repair candidate",
            "description": "Split causal input/state drivers and recurrent state into fixed partitions with distinct timescale bands plus deterministic diversity pressure so hidden units occupy more than the two dominant principal directions seen in Tier 7.7j.",
            "allowed_inputs": "observed stream and causal internal state only",
            "forbidden_inputs": "future targets, labels, test labels, task-specific post-hoc tuning",
            "promotable": True,
        },
        {
            "mechanism": "diversity_pressure_disabled",
            "role": "mechanism ablation",
            "description": "Same partitioned budget with diversity pressure disabled.",
            "promotable": False,
        },
        {
            "mechanism": "single_pool_same_capacity",
            "role": "baseline reference",
            "description": "Locked Tier 7.7h/7.7j full-recurrence candidate at matched capacity.",
            "promotable": False,
        },
        {
            "mechanism": "permuted_recurrence_ensemble",
            "role": "generic-basis sham",
            "description": "Multiple deterministic recurrence permutations at the same capacity and readout budget.",
            "promotable": False,
        },
        {
            "mechanism": "orthogonal_random_basis_reference",
            "role": "generic high-dimensional reference",
            "description": "Random orthogonal recurrent basis with no CRA-specific state-diversity mechanism.",
            "promotable": False,
        },
        {
            "mechanism": "block_structured_basis_reference",
            "role": "partition-structure sham",
            "description": "Block structure without CRA state-diversity pressure, used to separate partitioning from the repair itself.",
            "promotable": False,
        },
    ]


def failure_hypothesis_rows() -> list[dict[str, Any]]:
    return [
        {
            "hypothesis": "shared_driver_synchronization",
            "status": "primary_suspect",
            "rationale": "Candidate, permuted, orthogonal, and block probes all stayed near PR 2, suggesting nominally separate units are being driven into the same few causal directions.",
            "repair_implication": "Partition causal drivers and add state-diversity pressure before increasing capacity further.",
        },
        {
            "hypothesis": "input_state_bottleneck",
            "status": "primary_suspect",
            "rationale": "Lorenz receives a compact observed stream; larger hidden state may amplify the same low-dimensional input instead of building independent latent coordinates.",
            "repair_implication": "Use causal multi-timescale/novelty/channelized drivers, but no future labels or test leakage.",
        },
        {
            "hypothesis": "inhibitory_or_normalization_compression",
            "status": "alternate_suspect",
            "rationale": "If state normalization or inhibition forces global co-movement, partitions may still collapse unless diversity pressure is explicit.",
            "repair_implication": "Include diversity-disabled and block-only ablations to separate partitioning from anti-synchronization.",
        },
        {
            "hypothesis": "readout_concentration",
            "status": "weakened_by_7_7j",
            "rationale": "Tier 7.7j readout PR was not collapsed and top-weight concentration was not extreme at 128 units.",
            "repair_implication": "Keep readout metrics as guards, but do not make readout the first repair target.",
        },
        {
            "hypothesis": "leakage_or_metric_artifact",
            "status": "weakened_by_7_7j",
            "rationale": "Target and time shuffles separated strongly in Tier 7.7j.",
            "repair_implication": "Preserve shuffle guards for the repair gate.",
        },
        {
            "hypothesis": "single_channel_observability_only",
            "status": "not_primary_from_7_7j",
            "rationale": "The delay-embedding reference did not explain the Lorenz result in Tier 7.7j.",
            "repair_implication": "Track observability, but do not use it to excuse a non-separated repair.",
        },
    ]


def task_rows() -> list[dict[str, Any]]:
    return [
        {
            "task": "lorenz",
            "role": "primary repair target",
            "why": "Tier 7.7j found low effective dimensionality under Lorenz pressure despite larger nominal recurrent capacity.",
            "lengths": "8000,16000,32000",
            "seeds": "42,43,44",
            "required": True,
        },
        {
            "task": "mackey_glass",
            "role": "positive-control regression guard",
            "why": "CRA v2.5 already has a localized Mackey signal; repair must not break it.",
            "lengths": "8000,16000,32000",
            "seeds": "42,43,44",
            "required": True,
        },
        {
            "task": "narma10_repaired_u02",
            "role": "nonlinear-memory regression guard",
            "why": "Repaired finite NARMA stream remains the locked memory benchmark stream after Tier 7.7e/f.",
            "lengths": "8000,16000,32000",
            "seeds": "42,43,44",
            "required": True,
        },
    ]


def metric_rows() -> list[dict[str, Any]]:
    return [
        {"metric": "geomean_mse", "role": "primary task score", "required": True},
        {"metric": "tail_mse", "role": "tail stability", "required": True},
        {"metric": "test_corr", "role": "prediction shape", "required": True},
        {"metric": "participation_ratio", "role": "effective state dimensionality", "required": True},
        {"metric": "rank95_variance_count", "role": "variance dimensionality", "required": True},
        {"metric": "top_pc_fraction", "role": "collapse detector", "required": True},
        {"metric": "state_norm_mean_std", "role": "amplitude guard", "required": True},
        {"metric": "step_delta_mean_std", "role": "dynamic-state guard", "required": True},
        {"metric": "state_kernel_alignment", "role": "candidate/sham geometry similarity", "required": True},
        {"metric": "readout_weight_pr", "role": "readout concentration guard", "required": True},
        {"metric": "target_shuffle_guard", "role": "leakage guard", "required": True},
        {"metric": "time_shuffle_guard", "role": "temporal guard", "required": True},
        {"metric": "compact_regression_status", "role": "promotion guard if repair passes", "required": True},
    ]


def control_rows() -> list[dict[str, Any]]:
    return [
        {
            "control": "target_shuffle",
            "purpose": "Prove performance does not survive wrong causal targets.",
            "pass_requirement": "Target-shuffle MSE at least 5x worse than candidate on Lorenz or the gate is invalid.",
        },
        {
            "control": "time_shuffle",
            "purpose": "Prove temporal order matters.",
            "pass_requirement": "Time-shuffle MSE at least 5x worse than candidate on Lorenz or the gate is invalid.",
        },
        {
            "control": "diversity_disabled",
            "purpose": "Attribute gains to the repair, not only partition count.",
            "pass_requirement": "Candidate must beat disabled-diversity ablation on Lorenz while preserving guards.",
        },
        {
            "control": "permuted_recurrence_ensemble",
            "purpose": "Prevent generic random/permuted basis effects from being called CRA-specific.",
            "pass_requirement": "Candidate must beat best permuted ensemble by at least 5% MSE on Lorenz.",
        },
        {
            "control": "block_structured_basis_reference",
            "purpose": "Separate partition structure from state-diversity pressure.",
            "pass_requirement": "Candidate must beat block reference or disclose generic partition explanation.",
        },
        {
            "control": "readout_budget_match",
            "purpose": "Prevent wins from widened readout or unfair feature count.",
            "pass_requirement": "Feature/readout budget must match the locked capacity matrix within declared bounds.",
        },
    ]


def pass_fail_rows() -> list[dict[str, Any]]:
    return [
        {
            "outcome": "effective_dimension_repair_confirmed",
            "rule": "Candidate Lorenz PR at 128 >= 6 or >= 2x Tier 7.7j candidate PR, Lorenz MSE improves at least 10% versus 7.7j candidate, candidate beats best generic/permuted/block sham by at least 5%, Mackey and NARMA regressions stay within 10%, target/time shuffles fail, and compact regression passes.",
            "allowed_claim": "The state-dimensionality repair increases effective recurrent state geometry and improves the locked Lorenz diagnostic under controlled software conditions.",
        },
        {
            "outcome": "dimension_rises_but_no_task_gain",
            "rule": "PR/rank rises but Lorenz MSE does not improve or does not beat shams.",
            "allowed_claim": "The repair changes state geometry but has not yet produced useful benchmark improvement.",
        },
        {
            "outcome": "generic_basis_still_explains",
            "rule": "Generic/permuted/orthogonal/block probes match or beat candidate.",
            "allowed_claim": "Capacity/state gains remain non-specific; do not promote mechanism.",
        },
        {
            "outcome": "task_gain_without_dimension",
            "rule": "Lorenz improves but PR/rank does not materially rise.",
            "allowed_claim": "Treat as a performance diagnostic requiring attribution repair before promotion.",
        },
        {
            "outcome": "regression_or_leakage_blocked",
            "rule": "Mackey/NARMA regress materially, shuffles do not fail, or compact regression fails.",
            "allowed_claim": "No mechanism promotion; repair is blocked.",
        },
        {
            "outcome": "inconclusive",
            "rule": "Metrics conflict or confidence is insufficient.",
            "allowed_claim": "No claim beyond inconclusive diagnostic.",
        },
    ]


def expected_artifacts() -> list[dict[str, Any]]:
    names = [
        "tier7_7l_results.json",
        "tier7_7l_summary.csv",
        "tier7_7l_scoreboard.csv",
        "tier7_7l_score_summary.csv",
        "tier7_7l_state_geometry.csv",
        "tier7_7l_state_geometry_summary.csv",
        "tier7_7l_sham_controls.csv",
        "tier7_7l_regression_summary.json",
        "tier7_7l_claim_boundary.md",
        "tier7_7l_report.md",
    ]
    return [{"artifact": name, "required_for_scoring_gate": True} for name in names]


def build_contract(prereq: dict[str, Any]) -> dict[str, Any]:
    return {
        "question": "Can a predeclared state-diversity repair increase effective recurrent state dimensionality and improve Lorenz without relying on generic high-dimensional bases, leakage, or readout concentration?",
        "hypothesis": "Partitioned causal drivers plus diverse recurrent state should reduce shared-driver synchronization, raise effective participation ratio/rank under Lorenz pressure, and improve Lorenz MSE while preserving Mackey and repaired NARMA guards.",
        "null_hypothesis": "Any improvement is explained by nominal capacity, generic basis luck, readout budget, leakage, or task-specific post-hoc tuning; or state dimensionality does not increase.",
        "mechanism_under_test": "partitioned_driver_diverse_recurrent_state",
        "primary_reference": "Tier 7.7j candidate_full_recurrence at capacity 128",
        "prior_diagnostic": {
            "tier": "7.7j",
            "status": prereq.get("status"),
            "outcome": ((prereq.get("classification") or {}).get("outcome")),
            "candidate_pr_128": ((prereq.get("classification") or {}).get("diagnostics") or {}).get("candidate_pr_128"),
            "max_probe_pr_128": ((prereq.get("classification") or {}).get("diagnostics") or {}).get("max_probe_pr_128"),
        },
        "decision_boundary": "This contract authorizes only a scored diagnostic implementation in Tier 7.7l. It does not authorize a repair claim, software baseline freeze, public usefulness claim, hardware/native transfer, language, AGI, or ASI claim.",
    }


def run(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    prereq = read_json(PREREQ_77J)
    contract = build_contract(prereq)
    mechanisms = mechanism_rows()
    failure_hypotheses = failure_hypothesis_rows()
    tasks = task_rows()
    metrics = metric_rows()
    controls = control_rows()
    outcomes = pass_fail_rows()
    artifacts = expected_artifacts()
    claim_boundary = (
        "Tier 7.7k is a pre-registration contract for an effective-state-dimensionality repair after Tier 7.7j classified the standardized Lorenz failure as low-rank collapse. It does not implement the repair, score CRA, freeze a baseline, promote a mechanism, claim public usefulness, or transfer anything to hardware/native runtime."
    )
    criteria = [
        criterion("Tier 7.7j prerequisite exists", str(PREREQ_77J), "exists", PREREQ_77J.exists()),
        criterion("Tier 7.7j prerequisite passed", prereq.get("status"), "== pass", prereq.get("status") == "pass"),
        criterion("Tier 7.7j low-rank outcome", contract["prior_diagnostic"]["outcome"], "== low_rank_collapse_confirmed", contract["prior_diagnostic"]["outcome"] == "low_rank_collapse_confirmed"),
        criterion("question locked", contract["question"], "non-empty", bool(contract["question"])),
        criterion("hypothesis locked", contract["hypothesis"], "non-empty", bool(contract["hypothesis"])),
        criterion("null hypothesis locked", contract["null_hypothesis"], "non-empty", bool(contract["null_hypothesis"])),
        criterion("primary mechanism named", contract["mechanism_under_test"], "== partitioned_driver_diverse_recurrent_state", contract["mechanism_under_test"] == "partitioned_driver_diverse_recurrent_state"),
        criterion("failure hypotheses locked", [row["hypothesis"] for row in failure_hypotheses], "includes shared driver and input bottleneck", {"shared_driver_synchronization", "input_state_bottleneck"}.issubset({row["hypothesis"] for row in failure_hypotheses})),
        criterion("tasks locked", [row["task"] for row in tasks], "Lorenz/Mackey/repaired NARMA", {row["task"] for row in tasks} == {"lorenz", "mackey_glass", "narma10_repaired_u02"}),
        criterion("mechanism ablations present", [row["mechanism"] for row in mechanisms], "includes diversity disabled", any(row["mechanism"] == "diversity_pressure_disabled" for row in mechanisms)),
        criterion("generic shams present", [row["mechanism"] for row in mechanisms], "permuted/orthogonal/block references", {"permuted_recurrence_ensemble", "orthogonal_random_basis_reference", "block_structured_basis_reference"}.issubset({row["mechanism"] for row in mechanisms})),
        criterion("metrics include PR", [row["metric"] for row in metrics], "includes participation_ratio", any(row["metric"] == "participation_ratio" for row in metrics)),
        criterion("metrics include rank95", [row["metric"] for row in metrics], "includes rank95", any(row["metric"] == "rank95_variance_count" for row in metrics)),
        criterion("leakage controls locked", [row["control"] for row in controls], "target/time shuffles", {"target_shuffle", "time_shuffle"}.issubset({row["control"] for row in controls})),
        criterion("decision classes locked", [row["outcome"] for row in outcomes], ">= 5 classes", len(outcomes) >= 5),
        criterion("expected artifacts locked", [row["artifact"] for row in artifacts], ">= 8 artifacts", len(artifacts) >= 8),
        criterion("no baseline freeze authorized", False, "false", True),
        criterion("no hardware/native transfer authorized", False, "false", True),
    ]
    passed = sum(1 for row in criteria if row["passed"])
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
        "contract": contract,
        "mechanisms": mechanisms,
        "failure_hypotheses": failure_hypotheses,
        "tasks": tasks,
        "metrics": metrics,
        "controls": controls,
        "outcome_classes": outcomes,
        "expected_artifacts": artifacts,
        "claim_boundary": claim_boundary,
        "nonclaims": [
            "not a repair implementation",
            "not a mechanism promotion",
            "not a baseline freeze",
            "not a public usefulness claim",
            "not external-baseline superiority",
            "not hardware/native transfer",
            "not language, AGI, or ASI evidence",
        ],
        "prerequisite": {
            "path": str(PREREQ_77J),
            "sha256": sha256_file(PREREQ_77J),
            "status": prereq.get("status"),
        },
        "next_gate": NEXT_GATE,
    }
    write_json(output_dir / "tier7_7k_results.json", payload)
    write_json(output_dir / "tier7_7k_contract.json", contract)
    write_csv(output_dir / "tier7_7k_summary.csv", criteria)
    write_csv(output_dir / "tier7_7k_mechanisms.csv", mechanisms)
    write_csv(output_dir / "tier7_7k_failure_hypotheses.csv", failure_hypotheses)
    write_csv(output_dir / "tier7_7k_tasks.csv", tasks)
    write_csv(output_dir / "tier7_7k_metrics.csv", metrics)
    write_csv(output_dir / "tier7_7k_controls.csv", controls)
    write_csv(output_dir / "tier7_7k_outcome_classes.csv", outcomes)
    write_csv(output_dir / "tier7_7k_expected_artifacts.csv", artifacts)
    (output_dir / "tier7_7k_claim_boundary.md").write_text(claim_boundary + "\n", encoding="utf-8")
    report = [
        "# Tier 7.7k Effective-State-Dimensionality Repair Contract",
        "",
        f"- Generated: `{payload['generated_at_utc']}`",
        f"- Status: **{status.upper()}**",
        f"- Criteria: `{passed}/{len(criteria)}`",
        f"- Next gate: `{NEXT_GATE}`",
        "",
        "## Question",
        "",
        contract["question"],
        "",
        "## Boundary",
        "",
        claim_boundary,
        "",
        "## Nonclaims",
        "",
    ]
    report.extend(f"- {item}" for item in payload["nonclaims"])
    report.append("")
    (output_dir / "tier7_7k_report.md").write_text("\n".join(report), encoding="utf-8")
    manifest = {
        "tier": TIER,
        "status": status,
        "generated_at_utc": payload["generated_at_utc"],
        "output_dir": str(output_dir),
        "results_json": str(output_dir / "tier7_7k_results.json"),
        "report_md": str(output_dir / "tier7_7k_report.md"),
        "summary_csv": str(output_dir / "tier7_7k_summary.csv"),
    }
    write_json(output_dir / "tier7_7k_latest_manifest.json", manifest)
    write_json(CONTROLLED / "tier7_7k_latest_manifest.json", manifest)
    return payload


def main() -> int:
    payload = run()
    print(json.dumps(json_safe({"status": payload["status"], "criteria": f"{payload['criteria_passed']}/{payload['criteria_total']}", "output_dir": payload["output_dir"], "next_gate": payload["next_gate"]}), indent=2, sort_keys=True))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
