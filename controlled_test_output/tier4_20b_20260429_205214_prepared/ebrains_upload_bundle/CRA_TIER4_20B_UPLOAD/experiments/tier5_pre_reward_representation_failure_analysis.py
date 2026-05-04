#!/usr/bin/env python3
"""Tier 5.17b pre-reward representation failure analysis.

This tier does not introduce a new representation mechanism. It diagnoses the
failed Tier 5.17 bundle and answers four questions:

1. Did the candidate form any measurable structure at all?
2. Did simple controls or visible encoders explain the result?
3. Did temporal order matter?
4. Did frozen representations improve downstream sample efficiency?

A pass here means the failure is classified and the next repair is bounded. It
does not promote pre-reward representation learning and does not freeze a new
baseline.
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

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except Exception as exc:  # pragma: no cover - optional plotting dependency
    plt = None
    MATPLOTLIB_ERROR = str(exc)
else:
    MATPLOTLIB_ERROR = None

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from tier2_learning import criterion, markdown_value, pass_fail, write_csv, write_json  # noqa: E402

TIER = "Tier 5.17b - Pre-Reward Representation Failure Analysis"
CANDIDATE = "cra_pre_reward_state"
EPS = 1e-12


FAILURE_MODE_DESCRIPTIONS = {
    "input_encoded_too_easy": "Visible input or simple history already recovers the latent target, so the task cannot prove representation formation.",
    "history_baseline_dominates": "A fixed rolling-history or random-projection history baseline solves the task far better than the candidate, so the candidate lacks sufficient temporal state.",
    "candidate_structure_but_no_sample_efficiency": "The candidate forms structure and beats controls, but it needs too many labels downstream or does not improve sample efficiency enough.",
    "candidate_structure_present": "The candidate forms useful structure and separates from controls on this task, but this alone is not enough for full-tier promotion.",
    "no_structure": "The candidate does not separate from random/untrained state enough to show measurable structure.",
    "mixed_or_ambiguous": "The diagnostic signals are mixed and require sharper task pressure before a mechanism claim.",
}


REPAIR_MAP = {
    "input_encoded_too_easy": "repair_task_pressure: use same-visible-input/different-latent-state streams, masked-channel recovery, or held-out cross-channel binding so input-only/history controls cannot solve the task.",
    "history_baseline_dominates": "repair_mechanism: add an intrinsic predictive/MI objective so internal state learns temporal continuation instead of relying on fixed history features.",
    "candidate_structure_but_no_sample_efficiency": "repair_transfer: add freeze/partial-freeze and consolidation transfer checks to prove preexposed structure is usable downstream.",
    "candidate_structure_present": "retain_as_positive_subcase: keep task as evidence of possible structure but require additional tasks and transfer gates before promotion.",
    "no_structure": "repair_mechanism: add label-free predictive, masked-input, novelty-reduction, or sensory-trophic objective before retesting.",
    "mixed_or_ambiguous": "repair_design: sharpen tasks and controls, then rerun before adding a promoted mechanism.",
}


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
        f = float(value)
        return None if math.isnan(f) or math.isinf(f) else f
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def f(row: dict[str, Any], key: str, default: float = 0.0) -> float:
    raw = row.get(key, default)
    if raw is None or raw == "":
        return default
    try:
        value = float(raw)
    except Exception:
        return default
    if math.isnan(value) or math.isinf(value):
        return default
    return value


def maybe_float(row: dict[str, Any], key: str) -> float | None:
    raw = row.get(key)
    if raw is None or raw == "":
        return None
    try:
        value = float(raw)
    except Exception:
        return None
    if math.isnan(value) or math.isinf(value):
        return None
    return value


def latest_tier5_17_dir() -> Path:
    latest = ROOT / "controlled_test_output" / "tier5_17_latest_manifest.json"
    payload = read_json(latest)
    return Path(payload["output_dir"])


def load_bundle(bundle_dir: Path) -> dict[str, Any]:
    manifest = read_json(bundle_dir / "tier5_17_results.json")
    comparisons = read_csv(bundle_dir / "tier5_17_comparisons.csv")
    summary = read_csv(bundle_dir / "tier5_17_summary.csv")
    runs = read_csv(bundle_dir / "tier5_17_runs.csv")
    return {
        "bundle_dir": bundle_dir,
        "manifest": manifest,
        "comparisons": comparisons,
        "summary": summary,
        "runs": runs,
    }


def task_summary_rows(summary_rows: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    return {(row["task"], row["variant"]): row for row in summary_rows}


def classify_task(row: dict[str, Any], summary_lookup: dict[tuple[str, str], dict[str, Any]], args: argparse.Namespace) -> dict[str, Any]:
    task = str(row["task"])
    temporal = str(row.get("temporal_pressure", "False")).lower() == "true"
    candidate = f(row, "candidate_ridge_accuracy")
    candidate_knn = f(row, "candidate_knn_accuracy")
    random_acc = f(row, "random_untrained_state_ridge_accuracy")
    no_plasticity = f(row, "no_state_plasticity_ridge_accuracy")
    current_input = f(row, "current_input_only_ridge_accuracy")
    history = f(row, "rolling_history_input_ridge_accuracy")
    random_projection = f(row, "random_projection_history_ridge_accuracy")
    time_shuffle = f(row, "time_shuffled_exposure_ridge_accuracy")
    temporal_destroyed = f(row, "temporal_destroyed_exposure_ridge_accuracy")
    best_control_name = str(row.get("best_non_oracle_control", ""))
    best_control = f(row, "best_non_oracle_ridge_accuracy")
    edge_random = candidate - random_acc
    edge_no_plasticity = candidate - no_plasticity
    edge_current_input = candidate - current_input
    edge_history = candidate - max(history, random_projection)
    edge_best = candidate - best_control
    edge_time_shuffle = candidate - time_shuffle
    edge_temporal_destroyed = candidate - temporal_destroyed
    labels_to_threshold = maybe_float(row, "candidate_labels_to_threshold")
    best_history_labels = min(
        [v for v in [maybe_float(row, "rolling_history_input_labels_to_threshold"), maybe_float(row, "random_projection_history_labels_to_threshold")] if v is not None],
        default=None,
    )

    structure_present = bool(
        candidate >= float(args.min_structure_probe_accuracy)
        and edge_random >= float(args.min_edge_vs_random_for_structure)
    )
    temporal_order_matters = bool(
        temporal
        and edge_time_shuffle >= float(args.min_temporal_edge)
        and edge_temporal_destroyed >= float(args.min_temporal_edge)
    )
    controls_explain = bool(
        edge_best <= float(args.max_edge_for_control_explains)
        or (current_input >= float(args.control_solves_accuracy) and edge_current_input <= float(args.max_edge_for_control_explains))
        or (max(history, random_projection) >= float(args.control_solves_accuracy) and edge_history <= float(args.max_edge_for_control_explains))
    )
    sample_efficiency_ok = bool(
        labels_to_threshold is not None
        and (
            best_history_labels is None
            or labels_to_threshold <= best_history_labels * float(args.max_sample_efficiency_ratio)
        )
    )

    if not structure_present:
        mode = "no_structure"
    elif controls_explain and (current_input >= args.control_solves_accuracy or task == "latent_cluster_sequence"):
        mode = "input_encoded_too_easy"
    elif controls_explain and max(history, random_projection) >= args.control_solves_accuracy:
        mode = "history_baseline_dominates"
    elif structure_present and not sample_efficiency_ok:
        mode = "candidate_structure_but_no_sample_efficiency"
    elif structure_present and not controls_explain:
        mode = "candidate_structure_present"
    else:
        mode = "mixed_or_ambiguous"

    candidate_summary = summary_lookup.get((task, CANDIDATE), {})
    return {
        "task": task,
        "temporal_pressure": temporal,
        "candidate_ridge_accuracy": candidate,
        "candidate_knn_accuracy": candidate_knn,
        "candidate_silhouette": f(row, "candidate_silhouette"),
        "random_untrained_accuracy": random_acc,
        "no_plasticity_accuracy": no_plasticity,
        "current_input_accuracy": current_input,
        "rolling_history_accuracy": history,
        "random_projection_accuracy": random_projection,
        "time_shuffled_accuracy": time_shuffle,
        "temporal_destroyed_accuracy": temporal_destroyed,
        "best_non_oracle_control": best_control_name,
        "best_non_oracle_accuracy": best_control,
        "edge_vs_random": edge_random,
        "edge_vs_no_plasticity": edge_no_plasticity,
        "edge_vs_current_input": edge_current_input,
        "edge_vs_history_best": edge_history,
        "edge_vs_best_non_oracle": edge_best,
        "edge_vs_time_shuffle": edge_time_shuffle,
        "edge_vs_temporal_destroyed": edge_temporal_destroyed,
        "candidate_labels_to_threshold": labels_to_threshold,
        "best_history_labels_to_threshold": best_history_labels,
        "structure_present": structure_present,
        "temporal_order_matters": temporal_order_matters,
        "controls_explain": controls_explain,
        "sample_efficiency_ok": sample_efficiency_ok,
        "failure_mode": mode,
        "failure_mode_description": FAILURE_MODE_DESCRIPTIONS[mode],
        "repair_recommendation": REPAIR_MAP[mode],
        "mean_latent_factor_abs_corr": maybe_float(candidate_summary, "mean_latent_factor_abs_corr"),
        "mean_silhouette_score": maybe_float(candidate_summary, "mean_silhouette_score"),
    }


def summarize_failure_modes(task_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    modes = sorted({row["failure_mode"] for row in task_rows})
    out = []
    for mode in modes:
        rows = [row for row in task_rows if row["failure_mode"] == mode]
        out.append(
            {
                "failure_mode": mode,
                "task_count": len(rows),
                "tasks": ",".join(row["task"] for row in rows),
                "description": FAILURE_MODE_DESCRIPTIONS[mode],
                "repair_recommendation": REPAIR_MAP[mode],
            }
        )
    return out


def choose_overall_decision(task_rows: list[dict[str, Any]]) -> dict[str, Any]:
    modes = [row["failure_mode"] for row in task_rows]
    counts = {mode: modes.count(mode) for mode in sorted(set(modes))}
    temporal_failures = [row for row in task_rows if row["temporal_pressure"] and row["failure_mode"] in {"history_baseline_dominates", "no_structure"}]
    too_easy = [row for row in task_rows if row["failure_mode"] == "input_encoded_too_easy"]
    positive = [row for row in task_rows if row["failure_mode"] == "candidate_structure_present"]

    if temporal_failures:
        next_step = "Tier 5.17c - intrinsic predictive / MI-based preexposure objective"
        rationale = "Temporal-pressure tasks expose that fixed history can dominate the current scaffold, so the next repair should give CRA an intrinsic label-free reason to learn temporal continuation or masked-channel structure."
        classification = "mechanism_needs_intrinsic_predictive_objective"
    elif too_easy and not positive:
        next_step = "Tier 5.17b-task-repair - sharper representation pressure"
        rationale = "The tasks are too visible-input-solvable to evaluate representation formation."
        classification = "task_pressure_insufficient"
    elif positive and len(positive) < len(task_rows):
        next_step = "Tier 5.17c - predictive objective plus transfer/freeze gate"
        rationale = "One or more tasks show structure, but not enough task coverage or sample-efficiency transfer for promotion."
        classification = "mixed_structure_not_promotable"
    else:
        next_step = "Tier 5.17c - repair mechanism before promotion"
        rationale = "The diagnostic is mixed and does not justify a paper claim."
        classification = "mixed_or_ambiguous"

    return {
        "classification": classification,
        "failure_mode_counts": counts,
        "next_step": next_step,
        "rationale": rationale,
        "promote_pre_reward_representation": False,
        "revisit_tier5_9_now": False,
        "tier5_9_revisit_rule": "Only revisit delayed-credit / eligibility if a future pre-reward mechanism forms useful structure but downstream reward cannot credit, preserve, or use it.",
    }


def leakage_summary(runs: list[dict[str, Any]]) -> dict[str, Any]:
    non_oracle = [row for row in runs if str(row.get("uses_hidden_labels", "False")).lower() != "true"]
    label_leakage = sum(1 for row in non_oracle if str(row.get("labels_visible_during_exposure", "False")).lower() == "true")
    reward_leakage = sum(1 for row in runs if str(row.get("reward_visible_during_exposure", "False")).lower() == "true")
    max_da = max([abs(f(row, "max_abs_raw_dopamine")) for row in non_oracle] or [0.0])
    return {
        "non_oracle_run_count": len(non_oracle),
        "label_leakage_runs": label_leakage,
        "reward_leakage_runs": reward_leakage,
        "max_abs_raw_dopamine_non_oracle": max_da,
    }


def plot_failure_modes(path: Path, task_rows: list[dict[str, Any]]) -> None:
    if plt is None:
        path.with_suffix(".txt").write_text(f"matplotlib unavailable: {MATPLOTLIB_ERROR}\n", encoding="utf-8")
        return
    labels = [row["task"].replace("_", "\n") for row in task_rows]
    x = np.arange(len(labels))
    width = 0.22
    series = [
        ("candidate", [row["candidate_ridge_accuracy"] for row in task_rows]),
        ("best control", [row["best_non_oracle_accuracy"] for row in task_rows]),
        ("random", [row["random_untrained_accuracy"] for row in task_rows]),
    ]
    fig, ax = plt.subplots(figsize=(11, 5.5))
    for idx, (name, vals) in enumerate(series):
        ax.bar(x + (idx - 1) * width, vals, width, label=name)
    ax.axhline(0.72, color="black", linewidth=0.9, linestyle="--", label="candidate gate")
    ax.set_ylim(0.0, 1.05)
    ax.set_ylabel("ridge probe accuracy")
    ax.set_title("Tier 5.17b failure-analysis classification")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.grid(axis="y", alpha=0.25)
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def write_report(path: Path, result: dict[str, Any], task_rows: list[dict[str, Any]], modes: list[dict[str, Any]]) -> None:
    lines = [
        "# Tier 5.17b Pre-Reward Representation Failure Analysis",
        "",
        f"- Generated: `{result['generated_at_utc']}`",
        f"- Status: **{result['status'].upper()}**",
        f"- Source Tier 5.17 bundle: `{result['summary']['source_bundle']}`",
        f"- Classification: `{result['summary']['decision']['classification']}`",
        f"- Next step: `{result['summary']['decision']['next_step']}`",
        "",
        "Tier 5.17b diagnoses why Tier 5.17 failed. It does not add a new mechanism and does not promote pre-reward representation learning.",
        "",
        "## Boundary",
        "",
        "- Diagnostic analysis only; no new baseline freeze.",
        "- Does not claim reward-free representation learning, unsupervised concept learning, or hardware/on-chip representation formation.",
        "- Does not send us back to Tier 5.9 unless future evidence shows useful pre-reward structure exists but downstream credit/preservation fails.",
        "",
        "## Task Diagnostics",
        "",
        "| Task | Mode | Candidate | Best control | Edge vs best | Edge vs random | Temporal order matters | Sample efficiency ok | Repair |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- | --- | --- |",
    ]
    for row in task_rows:
        lines.append(
            "| {task} | `{failure_mode}` | {candidate_ridge_accuracy} | {best_non_oracle_accuracy} | {edge_vs_best_non_oracle} | {edge_vs_random} | {temporal_order_matters} | {sample_efficiency_ok} | {repair_recommendation} |".format(
                **{k: markdown_value(v) for k, v in row.items()}
            )
        )
    lines.extend(["", "## Failure Modes", "", "| Mode | Tasks | Interpretation | Repair |", "| --- | --- | --- | --- |"])
    for mode in modes:
        lines.append(
            "| `{failure_mode}` | {tasks} | {description} | {repair_recommendation} |".format(
                **{k: markdown_value(v) for k, v in mode.items()}
            )
        )
    lines.extend(
        [
            "",
            "## Decision",
            "",
            f"- promote_pre_reward_representation: `{result['summary']['decision']['promote_pre_reward_representation']}`",
            f"- revisit_tier5_9_now: `{result['summary']['decision']['revisit_tier5_9_now']}`",
            f"- rationale: {result['summary']['decision']['rationale']}",
            f"- Tier 5.9 revisit rule: {result['summary']['decision']['tier5_9_revisit_rule']}",
            "",
            "## Criteria",
            "",
            "| Criterion | Value | Rule | Pass |",
            "| --- | --- | --- | --- |",
        ]
    )
    for item in result["criteria"]:
        lines.append(
            f"| {item['name']} | {markdown_value(item.get('value'))} | {item.get('operator')} {markdown_value(item.get('threshold'))} | {'yes' if item.get('passed') else 'no'} |"
        )
    if result.get("failure_reason"):
        lines.extend(["", f"Failure: {result['failure_reason']}"])
    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            "- `tier5_17b_results.json`: machine-readable manifest.",
            "- `tier5_17b_report.md`: human-readable classification.",
            "- `tier5_17b_task_diagnostics.csv`: per-task failure analysis.",
            "- `tier5_17b_failure_modes.csv`: mode-level repair map.",
            "- `tier5_17b_repair_plan.json`: next-step decision and Tier 5.9 revisit rule.",
            "- `tier5_17b_failure_modes.png`: candidate/control diagnostic plot.",
            "",
            "![tier5_17b_failure_modes](tier5_17b_failure_modes.png)",
        ]
    )
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_latest(output_dir: Path, manifest_json: Path, report_md: Path, status: str) -> None:
    write_json(
        ROOT / "controlled_test_output" / "tier5_17b_latest_manifest.json",
        {
            "tier": TIER,
            "status": status,
            "canonical": False,
            "output_dir": str(output_dir),
            "manifest_json": str(manifest_json),
            "report_md": str(report_md),
            "updated_at_utc": utc_now(),
        },
    )


def run(args: argparse.Namespace) -> dict[str, Any]:
    started = time.perf_counter()
    bundle_dir = Path(args.source_dir) if args.source_dir else latest_tier5_17_dir()
    data = load_bundle(bundle_dir)
    manifest = data["manifest"]
    comparisons = data["comparisons"]
    summary_rows = data["summary"]
    runs = data["runs"]
    summary_lookup = task_summary_rows(summary_rows)
    task_rows = [classify_task(row, summary_lookup, args) for row in comparisons]
    modes = summarize_failure_modes(task_rows)
    decision = choose_overall_decision(task_rows)
    leak = leakage_summary(runs)

    output_dir = Path(args.output_dir) if args.output_dir else ROOT / "controlled_test_output" / f"tier5_17b_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    output_dir.mkdir(parents=True, exist_ok=True)
    task_csv = output_dir / "tier5_17b_task_diagnostics.csv"
    modes_csv = output_dir / "tier5_17b_failure_modes.csv"
    repair_json = output_dir / "tier5_17b_repair_plan.json"
    plot_png = output_dir / "tier5_17b_failure_modes.png"
    manifest_json = output_dir / "tier5_17b_results.json"
    report_md = output_dir / "tier5_17b_report.md"

    write_csv(task_csv, task_rows)
    write_csv(modes_csv, modes)
    write_json(repair_json, decision)
    plot_failure_modes(plot_png, task_rows)

    expected_tasks = int(args.expected_tasks)
    criteria = [
        criterion("source Tier 5.17 bundle was found", str(bundle_dir), "exists", True, bundle_dir.exists()),
        criterion("source Tier 5.17 completed expected matrix", manifest.get("summary", {}).get("observed_runs"), "==", manifest.get("summary", {}).get("expected_runs"), manifest.get("summary", {}).get("observed_runs") == manifest.get("summary", {}).get("expected_runs")),
        criterion("non-oracle source had no label leakage", leak["label_leakage_runs"], "==", 0, leak["label_leakage_runs"] == 0),
        criterion("source had no reward visibility", leak["reward_leakage_runs"], "==", 0, leak["reward_leakage_runs"] == 0),
        criterion("source raw dopamine stayed zero", leak["max_abs_raw_dopamine_non_oracle"], "<=", args.max_abs_raw_dopamine, leak["max_abs_raw_dopamine_non_oracle"] <= float(args.max_abs_raw_dopamine)),
        criterion("all expected tasks classified", len(task_rows), "==", expected_tasks, len(task_rows) == expected_tasks),
        criterion("at least one concrete failure mode assigned", len(modes), ">=", 1, len(modes) >= 1),
        criterion("repair plan does not promote representation", decision["promote_pre_reward_representation"], "==", False, decision["promote_pre_reward_representation"] is False),
        criterion("repair plan does not jump to Tier 5.9", decision["revisit_tier5_9_now"], "==", False, decision["revisit_tier5_9_now"] is False),
    ]
    status, failure_reason = pass_fail(criteria)
    result = {
        "name": TIER,
        "status": status,
        "generated_at_utc": utc_now(),
        "output_dir": str(output_dir),
        "failure_reason": failure_reason,
        "summary": {
            "source_bundle": str(bundle_dir),
            "source_status": manifest.get("status"),
            "leakage_summary": leak,
            "task_count": len(task_rows),
            "failure_mode_count": len(modes),
            "decision": decision,
            "runtime_seconds": time.perf_counter() - started,
            "claim_boundary": "Noncanonical diagnostic classification only; not a pre-reward representation-learning promotion, not hardware evidence, and not a v2.0 freeze.",
        },
        "criteria": criteria,
        "artifacts": {
            "manifest_json": str(manifest_json),
            "report_md": str(report_md),
            "task_diagnostics_csv": str(task_csv),
            "failure_modes_csv": str(modes_csv),
            "repair_plan_json": str(repair_json),
            "failure_modes_png": str(plot_png),
        },
        "canonical": False,
    }
    write_json(manifest_json, result)
    write_report(report_md, result, task_rows, modes)
    if not bool(args.smoke):
        write_latest(output_dir, manifest_json, report_md, status)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=None, help="Tier 5.17 output directory. Defaults to tier5_17_latest_manifest.json.")
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--stop-on-fail", action="store_true")
    parser.add_argument("--expected-tasks", type=int, default=3)
    parser.add_argument("--min-structure-probe-accuracy", type=float, default=0.58)
    parser.add_argument("--min-edge-vs-random-for-structure", type=float, default=0.20)
    parser.add_argument("--min-temporal-edge", type=float, default=0.05)
    parser.add_argument("--max-edge-for-control-explains", type=float, default=0.05)
    parser.add_argument("--control-solves-accuracy", type=float, default=0.90)
    parser.add_argument("--max-sample-efficiency-ratio", type=float, default=1.25)
    parser.add_argument("--max-abs-raw-dopamine", type=float, default=1e-12)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = run(args)
    print(json.dumps(json_safe({"status": result["status"], "summary": result["summary"], "output_dir": result["output_dir"]}), indent=2, sort_keys=True))
    if args.stop_on_fail and result["status"] != "pass":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
