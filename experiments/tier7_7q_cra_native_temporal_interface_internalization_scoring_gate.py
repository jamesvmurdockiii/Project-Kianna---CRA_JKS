#!/usr/bin/env python3
"""Tier 7.7q - CRA-native temporal-interface internalization scoring gate.

Scores the Tier 7.7p contract. The candidate is a software proxy for a
CRA-native temporal expansion mechanism: causal delay/trace branches,
thresholded nonlinear branch units, sparse polyp-local sensory projections, and
recurrent sensory-basis state. It must beat or cleanly separate from the strong
random-projection and nonlinear-lag controls before any promotion.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from tier5_19a_temporal_substrate_reference import FeatureBundle, criterion, json_safe, parse_timescales  # noqa: E402
from tier5_19b_temporal_substrate_gate import temporal_features_variant  # noqa: E402
from tier7_0_standard_dynamical_benchmarks import parse_csv, parse_seeds  # noqa: E402
from tier7_0c_continuous_readout_repair import shuffled_rows, shuffled_target  # noqa: E402
from tier7_7j_capacity_sham_separation_scoring_gate import (  # noqa: E402
    TARGET_SHUFFLE,
    TIME_SHUFFLE,
    build_task,
    geometry_metrics,
    hidden_columns,
    metric,
    readout_metrics,
    run_probe_model,
    safe_float,
    summarize_numeric,
    summarize_scoreboard,
    utc_now,
    write_json,
    write_rows,
)
from tier7_7l_effective_state_dimensionality_repair_scoring_gate import ratio  # noqa: E402
from tier7_7n_partitioned_driver_attribution_scoring_gate import (  # noqa: E402
    NONLINEAR_LAG,
    RANDOM_PROJECTION,
    nonlinear_lag_unpartitioned_features,
    random_projection_features,
)


TIER = "Tier 7.7q - CRA-Native Temporal-Interface Internalization Scoring Gate"
RUNNER_REVISION = "tier7_7q_cra_native_temporal_interface_internalization_scoring_gate_20260509_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_7q_20260509_cra_native_temporal_interface_internalization_scoring_gate"
CONTRACT_77P = CONTROLLED / "tier7_7p_20260509_cra_native_temporal_interface_internalization_contract" / "tier7_7p_results.json"

DEFAULT_TASKS = "mackey_glass,lorenz,narma10"
DEFAULT_LENGTHS = "8000,16000,32000"
DEFAULT_SEEDS = "42,43,44"
DEFAULT_CAPACITIES = "16,32,64,128"

NATIVE = "cra_native_sparse_temporal_expansion"
NO_NONLINEARITY = "temporal_expansion_no_nonlinearity"
NO_DELAY = "temporal_expansion_no_delays"
CURRENT = "current_cra_baseline"


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def parse_int_csv(raw: str) -> list[int]:
    values = [int(item) for item in parse_csv(raw)]
    if not values:
        raise ValueError("at least one integer value is required")
    return values


def causal_temporal_drivers(values: np.ndarray, timescales: list[float], *, include_delay: bool = True) -> tuple[np.ndarray, list[str]]:
    values = np.asarray(values, dtype=float)
    traces = np.zeros(len(timescales), dtype=float)
    lag_steps = [1, 2, 4, 8, 16, 32]
    rows: list[np.ndarray] = []
    for step, value in enumerate(values):
        x = float(value)
        previous = traces.copy()
        for idx, tau in enumerate(timescales):
            alpha = 1.0 - math.exp(-1.0 / max(1e-6, float(tau)))
            traces[idx] = traces[idx] + alpha * (x - traces[idx])
        trace_deltas = np.diff(traces) if traces.size > 1 else np.asarray([], dtype=float)
        novelty = x - float(previous[-1] if previous.size else 0.0)
        base = [x, novelty, *traces.tolist(), *trace_deltas.tolist()]
        if include_delay:
            lags = [float(values[step - lag]) if step - lag >= 0 else 0.0 for lag in lag_steps]
            lag_deltas = [x - lag for lag in lags]
            base.extend(lags)
            base.extend(lag_deltas)
        rows.append(np.asarray(base, dtype=float))
    names = ["observed_current", "novelty_vs_slowest_ema"]
    names += [f"trace_tau_{tau:g}" for tau in timescales]
    names += [f"trace_delta_{idx}_{idx+1}" for idx in range(max(0, len(timescales) - 1))]
    if include_delay:
        names += [f"lag_{lag}" for lag in lag_steps]
        names += [f"lag_delta_{lag}" for lag in lag_steps]
    return np.vstack(rows), names


def native_temporal_expansion_features(
    observed: np.ndarray,
    *,
    seed: int,
    train_end: int,
    timescales: list[float],
    hidden_units: int,
    recurrent_scale: float,
    input_scale: float,
    hidden_decay: float,
    mode: str,
) -> FeatureBundle:
    include_delay = mode != NO_DELAY
    nonlinear = mode != NO_NONLINEARITY
    drivers, driver_names = causal_temporal_drivers(np.asarray(observed, dtype=float), timescales, include_delay=include_delay)
    hidden_units = max(1, int(hidden_units))
    rng = np.random.default_rng(seed + 104729 + hidden_units)
    sparse = rng.normal(0.0, float(input_scale), size=(hidden_units, drivers.shape[1]))
    mask = rng.random(size=sparse.shape) < min(0.45, max(0.10, 8.0 / max(1, drivers.shape[1])))
    sparse *= mask
    rec_raw = rng.normal(0.0, 1.0, size=(hidden_units, hidden_units))
    rec_mask = rng.random(size=rec_raw.shape) < min(0.12, max(0.02, 4.0 / max(1, hidden_units)))
    rec_raw *= rec_mask
    if hidden_units > 1:
        spectral = max(1e-6, float(np.max(np.abs(np.linalg.eigvals(rec_raw)))))
        rec = rec_raw / spectral * float(recurrent_scale)
    else:
        rec = np.zeros((hidden_units, hidden_units), dtype=float)
    thresholds = rng.normal(0.0, 0.35, size=hidden_units)
    branch_decay = np.linspace(float(hidden_decay) - 0.08, float(hidden_decay) + 0.08, hidden_units)
    branch_decay = np.clip(branch_decay, 0.35, 0.96)
    membrane = np.zeros(hidden_units, dtype=float)
    branch = np.zeros(hidden_units, dtype=float)
    rows: list[np.ndarray] = []
    for driver in drivers:
        membrane = branch_decay * membrane + sparse @ driver + rec @ branch
        if nonlinear:
            positive = np.maximum(0.0, membrane - thresholds)
            negative = np.maximum(0.0, -membrane - thresholds)
            branch = np.tanh(positive) - 0.5 * np.tanh(negative)
        else:
            branch = np.clip(membrane, -3.0, 3.0) / 3.0
        rows.append(np.concatenate([[1.0], driver, branch]))
    names = ["bias"] + driver_names + [f"hidden_{idx}" for idx in range(hidden_units)]
    diagnostics = {
        "mode": mode,
        "state_location": "CRA-native sparse temporal expansion proxy",
        "native_proxy": True,
        "causal_only": True,
        "hidden_units": int(hidden_units),
        "feature_count": int(len(names)),
        "include_delay": include_delay,
        "nonlinear_branch_units": nonlinear,
        "input_sparsity": float(np.mean(mask)),
        "recurrent_sparsity": float(np.mean(rec_mask)),
        "train_end": int(train_end),
    }
    return FeatureBundle(features=np.vstack(rows), temporal_start=len(names) - hidden_units, names=names, diagnostics=diagnostics)


def make_bundle(features: np.ndarray, names: list[str], temporal_start: int, diagnostics: dict[str, Any]) -> FeatureBundle:
    return FeatureBundle(features=features, temporal_start=temporal_start, names=names, diagnostics=diagnostics)


def run_family(task: Any, *, seed: int, length: int, capacity: int, args: argparse.Namespace) -> list[Any]:
    timescales = parse_timescales(args.temporal_timescales)
    base = {
        "seed": seed,
        "train_end": task.train_end,
        "timescales": timescales,
        "hidden_units": capacity,
        "recurrent_scale": args.temporal_recurrent_scale,
        "input_scale": args.temporal_input_scale,
        "hidden_decay": args.temporal_hidden_decay,
    }
    bundles: list[tuple[str, FeatureBundle, str]] = []
    native = native_temporal_expansion_features(task.observed, mode=NATIVE, **base)
    bundles.append((NATIVE, native, "CRA-native temporal expansion candidate"))
    bundles.append((NO_NONLINEARITY, native_temporal_expansion_features(task.observed, mode=NO_NONLINEARITY, **base), "nonlinearity ablation"))
    bundles.append((NO_DELAY, native_temporal_expansion_features(task.observed, mode=NO_DELAY, **base), "delay/trace ablation"))
    bundles.append((RANDOM_PROJECTION, random_projection_features(task.observed, seed=seed, train_end=task.train_end, timescales=timescales, hidden_units=capacity, input_scale=args.temporal_input_scale), "strong random-projection control"))
    bundles.append((NONLINEAR_LAG, nonlinear_lag_unpartitioned_features(task.observed, **base), "strong nonlinear/lag control"))
    current = temporal_features_variant(task.observed, mode="full", **base)
    bundles.append((CURRENT, make_bundle(current.features, current.names, current.temporal_start, {**current.diagnostics, "mode": CURRENT}), "current CRA temporal-state baseline"))
    results: list[Any] = []
    for family, bundle, role in bundles:
        results.append(
            run_probe_model(
                task,
                seed=seed,
                length=length,
                capacity=capacity,
                probe_family=family,
                probe_id=f"{family}_{capacity}",
                features=bundle.features,
                feature_names=bundle.names,
                hidden_columns=hidden_columns(bundle.names),
                args=args,
                diagnostics={**bundle.diagnostics, "role": role},
            )
        )
    wrong_target = shuffled_target(task.target, task.train_end, seed)
    results.append(
        run_probe_model(
            task,
            seed=seed,
            length=length,
            capacity=capacity,
            probe_family=TARGET_SHUFFLE,
            probe_id=f"{TARGET_SHUFFLE}_{capacity}",
            features=native.features,
            feature_names=native.names,
            hidden_columns=hidden_columns(native.names),
            args=args,
            update_target=wrong_target,
            diagnostics={**native.diagnostics, "control": "target shuffle native candidate"},
        )
    )
    results.append(
        run_probe_model(
            task,
            seed=seed,
            length=length,
            capacity=capacity,
            probe_family=TIME_SHUFFLE,
            probe_id=f"{TIME_SHUFFLE}_{capacity}",
            features=shuffled_rows(native.features, task.train_end, seed),
            feature_names=native.names,
            hidden_columns=hidden_columns(native.names),
            args=args,
            diagnostics={**native.diagnostics, "control": "time/row shuffle native candidate"},
        )
    )
    return results


def summarize_budget(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault((row["probe_family"], int(row["capacity_units"])), []).append(row)
    out: list[dict[str, Any]] = []
    for (family, capacity), items in sorted(grouped.items()):
        feature_counts = [safe_float((item.get("diagnostics") or {}).get("feature_count")) for item in items]
        feature_counts = [value for value in feature_counts if value is not None]
        out.append({"probe_family": family, "capacity_units": capacity, "feature_count_mean": float(np.mean(feature_counts)) if feature_counts else None, "run_count": len(items)})
    return out


def classify(score_summary: list[dict[str, Any]], prereq: dict[str, Any]) -> dict[str, Any]:
    def score(task: str, family: str, capacity: int = 128) -> float | None:
        return metric(score_summary, task, family, capacity)

    native_lorenz = score("lorenz", NATIVE)
    random_lorenz = score("lorenz", RANDOM_PROJECTION)
    nonlinear_lorenz = score("lorenz", NONLINEAR_LAG)
    current_lorenz = score("lorenz", CURRENT)
    no_nonlin = score("lorenz", NO_NONLINEARITY)
    no_delay = score("lorenz", NO_DELAY)
    target = score("lorenz", TARGET_SHUFFLE)
    time_shuf = score("lorenz", TIME_SHUFFLE)
    random_margin = ratio(random_lorenz, native_lorenz)
    nonlinear_margin = ratio(nonlinear_lorenz, native_lorenz)
    current_margin = ratio(current_lorenz, native_lorenz)
    no_nonlin_margin = ratio(no_nonlin, native_lorenz)
    no_delay_margin = ratio(no_delay, native_lorenz)
    target_guard = ratio(target, native_lorenz)
    time_guard = ratio(time_shuf, native_lorenz)
    regressions_ok = all(
        ratio(score(task, NATIVE), score(task, CURRENT)) is not None and ratio(score(task, NATIVE), score(task, CURRENT)) <= 1.10
        for task in ["mackey_glass", "narma10"]
    )
    useful_vs_current = current_margin is not None and current_margin >= 1.10
    beats_random = random_margin is not None and random_margin >= 1.05
    beats_nonlinear = nonlinear_margin is not None and nonlinear_margin >= 1.05
    matches_strong = all(value is not None and value >= 0.98 for value in [random_margin, nonlinear_margin])
    ablations_hurt = any(value is not None and value >= 1.05 for value in [no_nonlin_margin, no_delay_margin])
    guards_ok = (target_guard is not None and target_guard >= 5.0) and (time_guard is not None and time_guard >= 5.0)
    if not guards_ok or not regressions_ok:
        outcome = "regression_or_leakage_blocked"
        recommendation = "Do not promote; candidate failed regression or leakage guards."
    elif beats_random and beats_nonlinear and useful_vs_current and ablations_hurt:
        outcome = "native_temporal_interface_promotable_candidate"
        recommendation = "Candidate is eligible for compact promotion/regression gate before any freeze."
    elif not matches_strong:
        outcome = "external_controls_still_win"
        recommendation = "External controls still beat the native candidate; do not promote."
    elif not ablations_hurt:
        outcome = "ablation_not_causal"
        recommendation = "Candidate may score well, but internal ablations did not establish causality."
    else:
        outcome = "inconclusive"
        recommendation = "No promotion; inspect artifacts and refine only through a new contract."
    return {
        "outcome": outcome,
        "recommendation": recommendation,
        "diagnostics": {
            "native_lorenz_128_geomean_mse": native_lorenz,
            "random_projection_lorenz_128_geomean_mse": random_lorenz,
            "nonlinear_lag_lorenz_128_geomean_mse": nonlinear_lorenz,
            "current_lorenz_128_geomean_mse": current_lorenz,
            "no_nonlinearity_lorenz_128_geomean_mse": no_nonlin,
            "no_delay_lorenz_128_geomean_mse": no_delay,
            "random_projection_divided_by_native": random_margin,
            "nonlinear_lag_divided_by_native": nonlinear_margin,
            "current_divided_by_native": current_margin,
            "no_nonlinearity_divided_by_native": no_nonlin_margin,
            "no_delay_divided_by_native": no_delay_margin,
            "target_shuffle_divided_by_native": target_guard,
            "time_shuffle_divided_by_native": time_guard,
            "useful_vs_current": useful_vs_current,
            "beats_random_projection": beats_random,
            "beats_nonlinear_lag": beats_nonlinear,
            "matches_strong_controls": matches_strong,
            "ablations_hurt": ablations_hurt,
            "guards_ok": guards_ok,
            "regressions_ok": regressions_ok,
        },
        "claim_allowed": {"promotion_candidate": outcome == "native_temporal_interface_promotable_candidate", "mechanism_promotion": False, "baseline_freeze": False, "hardware_or_native_transfer": False, "public_usefulness": False},
        "nonclaims": ["not a baseline freeze", "not a mechanism promotion", "not hardware/native transfer", "not external-baseline superiority", "not broad public usefulness", "not language, AGI, or ASI evidence"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=TIER)
    parser.add_argument("--tasks", default=DEFAULT_TASKS)
    parser.add_argument("--lengths", default=DEFAULT_LENGTHS)
    parser.add_argument("--seeds", default=DEFAULT_SEEDS)
    parser.add_argument("--capacities", default=DEFAULT_CAPACITIES)
    parser.add_argument("--horizon", type=int, default=8)
    parser.add_argument("--readout-lr", type=float, default=0.08)
    parser.add_argument("--readout-decay", type=float, default=1e-5)
    parser.add_argument("--weight-clip", type=float, default=20.0)
    parser.add_argument("--output-clip", type=float, default=3.0)
    parser.add_argument("--temporal-timescales", default="2,4,8,16,32,64,128")
    parser.add_argument("--temporal-recurrent-scale", type=float, default=0.65)
    parser.add_argument("--temporal-input-scale", type=float, default=0.45)
    parser.add_argument("--temporal-hidden-decay", type=float, default=0.72)
    parser.add_argument("--state-reset-interval", type=int, default=64)
    parser.add_argument("--delay-embedding-history", type=int, default=64)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--smoke", action="store_true")
    return parser


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if args.smoke:
        args.tasks = "lorenz"
        args.lengths = "720"
        args.seeds = "42"
        args.capacities = "16,32"
    tasks = parse_csv(args.tasks)
    lengths = parse_int_csv(args.lengths)
    seeds = parse_seeds(argparse.Namespace(seeds=args.seeds, seed_count=None, base_seed=42))
    capacities = parse_int_csv(args.capacities)
    started = time.perf_counter()
    contract = read_json(CONTRACT_77P)
    scoreboard_rows: list[dict[str, Any]] = []
    geometry_rows: list[dict[str, Any]] = []
    readout_rows: list[dict[str, Any]] = []
    task_descriptors: list[dict[str, Any]] = []
    invalid_tasks: list[dict[str, Any]] = []
    for length in lengths:
        for seed in seeds:
            for task_name in tasks:
                task = build_task(task_name, length, seed, args.horizon)
                finite = bool(np.all(np.isfinite(task.observed)) and np.all(np.isfinite(task.target)))
                task_descriptors.append({"task": task.name, "length": int(length), "seed": int(seed), "horizon": int(task.horizon), "train_end": int(task.train_end), "sample_count": int(len(task.target)), "finite": finite, "metadata": task.metadata})
                if not finite:
                    invalid_tasks.append(task_descriptors[-1])
                    continue
                for capacity in capacities:
                    for result in run_family(task, seed=seed, length=length, capacity=capacity, args=args):
                        scoreboard_rows.append(result.row)
                        geometry_rows.append({"task": task.name, "length": int(length), "seed": int(seed), "capacity_units": int(capacity), "probe_family": result.row["probe_family"], "probe_id": result.row["probe_id"], **geometry_metrics(result.features, result.hidden_columns, task.train_end)})
                        readout_rows.append({"task": task.name, "length": int(length), "seed": int(seed), "capacity_units": int(capacity), "probe_family": result.row["probe_family"], "probe_id": result.row["probe_id"], **readout_metrics(result.weights, result.hidden_columns)})
    score_summary = summarize_scoreboard(scoreboard_rows)
    geometry_summary = summarize_numeric(geometry_rows, ["participation_ratio", "participation_ratio_per_unit", "rank95_variance_count", "top_pc_fraction", "state_norm_mean", "state_norm_std", "step_delta_mean", "step_delta_std", "total_state_variance"], ["task", "probe_family", "capacity_units"])
    readout_summary = summarize_numeric(readout_rows, ["readout_weight_pr", "top_weight_fraction", "hidden_weight_energy_fraction", "final_weight_norm"], ["task", "probe_family", "capacity_units"])
    budget = summarize_budget(scoreboard_rows)
    classification = classify(score_summary, contract)
    regression_summary = {"compact_regression_inside_gate": False, "required_before_promotion": True, "reason": "Tier 7.7q is a scoring gate. Passing routes to separate compact promotion/regression before freeze."}
    criteria = [
        criterion("Tier 7.7p contract exists", str(CONTRACT_77P), "exists and pass", bool(contract) and contract.get("status") == "pass"),
        criterion("locked tasks", tasks, "Mackey/Lorenz/NARMA", set(tasks) == {"mackey_glass", "lorenz", "narma10"} or bool(args.smoke)),
        criterion("locked lengths", lengths, "8000/16000/32000", lengths == [8000, 16000, 32000] or bool(args.smoke)),
        criterion("locked seeds", seeds, "42/43/44", seeds == [42, 43, 44] or bool(args.smoke)),
        criterion("locked capacities", capacities, "16/32/64/128", capacities == [16, 32, 64, 128] or bool(args.smoke)),
        criterion("finite generated streams", len(invalid_tasks), "== 0", len(invalid_tasks) == 0),
        criterion("scoreboard produced", len(scoreboard_rows), "> 0", len(scoreboard_rows) > 0),
        criterion("state geometry produced", len(geometry_rows), "> 0", len(geometry_rows) > 0),
        criterion("readout audit produced", len(readout_rows), "> 0", len(readout_rows) > 0),
        criterion("budget audit produced", len(budget), "> 0", len(budget) > 0),
        criterion("classification produced", classification["outcome"], "non-empty", bool(classification["outcome"])),
        criterion("no baseline freeze", classification["claim_allowed"]["baseline_freeze"], "false", classification["claim_allowed"]["baseline_freeze"] is False),
        criterion("no mechanism promotion", classification["claim_allowed"]["mechanism_promotion"], "false", classification["claim_allowed"]["mechanism_promotion"] is False),
        criterion("hardware/native transfer blocked", classification["claim_allowed"]["hardware_or_native_transfer"], "false", classification["claim_allowed"]["hardware_or_native_transfer"] is False),
    ]
    passed = sum(1 for item in criteria if item["passed"])
    status = "pass" if passed == len(criteria) else "fail"
    claim_boundary = "Tier 7.7q scores the locked 7.7p CRA-native temporal-interface internalization candidate. It may support or block the candidate diagnostically, but it does not freeze a baseline, promote a mechanism, authorize hardware/native transfer, or claim broad public usefulness."
    payload = {"tier": TIER, "runner_revision": RUNNER_REVISION, "generated_at_utc": utc_now(), "status": status, "criteria": criteria, "criteria_passed": passed, "criteria_total": len(criteria), "output_dir": str(output_dir), "tasks": tasks, "lengths": lengths, "seeds": seeds, "capacities": capacities, "classification": classification, "scoreboard_rows": scoreboard_rows, "score_summary": score_summary, "mechanism_ablations": [row for row in scoreboard_rows if row.get("probe_family") in {NO_NONLINEARITY, NO_DELAY}], "budget_audit": budget, "state_geometry": geometry_rows, "state_geometry_summary": geometry_summary, "strong_controls": [row for row in scoreboard_rows if row.get("probe_family") in {RANDOM_PROJECTION, NONLINEAR_LAG}], "readout_audit": readout_rows, "readout_audit_summary": readout_summary, "task_descriptors": task_descriptors, "invalid_tasks": invalid_tasks, "regression_summary": regression_summary, "claim_boundary": claim_boundary, "runtime_seconds": time.perf_counter() - started}
    prefix = "tier7_7q"
    write_json(output_dir / f"{prefix}_results.json", payload)
    write_rows(output_dir / f"{prefix}_summary.csv", criteria)
    write_rows(output_dir / f"{prefix}_scoreboard.csv", scoreboard_rows)
    write_rows(output_dir / f"{prefix}_score_summary.csv", score_summary)
    write_rows(output_dir / f"{prefix}_mechanism_ablations.csv", payload["mechanism_ablations"])
    write_rows(output_dir / f"{prefix}_budget_audit.csv", budget)
    write_rows(output_dir / f"{prefix}_state_geometry.csv", geometry_rows)
    write_rows(output_dir / f"{prefix}_state_geometry_summary.csv", geometry_summary)
    write_rows(output_dir / f"{prefix}_strong_controls.csv", payload["strong_controls"])
    write_json(output_dir / f"{prefix}_regression_summary.json", regression_summary)
    write_json(output_dir / f"{prefix}_task_descriptors.json", task_descriptors)
    write_json(output_dir / f"{prefix}_probe_manifest.json", {"tasks": tasks, "lengths": lengths, "seeds": seeds, "capacities": capacities, "candidate": NATIVE})
    (output_dir / f"{prefix}_claim_boundary.md").write_text(claim_boundary + "\n", encoding="utf-8")
    report = ["# Tier 7.7q CRA-Native Temporal-Interface Internalization Scoring Gate", "", f"- Generated: `{payload['generated_at_utc']}`", f"- Status: **{status.upper()}**", f"- Criteria: `{passed}/{len(criteria)}`", f"- Outcome: `{classification['outcome']}`", f"- Recommendation: {classification['recommendation']}", "", "## Boundary", "", claim_boundary, "", "## Diagnostics", ""]
    for key, value in classification["diagnostics"].items():
        report.append(f"- {key}: `{value}`")
    report.extend(["", "## Nonclaims", ""])
    report.extend(f"- {item}" for item in classification["nonclaims"])
    report.append("")
    (output_dir / f"{prefix}_report.md").write_text("\n".join(report), encoding="utf-8")
    manifest = {"tier": TIER, "status": status, "generated_at_utc": payload["generated_at_utc"], "output_dir": str(output_dir), "results_json": str(output_dir / f"{prefix}_results.json"), "report_md": str(output_dir / f"{prefix}_report.md"), "summary_csv": str(output_dir / f"{prefix}_summary.csv"), "classification_outcome": classification["outcome"]}
    write_json(output_dir / f"{prefix}_latest_manifest.json", manifest)
    write_json(CONTROLLED / f"{prefix}_latest_manifest.json", manifest)
    return payload


def main() -> int:
    args = build_parser().parse_args()
    payload = run(args)
    print(json.dumps(json_safe({"status": payload["status"], "criteria": f"{payload['criteria_passed']}/{payload['criteria_total']}", "classification": payload["classification"]["outcome"], "output_dir": payload["output_dir"]}), indent=2, sort_keys=True))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
