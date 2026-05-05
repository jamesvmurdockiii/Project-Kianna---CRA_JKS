#!/usr/bin/env python3
"""Tier 7.0c - Bounded Continuous Readout / Interface Repair.

Tier 7.0b localized the standard-dynamical-benchmark gap to a recoverable
state-signal/default-readout failure. This tier tests one narrow repair:
a bounded online continuous readout over causal CRA state.

This is still a software repair gate, not a baseline freeze. The readout is
diagnostic/engineering scaffolding until it beats ablations and later compact
regression. It does not use future labels, does not fit on held-out test rows
in batch, and does not move the benchmark to hardware.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "controlled_test_output"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from tier4_scaling import mean, stdev  # noqa: E402
from tier7_0_standard_dynamical_benchmarks import (  # noqa: E402
    DEFAULT_TASKS,
    SequenceTask,
    build_task,
    geometric_mean,
    parse_csv,
    parse_seeds,
    score_predictions,
)
from tier7_0b_continuous_regression_failure_analysis import (  # noqa: E402
    collect_cra_trace,
    evaluate_probe,
    lag_matrix,
)


TIER = "Tier 7.0c - Bounded Continuous Readout / Interface Repair"
RUNNER_REVISION = "tier7_0c_continuous_readout_repair_20260505_0001"
DEFAULT_OUTPUT_DIR = OUTPUT_ROOT / "tier7_0c_20260505_continuous_readout_repair"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.ndarray):
        return [json_safe(v) for v in value.tolist()]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        value = float(value)
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def criterion(name: str, value: Any, rule: str, passed: bool, note: str = "") -> dict[str, Any]:
    return {"name": name, "value": json_safe(value), "rule": rule, "passed": bool(passed), "note": note}


def normalize_features(features: np.ndarray, train_end: int, *, keep_bias: bool = True) -> tuple[np.ndarray, dict[str, Any]]:
    x = np.asarray(features, dtype=float)
    mu = np.mean(x[:train_end], axis=0)
    sd = np.std(x[:train_end], axis=0)
    sd[sd < 1e-9] = 1.0
    if keep_bias:
        mu[0] = 0.0
        sd[0] = 1.0
    return (x - mu) / sd, {"feature_mu": mu, "feature_sd": sd}


def online_normalized_lms(
    features: np.ndarray,
    target: np.ndarray,
    *,
    train_end: int,
    lr: float,
    decay: float,
    weight_clip: float,
    output_clip: float,
    update_target: np.ndarray | None = None,
    update_enabled: bool = True,
) -> tuple[np.ndarray, dict[str, Any]]:
    del train_end  # retained in signature to make causal contract explicit.
    x = np.asarray(features, dtype=float)
    y = np.asarray(target, dtype=float)
    update_y = y if update_target is None else np.asarray(update_target, dtype=float)
    w = np.zeros(x.shape[1], dtype=float)
    predictions = np.zeros(len(y), dtype=float)
    norm_trace = []
    for step, row in enumerate(x):
        pred = float(np.dot(w, row))
        if output_clip > 0.0:
            pred = float(np.clip(pred, -output_clip, output_clip))
        predictions[step] = pred
        if update_enabled:
            err = float(update_y[step] - pred)
            denom = 1.0 + float(np.dot(row, row))
            w = (1.0 - float(decay)) * w + (float(lr) * err / denom) * row
            norm = float(np.linalg.norm(w))
            if weight_clip > 0.0 and norm > weight_clip:
                w *= weight_clip / norm
        norm_trace.append(float(np.linalg.norm(w)))
    return predictions, {
        "lr": float(lr),
        "decay": float(decay),
        "weight_clip": float(weight_clip),
        "output_clip": float(output_clip),
        "final_weight_norm": float(np.linalg.norm(w)),
        "max_weight_norm": max(norm_trace) if norm_trace else 0.0,
        "update_enabled": bool(update_enabled),
    }


def shuffled_target(target: np.ndarray, train_end: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed + 9091)
    out = np.asarray(target, dtype=float).copy()
    train = out[:train_end].copy()
    test = out[train_end:].copy()
    rng.shuffle(train)
    rng.shuffle(test)
    out[:train_end] = train
    out[train_end:] = test
    return out


def shuffled_rows(features: np.ndarray, train_end: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed + 9113)
    out = np.asarray(features, dtype=float).copy()
    train_idx = np.arange(train_end)
    test_idx = np.arange(train_end, len(out))
    rng.shuffle(train_idx)
    rng.shuffle(test_idx)
    out[:train_end] = out[train_idx]
    out[train_end:] = out[test_idx]
    return out


def run_repair_models(task: SequenceTask, trace: Any, *, seed: int, args: argparse.Namespace) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    target = trace.target
    train_end = trace.train_end
    lag_features = lag_matrix(trace.observed, args.history)
    state_features, state_norm = normalize_features(trace.features, train_end)
    lag_norm, lag_meta = normalize_features(lag_features, train_end)
    state_plus_lag = np.column_stack([state_features, lag_norm[:, 1:]])
    shuffled_state = shuffled_rows(state_features, train_end, seed)
    wrong_target = shuffled_target(target, train_end, seed)

    specs: list[tuple[str, np.ndarray, np.ndarray | None, bool, dict[str, Any]]] = [
        (
            "raw_cra_v2_1_online",
            np.column_stack([np.ones(len(target)), trace.cra_prediction]),
            None,
            False,
            {"repair_role": "raw CRA prediction, no continuous repair"},
        ),
        (
            "bounded_state_readout_repair",
            state_features,
            None,
            True,
            {"repair_role": "bounded online continuous readout over causal CRA state", "feature_norm": "train_prefix"},
        ),
        (
            "bounded_state_plus_lag_readout_repair",
            state_plus_lag,
            None,
            True,
            {
                "repair_role": "bounded online continuous readout over causal CRA state plus same lag budget",
                "feature_norm": "train_prefix",
                "lag_budget": int(args.history),
            },
        ),
        (
            "lag_only_online_lms_control",
            lag_norm,
            None,
            True,
            {"repair_role": "same online readout over lag features only", "lag_budget": int(args.history)},
        ),
        (
            "state_shuffled_feature_control",
            shuffled_state,
            None,
            True,
            {"repair_role": "state features shuffled within train/test split"},
        ),
        (
            "state_shuffled_target_control",
            state_features,
            wrong_target,
            True,
            {"repair_role": "state readout updated from shuffled targets"},
        ),
        (
            "state_frozen_no_update_control",
            state_features,
            None,
            False,
            {"repair_role": "state readout with updates disabled"},
        ),
    ]
    rows: list[dict[str, Any]] = []
    timeseries: list[dict[str, Any]] = []
    for model, features, update_target, update_enabled, diagnostics in specs:
        if model == "raw_cra_v2_1_online":
            pred = trace.cra_prediction
            diag = {**diagnostics}
        else:
            pred, diag = online_normalized_lms(
                features,
                target,
                train_end=train_end,
                lr=args.readout_lr,
                decay=args.readout_decay,
                weight_clip=args.weight_clip,
                output_clip=args.output_clip,
                update_target=update_target,
                update_enabled=update_enabled,
            )
            diag = {**diagnostics, **diag, "state_normalization": "train_prefix", "lag_normalization": lag_meta}
            if model.startswith("bounded_state"):
                diag["state_feature_mu_count"] = len(state_norm["feature_mu"])
        rows.append(evaluate_probe(task.name, seed, train_end, target, pred, model, diag))
        for step, (obs, tgt, pred_value) in enumerate(zip(trace.observed, target, pred)):
            timeseries.append(
                {
                    "task": task.name,
                    "seed": int(seed),
                    "model": model,
                    "step": int(step),
                    "split": "train" if step < train_end else "test",
                    "observed": float(obs),
                    "target": float(tgt),
                    "prediction": float(pred_value),
                    "squared_error": float((float(pred_value) - float(tgt)) ** 2),
                }
            )
    return rows, timeseries


def summarize(rows: list[dict[str, Any]], tasks: list[str], models: list[str], seeds: list[int]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    summary_rows: list[dict[str, Any]] = []
    aggregate_rows: list[dict[str, Any]] = []
    for task in tasks:
        for model in models:
            subset = [r for r in rows if r["task"] == task and r["model"] == model and r["status"] == "pass"]
            summary_rows.append(
                {
                    "task": task,
                    "model": model,
                    "status": "pass" if len(subset) == len(seeds) else "fail",
                    "seed_count": len(subset),
                    "mse_mean": mean([r["mse"] for r in subset]),
                    "mse_median": float(np.median([r["mse"] for r in subset])) if subset else None,
                    "mse_std": stdev([r["mse"] for r in subset]),
                    "mse_worst": max([r["mse"] for r in subset]) if subset else None,
                    "nmse_mean": mean([r["nmse"] for r in subset]),
                    "tail_mse_mean": mean([r["tail_mse"] for r in subset]),
                    "test_corr_mean": mean([r["test_corr"] for r in subset]),
                }
            )
    for model in models:
        for seed in seeds:
            subset = [r for r in rows if r["model"] == model and r["seed"] == seed and r["status"] == "pass"]
            by_task = {r["task"]: r for r in subset}
            if all(task in by_task for task in tasks):
                aggregate_rows.append(
                    {
                        "task": "all_three_geomean",
                        "model": model,
                        "seed": int(seed),
                        "status": "pass",
                        "geomean_mse": geometric_mean([by_task[task]["mse"] for task in tasks]),
                        "geomean_nmse": geometric_mean([by_task[task]["nmse"] for task in tasks]),
                    }
                )
            else:
                aggregate_rows.append(
                    {
                        "task": "all_three_geomean",
                        "model": model,
                        "seed": int(seed),
                        "status": "fail",
                        "geomean_mse": None,
                        "geomean_nmse": None,
                    }
                )
    aggregate_summary = []
    for model in models:
        subset = [r for r in aggregate_rows if r["model"] == model and r["status"] == "pass"]
        values = [float(r["geomean_mse"]) for r in subset if r["geomean_mse"] is not None]
        nmse_values = [float(r["geomean_nmse"]) for r in subset if r["geomean_nmse"] is not None]
        aggregate_summary.append(
            {
                "model": model,
                "status": "pass" if values else "fail",
                "seed_count": len(values),
                "geomean_mse_mean": mean(values),
                "geomean_mse_median": float(np.median(values)) if values else None,
                "geomean_mse_worst": max(values) if values else None,
                "geomean_nmse_mean": mean(nmse_values),
            }
        )
    pass_rows = [r for r in aggregate_summary if r["status"] == "pass" and r["geomean_mse_mean"] is not None]
    pass_rows.sort(key=lambda r: float(r["geomean_mse_mean"]))
    rank = {row["model"]: i + 1 for i, row in enumerate(pass_rows)}
    for row in aggregate_summary:
        row["rank_by_geomean_mse"] = rank.get(row["model"])
    aggregate_summary.sort(key=lambda row: (row["rank_by_geomean_mse"] or 10_000, row["model"]))
    return summary_rows, aggregate_rows, aggregate_summary


def classify_repair(aggregate_summary: list[dict[str, Any]]) -> dict[str, Any]:
    by_model = {row["model"]: row for row in aggregate_summary if row["status"] == "pass"}

    def mse(name: str) -> float:
        row = by_model.get(name)
        if not row or row.get("geomean_mse_mean") is None:
            return math.inf
        return float(row["geomean_mse_mean"])

    raw = mse("raw_cra_v2_1_online")
    state = mse("bounded_state_readout_repair")
    state_lag = mse("bounded_state_plus_lag_readout_repair")
    lag_only = mse("lag_only_online_lms_control")
    shuffled_state = mse("state_shuffled_feature_control")
    shuffled_target = mse("state_shuffled_target_control")
    frozen = mse("state_frozen_no_update_control")
    best_repair_name = "bounded_state_plus_lag_readout_repair" if state_lag <= state else "bounded_state_readout_repair"
    best_repair = min(state, state_lag)
    improvement = raw / best_repair if best_repair > 0 and math.isfinite(raw) and math.isfinite(best_repair) else None
    shuffled_margin = min(shuffled_state, shuffled_target) / best_repair if best_repair > 0 and math.isfinite(best_repair) else None
    lag_margin = lag_only / best_repair if best_repair > 0 and math.isfinite(best_repair) and math.isfinite(lag_only) else None
    frozen_margin = frozen / best_repair if best_repair > 0 and math.isfinite(best_repair) and math.isfinite(frozen) else None
    if (
        improvement is not None
        and improvement >= 2.0
        and shuffled_margin is not None
        and shuffled_margin >= 1.25
        and frozen_margin is not None
        and frozen_margin >= 1.25
    ):
        if lag_margin is not None and lag_margin < 1.10:
            outcome = "repair_works_but_lag_only_explains_most_gain"
            recommendation = "Do not promote yet; design a stricter state-specific repair or accept this benchmark mostly measures lag regression."
        else:
            outcome = "repair_candidate_passes_diagnostic_gate"
            recommendation = "Run Tier 7.0d compact regression/promotion gate before freezing a software baseline."
    else:
        outcome = "repair_candidate_not_promoted"
        recommendation = "Do not promote; inspect controls and consider history/reservoir dynamics rather than readout repair."
    return {
        "outcome": outcome,
        "best_repair_model": best_repair_name,
        "raw_cra_geomean_mse": raw,
        "bounded_state_geomean_mse": state,
        "bounded_state_plus_lag_geomean_mse": state_lag,
        "lag_only_geomean_mse": lag_only,
        "shuffled_state_geomean_mse": shuffled_state,
        "shuffled_target_geomean_mse": shuffled_target,
        "frozen_geomean_mse": frozen,
        "best_repair_improvement_over_raw": improvement,
        "best_repair_margin_vs_best_shuffled_control": shuffled_margin,
        "best_repair_margin_vs_lag_only": lag_margin,
        "best_repair_margin_vs_frozen": frozen_margin,
        "recommendation": recommendation,
    }


def write_report(output_dir: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# Tier 7.0c Bounded Continuous Readout / Interface Repair",
        "",
        f"- Generated: `{payload['generated_at_utc']}`",
        f"- Status: **{payload['status'].upper()}**",
        f"- Criteria: `{payload['criteria_passed']}/{payload['criteria_total']}`",
        f"- Outcome: `{payload['repair_classification']['outcome']}`",
        "",
        "## Claim Boundary",
        "",
        payload["claim_boundary"],
        "",
        "## Aggregate Summary",
        "",
        "| Model | Rank | Geomean MSE mean | Geomean NMSE mean |",
        "| --- | ---: | ---: | ---: |",
    ]
    for row in payload["aggregate_summary"]:
        lines.append(
            f"| {row['model']} | {row['rank_by_geomean_mse']} | {row['geomean_mse_mean']} | {row['geomean_nmse_mean']} |"
        )
    lines.extend(
        [
            "",
            "## Repair Classification",
            "",
            f"- Outcome: `{payload['repair_classification']['outcome']}`",
            f"- Best repair model: `{payload['repair_classification']['best_repair_model']}`",
            f"- Raw CRA geomean MSE: `{payload['repair_classification']['raw_cra_geomean_mse']}`",
            f"- Best repair improvement over raw: `{payload['repair_classification']['best_repair_improvement_over_raw']}`",
            f"- Margin vs best shuffled control: `{payload['repair_classification']['best_repair_margin_vs_best_shuffled_control']}`",
            f"- Margin vs lag-only: `{payload['repair_classification']['best_repair_margin_vs_lag_only']}`",
            f"- Recommendation: {payload['repair_classification']['recommendation']}",
            "",
            "## Interpretation Rule",
            "",
            "- This tier is a repair candidate, not a baseline freeze.",
            "- If the repair passes, the next step is compact regression/promotion, not hardware.",
            "- If lag-only explains the gain, do not call this a CRA mechanism win.",
            "",
        ]
    )
    (output_dir / "tier7_0c_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    tasks = parse_csv(args.tasks)
    seeds = parse_seeds(args)
    started = time.perf_counter()
    all_rows: list[dict[str, Any]] = []
    all_timeseries: list[dict[str, Any]] = []
    trace_diagnostics: list[dict[str, Any]] = []
    for seed in seeds:
        for task_name in tasks:
            task = build_task(task_name, args.length, seed, args.horizon)
            trace = collect_cra_trace(task, seed=seed, args=args)
            rows, timeseries = run_repair_models(task, trace, seed=seed, args=args)
            all_rows.extend(rows)
            all_timeseries.extend(timeseries)
            trace_diagnostics.append({"task": task_name, "seed": int(seed), **trace.diagnostics})
    models = sorted({row["model"] for row in all_rows})
    summary_rows, aggregate_rows, aggregate_summary = summarize(all_rows, tasks, models, seeds)
    repair_classification = classify_repair(aggregate_summary)
    criteria = [
        criterion("runner revision current", RUNNER_REVISION, "expected current source", RUNNER_REVISION.endswith("_0001")),
        criterion("all task names known", tasks, "subset of Tier 7.0 tasks", all(t in {"mackey_glass", "lorenz", "narma10"} for t in tasks)),
        criterion("all repair/control runs completed", f"{sum(r['status'] == 'pass' for r in all_rows)}/{len(all_rows)}", "all pass", all(r["status"] == "pass" for r in all_rows)),
        criterion("repair outcome classified", repair_classification["outcome"], "non-empty", bool(repair_classification["outcome"])),
        criterion("raw CRA present", "raw_cra_v2_1_online" in models, "== true", "raw_cra_v2_1_online" in models),
        criterion("state repair present", "bounded_state_readout_repair" in models, "== true", "bounded_state_readout_repair" in models),
        criterion("state plus lag repair present", "bounded_state_plus_lag_readout_repair" in models, "== true", "bounded_state_plus_lag_readout_repair" in models),
        criterion("lag-only control present", "lag_only_online_lms_control" in models, "== true", "lag_only_online_lms_control" in models),
        criterion("shuffled controls present", "state_shuffled_feature_control,state_shuffled_target_control", "both present", all(m in models for m in ["state_shuffled_feature_control", "state_shuffled_target_control"])),
        criterion("frozen control present", "state_frozen_no_update_control" in models, "== true", "state_frozen_no_update_control" in models),
    ]
    failed = [c for c in criteria if not c["passed"]]
    payload = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "status": "pass" if not failed else "fail",
        "criteria": criteria,
        "criteria_passed": len(criteria) - len(failed),
        "criteria_total": len(criteria),
        "failed_criteria": failed,
        "tasks": tasks,
        "seeds": seeds,
        "backend": str(args.backend),
        "length": int(args.length),
        "horizon": int(args.horizon),
        "history": int(args.history),
        "runtime_seconds": time.perf_counter() - started,
        "summary_rows": summary_rows,
        "aggregate_rows": aggregate_rows,
        "aggregate_summary": aggregate_summary,
        "classification": repair_classification["outcome"],
        "key_metrics": repair_classification,
        "repair_classification": repair_classification,
        "summary": repair_classification,
        "run_rows": all_rows,
        "trace_diagnostics": trace_diagnostics,
        "fairness_contract": {
            "tier": TIER,
            "source_tiers": ["Tier 7.0", "Tier 7.0b"],
            "same_tasks_and_split": True,
            "feature_normalization": "train prefix only",
            "readout_update": "prediction before update; online normalized LMS; no batch test fit",
            "no_future_leakage": [
                "all repairs consume only current/past features",
                "feature normalization uses train prefix only",
                "online updates occur after each prediction",
                "no model fits on held-out test rows in batch",
            ],
            "nonclaims": [
                "not hardware evidence",
                "not a baseline freeze",
                "not proof of superiority until promotion/regression",
            ],
        },
        "claim_boundary": (
            "Tier 7.0c is software repair-candidate evidence only. It tests a "
            "bounded online continuous readout/interface over causal CRA state "
            "after Tier 7.0b localized the gap. It is not hardware evidence, "
            "not a new baseline freeze, not an unconstrained supervised model, "
            "and not a final superiority claim."
        ),
    }
    write_json(output_dir / "tier7_0c_results.json", payload)
    write_json(output_dir / "tier7_0c_fairness_contract.json", payload["fairness_contract"])
    write_csv(
        output_dir / "tier7_0c_summary.csv",
        summary_rows,
        ["task", "model", "status", "seed_count", "mse_mean", "mse_median", "mse_std", "mse_worst", "nmse_mean", "tail_mse_mean", "test_corr_mean"],
    )
    write_csv(
        output_dir / "tier7_0c_aggregate.csv",
        aggregate_rows,
        ["task", "model", "seed", "status", "geomean_mse", "geomean_nmse"],
    )
    write_csv(
        output_dir / "tier7_0c_timeseries.csv",
        all_timeseries,
        ["task", "seed", "model", "step", "split", "observed", "target", "prediction", "squared_error"],
    )
    write_report(output_dir, payload)
    write_json(
        OUTPUT_ROOT / "tier7_0c_latest_manifest.json",
        {
            "tier": TIER,
            "runner_revision": RUNNER_REVISION,
            "generated_at_utc": payload["generated_at_utc"],
            "status": payload["status"],
            "manifest": str(output_dir / "tier7_0c_results.json"),
            "output_dir": str(output_dir),
        },
    )
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=TIER)
    parser.add_argument("--tasks", default=DEFAULT_TASKS)
    parser.add_argument("--seeds", default="42,43,44")
    parser.add_argument("--seed-count", type=int, default=None)
    parser.add_argument("--base-seed", type=int, default=42)
    parser.add_argument("--length", type=int, default=720)
    parser.add_argument("--horizon", type=int, default=8)
    parser.add_argument("--history", type=int, default=12)
    parser.add_argument("--backend", default="mock")
    parser.add_argument("--cra-population-size", type=int, default=8)
    parser.add_argument("--cra-readout-lr", type=float, default=0.20)
    parser.add_argument("--cra-delayed-lr", type=float, default=0.20)
    parser.add_argument("--readout-lr", type=float, default=0.08)
    parser.add_argument("--readout-decay", type=float, default=1e-5)
    parser.add_argument("--weight-clip", type=float, default=20.0)
    parser.add_argument("--output-clip", type=float, default=3.0)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    payload = run(args)
    print(
        json.dumps(
            {
                "tier": payload["tier"],
                "status": payload["status"],
                "criteria": f"{payload['criteria_passed']}/{payload['criteria_total']}",
                "outcome": payload["repair_classification"]["outcome"],
                "output_dir": str(args.output_dir),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
