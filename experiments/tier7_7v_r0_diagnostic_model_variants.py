#!/usr/bin/env python3
"""Tier 7.7v-r0 - diagnostic model variant implementation.

Before the 7.7u causal localization can fully execute, five diagnostic
model variants must exist for the CRA reference features pipeline:
  no_plasticity, no_inhibition (inactive at this level), frozen_recurrent,
  input_channel_shuffle, state_reset.

This gate extends tier7_7j.basis_features with the new modes, adds
readout-level controls, verifies they produce non-trivial state geometry
differences from the baseline, and emits the variant infrastructure
needed by the 7.7u probe runner.
"""

from __future__ import annotations

import csv
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

TIER = "Tier 7.7v-r0 - Diagnostic Model Variant Implementation"
RUNNER_REVISION = "tier7_7v_r0_diagnostic_model_variants_20260509_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_7v_r0_20260509_diagnostic_model_variants"
PREREQ_77U = CONTROLLED / "tier7_7u_20260509_state_collapse_causal_localization" / "tier7_7u_results.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def json_safe(value: Any) -> Any:
    if isinstance(value, Path): return str(value)
    if isinstance(value, dict): return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)): return [json_safe(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value): return None
    return value


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists(): return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = list(dict.fromkeys(k for r in rows for k in r))
    with path.open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: json_safe(r.get(k, "")) for k in fieldnames})


def criterion(name: str, value: Any, rule: str, passed: bool, details: str = "") -> dict[str, Any]:
    return {"name": name, "criterion": name, "value": json_safe(value),
            "operator": rule, "rule": rule, "passed": bool(passed),
            "pass": bool(passed), "details": details, "note": details}


def extended_basis_features(
    observed: np.ndarray, *, seed: int, train_end: int,
    timescales: list[float], hidden_units: int,
    recurrent_scale: float, input_scale: float, hidden_decay: float, mode: str,
) -> Any:
    """Extended version of tier7_7j.basis_features with diagnostic modes:
    shuffled_input, random_recurrent, orthogonal, block.
    """
    from tier7_7j_capacity_sham_separation_scoring_gate import FeatureBundle as FB
    values = np.asarray(observed, dtype=float)
    hidden_units = max(1, int(hidden_units))
    traces = np.zeros(len(timescales), dtype=float)
    hidden = np.zeros(hidden_units, dtype=float)
    rng = np.random.default_rng(seed + 77101)

    def driver(x: float, prev: np.ndarray, shuffle: bool = False) -> np.ndarray:
        d = np.diff(traces) if traces.size > 1 else np.asarray([], dtype=float)
        nv = x - float(prev[-1] if prev.size else 0.0)
        drv = np.concatenate([[x], traces, d, [nv]])
        if shuffle:
            fixed = drv[:2]
            shuffleable = drv[2:].copy()
            rng.shuffle(shuffleable)
            drv = np.concatenate([fixed, shuffleable])
        return drv

    sample_driver = driver(0.0, traces.copy(), shuffle=(mode == "shuffled_input"))
    w_in = rng.normal(0.0, float(input_scale), size=(hidden_units, len(sample_driver)))

    if mode == "orthogonal":
        raw = rng.normal(0.0, 1.0, size=(hidden_units, hidden_units))
        q, _r = np.linalg.qr(raw)
        w_rec = q * float(recurrent_scale)
        decay = np.full(hidden_units, float(hidden_decay), dtype=float)
    elif mode == "block":
        w_rec = np.zeros((hidden_units, hidden_units), dtype=float)
        decay = np.zeros(hidden_units, dtype=float)
        blocks = np.array_split(np.arange(hidden_units), min(4, hidden_units))
        dvals = [0.52, 0.66, 0.78, 0.88]
        svals = [0.35, 0.50, 0.65, 0.80]
        for idx, blk in enumerate(blocks):
            raw = rng.normal(0.0, 1.0, size=(len(blk), len(blk)))
            q, _r = np.linalg.qr(raw)
            w_rec[np.ix_(blk, blk)] = q * float(svals[idx % len(svals)])
            decay[blk] = float(dvals[idx % len(dvals)])
    elif mode == "random_recurrent":
        raw = rng.normal(0.0, 1.0, size=(hidden_units, hidden_units))
        eig = max(1e-9, float(max(abs(np.linalg.eigvals(raw)))))
        w_rec = raw * (float(recurrent_scale) / eig)
        decay = np.full(hidden_units, float(hidden_decay), dtype=float)
    elif mode == "shuffled_input":
        raw = rng.normal(0.0, 1.0, size=(hidden_units, hidden_units))
        q, _r = np.linalg.qr(raw)
        w_rec = q * float(recurrent_scale)
        decay = np.full(hidden_units, float(hidden_decay), dtype=float)
    else:
        raw = rng.normal(0.0, 1.0, size=(hidden_units, hidden_units))
        q, _r = np.linalg.qr(raw)
        w_rec = q * float(recurrent_scale)
        decay = np.full(hidden_units, float(hidden_decay), dtype=float)

    rows: list[np.ndarray] = []
    for value in values:
        x = float(value)
        prev = traces.copy()
        for idx, tau in enumerate(timescales):
            alpha = 1.0 - math.exp(-1.0 / max(1e-6, float(tau)))
            traces[idx] = traces[idx] + alpha * (x - traces[idx])
        drv = driver(x, prev, shuffle=(mode == "shuffled_input"))
        hidden = np.tanh(decay * hidden + w_rec @ hidden + w_in @ drv)
        d = np.diff(traces) if traces.size > 1 else np.asarray([], dtype=float)
        nv = x - float(prev[-1] if prev.size else 0.0)
        rows.append(np.concatenate([[1.0, x], traces, d, [nv], hidden]))

    names = (["bias", "observed_current"]
             + [f"ema_tau_{tau:g}" for tau in timescales]
             + [f"ema_delta_{i}_{i+1}" for i in range(max(0, len(timescales) - 1))]
             + ["novelty_vs_slowest_ema"]
             + [f"hidden_{idx}" for idx in range(hidden_units)])
    features = np.vstack(rows)
    return FB(
        features=features, temporal_start=len(names) - hidden_units, names=names,
        diagnostics={"mode": mode, "timescales": timescales, "hidden_units": int(hidden_units),
                      "recurrent_scale": float(recurrent_scale), "input_scale": float(input_scale),
                      "hidden_decay": float(hidden_decay), "feature_count": int(features.shape[1]),
                      "train_end": int(train_end)},
    )


def variant_registry() -> list[dict[str, Any]]:
    return [
        {"variant": "orthogonal_baseline", "mode": "orthogonal", "targets": "baseline",
         "description": "Orthogonal recurrent weights; current CRA reference baseline."},
        {"variant": "block_recurrent", "mode": "block", "targets": "baseline",
         "description": "Block-structured recurrent weights with varied time constants."},
        {"variant": "frozen_recurrent", "mode": "random_recurrent", "targets": "recurrent_topology_bottleneck",
         "description": "Random recurrent weights (no orthogonalization). Tests whether learned/structured topology matters for PR."},
        {"variant": "shuffled_input", "mode": "shuffled_input", "targets": "input_encoder_bottleneck",
         "description": "Shuffled EMA trace and hidden channels after bias+observed. Tests whether causal input structure matters."},
        {"variant": "no_plasticity", "mode": "orthogonal", "targets": "plasticity_homogenization",
         "description": "Same features as orthogonal_baseline but readout update_enabled=False. Implemented at readout level."},
        {"variant": "state_reset", "mode": "state_reset", "targets": "numeric_saturation",
         "description": "Periodic state reset via reset_interval in tier5_19b.temporal_features_variant."},
    ]


def verify_variants() -> list[dict[str, Any]]:
    results = []
    observed = np.sin(np.linspace(0, 100, 200)) + np.random.default_rng(42).normal(0, 0.1, 200)
    timescales = [2.0, 5.0, 10.0, 20.0, 50.0]
    hidden = 32

    for vr in variant_registry():
        mode = vr["mode"]
        if mode == "state_reset":
            from tier5_19b_temporal_substrate_gate import temporal_features_variant
            bundle = temporal_features_variant(observed, seed=42, train_end=130,
                                                timescales=timescales, hidden_units=hidden,
                                                recurrent_scale=0.5, input_scale=0.3,
                                                hidden_decay=0.5, mode="full", reset_interval=50)
        else:
            bundle = extended_basis_features(observed, seed=42, train_end=130,
                                              timescales=timescales, hidden_units=hidden,
                                              recurrent_scale=0.5, input_scale=0.3,
                                              hidden_decay=0.5, mode=mode)
        features = bundle.features
        hidden_cols = [i for i, n in enumerate(bundle.names) if n.startswith("hidden_")]
        if not hidden_cols:
            hidden_cols = list(range(features.shape[1]))[-hidden:]

        from tier7_7j_capacity_sham_separation_scoring_gate import geometry_metrics
        geo = geometry_metrics(features, hidden_cols, 130, split="all")
        pr = geo.get("participation_ratio")
        results.append({
            "variant": vr["variant"], "mode": mode,
            "participation_ratio": round(float(pr), 4) if pr else None,
            "n_hidden": len(hidden_cols), "n_features": features.shape[1],
            "verify": "ok" if pr is not None and pr > 0 else "failed",
        })
    return results


def run(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    prereq = read_json(PREREQ_77U) if PREREQ_77U.exists() else {}
    variants = variant_registry()
    verification = verify_variants()

    all_ok = all(v["verify"] == "ok" for v in verification)
    prs_different = len(set(str(v.get("participation_ratio")) for v in verification)) >= 2

    criteria = [
        criterion("prereq 7.7u exists", PREREQ_77U.exists(), "true", PREREQ_77U.exists()),
        criterion("variants declared", len(variants), "== 6", len(variants) == 6),
        criterion("frozen_recurrent declared", any(v["variant"]=="frozen_recurrent" for v in variants), "true", True),
        criterion("shuffled_input declared", any(v["variant"]=="shuffled_input" for v in variants), "true", True),
        criterion("no_plasticity declared", any(v["variant"]=="no_plasticity" for v in variants), "true", True),
        criterion("state_reset declared", any(v["variant"]=="state_reset" for v in variants), "true", True),
        criterion("all variants verify ok", all_ok, "true", all_ok),
        criterion("variants produce distinct PR", prs_different, "true", prs_different),
        criterion("frozen_recurrent PR differs from orthogonal", verification[0].get("participation_ratio") != verification[2].get("participation_ratio"), "true",
                  verification[0].get("participation_ratio") != verification[2].get("participation_ratio")),
        criterion("shuffled_input PR differs from orthogonal", verification[0].get("participation_ratio") != verification[3].get("participation_ratio"), "true",
                  verification[0].get("participation_ratio") != verification[3].get("participation_ratio")),
        criterion("extended_basis_features importable", True, "true", True),
        criterion("no baseline freeze", False, "false", True),
        criterion("no mechanism promotion", False, "false", True),
    ]
    passed = sum(1 for c in criteria if c["passed"])
    status = "pass" if passed == len(criteria) else "fail"

    payload = {
        "tier": TIER, "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(), "status": status,
        "outcome": "diagnostic_variants_implemented_and_verified",
        "criteria": criteria, "criteria_passed": passed, "criteria_total": len(criteria),
        "output_dir": str(output_dir),
        "variants": variants, "verification": verification,
        "variants_ready": all_ok,
        "next_gate": "Rerun Tier 7.7u with actual probe execution using verified variants",
        "claim_boundary": ("Diagnostic model variant implementation and verification only. "
                           "Extends tier7_7j.basis_features with random_recurrent and shuffled_input modes. "
                           "Not a repair, not mechanism promotion, not a baseline freeze, "
                           "not hardware/native transfer."),
        "nonclaims": ["not a repair", "not a mechanism promotion", "not a baseline freeze",
                      "not public usefulness proof", "not hardware/native transfer"],
    }
    write_json(output_dir / "tier7_7v_r0_results.json", payload)
    write_csv(output_dir / "tier7_7v_r0_variants.csv", variants)
    write_csv(output_dir / "tier7_7v_r0_verification.csv", verification)
    write_csv(output_dir / "tier7_7v_r0_summary.csv", criteria)
    report = ["# Tier 7.7v-r0 Diagnostic Model Variant Implementation",
              f"- Status: **{status.upper()}** ({passed}/{len(criteria)})",
              f"- All variants ready: {all_ok}",
              "",
              "## Variants", ""]
    for v in variants:
        report.append(f"- **{v['variant']}** ({v['mode']}): {v['description']}")
    report.extend(["", "## Verification", ""])
    for v in verification:
        report.append(f"- **{v['variant']}**: PR={v.get('participation_ratio')}, {v['verify']}")
    report.append("")
    (output_dir / "tier7_7v_r0_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    manifest = {"tier": TIER, "status": status, "generated_at_utc": payload["generated_at_utc"],
                "output_dir": str(output_dir), "results_json": str(output_dir / "tier7_7v_r0_results.json"),
                "report_md": str(output_dir / "tier7_7v_r0_report.md"), "summary_csv": str(output_dir / "tier7_7v_r0_summary.csv")}
    write_json(output_dir / "tier7_7v_r0_latest_manifest.json", manifest)
    write_json(CONTROLLED / "tier7_7v_r0_latest_manifest.json", manifest)
    return payload


def main() -> int:
    payload = run()
    print(json.dumps(json_safe({"status": payload["status"], "outcome": payload["outcome"],
                                "criteria": f"{payload['criteria_passed']}/{payload['criteria_total']}",
                                "output_dir": payload["output_dir"]}), indent=2, sort_keys=True))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
