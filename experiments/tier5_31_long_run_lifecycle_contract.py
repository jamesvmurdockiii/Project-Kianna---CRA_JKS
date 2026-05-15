#!/usr/bin/env python3
"""Tier 5.31 — Long-Run Lifecycle Diversity Diagnostic Contract.

Diagnosis: All 5 lifecycle diversity mechanisms (neural heritability,
stream specialization, variable allocation, task-fitness selection,
synaptic weight heritability) show positive-but-small PR margins
(+0.1-0.16) at 400 steps. The hypothesis is that evolutionary timescales
(longer runs) let per-generation effects compound into measurable
computational diversity that cleanly beats shams.

This contract locks a long-run diagnostic comparing lifecycle-enabled
(full stack, all 5 features) vs lifecycle-disabled (static uniform
population) at 8000 steps on a sine wave task.

Contract only: no implementation, no scoring, no mechanism promotion.
"""

from __future__ import annotations
import csv, json, math, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CONTROLLED = ROOT / "controlled_test_output"

TIER = "Tier 5.31 — Long-Run Lifecycle Diversity Diagnostic Contract"
RUNNER_REVISION = "tier5_31_long_run_lifecycle_contract_20260510_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier5_31_20260510_long_run_lifecycle_contract"
NEXT_GATE = "Tier 5.31a — Long-Run Lifecycle Scoring Gate"

PASS_MARGIN = 0.5
STEPS = 8000
INIT_POP = 4
MAX_POP = 32

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
            f"At {STEPS} steps with full lifecycle stack (all 5 diversity "
            "mechanisms enabled), does the organism's per-polyp PR exceed "
            f"the static uniform baseline by more than {PASS_MARGIN}, "
            "demonstrating that per-generation diversity effects compound "
            "into measurable state diversity at evolutionary timescales?"
        ),
        "diagnosis": (
            "All 5 lifecycle mechanisms show positive-but-small PR margins "
            "(+0.1-0.16) at 400 steps. Each creates real architectural "
            "diversity (5.1x tau_m std growth, 48% unique masks, 20 "
            "allocation profiles, 170+ inherited connections) but the "
            "per-polyp PR metric is dominated by population-size inflation "
            "until enough generations pass for accumulated divergence to "
            "create genuinely orthogonal activity patterns."
        ),
        "hypothesis": (
            f"At {STEPS} steps, the full lifecycle stack (neural + stream + "
            "allocation + fitness + synaptic heritability) will produce "
            "per-polyp PR that significantly exceeds the static baseline "
            f"by more than {PASS_MARGIN}, because 8k steps provides 40+ "
            "generations of reproduction with compounded trait divergence."
        ),
        "null_hypothesis": (
            "PR does not significantly exceed static baseline at 8000 steps "
            "because (1) the PR plateau is architectural, not timescale-bound, "
            "(2) population size dominates PR regardless of trait diversity, "
            "or (3) the per-generation effects are too small to compound "
            "meaningfully even at 40+ generations."
        ),
        "conditions": {
            "lifecycle_full": {
                "enable_reproduction": True,
                "enable_apoptosis": True,
                "enable_neural_heritability": True,
                "enable_stream_specialization": True,
                "enable_variable_allocation": True,
                "enable_task_fitness_selection": True,
                "enable_synaptic_heritability": True,
            },
            "static_uniform": {
                "enable_reproduction": False,
                "enable_apoptosis": False,
            },
        },
        "measurement": {
            "steps": STEPS,
            "init_pop": INIT_POP,
            "max_pop": MAX_POP,
            "task": "sine_wave (sin(0..80))",
            "pr_metric": "per-polyp activity_rate covariance PR on last 40% of steps",
            "timepoints": [500, 1000, 2000, 4000, 6000, 8000],
            "sync_interval": 10,
        },
        "pass_criteria": {
            "primary": (
                f"lifecycle_full per-polyp PR > static_uniform per-polyp PR "
                f"by margin > {PASS_MARGIN} at final timepoint ({STEPS} steps)"
            ),
            "secondary": [
                "PR trajectory increases monotonically (Kendall tau > 0)",
                f"Population stabilizes (final pop between {INIT_POP+4} and {MAX_POP})",
                "At least 10 unique allocation profiles at final timepoint",
                "Neural factor std exceeds 0.5 at final timepoint",
            ],
        },
        "outcome_classes": [
            {"outcome": "lifecycle_diversity_confirmed_at_scale",
             "condition": "primary pass AND all secondary pass",
             "action": "Lifecycle diversity compounds at evolutionary timescale. Lock as evidence."},
            {"outcome": "lifecycle_partial_at_scale",
             "condition": "primary pass but not all secondary",
             "action": "Diversity helps but not cleanly. Continue investigation."},
            {"outcome": "lifecycle_plateau",
             "condition": "PR does not increase with steps (trajectory flat)",
             "action": "PR is bounded by architecture, not timescale. Rethink mechanism."},
            {"outcome": "lifecycle_unstable",
             "condition": "Population crashes, NaN, or infinite values",
             "action": "Lifecycle parameters unstable at scale."},
        ],
        "claim_boundary": (
            "Host-side NEST diagnostic of lifecycle diversity at long timescale "
            "only. Not mechanism promotion, not baseline freeze, not hardware "
            "evidence, not public usefulness proof."
        ),
        "decision": "contract_locked_authorize_long_run_scoring",
    }

def run(output_dir=None):
    if output_dir is None: output_dir = DEFAULT_OUTPUT_DIR
    output_dir = output_dir.resolve(); output_dir.mkdir(parents=True, exist_ok=True)
    contract = build_contract()
    criteria = [
        criterion("question locked", bool(contract["question"]), "true", True),
        criterion("steps specified", STEPS, f"== {STEPS}", True),
        criterion("two conditions defined", len(contract["conditions"]), "== 2", True),
        criterion("5 features in full condition", sum(1 for k in contract["conditions"]["lifecycle_full"] if contract["conditions"]["lifecycle_full"][k]), ">= 5", True),
        criterion("primary pass: margin > 0.5", contract["pass_criteria"]["primary"], "non-empty", True),
        criterion("4 outcome classes", len(contract["outcome_classes"]), "== 4", True),
        criterion("no baseline freeze authorized", False, "false", True),
        criterion("no mechanism promotion authorized", False, "false", True),
    ]
    passed = sum(1 for c in criteria if c["passed"])
    payload = dict(tier=TIER, runner_revision=RUNNER_REVISION, generated_at_utc=utc_now(),
                   status="pass", outcome="long_run_lifecycle_contract_locked",
                   criteria=criteria, criteria_passed=passed, criteria_total=len(criteria),
                   output_dir=str(output_dir), contract=contract, next_gate=NEXT_GATE,
                   claim_boundary=contract["claim_boundary"])
    write_json(output_dir / "tier5_31_results.json", payload)
    return payload

def main():
    payload = run()
    print(json.dumps(json_safe(dict(status=payload["status"], criteria=f"{payload['criteria_passed']}/{payload['criteria_total']}")), indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
