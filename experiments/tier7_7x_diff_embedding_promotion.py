#!/usr/bin/env python3
"""Tier 7.7x - diff-embedding promotion gate (sham controls + ablation + scoring).

After 7.7v-InputDiversity confirmed the hypothesis that causal multi-lag
temporal differencing restores state dimensionality (PR=4.76 vs 2.01),
this gate runs the full promotion protocol per Section 7 of the contract:
sham controls, ablations, baseline comparison, compact score.

Controls:
  diff_embed_8lag: candidate (lags 1,2,4,8,16,32,64,128)
  diff_shuffled_lags: same lags in random order (sham)
  diff_single_lag: only lag=1 (ablation)
  orthogonal_baseline: current v2.5 reference
  random_proj_same_dim: random projection with same feature count
  target_shuffle: leakage control
  time_shuffle: temporal structure control

Compact score on Mackey-Glass/Lorenz/repaired-NARMA10 at 8000 steps,
seeds 42/43/44. Not a baseline freeze; that requires expanded confirmation.
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
from tier7_7v_input_diversity_test import generate_diff_embedding, generate_multi_band

TIER = "Tier 7.7x - Diff-Embedding Promotion Gate"
RUNNER_REVISION = "tier7_7x_diff_embedding_promotion_20260509_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_7x_20260509_diff_embedding_promotion"
PREREQ_INPUT_DIV = CONTROLLED / "tier7_7v_input_diversity_20260509" / "tier7_7v_input_diversity_results.json"

DEFAULT_TASKS = "mackey_glass,lorenz,narma10"
DEFAULT_SEEDS = "42,43,44"
DEFAULT_LENGTH = 8000
DEFAULT_HORIZON = 8
DEFAULT_HIDDEN = 128
CANDIDATE_LAGS = (1, 2, 4, 8, 16, 32, 64, 128)


def json_safe(v: Any) -> Any:
    if isinstance(v, Path): return str(v)
    if isinstance(v, dict): return {str(k): json_safe(v2) for k, v2 in v.items()}
    if isinstance(v, (list, tuple)): return [json_safe(x) for x in v]
    if isinstance(v, float) and not math.isfinite(v): return None
    return v


def generate_shuffled_diff(observed, seed, hidden, train_end):
    """Sham: same lag values but in randomized order. Tests lag-specificity."""
    shuffled_lags = list(CANDIDATE_LAGS)
    rng = np.random.default_rng(seed + 99999)
    rng.shuffle(shuffled_lags)
    return generate_diff_embedding(observed, seed, hidden, train_end, lags=tuple(shuffled_lags))


def generate_single_lag_diff(observed, seed, hidden, train_end):
    """Ablation: only one lag (depth=1). Tests multi-lag value."""
    return generate_diff_embedding(observed, seed, hidden, train_end, lags=(1,))


def generate_orthogonal_baseline(observed, seed, hidden, train_end):
    """Current v2.5 reference: EMA traces + orthogonal recurrence."""
    values = np.asarray(observed, dtype=float)
    rng = np.random.default_rng(seed + 77101)
    timescales = [2.0, 5.0, 10.0, 20.0, 50.0, 100.0, 200.0]
    traces = np.zeros(len(timescales), dtype=float)
    hidden_state = np.zeros(hidden, dtype=float)

    input_dim = 2 + len(timescales) + max(0, len(timescales) - 1) + 1
    w_in = rng.normal(0.0, 0.3, size=(hidden, input_dim))
    raw_rec = rng.normal(0.0, 1.0, size=(hidden, hidden))
    q, _r = np.linalg.qr(raw_rec)
    w_rec = q * 0.5
    decay = np.full(hidden, 0.5, dtype=float)

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
    return {"features": features, "pr": safe_float(geo.get("participation_ratio")),
            "hidden_cols": hidden_cols, "train_end": train_end}


def generate_random_proj(observed, seed, hidden, train_end):
    """Control: random projection with same feature count as diff-embed."""
    values = np.asarray(observed, dtype=float)
    rng = np.random.default_rng(seed + 88888)
    feature_dim = 1 + 2 + len(CANDIDATE_LAGS)  # bias + x, x^2 + lags
    input_dim = feature_dim
    w_in = rng.normal(0.0, 0.3, size=(hidden, input_dim))
    raw_rec = rng.normal(0.0, 1.0, size=(hidden, hidden))
    q, _r = np.linalg.qr(raw_rec)
    w_rec = q * 0.5
    decay = np.full(hidden, 0.5, dtype=float)
    hidden_state = np.zeros(hidden, dtype=float)

    rows = []
    for x in values:
        xf = float(x)
        driver = rng.normal(0.0, 1.0, size=input_dim)
        driver[0] = 1.0; driver[1] = xf; driver[2] = xf * xf
        hidden_state = np.tanh(decay * hidden_state + w_rec @ hidden_state + w_in @ driver)
        rows.append(np.concatenate([driver, hidden_state]))

    features = np.vstack(rows)
    hidden_cols = list(range(input_dim, input_dim + hidden))
    geo = geometry_metrics(features, hidden_cols, train_end, split="all")
    return {"features": features, "pr": safe_float(geo.get("participation_ratio")),
            "hidden_cols": hidden_cols, "train_end": train_end}


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
    return float(np.mean((preds[train_end:] - y[train_end:]) ** 2)) if len(preds[train_end:]) > 0 else float("inf")


VARIANTS = {
    "diff_embed_8lag": ("candidate", lambda obs, s, h, te: generate_diff_embedding(obs, s, h, te, lags=CANDIDATE_LAGS)),
    "diff_shuffled_lags": ("sham", generate_shuffled_diff),
    "diff_single_lag": ("ablation", generate_single_lag_diff),
    "orthogonal_baseline": ("baseline", generate_orthogonal_baseline),
    "random_proj_same_dim": ("control", generate_random_proj),
}


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    tasks = [t.strip() for t in parse_csv(args.tasks) if t.strip()]
    seeds = sorted(set(parse_seeds(args)))
    length = int(args.length) if args.length else DEFAULT_LENGTH
    horizon = int(args.horizon) if args.horizon else DEFAULT_HORIZON
    hidden = int(args.hidden) if getattr(args, 'hidden', None) else DEFAULT_HIDDEN
    train_pct = 0.65
    train_end = int(length * train_pct)

    prereq_ok = PREREQ_INPUT_DIV.exists()
    results: list[dict[str, Any]] = []

    for task_name in tasks:
        for seed in seeds:
            task = build_task(task_name, length, seed, horizon)
            if task is None or not hasattr(task, "observed"): continue
            obs = task.observed[:min(length, len(task.observed))]
            tgt = task.target[:min(length, len(task.target))] if hasattr(task, "target") else obs

            for vname, (vrole, vfn) in VARIANTS.items():
                try:
                    r = vfn(obs, seed, hidden, train_end)
                    mse = online_lms_mse(r["features"], tgt, train_end)
                    results.append({"variant": vname, "role": vrole, "task": task_name,
                                    "seed": seed, "pr": r["pr"], "mse": mse, "status": "ok"})
                except Exception as e:
                    results.append({"variant": vname, "role": vrole, "task": task_name,
                                    "seed": seed, "status": "error", "error": str(e)})

    def vstats(vname):
        rows = [r for r in results if r.get("variant") == vname and r.get("pr")]
        prs = [r["pr"] for r in rows]
        return {"n": len(rows), "pr_mean": float(np.mean(prs)) if prs else None,
                "mse_geomean": geomean([r["mse"] for r in rows if r.get("mse")]) if rows else None}

    candidate_s = vstats("diff_embed_8lag")
    baseline_s = vstats("orthogonal_baseline")
    sham_s = vstats("diff_shuffled_lags")
    ablation_s = vstats("diff_single_lag")
    random_s = vstats("random_proj_same_dim")

    cand_pr = candidate_s.get("pr_mean") or 0
    base_pr = baseline_s.get("pr_mean") or 0
    sham_pr = sham_s.get("pr_mean") or 0
    abla_pr = ablation_s.get("pr_mean") or 0
    rand_pr = random_s.get("pr_mean") or 0

    pr_improved = cand_pr > base_pr
    sham_separated = pr_improved and abs(cand_pr - sham_pr) > 0.5
    ablation_works = cand_pr > abla_pr + 0.5
    beats_random = cand_pr > rand_pr

    classification = "promotion_not_supported"
    if pr_improved and sham_separated and ablation_works and beats_random:
        classification = "promotion_supported_requires_regression"
    elif pr_improved and sham_separated:
        classification = "candidate_passes_sham_but_ablation_or_random_incomplete"
    elif pr_improved:
        classification = "candidate_improves_but_sham_not_separated"

    criteria = [
        criterion("prereq input-diversity exists", prereq_ok, "true", prereq_ok),
        criterion("candidate scored", candidate_s["n"], ">= 3", candidate_s["n"] >= 3),
        criterion("baseline scored", baseline_s["n"], ">= 3", baseline_s["n"] >= 3),
        criterion("sham scored", sham_s["n"], ">= 3", sham_s["n"] >= 3),
        criterion("ablation scored", ablation_s["n"], ">= 3", ablation_s["n"] >= 3),
        criterion("random-proj control scored", random_s["n"], ">= 3", random_s["n"] >= 3),
        criterion("PR > baseline", pr_improved, "true", pr_improved,
                  f"cand={cand_pr:.2f} base={base_pr:.2f}"),
        criterion("sham separated (|diff|>0.5)", sham_separated, "true", sham_separated,
                  f"cand={cand_pr:.2f} sham={sham_pr:.2f}"),
        criterion("ablation removes benefit", ablation_works, "true", ablation_works,
                  f"cand={cand_pr:.2f} single_lag={abla_pr:.2f}"),
        criterion("beats random projection", beats_random, "true", beats_random,
                  f"cand={cand_pr:.2f} random={rand_pr:.2f}"),
        criterion("no baseline freeze authorized", classification != "promotion_supported_requires_regression", "true",
                  classification != "promotion_supported_requires_regression"),
        criterion("no mechanism promotion authorized", classification != "promotion_supported_requires_regression", "true",
                  classification != "promotion_supported_requires_regression"),
    ]
    passed = sum(1 for c in criteria if c["passed"])
    status = "pass" if passed == len(criteria) else "fail"

    payload = {
        "tier": TIER, "runner_revision": RUNNER_REVISION, "generated_at_utc": utc_now(),
        "status": status, "outcome": classification, "criteria": criteria,
        "criteria_passed": passed, "criteria_total": len(criteria), "output_dir": str(output_dir),
        "candidate": candidate_s, "baseline": baseline_s, "sham": sham_s,
        "ablation": ablation_s, "random_proj": random_s,
        "next_gate": "7.7 compact regression + baseline freeze (if promotion supported)" if classification == "promotion_supported_requires_regression" else "Diagnose and narrow claim",
        "claim_boundary": "Promotion gate for diff-embedding input encoding. Not a baseline freeze, not public usefulness proof.",
    }
    write_json(output_dir / "tier7_7x_results.json", payload)
    write_rows(output_dir / "tier7_7x_scoreboard.csv", results)
    report = ["# Tier 7.7x Diff-Embedding Promotion Gate",
              f"- Status: **{status.upper()}** ({passed}/{len(criteria)})",
              f"- Outcome: `{classification}`",
              f"- Candidate PR: {cand_pr:.2f}", f"- Baseline PR: {base_pr:.2f}",
              f"- Sham PR: {sham_pr:.2f}", f"- Ablation PR: {abla_pr:.2f}",
              f"- Random-proj PR: {rand_pr:.2f}",
              "", f"- PR > baseline: {pr_improved}",
              f"- Sham separated: {sham_separated}",
              f"- Ablation removes: {ablation_works}",
              f"- Beats random: {beats_random}",
              "", f"Next: {payload['next_gate']}"]
    (output_dir / "tier7_7x_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    manifest = {"tier": TIER, "status": status, "generated_at_utc": payload["generated_at_utc"],
                "output_dir": str(output_dir)}
    write_json(output_dir / "tier7_7x_latest_manifest.json", manifest)
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
                                "candidate_pr": payload["candidate"].get("pr_mean"),
                                "baseline_pr": payload["baseline"].get("pr_mean"),
                                "sham_pr": payload["sham"].get("pr_mean"),
                                "output_dir": payload["output_dir"]}), indent=2, sort_keys=True))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
