#!/usr/bin/env python3
"""Tier 7.0g - General Mechanism-Selection Contract.

This is a contract gate, not a mechanism implementation.

It consumes Tier 7.0f and the valid 8000-step public scoreboard rerun, then
selects the next planned mechanism based on the measured public failure class.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
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


TIER = "Tier 7.0g - General Mechanism-Selection Contract"
RUNNER_REVISION = "tier7_0g_general_mechanism_selection_contract_20260508_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_0g_20260508_general_mechanism_selection_contract"
DEFAULT_TIER7_0F = CONTROLLED / "tier7_0f_20260508_benchmark_protocol_failure_localization"
DEFAULT_8000 = CONTROLLED / "tier7_0e_20260508_length_8000_scoreboard"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def safe_float(value: Any) -> float | None:
    if value in ("", None):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def load_inputs(tier7_0f_dir: Path, score8000_dir: Path) -> dict[str, Any]:
    return {
        "tier7_0f": json.loads((tier7_0f_dir / "tier7_0f_results.json").read_text(encoding="utf-8")),
        "tier7_0f_summary": read_csv(tier7_0f_dir / "tier7_0f_summary.csv"),
        "score8000": json.loads((score8000_dir / "tier7_0e_results.json").read_text(encoding="utf-8")),
        "score8000_aggregate": read_csv(score8000_dir / "tier7_0e_model_aggregate.csv"),
        "score8000_summary": read_csv(score8000_dir / "tier7_0e_summary.csv"),
    }


def aggregate_metric(rows: list[dict[str, Any]], model: str) -> float | None:
    row = next((item for item in rows if item.get("model") == model), None)
    return None if row is None else safe_float(row.get("geomean_mse"))


def select_mechanism(inputs: dict[str, Any]) -> dict[str, Any]:
    aggregate = inputs["score8000_aggregate"]
    v22 = aggregate_metric(aggregate, "fading_memory_only_ablation")
    esn = aggregate_metric(aggregate, "fixed_esn_train_prefix_ridge_baseline")
    lag = aggregate_metric(aggregate, "lag_only_online_lms_control")
    reservoir = aggregate_metric(aggregate, "fixed_random_reservoir_online_control")
    esn_gap = None if v22 is None or esn is None or esn <= 0 else v22 / esn
    beats_lag = bool(v22 is not None and lag is not None and v22 < lag)
    beats_reservoir = bool(v22 is not None and reservoir is not None and v22 < reservoir)
    mechanism = {
        "selected_mechanism": "bounded_nonlinear_recurrent_continuous_state_interface",
        "why_selected": [
            "ESN dominates Mackey-Glass/Lorenz, indicating nonlinear recurrent state plus train-prefix readout remains stronger than v2.2 fading memory.",
            "NARMA10 favors explicit lag memory, indicating the next mechanism needs stronger causal memory/readout rather than only longer exposure.",
            "v2.2 ranks second at 8000 and beats lag/reservoir aggregate, so the path is worth repairing rather than abandoning.",
        ],
        "why_not_sleep_replay_now": "The current public failure is continuous sequence modeling, not measured retention decay after reentry.",
        "why_not_lifecycle_now": "Lifecycle helps ecology, but the measured public gap is readout/state capacity on stationary sequence tasks.",
        "why_not_hardware_now": "Hardware transfer cannot rescue a software benchmark gap; transfer only after software earns a useful regime.",
        "score8000": {
            "v2_2_geomean_mse": v22,
            "esn_geomean_mse": esn,
            "lag_geomean_mse": lag,
            "reservoir_geomean_mse": reservoir,
            "v2_2_divided_by_esn": esn_gap,
            "v2_2_beats_lag": beats_lag,
            "v2_2_beats_reservoir": beats_reservoir,
        },
    }
    return mechanism


def build_contract(mechanism: dict[str, Any]) -> dict[str, Any]:
    return {
        "tier": "Tier 7.0h / mechanism implementation candidate",
        "mechanism": mechanism["selected_mechanism"],
        "hypothesis": (
            "A bounded nonlinear recurrent continuous-state interface layered on v2.2 will improve "
            "standard dynamical benchmark performance by adding reusable causal state beyond fading "
            "memory alone, without task-specific labels or leakage."
        ),
        "null_hypothesis": (
            "Nonlinear recurrent state does not improve over v2.2 fading memory, or any improvement "
            "is matched by shuffled/permuted/frozen-state controls."
        ),
        "public_tasks": ["mackey_glass", "lorenz", "narma10"],
        "required_lengths": [720, 2000, 8000],
        "optional_sensitivity": {"narma10_10000_finite_seeds": [42, 43, 45]},
        "baselines": [
            "v2.2 fading_memory_only_ablation",
            "lag_only_online_lms_control",
            "fixed_random_reservoir_online_control",
            "fixed_esn_train_prefix_ridge_baseline",
        ],
        "controls_and_ablations": [
            "no_recurrence_ablation",
            "permuted_recurrence_sham",
            "frozen_state_after_train_prefix",
            "state_reset_ablation",
            "shuffled_state_rows",
            "shuffled_target_control",
            "no_plasticity_or_no_update_control",
        ],
        "promotion_criteria": [
            "aggregate geomean MSE improves at least 25 percent versus v2.2 at the valid 8000-step same-seed scoreboard",
            "mechanism beats lag-only aggregate or identifies a task-specific complement with predeclared claim boundary",
            "Mackey-Glass/Lorenz ESN gap narrows materially without worsening NARMA10",
            "permuted/frozen/shuffled/no-update controls do not match the promoted mechanism",
            "finite-stream and leakage guardrails pass",
            "compact regression passes before any baseline freeze",
        ],
        "fail_or_park_criteria": [
            "no material improvement over v2.2",
            "shams match the candidate",
            "improvement appears only on a private diagnostic task",
            "NARMA10 or any public task regresses without a declared tradeoff",
            "result requires test-row fitting, future leakage, or task-specific seed hacking",
        ],
        "nonclaims": [
            "not sleep/replay",
            "not lifecycle/self-scaling",
            "not hardware transfer",
            "not a baseline freeze",
            "not AGI/ASI evidence",
        ],
    }


def write_report(output_dir: Path, payload: dict[str, Any]) -> None:
    contract = payload["contract"]
    mechanism = payload["selection"]
    lines = [
        "# Tier 7.0g General Mechanism-Selection Contract",
        "",
        f"- Generated: `{payload['generated_at_utc']}`",
        f"- Status: **{payload['status'].upper()}**",
        f"- Criteria: `{payload['criteria_passed']}/{payload['criteria_total']}`",
        f"- Selected mechanism: `{mechanism['selected_mechanism']}`",
        "",
        "## Why This Mechanism",
        "",
    ]
    for item in mechanism["why_selected"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Contract",
            "",
            f"- Hypothesis: {contract['hypothesis']}",
            f"- Null: {contract['null_hypothesis']}",
            f"- Required lengths: `{contract['required_lengths']}`",
            "",
            "Promotion criteria:",
            "",
        ]
    )
    for item in contract["promotion_criteria"]:
        lines.append(f"- {item}")
    lines.extend(["", "Fail or park criteria:", ""])
    for item in contract["fail_or_park_criteria"]:
        lines.append(f"- {item}")
    lines.extend(["", "Nonclaims:", ""])
    for item in contract["nonclaims"]:
        lines.append(f"- {item}")
    lines.append("")
    (output_dir / "tier7_0g_report.md").write_text("\n".join(lines), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=TIER)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--tier7-0f-dir", type=Path, default=DEFAULT_TIER7_0F)
    parser.add_argument("--score8000-dir", type=Path, default=DEFAULT_8000)
    return parser


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    inputs = load_inputs(args.tier7_0f_dir.resolve(), args.score8000_dir.resolve())
    selection = select_mechanism(inputs)
    contract = build_contract(selection)
    criteria = [
        criterion("Tier 7.0f loaded", inputs["tier7_0f"].get("status"), "pass", inputs["tier7_0f"].get("status") == "pass"),
        criterion("8000 scoreboard loaded", inputs["score8000"].get("status"), "pass", inputs["score8000"].get("status") == "pass"),
        criterion("v2.2 beats lag/reservoir aggregate at 8000", selection["score8000"], "beats lag and reservoir", bool(selection["score8000"]["v2_2_beats_lag"] and selection["score8000"]["v2_2_beats_reservoir"])),
        criterion("ESN gap remains material", selection["score8000"]["v2_2_divided_by_esn"], "> 2.0", bool((selection["score8000"]["v2_2_divided_by_esn"] or 0.0) > 2.0)),
        criterion("mechanism selected", selection["selected_mechanism"], "non-empty", bool(selection["selected_mechanism"])),
        criterion("promotion criteria declared", len(contract["promotion_criteria"]), ">= 5", len(contract["promotion_criteria"]) >= 5),
        criterion("nonclaims declared", contract["nonclaims"], "includes no hardware/no freeze", "not hardware transfer" in contract["nonclaims"] and "not a baseline freeze" in contract["nonclaims"]),
    ]
    status = "pass" if all(item["passed"] for item in criteria) else "fail"
    payload = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "status": status,
        "criteria": criteria,
        "criteria_passed": sum(1 for item in criteria if item["passed"]),
        "criteria_total": len(criteria),
        "output_dir": str(output_dir),
        "selection": selection,
        "contract": contract,
        "claim_boundary": "Tier 7.0g is a mechanism-selection contract only; it does not implement or prove the mechanism.",
    }
    write_json(output_dir / "tier7_0g_results.json", payload)
    write_json(output_dir / "tier7_0g_contract.json", contract)
    write_rows(
        output_dir / "tier7_0g_summary.csv",
        [
            {
                "status": status,
                "selected_mechanism": selection["selected_mechanism"],
                "v2_2_geomean_mse": selection["score8000"]["v2_2_geomean_mse"],
                "esn_geomean_mse": selection["score8000"]["esn_geomean_mse"],
                "v2_2_divided_by_esn": selection["score8000"]["v2_2_divided_by_esn"],
                "next_tier": contract["tier"],
            }
        ],
    )
    write_report(output_dir, payload)
    write_json(
        CONTROLLED / "tier7_0g_latest_manifest.json",
        {
            "tier": TIER,
            "runner_revision": RUNNER_REVISION,
            "generated_at_utc": payload["generated_at_utc"],
            "status": status,
            "manifest": str(output_dir / "tier7_0g_results.json"),
            "output_dir": str(output_dir),
        },
    )
    return payload


def main() -> None:
    result = run(build_parser().parse_args())
    print(
        json.dumps(
            {
                "tier": TIER,
                "status": result["status"],
                "criteria": f"{result['criteria_passed']}/{result['criteria_total']}",
                "selected_mechanism": result["selection"]["selected_mechanism"],
                "output_dir": result["output_dir"],
            },
            indent=2,
        )
    )
    if result["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
