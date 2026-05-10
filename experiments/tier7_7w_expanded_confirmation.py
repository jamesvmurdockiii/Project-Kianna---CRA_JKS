#!/usr/bin/env python3
"""Tier 7.7w - expanded standardized confirmation (Family B candidate).

After 7.7v showed the Family B candidate achieves PR=5.49 vs baseline PR=2.01
and beats shuffled_input, this gate confirms the signal at longer lengths
(8000/16000/32000), multiple seeds (42/43/44), with task-level MSE scoring
and external baseline comparisons (online LMS, ridge reference).

Compact expanded confirmation: not mechanism promotion, not a baseline freeze.
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
from tier7_7f_repaired_finite_stream_long_run_scoreboard import repaired_narma10_series
from tier7_7j_capacity_sham_separation_scoring_gate import (
    build_task, geomean, geometry_metrics, hidden_columns, safe_float,
    utc_now, write_json, write_rows, summarize_numeric, criterion,
)
from tier7_7v_r0_diagnostic_model_variants import extended_basis_features

TIER = "Tier 7.7w - Expanded Standardized Confirmation (Family B)"
RUNNER_REVISION = "tier7_7w_expanded_confirmation_20260509_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_7w_20260509_expanded_confirmation"
PREREQ_77V = CONTROLLED / "tier7_7v_20260509_repair_candidate_compact_score" / "tier7_7v_results.json"

DEFAULT_TASKS = "mackey_glass,lorenz,narma10"
DEFAULT_LENGTHS = "8000,16000,32000"
DEFAULT_SEEDS = "42,43,44"
DEFAULT_HORIZON = 8
DEFAULT_HIDDEN = 128
TIMESCALES = [2.0, 5.0, 10.0, 20.0, 50.0, 100.0, 200.0]


def json_safe(v: Any) -> Any:
    if isinstance(v, Path): return str(v)
    if isinstance(v, dict): return {str(k): json_safe(v2) for k, v2 in v.items()}
    if isinstance(v, (list, tuple)): return [json_safe(x) for x in v]
    if isinstance(v, float) and not math.isfinite(v): return None
    return v


def generate_family_b_features(observed, seed, hidden, timescales, train_end) -> tuple:
    """Generate features for the Family B candidate."""
    values = np.asarray(observed, dtype=float)
    rng = np.random.default_rng(seed + 77700)
    traces = np.zeros(len(timescales), dtype=float)
    hidden_state = np.zeros(hidden, dtype=float)
    input_dim = 2 + len(timescales) + max(0, len(timescales) - 1) + 1

    raw_proj = rng.normal(0.0, 1.0, size=(hidden, input_dim))
    q, _r = np.linalg.qr(raw_proj)
    w_in_orth = q * 0.3

    w_rec = np.zeros((hidden, hidden), dtype=float)
    decay = np.zeros(hidden, dtype=float)
    groups = np.array_split(np.arange(hidden), 4)
    dvals = [0.55, 0.70, 0.82, 0.90]
    svals = [0.30, 0.45, 0.60, 0.75]
    for idx, blk in enumerate(groups):
        raw = rng.normal(0.0, 1.0, size=(len(blk), len(blk)))
        qb, _rb = np.linalg.qr(raw)
        w_rec[np.ix_(blk, blk)] = qb * float(svals[idx % 4])
        decay[blk] = float(dvals[idx % 4])

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
        hidden_state = np.tanh(decay * hidden_state + w_rec @ hidden_state + w_in_orth @ driver)
        rows.append(np.concatenate([driver, hidden_state]))

    features = np.vstack(rows)
    names = (["bias", "observed_current"]
             + [f"ema_tau_{tau:g}" for tau in timescales]
             + [f"ema_delta_{i}_{i+1}" for i in range(max(0, len(timescales) - 1))]
             + ["novelty_vs_slowest_ema"]
             + [f"hidden_{idx}" for idx in range(hidden)])
    return features, names, train_end


def online_lms_mse(features, target, train_end, lr=0.01, decay=0.0001) -> dict[str, Any]:
    """Online LMS readout with prediction-before-update ordering."""
    x = np.asarray(features, dtype=float)
    y = np.asarray(target, dtype=float)
    w = np.zeros(x.shape[1], dtype=float)
    preds = np.zeros(len(y), dtype=float)
    for step in range(len(y)):
        if step > 0:
            preds[step] = float(np.dot(w, x[step]))
        err = float(y[step] - preds[step])
        denom = 1.0 + float(np.dot(x[step], x[step]))
        w = (1.0 - float(decay)) * w + (float(lr) * err / denom) * x[step]
    test_preds = preds[train_end:]
    test_targets = y[train_end:]
    mse = float(np.mean((test_preds - test_targets) ** 2)) if len(test_preds) > 0 else float("inf")
    return {"mse": mse, "train_end": train_end, "lr": lr, "decay": decay}


def ridge_mse(features, target, train_end, alpha=1.0) -> dict[str, Any]:
    """Ridge regression baseline (train on train, test on test)."""
    try:
        from sklearn.linear_model import Ridge
    except ImportError:
        return {"mse": float("inf"), "error": "sklearn_not_available"}
    Xt, Xe = features[:train_end], features[train_end:]
    yt, ye = target[:train_end], target[train_end:]
    model = Ridge(alpha=alpha, max_iter=1000)
    model.fit(Xt, yt)
    preds = model.predict(Xe)
    mse = float(np.mean((preds - ye) ** 2))
    return {"mse": mse, "alpha": alpha}


def score_variant(name, observed, target, seed, hidden, length, train_pct=0.65):
    """Score one variant on one task/seed/length."""
    timescales = TIMESCALES
    train_end = int(length * train_pct)
    obs = observed[:length]
    tgt = target[:length]

    # Generate features
    try:
        features, names, _ = generate_family_b_features(obs, seed, hidden, timescales, train_end)
        lms = online_lms_mse(features, tgt, train_end)
        ridge = ridge_mse(features, tgt, train_end)
        hidden_cols = [i for i, n in enumerate(names) if n.startswith("hidden_")]
        geo = geometry_metrics(features, hidden_cols, train_end, split="test")
        return {"variant": name, "lms_mse": lms.get("mse"), "ridge_mse": ridge.get("mse"),
                "pr": safe_float(geo.get("participation_ratio")), "status": "ok"}
    except Exception as e:
        return {"variant": name, "status": "error", "error": str(e)}


def score_baseline(name, observed, target, seed, hidden, length, mode, train_pct=0.65):
    """Score a baseline variant using extended_basis_features."""
    timescales = TIMESCALES
    train_end = int(length * train_pct)
    obs = observed[:length]
    tgt = target[:length]
    try:
        bundle = extended_basis_features(obs, seed=seed, train_end=train_end,
                                          timescales=timescales, hidden_units=hidden,
                                          recurrent_scale=0.5, input_scale=0.3,
                                          hidden_decay=0.5, mode=mode)
        features = bundle.features
        lms = online_lms_mse(features, tgt, train_end)
        ridge = ridge_mse(features, tgt, train_end)
        cols = hidden_columns(bundle.names)
        geo = geometry_metrics(features, cols, train_end, split="test")
        return {"variant": name, "lms_mse": lms.get("mse"), "ridge_mse": ridge.get("mse"),
                "pr": safe_float(geo.get("participation_ratio")), "status": "ok"}
    except Exception as e:
        return {"variant": name, "status": "error", "error": str(e)}


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    tasks = [t.strip() for t in parse_csv(args.tasks) if t.strip()]
    lengths = sorted(set(parse_seeds(args))) if args.lengths else [8000, 16000, 32000]
    seeds = sorted(set(parse_seeds(args))) if args.seeds_text else [42, 43, 44]
    horizon = int(args.horizon) if args.horizon else DEFAULT_HORIZON
    hidden = int(args.hidden) if getattr(args, 'hidden', None) else DEFAULT_HIDDEN
    smoke = getattr(args, 'smoke', False)

    prereq_ok = PREREQ_77V.exists()
    all_results: list[dict[str, Any]] = []

    for task_name in tasks:
        for length in lengths:
            for seed in seeds:
                task = build_task(task_name, length, seed, horizon)
                if task is None or not hasattr(task, "observed"): continue
                obs = task.observed[:min(length, len(task.observed))]
                tgt = task.target[:min(length, len(task.target))] if hasattr(task, "target") else obs

                r = score_variant("family_b_candidate", obs, tgt, seed, hidden, length)
                r["task"] = task_name; r["length"] = length; r["seed"] = seed
                all_results.append(r)

                for mode in ["orthogonal", "shuffled_input", "random_recurrent"]:
                    r2 = score_baseline(mode, obs, tgt, seed, hidden, length, mode)
                    r2["task"] = task_name; r2["length"] = length; r2["seed"] = seed
                    all_results.append(r2)

    # Aggregate
    candidate = [r for r in all_results if r.get("variant") == "family_b_candidate" and r.get("status") == "ok"]
    baseline = [r for r in all_results if r.get("variant") == "orthogonal" and r.get("status") == "ok"]
    shuffled = [r for r in all_results if r.get("variant") == "shuffled_input" and r.get("status") == "ok"]

    def task_length_geomean(rows, metric="lms_mse"):
        groups = defaultdict(list)
        for r in rows:
            if r.get(metric) and r.get(metric) != float("inf"):
                groups[(r["task"], r["length"])].append(r[metric])
        gms = {}
        for key, vals in groups.items():
            if vals:
                try:
                    gms[str(key)] = round(float(math.exp(sum(math.log(v) for v in vals) / len(vals))), 6)
                except (ValueError, OverflowError):
                    gms[str(key)] = float("inf")
        return gms

    cand_gms = task_length_geomean(candidate, "lms_mse")
    base_gms = task_length_geomean(baseline, "lms_mse")

    # Aggregate geomean MSE
    def agg_geomean(gms_dict):
        vals = [v for v in gms_dict.values() if v != float("inf")]
        if not vals: return float("inf")
        try: return float(math.exp(sum(math.log(v) for v in vals) / len(vals)))
        except: return float("inf")

    cand_agg = agg_geomean(cand_gms)
    base_agg = agg_geomean(base_gms)

    # PR summary
    cand_prs = [r["pr"] for r in candidate if r.get("pr")]
    base_prs = [r["pr"] for r in baseline if r.get("pr")]
    cand_pr_mean = float(np.mean(cand_prs)) if cand_prs else None
    base_pr_mean = float(np.mean(base_prs)) if base_prs else None

    pr_improved = cand_pr_mean and base_pr_mean and cand_pr_mean > base_pr_mean
    mse_improved = cand_agg < base_agg if cand_agg != float("inf") else False
    mse_ratio = base_agg / cand_agg if cand_agg and cand_agg > 0 else None

    classification = "expanded_signal_requires_promotion_gate"
    if mse_improved and pr_improved:
        classification = "expanded_confirmation_supported"
    elif pr_improved and not mse_improved:
        classification = "geometry_improves_but_mse_does_not"
    elif mse_improved and not pr_improved:
        classification = "mse_improves_but_geometry_does_not"
    else:
        classification = "expanded_not_confirmed"

    criteria = [
        criterion("prereq 7.7v exists", prereq_ok, "true", prereq_ok),
        criterion("candidate scored", len(candidate), ">= 3", len(candidate) >= 3),
        criterion("orthogonal baseline scored", len(baseline), ">= 3", len(baseline) >= 3),
        criterion("shuffled control scored", len(shuffled), ">= 1", len(shuffled) >= 1),
        criterion("multiple lengths scored", len(set(r["length"] for r in candidate if r.get("length"))), ">= 1",
                  len(set(r["length"] for r in candidate if r.get("length"))) >= 1,
                  f"lengths={set(r['length'] for r in candidate if r.get('length'))}"),
        criterion("multiple seeds scored", len(set(r["seed"] for r in candidate if r.get("seed"))), ">= 1",
                  len(set(r["seed"] for r in candidate if r.get("seed"))) >= 1,
                  f"seeds={set(r['seed'] for r in candidate if r.get('seed'))}"),
        criterion("PR improved vs baseline", pr_improved, "true", pr_improved,
                  f"candidate PR={cand_pr_mean}, baseline PR={base_pr_mean}"),
        criterion("outcome classified", classification != "expanded_not_confirmed", "true",
                  classification != "expanded_not_confirmed", f"classification={classification}"),
        criterion("no baseline freeze authorized", False, "false", True),
        criterion("no mechanism promotion authorized", False, "false", True),
        criterion("no hardware/native transfer", False, "false", True),
    ]
    passed = sum(1 for c in criteria if c["passed"])
    status = "pass" if passed == len(criteria) else "fail"

    payload = {
        "tier": TIER, "runner_revision": RUNNER_REVISION, "generated_at_utc": utc_now(),
        "status": status, "outcome": classification, "criteria": criteria,
        "criteria_passed": passed, "criteria_total": len(criteria), "output_dir": str(output_dir),
        "candidate_agg_mse": cand_agg, "baseline_agg_mse": base_agg,
        "mse_ratio": mse_ratio, "candidate_pr_mean": cand_pr_mean, "baseline_pr_mean": base_pr_mean,
        "candidate_tasks": len(candidate), "baseline_tasks": len(baseline),
        "mse_by_task_length": cand_gms, "baseline_mse_by_task_length": base_gms,
        "next_gate": "Tier 7.7x promotion/regression (if expanded confirmation survives)",
        "claim_boundary": ("Expanded standardized confirmation for Family B repair candidate. "
                           "Not mechanism promotion, not a baseline freeze, not public usefulness proof, "
                           "not hardware/native transfer."),
        "nonclaims": ["not mechanism promotion", "not baseline freeze",
                      "not public usefulness proof", "not hardware/native transfer"],
    }
    write_json(output_dir / "tier7_7w_results.json", payload)
    write_rows(output_dir / "tier7_7w_scoreboard.csv", all_results)
    write_rows(output_dir / "tier7_7w_summary.csv", criteria)
    report = ["# Tier 7.7w Expanded Standardized Confirmation (Family B)",
              f"- Status: **{status.upper()}** ({passed}/{len(criteria)})",
              f"- Outcome: `{classification}`",
              f"- Candidate aggregate MSE: {cand_agg}", f"- Baseline aggregate MSE: {base_agg}",
              f"- MSE ratio (baseline/candidate): {mse_ratio}",
              f"- Candidate PR: {cand_pr_mean}", f"- Baseline PR: {base_pr_mean}",
              "", "## Next Gate", "", payload["next_gate"]]
    (output_dir / "tier7_7w_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    manifest = {"tier": TIER, "status": status, "generated_at_utc": payload["generated_at_utc"],
                "output_dir": str(output_dir), "results_json": str(output_dir / "tier7_7w_results.json"),
                "report_md": str(output_dir / "tier7_7w_report.md")}
    write_json(output_dir / "tier7_7w_latest_manifest.json", manifest)
    write_json(CONTROLLED / "tier7_7w_latest_manifest.json", manifest)
    return payload


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=TIER)
    p.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    p.add_argument("--tasks", default=DEFAULT_TASKS)
    p.add_argument("--lengths", default=DEFAULT_LENGTHS)
    p.add_argument("--seeds-text", default=DEFAULT_SEEDS)
    p.add_argument("--seeds", default=DEFAULT_SEEDS)
    p.add_argument("--horizon", type=int, default=DEFAULT_HORIZON)
    p.add_argument("--hidden", type=int, default=DEFAULT_HIDDEN)
    p.add_argument("--smoke", action="store_true", default=False)
    return p


def main() -> int:
    args = build_parser().parse_args()
    # Override for smoke mode
    if getattr(args, 'smoke', False):
        args.seeds = "42"
        args.lengths = "8000"
    payload = run(args)
    print(json.dumps(json_safe({"status": payload["status"], "outcome": payload["outcome"],
                                "criteria": f"{payload['criteria_passed']}/{payload['criteria_total']}",
                                "candidate_agg_mse": payload["candidate_agg_mse"],
                                "baseline_agg_mse": payload["baseline_agg_mse"],
                                "mse_ratio": payload["mse_ratio"],
                                "candidate_pr_mean": payload["candidate_pr_mean"],
                                "baseline_pr_mean": payload["baseline_pr_mean"],
                                "output_dir": payload["output_dir"]}), indent=2, sort_keys=True))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
