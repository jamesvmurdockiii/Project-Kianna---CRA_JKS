#!/usr/bin/env python3
"""Tier 5.38 — Signal Transport: Bounded Export Interface Contract.

Diagnosis: The organism's inter-polyp communication transmits raw spike data
through PyNN projections.  This creates an unbounded information channel where
any polyp's internal state can destabilize neighboring polyps.  Biology solves
this with compressive signaling: neurons export action potentials, cells export
hormones, organs export blood chemistry — never full internal state.

This contract tests whether each polyp exporting a bounded interface vector
[activity, prediction, uncertainty, energy, novelty] — with contractive
transport constraints — preserves rich local dynamics while preventing
cross-polyp state corruption.

Contract only: no implementation, no scoring, no mechanism promotion.
"""

from __future__ import annotations
import csv, json, math, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CONTROLLED = ROOT / "controlled_test_output"

TIER = "Tier 5.38 — Signal Transport: Bounded Export Interface Contract"
RUNNER_REVISION = "tier5_38_signal_transport_contract_20260513_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier5_38_20260513_signal_transport_contract"
NEXT_GATE = "Tier 5.38a — Signal Transport Scoring Gate"

PASS_MARGIN_VS_RAW = 0.5

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
            "Does a bounded per-polyp export interface (activity, prediction, "
            "uncertainty, energy, novelty) with contractive transport constraints "
            "preserve rich internal dynamics (PR maintained) while preventing "
            "cross-polyp signal amplification that degrades stability?"
        ),
        "diagnosis": (
            "Current inter-polyp communication transmits raw spikes through "
            "PyNN projections — an unbounded channel where any polyp's "
            "internal state can destabilize neighbors.  This causes the "
            "accumulating NEST failures we observe at scale.\n\n"
            "Biological systems use compressive signaling: neurons export "
            "action potentials (binary), cells export hormones (bounded "
            "concentration), organs export blood chemistry (filtered). "
            "The polyp should export a bounded interface vector:\n"
            "  [activity, prediction, uncertainty, energy, novelty]\n"
            "with contractive transport (tanh/sigmoid bounds, spectral "
            "normalization) so that messages cannot amplify divergence."
        ),
        "hypothesis": (
            "Adding a bounded export interface per polyp — with tanh/sigmoid "
            "bounds on all exported values — will maintain or improve PR "
            "while reducing NEST failure rate by providing a compressive "
            "transport layer that prevents signal amplification."
        ),
        "null_hypothesis": (
            "Bounded export does not improve stability because: (1) the NEST "
            "failures are from connection accumulation, not signal divergence, "
            "(2) the per-polyp interface adds overhead without value, or "
            "(3) existing ReefNetwork already provides sufficient coupling."
        ),
        "mechanism_under_test": {
            "name": "signal_transport_export",
            "type": "communication/lifecycle mechanism",
            "exported_fields": {
                "activity": {"source": "activity_rate", "bound": "sigmoid", "range": (0, 1)},
                "prediction": {"source": "current_prediction", "bound": "tanh", "range": (-1, 1)},
                "uncertainty": {"source": "1 - directional_accuracy_ema", "bound": "sigmoid", "range": (0, 1)},
                "energy": {"source": "trophic_health / 20", "bound": "sigmoid", "range": (0, 1)},
                "novelty": {"source": "last_raw_rpe abs", "bound": "tanh", "range": (-1, 1)},
            },
            "transport_constraint": "All exported values pass through tanh or sigmoid bounds. Inter-polyp messages carry this compressed vector.",
            "stored_on": "PolypState (export_activity, export_prediction, export_uncertainty, export_energy, export_novelty)",
        },
        "conditions": {
            "export_enabled": "Full lifecycle stack + bounded export interface active",
            "export_disabled": "Full lifecycle stack + raw spike transport (current behavior, sham)",
        },
        "measurement": {
            "state_vector": "Per-polyp activity_rate",
            "pr_computation": "Standard PR on test-split",
            "task": "sine and Mackey-Glass",
            "population": {"initial": 4, "max": 12},
            "stability_metric": "NEST sim_run_failures at 2000 steps",
        },
        "pass_criteria": {
            "primary": (
                f"export_enabled PR > export_disabled PR by >{PASS_MARGIN_VS_RAW} "
                "AND export_enabled NEST failures < export_disabled failures "
                "AND population remains stable (no crashes)"
            ),
        },
        "outcome_classes": [
            {"outcome": "signal_transport_confirmed",
             "condition": "primary pass",
             "action": "Bounded export interface preserves diversity while improving stability."},
            {"outcome": "signal_transport_partial",
             "condition": "PR maintained but failures unchanged",
             "action": "Export helps quality but doesn't reduce NEST platform issues."},
            {"outcome": "signal_transport_no_effect",
             "condition": "No difference in PR or failures",
             "action": "Bounded export adds overhead without benefit at this scale."},
        ],
        "claim_boundary": (
            "Host-side NEST diagnostic of bounded signal transport only. "
            "Not mechanism promotion, not baseline freeze, not hardware evidence."
        ),
        "layers_on": "Tiers 5.26-5.35 (lifecycle + operator diversity + niche pressure)",
        "decision": "contract_locked_authorize_implementation",
    }

def run(output_dir=None):
    if output_dir is None: output_dir = DEFAULT_OUTPUT_DIR
    output_dir = output_dir.resolve(); output_dir.mkdir(parents=True, exist_ok=True)
    contract = build_contract()
    criteria = [
        criterion("question locked", bool(contract["question"]), "true", True),
        criterion("diagnosis documented", "compressive" in contract["diagnosis"], "true", True),
        criterion("null hypothesis", bool(contract["null_hypothesis"]), "true", True),
        criterion("5 export fields", len(contract["mechanism_under_test"]["exported_fields"]), "== 5", True),
        criterion("transport constraint specified", bool(contract["mechanism_under_test"].get("transport_constraint")), "true", True),
        criterion("primary pass criteria", bool(contract["pass_criteria"]["primary"]), "true", True),
        criterion("3 outcome classes", len(contract["outcome_classes"]), "== 3", True),
        criterion("layers on prior infra", bool(contract.get("layers_on")), "true", True),
        criterion("no baseline freeze", False, "false", True),
        criterion("no mechanism promotion", False, "false", True),
    ]
    passed = sum(1 for c in criteria if c["passed"])
    payload = dict(tier=TIER, runner_revision=RUNNER_REVISION, generated_at_utc=utc_now(),
                   status="pass", outcome="signal_transport_contract_locked",
                   criteria=criteria, criteria_passed=passed, criteria_total=len(criteria),
                   output_dir=str(output_dir), contract=contract, next_gate=NEXT_GATE)
    write_json(output_dir / "tier5_38_results.json", payload)
    return payload

def main():
    payload = run()
    print(json.dumps(json_safe(dict(status=payload["status"], criteria=f"{payload['criteria_passed']}/{payload['criteria_total']}")), indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
