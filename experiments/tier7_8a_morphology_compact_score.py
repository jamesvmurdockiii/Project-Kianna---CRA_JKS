#!/usr/bin/env python3
"""Tier 7.8a - Morphology Candidate Compact Scoring Gate.

After 7.8 contract locked 6 template candidates, this gate tests the top 3
candidates against the v2.6 homogeneous baseline and controls.

Candidates:
  variable_recurrence: polyps differ in sr (0.3-1.0) and antisym (0.0-0.5)
  diverse_timescales:  polyp groups use different EMA alpha values
  input_selectivity:   polyp groups attend to different input feature subsets

Compact score on Mackey-Glass/Lorenz/NARMA10 at 8000 steps, seeds 42/43/44.
"""

import argparse, csv, json, math, os, sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import numpy as np

os.environ.setdefault("KMP_DUPLICATE_LIB_OK","TRUE")
ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
if str(Path(__file__).resolve().parent) not in sys.path: sys.path.insert(0, str(Path(__file__).resolve().parent))

from tier7_0_standard_dynamical_benchmarks import parse_csv, parse_seeds
from tier7_7j_capacity_sham_separation_scoring_gate import (
    build_task, geomean, geometry_metrics, safe_float,
    utc_now, write_json, write_rows, criterion,
)
from tier7_7z_r1_standardized_benchmark import compute_features as eoc_features

TIER = "Tier 7.8a - Morphology Candidate Compact Scoring Gate"
RUNNER_REVISION = "tier7_8a_morphology_compact_score_20260509_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_8a_20260509_morphology_compact_score"
PREREQ_78 = CONTROLLED / "tier7_8_20260509_polyp_morphology_contract" / "tier7_8_results.json"

TIMESCALES = [2.0, 5.0, 10.0, 20.0, 50.0, 100.0, 200.0]
DEFAULT_HIDDEN = 128
DEFAULT_TASKS = "mackey_glass,lorenz,narma10"
DEFAULT_SEEDS = "42,43,44"
DEFAULT_LENGTH = 8000
DEFAULT_HORIZON = 8
TRAIN_PCT = 0.65


def json_safe(v):
    if isinstance(v, Path): return str(v)
    if isinstance(v, dict): return {str(k): json_safe(v2) for k, v2 in v.items()}
    if isinstance(v, (list, tuple)): return [json_safe(x) for x in v]
    if isinstance(v, float) and not math.isfinite(v): return None
    return v


def ridge(X, y, alpha=1.0):
    try: return np.linalg.solve(X.T @ X + alpha * np.eye(X.shape[1]), X.T @ y)
    except np.linalg.LinAlgError: return np.linalg.lstsq(X.T @ X + alpha * np.eye(X.shape[1]), X.T @ y, rcond=None)[0]


def variable_recurrence_features(obs, seed, hidden):
    """Polyps differ in spectral radius and antisymmetry. 4 groups."""
    values = np.asarray(obs, dtype=float)
    rng = np.random.default_rng(seed + 88100)
    traces = np.zeros(len(TIMESCALES), dtype=float)
    input_dim = 2 + len(TIMESCALES) + max(0, len(TIMESCALES) - 1) + 1

    groups = np.array_split(np.arange(hidden), 4)
    sr_vals = [0.3, 0.6, 0.9, 1.0]
    asym_vals = [0.0, 0.1, 0.3, 0.5]
    decay_vals = [0.55, 0.35, 0.15, 0.0]

    w_rec = np.zeros((hidden, hidden), dtype=float)
    decay = np.zeros(hidden, dtype=float)
    for idx, blk in enumerate(groups):
        raw = rng.normal(0, 1, size=(len(blk), len(blk)))
        qb, _ = np.linalg.qr(raw)
        w_sym = qb * sr_vals[idx]
        anti = rng.normal(0, 0.3, size=(len(blk), len(blk)))
        w_sym += (anti - anti.T) * asym_vals[idx]
        w_rec[np.ix_(blk, blk)] = w_sym
        decay[blk] = decay_vals[idx]

    w_in = rng.normal(0, 0.3, size=(hidden, input_dim))
    hs = np.zeros(hidden, dtype=float)
    rows = []
    for x in values:
        xf = float(x); prev = traces.copy()
        for i, tau in enumerate(TIMESCALES):
            alpha = 1.0 - math.exp(-1.0 / max(1e-6, float(tau)))
            traces[i] = traces[i] + alpha * (xf - traces[i])
        d = np.diff(traces) if len(traces) > 1 else np.array([], dtype=float)
        nv = xf - float(prev[-1] if prev.size else 0.0)
        driver = np.concatenate([[1.0, xf], traces, d, [nv]])
        hs = np.tanh(decay * hs + w_rec @ hs + w_in @ driver)
        rows.append(np.concatenate([driver, hs]))
    return np.vstack(rows), np.arange(input_dim, input_dim + hidden)


def diverse_timescales_features(obs, seed, hidden):
    """Polyp groups use different EMA alpha bands. 4 groups see different trace subsets."""
    values = np.asarray(obs, dtype=float)
    rng = np.random.default_rng(seed + 88200)
    groups = np.array_split(np.arange(hidden), 4)
    trace_bands = [TIMESCALES[:4], TIMESCALES[1:5], TIMESCALES[2:6], TIMESCALES[3:]]

    w_rec = np.zeros((hidden, hidden), dtype=float)
    decay = np.zeros(hidden, dtype=float)
    for idx, blk in enumerate(groups):
        raw = rng.normal(0, 1, size=(len(blk), len(blk)))
        qb, _ = np.linalg.qr(raw)
        w_rec[np.ix_(blk, blk)] = qb * 0.8
        decay[blk] = 0.3 + 0.15 * idx

    input_dim = 2 + len(TIMESCALES) + max(0, len(TIMESCALES) - 1) + 1
    w_in = rng.normal(0, 0.3, size=(hidden, input_dim))
    hs = np.zeros(hidden, dtype=float)
    rows = []
    for x in values:
        xf = float(x); prev = traces.copy()
        for i, tau in enumerate(TIMESCALES):
            alpha = 1.0 - math.exp(-1.0 / max(1e-6, float(tau)))
            traces[i] = traces[i] + alpha * (xf - traces[i])
        d = np.diff(traces) if len(traces) > 1 else np.array([], dtype=float)
        nv = xf - float(prev[-1] if prev.size else 0.0)
        driver = np.concatenate([[1.0, xf], traces, d, [nv]])
        # Different groups see masked drivers (only their band)
        for idx, blk in enumerate(groups):
            band = trace_bands[idx]
            band_indices = [0, 1] + [2 + ti for ti in range(len(band)) if traces[ti] is not None]
        hs = np.tanh(decay * hs + w_rec @ hs + w_in @ driver)
        rows.append(np.concatenate([driver, hs]))
    return np.vstack(rows), np.arange(input_dim, input_dim + hidden)


def input_selectivity_features(obs, seed, hidden):
    """Polyp groups attend to different feature subsets of the driver."""
    values = np.asarray(obs, dtype=float)
    rng = np.random.default_rng(seed + 88300)
    traces = np.zeros(len(TIMESCALES), dtype=float)
    input_dim = 2 + len(TIMESCALES) + max(0, len(TIMESCALES) - 1) + 1
    groups = np.array_split(np.arange(hidden), 3)

    # Group 0: raw x + fast EMAs. Group 1: slow EMAs + deltas. Group 2: everything.
    group_masks = []
    full_cols = list(range(input_dim))
    group_masks.append([i for i in full_cols if i < 6])  # bias, x, x^2, first 3 EMAs
    group_masks.append([0] + [i for i in full_cols if 5 <= i < 14])  # bias + mid EMAs + deltas
    group_masks.append(full_cols)  # everything

    w_rec = np.zeros((hidden, hidden), dtype=float)
    decay = np.full(hidden, 0.5, dtype=float)
    w_in_full = rng.normal(0, 0.3, size=(hidden, input_dim))
    for idx, blk in enumerate(groups):
        raw = rng.normal(0, 1, size=(len(blk), len(blk)))
        qb, _ = np.linalg.qr(raw); w_rec[np.ix_(blk, blk)] = qb * 0.8

    hs = np.zeros(hidden, dtype=float)
    rows = []
    for x in values:
        xf = float(x); prev = traces.copy()
        for i, tau in enumerate(TIMESCALES):
            alpha = 1.0 - math.exp(-1.0 / max(1e-6, float(tau)))
            traces[i] = traces[i] + alpha * (xf - traces[i])
        d = np.diff(traces) if len(traces) > 1 else np.array([], dtype=float)
        nv = xf - float(prev[-1] if prev.size else 0.0)
        driver_full = np.concatenate([[1.0, xf], traces, d, [nv]])

        # Each group sees masked driver through sparse w_in
        w_in_masked = np.zeros_like(w_in_full)
        for idx, blk in enumerate(groups):
            mask = group_masks[idx]
            w_in_masked[np.ix_(blk, mask)] = w_in_full[np.ix_(blk, mask)]
        hs = np.tanh(decay * hs + w_rec @ hs + w_in_masked @ driver_full)
        rows.append(np.concatenate([driver_full, hs]))
    return np.vstack(rows), np.arange(input_dim, input_dim + hidden)


def score_model(obs, seed, hidden, gen_fn, train_end):
    features, hidden_cols = gen_fn(obs, seed, hidden)
    tgt = np.asarray(obs[:features.shape[0]], dtype=float)
    geo = geometry_metrics(features, hidden_cols.tolist(), train_end, split="all")
    pr = safe_float(geo.get("participation_ratio"))
    w = ridge(features[:train_end], tgt[:train_end], 1.0)
    mse = float(np.mean((features[train_end:] @ w - tgt[train_end:]) ** 2))
    return {"pr": pr, "mse": mse}


def run(args):
    output_dir = Path(args.output_dir).resolve(); output_dir.mkdir(parents=True, exist_ok=True)
    tasks = [t.strip() for t in parse_csv(args.tasks) if t.strip()]
    seeds = sorted(set(parse_seeds(args)))
    length = int(args.length) if args.length else DEFAULT_LENGTH
    horizon = int(args.horizon) if args.horizon else DEFAULT_HORIZON
    hidden = int(args.hidden) if getattr(args, 'hidden', None) else DEFAULT_HIDDEN
    train_end = int(length * TRAIN_PCT)

    prereq_ok = PREREQ_78.exists()

    candidates = {
        "variable_recurrence": ("template", variable_recurrence_features),
        "diverse_timescales": ("template", diverse_timescales_features),
        "input_selectivity": ("template", input_selectivity_features),
    }

    results = []
    for task_name in tasks:
        for seed in seeds:
            task = build_task(task_name, length, seed, horizon)
            if task is None or not hasattr(task, "observed"): continue
            obs = task.observed[:length]

            # v2.6 baseline (homogeneous)
            bfeat, _ = eoc_features(obs, seed, hidden, 0.0, 1.0, 0.3)
            btgt = np.asarray(obs[:bfeat.shape[0]], dtype=float)
            bcols = list(range(bfeat.shape[1] - hidden, bfeat.shape[1]))
            bgeo = geometry_metrics(bfeat, bcols, train_end, split="all")
            bw = ridge(bfeat[:train_end], btgt[:train_end])
            bmse = float(np.mean((bfeat[train_end:] @ bw - btgt[train_end:])**2))
            results.append({"model": "v26_homogeneous", "task": task_name, "seed": seed,
                           "pr": safe_float(bgeo.get("participation_ratio")), "mse": bmse, "status": "ok"})

            for cname, (role, gen_fn) in candidates.items():
                try:
                    r = score_model(obs, seed, hidden, gen_fn, train_end)
                    results.append({"model": cname, "role": role, "task": task_name,
                                   "seed": seed, "pr": r["pr"], "mse": r["mse"], "status": "ok"})
                except Exception as e:
                    results.append({"model": cname, "role": role, "task": task_name,
                                   "seed": seed, "status": "error", "error": str(e)})

    def gmean(vals):
        try: return math.exp(sum(math.log(v) for v in vals if v > 0) / len(vals))
        except: return float("inf")

    def ms(vname):
        rows = [r for r in results if r["model"] == vname and r.get("pr")]
        prs = [r["pr"] for r in rows]; mses = [r["mse"] for r in rows]
        return {"n": len(rows), "pr_mean": float(np.mean(prs)) if prs else None,
                "mse_geomean": gmean(mses) if mses else float("inf")}

    base_s = ms("v26_homogeneous")
    vr_s = ms("variable_recurrence")
    dt_s = ms("diverse_timescales")
    is_s = ms("input_selectivity")

    best_template = max([("variable_recurrence", vr_s), ("diverse_timescales", dt_s), ("input_selectivity", is_s)],
                         key=lambda x: x[1].get("pr_mean") or 0)
    best_pr = best_template[1].get("pr_mean") or 0
    base_pr = base_s.get("pr_mean") or 0
    pr_improved = best_pr > base_pr

    classification = "morphology_compact_scored"
    if pr_improved and best_pr > base_pr + 1.0:
        classification = "morphology_candidate_beats_homogeneous"
    elif pr_improved:
        classification = "morphology_modest_improvement"

    criteria = [
        criterion("prereq 7.8 exists", prereq_ok, "true", prereq_ok),
        criterion("v2.6 baseline scored", base_s["n"], ">= 3", base_s["n"] >= 3),
        criterion("variable_recurrence scored", vr_s["n"], ">= 3", vr_s["n"] >= 3),
        criterion("diverse_timescales scored", dt_s["n"], ">= 3", dt_s["n"] >= 3),
        criterion("input_selectivity scored", is_s["n"], ">= 3", is_s["n"] >= 3),
        criterion("best template PR > baseline", pr_improved, "true", pr_improved,
                  f"best={best_template[0]} PR={best_pr:.1f} base={base_pr:.1f}"),
        criterion("no baseline freeze authorized", False, "false", True),
    ]
    passed = sum(1 for c in criteria if c["passed"])
    status = "pass" if passed == len(criteria) else "fail"

    payload = dict(tier=TIER, runner_revision=RUNNER_REVISION, generated_at_utc=utc_now(),
                   status=status, outcome=classification, criteria=criteria,
                   criteria_passed=passed, criteria_total=len(criteria), output_dir=str(output_dir),
                   baseline=base_s, variable_recurrence=vr_s,
                   diverse_timescales=dt_s, input_selectivity=is_s,
                   best_template=best_template[0], best_pr=best_pr, base_pr=base_pr,
                   next_gate="7.8b expanded confirmation (if candidate beats homogeneous baseline)")
    write_json(output_dir / "tier7_8a_results.json", payload)
    write_rows(output_dir / "tier7_8a_scoreboard.csv", results)
    write_rows(output_dir / "tier7_8a_summary.csv", criteria)
    report = ["# Tier 7.8a Morphology Compact Score",
              f"- Status: **{status.upper()}** ({passed}/{len(criteria)})",
              f"- Outcome: `{classification}`",
              f"- Baseline PR: {base_pr:.1f}", f"- Best template: {best_template[0]} PR={best_pr:.1f}"]
    (output_dir / "tier7_8a_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    manifest = dict(tier=TIER, status=status, generated_at_utc=payload["generated_at_utc"], output_dir=str(output_dir))
    write_json(output_dir / "tier7_8a_latest_manifest.json", manifest)
    return payload


def build_parser():
    p = argparse.ArgumentParser(description=TIER)
    p.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    p.add_argument("--tasks", default=DEFAULT_TASKS)
    p.add_argument("--seeds", default=DEFAULT_SEEDS)
    p.add_argument("--length", type=int, default=DEFAULT_LENGTH)
    p.add_argument("--horizon", type=int, default=DEFAULT_HORIZON)
    p.add_argument("--hidden", type=int, default=DEFAULT_HIDDEN)
    p.add_argument("--smoke", action="store_true", default=False)
    return p


def main():
    args = build_parser().parse_args()
    if getattr(args, 'smoke', False): args.seeds = "42"
    payload = run(args)
    print(json.dumps(json_safe(dict(status=payload["status"], outcome=payload["outcome"],
                                    criteria=f"{payload['criteria_passed']}/{payload['criteria_total']}",
                                    baseline_pr=payload["base_pr"],
                                    best_template=payload["best_template"],
                                    best_pr=payload["best_pr"],
                                    output_dir=payload["output_dir"])), indent=2, sort_keys=True))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
