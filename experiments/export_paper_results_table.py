#!/usr/bin/env python3
"""Export paper-facing CRA evidence tables from the canonical registry."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "controlled_test_output" / "STUDY_REGISTRY.json"
DOC_PATH = ROOT / "docs" / "PAPER_RESULTS_TABLE.md"
CSV_PATH = ROOT / "controlled_test_output" / "PAPER_RESULTS_TABLE.csv"

PREFERRED_METRICS = [
    "all_accuracy",
    "all_accuracy_mean",
    "strict_accuracy_all_nonzero_targets",
    "strict_accuracy_tail_nonzero_targets",
    "tail_accuracy",
    "tail_accuracy_mean",
    "final_accuracy_ema",
    "prediction_target_corr_mean",
    "prediction_target_corr",
    "tail_prediction_target_corr_mean",
    "tail_prediction_target_corr",
    "accuracy_improvement",
    "capital_delta",
    "final_capital",
    "max_abs_dopamine",
    "delta_tail_accuracy_mean",
    "best_vs_small_all_accuracy_delta",
    "large_vs_small_all_accuracy_delta",
    "population_sizes",
    "seeds",
    "synthetic_fallbacks_sum",
    "sim_run_failures_sum",
    "summary_read_failures_sum",
    "total_step_spikes_mean",
    "runtime_seconds_mean",
    "runtime_seconds",
    "simulated_biological_seconds",
    "wall_to_simulated_ratio",
    "dominant_category",
    "dominant_category_seconds",
    "application_runner_seconds_per_step",
    "buffer_extractor_seconds_per_step",
    "expected_runs",
    "observed_runs",
    "expected_cells",
    "observed_cells",
    "expected_comparison_rows",
    "observed_comparison_rows",
    "best_fixed_external_tail_accuracy",
    "robust_advantage_regime_count",
    "not_dominated_hard_regime_count",
    "actual_runs",
    "expected_actual_runs",
    "intact_non_handoff_lifecycle_events_sum",
    "fixed_non_handoff_lifecycle_events_sum",
    "actual_lineage_integrity_failures",
    "performance_control_win_count",
    "fixed_max_win_count",
    "random_event_replay_win_count",
    "lineage_shuffle_detected_count",
    "intact_motif_diverse_aggregate_count",
    "expected_intact_aggregates",
    "intact_motif_activity_steps_sum",
    "motif_loss_count",
    "motif_ablation_loss_count",
    "random_or_monolithic_domination_count",
    "motif_shuffled_row_count",
    "no_wta_row_count",
    "lifecycle_births_sum",
    "lifecycle_deaths_sum",
    "lineage_integrity_failures",
    "advantage_regime_count",
    "advantage_tasks",
    "max_tail_delta_vs_paired_fixed",
    "max_abs_corr_delta_vs_paired_fixed",
    "max_recovery_improvement_steps_vs_paired_fixed",
    "outcome",
    "best_model",
    "cra_rank",
    "cra_geomean_mse_mean",
    "best_non_cra_model",
    "best_non_cra_geomean_mse_mean",
    "cra_vs_best_non_cra_mse_ratio",
    "failure_class",
    "raw_cra_geomean_mse",
    "state_probe_geomean_mse",
    "state_plus_lag_geomean_mse",
    "shuffled_control_geomean_mse",
    "state_improvement_over_raw",
    "state_plus_lag_improvement_over_raw",
    "state_vs_shuffled_control_advantage",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: str | None) -> str:
    if not path:
        return ""
    p = Path(path)
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return str(p)


def markdown_escape(value: Any) -> str:
    text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\n", " ")


def compact(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.6g}"
    return "" if value is None else str(value)


def collect_metrics(entry: dict[str, Any]) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    for result in entry.get("test_results") or []:
        for key, value in (result.get("metrics") or {}).items():
            metrics.setdefault(key, value)
    for key, value in (entry.get("top_level_metrics") or {}).items():
        metrics.setdefault(key, value)
    return metrics


def metric_summary(metrics: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in PREFERRED_METRICS:
        if key in metrics and metrics[key] not in (None, ""):
            parts.append(f"{key}={compact(metrics[key])}")
    return "; ".join(parts)


def read_summary_rows(path: str | None) -> list[dict[str, str]]:
    if not path:
        return []
    p = Path(path)
    if not p.exists():
        return []
    with p.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def first_value(row: dict[str, str], keys: list[str]) -> str:
    for key in keys:
        value = row.get(key, "")
        if value not in ("", None):
            return value
    return ""


def summary_highlights(entry: dict[str, Any]) -> str:
    if entry.get("entry_id") == "tier6_1_lifecycle_self_scaling":
        run_dir = Path(entry["canonical_output_dir"])
        event_analysis_path = run_dir / "tier6_1_event_analysis.json"
        comparisons_path = run_dir / "tier6_1_comparisons.csv"
        parts: list[str] = []
        if event_analysis_path.exists():
            event_analysis = json.loads(event_analysis_path.read_text(encoding="utf-8"))
            parts.append(f"new_polyp_events={compact(event_analysis.get('new_polyp_events_total'))}")
            parts.append(f"cleavage={compact(event_analysis.get('cleavage_events'))}")
            parts.append(f"adult_birth={compact(event_analysis.get('adult_birth_events'))}")
            parts.append(f"deaths={compact(event_analysis.get('death_events'))}")
        rows = read_summary_rows(str(comparisons_path))
        advantages = [row for row in rows if row.get("advantage_flag") == "True"]
        if advantages:
            tasks = sorted({row.get("task", "") for row in advantages if row.get("task")})
            parts.append(f"advantage_tasks={','.join(tasks)}")
            tail_deltas = [float(row["tail_delta"]) for row in advantages if row.get("tail_delta")]
            recovery = [
                float(row["recovery_improvement_steps"])
                for row in advantages
                if row.get("recovery_improvement_steps")
            ]
            if tail_deltas:
                parts.append(f"max_tail_delta={max(tail_deltas):.6g}")
            if recovery:
                parts.append(f"max_recovery_improvement={max(recovery):.6g}")
        if parts:
            return "; ".join(parts)

    if entry.get("entry_id") == "tier6_3_lifecycle_sham_controls":
        comparisons_path = Path(entry["canonical_output_dir"]) / "tier6_3_comparisons.csv"
        rows = read_summary_rows(str(comparisons_path))
        wins = [row for row in rows if row.get("performance_control") == "True" and row.get("advantage") == "True"]
        fixed_max_wins = [row for row in wins if row.get("control_type") == "fixed_max"]
        replay_wins = [row for row in wins if row.get("control_type") == "random_event_replay"]
        lineage_shuffle_rows = [row for row in rows if row.get("control_type") == "lineage_id_shuffle"]
        detected = sum(int(float(row.get("control_lineage_integrity_failures") or 0)) for row in lineage_shuffle_rows)
        if rows:
            return (
                f"performance_sham_wins={len(wins)}/10; "
                f"fixed_max_wins={len(fixed_max_wins)}/2; "
                f"event_replay_wins={len(replay_wins)}/2; "
                f"lineage_shuffle_detections={detected}/6"
            )

    if entry.get("entry_id") == "tier6_4_circuit_motif_causality":
        comparisons_path = Path(entry["canonical_output_dir"]) / "tier6_4_comparisons.csv"
        rows = read_summary_rows(str(comparisons_path))
        motif_rows = [row for row in rows if row.get("case_group") == "motif_ablation"]
        motif_losses = [row for row in motif_rows if row.get("motif_loss") == "True"]
        label_rows = [row for row in rows if row.get("variant_type") == "motif_shuffled"]
        label_losses = [row for row in label_rows if row.get("motif_loss") == "True"]
        domination = [row for row in rows if row.get("control_dominates_intact") == "True"]
        random_monolithic = [
            row for row in rows
            if row.get("variant_type") in {"random_graph_same_edge_count", "monolithic_same_capacity"}
        ]
        summary = entry.get("top_level_metrics") or {}
        parts: list[str] = [
            f"motif_ablation_losses={len(motif_losses)}/{len(motif_rows)}",
            f"label_shuffle_losses={len(label_losses)}/{len(label_rows)}",
            f"random_or_monolithic_dominations={len(domination)}/{len(random_monolithic)}",
        ]
        if summary.get("intact_motif_activity_steps_sum") not in (None, ""):
            parts.append(f"motif_active_steps={compact(summary.get('intact_motif_activity_steps_sum'))}")
        if summary.get("intact_motif_diverse_aggregate_count") not in (None, ""):
            parts.append(
                "motif_diverse_intact="
                f"{compact(summary.get('intact_motif_diverse_aggregate_count'))}/"
                f"{compact(summary.get('expected_intact_aggregates'))}"
            )
        return "; ".join(parts)

    if entry.get("entry_id") == "tier5_5_expanded_baselines":
        comparisons_path = Path(entry["canonical_output_dir"]) / "tier5_5_comparisons.csv"
        rows = read_summary_rows(str(comparisons_path))
        parts: list[str] = []
        hard_1500 = [
            row for row in rows
            if row.get("task") == "hard_noisy_switching"
            and row.get("run_length_steps") == "1500"
        ]
        delayed_1500 = [
            row for row in rows
            if row.get("task") == "delayed_cue"
            and row.get("run_length_steps") == "1500"
        ]
        robust = sum(1 for row in rows if row.get("robust_advantage_regime") == "True")
        not_dominated = sum(
            1
            for row in rows
            if row.get("task") in {"delayed_cue", "hard_noisy_switching", "sensor_control"}
            and row.get("not_dominated_by_best_external") == "True"
        )
        if robust:
            parts.append(f"robust_advantage_regimes={robust}")
        if not_dominated:
            parts.append(f"not_dominated_hard_regimes={not_dominated}")
        if hard_1500:
            row = hard_1500[0]
            parts.append(f"hard1500_cra_tail={compact(row.get('cra_tail_accuracy_mean'))}")
            parts.append(f"hard1500_ext_median={compact(row.get('external_median_tail_accuracy'))}")
            parts.append(f"hard1500_best={compact(row.get('best_external_tail_accuracy_mean'))}")
            parts.append(f"hard1500_best_model={row.get('best_external_tail_model')}")
        if delayed_1500:
            row = delayed_1500[0]
            parts.append(f"delayed1500_cra_tail={compact(row.get('cra_tail_accuracy_mean'))}")
            parts.append(f"delayed1500_best={compact(row.get('best_external_tail_accuracy_mean'))}")
        if parts:
            return "; ".join(parts)

    if entry.get("entry_id") == "tier5_4_delayed_credit_confirmation":
        confirmation_path = Path(entry["canonical_output_dir"]) / "tier5_4_confirmation.csv"
        rows = read_summary_rows(str(confirmation_path))
        delayed = [
            row for row in rows if row.get("task") == "delayed_cue"
        ]
        hard = [
            row for row in rows if row.get("task") == "hard_noisy_switching"
        ]
        parts: list[str] = []
        if delayed:
            tails = [float(row["candidate_cra_tail_accuracy_mean"]) for row in delayed]
            deltas = [float(row["candidate_tail_delta_vs_current"]) for row in delayed]
            parts.append(f"delayed_cue_candidate_tail_min={min(tails):.6g}")
            parts.append(f"delayed_cue_delta_vs_current_min={min(deltas):.6g}")
        if hard:
            tails = [float(row["candidate_cra_tail_accuracy_mean"]) for row in hard]
            current = [float(row["candidate_tail_delta_vs_current"]) for row in hard]
            median = [float(row["candidate_tail_delta_vs_external_median"]) for row in hard]
            best = [float(row["candidate_tail_delta_vs_best_external"]) for row in hard]
            parts.append(f"hard_switch_candidate_tail_min={min(tails):.6g}")
            parts.append(f"hard_switch_delta_vs_current_min={min(current):.6g}")
            parts.append(f"hard_switch_delta_vs_median_min={min(median):.6g}")
            parts.append(f"hard_switch_delta_vs_best_min={min(best):.6g}")
        if parts:
            return "; ".join(parts)

    rows = read_summary_rows(entry.get("summary_csv"))
    if not rows:
        return ""
    header = set(rows[0].keys())
    parts: list[str] = []

    if "case" in header:
        for row in rows:
            case = row.get("case", "")
            if not case:
                continue
            vals = []
            for label, key in [
                ("acc", "all_accuracy_mean"),
                ("tail", "tail_accuracy_mean"),
                ("corr", "prediction_target_corr_mean"),
                ("bridge", "trading_bridge_present_any_run"),
            ]:
                value = row.get(key, "")
                if value:
                    vals.append(f"{label}={compact(value)}")
            if vals:
                parts.append(f"{case}({', '.join(vals)})")
        return "; ".join(parts[:6])

    if "tier_part" in header and "task" in header:
        task = first_value(rows[0], ["task"])
        seeds = [row.get("seed", "") for row in rows if row.get("seed")]
        vals = []
        for label, key in [
            ("acc_mean", "all_accuracy"),
            ("tail_mean", "tail_accuracy"),
            ("tail_corr_mean", "tail_prediction_target_corr"),
            ("spikes_min", "total_step_spikes"),
            ("runtime_mean", "runtime_seconds"),
        ]:
            numeric = [float(row[key]) for row in rows if row.get(key)]
            if not numeric:
                continue
            if label.endswith("_min"):
                vals.append(f"{label}={min(numeric):.6g}")
            else:
                vals.append(f"{label}={sum(numeric) / len(numeric):.6g}")
        if task:
            parts.append(f"task={task}")
        if seeds:
            parts.append(f"seeds={','.join(seeds)}")
        parts.extend(vals)
        if parts:
            return "; ".join(parts)

    if "population_size" in header:
        sizes = [row.get("population_size", "") for row in rows if row.get("population_size")]
        acc = [float(row["all_accuracy_mean"]) for row in rows if row.get("all_accuracy_mean")]
        corr = [
            float(row["tail_prediction_target_corr_mean"])
            for row in rows
            if row.get("tail_prediction_target_corr_mean")
        ]
        recovery = [
            float(row["mean_recovery_steps_mean"])
            for row in rows
            if row.get("mean_recovery_steps_mean")
        ]
        if sizes:
            parts.append(f"sizes={','.join(sizes)}")
        if acc:
            parts.append(f"acc_range={min(acc):.6g}..{max(acc):.6g}")
        if corr:
            parts.append(f"tail_corr_range={min(corr):.6g}..{max(corr):.6g}")
        if recovery:
            parts.append(f"recovery_range={min(recovery):.6g}..{max(recovery):.6g}")
        return "; ".join(parts)

    if "backend_key" in header:
        for row in rows:
            backend = row.get("backend_key") or row.get("test_name", "")
            if not backend:
                continue
            vals = []
            for label, key in [
                ("acc", "all_accuracy_mean"),
                ("tail", "tail_accuracy_mean"),
                ("corr", "tail_prediction_target_corr_mean"),
                ("fallback", "synthetic_fallbacks_sum"),
                ("delta", "all_accuracy_delta"),
            ]:
                value = row.get(key, "")
                if value:
                    vals.append(f"{label}={compact(value)}")
            if vals:
                parts.append(f"{backend}({', '.join(vals)})")
        return "; ".join(parts[:4])

    return ""


def selected_tests(entry: dict[str, Any]) -> str:
    selected = entry.get("selected_tests")
    if selected:
        return ", ".join(str(v) for v in selected)
    tests = entry.get("test_results") or []
    if len(tests) == 1:
        return str(tests[0].get("name", ""))
    return ", ".join(str(t.get("name", "")) for t in tests if t.get("name"))


def build_rows(registry: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for entry in registry.get("entries", []):
        metrics = collect_metrics(entry)
        key_metrics = metric_summary(metrics)
        highlights = summary_highlights(entry)
        if highlights:
            key_metrics = f"{key_metrics}; {highlights}" if key_metrics else highlights
        rows.append(
            {
                "entry_id": entry.get("entry_id", ""),
                "tier": entry.get("tier_label", ""),
                "status": str(entry.get("status", "")).upper(),
                "role": entry.get("evidence_role", ""),
                "backend": entry.get("backend") or "see manifest",
                "tests_or_scope": selected_tests(entry),
                "key_metrics": key_metrics,
                "claim": entry.get("claim", ""),
                "boundary": entry.get("caveat", ""),
                "results": rel(entry.get("results_json")),
                "report": rel(entry.get("report_md")),
                "summary_csv": rel(entry.get("summary_csv")),
            }
        )
    return rows


def write_csv_table(rows: list[dict[str, str]]) -> None:
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(registry: dict[str, Any], rows: list[dict[str, str]]) -> None:
    lines = [
        "# CRA Paper Results Table",
        "",
        "This table is generated from `controlled_test_output/STUDY_REGISTRY.json`.",
        "It is intended as a paper/technical-note citation table, not as a new",
        "source of claims. If the registry changes, regenerate this file.",
        "",
        f"- Generated: `{utc_now()}`",
        f"- Registry generated: `{registry.get('generated_at_utc')}`",
        f"- Registry status: **{str(registry.get('registry_status', '')).upper()}**",
        f"- Canonical bundles: `{registry.get('evidence_count')}`",
        f"- Expanded entries: `{registry.get('expanded_test_entry_count')}`",
        "",
        "## Summary Table",
        "",
        "| Entry | Status | Backend | Scope | Key Metrics | Claim Boundary | Artifacts |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        artifacts = (
            f"results: `{row['results']}`; report: `{row['report']}`; "
            f"summary: `{row['summary_csv']}`"
        )
        lines.append(
            "| "
            f"`{markdown_escape(row['entry_id'])}` | "
            f"{markdown_escape(row['status'])} | "
            f"{markdown_escape(row['backend'])} | "
            f"{markdown_escape(row['tests_or_scope'])} | "
            f"{markdown_escape(row['key_metrics'])} | "
            f"{markdown_escape(row['boundary'])} | "
            f"{markdown_escape(artifacts)} |"
        )
    lines.extend(
        [
            "",
            "## Claim Discipline",
            "",
            "- Tier 4.13 is a single-seed N=8 fixed-pattern hardware capsule pass.",
            "- Tier 4.14 characterizes runtime/provenance overhead from that pass.",
            "- Tier 4.15 repeats the same minimal hardware capsule across three seeds.",
            "- Tier 4.16a transfers the repaired delayed-cue capsule to real SpiNNaker across three seeds; it is not hard-switching transfer, hardware scaling, on-chip learning, or full Tier 4.16.",
            "- Tier 4.16b transfers the repaired hard-switch capsule to real SpiNNaker across three seeds; it remains close to threshold and is not hardware scaling, on-chip learning, or external-baseline superiority.",
            "- Tier 4.18a characterizes the v0.7 chunked-host hardware bridge and recommends chunk 50; it is runtime/resource evidence, not a new learning or scaling claim.",
            "- Tier 5.4 is software confirmation of `delayed_lr_0_20`; it is not a hardware result.",
            "- Hard noisy switching still trails the best external baseline, so Tier 5.4 is not a superiority claim.",
            "- Tier 6.1 is software lifecycle/self-scaling evidence with clean lineage tracking and hard-switch advantage regimes; it is not full adult turnover, sham-control proof, hardware lifecycle, or external-baseline superiority.",
            "- Tier 6.3 is software lifecycle sham-control evidence; replay/shuffle controls are audit artifacts, and it is not hardware lifecycle, full adult turnover, or external-baseline superiority.",
            "- Tier 6.4 is software circuit-motif causality evidence; the motif-diverse graph is seeded for this suite, motif-label shuffle is not causal by itself, and it is not hardware motif execution, custom-C/on-chip learning, compositionality, or world-model evidence.",
            "- `docs/REVIEWER_DEFENSE_PLAN.md` defines the fairness, statistics, leakage, mechanism, and reproducibility safeguards required before a strong paper claim.",
            "- Frozen baselines in `baselines/` are historical claim locks and should not be rewritten.",
            "",
        ]
    )
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOC_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    rows = build_rows(registry)
    if not rows:
        raise SystemExit("No registry entries found")
    write_csv_table(rows)
    write_markdown(registry, rows)
    print(json.dumps({"markdown": str(DOC_PATH), "csv": str(CSV_PATH), "rows": len(rows)}, indent=2))


if __name__ == "__main__":
    main()
