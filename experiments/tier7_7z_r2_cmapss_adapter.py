#!/usr/bin/env python3
"""Tier 7.7z-r2 - v2.6 C-MAPSS FD001 Adapter Rerun.

After v2.6 baseline freeze, applies edge-of-chaos + ridge to the C-MAPSS
FD001 streaming RUL adapter. Comparison targets from 7.1c:
  v2.3 baseline: test RMSE 49.49
  Best model (monotone age-to-RUL ridge): 46.11
"""

import argparse, csv, json, math, os, sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import numpy as np

os.environ.setdefault("KMP_DUPLICATE_LIB_OK","TRUE")
ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
if str(Path(__file__).resolve().parent) not in sys.path: sys.path.insert(0, str(Path(__file__).resolve().parent))

from experiments.tier7_1b_cmapss_source_data_preflight import (
    find_named_file, parse_numeric_rows, parse_rul,
)

TIER = "Tier 7.7z-r2 - v2.6 C-MAPSS FD001 Adapter Rerun"
RUNNER_REVISION = "tier7_7z_r2_cmapss_adapter_20260509_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_7z_r2_20260509_cmapss_adapter"
TIMESCALES = [2.0, 5.0, 10.0, 20.0, 50.0, 100.0, 200.0]
V23_BASELINE_RMSE = 49.49
BEST_MODEL_RMSE = 46.11


def json_safe(v):
    if isinstance(v, Path): return str(v)
    if isinstance(v, dict): return {str(k): json_safe(v2) for k, v2 in v.items()}
    if isinstance(v, (list, tuple)): return [json_safe(x) for x in v]
    if isinstance(v, float) and not math.isfinite(v): return None
    return v


def criterion(name, value, rule, passed, details=""):
    return {"name": name, "criterion": name, "value": json_safe(value),
            "operator": rule, "rule": rule, "passed": bool(passed),
            "pass": bool(passed), "details": details, "note": details}


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_rows(path, rows, fieldnames=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None: fieldnames = list(dict.fromkeys(k for r in rows for k in r))
    with path.open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        for r in rows: w.writerow({k: json_safe(r.get(k,"")) for k in fieldnames})


def load_cmapss():
    cache = ROOT / ".cra_data_cache" / "nasa_cmapss" / "extracted"
    train_path = find_named_file(cache, "train_FD001.txt")
    test_path = find_named_file(cache, "test_FD001.txt")
    rul_path = find_named_file(cache, "RUL_FD001.txt")
    if not all([train_path, test_path, rul_path]):
        raise FileNotFoundError("C-MAPSS FD001 not found in cache")
    train_rows = parse_numeric_rows(train_path)
    test_rows = parse_numeric_rows(test_path)
    test_rul_raw = parse_rul(rul_path)

    train_x = np.array([[r[2],r[3],r[4]] + r[5:26] for r in train_rows], dtype=float)
    test_x = np.array([[r[2],r[3],r[4]] + r[5:26] for r in test_rows], dtype=float)
    train_mu, train_sd = np.mean(train_x, axis=0), np.std(train_x, axis=0)
    train_sd[train_sd < 1e-8] = 1.0
    train_z = (train_x - train_mu) / train_sd
    test_z = (test_x - train_mu) / train_sd
    _, _, vh = np.linalg.svd(train_z - np.mean(train_z, axis=0), full_matrices=False)
    pc1 = vh[0]
    train_pca, test_pca = train_z @ pc1, test_z @ pc1
    pca_mu, pca_sd = np.mean(train_pca), np.std(train_pca)
    if pca_sd < 1e-8: pca_sd = 1.0
    train_sc = (train_pca - pca_mu) / pca_sd
    test_sc = (test_pca - pca_mu) / pca_sd

    # RUL: train = max_cycle - current_cycle per engine
    train_rul = np.zeros(len(train_rows), dtype=float)
    engine_max = {}
    for i, r in enumerate(train_rows):
        uid = int(r[0]); engine_max[uid] = max(engine_max.get(uid, 0), int(r[1]))
    for i, r in enumerate(train_rows):
        uid = int(r[0]); train_rul[i] = engine_max[uid] - int(r[1])

    test_rul = np.zeros(len(test_rows), dtype=float)
    test_engines = {}
    for i, r in enumerate(test_rows):
        uid = int(r[0]); test_engines[uid] = max(test_engines.get(uid, 0), int(r[1]))
    for i, r in enumerate(test_rows):
        uid = int(r[0])
        test_rul[i] = test_rul_raw[uid-1] + test_engines[uid] - int(r[1])

    test_rul = np.clip(test_rul, 0, 400)
    return train_sc, test_sc, train_rul, test_rul


def eoc_features(stream, seed, hidden):
    values = np.asarray(stream, dtype=float)
    rng = np.random.default_rng(seed + 55555)
    traces = np.zeros(len(TIMESCALES), dtype=float)
    hs = np.zeros(hidden, dtype=float)
    input_dim = 2 + len(TIMESCALES) + max(0, len(TIMESCALES)-1) + 1
    w_in = rng.normal(0, 0.3, size=(hidden, input_dim))
    raw = rng.normal(0, 1, size=(hidden, hidden)); q,_ = np.linalg.qr(raw)
    anti = rng.normal(0, 0.3, size=(hidden, hidden))
    w_rec = q * 1.0 + (anti - anti.T) * 0.3
    rows = []
    for x in values:
        xf = float(x); prev = traces.copy()
        for i, tau in enumerate(TIMESCALES):
            alpha = 1.0 - math.exp(-1.0/max(1e-6, float(tau)))
            traces[i] = traces[i] + alpha*(xf - traces[i])
        d = np.diff(traces) if len(traces) > 1 else np.array([], dtype=float)
        nv = xf - float(prev[-1] if prev.size else 0.0)
        driver = np.concatenate([[1.0, xf], traces, d, [nv]])
        hs = np.tanh(hs + w_rec @ hs + w_in @ driver)
        rows.append(np.concatenate([driver, hs]))
    return np.vstack(rows)


def ridge(X, y, alpha=1.0):
    try: return np.linalg.solve(X.T@X + alpha*np.eye(X.shape[1]), X.T@y)
    except: return np.linalg.lstsq(X.T@X + alpha*np.eye(X.shape[1]), X.T@y, rcond=None)[0]


def run(args):
    output_dir = Path(args.output_dir).resolve(); output_dir.mkdir(parents=True, exist_ok=True)
    seeds = [int(s) for s in args.seeds.split(",")] if args.seeds else [42,43,44]
    hidden = int(args.hidden) if getattr(args,'hidden',None) else 128

    train_sc, test_sc, train_rul, test_rul = load_cmapss()
    results = []
    for seed in seeds:
        features = eoc_features(np.concatenate([train_sc, test_sc]), seed, hidden)
        f_train, f_test = features[:len(train_sc)], features[len(train_sc):]
        w = ridge(f_train, train_rul, 1.0)
        preds = np.clip(f_test @ w, 0, 400)
        rmse = math.sqrt(float(np.mean((preds - test_rul)**2)))
        results.append({"model": "v26_eoc_ridge", "seed": seed, "test_rmse": rmse})

    rmse_mean = float(np.mean([r["test_rmse"] for r in results]))
    rmse_med = float(np.median([r["test_rmse"] for r in results]))
    beats_v23 = rmse_mean < V23_BASELINE_RMSE
    beats_best = rmse_mean < BEST_MODEL_RMSE
    classification = "v26_beats_v23_and_best" if (beats_v23 and beats_best) else ("v26_beats_v23" if beats_v23 else "v26_no_adapter_signal")

    criteria = [
        criterion("C-MAPSS data loaded", len(train_sc) > 0, "true", len(train_sc) > 0),
        criterion("v2.6 scored (3 seeds)", len(results), "== 3", len(results) == 3,
                  f"RMSEs={[round(r['test_rmse'],2) for r in results]}"),
        criterion("v2.6 RMSE < v2.3 baseline (49.49)", round(rmse_mean,2), "< 49.49", beats_v23,
                  f"v2.6={rmse_mean:.2f} v2.3=49.49"),
        criterion("v2.6 RMSE < best public (46.11)", round(rmse_mean,2), "< 46.11", beats_best,
                  f"v2.6={rmse_mean:.2f} best=46.11"),
        criterion("no baseline freeze", False, "false", True),
        criterion("no public usefulness claim", False, "false", True),
    ]
    passed = sum(1 for c in criteria if c["passed"])
    status = "pass" if passed == len(criteria) else "fail"

    payload = dict(tier=TIER, runner_revision=RUNNER_REVISION, generated_at_utc=utc_now(),
                   status=status, outcome=classification, criteria=criteria,
                   criteria_passed=passed, criteria_total=len(criteria), output_dir=str(output_dir),
                   v26_rmse_mean=round(rmse_mean,2), v26_rmse_median=round(rmse_med,2),
                   v23_baseline=V23_BASELINE_RMSE, best_model=BEST_MODEL_RMSE,
                   beats_v23=beats_v23, beats_best=beats_best)
    write_json(output_dir / "tier7_7z_r2_results.json", payload)
    write_rows(output_dir / "tier7_7z_r2_scoreboard.csv", results)
    write_rows(output_dir / "tier7_7z_r2_summary.csv", criteria)
    report = ["# Tier 7.7z-r2 v2.6 C-MAPSS FD001 Adapter Rerun",
              f"- Status: **{status.upper()}** ({passed}/{len(criteria)})",
              f"- Outcome: `{classification}`",
              f"- v2.6 RMSE: {rmse_mean:.2f} (median {rmse_med:.2f})",
              f"- v2.3 RMSE: 49.49", f"- Best: 46.11",
              f"- Beats v2.3: {beats_v23}", f"- Beats best: {beats_best}"]
    (output_dir / "tier7_7z_r2_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    manifest = dict(tier=TIER, status=status, generated_at_utc=payload["generated_at_utc"], output_dir=str(output_dir))
    write_json(output_dir / "tier7_7z_r2_latest_manifest.json", manifest)
    return payload


def build_parser():
    p = argparse.ArgumentParser(description=TIER)
    p.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    p.add_argument("--seeds", default="42,43,44")
    p.add_argument("--hidden", type=int, default=128)
    return p


def main():
    args = build_parser().parse_args()
    payload = run(args)
    print(json.dumps(json_safe(dict(status=payload["status"], outcome=payload["outcome"],
                                    criteria=f"{payload['criteria_passed']}/{payload['criteria_total']}",
                                    v26_rmse=payload["v26_rmse_mean"],
                                    beats_v23=payload["beats_v23"],
                                    beats_best=payload["beats_best"],
                                    output_dir=payload["output_dir"])), indent=2, sort_keys=True))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
