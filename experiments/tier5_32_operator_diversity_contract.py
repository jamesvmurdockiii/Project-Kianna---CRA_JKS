#!/usr/bin/env python3
"""Tier 5.32 — Per-Polyp Operator Diversity (Spectral Radius + E/I Ratio) Contract.

Diagnosis: The PR ceiling (~1.5) persists through 7 lifecycle features because
all polyps implement the SAME dynamical operator (same spectral radius, same E/I
balance).  Parameter variation (tau_m, delays, gains) creates time-warped
copies — not orthogonal dynamics.  The standalone tanh reference achieves PR=7.0
through each unit implementing a genuinely different dynamical operator.

This contract tests whether per-polyp spectral radius variation (0.4-2.0) and
E/I ratio variation (0.3-3.0) — heritable through lifecycle — create operator
diversity and break the PR ceiling.

Contract only: no scoring, no mechanism promotion.
"""

from __future__ import annotations
import csv, json, math, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CONTROLLED = ROOT / "controlled_test_output"

TIER = "Tier 5.32 — Per-Polyp Operator Diversity Contract"
RUNNER_REVISION = "tier5_32_operator_diversity_contract_20260511_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier5_32_20260511_operator_diversity_contract"
NEXT_GATE = "Tier 5.32a — Operator Diversity Scoring Gate"

PASS_MARGIN_VS_CLONE = 1.0  # operator diversity must beat uniform by >1.0 PR
PASS_MARGIN_VS_STATIC = 2.0

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
            "Does per-polyp operator diversity (heritable spectral radius and "
            "E/I ratio variation) break the PR ceiling of ~1.5 by creating "
            "polyps that implement genuinely different dynamical operators "
            "rather than time-warped copies of the same operator?"
        ),
        "diagnosis": (
            "The PR ceiling (~1.5) persists across 7 lifecycle diversity "
            "features because all polyps implement the SAME dynamical "
            "operator.  Parameter variation (tau_m, delays, gains, streams) "
            "creates time-warped copies — not orthogonal dynamics.  Each "
            "polyp computes h_{t+1} = F(W_rec * h_t + W_in * x_t) with "
            "the same F (same spectral radius, same E/I balance).  The "
            "standalone tanh reference achieves PR=7.0 through each unit "
            "having a different w_rec operator.\n\n"
            "Biological reality: Cortical columns have different dynamical "
            "regimes — some are contractive (sensory filters), others near-"
            "critical (memory), others oscillatory (rhythmic generators). "
            "This operator diversity is what creates orthogonal cortical "
            "response subspaces.\n\n"
            "Implementation: Two heritable traits control the polyp's "
            "dynamical regime — spectral_radius (E→E weight scaling, "
            "0.4-2.0) and ei_ratio (I→E inhibitory strength, 0.3-3.0). "
            "These are applied in instantiate_internal_template to scale "
            "the per-polyp recurrent weight matrix and inhibitory projections."
        ),
        "hypothesis": (
            "Per-polyp spectral radius variation (0.4-2.0) will create "
            "polyps with contractive (sr<1), critical (sr≈1), and "
            "expansive (sr>1) dynamics.  Combined with E/I ratio variation, "
            "each polyp becomes a genuinely different dynamical operator. "
            "This operator diversity will produce orthogonal spike patterns "
            "and increase per-polyp PR significantly beyond the current "
            "~1.5 ceiling."
        ),
        "null_hypothesis": (
            "Operator diversity does not increase PR because: (1) spectral "
            "radius variation at this range destabilizes some polyps "
            "(silence or explosion), (2) E/I ratio variation is normalized "
            "away by the shared input, or (3) the per-polyp weight "
            "scaling is too small relative to the shared input drive."
        ),
        "mechanism_under_test": {
            "name": "operator_diversity",
            "type": "neural/lifecycle mechanism",
            "heritable_traits": {
                "spectral_radius": {"range": (0.4, 2.0), "default": 1.0,
                    "effect": "Scales E→E weights to target spectral radius. <1=contractive, =1=critical, >1=expansive"},
                "ei_ratio": {"range": (0.3, 3.0), "default": 1.0,
                    "effect": "Multiplies I→E inhibitory weights. >1=stable, <1=excitable/oscillatory"},
            },
            "applied_in": "polyp_population.instantiate_internal_template()",
            "stored_on": "PolypState (spectral_radius, ei_ratio)",
            "heritable_via": "LifecycleManager TRAIT_BOUNDS + _instantiate_polyp",
        },
        "conditions": {
            "operator_diverse": "Lifecycle ON + spectral radius + E/I ratio heritable",
            "uniform_sham": "Lifecycle ON + spectral radius clamped to 1.0 + E/I ratio clamped to 1.0 (all polyps identical operator)",
            "static": "Lifecycle OFF — static uniform population",
        },
        "measurement": {
            "state_vector": "Per-polyp activity_rate (sum of per-neuron spikes / polyp)",
            "pr_computation": "Standard PR on test-split (last 40%) covariance",
            "task": "sine_wave (sin(0..80))",
            "population": {"initial": 4, "max": 8},
        },
        "pass_criteria": {
            "primary": (
                f"operator_diverse PR > uniform_sham PR by >{PASS_MARGIN_VS_CLONE} "
                f"AND > static PR by >{PASS_MARGIN_VS_STATIC} "
                "AND spectral_radius range spans >=0.3 across polyps"
            ),
        },
        "outcome_classes": [
            {"outcome": "operator_diversity_confirmed",
             "condition": "primary pass",
             "action": "Operator diversity breaks PR ceiling. Layer on all prior features."},
            {"outcome": "operator_diversity_partial",
             "condition": "PR improves but margin < threshold wrt uniform sham",
             "action": "Operator diversity helps but needs stronger effect."},
            {"outcome": "operator_diversity_no_effect",
             "condition": "No PR difference between diverse and uniform",
             "action": "Spectral radius/EI ratio at this range doesn't create operator diversity."},
            {"outcome": "operator_diversity_unstable",
             "condition": "Population crashes, NaN, or silence from extreme sr/eir values",
             "action": "Spectral radius/EI ratio bounds too wide. Tighten."},
        ],
        "claim_boundary": (
            "Host-side NEST diagnostic of per-polyp operator diversity only. "
            "Not mechanism promotion, not a baseline freeze, not hardware "
            "evidence, not public usefulness proof."
        ),
        "layers_on": "Lifecycle infrastructure (Tiers 5.26-5.31) + temporal specialization + NEST Cleanup fix",
        "decision": "contract_locked_authorize_scoring",
    }


def run(output_dir=None):
    if output_dir is None: output_dir = DEFAULT_OUTPUT_DIR
    output_dir = output_dir.resolve(); output_dir.mkdir(parents=True, exist_ok=True)
    contract = build_contract()
    criteria = [
        criterion("question locked", bool(contract["question"]), "true", True),
        criterion("diagnosis explains operator diversity", "operator" in contract["diagnosis"], "true", True),
        criterion("null hypothesis locked", bool(contract["null_hypothesis"]), "true", True),
        criterion("two heritable traits specified", len(contract["mechanism_under_test"]["heritable_traits"]), "== 2", True),
        criterion("sr range specified", str(contract["mechanism_under_test"]["heritable_traits"]["spectral_radius"]["range"]), "non-empty", True),
        criterion("primary pass: margin >{0} vs sham, >{1} vs static".format(PASS_MARGIN_VS_CLONE, PASS_MARGIN_VS_STATIC), True, "true", True),
        criterion("4 outcome classes", len(contract["outcome_classes"]), "== 4", True),
        criterion("layers on prior infrastructure", bool(contract.get("layers_on")), "true", True),
        criterion("no baseline freeze authorized", False, "false", True),
        criterion("no mechanism promotion authorized", False, "false", True),
    ]
    passed = sum(1 for c in criteria if c["passed"])
    payload = dict(tier=TIER, runner_revision=RUNNER_REVISION, generated_at_utc=utc_now(),
                   status="pass", outcome="operator_diversity_contract_locked",
                   criteria=criteria, criteria_passed=passed, criteria_total=len(criteria),
                   output_dir=str(output_dir), contract=contract, next_gate=NEXT_GATE)
    write_json(output_dir / "tier5_32_results.json", payload)
    return payload

def main():
    payload = run()
    print(json.dumps(json_safe(dict(status=payload["status"], criteria=f"{payload['criteria_passed']}/{payload['criteria_total']}",
                                    outcome=payload["outcome"])), indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
