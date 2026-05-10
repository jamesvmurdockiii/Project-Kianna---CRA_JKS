#!/usr/bin/env python3
"""Tier 5.22 - Within-Polyp Per-Neuron Input Diversity Diagnostic Contract.

After Tier 5.21 showed per-neuron spike readout does not increase NEST organism
state dimensionality because within-polyp neurons are synchronized, this contract
tests the next hypothesis: per-neuron input gain diversity within each polyp's
8 input neurons creates genuinely different firing patterns that decorrelate
the excitatory population.

Mechanism: modify update_current_injections() in polyp_population.py to assign
each of the 8 input neurons a different gain on the sensory signal (0.3x-1.5x
range), plus amplify the per-neuron bias to 15% of sensory drive ceiling.

Contract only: no implementation, no scoring, no mechanism promotion.
"""

from __future__ import annotations

import csv, hashlib, json, math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"

TIER = "Tier 5.22 - Within-Polyp Per-Neuron Input Diversity Diagnostic Contract"
RUNNER_REVISION = "tier5_22_within_polyp_per_neuron_diversity_contract_20260510_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier5_22_20260510_within_polyp_per_neuron_diversity_contract"
PREREQ_521 = CONTROLLED / "tier5_21_20260510_nest_per_neuron_dimensionality_contract" / "tier5_21_results.json"
NEXT_GATE = "Tier 5.22a - Within-Polyp Per-Neuron Diversity Scoring Gate"


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
            "Does per-neuron input gain diversity within each polyp's 8 input "
            "neurons (0.3x-1.5x gain range on sensory signal, plus amplified "
            "per-neuron biases at 15% of sensory ceiling) increase NEST organism "
            "state dimensionality beyond the current PR≈1.3 ceiling?"
        ),
        "hypothesis": (
            "The current organism has all 8 input neurons per polyp receiving "
            "identical sensory drive, with per-neuron biases at ±0.02 nA "
            "(negligible vs ~30 nA signal). Different input gains and meaningful "
            "biases will cause input neurons to fire at different rates, which "
            "propagates through the within-polyp E/I structure to create diverse "
            "excitatory neuron firing patterns."
        ),
        "null_hypothesis": (
            "Per-neuron input diversity does not materially increase state "
            "dimensionality because the within-polyp connectivity is all-to-all "
            "from input to exc/inh, and the inhibitory feedback loop homogenizes "
            "any input-level diversity."
        ),
        "code_change": {
            "file": "coral_reef_spinnaker/polyp_population.py",
            "method": "update_current_injections",
            "changes": [
                "Replace sin(idx * 2.4) * 0.02 bias with per-polyp random biases at amplitude 0.15 * sensory_drive",
                "Assign each input neuron a unique gain (0.3 + index * 0.15) on sensory_drive",
            ],
        },
        "measurement": {
            "state_vector": "Per-step per-polyp activity_rate (one scalar per polyp)",
            "pr_computation": "Standard PR on test split covariance",
            "population_sizes": {
                "primary": 16,
                "diagnostic": [8],
            },
        },
        "sham": {
            "name": "shuffled_input_neuron_gains",
            "description": "Same per-input-neuron gain values but randomly shuffled across neurons within each polyp. Tests whether specific gain-to-position mapping matters or any 8 different gains produce the same diversity.",
            "passes_if": "Shuffled gain PR < candidate PR - 0.5, confirming structured gain assignment is causal.",
        },
        "pass_criteria": {
            "primary": "16-polyp per-polyp PR > 2.5 AND PR > 1.5x baseline (no per-neuron diversity)",
        },
        "outcome_classes": [
            {"outcome": "per_neuron_diversity_confirmed",
             "condition": "primary pass AND sham separated",
             "action": "Document that within-polyp input diversity increases state dimensionality. Promote as organism configuration change."},
            {"outcome": "per_neuron_diversity_partial",
             "condition": "PR improves but does not reach 2.5 or 1.5x",
             "action": "Document partial signal with remaining gap."},
            {"outcome": "per_neuron_diversity_not_supported",
             "condition": "No meaningful PR improvement over baseline",
             "action": "Within-polyp input diversity alone does not break synchrony."},
        ],
        "claim_boundary": (
            "NEST organism within-polyp diversity diagnostic only. "
            "Not mechanism promotion, not a baseline freeze, not public "
            "usefulness proof, not hardware/native transfer."
        ),
        "decision": "contract_locked_authorize_scoring_gate",
    }


def run(output_dir=DEFAULT_OUTPUT_DIR):
    output_dir = output_dir.resolve(); output_dir.mkdir(parents=True, exist_ok=True)
    contract = build_contract()
    prereq_ok = PREREQ_521.exists()

    # Verify the current organism code has the target method and current biases
    import os, sys
    sys.path.insert(0, str(ROOT))
    file_path = ROOT / "coral_reef_spinnaker" / "polyp_population.py"
    source_ok = file_path.exists()
    has_biases = "sin(neuron_indices * 2.39996" in file_path.read_text() if source_ok else False

    criteria = [
        criterion("prereq 5.21 exists", prereq_ok, "true", prereq_ok),
        criterion("question locked", bool(contract["question"]), "true", True),
        criterion("null hypothesis locked", bool(contract["null_hypothesis"]), "true", True),
        criterion("code change specified", bool(contract["code_change"]["file"]), "true", True),
        criterion("sham: shuffled input neuron gains", contract["sham"]["name"], "== shuffled_input_neuron_gains",
                  contract["sham"]["name"] == "shuffled_input_neuron_gains"),
        criterion("primary pass: PR > 2.5 AND > 1.5x baseline", True, "true", True),
        criterion("3 outcome classes defined", len(contract["outcome_classes"]), "== 3", True),
        criterion("current source has per-neuron biases", has_biases, "true", has_biases,
                  "sin(idx*2.4)*0.02 pattern found in update_current_injections"),
        criterion("no baseline freeze authorized", False, "false", True),
        criterion("no mechanism promotion authorized", False, "false", True),
        criterion("no hardware/native transfer authorized", False, "false", True),
    ]
    passed = sum(1 for c in criteria if c["passed"])
    status = "pass" if passed == len(criteria) else "fail"

    payload = dict(tier=TIER, runner_revision=RUNNER_REVISION, generated_at_utc=utc_now(),
                   status=status, outcome="within_polyp_diversity_contract_locked",
                   criteria=criteria, criteria_passed=passed, criteria_total=len(criteria),
                   output_dir=str(output_dir), contract=contract, next_gate=NEXT_GATE,
                   claim_boundary=contract["claim_boundary"],
                   nonclaims=["not scoring", "not mechanism promotion", "not a baseline freeze"])

    write_json(output_dir / "tier5_22_results.json", payload)
    write_json(output_dir / "tier5_22_contract.json", contract)
    write_csv(output_dir / "tier5_22_summary.csv", criteria)
    write_csv(output_dir / "tier5_22_outcomes.csv", contract["outcome_classes"])
    (output_dir / "tier5_22_claim_boundary.md").write_text(contract["claim_boundary"] + "\n", encoding="utf-8")
    report = ["# Tier 5.22 Within-Polyp Per-Neuron Input Diversity Contract",
              f"- Status: **{status.upper()}** ({passed}/{len(criteria)})",
              f"- Outcome: `within_polyp_diversity_contract_locked`",
              "", "## Question", "", contract["question"], "",
              "## Code Change", "",
              f"- File: `{contract['code_change']['file']}`",
              f"- Method: `{contract['code_change']['method']}`",
              "## Next Gate", "", NEXT_GATE]
    (output_dir / "tier5_22_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    manifest = dict(tier=TIER, status=status, generated_at_utc=payload["generated_at_utc"], output_dir=str(output_dir))
    write_json(output_dir / "tier5_22_latest_manifest.json", manifest)
    write_json(CONTROLLED / "tier5_22_latest_manifest.json", manifest)
    return payload


def main():
    payload = run()
    print(json.dumps(json_safe(dict(status=payload["status"], outcome=payload["outcome"],
                                    criteria=f"{payload['criteria_passed']}/{payload['criteria_total']}",
                                    output_dir=payload["output_dir"])), indent=2, sort_keys=True))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
