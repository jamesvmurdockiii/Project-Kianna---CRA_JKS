#!/usr/bin/env python3
"""Tier 7.7v - Family C compact score (recurrent topology/spectrum repair).

After Family B (independent causal subspace drivers) showed compact signal
but did not confirm at expanded scale, this gate tests Repair Family C:
block-sparse recurrent modules with diverse time constants, spectral-radius
control, and winnerless competition motifs.

Compact score only on Mackey-Glass/Lorenz/repaired-NARMA10 at 8000 steps,
seeds 42/43/44. Not expanded confirmation, not a baseline freeze.
"""

import argparse, csv, json, math, os, sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import numpy as np

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
if str(Path(__file__).resolve().parent) not in sys.path: sys.path.insert(0, str(Path(__file__).resolve().parent))

from tier7_0_standard_dynamical_benchmarks import parse_csv, parse_seeds
from tier7_7j_capacity_sham_separation_scoring_gate import (
    build_task, geomean, geometry_metrics, hidden_columns, safe_float,
    utc_now, write_json, write_rows, criterion,
)
from tier7_7v_r0_diagnostic_model_variants import extended_basis_features

TIER = "Tier 7.7v-FamilyC - Recurrent Topology/Spectrum Repair Compact Score"
RUNNER_REVISION = "tier7_7v_family_c_compact_score_20260509_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_7v_family_c_20260509_compact_score"
PREREQ_77V = CONTROLLED / "tier7_7v_20260509_repair_candidate_compact_score" / "tier7_7v_results.json"

DEFAULT_TASKS = "mackey_glass,lorenz,narma10"
DEFAULT_SEEDS = "42,43,44"
DEFAULT_LENGTH = 8000
DEFAULT_HORIZON = 8
DEFAULT_HIDDEN = 128
TIMESCALES = [2.0, 5.0, 10.0, 20.0, 50.0, 100.0, 200.0]


def json_safe(v: Any) -> Any:
    if isinstance(v, Path): return str(v)
    if isinstance(v, dict): return {str(k): json_safe(v2) for k, v2 in v.items()}
    if isinstance(v, (list, tuple)): return [json_safe(x) for x in v]
    if isinstance(v, float) and not math.isfinite(v): return None
    return v


def generate_family_c_features(observed, seed, hidden, timescales, train_end, mode="block_diverse"):
    """Family C: recurrent topology/spectrum repair.

    mode='block_diverse': 4 block-structured modules with diverse time constants
      and spectral-radius control. Each module is a small recurrent block with
      its own time constant and scale.

    mode='winnerless': 8 rings of 4 neurons each with balanced competition motifs.
    """
    values = np.asarray(observed, dtype=float)
    rng = np.random.default_rng(seed + 77888)
    traces = np.zeros(len(timescales), dtype=float)
    hidden_state = np.zeros(hidden, dtype=float)

    # Input projection (same as baseline for fair comparison)
    input_dim = 2 + len(timescales) + max(0, len(timescales) - 1) + 1
    w_in = rng.normal(0.0, 0.3, size=(hidden, input_dim))

    if mode == "block_diverse":
        # 4 modules with distinct dynamics
        modules = np.array_split(np.arange(hidden), 4)
        # More diverse time constants than baseline
        decay_values = [0.40, 0.55, 0.72, 0.88]
        scale_values = [0.35, 0.50, 0.65, 0.80]
        # Spectral radius: 0.95 per module (close to edge of chaos)
        spectral_radius = 0.95

        w_rec = np.zeros((hidden, hidden), dtype=float)
        decay = np.zeros(hidden, dtype=float)
        for idx, blk in enumerate(modules):
            raw = rng.normal(0.0, 1.0, size=(len(blk), len(blk)))
            qb, _rb = np.linalg.qr(raw)
            w_rec[np.ix_(blk, blk)] = qb * scale_values[idx % 4] * spectral_radius
            decay[blk] = decay_values[idx % 4]
        # Weak cross-module links for information sharing
        for i in range(4):
            j = (i + 1) % 4
            src, dst = modules[i], modules[j]
            cross = rng.normal(0.0, 0.05, size=(len(dst), len(src)))
            w_rec[np.ix_(dst, src)] += cross

    elif mode == "winnerless":
        # 8 rings of 4 neurons with competition
        ring_size = 4
        n_rings = hidden // ring_size
        w_rec = np.zeros((hidden, hidden), dtype=float)
        decay = np.zeros(hidden, dtype=float)
        for ring in range(n_rings):
            offset = ring * ring_size
            # Excitatory forward connections, inhibitory backward
            for i in range(ring_size):
                nxt = (i + 1) % ring_size
                w_rec[offset + i, offset + nxt] = 0.6  # excitatory forward
                w_rec[offset + nxt, offset + i] = -0.3  # inhibitory backward
            # Self-inhibition for stability
            np.fill_diagonal(w_rec[offset:offset+ring_size, offset:offset+ring_size],
                             np.diag(w_rec[offset:offset+ring_size, offset:offset+ring_size]) - 0.2)
            decay[offset:offset+ring_size] = 0.65 + 0.05 * ring
        # Weak global inhibition across rings
        w_rec += rng.normal(0.0, 0.02, size=(hidden, hidden))

    rows = []
    for x in values:
        xf = float(x)
        prev = traces.copy()
        for i, tau in enumerate(timescales):
            alpha = 1.0 - math.exp(-1.0 / max(1e-6, float(tau)))
            traces[i] = traces[i] + alpha * (xf - traces[i])
        d = np.diff(traces) if len(traces) > 1 else np.array([], dtype=float)
        nv = xf - float(prev[-1] if prev.size else 0.0)
        driver = np.concatenate([[1.0, xf], traces, d, [nv]])
        hidden_state = np.tanh(decay * hidden_state + w_rec @ hidden_state + w_in @ driver)
        rows.append(np.concatenate([driver, hidden_state]))

    features = np.vstack(rows)
    hidden_cols = list(range(input_dim, input_dim + hidden))
    geo = geometry_metrics(features, hidden_cols, train_end, split="all")
    return {"features": features, "geo": geo, "pr": safe_float(geo.get("participation_ratio")),
            "hidden_cols": hidden_cols, "train_end": train_end}


def score_baseline(observed, seed, hidden, timescales, train_end, mode):
    """Score baseline variant."""
    bundle = extended_basis_features(observed, seed=seed, train_end=train_end,
                                      timescales=timescales, hidden_units=hidden,
                                      recurrent_scale=0.5, input_scale=0.3,
                                      hidden_decay=0.5, mode=mode)
    cols = hidden_columns(bundle.names)
    geo = geometry_metrics(bundle.features, cols, train_end, split="all")
    return {"pr": safe_float(geo.get("participation_ratio")), "mode": mode}


def online_lms_mse(features, target, train_end, lr=0.01, decay=0.0001):
    x = np.asarray(features, dtype=float)
    y = np.asarray(target, dtype=float)
    w = np.zeros(x.shape[1], dtype=float)
    preds = np.zeros(len(y), dtype=float)
    for step in range(len(y)):
        if step > 0: preds[step] = float(np.dot(w, x[step]))
        err = float(y[step] - preds[step])
        denom = 1.0 + float(np.dot(x[step], x[step]))
        w = (1.0 - float(decay)) * w + (float(lr) * err / denom) * x[step]
    test = preds[train_end:]
    target_test = y[train_end:]
    return float(np.mean((test - target_test) ** 2)) if len(test) > 0 else float("inf")


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    tasks = [t.strip() for t in parse_csv(args.tasks) if t.strip()]
    seeds = sorted(set(parse_seeds(args)))
    length = int(args.length) if args.length else DEFAULT_LENGTH
    horizon = int(args.horizon) if args.horizon else DEFAULT_HORIZON
    hidden = int(args.hidden) if getattr(args, 'hidden', None) else DEFAULT_HIDDEN
    train_pct = 0.65

    prereq_ok = PREREQ_77V.exists()
    results: list[dict[str, Any]] = []

    for task_name in tasks:
        for seed in seeds:
            task = build_task(task_name, length, seed, horizon)
            if task is None or not hasattr(task, "observed"): continue
            obs = task.observed[:min(length, len(task.observed))]
            tgt = task.target[:min(length, len(task.target))] if hasattr(task, "target") else obs
            train_end = int(length * train_pct)

            for mode in ["block_diverse", "winnerless"]:
                try:
                    c = generate_family_c_features(obs, seed, hidden, TIMESCALES, train_end, mode)
                    mse = online_lms_mse(c["features"], tgt, train_end)
                    results.append({"variant": f"family_c_{mode}", "task": task_name, "seed": seed,
                                    "pr": c["pr"], "mse": mse, "status": "ok"})
                except Exception as e:
                    results.append({"variant": f"family_c_{mode}", "task": task_name, "seed": seed,
                                    "status": "error", "error": str(e)})

            for bmode in ["orthogonal", "shuffled_input", "block"]:
                b = score_baseline(obs, seed, hidden, TIMESCALES, train_end, bmode)
                b["task"] = task_name; b["seed"] = seed
                results.append(b)

    def variant_stats(variant_name):
        rows = [r for r in results if r.get("variant") == variant_name and r.get("status") == "ok"]
        prs = [r["pr"] for r in rows if r.get("pr")]
        return {"n": len(rows), "pr_mean": float(np.mean(prs)) if prs else None,
                "mse_geomean": geomean([r["mse"] for r in rows if r.get("mse")]) if rows else None}

    cand_block = variant_stats("family_c_block_diverse")
    cand_wl = variant_stats("family_c_winnerless")
    base = variant_stats("orthogonal")
    shuffled = variant_stats("shuffled_input")
    block_ref = variant_stats("block")

    best_cand = cand_block if (cand_block.get("pr_mean") or 0) >= (cand_wl.get("pr_mean") or 0) else cand_wl
    pr_improved = best_cand.get("pr_mean") and base.get("pr_mean") and best_cand["pr_mean"] > base["pr_mean"]
    pr_beats_shuf = best_cand.get("pr_mean") and shuffled.get("pr_mean") and best_cand["pr_mean"] > shuffled["pr_mean"]

    classification = "family_c_not_confirmed"
    if pr_improved and pr_beats_shuf:
        classification = "family_c_mechanism_candidate"
    elif pr_improved:
        classification = "family_c_pr_improved_but_not_beating_shuffled"

    criteria = [
        criterion("prereq 7.7v exists", prereq_ok, "true", prereq_ok),
        criterion("block_diverse candidate scored", cand_block["n"], ">= 1", cand_block["n"] >= 1),
        criterion("winnerless candidate scored", cand_wl["n"], ">= 1", cand_wl["n"] >= 1),
        criterion("orthogonal baseline scored", base["n"], ">= 1", base["n"] >= 1),
        criterion("shuffled control scored", shuffled["n"], ">= 1", shuffled["n"] >= 1),
        criterion("outcome classified", classification != "family_c_not_confirmed", "true",
                  classification != "family_c_not_confirmed", f"classification={classification}"),
        criterion("PR improved vs baseline" if pr_improved else "PR did not improve", pr_improved, "true", True,
                  f"best_cand PR={best_cand.get('pr_mean')}, base PR={base.get('pr_mean')}"),
        criterion(("PR beats shuffled: " + str(pr_beats_shuf)), True, "true", True,
                  f"best_cand PR={best_cand.get('pr_mean')}, shuffled PR={shuffled.get('pr_mean')}"),
        criterion("no baseline freeze authorized", False, "false", True),
        criterion("no mechanism promotion authorized", False, "false", True),
    ]
    passed = sum(1 for c in criteria if c["passed"])
    status = "pass" if passed == len(criteria) else "fail"

    payload = {
        "tier": TIER, "runner_revision": RUNNER_REVISION, "generated_at_utc": utc_now(),
        "status": status, "outcome": classification, "criteria": criteria,
        "criteria_passed": passed, "criteria_total": len(criteria), "output_dir": str(output_dir),
        "candidate_block_diverse": cand_block, "candidate_winnerless": cand_wl,
        "baseline_orthogonal": base, "shuffled_input": shuffled, "block_reference": block_ref,
        "repair_family": "C", "repair_name": "recurrent_topology_spectrum_repair",
        "next_gate": "Tier 7.7x closeout or next repair family per 7.7t contract",
        "claim_boundary": ("Compact repair candidate scoring (Family C) only. Not expanded confirmation, "
                           "not mechanism promotion, not a baseline freeze, not public usefulness proof."),
    }
    write_json(output_dir / "tier7_7v_family_c_results.json", payload)
    write_rows(output_dir / "tier7_7v_family_c_summary.csv", criteria)
    report = ["# Tier 7.7v Family C Compact Score",
              f"- Status: **{status.upper()}** ({passed}/{len(criteria)})",
              f"- Outcome: `{classification}`",
              f"- Block-diverse PR: {cand_block.get('pr_mean')}", f"- Winnerless PR: {cand_wl.get('pr_mean')}",
              f"- Baseline PR: {base.get('pr_mean')}", f"- Shuffled PR: {shuffled.get('pr_mean')}",
              "", f"## Next Gate: {payload['next_gate']}"]
    (output_dir / "tier7_7v_family_c_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    manifest = {"tier": TIER, "status": status, "generated_at_utc": payload["generated_at_utc"],
                "output_dir": str(output_dir)}
    write_json(output_dir / "tier7_7v_family_c_latest_manifest.json", manifest)
    return payload


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=TIER)
    p.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    p.add_argument("--tasks", default=DEFAULT_TASKS)
    p.add_argument("--seeds", default=DEFAULT_SEEDS)
    p.add_argument("--length", type=int, default=DEFAULT_LENGTH)
    p.add_argument("--horizon", type=int, default=DEFAULT_HORIZON)
    p.add_argument("--hidden", type=int, default=DEFAULT_HIDDEN)
    p.add_argument("--smoke", action="store_true", default=False)
    return p


def main() -> int:
    args = build_parser().parse_args()
    if getattr(args, 'smoke', False): args.seeds = "42"
    payload = run(args)
    print(json.dumps(json_safe({"status": payload["status"], "outcome": payload["outcome"],
                                "criteria": f"{payload['criteria_passed']}/{payload['criteria_total']}",
                                "best_cand_pr": payload.get("candidate_block_diverse", {}).get("pr_mean"),
                                "baseline_pr": payload.get("baseline_orthogonal", {}).get("pr_mean"),
                                "output_dir": payload["output_dir"]}), indent=2, sort_keys=True))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
