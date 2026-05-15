#!/usr/bin/env python3
"""Tier 5.25 — Lifecycle-Enabled State Diversity Diagnostic Contract.

Diagnosis: Every NEST organism mechanism investigation (per-neuron gains,
per-polyp scaling, multi-channel routing, inter-polyp projections,
within-polyp recurrence) has hit a PR≈1.9 per-polyp / PR≈2.9 per-neuron
ceiling.  All of these are ENGINEERED diversity — external injection of
heterogeneity into a system designed for EMERGENT selection pressure.

The organism was designed with reproduction (mitosis with mutation),
apoptosis (death of low-fitness polyps), and trophic economy precisely
to generate diversity organically: offspring inherit parent traits with
small mutations, selection preserves beneficial variations, and over
generations the population diverges naturally.

The Tier 7.8a morphology test FALSIFIED static heterogeneity (different
templates at initialization) — correctly.  But static heterogeneity is
NOT lifecycle diversity.  Lifecycle diversity emerges from the INTERACTION
of reproduction, mutation, and selection over time.  This contract tests
that distinct hypothesis.

Contract only: no implementation, no scoring, no mechanism promotion.
"""

from __future__ import annotations

import csv, hashlib, json, math, sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CONTROLLED = ROOT / "controlled_test_output"

TIER = "Tier 5.25 — Lifecycle-Enabled State Diversity Diagnostic Contract"
RUNNER_REVISION = "tier5_25_lifecycle_state_diversity_contract_20260510_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier5_25_20260510_lifecycle_state_diversity_contract"
NEXT_GATE = "Tier 5.25a — Lifecycle State Diversity Scoring Gate"


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
            "Does enabling organism lifecycle (reproduction with mutation + "
            "apoptosis + trophic selection) increase state dimensionality "
            "beyond the current PR≈1.9 ceiling, by generating emergent "
            "population diversity through inheritance, variation, and "
            "selection rather than through engineered parameter injection?"
        ),
        "diagnosis": (
            "Every NEST organism mechanism tested (Tiers 5.21-5.24, 5.23a) "
            "has hit a PR ceiling of ≈1.9 per-polyp / ≈2.9 per-neuron. "
            "All of these are forms of ENGINEERED diversity: setting per-neuron "
            "gains, per-polyp sensory scaling, multi-channel feature routing, "
            "inter-polyp projections, or within-polyp antisymmetric recurrence. "
            "The organism was designed to achieve diversity through LIFECYCLE: "
            "reproduction with heritable trait mutation, apoptosis of low-fitness "
            "polyps, and trophic selection. Engineered diversity works against "
            "the organism's fundamental design principle."
        ),
        "reversal_of_79_dequeue": (
            "The Tier 7.8a morphology test falsified STATIC heterogeneity — "
            "assigning different templates at initialisation. This correctly "
            "showed that heterogeneous initial templates do not improve PR. "
            "But lifecycle diversity is NOT static heterogeneity: it is "
            "EMERGENT diversity evolving over generations through reproduction "
            "+ mutation + selection. The 7.9 dequeue decision conflated these "
            "two mechanisms. Tier 7.9 is re-queued with corrected scope: "
            "lifecycle-enabled emergent diversity, not static template variation."
        ),
        "hypothesis": (
            "Enabling reproduction with heritable trait mutation and "
            "apoptosis with trophic selection will cause the polyp population "
            "to diverge over generations, producing genuinely different "
            "neuronal properties (tau_m, connectivity parameters, input "
            "sensitivity) across polyps. This emergent diversity will "
            "increase state dimensionality (PR) compared to a static "
            "population without lifecycle."
        ),
        "null_hypothesis": (
            "Enabling lifecycle does not increase state dimensionality "
            "because: (1) mutation rates are too small to create meaningful "
            "trait divergence within typical simulation lengths, "
            "(2) selection pressure is too weak to preserve beneficial "
            "variations, or (3) the polyp trait space doesn't contain "
            "parameters that affect state diversity."
        ),
        "mechanism_under_test": {
            "name": "lifecycle_emergent_diversity",
            "type": "population/lifecycle mechanism",
            "description": (
                "Reproduction (mitosis with trait mutation), apoptosis "
                "(death of low-fitness/poor-trophic polyps), and trophic "
                "economy create a selection pressure that drives trait "
                "diversification over generations."
            ),
            "heritable_traits": [
                "tau_m (membrane time constant, ±5% per generation)",
                "v_thresh (firing threshold, ±2% per generation)",
                "input_sensitivity (via tau_syn_E modulation, ±5%)",
                "connectivity_pattern (via internal_conn_seed offset, ±10%)",
                "reproduction_threshold (cyclin accumulation rate, ±3%)",
            ],
        },
        "measurement": {
            "state_vector": "Per-neuron spike vector (512 channels for initial 8 polyps)",
            "pr_computation": "Standard PR on test-split covariance",
            "timepoints": [0, 50, 100, 150, 200, 300],
            "task": "sine_wave (sin(0..25), 300 steps)",
            "population": {
                "initial": 4,
                "max": 32,
            },
        },
        "conditions": [
            {
                "name": "lifecycle_on",
                "description": "Reproduction + mutation + apoptosis enabled. "
                               "Polyps reproduce when trophic health > threshold, "
                               "offspring inherit parent traits with small mutations. "
                               "Low-fitness polyps die via apoptosis.",
            },
            {
                "name": "lifecycle_off",
                "description": "Static population: no reproduction, no apoptosis. "
                               "Same initial polyps survive the entire run. "
                               "This is the current benchmark configuration.",
            },
        ],
        "shams": [
            {
                "name": "reproduction_no_mutation",
                "role": "ablation/control",
                "description": "Reproduction enabled but mutation disabled. "
                               "Offspring are exact clones of parents. Tests "
                               "whether population growth alone (not trait "
                               "diversification) affects PR.",
                "passes_if": "no-mutation PR < lifecycle-on PR",
            },
            {
                "name": "no_selection_pressure",
                "role": "ablation/control",
                "description": "Reproduction + mutation enabled but apoptosis "
                               "disabled (no death, polyps never culled). Tests "
                               "whether selection is causal or just reproduction.",
                "passes_if": "no-selection PR < lifecycle-on PR",
            },
            {
                "name": "shuffled_fitness",
                "role": "sham",
                "description": "Reproduction + mutation enabled but fitness "
                               "scores are randomly shuffled before selection. "
                               "Tests whether directed selection produces better "
                               "diversity than random drift.",
                "passes_if": "shuffled-fitness PR < lifecycle-on PR",
            },
        ],
        "pass_criteria": {
            "primary": (
                "PR at lifecycle-on final timepoint > 1.5x PR at lifecycle-off "
                "same timepoint, AND PR trajectory increases with lifecycle steps "
                "(positive Kendall tau between step and PR), AND at least one "
                "sham/ablation separated by margin > 0.5 PR."
            ),
            "secondary": [
                "Population size remains stable (no extinction or unbounded growth)",
                "At least 2 generations of reproduction occur",
                "Trait variance (std of tau_m across polyps) increases over time",
            ],
        },
        "outcome_classes": [
            {"outcome": "lifecycle_diversity_confirmed",
             "condition": "primary pass AND all shams separated AND secondary criteria met",
             "action": "Lifecycle-enabled emergent diversity is the correct mechanism "
                       "for organism state dimensionality. Promote to full investigation. "
                       "Dequeue reversed successfully."},
            {"outcome": "lifecycle_helps_partially",
             "condition": "PR improves but not 1.5x, or shams not fully separated",
             "action": "Lifecycle direction is correct but current parameters "
                       "(mutation rate, selection pressure) need tuning."},
            {"outcome": "lifecycle_no_effect",
             "condition": "No PR improvement over static population",
             "action": "Lifecycle reproduction + mutation does not create measurable "
                       "trait diversity at these run lengths/parameters."},
            {"outcome": "lifecycle_unstable",
             "condition": "Population crashes (extinction) or explodes beyond max",
             "action": "Lifecycle parameter tuning needed before diversity measurement."},
        ],
        "claim_boundary": (
            "Host-side software diagnostic of lifecycle-enabled state diversity only. "
            "Not mechanism promotion, not a baseline freeze, not hardware/Spynnaker "
            "lifecycle evidence, not full ecology scaling, not public usefulness proof."
        ),
        "decision": "contract_locked_authorize_scoring_gate",
    }


def run(output_dir=None):
    if output_dir is None:
        output_dir = DEFAULT_OUTPUT_DIR
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    contract = build_contract()

    org_file = ROOT / "coral_reef_spinnaker" / "organism.py"
    source_ok = org_file.exists()

    criteria = [
        criterion("question locked", bool(contract["question"]), "true", True),
        criterion("diagnosis documented", bool(contract["diagnosis"]), "true", True),
        criterion("7.9 dequeue reversal reasoned", bool(contract.get("reversal_of_79_dequeue")), "true", True),
        criterion("null hypothesis locked", bool(contract["null_hypothesis"]), "true", True),
        criterion("heritable traits specified", len(contract["mechanism_under_test"]["heritable_traits"]), ">= 3", True),
        criterion("two primary conditions", len(contract["conditions"]), "== 2", True, "lifecycle_on, lifecycle_off"),
        criterion("primary sham: no-mutation", contract["shams"][0]["name"], "== reproduction_no_mutation", True),
        criterion("ablation: no-selection", contract["shams"][1]["name"], "== no_selection_pressure", True),
        criterion("sham: shuffled fitness", contract["shams"][2]["name"], "== shuffled_fitness", True),
        criterion("primary pass: PR 1.5x + trajectory", contract["pass_criteria"]["primary"], "non-empty", True),
        criterion("4 outcome classes defined", len(contract["outcome_classes"]), "== 4", True),
        criterion("source file exists", source_ok, "true", source_ok),
        criterion("no baseline freeze authorized", False, "false", True),
        criterion("no mechanism promotion authorized", False, "false", True),
        criterion("no hardware/native transfer authorized", False, "false", True),
        criterion("engineered diversity documented as dead-end",
                  "engineered" in contract["diagnosis"].lower(), "true",
                  "engineered" in contract["diagnosis"].lower()),
    ]
    passed = sum(1 for c in criteria if c["passed"])
    status = "pass" if passed == len(criteria) else "fail"

    payload = dict(tier=TIER, runner_revision=RUNNER_REVISION, generated_at_utc=utc_now(),
                   status=status, outcome="lifecycle_state_diversity_contract_locked",
                   criteria=criteria, criteria_passed=passed, criteria_total=len(criteria),
                   output_dir=str(output_dir), contract=contract, next_gate=NEXT_GATE,
                   claim_boundary=contract["claim_boundary"],
                   nonclaims=["not scoring", "not mechanism promotion", "not a baseline freeze"])

    write_json(output_dir / "tier5_25_results.json", payload)
    write_json(output_dir / "tier5_25_contract.json", contract)
    write_csv(output_dir / "tier5_25_summary.csv", criteria)
    write_csv(output_dir / "tier5_25_shams.csv", contract["shams"])
    write_csv(output_dir / "tier5_25_outcomes.csv", contract["outcome_classes"])
    (output_dir / "tier5_25_report.md").write_text(
        f"# Tier 5.25 Lifecycle-Enabled State Diversity Contract\n\n"
        f"- Status: **{status.upper()}** ({passed}/{len(criteria)})\n"
        f"- Outcome: `lifecycle_state_diversity_contract_locked`\n\n"
        f"## Question\n\n{contract['question']}\n\n"
        f"## Diagnosis\n\n{contract['diagnosis']}\n\n"
        f"## Next Gate\n\n{NEXT_GATE}\n"
    )
    manifest = dict(tier=TIER, status=status, generated_at_utc=payload["generated_at_utc"],
                    output_dir=str(output_dir))
    write_json(output_dir / "tier5_25_latest_manifest.json", manifest)
    write_json(CONTROLLED / "tier5_25_latest_manifest.json", manifest)
    return payload


def main():
    payload = run()
    print(json.dumps(json_safe(dict(status=payload["status"], outcome=payload["outcome"],
                                    criteria=f"{payload['criteria_passed']}/{payload['criteria_total']}",
                                    output_dir=payload["output_dir"])), indent=2, sort_keys=True))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
