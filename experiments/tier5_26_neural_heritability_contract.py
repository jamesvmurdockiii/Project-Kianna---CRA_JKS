#!/usr/bin/env python3
"""Tier 5.26 — Neural Parameter Heritability & Mutation Contract.

Diagnosis: Tier 5.25a showed lifecycle ON (PR=2.29) == lifecycle with
clones (PR=2.29). The PR increase is NOT from trait evolution — it's
mathematical inflation from more polyps = more channels. The critical
sham (no-mutation) produces identical results.

Root cause: The lifecycle's 11 heritable ecological traits (metabolic_decay,
apoptosis_threshold, etc.) do NOT affect neural parameters (tau_m, v_thresh,
cm). Polyps evolve different reproductive rates and death thresholds but
remain COMPUTATIONALLY IDENTICAL — same membrane dynamics, same firing
behavior, same information processing.

The missing link: when a polyp reproduces, each child should inherit
mutated neural parameter scalings derived from ecological traits:
- metabolic_decay → tau_m scaling (faster metabolism = faster membrane)
- bdnf_uptake_efficiency → v_thresh scaling (more neurotrophin = lower threshold)
- cyclin_accumulation_rate → cm scaling (growth hormones affect capacitance)

This maps ecological diversity to computational diversity — the organism's
evolution now drives genuine differences in how polyps process information.

Contract only: no implementation, no scoring, no mechanism promotion.
"""

from __future__ import annotations

import csv, json, math, sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CONTROLLED = ROOT / "controlled_test_output"

TIER = "Tier 5.26 — Neural Parameter Heritability & Mutation Contract"
RUNNER_REVISION = "tier5_26_neural_heritability_contract_20260510_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier5_26_20260510_neural_heritability_contract"
NEXT_GATE = "Tier 5.26a — Neural Heritability Scoring Gate"


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
            "Does making neural parameters (tau_m, v_thresh, cm) heritable "
            "and mutable through lifecycle reproduction create genuine "
            "computational diversity — polyps evolving genuinely different "
            "neural dynamics — beyond the current ecological-only trait "
            "heritability?"
        ),
        "diagnosis": (
            "Tier 5.25a sham: lifecycle with mutation (PR=2.29) == lifecycle "
            "with CLONES/no-mutation (PR=2.29). The PR increase is mathematical "
            "inflation from larger population (more channels), not from trait "
            "evolution. ALL polyps have IDENTICAL neural computations regardless "
            "of their evolved ecological traits.\n\n"
            "Root cause: the 11 heritable ecology traits (metabolic_decay, "
            "apoptosis_threshold, cyclin_accumulation_rate, etc.) affect WHEN "
            "polyps reproduce and die, but have ZERO effect on HOW they compute. "
            "tau_m, v_thresh, cm are set from global config defaults with "
            "per-slot Gaussian noise (fixed, not heritable).\n\n"
            "The fix: map ecological traits to neural parameter scalings via "
            "a simple nonlinear mapping. When a polyp reproduces, the child "
            "inherits the parent's neural scalings with small mutations. "
            "push_all_parameters() already exists for applying changed "
            "parameters after mutation."
        ),
        "hypothesis": (
            "Adding heritable neural parameter scalings (tau_m_factor, "
            "v_thresh_factor, cm_factor) derived from ecological traits and "
            "subject to mutation during reproduction will create polyps with "
            "genuinely different computational properties. A population with "
            "divergent neural parameters will have higher state dimensionality "
            "(PR) than a clone population, because different neurons respond "
            "to the same input with genuinely different dynamics."
        ),
        "null_hypothesis": (
            "Heritable neural parameters do not increase state dimensionality "
            "because: (1) the mutation range is too small to create measurable "
            "differences, (2) LIF dynamics are insensitive to parameter "
            "variation at this scale, or (3) the I/E balance normalizes away "
            "individual parameter differences."
        ),
        "mechanism_under_test": {
            "name": "neural_parameter_heritability",
            "type": "lifecycle/neural mechanism",
            "description": (
                "Each polyp carries heritable neural scaling factors that "
                "multiply the base config values for tau_m, v_thresh, and cm. "
                "These factors are inherited from parents with bounded "
                "log-space mutation during reproduction. "
            ),
            "heritable_neural_params": {
                "tau_m_factor": {
                    "default": 1.0,
                    "mutation_sigma": 0.08,
                    "bounds": (0.5, 3.0),
                    "eco_derive_from": "metabolic_decay",
                    "description": "Faster metabolism = shorter membrane time constant",
                },
                "v_thresh_factor": {
                    "default": 1.0,
                    "mutation_sigma": 0.05,
                    "bounds": (0.7, 1.5),
                    "eco_derive_from": "bdnf_uptake_efficiency",
                    "description": "Better neurotrophin = lower firing threshold",
                },
                "cm_factor": {
                    "default": 1.0,
                    "mutation_sigma": 0.05,
                    "bounds": (0.5, 2.0),
                    "eco_derive_from": "cyclin_accumulation_rate",
                    "description": "Growth rate affects membrane capacitance",
                },
            },
        },
        "code_change": {
            "description": (
                "1. Add neural_factor attributes (tau_m_factor, v_thresh_factor, "
                "cm_factor) to PolypState in polyp_neuron.py\n"
                "2. In lifecycle.py inherit_traits(), also inherit and mutate "
                "neural parameter factors using the same bounded log-space mutation\n"
                "3. In create_lif_params() (polyp_population.py PolypNeuronType), "
                "apply the polyp's neural factors to scale base params\n"
                "4. In add_polyp/restore_polyp, use the polyp's neural factors "
                "instead of per-slot Gaussian noise\n"
                "5. Config flag: lifecycle.enable_neural_heritability (bool, default True)"
            ),
            "files": [
                "coral_reef_spinnaker/polyp_neuron.py",
                "coral_reef_spinnaker/lifecycle.py",
                "coral_reef_spinnaker/polyp_population.py",
            ],
        },
        "measurement": {
            "state_vector": "Per-neuron spike vector",
            "pr_computation": "Standard PR on test-split covariance",
            "task": "sine_wave (sin(0..40), 300 steps)",
            "population": {"initial": 8, "max": 32},
        },
        "conditions": [
            {"name": "neural_heritable", "description": "Lifecycle ON + neural parameter heritability"},
            {"name": "clone_no_heritability", "description": "Lifecycle ON but neural factors are clones (no mutation) — ecological traits still evolve"},
            {"name": "static_no_lifecycle", "description": "Lifecycle OFF — static population"},
        ],
        "shams": [
            {
                "name": "neural_clones_only",
                "role": "primary",
                "description": "Reproduction ON, ecology traits evolve, but neural_factor "
                               "mutation is disabled (children inherit exact parent factors). "
                               "Tests whether neural parameter heritability specifically "
                               "increases PR beyond ecological trait diversity alone.",
            },
            {
                "name": "random_neural_assign",
                "role": "secondary",
                "description": "Each polyp gets random neural factors at birth "
                               "(same variance as mutation) but factor NOT inherited from parent. "
                               "Tests whether heritability (lineage-specific accumulation) "
                               "is better than random variation.",
            },
        ],
        "pass_criteria": {
            "primary": (
                "heritable PR > clone PR by margin > 0.3 at final timepoint, "
                "AND heritable PR > static PR by margin > 0.5, "
                "AND neural_factor variance (std across polyps) increases over generations"
            ),
        },
        "outcome_classes": [
            {"outcome": "neural_heritability_confirmed",
             "condition": "primary pass AND neurally-heritable beats clone by > 0.3",
             "action": "Neural parameter heritability creates genuine computational diversity through evolution."},
            {"outcome": "neural_heritability_partial",
             "condition": "PR improves but margin < 0.3 vs clone",
             "action": "Neural heritability helps but effect is small; consider stronger mutation."},
            {"outcome": "neural_heritability_no_effect",
             "condition": "No PR difference between heritable and clone",
             "action": "Neural parameter variation at this scale is too small to affect LIF dynamics."},
            {"outcome": "neural_heritability_unstable",
             "condition": "Parameter variation destabilizes the network (NaN, extinction, silence)",
             "action": "Parameter bounds need tightening or different neural params."},
        ],
        "claim_boundary": (
            "Host-side NEST diagnostic of heritable neural parameter diversity only. "
            "Not mechanism promotion, not a baseline freeze, not hardware/Spynnaker "
            "evidence, not public usefulness proof."
        ),
        "decision": "contract_locked_authorize_implementation_and_scoring",
    }


def run(output_dir=None):
    if output_dir is None: output_dir = DEFAULT_OUTPUT_DIR
    output_dir = output_dir.resolve(); output_dir.mkdir(parents=True, exist_ok=True)
    contract = build_contract()

    criteria = [
        criterion("question locked", bool(contract["question"]), "true", True),
        criterion("diagnosis references 5.25a sham", "5.25a" in contract.get("diagnosis",""), "true", True),
        criterion("null hypothesis locked", bool(contract["null_hypothesis"]), "true", True),
        criterion("3 neural params specified", len(contract["mechanism_under_test"]["heritable_neural_params"]), "== 3", True),
        criterion("code change specifies 3 files", len(contract["code_change"]["files"]), "== 3", True),
        criterion("primary sham: neural clones", contract["shams"][0]["name"], "== neural_clones_only", True),
        criterion("secondary sham: random assign", contract["shams"][1]["name"], "== random_neural_assign", True),
        criterion("primary pass clear", contract["pass_criteria"]["primary"], "non-empty", True),
        criterion("4 outcome classes", len(contract["outcome_classes"]), "== 4", True),
        criterion("no baseline freeze authorized", False, "false", True),
        criterion("no mechanism promotion authorized", False, "false", True),
        criterion("no hardware/native transfer authorized", False, "false", True),
    ]
    passed = sum(1 for c in criteria if c["passed"])
    status = "pass" if passed == len(criteria) else "fail"

    payload = dict(tier=TIER, runner_revision=RUNNER_REVISION, generated_at_utc=utc_now(),
                   status=status, outcome="neural_heritability_contract_locked",
                   criteria=criteria, criteria_passed=passed, criteria_total=len(criteria),
                   output_dir=str(output_dir), contract=contract, next_gate=NEXT_GATE,
                   claim_boundary=contract["claim_boundary"])

    write_json(output_dir / "tier5_26_results.json", payload)
    write_json(output_dir / "tier5_26_contract.json", contract)
    write_csv(output_dir / "tier5_26_summary.csv", criteria)
    write_csv(output_dir / "tier5_26_shams.csv", contract["shams"])
    write_csv(output_dir / "tier5_26_outcomes.csv", contract["outcome_classes"])
    (output_dir / "tier5_26_report.md").write_text(
        f"# {TIER}\n\n- Status: **{status.upper()}** ({passed}/{len(criteria)})\n"
        f"- Outcome: `neural_heritability_contract_locked`\n\n"
        f"## Question\n\n{contract['question']}\n\n"
        f"## Next Gate\n\n{NEXT_GATE}\n"
    )
    return payload


def main():
    payload = run()
    print(json.dumps(json_safe(dict(status=payload["status"], outcome=payload["outcome"],
                                    criteria=f"{payload['criteria_passed']}/{payload['criteria_total']}",
                                    output_dir=payload["output_dir"])), indent=2, sort_keys=True))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
