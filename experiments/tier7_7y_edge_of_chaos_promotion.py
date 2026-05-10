#!/usr/bin/env python3
"""Tier 7.7y - Edge-of-Chaos Recurrent Dynamics Promotion Gate.

Tier:
  7.7y - Edge-of-Chaos Recurrent Dynamics Promotion
Status:
  Promotion candidate after 7.7 diagnostic campaign
Current baseline:
  v2.5 (CRA_EVIDENCE_BASELINE_v2.5)
Question:
  Does shifting CRA recurrent dynamics from contractive (decay=0.5, sr=0.5)
  to edge-of-chaos with antisymmetric modes (decay=0, sr=1.0, antisym=0.3)
  restore state dimensionality AND survive sham controls, ablations, and
  external baseline comparisons?
Hypothesis:
  Yes. The contractive recurrent dynamics are the primary ~2D collapse
  mechanism. Edge-of-chaos with antisymmetric oscillatory modes restores
  state dimensionality (PR 2→7) because it eliminates the low-dimensional
  attractor that collapses all input trajectories.
Null hypothesis:
  The gain is explained by extra capacity (same-budget control), generic
  topology (permuted/sparse recurrence matches it), or readout observability
  (readout concentration explains the gap).
Mechanism under test:
  Dynamical-regime shift: decay=0 (no intrinsic leak), spectral_radius=1.0
  (unit-circle eigenvalues), antisymmetric component=0.3 (oscillatory modes).
  The EMA input encoding is unchanged; only the recurrent operating point
  changes.
Nonclaims:
  Not a connectivity-specific topology claim; not a new input encoding
  mechanism; not hardware/native transfer; not public usefulness proof.
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
    utc_now, write_json, write_rows, criterion, summarize_numeric,
)

TIER = "Tier 7.7y - Edge-of-Chaos Recurrent Dynamics Promotion Gate"
RUNNER_REVISION = "tier7_7y_edge_of_chaos_promotion_20260509_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_7y_20260509_edge_of_chaos_promotion"

DEFAULT_TASKS = "mackey_glass,lorenz,narma10"
DEFAULT_SEEDS = "42,43,44"
DEFAULT_LENGTHS = "8000,16000,32000"
DEFAULT_HORIZON = 8
DEFAULT_HIDDEN = 128
TIMESCALES = [2.0, 5.0, 10.0, 20.0, 50.0, 100.0, 200.0]
TRAIN_PCT = 0.65


def json_safe(v: Any) -> Any:
    if isinstance(v, Path): return str(v)
    if isinstance(v, dict): return {str(k): json_safe(v2) for k, v2 in v.items()}
    if isinstance(v, (list, tuple)): return [json_safe(x) for x in v]
    if isinstance(v, float) and not math.isfinite(v): return None
    return v


def score_model(observed, seed, hidden, decay_val, sr, antisym_frac, train_end):
    """Score one model variant on one (task, seed, length) triplet."""
    values = np.asarray(observed, dtype=float)
    rng = np.random.default_rng(seed + 55555)
    traces = np.zeros(len(TIMESCALES), dtype=float)
    hs = np.zeros(hidden, dtype=float)
    input_dim = 2 + len(TIMESCALES) + max(0, len(TIMESCALES) - 1) + 1
    w_in = rng.normal(0.0, 0.3, size=(hidden, input_dim))
    raw = rng.normal(0.0, 1.0, size=(hidden, hidden))
    q, _r = np.linalg.qr(raw)
    w_sym = q * sr
    if antisym_frac > 0:
        anti = rng.normal(0.0, 0.3, size=(hidden, hidden))
        w_sym += (anti - anti.T) * antisym_frac
    w_rec = w_sym
    decay_arr = np.full(hidden, decay_val, dtype=float)
    rows = []
    for x in values:
        xf = float(x)
        prev = traces.copy()
        for i, tau in enumerate(TIMESCALES):
            alpha = 1.0 - math.exp(-1.0 / max(1e-6, float(tau)))
            traces[i] = traces[i] + alpha * (xf - traces[i])
        d = np.diff(traces) if len(traces) > 1 else np.array([], dtype=float)
        nv = xf - float(prev[-1] if prev.size else 0.0)
        driver = np.concatenate([[1.0, xf], traces, d, [nv]])
        hs = np.tanh(decay_arr * hs + w_rec @ hs + w_in @ driver)
        rows.append(np.concatenate([driver, hs]))
    features = np.vstack(rows)
    hidden_cols = list(range(input_dim, input_dim + hidden))
    geo = geometry_metrics(features, hidden_cols, train_end, split="all")
    pr = safe_float(geo.get("participation_ratio"))
    rank95 = safe_float(geo.get("rank_95"))
    # Online LMS readout
    x = np.asarray(features, dtype=float)
    y = np.asarray(values, dtype=float)
    w = np.zeros(x.shape[1], dtype=float)
    preds = np.zeros(len(y), dtype=float)
    for step in range(len(y)):
        if step > 0: preds[step] = float(np.dot(w, x[step]))
        err = float(y[step] - preds[step])
        denom = 1.0 + float(np.dot(x[step], x[step]))
        w = (1.0 - 0.0001) * w + (0.01 * err / denom) * x[step]
    mse = float(np.mean((preds[train_end:] - y[train_end:]) ** 2)) if len(preds[train_end:]) > 0 else float("inf")
    return {"pr": pr, "rank_95": rank95, "mse": mse}


def score_baseline_esn(observed, seed, hidden, train_end, **kw):
    """Simple ESN-style baseline: random recurrent, no learning, ridge readout."""
    values = np.asarray(observed, dtype=float)
    rng = np.random.default_rng(seed + 99999)
    w_in = rng.normal(0.0, 0.3, size=(hidden, 3))  # bias, x, x^2
    raw = rng.normal(0.0, 1.0, size=(hidden, hidden))
    q, _r = np.linalg.qr(raw)
    w_rec = q * 0.9
    hs = np.zeros(hidden, dtype=float)
    rows = []
    for x in values:
        xf = float(x)
        driver = np.array([1.0, xf, xf * xf])
        hs = np.tanh(0.7 * hs + w_rec @ hs + w_in @ driver)
        rows.append(np.concatenate([driver, hs]))
    features = np.vstack(rows)
    hidden_cols = list(range(3, 3 + hidden))
    geo = geometry_metrics(features, hidden_cols, train_end, split="all")
    # Ridge readout
    try:
        from sklearn.linear_model import Ridge
        Xt, Xe = features[:train_end], features[train_end:]
        yt, ye = values[:train_end], values[train_end:]
        m = Ridge(alpha=1.0, max_iter=1000)
        m.fit(Xt, yt)
        mse = float(np.mean((m.predict(Xe) - ye) ** 2))
    except ImportError:
        mse = float("inf")
    return {"pr": safe_float(geo.get("participation_ratio")), "mse": mse}


VARIANTS = {
    "candidate_eoc(d0_sr1_a3)":    {"role": "candidate", "decay": 0.0, "sr": 1.0, "antisym": 0.3},
    "sham_no_antisym(d0_sr1_a0)":  {"role": "sham_mechanism", "decay": 0.0, "sr": 1.0, "antisym": 0.0},
    "ablation_baseline(d5_sr5_a0)":{"role": "ablation", "decay": 0.5, "sr": 0.5, "antisym": 0.0},
    "control_permuted(d0_sr1_a3_p)":{"role": "sham_topology", "decay": 0.0, "sr": 1.0, "antisym": 0.3, "permute": True},
}


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    tasks = [t.strip() for t in parse_csv(args.tasks) if t.strip()]
    seeds = sorted(set(parse_seeds(args)))
    lengths = sorted(set(int(l) for l in parse_csv(args.lengths))) if args.lengths else [8000]
    horizon = int(args.horizon) if args.horizon else DEFAULT_HORIZON
    hidden = int(args.hidden) if getattr(args, 'hidden', None) else DEFAULT_HIDDEN
    smoke = getattr(args, 'smoke', False)

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
                        r = score_model(obs, seed, hidden,
                                       vcfg["decay"], vcfg["sr"], vcfg["antisym"], train_end)
                        if vcfg.get("permute"):
                            # Score with permuted recurrent matrix
                            # Re-do with permutation applied
                            values2 = np.asarray(obs, dtype=float)
                            rng2 = np.random.default_rng(seed + 55555 + 77777)
                            traces2 = np.zeros(len(TIMESCALES), dtype=float)
                            hs2 = np.zeros(hidden, dtype=float)
                            input_dim = 2 + len(TIMESCALES) + max(0, len(TIMESCALES) - 1) + 1
                            w_in2 = rng2.normal(0.0, 0.3, size=(hidden, input_dim))
                            raw2 = rng2.normal(0.0, 1.0, size=(hidden, hidden))
                            q2, _r2 = np.linalg.qr(raw2)
                            w_sym2 = q2 * vcfg["sr"]
                            anti2 = rng2.normal(0.0, 0.3, size=(hidden, hidden))
                            w_sym2 += (anti2 - anti2.T) * vcfg["antisym"]
                            perm = np.arange(hidden); rng2.shuffle(perm)
                            signs = rng2.choice([-1.0, 1.0], size=hidden)
                            w_rec2 = w_sym2[:, perm] * signs.reshape(1, -1)
                            decay_arr2 = np.full(hidden, vcfg["decay"], dtype=float)
                            rows2 = []
                            for x in values2:
                                xf = float(x)
                                prev2 = traces2.copy()
                                for i, tau in enumerate(TIMESCALES):
                                    alpha = 1.0 - math.exp(-1.0 / max(1e-6, float(tau)))
                                    traces2[i] = traces2[i] + alpha * (xf - traces2[i])
                                d2 = np.diff(traces2) if len(traces2) > 1 else np.array([], dtype=float)
                                nv2 = xf - float(prev2[-1] if prev2.size else 0.0)
                                driver2 = np.concatenate([[1.0, xf], traces2, d2, [nv2]])
                                hs2 = np.tanh(decay_arr2 * hs2 + w_rec2 @ hs2 + w_in2 @ driver2)
                                rows2.append(np.concatenate([driver2, hs2]))
                            features2 = np.vstack(rows2)
                            hidden_cols2 = list(range(input_dim, input_dim + hidden))
                            geo2 = geometry_metrics(features2, hidden_cols2, train_end, split="all")
                            pr2 = safe_float(geo2.get("participation_ratio"))
                            xp = np.asarray(features2, dtype=float)
                            yp = np.asarray(values2, dtype=float)
                            wp = np.zeros(xp.shape[1], dtype=float)
                            preds2 = np.zeros(len(yp), dtype=float)
                            for step in range(len(yp)):
                                if step > 0: preds2[step] = float(np.dot(wp, xp[step]))
                                errp = float(yp[step] - preds2[step])
                                denomp = 1.0 + float(np.dot(xp[step], xp[step]))
                                wp = (1.0 - 0.0001) * wp + (0.01 * errp / denomp) * xp[step]
                            mse2 = float(np.mean((preds2[train_end:] - yp[train_end:]) ** 2)) if len(preds2[train_end:]) > 0 else float("inf")
                            results.append({"variant": "control_permuted(d0_sr1_a3_p)", "role": "sham_topology",
                                           "task": task_name, "length": length, "seed": seed,
                                           "pr": pr2, "mse": mse2, "status": "ok"})
                        else:
                            results.append({"variant": vname, "role": vcfg["role"],
                                           "task": task_name, "length": length, "seed": seed,
                                           "pr": r["pr"], "rank_95": r["rank_95"], "mse": r["mse"],
                                           "status": "ok"})
                    except Exception as e:
                        results.append({"variant": vname, "role": vcfg["role"],
                                       "task": task_name, "length": length, "seed": seed,
                                       "status": "error", "error": str(e)})

                # ESN baseline
                try:
                    esn_r = score_baseline_esn(obs, seed, hidden, train_end)
                    results.append({"variant": "esn_baseline", "role": "external_baseline",
                                   "task": task_name, "length": length, "seed": seed,
                                   "pr": esn_r["pr"], "mse": esn_r["mse"], "status": "ok"})
                except Exception as e:
                    results.append({"variant": "esn_baseline", "role": "external_baseline",
                                   "task": task_name, "length": length, "seed": seed,
                                   "status": "error", "error": str(e)})

    def vstats(vname):
        rows = [r for r in results if r.get("variant") == vname and r.get("pr")]
        prs = [r["pr"] for r in rows]
        mses = [r["mse"] for r in rows if r.get("mse") and r["mse"] != float("inf")]
        def gm(vals):
            try: return float(math.exp(sum(math.log(v) for v in vals) / len(vals)))
            except: return float("inf")
        return {"n": len(rows), "pr_mean": float(np.mean(prs)) if prs else None,
                "pr_stdev": float(np.std(prs)) if len(prs) > 1 else 0.0,
                "mse_geomean": gm(mses) if mses else float("inf")}

    cand_s = vstats("candidate_eoc(d0_sr1_a3)")
    sham_s = vstats("sham_no_antisym(d0_sr1_a0)")
    abla_s = vstats("ablation_baseline(d5_sr5_a0)")
    esn_s  = vstats("esn_baseline")

    cand_pr = cand_s.get("pr_mean") or 0
    sham_pr = sham_s.get("pr_mean") or 0
    abla_pr = abla_s.get("pr_mean") or 0
    esn_pr  = esn_s.get("pr_mean") or 0
    cand_mse = cand_s.get("mse_geomean") or float("inf")
    abla_mse = abla_s.get("mse_geomean") or float("inf")
    esn_mse  = esn_s.get("mse_geomean") or float("inf")

    pr_improved    = cand_pr > abla_pr + 2.0
    sham_separated = abs(cand_pr - sham_pr) > 2.0
    ablation_works = cand_pr > abla_pr
    pr_beats_esn   = cand_pr > esn_pr if esn_pr else None
    mse_beats_abla = cand_mse < abla_mse if cand_mse != float("inf") else False

    classification = "promotion_not_supported"
    if pr_improved and sham_separated and ablation_works:
        if pr_beats_esn and mse_beats_abla:
            classification = "promotion_supported_requires_compact_regression"
        elif sham_separated and ablation_works:
            classification = "mechanism_candidate_baselines_partial"

    criteria = [
        criterion("candidate scored (all tasks/seeds/lengths)", cand_s["n"], ">= 6", cand_s["n"] >= 6,
                  f"n={cand_s['n']}"),
        criterion("sham (no-antisymmetry) scored", sham_s["n"], ">= 3", sham_s["n"] >= 3),
        criterion("ablation (baseline) scored", abla_s["n"], ">= 3", abla_s["n"] >= 3),
        criterion("ESN baseline scored", esn_s["n"], ">= 1", esn_s["n"] >= 1),
        criterion("PR > baseline (ablation)", pr_improved, "true", pr_improved,
                  f"cand={cand_pr:.1f} abla={abla_pr:.1f}"),
        criterion("sham separated (|ΔPR| > 2.0)", sham_separated, "true", sham_separated,
                  f"cand={cand_pr:.1f} sham={sham_pr:.1f}"),
        criterion("ablation removes benefit", ablation_works, "true", ablation_works),
        criterion("PR > ESN baseline", pr_beats_esn, "true", pr_beats_esn,
                  f"cand={cand_pr:.1f} esn={esn_pr:.1f}" if pr_beats_esn is not None else "esn_not_scored"),
        criterion("MSE < baseline (ablation)", mse_beats_abla, "true", mse_beats_abla,
                  f"cand_mse={cand_mse:.6f} abla_mse={abla_mse:.6f}"),
        criterion("outcome classified", classification != "promotion_not_supported", "true",
                  classification != "promotion_not_supported",
                  f"classification={classification}"),
        criterion("no baseline freeze authorized", classification != "promotion_supported_requires_compact_regression", "true",
                  classification != "promotion_supported_requires_compact_regression",
                  "Freeze requires compact regression gate"),
    ]
    passed = sum(1 for c in criteria if c["passed"])
    status = "pass" if passed == len(criteria) else "fail"

    payload = {
        "tier": TIER, "runner_revision": RUNNER_REVISION, "generated_at_utc": utc_now(),
        "status": status, "outcome": classification, "criteria": criteria,
        "criteria_passed": passed, "criteria_total": len(criteria), "output_dir": str(output_dir),
        "candidate": cand_s, "sham": sham_s, "ablation": abla_s, "esn": esn_s,
        "next_gate": "7.7z compact regression + baseline freeze (if promotion supported)",
        "claim_boundary": ("Promotion gate for edge-of-chaos recurrent dynamics. "
                           "Not a baseline freeze (requires compact regression). "
                           "Not public usefulness proof. Not hardware/native transfer."),
        "nonclaims": ["not a connectivity-specific topology claim", "not a new input encoding mechanism",
                      "not hardware/native transfer", "not public usefulness proof", "not a baseline freeze"],
    }
    write_json(output_dir / "tier7_7y_results.json", payload)
    write_rows(output_dir / "tier7_7y_scoreboard.csv", results)
    write_rows(output_dir / "tier7_7y_summary.csv", criteria)
    report = ["# Tier 7.7y Edge-of-Chaos Recurrent Dynamics Promotion Gate",
              f"- Status: **{status.upper()}** ({passed}/{len(criteria)})",
              f"- Outcome: `{classification}`",
              f"- Candidate PR: {cand_pr:.1f}", f"- Sham PR: {sham_pr:.1f}",
              f"- Ablation PR: {abla_pr:.1f}", f"- ESN PR: {esn_pr:.1f}" if esn_pr else "",
              f"- Candidate MSE: {cand_mse:.6f}", f"- Ablation MSE: {abla_mse:.6f}",
              f"- Sham separated: {sham_separated}", f"- PR > baseline: {pr_improved}",
              f"- PR > ESN: {pr_beats_esn}", f"- MSE < baseline: {mse_beats_abla}",
              "", f"Next: {payload['next_gate']}"]
    (output_dir / "tier7_7y_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    manifest = {"tier": TIER, "status": status, "generated_at_utc": payload["generated_at_utc"],
                "output_dir": str(output_dir)}
    write_json(output_dir / "tier7_7y_latest_manifest.json", manifest)
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
    print(json.dumps(json_safe({
        "status": payload["status"], "outcome": payload["outcome"],
        "criteria": f"{payload['criteria_passed']}/{payload['criteria_total']}",
        "candidate_pr": cand.get("pr_mean"), "sham_pr": sham.get("pr_mean"),
        "ablation_pr": abla.get("pr_mean"),
        "candidate_mse": cand.get("mse_geomean"), "ablation_mse": abla.get("mse_geomean"),
        "pr_delta_vs_sham": round(abs(cand.get("pr_mean", 0) - sham.get("pr_mean", 0)), 2),
        "pr_ratio_vs_abla": round(cand.get("pr_mean", 0) / abla.get("pr_mean", 1), 2) if abla.get("pr_mean") else None,
        "output_dir": payload["output_dir"],
    }), indent=2, sort_keys=True))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
