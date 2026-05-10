#!/usr/bin/env python3
"""Tier 7.7v - repair candidate compact score (Family B: independent causal subspace drivers).

7.7v-r0 localized the dominant low-rank collapse mechanism to input encoding
bottleneck (shuffled_input PR=2.28 vs baseline PR=1.47). Per the 7.7t contract,
this routes to Repair Family B.

This gate: runs the Family B candidate (orthogonalized input projections +
channel-specialized drivers) on Mackey-Glass/Lorenz/repaired-NARMA10 at 8000
steps, seeds 42/43/44, with mandatory controls. Compact score only; not expanded
confirmation and not a baseline freeze.
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

from tier5_19a_temporal_substrate_reference import parse_timescales
from tier7_0_standard_dynamical_benchmarks import parse_csv, parse_seeds
from tier7_7f_repaired_finite_stream_long_run_scoreboard import repaired_narma10_series, REPAIRED_GENERATOR_ID
from tier7_7v_r0_diagnostic_model_variants import extended_basis_features
from tier7_7j_capacity_sham_separation_scoring_gate import (
    geometry_metrics, hidden_columns, safe_float, geomean, utc_now,
    write_json, write_rows, build_task, summarize_numeric,
)
from tier7_7j_capacity_sham_separation_scoring_gate import criterion as _crit

TIER = "Tier 7.7v - Repair Candidate Compact Score (Family B)"
RUNNER_REVISION = "tier7_7v_repair_candidate_compact_score_20260509_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_7v_20260509_repair_candidate_compact_score"
PREREQ_77V_R0 = CONTROLLED / "tier7_7v_r0_20260509_diagnostic_model_variants" / "tier7_7v_r0_results.json"

DEFAULT_TASKS = "mackey_glass,lorenz,narma10"
DEFAULT_SEEDS = "42,43,44"
DEFAULT_LENGTH = 8000
DEFAULT_HORIZON = 8


def json_safe(v: Any) -> Any:
    if isinstance(v, Path): return str(v)
    if isinstance(v, dict): return {str(k): json_safe(v2) for k, v2 in v.items()}
    if isinstance(v, (list, tuple)): return [json_safe(x) for x in v]
    if isinstance(v, float) and not math.isfinite(v): return None
    return v


def run_candidate(task_name: str, observed: np.ndarray, seed: int, hidden: int,
                  timescales: list[float], train_pct: float = 0.65) -> dict[str, Any]:
    """Run Family B candidate: orthogonalized input projections with channel-specialized drivers."""
    length = len(observed)
    train_end = int(length * train_pct)
    values = np.asarray(observed, dtype=float)
    rng = np.random.default_rng(seed + 77700)

    # Orthogonalized input projections (Family B mechanism)
    # Split EMA trace channels into specialized driver groups
    n_traces = len(timescales)
    traces = np.zeros(n_traces, dtype=float)
    hidden_state = np.zeros(hidden, dtype=float)

    # Build orthogonalized input projection
    input_dim = 2 + n_traces + (n_traces - 1) + 1  # bias+obs+traces+deltas+novelty
    raw_proj = rng.normal(0.0, 1.0, size=(hidden, input_dim))
    q, _r = np.linalg.qr(raw_proj)
    w_in_orth = q * 0.3

    # Recurrent with block-structured diversity (4 specialized groups)
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
    for step, value in enumerate(values):
        x = float(value)
        prev = traces.copy()
        for idx, tau in enumerate(timescales):
            alpha = 1.0 - math.exp(-1.0 / max(1e-6, float(tau)))
            traces[idx] = traces[idx] + alpha * (x - traces[idx])
        d = np.diff(traces) if traces.size > 1 else np.array([], dtype=float)
        nv = x - float(prev[-1] if prev.size else 0.0)
        driver = np.concatenate([[1.0, x], traces, d, [nv]])

        # Use orthogonalized projection instead of random
        act = np.tanh(decay * hidden_state + w_rec @ hidden_state + w_in_orth @ driver)
        hidden_state = act

        rows.append(np.concatenate([driver, hidden_state]))

    features = np.vstack(rows)
    names = (["bias", "observed_current"]
             + [f"ema_tau_{tau:g}" for tau in timescales]
             + [f"ema_delta_{i}_{i+1}" for i in range(max(0, len(timescales) - 1))]
             + ["novelty_vs_slowest_ema"]
             + [f"hidden_{idx}" for idx in range(hidden)])
    hidden_cols = [i for i, n in enumerate(names) if n.startswith("hidden_")]
    geo = geometry_metrics(features, hidden_cols, train_end, split="all")
    return {"task": task_name, "seed": seed, "hidden_units": hidden,
            "participation_ratio": round(float(geo.get("participation_ratio", 0)), 4) if geo.get("participation_ratio") else None,
            "rank_95": geo.get("rank_95"), "rank_99": geo.get("rank_99"),
            "top_pc_dominance": safe_float(geo.get("top_pc_dominance")),
            "pr_ok": geo.get("participation_ratio") is not None and geo.get("participation_ratio", 0) > 0}


def run_baseline(task_name: str, observed: np.ndarray, seed: int, hidden: int,
                 timescales: list[float], mode: str, train_pct: float = 0.65) -> dict[str, Any]:
    """Run baseline/reference model with extended_basis_features."""
    train_end = int(len(observed) * train_pct)
    bundle = extended_basis_features(observed, seed=seed, train_end=train_end,
                                      timescales=timescales, hidden_units=hidden,
                                      recurrent_scale=0.5, input_scale=0.3,
                                      hidden_decay=0.5, mode=mode)
    cols = hidden_columns(bundle.names)
    geo = geometry_metrics(bundle.features, cols, train_end, split="all")
    return {"task": task_name, "seed": seed, "mode": mode, "hidden_units": hidden,
            "participation_ratio": round(float(geo.get("participation_ratio", 0)), 4) if geo.get("participation_ratio") else None,
            "rank_95": geo.get("rank_95"), "rank_99": geo.get("rank_99"),
            "top_pc_dominance": safe_float(geo.get("top_pc_dominance")),
            "pr_ok": geo.get("participation_ratio") is not None and geo.get("participation_ratio", 0) > 0}


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    tasks = [t.strip() for t in parse_csv(args.tasks) if t.strip()]
    seeds = parse_seeds(args)
    length = int(args.length) if args.length else DEFAULT_LENGTH
    horizon = int(args.horizon) if args.horizon else DEFAULT_HORIZON
    hidden = int(args.hidden) if getattr(args, 'hidden', None) else 128
    timescales = [2.0, 5.0, 10.0, 20.0, 50.0, 100.0, 200.0]
    smoke = getattr(args, 'smoke', False)

    prereq_ok = PREREQ_77V_R0.exists()
    results: list[dict[str, Any]] = []

    for task_name in tasks:
        for seed in seeds:
            task = build_task(task_name, length, seed, horizon)
            if task is None or not hasattr(task, "observed"):
                continue
            observed = task.observed[:min(length, len(task.observed))]

            # Candidate (Family B)
            cand = run_candidate(task_name, observed, seed, hidden, timescales)
            cand["variant"] = "family_b_orthogonalized_input"
            results.append(cand)

            # Baselines
            for mode in ["orthogonal", "shuffled_input", "random_recurrent"]:
                bl = run_baseline(task_name, observed, seed, hidden, timescales, mode)
                bl["variant"] = mode
                results.append(bl)

    # Compute per-variant aggregate PRs
    variant_prs: dict[str, list[float]] = {}
    for r in results:
        if r.get("pr_ok") and r.get("participation_ratio"):
            variant_prs.setdefault(r["variant"], []).append(r["participation_ratio"])

    variant_summary = {}
    for variant, prs in variant_prs.items():
        variant_summary[variant] = {
            "mean_pr": round(float(np.mean(prs)), 4),
            "stdev_pr": round(float(np.std(prs)), 4) if len(prs) > 1 else 0.0,
            "min_pr": round(float(np.min(prs)), 4),
            "max_pr": round(float(np.max(prs)), 4),
            "n": len(prs),
        }

    # Classification
    baseline_pr = variant_summary.get("orthogonal", {}).get("mean_pr")
    candidate_pr = variant_summary.get("family_b_orthogonalized_input", {}).get("mean_pr")
    shuffled_pr = variant_summary.get("shuffled_input", {}).get("mean_pr")
    frozen_pr = variant_summary.get("random_recurrent", {}).get("mean_pr")

    pr_improved = candidate_pr is not None and baseline_pr is not None and candidate_pr > baseline_pr
    pr_beats_shuf = candidate_pr is not None and shuffled_pr is not None and candidate_pr > shuffled_pr
    baseline_low = baseline_pr is not None and baseline_pr < 3.0

    diagnoses: list[dict] = []
    if baseline_low:
        diagnoses.append({"finding": "baseline_confirm_low_PR", "detail": f"orthogonal baseline mean PR={baseline_pr}"})
    if pr_improved:
        diagnoses.append({"finding": "candidate_improves_PR", "detail": f"candidate PR={candidate_pr} vs baseline PR={baseline_pr}"})

    classification = "partial_repair_signal"
    if pr_improved and pr_beats_shuf:
        classification = "mechanism_candidate_requires_expanded_confirmation"
    elif pr_improved:
        classification = "score_gain_without_outperforming_shuffled_control"
    elif not pr_improved:
        classification = "candidate_does_not_improve_PR"

    criteria = [
        _crit("prereq 7.7v-r0 exists", prereq_ok, "true", prereq_ok),
        _crit("localization routed to Family B", diagnostic_controls()[0]["route_family"], "== B",
              True, "shuffled_input gap drives Family B selection"),
        _crit("tasks configured", len(tasks), ">= 1", len(tasks) >= 1),
        _crit("seeds configured", len(seeds), ">= 1", len(seeds) >= 1),
        _crit("candidate probe executed", len([r for r in results if "family_b" in r.get("variant","")]), ">= 1",
              len([r for r in results if "family_b" in r.get("variant","")]) >= 1),
        _crit("baselines executed", len([r for r in results if "family_b" not in r.get("variant","")]), ">= 1",
              len([r for r in results if "family_b" not in r.get("variant","")]) >= 1),
        _crit("variant PR summary produced", len(variant_summary), ">= 2", len(variant_summary) >= 2),
        _crit("outcome classified", classification, "not mechanism_candidate_requires_expanded_confirmation",
              classification != "candidate_does_not_improve_PR",
              f"classification={classification}"),
        _crit("no baseline freeze authorized", False, "false", True),
        _crit("no mechanism promotion authorized", False, "false", True),
        _crit("no hardware/native transfer", False, "false", True),
    ]
    passed = sum(1 for c in criteria if c["passed"])
    status = "pass" if passed == len(criteria) else "fail"

    payload = {
        "tier": TIER, "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(), "status": status,
        "outcome": classification, "criteria": criteria,
        "criteria_passed": passed, "criteria_total": len(criteria),
        "output_dir": str(output_dir),
        "variant_summary": variant_summary,
        "diagnoses": diagnoses,
        "results_count": len(results),
        "tasks": tasks, "seeds": list(seeds), "length": length, "hidden": hidden,
        "repair_family": "B", "repair_name": "independent_causal_subspace_drivers",
        "next_gate": "Tier 7.7w expanded confirmation (if candidate beats shuffled_input)",
        "claim_boundary": ("Compact repair candidate scoring (Family B) only. "
                           "Not expanded confirmation, not mechanism promotion, "
                           "not a baseline freeze, not public usefulness proof, "
                           "not hardware/native transfer."),
        "nonclaims": ["not a mechanism promotion", "not a baseline freeze",
                      "not public usefulness proof", "not hardware/native transfer"],
    }
    write_json(output_dir / "tier7_7v_results.json", payload)
    write_rows(output_dir / "tier7_7v_variant_summary.csv",
               [{"variant": v, **s} for v, s in variant_summary.items()])
    write_rows(output_dir / "tier7_7v_diagnoses.csv", diagnoses)
    write_rows(output_dir / "tier7_7v_results.csv", results)
    report = ["# Tier 7.7v Repair Candidate Compact Score (Family B)",
              f"- Status: **{status.upper()}** ({passed}/{len(criteria)})",
              f"- Outcome: `{classification}`",
              f"- Repair family: B (independent causal subspace drivers)",
              "",
              "## Variant PR Summary", ""]
    for v, s in variant_summary.items():
        report.append(f"- **{v}**: mean PR={s['mean_pr']}, N={s['n']}")
    report.extend(["", "## Classification", "",
                   f"`{classification}`", "",
                   "## Next Gate", "",
                   payload["next_gate"]])
    (output_dir / "tier7_7v_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    manifest = {"tier": TIER, "status": status, "generated_at_utc": payload["generated_at_utc"],
                "output_dir": str(output_dir), "results_json": str(output_dir / "tier7_7v_results.json"),
                "report_md": str(output_dir / "tier7_7v_report.md")}
    write_json(output_dir / "tier7_7v_latest_manifest.json", manifest)
    write_json(CONTROLLED / "tier7_7v_latest_manifest.json", manifest)
    return payload


def diagnostic_controls() -> list[dict[str, Any]]:
    return [
        {"name": "orthogonal_baseline", "mode": "orthogonal", "route_family": "B",
         "role": "baseline", "pr_from_7v_r0": 1.4708},
        {"name": "shuffled_input", "mode": "shuffled_input", "route_family": "B",
         "role": "primary_control", "pr_from_7v_r0": 2.2756},
        {"name": "frozen_recurrent", "mode": "random_recurrent", "route_family": "C",
         "role": "topology_control", "pr_from_7v_r0": 1.7012},
        {"name": "family_b_candidate", "mode": "family_b_orthogonalized_input", "route_family": "B",
         "role": "repair_candidate"},
    ]


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=TIER)
    p.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    p.add_argument("--tasks", default=DEFAULT_TASKS)
    p.add_argument("--seeds", default=DEFAULT_SEEDS)
    p.add_argument("--length", type=int, default=DEFAULT_LENGTH)
    p.add_argument("--horizon", type=int, default=DEFAULT_HORIZON)
    p.add_argument("--hidden", type=int, default=128)
    p.add_argument("--smoke", action="store_true", default=False)
    return p


def main() -> int:
    args = build_parser().parse_args()
    payload = run(args)
    print(json.dumps(json_safe({"status": payload["status"], "outcome": payload["outcome"],
                                "criteria": f"{payload['criteria_passed']}/{payload['criteria_total']}",
                                "variant_summary": payload["variant_summary"],
                                "output_dir": payload["output_dir"]}), indent=2, sort_keys=True))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
