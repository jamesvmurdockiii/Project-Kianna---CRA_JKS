#!/usr/bin/env python3
"""Tier 7.7z - Edge-of-Chaos Recurrent Dynamics Promotion Gate (Ridge Readout).

After 7.7y confirmed edge-of-chaos dynamics restore state dimensionality
(PR 2→7, sham separated) but online LMS couldn't use the extra dimensions,
this gate tests the same mechanism with ridge regression readout.

Tier: 7.7z - Edge-of-Chaos Promotion (Ridge Readout)
Question: Does the higher-dimensional state from edge-of-chaos dynamics
  translate to improved prediction under a regularized readout?
Hypothesis: Yes. Ridge regularization can exploit the extra state dimensions
  that online LMS discards as noise.
Claim boundary: Bounded mechanism evidence for edge-of-chaos recurrent
  dynamics with ridge readout. Not a baseline freeze (requires compact
  regression). Not public usefulness proof. Not hardware/native transfer.
"""

from __future__ import annotations
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
    utc_now, write_json, write_rows, criterion,
)

TIER = "Tier 7.7z - Edge-of-Chaos Promotion (Ridge Readout)"
RUNNER_REVISION = "tier7_7z_edge_of_chaos_ridge_promotion_20260509_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_7z_20260509_edge_of_chaos_ridge_promotion"
PREREQ_7_7Y = CONTROLLED / "tier7_7y_20260509_edge_of_chaos_promotion" / "tier7_7y_results.json"

TIMESCALES = [2.0, 5.0, 10.0, 20.0, 50.0, 100.0, 200.0]
DEFAULT_HIDDEN = 128
DEFAULT_LENGTH = 8000
DEFAULT_HORIZON = 8
DEFAULT_TASKS = "mackey_glass,lorenz,narma10"
DEFAULT_SEEDS = "42,43,44"
DEFAULT_LENGTHS = "8000,16000,32000"
TRAIN_PCT = 0.65


def json_safe(v: Any) -> Any:
    if isinstance(v, Path): return str(v)
    if isinstance(v, dict): return {str(k): json_safe(v2) for k, v2 in v.items()}
    if isinstance(v, (list, tuple)): return [json_safe(x) for x in v]
    if isinstance(v, float) and not math.isfinite(v): return None
    return v


def ridge(X, y, alpha=1.0):
    n, p = X.shape
    try:
        w = np.linalg.solve(X.T @ X + alpha * np.eye(p), X.T @ y)
    except np.linalg.LinAlgError:
        w = np.linalg.lstsq(X.T @ X + alpha * np.eye(p), X.T @ y, rcond=None)[0]
    return w


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
    features = np.vstack(rows)
    hidden_cols = list(range(input_dim, input_dim + hidden))
    return features, hidden_cols, values


VARIANTS = {
    "candidate_eoc(d0_sr1_a3)":   {"role": "candidate", "decay": 0.0, "sr": 1.0, "antisym": 0.3},
    "sham_no_antisym(d0_sr1_a0)": {"role": "sham",       "decay": 0.0, "sr": 1.0, "antisym": 0.0},
    "ablation_baseline(d5_sr5)":  {"role": "ablation",   "decay": 0.5, "sr": 0.5, "antisym": 0.0},
}


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    tasks = [t.strip() for t in parse_csv(args.tasks) if t.strip()]
    seeds = sorted(set(parse_seeds(args)))
    lengths = sorted(set(int(l) for l in parse_csv(args.lengths))) if args.lengths else [8000]
    horizon = int(args.horizon) if args.horizon else DEFAULT_HORIZON
    hidden = int(args.hidden) if getattr(args, 'hidden', None) else DEFAULT_HIDDEN

    results: list[dict[str, Any]] = []
    for task_name in tasks:
        for length in lengths:
            train_end = int(length * TRAIN_PCT)
            for seed in seeds:
                task = build_task(task_name, length, seed, horizon)
                if task is None or not hasattr(task, "observed"): continue
                obs = task.observed[:length]

                for vname, vcfg in VARIANTS.items():
                    try:
                        features, hidden_cols, tgt = compute_features(
                            obs, seed, hidden, vcfg["decay"], vcfg["sr"], vcfg["antisym"])
                        geo = geometry_metrics(features, hidden_cols, train_end, split="all")
                        pr = safe_float(geo.get("participation_ratio"))
                        w = ridge(features[:train_end], tgt[:train_end], 1.0)
                        mse = float(np.mean((features[train_end:] @ w - tgt[train_end:]) ** 2))
                        results.append({"variant": vname, "role": vcfg["role"],
                                       "task": task_name, "length": length, "seed": seed,
                                       "pr": pr, "mse": mse, "status": "ok"})
                    except Exception as e:
                        results.append({"variant": vname, "role": vcfg["role"],
                                       "task": task_name, "length": length, "seed": seed,
                                       "status": "error", "error": str(e)})

    def vstats(vname):
        rows = [r for r in results if r.get("variant") == vname and r.get("pr")]
        prs = [r["pr"] for r in rows]
        mses = [r["mse"] for r in rows if r.get("mse") and r["mse"] != float("inf")]
        gm = float(math.exp(sum(math.log(v) for v in mses) / len(mses))) if mses else float("inf")
        return {"n": len(rows), "pr_mean": float(np.mean(prs)) if prs else None,
                "pr_stdev": float(np.std(prs)) if len(prs) > 1 else 0.0,
                "mse_geomean": gm}

    cand_s = vstats("candidate_eoc(d0_sr1_a3)")
    sham_s = vstats("sham_no_antisym(d0_sr1_a0)")
    abla_s = vstats("ablation_baseline(d5_sr5)")

    cand_pr = cand_s.get("pr_mean") or 0
    sham_pr = sham_s.get("pr_mean") or 0
    abla_pr = abla_s.get("pr_mean") or 0
    cand_mse = cand_s.get("mse_geomean") or float("inf")
    abla_mse = abla_s.get("mse_geomean") or float("inf")

    pr_improved    = cand_pr > abla_pr + 2.0
    sham_separated = abs(cand_pr - sham_pr) > 2.0
    ablation_works = cand_pr > abla_pr
    mse_beats_abla = cand_mse < abla_mse

    pr_ratio = cand_pr / abla_pr if abla_pr else 0
    mse_ratio = cand_mse / abla_mse if abla_mse and abla_mse != float("inf") else 0

    classification = "promotion_not_supported"
    if pr_improved and sham_separated and ablation_works and mse_beats_abla:
        classification = "promotion_supported_requires_compact_regression"
    elif pr_improved and sham_separated and mse_beats_abla:
        classification = "promotion_supported_requires_compact_regression"
    elif pr_improved and sham_separated:
        classification = "mechanism_candidate_mse_partial"

    criteria = [
        criterion("candidate scored", cand_s["n"], ">= 6", cand_s["n"] >= 6, f"n={cand_s['n']}"),
        criterion("sham (no-antisymmetry) scored", sham_s["n"], ">= 3", sham_s["n"] >= 3),
        criterion("ablation (baseline) scored", abla_s["n"], ">= 3", abla_s["n"] >= 3),
        criterion("PR > ablation (+2.0)", pr_improved, "true", pr_improved,
                  f"cand={cand_pr:.1f} abla={abla_pr:.1f} ratio={pr_ratio:.1f}x"),
        criterion("sham separated (|ΔPR|>2.0)", sham_separated, "true", sham_separated,
                  f"cand={cand_pr:.1f} sham={sham_pr:.1f} Δ={abs(cand_pr-sham_pr):.1f}"),
        criterion("ablation confirms benefit", ablation_works, "true", ablation_works),
        criterion("MSE < ablation (ridge readout)", mse_beats_abla, "true", mse_beats_abla,
                  f"cand={cand_mse:.6f} abla={abla_mse:.6f} ratio={mse_ratio:.4f}"),
        criterion("sham MSE > candidate MSE", sham_s.get("mse_geomean", float("inf")) > cand_mse, "true",
                  sham_s.get("mse_geomean", float("inf")) > cand_mse if sham_s.get("mse_geomean") else False,
                  f"sham_mse={sham_s.get('mse_geomean')}"),
        criterion("outcome classified", classification != "promotion_not_supported", "true",
                  classification != "promotion_not_supported", f"classification={classification}"),
        criterion("no baseline freeze authorized yet", classification != "promotion_supported_requires_compact_regression", "true",
                  classification != "promotion_supported_requires_compact_regression",
                  "Freeze requires compact regression gate"),
    ]
    passed = sum(1 for c in criteria if c["passed"])
    status = "pass" if passed == len(criteria) else "fail"

    payload = dict(tier=TIER, runner_revision=RUNNER_REVISION, generated_at_utc=utc_now(),
                   status=status, outcome=classification, criteria=criteria,
                   criteria_passed=passed, criteria_total=len(criteria), output_dir=str(output_dir),
                   candidate=cand_s, sham=sham_s, ablation=abla_s,
                   pr_ratio=round(pr_ratio, 2), mse_ratio=round(mse_ratio, 4),
                   next_gate="7.7z-r0 compact regression + baseline freeze" if classification == "promotion_supported_requires_compact_regression" else "Diagnose narrowing",
                   claim_boundary="Bounded mechanism evidence for edge-of-chaos recurrent dynamics with ridge readout. Not a baseline freeze (requires compact regression). Not public usefulness proof. Not hardware/native transfer.")
    write_json(output_dir / "tier7_7z_results.json", payload)
    write_rows(output_dir / "tier7_7z_scoreboard.csv", results)
    write_rows(output_dir / "tier7_7z_summary.csv", criteria)
    report = ["# Tier 7.7z Edge-of-Chaos Promotion (Ridge Readout)",
              f"- Status: **{status.upper()}** ({passed}/{len(criteria)})",
              f"- Outcome: `{classification}`",
              f"- Candidate PR: {cand_pr:.1f} ({pr_ratio:.1f}x ablation)", f"- Sham PR: {sham_pr:.1f}",
              f"- Ablation PR: {abla_pr:.1f}",
              f"- Candidate MSE: {cand_mse:.6f}", f"- Ablation MSE: {abla_mse:.6f}",
              f"- MSE ratio: {mse_ratio:.4f}",
              f"- PR improved: {pr_improved}", f"- Sham separated: {sham_separated}",
              f"- MSE < ablation: {mse_beats_abla}",
              "", f"Next: {payload['next_gate']}"]
    (output_dir / "tier7_7z_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    manifest = dict(tier=TIER, status=status, generated_at_utc=payload["generated_at_utc"],
                    output_dir=str(output_dir))
    write_json(output_dir / "tier7_7z_latest_manifest.json", manifest)
    return payload


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=TIER)
    p.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    p.add_argument("--tasks", default=DEFAULT_TASKS)
    p.add_argument("--seeds", default=DEFAULT_SEEDS)
    p.add_argument("--lengths", default=DEFAULT_LENGTHS)
    p.add_argument("--horizon", type=int, default=DEFAULT_HORIZON)
    p.add_argument("--hidden", type=int, default=DEFAULT_HIDDEN)
    p.add_argument("--smoke", action="store_true", default=False)
    return p


def main() -> int:
    args = build_parser().parse_args()
    if getattr(args, 'smoke', False): args.seeds = "42"; args.lengths = "8000"
    payload = run(args)
    cand = payload["candidate"]; sham = payload["sham"]; abla = payload["ablation"]
    print(json.dumps(json_safe(dict(
        status=payload["status"], outcome=payload["outcome"],
        criteria=f"{payload['criteria_passed']}/{payload['criteria_total']}",
        candidate_pr=cand.get("pr_mean"), sham_pr=sham.get("pr_mean"),
        ablation_pr=abla.get("pr_mean"),
        candidate_mse=cand.get("mse_geomean"), ablation_mse=abla.get("mse_geomean"),
        pr_ratio=payload["pr_ratio"], mse_ratio=payload["mse_ratio"],
        output_dir=payload["output_dir"])), indent=2, sort_keys=True))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
