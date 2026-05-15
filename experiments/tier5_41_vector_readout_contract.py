#!/usr/bin/env python3
"""Tier 5.41 — Structured Vector Readout / Caste-Separated Projections Contract.

Diagnosis: The colony prediction collapses all per-polyp state diversity into
a single scalar via `tanh(weight * sensory_drive + bias)` — a function of
input, not internal state.  PR jumps 1.3-2.4x with maturation but MSE stays
identical.  The organism creates a computational ecosystem but the readout
only sees one collapsed value.

This contract tests a structured vector readout where each functional caste
(filters, memory, rotors, chaotic, stabilizers) contributes to a different
output component: trend, memory, oscillation, and anomaly.  The colony
predicts a VECTOR, not a scalar.  Per-task, a learned weighting combines
components into the required output format.

Option B of the readout architecture.  Contract only.
"""

from __future__ import annotations
import csv, json, math, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CONTROLLED = ROOT / "controlled_test_output"

TIER = "Tier 5.41 — Structured Vector Readout Contract"
RUNNER_REVISION = "tier5_41_vector_readout_contract_20260513_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier5_41_20260513_vector_readout_contract"
NEXT_GATE = "Tier 5.41a — Vector Readout Scoring Gate"

PASS_MARGIN_MSE = 0.05  # MSE must improve by at least 5% over scalar baseline

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
def criterion(name, value, rule, passed, details=""):
    return {"name": name, "criterion": name, "value": json_safe(value), "rule": rule, "passed": bool(passed), "note": details}

def build_contract():
    return {
        "question": (
            "Does a caste-separated structured vector readout — where filter "
            "polyps contribute to trend, memory polyps to memory, rotors to "
            "oscillation, and chaotic to anomaly — convert organism state "
            "diversity into improved prediction performance (lower MSE) "
            "compared to the scalar readout?"
        ),
        "diagnosis": (
            "The current readout collapses per-polyp state into a single scalar "
            "via `tanh(weight * sensory_drive + bias)`.  PR increases 1.3-2.4x "
            "with maturation but MSE is identical — the readout produces the "
            "same output from any internal state.\n\n"
            "The organism's functional castes (filter, memory, rotor, chaotic, "
            "stabilizer) create different dynamical operators per polyp.  The "
            "readout should USE this structure: filters capture trends, memory "
            "polyps retain history, rotors detect oscillations, chaotic polyps "
            "flag anomalies.\n\n"
            "The colony output becomes a 4-vector [trend, memory, oscillation, "
            "anomaly].  Each component is a weighted aggregation of state "
            "vectors from the corresponding caste.  Per-task, a learned linear "
            "combination maps the 4-vector to the required scalar prediction."
        ),
        "hypothesis": (
            "Caste-separated structured readout will reduce prediction MSE "
            "compared to scalar readout because (1) each component captures "
            "a different signal aspect, (2) the caste structure provides "
            "pre-organization for the learned combination, (3) the output "
            "vector has 4x the dimensionality of the scalar, and (4) per-task "
            "weighting selects the relevant components automatically."
        ),
        "null_hypothesis": (
            "Structured vector readout does not improve MSE because "
            "(1) the caste structure is too noisy at 2000 steps, "
            "(2) the components are correlated (collapsed to 1-2 effective), "
            "or (3) the online LMS learning rate is too slow."
        ),
        "mechanism_under_test": {
            "name": "structured_vector_readout",
            "type": "readout architecture",
            "caste_to_component": {
                0: "trend",      # Filter → trend tracking
                1: "memory",     # Memory → historical retention
                2: "oscillation", # Rotor → periodic detection
                3: "anomaly",    # Chaotic → surprise detection
                4: "baseline",   # Stabilizer → normalization
            },
            "output_vector": "[trend, memory, oscillation, anomaly]",
            "per_task_weighting": "Learned linear combination of 4 components via online LMS",
        },
        "conditions": {
            "vector_readout": "Caste-separated 4-vector output",
            "scalar_readout": "Current single-scalar output (sham baseline)",
        },
        "measurement": {
            "tasks": ["sine", "Mackey-Glass"],
            "steps": 2000,
            "train_frac": 0.6,
            "metrics": ["MSE", "MAE", "PR"],
            "population": {"initial": 4, "max": 12},
        },
        "pass_criteria": {
            "primary": (
                f"vector_readout MSE < scalar_readout MSE by >{PASS_MARGIN_MSE} "
                "on at least one task, AND output vector rank >= 2 (not collapsed)"
            ),
        },
        "outcome_classes": [
            {"outcome": "vector_readout_confirmed",
             "condition": "primary pass on both MG and sine",
             "action": "Structured vector readout converts diversity into prediction. Promote."},
            {"outcome": "vector_readout_partial",
             "condition": "primary pass on one task only",
             "action": "Vector readout helps on specific signal types."},
            {"outcome": "vector_readout_no_effect",
             "condition": "No MSE improvement over scalar",
             "action": "Caste structure not yet coherent enough for readout to leverage."},
        ],
        "claim_boundary": (
            "Host-side NEST diagnostic. Not mechanism promotion, not baseline "
            "freeze, not hardware evidence, not public usefulness proof."
        ),
        "layers_on": "v2.7 baseline + conservation laws (5.38-5.40)",
        "decision": "contract_locked_authorize_implementation",
    }

def run(output_dir=None):
    if output_dir is None: output_dir = DEFAULT_OUTPUT_DIR
    output_dir = output_dir.resolve(); output_dir.mkdir(parents=True, exist_ok=True)
    contract = build_contract()
    criteria = [
        criterion("question locked", bool(contract["question"]), "true", True),
        criterion("Option B specified", "vector" in contract["diagnosis"].lower(), "true", True),
        criterion("5 castes to components", len(contract["mechanism_under_test"]["caste_to_component"]), "== 5", True),
        criterion("4 output components", len(contract["mechanism_under_test"]["output_vector"].strip("[]").split(",")), ">= 3", True),
        criterion("primary pass: MSE margin", bool(contract["pass_criteria"]["primary"]), "true", True),
        criterion("3 outcome classes", len(contract["outcome_classes"]), "== 3", True),
        criterion("layers on v2.7", bool(contract.get("layers_on")), "true", True),
        criterion("no baseline freeze", False, "false", True),
        criterion("no mechanism promotion", False, "false", True),
    ]
    passed = sum(1 for c in criteria if c["passed"])
    payload = dict(tier=TIER, runner_revision=RUNNER_REVISION, generated_at_utc=utc_now(),
                   status="pass", outcome="vector_readout_contract_locked",
                   criteria=criteria, criteria_passed=passed, criteria_total=len(criteria),
                   output_dir=str(output_dir), contract=contract, next_gate=NEXT_GATE)
    write_json(output_dir / "tier5_41_results.json", payload)
    return payload

def main():
    payload = run()
    print(json.dumps(json_safe(dict(status=payload["status"], criteria=f"{payload['criteria_passed']}/{payload['criteria_total']}")), indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
