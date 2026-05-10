#!/usr/bin/env python3
"""Tier 7.7z-r0 - edge-of-chaos compact regression gate.

After 7.7z promotion_supported_requires_compact_regression, this gate
verifies the edge-of-chaos mechanism survives Tier 1-3 sanity controls
before a baseline freeze can proceed.

Tier 1: shuffled_target (breaks causal structure)
Tier 2: no_plasticity (fixed random readout — tests whether learning matters)
Tier 3: architecture_ablation (baseline contractive regime — tests mechanism)

All controls must fail before freezing.
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
    build_task, geomean, geometry_metrics, safe_float,
    utc_now, write_json, write_rows, criterion,
)

TIER = "Tier 7.7z-r0 - Edge-of-Chaos Compact Regression Gate"
RUNNER_REVISION = "tier7_7z_r0_compact_regression_20260509_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_7z_r0_20260509_compact_regression"
PREREQ_7_7Z = CONTROLLED / "tier7_7z_20260509_edge_of_chaos_ridge_promotion" / "tier7_7z_results.json"

TIMESCALES = [2.0, 5.0, 10.0, 20.0, 50.0, 100.0, 200.0]
DEFAULT_HIDDEN = 128
DEFAULT_TASKS = "mackey_glass,lorenz,narma10"
DEFAULT_SEEDS = "42,43,44"
DEFAULT_LENGTHS = "8000,16000,32000"
DEFAULT_HORIZON = 8
TRAIN_PCT = 0.65


def json_safe(v: Any) -> Any:
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
    return np.vstack(rows), hidden, values


def ridge(X, y, alpha=1.0):
    n, p = X.shape
    try:
        return np.linalg.solve(X.T @ X + alpha * np.eye(p), X.T @ y)
    except np.linalg.LinAlgError:
        return np.linalg.lstsq(X.T @ X + alpha * np.eye(p), X.T @ y, rcond=None)[0]


def score_variant(observed, seed, hidden, decay_val, sr, antisym, shuffle_target=False, no_learning=False, train_end=0):
    features, h, tgt = compute_features(observed, seed, hidden, decay_val, sr, antisym)
    if shuffle_target:
        rng = np.random.default_rng(seed + 99998)
        tgt = tgt.copy(); rng.shuffle(tgt)
    hidden_cols = list(range(features.shape[1] - hidden, features.shape[1]))
    geo = geometry_metrics(features, hidden_cols, train_end, split="all")
    pr = safe_float(geo.get("participation_ratio"))
    if no_learning:
        w = np.zeros(features.shape[1], dtype=float)
        w[:3] = np.random.default_rng(seed + 77777).normal(0, 0.1, 3)
    else:
        w = ridge(features[:train_end], tgt[:train_end], 1.0)
    mse = float(np.mean((features[train_end:] @ w - tgt[train_end:]) ** 2))
    return {"pr": pr, "mse": mse}


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

                # Candidate: edge-of-chaos
                r = score_variant(obs, seed, hidden, 0.0, 1.0, 0.3, train_end=train_end)
                results.append({"variant": "candidate_eoc", "task": task_name, "length": length,
                               "seed": seed, "pr": r["pr"], "mse": r["mse"], "status": "ok",
                               "control": "candidate"})

                # Tier 1: shuffled target (should fail)
                r1 = score_variant(obs, seed, hidden, 0.0, 1.0, 0.3, shuffle_target=True, train_end=train_end)
                results.append({"variant": "candidate_eoc", "task": task_name, "length": length,
                               "seed": seed, "pr": r1["pr"], "mse": r1["mse"], "status": "ok",
                               "control": "shuffled_target"})

                # Tier 2: no learning (fixed random readout — should fail)
                r2 = score_variant(obs, seed, hidden, 0.0, 1.0, 0.3, no_learning=True, train_end=train_end)
                results.append({"variant": "candidate_eoc", "task": task_name, "length": length,
                               "seed": seed, "pr": r2["pr"], "mse": r2["mse"], "status": "ok",
                               "control": "no_learning"})

                # Tier 3: ablation (baseline contractive regime — should fail)
                r3 = score_variant(obs, seed, hidden, 0.5, 0.5, 0.0, train_end=train_end)
                results.append({"variant": "ablation_baseline", "task": task_name, "length": length,
                               "seed": seed, "pr": r3["pr"], "mse": r3["mse"], "status": "ok",
                               "control": "ablation"})

    def gmean(vals):
        try: return float(math.exp(sum(math.log(v) for v in vals if v > 0) / len(vals)))
        except: return float("inf")

    cand_rows = [r for r in results if r["control"] == "candidate"]
    shuf_rows = [r for r in results if r["control"] == "shuffled_target"]
    nole_rows = [r for r in results if r["control"] == "no_learning"]
    abla_rows = [r for r in results if r["control"] == "ablation"]

    nol_rows = nole_rows  # alias for readability in criteria below

    cand_pr = float(np.mean([r["pr"] for r in cand_rows if r.get("pr")]))
    shuf_pr = float(np.mean([r["pr"] for r in shuf_rows if r.get("pr")]))
    nol_pr  = float(np.mean([r["pr"] for r in nole_rows if r.get("pr")]))
    abla_pr = float(np.mean([r["pr"] for r in abla_rows if r.get("pr")]))

    cand_mse = gmean([r["mse"] for r in cand_rows if r.get("mse")])
    shuf_mse = gmean([r["mse"] for r in shuf_rows if r.get("mse")])
    nol_mse  = gmean([r["mse"] for r in nole_rows if r.get("mse")])
    abla_mse = gmean([r["mse"] for r in abla_rows if r.get("mse")])

    shuffle_hurts = shuf_mse > cand_mse
    learning_matters = nol_mse > cand_mse
    ablation_confirms = abla_pr < cand_pr

    classification = "compact_regression_pass" if shuffle_hurts and learning_matters and ablation_confirms else "compact_regression_fail"
    frozen = classification == "compact_regression_pass"

    criteria = [
        criterion("prereq 7.7z exists", PREREQ_7_7Z.exists(), "true", PREREQ_7_7Z.exists()),
        criterion("candidate scored", len(cand_rows), ">= 3", len(cand_rows) >= 3),
        criterion("shuffled target scored", len(shuf_rows), ">= 3", len(shuf_rows) >= 3),
        criterion("no-learning scored", len(nol_rows), ">= 3", len(nol_rows) >= 3),
        criterion("ablation scored", len(abla_rows), ">= 3", len(abla_rows) >= 3),
        criterion("Tier 1: shuffled target hurts MSE", shuffle_hurts, "true", shuffle_hurts,
                  f"cand={cand_mse:.6f} shuffled={shuf_mse:.6f}"),
        criterion("Tier 2: no-learning hurts MSE", learning_matters, "true", learning_matters,
                  f"cand={cand_mse:.6f} no_learning={nol_mse:.6f}"),
        criterion("Tier 3: ablation loses PR", ablation_confirms, "true", ablation_confirms,
                  f"cand PR={cand_pr:.1f} abla PR={abla_pr:.1f}"),
        criterion("candidate PR > abla PR", cand_pr > abla_pr, "true", cand_pr > abla_pr),
        criterion("compact regression outcome", classification, "== compact_regression_pass",
                  classification == "compact_regression_pass", classification),
        criterion("baseline freeze authorized", frozen, "true", frozen,
                  "CRA_EVIDENCE_BASELINE_v2.6 ready" if frozen else "fix remaining controls first"),
    ]
    passed = sum(1 for c in criteria if c["passed"])
    status = "pass" if passed == len(criteria) else "fail"

    payload = dict(tier=TIER, runner_revision=RUNNER_REVISION, generated_at_utc=utc_now(),
                   status=status, outcome=classification, criteria=criteria,
                   criteria_passed=passed, criteria_total=len(criteria), output_dir=str(output_dir),
                   baseline_frozen=frozen,
                   baseline_version="CRA_EVIDENCE_BASELINE_v2.6" if frozen else None,
                   candidate_pr=cand_pr, shuffled_pr=shuf_pr,
                   no_learning_pr=nol_pr, ablation_pr=abla_pr,
                   candidate_mse=cand_mse, shuffled_mse=shuf_mse,
                   no_learning_mse=nol_mse, ablation_mse=abla_mse,
                   next_gate="Tier 7.7z-r1 baseline freeze manifest + registry snapshot" if frozen else "Diagnose and narrow",
                   claim_boundary="Edge-of-chaos compact regression + baseline freeze decision." + (" Baseline CRA_EVIDENCE_BASELINE_v2.6 frozen." if frozen else ""))
    write_json(output_dir / "tier7_7z_r0_results.json", payload)
    write_rows(output_dir / "tier7_7z_r0_scoreboard.csv", results)
    write_rows(output_dir / "tier7_7z_r0_summary.csv", criteria)
    report = ["# Tier 7.7z-r0 Edge-of-Chaos Compact Regression",
              f"- Status: **{status.upper()}** ({passed}/{len(criteria)})",
              f"- Outcome: `{classification}`",
              f"- Baseline frozen: {frozen}",
              f"- Candidate PR: {cand_pr:.1f}  MSE: {cand_mse:.6f}",
              f"- Shuffled: PR={shuf_pr:.1f} MSE={shuf_mse:.6f} (hurts: {shuffle_hurts})",
              f"- No-learn: PR={nol_pr:.1f} MSE={nol_mse:.6f} (hurts: {learning_matters})",
              f"- Ablation: PR={abla_pr:.1f} MSE={abla_mse:.6f} (confirm: {ablation_confirms})",
              "", f"Next: {payload['next_gate']}"]
    (output_dir / "tier7_7z_r0_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    manifest = dict(tier=TIER, status=status, generated_at_utc=payload["generated_at_utc"], output_dir=str(output_dir))
    write_json(output_dir / "tier7_7z_r0_latest_manifest.json", manifest)
    write_json(CONTROLLED / "tier7_7z_r0_latest_manifest.json", manifest)
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
    print(json.dumps(json_safe(dict(status=payload["status"], outcome=payload["outcome"],
                                    criteria=f"{payload['criteria_passed']}/{payload['criteria_total']}",
                                    baseline_frozen=payload["baseline_frozen"],
                                    output_dir=payload["output_dir"])), indent=2, sort_keys=True))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
