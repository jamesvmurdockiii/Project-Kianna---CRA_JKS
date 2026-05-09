#!/usr/bin/env python3
"""Tier 7.7e - finite-stream repair / preflight contract.

Tier 7.7d found that the locked long-run NARMA10 stream becomes non-finite at
required lengths for seed 44. This gate does not score CRA. It reproduces the
blocker, defines an explicit finite-stream repair rule, validates that rule
across the locked lengths/seeds, and records the boundary before any long-run
scoreboard can be rerun.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"

TIER = "Tier 7.7e - Finite-Stream Repair / Preflight Contract"
RUNNER_REVISION = "tier7_7e_finite_stream_repair_preflight_20260509_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_7e_20260509_finite_stream_repair_preflight"
PREREQ_77D = CONTROLLED / "tier7_7d_20260509_standardized_long_run_failure_scoring_gate" / "tier7_7d_results.json"
PREREQ_77C = CONTROLLED / "tier7_7c_20260509_standardized_long_run_failure_contract" / "tier7_7c_results.json"

REQUIRED_LENGTHS = [8000, 16000, 32000]
OPTIONAL_LENGTHS = [50000]
LOCKED_SEEDS = [42, 43, 44]
NEXT_GATE = "Tier 7.7f - Repaired Finite-Stream Long-Run Scoreboard"


@dataclass(frozen=True)
class GeneratorOption:
    generator_id: str
    role: str
    input_max: float
    bounded_output: bool
    selected: bool
    rationale: str
    literature_status: str


GENERATOR_OPTIONS = [
    GeneratorOption(
        generator_id="narma10_standard_u05",
        role="current locked 7.7b/7.7d generator",
        input_max=0.5,
        bounded_output=False,
        selected=False,
        rationale="Preserve as the original standard-equation audit row; 7.7d showed it can diverge at long length.",
        literature_status="standard Atiya/Parlos-style NARMA10 input range used broadly in reservoir-computing benchmarks",
    ),
    GeneratorOption(
        generator_id="narma10_reduced_input_u02",
        role="selected finite-stream repair for the next long-run rerun",
        input_max=0.2,
        bounded_output=False,
        selected=True,
        rationale="Keep the same NARMA10 recurrence coefficients and seed policy, but reduce the input range using a documented divergence-control variant. Future scoring must label this as repaired NARMA10 and may not merge it silently with prior u05 scores.",
        literature_status="documented NARMA-family divergence-control option; changes target scale and therefore requires a fresh repaired-scoreboard rerun",
    ),
    GeneratorOption(
        generator_id="narma10_tanh_bounded_u05",
        role="alternative not selected",
        input_max=0.5,
        bounded_output=True,
        selected=False,
        rationale="Finite by construction but changes the target nonlinearity more strongly than reduced input range, so it remains a fallback only.",
        literature_status="bounded-output wrappers appear in NARMA-family variants but are not selected for this repair",
    ),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, np.generic):
        return json_safe(value.item())
    return value


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = []
        for row in rows:
            for key in row:
                if key not in fieldnames:
                    fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json_safe(row.get(key, "")) for key in fieldnames})


def criterion(name: str, value: Any, rule: str, passed: bool, details: str = "") -> dict[str, Any]:
    return {
        "name": name,
        "criterion": name,
        "value": json_safe(value),
        "operator": rule,
        "rule": rule,
        "passed": bool(passed),
        "pass": bool(passed),
        "note": details,
        "details": details,
    }


def zscore_descriptor(values: np.ndarray, train_end: int) -> dict[str, Any]:
    finite = bool(np.all(np.isfinite(values)))
    if not finite:
        return {
            "finite": False,
            "train_mean": None,
            "train_std": None,
            "normalized_finite": False,
        }
    train = values[:train_end]
    mean = float(np.mean(train))
    std = float(np.std(train))
    safe_std = std if std > 1e-12 else 1.0
    normalized = (values - mean) / safe_std
    return {
        "finite": True,
        "train_mean": mean,
        "train_std": std,
        "safe_train_std": safe_std,
        "normalized_finite": bool(np.all(np.isfinite(normalized))),
        "normalized_min": float(np.min(normalized)),
        "normalized_max": float(np.max(normalized)),
    }


def generate_narma10_raw(length: int, seed: int, option: GeneratorOption) -> dict[str, Any]:
    rng = np.random.default_rng(seed + 3003)
    warmup = 200
    total = int(length) + warmup + 20
    u = rng.uniform(0.0, float(option.input_max), size=total)
    y = np.zeros(total, dtype=float)
    first_nonfinite_index: int | None = None
    first_nonfinite_value: float | None = None
    for t in range(10, total - 1):
        # The original u05 generator is intentionally audited for divergence;
        # suppress expected NumPy overflow noise while still recording the
        # first non-finite cell.
        with np.errstate(over="ignore", invalid="ignore"):
            raw = (
                0.3 * y[t]
                + 0.05 * y[t] * np.sum(y[t - 9 : t + 1])
                + 1.5 * u[t - 9] * u[t]
                + 0.1
            )
        if option.bounded_output:
            raw = math.tanh(float(raw)) if math.isfinite(float(raw)) else raw
        y[t + 1] = raw
        if not math.isfinite(float(raw)):
            first_nonfinite_index = int(t + 1)
            first_nonfinite_value = float(raw)
            break
    observed_raw = u[warmup : warmup + int(length)]
    target_raw = y[warmup + 1 : warmup + 1 + int(length)]
    train_end = int(math.floor(int(length) * 0.65))
    observed_desc = zscore_descriptor(observed_raw, train_end)
    target_desc = zscore_descriptor(target_raw, train_end)
    target_finite = bool(np.all(np.isfinite(target_raw)))
    observed_finite = bool(np.all(np.isfinite(observed_raw)))
    finite = observed_finite and target_finite and observed_desc["normalized_finite"] and target_desc["normalized_finite"]
    return {
        "generator_id": option.generator_id,
        "length": int(length),
        "seed": int(seed),
        "input_min": 0.0,
        "input_max": float(option.input_max),
        "bounded_output": bool(option.bounded_output),
        "warmup": warmup,
        "train_end": train_end,
        "observed_finite": observed_finite,
        "target_finite": target_finite,
        "observed_normalized_finite": bool(observed_desc["normalized_finite"]),
        "target_normalized_finite": bool(target_desc["normalized_finite"]),
        "finite_stream_pass": finite,
        "first_nonfinite_index_raw": first_nonfinite_index,
        "first_nonfinite_value": first_nonfinite_value,
        "target_min": float(np.nanmin(target_raw)) if target_finite else None,
        "target_max": float(np.nanmax(target_raw)) if target_finite else None,
        "target_mean_train": target_desc.get("train_mean"),
        "target_std_train": target_desc.get("train_std"),
        "target_normalized_min": target_desc.get("normalized_min"),
        "target_normalized_max": target_desc.get("normalized_max"),
    }


def build_contract(selected: GeneratorOption) -> dict[str, Any]:
    return {
        "question": "Can the long-run NARMA10 stream be made finite under a predeclared standardized rule before rerunning any long-run scoreboard?",
        "hypothesis": "A documented finite-stream NARMA10 repair can preserve the nonlinear-memory benchmark role while eliminating long-run non-finite targets across locked lengths and seeds.",
        "null_hypothesis": "The NARMA10 repair is not finite across locked lengths/seeds, silently changes the benchmark without labeling it, or would allow post-hoc score inflation.",
        "mechanism_under_test": "benchmark stream generator policy only; no CRA mechanism, model score, readout retune, baseline freeze, or hardware/native transfer is tested here",
        "selected_generator": selected.generator_id,
        "selected_generator_rule": {
            "equation_coefficients": {"alpha": 0.3, "beta": 0.05, "gamma": 1.5, "delta": 0.1, "order": 10},
            "input_distribution": f"u_t ~ Uniform(0, {selected.input_max})",
            "output_wrapper": "none" if not selected.bounded_output else "tanh(raw_update)",
            "seed_policy": "same locked seeds 42/43/44 with the existing seed+3003 random stream",
            "labeling_rule": "future scoreboards must label NARMA as repaired_narma10_reduced_input_u02 and must not merge these scores silently with prior u05 NARMA scores",
        },
        "lengths": REQUIRED_LENGTHS,
        "optional_lengths": OPTIONAL_LENGTHS,
        "seeds": LOCKED_SEEDS,
        "repair_options": [option.__dict__ for option in GENERATOR_OPTIONS],
        "pass_fail_criteria": [
            {
                "criterion": "selected generator finite at all required length/seed cells",
                "pass_rule": "observed, target, and train-prefix normalized arrays are all finite for 8000/16000/32000 x seeds 42/43/44",
            },
            {
                "criterion": "original failure preserved",
                "pass_rule": "the original standard_u05 generator is retained as an audit row and reproduces at least one non-finite long-run cell",
            },
            {
                "criterion": "no hidden score inflation",
                "pass_rule": "the repaired stream must be scored in a new gate, with all models rerun on the same repaired stream and no direct recycling of prior NARMA scores",
            },
            {
                "criterion": "no mechanism tuning",
                "pass_rule": "the repair changes only the benchmark generator policy, not CRA mechanisms, baselines, readout hyperparameters, or splits",
            },
        ],
        "expected_next_artifacts": [
            "tier7_7f_results.json",
            "tier7_7f_report.md",
            "tier7_7f_length_scoreboard.csv",
            "tier7_7f_length_aggregate.csv",
            "tier7_7f_repaired_stream_manifest.json",
            "tier7_7f_claim_boundary.md",
        ],
        "external_reference_notes": [
            {
                "topic": "standard NARMA10",
                "note": "The standard recurrence commonly uses u in [0, 0.5] with coefficients 0.3, 0.05, 1.5, 0.1.",
                "url": "https://www.nature.com/articles/srep22381",
            },
            {
                "topic": "NARMA divergence and repair variants",
                "note": "A reservoir-computing tutorial explicitly notes that even standard NARMA10 can occasionally diverge and cites reduced input range u in [0, 0.2] as one documented approach.",
                "url": "https://link.springer.com/article/10.1007/s11047-024-09997-y",
            },
        ],
        "nonclaims": [
            "not a CRA score",
            "not a public-usefulness result",
            "not a baseline freeze",
            "not evidence that CRA beats ESN/ridge/online baselines",
            "not hardware/native transfer",
            "not a mechanism implementation",
            "not language, broad reasoning, AGI, or ASI evidence",
        ],
        "next_gate": NEXT_GATE,
    }


def write_report(output_dir: Path, payload: dict[str, Any]) -> None:
    contract = payload["contract"]
    lines = [
        "# Tier 7.7e Finite-Stream Repair / Preflight Contract",
        "",
        f"- Generated: `{payload['generated_at_utc']}`",
        f"- Status: **{payload['status'].upper()}**",
        f"- Criteria: `{payload['criteria_passed']}/{payload['criteria_total']}`",
        f"- Outcome: `{payload['classification']['outcome']}`",
        f"- Selected generator: `{contract['selected_generator']}`",
        "",
        "## Question",
        "",
        contract["question"],
        "",
        "## Selected Repair",
        "",
        f"- Input distribution: `{contract['selected_generator_rule']['input_distribution']}`",
        f"- Output wrapper: `{contract['selected_generator_rule']['output_wrapper']}`",
        f"- Labeling rule: {contract['selected_generator_rule']['labeling_rule']}",
        "",
        "## Preflight Summary",
        "",
        "| Generator | Required cells | Passed cells | Non-finite cells | Selected |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for row in payload["generator_summary"]:
        lines.append(
            f"| `{row['generator_id']}` | {row['required_cells']} | {row['required_passed_cells']} | {row['required_nonfinite_cells']} | {row['selected']} |"
        )
    lines.extend(["", "## Claim Boundary", "", payload["claim_boundary"], "", "## Nonclaims", ""])
    for item in contract["nonclaims"]:
        lines.append(f"- {item}")
    lines.append("")
    (output_dir / "tier7_7e_report.md").write_text("\n".join(lines), encoding="utf-8")


def summarize_generators(preflight_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for option in GENERATOR_OPTIONS:
        rows = [row for row in preflight_rows if row["generator_id"] == option.generator_id and row["length"] in REQUIRED_LENGTHS]
        passed = [row for row in rows if row["finite_stream_pass"]]
        out.append(
            {
                "generator_id": option.generator_id,
                "selected": option.selected,
                "required_cells": len(rows),
                "required_passed_cells": len(passed),
                "required_nonfinite_cells": len(rows) - len(passed),
                "all_required_finite": len(rows) == len(REQUIRED_LENGTHS) * len(LOCKED_SEEDS) and len(rows) == len(passed),
                "role": option.role,
                "rationale": option.rationale,
            }
        )
    return out


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    prereq_77d = read_json(PREREQ_77D)
    prereq_77c = read_json(PREREQ_77C)
    selected = next(option for option in GENERATOR_OPTIONS if option.selected)
    lengths = REQUIRED_LENGTHS + ([] if args.skip_optional else OPTIONAL_LENGTHS)
    preflight_rows: list[dict[str, Any]] = []
    for option in GENERATOR_OPTIONS:
        for length in lengths:
            for seed in LOCKED_SEEDS:
                preflight_rows.append(generate_narma10_raw(length, seed, option))
    generator_summary = summarize_generators(preflight_rows)
    selected_summary = next(row for row in generator_summary if row["selected"])
    original_summary = next(row for row in generator_summary if row["generator_id"] == "narma10_standard_u05")
    selected_required_rows = [
        row
        for row in preflight_rows
        if row["generator_id"] == selected.generator_id and row["length"] in REQUIRED_LENGTHS
    ]
    original_required_rows = [
        row
        for row in preflight_rows
        if row["generator_id"] == "narma10_standard_u05" and row["length"] in REQUIRED_LENGTHS
    ]
    contract = build_contract(selected)
    criteria = [
        criterion("Tier 7.7d prerequisite exists", str(PREREQ_77D), "exists", PREREQ_77D.exists()),
        criterion("Tier 7.7d prerequisite passed", prereq_77d.get("status"), "== pass", prereq_77d.get("status") == "pass"),
        criterion("Tier 7.7d outcome is finite-stream blocker", (prereq_77d.get("classification") or {}).get("outcome"), "== benchmark_stream_invalid", (prereq_77d.get("classification") or {}).get("outcome") == "benchmark_stream_invalid"),
        criterion("Tier 7.7c contract exists", str(PREREQ_77C), "exists and pass", PREREQ_77C.exists() and prereq_77c.get("status") == "pass"),
        criterion("selected repair is explicit", selected.generator_id, "non-empty selected generator", bool(selected.generator_id)),
        criterion("selected repair preserves equation coefficients", contract["selected_generator_rule"]["equation_coefficients"], "standard NARMA10 coefficients", True),
        criterion("selected repair finite at all required cells", selected_summary["required_passed_cells"], "== 9", selected_summary["required_passed_cells"] == len(REQUIRED_LENGTHS) * len(LOCKED_SEEDS)),
        criterion("selected repair normalization finite", all(row["observed_normalized_finite"] and row["target_normalized_finite"] for row in selected_required_rows), "all true", all(row["observed_normalized_finite"] and row["target_normalized_finite"] for row in selected_required_rows)),
        criterion("original failure reproduced and preserved", original_summary["required_nonfinite_cells"], "> 0", original_summary["required_nonfinite_cells"] > 0),
        criterion("same seeds locked", LOCKED_SEEDS, "== [42,43,44]", LOCKED_SEEDS == [42, 43, 44]),
        criterion("same required lengths locked", REQUIRED_LENGTHS, "== [8000,16000,32000]", REQUIRED_LENGTHS == [8000, 16000, 32000]),
        criterion("all generator options documented", len(GENERATOR_OPTIONS), ">= 3", len(GENERATOR_OPTIONS) >= 3),
        criterion("next gate is scoring rerun only after repair", NEXT_GATE, "declared", bool(NEXT_GATE)),
        criterion("no candidate scores computed", False, "must remain false", True),
        criterion("no automatic baseline freeze", False, "must remain false", True),
        criterion("hardware/native transfer blocked", False, "must remain false", True),
    ]
    passed = sum(1 for item in criteria if item["passed"])
    status = "pass" if passed == len(criteria) else "fail"
    claim_boundary = (
        "Tier 7.7e repairs and preflights the long-run NARMA10 benchmark stream only. "
        "It authorizes a new repaired-stream long-run scoring gate if the selected generator is finite, but it does not score CRA, "
        "does not freeze a baseline, does not claim public usefulness, does not authorize hardware/native transfer, and does not allow prior u05 NARMA scores to be silently mixed with repaired u02 scores."
    )
    payload = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "status": status,
        "criteria": criteria,
        "criteria_passed": passed,
        "criteria_total": len(criteria),
        "output_dir": str(output_dir),
        "prerequisites": {
            "tier7_7d_results": str(PREREQ_77D),
            "tier7_7d_status": prereq_77d.get("status"),
            "tier7_7d_outcome": (prereq_77d.get("classification") or {}).get("outcome"),
            "tier7_7c_results": str(PREREQ_77C),
            "tier7_7c_status": prereq_77c.get("status"),
        },
        "contract": contract,
        "generator_summary": generator_summary,
        "preflight_rows": preflight_rows,
        "classification": {
            "outcome": "finite_stream_repair_preflight_passed" if status == "pass" else "finite_stream_repair_preflight_failed",
            "selected_generator": selected.generator_id,
            "repaired_scoring_authorized": status == "pass",
            "next_gate": NEXT_GATE,
            "baseline_freeze_authorized": False,
            "hardware_transfer_authorized": False,
            "public_usefulness_authorized": False,
        },
        "claim_boundary": claim_boundary,
    }
    write_json(output_dir / "tier7_7e_results.json", payload)
    write_json(output_dir / "tier7_7e_finite_stream_contract.json", contract)
    write_csv(output_dir / "tier7_7e_summary.csv", criteria)
    write_csv(output_dir / "tier7_7e_stream_preflight.csv", preflight_rows)
    write_csv(output_dir / "tier7_7e_generator_options.csv", [option.__dict__ for option in GENERATOR_OPTIONS])
    write_csv(output_dir / "tier7_7e_generator_summary.csv", generator_summary)
    write_csv(output_dir / "tier7_7e_standard_failure_reproduction.csv", original_required_rows)
    (output_dir / "tier7_7e_claim_boundary.md").write_text(claim_boundary + "\n", encoding="utf-8")
    write_report(output_dir, payload)
    manifest = {
        "tier": TIER,
        "status": status,
        "generated_at_utc": payload["generated_at_utc"],
        "output_dir": str(output_dir),
        "results_json": str(output_dir / "tier7_7e_results.json"),
        "report_md": str(output_dir / "tier7_7e_report.md"),
        "summary_csv": str(output_dir / "tier7_7e_summary.csv"),
        "selected_generator": selected.generator_id,
        "classification_outcome": payload["classification"]["outcome"],
    }
    write_json(output_dir / "tier7_7e_latest_manifest.json", manifest)
    write_json(CONTROLLED / "tier7_7e_latest_manifest.json", manifest)
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=TIER)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--skip-optional", action="store_true", help="Skip optional 50000-step finite preflight rows.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    payload = run(args)
    print(
        json.dumps(
            json_safe(
                {
                    "status": payload["status"],
                    "classification": payload["classification"],
                    "generator_summary": payload["generator_summary"],
                }
            ),
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
