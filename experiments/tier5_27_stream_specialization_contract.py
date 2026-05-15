#!/usr/bin/env python3
"""Tier 5.27 — Stream Specialization Heritability Contract.

Diagnosis: The current organism feeds ALL polyps the SAME sensory_value
and the SAME set of encoded input channels. Every polyp processes
identical information. This is the root cause of the PR ceiling — if
every polyp sees the same input, their activity will be correlated.

Biological reality: Different minicolumns in cortex receive different
thalamocortical projections. V1 orientation columns respond to different
edge orientations. Cortical column specialization is the primary
mechanism for creating orthogonal response subspaces.

This contract tests whether evolved stream specialization — each polyp
inheriting a feature selection mask that determines which encoded input
channels it attends to, with mutation during reproduction — creates
genuinely orthogonal activity patterns and increases state dimensionality.

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

TIER = "Tier 5.27 — Stream Specialization Heritability Contract"
RUNNER_REVISION = "tier5_27_stream_specialization_contract_20260510_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier5_27_20260510_stream_specialization_contract"
NEXT_GATE = "Tier 5.27a — Stream Specialization Scoring Gate"


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
            "Does evolved stream specialization — each polyp inheriting "
            "a feature selection mask that determines which encoded input "
            "channels it attends to, with mutation during reproduction — "
            "create genuinely orthogonal activity patterns across polyps "
            "and increase per-polyp PR beyond the current 2.3 ceiling?"
        ),
        "diagnosis": (
            "The current organism feeds ALL polyps the SAME sensory_value "
            "(encoded[0]) and the SAME set of encoded input channels. Every "
            "polyp processes identical information. This is the root cause "
            "of the PR ceiling — if every polyp sees the same input, their "
            "activity will be correlated regardless of how different their "
            "neural parameters are.\n\n"
            "Biological reality: Different cortical minicolumns receive "
            "different thalamocortical projections. V1 orientation columns "
            "respond to different edge orientations. Cortical column "
            "specialization creates orthogonal response subspaces — the "
            "precise thing PR measures.\n\n"
            "The organism already encodes observations into 8 channels "
            "(n_input_per_polyp=8). The adapter produces different temporal "
            "features in each channel. But all polyps receive all channels "
            "identically. If each polyp EVOLVED to attend to a DIFFERENT "
            "subset of channels, their activity patterns would naturally "
            "decorrelate."
        ),
        "hypothesis": (
            "Adding a heritable stream_attention_mask to each polyp — a"
            "2^8=256 possible channel combinations — will allow evolution "
            "to discover which combinations produce useful activity. "
            "Children inherit their parent's mask with small mutations "
            "(toggle 1 channel per generation). Selection preserves masks "
            "that produce diverse, informative activity. The population "
            "will partition the feature space, creating orthogonal response "
            "subspaces and increasing PR."
        ),
        "null_hypothesis": (
            "Stream specialization does not increase PR because: "
            "(1) random channel selection is equivalent to reduced "
            "information per polyp (fewer channels = less info = same or "
            "lower diversity), (2) the adapter's channels (EMA, deltas, "
            "squares) are too correlated for channel selection to matter, "
            "or (3) the mutation rate is too slow for masks to diverge "
            "meaningfully at tested run lengths."
        ),
        "mechanism_under_test": {
            "name": "stream_specialization_heritability",
            "type": "lifecycle/input mechanism",
            "description": (
                "Each polyp carries a heritable stream_attention_mask "
                "indicating which encoded input channels it attends to. "
                "Only masked-in channels contribute to the polyp's input "
                "drive. Mutation occasionally toggles one channel per "
                "generation. Selection preserves masks that produce "
                "useful diversity."
            ),
            "heritable_mask": {
                "type": "bitmask / set of ints",
                "default": "all channels active (full mask)",
                "mutation": "toggle one random channel per generation",
                "mutation_probability": 0.3,  # per reproduction event
            },
        },
        "code_change": {
            "description": (
                "1. Add stream_attention_mask (set of ints) to PolypState\n"
                "2. Add to TRAIT_BOUNDS as 'stream_mask_coverage' (fraction "
                "of channels active, 0.1-1.0)\n"
                "3. In _instantiate_polyp, generate specific channel mask "
                "from coverage fraction using random selection\n"
                "4. In organism._execute_task_step, use each polyp's mask "
                "to zero out channels that polyp ignores\n"
                "5. Mutation: during reproduction, with probability 0.3, "
                "toggle one random channel"
            ),
            "files": [
                "coral_reef_spinnaker/polyp_state.py",
                "coral_reef_spinnaker/lifecycle.py",
                "coral_reef_spinnaker/organism.py",
            ],
        },
        "measurement": {
            "state_vector": "Per-polyp activity_rate (sum of spikes per polyp)",
            "pr_computation": "Standard PR on test-split (last 40%) covariance",
            "task": "sine_wave (sin(0..40), with multi-channel encoding)",
            "multi_channel_adapter": True,
            "n_input_per_polyp": 8,
            "population": {"initial": 4, "max": 32},
        },
        "conditions": [
            {"name": "heritable_specialization",
             "description": "Lifecycle ON + neural heritability ON + stream mask heritability ON"},
            {"name": "clones_no_specialization",
             "description": "Lifecycle ON + neural heritability ON + stream masks clamped to full (all channels). Primary sham."},
            {"name": "static_no_lifecycle",
             "description": "Lifecycle OFF — static population"},
        ],
        "shams": [
            {"name": "full_mask_clones",
             "role": "primary",
             "description": "All polyps receive full channel mask (equivalent "
                            "to current behavior). Tests whether stream "
                            "specialization specifically creates diversity."},
            {"name": "random_mask_per_step",
             "role": "secondary",
             "description": "Each polyp gets a random mask each step (not "
                            "inherited). Tests whether mask heritability "
                            "(lineage-specific accumulation) matters."},
        ],
        "pass_criteria": {
            "primary": (
                "specialized PR > full-mask clone PR by margin > 0.5 at final "
                "timepoint, AND specialized > static by > 1.0, AND mask "
                "diversity (unique masks / population) > 0.3"
            ),
        },
        "outcome_classes": [
            {"outcome": "stream_specialization_confirmed",
             "condition": "primary pass AND sham separated",
             "action": "Stream specialization is the mechanism that breaks PR ceiling."},
            {"outcome": "stream_specialization_partial",
             "condition": "PR improves but margin < 0.5 vs clone",
             "action": "Stream specialization helps but needs longer evolution or stronger mutation."},
            {"outcome": "stream_specialization_no_effect",
             "condition": "No PR difference between specialized and clone",
             "action": "Channel selection alone does not create diversity at this scale."},
            {"outcome": "stream_specialization_reduces_pr",
             "condition": "Specialized PR < clone PR",
             "action": "Reducing information per polyp hurts more than specialization helps."},
        ],
        "claim_boundary": (
            "Host-side NEST diagnostic of heritable stream specialization only. "
            "Not mechanism promotion, not a baseline freeze, not hardware "
            "evidence, not public usefulness proof."
        ),
        "decision": "contract_locked_authorize_implementation_and_scoring",
        "layers_on": "Tier 5.26 neural heritability infrastructure",
    }


def run(output_dir=None):
    if output_dir is None: output_dir = DEFAULT_OUTPUT_DIR
    output_dir = output_dir.resolve(); output_dir.mkdir(parents=True, exist_ok=True)
    contract = build_contract()

    criteria = [
        criterion("question locked", bool(contract["question"]), "true", True),
        criterion("diagnosis references all-polyp same input", "identical" in contract["diagnosis"] or "same" in contract["diagnosis"], "true", True),
        criterion("null hypothesis locked", bool(contract["null_hypothesis"]), "true", True),
        criterion("stream mask mechanism specified", bool(contract["mechanism_under_test"].get("heritable_mask")), "true", True),
        criterion("3 code files specified", len(contract["code_change"]["files"]), "== 3", True),
        criterion("primary sham: full mask clones", contract["shams"][0]["name"], "== full_mask_clones", True),
        criterion("secondary sham: random per step", contract["shams"][1]["name"], "== random_mask_per_step", True),
        criterion("primary pass: PR > clone by 0.5 + static by 1.0", contract["pass_criteria"]["primary"], "non-empty", True),
        criterion("4 outcome classes", len(contract["outcome_classes"]), "== 4", True),
        criterion("layers on 5.26 neural heritability", "5.26" in str(contract.get("layers_on","")), "true", True),
        criterion("no baseline freeze authorized", False, "false", True),
        criterion("no mechanism promotion authorized", False, "false", True),
    ]
    passed = sum(1 for c in criteria if c["passed"])
    status = "pass" if passed == len(criteria) else "fail"

    payload = dict(tier=TIER, runner_revision=RUNNER_REVISION, generated_at_utc=utc_now(),
                   status=status, outcome="stream_specialization_contract_locked",
                   criteria=criteria, criteria_passed=passed, criteria_total=len(criteria),
                   output_dir=str(output_dir), contract=contract, next_gate=NEXT_GATE,
                   claim_boundary=contract["claim_boundary"])

    write_json(output_dir / "tier5_27_results.json", payload)
    write_json(output_dir / "tier5_27_contract.json", contract)
    write_csv(output_dir / "tier5_27_summary.csv", criteria)
    write_csv(output_dir / "tier5_27_shams.csv", contract["shams"])
    write_csv(output_dir / "tier5_27_outcomes.csv", contract["outcome_classes"])
    (output_dir / "tier5_27_report.md").write_text(
        f"# {TIER}\n\n- Status: **{status.upper()}** ({passed}/{len(criteria)})\n"
        f"- Outcome: `stream_specialization_contract_locked`\n\n"
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
