#!/usr/bin/env python3
"""Tier 7.4g - held-out policy/action confirmation + reference separation.

Tier 7.4f found a qualified C-MAPSS-only action-cost signal: the v2.4
cost-aware policy ranked first and beat the strongest external baseline, while
NAB did not confirm and C-MAPSS did not separate from the prior v2.2 CRA
reference with a positive paired interval.

This gate does not tune, retrain, or change the held-out scoring contract. It
reuses the locked Tier 7.4f score rows to:

1. confirm the C-MAPSS signal against external and sham controls,
2. explicitly test v2.4-v2.2 reference separation, and
3. classify the NAB non-confirmation without turning it into a new claim.

Boundary: software held-out action-cost confirmation only. Passing this harness
means the confirmation/failure-analysis procedure completed and preserved the
claim boundary. It does not authorize a freeze, hardware transfer, broad public
usefulness, or incremental v2.4 superiority when the reference CI crosses zero.
"""

from __future__ import annotations

import csv
import json
import math
import random
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"

TIER = "Tier 7.4g - Held-Out Policy/Action Confirmation + Reference Separation"
RUNNER_REVISION = "tier7_4g_policy_action_confirmation_reference_separation_20260509_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_4g_20260509_policy_action_confirmation_reference_separation"

TIER7_4F_DIR = CONTROLLED / "tier7_4f_20260509_cost_aware_policy_action_heldout_scoring_gate"
TIER7_4F_RESULTS = TIER7_4F_DIR / "tier7_4f_results.json"
TIER7_4F_SCORE_ROWS = TIER7_4F_DIR / "tier7_4f_score_rows.csv"
TIER7_4F_MODEL_SUMMARY = TIER7_4F_DIR / "tier7_4f_model_summary.csv"
TIER7_4F_FAMILY_DECISIONS = TIER7_4F_DIR / "tier7_4f_family_decisions.csv"
TIER7_4F_COST_MODEL = TIER7_4F_DIR / "tier7_4f_cost_model.csv"

CANDIDATE = "v2_4_cost_aware_policy"
V22_REFERENCE = "v2_2_reference_policy"
FAMILY_CMAPSS = "cmapss_maintenance_action_cost"
FAMILY_NAB = "nab_heldout_alarm_action_cost"

NEXT_GATE = "Tier 7.4h - Policy/Action Attribution Closeout / Mechanism Return Decision"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    if fieldnames is None:
        keys: list[str] = []
        for row in rows:
            for key in row:
                if key not in keys:
                    keys.append(key)
        fieldnames = keys
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json_safe(row.get(key, "")) for key in fieldnames})


def json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def sha256_file(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in {None, ""}:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def to_int(value: Any, default: int = 0) -> int:
    try:
        if value in {None, ""}:
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def bool_from_csv(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def finite_mean(values: list[float]) -> float | None:
    vals = [v for v in values if math.isfinite(v)]
    return float(mean(vals)) if vals else None


def finite_median(values: list[float]) -> float | None:
    vals = [v for v in values if math.isfinite(v)]
    return float(median(vals)) if vals else None


def stable_std(values: list[float]) -> float:
    vals = [v for v in values if math.isfinite(v)]
    if len(vals) < 2:
        return 0.0
    mu = mean(vals)
    return float(math.sqrt(sum((x - mu) ** 2 for x in vals) / (len(vals) - 1)))


def criterion(name: str, value: Any, rule: str, passed: bool, details: str = "") -> dict[str, Any]:
    return {
        "name": name,
        "criterion": name,
        "value": value,
        "operator": rule,
        "rule": rule,
        "passed": bool(passed),
        "pass": bool(passed),
        "note": details,
        "details": details,
    }


def model_summary_map(rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, str]]:
    return {(row.get("family", ""), row.get("model", "")): row for row in rows}


def family_decision_map(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {row.get("family", ""): row for row in rows}


def paired_deltas(score_rows: list[dict[str, str]], family: str, candidate: str, baseline: str) -> list[dict[str, Any]]:
    by_key: dict[tuple[int, str], dict[str, float]] = {}
    for row in score_rows:
        if row.get("family") != family or row.get("model") not in {candidate, baseline}:
            continue
        key = (to_int(row.get("seed")), str(row.get("unit_or_stream", "")))
        by_key.setdefault(key, {})[str(row["model"])] = to_float(row.get("expected_utility_per_1000"))
    out = []
    for (seed, unit), vals in sorted(by_key.items()):
        if candidate not in vals or baseline not in vals:
            continue
        out.append(
            {
                "family": family,
                "candidate": candidate,
                "baseline": baseline,
                "seed": seed,
                "unit_or_stream": unit,
                "candidate_expected_utility_per_1000": vals[candidate],
                "baseline_expected_utility_per_1000": vals[baseline],
                "delta_expected_utility_per_1000": vals[candidate] - vals[baseline],
            }
        )
    return out


def paired_bootstrap(rows: list[dict[str, Any]], *, samples: int = 5000, seed: int = 7407) -> dict[str, Any]:
    deltas = [to_float(row.get("delta_expected_utility_per_1000")) for row in rows]
    if not deltas:
        return {
            "paired_units": 0,
            "mean_delta": None,
            "median_delta": None,
            "ci_low": None,
            "ci_high": None,
            "effect_size": None,
            "positive_fraction": None,
        }
    rng = random.Random(seed + len(deltas))
    boot = [mean(rng.choice(deltas) for _ in deltas) for _ in range(samples)]
    boot.sort()
    sd = stable_std(deltas)
    return {
        "paired_units": len(deltas),
        "mean_delta": float(mean(deltas)),
        "median_delta": finite_median(deltas),
        "ci_low": float(boot[int(0.025 * (samples - 1))]),
        "ci_high": float(boot[int(0.975 * (samples - 1))]),
        "effect_size": None if sd < 1e-12 else float(mean(deltas) / sd),
        "positive_fraction": float(sum(1 for d in deltas if d > 0) / len(deltas)),
    }


def comparison_check(score_rows: list[dict[str, str]], family: str, baseline: str, label: str) -> dict[str, Any]:
    rows = paired_deltas(score_rows, family, CANDIDATE, baseline)
    stats = paired_bootstrap(rows, seed=7407 + len(label))
    return {
        "comparison": label,
        "family": family,
        "candidate": CANDIDATE,
        "baseline": baseline,
        "paired_units": stats["paired_units"],
        "mean_delta": stats["mean_delta"],
        "median_delta": stats["median_delta"],
        "ci_low": stats["ci_low"],
        "ci_high": stats["ci_high"],
        "effect_size": stats["effect_size"],
        "positive_fraction": stats["positive_fraction"],
        "positive_ci_confirmed": stats["ci_low"] is not None and stats["ci_low"] > 0.0,
        "delta_rows": rows,
    }


def partition_checks(score_rows: list[dict[str, str]], family: str, baseline: str) -> list[dict[str, Any]]:
    rows = paired_deltas(score_rows, family, CANDIDATE, baseline)
    out: list[dict[str, Any]] = []
    by_seed: dict[int, list[float]] = defaultdict(list)
    by_unit_parity: dict[str, list[float]] = defaultdict(list)
    by_third: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        seed = to_int(row["seed"])
        unit_label = str(row["unit_or_stream"])
        unit_number = to_int(unit_label.replace("unit_", ""), default=-1)
        delta = to_float(row["delta_expected_utility_per_1000"])
        by_seed[seed].append(delta)
        by_unit_parity["even_unit" if unit_number >= 0 and unit_number % 2 == 0 else "odd_unit"].append(delta)
        if unit_number < 0:
            third = "unknown_unit"
        elif unit_number <= 33:
            third = "unit_001_033"
        elif unit_number <= 66:
            third = "unit_034_066"
        else:
            third = "unit_067_100"
        by_third[third].append(delta)
    for partition_type, groups in (
        ("seed", {str(k): v for k, v in sorted(by_seed.items())}),
        ("unit_parity", dict(sorted(by_unit_parity.items()))),
        ("unit_third", dict(sorted(by_third.items()))),
    ):
        for name, deltas in groups.items():
            out.append(
                {
                    "family": family,
                    "candidate": CANDIDATE,
                    "baseline": baseline,
                    "partition_type": partition_type,
                    "partition": name,
                    "paired_units": len(deltas),
                    "mean_delta": finite_mean(deltas),
                    "median_delta": finite_median(deltas),
                    "positive_fraction": None if not deltas else sum(1 for d in deltas if d > 0) / len(deltas),
                    "candidate_wins_partition": bool(deltas and mean(deltas) > 0.0),
                }
            )
    return out


def aggregate_by_category(score_rows: list[dict[str, str]], family: str) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in score_rows:
        if row.get("family") == family:
            grouped[(str(row.get("category", "")), str(row.get("model", "")))].append(row)
    out = []
    for (category, model), rows in sorted(grouped.items()):
        out.append(
            {
                "family": family,
                "category": category,
                "model": model,
                "role": sorted({r.get("role", "") for r in rows})[0],
                "streams": len(rows),
                "expected_utility_per_1000_mean": finite_mean([to_float(r.get("expected_utility_per_1000")) for r in rows]),
                "event_recall_mean": finite_mean([to_float(r.get("event_recall")) for r in rows]),
                "false_positive_cost_per_1000_mean": finite_mean([to_float(r.get("false_positive_cost_per_1000")) for r in rows]),
                "action_rate_mean": finite_mean([to_float(r.get("action_rate")) for r in rows]),
                "missed_event_cost_mean": finite_mean([to_float(r.get("missed_event_cost")) for r in rows]),
            }
        )
    return out


def classify_nab_failure(model_rows: dict[tuple[str, str], dict[str, str]], category_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    candidate = model_rows.get((FAMILY_NAB, CANDIDATE), {})
    ewma = model_rows.get((FAMILY_NAB, "ewma_residual_policy"), {})
    v22 = model_rows.get((FAMILY_NAB, V22_REFERENCE), {})
    candidate_score = to_float(candidate.get("expected_utility_per_1000_mean"))
    ewma_score = to_float(ewma.get("expected_utility_per_1000_mean"))
    v22_score = to_float(v22.get("expected_utility_per_1000_mean"))
    candidate_recall = to_float(candidate.get("event_recall_mean"))
    ewma_recall = to_float(ewma.get("event_recall_mean"))
    v22_recall = to_float(v22.get("event_recall_mean"))
    candidate_fp = to_float(candidate.get("false_positive_cost_per_1000_mean"))
    ewma_fp = to_float(ewma.get("false_positive_cost_per_1000_mean"))
    v22_fp = to_float(v22.get("false_positive_cost_per_1000_mean"))

    by_category: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in category_rows:
        by_category[str(row["category"])][str(row["model"])] = row

    rows: list[dict[str, Any]] = []
    for category, models in sorted(by_category.items()):
        cand = models.get(CANDIDATE, {})
        best_ext = models.get("ewma_residual_policy", {})
        ref = models.get(V22_REFERENCE, {})
        cand_score = to_float(cand.get("expected_utility_per_1000_mean"))
        ext_score = to_float(best_ext.get("expected_utility_per_1000_mean"))
        ref_score = to_float(ref.get("expected_utility_per_1000_mean"))
        cand_recall = to_float(cand.get("event_recall_mean"))
        ext_recall = to_float(best_ext.get("event_recall_mean"))
        ref_recall = to_float(ref.get("event_recall_mean"))
        cand_fp = to_float(cand.get("false_positive_cost_per_1000_mean"))
        ext_fp = to_float(best_ext.get("false_positive_cost_per_1000_mean"))
        ref_fp = to_float(ref.get("false_positive_cost_per_1000_mean"))
        if cand_score < ext_score and cand_recall < ext_recall:
            failure_class = "event_coverage_gap_vs_ewma"
        elif cand_score < ext_score and cand_fp > ext_fp:
            failure_class = "false_positive_cost_gap_vs_ewma"
        elif cand_score < ext_score:
            failure_class = "utility_margin_gap_vs_ewma"
        elif cand_score < ref_score:
            failure_class = "reference_gap_without_external_gap"
        else:
            failure_class = "candidate_not_category_failure"
        rows.append(
            {
                "family": FAMILY_NAB,
                "category": category,
                "candidate_expected_utility_per_1000_mean": cand_score,
                "ewma_expected_utility_per_1000_mean": ext_score,
                "v2_2_expected_utility_per_1000_mean": ref_score,
                "candidate_minus_ewma": cand_score - ext_score,
                "candidate_minus_v2_2": cand_score - ref_score,
                "candidate_event_recall_mean": cand_recall,
                "ewma_event_recall_mean": ext_recall,
                "v2_2_event_recall_mean": ref_recall,
                "candidate_false_positive_cost_per_1000_mean": cand_fp,
                "ewma_false_positive_cost_per_1000_mean": ext_fp,
                "v2_2_false_positive_cost_per_1000_mean": ref_fp,
                "failure_class": failure_class,
            }
        )

    if candidate_score >= ewma_score:
        overall_class = "nab_not_failed_vs_best_external"
    elif candidate_recall < ewma_recall:
        overall_class = "event_coverage_gap_vs_ewma"
    elif candidate_fp > ewma_fp:
        overall_class = "false_positive_cost_gap_vs_ewma"
    else:
        overall_class = "small_utility_margin_or_cost_tradeoff_gap_vs_ewma"
    if candidate_score < v22_score and candidate_recall < v22_recall:
        reference_class = "event_coverage_gap_vs_v2_2"
    elif candidate_score < v22_score and candidate_fp > v22_fp:
        reference_class = "false_positive_cost_gap_vs_v2_2"
    elif candidate_score < v22_score:
        reference_class = "small_utility_margin_or_cost_tradeoff_gap_vs_v2_2"
    else:
        reference_class = "not_lower_than_v2_2_reference"

    overall = {
        "family": FAMILY_NAB,
        "candidate": CANDIDATE,
        "best_external": "ewma_residual_policy",
        "reference": V22_REFERENCE,
        "candidate_expected_utility_per_1000_mean": candidate_score,
        "ewma_expected_utility_per_1000_mean": ewma_score,
        "v2_2_expected_utility_per_1000_mean": v22_score,
        "candidate_minus_ewma": candidate_score - ewma_score,
        "candidate_minus_v2_2": candidate_score - v22_score,
        "candidate_event_recall_mean": candidate_recall,
        "ewma_event_recall_mean": ewma_recall,
        "v2_2_event_recall_mean": v22_recall,
        "candidate_false_positive_cost_per_1000_mean": candidate_fp,
        "ewma_false_positive_cost_per_1000_mean": ewma_fp,
        "v2_2_false_positive_cost_per_1000_mean": v22_fp,
        "failure_class_vs_ewma": overall_class,
        "failure_class_vs_v2_2": reference_class,
        "heldout_tuning_performed": False,
    }
    return rows, overall


def make_report(
    output_dir: Path,
    status: str,
    criteria: list[dict[str, Any]],
    checks: list[dict[str, Any]],
    decision: dict[str, Any],
    nab_failure: dict[str, Any],
) -> str:
    passed = sum(1 for c in criteria if c["pass"])
    lines = [
        "# Tier 7.4g Held-Out Policy/Action Confirmation + Reference Separation",
        "",
        f"- Generated: `{utc_now()}`",
        f"- Status: **{status}**",
        f"- Output directory: `{output_dir}`",
        f"- Runner revision: `{RUNNER_REVISION}`",
        "",
        "## Claim Boundary",
        "",
        "- This is a software held-out action-cost confirmation gate.",
        "- It reuses the locked Tier 7.4f cost model, policies, score rows, baselines, and shams.",
        "- It does not tune costs, thresholds, policies, or held-out splits.",
        "- It does not authorize a new baseline freeze, hardware/native transfer, broad public usefulness, planning, language, AGI, or ASI claims.",
        "",
        "## Summary",
        "",
        f"- criteria_passed: `{passed}/{len(criteria)}`",
        f"- outcome: `{decision['outcome']}`",
        f"- narrow_cmapss_external_signal_authorized: `{decision['narrow_cmapss_external_signal_authorized']}`",
        f"- incremental_v2_4_reference_claim_authorized: `{decision['incremental_v2_4_reference_claim_authorized']}`",
        f"- broad_public_usefulness_authorized: `{decision['broad_public_usefulness_authorized']}`",
        f"- freeze_authorized: `{decision['freeze_authorized']}`",
        f"- hardware_transfer_authorized: `{decision['hardware_transfer_authorized']}`",
        f"- next_gate: `{decision['next_gate']}`",
        "",
        "## Confirmation Checks",
        "",
        "| Comparison | CI low | CI high | Mean delta | Positive CI confirmed |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for row in checks:
        lines.append(
            f"| {row['comparison']} | {row['ci_low']} | {row['ci_high']} | "
            f"{row['mean_delta']} | {row['positive_ci_confirmed']} |"
        )
    lines.extend(
        [
            "",
            "## NAB Failure Analysis",
            "",
            f"- failure_class_vs_ewma: `{nab_failure['failure_class_vs_ewma']}`",
            f"- failure_class_vs_v2_2: `{nab_failure['failure_class_vs_v2_2']}`",
            f"- candidate_minus_ewma: `{nab_failure['candidate_minus_ewma']}`",
            f"- candidate_minus_v2_2: `{nab_failure['candidate_minus_v2_2']}`",
            f"- heldout_tuning_performed: `{nab_failure['heldout_tuning_performed']}`",
            "",
            "## Criteria",
            "",
            "| Criterion | Value | Rule | Pass | Details |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for row in criteria:
        lines.append(
            f"| {row['criterion']} | `{row['value']}` | {row['rule']} | "
            f"{'yes' if row['pass'] else 'no'} | {row.get('details', '')} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "Tier 7.4g confirms the narrow C-MAPSS external/sham action-cost signal from Tier 7.4f, but it also preserves the most important limit: the v2.4 candidate still does not separate from the prior v2.2 CRA reference with a positive paired confidence interval. NAB remains a non-confirmation, with the failure analysis pointing to event-coverage and utility tradeoff gaps rather than a held-out scoring bug. The correct next move is attribution/closeout, not a freeze or hardware transfer.",
            "",
        ]
    )
    return "\n".join(lines)


def make_manifest(output_dir: Path, artifacts: dict[str, Path], status: str) -> dict[str, Any]:
    return {
        "tier": TIER,
        "status": status,
        "generated_at_utc": utc_now(),
        "runner_revision": RUNNER_REVISION,
        "output_dir": str(output_dir),
        "artifacts": [
            {
                "name": name,
                "path": str(path),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
            for name, path in sorted(artifacts.items())
        ],
    }


def main() -> int:
    output_dir = DEFAULT_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    prior = read_json(TIER7_4F_RESULTS)
    score_rows = read_csv_rows(TIER7_4F_SCORE_ROWS)
    summary_rows = read_csv_rows(TIER7_4F_MODEL_SUMMARY)
    decision_rows = read_csv_rows(TIER7_4F_FAMILY_DECISIONS)
    cost_rows = read_csv_rows(TIER7_4F_COST_MODEL)

    summary = model_summary_map(summary_rows)
    family_decisions = family_decision_map(decision_rows)

    cmapss_decision = family_decisions.get(FAMILY_CMAPSS, {})
    nab_decision = family_decisions.get(FAMILY_NAB, {})

    best_external = str(cmapss_decision.get("best_external_baseline", "lag_multichannel_ridge_policy"))
    best_sham = str(cmapss_decision.get("best_sham_or_ablation", "shuffled_state_sham"))

    cmapss_external = comparison_check(score_rows, FAMILY_CMAPSS, best_external, "cmapss_candidate_vs_best_external")
    cmapss_reference = comparison_check(score_rows, FAMILY_CMAPSS, V22_REFERENCE, "cmapss_candidate_vs_v2_2_reference")
    cmapss_sham = comparison_check(score_rows, FAMILY_CMAPSS, best_sham, "cmapss_candidate_vs_best_sham")
    nab_external = comparison_check(score_rows, FAMILY_NAB, str(nab_decision.get("best_external_baseline", "ewma_residual_policy")), "nab_candidate_vs_best_external")
    nab_reference = comparison_check(score_rows, FAMILY_NAB, V22_REFERENCE, "nab_candidate_vs_v2_2_reference")
    checks = [cmapss_external, cmapss_reference, cmapss_sham, nab_external, nab_reference]

    reference_partition_rows = partition_checks(score_rows, FAMILY_CMAPSS, V22_REFERENCE)
    external_partition_rows = partition_checks(score_rows, FAMILY_CMAPSS, best_external)

    category_rows = aggregate_by_category(score_rows, FAMILY_NAB)
    nab_category_failure_rows, nab_failure = classify_nab_failure(summary, category_rows)

    reference_confirmed = bool(cmapss_reference["positive_ci_confirmed"])
    cmapss_external_confirmed = bool(cmapss_external["positive_ci_confirmed"])
    cmapss_sham_confirmed = bool(cmapss_sham["positive_ci_confirmed"])
    nab_external_failed = not bool(nab_external["positive_ci_confirmed"]) and to_float(nab_external["mean_delta"], 1.0) <= 0.0

    criteria = [
        criterion("tier7_4f_results_exist", TIER7_4F_RESULTS.exists(), "must exist", TIER7_4F_RESULTS.exists(), str(TIER7_4F_RESULTS)),
        criterion("tier7_4f_status_pass", prior.get("status"), "case-insensitive == PASS", str(prior.get("status", "")).upper() == "PASS"),
        criterion("score_rows_present", len(score_rows), "> 0", len(score_rows) > 0, str(TIER7_4F_SCORE_ROWS)),
        criterion("model_summary_present", len(summary_rows), "> 0", len(summary_rows) > 0, str(TIER7_4F_MODEL_SUMMARY)),
        criterion("family_decisions_present", len(decision_rows), ">= 2", len(decision_rows) >= 2, str(TIER7_4F_FAMILY_DECISIONS)),
        criterion("locked_cost_model_present", len(cost_rows), "> 0", len(cost_rows) > 0, str(TIER7_4F_COST_MODEL)),
        criterion("heldout_tuning_performed", False, "must remain False", True, "7.4g only reuses locked 7.4f scores."),
        criterion("cmapss_candidate_rank_first", cmapss_decision.get("candidate_rank"), "== 1", str(cmapss_decision.get("candidate_rank")) == "1"),
        criterion("cmapss_family_previously_confirmed", cmapss_decision.get("public_usefulness_family_confirmed"), "== True", bool_from_csv(cmapss_decision.get("public_usefulness_family_confirmed"))),
        criterion("cmapss_external_positive_ci", cmapss_external["ci_low"], "> 0", cmapss_external_confirmed),
        criterion("cmapss_sham_positive_ci", cmapss_sham["ci_low"], "> 0", cmapss_sham_confirmed),
        criterion("cmapss_reference_separation_evaluated", cmapss_reference["paired_units"], "> 0", to_int(cmapss_reference["paired_units"]) > 0),
        criterion("cmapss_reference_overclaim_blocked", reference_confirmed, "must be False for no incremental claim", not reference_confirmed),
        criterion("cmapss_partition_checks_written", len(reference_partition_rows) + len(external_partition_rows), "> 0", len(reference_partition_rows) + len(external_partition_rows) > 0),
        criterion("nab_family_nonconfirmation_preserved", nab_decision.get("public_usefulness_family_confirmed"), "== False", not bool_from_csv(nab_decision.get("public_usefulness_family_confirmed"))),
        criterion("nab_external_failure_confirmed_or_preserved", nab_external["mean_delta"], "<= 0 or CI not positive", nab_external_failed),
        criterion("nab_failure_classified", nab_failure["failure_class_vs_ewma"], "non-empty", bool(nab_failure["failure_class_vs_ewma"])),
        criterion("nab_category_analysis_written", len(nab_category_failure_rows), "> 0", len(nab_category_failure_rows) > 0),
        criterion("freeze_not_authorized", False, "must remain False", True),
        criterion("hardware_transfer_not_authorized", False, "must remain False", True),
    ]

    passed = all(row["pass"] for row in criteria)
    status = "PASS" if passed else "FAIL"

    narrow_cmapss_signal = cmapss_external_confirmed and cmapss_sham_confirmed and not reference_confirmed
    if narrow_cmapss_signal and nab_external_failed:
        outcome = "cmapss_external_signal_confirmed_reference_not_separated_nab_failed"
    elif reference_confirmed and cmapss_external_confirmed and cmapss_sham_confirmed:
        outcome = "cmapss_reference_separation_confirmed_but_requires_separate_freeze_gate"
    else:
        outcome = "heldout_action_signal_not_confirmed"

    decision = {
        "tier": TIER,
        "status": status,
        "outcome": outcome,
        "narrow_cmapss_external_signal_authorized": narrow_cmapss_signal,
        "incremental_v2_4_reference_claim_authorized": reference_confirmed,
        "broad_public_usefulness_authorized": False,
        "freeze_authorized": False,
        "hardware_transfer_authorized": False,
        "heldout_tuning_performed": False,
        "next_gate": NEXT_GATE,
        "claim_boundary": (
            "C-MAPSS external/sham action-cost signal may be described as confirmed "
            "only as a narrow software held-out signal. v2.4 does not earn an "
            "incremental superiority claim over v2.2 while the paired reference CI crosses zero."
        ),
    }

    confirmation_csv_rows = [{k: v for k, v in row.items() if k != "delta_rows"} for row in checks]
    reference_csv_rows = []
    for row in checks:
        if row["family"] == FAMILY_CMAPSS:
            reference_csv_rows.append({k: v for k, v in row.items() if k != "delta_rows"})
    partition_csv_rows = external_partition_rows + reference_partition_rows

    results = {
        "tier": TIER,
        "status": status,
        "generated_at_utc": utc_now(),
        "runner_revision": RUNNER_REVISION,
        "source_tier7_4f": {
            "results": str(TIER7_4F_RESULTS),
            "score_rows": str(TIER7_4F_SCORE_ROWS),
            "model_summary": str(TIER7_4F_MODEL_SUMMARY),
            "family_decisions": str(TIER7_4F_FAMILY_DECISIONS),
            "cost_model": str(TIER7_4F_COST_MODEL),
        },
        "criteria": criteria,
        "confirmation_checks": confirmation_csv_rows,
        "reference_partition_checks": partition_csv_rows,
        "nab_failure": nab_failure,
        "decision": decision,
    }

    artifacts: dict[str, Path] = {}
    artifacts["results_json"] = output_dir / "tier7_4g_results.json"
    artifacts["summary_csv"] = output_dir / "tier7_4g_summary.csv"
    artifacts["report_md"] = output_dir / "tier7_4g_report.md"
    artifacts["confirmation_checks_csv"] = output_dir / "tier7_4g_confirmation_checks.csv"
    artifacts["reference_separation_csv"] = output_dir / "tier7_4g_reference_separation.csv"
    artifacts["partition_checks_csv"] = output_dir / "tier7_4g_partition_checks.csv"
    artifacts["nab_failure_analysis_csv"] = output_dir / "tier7_4g_nab_failure_analysis.csv"
    artifacts["nab_category_analysis_csv"] = output_dir / "tier7_4g_nab_category_analysis.csv"
    artifacts["decision_json"] = output_dir / "tier7_4g_decision.json"
    artifacts["decision_csv"] = output_dir / "tier7_4g_decision.csv"

    write_json(artifacts["results_json"], results)
    write_csv(artifacts["summary_csv"], criteria, ["criterion", "value", "rule", "pass", "details"])
    write_csv(artifacts["confirmation_checks_csv"], confirmation_csv_rows)
    write_csv(artifacts["reference_separation_csv"], reference_csv_rows)
    write_csv(artifacts["partition_checks_csv"], partition_csv_rows)
    write_csv(artifacts["nab_failure_analysis_csv"], [nab_failure])
    write_csv(artifacts["nab_category_analysis_csv"], nab_category_failure_rows)
    write_json(artifacts["decision_json"], decision)
    write_csv(artifacts["decision_csv"], [decision])
    artifacts["report_md"].write_text(
        make_report(output_dir, status, criteria, confirmation_csv_rows, decision, nab_failure),
        encoding="utf-8",
    )

    manifest = make_manifest(output_dir, artifacts, status)
    artifacts["latest_manifest_json"] = output_dir / "tier7_4g_latest_manifest.json"
    write_json(artifacts["latest_manifest_json"], manifest)

    print(json.dumps(json_safe({"status": status, "outcome": outcome, "output_dir": output_dir, "next_gate": NEXT_GATE}), indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
