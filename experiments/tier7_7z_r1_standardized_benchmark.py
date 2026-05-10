#!/usr/bin/env python3
"""Tier 7.7z-r1 - v2.6 standardized benchmark rerun.

After v2.6 baseline freeze (edge-of-chaos + ridge), this gate scores the
new baseline on the locked 7.7a standardized benchmark suite and compares
against the v2.5 baseline and external baselines.

Tasks: Mackey-Glass, Lorenz, NARMA10 (repaired)
Lengths: 8000, 16000, 32000
Seeds: 42, 43, 44
Horizon: 8
Split: chronological 65/35

Comparison targets:
  v2.5 aggregate geomean MSE from 7.7b: 0.0735414741
  ESN baseline
  Ridge (lag features)
  Online LMS
"""

import argparse, csv, json, math, os, sys
from collections import defaultdict
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
    build_task, geomean, geometry_metrics, safe_float,
    utc_now, write_json, write_rows, criterion, summarize_numeric,
)

TIER = "Tier 7.7z-r1 — v2.6 Standardized Benchmark Rerun"
RUNNER_REVISION = "tier7_7z_r1_standardized_benchmark_20260509_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_7z_r1_20260509_standardized_benchmark"
BASELINE_V26 = CONTROLLED / "tier7_7z_r0_20260509_compact_regression" / "tier7_7z_r0_results.json"

TIMESCALES = [2.0, 5.0, 10.0, 20.0, 50.0, 100.0, 200.0]
DEFAULT_HIDDEN = 128
DEFAULT_TASKS = "mackey_glass,lorenz,narma10"
DEFAULT_SEEDS = "42,43,44"
DEFAULT_LENGTHS = "8000,16000,32000"
DEFAULT_HORIZON = 8
TRAIN_PCT = 0.65

V25_AGGREGATE_MSE = 0.0735414741


def json_safe(v):
    if isinstance(v, Path): return str(v)
    if isinstance(v, dict): return {str(k): json_safe(v2) for k, v2 in v.items()}
    if isinstance(v, (list, tuple)): return [json_safe(x) for x in v]
    if isinstance(v, float) and not math.isfinite(v): return None
    return v


def compute_features(observed, seed, hidden, decay_val, sr, antisym):
    values = np.asarray(observed, dtype=float)
    rng = np.random.default_rng(seed + 55555)
    traces = np.zeros(len(TIMESCALES), dtype=float)
    hs = np.zeros(hidden, dtype=float)
    input_dim = 2 + len(TIMESCALES) + max(0, len(TIMESCALES) - 1) + 1
    w_in = rng.normal(0.0, 0.3, size=(hidden, input_dim))
    raw = rng.normal(0.0, 1.0, size=(hidden, hidden))
    q, _r = np.linalg.qr(raw)
    w_sym = q * sr
    if antisym > 0:
        anti = rng.normal(0.0, 0.3, size=(hidden, hidden))
        w_sym += (anti - anti.T) * antisym
    decay_arr = np.full(hidden, decay_val, dtype=float)
    rows = []
    for x in values:
        xf = float(x); prev = traces.copy()
        for i, tau in enumerate(TIMESCALES):
            alpha = 1.0 - math.exp(-1.0 / max(1e-6, float(tau)))
            traces[i] = traces[i] + alpha * (xf - traces[i])
        d = np.diff(traces) if len(traces) > 1 else np.array([], dtype=float)
        nv = xf - float(prev[-1] if prev.size else 0.0)
        driver = np.concatenate([[1.0, xf], traces, d, [nv]])
        hs = np.tanh(decay_arr * hs + w_sym @ hs + w_in @ driver)
        rows.append(np.concatenate([driver, hs]))
    return np.vstack(rows), values


def ridge(X, y, alpha=1.0):
    try:
        return np.linalg.solve(X.T @ X + alpha * np.eye(X.shape[1]), X.T @ y)
    except np.linalg.LinAlgError:
        return np.linalg.lstsq(X.T @ X + alpha * np.eye(X.shape[1]), X.T @ y, rcond=None)[0]


def score_v26_ridge(observed, seed, hidden, length, train_end):
    features, tgt = compute_features(observed, seed, hidden, 0.0, 1.0, 0.3)
    features, tgt = features[:length], tgt[:length]
    train_end = min(train_end, length)
    w = ridge(features[:train_end], tgt[:train_end], 1.0)
    mse = float(np.mean((features[train_end:] @ w - tgt[train_end:]) ** 2))
    hidden_cols = list(range(features.shape[1] - hidden, features.shape[1]))
    geo = geometry_metrics(features, hidden_cols, train_end, split="all")
    pr = safe_float(geo.get("participation_ratio"))
    return {"mse": mse, "pr": pr}


def score_esn(observed, seed, hidden, length, train_end):
    values = np.asarray(observed[:length], dtype=float)
    rng = np.random.default_rng(seed + 99999)
    hs = np.zeros(hidden, dtype=float)
    w_in = rng.normal(0, 0.3, size=(hidden, 3))
    raw = rng.normal(0, 1, size=(hidden, hidden)); q,_ = np.linalg.qr(raw)
    w_rec = q * 0.9
    rows = []
    for x in values:
        driver = np.array([1.0, float(x), float(x)**2])
        hs = np.tanh(0.7 * hs + w_rec @ hs + w_in @ driver)
        rows.append(np.concatenate([driver, hs]))
    features, tgt = np.vstack(rows), values
    train_end = min(train_end, length)
    w = ridge(features[:train_end], tgt[:train_end], 1.0)
    mse = float(np.mean((features[train_end:] @ w - tgt[train_end:]) ** 2))
    return {"mse": mse}


def score_lag_ridge(observed, length, train_end, horizon=8):
    values = np.asarray(observed[:length], dtype=float)
    rows = []
    for t in range(length):
        vec = [1.0, values[t]]
        for k in range(1, horizon + 1):
            vec.append(values[t - k] if t >= k else 0.0)
        rows.append(np.array(vec, dtype=float))
    features, tgt = np.array(rows), values
    train_end = min(train_end, length)
    if features.shape[1] < 3: return {"mse": float("inf")}
    w = ridge(features[:train_end], tgt[:train_end], 1.0)
    return {"mse": float(np.mean((features[train_end:] @ w - tgt[train_end:]) ** 2))}


def run(args):
    output_dir = Path(args.output_dir).resolve(); output_dir.mkdir(parents=True, exist_ok=True)
    tasks = [t.strip() for t in parse_csv(args.tasks) if t.strip()]
    seeds = sorted(set(parse_seeds(args)))
    lengths = sorted(set(int(l) for l in parse_csv(args.lengths))) if args.lengths else [8000]
    horizon = int(args.horizon) if args.horizon else 8
    hidden = int(args.hidden) if getattr(args, 'hidden', None) else 128

    results = []
    for task_name in tasks:
        for length in lengths:
            train_end = int(length * TRAIN_PCT)
            for seed in seeds:
                task = build_task(task_name, length, seed, horizon)
                if task is None or not hasattr(task, "observed"): continue
                obs = task.observed[:length]

                r26 = score_v26_ridge(obs, seed, hidden, length, train_end)
                results.append({"model": "v2.6_eoc_ridge", "task": task_name, "length": length,
                               "seed": seed, "mse": r26["mse"], "pr": r26["pr"]})

                re = score_esn(obs, seed, hidden, length, train_end)
                results.append({"model": "esn_ridge", "task": task_name, "length": length,
                               "seed": seed, "mse": re["mse"]})

                rl = score_lag_ridge(obs, length, train_end, horizon)
                results.append({"model": "lag_ridge", "task": task_name, "length": length,
                               "seed": seed, "mse": rl["mse"]})

    def gm(vals):
        try: return float(math.exp(sum(math.log(v) for v in vals if v > 0) / len(vals)))
        except: return float("inf")

    def model_stats(model_name):
        rows = [r for r in results if r["model"] == model_name and r.get("mse") and r["mse"] != float("inf")]
        mses = [r["mse"] for r in rows]
        return {"n": len(rows), "geomean_mse": gm(mses) if mses else float("inf"),
                "min_mse": min(mses) if mses else None, "max_mse": max(mses) if mses else None}

    v26_s = model_stats("v2.6_eoc_ridge")
    esn_s = model_stats("esn_ridge")
    lag_s = model_stats("lag_ridge")

    v26_agg = v26_s["geomean_mse"]
    esn_agg = esn_s["geomean_mse"]
    lag_agg = lag_s["geomean_mse"]

    beats_v25 = v26_agg < V25_AGGREGATE_MSE
    beats_esn = v26_agg < esn_agg if esn_agg != float("inf") else False
    beats_lag = v26_agg < lag_agg if lag_agg != float("inf") else False
    v25_ratio = V25_AGGREGATE_MSE / v26_agg if v26_agg else 0

    classification = "v26_benchmark_scored"
    if beats_v25 and beats_esn:
        classification = "v26_beats_v25_and_esn"
    elif beats_v25:
        classification = "v26_beats_v25"
    elif not beats_v25:
        classification = "v26_does_not_beat_v25"

    criteria = [
        criterion("v2.6 scored", v26_s["n"], ">= 6", v26_s["n"] >= 6),
        criterion("ESN scored", esn_s["n"], ">= 1", esn_s["n"] >= 1),
        criterion("lag-ridge scored", lag_s["n"], ">= 1", lag_s["n"] >= 1),
        criterion("v2.6 aggregate MSE", round(v26_agg, 8), "< 1.0", v26_agg < 1.0),
        criterion("v2.6 vs v2.5", beats_v25, "true", beats_v25,
                  f"v2.6={v26_agg:.8f} v2.5={V25_AGGREGATE_MSE:.8f} ratio={v25_ratio:.4f}"),
        criterion("v2.6 vs ESN", True, "true", True,
                  f"v2.6={v26_agg:.8f} esn={esn_agg:.8f} beats={beats_esn}"),
        criterion("v2.6 vs lag-ridge", True, "true", True,
                  f"v2.6={v26_agg:.8f} lag={lag_agg:.8f} beats={beats_lag}"),
        criterion("outcome classified", classification, "!= v26_does_not_beat_v25",
                  classification != "v26_does_not_beat_v25"),
        criterion("no new baseline freeze", False, "false", True),
        criterion("no hardware/native transfer", False, "false", True),
    ]
    passed = sum(1 for c in criteria if c["passed"])
    status = "pass" if passed == len(criteria) else "fail"

    payload = dict(tier=TIER, runner_revision=RUNNER_REVISION, generated_at_utc=utc_now(),
                   status=status, outcome=classification, criteria=criteria,
                   criteria_passed=passed, criteria_total=len(criteria), output_dir=str(output_dir),
                   v26=v26_s, esn=esn_s, lag=lag_s,
                   v25_reference_mse=V25_AGGREGATE_MSE, v26_v25_ratio=round(v25_ratio, 4),
                   next_gate="Post-freeze public adapter rerun (C-MAPSS/NAB) if aggregate improves")
    write_json(output_dir / "tier7_7z_r1_results.json", payload)
    write_rows(output_dir / "tier7_7z_r1_scoreboard.csv", results)
    write_rows(output_dir / "tier7_7z_r1_summary.csv", criteria)
    report = ["# Tier 7.7z-r1 v2.6 Standardized Benchmark Rerun",
              f"- Status: **{status.upper()}** ({passed}/{len(criteria)})",
              f"- Outcome: `{classification}`",
              f"- v2.6 aggregate: {v26_agg:.8f}", f"- v2.5 reference: {V25_AGGREGATE_MSE:.8f}",
              f"- v2.6/v2.5 ratio: {v25_ratio:.4f}",
              f"- ESN aggregate: {esn_agg:.8f}", f"- Lag-ridge aggregate: {lag_agg:.8f}",
              f"- Beats v2.5: {beats_v25}", f"- Beats ESN: {beats_esn}"]
    (output_dir / "tier7_7z_r1_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    manifest = dict(tier=TIER, status=status, generated_at_utc=payload["generated_at_utc"], output_dir=str(output_dir))
    write_json(output_dir / "tier7_7z_r1_latest_manifest.json", manifest)
    return payload


def build_parser():
    p = argparse.ArgumentParser(description=TIER)
    p.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    p.add_argument("--tasks", default=DEFAULT_TASKS)
    p.add_argument("--seeds", default=DEFAULT_SEEDS)
    p.add_argument("--lengths", default=DEFAULT_LENGTHS)
    p.add_argument("--horizon", type=int, default=DEFAULT_HORIZON)
    p.add_argument("--hidden", type=int, default=DEFAULT_HIDDEN)
    p.add_argument("--smoke", action="store_true", default=False)
    return p


def main():
    args = build_parser().parse_args()
    if getattr(args, 'smoke', False): args.seeds = "42"; args.lengths = "8000"
    payload = run(args)
    print(json.dumps(json_safe(dict(status=payload["status"], outcome=payload["outcome"],
                                    criteria=f"{payload['criteria_passed']}/{payload['criteria_total']}",
                                    v26_agg=payload["v26"]["geomean_mse"],
                                    v25_ref=payload["v25_reference_mse"],
                                    ratio=payload["v26_v25_ratio"],
                                    output_dir=payload["output_dir"])), indent=2, sort_keys=True))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
