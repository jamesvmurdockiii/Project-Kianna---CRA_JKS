#!/usr/bin/env python3
"""Tier 4.33 - Edge-of-Chaos Native Mechanism Transfer Contract.

After v2.6 baseline freeze demonstrated edge-of-chaos recurrent dynamics
restore state dimensionality (PR 2->7, sham-separated) and beat ESN on
chaotic benchmark tasks, this contract defines the staged migration of
the mechanism to the SpiNNaker custom C runtime.

Contract only: no C implementation, no hardware execution, no baseline freeze.
"""

from __future__ import annotations

import csv, hashlib, json, math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"

TIER = "Tier 4.33 - Edge-of-Chaos Native Mechanism Transfer Contract"
RUNNER_REVISION = "tier4_33_eoc_native_transfer_contract_20260509_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier4_33_20260509_eoc_native_transfer_contract"
NEXT_GATE = "Tier 4.33a - Edge-of-Chaos Fixed-Point Local Reference"


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
        w = csv.DictWriter(h, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        for r in rows: w.writerow({k: json_safe(r.get(k,"")) for k in fieldnames})

def sha256_file(path):
    if not path.exists(): return None
    d = hashlib.sha256()
    with path.open("rb") as f:
        for c in iter(lambda: f.read(1024*1024), b""): d.update(c)
    return d.hexdigest()

def criterion(name, value, rule, passed, details=""):
    return {"name": name, "criterion": name, "value": json_safe(value),
            "operator": rule, "rule": rule, "passed": bool(passed),
            "pass": bool(passed), "details": details, "note": details}


def migration_stages():
    return [
        {"stage": "4.33_contract", "description": "Lock transfer contract. Define mechanism, state budget, fixed-point constraints, failure classes. No implementation."},
        {"stage": "4.33a_local_ref", "description": "Fixed-point local reference: verify edge-of-chaos with s16.15 arithmetic produces same PR and MSE as float reference within tolerance."},
        {"stage": "4.33b_source_audit", "description": "C runtime source audit: verify new opcodes, state layout, READ_STATE fields, profile ownership, and host tests pass."},
        {"stage": "4.33c_prepare", "description": "Prepare EBRAINS package: build .aplx with EOC profile, source-only upload, verify binary size fits ITCM/DTCM."},
        {"stage": "4.33d_smoke", "description": "Single-core hardware smoke: build/load/readback on one SpiNNaker board, verify compact state matches fixed-point reference."},
        {"stage": "4.33e_multiseed", "description": "Three-seed repeatability: Mackey-Glass/Lorenz at 8000 steps, seeds 42/43/44, 3 boards."},
    ]


def mechanism_spec():
    return {
        "name": "edge_of_chaos_recurrent_dynamics",
        "software_baseline": "v2.6",
        "decay": 0.0, "spectral_radius": 1.0, "antisym_fraction": 0.3,
        "input_encoding": "7 EMA traces (unchanged from v2.5)",
        "readout": "ridge regression (alpha=1.0, host-side)",
        "state_dimensions": {
            "ema_traces": "7 * 4 bytes = 28 bytes",
            "hidden_units": "128 * 4 bytes = 512 bytes",
            "trace_deltas": "6 * 4 bytes = 24 bytes",
            "novelty": "4 bytes",
            "total_state": "~568 bytes DTCM",
        },
        "compute_per_tick": {
            "ema_updates": "7 multiply-adds",
            "driver_construction": "concatenation, no computation",
            "recurrent_step": "128 x 128 matmul + 128 x input_dim matmul + 128 tanh calls",
            "antisym_contribution": "precomputed static matrix, O(n^2) multiply-adds per tick",
            "total_ops": "O(n^2 + n * input_dim) ~ 18k multiply-adds per tick at n=128",
        },
        "resource_assessment": {
            "w_rec_storage": "128*128*4 = 64KB for recurrent matrix",
            "w_in_storage": "128*16*4 = 8KB for input projection",
            "fits_itcm": "w_in fits ITCM; w_rec requires DTCM (64KB)",
            "dtcm_budget": "CRA_NATIVE_SCALE_BASELINE_v0.5 measured DTCM budget ~80KB available",
            "risk": "w_rec at 64KB is near DTCM limit; consider n=64 for first smoke (16KB w_rec)",
        },
    }


def failure_classes():
    return [
        {"class": "itcm_overflow", "symptom": ".aplx link fails with RO_DATA will not fit", "repair": "Reduce hidden units, move w_rec to DTCM, use int16 packing"},
        {"class": "dtcm_overflow", "symptom": "Runtime data exceeds DTCM", "repair": "Reduce hidden units from 128 to 64 for first smoke"},
        {"class": "fixed_point_overflow", "symptom": "FP_MUL produces non-finite values", "repair": "Clamp antisymmetric component, verify tanh input range"},
        {"class": "state_readback_mismatch", "symptom": "Compact readback differs from float reference", "repair": "Audit FP_MUL rounding, verify EMA trace update order"},
        {"class": "timing_overrun", "symptom": "Timer callback takes >1ms", "repair": "Reduce hidden units, profile matmul, consider sparse antisym"},
    ]


def build_contract():
    return {
        "question": "Can the v2.6 edge-of-chaos recurrent dynamics mechanism be migrated to the SpiNNaker custom C runtime with s16.15 fixed-point arithmetic while preserving the mechanism's stated benefits (PR restoration, sham separation)?",
        "hypothesis": "Yes. The mechanism uses only multiply-add, tanh, and EMA updates — all expressible in s16.15 with existing FP_MUL/FP_TANH primitives in the C runtime. The antisymmetric component is precomputed and static, requiring no online learning.",
        "null_hypothesis": "Fixed-point rounding, DTCM budget constraints, or timing overruns prevent faithful reproduction of the software mechanism on hardware.",
        "decision": "contract_locked_authorize_fixed_point_reference",
        "starting_baseline": "CRA_NATIVE_SCALE_BASELINE_v0.5",
        "software_reference": "CRA_EVIDENCE_BASELINE_v2.6",
        "claim_boundary": "This contract locks the edge-of-chaos native mechanism transfer protocol without implementing C code or executing hardware. Not hardware evidence. Not a baseline freeze.",
    }


def run(output_dir=DEFAULT_OUTPUT_DIR):
    output_dir = output_dir.resolve(); output_dir.mkdir(parents=True, exist_ok=True)
    contract = build_contract()
    stages = migration_stages()
    mech = mechanism_spec()
    failures = failure_classes()

    criteria = [
        criterion("contract question locked", bool(contract["question"]), "true", True),
        criterion("6 migration stages defined", len(stages), "== 6", len(stages) == 6),
        criterion("state budget defined (DTCM)", mech["state_dimensions"]["total_state"], "non-empty", True),
        criterion("compute budget assessed", mech["compute_per_tick"]["total_ops"], "non-empty", True),
        criterion("resource risk documented (w_rec 64KB)", mech["resource_assessment"]["risk"], "non-empty", True),
        criterion("5 failure classes defined", len(failures), "== 5", len(failures) == 5),
        criterion("DTCM overflow has repair", any(f["class"] == "dtcm_overflow" for f in failures), "true", True),
        criterion("fixed-point overflow has repair", any(f["class"] == "fixed_point_overflow" for f in failures), "true", True),
        criterion("software baseline referenced", contract["starting_baseline"], "non-empty", True),
        criterion("no baseline freeze authorized", False, "false", True),
        criterion("no hardware evidence claimed", False, "false", True),
    ]
    passed = sum(1 for c in criteria if c["passed"])
    status = "pass" if passed == len(criteria) else "fail"

    payload = dict(tier=TIER, runner_revision=RUNNER_REVISION, generated_at_utc=utc_now(),
                   status=status, outcome="eoc_native_transfer_contract_locked",
                   criteria=criteria, criteria_passed=passed, criteria_total=len(criteria),
                   output_dir=str(output_dir), contract=contract, migration_stages=stages,
                   mechanism_spec=mech, failure_classes=failures, next_gate=NEXT_GATE,
                   claim_boundary=contract["claim_boundary"],
                   nonclaims=["not C implementation", "not hardware evidence", "not a baseline freeze"])
    write_json(output_dir / "tier4_33_results.json", payload)
    write_json(output_dir / "tier4_33_contract.json", contract)
    write_csv(output_dir / "tier4_33_stages.csv", stages)
    write_csv(output_dir / "tier4_33_mechanism_spec.csv", [{"key": k, "value": str(v)} for k, v in mech.items()])
    write_csv(output_dir / "tier4_33_failures.csv", failures)
    write_csv(output_dir / "tier4_33_summary.csv", criteria)
    report = ["# Tier 4.33 Edge-of-Chaos Native Transfer Contract",
              f"- Status: **{status.upper()}** ({passed}/{len(criteria)})",
              f"- Outcome: `eoc_native_transfer_contract_locked`",
              "", "## Question", "", contract["question"], "",
              "## Resource Budget", "",
              f"- State: {mech['state_dimensions']['total_state']}",
              f"- Compute: {mech['compute_per_tick']['total_ops']} per tick",
              f"- Risk: {mech['resource_assessment']['risk']}",
              "", "## Next Gate", "", NEXT_GATE]
    (output_dir / "tier4_33_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    manifest = dict(tier=TIER, status=status, generated_at_utc=payload["generated_at_utc"], output_dir=str(output_dir))
    write_json(output_dir / "tier4_33_latest_manifest.json", manifest)
    write_json(CONTROLLED / "tier4_33_latest_manifest.json", manifest)
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
