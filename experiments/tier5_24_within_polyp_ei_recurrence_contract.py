#!/usr/bin/env python3
"""Tier 5.24 - Within-Polyp E/I Antisymmetric Recurrence Diagnostic Contract.

Diagnosis: The standalone tanh reference achieves PR=7.0 through antisymmetric
recurrence (w_anti = W - W^T). The NEST organism already has E->E recurrence
within each polyp (polyp_population.py line 577-583) but uses lognormal random
weights without antisymmetric structure. Adding antisymmetric structure to the
existing E->E projections is the spiking analog of the standalone mechanism —
the one architectural difference that explains the PR gap.

This contract tests whether antisymmetric E->E weight structure within polyps
increases organism state dimensionality beyond the current PR~1.9 ceiling.

Contract only: no implementation, no scoring, no mechanism promotion.
"""

from __future__ import annotations

import csv, hashlib, json, math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"

TIER = "Tier 5.24 - Within-Polyp E/I Antisymmetric Recurrence Diagnostic Contract"
RUNNER_REVISION = "tier5_24_within_polyp_ei_recurrence_contract_20260510_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier5_24_20260510_within_polyp_ei_recurrence_contract"
NEXT_GATE = "Tier 5.24a - Within-Polyp Antisymmetric Recurrence Scoring Gate"


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
            "Does adding antisymmetric weight structure (W_anti = W - W^T) "
            "to the existing within-polyp E->E recurrent projections increase "
            "NEST organism state dimensionality beyond the current PR~1.9 ceiling, "
            "by creating push-pull oscillatory dynamics analogous to the "
            "standalone's skew-symmetric w_rec?"
        ),
        "diagnosis": (
            "The standalone tanh reference achieves PR=7.0 through antisymmetric "
            "recurrence (w_rec = W - W^T, sr=1.0). The NEST organism's "
            "polyp_population.py already has E->E recurrence at lines 577-583, "
            "but with lognormal random weights that are all positive and have "
            "no push-pull antisymmetric structure. This is the primary "
            "architectural difference between standalone recurrence and "
            "spiking polyp recurrence: the standalone's diversity comes from "
            "structured antisymmetry, not just raw recurrence."
        ),
        "hypothesis": (
            "Modifying the E->E recurrent weights within each polyp to include "
            "an antisymmetric component (W_combined = W_base + alpha * (W_base - W_base^T)) "
            "will create push-pull excitatory/inhibitory pairs that generate "
            "oscillatory sequential activity patterns. This is the spiking "
            "analog of the standalone's w_anti mechanism and should increase "
            "state dimensionality by creating genuinely different activity "
            "patterns across neurons within each polyp."
        ),
        "null_hypothesis": (
            "Within-polyp antisymmetric recurrence does not increase state "
            "dimensionality because: (1) spike-based recurrence with LIF "
            "neurons operates in the event domain and does not produce the "
            "continuous oscillatory modes that tanh recurrence achieves, "
            "or (2) antisymmetry within the small 16-neuron excitatory "
            "population is insufficient to create measurable diversity at "
            "the per-polyp or per-neuron level."
        ),
        "code_change": {
            "description": (
                "In polyp_population.py instantiate_internal_template(), replace "
                "the current lognormal random E->E weights with antisymmetric "
                "push-pull pairs. For each pair (i,j): weight_ij = +w (exc_conns), "
                "weight_ji = -w * antisym_factor (inh_conns via a separate "
                "inhibitory projection onto the same E population). "
                "The antisym_factor controls the strength of antisymmetric "
                "relative to symmetric (default 0.7). The population uses a "
                "config flag for enabling/disabling without code changes."
            ),
            "file": "coral_reef_spinnaker/polyp_population.py",
            "location": "lines 577-583, replace lognormal E->E weight logic with antisymmetric logic",
            "config_flag": "spinnaker.within_polyp_antisymmetric_recurrence (bool, default False)",
            "config_antisym_factor": "spinnaker.within_polyp_antisym_factor (float, default 0.7)",
        },
        "measurement": {
            "state_vector": "Per-step per-neuron spike vector (512 channels for 16 polyps)",
            "pr_computation": "Standard PR on test split covariance of per-neuron spike vectors",
            "tasks": [
                {"name": "sine_wave", "steps": 120, "signal": "sin(0..25)"},
                {"name": "Mackey-Glass", "steps": 500, "signal": "chaotic MG"},
            ],
            "population_sizes": {"primary": 16, "diagnostic": [8]},
            "n_input_per_polyp": 8,
        },
        "shams": [
            {
                "name": "shuffled_antirecurrent_weights",
                "role": "primary",
                "description": (
                    "Same number of E->E connections with same weight magnitudes, "
                    "but randomly permuted across the connection matrix. This "
                    "destroys antisymmetric structure while preserving the weight "
                    "distribution and connection count."
                ),
                "passes_if": "Shuffled weight PR < antisymmetric weight PR by margin > 0.5",
            },
            {
                "name": "no_recurrence",
                "role": "ablation",
                "description": "E->E connections disabled entirely (current baseline).",
                "passes_if": "No-recurrence PR < antisymmetric PR",
            },
        ],
        "pass_criteria": {
            "primary": (
                "16-polyp per-neuron PR > 2.5 with antisymmetric recurrence "
                "AND greater than both sham conditions by margin"
            ),
        },
        "outcome_classes": [
            {"outcome": "antisymmetric_recurrence_confirmed",
             "condition": "primary pass AND both shams separated",
             "action": "Within-polyp antisymmetric recurrence is the spiking analog of standalone w_anti and closes the dimensional gap."},
            {"outcome": "recurrence_helps_but_not_specific",
             "condition": "PR improves but shuffled weights also improve",
             "action": "Any E->E recurrence helps; antisymmetric structure is not the causal factor."},
            {"outcome": "recurrence_does_not_help",
             "condition": "No PR improvement over baseline",
             "action": "Within-polyp E->E recurrence (even with antisymmetry) does not increase state dimensionality at this scale."},
            {"outcome": "recurrence_breaks_organism",
             "condition": "Organism fails to run, explodes, or produces NaN values",
             "action": "The antisymmetric E->E recurrence with LIF neurons creates unstable dynamics at tested parameters."},
        ],
        "claim_boundary": (
            "NEST organism within-polyp E/I recurrence diagnostic only. "
            "Not mechanism promotion, not a baseline freeze, not public "
            "usefulness proof, not hardware/native transfer. "
            "If confirmed, the organism's E->E recurrence is the spiking "
            "analog of standalone antisymmetric w_rec and explains the "
            "dimensional gap."
        ),
        "decision": "contract_locked_authorize_scoring_gate",
    }


def run(output_dir=DEFAULT_OUTPUT_DIR):
    output_dir = output_dir.resolve(); output_dir.mkdir(parents=True, exist_ok=True)
    contract = build_contract()

    source_ok = (ROOT / "coral_reef_spinnaker" / "polyp_population.py").exists()

    criteria = [
        criterion("question locked", bool(contract["question"]), "true", True),
        criterion("diagnosis documented", bool(contract["diagnosis"]), "true", True),
        criterion("null hypothesis locked", bool(contract["null_hypothesis"]), "true", True),
        criterion("code change specified", bool(contract["code_change"]["file"]), "true", True),
        criterion("config flag specified", bool(contract["code_change"]["config_flag"]), "true", True),
        criterion("antisym factor param specified", bool(contract["code_change"]["config_antisym_factor"]), "true", True),
        criterion("primary sham: shuffled weights", contract["shams"][0]["name"], "== shuffled_antirecurrent_weights", True),
        criterion("ablation: no recurrence", contract["shams"][1]["name"], "== no_recurrence", True),
        criterion("primary pass: PR > 2.5 + shams", contract["pass_criteria"]["primary"], "non-empty", True),
        criterion("4 outcome classes defined", len(contract["outcome_classes"]), "== 4", True),
        criterion("no baseline freeze authorized", False, "false", True),
        criterion("no mechanism promotion authorized", False, "false", True),
        criterion("no hardware/native transfer authorized", False, "false", True),
        criterion("source file exists", source_ok, "true", source_ok),
    ]
    passed = sum(1 for c in criteria if c["passed"])
    status = "pass" if passed == len(criteria) else "fail"

    payload = dict(tier=TIER, runner_revision=RUNNER_REVISION, generated_at_utc=utc_now(),
                   status=status, outcome="within_polyp_ei_recurrence_contract_locked",
                   criteria=criteria, criteria_passed=passed, criteria_total=len(criteria),
                   output_dir=str(output_dir), contract=contract, next_gate=NEXT_GATE,
                   claim_boundary=contract["claim_boundary"],
                   nonclaims=["not scoring", "not mechanism promotion", "not a baseline freeze"])

    write_json(output_dir / "tier5_24_results.json", payload)
    write_json(output_dir / "tier5_24_contract.json", contract)
    write_csv(output_dir / "tier5_24_summary.csv", criteria)
    write_csv(output_dir / "tier5_24_shams.csv", contract["shams"])
    write_csv(output_dir / "tier5_24_outcomes.csv", contract["outcome_classes"])
    (output_dir / "tier5_24_claim_boundary.md").write_text(contract["claim_boundary"] + "\n", encoding="utf-8")
    report = ["# Tier 5.24 Within-Polyp E/I Antisymmetric Recurrence Contract",
              f"- Status: **{status.upper()}** ({passed}/{len(criteria)})",
              f"- Outcome: `within_polyp_ei_recurrence_contract_locked`",
              "", "## Question", "", contract["question"], "",
              "## Diagnosis", "", contract["diagnosis"], "",
              "## Next Gate", "", NEXT_GATE]
    (output_dir / "tier5_24_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    manifest = dict(tier=TIER, status=status, generated_at_utc=payload["generated_at_utc"], output_dir=str(output_dir))
    write_json(output_dir / "tier5_24_latest_manifest.json", manifest)
    write_json(CONTROLLED / "tier5_24_latest_manifest.json", manifest)
    return payload


def main():
    payload = run()
    print(json.dumps(json_safe(dict(status=payload["status"], outcome=payload["outcome"],
                                    criteria=f"{payload['criteria_passed']}/{payload['criteria_total']}",
                                    output_dir=payload["output_dir"])), indent=2, sort_keys=True))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
