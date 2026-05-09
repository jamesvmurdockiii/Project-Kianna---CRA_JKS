#!/usr/bin/env python3
"""Tier 7.7f - repaired finite-stream long-run scoreboard.

This gate reruns the Tier 7.7c long-run matrix after Tier 7.7e repaired and
preflighted the NARMA10 stream. It changes only the NARMA10 generator policy
for this repaired-scoreboard run: same recurrence coefficients, input
u_t ~ Uniform(0, 0.2), same locked seeds, same locked lengths, and all models
rerun on the same repaired stream.
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

import numpy as np

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import tier7_7b_v2_5_standardized_scoreboard_scoring_gate as scoreboard_mod  # noqa: E402
from tier5_19a_temporal_substrate_reference import criterion, json_safe, write_json  # noqa: E402
from tier7_0_standard_dynamical_benchmarks import SequenceTask, chronological_split, zscore_from_train  # noqa: E402
from tier7_0e_standard_dynamical_v2_2_sweep import write_rows  # noqa: E402
from tier7_7b_v2_5_standardized_scoreboard_scoring_gate import (  # noqa: E402
    classify as classify_single_length,
    fairness_contract as fairness_contract_single_length,
    leakage_audit as leakage_audit_single_length,
    load_secondary_confirmation,
    run_scoreboard,
)
from tier7_7b_v2_5_standardized_scoreboard_scoring_gate import build_parser as build_77b_parser  # noqa: E402
from tier7_7d_standardized_long_run_failure_scoring_gate import (  # noqa: E402
    OPTIONAL_LENGTH,
    REQUIRED_LENGTHS,
    classify_long_run,
    failure_decomposition,
    parse_int_csv,
    summarize_length,
)


TIER = "Tier 7.7f - Repaired Finite-Stream Long-Run Scoreboard"
RUNNER_REVISION = "tier7_7f_repaired_finite_stream_long_run_scoreboard_20260509_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_7f_20260509_repaired_finite_stream_long_run_scoreboard"
PREREQ_77E = CONTROLLED / "tier7_7e_20260509_finite_stream_repair_preflight" / "tier7_7e_results.json"
PREREQ_77C = CONTROLLED / "tier7_7c_20260509_standardized_long_run_failure_contract" / "tier7_7c_results.json"
REPAIRED_GENERATOR_ID = "narma10_reduced_input_u02"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def repaired_narma10_series(length: int, seed: int, *, horizon: int) -> SequenceTask:
    del horizon
    rng = np.random.default_rng(seed + 3003)
    warmup = 200
    total = int(length) + warmup + 20
    input_max = 0.2
    u = rng.uniform(0.0, input_max, size=total)
    y = np.zeros(total, dtype=float)
    for t in range(10, total - 1):
        y[t + 1] = (
            0.3 * y[t]
            + 0.05 * y[t] * np.sum(y[t - 9 : t + 1])
            + 1.5 * u[t - 9] * u[t]
            + 0.1
        )
    observed_raw = u[warmup : warmup + int(length)]
    target_raw = y[warmup + 1 : warmup + 1 + int(length)]
    train_end = chronological_split(int(length), 0.65)
    observed, obs_mu, obs_sd = zscore_from_train(observed_raw, train_end)
    target, tgt_mu, tgt_sd = zscore_from_train(target_raw, train_end)
    return SequenceTask(
        name="narma10",
        display_name="NARMA10 repaired U(0,0.2)",
        observed=observed,
        target=target,
        train_end=train_end,
        horizon=1,
        metadata={
            "generator_id": REPAIRED_GENERATOR_ID,
            "repaired_stream": True,
            "input_distribution": "Uniform(0,0.2)",
            "equation_coefficients": {"alpha": 0.3, "beta": 0.05, "gamma": 1.5, "delta": 0.1, "order": 10},
            "obs_mu": obs_mu,
            "obs_sd": obs_sd,
            "target_mu": tgt_mu,
            "target_sd": tgt_sd,
            "source_gate": "Tier 7.7e finite-stream repair/preflight",
            "labeling_rule": "Do not silently mix with prior U(0,0.5) NARMA scores.",
        },
    )


def install_repaired_build_task() -> None:
    original_build_task = scoreboard_mod.build_task

    def build_task(name: str, length: int, seed: int, horizon: int) -> SequenceTask:
        if name == "narma10":
            return repaired_narma10_series(length, seed, horizon=horizon)
        return original_build_task(name, length, seed, horizon)

    scoreboard_mod.build_task = build_task


def write_report(output_dir: Path, payload: dict[str, Any]) -> None:
    c = payload["classification"]
    lines = [
        "# Tier 7.7f Repaired Finite-Stream Long-Run Scoreboard",
        "",
        f"- Generated: `{payload['generated_at_utc']}`",
        f"- Status: **{payload['status'].upper()}**",
        f"- Criteria: `{payload['criteria_passed']}/{payload['criteria_total']}`",
        f"- Outcome: `{c['outcome']}`",
        f"- Recommendation: {c['recommendation']}",
        f"- Repaired generator: `{payload['repaired_stream_manifest']['selected_generator']}`",
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
    (output_dir / "tier7_7f_report.md").write_text("\n".join(lines), encoding="utf-8")


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
    install_repaired_build_task()
    prereq_77e = read_json(PREREQ_77E)
    prereq_77c = read_json(PREREQ_77C)
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
    for length in lengths:
        length_args = copy.copy(args)
        length_args.length = int(length)
        length_args.output_dir = output_dir / f"length_{length}"
        length_args.smoke = False
        length_args.output_dir.mkdir(parents=True, exist_ok=True)
        scoreboard = run_scoreboard(length_args, length_args.output_dir)
        classification = classify_single_length(scoreboard, secondary_rows)
        leak = leakage_audit_single_length(scoreboard, length_args)
        classifications[int(length)] = classification
        length_summary.append(summarize_length(length, scoreboard, classification, leak))
        for row in scoreboard["summary_rows"]:
            length_scoreboard_rows.append({"length": int(length), **row})
        for row in [*scoreboard["seed_aggregate_rows"], *scoreboard["seed_aggregate_summary"], *scoreboard["model_aggregate_rows"]]:
            length_aggregate_rows.append({"length": int(length), **row})
        for row in classification["sham_rows"]:
            sham_rows.append({"length": int(length), **row})
        leakage_by_length.append({"length": int(length), **leak})
    invalid_task_count = sum(int(row.get("invalid_task_count") or 0) for row in leakage_by_length)
    failure_rows = failure_decomposition(length_summary, classifications)
    classification = classify_long_run(length_summary, invalid_task_count=invalid_task_count)
    required_lengths_present = all(length in lengths for length in REQUIRED_LENGTHS) if not args.smoke else True
    repaired_stream_manifest = {
        "selected_generator": REPAIRED_GENERATOR_ID,
        "source_gate": str(PREREQ_77E),
        "equation_coefficients": {"alpha": 0.3, "beta": 0.05, "gamma": 1.5, "delta": 0.1, "order": 10},
        "input_distribution": "Uniform(0,0.2)",
        "output_wrapper": "none",
        "seed_policy": "same locked seeds 42/43/44 using seed+3003 random stream",
        "labeling_rule": "Repaired NARMA10 U(0,0.2); do not silently mix with prior U(0,0.5) scores.",
    }
    criteria = [
        criterion("Tier 7.7e prerequisite exists", str(PREREQ_77E), "exists and status pass", bool(prereq_77e) and prereq_77e.get("status") == "pass"),
        criterion("Tier 7.7e selected repaired generator", (prereq_77e.get("classification") or {}).get("selected_generator"), f"== {REPAIRED_GENERATOR_ID}", (prereq_77e.get("classification") or {}).get("selected_generator") == REPAIRED_GENERATOR_ID),
        criterion("Tier 7.7e authorizes repaired scoring", (prereq_77e.get("classification") or {}).get("repaired_scoring_authorized"), "true", bool((prereq_77e.get("classification") or {}).get("repaired_scoring_authorized"))),
        criterion("Tier 7.7c contract exists", str(PREREQ_77C), "exists and status pass", bool(prereq_77c) and prereq_77c.get("status") == "pass"),
        criterion("required lengths present", lengths, "contains 8000/16000/32000", required_lengths_present),
        criterion("locked tasks", args.tasks, "Mackey/Lorenz/NARMA", args.tasks == "mackey_glass,lorenz,narma10" or bool(args.smoke)),
        criterion("locked seeds", args.seeds, "42,43,44", args.seeds == "42,43,44" or bool(args.smoke)),
        criterion("locked horizon", int(args.horizon), "8", int(args.horizon) == 8),
        criterion("all length scoreboards produced", len(length_summary), "== requested length count", len(length_summary) == len(lengths)),
        criterion("finite-stream audits pass", [row.get("status") for row in leakage_by_length], "all pass", all(row.get("status") == "pass" for row in leakage_by_length)),
        criterion("no invalid repaired-stream tasks", invalid_task_count, "== 0", invalid_task_count == 0),
        criterion("failure decomposition produced", len(failure_rows), ">= 5", len(failure_rows) >= 5),
        criterion("classification produced", classification["outcome"], "non-empty", bool(classification["outcome"])),
        criterion("repaired stream manifest produced", repaired_stream_manifest["selected_generator"], f"== {REPAIRED_GENERATOR_ID}", repaired_stream_manifest["selected_generator"] == REPAIRED_GENERATOR_ID),
        criterion("no automatic baseline freeze", classification["claim_allowed"]["baseline_freeze"], "false", classification["claim_allowed"]["baseline_freeze"] is False),
        criterion("hardware/native transfer blocked", classification["claim_allowed"]["hardware_or_native_transfer"], "false", classification["claim_allowed"]["hardware_or_native_transfer"] is False),
    ]
    passed = sum(1 for item in criteria if item["passed"])
    status = "pass" if passed == len(criteria) else "fail"
    claim_boundary = (
        "Tier 7.7f reruns the locked long-run scoreboard after the Tier 7.7e repaired NARMA stream preflight. "
        "It may classify whether the v2.5 signal is long-run confirmed, Mackey-only localized, baseline-gap limited, collapsed, or stop/narrow, "
        "but it does not freeze a baseline, does not authorize hardware/native transfer, and does not permit repaired U(0,0.2) NARMA results to be silently mixed with prior U(0,0.5) NARMA scores."
    )
    fairness_args = copy.copy(args)
    fairness_args.length = int(lengths[0]) if lengths else 0
    payload = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "status": status,
        "criteria": criteria,
        "criteria_passed": passed,
        "criteria_total": len(criteria),
        "output_dir": str(output_dir),
        "contract_results": str(PREREQ_77C),
        "preflight_results": str(PREREQ_77E),
        "preflight_status": prereq_77e.get("status"),
        "lengths": lengths,
        "repaired_stream_manifest": repaired_stream_manifest,
        "classification": classification,
        "length_summary": length_summary,
        "failure_decomposition": failure_rows,
        "sham_controls": sham_rows,
        "leakage_audit": {"status": "pass" if all(row.get("status") == "pass" for row in leakage_by_length) else "fail", "by_length": leakage_by_length},
        "fairness_contract": {
            **fairness_contract_single_length(fairness_args),
            "lengths": lengths,
            "repaired_stream_manifest": repaired_stream_manifest,
            "length_rule": "7.7f may score only lengths locked by Tier 7.7c unless optional diagnostics are explicitly requested.",
        },
        "secondary_confirmation": secondary_rows,
        "claim_boundary": claim_boundary,
        "runtime_seconds": time.perf_counter() - started,
    }
    write_json(output_dir / "tier7_7f_results.json", payload)
    write_rows(output_dir / "tier7_7f_summary.csv", criteria)
    write_report(output_dir, payload)
    write_rows(output_dir / "tier7_7f_length_scoreboard.csv", length_scoreboard_rows)
    write_rows(output_dir / "tier7_7f_length_aggregate.csv", [*length_summary, *length_aggregate_rows])
    write_rows(output_dir / "tier7_7f_failure_decomposition.csv", failure_rows)
    write_rows(output_dir / "tier7_7f_sham_controls.csv", sham_rows)
    write_json(output_dir / "tier7_7f_leakage_audit.json", payload["leakage_audit"])
    write_json(output_dir / "tier7_7f_repaired_stream_manifest.json", repaired_stream_manifest)
    (output_dir / "tier7_7f_claim_boundary.md").write_text(claim_boundary + "\n", encoding="utf-8")
    manifest = {
        "tier": TIER,
        "status": status,
        "generated_at_utc": payload["generated_at_utc"],
        "output_dir": str(output_dir),
        "results_json": str(output_dir / "tier7_7f_results.json"),
        "report_md": str(output_dir / "tier7_7f_report.md"),
        "summary_csv": str(output_dir / "tier7_7f_summary.csv"),
        "classification_outcome": classification["outcome"],
        "selected_generator": REPAIRED_GENERATOR_ID,
    }
    write_json(output_dir / "tier7_7f_latest_manifest.json", manifest)
    write_json(CONTROLLED / "tier7_7f_latest_manifest.json", manifest)
    return payload


def main() -> int:
    args = build_parser().parse_args()
    payload = run(args)
    print(
        json.dumps(
            json_safe(
                {
                    "status": payload["status"],
                    "classification": payload["classification"],
                    "length_summary": payload["length_summary"],
                }
            ),
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
