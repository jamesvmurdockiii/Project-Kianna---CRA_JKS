#!/usr/bin/env python3
"""Tier 4.29f - Compact Native Mechanism Regression.

This tier is an evidence-regression gate over the canonical hardware passes
from Tiers 4.29a-e. It intentionally does not spend another SpiNNaker allocation
rerunning five already-ingested hardware suites. Instead, it verifies that the
promoted native-mechanism evidence set is complete, internally aligned, and safe
to freeze as a cumulative native mechanism bridge baseline.

Boundary:
  - This is a canonical audit/regression gate over real hardware evidence.
  - It is not a new hardware execution by itself.
  - It does not prove all mechanisms are active in one single runtime task.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "controlled_test_output"

TIER = "Tier 4.29f - Compact Native Mechanism Regression"
RUNNER_REVISION = "tier4_29f_compact_native_mechanism_regression_20260505_0001"
DEFAULT_OUTPUT_DIR = OUTPUT_ROOT / "tier4_29f_20260505_native_mechanism_regression"


@dataclass(frozen=True)
class MechanismSpec:
    tier: str
    mechanism: str
    entry_id: str
    canonical_dir: str
    results_file: str
    summary_file: str
    report_file: str
    runner_revision: str
    expected_seeds: tuple[int, ...]
    expected_total_criteria: int
    expected_passed_criteria: int
    expected_per_seed_criteria: int
    required_criteria_substrings: tuple[str, ...]
    required_control_names: tuple[str, ...] = ()


MECHANISMS: tuple[MechanismSpec, ...] = (
    MechanismSpec(
        tier="4.29a",
        mechanism="native keyed-memory overcapacity",
        entry_id="tier4_29a_native_keyed_memory_overcapacity",
        canonical_dir="tier4_29a_20260503_hardware_pass_ingested",
        results_file="tier4_29a_multi_seed_ingest_summary.json",
        summary_file="tier4_29a_combined_results.json",
        report_file="tier4_29a_ingest_report.md",
        runner_revision="tier4_29a_native_keyed_memory_overcapacity_20260503_0001",
        expected_seeds=(42, 43, 44),
        expected_total_criteria=141,
        expected_passed_criteria=141,
        expected_per_seed_criteria=47,
        required_criteria_substrings=(
            "wrong-key events fail cleanly",
            "overwrite events use new value",
            "slot-shuffle maintains correctness",
        ),
    ),
    MechanismSpec(
        tier="4.29b",
        mechanism="native routing/composition",
        entry_id="tier4_29b_native_routing_composition_gate",
        canonical_dir="tier4_29b_20260503_hardware_pass_ingested",
        results_file="tier4_29b_multi_seed_ingest_summary.json",
        summary_file="tier4_29b_combined_results.json",
        report_file="tier4_29b_report.md",
        runner_revision="tier4_29b_native_routing_composition_20260503_0002",
        expected_seeds=(42, 43, 44),
        expected_total_criteria=156,
        expected_passed_criteria=156,
        expected_per_seed_criteria=52,
        required_criteria_substrings=(
            "wrong-context events fail cleanly",
            "wrong-route events fail cleanly",
            "route overwrite events use new value",
            "route-shuffle maintains correctness",
        ),
    ),
    MechanismSpec(
        tier="4.29c",
        mechanism="native predictive binding",
        entry_id="tier4_29c_native_predictive_binding",
        canonical_dir="tier4_29c_20260504_pass_ingested",
        results_file="tier4_29c_ingest_results.json",
        summary_file="tier4_29c_combined_results.json",
        report_file="tier4_29c_report_seed42.json",
        runner_revision="tier4_29c_native_predictive_binding_20260503_0001",
        expected_seeds=(42, 43, 44),
        expected_total_criteria=78,
        expected_passed_criteria=78,
        expected_per_seed_criteria=26,
        required_criteria_substrings=(
            "learning final weight within tolerance",
            "learning final bias within tolerance",
            "all pending matured",
        ),
    ),
    MechanismSpec(
        tier="4.29d",
        mechanism="native self-evaluation / confidence gating",
        entry_id="tier4_29d_native_self_evaluation",
        canonical_dir="tier4_29d_20260504_pass_ingested",
        results_file="tier4_29d_ingest_results.json",
        summary_file="tier4_29d_combined_results.json",
        report_file="tier4_29d_report_seed44.json",
        runner_revision="tier4_29d_native_self_evaluation_20260504_0002",
        expected_seeds=(42, 43, 44),
        expected_total_criteria=90,
        expected_passed_criteria=90,
        expected_per_seed_criteria=30,
        required_criteria_substrings=(
            "full_confidence_hardware_weight_within_tolerance",
            "zero_confidence_weight_zero",
            "zero_context_confidence_weight_zero",
            "half_context_confidence_weight_magnitude_less_than_full",
        ),
        required_control_names=(
            "full_confidence",
            "zero_confidence",
            "zero_context_confidence",
            "half_context_confidence",
        ),
    ),
    MechanismSpec(
        tier="4.29e",
        mechanism="native host-scheduled replay/consolidation",
        entry_id="tier4_29e_native_replay_consolidation",
        canonical_dir="tier4_29e_20260505_pass_ingested",
        results_file="tier4_29e_ingest_results.json",
        summary_file="tier4_29e_combined_results.json",
        report_file="tier4_29e_report.md",
        runner_revision="tier4_29e_native_replay_consolidation_20260505_0003",
        expected_seeds=(42, 43, 44),
        expected_total_criteria=114,
        expected_passed_criteria=114,
        expected_per_seed_criteria=38,
        required_criteria_substrings=(
            "correct_replay_differs_from_wrong_key",
            "correct_replay_weight_differs_from_no_replay",
            "wrong_key_replay_weight_approx_no_replay",
            "random_event_replay_differs_from_correct_replay",
        ),
        required_control_names=(
            "no_replay",
            "correct_replay",
            "wrong_key_replay",
            "random_event_replay",
        ),
    ),
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def criterion(name: str, value: Any, rule: str, passed: bool, note: str = "") -> dict[str, Any]:
    return {
        "name": name,
        "value": value,
        "rule": rule,
        "passed": bool(passed),
        "note": note,
    }


def status_is_pass(data: dict[str, Any]) -> bool:
    return str(data.get("status", "")).lower() == "pass"


def total_counts(data: dict[str, Any]) -> tuple[int | None, int | None]:
    if "total_criteria_across_seeds" in data:
        return int(data.get("total_criteria_across_seeds", 0)), int(
            data.get("total_passed_across_seeds", 0)
        )
    if "total_criteria" in data:
        return int(data.get("total_criteria", 0)), int(data.get("passed_criteria", 0))
    if "total_count" in data:
        return int(data.get("total_count", 0)), int(data.get("passed_count", 0))
    return None, None


def per_seed_rows(data: dict[str, Any]) -> list[dict[str, Any]]:
    rows = data.get("per_seed") or []
    return rows if isinstance(rows, list) else []


def per_seed_total(row: dict[str, Any]) -> int | None:
    for key in ("criteria_total", "total"):
        if key in row:
            return int(row[key])
    return None


def per_seed_passed(row: dict[str, Any]) -> int | None:
    for key in ("criteria_passed", "passed"):
        if key in row:
            return int(row[key])
    return None


def collect_hardware_criteria(run_dir: Path) -> list[str]:
    names: list[str] = []
    for path in sorted(run_dir.glob("*.json")):
        try:
            data = load_json(path)
        except Exception:
            continue
        criteria = data.get("criteria")
        if isinstance(criteria, list):
            names.extend(str(item.get("name", "")) for item in criteria if isinstance(item, dict))
        control_results = data.get("control_results")
        if isinstance(control_results, list):
            for control in control_results:
                if not isinstance(control, dict):
                    continue
                for item in control.get("criteria", []) or []:
                    if isinstance(item, dict):
                        names.append(str(item.get("name", "")))
    return names


def collect_controls(data: dict[str, Any], run_dir: Path) -> set[str]:
    controls: set[str] = set()
    summary = data.get("control_summary")
    if isinstance(summary, dict):
        controls.update(str(key) for key in summary)
    for path in sorted(run_dir.glob("*.json")):
        try:
            payload = load_json(path)
        except Exception:
            continue
        control_results = payload.get("control_results")
        if isinstance(control_results, list):
            for control in control_results:
                if isinstance(control, dict) and "control" in control:
                    controls.add(str(control["control"]))
    return controls


def evaluate_mechanism(spec: MechanismSpec) -> dict[str, Any]:
    run_dir = OUTPUT_ROOT / spec.canonical_dir
    results_path = run_dir / spec.results_file
    summary_path = run_dir / spec.summary_file
    report_path = run_dir / spec.report_file
    mechanism_criteria: list[dict[str, Any]] = []

    mechanism_criteria.append(
        criterion("canonical directory exists", str(run_dir), "exists", run_dir.exists())
    )
    mechanism_criteria.append(
        criterion("results file exists", str(results_path), "exists", results_path.exists())
    )
    mechanism_criteria.append(
        criterion("summary file exists", str(summary_path), "exists", summary_path.exists())
    )
    mechanism_criteria.append(
        criterion("report file exists", str(report_path), "exists", report_path.exists())
    )

    results: dict[str, Any] = {}
    summary: dict[str, Any] = {}
    if results_path.exists():
        results = load_json(results_path)
    if summary_path.exists():
        summary = load_json(summary_path)

    mechanism_criteria.append(
        criterion("results status pass", results.get("status"), "== pass", status_is_pass(results))
    )
    mechanism_criteria.append(
        criterion("summary status pass", summary.get("status"), "== pass", status_is_pass(summary))
    )
    mechanism_criteria.append(
        criterion(
            "runner revision matches",
            results.get("runner_revision"),
            spec.runner_revision,
            results.get("runner_revision") == spec.runner_revision,
        )
    )

    observed_seeds = tuple(int(seed) for seed in results.get("seeds", []) if str(seed).isdigit())
    mechanism_criteria.append(
        criterion(
            "expected seeds present",
            observed_seeds,
            str(spec.expected_seeds),
            observed_seeds == spec.expected_seeds,
        )
    )

    total, passed = total_counts(results)
    mechanism_criteria.append(
        criterion(
            "total criteria count matches",
            total,
            f"== {spec.expected_total_criteria}",
            total == spec.expected_total_criteria,
        )
    )
    mechanism_criteria.append(
        criterion(
            "total criteria all passed",
            passed,
            f"== {spec.expected_passed_criteria}",
            passed == spec.expected_passed_criteria,
        )
    )

    per_seed = per_seed_rows(results)
    mechanism_criteria.append(
        criterion("per-seed rows present", len(per_seed), f"== {len(spec.expected_seeds)}", len(per_seed) == len(spec.expected_seeds))
    )
    for idx, row in enumerate(per_seed):
        row_total = per_seed_total(row)
        row_passed = per_seed_passed(row)
        label = row.get("seed", spec.expected_seeds[idx] if idx < len(spec.expected_seeds) else idx)
        mechanism_criteria.append(
            criterion(
                f"seed {label} criteria total matches",
                row_total,
                f"== {spec.expected_per_seed_criteria}",
                row_total == spec.expected_per_seed_criteria,
            )
        )
        mechanism_criteria.append(
            criterion(
                f"seed {label} criteria all pass",
                row_passed,
                f"== {spec.expected_per_seed_criteria}",
                row_passed == spec.expected_per_seed_criteria,
            )
        )

    names = collect_hardware_criteria(run_dir)
    for required in spec.required_criteria_substrings:
        matched = any(required in name for name in names)
        mechanism_criteria.append(
            criterion("required control criterion present", required, "substring found", matched)
        )

    controls = collect_controls(results, run_dir)
    for control in spec.required_control_names:
        mechanism_criteria.append(
            criterion("required control summary present", control, "in controls", control in controls)
        )

    failed = [item for item in mechanism_criteria if not item["passed"]]
    return {
        "tier": spec.tier,
        "mechanism": spec.mechanism,
        "entry_id": spec.entry_id,
        "canonical_dir": str(run_dir),
        "status": "pass" if not failed else "fail",
        "criteria_passed": len(mechanism_criteria) - len(failed),
        "criteria_total": len(mechanism_criteria),
        "criteria": mechanism_criteria,
        "failed_criteria": failed,
        "seeds": list(observed_seeds),
        "total_criteria": total,
        "passed_criteria": passed,
    }


def write_summary_csv(path: Path, mechanisms: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "tier",
                "mechanism",
                "status",
                "criteria_passed",
                "criteria_total",
                "hardware_criteria_passed",
                "hardware_criteria_total",
                "seeds",
                "canonical_dir",
            ],
        )
        writer.writeheader()
        for row in mechanisms:
            writer.writerow(
                {
                    "tier": row["tier"],
                    "mechanism": row["mechanism"],
                    "status": row["status"],
                    "criteria_passed": row["criteria_passed"],
                    "criteria_total": row["criteria_total"],
                    "hardware_criteria_passed": row.get("passed_criteria"),
                    "hardware_criteria_total": row.get("total_criteria"),
                    "seeds": ",".join(str(seed) for seed in row.get("seeds", [])),
                    "canonical_dir": row["canonical_dir"],
                }
            )


def write_report(path: Path, results: dict[str, Any]) -> None:
    lines = [
        "# Tier 4.29f Compact Native Mechanism Regression",
        "",
        f"- Generated: `{results['generated_at_utc']}`",
        f"- Status: **{results['status'].upper()}**",
        f"- Runner revision: `{results['runner_revision']}`",
        f"- Mode: `{results['mode']}`",
        f"- Criteria: `{results['criteria_passed']}/{results['criteria_total']}`",
        "",
        "## Claim Boundary",
        "",
        results["claim_boundary"],
        "",
        "## Mechanism Rows",
        "",
        "| Tier | Mechanism | Status | Audit Criteria | Hardware Criteria | Seeds |",
        "| --- | --- | --- | ---: | ---: | --- |",
    ]
    for row in results["mechanisms"]:
        lines.append(
            "| "
            f"{row['tier']} | "
            f"{row['mechanism']} | "
            f"{row['status']} | "
            f"{row['criteria_passed']}/{row['criteria_total']} | "
            f"{row.get('passed_criteria')}/{row.get('total_criteria')} | "
            f"`{','.join(str(seed) for seed in row.get('seeds', []))}` |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- This pass freezes the cumulative native mechanism bridge evidence set only if all rows pass.",
            "- It does not create a new hardware execution trace.",
            "- It does not prove all five mechanisms are simultaneously active in one monolithic task.",
            "- It authorizes moving to standard benchmarks only if the freeze artifact is created from this pass.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def run_local(output_dir: Path) -> dict[str, Any]:
    mechanisms = [evaluate_mechanism(spec) for spec in MECHANISMS]
    all_criteria: list[dict[str, Any]] = [
        criterion(
            "runner revision current",
            RUNNER_REVISION,
            "expected current source",
            RUNNER_REVISION.endswith("_0001"),
        ),
        criterion(
            "all mechanism rows pass",
            [row["status"] for row in mechanisms],
            "all == pass",
            all(row["status"] == "pass" for row in mechanisms),
        ),
    ]
    for row in mechanisms:
        all_criteria.extend(
            {
                **item,
                "name": f"{row['tier']} {item['name']}",
            }
            for item in row["criteria"]
        )
    failed = [item for item in all_criteria if not item["passed"]]
    status = "pass" if not failed else "fail"
    results = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "mode": "local-evidence-regression",
        "status": status,
        "output_dir": str(output_dir),
        "criteria_passed": len(all_criteria) - len(failed),
        "criteria_total": len(all_criteria),
        "criteria": all_criteria,
        "failed_criteria": failed,
        "mechanisms": mechanisms,
        "claim_boundary": (
            "Tier 4.29f is a canonical evidence-regression gate over the real "
            "hardware passes from 4.29a-e. It verifies that native keyed memory, "
            "routing/composition, predictive binding, confidence gating, and "
            "host-scheduled replay/consolidation all remain complete and aligned "
            "as ingested evidence. It is not a new SpiNNaker execution, not a "
            "single-task all-mechanism stack proof, not lifecycle evidence, not "
            "multi-chip scaling, and not speedup evidence."
        ),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "tier4_29f_results.json", results)
    write_summary_csv(output_dir / "tier4_29f_summary.csv", mechanisms)
    write_report(output_dir / "tier4_29f_report.md", results)
    write_json(
        OUTPUT_ROOT / "tier4_29f_latest_manifest.json",
        {
            "tier": TIER,
            "runner_revision": RUNNER_REVISION,
            "generated_at_utc": results["generated_at_utc"],
            "status": status,
            "manifest": str(output_dir / "tier4_29f_results.json"),
            "output_dir": str(output_dir),
            "registry_entry_id": "tier4_29f_compact_native_mechanism_regression",
        },
    )
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=TIER)
    parser.add_argument(
        "--mode",
        choices=("local", "local-evidence-regression"),
        default="local",
        help="Run the local evidence-regression audit.",
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    results = run_local(args.output_dir)
    print(json.dumps({
        "tier": TIER,
        "status": results["status"],
        "criteria": f"{results['criteria_passed']}/{results['criteria_total']}",
        "output_dir": str(args.output_dir),
    }, indent=2))
    if results["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
