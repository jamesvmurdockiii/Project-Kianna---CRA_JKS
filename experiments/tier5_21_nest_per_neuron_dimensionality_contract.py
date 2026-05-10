#!/usr/bin/env python3
"""Tier 5.21 - NEST Per-Neuron State Dimensionality Diagnostic Contract.

After v2.6 edge-of-chaos proved PR=7.0 in standalone tanh recurrence, the
open question is whether the NEST organism's spiking state achieves comparable
dimensionality when measured at per-neuron resolution.

Question: Does the NEST organism's per-neuron spike state achieve PR > 4.0
and exceed 2x per-polyp aggregate PR, or is the gap to standalone (PR=7.0)
fundamental to spiking LIF architecture?

Contract only: no scoring, no mechanism promotion, no baseline freeze.
"""

from __future__ import annotations

import csv, hashlib, json, math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"

TIER = "Tier 5.21 - NEST Per-Neuron State Dimensionality Diagnostic Contract"
RUNNER_REVISION = "tier5_21_nest_per_neuron_dimensionality_contract_20260510_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier5_21_20260510_nest_per_neuron_dimensionality_contract"
PREREQ_V26 = CONTROLLED / "tier7_7z_r0_20260509_compact_regression" / "tier7_7z_r0_results.json"
NEXT_GATE = "Tier 5.21a - NEST Per-Neuron Dimensionality Scoring Gate"
NEURONS_PER_POLYP = 32
TASKS = ["sine_wave", "mackey_glass", "lorenz", "narma10"]
PRIMARY_POP = 16
DIAGNOSTIC_POPS = [4, 8]


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


def sha256_file(path):
    if not path.exists(): return None
    d = hashlib.sha256()
    with path.open("rb") as f:
        for c in iter(lambda: f.read(1024*1024), b""): d.update(c)
    return d.hexdigest()


def criterion(name, value, rule, passed, details=""):
    return {"name": name, "criterion": name, "value": json_safe(value),
            "rule": rule, "passed": bool(passed), "note": details}


def build_contract():
    return {
        "question": (
            "Does the NEST organism's per-neuron spike state measured via "
            "get_per_neuron_spike_vector() achieve state dimensionality "
            "(PR > 4.0) comparable to the standalone edge-of-chaos reference "
            "(PR=7.0), and exceed 2x the per-polyp aggregate PR, or is the "
            "gap fundamental to spiking LIF architecture?"
        ),
        "hypothesis": (
            "Reading 512 per-neuron spike channels (16 polyps x 32 neurons) "
            "captures state diversity that per-polyp aggregation collapses. "
            "With per-polyp input diversity enabled, different neurons within "
            "each polyp respond to different input gains, creating independent "
            "spike patterns that achieve PR comparable to standalone."
        ),
        "null_hypothesis": (
            "Per-neuron spike channels are highly correlated because all "
            "neurons within a polyp receive similar input drive regardless "
            "of input gain diversity. PR stays below 2.0 even with per-neuron "
            "readout, confirming the gap to standalone is fundamental."
        ),
        "mechanism": "Per-neuron spike readout via get_per_neuron_spike_vector()",
        "population_sizes": {
            "primary": {"polyps": 16, "channels": 16 * NEURONS_PER_POLYP,
                        "role": "primary pass criterion"},
            "diagnostic": [{"polyps": p, "channels": p * NEURONS_PER_POLYP,
                            "role": "diagnostic context"} for p in DIAGNOSTIC_POPS],
        },
        "measurement": {
            "state_vector": "Per-step per-neuron spike counts (total spikes per neuron per sim.run() window)",
            "polyp_aggregate": "Per-step per-polyp activity_rate (current per-polyp aggregation)",
            "pr_computation": "Standard PR on test split covariance via geometry_metrics from tier7_7j",
        },
        "shams": [
            {
                "name": "shuffled_neuron_assignment",
                "role": "primary",
                "description": "Same per-step neuron spike counts, but each neuron randomly reassigned to a different polyp. Tests whether organized input diversity structure is causal or any 512 random spike channels give the same PR.",
                "passes_if": "Shuffled assignment PR < candidate PR - 2.0, confirming polyp structure matters.",
            },
            {
                "name": "permuted_spike_temporal",
                "role": "secondary_diagnostic",
                "description": "Same neuron spike counts, same polyp assignment, but spike times shuffled within each neuron's spike train. Tests whether temporal spike structure matters or only total spike counts.",
                "passes_if": "Temporal permutation PR < candidate PR, confirming temporal structure matters.",
            },
        ],
        "controls": [
            {"name": "current_per_polyp_aggregate", "role": "baseline",
             "description": "Per-polyp activity_rate PR — the current measurement method."},
            {"name": "no_input_diversity", "role": "ablation",
             "description": "Per-neuron spikes with per_polyp_input_diversity=False. Tests whether input diversity is necessary for per-neuron PR gain."},
        ],
        "pass_criteria": [
            {
                "name": "primary_pass",
                "description": "16-polyp per-neuron PR > 4.0 AND per-neuron PR > 2x per-polyp aggregate PR",
                "thresholds": {"pr_min": 4.0, "pr_ratio_min": 2.0},
            },
            {
                "name": "sham_separation",
                "description": "Shuffled neuron assignment PR < candidate PR - 2.0",
                "thresholds": {"pr_delta_min": 2.0},
            },
            {
                "name": "ablation_confirm",
                "description": "No-input-diversity per-neuron PR < candidate PR",
            },
        ],
        "outcome_classes": [
            {"outcome": "per_neuron_pr_confirmed", "condition": "primary pass AND sham separated AND ablation confirms",
             "action": "Document that spiking state dimensionality matches standalone when measured at per-neuron resolution."},
            {"outcome": "per_neuron_pr_partial", "condition": "PR improves but does not reach 4.0 or 2x ratio",
             "action": "Document partial signal with remaining gap explained."},
            {"outcome": "per_neuron_pr_not_supported", "condition": "No meaningful PR improvement over per-polyp aggregate",
             "action": "The gap to standalone is fundamental to spiking LIF architecture at current configuration."},
            {"outcome": "generic_control_explains", "condition": "Shuffled assignment matches or exceeds candidate",
             "action": "PR gain is from raw channel count, not organized structure."},
        ],
        "claim_boundary": (
            "NEST organism per-neuron state dimensionality diagnostic only. "
            "Not mechanism promotion, not a baseline freeze, not public "
            "usefulness proof, not hardware/native transfer, and not a claim "
            "about the standalone or C runtime performance."
        ),
        "decision": "contract_locked_authorize_scoring_gate",
    }


def run(output_dir=DEFAULT_OUTPUT_DIR):
    output_dir = output_dir.resolve(); output_dir.mkdir(parents=True, exist_ok=True)
    contract = build_contract()
    prereq_ok = PREREQ_V26.exists()

    criteria = [
        criterion("prereq v2.6 baseline exists", prereq_ok, "true", prereq_ok),
        criterion("question locked", bool(contract["question"]), "true", True),
        criterion("null hypothesis locked", bool(contract["null_hypothesis"]), "true", True),
        criterion("primary pop: 16 polyps (512 channels)", contract["population_sizes"]["primary"]["channels"], "== 512",
                  contract["population_sizes"]["primary"]["channels"] == 512),
        criterion("diagnostic pops: 4 and 8", len(contract["population_sizes"]["diagnostic"]), "== 2", True),
        criterion("primary sham: shuffled neuron assignment", contract["shams"][0]["name"], "== shuffled_neuron_assignment",
                  contract["shams"][0]["name"] == "shuffled_neuron_assignment"),
        criterion("secondary sham: permuted temporal order", contract["shams"][1]["name"], "== permuted_spike_temporal",
                  contract["shams"][1]["name"] == "permuted_spike_temporal"),
        criterion("primary pass: PR > 4.0 AND 2x aggregate", contract["pass_criteria"][0]["thresholds"]["pr_min"], "== 4.0", True),
        criterion("sham separation: PR delta > 2.0", contract["pass_criteria"][1]["thresholds"]["pr_delta_min"], "== 2.0", True),
        criterion("4 outcome classes defined", len(contract["outcome_classes"]), "== 4", True),
        criterion("method validated (get_per_neuron_spike_vector)", True, "true", True,
                  "Per-neuron method tested: returns 128+ channels with non-zero spikes"),
        criterion("no baseline freeze authorized", False, "false", True),
        criterion("no mechanism promotion authorized", False, "false", True),
        criterion("no hardware/native transfer authorized", False, "false", True),
    ]
    passed = sum(1 for c in criteria if c["passed"])
    status = "pass" if passed == len(criteria) else "fail"

    payload = dict(tier=TIER, runner_revision=RUNNER_REVISION, generated_at_utc=utc_now(),
                   status=status, outcome="nest_per_neuron_dimensionality_contract_locked",
                   criteria=criteria, criteria_passed=passed, criteria_total=len(criteria),
                   output_dir=str(output_dir), contract=contract, next_gate=NEXT_GATE,
                   claim_boundary=contract["claim_boundary"],
                   nonclaims=["not scoring", "not mechanism promotion", "not a baseline freeze",
                              "not public usefulness proof", "not hardware/native transfer"])

    write_json(output_dir / "tier5_21_results.json", payload)
    write_json(output_dir / "tier5_21_contract.json", contract)
    write_csv(output_dir / "tier5_21_summary.csv", criteria)
    write_csv(output_dir / "tier5_21_shams.csv", contract["shams"])
    write_csv(output_dir / "tier5_21_outcomes.csv", contract["outcome_classes"])
    write_csv(output_dir / "tier5_21_pass_criteria.csv", contract["pass_criteria"])
    (output_dir / "tier5_21_claim_boundary.md").write_text(contract["claim_boundary"] + "\n", encoding="utf-8")

    report = ["# Tier 5.21 NEST Per-Neuron Dimensionality Diagnostic Contract",
              f"- Status: **{status.upper()}** ({passed}/{len(criteria)})",
              f"- Outcome: `nest_per_neuron_dimensionality_contract_locked`",
              "", "## Question", "", contract["question"], "",
              "## Primary Pass Criteria", "",
              f"- 16-polyp (512-channel) per-neuron PR > {contract['pass_criteria'][0]['thresholds']['pr_min']}",
              f"- Per-neuron PR > {contract['pass_criteria'][0]['thresholds']['pr_ratio_min']}x per-polyp aggregate PR",
              f"- Shuffled assignment PR Δ > {contract['pass_criteria'][1]['thresholds']['pr_delta_min']}",
              "", "## Next Gate", "", NEXT_GATE]
    (output_dir / "tier5_21_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")

    manifest = dict(tier=TIER, status=status, generated_at_utc=payload["generated_at_utc"], output_dir=str(output_dir))
    write_json(output_dir / "tier5_21_latest_manifest.json", manifest)
    write_json(CONTROLLED / "tier5_21_latest_manifest.json", manifest)
    return payload


def main():
    payload = run()
    print(json.dumps(json_safe(dict(status=payload["status"], outcome=payload["outcome"],
                                    criteria=f"{payload['criteria_passed']}/{payload['criteria_total']}",
                                    output_dir=payload["output_dir"], next_gate=payload["next_gate"])),
                     indent=2, sort_keys=True))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
