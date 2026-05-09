#!/usr/bin/env python3
"""Tier 7.7d - standardized long-run / failure-localization scoring gate.

This runner executes the Tier 7.7c pre-registered long-run contract. It reuses
Tier 7.7b's locked scoreboard implementation and only varies the predeclared
stream length. It does not add mechanisms, retune models, alter splits, or
promote a baseline.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from tier5_19a_temporal_substrate_reference import criterion, json_safe, write_json  # noqa: E402
from tier7_0e_standard_dynamical_v2_2_sweep import geomean, ratio, write_rows  # noqa: E402
from tier7_7b_v2_5_standardized_scoreboard_scoring_gate import (  # noqa: E402
    COMPOSITION_DISABLED,
    ESN,
    MEMORY_DISABLED,
    ONLINE_LMS,
    PREDICTION_DISABLED,
    RIDGE_LAG,
    SELF_EVAL_DISABLED,
    STATE_DISABLED,
    TARGET_SHUFFLE,
    TIME_SHUFFLE,
    V23,
    V25,
    classify as classify_single_length,
    fairness_contract as fairness_contract_single_length,
    leakage_audit as leakage_audit_single_length,
    load_secondary_confirmation,
    run_scoreboard,
)
from tier7_7c_standardized_long_run_failure_contract import (  # noqa: E402
    DEFAULT_OUTPUT_DIR as CONTRACT_OUTPUT_DIR,
    RUNNER_REVISION as CONTRACT_REVISION,
)
from tier7_7b_v2_5_standardized_scoreboard_scoring_gate import build_parser as build_77b_parser  # noqa: E402


TIER = "Tier 7.7d - Standardized Long-Run / Failure-Localization Scoring Gate"
RUNNER_REVISION = "tier7_7d_standardized_long_run_failure_scoring_gate_20260509_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_7d_20260509_standardized_long_run_failure_scoring_gate"
CONTRACT_RESULTS = CONTRACT_OUTPUT_DIR / "tier7_7c_results.json"
CONTRACT_JSON = CONTRACT_OUTPUT_DIR / "tier7_7c_long_run_contract.json"
REQUIRED_LENGTHS = [8000, 16000, 32000]
OPTIONAL_LENGTH = 50000


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def parse_int_csv(value: str) -> list[int]:
    out: list[int] = []
    for chunk in str(value).split(","):
        chunk = chunk.strip()
        if chunk:
            out.append(int(chunk))
    return out


def safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def metric_from_per_task(classification: dict[str, Any], task: str, key: str) -> float | None:
    row = next((item for item in classification.get("per_task", []) if item.get("task") == task), None)
    if not row:
        return None
    return safe_float(row.get(key))


def summarize_length(length: int, scoreboard: dict[str, Any], classification: dict[str, Any], leak: dict[str, Any]) -> dict[str, Any]:
    best_external = classification.get("best_external") or {}
    return {
        "length": int(length),
        "status": "pass",
        "outcome": classification.get("outcome"),
        "v2_5_geomean_mse": classification.get("v2_5_geomean_mse"),
        "v2_3_geomean_mse": classification.get("v2_3_geomean_mse"),
        "v2_3_divided_by_v2_5": classification.get("v2_3_divided_by_v2_5"),
        "paired_ci_low": (classification.get("paired_delta_v2_3_minus_v2_5") or {}).get("ci_low"),
        "paired_ci_high": (classification.get("paired_delta_v2_3_minus_v2_5") or {}).get("ci_high"),
        "task_wins_vs_v2_3": classification.get("task_wins_vs_v2_3"),
        "mackey_v2_3_divided_by_v2_5": metric_from_per_task(classification, "mackey_glass", "v2_3_divided_by_v2_5"),
        "lorenz_v2_3_divided_by_v2_5": metric_from_per_task(classification, "lorenz", "v2_3_divided_by_v2_5"),
        "narma10_v2_3_divided_by_v2_5": metric_from_per_task(classification, "narma10", "v2_3_divided_by_v2_5"),
        "best_external_model": best_external.get("model"),
        "best_external_geomean_mse": best_external.get("geomean_mse"),
        "v2_5_beats_best_external": classification.get("v2_5_beats_best_external"),
        "target_shuffle_margin": classification.get("target_shuffle_margin"),
        "time_shuffle_margin": classification.get("time_shuffle_margin"),
        "shams_block_promotion": classification.get("shams_block_promotion"),
        "leakage_status": leak.get("status"),
        "runtime_seconds": scoreboard.get("runtime_seconds"),
    }


def margin_for_model(classification: dict[str, Any], model: str) -> float | None:
    row = next((item for item in classification.get("sham_rows", []) if item.get("model") == model), None)
    return safe_float((row or {}).get("margin_sham_divided_by_v2_5"))


def classify_long_run(length_rows: list[dict[str, Any]], *, invalid_task_count: int = 0) -> dict[str, Any]:
    required = [row for row in length_rows if int(row["length"]) in REQUIRED_LENGTHS]
    aggregate_ratios = [safe_float(row.get("v2_3_divided_by_v2_5")) for row in required]
    mackey_ratios = [safe_float(row.get("mackey_v2_3_divided_by_v2_5")) for row in required]
    lorenz_ratios = [safe_float(row.get("lorenz_v2_3_divided_by_v2_5")) for row in required]
    narma_ratios = [safe_float(row.get("narma10_v2_3_divided_by_v2_5")) for row in required]
    external_beats = [not bool(row.get("v2_5_beats_best_external")) for row in required]
    shams_block = [bool(row.get("shams_block_promotion")) for row in required]
    aggregate_persists = all(value is not None and value > 1.0 for value in aggregate_ratios)
    aggregate_material = all(value is not None and value >= 1.10 for value in aggregate_ratios[1:])
    mackey_persists = all(value is not None and value > 1.0 for value in mackey_ratios)
    lorenz_improves = any(value is not None and value > 1.05 for value in lorenz_ratios)
    narma_improves = any(value is not None and value > 1.05 for value in narma_ratios)
    external_gap_persists = all(external_beats)
    sham_specific = not any(shams_block)
    if invalid_task_count > 0:
        outcome = "benchmark_stream_invalid"
        recommendation = "Do not cite a long-run scoreboard; repair/preflight the finite NARMA10 long-run stream before scoring."
    elif aggregate_persists and aggregate_material and sham_specific and not external_gap_persists and (lorenz_improves or narma_improves):
        outcome = "long_run_confirmed"
        recommendation = "Long-run standardized support is strong enough to design an independent confirmation gate; still no automatic freeze."
    elif mackey_persists and external_gap_persists and not (lorenz_improves or narma_improves):
        outcome = "mackey_only_localized"
        recommendation = "The signal remains localized to Mackey-Glass; prioritize failure-specific diagnostics before adding mechanisms."
    elif external_gap_persists:
        outcome = "baseline_gap_persists"
        recommendation = "Strong external baselines still dominate; broad usefulness remains blocked."
    elif not aggregate_persists:
        outcome = "signal_collapses"
        recommendation = "The 7.7b signal does not persist across required longer streams; narrow claims or return to mechanism diagnostics."
    else:
        outcome = "stop_or_narrow"
        recommendation = "Long-run evidence is mixed and not promotion-grade; stop broad usefulness claims until a new predeclared mechanism gate changes this."
    return {
        "outcome": outcome,
        "recommendation": recommendation,
        "aggregate_persists": aggregate_persists,
        "aggregate_material_long_lengths": aggregate_material,
        "mackey_persists": mackey_persists,
        "lorenz_improves_any_length": lorenz_improves,
        "narma10_improves_any_length": narma_improves,
        "external_gap_persists": external_gap_persists,
        "sham_specific": sham_specific,
        "invalid_task_count": int(invalid_task_count),
        "required_aggregate_ratios": aggregate_ratios,
        "required_mackey_ratios": mackey_ratios,
        "required_lorenz_ratios": lorenz_ratios,
        "required_narma10_ratios": narma_ratios,
        "claim_allowed": {
            "long_run_confirmed": outcome == "long_run_confirmed",
            "localized_signal": outcome in {"long_run_confirmed", "mackey_only_localized"},
            "public_usefulness_upgrade": False,
            "baseline_freeze": False,
            "hardware_or_native_transfer": False,
        },
        "nonclaims": [
            "not a new baseline freeze",
            "not hardware/native evidence",
            "not public-usefulness superiority over ESN/ridge/online baselines unless the table shows it",
            "not a complete long-run scoreboard if any required benchmark stream is non-finite",
            "not a license to tune benchmarks after seeing long-run results",
            "not language, AGI, or ASI evidence",
        ],
    }


def failure_decomposition(length_rows: list[dict[str, Any]], classifications: dict[int, dict[str, Any]]) -> list[dict[str, Any]]:
    by_len = {int(row["length"]): row for row in length_rows}
    lengths = [int(row["length"]) for row in length_rows]
    def series(key: str) -> str:
        return ";".join(f"{length}:{by_len[length].get(key)}" for length in lengths)
    narma_values = [safe_float(by_len[length].get("narma10_v2_3_divided_by_v2_5")) for length in lengths]
    rows = [
        {
            "question_id": "mackey_signal_persistence",
            "answer": "persists" if all((safe_float(by_len[l].get("mackey_v2_3_divided_by_v2_5")) or 0.0) > 1.0 for l in lengths) else "does_not_persist",
            "evidence": series("mackey_v2_3_divided_by_v2_5"),
            "interpretation": "Mackey-Glass is the scalar delayed-recurrence signal first seen in 7.7b.",
        },
        {
            "question_id": "lorenz_state_reconstruction_gap",
            "answer": "improves" if any((safe_float(by_len[l].get("lorenz_v2_3_divided_by_v2_5")) or 0.0) > 1.05 for l in lengths) else "flat_or_negative",
            "evidence": series("lorenz_v2_3_divided_by_v2_5"),
            "interpretation": "Flat Lorenz ratios indicate the current scalar interface/state reconstruction remains insufficient.",
        },
        {
            "question_id": "narma_memory_depth_gap",
            "answer": "invalid_nonfinite_stream" if any(value is None for value in narma_values) else ("improves" if any((value or 0.0) > 1.05 for value in narma_values) else "flat_or_negative"),
            "evidence": series("narma10_v2_3_divided_by_v2_5"),
            "interpretation": "Missing NARMA10 ratios at required lengths are benchmark-generator failures, not CRA scores.",
        },
        {
            "question_id": "external_baseline_gap",
            "answer": "persists" if all(not bool(by_len[l].get("v2_5_beats_best_external")) for l in lengths) else "partially_closed",
            "evidence": ";".join(f"{l}:{by_len[l].get('best_external_model')}={by_len[l].get('best_external_geomean_mse')}" for l in lengths),
            "interpretation": "If ESN/ridge/online baselines still win, broad usefulness remains blocked.",
        },
        {
            "question_id": "sham_specificity",
            "answer": "separated" if all(not bool(by_len[l].get("shams_block_promotion")) for l in lengths) else "blocked_by_sham",
            "evidence": ";".join(
                f"{l}:target={by_len[l].get('target_shuffle_margin')},time={by_len[l].get('time_shuffle_margin')}" for l in lengths
            ),
            "interpretation": "Shams must remain worse than v2.5 for any positive long-run claim.",
        },
    ]
    return rows


def write_report(output_dir: Path, payload: dict[str, Any]) -> None:
    c = payload["classification"]
    lines = [
        "# Tier 7.7d Standardized Long-Run / Failure-Localization Scoring Gate",
        "",
        f"- Generated: `{payload['generated_at_utc']}`",
        f"- Status: **{payload['status'].upper()}**",
        f"- Criteria: `{payload['criteria_passed']}/{payload['criteria_total']}`",
        f"- Outcome: `{c['outcome']}`",
        f"- Recommendation: {c['recommendation']}",
        "",
        "## Claim Boundary",
        "",
        payload["claim_boundary"],
        "",
        "## Length Summary",
        "",
        "| Length | v2.5 MSE | v2.3 MSE | v2.3/v2.5 | Best external | v2.5 beats external | Outcome |",
        "| ---: | ---: | ---: | ---: | --- | --- | --- |",
    ]
    for row in payload["length_summary"]:
        lines.append(
            f"| {row['length']} | {row['v2_5_geomean_mse']} | {row['v2_3_geomean_mse']} | {row['v2_3_divided_by_v2_5']} | {row['best_external_model']} | {row['v2_5_beats_best_external']} | {row['outcome']} |"
        )
    lines.extend(["", "## Failure Decomposition", "", "| Question | Answer | Evidence |", "| --- | --- | --- |"])
    for row in payload["failure_decomposition"]:
        lines.append(f"| `{row['question_id']}` | `{row['answer']}` | {row['evidence']} |")
    lines.extend(["", "## Nonclaims", ""])
    for item in c["nonclaims"]:
        lines.append(f"- {item}")
    lines.append("")
    (output_dir / "tier7_7d_report.md").write_text("\n".join(lines), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    base = build_77b_parser()
    parser = argparse.ArgumentParser(description=TIER)
    parser.add_argument("--lengths", default="8000,16000,32000")
    parser.add_argument("--include-optional-50000", action="store_true")
    parser.add_argument("--tasks", default="mackey_glass,lorenz,narma10")
    parser.add_argument("--seeds", default="42,43,44")
    parser.add_argument("--horizon", type=int, default=8)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--smoke", action="store_true")
    # Mirror the scoring hyperparameters from 7.7b to avoid a hidden retune.
    for action in base._actions:
        if not action.option_strings or action.dest in {"help", "tasks", "seeds", "horizon", "output_dir", "smoke", "length"}:
            continue
        kwargs: dict[str, Any] = {"default": action.default, "help": argparse.SUPPRESS}
        if action.type is not None:
            kwargs["type"] = action.type
        if isinstance(action, argparse._StoreTrueAction):
            kwargs.pop("default", None)
            parser.add_argument(*action.option_strings, action="store_true", help=argparse.SUPPRESS)
        else:
            parser.add_argument(*action.option_strings, **kwargs)
    return parser


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    contract_results = read_json(CONTRACT_RESULTS)
    contract_json = read_json(CONTRACT_JSON)
    lengths = [720] if args.smoke else parse_int_csv(args.lengths)
    if args.include_optional_50000 and OPTIONAL_LENGTH not in lengths:
        lengths.append(OPTIONAL_LENGTH)
    started = time.perf_counter()
    secondary_rows = load_secondary_confirmation()
    length_summary: list[dict[str, Any]] = []
    length_scoreboard_rows: list[dict[str, Any]] = []
    length_aggregate_rows: list[dict[str, Any]] = []
    sham_rows: list[dict[str, Any]] = []
    leakage_by_length: list[dict[str, Any]] = []
    classifications: dict[int, dict[str, Any]] = {}
    scoreboards: dict[int, dict[str, Any]] = {}
    for length in lengths:
        length_args = copy.copy(args)
        length_args.length = int(length)
        length_args.output_dir = output_dir / f"length_{length}"
        length_args.smoke = False
        length_dir = output_dir / f"length_{length}"
        length_dir.mkdir(parents=True, exist_ok=True)
        scoreboard = run_scoreboard(length_args, length_dir)
        classification = classify_single_length(scoreboard, secondary_rows)
        leak = leakage_audit_single_length(scoreboard, length_args)
        classifications[int(length)] = classification
        scoreboards[int(length)] = scoreboard
        length_summary.append(summarize_length(length, scoreboard, classification, leak))
        for row in scoreboard["summary_rows"]:
            length_scoreboard_rows.append({"length": int(length), **row})
        for row in [*scoreboard["seed_aggregate_rows"], *scoreboard["seed_aggregate_summary"], *scoreboard["model_aggregate_rows"]]:
            length_aggregate_rows.append({"length": int(length), **row})
        for row in classification["sham_rows"]:
            sham_rows.append({"length": int(length), **row})
        leakage_by_length.append({"length": int(length), **leak})
    failure_rows = failure_decomposition(length_summary, classifications)
    invalid_task_count = sum(int(row.get("invalid_task_count") or 0) for row in leakage_by_length)
    classification = classify_long_run(length_summary, invalid_task_count=invalid_task_count)
    required_lengths_present = all(length in lengths for length in REQUIRED_LENGTHS) if not args.smoke else True
    criteria = [
        criterion("Tier 7.7c contract exists", str(CONTRACT_RESULTS), "exists and status pass", bool(contract_results) and contract_results.get("status") == "pass"),
        criterion("Tier 7.7c scoring authorization", (contract_results.get("classification") or {}).get("scoring_authorized"), "true", bool((contract_results.get("classification") or {}).get("scoring_authorized"))),
        criterion("required lengths present", lengths, "contains 8000/16000/32000", required_lengths_present),
        criterion("locked tasks", args.tasks, "Mackey/Lorenz/NARMA", args.tasks == "mackey_glass,lorenz,narma10" or bool(args.smoke)),
        criterion("locked seeds", args.seeds, "42,43,44", args.seeds == "42,43,44" or bool(args.smoke)),
        criterion("locked horizon", int(args.horizon), "8", int(args.horizon) == 8),
        criterion("all length scoreboards produced", len(length_summary), ">= required length count", len(length_summary) == len(lengths)),
        criterion("finite-stream audits captured", [row.get("status") for row in leakage_by_length], "all pass or benchmark_stream_invalid", all(row.get("status") == "pass" for row in leakage_by_length) or classification["outcome"] == "benchmark_stream_invalid"),
        criterion("failure decomposition produced", len(failure_rows), ">= 5", len(failure_rows) >= 5),
        criterion("classification produced", classification["outcome"], "non-empty", bool(classification["outcome"])),
        criterion("no automatic baseline freeze", classification["claim_allowed"]["baseline_freeze"], "false", classification["claim_allowed"]["baseline_freeze"] is False),
        criterion("hardware/native transfer blocked", classification["claim_allowed"]["hardware_or_native_transfer"], "false", classification["claim_allowed"]["hardware_or_native_transfer"] is False),
    ]
    passed = sum(1 for item in criteria if item["passed"])
    status = "pass" if passed == len(criteria) else "fail"
    claim_boundary = (
        "Tier 7.7d scores the Tier 7.7c locked long-run/failure-localization contract. "
        "It may localize whether the 7.7b signal persists, grows, or collapses, but it does not freeze a new baseline, "
        "does not authorize hardware/native transfer, does not retune benchmarks after seeing results, and does not claim "
        "language, broad reasoning, AGI, or ASI."
    )
    fairness_args = copy.copy(args)
    fairness_args.length = int(lengths[0]) if lengths else 0
    payload = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "contract_revision": CONTRACT_REVISION,
        "generated_at_utc": utc_now(),
        "status": status,
        "criteria": criteria,
        "criteria_passed": passed,
        "criteria_total": len(criteria),
        "output_dir": str(output_dir),
        "contract_results": str(CONTRACT_RESULTS),
        "contract_status": contract_results.get("status"),
        "contract": contract_json,
        "lengths": lengths,
        "classification": classification,
        "length_summary": length_summary,
        "failure_decomposition": failure_rows,
        "sham_controls": sham_rows,
        "leakage_audit": {"status": "pass" if all(row.get("status") == "pass" for row in leakage_by_length) else "fail", "by_length": leakage_by_length},
        "fairness_contract": {
            **fairness_contract_single_length(fairness_args),
            "lengths": lengths,
            "contract_source": str(CONTRACT_JSON),
            "long_run_contract": str(CONTRACT_RESULTS),
            "length_rule": "7.7d may score only lengths locked by Tier 7.7c.",
        },
        "secondary_confirmation": secondary_rows,
        "claim_boundary": claim_boundary,
        "runtime_seconds": time.perf_counter() - started,
    }
    write_json(output_dir / "tier7_7d_results.json", payload)
    write_rows(output_dir / "tier7_7d_summary.csv", criteria)
    write_report(output_dir, payload)
    write_rows(output_dir / "tier7_7d_length_scoreboard.csv", length_scoreboard_rows)
    write_rows(output_dir / "tier7_7d_length_aggregate.csv", [*length_summary, *length_aggregate_rows])
    write_rows(output_dir / "tier7_7d_failure_decomposition.csv", failure_rows)
    write_rows(output_dir / "tier7_7d_sham_controls.csv", sham_rows)
    write_json(output_dir / "tier7_7d_leakage_audit.json", payload["leakage_audit"])
    (output_dir / "tier7_7d_claim_boundary.md").write_text(claim_boundary + "\n", encoding="utf-8")
    manifest = {
        "tier": TIER,
        "status": status,
        "generated_at_utc": payload["generated_at_utc"],
        "output_dir": str(output_dir),
        "results_json": str(output_dir / "tier7_7d_results.json"),
        "report_md": str(output_dir / "tier7_7d_report.md"),
        "summary_csv": str(output_dir / "tier7_7d_summary.csv"),
        "classification_outcome": classification["outcome"],
    }
    write_json(output_dir / "tier7_7d_latest_manifest.json", manifest)
    write_json(CONTROLLED / "tier7_7d_latest_manifest.json", manifest)
    return payload


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    payload = run(args)
    print(json.dumps(json_safe({"status": payload["status"], "classification": payload["classification"], "output_dir": payload["output_dir"]}), indent=2, sort_keys=True))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
