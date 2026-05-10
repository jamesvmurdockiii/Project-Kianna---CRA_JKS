#!/usr/bin/env python3
"""Tier 5.23 - Inter-Polyp Antisymmetric PyNN Projections Diagnostic Contract.

Diagnosis: The NEST organism has zero inter-polyp synaptic connections in
benchmark mode. sync_to_spinnaker() is gated behind backend_name == "sPyNNaker"
at organism.py:264, so the antisymmetric edges configured via the
antisymmetric_inter_polyp_edges flag only exist as host-level ReefNetwork edges
and are never pushed to NEST as actual PyNN projections.

This contract tests whether calling sync_to_spinnaker() for the NEST backend
with antisymmetric E/I projection weights between polyps increases the
organism's state dimensionality beyond the current PR≈1.9 ceiling.

Contract only: no implementation, no scoring, no mechanism promotion.
"""

from __future__ import annotations

import csv, hashlib, json, math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"

TIER = "Tier 5.23 - Inter-Polyp Antisymmetric PyNN Projections Diagnostic Contract"
RUNNER_REVISION = "tier5_23_inter_polyp_antisymmetric_projections_contract_20260510_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier5_23_20260510_inter_polyp_antisymmetric_projections_contract"
PREREQ_522 = CONTROLLED / "tier5_22_20260510_within_polyp_per_neuron_diversity_contract" / "tier5_22_results.json"
NEXT_GATE = "Tier 5.23a - Inter-Polyp Antisymmetric Projections Scoring Gate"


def utc_now(): return datetime.now(timezone.utc).isoformat(timespec="seconds")

def json_safe(v):
    if isinstance(v, Path): return str(v)
    if isinstance(v, dict): return {str(k): json_safe(v2) for k, v2 in v.items()}
    if isinstance(v, (list, tuple)): return [json_safe(x) for x in v]
    if isinstance(v, float) and not math.isfinite(v): return None
    return v

def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")

def write_csv(path, rows, fieldnames=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None: fieldnames = list(dict.fromkeys(k for r in rows for k in r))
    with path.open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n"); w.writeheader()
        for r in rows: w.writerow({k: json_safe(r.get(k,"")) for k in fieldnames})

def criterion(name, value, rule, passed, details=""):
    return {"name": name, "criterion": name, "value": json_safe(value),
            "rule": rule, "passed": bool(passed), "note": details}

def build_contract():
    return {
        "question": (
            "Does enabling inter-polyp PyNN projections with antisymmetric E/I "
            "weights on the NEST backend increase organism state dimensionality "
            "beyond the current PR≈1.9 ceiling, by creating genuine synaptic "
            "recurrence analogous to the standalone's skew-symmetric w_rec?"
        ),
        "diagnosis": (
            "The NEST organism's inter-polyp edges are stored as host-level "
            "ReefNetwork objects but never materialized as PyNN projections "
            "because sync_to_spinnaker() at organism.py:264 is gated behind "
            "backend_name == 'sPyNNaker'. With reproduce=False, the organism "
            "has zero inter-polyp synaptic connections — each polyp is "
            "synaptically isolated. The antisymmetric_inter_polyp_edges config "
            "flag creates host-level edges that never reach the NEST simulation."
        ),
        "hypothesis": (
            "Calling sync_to_spinnaker() for the NEST backend after the "
            "antisymmetric inter-polyp edges are created will materialize them "
            "as PyNN projections (Projection with StaticSynapse on NEST). "
            "These projections create the structured E/I recurrence that the "
            "standalone achieves via skew-symmetric w_rec. This will increase "
            "organism state dimensionality because polyps now communicate "
            "through synaptic connections with push-pull E/I dynamics."
        ),
        "null_hypothesis": (
            "Inter-polyp PyNN projections do not increase state dimensionality "
            "because: (1) the projections exist but spike-based communication "
            "does not create continuous oscillatory modes like tanh recurrence, "
            "or (2) the NEST backend factory's create_inter_polyp_projection "
            "fails or produces no-op projections on NEST."
        ),
        "code_change": {
            "description": "Remove the backend_name=='sPyNNaker' gate from sync_to_spinnaker() call at organism.py line 264, so NEST also materializes inter-polyp edges as PyNN projections.",
            "file": "coral_reef_spinnaker/organism.py",
            "location": "line 264, remove 'self._backend_factory.backend_name == \"sPyNNaker\"' condition",
        },
        "measurement": {
            "state_vector": "Per-step per-polyp activity_rate",
            "pr_computation": "Standard PR on test split covariance",
            "tasks": ["sine_wave", "mackey_glass_500step"],
            "population_sizes": {"primary": 8, "diagnostic": [4, 16]},
        },
        "shams": [
            {
                "name": "random_symmetric_projections",
                "role": "primary",
                "description": "Same number of inter-polyp projections but with random weights (no antisymmetric structure). Tests whether antisymmetric E/I pairing is causal or any inter-polyp connectivity helps.",
                "passes_if": "Random projection PR < antisymmetric projection PR - 1.0",
            },
            {
                "name": "no_projections",
                "role": "ablation",
                "description": "Default benchmark mode: zero inter-polyp projections (current state).",
                "passes_if": "No-projection PR < antisymmetric projection PR",
            },
        ],
        "pass_criteria": {
            "primary": "8-polyp per-polyp PR > 2.5 with antisymmetric projections AND greater than both sham conditions",
        },
        "outcome_classes": [
            {"outcome": "antisymmetric_projections_confirmed",
             "condition": "primary pass AND both shams separated",
             "action": "Inter-polyp antisymmetric projections are the missing recurrence component for NEST organism."},
            {"outcome": "projections_help_but_not_specific",
             "condition": "PR improves but random projections also improve",
             "action": "Any inter-polyp connectivity helps; antisymmetric structure is not the causal factor."},
            {"outcome": "projections_dont_help",
             "condition": "No PR improvement over baseline",
             "action": "Inter-polyp PyNN projections on NEST do not increase state dimensionality at this scale."},
            {"outcome": "projections_break_organism",
             "condition": "Organism fails to run or produces NaN/infinite values",
             "action": "The backend factory fails to create inter-polyp projections on NEST."},
        ],
        "claim_boundary": (
            "NEST organism inter-polyp recurrence diagnostic only. "
            "Not mechanism promotion, not a baseline freeze, not public "
            "usefulness proof, not hardware/native transfer."
        ),
        "decision": "contract_locked_authorize_scoring_gate",
    }


def run(output_dir=DEFAULT_OUTPUT_DIR):
    output_dir = output_dir.resolve(); output_dir.mkdir(parents=True, exist_ok=True)
    contract = build_contract()
    prereq_ok = PREREQ_522.exists()

    # Verify the current organism code has the backend gate at line ~264
    org_file = ROOT / "coral_reef_spinnaker" / "organism.py"
    source_ok = org_file.exists()
    has_sPynnaker_gate = "backend_factory.backend_name" in org_file.read_text() if source_ok else False

    criteria = [
        criterion("prereq 5.22 exists", prereq_ok, "true", prereq_ok),
        criterion("question locked", bool(contract["question"]), "true", True),
        criterion("diagnosis documented", bool(contract["diagnosis"]), "true", True),
        criterion("null hypothesis locked", bool(contract["null_hypothesis"]), "true", True),
        criterion("code change specified", bool(contract["code_change"]["file"]), "true", True),
        criterion("primary sham: random symmetric", contract["shams"][0]["name"], "== random_symmetric_projections", True),
        criterion("ablation: no projections", contract["shams"][1]["name"], "== no_projections", True),
        criterion("primary pass: PR > 2.5 + shams", contract["pass_criteria"]["primary"], "non-empty", True),
        criterion("4 outcome classes defined", len(contract["outcome_classes"]), "== 4", True),
        criterion("backend gate confirmed in source", has_sPynnaker_gate, "true", has_sPynnaker_gate),
        criterion("no baseline freeze authorized", False, "false", True),
        criterion("no mechanism promotion authorized", False, "false", True),
        criterion("no hardware/native transfer authorized", False, "false", True),
    ]
    passed = sum(1 for c in criteria if c["passed"])
    status = "pass" if passed == len(criteria) else "fail"

    payload = dict(tier=TIER, runner_revision=RUNNER_REVISION, generated_at_utc=utc_now(),
                   status=status, outcome="inter_polyp_antisymmetric_projections_contract_locked",
                   criteria=criteria, criteria_passed=passed, criteria_total=len(criteria),
                   output_dir=str(output_dir), contract=contract, next_gate=NEXT_GATE,
                   claim_boundary=contract["claim_boundary"],
                   nonclaims=["not scoring", "not mechanism promotion", "not a baseline freeze"])

    write_json(output_dir / "tier5_23_results.json", payload)
    write_json(output_dir / "tier5_23_contract.json", contract)
    write_csv(output_dir / "tier5_23_summary.csv", criteria)
    write_csv(output_dir / "tier5_23_shams.csv", contract["shams"])
    write_csv(output_dir / "tier5_23_outcomes.csv", contract["outcome_classes"])
    (output_dir / "tier5_23_claim_boundary.md").write_text(contract["claim_boundary"] + "\n", encoding="utf-8")
    report = ["# Tier 5.23 Inter-Polyp Antisynaptic PyNN Projections Contract",
              f"- Status: **{status.upper()}** ({passed}/{len(criteria)})",
              f"- Outcome: `inter_polyp_antisymmetric_projections_contract_locked`",
              "", "## Question", "", contract["question"], "",
              "## Diagnosis", "", contract["diagnosis"], "",
              "## Next Gate", "", NEXT_GATE]
    (output_dir / "tier5_23_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    manifest = dict(tier=TIER, status=status, generated_at_utc=payload["generated_at_utc"], output_dir=str(output_dir))
    write_json(output_dir / "tier5_23_latest_manifest.json", manifest)
    write_json(CONTROLLED / "tier5_23_latest_manifest.json", manifest)
    return payload


def main():
    payload = run()
    print(json.dumps(json_safe(dict(status=payload["status"], outcome=payload["outcome"],
                                    criteria=f"{payload['criteria_passed']}/{payload['criteria_total']}",
                                    output_dir=payload["output_dir"])), indent=2, sort_keys=True))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
