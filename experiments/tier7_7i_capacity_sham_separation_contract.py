#!/usr/bin/env python3
"""Tier 7.7i - capacity sham-separation / state-specificity contract.

Tier 7.7h showed a useful but blocked pattern: capacity materially improved
Mackey-Glass and Lorenz, yet Lorenz failed attribution because a
best-capacity permuted-recurrence sham beat the candidate. This contract
pre-registers the next diagnostic before any repair, tuning, or mechanism
layering.
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

TIER = "Tier 7.7i - Capacity Sham-Separation / State-Specificity Contract"
RUNNER_REVISION = "tier7_7i_capacity_sham_separation_contract_20260509_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_7i_20260509_capacity_sham_separation_contract"
PREREQ_77H = CONTROLLED / "tier7_7h_20260509_lorenz_capacity_narma_memory_scoring_gate" / "tier7_7h_results.json"
PREREQ_77G = CONTROLLED / "tier7_7g_20260509_lorenz_capacity_narma_memory_contract" / "tier7_7g_results.json"
NEXT_GATE = "Tier 7.7j - Capacity Sham-Separation / State-Specificity Scoring Gate"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
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
        "details": details,
        "note": details,
    }


def task_rows() -> list[dict[str, Any]]:
    return [
        {
            "task": "lorenz",
            "role": "primary blocked state-geometry task",
            "why": "Tier 7.7h showed material capacity gain but failed permuted-recurrence sham separation.",
            "lengths": "8000,16000,32000",
            "required": True,
        },
        {
            "task": "mackey_glass",
            "role": "positive-control anchor",
            "why": "Tier 7.7h showed capacity gain with cleaner state-reset/permuted separation at high capacity.",
            "lengths": "8000,16000,32000",
            "required": True,
        },
        {
            "task": "narma10",
            "role": "repaired nonlinear-memory sanity check",
            "why": "Tier 7.7h showed only weak capacity response on repaired U(0,0.2) NARMA.",
            "stream_policy": "repaired_narma10_reduced_input_u02",
            "lengths": "8000,16000,32000",
            "required": True,
        },
    ]


def probe_rows() -> list[dict[str, Any]]:
    return [
        {
            "probe": "candidate_full_recurrence",
            "purpose": "locked CRA v2.5 temporal-state candidate from Tier 7.7h",
            "capacity_units": "16,32,64,128",
            "promotable": False,
        },
        {
            "probe": "permuted_recurrence_ensemble",
            "purpose": "test whether the 7.7h permuted win was basis luck or a robust generic-basis effect",
            "capacity_units": "16,32,64,128",
            "recurrence_seed_offsets": "11,23,37,71,101",
            "promotable": False,
        },
        {
            "probe": "state_reset_by_capacity",
            "purpose": "test whether temporal persistence, not only capacity, is necessary",
            "capacity_units": "16,32,64,128",
            "promotable": False,
        },
        {
            "probe": "orthogonal_random_basis_reference",
            "purpose": "compare candidate against a high-dimensional but non-CRA orthogonal basis",
            "capacity_units": "16,32,64,128",
            "promotable": False,
        },
        {
            "probe": "block_structured_basis_reference",
            "purpose": "test whether partitioned timescale/state groups raise effective dimensionality without claiming a CRA repair",
            "capacity_units": "16,32,64,128",
            "promotable": False,
        },
        {
            "probe": "causal_delay_embedding_reference",
            "purpose": "test whether Lorenz weakness is partly single-channel observability rather than recurrence alone",
            "capacity_units": "0",
            "promotable": False,
        },
        {
            "probe": "readout_concentration_audit",
            "purpose": "measure whether the state is rich but readout uses only one/two directions, or whether the state itself is low-rank",
            "capacity_units": "16,32,64,128",
            "promotable": False,
        },
    ]


def metric_rows() -> list[dict[str, Any]]:
    return [
        {"metric": "test_mse", "scope": "performance", "required": True},
        {"metric": "tail_mse", "scope": "performance", "required": True},
        {"metric": "test_corr", "scope": "performance", "required": True},
        {"metric": "participation_ratio", "scope": "state_geometry", "required": True},
        {"metric": "participation_ratio_per_unit", "scope": "state_geometry", "required": True},
        {"metric": "rank95_variance_count", "scope": "state_geometry", "required": True},
        {"metric": "top_pc_fraction", "scope": "state_geometry", "required": True},
        {"metric": "state_norm_mean_std", "scope": "state_dynamics", "required": True},
        {"metric": "step_delta_mean_std", "scope": "state_dynamics", "required": True},
        {"metric": "total_state_variance", "scope": "state_dynamics", "required": True},
        {"metric": "state_kernel_alignment", "scope": "state_geometry", "required": True},
        {"metric": "candidate_vs_sham_cka", "scope": "state_geometry", "required": True},
        {"metric": "readout_weight_pr", "scope": "readout", "required": True},
        {"metric": "top_weight_fraction", "scope": "readout", "required": True},
        {"metric": "seed_stability_mean_std", "scope": "repeatability", "required": True},
        {"metric": "feature_count_budget", "scope": "fairness", "required": True},
    ]


def outcome_rows() -> list[dict[str, Any]]:
    return [
        {
            "outcome": "candidate_specific_state_confirmed",
            "rule": "Candidate improves Lorenz, separates from permuted/orthogonal/block/state-reset probes, and has higher or more stable state-specific geometry than shams.",
            "allowed_claim": "CRA candidate state geometry is causally implicated in the high-capacity Lorenz gain.",
        },
        {
            "outcome": "generic_basis_explains_gain",
            "rule": "Permuted, orthogonal, block, or generic random bases match/beat candidate while showing comparable or better geometry.",
            "allowed_claim": "Capacity gain is real but not CRA-specific; route to state-interface/connectivity redesign before mechanism promotion.",
        },
        {
            "outcome": "low_rank_collapse_confirmed",
            "rule": "Candidate and probe families remain at participation ratio <= 3 or rank95 <= 8 across 64/128 while Lorenz remains weak.",
            "allowed_claim": "Current temporal-state interface expands amplitude more than independent state dimensions.",
        },
        {
            "outcome": "readout_bottleneck",
            "rule": "State PR/rank rises materially but readout weight PR/top-weight concentration stays low and performance does not follow.",
            "allowed_claim": "Repair readout/state interface before changing recurrence.",
        },
        {
            "outcome": "observability_bottleneck",
            "rule": "Causal delay embeddings improve Lorenz for all families while recurrence-specific probes remain non-separated.",
            "allowed_claim": "Single-scalar Lorenz interface is a major bottleneck; task/interface must be disclosed before architecture claims.",
        },
        {
            "outcome": "inconclusive_or_sham_blocked",
            "rule": "Missing data, inconsistent seeds, target/time shams fail, or no stable separation class is produced.",
            "allowed_claim": "No promotion; repair diagnostic design.",
        },
    ]


def expected_artifacts() -> list[dict[str, Any]]:
    return [
        {"artifact": "tier7_7j_results.json", "purpose": "scored state-specificity result and classification"},
        {"artifact": "tier7_7j_report.md", "purpose": "human-readable summary"},
        {"artifact": "tier7_7j_summary.csv", "purpose": "criteria summary"},
        {"artifact": "tier7_7j_state_geometry.csv", "purpose": "PR/rank/top-PC/norm/delta metrics"},
        {"artifact": "tier7_7j_state_kernel_alignment.csv", "purpose": "candidate/sham state-kernel alignment"},
        {"artifact": "tier7_7j_readout_concentration.csv", "purpose": "readout weight PR and concentration"},
        {"artifact": "tier7_7j_scoreboard.csv", "purpose": "performance table"},
        {"artifact": "tier7_7j_sham_separation.csv", "purpose": "candidate versus sham margins"},
        {"artifact": "tier7_7j_probe_manifest.json", "purpose": "locked probes, seeds, capacities, and stream policies"},
        {"artifact": "tier7_7j_claim_boundary.md", "purpose": "allowed claims and nonclaims"},
    ]


def build_contract() -> dict[str, Any]:
    return {
        "question": "Are the Tier 7.7h high-capacity gains candidate-specific state geometry, or generic high-dimensional/permuted recurrent feature effects?",
        "hypothesis": "If CRA's candidate recurrence is doing causal work, it should separate from permuted/orthogonal/block/state-reset probes on Lorenz while showing stable effective-dimensionality and readout-use signatures.",
        "null_hypothesis": "The high-capacity gain is explained by generic bases, basis luck, readout concentration, low-rank collapse, or single-channel observability rather than candidate-specific CRA recurrence.",
        "mechanism_under_test": "diagnostic state-specificity only; no repair, mechanism promotion, baseline freeze, hardware transfer, or benchmark tuning",
        "tasks": task_rows(),
        "seeds": [42, 43, 44],
        "lengths": [8000, 16000, 32000],
        "capacities": [16, 32, 64, 128],
        "probe_families": probe_rows(),
        "metrics": metric_rows(),
        "outcome_classes": outcome_rows(),
        "expected_artifacts": expected_artifacts(),
        "required_negative_result_handling": [
            "If effective dimensionality remains <= 3, document low-rank collapse and do not add mechanisms blindly.",
            "If generic bases explain the gain, route to a state-interface/connectivity contract rather than claiming CRA-specific recurrence.",
            "If readout concentration explains the gap, repair the readout/state interface before changing recurrence.",
            "If observability is the bottleneck, disclose the benchmark interface limitation before making architecture claims.",
        ],
        "leakage_rules": [
            "same repaired NARMA U(0,0.2) stream policy from 7.7e/7.7f/7.7h",
            "same chronological train/test split",
            "normalization fit on train prefix only",
            "prediction before online update for online models",
            "target/time shuffle controls retained",
            "feature counts and capacity budgets disclosed",
            "no tuning or mechanism promotion inside the diagnostic",
        ],
        "nonclaims": [
            "not a new mechanism",
            "not a repair tier",
            "not a baseline freeze",
            "not hardware/native transfer",
            "not public usefulness evidence",
            "not external-baseline superiority",
            "not language, AGI, or ASI evidence",
        ],
        "next_gate": NEXT_GATE,
    }


def summarize_77h(prereq_77h: dict[str, Any]) -> dict[str, Any]:
    classification = prereq_77h.get("classification") or {}
    task_diag = classification.get("task_diagnostics") or []
    out = {
        "status": prereq_77h.get("status"),
        "outcome": classification.get("outcome"),
        "recommendation": classification.get("recommendation"),
        "task_diagnostics": [],
    }
    for row in task_diag:
        out["task_diagnostics"].append(
            {
                "task": row.get("task"),
                "best_capacity_units": row.get("best_capacity_units"),
                "base16_divided_by_best_capacity": row.get("base16_divided_by_best_capacity"),
                "gap_closure_to_matched_esn": row.get("gap_closure_to_matched_esn"),
                "sham_blocked": row.get("sham_blocked"),
            }
        )
    return out


def write_report(output_dir: Path, payload: dict[str, Any]) -> None:
    contract = payload["contract"]
    lines = [
        "# Tier 7.7i Capacity Sham-Separation / State-Specificity Contract",
        "",
        f"- Generated: `{payload['generated_at_utc']}`",
        f"- Status: **{payload['status'].upper()}**",
        f"- Criteria: `{payload['criteria_passed']}/{payload['criteria_total']}`",
        f"- Outcome: `{payload['classification']['outcome']}`",
        "",
        "## Question",
        "",
        contract["question"],
        "",
        "## Why This Exists",
        "",
        "Tier 7.7h found material high-capacity gains but blocked attribution because Lorenz failed sham separation. This contract locks the next diagnostic before any repair or mechanism layering.",
        "",
        "## Probe Families",
        "",
        "| Probe | Purpose | Capacities | Promotable |",
        "| --- | --- | --- | --- |",
    ]
    for row in contract["probe_families"]:
        lines.append(f"| `{row['probe']}` | {row['purpose']} | {row['capacity_units']} | {row['promotable']} |")
    lines.extend(["", "## Outcome Classes", ""])
    for row in contract["outcome_classes"]:
        lines.append(f"- `{row['outcome']}`: {row['rule']}")
    lines.extend(["", "## Nonclaims", ""])
    for item in contract["nonclaims"]:
        lines.append(f"- {item}")
    lines.append("")
    (output_dir / "tier7_7i_report.md").write_text("\n".join(lines), encoding="utf-8")


def run(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    prereq_77h = read_json(PREREQ_77H)
    prereq_77g = read_json(PREREQ_77G)
    contract = build_contract()
    outcome_names = {row["outcome"] for row in contract["outcome_classes"]}
    metric_names = {row["metric"] for row in contract["metrics"]}
    probe_names = {row["probe"] for row in contract["probe_families"]}
    criteria = [
        criterion("Tier 7.7h prerequisite exists", str(PREREQ_77H), "exists and pass", PREREQ_77H.exists() and prereq_77h.get("status") == "pass"),
        criterion("Tier 7.7h outcome requires sham-separation contract", (prereq_77h.get("classification") or {}).get("outcome"), "== overfit_or_sham_blocked", (prereq_77h.get("classification") or {}).get("outcome") == "overfit_or_sham_blocked"),
        criterion("Tier 7.7g contract prerequisite exists", str(PREREQ_77G), "exists and pass", PREREQ_77G.exists() and prereq_77g.get("status") == "pass"),
        criterion("tasks locked", [row["task"] for row in contract["tasks"]], "Mackey/Lorenz/NARMA", {row["task"] for row in contract["tasks"]} == {"mackey_glass", "lorenz", "narma10"}),
        criterion("lengths locked", contract["lengths"], "== [8000,16000,32000]", contract["lengths"] == [8000, 16000, 32000]),
        criterion("seeds locked", contract["seeds"], "== [42,43,44]", contract["seeds"] == [42, 43, 44]),
        criterion("capacities locked", contract["capacities"], "== [16,32,64,128]", contract["capacities"] == [16, 32, 64, 128]),
        criterion("candidate and permuted probes included", sorted(probe_names), "contains candidate and permuted ensemble", {"candidate_full_recurrence", "permuted_recurrence_ensemble"}.issubset(probe_names)),
        criterion("orthogonal/block references included", sorted(probe_names), "contains orthogonal and block references", {"orthogonal_random_basis_reference", "block_structured_basis_reference"}.issubset(probe_names)),
        criterion("observability/readout probes included", sorted(probe_names), "contains delay embedding and readout audit", {"causal_delay_embedding_reference", "readout_concentration_audit"}.issubset(probe_names)),
        criterion("participation ratio metric included", sorted(metric_names), "contains participation_ratio", "participation_ratio" in metric_names),
        criterion("rank/top-PC metrics included", sorted(metric_names), "contains rank95 and top_pc", {"rank95_variance_count", "top_pc_fraction"}.issubset(metric_names)),
        criterion("state dynamics metrics included", sorted(metric_names), "contains norm/delta/variance", {"state_norm_mean_std", "step_delta_mean_std", "total_state_variance"}.issubset(metric_names)),
        criterion("readout concentration metrics included", sorted(metric_names), "contains readout weight metrics", {"readout_weight_pr", "top_weight_fraction"}.issubset(metric_names)),
        criterion("negative outcome classes included", sorted(outcome_names), "contains low-rank/generic/readout/observability outcomes", {"low_rank_collapse_confirmed", "generic_basis_explains_gain", "readout_bottleneck", "observability_bottleneck"}.issubset(outcome_names)),
        criterion("expected artifacts locked", len(contract["expected_artifacts"]), ">= 10", len(contract["expected_artifacts"]) >= 10),
        criterion("no scoring in contract", False, "must remain false", True),
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
            "tier7_7h_results": str(PREREQ_77H),
            "tier7_7h_status": prereq_77h.get("status"),
            "tier7_7h_outcome": (prereq_77h.get("classification") or {}).get("outcome"),
            "tier7_7h_sha256": sha256_file(PREREQ_77H),
            "tier7_7g_results": str(PREREQ_77G),
            "tier7_7g_status": prereq_77g.get("status"),
            "tier7_7g_sha256": sha256_file(PREREQ_77G),
        },
        "tier7_7h_summary": summarize_77h(prereq_77h),
        "contract": contract,
        "classification": {
            "outcome": "capacity_sham_separation_contract_locked",
            "scoring_authorized": status == "pass",
            "next_gate": NEXT_GATE,
            "baseline_freeze_authorized": False,
            "hardware_transfer_authorized": False,
            "mechanism_promotion_authorized": False,
        },
        "claim_boundary": "Tier 7.7i is a contract/pre-registration gate only. It performs no scoring, promotes no mechanism, freezes no baseline, claims no public usefulness, and authorizes no hardware/native transfer.",
    }
    write_json(output_dir / "tier7_7i_results.json", payload)
    write_json(output_dir / "tier7_7i_contract.json", contract)
    write_csv(output_dir / "tier7_7i_summary.csv", criteria)
    write_csv(output_dir / "tier7_7i_tasks.csv", contract["tasks"])
    write_csv(output_dir / "tier7_7i_probe_families.csv", contract["probe_families"])
    write_csv(output_dir / "tier7_7i_metrics.csv", contract["metrics"])
    write_csv(output_dir / "tier7_7i_outcome_classes.csv", contract["outcome_classes"])
    write_csv(output_dir / "tier7_7i_expected_artifacts.csv", contract["expected_artifacts"])
    (output_dir / "tier7_7i_claim_boundary.md").write_text(payload["claim_boundary"] + "\n", encoding="utf-8")
    write_report(output_dir, payload)
    manifest = {
        "tier": TIER,
        "status": status,
        "generated_at_utc": payload["generated_at_utc"],
        "output_dir": str(output_dir),
        "results_json": str(output_dir / "tier7_7i_results.json"),
        "report_md": str(output_dir / "tier7_7i_report.md"),
        "summary_csv": str(output_dir / "tier7_7i_summary.csv"),
        "classification_outcome": payload["classification"]["outcome"],
    }
    write_json(output_dir / "tier7_7i_latest_manifest.json", manifest)
    write_json(CONTROLLED / "tier7_7i_latest_manifest.json", manifest)
    return payload


def main() -> int:
    payload = run()
    print(
        json.dumps(
            json_safe(
                {
                    "status": payload["status"],
                    "criteria": f"{payload['criteria_passed']}/{payload['criteria_total']}",
                    "classification": payload["classification"]["outcome"],
                    "output_dir": payload["output_dir"],
                }
            ),
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
